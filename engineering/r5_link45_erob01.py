# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-LINK45-EROB01 original short elbow. mm; local axes match world, O=J4.
Vendor CAD remains private; nominal exterior proofs are not a production release.
"""
from pathlib import Path
import argparse,csv,hashlib,inspect,itertools,json,math
import numpy as np
import cadquery as cq
import trimesh,ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder,GeomAbs_Plane
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from build_layout import frame,moved
from r5_link56_erob01 import cap,ann,cone,polar,bb,volume,inter,X80,X70,A80,REL80,curves,yzcs,rotY,group
from draw_central_display01 import section,dxf_geometry,Sheet,BLUE,GREY
from r5_wrist_erob01 import OEM_ANGLES,HEAD_ANGLES
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/r5-link45-erob01';SRC=ROOT/'docs/engineering/sources/r5-link45-erob01.json'
L56=ROOT/'engineering/generated/r5-link56-erob01';PAIR=ROOT/'engineering/generated/r5-wrist-pair01'
ORIGIN=np.array([0.,0.,435.]);J5=np.array([0.,-55.,50.]);J6=np.array([0.,0.,205.]);J7=np.array([0.,55.,240.]);T4=frame([0,0,0],[0,-1,0]);T5=frame(J5,[0,0,1]);FIX=list(range(15,360,30));RHO=2.7e-6
Q=np.eye(4);t=math.radians(15);Q[:3,:3]=[[math.cos(t),-math.sin(t),0],[math.sin(t),math.cos(t),0],[0,0,1]];T6=frame(J6,[0,1,0])@Q;T7=frame(J7,[0,0,1])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def properties(s):
 p=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,p);I=np.array([[p.MatrixOfInertia().Value(i,j) for j in range(1,4)] for i in range(1,4)])*RHO*1e-6
 return dict(volume_mm3=volume(s),mass_if_6061_kg=volume(s)*RHO,com_link_mm=list(s.Center().toTuple()),com_world_mm=(np.array(s.Center().toTuple())+ORIGIN).tolist(),inertia_at_com_world_kg_m2=I.tolist(),preceding_joints=4,density_assumption_kg_m3=2700)
def build(gauge=False):
 bore=30.2 if gauge else 30.;hole=1.9 if gauge else 1.7;ri=33.7 if gauge else 33.5
 a=ann(33,bore,-8,0).fuse(cap(38,0,10));es=[e for e in a.Edges() if abs(e.Length()-2*math.pi*bore)<1e-5 and abs(e.Center().z)<1e-5];assert len(es)==1;a=a.fillet(.1,es)
 a=a.cut(cone(bore+.3,bore,-8,.3)).cut(cap(9.2 if gauge else 9,-9,11)).cut(cap(24.6 if gauge else 24.5,-.01,.5 if gauge else .3))
 for xy in polar(27,A80):a=a.cut(cap(hole,-.01,10.01,xy)).cut(cap(3.1,6.6,10.01,xy)).cut(cone(hole,hole+.2,6.4,.2,xy))
 for xy in polar(27,REL80):a=a.cut(cap(2.65,-.01,.5,xy))
 a=moved(a,T4).fuse(cq.Solid.makeBox(28,6,15,cq.Vector(-14,-10,30.5))).fuse(cq.Solid.makeBox(28,20,7,cq.Vector(-14,-24,38.5)))
 a=a.fuse(moved(ann(43,ri,-11.5,-4.5),T5)).cut(moved(cap(ri,-11.51,-4.49),T5))
 for xy in polar(37,FIX):a=a.cut(moved(cap(hole,-11.51,-4.49,xy).fuse(cone(hole,hole+.2,-4.7,.2,xy)),T5))
 a=a.clean();es=[e for e in a.Edges() if e.geomType()=='LINE' and math.dist(e.Center().toTuple(),(0,-10,38.5))<1e-5];assert len(es)==1
 return a.fillet(2,es).clean()
def export(n,s):
 assert s.isValid() and len(s.Solids())==1
 p=OUT/'STEP'/(n+'.step');f=OUT/'STL'/(n+'.stl');cq.exporters.export(s,str(p));cq.exporters.export(s,str(f),tolerance=.01,angularTolerance=.05)
 r=cq.importers.importStep(str(p)).val();m=trimesh.load(f,force='mesh',process=True)
 q=dict(**properties(s),bbox_mm=bb(s),step_sha256=sha(p),stl_sha256=sha(f),step_valid=r.isValid(),step_solids=len(r.Solids()),step_volume_relative_error=abs(volume(r)-volume(s))/volume(s),mesh_watertight=bool(m.is_watertight),mesh_winding_consistent=bool(m.is_winding_consistent),mesh_volume_relative_error=abs(m.volume-volume(s))/volume(s),mesh_bbox_max_error_mm=float(np.abs(m.bounds-np.array(bb(s))).max()),chordal_tolerance_mm=.01,angular_tolerance_rad=.05)
 assert q['step_valid'] and q['step_solids']==1 and q['step_volume_relative_error']<1e-8 and q['mesh_watertight'] and q['mesh_winding_consistent'] and q['mesh_volume_relative_error']<.001 and q['mesh_bbox_max_error_mm']<.02
 return q

def vendor_fixed_extraction(v):
 rows=[];planes=[]
 for si,s in enumerate(v.Solids()):
  for fi,f in enumerate(s.Faces()):
   a=BRepAdaptor_Surface(f.wrapped);b=bb(f)
   if a.GetType()==GeomAbs_Cylinder:
    c=a.Cylinder();p=c.Location();d=c.Axis().Direction();r=math.hypot(p.X(),p.Y())
    if abs(d.Z())>.999999 and (abs(r-37)<1e-5 or r<1e-5):rows.append(dict(solid=si,face=fi,radius_mm=c.Radius(),xy_mm=[p.X(),p.Y()],axis_radius_mm=r,angle_deg=round(math.degrees(math.atan2(p.Y(),p.X()))%360,6)%360,z_interval_mm=[b[0][2],b[1][2]]))
   elif a.GetType()==GeomAbs_Plane:
    pp=a.Plane();dd=pp.Axis().Direction()
    if abs(dd.Z())>.999999 and abs(pp.Location().Z()+11.5)<1e-5 and f.Area()>50:planes.append(dict(solid=si,face=fi,area_mm2=f.Area(),bbox_mm=b))
 aa=sorted(set(r['angle_deg'] for r in rows if abs(r['axis_radius_mm']-37)<1e-5 and abs(r['radius_mm']-1.65)<1e-5));assert aa==FIX
 assert len(planes)==2
 return dict(native_output_x_mm=X80,proper_transform='X=nativeY,Y=nativeZ,Z=nativeX-32.92358111047752',fixed_face_jointZ_mm=-11.5,fixed_pcd_mm=74,fixed_mount_angles_deg=aa,fixed_material_faces=planes,cylinders=rows,fixed_known_free_segment_policy='Only new7mm carrier thickness; native region belowZ-11.5 is excluded from external free-shaft claim. Modeled thread-like surfaces are not a controlled engagement-start proof.',minimum_full_fixed_engagement_manual_mm=4.0,output_minimum_full_engagement_mm=3.0,thread_spec='M3x0.35 cap12.9 black oxide; finalSKU/full engagement/lengthTBD')

def originals():
 return {'L56':cq.importers.importStep(str(L56/'STEP/L56-E01.step')).val().translate(tuple(J5)),
 'W01':cq.importers.importStep(str(PAIR/'STEP/W01.step')).val().translate(tuple(J6)),
 'A01P':moved(cq.importers.importStep(str(PAIR/'STEP/A01-P.step')).val(),T7),
 'H01':moved(cq.importers.importStep(str(PAIR/'STEP/H01-reuse.step')).val(),T7)}
def R(s,o,axis,q):return s.rotate(tuple(o),tuple(np.array(o)+np.array(axis)),q)
def point_pose(p,q5,q6,q7,pre):
 p=np.array(p,dtype=float)
 if pre>=7:
  t=math.radians(q7);rz=np.array([[math.cos(t),-math.sin(t),0],[math.sin(t),math.cos(t),0],[0,0,1]]);p=J7+rz@(p-J7)
 if pre>=6:p=J6+rotY(q6)@(p-J6)
 if pre>=5:
  t=math.radians(q5);rz=np.array([[math.cos(t),-math.sin(t),0],[math.sin(t),math.cos(t),0],[0,0,1]]);p=J5+rz@(p-J5)
 return p

def checks(L,v80,v70,orig):
 v4=moved(v80,T4);v5=moved(v80,T5);v6=moved(v70,T6);v7=moved(v70,T7)
 vv={**{f'J4_{i}':s for i,s in enumerate(v4.Solids())},**{f'J5_{i}':s for i,s in enumerate(v5.Solids())},'J6':v6,'J7':v7}
 static=[]
 for n,t in {**vv,**orig}.items():
  x=inter(L,t);assert x<1e-5;static.append(dict(against=n,intersection_mm3=x))
 hw={};hrows=[];tools=[];sweeps=[]
 for group0,aa,r,z0,seat,T,obstacles in [('J4_OUT',A80,27,-5,6.6,T4,{'L45':L,**{n:s for n,s in vv.items() if n.startswith('J4')}}),('J5_FIXED',FIX,37,-11.5,-4.5,T5,{'L45':L,**{n:s for n,s in vv.items() if n.startswith(('J4','J5'))}})]:
  for i,xy in enumerate(polar(r,aa)):
   h=moved(cap(1.5,z0,seat,xy).fuse(cap(2.84,seat,seat+3,xy)),T);hn=f'{group0}_{i+1}';hw[hn]=h
   vals={n:inter(h,t) for n,t in {'L45':L,**vv,**orig}.items()};assert max(vals.values())<1e-5;hrows.append(dict(id=hn,head_max_mm=[5.68,3],known_free_length_mm=seat-z0,intersections_mm3=vals,complete_screw=False))
   tool=moved(cap(2.9,seat+.001,seat+60,xy),T);vals={n:inter(tool,t) for n,t in obstacles.items()};assert max(vals.values())<1e-5;tools.append(dict(id=hn,diameter_length_mm=[5.8,60],intersections_mm3=vals,actual_tool_selected=False))
   sweep=moved(cap(1.5,z0,seat+60,xy).fuse(cap(2.84,seat,seat+63,xy)),T);vals={n:inter(sweep,t) for n,t in obstacles.items()};assert max(vals.values())<1e-5;sweeps.append(dict(id=hn,travel_mm=[0,60],intersections_mm3=vals,unknown_thread_excluded=True))
 hpair=[]
 for (a,x),(b,y) in itertools.combinations(hw.items(),2):
  vi=inter(x,y);assert vi<1e-5;hpair.append(dict(a=a,b=b,intersection_mm3=vi))
 ordered=[]
 for i,xy in enumerate(polar(37,FIX)):
  sw=moved(cap(1.5,-11.5,55.5,xy).fuse(cap(2.84,-4.5,58.5,xy)),T5);vals={n:inter(sw,h) for n,h in hw.items() if n.startswith('J4_OUT')};assert max(vals.values())<1e-5;ordered.append(vals)
 print('Static+hardware passed',flush=True)
 # Verify actual OEM material fits the stated invariant exterior bounds, all5solids.
 bound80=cap(40.1,-67.6,-11.5).fuse(cap(30.1,-11.5,.001));escapes=[volume(s.cut(bound80)) for s in v80.Solids()];assert max(escapes)<1e-5
 carrier_local=moved(L,np.linalg.inv(T4));negative=carrier_local.intersect(cq.Solid.makeBox(250,250,10,cq.Vector(-125,-125,-10)));skirt=ann(33,30,-8,0).fuse(ann(33,29.9,-.1,0));esc=volume(negative.cut(skirt));assert esc<1e-5
 skirtv=[inter(skirt,s) for s in v80.Solids()];assert max(skirtv)<1e-5
 ins4=ann(33,30,-8,80).fuse(ann(33,29.9,-.1,80));ins4v=[inter(ins4,s) for s in v80.Solids()];assert max(ins4v)<1e-5
 ins5=moved(cap(40.1,-167.6,-11.5).fuse(cap(30.1,-111.5,.001)),T5);is5=inter(ins5,L);assert is5<1e-5
 # q5: L56 main material Z>=50, only rear sleeve enters carrier's Z<=45.5.
 sleeve5=moved(ann(33,30,-8,0).fuse(ann(33,29.9,-.1,0)),T5);vs=inter(sleeve5,L);assert vs<1e-5
 boltring5=moved(ann(28.5,25.5,-5,4.6).fuse(ann(29.84,24.16,4.6,7.6)),T5);vr=inter(boltring5,L);assert vr<1e-5
 # q4 invariance: allL56 material remains Z>=42 under q5; q4 preserves RaboutY.
 # Wrist+J7 minZ uses frozen verified64.4mm XZ radius, q6/q7 continuum, and source hashes.
 ls=json.loads((L56/'study.json').read_text());wmin=50+ls['checks']['q5_continuous']['continuous_downstream_min_Z_mm'];assert wmin>40.1
 low=orig['L56'].intersect(cq.Solid.makeBox(250,250,158,cq.Vector(-125,-125,-58)));lowbound=moved(cap(38.1,-8,50),T5);lowesc=volume(low.cut(lowbound));assert lowesc<1e-5
 assert bb(orig['L56'])[0][2]>41.999 and bb(v6)[0][2]>169.8
 # Reserve volumes deliberately NOT full mating connectors. Both remain clear at zero pose.
 port4=moved(cap(44,-107.5,-67.5),T4);port5=moved(cap(44,-107.5,-67.5),T5);ports={}
 for n,p in [('J4_rear',port4),('J5_rear',port5)]:
  vals={nn:inter(p,ss) for nn,ss in {'L45':L,**orig,**hw}.items()};assert max(vals.values())<1e-5;ports[n]=vals
 # Actual finite poses across all four inherited local coordinates. Not the continuous proof.
 discrete=[];down=[(n,s,5 if n in ['L56','J6'] else 7 if n in ['A01P','H01'] else 6) for n,s in {**orig,'J6':v6,'J7':v7}.items()]
 for q4,q5,q6,q7 in itertools.product([-120,0,120],[-90,0,90],[-100,100],[-90,90]):
  movedL=R(L,[0,0,0],[0,-1,0],q4)
  for n,s,pre in down:
   obj=s
   if pre>=7:obj=R(obj,J7,[0,0,1],q7)
   if pre>=6:obj=R(obj,J6,[0,1,0],q6)
   obj=R(obj,J5,[0,0,1],q5)
   against_link=inter(obj,L);assert against_link<1e-5
   obj=R(obj,[0,0,0],[0,-1,0],q4);vals={f'J4_{i}':inter(obj,t) for i,t in enumerate(v4.Solids())};assert max(vals.values())<1e-5
   discrete.append(dict(q_deg=[q4,q5,q6,q7],moving=n,L45_intersection_mm3=against_link,J4_solid_intersections_mm3=vals))
 # J5 is before q5: every OEM solid moves with q4 only; check itself and newcarrier.
 direct=[]
 for q4 in [-120,-60,0,60,120]:
  for n,s in {'L45':L,**{f'J5_{i}':s for i,s in enumerate(v5.Solids())}}.items():
   ss=R(s,[0,0,0],[0,-1,0],q4);vals={f'J4_{i}':inter(ss,t) for i,t in enumerate(v4.Solids())};assert max(vals.values())<1e-5;direct.append(dict(q4_deg=q4,moving=n,intersections_mm3=vals))
 ca4=sum(volume(L.intersect(s.translate((0,-.0001,0))))/.0001 for s in v4.Solids());ca5=sum(volume(L.intersect(s.translate((0,0,.0001))))/.0001 for s in v5.Solids());assert min(ca4,ca5)>100
 return dict(static=static,known_hardware=hrows,hardware_pairs=hpair,tool_probes=tools,known_hardware_sweeps=sweeps,J5_insertion_vs_prior_J4_hardware=ordered,discrete_pose_rows=discrete,direct_q4_rows=direct,contact_area_proxy_mm2={'J4_output':ca4,'J5_fixed':ca5},continuous={'q4_deg':[-120,120],'q5_deg':[-90,90],'q6_deg':[-100,100],'q7_deg':[-90,90],'vendor80_bound_escape_per_solid_mm3':escapes,'J4_negative_original_subset_escape_mm3':esc,'J4_rear_skirt_invariant_intersections_mm3':skirtv,'J4_aligned_insertion_0_80mm':ins4v,'J5_aligned_insertion_0_100mm':is5,'J5_insertion_beyond100':'OEM maxZ<=-50, while carrier minZ=-38: separated','J5_sleeve_sweep_intersection_mm3':vs,'J5_known_output_shaft_sweep_intersection_mm3':vr,'L45_max_Z_mm':bb(L)[1][2],'L56_main_min_Z_mm':50,'sleeve_to_fixed_ring_radial_gap_mm':.5,'sleeve_to_fixed_head_radial_gap_mm':1.16,'fixed_head_top_to_L56_main_gap_mm':1.5,'L56_min_radial_distance_to_J4_axis_bound_mm':42,'J4_max_radius_bound_mm':40.1,'minimum_radial_gap_mm':1.9,'wrist_J7_continuous_min_Z_mm':wmin,'L56_low_subset_escape_mm3':lowesc,'L56_low_Z_split_mm':100,'L56_low_invariant_radius_about_J5_mm':38.1,'q4_proof':'Carrier negative-Y halfspace plus its axisymmetric rear skirt. J5 full body Y<=-14.9 independent q4. L56 minZ42 under q5, thus RaboutJ4>=42 preserved by q4; J6 and wrist/J7 are farther using actual/frozen bounds. q5 sleeve/heads clear invariant ring, higher material separated inZ. No OEM rotor/thread internal certification.','port_proof':'J5 reserveY<=-11, clear carrierY>=-10 where rearZoverlaps. J4reserveY>=67.5: lowL56Z<=100 has invariantR38.1 aboutJ5 henceY<=-16.9; highL56Z>=100 and alllater members haveRaboutJ4>44. Full wired plugs not modeled.'},port_reserve={'radius_mm':44,'length_mm':40,'intersections_mm3':ports,'selected_mating_connector_model':False},harness={'straight_J4_J5_each_bore_mm':18,'complete_route_verified':False,'note':'Two orthogonal18mm bores do not prove complete harness. Existing LINK56 R35 underbody route failure remains. No cable bend/torsion, connector insertion or selected port angular contract.'},scope_excludes=['J3/L34 and whole arm','Actual complete head geometry','Unknown OEM female threads and rotor split','Cables, matingplugs, covers, elastic/tolerance effects']),hw,{'J4':v4,'J5':v5,'J6':v6,'J7':v7}

def prior_hardware_checks(L,new_hw):
 hist={};membership={}
 specs=[('L56_J5OUT',A80,27,-5,4.6,1.5,2.84,3,T5,5),('L56_J6FIX',list(range(0,360,45)),32,-26.5,-4,1.5,2.84,3,T6,5),('PAIR_J6OUT',OEM_ANGLES,22,-9,4.6,1.5,2.84,3,T6,6),('PAIR_J7FIX',list(range(0,360,45)),32,-26.5,-4,1.5,2.84,3,T7,6),('PAIR_J7OUT',OEM_ANGLES,22,-9,4.6,1.5,2.84,3,T7,7),('PAIR_HEAD',HEAD_ANGLES,32,-.35,12,2,3.61,4,T7,7)]
 for n,aa,r,z0,seat,sr,hr,hh,T,pre in specs:
  for i,xy in enumerate(polar(r,aa)):
   key=f'{n}_{i+1}';hist[key]=moved(cap(sr,z0,seat,xy).fuse(cap(hr,seat,seat+hh,xy)),T);membership[key]=pre
 # Nominal cylindrical dowel proxies, not a validated vendor end-profile/retention design.
 for i,xy in enumerate([(0,32),(0,-32)]):key=f'PAIR_PIN_PROXY_{i+1}';hist[key]=moved(cap(1.5,4,12,xy),T7);membership[key]=7
 rows=[]
 for n,h in hist.items():
  vals={k:inter(h,t) for k,t in {'L45':L,**new_hw}.items()};assert max(vals.values())<1e-5;pre=membership[n];b=np.array(bb(h))
  if pre==5:assert b[0,2]>=45-1e-5
  elif pre==6:assert max(math.hypot(x,z-205) for x,z in itertools.product([b[0,0],b[1,0]],[b[0,2],b[1,2]]))<64.4
  else:
   hlocal=moved(h,np.linalg.inv(T7));assert volume(hlocal.cut(cap(39.1,-9.1,16.1)))<1e-5
  rows.append(dict(id=n,preceding_joints=pre,intersections_mm3=vals,known_external_geometry_only=True))
 return dict(count=len(hist),rows=rows,continuous_containment='pre5 minZ>=45 preserved byq5; pre6 XZradius<64.4 aboutJ6; pre7 insideR39.1 andrelativeJ7 Z[-9.1,16.1], invariantunderq7 givesXZradius<=hypot(39.1,51.1)<64.4. ThusminZ140.6 underq6. OwnOEM embedded thread/rotor motion not certified.'),hist

def net_section(shape,y=-11,h=.002):
 slab=shape.intersect(cq.Solid.makeBox(250,h,250,cq.Vector(-125,y-h/2,-100)));p=GProp_GProps();BRepGProp.VolumeProperties_s(slab.wrapped,p)
 area=volume(slab)/h;co=np.array(slab.Center().toTuple());b=np.array(bb(slab));I=np.array([[p.MatrixOfInertia().Value(i,j) for j in [1,3]] for i in [1,3]])/h;I-=np.eye(2)*area*h*h/12
 assert min(np.linalg.eigvalsh(I))>0
 gain=max(np.linalg.norm(np.linalg.inv(I)@np.array([-(z-co[2]),x-co[0]])) for x,z in itertools.product([b[0,0],b[1,0]],[b[0,2],b[1,2]]))
 return dict(plane_link_Y_mm=y,slab_thickness_mm=h,method='finite symmetric slab area/inertia with normal-thickness correction, not exact analytic section',area_mm2=area,centroid_link_mm=co.tolist(),I_XZ_mm4=I.tolist(),normal_stress_gain_per_Nmm=float(gain),bbox_mm=b.tolist())

def mechanics(pr):
 s56=json.loads((L56/'study.json').read_text());p56=s56['parts']['L56-E01'];m56=s56['mechanics'];pair=json.loads((PAIR/'study.json').read_text())['mechanics'];g=9.80665
 rows=[dict(id='L45',m=pr['mass_if_6061_kg'],p=pr['com_link_mm'],pre=4),dict(id='J5_COM_proxy',m=1.09,p=[0,-55,19.99],pre=4),dict(id='L56',m=p56['mass_if_6061_kg'],p=(J5+np.array(p56['com_link_mm'])).tolist(),pre=5),dict(id='J6_COM_proxy',m=.88,p=[0,-32.15,205],pre=5),dict(id='J7_COM_proxy',m=.88,p=[0,55,207.85],pre=6),dict(id='head_budget',m=1.5,p=[0,55,340],pre=7),dict(id='net_payload',m=2,p=[0,55,440],pre=7)]
 rows.extend(dict(id=r['id'],m=r['mass_kg'],p=(np.array(r['com_pair_mm'])+J6).tolist(),pre=r['preceding_joints']) for r in pair['body_rows'])
 C=np.array(m56['C_kg_mm']);D=np.array(m56['D_kg_mm']);B=pr['mass_if_6061_kg']*np.array(pr['com_link_mm'])+1.09*np.array([0,-55,19.99])+m56['output_loaded_mass_kg']*J5
 eps=m56['q7_off_axis_first_moment_bound_kg_mm']+abs(B[0])+abs(C[0])+abs(D[0]);assert abs(B[0])+abs(C[0])+abs(D[0])<1e-8 and B[1]<0 and C[1]+D[1]>0 and D[2]>0
 H=B[2]+C[2];Y=C[1]+D[1];Z=D[2];qstar=math.degrees(math.atan2(abs(B[1]),H));assert 0<=qstar<=100
 M=g*(math.sqrt(B[1]**2+Y**2+H**2+Z**2+2*Z*math.hypot(H,B[1]))+eps)/1000
 axis=g*(math.hypot(Y,H+Z)+eps)/1000;mass=sum(r['m'] for r in rows);F=mass*g
 delta5=1.09*g*math.hypot(40.1,max(67.6-30.01,30.01))/1000;delta=m56['two_motor_COM_geometry_uncertainty_Nm']+delta5
 fine=.10*g*.335+.05*g*.110;Mplan=M+delta+fine;Fplan=F+.15*g
 samples=[]
 for q5,q6,q7 in itertools.product(np.linspace(-90,90,37),np.linspace(-100,100,41),[-90,0,90]):
  mr=sum(r['m']*point_pose(r['p'],q5,q6,q7,r['pre']) for r in rows);mt=g*np.linalg.norm(mr)/1000;ax=g*np.linalg.norm(mr[[0,2]])/1000;assert mt<=M+1e-8 and ax<=axis+1e-8;samples.append([float(q5),float(q6),q7,float(mt),float(ax)])
 # Separate independent seeded point recursion, not reuse C/D analytic values.
 rng=np.random.default_rng(4501);qs=np.column_stack([rng.uniform(-90,90,10000),rng.uniform(-100,100,10000),rng.uniform(-90,90,10000)]);mx=0;maxax=0
 for q5,q6,q7 in qs:
  mr=sum(r['m']*point_pose(r['p'],q5,q6,q7,r['pre']) for r in rows);mx=max(mx,g*np.linalg.norm(mr)/1000);maxax=max(maxax,g*np.linalg.norm(mr[[0,2]])/1000)
 assert mx<=M+1e-8 and maxax<=axis+1e-8
 M5=m56['worst_J5_output_moment_Nm']+m56['force_N']*.0115+1.09*g*.01851+delta+.1*g*.2715+.025*g*.06
 F5=m56['force_N']+1.09*g+.125*g
 I=28*7**3/12;A=28*7;E=69000;length=14
 shape=cq.importers.importStep(str(OUT/'STEP/L45-E01.step')).val();assert np.linalg.norm(np.max(np.abs(np.array(bb(shape))),axis=0))<=117;removal=pr['mass_if_6061_kg']*g*.117;Mlocal=Mplan+Fplan*.011+removal;ns=net_section(shape);ns['local_moment_bound_Nm']=Mlocal;ns['carrier_upstream_removal_moment_allowance_Nm']=removal;ns['normal_stress_rectangle_bound_indicator_MPa']=Mlocal*1000*ns['normal_stress_gain_per_Nmm']+Fplan/ns['area_mm2'];ns['conditions']='Nominal beam normal stress only. Global moment shifted11mm, plus bound for removing upstreamcarrier mass. Fullcarrier maxdistance<=117mm confirmed from bbox. No notch/prying/contact/shear/torsion/fatigue stress claim.'
 return dict(body_rows=rows,head_budget_kg=1.5,head_excludes_actual_PAIR_interface=True,payload_net_kg=2,head_COM_from_J7_output_mm=100,TCP_from_J7_output_mm=200,J4_self_mass_excluded=True,output_loaded_mass_kg=mass,gravity_m_s2=g,B_kg_mm=B.tolist(),C_kg_mm=C.tolist(),D_kg_mm=D.tolist(),off_axis_residual_bound_kg_mm=eps,continuous_nominal_arbitrary_gravity_moment_Nm=M,continuous_J4_axis_gravity_torque_bound_Nm=axis,maximizing_nominal_q5_q6_deg=[-90,qstar],analytic_formula='By<0, wY>0 and q5in[-90,90]: min rotated wY=-abs(wX), attained at endpoint. max H*cos(q6)+abs(By)*abs(sin(q6))=hypot(H,By). q4 about-Y preserves norm and Y-axis moment bound; small residual uses triangle.',three_module_COM_uncertainty_Nm=delta,J5_COM_uncertainty_Nm=delta5,fine_hardware_budgets=[{'mass_kg':.10,'radius_from_J4_m':.335,'role':'InheritedLINK56 entire downstream finehardware contingency'},{'mass_kg':.05,'radius_from_J4_m':.110,'role':'NewJ4/J5 finehardware contingency'}],planned_moment_Nm=Mplan,planned_J4_axis_torque_bound_Nm=axis+delta+fine,planned_force_N=Fplan,J4_output_bolts=group(27,A80,Mplan,Fplan),J5_fixed_bolts=group(37,FIX,M5,F5),neck_strip={'width_mm':28,'thickness_mm':7,'length_mm':length,'I_mm4':I,'area_mm2':A,'E_assumed_MPa':E,'normal_stress_indicator_MPa':Mlocal*1000*3.5/I+Fplan/A,'local_moment_input_Nm':Mlocal,'cantilever_deflection_indicator_mm':Mlocal*1000*length**2/(2*E*I)+Fplan*length**3/(3*E*I),'condition':'Selected28x7 rectangular bridge strip; J4 moment shifted11mm and upstreamcarrier removal allowance added. Not actual fillet/notch/ring stress, prying, contactFEA or globally conservative assembly stress bound.'},actual_neck_slab=ns,sampled_rows=samples,independent_random_check={'seed':4501,'count':10000,'method':'per-body nested rotations, independently of aggregate analytic C/D','max_moment_Nm':mx,'max_axis_bound_Nm':maxax},not_validated=['FullOEMthread/screwSKU/length/preload','Materialallowables/contact/localFEA/fatigue','Dynamicinertia/stop/bearinglife','Staticzerovelocitythermalhold','Upstreamstructure, fullhead and completeharness'])

def dimensional_recheck():
 s=cq.importers.importStep(str(OUT/'STEP/L45-E01.step')).val();rows={}
 for name,T,rad,n in [('J4_OUTPUT',T4,27,16),('J5_FIXED',T5,37,12)]:
  shape=moved(s,np.linalg.inv(T));pts=[]
  for f in shape.Faces():
   a=BRepAdaptor_Surface(f.wrapped)
   if a.GetType()!=GeomAbs_Cylinder:continue
   c=a.Cylinder();p=c.Location();d=c.Axis().Direction()
   if abs(c.Radius()-1.7)<1e-5 and abs(d.Z())>.999999 and abs(math.hypot(p.X(),p.Y())-rad)<1e-5:pts.append([p.X(),p.Y()])
  pts=sorted(set(tuple(round(v,6) for v in p) for p in pts));assert len(pts)==n
  exp=polar(rad,A80 if name=='J4_OUTPUT' else FIX);err=max(min(math.dist(a,b) for b in exp) for a in pts);assert err<1e-6;rows[name]=dict(count=n,centres_in_joint_frame_mm=pts,max_axis_error_mm=err)
 return dict(step_sha256=sha(OUT/'STEP/L45-E01.step'),actual_holes=rows,bbox_mm=bb(s),valid=s.isValid(),solids=len(s.Solids()))
def shifted(cs,dx,dy):
 cs=json.loads(json.dumps(cs))
 for r in cs:
  for k in ['p','q','c']:
   if k in r:r[k][0]+=dx;r[k][1]+=dy
 return cs
class Page(Sheet):
 def header(self,n,title,sub):
  self.text(14,282,'ODRADEK / R5-LINK45-EROB01',18);self.text(405,282,f'{n} / 5',10,align='right');self.text(14,271,title,12,BLUE);self.text(405,271,sub,8.2,align='right');self.line((14,266),(406,266),BLUE,.8)
 def footer(self,n):
  self.line((14,20),(406,20),GREY,.5);self.text(14,13,'mm / A3 | 名义金属候选与无载样件 | 非生产图、非全臂/2kg额定认证',8);self.text(406,13,f'2026-09-28 / {n}',8,align='right')
def drawings(L,orig,S):
 cs={'J4_OUTPUT_LOCAL_Z6.8':curves(section(moved(L,np.linalg.inv(T4)),'XY',6.8),'XY'),'J5_FIXED_WORLD_Z45.4':curves(section(L,'XY',45.4),'XY'),'SIDE_X0':yzcs(L),'SIDE_X10':yzcs(L,10)}
 d=ezdxf.new('R2013');d.units=4;d.header['$INSUNITS']=4
 for l,col in [('BOUNDARY',7),('NOTE',3),('DIM',2)]:d.layers.new(l,dxfattribs={'color':col})
 ms=d.modelspace()
 for i,(n,c) in enumerate(cs.items()):dxf_geometry(ms,c,(i*180,0));ms.add_text(n,dxfattribs={'height':2.4,'insert':(i*180-45,65),'layer':'NOTE'})
 notes=['R5-LINK45-EROB01 / mm / NOT PRODUCTION RELEASE','O=J4 world(0,0,435), axis-Y; J5=(0,-55,50), axis+Z','J4 disc OD76, localz0..10; rearOD66/ID60+0..019,z-8..0,C.3/innerR.1','CentreID18; rearreliefID49depth.3;16xID3.4PCD54nonuniform,CB6.2depth3.4floor6.6,C.2','12 factoryhead reliefsID5.3depth.5; actual CSV coordinates authoritative','J5 ring OD86/ID67, linkZ38.5..45.5, centreXY(0,-55);12xID3.4PCD74 at15+30k','PostX+/-14,Y-10..-4,Z30.5..45.5;bridgeX+/-14,Y-24..-4,Z38.5..45.5','Inside elbowR2 atY-10/Z38.5; ring bore cuts bridge; otheredges nominalsharp','OEM M3x.35/fullthread/length/SKU TBD, outputeng>=3/fixedeng>=4mm','Head/cables/J3-L34/material/preload/FEA/thermal not validated']
 for i,n in enumerate(notes):ms.add_text(n,dxfattribs={'height':2.1,'insert':(-45,-120-i*4),'layer':'NOTE'})
 dx=OUT/'DXF/ODR-L45-E01.dxf';d.saveas(dx);assert not ezdxf.readfile(dx).audit().has_errors
 p=OUT/'ODR-R5-LINK45-EROB01.pdf';c=canvas.Canvas(str(p),pagesize=landscape(A3));s=Page(c)
 s.header(1,'短偏置肘架 / 轴布局不变','侧剖1.25:1；+Y右/+Z上，灰框仅源已核包络')
 s.geo(yzcs(L),(182,143),1.25,BLUE,1);context=orig['L56'].intersect(cq.Solid.makeBox(250,250,30,cq.Vector(-125,-125,42)));s.geo(yzcs(context),(182,143),1.25,'#6F824C',.6)
 # L56 context is explicitly cut atlinkZ72, not shown as a complete part.
 s.dim_h(113.25,182,69,205.5,143,'55');s.line((113.25,205.5),(257,205.5),GREY,.3);s.dim_v(143,205.5,257,182,'50')
 for y,z,w,h in [(0,-40.1,67.6,80.2),(-95.1,-17.6,80.2,56.1),(-85.1,38.5,60.2,11.5)]:
  aa=(182+y*1.25,143+z*1.25);b=(182+(y+w)*1.25,143+(z+h)*1.25)
  for e,f in [(aa,(b[0],aa[1])),((b[0],aa[1]),b),(b,(aa[0],b[1])),((aa[0],b[1]),aa)]:s.line(e,f,GREY,.35,[4,2])
 s.text(185,136,'J4 −Y',9);s.text(107,220,'J5 +Z',9);s.text(17,252,'蓝：本件；绿：L56底部截至Z72；不含整头/上游',9,BLUE)
 s.text(287,251,'同一布局与实际接口',11,BLUE);s.rows(287,239,['J4 world(0,0,435)，轴−Y','J5 world(0,−55,485)，轴+Z','J4数学±120° / J5 ±90°','J6±100° / J7±90°仅局部集合','两端均eRob80I V6带闸候选','J4输出16孔PCD54非均布','J5固定12孔PCD74，相位15°','不复制70I的8孔与长自由孔','单体一体肘架，无新增拼接螺钉','J5环OD86/ID67，厚7','LINK56及PAIR尺寸保持'],7,8.6)
 s.rows(16,43,[f"6061密度假设下本件{S['parts']['L45-E01']['mass_if_6061_kg']*1000:.3f}g；轴距不变。前后接口真实接触，仍非材料/强度放行。"],7,9);s.footer(1);c.showPage()
 s.header(2,'L45-E01 / 真截面与全部名义形状','J4输出局部XY 1.65:1；全局侧剖1.1:1')
 s.geo(cs['J4_OUTPUT_LOCAL_Z6.8'],(95,181),1.65);s.axes((95,181),40,1.65);s.dim_h(32.3,157.7,260,181,181,'Ø76')
 s.geo(cs['SIDE_X0'],(340,188),1.1);s.dim_h(232.2,348.8,127,230.35,224.3,'外形Y−98…+8 / 106');s.dim_v(230.35,238.05,358,334,'7 固定环');s.lead((329,230.35),(363,220),(373,220),'内根R2')
 s.rows(15,107,['J4局部frame：X=worldX，Y=worldZ，Z=−worldY；输出接触面localZ0。','底盘OD76，localZ0…10；后裙OD66/ID60+0.019/0，Z−8…0，入口C0.3，内根R0.1。','中央Ø18贯通；背面Ø49×0.3不承力避空；16×Ø3.4，前沉孔Ø6.2深3.4、底Z6.6/内口C0.2。','12处原厂齐平头避空Ø5.3×0.5；不拆原厂头、不将其计为安装孔。','立柱X−14…14、Y−10…−4、Z30.5…45.5；横桥X−14…14、Y−24…−4、Z38.5…45.5。','立柱/横桥内根真实R2；J5固定环中心XY(0,−55)，OD86/ID67，Z38.5…45.5；内孔切通横桥。','J5：12×Ø3.4贯穿7，PCD74/15+30k°，前孔口C0.2；其他未注边为名义锐边。','关键厚度±0.05、外形±0.10、孔位Ø0.10仅试制建议；原厂母止口/接触面要求另遵受控图。'],7,8.9)
 s.footer(2);c.showPage()
 s.header(3,'两端安装孔 / 明确牙段边界','J5俯视1.35:1；表中J4为localXY，J5为linkXY')
 s.geo(shifted(cs['J5_FIXED_WORLD_Z45.4'],0,55),(91,186),1.35);s.axes((91,186),45,1.35);s.dim_h(32.95,149.05,261,186,186,'Ø86 / ID67')
 s.text(174,249,'J4输出16孔 / PCD54',10,BLUE)
 for i,(a,pt) in enumerate(zip(A80,polar(27,A80))):s.text(174,237-i*6,f'{i+1:2d} {pt[0]:+.6f} {pt[1]:+.6f} {a}°',8.4)
 s.text(299,249,'J5固定12孔 / PCD74',10,BLUE)
 for i,(a,pt) in enumerate(zip(FIX,polar(37,FIX))):s.text(299,237-i*6.5,f'{i+1:2d} {pt[0]:+.6f} {pt[1]-55:+.6f} {a}°',8.4)
 s.rows(15,111,['80I V6源：native输出+X；统一X=nativeY、Y=nativeZ、Z=nativeX−32.9235811105。','真实固定面jointZ−11.5；12个固定孔在15+30k°，与原厂装配螺钉/其他孔区别保留。','原厂M3×0.35、12.9黑氧化圆柱头：输出完整牙≥3.0、80I V6固定完整牙≥4.0。','J4已知自由杆=6.6+5=11.6mm；J5只计本件厚7mm，不把OEM模型螺纹样貌当已确认自由孔。','全部28颗新螺钉精确SKU/长度/最大深入仍TBD；普通M3×0.5不能默认替换。','头包络Ø5.68×3；Ø5.8×60工具仅空间探针。条件成立后手册干装扭矩2.0±0.2Nm，非预紧验证。'],7,8.9)
 s.footer(3);c.showPage()
 s.header(4,'装配与局部全角域 / 线束边界','离散真实交集与连续外部证明分别记录')
 s.text(15,251,'一体路线与连贯装拆',11,BLUE);s.rows(15,239,['先独立支承模块、断电；L45沿J4的−Y方向套入。','在J5尚未装入时，装16颗J4输出细牙螺钉。','J5从下方沿+Z进入固定环；逐solid验证整机鼻部装入。','装12颗J5固定螺钉，随后才装冻结LINK56。','再按LINK56与PAIR顺序装J6、W01、J7和头接口。','拆卸需卸载、断电、解绑线束后逆序，不能带整头松螺钉。','分体可拆路线会增加连接面/预紧和至少4个小螺钉。','本选定15高颈部，四M3头+8行距+1.5边缘要16.68高。','该分体尺寸不足1.68；不宣称其他分体布局都无解。'],7,8.9)
 s.text(220,251,'连续几何依据',11,BLUE);s.rows(220,239,['q4：新件主体在Y≤0，后裙为轴对称避空环。','J5整机Y≤−14.9；q4绕Y不改变此半空间。','L56最低Z42，q5不改Z；q4保持到Y轴的径距。','J4源包含R40.1，因此全域径向余量至少1.9。','J6更高；腕/J7按冻结真实包含最低Z140.6。','q5：只有L56后裙进入载体高度，R33/ID33.5。','固定头内缘R34.16；前板与头顶留1.5轴向隙。','q6/q7沿用实际下游包含，不包含尚未建模整头。','OEM内部/完整牙段、公差弹性、J3/L34不认证。'],7,8.9)
 s.text(15,155,'端口和内走线',11,BLUE);s.rows(15,143,['两模块后方均有R44×40轴向预留，实际CAD静态与连续分离条件在JSON；不是配对插头模型。','80I前固定孔与后端口角向位置无固定关系；不能据一份STEP冻结实物clocking或针序。','两轴Ø18只是几何孔；本件没有证明90°方向转换、两个GMSL、电源和EtherCAT全束通过。','LINK56既有R35底部路径真实撞J6的失败保留，需要另做后向/侧舱服务环；本阶段不覆盖为已通过。','当前打印只核孔/面/工具：模块需独立支撑，塑料不承载电机自重、更不能挂2kg或通电运动。'],7,9)
 s.footer(4);c.showPage()
 s.header(5,'质量、条件静力与无载打印','2kg净物体+1.5kg头预算；接口和电机自重另计')
 M=S['mechanics'];s.rows(15,251,[f"本件金属{S['parts']['L45-E01']['mass_if_6061_kg']*1000:.3f}g，pre4；LINK56及PAIR用实际CAD质量/COM；J5=1.09、J6/J7各0.88kg。",f"1.5kg头不含PAIR接口；TCP+200/头COM+100从J7 OEM输出面算。本输出加载{M['output_loaded_mass_kg']:.6f}kg。",f"q5/q6连续解析弯矩界{M['continuous_nominal_arbitrary_gravity_moment_Nm']:.5f}Nm；J4轴驱动矩界{M['continuous_J4_axis_gravity_torque_bound_Nm']:.5f}Nm，不能混用。",f"加三电机COM几何余量{M['three_module_COM_uncertainty_Nm']:.5f}Nm，旧下游.10kg/335mm和本新增.05kg/110mm紧固件预算。",f"规划M={M['planned_moment_Nm']:.5f}Nm / 轴矩界{M['planned_J4_axis_torque_bound_Nm']:.5f}Nm / 力{M['planned_force_N']:.3f}N；未含动态冲击/制动。",f"J4螺钉最大附加轴力{M['J4_output_bolts']['maximum_axial_increment_N']:.3f}N；J5固定组{M['J5_fixed_bolts']['maximum_axial_increment_N']:.3f}N；均不含预紧/撬力。"],7,9)
 N=M['neck_strip'];s.rows(15,196,[f"颈部输入M={N['local_moment_input_Nm']:.5f}Nm：移至Y−11，并加去除上游本件自重的几何余量。",f"选定28×7、跨14颈部条带：截面应力指标{N['normal_stress_indicator_MPa']:.3f}MPa，悬臂挠度指标{N['cantilever_deflection_indicator_mm']:.5f}mm。",f"Y−11真实截面薄层A={M['actual_neck_slab']['area_mm2']:.3f}mm²，法向应力边框指标{M['actual_neck_slab']['normal_stress_rectangle_bound_indicator_MPa']:.3f}MPa；非缺口/接触FEA。",'母止口薄裙、主盘孔间韧带、横桥/环融合与R2圆根需局部FEA和疲劳；没有材料许用值放行。','原厂31Nm额定/70Nm启停不等同本散热条件下的零速连续保持；停止/回生/制动由独立研究验证。'],7,9)
 s.text(15,153,'L45-G 无电无载样件',11,BLUE);s.rows(15,141,['母止口Ø60.4、中心Ø18.4、后避空Ø49.2深0.5、OEM通孔Ø3.8、J5固定环ID67.4。','打印向：先变到J4局部坐标，再+Z移8落床；高度106mm。PLA/PETG、局部支撑须可拆。','先测止口/孔径试片，仅补局部孔，不整体缩放；打印件不代替金属公差/预紧/寿命试验。','STEP有效单实体；STL导出.01mm/.05rad，水密/体积/bbox重读检查；完整数值及来源哈希在JSON。','无可执行整臂轨迹、无生产发布：先闭合完整牙/SKU、工具/插头、材料和结构验证。'],7,9)
 s.footer(5);c.save();assert len(PdfReader(p).pages)==5
 return dict(file=p.name,sha256=sha(p),pages=5),dict(file=str(dx.relative_to(OUT)),sha256=sha(dx),units_mm=True,audit_errors=0)

def core_hash():
 return hashlib.sha256((''.join(inspect.getsource(f) for f in [build,properties,export,vendor_fixed_extraction,originals,R,point_pose,checks,prior_hardware_checks,net_section,mechanics,dimensional_recheck])+repr(T4.tolist())+repr(T5.tolist())+''.join(sha(p) for p in [SRC,ROOT/'engineering/r5_link56_erob01.py',L56/'study.json',ROOT/'engineering/r5_wrist_pair01.py',PAIR/'study.json'])).encode()).hexdigest()
def manifest():
 js(OUT/'manifest.json',{'revision':'R5-LINK45-EROB01','outputs':[dict(path=str(p.relative_to(OUT)),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['manifest.json','visual-qa.json'] and p.suffix!='.png']})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--vendor80-step',type=Path);ap.add_argument('--vendor70-step',type=Path);ap.add_argument('--private-preview-dir',type=Path);ap.add_argument('--redraw',action='store_true');args=ap.parse_args()
 for d in ['STEP','STL','DXF']:(OUT/d).mkdir(parents=True,exist_ok=True)
 pdfmetrics.registerFont(TTFont('CN','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
 if args.redraw:
  S=json.load(open(OUT/'study.json'));assert S['core_hash']==core_hash();assert sha(OUT/'STEP/L45-E01.step')==S['parts']['L45-E01']['step_sha256'];L=cq.importers.importStep(str(OUT/'STEP/L45-E01.step')).val();S['source_hashes'][0]['sha256']=sha(__file__);S['pdf'],S['dxf']=drawings(L,originals(),S);js(OUT/'study.json',S);manifest();return
 src=json.load(open(SRC))
 for p,id in [(args.vendor80_step,'vendor80_step'),(args.vendor70_step,'vendor70_step')]:assert p and sha(p)==next(s['sha256'] for s in src['sources'] if s['id']==id)
 model=ROOT/'engineering/generated/raised-arm-integration01/model.json';jj=json.load(open(model))['arm']['joints'];assert jj[3]['origin_mm']==ORIGIN.tolist() and jj[3]['axis']==[0,-1,0] and jj[3]['limit_deg']==[-120,120] and jj[4]['origin_mm']==(ORIGIN+J5).tolist() and jj[4]['axis']==[0,0,1] and jj[4]['limit_deg']==[-90,90]
 v80=cq.importers.importStep(str(args.vendor80_step)).val().rotate((0,0,0),(1,1,1),-120).translate((0,0,-X80));v70=cq.importers.importStep(str(args.vendor70_step)).val().rotate((0,0,0),(1,1,-1),120).translate((0,0,X70));assert len(v80.Solids())==5
 js(OUT/'vendor80-fixed-extraction.json',vendor_fixed_extraction(v80));L=build();G=build(True);P={'L45-E01':export('L45-E01',L),'L45-G':export('L45-G',G)}
 print('Original exported mass '+str(P['L45-E01']['mass_if_6061_kg']),flush=True)
 gp=moved(G,np.linalg.inv(T4)).translate((0,0,8));pp=OUT/'STL/L45-G-print-oriented.stl';cq.exporters.export(gp,str(pp),tolerance=.01,angularTolerance=.05);gm=trimesh.load(pp,force='mesh',process=True);assert gm.is_watertight and gm.is_winding_consistent and abs(gm.bounds[0,2])<1e-5
 orig=originals();ch,hw,vendors=checks(L,v80,v70,orig);ch['prior_hardware'],old_hw=prior_hardware_checks(L,hw);print('Geometry passed',flush=True);mech=mechanics(P['L45-E01'])
 with (OUT/'gravity-sampled-check.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(['q5_deg','q6_deg','q7_deg','J4_moment_Nm','J4_axis_gravity_bound_Nm']);w.writerows(mech.pop('sampled_rows'))
 with (OUT/'hole-coordinates.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['group','index','x_link_mm','y_link_mm','z_link_mm','hole_mm','note'])
  for n,aa,r,z,T,d,no in [('J4_OUTPUT',A80,27,0,T4,3.4,'CB6.2depth3.4floor6.6; C.2'),('J4_FACTORY_RELIEF',REL80,27,0,T4,5.3,'depth.5 notmounting'),('J5_FIXED',FIX,37,-11.5,T5,3.4,'THRU7frontC.2')]:
   for i,xy in enumerate(polar(r,aa)):w.writerow([n,i+1,*(T@np.r_[xy,z,1])[:3],d,no])
 files=[Path(__file__),SRC,model,ROOT/'engineering/r5_link56_erob01.py',L56/'study.json',L56/'STEP/L56-E01.step',ROOT/'engineering/r5_wrist_pair01.py',PAIR/'study.json',PAIR/'STEP/W01.step',PAIR/'STEP/A01-P.step',PAIR/'STEP/H01-reuse.step',ROOT/'engineering/build_layout.py',ROOT/'engineering/draw_central_display01.py',ROOT/'engineering/r5_wrist_erob01.py']
 S=dict(revision='R5-LINK45-EROB01',license='CC-BY-NC-4.0',status='nominal original geometry candidate, not productionrelease',core_hash=core_hash(),source_hashes=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in files],frames={'world_origin_mm':ORIGIN.tolist(),'T4':T4.tolist(),'T5':T5.tolist(),'T6':T6.tolist(),'T7':T7.tolist(),'limits_deg':[[-120,120],[-90,90],[-100,100],[-90,90]]},parts=P,print_oriented={'sha256':sha(pp),'bbox_mm':gm.bounds.tolist(),'watertight':bool(gm.is_watertight)},checks=ch,mechanics=mech,comparison={'selected':'one-piece original','split_variant':'Not detailed. A selected4xM3,8mm rowgap and1.5mm edge-to-headface budget requires8+5.68+3=16.68mm height; present15mm post insufficientby1.68. Other split architectures not ruledout. Avoid extra joint/preload while retaining axes.'})
 js(OUT/'study.json',S);js(OUT/'part-placements.json',{'revision':'R5-LINK45-EROB01','parts':[dict(id='L45-E01',**properties(L))]});js(OUT/'dimension-qa.json',dimensional_recheck());S['pdf'],S['dxf']=drawings(L,orig,S);js(OUT/'study.json',S)
 a=cq.Assembly();a.add(L,name='L45_E01')
 for n,s in orig.items():a.add(s,name=n)
 a.save(str(OUT/'STEP/ORIGINAL-context-assembly.step'))
 if args.private_preview_dir:
  args.private_preview_dir.mkdir(parents=True,exist_ok=True);aa=cq.Assembly()
  for n,s in {'L45':L,**orig,**vendors,**hw,**old_hw}.items():aa.add(s,name=n)
  aa.save(str(args.private_preview_dir/'PRIVATE-with-vendor.step'))
 manifest();print(json.dumps({'mass':P['L45-E01']['mass_if_6061_kg'],'com':P['L45-E01']['com_world_mm'],'moment':mech['continuous_nominal_arbitrary_gravity_moment_Nm'],'axis':mech['continuous_J4_axis_gravity_torque_bound_Nm'],'plannedM':mech['planned_moment_Nm'],'neck':mech['neck_strip'],'contacts':ch['contact_area_proxy_mm2']},indent=2),flush=True)
if __name__=='__main__':main()
