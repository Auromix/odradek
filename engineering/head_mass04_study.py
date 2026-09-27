#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""HEAD-MASS04: read frozen named STEP; integrate nominal/proxy inertial inputs.
No HEAD03 writes. No arm dynamics. Public relative_transform() takes radians/SI.
"""
from pathlib import Path
import csv, hashlib, json, math, re
import numpy as np
import cadquery as cq
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'engineering/generated/head-integrated-03'
OUT=ROOT/'engineering/generated/head-mass04'
NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(name,data):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,indent=2)+'\n')
def skew(v):
 x,y,z=v;return np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])
def rotation(axis,angle):
 axis=np.asarray(axis,dtype=float);axis/=np.linalg.norm(axis);K=skew(axis)
 return np.eye(3)+math.sin(angle)*K+(1-math.cos(angle))*(K@K)
def shift_inertia(m,d):
 d=np.asarray(d);return m*((d@d)*np.eye(3)-np.outer(d,d))

def geometry_properties(s):
 """OCC volume integrals: V mm^3, COM mm, raw central tensor mm^5.
 I_per_mass = (Iraw / V) * 1e-6 m^2; multiply by kg, never by g.
 """
 g=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,g)
 v=g.Mass();c=np.array(g.CentreOfMass().Coord())*.001
 a=g.MatrixOfInertia();raw=np.array([[a.Value(i,j) for j in [1,2,3]] for i in [1,2,3]])
 assert v>0 and np.isfinite(raw).all()
 return dict(volume_mm3=v,com_m=c,inertia_per_mass_m2=raw/v*1e-6)

def unit_checks():
 d=np.array([.010,.020,.030]);mass=2.;box=cq.Workplane('XY').box(*(d*1000)).val();p=geometry_properties(box)
 expected=mass/12*np.diag([d[1]**2+d[2]**2,d[0]**2+d[2]**2,d[0]**2+d[1]**2]);calc=mass*p['inertia_per_mass_m2']
 trans=geometry_properties(box.translate((500,600,700)));rot=geometry_properties(box.rotate((0,0,0),(1,2,3),37));R=rotation([1,2,3],math.radians(37))
 scaled=geometry_properties(cq.Workplane('XY').box(*(d*2000)).val())
 checks=dict(box_volume_mm3=p['volume_mm3'],box_expected_inertia_kg_m2=expected.tolist(),box_calculated_inertia_kg_m2=calc.tolist(),box_error_kg_m2=float(np.max(abs(calc-expected))),translation_invariance_error_m2=float(np.max(abs(trans['inertia_per_mass_m2']-p['inertia_per_mass_m2']))),rotation_covariance_error_m2=float(np.max(abs(rot['inertia_per_mass_m2']-R@p['inertia_per_mass_m2']@R.T))),double_size_same_mass_inertia_ratio=[float(scaled['inertia_per_mass_m2'][i,i]/p['inertia_per_mass_m2'][i,i]) for i in range(3)],double_size_fixed_density_mass_ratio=scaled['volume_mm3']/p['volume_mm3'],fixed_density_inertia_ratio=scaled['volume_mm3']/p['volume_mm3']*scaled['inertia_per_mass_m2'][0,0]/p['inertia_per_mass_m2'][0,0])
 assert checks['box_error_kg_m2']<1e-15 and checks['translation_invariance_error_m2']<1e-15 and checks['rotation_covariance_error_m2']<1e-15
 assert np.allclose(checks['double_size_same_mass_inertia_ratio'],4) and abs(checks['fixed_density_inertia_ratio']-32)<1e-10
 return checks

def load_named(path):
 a=cq.Assembly.importStep(str(path));rows={}
 def visit(node,parent):
  loc=parent*node.loc
  if isinstance(node.obj,cq.Shape):
   assert node.name not in rows;rows[node.name]=node.obj.moved(loc)
  elif node.obj is not None:raise TypeError((node.name,type(node.obj)))
  for child in node.children:visit(child,loc)
 visit(a,cq.Location());assert len(rows)==697 and all(s.isValid() and len(s.Solids())==1 for s in rows.values())
 return rows

def p16_kin(q,joint):
 """Reconstructed from frozen manifest, independent of CAD build implementation."""
 p=joint['P16'];a=p['a_mm']*.001;D=p['D_mm']*.001;phase=math.radians(p['phase_deg']);A=np.array(p['base_local_xuz_mm'])*.001
 B=np.array([a*math.cos(q-phase),A[1],a*math.sin(q-phase)]);L=np.linalg.norm(B-A);w=(B-A)/L
 R=np.column_stack(([-w[2],0,w[0]],[0,-1,0],w));assert abs(np.linalg.det(R)-1)<1e-12
 phi=math.atan2(joint['pivot_head_mm'][1],joint['pivot_head_mm'][0]);F=rotation([0,0,1],phi)@np.diag([1,joint['mechanical_mirror_sign'],1])
 root=np.array(joint['pivot_head_mm'])*.001
 return dict(A_head=F@A+root,L=L,R=R,F=F,rod_axis_head=F@R[:,2])

def relative_transform(group,q,joint=None):
 """Return proper R,t: c(q)=R*c(home)+t, all lengths m, q radians."""
 if group=='head_fixed':return np.eye(3),np.zeros(3)
 if group=='finger_rotor':
  R=rotation(joint['closing_axis_head'],q);pivot=np.array(joint['pivot_head_mm'])*.001
  return R,pivot-R@pivot
 k=p16_kin(q,joint);h=p16_kin(0,joint);R=k['F']@k['R']@h['R'].T@h['F'].T;t=k['A_head']-R@h['A_head']
 if group=='P16_slider':t+=k['rod_axis_head']*(k['L']-h['L'])
 else:assert group=='P16_body'
 assert abs(np.linalg.det(R)-1)<1e-12 and np.max(abs(R@R.T-np.eye(3)))<1e-12
 return R,t

def classify(part):
 if part['material']=='P16_envelope':
  local=part['id'].split('_P16_envelope_',1)[1];group='P16_body' if local in ['case','guide'] else 'P16_slider';assert local in ['case','guide','slider','tip']
 elif part['finger']:group='finger_rotor'
 else:group='head_fixed'
 body='head_fixed' if group=='head_fixed' else part['finger']+'_'+group
 return group,body

def tensor_check(I):
 sym=float(np.max(abs(I-I.T)));e=np.linalg.eigvalsh((I+I.T)/2);assert sym<1e-12 and e.min()>-1e-12 and e[-1]<=e[0]+e[1]+1e-12
 return dict(symmetry_error_kg_m2=sym,minimum_eigenvalue_kg_m2=float(e.min()),principal_triangle_margin_kg_m2=float(e[0]+e[1]-e[2]))

def combine(rows):
 m=sum(x['mass_kg'] for x in rows);assert m>0;c=sum(x['mass_kg']*np.array(x['com_head_home_m']) for x in rows)/m
 I=sum(np.array(x['inertia_about_COM_head_axes_kg_m2'])+shift_inertia(x['mass_kg'],np.array(x['com_head_home_m'])-c) for x in rows)
 return dict(mass_kg=m,com_head_home_m=c.tolist(),inertia_about_COM_head_axes_kg_m2=I.tolist())

def transform_body(row,q,joints):
 R,t=relative_transform(row['kinematic_group'],q,joints.get(row.get('finger')));c=R@np.array(row['com_head_home_m'])+t;I=R@np.array(row['inertia_about_COM_head_axes_kg_m2'])@R.T
 return {**row,'com_head_home_m':c.tolist(),'inertia_about_COM_head_axes_kg_m2':I.tolist()}

def main():
 OUT.mkdir(parents=True,exist_ok=True);paths=[BASE/p for p in ['HEAD-INTEGRATED03-open.step','HEAD-INTEGRATED03-closed.step','blender-parts-manifest.json','blender-parts-manifest-closed.json','export-mass.json','qa.json']];inputs={str(p.relative_to(ROOT)):sha(p) for p in paths};start_hashes=dict(inputs)
 manifest=read(paths[2]);closed_manifest=read(paths[3]);reference=read(paths[4]);baselineqa=read(paths[5]);assert baselineqa['artifact_integrity_passed']
 for state,p in [('open',paths[0]),('closed',paths[1])]:assert reference['states'][state]['STEP']['sha256']==sha(p)
 assert manifest['head_face_world_mm']==[0,55,804] and manifest['J7_pivot_head_mm']==[0,0,-164]
 print('unit checks',flush=True);units=unit_checks();print('read named STEP',flush=True);home=load_named(paths[0]);closed=load_named(paths[1]);meta={p['id']:p for p in manifest['parts']};assert home.keys()==closed.keys()==meta.keys()
 gp={n:geometry_properties(s) for n,s in home.items()};gc={n:geometry_properties(s) for n,s in closed.items()};joints={p['id']:p for p in manifest['finger_joints']};groups={g['part'].split('_')[0]:g for g in manifest['mass_groups']};assert set(groups)==set(joints)
 Vact={f:sum(gp[n]['volume_mm3'] for n,p in meta.items() if p['finger']==f and p['material']=='P16_envelope') for f in joints};parts=[];unknown=[];shape_audit=[];proxy_catalog=[]
 for n,p in meta.items():
  g=gp[n];group,body=classify(p);vdelta=g['volume_mm3']-p['shape_volume_mm3'];assert abs(vdelta)<max(1e-4,p['shape_volume_mm3']*1e-7),(n,vdelta)
  source=dict(step=str(paths[0].relative_to(ROOT)),named_entity=n,manifest=str(paths[2].relative_to(ROOT)),upstream=p['source']);hashes=dict(STEP_sha256=inputs[str(paths[0].relative_to(ROOT))],manifest_sha256=inputs[str(paths[2].relative_to(ROOT))])
  common=dict(id=n,body_id=body,kinematic_group=group,finger=p['finger'],material=p['material'],source=source,hash=hashes,shape_volume_mm3=g['volume_mm3'],mass_measured=False)
  if p['material']=='P16_envelope':
   m=groups[p['finger']]['mass_g']*.001*g['volume_mm3']/Vact[p['finger']];assumption='P16 total95g distributed over SUM of four possibly overlapping envelope primitive volumes; unidentifed internal mass distribution. Never count complete95g again.';basis='P16_unidentified_volume_partition_proxy';proxy=True
  elif p['mass_g'] is None:
   unknown.append({**common,'mass_kg':None,'com_head_home_m':None,'inertia_about_COM_head_axes_kg_m2':None,'envelope_centroid_head_m':g['com_m'].tolist(),'assumption':'Unweighed electronic part or EMPTY reservation. No density/mass assigned. Planning budgets supplied separately; this is not physical zero mass.','inertia_is_proxy':None});shape_audit.append(dict(id=n,volume_delta_mm3=vdelta));continue
  elif 'rho=' in p['mass_status']:
   rho=float(re.search(r'rho=([0-9.eE+-]+)',p['mass_status']).group(1));m=g['volume_mm3']*rho*.001;basis='nominal_CAD_uniform_material';proxy=p['material'].endswith('assumed') or '_assumed' in p['material'];assumption='Nominal STEP volume integral with HEAD03 uniform density '+str(rho)+' g/mm3. Geometry/density are design inputs, not measured manufactured inertia.'
  else:
   m=p['mass_g']*.001;basis='catalog_mass_uniform_shape_proxy';proxy=True;assumption='HEAD03 catalog mass distributed uniformly over same nominal/envelope shape; supplier internal mass distribution/inertia not identified.';proxy_catalog.append(n)
  I=m*g['inertia_per_mass_m2'];row={**common,'mass_kg':m,'com_head_home_m':g['com_m'].tolist(),'inertia_about_COM_head_axes_kg_m2':I.tolist(),'mass_inertia_basis':basis,'inertia_is_proxy':proxy,'assumption':assumption};row['tensor_check']=tensor_check(I);parts.append(row)
  if p['mass_g'] is not None:assert abs(m-p['mass_g']*.001)<1e-8,(n,m,p['mass_g'])
  shape_audit.append(dict(id=n,volume_delta_mm3=vdelta))
 print('integrated measured/nominal/proxy parts',len(parts),'unweighed',len(unknown),flush=True)
 bodies=[]
 for bid in dict.fromkeys(x['body_id'] for x in parts):
  members=[x for x in parts if x['body_id']==bid];first=members[0];out=combine(members);bodies.append(dict(id=bid,**out,kinematic_group=first['kinematic_group'],finger=first['finger'],source=[x['id'] for x in members],hash=inputs,assumption='Parallel-axis aggregation of listed nominal/proxy parts; do not add both aggregate and member masses.',contains_proxy=any(x['inertia_is_proxy'] for x in members),mass_measured=False,tensor_check=tensor_check(np.array(out['inertia_about_COM_head_axes_kg_m2']))))
 assert len(bodies)==13
 qs={f:math.radians(j['range_deg'][1]) for f,j in joints.items()};transformed=[];closed_checks=[];direct=[]
 for row in parts:
  n=row['id'];m=row['mass_kg'];pred=transform_body(row,qs.get(row['finger'],0),joints);actual=gc[n];dc=np.linalg.norm(np.array(pred['com_head_home_m'])-actual['com_m']);dI=float(np.max(abs(np.array(pred['inertia_about_COM_head_axes_kg_m2'])-m*actual['inertia_per_mass_m2'])));assert dc<1e-7 and dI<1e-10,(n,dc,dI)
  tensor_check(np.array(pred['inertia_about_COM_head_axes_kg_m2']));transformed.append(pred);direct.append({**row,'com_head_home_m':actual['com_m'].tolist(),'inertia_about_COM_head_axes_kg_m2':(m*actual['inertia_per_mass_m2']).tolist()});closed_checks.append(dict(id=n,independent_transform_COM_error_m=dc,independent_transform_inertia_error_kg_m2=dI))
 whole=combine(parts);pred=combine(transformed);direct_total=combine(direct);agg_closed=combine([transform_body(x,qs.get(x['finger'],0),joints) for x in bodies]);totals={}
 for state,total in [('open',whole),('closed',pred)]:
  ref=reference['states'][state]['mass'];dm=total['mass_kg']-ref['modeled_mass_g']*.001;dc=np.array(total['com_head_home_m'])-np.array(ref['COM_proxy_head_mm'])*.001;assert abs(dm)<1e-8 and np.linalg.norm(dc)<1e-7
  totals[state]=dict(**total,reference_mass_difference_kg=dm,reference_COM_difference_m=dc.tolist(),tensor_check=tensor_check(np.array(total['inertia_about_COM_head_axes_kg_m2'])))
 assert np.max(abs(np.array(agg_closed['inertia_about_COM_head_axes_kg_m2'])-pred['inertia_about_COM_head_axes_kg_m2']))<1e-10
 assert np.max(abs(np.array(direct_total['inertia_about_COM_head_axes_kg_m2'])-pred['inertia_about_COM_head_axes_kg_m2']))<1e-10
 sensitivity=[];p16splits=[]
 for f in joints:
  bb=next(x for x in bodies if x['id']==f+'_P16_body');sl=next(x for x in bodies if x['id']==f+'_P16_slider');sum_m=bb['mass_kg']+sl['mass_kg'];assert abs(sum_m-.095)<1e-10
  names=[n for n,p in meta.items() if p['finger']==f and p['material']=='P16_envelope'];sumv=sum(gp[n]['volume_mm3'] for n in names);fused=home[names[0]].fuse(*[home[n] for n in names[1:]]);fusedc=closed[names[0]].fuse(*[closed[n] for n in names[1:]])
  p16splits.append(dict(finger=f,total_mass_kg=sum_m,body_mass_kg=bb['mass_kg'],slider_mass_kg=sl['mass_kg'],body_fraction=bb['mass_kg']/sum_m,slider_fraction=sl['mass_kg']/sum_m,primitive_volume_sum_mm3=sumv,open_union_volume_mm3=fused.Volume(),closed_union_volume_mm3=fusedc.Volume(),open_overlap_volume_counted_more_than_once_mm3=sumv-fused.Volume(),closed_overlap_volume_counted_more_than_once_mm3=sumv-fusedc.Volume(),assumption='Mass allocation uses primitive-volume SUM, NOT fused physical material volume. Overlapping boxes are intentional conservative spatial envelopes, not motor material.'))
  sensitivity.append(dict(finger=f,slider_mass_kg_interval=[0,.095],body_mass_kg_formula='0.095 - slider_mass_kg',nominal_slider_mass_kg=sl['mass_kg'],body_com_head_home_m=bb['com_head_home_m'],slider_com_head_home_m=sl['com_head_home_m'],body_normalized_central_inertia_m2=(np.array(bb['inertia_about_COM_head_axes_kg_m2'])/bb['mass_kg']).tolist(),slider_normalized_central_inertia_m2=(np.array(sl['inertia_about_COM_head_axes_kg_m2'])/sl['mass_kg']).tolist(),assumption='Scalar allocation sensitivity with each group uniformly distributed over its own overlapping envelope sum. Does not bound all possible true internal COM/inertia distributions. Endpoints allow zero mass; do not divide by zero.'))
 samples=[]
 for sm in [0,.025,.05,.075,.095]:
  altered=[]
  for b in bodies:
   if b['kinematic_group'] not in ['P16_body','P16_slider']:altered.append(b);continue
   newm=sm if b['kinematic_group']=='P16_slider' else .095-sm;altered.append({**b,'mass_kg':newm,'inertia_about_COM_head_axes_kg_m2':(np.array(b['inertia_about_COM_head_axes_kg_m2'])*newm/b['mass_kg']).tolist()})
  samples.append(dict(slider_mass_per_P16_kg=sm,all_four_allocations_equal_for_this_example=True,open=combine(altered),closed=combine([transform_body(x,qs.get(x['finger'],0),joints) for x in altered])))
 budget=reference['states']['open']['mass']['planning_remainder'];budget_si=[dict(item=x['item'],mass_kg_interval=[m*.001 for m in x['mass_g']],COM_head_home_box_m=(np.array(x['COM_head_box_mm'])*.001).tolist(),basis=x['basis'],frame_scope='Copied HEAD03 planning box, not measured COM nor all-configuration guaranteed enclosure. No unique kinematic attachment/inertia yet.') for x in budget]
 # Prefix exported model ids; preserve actual STEP entity names in source.
 for row in parts+unknown:
  row['id']='HEAD_'+row['id'];row['body_id']='HEAD_'+row['body_id']
 for body in bodies:
  body['id']='HEAD_'+body['id'];body['source']=['HEAD_'+x for x in body['source']]
 common=dict(revision='HEAD-MASS04',license='CC-BY-NC-4.0',required_notice=NOTICE,manufacturing_release=False,dynamics_or_grasp_rating=False,units=dict(mass='kg',length='m',angle='rad',inertia='kg*m^2'),coordinate_contract=dict(frame='HEAD03 head face home',head_face_world_home_m=[0,.055,.804],J7_pivot_head_home_m=[0,0,-.164],inertia_reference='each body COM, tensor components resolved along head HOME axes',inertia_transform='I(q)=R(q) I_home R(q)^T; use parallel-axis theorem only when changing reference point',world_translation_does_not_change_COM_central_inertia=True),head_face_world_mm=manifest['head_face_world_mm'],source_hashes=inputs)
 model=dict(**common,integration_rule='Choose either the262 mass-bearing primitive parts or13 aggregate bodies, NEVER add both.435 unweighed/reservation entries have null mass, not physical zero.',bodies=parts,unweighed_parts=unknown,aggregated_bodies=bodies,finger_joints=manifest['finger_joints'],joints_angle_input='relative_transform accepts radians; source manifest range_deg is retained only as provenance.',whole_head_nominal_proxy=totals,planning_remainder=budget_si,planning_remainder_total_kg_interval=[.185,.450],whole_head_planning_mass_kg_interval=[whole['mass_kg']+.185,whole['mass_kg']+.450],old_L7_budget_policy='No generic0.15kg L7/tool budget here. This model already includes adapter, EXT24, carrier and modeled head hardware. Remove overlapping old tool/L7 allocation when composing the arm; J7 motor itself remains excluded.',excludes='J7 motor, remaining six arm structures/joints, payload, unweighed electronics, final harness/armor/thermal bridge/cover retention.',P16_partition=p16splits)
 # Assert partition inventory rather than encoding an accidental zero-mass part.
 model['integration_rule']=f'Choose either the {len(parts)} mass-bearing primitive parts or 13 aggregate bodies, NEVER add both. {len(unknown)} unweighed/reservation entries have null mass, not physical zero.'
 validation=dict(**common,unit_checks=units,named_step_entities=len(home),name_sets_match_manifest_and_closed=True,per_part_geometry_audit=shape_audit,closed_rigid_transform_checks=closed_checks,maximum_closed_COM_error_m=max(x['independent_transform_COM_error_m'] for x in closed_checks),maximum_closed_inertia_error_kg_m2=max(x['independent_transform_inertia_error_kg_m2'] for x in closed_checks),all_nominal_and_transformed_tensors_symmetric_PSD_and_triangle_consistent=True,whole_head_comparison=totals,aggregate_closed_tensor_matches_per_part=True,direct_closed_STEP_tensor_matches_independent_transform=True,aggregate_group_count=13,mass_bearing_part_count=len(parts),unweighed_or_reservation_count=len(unknown),catalogue_mass_proxy_parts=proxy_catalog,HEAD03_read_only_sha_before_after_identical=all(sha(ROOT/p)==h for p,h in start_hashes.items()),script_sha256=sha(__file__))
 assert validation['HEAD03_read_only_sha_before_after_identical']
 save('mass-properties.json',model);save('rigid-bodies.json',dict(**common,bodies=bodies,integration_rule=model['integration_rule']));save('p16-mass-sensitivity.json',dict(**common,per_finger_inputs=sensitivity,common_mass_examples=samples,allocation_notes=p16splits));save('validation.json',validation)
 with (OUT/'parts-ledger.csv').open('w',newline='') as fp:
  fields=['id','body_id','kinematic_group','finger','material','mass_kg','com_x_m','com_y_m','com_z_m']+[f'I_{a}{b}_kg_m2' for a in 'xyz' for b in 'xyz']+['mass_inertia_basis','inertia_is_proxy','assumption','source_step','source_sha256'];w=csv.DictWriter(fp,fieldnames=fields);w.writeheader()
  for x in parts+unknown:
   c=x['com_head_home_m'] or [None]*3;I=np.array(x['inertia_about_COM_head_axes_kg_m2'] if x['inertia_about_COM_head_axes_kg_m2'] is not None else [[None]*3]*3)
   row={k:x.get(k) for k in ['id','body_id','kinematic_group','finger','material','mass_kg','mass_inertia_basis','inertia_is_proxy','assumption']};row.update(zip(['com_x_m','com_y_m','com_z_m'],c));row.update({f'I_{a}{b}_kg_m2':I[i,j] for i,a in enumerate('xyz') for j,b in enumerate('xyz')});row.update(source_step=x['source']['step'],source_sha256=x['hash']['STEP_sha256']);w.writerow(row)
 print(json.dumps(dict(mass_kg=whole['mass_kg'],COM_home_m=whole['com_head_home_m'],groups=len(bodies),P16_slider_mass_kg=p16splits[0]['slider_mass_kg'],max_closed_COM_error_m=validation['maximum_closed_COM_error_m'],max_closed_inertia_error_kg_m2=validation['maximum_closed_inertia_error_kg_m2']),indent=2),flush=True)
if __name__=='__main__':main()
