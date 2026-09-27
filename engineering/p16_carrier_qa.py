#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Carrier geometry QA and original CAD render; no vendor media output."""
from pathlib import Path
import hashlib,json,math
import numpy as np
import cadquery as cq
import trimesh
import p16_carrier_study as cs
import p16_carrier_review as cr
import p16_packaging_study as p16
import gripper_root_support_study as st
ROOT,OUT=cs.ROOT,cs.OUT

def render(rows):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from mpl_toolkits.mplot3d.art3d import Poly3DCollection
 fig=plt.figure(figsize=(14,8));axes=[fig.add_subplot(121,projection='3d'),fig.add_subplot(122,projection='3d')]
 polys=[];cols=[]
 for n,s in rows:
  v,t=s.tessellate(.6);v=np.array([x.toTuple() for x in v]);t=np.array(t)
  col='#f0b638' if 'LED' in n else '#148778' if 'display' in n or 'pad' in n else '#203742' if 'camera' in n or 'P16' in n else '#5c8890' if n=='main_carrier' else '#afb8bd'
  polys.extend(v[t]);cols.extend([col]*len(t))
 for ax in axes:
  ax.add_collection3d(Poly3DCollection(polys,facecolor=cols,edgecolor='none'))
  ax.set(xlim=(-190,190),ylim=(-155,180),zlim=(-160,180),xlabel='Head x / mm',ylabel='Head y / mm',zlabel='Head z / mm');ax.set_box_aspect((380,335,340))
 axes[0].view_init(24,-62);axes[0].set_title('Original solid assembly / open pose')
 axes[1].view_init(90,-90);axes[1].set_proj_type('ortho');axes[1].set_zticks([]);axes[1].set_zlabel('');axes[1].set_title('Front / upper and lower pairs remain independent')
 fig.suptitle('P16-CARRIER-01 | Load path and optical packaging study\nNominal metal geometry + original supplier envelopes; not manufacturing release',fontsize=14)
 fig.tight_layout();fig.savefig(OUT/'carrier-open.png',dpi=160);plt.close(fig)


def led_probe(f,fixed):
 probe=cs.B(38.5,47.5,-8.75,8.75,-3.7,0);obstacles=cs.FastSet(fixed.values());rows=[];act=[]
 for i,ff in enumerate(f):
  r=p16.certificate(lambda q:cs.FastSet([st.place(probe,ff,st.SIGNS[i],q)]),lambda q:obstacles,p16.radius(probe),ff['closure_study_deg'],step=2)
  rows.append(dict(finger=ff['id'],**r))
 for i in [0,2]:
  ff=f[i];Vact=26+160*26*(123+26)/p16.kin(0)[2]**2
  r=p16.certificate(lambda q:cs.FastSet([probe.rotate((0,0,0),(0,1,0),-q)]),lambda q:cs.FastSet(p16.envelopes(q).values()),p16.radius(probe)+Vact,ff['closure_study_deg'],step=2)
  act.append(dict(finger=ff['id'],**r))
 return dict(revision='P16-CARRIER-01',provisional_keepout_local_mm=[[38.5,-8.75,-3.7],[47.5,8.75,0]],source='Parent latest pocket centeredX43, openingX38.5..47.5/Y+/-8.75. Direct GH7.3mm stack reachesZ-3.7; side GH4.35mm reachesZ-0.75. This is a conservative below-plate pocket-sized probe, not mated connector CAD.',fixed_obstacle_checks=rows,own_P16_continuous_checks=act,earlier_box_superseded=dict(box=[[25,-7,-4],[40,7,0]],old_constant_u_gap_mm=.9,conclusion='Old0.9mm u-slab separation does NOT apply to the wider latest pocket. Recomputed geometric certificates replace it.'),scope='Backside space against fixed carrier/optics and own actuator only. Does not replace actual GH/pin/wire/PCB integration, inner cavity fit or adjacent moving-petal proof. x>25 geometry remains parent-owned and unmodified.')


def wrist_probe():
 from mount_interface_study import load_vendor,collision
 from build_layout import frame,moved
 model=next(x for x in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models'] if x['id']=='RH17-B')
 vp=ROOT.parents[1]/'work/r4-joints/cad17/RH-17-100-E-B-D/RH-17-100-E-B-D 3D-A.STEP'
 j6=moved(load_vendor(vp,model),frame([0,0,605],[0,1,0]));path=OUT/'main-carrier.step';car=cq.importers.importStep(str(path)).val();rows=[]
 for q in [-90.,90.]:
  s=car.rotate((0,0,0),(0,0,1),q).translate((0,55,780));d=collision(s,j6);rows.append(dict(q7_deg=q,**d))
 return dict(revision='P16-CARRIER-01',scope='Final carrier vs native RH17-B J6 only, q6=0, baseline axis origins; failure witness, no motion-range approval.',carrier_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),J6_sha256=hashlib.sha256(vp.read_bytes()).hexdigest(),J7_world_axis_mm=[0,55,640],face_world_mm=[0,55,780],rows=rows,current_plus_minus90_supported=False)


def main():
 f,roots,base,fixed,mods,om=cs.nominal();qa={'revision':'P16-CARRIER-01','parts':[]};oldpath=ROOT.parents[1]/'work/p16-carrier-reference/carrier-before-bore-access-fix.step'
 if oldpath.exists():
  old=cq.importers.importStep(str(oldpath)).val();new=fixed['main_carrier'];delta=new.cut(old).Volume();removed=old.cut(new).Volume();assert delta<1e-5
  qa['late_drilling_fix']=dict(new_material_outside_checked_old_carrier_mm3=delta,removed_material_mm3=removed,reason='Re-cut axial bore after all unions to keep bottom drilling access open; old carrier subset collision and service results remain conservative.',native_J7_proof_preserved_by_subset=True)
 # STEP roundtrip and watertight QA only on original parts; no massive mesh asset deliverable.
 for name in ['main-carrier','integral-steel-root-spindle','bearing-outer-cap','base-bracket','removable-optical-frame']:
  path=OUT/(name+'.step');s=cq.importers.importStep(str(path)).val();v,t=s.tessellate(.12,.12);mesh=trimesh.Trimesh(vertices=[x.toTuple() for x in v],faces=t,process=True)
  q=dict(part=name,valid=s.isValid(),solid_count=len(s.Solids()),mesh_watertight=bool(mesh.is_watertight),mesh_body_count=int(mesh.body_count),bbox_mm=[x.tolist() for x in st.bb(s)],volume_mm3=s.Volume(),step_sha256=hashlib.sha256(path.read_bytes()).hexdigest());assert q['valid'] and q['solid_count']==1 and q['mesh_watertight'];qa['parts'].append(q)
 # Nominal bore access: directly test bottom centerline above the drilling opening.
 access=[]
 for i,ff in enumerate(f):
  bottom=min(-154+ff['root_z_mm'],-130)-ff['root_z_mm'];probe=st.place(cs.C(6.9,-28-bottom,(0,24,bottom-.01),(0,0,1)),ff,st.SIGNS[i]);v=probe.intersect(fixed['main_carrier']).Volume();access.append(dict(finger=ff['id'],tool_probe_D_mm=13.8,clear_path_mm=-28-bottom,positive_intersection_mm3=v,passes=v<1e-5))
 assert all(x['passes'] for x in access);qa['blind_bore_access']=access
 rows=list(fixed.items())
 for i,ff in enumerate(f):
  rows.extend((ff['id']+'_'+k,st.place(s,ff,st.SIGNS[i])) for k,s in roots[i][0].items());rows.extend((ff['id']+'_P16_'+k,st.place(s,ff,st.SIGNS[i])) for k,s in p16.envelopes(0).items())
 render(rows)
 (OUT/'led-interface-reservation.json').write_text(json.dumps(led_probe(f,fixed),indent=2)+'\n')
 (OUT/'wrist-cross-check.json').write_text(json.dumps(wrist_probe(),indent=2)+'\n')
 # Recompute mass after the final bore access correction; previous tool paths only lose obstacles.
 rev=json.loads((OUT/'review.json').read_text());rev['mass']=cr.mass(f,roots,base,fixed,om);rev['service']['post_boolean_note']='Final carrier drilling only removes material; contained subset verified in qa.json, so prior tool clearance remains valid.'
 (OUT/'review.json').write_text(json.dumps(rev,indent=2)+'\n');(OUT/'qa.json').write_text(json.dumps(qa,indent=2)+'\n')
 import csv
 with (OUT/'mass-ledger.csv').open('w',newline='') as h:
  w=csv.writer(h);w.writerow(['part','mass_g','head_com_x_mm','head_com_y_mm','head_com_z_mm','method'])
  for r in rev['mass']['rows']:w.writerow([r['part'],r['mass_g'],*r['head_center_mm'],r['method']])
 print('QA',len(qa['parts']),'mass',rev['mass']['modeled_mass_g'],rev['mass']['open_COM_proxy_head_mm'],flush=True)
if __name__=='__main__':main()
