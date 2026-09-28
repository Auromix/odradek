# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-LINK56-EROB01: one original eRob80I->70I load-path candidate.
Millimetres; vendor STEP inputs are private/hash-checked. No frozen model is changed.
Continuous external geometry is distinct from unknown OEM thread/rotor internals.
"""
from pathlib import Path
import argparse,json,hashlib,math,csv,itertools,inspect
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
from r5_wrist_erob01 import cyl,cone,polar,bb,volume,OEM_ANGLES,HEAD_ANGLES
from r5_wrist_pair01 import cap,ann,T6 as PAIR_T6,curves
from draw_central_display01 import section,dxf_geometry,Sheet,BLUE,GREY
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/r5-link56-erob01';SRC=ROOT/'docs/engineering/sources/r5-link56-erob01.json'
PAIR=ROOT/'engineering/generated/r5-wrist-pair01'
X80=32.92358111047752;X70=-9.774999898159106
A80=[0,36,54,72,90,126,144,162,180,216,234,252,270,306,324,342]
REL80=[(a+b)%360 for a in [45,63,81] for b in [0,90,180,270]]
ORIGIN=np.array([0.,-55.,485.]);J6=np.array([0.,55.,155.]);J7=np.array([0.,110.,190.])
T6=PAIR_T6.copy();T6[:3,3]=J6;T7=frame(J7,[0,0,1]);RHO=2.7e-6

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def inter(a,b):
 x,y=np.array(bb(a)),np.array(bb(b))
 if np.any(x[1]<=y[0]+1e-8) or np.any(y[1]<=x[0]+1e-8):return 0.
 return volume(a.intersect(b))
def props(s):
 p=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,p);I=np.array([[p.MatrixOfInertia().Value(i,j) for j in range(1,4)] for i in range(1,4)])*RHO*1e-6
 return dict(mass_if_6061_kg=volume(s)*RHO,volume_mm3=volume(s),com_link_mm=list(s.Center().toTuple()),com_world_mm=(np.array(s.Center().toTuple())+ORIGIN).tolist(),inertia_at_com_world_kg_m2=I.tolist(),density_assumption_kg_m3=2700,preceding_joints=5)

def build(gauge=False):
 bore=30.2 if gauge else 30;rhole=1.9 if gauge else 1.7
 a=cap(38,0,8).fuse(ann(33,bore,-8,0));es=[e for e in a.Edges() if abs(e.Length()-2*math.pi*bore)<1e-4 and abs(e.Center().z)<1e-5];assert len(es)==1;a=a.fillet(.1,es)
 a=a.cut(cone(bore+.3,bore,-8,.3)).cut(cap(9.2 if gauge else 9,-9,9)).cut(cap(24.6 if gauge else 24.5,-.01,.5 if gauge else .3))
 for xy in polar(27,A80):a=a.cut(cap(rhole,-.01,8.01,xy)).cut(cap(3.1,4.6,8.01,xy)).cut(cone(rhole,rhole+.2,4.4,.2,xy))
 for xy in polar(27,REL80):a=a.cut(cap(2.65,-.01,.5,xy))
 a=a.fuse(ann(20,17,8,104)).fuse(cq.Solid.makeBox(44,71,10,cq.Vector(-22,-20,104)))
 a=a.fuse(cq.Solid.makeBox(36,6,31,cq.Vector(-18,45,104))).fuse(moved(ann(39,29.4 if gauge else 29.3,-10,-4),T6))
 a=a.cut(cap(17,8,114.01)).cut(moved(cap(29.4 if gauge else 29.3,-10.01,-3.99),T6))
 for xy in polar(32,range(0,360,45)):a=a.cut(moved(cap(rhole,-10.01,-3.99,xy).fuse(cone(rhole,rhole+.2,-4.2,.2,xy)),T6))
 a=a.clean();es=[e for e in a.Edges() if abs(e.Length()-40*math.pi)<1e-5 and abs(e.Center().z-8)<1e-5];assert len(es)==1;a=a.fillet(2,es)
 es=[e for e in a.Edges() if e.geomType()=='LINE' and math.dist(e.Center().toTuple(),(0,45,114))<1e-5];assert len(es)==1
 return a.fillet(1.5,es).clean()

def export(name,s):
 assert s.isValid() and len(s.Solids())==1
 p=OUT/'STEP'/(name+'.step');f=OUT/'STL'/(name+'.stl');cq.exporters.export(s,str(p));cq.exporters.export(s,str(f),tolerance=.01,angularTolerance=.05)
 r=cq.importers.importStep(str(p)).val();m=trimesh.load(f,force='mesh',process=True)
 q=dict(**props(s),bbox_mm=bb(s),step_sha256=sha(p),stl_sha256=sha(f),step_valid=r.isValid(),step_solids=len(r.Solids()),step_volume_relative_error=abs(volume(r)-volume(s))/volume(s),mesh_watertight=bool(m.is_watertight),mesh_winding_consistent=bool(m.is_winding_consistent),mesh_volume_relative_error=abs(m.volume-volume(s))/volume(s),mesh_bbox_max_error_mm=float(np.max(np.abs(m.bounds-np.array(bb(s))))),chordal_tolerance_mm=.01,angular_tolerance_rad=.05)
 assert q['step_valid'] and q['step_solids']==1 and q['step_volume_relative_error']<1e-8 and q['mesh_watertight'] and q['mesh_winding_consistent'] and q['mesh_volume_relative_error']<.001 and q['mesh_bbox_max_error_mm']<.02
 return q

def extraction(v):
 cylinders=[];planes=[]
 for si,s in enumerate(v.Solids()):
  for fi,f in enumerate(s.Faces()):
   a=BRepAdaptor_Surface(f.wrapped);b=bb(f)
   if a.GetType()==GeomAbs_Cylinder:
    c=a.Cylinder();d=c.Axis().Direction();p=c.Location();rr=math.hypot(p.X(),p.Y())
    if abs(d.Z())>.999999 and ((rr<1e-5 and any(abs(c.Radius()-r)<1e-5 for r in [9,29.8,30,40])) or abs(rr-27)<1e-5):
     cylinders.append(dict(solid=si,face=fi,radius_mm=c.Radius(),xy_mm=[p.X(),p.Y()],pcd_radius_mm=rr,angle_deg=round(math.degrees(math.atan2(p.Y(),p.X()))%360,6)%360,z_interval_mm=[b[0][2],b[1][2]]))
   elif a.GetType()==GeomAbs_Plane:
    p=a.Plane();d=p.Axis().Direction()
    if abs(d.Z())>.999999 and abs(p.Location().Z())<1e-6:planes.append(dict(solid=si,face=fi,z_mm=p.Location().Z(),area_mm2=f.Area()))
 holes=sorted(set(r['angle_deg'] for r in cylinders if abs(r['pcd_radius_mm']-27)<1e-5 and abs(r['radius_mm']-1.7)<1e-5 and abs(r['z_interval_mm'][1])<1e-5))
 relief=sorted(set(r['angle_deg'] for r in cylinders if abs(r['pcd_radius_mm']-27)<1e-5 and abs(r['radius_mm']-2.35)<1e-5 and abs(r['z_interval_mm'][1])<1e-5))
 assert holes==A80 and relief==sorted(REL80)
 assert any(abs(r['radius_mm']-30)<1e-5 and abs(r['z_interval_mm'][1]+5.3)<1e-5 for r in cylinders)
 return dict(native_output_x_mm=X80,transform='joint X=nativeY; Y=nativeZ; Z=nativeX-X80, rotationdet+1',output_pcd_mm=54,output_angles_deg=holes,factory_head_relief_angles_deg=relief,output_known_free_channel_joint_z_mm=[-5,0],cylinders=cylinders,output_planes=planes,manual_central_no_load_relief_diameter_mm=49,drawing_other_central_diameter_mm=46.4,note='49mm is manual no-load region; do not substitute unrelated46.4mm diameter. Rendered CAD threads are not controlled full-thread depth/pitch evidence.')

def pair_originals():
 return {'PAIR_W01':cq.importers.importStep(str(PAIR/'STEP/W01.step')).val().translate(tuple(J6)),
 'PAIR_A01P':moved(cq.importers.importStep(str(PAIR/'STEP/A01-P.step')).val(),T7),
 'PAIR_H01':moved(cq.importers.importStep(str(PAIR/'STEP/H01-reuse.step')).val(),T7)}

def check_geometry(L,V5,V6,V7,pair):
 originals={'L56':L,**pair};vendors={**{f'J5_solid{i+1}':v for i,v in enumerate(V5.Solids())},'J6':V6,'J7':V7}
 static=[]
 for n,s in originals.items():
  if n!='L56':continue
  for m,t in {**vendors,**pair}.items():
   v=inter(s,t);assert v<1e-5;static.append(dict(a=n,b=m,intersection_mm3=v))
 hp=[];hardware={};tools=[];sweeps=[]
 for group,aa,radius,z0,seat,T,obs in [('J5_OUT',A80,27,-5,4.6,np.eye(4),{'L56':L,**{k:v for k,v in vendors.items() if k.startswith('J5')}}),('J6_FIXED',list(range(0,360,45)),32,-26.5,-4,T6,{'L56':L,**{k:v for k,v in vendors.items() if k!='J7'}})]:
  for i,xy in enumerate(polar(radius,aa)):
   h=moved(cap(1.5,z0,seat,xy).fuse(cap(2.84,seat,seat+3,xy)),T);hardware[f'{group}_{i+1}']=h
   vals={n:inter(h,s) for n,s in {**originals,**vendors}.items()};assert max(vals.values())<1e-5;hp.append(dict(id=f'{group}_{i+1}',free_shaft_length_mm=seat-z0,head_max_mm=[5.68,3],intersection_mm3=vals,complete_fastener=False))
   tool=moved(cap(2.9,seat+.001,seat+60,xy),T);vals={n:inter(tool,s) for n,s in obs.items()};assert max(vals.values())<1e-5;tools.append(dict(id=f'{group}_{i+1}',diameter_length_mm=[5.8,60],intersection_mm3=vals,selected_tool=False))
   sw=moved(cap(1.5,z0,seat+60,xy).fuse(cap(2.84,seat,seat+63,xy)),T);vals={n:inter(sw,s) for n,s in obs.items()};assert max(vals.values())<1e-5;sweeps.append(dict(id=f'{group}_{i+1}',translation_from_seated_mm=[0,60],intersection_mm3=vals,thread_segment_unknown=True))
 hardware_pairs=[]
 for (a,sa),(b,sb) in itertools.combinations(hardware.items(),2):
  v=inter(sa,sb);assert v<1e-5;hardware_pairs.append(dict(a=a,b=b,intersection_mm3=v))
 # Later-stage J6 fixed bolts against already-installed J5 bolts, swept continuously.
 ordered=[]
 for xy in polar(32,range(0,360,45)):
  sw=moved(cap(1.5,-26.5,56,xy).fuse(cap(2.84,-4,59,xy)),T6)
  vals={n:inter(sw,h) for n,h in hardware.items() if n.startswith('J5_OUT')};assert max(vals.values())<1e-5;ordered.append(vals)
 # Real BREP in an axisymmetric sleeve/positive half-space gives q5 continuous exterior proof.
 skirt=ann(33,30,-8,0).fuse(ann(33,29.9,-.1,0))
 neg=L.intersect(cq.Solid.makeBox(300,300,10,cq.Vector(-150,-150,-10)))
 escape=volume(neg.cut(skirt));assert escape<1e-5
 sv={n:inter(skirt,v) for n,v in vendors.items() if n.startswith('J5')};assert max(sv.values())<1e-5
 insertion=ann(33,30,-8,70).fuse(ann(33,29.9,-.1,70))
 iv={n:inter(insertion,v) for n,v in vendors.items() if n.startswith('J5')};assert max(iv.values())<1e-5
 # J6 rearward insertion uses the SAME source-verified bound as PAIR, repeated on this actual source.
 local6=moved(V6,np.linalg.inv(T6));body=cap(35.1,-74.5,-10).fuse(cap(29.1,-10,.001));escape6=volume(local6.cut(body));assert escape6<1e-5
 sweep6=moved(cap(35.1,-174.5,-10).fuse(cap(29.1,-110,.001)),T6);ins6=inter(sweep6,L);assert ins6<1e-5
 # q6: link stays at Y<=51, wrist main Y>=55; its only rear annulus fits the fixed ring.
 pair_rear=moved(ann(28,25,-6.5,0).fuse(ann(28,24.9,-.1,0)),T6);rear_inter=inter(pair_rear,L);assert rear_inter<1e-5
 # Known J6 output free shafts sweep a circular band; do not infer unprovided internal thread states.
 out_free_band=moved(ann(23.5,20.5,-9,4.6).fuse(ann(24.84,19.16,4.6,7.6)),T6);out_band_inter=inter(out_free_band,L);assert out_band_inter<1e-5
 # q5 whole downstream exterior height: q6 rotation cannot exceed measured XZ corner bound.
 radial={}
 for n,sh in {**pair,'J7':V7}.items():
  b=np.array(bb(sh));radial[n]=max(math.hypot(x,z-J6[2]) for x,z in itertools.product([b[0,0],b[1,0]],[b[0,2],b[1,2]]))
 assert max(radial.values())<64.4
 #64.4 additionally covers PAIR known exterior screw/head bounds X<=39.1, Zrel<=51.1.
 downstream_min_z=J6[2]-64.4;assert downstream_min_z>0
 # Actual finite configurations are separate records, not the continuous proof.
 discrete=[]
 for q in [-100,-50,0,50,100]:
  for n,s in {**pair,'J7':V7}.items():
   v=inter(L,s.rotate(tuple(J6),tuple(J6+np.array([0,1,0])),q));assert v<1e-5;discrete.append(dict(q6_deg=q,moving=n,against='L56',intersection_mm3=v))
 for q in [-90,0,90]:
  movedL=L.rotate((0,0,0),(0,0,1),q)
  for n,v in vendors.items():
   if n.startswith('J5'):
    ivv=inter(movedL,v);assert ivv<1e-5;discrete.append(dict(q5_deg=q,moving='L56',against=n,intersection_mm3=ivv))
 # Beam/foot through-channel is real; no assumed right-angle continuation into J6.
 channel=cap(9,-8,114);channel_inter=inter(channel,L);assert channel_inter<1e-5
 service=moved(cap(40,-114.4,-74.4),T6);service_inter=inter(service,L);assert service_inter<1e-5
 # A specific R35/OD3.5 pure-geometry 90deg route, checked against actual vendor material.
 bend_pts=[cq.Vector(0,35*(1-math.cos(t)),120+35*math.sin(t)) for t in [0,math.pi/4,math.pi/2]]
 bend_wire=cq.Wire.assembleEdges([cq.Edge.makeThreePointArc(*bend_pts)])
 bend=cq.Workplane('XY',origin=(0,0,120)).circle(1.75).sweep(cq.Workplane().newObject([bend_wire]),isFrenet=True).val()
 bend_inter=inter(bend,V6);assert bend_inter>1

 ca5=sum(volume(L.intersect(v.translate((0,0,.0001))))/.0001 for v in V5.Solids());ca6=volume(L.intersect(V6.translate((0,.0001,0))))/.0001
 assert ca5>100 and ca6>100
 return dict(static=static,known_hardware=hp,hardware_pairs=hardware_pairs,tools=tools,known_hardware_sweeps=sweeps,J6_sweep_against_prior_J5_hardware=ordered,discrete_actual=discrete,contact_area_mm2={'J5_output':ca5,'J6_fixed':ca6},q5_continuous={'range_deg':[-90,90],'rear_subset_escape_mm3':escape,'rear_invariant_annulus_vendor_intersections_mm3':sv,'positive_material_halfspace':'All other original material Z>=0; downstream modules/wrist remain above J5 at any q6 in requested range. OEM internal output/thread states excluded.','future_J5_fixed_head_radial_clearance_mm':37-2.84-33,'future_fixed_bracket_not_designed':True,'actual_downstream_XZ_corner_radius_mm':radial,'known_hardware_inclusive_radius_bound_mm':64.4,'continuous_downstream_min_Z_mm':downstream_min_z},J5_aligned_insertion={'swept_rear_intersections_mm3':iv,'translations_from_seat_mm':[0,70],'beyond':'Skirt wholly Z>0; main original always Z>=0'},J6_aligned_insertion={'vendor_BREP_escape_from_two_cylinder_bound_mm3':escape6,'direction_from_seat':'-jointZ = -worldY','translations_mm':[0,100],'swept_bound_intersection_mm3':ins6,'beyond100':'All OEM world/link Y< -45, while L56 Y>=-38; separated'},q6_continuous={'range_deg':[-100,100],'link_max_Y_mm':bb(L)[1][1],'wrist_main_min_Y_mm':55,'invariant_rear_annulus_intersection_mm3':rear_inter,'known_output_shaft_sweep_intersection_mm3':out_band_inter,'skirt_to_carrier_radial_gap_mm':1.3,'skirt_to_fixed_head_radial_gap_mm':1.16,'scope':'External geometry with PAIR q7 in[-90,90]. No OEM internal partition certification, upstream J4/L45, actual head, cables or tolerance/elastic clearance.'},harness={'base_nominal_through_diameter_mm':18,'beam_inner_diameter_mm':34,'beam_inner_Z_mm':[8,114],'straight_18mm_probe_intersection_mm3':channel_inter,'underbody_gap_from_verified_bound_mm':119.9-114,'actual_J6_BREP_min_Z_mm':bb(V6)[0][2],'actual_J6_min_Z_minus_foot_mm':bb(V6)[0][2]-114,'explicit_bend_counterexample':{'centreline_radius_mm':35,'probe_diameter_mm':3.5,'start_link_mm':[0,0,120],'end_link_mm':[0,35,155],'formula':'[0,35*(1-cos(t)),120+35*sin(t)], t0..pi/2; starts along+Z, ends+Y','probe_volume_mm3':volume(bend),'actual_J6_intersection_mm3':bend_inter,'scope':'Pure geometric route, not selected cable; collision rejects only this explicit underbody turn, not every possible rear/side route.'},'J6_rear_reserved_radius_mm':40,'J6_rear_reserved_length_mm':40,'rear_reserve_intersection_mm3':service_inter,'minimum_rear_reserve_to_foot_Z_gap_mm':1,'example_quarter_bend_radius_mm':35,'example_bare_arc_height_deficit_mm':35-(119.9-114),'example_status':'Pure geometric R35 example, not a selected cable specification; ignores cable radius, thus only a necessary screen.','complete_internal_harness_verified':False,'reason':'5.9mm is planning gap to verified outer bound, not proof of actual material obstruction. Explicit R35/OD3.5 underbody route intersects actual J6 BREP; must develop rear/side path. No universal route infeasibility or preassembled18mm plug claim.'}),hardware

def rotY(q):
 t=math.radians(q);c,s=math.cos(t),math.sin(t);return np.array([[c,0,s],[0,1,0],[-s,0,c]])
def group(r,aa,M,F):
 P=np.array(polar(r,aa));P-=P.mean(0);S=P.T@P;gain=np.linalg.norm(P@np.linalg.inv(S),axis=1)
 return dict(S_mm2=S.tolist(),maximum_axial_increment_N=float(max(gain)*M*1000),direct_transverse_share_N=F/len(P),moment_Nm=M,force_N=F,assumption='Equal bolt stiffness and compatible compressed contact; no prying. Added axial load only, not preload or rated capacity.')

def mechanics(pr):
 ps=json.loads((PAIR/'study.json').read_text());pm=ps['mechanics'];g=9.80665
 down=[dict(id=r['id'],mass_kg=r['mass_kg'],p=np.array(r['com_pair_mm']),pre=r['preceding_joints']) for r in pm['body_rows']]
 down += [dict(id='J7_eRob70I_COM_proxy',mass_kg=.88,p=np.array([0,55,2.85]),pre=6),dict(id='head_budget_excluding_interface',mass_kg=1.5,p=np.array([0,55,135.]),pre=7),dict(id='net_payload',mass_kg=2,p=np.array([0,55,235.]),pre=7)]
 mass_down=sum(r['mass_kg'] for r in down);mass_total=mass_down+.88+pr['mass_if_6061_kg']
 C=pr['mass_if_6061_kg']*np.array(pr['com_link_mm'])+.88*np.array([0,22.85,155])+mass_down*J6
 D=np.zeros(3);eps=np.zeros(3)
 for r in down:
  p=r['p'].copy()
  if r['pre']==7:eps+=r['mass_kg']*np.array([p[0],p[1]-55,0]);p[0]=0;p[1]=55
  D+=r['mass_kg']*p
 A=C[0]*D[0]+C[2]*D[2];B=C[0]*D[2]-C[2]*D[0]
 angles=[-100.,100.,0.]+[math.degrees(math.atan2(B,A))+k*360 for k in range(-2,3) if -100<=math.degrees(math.atan2(B,A))+k*360<=100]
 rows=[]
 for q in sorted(set(angles)):
  vec=C+rotY(q)@D;rows.append(dict(q6_deg=q,first_moment_kg_mm=vec.tolist(),arbitrary_gravity_moment_Nm=g*(np.linalg.norm(vec)+np.linalg.norm(eps))/1000))
 worst=max(rows,key=lambda r:r['arbitrary_gravity_moment_Nm']);M=worst['arbitrary_gravity_moment_Nm'];F=mass_total*g
 # Exact radial bound in the permitted interval when extrema +/-90 lie inside. eps uses triangle bound.
 xa=math.hypot(D[0],D[2]);radial=math.hypot(abs(C[0])+xa,C[1]+D[1]);q5=g*(radial+np.linalg.norm(eps))/1000
 delta=pm['J7_COM_geometry_uncertainty_moment_increment_Nm']*2
 reserve=.1;reserveR=.260;Mplan=M+delta+reserve*g*reserveR;Fplan=F+reserve*g
 sampled=[]
 for q in np.arange(-100,101,1):
  for q7 in [-90,0,90]:
   tt=math.radians(q7);Rz=np.array([[math.cos(tt),-math.sin(tt),0],[math.sin(tt),math.cos(tt),0],[0,0,1]])
   mr=C+rotY(q)@(D+Rz@eps);sampled.append([int(q),q7,float(g*np.linalg.norm(mr)/1000),float(g*np.linalg.norm(mr[:2])/1000)])
 assert max(r[2] for r in sampled)<=M+1e-8 and max(r[3] for r in sampled)<=q5+1e-8
 I=math.pi*(40**4-34**4)/64;area=math.pi*(40**2-34**2)/4;length=96;E=69000
 tube={'OD_ID_mm':[40,34],'length_mm':length,'area_mm2':area,'I_mm4':I,'E_assumed_MPa':E,'section_sigma_indicator_MPa':Mplan*1000*20/I+Fplan/area,'selected_cantilever_deflection_mm':Mplan*1000*length**2/(2*E*I)+Fplan*length**3/(3*E*I),'condition':'A selected uniform tube under the entire J5 moment bound plus transverse force; intentionally double-counts some moment, still does not bound whole assembly deflection or local plate roots.'}
 P=group(27,A80,Mplan,Fplan)['maximum_axial_increment_N'];strip={'width_mm':8,'thickness_mm':4.4,'radial_span_mm':7,'force_N':P,'sigma_MPa':6*P*7/(8*4.4**2),'deflection_mm':4*P*7**3/(E*8*4.4**3),'condition':'Selected bolt-to-tube strip at output plate. Not actual annular plate FEA/contact redistribution.'}
 # A deliberately harsh thin-foot section proxy: at Y=0 the foot alone has two5mm side ligaments.
 foot_b=44-34;foot_t=10;foot_I=foot_b*foot_t**3/12
 foot={'foot_only_Y0_total_ligament_width_mm':foot_b,'plate_thickness_mm':foot_t,'I_for_bending_about_X_mm4':foot_I,'whole_J5_moment_normal_stress_indicator_MPa':Mplan*1000*(foot_t/2)/foot_I,'condition':'Assigns whole J5 moment to foot-only two ligaments; real load also spreads into tube/ring. Neither local-notch maximum nor globally conservative stress solution. Requires FEA/fillet verification.'}
 return dict(gravity_m_s2=g,payload_kg=2,head_budget_kg=1.5,head_budget_excludes_PAIR_interface=True,PAIR_interface_mass_kg=pm['interface_mass_with_known_hardware_kg'],PAIR_interface_world_COM_mm=pm['interface_com_world_mm'],PAIR_W01_mass_kg=next(r['mass_kg'] for r in pm['body_rows'] if r['id']=='W01'),J6_and_J7_motor_mass_each_kg=.88,head_COM_from_J7_output_mm=100,TCP_from_J7_output_mm=200,output_loaded_mass_kg=mass_total,J5_module_self_mass_excluded=True,C_kg_mm=C.tolist(),D_kg_mm=D.tolist(),q7_off_axis_first_moment_bound_kg_mm=float(np.linalg.norm(eps)),continuous_arbitrary_gravity_candidate_extrema=rows,worst_J5_output_moment_Nm=M,continuous_J5_axis_gravity_torque_bound_Nm=q5,force_N=F,two_motor_COM_geometry_uncertainty_Nm=delta,unknown_fine_hardware_budget_kg=reserve,unknown_hardware_radial_bound_from_J5_m=reserveR,planned_moment_with_COM_and_hardware_budget_Nm=Mplan,planned_force_N=Fplan,planned_J5_axis_torque_bound_Nm=q5+delta+reserve*g*reserveR,J5_bolt_group=group(27,A80,Mplan,Fplan),J6_fixed_screen=group(32,list(range(0,360,45)),pm['J6_zero_geometry_arbitrary_gravity_moment_Nm']+pm['J6_upstream_total_force_N']*.010+.88*g*.02215+delta+reserve*g*.12,pm['J6_upstream_total_force_N']+.88*g+reserve*g),tube=tube,output_plate_strip=strip,foot_ligament_proxy=foot,sampled_q6_q7_gravity_rows=sampled,not_validated=['Full OEM thread engagement and screw SKU/length','Source motor COM axes/rigid-body inertias','Static hold thermal guarantee; rated drive torque is not substitute','Metal certificate/preload/contact/FEA/fatigue/shock','Whole arm/cable geometry and complete head'])

def yzcs(s,x=0):
 # Break shared polyline endpoint aliases before reflection; each point flips once.
 q=s.rotate((0,0,0),(0,0,1),90)
 cs=json.loads(json.dumps(curves(section(q,'XZ',x),'XZ')))
 for r in cs:
  for k in ['p','q','c']:
   if k in r:r[k][0]*=-1
  if r['kind']=='ARC':r['start'],r['end']=(180-r['end'])%360,(180-r['start'])%360
 b=np.array(bb(s))
 for r in cs:
  for k in ['p','q']:
   if k in r:assert b[0,1]-.003<=r[k][0]<=b[1,1]+.003 and b[0,2]-.003<=r[k][1]<=b[1,2]+.003
 return cs

def shifted(cs,dy):
 out=json.loads(json.dumps(cs))
 for r in out:
  for k in ['p','q','c']:
   if k in r:r[k][1]+=dy
 return out
class Page(Sheet):
 def header(self,n,title,sub):
  self.text(14,282,'ODRADEK / R5-LINK56-EROB01',18);self.text(405,282,f'{n} / 5',10,align='right');self.text(14,271,title,12,BLUE);self.text(405,271,sub,8.4,align='right');self.line((14,266),(406,266),BLUE,.8)
 def footer(self,n):
  self.line((14,20),(406,20),GREY,.5);self.text(14,13,'mm / A3 | 名义金属结构候选 / 无电无载试装 | 非生产放行、非整臂操作域认证',8);self.text(406,13,f'2026-09-28 / {n}',8,align='right')

def drawings(L,pair,S):
 views={'BASE_Z4.8':curves(section(L,'XY',4.8),'XY'),'SIDE_X0':yzcs(L),'J6_FRONT_Y50.9':curves(section(L,'XZ',50.9),'XZ'),'BASE_BACK_Z.1':curves(section(L,'XY',.1),'XY')}
 d=ezdxf.new('R2013');d.units=4;d.header['$INSUNITS']=4
 for l,col in [('BOUNDARY',7),('NOTE',3),('DIM',2)]:d.layers.new(l,dxfattribs={'color':col})
 m=d.modelspace()
 for i,(n,cs) in enumerate(views.items()):dxf_geometry(m,cs,(i*160,0));m.add_text(n,dxfattribs={'height':2.5,'insert':(i*160-40,205),'layer':'NOTE'})
 notes=['R5-LINK56-EROB01 / mm / original candidate, NOT PRODUCTION RELEASE','O=J5, world(0,-55,485); J6=(0,55,155), axisY, clocking+15deg','BASE OD76 Z0..8 / rear OD66 ID60+0..019 Z-8..0, C.3 and innerR.1','CentreID18; rear ID49 depth.3 / 12 factory head clearances ID5.3 depth.5','16xID3.4 PCD54 nonuniform: CSV / CB6.2depth3.4, underheadC.2','Closed tube OD40 ID34 Z8..104; ID34 continues through foot toZ114','Foot X+/-22, Y-20..51, Z104..114; wallX+/-18,Y45..51,Z104..135','J6 ring OD78 ID58.6, localz-10..-4; 8xID3.4 PCD64, frontC.2','Tube-base outsideR2; foot-wall innerR1.5; other edges sharp nominal','OEM M3x.35 exact length/SKU/full thread TBD; do not replace withM3x.5']
 for i,n in enumerate(notes):m.add_text(n,dxfattribs={'height':2.1,'insert':(-40,-60-4*i),'layer':'NOTE'})
 dxp=OUT/'DXF/ODR-L56-E01.dxf';d.saveas(dxp);rr=ezdxf.readfile(dxp);assert not rr.audit().has_errors
 pdf=OUT/'ODR-R5-LINK56-EROB01.pdf';c=canvas.Canvas(str(pdf),pagesize=landscape(A3));s=Page(c)
 s.header(1,'细长闭口梁 / 原点与轴保持','侧剖0.75:1；灰框为源已核外包络，非厂商CAD投影')
 for sh,col in [(L,BLUE),*[(v,'#6F824C') for v in pair.values()]]:s.geo(yzcs(sh),(117,84),.75,col,.8)
 for x,z,w,h in [(-40,-67.5,80,67.5),(-19.5,119.9,64.5,70.2),(45,125.9,10,58.2),(74.9,115.5,70.2,64.5),(80.9,180,58.2,10)]:
  a=(117+x*.75,84+z*.75);b=(117+(x+w)*.75,84+(z+h)*.75)
  for p,q in [(a,(b[0],a[1])),((b[0],a[1]),b),(b,(a[0],b[1])),((a[0],b[1]),a)]:s.line(p,q,GREY,.35,[4,2])
 s.dim_h(117,158.25,246,84,200.25,'55');s.dim_v(84,200.25,239,158.25,'155')
 s.geo([dict(kind='ARC',c=[35,120],r=35,start=90,end=180)],(117,84),.75,'#B4443C',1.2);s.text(16,153,'红：R35路径反例，实CAD干涉',9,'#B4443C');s.text(17,250,'+Y横向 / +Z竖向；link原点=J5',10,BLUE);s.text(122,77,'J5 +Z',9);s.text(167,205,'J6 +Y',9)
 s.text(280,249,'不变的布局',11,BLUE);s.rows(280,237,['J5 world (0,−55,485)，轴+Z','J6 world (0,0,640)，轴+Y','J7 world (0,55,675)，轴+Z','J5数学±90° / J6 ±100°','消费PAIR01：J6安装clocking+15°','本阶段不改整臂、PAIR或旧RH','J5候选80I V6 / J6候选70I V5','原生EtherCAT、带闸配置仍候选','主梁Ø40、壁3；安装环Ø78','Ø18仅轴孔，非完整动态束认证'],7,8.9)
 s.rows(280,153,['承力路径：','J5输出盘 → R2圆根 → 闭口管','→ 上托板/立壁 → J6固定前环','→ 原PAIR01与可拆头','所有并集为一个有效原创实体','无悬空梁端、未加轴间距','J6后端R40×40空域未被梁遮挡','该预留不是已验证配对插头'],7,8.9)
 s.rows(16,29,[f"金属候选质量 {S['parts']['L56-E01']['mass_if_6061_kg']*1000:.2f}g；材料仅6061-T6候选，实际材料/预紧/疲劳未放行。"],7,9)
 s.footer(1);c.showPage()
 s.header(2,'L56-E01 / 完整名义形状与根部孔阵','底盘XY 1.7:1；侧剖0.85:1；全部尺寸为真值')
 s.geo(views['BASE_Z4.8'],(92,189),1.7);s.axes((92,189),40,1.7);s.dim_h(27.4,156.6,258,189,189,'Ø76')
 s.geo(views['SIDE_X0'],(271,76),.85)
 s.dim_v(82.8,164.4,327,288,'96 管段Z8…104');s.dim_v(164.4,172.9,339,314,'10 托板')
 s.dim_h(254,288,65,82.8,82.8,'Ø40 / ID34');s.lead((288,84.5),(321,105),(335,105),'管根外R2')
 s.rows(15,102,['底盘：OD76、Z0…8；后裙OD66/母止口Ø60+0.019/0，Z−8…0，入口C0.3/内根R0.1。',
 '中心Ø18贯通；后面Ø49×0.3禁止承力避空，以手册d值为准；不套用图中另一Ø46.4。',
 '16×Ø3.4、PCD54非均布；前沉孔Ø6.2深3.4（底Z4.6），沉孔底内口C0.2。',
 '12×Ø5.3×0.5浅避空让开原厂齐平螺钉；禁止将这些原厂头当安装孔或拆掉。',
 '闭口圆管OD40/ID34，Z8…104；ID34向上贯通托板至Z114；与底盘有真实R2外根。',
 '托板X−22…22、Y−20…51、Z104…114；立壁X−18…18、Y45…51、Z104…135。',
 '立壁/托板内根R1.5；J6中心沿+Y(55)、+Z(155)，环和立壁共用ID58.6贯通避空。',
 '未画倒角/圆角不默认为存在；建议关键厚度±0.05、普通外形±0.10，孔位Ø0.10仅为试制目标。'],7,8.7)
 s.footer(2);c.showPage()
 s.header(3,'J6固定前环与孔中心坐标','J6正面XZ 1.4:1；孔表为非镜像link坐标')
 s.geo(shifted(views['J6_FRONT_Y50.9'],-155),(95,193),1.4);s.axes((95,193),41,1.4);s.dim_h(40.4,149.6,256,193,193,'Ø78 / ID58.6')
 s.text(184,249,'J5输出孔 / link X,Y / PCD54',10,BLUE)
 for i,(aa,xy) in enumerate(zip(A80,polar(27,A80))):s.text(184,237-i*6,f'{i+1:2d}  {xy[0]:+.6f}  {xy[1]:+.6f}  {aa}°',8.4)
 s.text(307,249,'J6固定孔 / link X,Z',10,BLUE)
 for i,xy in enumerate(polar(32,range(0,360,45))):
  pt=(T6@np.r_[xy,-10,1])[:3];s.text(307,237-i*7,f'{i+1}  {pt[0]:+.6f} / {pt[2]:.6f}',8.4)
 s.rows(307,171,['8孔PCD64，每45°','随J6本地坐标安装+15°','环背面Y45 / 头侧Y51','8×Ø3.4贯通厚6，前C0.2','固定头从Y51到54','PAIR主盘自Y55起','后裙R28，固定环R29.3','头内缘R29.16；名义余量1.16'],7,8.6)
 s.rows(15,112,['原厂80I V6统一frame：X=nativeY、Y=nativeZ、Z=nativeX−32.9235811105；proper rotation。',
 '70I V5的原厂输出反向，不能沿用80I变换；此处严格继承PAIR01已核frame与+15°安装角。',
 '80I真Ø60定位段Z−10.2…−5.3；本件前薄输出跨过后扣8，扣除C0.3后真实圆柱搭接约2.4。',
 'J5安装需16颗M3×0.35，J6固定需8颗M3×0.35，12.9黑氧化；精确长度/SKU仍TBD。',
 '手册输出最小完整牙3.0、70I固定最小4.5；已知自由杆J5为9.6、J6为22.5，不是订货长度。',
 'STEP光滑孔或螺纹样貌、2D简写深度均不能替代完整牙起止；普通M3×0.5不能默认替代。'],7,8.9)
 s.footer(3);c.showPage()
 s.header(4,'装配、连续局部几何与真实走线边界','供应商所有实体参与；完整内线束/公差未放行')
 s.text(15,251,'可连贯的无载装拆顺序',11,BLUE);s.rows(15,239,['1. 独立承托J5/J6，断电；将L56沿−Z套入J5输出。','2. 在J6尚未装入时，经底盘外侧通道装16颗J5螺钉。','3. J6从自身后方−Y位置向+Y推入，前鼻穿过固定环。','4. 从J6前方+Y装8颗固定螺钉；此时未装PAIR W01。','5. 按冻结PAIR顺序装W01、J7、A01-P与H01。','6. 先卸载、断电、解绑线束，再反向拆卸。','工具Ø5.8×60只是直向空间探针；真实工具型号待选。','已知自由段+头包络连续装入核查，不隐去未知完整牙段。'],7,9)
 s.text(220,251,'连续证明，不等同离散样本',11,BLUE);s.rows(220,239,['J5：其余原创材料Z≥0，后裙环轴对称。','真实后裙被环状扫掠包含，与5个OEM实体零相交。','J6装入：完整OEM包含于R35.1后体/R29.1前鼻。','后移0…100扫掠零穿透，更远Y平面完全分离。','q6±100：L56 Y≤51，PAIR主材Y≥55。','唯一相交轴向带是R≤28后裙，已核环状扫掠。','q7±90：继承PAIR真实包含；不新增整头认证。','原厂内部转子/牙段、上游J4/L45不在范围内。'],7,9)
 H=S['checks']['harness'];s.text(15,165,'通道事实与失败边界',11,BLUE);s.rows(15,153,[f"J5至梁顶存在连续Ø18直向几何通道；管腔ID34、Z8…114。原厂轴孔仍是Ø18瓶颈。",
 f"托板Z114，J6实CAD包含体最低Z119.9；下方净高仅{H['underbody_gap_from_verified_bound_mm']:.1f}mm。",
 '若将R35圆弧完全限制在该规划薄缝内，忽略线半径也差29.1mm；此尺寸筛查不等同真实材质碰撞。',
 f"另查R35/Ø3.5路径：从(0,0,120)沿+Z转向(0,35,155)+Y，与实际J6 BREP相交{H['explicit_bend_counterexample']['actual_J6_intersection_mm3']:.3f}mm³。",
 '只否定上述具体转线，不推论所有路线无解；需后向/侧舱路径，不给GMSL+电源/EtherCAT全束通过结论。',
 'J6后方预留R40×40，与L56零相交，离托板最小Z余量1mm；它不是配对插头或弯线模型。',
 '原厂后端插座体已在STEP内，但前端孔与后端端口的角向关系未固定，不能根据截图冻结线序/clocking。',
 '完整接头外壳通过、穿后再装壳、卡扣可达、服务弯曲/扭转及外罩都还需要独立设计。',
 '本阶段保持物理失败边界可复算，不能用大通孔或某一静态间隙宣布内走线完成。'],7,9)
 s.footer(4);c.showPage()
 s.header(5,'负载、材料质量与无载打印样件','2kg净物体；1.5kg头预算不含PAIR接口；静力条件比较')
 M=S['mechanics'];s.rows(15,251,[f"L56原创金属{S['parts']['L56-E01']['mass_if_6061_kg']*1000:.3f}g；PAIR W01 {M['PAIR_W01_mass_kg']*1000:.3f}g；PAIR接口+已列硬件{M['PAIR_interface_mass_kg']*1000:.3f}g。",
 f"另计J6/J7各0.88kg；J5自身质量由上游承担。本输出加载质量{M['output_loaded_mass_kg']:.6f}kg，不含未知细牙件。",
 f"物体+200/头COM+100从J7 OEM面计；q6±100与q7±90的静力矩界{M['worst_J5_output_moment_Nm']:.5f}Nm，J5轴矩界{M['continuous_J5_axis_gravity_torque_bound_Nm']:.5f}Nm。",
 f"两电机COM几何不确定性加{M['two_motor_COM_geometry_uncertainty_Nm']:.5f}Nm；再给未知细牙件0.10kg/0.26m预算。",
 f"规划筛查M={M['planned_moment_with_COM_and_hardware_budget_Nm']:.5f}Nm、F={M['planned_force_N']:.5f}N；不是2kg工作额定或真实试验。"],7,9)
 s.rows(15,205,[f"J5 16颗非均布螺钉：最大附加轴力{M['J5_bolt_group']['maximum_axial_increment_N']:.3f}N；不含预紧、撬力和螺纹剥离。",
 f"Ø40/34管截面I={M['tube']['I_mm4']:.1f}mm4；条件截面σ={M['tube']['section_sigma_indicator_MPa']:.3f}MPa，选定悬臂δ={M['tube']['selected_cantilever_deflection_mm']:.5f}mm。",
 f"主盘8×4.4×7条带指标σ={M['output_plate_strip']['sigma_MPa']:.3f}MPa；托板仅两5mm韧带承全矩代理={M['foot_ligament_proxy']['whole_J5_moment_normal_stress_indicator_MPa']:.2f}MPa。",
 '条带/韧带都不是整体FEA解；管根、托板跨孔分流、环板和3mm裙的接触/缺口/疲劳仍须验证。',
 '原厂31Nm额定、70Nm启停值不等于本机狭窄结构的连续零速热保证；不据此放行停止/制动。'],7,9)
 s.text(15,161,'打印只验证几何',11,BLUE);s.rows(15,149,['L56-G：母止口Ø60.4、中心Ø18.4、后避空Ø49.2深0.5、OEM孔Ø3.8、J6环ID58.8；其余轮廓保留。',
 'PLA/PETG；打印姿态沿link+Z、Tz+8落床，整体高202mm，所需支撑另计。',
 '底盘悬伸、上托板与固定环需要可拆支撑；先打孔径/止口试片，仅补局部孔，不整体缩放。',
 '必须独立托住关节本体；塑件只试合/检查孔和工具，不承担0.88kg模块自重，更不能挂真实头或工件。',
 'STEP重读为有效单实体；所有STL水密/方向/体积与bbox偏差已记录。',
 '下一步为供应商受控完整牙/螺钉、实际工具/插头、加工公差/材料/预紧、FEA/疲劳与完整线道。'],7,9)
 s.footer(5);c.save();assert len(PdfReader(pdf).pages)==5
 return dict(file=pdf.name,sha256=sha(pdf),pages=5),dict(file=str(dxp.relative_to(OUT)),sha256=sha(dxp),units_mm=True,audit_errors=0)

def dimensional_recheck(S):
 # Re-read exported STEP; recover actual cylindrical hole axes independently of the builder.
 shape=cq.importers.importStep(str(OUT/'STEP/L56-E01.step')).val()
 def holes(sh,radius,pcd):
  out=[]
  for face in sh.Faces():
   a=BRepAdaptor_Surface(face.wrapped)
   if a.GetType()!=GeomAbs_Cylinder:continue
   cy=a.Cylinder();d=cy.Axis().Direction();v=cy.Location()
   if abs(cy.Radius()-radius)<1e-5 and abs(d.Z())>.999999 and abs(math.hypot(v.X(),v.Y())-pcd)<1e-5:out.append([v.X(),v.Y()])
  return sorted(set(tuple(round(v,6) for v in p) for p in out))
 j5=holes(shape,1.7,27);j6=holes(moved(shape,np.linalg.inv(T6)),1.7,32)
 assert len(j5)==16 and len(j6)==8
 for got,expected in [(j5,polar(27,A80)),(j6,polar(32,range(0,360,45)))]:assert max(min(math.dist(a,b) for b in expected) for a in got)<1e-6
 C=np.array(S['mechanics']['C_kg_mm']);D=np.array(S['mechanics']['D_kg_mm']);eps=S['mechanics']['q7_off_axis_first_moment_bound_kg_mm']
 rng=np.random.default_rng(5601);qs=np.deg2rad(rng.uniform(-100,100,200001));V=np.column_stack([C[0]+np.cos(qs)*D[0]+np.sin(qs)*D[2],np.full(len(qs),C[1]+D[1]),C[2]-np.sin(qs)*D[0]+np.cos(qs)*D[2]])
 bound=9.80665*(np.linalg.norm(V,axis=1)+eps)/1000;assert bound.max()<=S['mechanics']['worst_J5_output_moment_Nm']+1e-10
 assert len(yzcs(shape))>10
 return dict(step_sha256=sha(OUT/'STEP/L56-E01.step'),method='Exported BREP cylindrical-axis recovery plus seeded random check; sampling does not replace analytic proof.',J5_actual_3p4_hole_axes_linkXY_mm=j5,J6_actual_3p4_hole_axes_localXY_mm=j6,counts=[16,8],seed=5601,random_sample_count=len(qs),random_max_arbitrary_gravity_bound_Nm=float(bound.max()),analytic_bound_Nm=S['mechanics']['worst_J5_output_moment_Nm'],re_read_bbox_mm=bb(shape),side_section_line_points_inside_real_BREP_bbox=True)

def core_hash():
 funcs=[inter,props,build,export,extraction,pair_originals,check_geometry,rotY,group,mechanics,dimensional_recheck]
 return hashlib.sha256((''.join(inspect.getsource(f) for f in funcs)+repr(T6.tolist())+repr(T7.tolist())+repr(A80)+repr(REL80)+''.join(sha(p) for p in [SRC,ROOT/'engineering/r5_wrist_pair01.py',PAIR/'study.json',ROOT/'engineering/build_layout.py',ROOT/'engineering/r5_wrist_erob01.py'])).encode()).hexdigest()
def manifest():
 js(OUT/'manifest.json',{'revision':'R5-LINK56-EROB01','outputs':[dict(path=str(p.relative_to(OUT)),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['manifest.json','visual-qa.json'] and p.suffix!='.png']})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--vendor80-step',type=Path);ap.add_argument('--vendor70-step',type=Path);ap.add_argument('--private-preview-dir',type=Path);ap.add_argument('--redraw',action='store_true');args=ap.parse_args()
 for d in ['STEP','STL','DXF']:(OUT/d).mkdir(parents=True,exist_ok=True)
 pdfmetrics.registerFont(TTFont('CN','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
 if args.redraw:
  S=json.loads((OUT/'study.json').read_text());assert S['core_hash']==core_hash();p=OUT/'STEP/L56-E01.step';assert sha(p)==S['parts']['L56-E01']['step_sha256'];L=cq.importers.importStep(str(p)).val();S['source_hashes'][0]['sha256']=sha(__file__);S['pdf'],S['dxf']=drawings(L,pair_originals(),S);js(OUT/'study.json',S);manifest();return
 src=json.loads(SRC.read_text())
 for p,id in [(args.vendor80_step,'vendor80_step'),(args.vendor70_step,'vendor70_step')]:assert p and sha(p)==next(x['sha256'] for x in src['sources'] if x['id']==id)
 arm=json.loads((ROOT/'engineering/generated/raised-arm-integration01/model.json').read_text())['arm']['joints']
 assert arm[4]['origin_mm']==ORIGIN.tolist() and arm[4]['axis']==[0,0,1] and arm[5]['origin_mm']==(ORIGIN+J6).tolist() and arm[5]['axis']==[0,1,0]
 V5=cq.importers.importStep(str(args.vendor80_step)).val().rotate((0,0,0),(1,1,1),-120).translate((0,0,-X80))
 v70=cq.importers.importStep(str(args.vendor70_step)).val().rotate((0,0,0),(1,1,-1),120).translate((0,0,X70));V6=moved(v70,T6);V7=moved(v70,T7)
 assert len(V5.Solids())==5 and all(s.isValid() for s in V5.Solids())
 js(OUT/'vendor80-interface-extraction.json',extraction(V5));L=build();G=build(True);parts={'L56-E01':export('L56-E01',L),'L56-G':export('L56-G',G)}
 gp=OUT/'STL/L56-G-print-oriented.stl';cq.exporters.export(G.translate((0,0,8)),str(gp),tolerance=.01,angularTolerance=.05);gm=trimesh.load(gp,force='mesh',process=True);assert gm.is_watertight and gm.is_winding_consistent and abs(gm.bounds[0,2])<1e-5
 pair=pair_originals();print('Shapes exported',flush=True);checks,hw=check_geometry(L,V5,V6,V7,pair);print('Geometry checks passed',flush=True)
 mech=mechanics(parts['L56-E01']);js(OUT/'part-placements.json',{'revision':'R5-LINK56-EROB01','frame_origin_world_mm':ORIGIN.tolist(),'parts':[dict(id='L56-E01',**props(L))]})
 with (OUT/'hole-coordinates.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['group','index','x_link_mm','y_link_mm','z_link_mm','diameter_mm','note'])
  for name,aa,r,z,T,diam,note in [('J5_OUTPUT',A80,27,0,np.eye(4),3.4,'CB6.2x3.4 bottomz4.6; C.2'),('J5_FACTORY_RELIEF',REL80,27,0,np.eye(4),5.3,'rear depth.5; not mounting holes'),('J6_FIXED',list(range(0,360,45)),32,-10,T6,3.4,'THRU6 frontC.2')]:
   for i,xy in enumerate(polar(r,aa)):w.writerow([name,i+1,*(T@np.r_[xy,z,1])[:3],diam,note])
 with (OUT/'gravity-sampled-check.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['q6_deg','q7_deg','J5_moment_Nm','J5_axis_torque_bound_Nm']);w.writerows(mech.pop('sampled_q6_q7_gravity_rows'))
 hashes=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in [Path(__file__),SRC,ROOT/'engineering/r5_wrist_pair01.py',ROOT/'engineering/r5_wrist_erob01.py',ROOT/'engineering/build_layout.py',ROOT/'engineering/draw_central_display01.py',ROOT/'engineering/generated/raised-arm-integration01/model.json',PAIR/'study.json',PAIR/'STEP/W01.step',PAIR/'STEP/A01-P.step',PAIR/'STEP/H01-reuse.step']]
 S=dict(revision='R5-LINK56-EROB01',status='conditional original geometry candidate, no manufacturing release',license='CC-BY-NC-4.0',source_hashes=hashes,core_hash=core_hash(),frames={'link_origin_world_mm':ORIGIN.tolist(),'J6_in_link':T6.tolist(),'J7_in_link':T7.tolist(),'J5_limit_deg':[-90,90],'J6_limit_deg':[-100,100],'PAIR_q7_limit_deg':[-90,90]},parts=parts,print_oriented={'file':str(gp.relative_to(OUT)),'sha256':sha(gp),'bbox_mm':gm.bounds.tolist(),'watertight':bool(gm.is_watertight),'winding_consistent':bool(gm.is_winding_consistent)},checks=checks,mechanics=mech,section_nonlinear_curve_chordal_target_mm=.002)
 js(OUT/'study.json',S);js(OUT/'dimension-qa.json',dimensional_recheck(S));S['pdf'],S['dxf']=drawings(L,pair,S);js(OUT/'study.json',S)
 pub=cq.Assembly();pub.add(L,name='L56_E01')
 for n,s in pair.items():pub.add(s,name=n)
 pub.save(str(OUT/'STEP/ORIGINAL-context-assembly.step'))
 if args.private_preview_dir:
  args.private_preview_dir.mkdir(parents=True,exist_ok=True);ass=cq.Assembly()
  for n,s in {'L56':L,**pair,**{f'J5_solid{i+1}':s for i,s in enumerate(V5.Solids())},'J6':V6,'J7':V7,**hw}.items():ass.add(s,name=n)
  ass.save(str(args.private_preview_dir/'PRIVATE-with-vendor.step'))
 manifest();print(json.dumps({'mass':parts['L56-E01']['mass_if_6061_kg'],'com':parts['L56-E01']['com_world_mm'],'contacts':checks['contact_area_mm2'],'M':mech['worst_J5_output_moment_Nm'],'q5':mech['continuous_J5_axis_gravity_torque_bound_Nm'],'Mplanned':mech['planned_moment_with_COM_and_hardware_budget_Nm'],'tube':mech['tube'],'foot':mech['foot_ligament_proxy']},indent=2),flush=True)
if __name__=='__main__':main()
