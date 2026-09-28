#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5 shaped-petal closure and one finite luminous-face contact case.

Original petal parts only: no complete head, actuator, hinges or cable claim.
The separating-plane bounds cover independent angles, hence any coupled path
within those limits. Nominal geometry is not a tolerance/deflection guarantee.
"""
from pathlib import Path
import csv, hashlib, itertools, json, math
import numpy as np
import cadquery as cq
from scipy.spatial import ConvexHull
from scipy.optimize import linprog
from build_layout import moved
from head_mass04_study import geometry_properties
from screen_integrated_collisions import named_step

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'engineering/generated/r5-petal-form01'
OUT=ROOT/'engineering/generated/r5-head-geometry01'
REV='R5-HEAD-GEOMETRY01'
R=62.
H=3.5
CONTACT_FACE_Z=9.5
SPHERE_R=R-(CONTACT_FACE_Z-H)
SPHERE_Z=65.
FINGERS=[('UR','upper','right',35.,105.),('UL','upper','left',145.,105.),('LL','lower','left',225.,113.),('LR','lower','right',315.,113.)]
COLORS={'frame':'#384d59','retainer':'#253641','bearing_cover':'#8ebecb','compliant_skin':'#efbc51','PCB_blank_reservation':'#257452','back_electronics_reservation':'#87669b','LED_front_reservation':'#c79332'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,(np.integer,np.floating,np.bool_)):return x.item()
 raise TypeError(type(x).__name__)
def dump(name,x):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(x,indent=2,default=serial)+'\n')
def volume(s):return sum(abs(t.Volume()) for t in s.Solids())
def axes(phi):
 p=math.radians(phi);return np.array([math.cos(p),math.sin(p),0.]),np.array([-math.sin(p),math.cos(p),0.]),np.array([0.,0.,1.])
def transform(f,q):
 er,et,ez=axes(f[3]);c,s=math.cos(q),math.sin(q);rot=np.column_stack((c*er+s*ez,et,-s*er+c*ez));T=np.eye(4);T[:3,:3]=rot;T[:3,3]=R*er-rot@np.array([0.,0.,H]);return T
def vertices(p,f):
 sign=1 if f[2]=='right' else -1
 return np.array([[x,sign*y,z-H] for x,y in p[f[1]]['outline_knots_mm'] for z in [0.,CONTACT_FACE_Z]])
def extremum(p,f,n):
 er,et,ez=axes(f[3]);end=math.radians(f[4]);values=[]
 for index,(x,y,z) in enumerate(vertices(p,f)):
  A=(n@er)*x+(n@ez)*z;B=(n@ez)*x-(n@er)*z;C=R*(n@er)+y*(n@et)
  qs=[0.,end]+[v for k in range(-2,3) if 0.<=(v:=math.atan2(B,A)+k*math.pi)<=end]
  values.extend((A*math.cos(q)+B*math.sin(q)+C,index,q) for q in qs)
 return min(values),max(values)

def continuous_certificate(p,source):
 containment=[]
 for f in FINGERS:
  xy=np.array(p[f[1]]['outline_knots_mm'],float);xy[:,1]*=(1 if f[2]=='right' else -1);hull=xy[ConvexHull(xy).vertices]
  envelope=cq.Workplane('XY').polyline(hull.tolist()).close().extrude(CONTACT_FACE_Z).val()
  for name,s in source[f[0]].items():
   v=volume(s.cut(envelope));assert v<1e-4,(f[0],name,v)
   containment.append(dict(finger=f[0],part=name,outside_convex_prism_mm3=v))
 rows=[]
 for a,b in itertools.combinations(FINGERS,2):
  n=axes(a[3])[0]-axes(b[3])[0];n/=np.linalg.norm(n);ia=extremum(p,a,n);ib=extremum(p,b,n);gap=ia[0][0]-ib[1][0];assert gap>0,(a[0],b[0],gap)
  rows.append(dict(pair=[a[0],b[0]],plane_unit_normal=n,min_projection_A_mm=ia[0][0],max_projection_B_mm=ib[1][0],separating_plane_offset_mm=(ia[0][0]+ib[1][0])/2,gap_lower_bound_mm=gap,witness_A_angle_deg=math.degrees(ia[0][2]),witness_B_angle_deg=math.degrees(ib[1][2]),witness_vertices=[ia[0][1],ib[1][1]]))
 return dict(method='CAD subset of original polygon convex prism; exact extrema of A*cos(q)+B*sin(q)+C over each independent bounded angle; fixed separating plane for each pair',parts_subset_checks=containment,pairs=rows,minimum_nominal_gap_lower_bound_mm=min(r['gap_lower_bound_mm'] for r in rows),scope='28 supplied petal solids including three electronic allocation volumes per petal; no root hinge, motor, linkage, palm, display, cameras, cable, fastener head or real deformation included',tolerance_deflection_margin_qualified=False)

def contact_case(source):
 sphere=cq.Solid.makeSphere(SPHERE_R,cq.Vector(0,0,SPHERE_Z),angleDegrees1=-90,angleDegrees2=90)
 assert abs(sphere.Volume()-4*math.pi*SPHERE_R**3/3)<1e-6
 rows=[];contacts=[]
 for f in FINGERS:
  er,et,ez=axes(f[3]);T=transform(f,math.pi/2);point=SPHERE_R*er+SPHERE_Z*ez;local=np.linalg.solve(T[:3,:3],point-T[:3,3]);assert np.max(abs(local-[SPHERE_Z,0,CONTACT_FACE_Z]))<1e-10
  # A 4 mm radius patch fits in the actual finite contact surface; the sphere
  # is tangent at one point, not over this whole patch. No area is inferred.
  skin=source[f[0]]['compliant_skin'];disk=cq.Solid.makeCylinder(4.,.05,cq.Vector(local[0],local[1],CONTACT_FACE_Z-.05));outside=volume(disk.cut(skin));assert outside<1e-5
  for name,s in source[f[0]].items():
   actual=moved(s,T);v=volume(actual.intersect(sphere));dist=actual.distance(sphere);assert v<1e-4,(f[0],name,v)
   if name=='compliant_skin':assert dist<1e-6
   else:assert dist>.49,(f[0],name,dist)
   rows.append(dict(finger=f[0],part=name,intersection_with_sphere_mm3=v,minimum_nominal_distance_mm=dist))
  contacts.append(dict(finger=f[0],point_head_mm=point,normal_into_object=-er,tangent1=et,tangent2=ez,point_hand_local_mm=local,contained_patch_radius_mm=4.,patch_area_not_an_actual_contact_area=True,patch_outside_skin_mm3=outside))
 # For every angle before 90deg, the whole sphere is on the +normal side of
 # the uncompressed face plane. The minimum analytic separation is at an end.
 plane=[]
 for q in [0.,math.pi/2,math.atan2(R,SPHERE_Z)]:
  plane.append(dict(q_deg=math.degrees(q),plane_to_sphere_surface_mm=R*math.sin(q)+SPHERE_Z*math.cos(q)-(CONTACT_FACE_Z-H)-SPHERE_R))
 assert min(r['plane_to_sphere_surface_mm'] for r in plane)>-1e-10
 return sphere,dict(object='Uncompressed nominal sphere Ø112 mm, center [0,0,65] mm; a geometry test object, not a promised grasp envelope',finger_angles_deg={f[0]:90. for f in FINGERS},contacts=contacts,part_checks=rows,precontact_plane_extrema=plane,first_skin_contact_on_approach_proved_for_independent_monotone_q_0_to_90=True,physical_contact_patch_and_compression_unknown=True)

def grasp_lp(contact):
 # Inner polyhedral friction cone. Feasibility is a sufficient point-contact
 # force model for assumed mu but does not establish the one-actuator forces.
 rows=[];k=16
 for mu in [.2,.4,.8]:
  A=[];owners=[]
  for i,c in enumerate(contact['contacts']):
   n,t1,t2=(np.array(c[a]) for a in ['normal_into_object','tangent1','tangent2']);r=(np.array(c['point_head_mm'])-[0,0,SPHERE_Z])/1000
   for j in range(k):
    a=2*math.pi*j/k;F=n+mu*(math.cos(a)*t1+math.sin(a)*t2);A.append(np.r_[F,np.cross(r,F)]);owners.append(i)
  A=np.array(A).T;N=np.array([[float(i==o) for o in owners] for i in range(4)]);cost=np.r_[np.zeros(4*k),1.];ub=np.c_[N,-np.ones(4)];eq=np.c_[A,np.zeros(6)];rank=int(np.linalg.matrix_rank(A));assert rank==6
  for direction in np.vstack((np.eye(3),-np.eye(3))):
   for mult in [1.,2.]:
    desired=np.r_[-direction*(2.*9.80665*mult),np.zeros(3)]
    # Require 5N at all four contacts in this explicit comparison; this is an
    # illustrative preload constraint, not a selected branch spring preload.
    aub=np.vstack((ub,np.c_[-N,np.zeros(4)]));bub=np.r_[np.zeros(4),-5.*np.ones(4)]
    sol=linprog(cost,A_ub=aub,b_ub=bub,A_eq=eq,b_eq=desired,bounds=[(0,None)]*(4*k+1),method='highs');assert sol.success,sol.message
    normal=N@sol.x[:-1];res=float(np.max(abs(eq@sol.x-desired)));assert res<1e-8
    rows.append(dict(assumed_mu=mu,gravity_direction_head=direction.tolist(),net_object_mass_kg=2.,load_multiplier=mult,assumed_min_per_contact_normal_N=5.,minimum_common_normal_cap_N=float(sol.x[-1]),per_finger_normal_N=normal.tolist(),wrench_residual=res,grasp_matrix_rank=rank,actuator_allocation_verified=False))
 return dict(friction_cone='16 generators inscribed in circular Coulomb cone per contact, point forces only; no soft-contact torsion',objective='Minimize shared per-contact normal upper bound while every contact >=5 N; assumptions for feasibility comparison only',rows=rows,does_not_prove='Measured friction, real contact patch/pressure, compliance allocation, actuator demand, surface temperature, object damage, holding or 2kg hardware rating')

def plot(states,source,certificate,contact):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9})
 fig,axs=plt.subplots(2,3,figsize=(15,9));fig.subplots_adjust(left=.06,right=.98,top=.86,bottom=.14,hspace=.3,wspace=.16)
 for col,(label,qs) in enumerate(states.items()):
  for row,view in enumerate([(0,1),(0,2)]):
   ax=axs[row,col]
   for f in FINGERS:
    for name in ['frame','retainer','compliant_skin']:
     shape=moved(source[f[0]][name],transform(f,qs[f[0]]));v,t=shape.tessellate(.15,.1);tri=np.array([x.toTuple() for x in v])[np.array(t)][:,:,view];ax.add_collection(PolyCollection(tri,facecolors=COLORS[name],edgecolors='none',alpha=.9,rasterized=True))
   if label=='common_contact_90deg':
    center=[0,0] if row==0 else [0,SPHERE_Z];ax.add_patch(plt.Circle(center,SPHERE_R,fill=False,color='#ad4451',lw=1.4,ls='--'))
   ax.autoscale_view();ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlabel('X [mm]');ax.set_ylabel(('Y' if row==0 else 'Z')+' [mm]');ax.set_title(label.replace('_',' ')+' / '+('front' if row==0 else 'side'))
 fig.suptitle('R5 / same shaped petals: open, common face contact, empty closure',x=.06,ha='left',fontsize=18,y=.97)
 fig.text(.06,.91,'Petal geometry only | R62 hinges | upper 0–105°, lower 0–113° | linkage, root supports and central head excluded',fontsize=11)
 fig.text(.06,.065,f'Six fixed separating planes: nominal continuous petal-to-petal gap lower bound {certificate["minimum_nominal_gap_lower_bound_mm"]:.3f} mm.\nØ112 sphere at Z65 touches four finite luminous faces at 90°; this is one uncompressed geometry case, not a 2 kg grip qualification.',fontsize=10)
 fig.savefig(OUT/'three-states.png',dpi=180);fig.savefig(OUT/'three-states.pdf');plt.close(fig)

def main():
 OUT.mkdir(parents=True,exist_ok=True);p=json.loads((SRC/'parameters.json').read_text());qa=json.loads((SRC/'qa.json').read_text());source={};hashes={str(x.relative_to(ROOT)):sha(x) for x in [SRC/'parameters.json',SRC/'study.json',SRC/'qa.json',Path(__file__)]}
 for f in FINGERS:
  source[f[0]]={}
  fam=next(x for x in qa['export_checks']['per_family'] if x['kind']==f[1] and x['hand']==f[2])
  for row in fam['parts']:
   path=SRC/row['file'];assert sha(path)==row['sha256'];shape=cq.importers.importStep(str(path)).val();assert shape.isValid();source[f[0]][row['id']]=shape;hashes[str(path.relative_to(ROOT))]=sha(path)
 cert=continuous_certificate(p,source);sphere,contact=contact_case(source);lp=grasp_lp(contact)
 states={'open':{f[0]:0. for f in FINGERS},'common_contact_90deg':{f[0]:math.pi/2 for f in FINGERS},'empty_closed':{f[0]:math.radians(f[4]) for f in FINGERS}}
 exports=[]
 for label,qs in states.items():
  ass=cq.Assembly(name=REV+'-'+label)
  for f in FINGERS:
   for name,s in source[f[0]].items():ass.add(moved(s,transform(f,qs[f[0]])),name=f[0]+'_'+name,color=cq.Color(COLORS[name]))
  path=OUT/(REV+'-'+label+'.step');ass.save(str(path));back=named_step(path);assert len(back)==28
  exports.append(dict(state=label,file=path.name,sha256=sha(path),named_solids=len(back),angles_deg={n:math.degrees(q) for n,q in qs.items()},sphere_included=False))
 cq.exporters.export(sphere,str(OUT/'reference-sphere-D112.step'))
 dump('continuous-separation.json',cert);dump('finite-face-contact.json',contact);dump('conditional-grasp.json',lp);plot(states,source,cert,contact)
 dump('study.json',dict(revision=REV,license='CC-BY-NC-4.0',required_notice='Odradek — Auromix contributors (https://github.com/Auromix/odradek)',source_hashes=hashes,root_radius_mm=R,root_local_pivot_mm=[0,0,H],fingers=[dict(id=f[0],family=f[1],hand=f[2],azimuth_deg=f[3],q_max_deg=f[4]) for f in FINGERS],transform='T columns [cos(q)er+sin(q)ez, et, -sin(q)er+cos(q)ez], translation R*er-Trot*[0,0,3.5]; left parts already mirrored',minimum_nominal_continuous_gap_mm=cert['minimum_nominal_gap_lower_bound_mm'],states=exports,contact_case='Four finite luminous faces at 90deg against Ø112 sphere with center Z65',manufacturing_release=False,full_head_collision_qualified=False,one_motor_contact_force_allocation_qualified=False,artifact_hashes={f.name:sha(f) for f in sorted(OUT.iterdir()) if f.is_file() and f.name!='study.json'}))
 print(json.dumps({'revision':REV,'pair_gap_mm':[r['gap_lower_bound_mm'] for r in cert['pairs']],'contact_checks':len(contact['part_checks']),'conditional_grasp_scenarios':len(lp['rows'])}))
if __name__=='__main__':main()
