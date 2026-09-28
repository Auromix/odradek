#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent guarded root-stop packaging candidate; CARRIER01 stays frozen.
No impact load, hardening, preload, manufacturing or1-second qualification.
"""
from pathlib import Path
import argparse,gzip,itertools,json,math
import cadquery as cq
import numpy as np
from scipy.special import betainc
from scipy.optimize import brentq
from shapely.geometry import LineString,Point,Polygon
from r5_carrier01 import ROOT,NOTICE,box,cyl,union,xzpoly,pose,azimuth,petal,bbox,common,vol,sha,serial,qR,FINGERS
from head_mass04_study import geometry_properties,tensor_check
from build_link56_study import face_contact

OUT=ROOT/'engineering/generated/r5-limit01'
OLD=ROOT/'engineering/generated/r5-carrier01'
REV='R5-LIMIT01'
SOURCE_SHA='3cb68e55e219802ef4042bf5869b9ec050e0b0417dea3fa3054bdd0e7e028723'
P=dict(min_guard_angle_deg=.5,max_guard_angle_deg=89.5,
       nominal_upper_backing_shim_mm=1.,nominal_lower_backing_shim_mm=1.,
       adjustment_slot_half_travel_mm=.15,plate_y_mm=[-26.,-23.5],
       density_steel_kg_m3=7850.,stop_load_moment_cases_Nm=[.5,1.,2.],
       external_load_cases_are_sensitivities_not_impact_predictions=True)
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,default=serial)+'\n')
def frozen():
 assert sha(ROOT/'engineering/r5_carrier01.py')==SOURCE_SHA
 m=json.loads((OLD/'parts-manifest.json').read_text());rows=[]
 for r in m['parts']:
  f=OLD/r['source_step'];assert sha(f)==r['sha256'];rows.append(r|{'shape':cq.importers.importStep(str(f)).val(),'origin':'CARRIER01 frozen'})
 return rows,m
def slotY(x,z,dx=0,dz=0):
 a=np.array([x-dx,z-dz]);b=np.array([x+dx,z+dz]);p=LineString([a,b]).buffer(1.6,resolution=24)
 return xzpoly(p,-27,-22)
def screwY(x,z,L,shoulder_y=-26,d=3,headD=5.5,headH=3):
 return union([cyl(d/2,shoulder_y,shoulder_y+L,x=x,z=z),cyl(headD/2,shoulder_y-headH,shoulder_y,x=x,z=z)])

def build():
 rows,manifest=frozen();removed=[r for r in rows if r['id'] in ['cap_M3x6_negative_0','cap_M3x6_negative_10']]
 assert len(removed)==2;rows=[r for r in rows if r not in removed];added=[]
 def add(n,s,kind,note=''):
  assert s.isValid() and len(s.Solids())==1,(n,len(s.Solids()))
  g=geometry_properties(s);m=g['volume_mm3']*7850e-9
  r=dict(id=n,shape=s,group='carrier',origin=REV,representation=kind,note=note,mass_kg=m,density_kg_m3=7850.,COM_part_m=g['com_m'],inertia_COM_part_axes_kg_m2=m*g['inertia_per_mass_m2'],mass_is_nominal_solid_proxy=True)
  rows.append(r);added.append(r)
 # Outside the -Y cap, no through shaft or changes to the old steel cradle.
 frame=union([box(-4,28,-26,-23.5,-18,-10),box(12,28,-26,-23.5,-18,17.5),
  box(-8,28,-26,-23.5,11.5,14.5),box(-8,8,-26,-23.5,7,19),box(17,27,-26,-23.5,-16,-6),
  box(-8,-3,-31,-21,10.5,16),box(19,25,-31,-21,-21,-16),
  box(-3,7,-23.5,-20.5,8,8.9),box(-3,7,-23.5,-20.5,17.1,18),
  box(16.9,17.9,-23.5,-20.5,-16,-6),box(26.1,27.1,-23.5,-20.5,-16,-6)])
 for x in [0,10]:frame=frame.cut(cyl(1.6,-27,-23,x=x,z=-14))
 frame=frame.cut(slotY(4,13,dx=.15)).cut(slotY(22,-9,dz=.15))
 # Captured shim tabs cross the backing plate through explicit service slots.
 frame=frame.cut(box(-3.1,-1.8,-26.1,-23.4,10,16)).cut(box(19,25,-26.1,-23.4,-16.1,-14.9))
 frame=frame.cut(cyl(.8,-7.1,-2.9,axis='x',y=-28.5,z=13)).cut(cyl(.8,-20.1,-15.9,axis='z',x=22,y=-28.5))
 add('external_negative_side_stop_arch',frame,'original steel','2.5mm outer plate with integral bosses/rails. Machining or fabricated process and actual material/heat treatment are not selected.')
 # Broad contact faces are machined to the guarded target angles, not left
 # square and then assigned a fictitious full-area contact at another angle.
 qlo=math.radians(P['min_guard_angle_deg']);qhi=math.radians(P['max_guard_angle_deg'])
 xf=lambda z:(3.5+z*math.cos(qhi))/math.sin(qhi)
 zf=lambda x:(-7.5+x*math.sin(qlo))/math.cos(qlo)
 upper=union([box(-2,7.5,-23.5,-20.5,9,17),xzpoly(Polygon([[-2,11.5],[xf(11.5),11.5],[xf(14.5),14.5],[-2,14.5]]),-23.5,-9.5)])
 upper=upper.cut(cyl(1.25,-24,-20,x=4,z=13))
 lower=union([box(18,26,-23.5,-19.5,-15,-5.5),xzpoly(Polygon([[20,-12],[23,-12],[23,zf(23)],[20,zf(20)]]),-23.5,-9.5)])
 lower=lower.cut(cyl(1.25,-24,-19,x=22,z=-9))
 add('upper_guard_contact_bridge',upper,'original steel','Target89.5deg matched contact face. Backing shim carries -X stop force; clamp/guide rails retain the block. No assumption that clamp friction alone carries stopping load.')
 add('lower_guard_contact_bridge',lower,'original steel','Target0.5deg matched contact face. Backing shim carries -Z stop force. Shim changes require angle/contact remeasurement.')
 us=box(-3,-2,-31,-19.5,10.5,16).cut(cyl(1.1,-4,-1,axis='x',y=-28.5,z=13))
 ls=box(19,25,-31,-19.5,-16,-15).cut(cyl(1.1,-17,-14,axis='z',x=22,y=-28.5))
 add('upper_retained_backing_shim',us,'original steel','Nominal1mm; .95/1/1.05 alternatives for metrology-only adjustment. No certified shim material, tolerance or final stack chosen.')
 add('lower_retained_backing_shim',ls,'original steel','Nominal1mm; .95/1/1.05 alternatives. Retention tab is explicit; do not use a loose unretained foil.')
 for x in [0,10]:
  s=cyl(3,-23.5,-20,x=x,z=-14).cut(cyl(1.6,-24,-19.5,x=x,z=-14))
  add(f'cap_mount_spacer_{x}',s,'original steel','OD6/ID3.2x3.5, nominal bearing area20.23mm2. Not a selected purchased spacer.')
  add(f'cap_mount_M3x12_{x}',screwY(x,-14,12),'standard fastener envelope','Replaces oldM3x6; same tipY-14 and5mm nominal aluminium thread engagement. ExactPN/grade/torque TBD; not an upgrade of thread strength.')
 for x,z,tag in [(4,13,'upper'),(22,-9,'lower')]:add(tag+'_clamp_M3x6',screwY(x,z,6),'standard fastener envelope','Major-cylinder threads intersect pilot holes intentionally.Upper3.0/lower3.5mm nominal steel engagement, locking/preload TBD.')
 uscrew=union([cyl(1,-7,-2,axis='x',y=-28.5,z=13),cyl(1.9,-2,0,axis='x',y=-28.5,z=13)])
 lscrew=union([cyl(1,-20,-15,axis='z',x=22,y=-28.5),cyl(1.9,-15,-13,axis='z',x=22,y=-28.5)])
 add('upper_shim_retainer_M2x5',uscrew,'standard fastener envelope','Nominal ISO4762 envelope only; exactPN/locking not selected. Not in main stop compression path.')
 add('lower_shim_retainer_M2x5',lscrew,'standard fastener envelope','Nominal ISO4762 envelope only; exactPN/locking not selected.')
 return rows,added,removed

def pose_rows(rows,R,q,phi=0):
 return {r['id']:(azimuth(r['shape'],phi) if r['group']=='guide' else pose(r['shape'],R,q if r['group']=='rotor' else 0,phi)) for r in rows}
def broad(a,b):
 A,B=bbox(a),bbox(b);return np.all(A[0]<=B[1]+1e-7) and np.all(B[0]<=A[1]+1e-7)
def q_band():
 R=np.linspace(31,91,6001);q=np.pi/2*betainc(3,3,np.clip((91-R)/25,0,1))
 line=LineString(np.c_[R+8*np.cos(q-np.pi/4),20+8*np.sin(q-np.pi/4)])
 def distance(r,a):
  t=math.radians(a-45);return line.distance(Point(r+8*math.cos(t),20+8*math.sin(t)))
 cases=[]
 for r in np.linspace(31,91,1201):
  a=qR(r);lo=brentq(lambda x:distance(r,x)-.15,a-5,a);hi=brentq(lambda x:distance(r,x)-.15,a,a+5)
  guarded=float(np.clip(a,.5,89.5));cases.append(dict(R_mm=float(r),nominal_q_deg=a,lower_local_branch_q_deg=lo,upper_local_branch_q_deg=hi,guarded_q_deg=guarded,guarded_centerline_distance_mm=distance(r,guarded)))
 return dict(scope='Numerical near-nominal branch of ideal centreline tube radius0.15. Not all periodic branches, not physical tolerances, not continuous max proof.',R_samples=1201,centerline_R_step_mm=.01,minimum_q_case=min(cases,key=lambda x:x['lower_local_branch_q_deg']),maximum_q_case=max(cases,key=lambda x:x['upper_local_branch_q_deg']),guarded_max_offset_case=max(cases,key=lambda x:x['guarded_centerline_distance_mm']),cases=cases)

def own_check(rows,added):
 source={r['id']:r for r in rows};newids={r['id'] for r in added};records=[]
 # Catalogue thread cylinders are not counted as unintended penetration.
 threads={frozenset(['cap_mount_M3x12_'+str(x),'bearing_pedestal_negative']) for x in [0,10]}
 threads|={frozenset(['upper_clamp_M3x6','upper_guard_contact_bridge']),frozenset(['lower_clamp_M3x6','lower_guard_contact_bridge']),frozenset(['upper_shim_retainer_M2x5','external_negative_side_stop_arch']),frozenset(['lower_shim_retainer_M2x5','external_negative_side_stop_arch'])}
 for q in [.5,5,15,30,45,60,75,85,89.5]:
  shapes=pose_rows(rows,31,q);shapes|={'FORM02_'+n:pose(s,31,q) for n,s in petal('upper','right').items()}
  violations=[];intended=[]
  for a,b in itertools.combinations(shapes,2):
   if a not in newids and b not in newids:continue
   if not broad(shapes[a],shapes[b]):continue
   v=common(shapes[a],shapes[b])
   if v>1e-5:
    r=dict(pair=[a,b],overlap_mm3=v)
    (intended if frozenset([a,b]) in threads else violations).append(r)
  records.append(dict(q_deg=q,violations=violations,intentional_thread_intersections=intended));print('own',q,len(violations),flush=True)
 return records

def contact_check(rows):
 d={r['id']:r['shape'] for r in rows};records=[]
 for tag,q,x,z in [('lower',.5,21.5,(-7.5+21.5*math.sin(math.radians(.5)))/math.cos(math.radians(.5))),('upper',89.5,(3.5+13*math.cos(math.radians(89.5)))/math.sin(math.radians(89.5)),13)]:
  t=math.radians(q);a=pose(d['rotor_split_trunnion_cradle'],31,q);b=pose(d[tag+'_guard_contact_bridge'],31,0)
  records.append(dict(stop=tag,target_angle_deg=q,contact=face_contact(a,b,[31+x,-10.65,20+z],[-math.sin(t),0,math.cos(t)]),nominal_intersection_mm3=common(a,b)))
  for delta in [-.25,.25]:records[-1][f'intersection_q_{q+delta:g}_mm3']=common(pose(d['rotor_split_trunnion_cradle'],31,q+delta),b)
 return records

def cross_samples(rows,added):
 newids={r['id'] for r in added};states=[(31,89.5),(66,89.5),(78.5,45),(91,.5)]
 modules={}
 for f,(kind,hand,phi) in FINGERS.items():
  for R,q in states:
   d=pose_rows(rows,R,q,phi)|{'FORM02_'+n:pose(s,R,q,phi) for n,s in petal(kind,hand).items()}
   modules[f,R,q]={n:(s,bbox(s)) for n,s in d.items()}
 result=[]
 for a,b in itertools.combinations(FINGERS,2):
  for (Ra,qa),(Rb,qb) in itertools.product(states,repeat=2):
   todo=[]
   for na,(sa,ba) in modules[a,Ra,qa].items():
    for nb,(sb,bb) in modules[b,Rb,qb].items():
     if na not in newids and nb not in newids:continue
     delta=np.maximum(np.maximum(ba[0]-bb[1],bb[0]-ba[1]),0);todo.append((float(np.linalg.norm(delta)),na,nb,sa,sb))
   todo.sort(key=lambda r:r[0]);dmin=float('inf');winner=None;viol=[]
   for lower,na,nb,sa,sb in todo:
    if lower>dmin+1e-7:break
    d=float(sa.distance(sb))
    if d<dmin:dmin=d;winner=[na,nb]
    if d<1e-7:
     v=common(sa,sb)
     if v>1e-5:viol.append(dict(parts=[na,nb],overlap_mm3=v))
   result.append(dict(fingers=[a,b],R_mm=[Ra,Rb],q_deg=[qa,qb],minimum_new_interface_distance_mm=dmin,nearest_parts=winner,violations=viol))
  print('cross',a,b,flush=True)
 return dict(scope='96 independent endpoint/midfold combinations, pairs involving a new LIMIT01 part only; not a continuous whole-module motion/tolerance certificate.',samples=result)

def load_screen(rows):
 # Unit-moment static screens are deliberately not inferred impact forces.
 d={r['id']:r['shape'] for r in rows};data=[]
 E=200000. # N/mm2, assumed isotropic modulus, no material allowable
 for tag,q in [('lower',.5),('upper',89.5)]:
  t=math.radians(q)
  if tag=='lower':x=21.5;z=(-7.5+x*math.sin(t))/math.cos(t);n=np.array([-math.sin(t),0,math.cos(t)])
  else:z=13.;x=(3.5+z*math.cos(t))/math.sin(t);n=np.array([-math.sin(t),0,math.cos(t)])
  # Normal acts on rotor: +n for lower, -n for upper.
  lever=abs(x*n[2]-z*n[0]);area=6.9/(math.cos(t) if tag=='lower' else math.sin(t))
  cases=[]
  for T in P['stop_load_moment_cases_Nm']:
   F=T*1000/lever;Fv=(-n if tag=='lower' else n)*F # rotor-on-stop
   r=np.array([x,-10.65,z]);boltcentre=np.array([5,-20,-14]);M=np.cross(r-boltcentre,Fv)
   # Existing two cap bolts have10mm separation inX. Equal direct shear
   # plus in-planeY moment; moments causing peel require face/preload model.
   bolts=[]
   for xb in [0,10]:
    ri=np.array([xb-5,0,0]);f=Fv/2+np.cross(np.array([0,M[1],0]),ri)/50
    bolts.append(dict(x_mm=xb,in_plane_shear_N=f[[0,2]],norm_N=float(np.linalg.norm(f[[0,2]]))))
   cases.append(dict(assumed_stop_moment_Nm=T,normal_contact_force_N=F,nominal_full_face_pressure_MPa=F/area,external_wrench_about_original_mount_centre_Nmm=M,bolt_equal_share_plus_in_plane_moment=bolts,unresolved_peeling_moment_XZ_Nmm=M[[0,2]]))
  # Actual bridge section lies atY-18; includes the machined face and holes.
  s=d[tag+'_guard_contact_bridge'].intersect(box(-100,100,-18.01,-17.99,-100,100));g=geometry_properties(s);A=g['volume_mm3']/.02
  I=g['inertia_per_mass_m2']*g['volume_mm3']*1e6/.02;I[0,0]-=A*.02**2/12;I[2,2]-=A*.02**2/12
  #14mm pure cantilever isolates the cross-tangent bridge. Joint/root-frame
  # compliance omitted; report component compliance, never total-stop angle.
  Funit=1000/lever;L=14.;axis=0 if tag=='lower' else 2;J=I[axis,axis]
  b=bbox(s);c=g['com_m']*1000;fiber=max(abs(b[:,2 if axis==0 else 0]-c[2 if axis==0 else 0]));sectionmod=J/fiber
  data.append(dict(stop=tag,contact_lever_mm=lever,nominal_contact_area_mm2=area,cases=cases,bridge_net_section_area_mm2=A,bridge_I_mm4=J,bridge_section_modulus_mm3=sectionmod,bridge_14mm_cantilever_component_stress_per_Nm_MPa=Funit*L/sectionmod,bridge_component_tip_deflection_per_Nm_mm=Funit*L**3/(3*E*J),assumed_E_N_mm2=E,scope='Nominal static sensitivities only. Full-frame torsion, hole/contact peaks, bolt preload/peeling, impact, wear and material allowable omitted. No safety factor or payload rating.'))
 return data

def export(rows,added,removed):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'parts').mkdir(exist_ok=True);ledger=[]
 for r in added:
  s=r['shape'];f=OUT/'parts'/(r['id']+'.step');cq.exporters.export(s,str(f));back=cq.importers.importStep(str(f)).val();assert back.isValid() and abs(vol(s)-vol(back))<1e-4
  ledger.append({k:v for k,v in r.items() if k!='shape'}|dict(source_step=str(f.relative_to(OUT)),sha256=sha(f),volume_mm3=vol(s),bbox_part_mm=bbox(s)))
 for label,R,q in [('upper_guard',31,89.5),('lower_guard',91,.5)]:
  a=cq.Assembly(name=REV+'-'+label);posed=pose_rows(rows,R,q)
  for r in rows:a.add(posed[r['id']],name=r['id'],color=cq.Color('#b47846' if r['origin']==REV else '#7a909b'))
  for n,s in petal('upper','right').items():a.add(pose(s,R,q),name='FORM02_'+n,color=cq.Color('#c7a762' if n=='compliant_skin' else '#456c78'))
  p=OUT/(label+'.step');a.save(str(p))
 dump(OUT/'parts-manifest.json',dict(revision=REV,coordinates='Root hinge zero-angle coordinates,mm; newparts are fixed to translating carrier, no q rotation.',parts=ledger,replaced_old_ids=[r['id'] for r in removed],new_nominal_steel_and_hardware_kg=sum(r['mass_kg'] for r in added),removed_old_proxy_kg=sum(r['mass_kg'] for r in removed),increment_per_branch_kg=sum(r['mass_kg'] for r in added)-sum(r['mass_kg'] for r in removed),whole_head_mass_kg=None))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build-only',action='store_true');ap.add_argument('--check-only',action='store_true');a=ap.parse_args()
 rows,added,removed=build();OUT.mkdir(parents=True,exist_ok=True)
 if not a.check_only:export(rows,added,removed)
 dump(OUT/'contact-checks.json',contact_check(rows))
 if not a.build_only:
  dump(OUT/'slot-angle-band.json',q_band());dump(OUT/'own-branch-checks.json',own_check(rows,added));dump(OUT/'cross-branch-samples.json',cross_samples(rows,added))
 dump(OUT/'unit-moment-load-screen.json',load_screen(rows))
 dump(OUT/'parameters.json',P)
 dump(OUT/'source-hashes.json',{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'engineering/r5_carrier01.py',OLD/'parts-manifest.json',OLD/'continuous-certificate.json',ROOT/'engineering/generated/r5-petal-form02/study.json',ROOT/'engineering/generated/r5-stage01/study.json']})
 print('DONE',flush=True)
if __name__=='__main__':main()
