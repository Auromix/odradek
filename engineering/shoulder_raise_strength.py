#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent raised shoulder load-flow and analytic screening, no network/FEA."""
from pathlib import Path
import copy,hashlib,json,math,itertools
import numpy as np
import cadquery as cq
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from build_layout import frame,moved
from articulated_head_dynamics import ArticulatedHeadArm,FINGER_ORDER,p16_geometry
from review_articulated_dynamics import vee
from build_link12_study import shape_box,POST_XY
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/shoulder-raise-strength01'
G=9.80665;E=70000.;RHO=2.7e-6
NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)'
SOURCES={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(rel):
 p=ROOT/rel;SOURCES[rel]=sha(p);return json.loads(p.read_text())
def dump(name,data):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,indent=2)+'\n')
def loaded_step(rel,T):
 p=ROOT/rel;SOURCES[rel]=sha(p);s=cq.importers.importStep(str(p)).val();assert s.isValid() and len(s.Solids())==1;return moved(s,np.array(T))
def cross(v):
 x,y,z=v;return np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])

def model_inputs():
 source=read('engineering/generated/articulated-dynamics-review/model.json');trials=read('engineering/generated/articulated-dynamics-review/review.json');head=read('engineering/generated/head-mass04/mass-properties.json');raised=read('engineering/generated/shoulder-raise-01/part-placements.json');qa=read('engineering/generated/shoulder-raise-01/qa.json')
 assert qa['nominal_continuous_local_q2_domain_passed'] and raised['candidate_raise_mm']==35
 for n,h in qa['artifacts'].items():assert sha(ROOT/'engineering/generated/shoulder-raise-01'/n)==h
 model=copy.deepcopy(source);arm=model['arm'];dz=np.array([0.,0.,.035])
 for j in arm['joints'][1:]:j['origin_m']=(np.array(j['origin_m'])+dz).tolist();j['origin_mm']=(np.array(j['origin_mm'])+dz*1000).tolist()
 for b in arm['bodies']:
  if b['id'].startswith('L12_') and b['id']!='L12_hardware_reserve':
   r=raised['original_L12_instances'][b['id'][4:]];b.update(mass_kg=r['mass_kg'],com_home_m=r['com_world_m'],orientation_home=np.eye(3).tolist(),inertia_com_kg_m2=r['inertia_about_COM_world_axes_kg_m2'])
  elif b['id']=='L12_hardware_reserve':b['com_home_m']=raised['new_L12_original_aggregate']['com_world_m'];assert b['mass_kg']==.2
  elif b['preceding_joints']>=1:b['com_home_m']=(np.array(b['com_home_m'])+dz).tolist()
 arm['tool_home_transform'][2][3]+=.035;model['head_face_home_m']=(np.array(model['head_face_home_m'])+dz).tolist()
 authoritative=read('engineering/generated/raised-arm-integration01/model.json')
 for ours,theirs in zip(arm['bodies'],authoritative['arm']['bodies']):
  assert ours['id']==theirs['id']
  for field in ['mass_kg','com_home_m','orientation_home','inertia_com_kg_m2']:assert np.allclose(ours.get(field,np.eye(3)),theirs.get(field,np.eye(3)),atol=1e-12),(ours['id'],field)
 for ours,theirs in zip(arm['joints'],authoritative['arm']['joints']):assert np.allclose(ours['origin_m'],theirs['origin_m'],atol=1e-12)
 assert np.allclose(model['head_face_home_m'],authoritative['head_face_home_m']);model=authoritative;arm=model['arm']
 m=ArticulatedHeadArm(arm,model['head_bodies'],model['finger_joints'],model['head_face_home_m']);old=sum(b['mass_kg'] for b in source['arm']['bodies'])+sum(b['mass_kg'] for b in source['head_bodies']);new=sum(b['mass_kg'] for b in m.states(np.zeros(11)))
 assert abs(new-old-raised['added_original_metal_mass_kg'])<1e-10
 shapes={n:loaded_step('engineering/generated/shoulder-raise-01/'+r['file'],r['T_world_from_part_mm']) for n,r in raised['original_L12_instances'].items()}
 oldplace=read('engineering/generated/link12-study/part-placements.json');r=oldplace['instances']['rear_fork'];oldfork=loaded_step('engineering/generated/link12-study/'+r['part_id']+'.step',r['T_world_from_part_mm'])
 return m,model,source,trials,head,raised,shapes,oldfork

def body_forces(model,q,v=None,a=None,h=2e-4):
 q=np.array(q);v=np.zeros(11) if v is None else np.array(v);a=np.zeros(11) if a is None else np.array(a);state=model.states(q)
 minus=model.states(q-v*h+.5*a*h*h);plus=model.states(q+v*h+.5*a*h*h);rows=[]
 for b,bm,bp in zip(state,minus,plus):
  acc=(bp['p']-2*b['p']+bm['p'])/h**2;rdot=(bp['R']-bm['R'])/(2*h);rddot=(bp['R']-2*b['R']+bm['R'])/h**2
  w=vee(rdot@b['R'].T);alpha=vee(rddot@b['R'].T+rdot@rdot.T);f=b['mass_kg']*(acc-model.gravity);moment=b['I_world']@alpha+np.cross(w,b['I_world']@w)
  rows.append(dict(id=b['id'],p=b['p'],F=f,M_com=moment,mass_kg=b['mass_kg']))
 return rows,state

def wrench(rows,point):
 f=sum((r['F'] for r in rows),np.zeros(3));m=sum((r['M_com']+np.cross(r['p']-point,r['F']) for r in rows),np.zeros(3));return f,m

def interfaces(model,q,rows):
 T=model.arm.prefixes(q[:7])[1];R=T[:3,:3];ids={b['id']:b for b in model.arm.bodies};result={}
 anchors={'J2_rear':[0,-.0457,.205],'foot_group':[0,-.039,.1272],'J1_output':[0,0,.1052]}
 for name,p in anchors.items():
  selected=[]
  for r in rows:
   b=ids.get(r['id']);upstream=(b is not None and b['preceding_joints']==0)
   if upstream:continue
   if name=='J2_rear' and r['id'].startswith('L12_'):continue
   if name=='foot_group' and r['id']=='L12_output_adapter':continue
   selected.append(r)
  point=R@p+T[:3,3];F,M=wrench(selected,point);result[name]=dict(point_in_L12_home_m=p,force_N=(R.T@F).tolist(),moment_Nm=(R.T@M).tolist(),selected_body_ids=[r['id'] for r in selected],included_mass_kg=sum(r['mass_kg'] for r in selected))
 # Within one selected set, moment transport is an exact accounting identity.
 selected=[r for r in rows if r['id'] in result['J2_rear']['selected_body_ids']];A=R@anchors['J2_rear']+T[:3,3];B=R@anchors['foot_group']+T[:3,3];Fa,Ma=wrench(selected,A);Fb,Mb=wrench(selected,B);err=float(np.max(abs(Mb-Ma-np.cross(A-B,Fa))));assert err<1e-10
 return result,err

def gravity_bounds(model,head):
 """All-pose triangle bounds conditional on each explicitly supplied COM model."""
 joints=[np.array(j['origin_m']) for j in model.arm.joints];j2=joints[1];path7=sum(np.linalg.norm(joints[k+1]-joints[k]) for k in range(1,6));rows=[]
 for b in model.arm.bodies:
  n=b['preceding_joints']
  if n==0:continue
  c=np.array(b['com_home_m'])
  if n==1:radius=np.linalg.norm((c-j2)[:2]);basis='Rigid preceding1 mass; only horizontal lever contributes to gravity.'
  else:radius=sum(np.linalg.norm(joints[k+1]-joints[k]) for k in range(1,n-1))+np.linalg.norm(c-joints[n-1]);basis='Polygonal path fromJ2 toCOM; every downstream rotation preserves each segment length.'
  rows.append(dict(id=b['id'],mass_kg=b['mass_kg'],radius_from_J2_m=float(radius),basis=basis))
 for b in model.head_bodies:
  c=np.array(b['com_head_home_m']);g=b['kinematic_group'];f=model.fingers.get(b.get('finger'));offset=model.face-joints[6]
  if g=='head_fixed':local=np.linalg.norm(offset+c)
  elif g=='finger_rotor':pivot=np.array(f['pivot_head_mm'])*.001;local=np.linalg.norm(offset+pivot)+np.linalg.norm(c-pivot)
  else:
   pivot=np.array(f['pivot_head_mm'])*.001;t=-np.array(f['closing_axis_head']);base=pivot-.018*f['mechanical_mirror_sign']*t+np.array([0,0,-.123]);local=np.linalg.norm(offset+base)+np.linalg.norm(c-base)
   if g=='P16_slider':local+=max(abs(p16_geometry(math.radians(x))[0]-p16_geometry(0)[0]) for x in f['range_deg'])
  rows.append(dict(id=b['id'],mass_kg=b['mass_kg'],radius_from_J2_m=float(path7+local),basis='Head rigid/pivot triangle; P16slider additionally includes full stated stroke variation; internal mass remains proxy.'))
 result={}
 for name,anchor in [('J2_rear',[0,-.0457,.205]),('foot_group',[0,-.039,.1272]),('J1_output',[0,0,.1052])]:
  selected=[r for r in rows if not(name=='J2_rear' and r['id'].startswith('L12_')) and not(name=='foot_group' and r['id']=='L12_output_adapter')];horizontal=np.linalg.norm((np.array(anchor)-j2)[:2]);mass=sum(r['mass_kg'] for r in selected);B=G*sum(r['mass_kg']*(r['radius_from_J2_m']+horizontal) for r in selected)
  remainder_radius=path7+np.linalg.norm(model.face-joints[6])+.25+horizontal;U=.45*G*remainder_radius
  uncertainty=2*G*.1+sum(b['mass_kg'] for b in model.head_bodies)*G*.05
  result[name]=dict(nominal_mass_kg=mass,nominal_vertical_force_N=mass*G,nominal_moment_norm_bound_Nm=B,planning_remainder_high_mass_kg=.45,conditional_remainder_moment_bound_Nm=U,planning_remainder_face_sphere_radius_m=.25,known_head_COM_sensitivity_m=.05,object_COM_sensitivity_m=.1,additional_COM_moment_sensitivity_Nm=uncertainty,research_multiplier=1.5,expanded_force_N=1.5*(mass+.45)*G,expanded_moment_bound_Nm=1.5*(B+U+uncertainty),limits='Remainder sphere0.25m is a NEW conditional planning enclosure, not a verified all-finger-state bound.1.5 multiplier and COM offsets are study assumptions, not certified safety factors.')
 return dict(body_radius_bounds=rows,interfaces=result,planning_remainder_source=head['planning_remainder'],not_an_inertia_or_trajectory_bound=True)

def bolt_group(points,normal,F,M):
 T=frame([0,0,0],normal)[:3,:3];f=T.T@F;m=T.T@M*1000.;p=np.array(points,float);p-=p.mean(axis=0);n=len(p);C=p.T@p
 axial=f[2]/n+p@np.linalg.solve(C,[-m[1],m[0]]);shear=f[:2]/n+np.column_stack((-p[:,1],p[:,0]))*m[2]/np.sum(p*p)
 recover_f=np.r_[shear.sum(axis=0),axial.sum()];recover_m=np.r_[axial@p[:,1],-axial@p[:,0],sum(np.cross(np.r_[r,0],np.r_[s,0])[2] for r,s in zip(p,shear))]
 err=max(np.max(abs(recover_f-f)),np.max(abs(recover_m-m)));assert err<1e-8
 return dict(axial_signed_N=axial.tolist(),in_plane_shear_N=shear.tolist(),max_absolute_axial_N=float(max(abs(axial))),max_shear_N=float(max(np.linalg.norm(shear,axis=1))),local_force_N=f.tolist(),local_moment_Nm=(m*.001).tolist(),equilibrium_error_mixed_N_Nmm=float(err))

def group_inputs():
 d=read('docs/engineering/sources/rh-interface-extraction.json');m=next(x for x in d['models'] if x['id']=='RH25-B')['unified_joint_interface'];out=[x['xy_mm'] for x in m['output_holes']['points']];fixed=[x['xy_mm'] for x in m['fixed_through_holes']['points']]
 return {'J2_rear':dict(points=fixed,normal=[0,1,0],stress_area_mm2=8.78,nominal_engagement_mm=14,thread='M4x0.7',friction_radius_mm=51.),'foot_group':dict(points=POST_XY.tolist(),normal=[0,0,1],stress_area_mm2=20.1,nominal_engagement_mm=13,thread='M6x1',friction_radius_mm=None),'J1_output':dict(points=out,normal=[0,0,1],stress_area_mm2=8.78,nominal_engagement_mm=None,thread='M4x0.7 lengthTBD',friction_radius_mm=38.5)}

def groups_for_wrenches(wrenches,groups):
 result={}
 for name,w in wrenches.items():
  b=groups[name];r=bolt_group(b['points'],b['normal'],np.array(w['force_N']),np.array(w['moment_Nm']));As=b['stress_area_mm2'];ax=np.array(r['axial_signed_N']);sh=np.linalg.norm(r['in_plane_shear_N'],axis=1)
  r.update(nominal_axial_external_stress_MPa=float(max(abs(ax))/As),nominal_shear_external_stress_MPa=float(max(sh)/As),nominal_external_VM_like_MPa=float(max(np.sqrt((ax/As)**2+3*(sh/As)**2))),thread=b['thread'],nominal_engagement_mm=b['nominal_engagement_mm'],pull_per_effective_engagement_N_per_mm={str(L):r['max_absolute_axial_N']/L for L in [4,6,10,13,14]},no_separation_equal_stiffness_preload_per_bolt_threshold_N=r['max_absolute_axial_N'])
  if b['friction_radius_mm']:
   r['conditional_friction_total_clamp_N']={str(mu):(np.linalg.norm(r['local_force_N'][:2])+abs(r['local_moment_Nm'][2])*1000/b['friction_radius_mm'])/mu for mu in [.08,.15,.20]}
  r['limits']='Signed elastic equal-stiffness reactions, not solved bolt tension/contact. VM-like external load omits preload/torsion/bending. Friction radius is assumed, not verified contact pressure. N/mm is not a thread stripping capacity.';result[name]=r
 return result

def section_properties(shape,z):
 t=.001;slab=shape.intersect(shape_box(300,300,t,[0,0,z]));assert slab.Solids();g=GProp_GProps();BRepGProp.VolumeProperties_s(slab.wrapped,g);A=g.Mass()/t;centre=np.array(g.CentreOfMass().Coord());I=g.MatrixOfInertia();Q=np.array([[I.Value(2,2),-I.Value(1,2)],[-I.Value(1,2),I.Value(1,1)]])/t-np.eye(2)*A*t*t/12
 islands=[];Qu=np.zeros((2,2))
 for s in slab.Solids():
  q=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,q);a=q.Mass()/t;c=np.array(q.CentreOfMass().Coord());ii=q.MatrixOfInertia();qi=np.array([[ii.Value(2,2),-ii.Value(1,2)],[-ii.Value(1,2),ii.Value(1,1)]])/t-np.eye(2)*a*t*t/12;bb=s.BoundingBox();Qu+=qi
  islands.append(dict(area_mm2=a,centroid_world_mm=c.tolist(),Q_area_mm4=qi.tolist(),relative_bbox_xy_mm=[[bb.xmin-c[0],bb.ymin-c[1]],[bb.xmax-c[0],bb.ymax-c[1]]]))
 bb=slab.BoundingBox();assert min(np.linalg.eigvalsh(Qu))>0;assert min(np.linalg.eigvalsh(Q-Qu))>-1e-5
 return dict(z_mm=float(z),area_mm2=A,centroid_world_mm=centre.tolist(),Q_composite_mm4=Q.tolist(),Q_no_axial_couple_mm4=Qu.tolist(),bbox_relative_xy_mm=[[bb.xmin-centre[0],bb.ymin-centre[1]],[bb.xmax-centre[0],bb.ymax-centre[1]]],islands=islands)

def beam_compliance(sections,end,E=E,kind='composite'):
 matrices=[]
 for s in sections:
  # Input [Fxyz in N, Mxyz in Nmm]. Internal moment at each real centroid.
  lever=np.array(end)-np.array(s['centroid_world_mm']);B=np.hstack((cross(lever),np.eye(3)));D=np.stack((-B[1],B[0]));Q=np.array(s['Q_'+('composite' if kind=='composite' else 'no_axial_couple')+'_mm4']);A=np.zeros((6,6));A[2,2]=1/s['area_mm2'];matrices.append((D.T@np.linalg.inv(Q)@D+A)/E)
 C=np.trapezoid(matrices,[s['z_mm'] for s in sections],axis=0);assert np.max(abs(C-C.T))<1e-9 and min(np.linalg.eigvalsh(C))>-1e-8
 return C

def stress_at_sections(sections,wrench,end,kind):
 F=np.array(wrench['force_N']);M=np.array(wrench['moment_Nm'])*1000;rows=[]
 for s in sections:
  mi=M+np.cross(np.array(end)-s['centroid_world_mm'],F);Q=np.array(s['Q_composite_mm4'] if kind=='composite' else s['Q_no_axial_couple_mm4']);b=np.linalg.solve(Q,[-mi[1],mi[0]]);boxes=[s['bbox_relative_xy_mm']] if kind=='composite' else [i['relative_bbox_xy_mm'] for i in s['islands']]
  maxsigma=max(abs(F[2]/s['area_mm2']+b@np.array([x,y])) for box in boxes for x in [box[0][0],box[1][0]] for y in [box[0][1],box[1][1]])
  rows.append(dict(z_mm=s['z_mm'],nominal_axial_plus_bending_bbox_upper_MPa=float(maxsigma),cross_section_islands=len(s['islands'])))
 return max(rows,key=lambda x:x['nominal_axial_plus_bending_bbox_upper_MPa'])

def beams(new_shape,old_shape):
 datasets={};result={}
 for label,shape,top in [('raised77_8',new_shape,205.),('old42_8',old_shape,170.)]:
  zs=np.linspace(127.2005,top-.0005,157 if top==205 else 87);sections=[]
  for i,z in enumerate(zs):
   sections.append(section_properties(shape,z))
   if i%40==0:print('section',label,i,len(zs),flush=True)
  datasets[label]=sections;end=[0,-45.7,top];cc=beam_compliance(sections,end);cu=beam_compliance(sections,end,kind='uncoupled');coarse=beam_compliance(sections[::2],end)
  assert min(np.linalg.eigvalsh(cu-cc))>-1e-8
  normal=np.maximum(abs(cc),1e-12);active=abs(cc)>1e-6;error=float(np.max(abs(cc-coarse)[active]/normal[active]));examples={}
  for axis in [0,1]:
   w=np.zeros(6);w[3+axis]=100000;examples['pure100Nm_about'+('X' if axis==0 else 'Y')]=dict(composite_response_mm_and_rad=(cc@w).tolist(),no_axial_couple_response_mm_and_rad=(cu@w).tolist())
  result[label]=dict(span_mm=top-127.2,section_count=len(sections),E_N_mm2=E,compliance_composite=cc.tolist(),compliance_no_axial_couple=cu.tolist(),coarse_refinement_relative_difference_on_active_entries=error,examples=examples)
 # Analytic constant-section verification checks units and end-force/moment factors.
 I=100000.;L=77.8;uniform=[dict(z_mm=z,area_mm2=1000.,centroid_world_mm=[0,0,z],Q_composite_mm4=[[I,0],[0,I]]) for z in np.linspace(0,L,1001)];C=beam_compliance(uniform,[0,0,L]);expected=L**3/(3*E*I);assert abs(C[0,0]/expected-1)<1e-6;assert abs(C[3,3]/(L/E/I)-1)<1e-10;assert abs(abs(C[0,4])/(L*L/2/E/I)-1)<1e-10
 return result,datasets,dict(unit_force_deflection_mm_per_N=C[0,0],analytical_mm_per_N=expected,unit_moment_rotation_rad_per_Nmm=C[3,3],pass_=True)

def case_analysis(model,trial_data,groups,sections,beamdata):
 p=read('engineering/parameters/r4-layout.json');cases=[]
 for name,angles in p['poses_deg'].items():cases.append((name+'_open',np.r_[np.deg2rad(angles),np.zeros(4)],np.zeros(11),np.zeros(11)))
 for sign in [-1,1]:cases.append(('q2_horizontal_'+str(sign),np.r_[np.deg2rad([0,90*sign,0,0,0,0,0]),np.zeros(4)],np.zeros(11),np.zeros(11)))
 for t in trial_data['trials']:cases.append(('existing_math_trial_'+str(t['trial']),np.deg2rad(t['q_deg']),np.array(t['qd_rad_s']),np.array(t['qdd_rad_s2'])))
 results=[];allerr=0.;rootc=np.array(beamdata['raised77_8']['compliance_composite']);rootu=np.array(beamdata['raised77_8']['compliance_no_axial_couple'])
 for name,q,v,a in cases:
  rows,state=body_forces(model,q,v,a);ws,err=interfaces(model,q,rows);allerr=max(allerr,err);other,_=body_forces(model,q,v,a,1e-4);ww,_=interfaces(model,q,other)
  ref=max(max(np.max(abs(np.array(ws[n][k])-ww[n][k])) for k in ['force_N','moment_Nm']) for n in ws);assert ref<1e-3
  generalized=sum((b['J'][:3].T@r['F']+b['J'][3:].T@r['M_com'] for r,b in zip(rows,state)),np.zeros(11));mcg=model.inverse_dynamics(q,v,a);mcgerr=float(np.max(abs(generalized-mcg)));assert mcgerr<1e-3
  groupsout=groups_for_wrenches(ws,groups);W=np.r_[ws['J2_rear']['force_N'],np.array(ws['J2_rear']['moment_Nm'])*1000]
  beam=dict(composite_nominal=stress_at_sections(sections,ws['J2_rear'],[0,-45.7,205],'composite'),no_axial_couple_nominal=stress_at_sections(sections,ws['J2_rear'],[0,-45.7,205],'uncoupled'),composite_displacement_mm_and_rotation_rad=(rootc@W).tolist(),no_axial_couple_displacement_mm_and_rotation_rad=(rootu@W).tolist())
  results.append(dict(id=name,q_deg=np.rad2deg(q).tolist(),qd_rad_s=v.tolist(),qdd_rad_s2=a.tolist(),wrenches=ws,bolt_groups=groupsout,beam_screen=beam,moment_transport_error_Nm=err,body_finite_difference_two_step_max_error_N_or_Nm=ref,body_effort_vs_MCG_max_error_Nm=mcgerr,qualified_physical_trajectory=False))
  print('case',name,ws['foot_group']['moment_Nm'],flush=True)
 return results,allerr

def envelope_screen(bounds,groups,sections,beamdata):
 out=[];cc=np.array(beamdata['raised77_8']['compliance_composite']);cu=np.array(beamdata['raised77_8']['compliance_no_axial_couple'])
 # Discrete directions are examples for vector load flow; exact per-hole force
 # bounds below separately remove any dependence on the direction sample grid.
 for kind in ['nominal','expanded']:
  envelopes={}
  for name,b in bounds['interfaces'].items():
   F=b['nominal_vertical_force_N'] if kind=='nominal' else b['expanded_force_N'];M=b['nominal_moment_norm_bound_Nm'] if kind=='nominal' else b['expanded_moment_bound_Nm'];gg=groups[name]
   zero=bolt_group(gg['points'],gg['normal'],np.array([0,0,F]),np.zeros(3));mx=bolt_group(gg['points'],gg['normal'],np.zeros(3),np.array([1.,0,0]));my=bolt_group(gg['points'],gg['normal'],np.zeros(3),np.array([0,1.,0]));n=np.array(zero['axial_signed_N']);nx=np.array(mx['axial_signed_N']);ny=np.array(my['axial_signed_N']);bound=abs(n)+M*np.hypot(nx,ny)
   shear=zero['max_shear_N']+M*max(np.linalg.norm(x) for x in np.array(mx['in_plane_shear_N'])+0)+M*max(np.linalg.norm(x) for x in np.array(my['in_plane_shear_N'])+0)
   envelopes[name]=dict(force_N=[0,0,F],gravity_moment_XY_norm_bound_Nm=M,per_hole_absolute_axial_bound_N=bound.tolist(),max_absolute_axial_bound_N=float(max(bound)),external_axial_stress_bound_MPa=float(max(bound)/gg['stress_area_mm2']),in_plane_shear_triangle_bound_N=float(shear),basis='Exact max of scalar axial linear function over Mx²+My²<=B²; independent triangle inequality for shear. These simultaneous maxima need not occur in one pose.')
  sample=[]
  for angle in np.linspace(0,2*np.pi,73):
   w={n:dict(force_N=e['force_N'],moment_Nm=[e['gravity_moment_XY_norm_bound_Nm']*math.cos(angle),e['gravity_moment_XY_norm_bound_Nm']*math.sin(angle),0]) for n,e in envelopes.items()};W=np.r_[w['J2_rear']['force_N'],np.array(w['J2_rear']['moment_Nm'])*1000];sample.append(dict(angle_deg=float(np.rad2deg(angle)),bolt_groups=groups_for_wrenches(w,groups),composite_stress=stress_at_sections(sections,w['J2_rear'],[0,-45.7,205],'composite'),uncoupled_stress=stress_at_sections(sections,w['J2_rear'],[0,-45.7,205],'uncoupled'),composite_response_mm_and_rad=(cc@W).tolist(),uncoupled_response_mm_and_rad=(cu@W).tolist()))
  out.append(dict(id=kind+'_gravity_triangle',exact_axial_bounds=envelopes,direction_examples=sample,direction_samples_are_not_stress_global_extrema=True))
 # Separate drive-reaction sensitivity, not added on top of an already derived
 # dynamics wrench and not asserted to be continuously available at zero speed.
 F=bounds['interfaces']['J2_rear']['expanded_force_N'];w0=dict(force_N=[0,0,F],moment_Nm=[0,157,0]);w={}
 A=np.array([0,-.0457,.205])
 for name,B in [('J2_rear',A),('foot_group',np.array([0,-.039,.1272])),('J1_output',np.array([0,0,.1052]))]:w[name]=dict(force_N=w0['force_N'],moment_Nm=(np.array(w0['moment_Nm'])+np.cross(A-B,w0['force_N'])).tolist())
 W=np.r_[w0['force_N'],np.array(w0['moment_Nm'])*1000];out.append(dict(id='separate_J2_catalog_peak157_about_Y',wrenches=w,bolt_groups=groups_for_wrenches(w,groups),composite_stress=stress_at_sections(sections,w0,[0,-45.7,205],'composite'),uncoupled_stress=stress_at_sections(sections,w0,[0,-45.7,205],'uncoupled'),composite_response_mm_and_rad=(cc@W).tolist(),uncoupled_response_mm_and_rad=(cu@W).tolist(),scope='157Nm aboutJ2Y plus independent expanded gravity force; separate synthetic input, no added downstream inertial wrench or implied stall/continuous torque rating.'))
 return out

def exact_direction_stress_bound(sections,Fz,B,end,kind):
 answers=[]
 for s in sections:
  Q=np.array(s['Q_composite_mm4'] if kind=='composite' else s['Q_no_axial_couple_mm4']);inv=np.linalg.inv(Q);m0=np.cross(np.array(end)-s['centroid_world_mm'],[0,0,Fz]);c0=inv@[-m0[1],m0[0]];cx=inv@[0,1000];cy=inv@[-1000,0];boxes=[s['bbox_relative_xy_mm']] if kind=='composite' else [i['relative_bbox_xy_mm'] for i in s['islands']]
  value=max(abs(Fz/s['area_mm2']+c0@np.array([x,y]))+B*math.hypot(cx@np.array([x,y]),cy@np.array([x,y])) for box in boxes for x in [box[0][0],box[1][0]] for y in [box[0][1],box[1][1]])
  answers.append(dict(z_mm=s['z_mm'],nominal_stress_MPa=float(value)))
 return max(answers,key=lambda r:r['nominal_stress_MPa'])

def summary_data(cases,bounds,envelopes,beamdata,sections,groups):
 summary={}
 for name in groups:
  summary[name]=dict(max_case_force_norm_N=max(np.linalg.norm(c['wrenches'][name]['force_N']) for c in cases),max_case_moment_norm_Nm=max(np.linalg.norm(c['wrenches'][name]['moment_Nm']) for c in cases),worst_sample_axial=max((dict(case=c['id'],N=c['bolt_groups'][name]['max_absolute_axial_N']) for c in cases),key=lambda r:r['N']),worst_sample_VM_like=max((dict(case=c['id'],MPa=c['bolt_groups'][name]['nominal_external_VM_like_MPa']) for c in cases),key=lambda r:r['MPa']))
 analytical={}
 for k in ['nominal','expanded']:
  d=bounds['interfaces']['J2_rear'];F=d[k+'_vertical_force_N'] if k=='nominal' else d['expanded_force_N'];B=d['nominal_moment_norm_bound_Nm'] if k=='nominal' else d['expanded_moment_bound_Nm'];a={}
  for label,key in [('composite','compliance_composite'),('uncoupled','compliance_no_axial_couple')]:
   C=np.array(beamdata['raised77_8'][key]);w=np.zeros(6);w[2]=F;response=np.abs(C@w)+B*1000*np.hypot(C[:,3],C[:,4]);a[label]=dict(exact_moment_direction_stress_at_sampled_sections=exact_direction_stress_bound(sections,F,B,[0,-45.7,205],label),exact_per_component_response_bound_mm_and_rad=response.tolist())
  analytical[k]=a
 return dict(interface_case_maxima=summary,beam_direction_bounds=analytical,beam_model_limits='Loads from J2-side bodies only for beam responses; fork/front/hardware self loads are included in foot/J1 force-flow but not distributed in these beam references. Curved-contact loading collapsed toaxis; not complete actual structure bounds.',no_FE_analysis_performed=True)

def draw(beamdata,sections,summary,bounds):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(2,2,figsize=(12,9));s=sections['raised77_8'];z=[r['z_mm']-127.2 for r in s]
 for i,name in [(0,'Qxx / bending aboutY'),(1,'Qyy / bending aboutX')]:
  ax[0,0].semilogy(z,[r['Q_composite_mm4'][i][i] for r in s],label=name+' composite');ax[0,0].semilogy(z,[r['Q_no_axial_couple_mm4'][i][i] for r in s],ls='--',label=name+' no couple')
 ax[0,0].set(xlabel='Height above foot / mm',ylabel='Net area moment / mm4',title='Actual raised fork sections');ax[0,0].legend(fontsize=8)
 vals=[];labels=[]
 for k in ['old42_8','raised77_8']:
  for kind in ['composite','no_axial_couple']:
   C=np.array(beamdata[k]['compliance_'+kind]);vals.append(np.linalg.norm((C@np.array([0,0,0,0,100000,0]))[:3]));labels.append(('Old 42.8' if k.startswith('old') else 'New 77.8')+'\n'+('composite' if kind=='composite' else 'no couple'))
 ax[0,1].bar(labels,vals,color=['#65958e','#b5c9c5','#d49754','#e7c5a0']);ax[0,1].set(ylabel='Translation / mm',title='100 Nm aboutY: beam-family examples')
 names=list(bounds['interfaces']);x=np.arange(3)
 ax[1,0].bar(x-.18,[bounds['interfaces'][n]['nominal_moment_norm_bound_Nm'] for n in names],.36,label='Nominal model bound');ax[1,0].bar(x+.18,[bounds['interfaces'][n]['expanded_moment_bound_Nm'] for n in names],.36,label='Conditional planning x1.5');ax[1,0].set(xticks=x,xticklabels=['J2 rear','Foot','J1 output'],ylabel='Moment norm bound / Nm',title='Gravity force-flow envelopes');ax[1,0].legend(fontsize=8)
 ax[1,1].bar(['Composite','No axial couple'],[summary['beam_direction_bounds']['expanded'][k]['exact_moment_direction_stress_at_sampled_sections']['nominal_stress_MPa'] for k in ['composite','uncoupled']],color=['#65958e','#d49754']);ax[1,1].set(ylabel='Nominal stress / MPa',title='Conditional expanded load / sampled sections')
 for a in ax.flat:a.grid(axis='y',alpha=.2)
 fig.suptitle('SHOULDER-RAISE-STRENGTH01 | analytic screening, no FEA or load qualification',fontsize=14);fig.tight_layout(rect=[0,.055,1,.95]);fig.text(.04,.016,'Curved collar/contact/bolt compliance and fatigue remain unresolved. Beam models are conditional references, not whole-part bounds.',fontsize=9);fig.savefig(OUT/'screening.png',dpi=160);plt.close(fig)

def main():
 m,model,oldmodel,trials,head,raised,shapes,oldfork=model_inputs();print('model masses matched root',flush=True);groups=group_inputs();bom=read('engineering/generated/link12-study/bom.json');original=read('engineering/generated/link12-study/evidence.json')
 beamdata,sections,unit=beams(shapes['rear_fork'],oldfork);dump('sections.json',dict(revision='SHOULDER-RAISE-STRENGTH01',slices=sections,beam_family=beamdata,unit_check=unit,limits='0.001mm BREP slices sampled along height; not continuum3D stress or torsional rigidity.'))
 cases,err=case_analysis(m,trials,groups,sections['raised77_8'],beamdata);bounds=gravity_bounds(m,head)
 for c in cases:
  if max(abs(np.array(c['qd_rad_s'])))==0 and max(abs(np.array(c['qdd_rad_s2'])))==0:
   for n,w in c['wrenches'].items():assert np.linalg.norm(w['moment_Nm'])<=bounds['interfaces'][n]['nominal_moment_norm_bound_Nm']+1e-8
 env=envelope_screen(bounds,groups,sections['raised77_8'],beamdata);summ=summary_data(cases,bounds,env,beamdata,sections['raised77_8'],groups)
 # Existing output ribs did not change. Reuse actual slice source, not the old
 # forces; feed new exact direction-free foot axial load bounds into its model.
 ribs=original['load_screening'].get('rib_strip_actual_net_sections')
 if ribs is None:
  from build_link12_study import rib_section_screen
  ribs=rib_section_screen(shapes['output_adapter'])
 coef=max(r['stress_per_N_MPa'] for r in ribs);defl=max(r['deflection_per_N_mm'] for r in ribs)
 ribscreen={e['id']:dict(isolated_actual16mm_rib_strip_stress_MPa=e['exact_axial_bounds']['foot_group']['max_absolute_axial_bound_N']*coef,isolated_rib_deflection_mm=e['exact_axial_bounds']['foot_group']['max_absolute_axial_bound_N']*defl) for e in env if 'exact_axial_bounds' in e}
 for rel in ['engineering/shoulder_raise_strength.py','engineering/articulated_head_dynamics.py','engineering/kinematics.py','engineering/build_link12_study.py','engineering/build_layout.py','engineering/review_articulated_dynamics.py']:SOURCES[rel]=sha(ROOT/rel)
 result=dict(revision='SHOULDER-RAISE-STRENGTH01',license='CC-BY-NC-4.0',required_notice=NOTICE,model_source='engineering/generated/raised-arm-integration01/model.json',source_hashes=SOURCES,modeled_mass_including_fixedJ1_and2kg_object_kg=sum(b['mass_kg'] for b in m.states(np.zeros(11))),new_L12_original_metal=raised['new_L12_original_aggregate'],hardware_policy='L12 whole0.20kg reserve, COM at new metalCOM, old50mm-cube inertia proxy. At foot, allreserve allocated downstream as explicit scenario; actual fastener positions/mass not identified.',groups=groups,beam_response_coordinate_contract=dict(order=['ux_mm','uy_mm','uz_mm','thetaX_rad','thetaY_rad','thetaZ_NOT_MODELED'],last_component_zero_is_omitted_physics_not_a_rigidity_claim=True,forces_N_and_moments_Nmm_in_compliance_input=True),material=dict(candidate='6061-T6, product form/heat treatment/billet thickness not certified',density_kg_m3=2700,E_N_mm2=E,E_sensitivity_N_mm2=[66500,70000,73500],yield_applied_MPa=None,source=bom['sources'],reason_no_yield_pass='Stored datasheet extract is not a controlled thick-billet guarantee for this49mm-legged milled part. No material name or oldthinwall240MPa value treated as release.'),load_cases=cases,gravity_bounds=bounds,envelope_screens=env,beam_family=beamdata,output_rib_screen=ribscreen,actual_rib_slice_inputs=ribs,summary=summ,moment_transport_max_error_Nm=err,beam_unit_check=unit,manufacturing_release=False,physical_payload_qualified=False,FEA_performed=False,unresolved=['OEM M4 effective thread start/end and selected length','Actual contact stiffness/preload/friction and separation','Thin1.3mm fixedM4 inneredge and aluminum thread breakout','Collar load distribution above/below axis and load transfer between legs','Root fillets/notches, machining, residual stresses and3D strain','Fatigue spectrum, repeated preload, emergency/contact/stop loads','Unknown head mass/inertia and true joint rotor distribution','Full-arm/cable-qualified dynamic operating domain'])
 dump('study.json',result);draw(beamdata,sections,summ,bounds);assert all(sha(ROOT/n)==h for n,h in SOURCES.items());dump('qa.json',dict(all_source_hashes_unchanged=True,source_count=len(SOURCES),generator_sha256=sha(__file__),force_moment_equilibrium_passed=True,actual_77_8mm_span_used=True,root_model_fields_independently_matched=True,beam_unit_check=unit,beam_family_energy_order_checked=True,FEA_performed=False,source_hashes=SOURCES,artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='qa.json'}));print('READY analytic screening',json.dumps(summ),flush=True)
if __name__=='__main__':main()
