#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Finite-face first contact and branch accommodation for explicit box/can trials.

Not a grasp rating. Object heights, insertion and alignment below are trial
variables, not user-specified inputs. Use actual frozen uncompressed petal CAD.
"""
from pathlib import Path
import csv, hashlib, json, math
import numpy as np
import cadquery as cq
from scipy.optimize import brentq
from build_layout import moved
from r5_head_geometry01 import FINGERS, axes, transform

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-grasp-range01'
SRC=ROOT/'engineering/generated/r5-petal-form01'
LINK=ROOT/'engineering/generated/r5-link01/study.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
params=json.loads(LINK.read_text())['parameters']
R=62.;FACE_OFFSET=6.

def slider(q,p):
 t=q+p['phase_rad'];a=p['crank_mm'];L=p['rod_mm'];d=R-p['slider_ear_radius_mm']
 return a*math.sin(t)-math.sqrt(L*L-(d+a*math.cos(t))**2)

def length(q,x,p):
 a=p['crank_mm'];t=q+p['phase_rad'];d=R-p['slider_ear_radius_mm']
 return math.hypot(d+a*math.cos(t),a*math.sin(t)-x)

def support(shape,width,yaw,f):
 er,et,ez=axes(f[3]);a=width/2
 if shape=='cylinder':xy=a*er
 else:
  g=math.radians(yaw);u=np.array([math.cos(g),math.sin(g),0]);v=np.array([-math.sin(g),math.cos(g),0])
  xy=a*(np.sign(er@u)*u+np.sign(er@v)*v)
 return float(er@xy),xy

def contact(shape,width,z0,height,yaw,f,skin):
 rho,xy=support(shape,width,yaw,f);z1=z0+height
 def gap(q):return (R-rho)*math.sin(q)+(z0 if math.cos(q)>=0 else z1)*math.cos(q)-FACE_OFFSET
 q=brentq(gap,0,math.radians(170),xtol=1e-14);qmax=math.radians(f[4]);z=min(max(65.,z0),z1) if abs(q-math.pi/2)<1e-9 else (z0 if q<math.pi/2 else z1)
 point=xy+np.array([0,0,z]);T=transform(f,q);local=np.linalg.solve(T[:3,:3],point-T[:3,3]);dist=skin.distance(cq.Vertex.makeVertex(*local));within=dist<1e-6
 # Report an extra edge-neighborhood check separately; point accessibility
 # alone does not require or imply this 2 mm margin.
 disk=cq.Solid.makeCylinder(2.,.02,cq.Vector(local[0],local[1],9.48))
 outside=sum(abs(s.Volume()) for s in disk.cut(skin).Solids())
 feasible=q<=qmax+1e-10 and within
 return dict(finger=f[0],family=f[1],infinite_face_first_contact_deg=math.degrees(q),angle_limit_deg=f[4],within_angle_limit=q<=qmax+1e-10,point_head_mm=point.tolist(),point_petal_mm=local.tolist(),nominal_skin_distance_mm=dist,contact_point_on_finite_luminous_face=within,contained_R2_neighborhood=outside<1e-5,R2_patch_is_not_physical_contact_area=True,object_contact_region='barrel generator / box vertical edge' if abs(q-math.pi/2)<1e-9 else ('rear rim / rear corner' if q<math.pi/2 else 'front rim / front corner'),face_first_contact_accessible=feasible,slider_at_contact_mm=slider(q,params[f[1]]) if q<=qmax+1e-10 else None,point_q_rad=q)

def accommodation(rows):
 if not all(r['face_first_contact_accessible'] for r in rows):return dict(available=False,reason='At least one plane support point misses finite luminous face or exceeds angle limit; no four-face contact/compliance result inferred')
 xs=[r['slider_at_contact_mm'] for r in rows];last=max(xs);result=[]
 for r in rows:
  p=params[r['family']];delta=length(r['point_q_rad'],last,p)-p['rod_mm']
  result.append(dict(finger=r['finger'],slider_contact_mm=r['slider_at_contact_mm'],rod_length_change_at_last_contact_mm=delta,compression_needed_mm=max(0.,-delta),extension_needed_mm=max(0.,delta)))
 return dict(available=True,first_slider_contact_mm=min(xs),last_slider_contact_mm=last,additional_master_travel_after_first_mm=max(xs)-min(xs),branches=result,maximum_branch_compression_mm=max(r['compression_needed_mm'] for r in result),interpretation='Geometric accommodation only while first contacting finger remains fixed; independent series branch springs or another differential needed. No stiffness/preload/force, friction, object motion or guaranteed allocation implied.')

def actual_first_contact(case,f,source,analytic):
 """BRep challenge for missed finite face only. Fixed object; nominal solids."""
 w=case['width_mm'];z0=case['rear_Z_mm'];h=case['height_mm']
 obj=cq.Solid.makeCylinder(w/2,h,cq.Vector(0,0,z0)) if case['shape']=='cylinder' else cq.Workplane('XY').box(w,w,h,centered=(True,True,False)).val().translate((0,0,z0)).rotate((0,0,0),(0,0,1),case['yaw_deg'])
 compound=cq.Compound.makeCompound(list(source.values()))
 def gap(q):return moved(compound,transform(f,q)).distance(obj)
 lo=analytic['point_q_rad'];limit=math.radians(f[4])
 if lo>limit:return dict(reached=False,reason='Whole object stays strictly ahead of the face plane throughout admitted angle interval')
 if gap(lo)<1e-7:hi=lo
 else:
  hi=None
  for q in np.linspace(lo,limit,max(2,int(math.ceil((limit-lo)*180/math.pi))+1))[1:]:
   if gap(q)<1e-7:hi=q;break
   lo=q
  if hi is None:return dict(reached=False,reason='No distance zero in <=1deg grid after analytic lower bound; sampling does not prove continuous noncontact',minimum_end_distance_mm=gap(limit))
  for _ in range(30):
   mid=(lo+hi)/2
   if gap(mid)<1e-7:hi=mid
   else:lo=mid
 q=hi;checks=[]
 for name,part in source.items():
  d=moved(part,transform(f,q)).distance(obj);checks.append(dict(part=name,distance_mm=d))
 return dict(reached=True,contact_angle_deg=math.degrees(q),first_touch_parts_at_1um=[r['part'] for r in checks if r['distance_mm']<.001],parts=checks,method='Analytic plane supplies collision-free approach lower bound; <=1deg grid then bisection of BRep distance for subsequent first observed zero; no continuous global root certification beyond plane bound')

def main():
 OUT.mkdir(parents=True,exist_ok=True);sources={};hashes={}
 for path in [Path(__file__),LINK,ROOT/'engineering/parameters/confirmed-inputs.json',ROOT/'engineering/r5_head_geometry01.py',ROOT/'engineering/build_layout.py']:
  hashes[str(path.relative_to(ROOT))]=sha(path)
 for f in FINGERS:
  sources[f[0]]={}
  for path in sorted((SRC/(f[1]+'-'+f[2])).glob('*.step')):
   if path.name.startswith('R5-'):continue
   sources[f[0]][path.stem]=cq.importers.importStep(str(path)).val();hashes[str(path.relative_to(ROOT))]=sha(path)
 cases=[]
 for shape,yaw in [('cylinder',0),('box',0),('box',15)]:
  for w in [50,65,80,100,112,120]:
   for h in [60,100,160]:
    for z0 in [10,20,40,60]:
     c=dict(shape=shape,width_mm=w,height_mm=h,rear_Z_mm=z0,yaw_deg=yaw)
     rows=[contact(shape,w,z0,h,yaw,f,sources[f[0]]['compliant_skin']) for f in FINGERS]
     acc=accommodation(rows);c.update(fingers=rows,accommodation=acc,four_finite_face_contacts_accessible=all(r['face_first_contact_accessible'] for r in rows),all_four_have_R2_neighborhood=all(r['contained_R2_neighborhood'] for r in rows));cases.append(c)
 audit=[]
 for c in cases:
  if c['yaw_deg']!=0 or c['rear_Z_mm']!=20 or c['height_mm'] not in [60,100] or c['width_mm'] not in [50,80,120]:continue
  for fid in ['UR','LR']:
   row=next(x for x in c['fingers'] if x['finger']==fid)
   if row['face_first_contact_accessible']:continue
   f=next(f for f in FINGERS if f[0]==fid);r=actual_first_contact(c,f,sources[fid],row);audit.append(dict(case={k:c[k] for k in ['shape','width_mm','height_mm','rear_Z_mm','yaw_deg']},finger=fid,result=r))
 (OUT/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');(OUT/'brep-challenges.json').write_text(json.dumps(audit,indent=2)+'\n')
 fields=['shape','yaw_deg','width_mm','height_mm','rear_Z_mm','four_finite_face_contacts_accessible','all_four_have_R2_neighborhood','first_slider_contact_mm','last_slider_contact_mm','additional_master_travel_after_first_mm','maximum_branch_compression_mm']
 with (OUT/'summary.csv').open('w',newline='') as fh:
  writer=csv.DictWriter(fh,fieldnames=fields);writer.writeheader()
  for c in cases:writer.writerow({k:c.get(k,c['accommodation'].get(k)) for k in fields})
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axs=plt.subplots(1,3,figsize=(14,4.8),sharey=True)
 for ax,(shape,yaw) in zip(axs,[('cylinder',0),('box',0),('box',15)]):
  for c in cases:
   if c['shape']!=shape or c['yaw_deg']!=yaw or c['rear_Z_mm']!=20:continue
   good=c['four_finite_face_contacts_accessible'];ax.scatter(c['width_mm'],c['height_mm'],c='#268479' if good else '#b6534d',marker='o' if good else 'x',s=90)
  ax.set(title=f'{shape} / yaw {yaw}deg',xlabel='Width / diameter [mm]',xticks=[50,65,80,100,112,120],yticks=[60,100,160]);ax.grid(alpha=.2)
 axs[0].set_ylabel('Trial object height along head Z [mm]');fig.suptitle('Finite luminous-face first contact | object rear Z=20 mm\nGreen: geometry accessible with branch accommodation; red: plane contact misses face or exceeds stop',fontsize=11);fig.tight_layout();fig.savefig(OUT/'range-map.png',dpi=170);fig.savefig(OUT/'range-map.pdf');plt.close(fig)
 summary=dict(revision='R5-GRASP-RANGE01',source_hashes=hashes,user_width_target_mm=[50,120],trial_heights_mm=[60,100,160],trial_rear_Z_mm=[10,20,40,60],trial_object_shapes='Round cylinder with axis head Z; square prism rotated0/15deg about head Z. Dimensions, poses and sharp corners are trial assumptions, not user requirements.',cases=len(cases),four_face_accessible_cases=sum(c['four_finite_face_contacts_accessible'] for c in cases),BRep_challenges=len(audit),friction_object_deformation_and_branch_spring_force_qualified=False,full_head_obstacle_qualified=False,manufacturing_release=False,artifact_hashes={f.name:sha(f) for f in OUT.iterdir() if f.is_file() and f.name!='study.json'})
 (OUT/'study.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ['source_hashes','artifact_hashes']}))
if __name__=='__main__':main()
