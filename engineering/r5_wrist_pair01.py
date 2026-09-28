# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-WRIST-PAIR01. Original eRob70I V5 J6/J7 elbow and thin-skirt A01-P.
All geometry mm. Real OEM STEP remains private, supplied by command line and hashed.
No original arm, WRIST01, or vendor geometry is changed. Not a production release.
"""
from pathlib import Path
import argparse, hashlib, json, math, csv, itertools, inspect
import cadquery as cq
import numpy as np
import trimesh, ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from r5_wrist_erob01 import cyl,cone,polar,OEM_ANGLES,OEM_RELIEF_ANGLES,HEAD_ANGLES,X0,adapter,mate,bb,volume
from build_layout import frame,moved
from draw_central_display01 import section,curves as analytic_curves,dxf_geometry,Sheet,INK,BLUE,GREY
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-wrist-pair01'
SRC=ROOT/'docs/engineering/sources/r5-wrist-pair01.json'
RHO=2.7e-6
ORIGIN=np.array([0.,0.,640.])
Q=np.eye(4);t=math.radians(15);Q[:3,:3]=[[math.cos(t),-math.sin(t),0],[math.sin(t),math.cos(t),0],[0,0,1]]
T6=frame([0,0,0],[0,1,0])@Q
T7=frame([0,55,35],[0,0,1])

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def curves(edges,plane):
 out=[];ix=[0,1] if plane=='XY' else [0,2]
 for e in edges:
  try:out.extend(analytic_curves([e],plane))
  except ValueError:
   ad=BRepAdaptor_Curve(e.wrapped);sam=GCPnts_QuasiUniformDeflection(ad,.002);assert sam.IsDone()
   pts=[[sam.Value(i).Coord()[j] for j in ix] for i in range(1,sam.NbPoints()+1)]
   out.extend(dict(kind='LINE',p=a,q=b) for a,b in zip(pts,pts[1:]))
 return out
def js(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def matrix_props(s):
 p=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,p)
 return np.array([[p.MatrixOfInertia().Value(i,j) for j in range(1,4)] for i in range(1,4)])
def cap(r,z0,z1,xy=(0,0)):return cyl(r,z0,z1-z0,xy)
def ann(ro,ri,z0,z1):return cap(ro,z0,z1).cut(cap(ri,z0-.01,z1+.01))
def contact(a,b,d):return volume(a.intersect(b.translate(tuple(np.array(d)*1e-4))))/1e-4

def yoke(gauge=False):
 bore=25.2 if gauge else 25
 a=cyl(38,0,8).fuse(cyl(28,-6.5,6.5)).cut(cyl(bore,-6.51,6.51))
 a=a.fillet(.1,[e for e in a.Edges() if abs(e.Length()-2*math.pi*bore)<1e-5 and abs(e.Center().z)<1e-5])
 a=a.cut(cone(bore+.3,bore,-6.5,.3)).cut(cyl(9.2 if gauge else 9,-7,16)).cut(cyl(19.6 if gauge else 19.5,-.01,.51 if gauge else .31))
 for xy in polar(22,OEM_ANGLES):
  r=1.9 if gauge else 1.7
  a=a.cut(cyl(r,-.01,8.02,xy)).cut(cyl(3.1,4.6,3.41,xy)).cut(cone(r,r+.2,4.4,.2,xy))
 for xy in polar(22,OEM_RELIEF_ANGLES):a=a.cut(cyl(2.8,-.01,.51,xy))
 a=moved(a,T6)
 a=a.fuse(moved(ann(39,29.4 if gauge else 29.3,-10,-4),T7))
 a=a.fuse(cq.Solid.makeBox(28,16,5,cq.Vector(-14,8,26)))
 for x in [-12,9]:
  a=a.fuse(cq.Workplane('YZ').workplane(offset=x).polyline([(8,10),(8,26),(18,26)]).close().extrude(3).val())
 for xy in polar(32,range(0,360,45)):
  r=1.9 if gauge else 1.7
  a=a.cut(moved(cyl(r,-10.01,6.02,xy).fuse(cone(r,r+.2,-4.2,.2,xy)),T7))
 return a.clean()

def a01p(gauge=False):
 return adapter(gauge).cut(ann(30.01,28,-6.51,0)).clean()

def original_props(name,s):
 p=OUT/'STEP'/(name+'.step');f=OUT/'STL'/(name+'.stl')
 cq.exporters.export(s,str(p));cq.exporters.export(s,str(f),tolerance=.01,angularTolerance=.05)
 r=cq.importers.importStep(str(p)).val();m=trimesh.load(f,force='mesh',process=True)
 I=matrix_props(s)*RHO*1e-6
 d=dict(step_sha256=sha(p),stl_sha256=sha(f),valid=s.isValid(),solids=len(s.Solids()),volume_mm3=volume(s),bbox_mm=bb(s),mass_6061_candidate_kg=volume(s)*RHO,com_mm=list(s.Center().toTuple()),inertia_at_com_kg_m2=I.tolist(),density_assumption_kg_m3=2700,step_volume_relative_error=abs(volume(r)-volume(s))/volume(s),mesh_watertight=bool(m.is_watertight),mesh_winding_consistent=bool(m.is_winding_consistent),mesh_volume_relative_error=abs(m.volume-volume(s))/volume(s),mesh_bbox_max_error_mm=float(np.max(np.abs(m.bounds-np.array(bb(s))))),export_tolerance_mm=.01,export_angular_tolerance_rad=.05)
 assert d['valid'] and d['solids']==1 and d['mesh_watertight'] and d['mesh_winding_consistent'] and d['step_volume_relative_error']<1e-8 and d['mesh_volume_relative_error']<.001 and d['mesh_bbox_max_error_mm']<.02
 return d

def oem_features(v):
 out=[];planes=[]
 for i,f in enumerate(v.Faces()):
  ad=BRepAdaptor_Surface(f.wrapped);b=bb(f)
  if ad.GetType()==GeomAbs_Cylinder:
   c=ad.Cylinder();p=c.Location();d=c.Axis().Direction()
   if abs(d.Z())>.999999 and abs(math.hypot(p.X(),p.Y())-32)<.001:
    out.append(dict(face_index=i,radius_mm=c.Radius(),xy_mm=[p.X(),p.Y()],z_interval_mm=[b[0][2],b[1][2]]))
  elif ad.GetType()==GeomAbs_Plane:
   p=ad.Plane();d=p.Axis().Direction()
   if abs(d.Z())>.999999 and abs(p.Location().Z()+10)<1e-6:
    planes.append(dict(face_index=i,area_mm2=f.Area(),z_mm=p.Location().Z(),bbox_mm=b))
 free=[r for r in out if abs(r['radius_mm']-1.75)<1e-6 and abs(r['z_interval_mm'][1]+10)<1e-6]
 assert len(free)==8
 for xy in polar(32,range(0,360,45)):assert min(math.dist(xy,r['xy_mm']) for r in free)<1e-6
 return dict(fixed_contact_z_mm=-10,fixed_pcd_mm=64,fixed_angles_deg=list(range(0,360,45)),fixed_free_channel_mm=[-26.5,-10],fixed_free_channel_diameter_mm=3.5,cylinder_evidence=out,contact_plane_evidence=planes,thread_full_start_end='Unknown. Smooth CAD bores are not complete thread evidence.')

def collision_and_motion(parts,v):
 Y=parts['W01'];A=moved(parts['A01-P'],T7);H=moved(parts['H01-reuse'],T7)
 V6,V7=moved(v,T6),moved(v,T7)
 actual={'W01':Y,'A01-P':A,'H01':H,'J6_OEM':V6,'J7_OEM':V7}
 static=[]
 for (n,a),(m,b) in itertools.combinations(actual.items(),2):
  val=volume(a.intersect(b));static.append(dict(a=n,b=m,intersection_mm3=val));assert val<1e-5
 # Explicit known free shaft plus max head; missing full thread segments are NOT omitted silently.
 hardware={};hp=[]
 for group,xylist,z0,seat,T in [('J6_OUT',polar(22,OEM_ANGLES),-9,4.6,T6),('J7_FIXED',polar(32,range(0,360,45)),-26.5,-4,T7),('J7_OUT',polar(22,OEM_ANGLES),-9,4.6,T7)]:
  for i,xy in enumerate(xylist):
   sh=moved(cap(1.5,z0,seat,xy).fuse(cap(2.84,seat,seat+3,xy)),T)
   hardware[f'{group}_{i+1}']=sh
   vals={n:volume(sh.intersect(o)) for n,o in actual.items()};assert max(vals.values())<1e-5
   hp.append(dict(id=f'{group}_{i+1}',modeled_free_shaft_length_mm=seat-z0,head_max_diameter_height_mm=[5.68,3],intersection_mm3=vals,complete_fastener=False))
 for i,xy in enumerate(polar(32,HEAD_ANGLES)):
  sh=moved(cap(2,-.35,12,xy).fuse(cap(3.61,12,16,xy)),T7);hardware[f'HEAD_SNS_M4_12_{i+1}']=sh
  vals={n:volume(sh.intersect(o)) for n,o in actual.items()};assert max(vals.values())<1e-5
  hp.append(dict(id=f'HEAD_SNS_M4_12_{i+1}',modeled_length_mm=12.35,head_max_diameter_height_mm=[7.22,4],intersection_mm3=vals,complete_exterior_envelope=True))
 pairs=[]
 for (n,a),(m,b) in itertools.combinations(hardware.items(),2):
  val=volume(a.intersect(b));assert val<1e-5;pairs.append(dict(a=n,b=m,intersection_mm3=val))
 tools=[]
 for group,xylist,r,z,T,obs in [('J6_OUT',polar(22,OEM_ANGLES),2.9,4.6,T6,{'W01':Y,'J6':V6}),('J7_FIXED',polar(32,range(0,360,45)),2.9,-4,T7,{'W01':Y,'J6':V6,'J7':V7}),('J7_OUT',polar(22,OEM_ANGLES),2.9,4.6,T7,{'W01':Y,'J6':V6,'J7':V7,'A01-P':A}),('HEAD',polar(32,HEAD_ANGLES),3.9,12,T7,actual)]:
  for i,xy in enumerate(xylist):
   pr=moved(cap(r,z+.001,z+60,xy),T);vals={n:volume(pr.intersect(o)) for n,o in obs.items()};assert max(vals.values())<1e-5
   tools.append(dict(id=f'{group}_{i+1}',diameter_mm=2*r,length_mm=60,intersection_mm3=vals,selected_tool=False))
 # Vendor BREP, INCLUDING every exported connector body, lies in this two-cylinder set.
 bound=cap(35.1,-74.5,-10).fuse(cap(29.1,-10,.001));escape=volume(v.cut(bound));assert escape<1e-5
 # All insertion distances d>=0 along -Z, not just samples: lower cylinder stops at contact plane;
 # upper nose passes the clearance hole. 100mm sufficient to become wholly below this yoke.
 ins=moved(cap(35.1,-174.5,-10).fuse(cap(29.1,-110,.001)),T7)
 vi={n:volume(ins.intersect(o)) for n,o in {'W01':Y,'J6':V6}.items()};assert max(vi.values())<1e-5
 # Reverse reference: old 60mm skirt versus actual new fixed screws, proves scope correction.
 old=moved(adapter(),T7)
 old_hits=[dict(id=n,intersection_mm3=volume(old.intersect(s))) for n,s in hardware.items() if n.startswith('J7_FIXED')]
 assert min(r['intersection_mm3'] for r in old_hits)>0
 # Existing WRIST full axial insertion proof is repeated for P skirt; disk always forward z>=0.
 skirt=ann(28,25,-6.5,70).fuse(ann(28,24.9,-.1,70))
 sv=volume(skirt.intersect(v));assert sv<1e-5
 # Complete known head/shaft swept envelopes, no invented thread length.
 hs=[]
 for group,xylist,z0,seat,rr,hr,hh,T,obs in [('J6_OUT',polar(22,OEM_ANGLES),-9,4.6,1.5,2.84,3,T6,{'W01':Y,'J6':V6}),('J7_FIXED',polar(32,range(0,360,45)),-26.5,-4,1.5,2.84,3,T7,{'W01':Y,'J6':V6,'J7':V7}),('J7_OUT',polar(22,OEM_ANGLES),-9,4.6,1.5,2.84,3,T7,{'W01':Y,'J6':V6,'J7':V7,'A01-P':A}),('HEAD',polar(32,HEAD_ANGLES),-.35,12,2,3.61,4,T7,actual)]:
  for i,xy in enumerate(xylist):
   sw=moved(cap(rr,z0,seat+60,xy).fuse(cap(hr,seat,seat+60+hh,xy)),T)
   vals={n:volume(sw.intersect(o)) for n,o in obs.items()};assert max(vals.values())<1e-5
   hs.append(dict(id=f'{group}_{i+1}',intersection_mm3=vals,missing_thread_segment=group!='HEAD'))
 # Continuous q6 external proof: all material except rear pilot is Y>=0. Rear pilot sweeps an
 # invariant annulus; fixed-side M3 heads occupy R>=29.16 at Y<=-1.
 neg=cq.Solid.makeBox(300,10,300,cq.Vector(-150,-10,-150))
 actual_rear=Y.intersect(neg);pilot_bound=moved(ann(28,25,-6.5,0).fuse(ann(28,24.9,-.1,0)),T6)
 rear_escape=volume(actual_rear.cut(pilot_bound));assert rear_escape<1e-5
 rear_vs_oem=volume(pilot_bound.intersect(V6));assert rear_vs_oem<1e-5
 downstream_positive={n:bb(s)[0][1] for n,s in {**actual,**hardware}.items() if n not in ['J6_OEM','W01'] and not n.startswith('J6_OUT')}
 assert min(downstream_positive.values())>0
 # Independently contain all q7-moving external parts; rotation preserves Z and radius.
 q7_bounds={'A01-P':ann(28,24.9,-6.5,0).fuse(cap(38,0,8)),'H01':cap(38,8,12)}
 q7_escape={n:volume((parts['A01-P'] if n=='A01-P' else parts['H01-reuse']).cut(b)) for n,b in q7_bounds.items()}
 assert max(q7_escape.values())<1e-5
 # Current service cylinder is a reservation for plugs/wires, not a claimed connector model.
 service=moved(cap(40,-114.4,-74.4),T7)
 service_vals={n:volume(service.intersect(s)) for n,s in {'W01':Y,'J6':V6}.items()};assert max(service_vals.values())<1e-5
 rear_connector_clip=v.intersect(cq.Solid.makeBox(100,100,4.4,cq.Vector(-50,-50,-74.4)))
 return dict(static=static,hardware_exterior=hp,hardware_pairs=pairs,tools=tools,known_hardware_insertion_sweeps=hs,contact_area_mm2={'J6_output':contact(Y,V6,[0,1,0]),'J7_fixed':contact(Y,V7,[0,0,1]),'J7_output_A01P':contact(A,V7,[0,0,1]),'A01P_H01':contact(H,A,[0,0,1])},vendor_envelope={'radius_body_mm':35.1,'body_z_mm':[-74.5,-10],'nose_radius_mm':29.1,'nose_z_mm':[-10,0],'actual_brep_escape_mm3':escape,'actual_rear_clip_z_mm':[-74.4,-70],'rear_clip_bbox_joint_mm':bb(rear_connector_clip),'rear_clip_volume_mm3':volume(rear_connector_clip),'includes_exported_socket_bodies':True,'unmodeled':'Mating plugs, wires, retention, assembly tolerances'},J7_insertion={'direction':'-Z relative to seated J7; slide upward into seat from below','tested_superset_translation_mm':[0,100],'beyond_100':'Entire OEM at Z<=-65 in pair frame, below yoke minZ=-38; separated','superset_intersections_mm3':vi},A01P_insertion={'skirt_swept_vendor_mm3':sv,'plane_and_radial_clearance_to_carrier_and_heads_mm':[0.65,1.16],'scope':'Skirt sweep plus z/radial separation; all aligned translations toward seated; tolerance and complete threads excluded'},old_A01_conflict=old_hits,q6_continuous={'limits_deg':[-100,100],'method':'Y-plane separation invariant under rotation about +Y, plus axisymmetric rear pilot containment','rear_material_escape_mm3':rear_escape,'rear_sweep_vendor_mm3':rear_vs_oem,'fixed_M3_head_radial_gap_mm':32-2.84-28,'downstream_min_Y_mm':downstream_positive,'excluded':'Unknown OEM output/internal fixed-versus-rotating partitions; all upstream links/J5/new J6 fixed bracket/head/cables. External interface compatibility only.'},q7_continuous={'limits_deg':[-90,90],'method':'Z-plane and annular separation invariant under +Z rotation','skirt_to_carrier_radial_gap_mm':29.3-28,'skirt_to_fixed_head_radial_gap_mm':32-2.84-28,'main_disc_to_fixed_head_z_gap_mm':1,'actual_original_brep_escape_from_rotational_bounds_mm3':q7_escape,'combined_q6_q7_head_min_Y_mm':17,'head_M4_tip_to_fixed_head_z_gap_mm':.65,'excluded':'True head and cable assembly, and OEM internal rotational partition. No end-effector full swept-volume approval.'},rear_service_reservation={'J7_radius_mm':40,'J7_axial_length_mm':40,'J7_z_mm':[-114.4,-74.4],'static_intersection_mm3':service_vals,'q6_invariant_min_Y_mm':15,'verified_mated_connectors':False,'warning':'A chosen keep-clear volume; cable bend radius, keyed insertion/latch access and actual mated plug tolerances NOT qualified. J6 rear (-Y) is unconstrained by this positive-Y candidate but next upstream bracket is unknown.'}),actual,hardware

def section_indicator(s,axis,v):
 d=.002;start=np.array([-100.,-100.,-100.]);lens=np.array([250.,250.,250.]);start[axis]=v-d/2;lens[axis]=d
 slab=s.intersect(cq.Solid.makeBox(*lens,cq.Vector(*start)))
 p=GProp_GProps();BRepGProp.VolumeProperties_s(slab.wrapped,p);A=p.Mass()/d
 ids=[i for i in range(3) if i!=axis];J=matrix_props(slab)/d;J=J[np.ix_(ids,ids)]-np.eye(2)*A*d*d/12
 b=np.array(bb(slab));com=np.array(p.CentreOfMass().Coord());r=max(np.linalg.norm(c-com[ids]) for c in itertools.product(*[(b[0,i],b[1,i]) for i in ids]))
 return dict(normal_axis='XYZ'[axis],position_mm=v,area_mm2=A,centroid_mm=com.tolist(),I_area_mm4=J.tolist(),lambda_min_mm4=float(np.linalg.eigvalsh(J).min()),extreme_radius_bound_mm=float(r))

def mechanics(parts,properties):
 g=9.80665
 rows=[]
 for n in ['W01','A01-P','H01-reuse']:
  c=np.array(properties[n]['com_mm']);T=np.eye(4) if n=='W01' else T7;c=(T@np.r_[c,1])[:3];I=np.array(properties[n]['inertia_at_com_kg_m2']);I=T[:3,:3]@I@T[:3,:3].T
  rows.append(dict(id=n,mass_kg=properties[n]['mass_6061_candidate_kg'],com_pair_mm=c.tolist(),com_world_mm=(c+ORIGIN).tolist(),inertia_at_com_world_kg_m2=I.tolist(),preceding_joints=6 if n=='W01' else 7,source='actual original solid + assumed 6061 density'))
 # Head hardware: catalog SNS mass and ideal steel cylinders for dowels, separately disclosed.
 rows += [dict(id='HEAD_SNS_M4_12_x4',mass_kg=.008,com_pair_mm=[0,55,43],preceding_joints=7,source='catalog2g each; COM at headside bearing plane proxy, not supplier COM'),dict(id='MS3_8_x2_proxy',mass_kg=2*math.pi*1.5**2*8*7.85e-6,com_pair_mm=[0,55,43],preceding_joints=7,source='ideal steel cylinder estimate; exact vendor mass/end geometry absent')]
 imass=sum(r['mass_kg'] for r in rows if r['id']!='W01');icom=sum(r['mass_kg']*np.array(r['com_pair_mm']) for r in rows if r['id']!='W01')/imass
 # No double-counting: 1.5kg head excludes this original interface and listed head hardware.
 bodies=[(2,np.array([0,55,235.])),(1.5,np.array([0,55,135.])),(.88,np.array([0,55,2.85]))]+[(r['mass_kg'],np.array(r['com_pair_mm'])) for r in rows]
 F=sum(m for m,c in bodies)*g;mr=sum(m*c/1000 for m,c in bodies);M=g*np.linalg.norm(mr);q6=g*np.linalg.norm(mr[[0,2]])
 headb=[(m,c-np.array([0,55,35.])) for m,c in bodies if not (m==.88)]
 # Exclude W01 from J7 output; interface and head/object are downstream of that plane.
 headb=[(2,np.array([0,0,200.])),(1.5,np.array([0,0,100.]))]+[(r['mass_kg'],np.array(r['com_pair_mm'])-np.array([0,55,35.])) for r in rows if r['id']!='W01']
 F7=sum(m for m,c in headb)*g;M7=g*np.linalg.norm(sum(m*c/1000 for m,c in headb))
 # J7 fixed face is 10mm behind output, and its module self mass lies ~22.15mm behind face.
 fixedb=[(m,c+np.array([0,0,10.])) for m,c in headb]+[(.88,np.array([0,0,-22.15]))]
 Mf=g*np.linalg.norm(sum(m*c/1000 for m,c in fixedb));Ff=sum(m for m,c in fixedb)*g
 # Motor COM axial32.15 only a proxy: supplier transverse direction/reference details unresolved.
 # A completely geometry-contained COM bound adds the maximum possible change of module moment.
 max_com_delta=math.sqrt(35.1**2+max(abs(-74.5+32.15),abs(0+32.15))**2)
 uncertain_extra=.88*g*max_com_delta/1000
 groups={}
 for name,r,ang,mo,force in [('J6_OUTPUT8',22,OEM_ANGLES,M,F),('J7_FIXED8',32,list(range(0,360,45)),Mf,Ff),('J7_OUTPUT8',22,OEM_ANGLES,M7,F7),('HEAD4',32,HEAD_ANGLES,M7,F7)]:
  P=np.array(polar(r,ang));P-=P.mean(0);S=P.T@P;gain=np.linalg.norm(P@np.linalg.inv(S),axis=1)
  groups[name]=dict(moment_bound_Nm=float(mo),force_N=float(force),S_mm2=S.tolist(),maximum_axial_increment_N=float(max(gain)*mo*1000),equal_direct_transverse_share_N=float(force/len(P)),conditions='Equal stiffness, compatible compression contact, no prying. Increments are not total/preload forces or strength acceptance.')
 for n in ['J6_OUTPUT8','J7_FIXED8']:
  gg=groups[n];gg['COM_uncertainty_moment_bound_Nm']=gg['moment_bound_Nm']+uncertain_extra;gg['COM_uncertainty_max_bolt_increment_N']=gg['maximum_axial_increment_N']*gg['COM_uncertainty_moment_bound_Nm']/gg['moment_bound_Nm']
 neck=section_indicator(parts['W01'],1,15);neck['selected_stress_indicator_MPa']=(M+uncertain_extra)*1000*neck['extreme_radius_bound_mm']/neck['lambda_min_mm4']+F/neck['area_mm2'];neck['condition']='Selected Y=15 neck section; M about J6 plus motor-COM geometric uncertainty used conservatively for this zero-pose geometry. Not fillet stress, ring bending, buckling or global lower bound.'
 sections=[]
 for n,axis,z,mom in [('A01-P',2,-5,M7),('A01-P',2,.65,M7),('A01-P',2,4.7,M7),('W01',2,28,Mf)]:
  s=section_indicator(parts[n],axis,z);s['part']=n;s['nominal_indicator_MPa']=mom*1000*s['extreme_radius_bound_mm']/s['lambda_min_mm4'];sections.append(s)
 P=groups['HEAD4']['maximum_axial_increment_N'];L=max(min(math.dist(h,o) for o in polar(22,OEM_ANGLES)) for h in polar(32,HEAD_ANGLES));b=8;t=4.4;E=69000
 strip=dict(width_mm=b,thickness_mm=t,span_mm=L,force_N=P,sigma_MPa=6*P*L/(b*t*t),deflection_mm=4*P*L**3/(E*b*t**3),E_assumed_MPa=E,scope='Selected cantilever strip between outer head screw and closest OEM screw; not guaranteed ring response or FEA.')
 return dict(gravity_m_s2=g,body_rows=rows,interface_mass_with_known_hardware_kg=imass,interface_com_pair_mm=icom.tolist(),interface_com_world_mm=(icom+ORIGIN).tolist(),unknown_OEM_fine_screw_mass_excluded=True,payload_kg=2,head_budget_kg=1.5,head_budget_excludes_interface=True,offset_origin='J7 OEM output plane at pair[0,55,35], not H01 front; TCP+200, headCOM+100',J7_output_moment_Nm=float(M7),J7_output_force_N=float(F7),J7_fixed_face_moment_Nm=float(Mf),J6_zero_geometry_arbitrary_gravity_moment_Nm=float(M),J6_axis_gravity_torque_abs_bound_Nm=float(q6),J6_upstream_total_force_N=float(F),J7_motor_COM_proxy_pair_mm=[0,55,2.85],J7_COM_max_geometric_delta_mm=max_com_delta,J7_COM_geometry_uncertainty_moment_increment_Nm=uncertain_extra,groups=groups,neck_section=neck,net_sections=sections,main_disc_strip=strip,skirt={'nominal_radial_wall_mm':3,'cylindrical_pilot_overlap_mm':1.8,'whole_transverse_force_uniform_projected_pressure_proxy_MPa':F7/(50*1.8),'condition':'Only a projected-area indicator, not actual contact pressure. No interference stress, hoop stability, tolerance or fretting calculation; main bolt-to-bolt load path stays within Z0..8.'},not_validated=['Certified material/process allowables','Complete OEM thread engagement, screw lengths/PN, preload/friction','Local ring/neck/notch FEA, fatigue, shock, elasticity or fast stop','Bearing life and static moment limit','Zero-speed continuous motor thermal torque/brake emergency duty','Head geometry and real cable motion'])

def additional_original_checks(parts,study):
 oldA=cq.importers.importStep(str(ROOT/'engineering/generated/r5-wrist-erob01/STEP/adapter.step')).val()
 oldH=cq.importers.importStep(str(ROOT/'engineering/generated/r5-wrist-erob01/STEP/mate.step')).val()
 expected=oldA.intersect(ann(30.01,28,-6.51,0));removed=oldA.cut(parts['A01-P'])
 delta={'A01P_added_outside_original_mm3':volume(parts['A01-P'].cut(oldA)),
        'A01P_removed_volume_mm3':volume(removed),
        'A01P_removed_outside_expected_skirt_mm3':volume(removed.cut(expected)),
        'expected_skirt_not_removed_mm3':volume(expected.cut(removed)),
        'H01_symmetric_difference_mm3':volume(oldH.cut(parts['H01-reuse']))+volume(parts['H01-reuse'].cut(oldH))}
 assert max(v for k,v in delta.items() if k!='A01P_removed_volume_mm3')<1e-5
 configurations=[('J6_OUT',polar(22,OEM_ANGLES),-9,4.6,1.5,2.84,3,T6),('J7_FIXED',polar(32,range(0,360,45)),-26.5,-4,1.5,2.84,3,T7),('J7_OUT',polar(22,OEM_ANGLES),-9,4.6,1.5,2.84,3,T7),('HEAD',polar(32,HEAD_ANGLES),-.35,12,2,3.61,4,T7)]
 previous={};pathrows=[]
 for group,xylist,z0,seat,rr,hr,hh,T in configurations:
  current={}
  for i,xy in enumerate(xylist):
   sw=moved(cap(rr,z0,seat+60,xy).fuse(cap(hr,seat,seat+60+hh,xy)),T)
   vals={n:volume(sw.intersect(sh)) for n,sh in previous.items()};assert not vals or max(vals.values())<1e-5
   pathrows.append(dict(id=f'{group}_{i+1}',prior_hardware_sweep_intersections_mm3=vals,scope='Only known free shaft/head; complete fine-thread segments still unknown.'))
   current[f'{group}_{i+1}']=moved(cap(rr,z0,seat,xy).fuse(cap(hr,seat,seat+hh,xy)),T)
  previous.update(current)
 # Tighter (still bounding-box) stress screen for the same selected Y15 section.
 N=study['mechanics']['neck_section'];J=np.array(N['I_area_mm4']);inv=np.linalg.inv(J)
 slab=parts['W01'].intersect(cq.Solid.makeBox(250,.002,250,cq.Vector(-100,14.999,-100)))
 b=np.array(bb(slab));co=np.array(N['centroid_mm']);coeff=max(np.linalg.norm(inv@np.array([-(z-co[2]),x-co[0]])) for x,z in itertools.product([b[0,0],b[1,0]],[b[0,2],b[1,2]]))
 mo=study['mechanics']['J6_zero_geometry_arbitrary_gravity_moment_Nm']+study['mechanics']['J7_COM_geometry_uncertainty_moment_increment_Nm']
 stress=mo*1000*coeff+study['mechanics']['J6_upstream_total_force_N']/N['area_mm2']
 assert stress<=N['selected_stress_indicator_MPa']+1e-7
 return dict(source_code_sha256=hashlib.sha256(inspect.getsource(additional_original_checks).encode()).hexdigest(),original_delta=delta,known_hardware_ordered_insertions=pathrows,neck_bounding_rectangle_normal_stress_indicator_MPa=float(stress),neck_assumptions='Same conditional global force/moment as main section; maximizes ||J^-1[-z,x]|| over actual section bounding-rectangle corners. Still omits notch, plate/shell stress, shear, prying, FEA and fatigue.')

class Page(Sheet):
 def header(self,n,title,sub):
  self.text(14,282,'ODRADEK / R5-WRIST-PAIR01',18);self.text(405,282,f'{n} / 5',10,align='right');self.text(14,271,title,12,BLUE);self.text(405,271,sub,8.6,align='right');self.line((14,266),(406,266),BLUE,.8)
 def footer(self,n):
  self.line((14,20),(406,20),GREY,.5);self.text(14,13,'mm / A3 | 原创候选名义尺寸 | 无载打印验证 | 非生产图、非2kg额定放行',8);self.text(406,13,f'2026-09-27 / {n}',8,align='right')

def yzcs(s,x=0):
 # Proper rotate +90deg about Y: new X=old Z, new Z=-old X; XY section yields (oldZ,oldY).
 # For intuitive sideview (+Y horizontal,+Z vertical), use XZ section after proper Rz90: newX=-Y.
 q=s.rotate((0,0,0),(0,0,1),90)
 cs=curves(section(q,'XZ',x),'XZ')
 for r in cs:
  for k in ['p','q','c']:
   # Fallback polyline segments share adjacent endpoint lists. Replace each
   # coordinate value so the same point is not reflected twice in-place.
   if k in r:r[k]=[-r[k][0],r[k][1]]
  if r['kind']=='ARC':r['start'],r['end']=(180-r['end'])%360,(180-r['start'])%360
 return cs

def drawings(parts,study):
 Y=parts['W01'];A=parts['A01-P'];H=parts['H01-reuse'];views={
 'W01':[('SIDE X0: Y horizontal Z vertical',yzcs(Y,0)),('SIDE X10.5',yzcs(Y,10.5)),('J7 RING layer Z28',curves(section(Y,'XY',28),'XY')),('J6 DISC layer Y4.8',curves(section(Y,'XZ',4.8),'XZ'))],
 'A01-P':[('FRONT Z7.9',curves(section(A,'XY',7.9),'XY')),('REAR LAND Z.1',curves(section(A,'XY',.1),'XY')),('SECTION Y0',curves(section(A,'XZ',0),'XZ'))],
 'H01-reuse':[('PLAN Z10',curves(section(H,'XY',10),'XY')),('SECTION Y0',curves(section(H,'XZ',0),'XZ'))]}
 dx=[]
 for name,vs in views.items():
  d=ezdxf.new('R2013');d.units=4;d.header['$INSUNITS']=4
  for l,c in [('BOUNDARY',7),('NOTE',3),('DIM',2)]:d.layers.new(l,dxfattribs={'color':c})
  m=d.modelspace()
  for i,(label,cs) in enumerate(vs):
   dxf_geometry(m,cs,(i*160,0));m.add_text(label,dxfattribs={'height':2.5,'insert':(i*160-40,105),'layer':'NOTE'})
  for i,n in enumerate(['R5-WRIST-PAIR01 / mm / NOMINAL STUDY ONLY, NOT PRODUCTION RELEASE','True sections from exported originals. All hole coordinates: hole-coordinates.csv','W01 pair frame O=J6 world(0,0,640); J7=(0,55,35), output +Z','W01 J6 output face Y0, mainY0..8; J7 fixed seatZ25 / frontZ31','W01 ring OD78 ID58.6 thick6; neck X+/-14 Y8..24 Z26..31','W01 ribs X-12..-9 and9..12; YZ(8,10),(8,26),(18,26)','A01-P same A01 except rear skirt OD56, wall3; no extension','OEM M3x.35 screw LENGTH/SKU TBD; smooth bore not full thread evidence']):m.add_text(n,dxfattribs={'height':2.1,'insert':(-40,-60-i*4),'layer':'NOTE'})
  p=OUT/'DXF'/(name+'.dxf');d.saveas(p);rr=ezdxf.readfile(p);assert not rr.audit().has_errors;dx.append(dict(path=str(p.relative_to(OUT)),sha256=sha(p),units_mm=True,audit_errors=0))
 p=OUT/'ODR-R5-WRIST-PAIR01.pdf';c=canvas.Canvas(str(p),pagesize=landscape(A3));s=Page(c)
 s.header(1,'两轴局部关系 / 保留原点与轴向','原创剖面1.25:1 + 已验证OEM包含圆柱；非厂商投影')
 # Side includes exact own X0 section; simple envelope is labelled, never presented as source CAD.
 for obj,col in [(Y,BLUE),(moved(A,T7),'#937233'),(moved(H,T7),'#44794E')]:s.geo(yzcs(obj),(116,147),1.25,col,.8)
 for x0,y0,w,h in [(-74.5,-35.1,64.5,70.2),(-10,-29.1,10,58.2),(19.9,-39.5,70.2,64.5),(25.9,25,58.2,10)]:
  s.line((116+1.25*x0,147+1.25*y0),(116+1.25*(x0+w),147+1.25*y0),GREY,.3,[4,2]);s.line((116+1.25*x0,147+1.25*(y0+h)),(116+1.25*(x0+w),147+1.25*(y0+h)),GREY,.3,[4,2]);s.line((116+1.25*x0,147+1.25*y0),(116+1.25*x0,147+1.25*(y0+h)),GREY,.3,[4,2]);s.line((116+1.25*(x0+w),147+1.25*y0),(116+1.25*(x0+w),147+1.25*(y0+h)),GREY,.3,[4,2])
 s.axes((116,147),5,1.25);s.axes((184.75,190.75),5,1.25)
 s.dim_h(116,184.75,217,147,190.75,'55');s.dim_v(147,190.75,245,184.75,'35')
 s.text(16,249,'侧向 Y-Z：横Y、纵Z；pair O=J6；虚线仅为包含体',10,BLUE)
 s.text(28,140,'J6 +Y →',9);s.text(184,208,'J7 +Z ↑',9)
 s.text(277,247,'当前局部基准',11,BLUE);s.rows(277,235,['J6 world (0,0,640)，轴+Y','J7 world (0,55,675)，轴+Z','pair坐标 = world − (0,0,640)','J6安装clocking：绕本地Z +15°','J7输出坐标：与worldXYZ同向','J6数学限位±100°；J7 ±90°','本研究不修改整链或旧RH连接','每只70I带闸目录质量0.88kg','原厂Ø70，轴向74.4（含CAD端子）','W01外包络宽78；未增加轴距','A01-P/H01仍Z0…12、无延长'],7,9)
 s.rows(16,91,['本图包含性验证使用真实OEM STEP（含其端子体）；原厂CAD不随公开输出分发。',
 'W01为一体直角连接：J6输出承力盘 → 双肋/颈部 → J7固定前环。J7输出再接A01-P。',
 '旧WRIST01只证明输出侧局部。加入J7固定侧螺钉后，旧OD60裙与8个头干涉；本变体减为OD56。',
 '两轴局部连续证明不含J5/上游J6固定架、整头或动态线束；这些依赖不能被本局部结论覆盖。',
 '约700mm仍是整臂肩到TCP目标，非裸腕长度；本研究不重复加35mm，也不移动冻结肩轴。'],7,9)
 s.footer(1);c.showPage()
 s.header(2,'W01 / 一体连接体完整名义定义','顶层1.25:1 / 侧剖1.5:1；pair坐标；6061材料候选')
 s.geo(views['W01'][2][1],(95,105),1.25);s.text(95,245,'顶层 Z=28 / X-Y',10,BLUE,align='center')
 s.dim_h(46.25,143.75,233,173.75,173.75,'Ø78 J7固定环')
 s.lead((95+29.3*1.25,173.75),(149,213),(161,213),'Ø58.6贯通')
 s.geo(views['W01'][1][1],(250,183),1.5);s.text(303,248,'侧剖 X=10.5 / Y-Z',10,BLUE,align='center')
 s.dim_h(262,286,243,222,222,'16 颈长 Y8…24')
 s.dim_v(222,229.5,397,340,'5 颈厚')
 s.rows(15,91,['J6盘：Ø76、轴向Y0…8；后裙OD56/母止口Ø50+0.016/0，Y−6.5…0，入口C0.3/内根R0.1。',
 'J6孔阵以本地+15°旋转后的面坐标为准：8×Ø3.4，PCD44非均布；前Ø6.2沉孔深3.4、底口C0.2。',
 '中心Ø18贯通；J6后面Ø39×0.3避空；6×Ø5.6×0.5浅孔让开原厂齐平头；孔表第4页/CSV。',
 'J7环中心(0,55)，OD78/ID58.6，Z25…31；8×Ø3.4贯通，PCD64每45°；前孔口C0.2，无头沉孔。',
 '矩形颈 X−14…14 / Y8…24 / Z26…31；双肋 X−12…−9、9…12，厚3；YZ三角见上图。',
 '三角顶点(8,10),(8,26),(18,26)；所有并集相交线由真实STEP定义，未增加隐含圆角。',
 '名义锐内角需EDM或获准改R后复核，不能直接当普通三轴铣削成品图；倒角/刀具半径尚未释放。',
 '建议试制：关键厚度±0.05，非配合外形±0.10；孔位置度Ø0.10相对各自接口轴/平面；不是通用公差。'],7,8.7)
 s.footer(2);c.showPage()
 s.header(3,'A01-P / 薄后裙；H01保持冻结接口','剖面2:1 / 前层1.75:1；单位为J7 joint frame')
 s.geo(views['A01-P'][2][1],(98,204),2);s.geo(views['A01-P'][0][1],(292,175),1.75)
 s.dim_h(42,154,181,191,191,'Ø56 后裙（壁3）');s.dim_h(48,148,170,191,191,'Ø50 +0.016/0')
 s.dim_v(191,204,185,154,'6.5');s.dim_v(204,220,197,174,'8')
 s.text(98,242,'剖面 Y=0；原A01仅后裙减径',10,BLUE,align='center')
 s.rows(16,95,['主盘OD76 Z0…8；后裙OD56 Z−6.5…0；H01厚4 Z8…12；主头侧、孔/销/母止口不变。',
 '8×Ø3.4、PCD44角0/30/90/120/180/210/270/300；前沉孔Ø6.2深3.4；底口C0.2。',
 '4×M4×0.7通牙PCD64角45/135/225/315，入口两面C0.25；STEPØ4为大径示意，不是钻孔尺寸。',
 '销孔(0,±32) Ø3.000…3.003；H01上一圆孔、下一沿Y槽，宽Ø3.020…3.035/槽长5。',
 '中心Ø18；后面Ø39×0.3；6×Ø5.6×0.5齐平螺钉避空；后口C0.3、内根R0.1。',
 'J7固定螺钉最大头Ø5.68从Z−4到−1；与裙径向余量1.16，主盘轴向余量1.0。',
 'H01用4×NBK SNS-M4-12；最长末端Z−0.35，与固定头轴向余量0.65；均为名义几何。',
 'A01-P/H01为项目自定义法兰，不称ISO标准；销/牙强度、预紧与公差叠加未发布。',
 '3mm裙只做有证据几何候选：主螺栓传力在盘Z0…8；并未假定薄裙无条件承担全部弯矩。'],7,9)
 s.footer(3);c.showPage()
 s.header(4,'孔坐标、装入路径与工具边界','CSV为完整坐标真值；角度在相应本地面坐标内定义')
 s.text(15,251,'J6输出孔：pair X / Z；轴向Y',10,BLUE)
 for i,xy in enumerate(polar(22,OEM_ANGLES)):
  p6=(T6@np.r_[xy,0,1])[:3];s.text(15,239-i*7,f'{i+1}  {p6[0]:+.6f}  {p6[2]:+.6f}',9)
 s.text(140,251,'J7固定孔：pair X / Y；Z25…31',10,BLUE)
 for i,xy in enumerate(polar(32,range(0,360,45))):s.text(140,239-i*7,f'{i+1}  {xy[0]:+.6f}  {55+xy[1]:+.6f}',9)
 s.text(277,251,'安装顺序 / 工具空间',10,BLUE);s.rows(277,239,['1. 台架支承后装A01-P定位销。','2. W01先装J6，8颗OEM细牙锁紧。','3. J7从−Z方向上移，套过固定环。','4. 从+Z装8颗J7固定细牙螺钉。','5. A01-P沿−Z装到J7输出面。','6. 解开线束限制后装H01和4颗M4。','J6不得在J7装好后才补拧螺钉。','Ø5.8/7.8×60是空间探针，非选定工具。','全部OEM长度/完整牙段仍TBD。'],7,8.9)
 s.rows(15,160,['J7轴向装入：实际OEM被R35.1后体 + R29.1前鼻包含；鼻通过R29.3固定环孔。',
 '下移0…100mm的完整包含扫掠与W01/J6零相交；更远时整关节低于W01最低面。',
 'q6±100°：绕Y旋转保持Y；下游实体Y>0，J6外壳Y≤0，后裙轴对称扫掠另核为零。',
 'q7±90°：Z不变，后裙R≤28；固定环R≥29.3/固定头R≥29.16；主盘与固定头Z分离。',
 '以上只证明列明的外部实体集合；不把原厂合并CAD推断为内部旋转认证，更不含上游与整头。',
 '后端插座原体已纳入；J7另留R40×40后向空间，未包含已选配对插头/出线/弯曲半径。',
 '原厂手册：GH4 EtherCAT配GHR-04V-S、XT30UPB-M配XT30U-F；详细键位/线弯仍待实物契约。',
 'Ø18只表示两条独立几何轴孔；90°转弯、2根GMSL及电源/EtherCAT束的动态通过未验证。'],7,9)
 s.footer(4);c.showPage()
 s.header(5,'条件载荷 / 真实质量 / 无载样件','静态筛查不等于持续零速、轴承或疲劳能力认证')
 L=study['mechanics'];s.rows(15,251,[f"W01原创金属 {study['parts']['W01']['mass_6061_candidate_kg']*1000:.2f}g；A01-P/H01及已列头侧硬件 {L['interface_mass_with_known_hardware_kg']*1000:.2f}g。",
 '头预算1.5kg明确排除上述接口；2kg是净物体，另计两只关节及W01；未知OEM细牙螺钉仍须补质量。',
 f"J7：物体+200mm、头COM+100mm均从OEM面起算；M={L['J7_output_moment_Nm']:.6f}Nm。",
 f"J6零位几何任意重力方向弯矩界 {L['J6_zero_geometry_arbitrary_gravity_moment_Nm']:.5f}Nm；轴向驱动重力矩界 {L['J6_axis_gravity_torque_abs_bound_Nm']:.5f}Nm。",
 f"J7模块COM代理不确定性：另加最多{L['J7_COM_geometry_uncertainty_moment_increment_Nm']:.4f}Nm几何上界；不把目录10/36Nm当静止持续保证。"],7,9.3)
 y=207
 for name,row in L['groups'].items():s.text(15,y,f"{name}:  M {row['moment_bound_Nm']:.4f}Nm / 单颗最大轴向增量 {row['maximum_axial_increment_N']:.3f}N",9);y-=7
 s.rows(15,167,['螺钉分配假设等刚度、接触压缩成立且无撬力，给的是增量而非总拉力/预紧。',
 f"Y15颈截面A={L['neck_section']['area_mm2']:.3f}mm²；选定截面应力指标{L['neck_section']['selected_stress_indicator_MPa']:.2f}MPa。",
 f"A01-P主盘条带：宽8、厚4.4、长{L['main_disc_strip']['span_mm']:.3f}，指标σ={L['main_disc_strip']['sigma_MPa']:.2f}MPa、δ={L['main_disc_strip']['deflection_mm']:.5f}mm。",
 f"同一颈截面矩形边界的较紧法向应力指标{study['additional_checks']['neck_bounding_rectangle_normal_stress_indicator_MPa']:.2f}MPa；仍不是缺口峰值。",
 '净截面/条带都没有包含整体环板弯曲、孔口/锐根应力、螺纹剥离、夹紧滑移与材料证书，不能据此放行。'],7,9)
 s.text(15,124,'打印与复核',11,BLUE);s.rows(15,112,['W01-G打印母止口Ø50.4、中心Ø18.4、OEM孔Ø3.8、固定环ID58.8；仅检查安装可达。',
 'A01-P-G沿用同类加大孔规则；H01-G销孔/槽宽3.3。PLA/PETG，不通电、不承重、不硬敲原厂。',
 'W01-G：Rx90°后Tz6.5；A01-P-G：Rx180°后Tz8；H01-G：Tz−8。模型附正确首层文件。',
 'W01需要可拆支撑，尤其主盘内孔/肋下方；先打小孔与止口试片，只补局部孔，不全局缩放。',
 'STEP重新读入有效单实体；STL逐件watertight/方向一致、bbox与体积差已写study.json。',
 '后续：供应商受控螺纹/螺钉、真实工具与插头、加工刀具R及材料/预紧、局部FEA/疲劳和整臂碰撞。'],7,9)
 s.footer(5);c.save();assert len(PdfReader(p).pages)==5
 return dict(file=p.name,sha256=sha(p),pages=5),dx

def core_fingerprint():
 names=[sha,js,matrix_props,cap,ann,contact,yoke,a01p,original_props,oem_features,collision_and_motion,section_indicator,mechanics]
 dep=[ROOT/'engineering/r5_wrist_erob01.py',ROOT/'engineering/build_layout.py',SRC]
 return hashlib.sha256((''.join(inspect.getsource(f) for f in names)+repr(T6.tolist())+repr(T7.tolist())+repr(ORIGIN.tolist())+repr(RHO)+''.join(sha(p) for p in dep)).encode()).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--vendor-step',type=Path);ap.add_argument('--private-preview-dir',type=Path);ap.add_argument('--redraw',action='store_true');args=ap.parse_args()
 for f in ['STEP','STL','DXF']:(OUT/f).mkdir(parents=True,exist_ok=True)
 src=json.loads(SRC.read_text());vendorhash=next(x['sha256'] for x in src['sources'] if x['id']=='vendor_step')
 pdfmetrics.registerFont(TTFont('CN','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
 if args.redraw:
  study=json.loads((OUT/'study.json').read_text());assert study['core_fingerprint']==core_fingerprint()
  parts={}
  for n,p in study['parts'].items():
   sp=OUT/'STEP'/(n+'.step');assert sha(sp)==p['step_sha256'];parts[n]=cq.importers.importStep(str(sp)).val()
  study['source_hashes'][0]['sha256']=sha(__file__);study['additional_checks']=additional_original_checks(parts,study);study['pdf'],study['dxfs']=drawings(parts,study);js(OUT/'study.json',study)
  js(OUT/'manifest.json',{'revision':'R5-WRIST-PAIR01','outputs':[dict(path=str(p.relative_to(OUT)),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['manifest.json','visual-qa.json','independent-review.json'] and p.suffix!='.png']})
  return
 assert args.vendor_step and sha(args.vendor_step)==vendorhash
 v=cq.importers.importStep(str(args.vendor_step)).val().rotate((0,0,0),(1,1,-1),120).translate((0,0,X0));assert v.isValid()
 parts={'W01':yoke(),'A01-P':a01p(),'H01-reuse':mate(),'W01-G':yoke(True),'A01-P-G':a01p(True),'H01-G':mate(True)}
 props={n:original_props(n,s) for n,s in parts.items()};print('Exports complete',flush=True)
 printqa={}
 for n in ['W01-G','A01-P-G','H01-G']:
  s=parts[n].rotate((0,0,0),(1,0,0),90).translate((0,0,6.5)) if n=='W01-G' else (parts[n].rotate((0,0,0),(1,0,0),180).translate((0,0,8)) if n=='A01-P-G' else parts[n].translate((0,0,-8)))
  p=OUT/'STL'/(n+'-print-oriented.stl');cq.exporters.export(s,str(p),tolerance=.01,angularTolerance=.05);m=trimesh.load(p,force='mesh',process=True);assert m.is_watertight and m.is_winding_consistent and abs(m.bounds[0,2])<1e-5
  printqa[n]=dict(path=str(p.relative_to(OUT)),sha256=sha(p),watertight=bool(m.is_watertight),bbox_mm=m.bounds.tolist())
 checks,actual,hardware=collision_and_motion(parts,v);print('Checks complete',flush=True)
 features=oem_features(v);js(OUT/'vendor-interface-extraction.json',features)
 mechanics_data=mechanics(parts,props);js(OUT/'part-placements.json',{'revision':'R5-WRIST-PAIR01','pair_origin_world_mm':ORIGIN.tolist(),'parts':mechanics_data['body_rows']})
 with (OUT/'hole-coordinates.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['group','index','frame','x_mm','y_mm','z_mm','diameter_mm','feature'])
  for group,pts,T,z,diam,note in [('J6_OUTPUT',polar(22,OEM_ANGLES),T6,0,3.4,'PCD44; CB6.2x3.4 at localz4.6'),('J6_RELIEF',polar(22,OEM_RELIEF_ANGLES),T6,0,5.6,'PCD44 depth.5'),('J7_FIXED',polar(32,range(0,360,45)),T7,-10,3.4,'PCD64; through to localz-4, topC.2'),('A01P_OUTPUT',polar(22,OEM_ANGLES),np.eye(4),0,3.4,'J7frame; CB6.2x3.4'),('A01P_HEAD',polar(32,HEAD_ANGLES),np.eye(4),0,4,'M4x.7 through8, NOT drill4'),('A01P_PINS',[(0,32),(0,-32)],np.eye(4),0,3,'3.000..3.003; H01 round and radial slot')]:
   for i,xy in enumerate(pts):w.writerow([group,i+1,'pair' if group.startswith('J') else 'J7',*(T@np.r_[xy,z,1])[:3],diam,note])
 hashes=[]
 for p in [Path(__file__),SRC,ROOT/'engineering/r5_wrist_erob01.py',ROOT/'engineering/build_layout.py',ROOT/'engineering/draw_central_display01.py',ROOT/'engineering/generated/raised-arm-integration01/model.json',ROOT/'engineering/generated/r5-body01/body-only-model.json',ROOT/'engineering/generated/r5-wrist-erob01/study.json',ROOT/'engineering/generated/r5-wrist-erob01/STEP/adapter.step',ROOT/'engineering/generated/r5-wrist-erob01/STEP/mate.step']:
  hashes.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
 study=dict(revision='R5-WRIST-PAIR01',status='single original lightweight candidate; nominal geometry only, not manufacture release',license='CC-BY-NC-4.0',units='mm, kg, N, Nm, kg m2 as marked',source_hashes=hashes,private_vendor_sha256=vendorhash,frames={'pair_origin_world_mm':ORIGIN.tolist(),'J6_from_joint_to_pair':T6.tolist(),'J7_from_joint_to_pair':T7.tolist(),'q6_deg':[-100,100],'q7_deg':[-90,90],'offset_policy':'No translation of old axes. Not a whole-arm eRob replacement.'},parts=props,print_oriented=printqa,checks=checks,mechanics=mechanics_data)
 study['core_fingerprint']=core_fingerprint();study['section_curve_approximation_mm']=.002;study['additional_checks']=additional_original_checks(parts,study);js(OUT/'study.json',study)
 study['pdf'],study['dxfs']=drawings(parts,study);js(OUT/'study.json',study)
 if args.private_preview_dir:
  args.private_preview_dir.mkdir(parents=True,exist_ok=True);ass=cq.Assembly()
  for n,s in {**actual,**hardware}.items():ass.add(s,name=n)
  ass.save(str(args.private_preview_dir/'PRIVATE-with-vendor.step'))
 public=cq.Assembly()
 for n,s in actual.items():
  if 'OEM' not in n:public.add(s,name=n)
 public.save(str(OUT/'STEP/ORIGINAL-assembly.step'))
 js(OUT/'manifest.json',{'revision':'R5-WRIST-PAIR01','outputs':[dict(path=str(p.relative_to(OUT)),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['manifest.json','visual-qa.json','independent-review.json'] and p.suffix!='.png']})
 print(json.dumps({'mass':{n:props[n]['mass_6061_candidate_kg'] for n in ['W01','A01-P','H01-reuse']},'interface_mass':mechanics_data['interface_mass_with_known_hardware_kg'],'contact':checks['contact_area_mm2'],'loads':{k:mechanics_data[k] for k in ['J7_output_moment_Nm','J6_zero_geometry_arbitrary_gravity_moment_Nm','J6_axis_gravity_torque_abs_bound_Nm']},'neck':mechanics_data['neck_section']},indent=2),flush=True)
if __name__=='__main__':main()
