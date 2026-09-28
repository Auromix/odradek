#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""RAISE03: integrate frozen PORT01 blocks and PROC01 nominal screw candidates.

Only new original/proxy artifacts are exported. No OEM geometry is redistributed.
"""
from pathlib import Path
import argparse,csv,hashlib,json,itertools,math,re
import numpy as np
import cadquery as cq
from screen_integrated_collisions import named_step,load_structure
from shoulder_raise_study import default_paths,properties,aggregate,frame,moved,comp,bbox
from head_mass04_study import geometry_properties,unit_checks
from build_link56_study import cylinder,face_contact
from studies.link_interface_tools import check,cache

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/shoulder-raise03'
PREV=ROOT/'engineering/generated/shoulder-raise02'
PORT=ROOT/'engineering/generated/shoulder-port01'
REV='SHOULDER-RAISE03'
NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)'
T2=frame([0,0,205],[0,1,0])

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def native(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,(np.integer,np.floating,np.bool_)):return x.item()
 raise TypeError(type(x).__name__)
def dump(name,x):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(x,indent=2,default=native)+'\n')
def volume(s):return sum(abs(x.Volume()) for x in s.Solids())
def outside(a,b):return sum(volume(s.cut(b)) for s in a.Solids())
def bounds(s):
 b=s.BoundingBox();return [[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]
def source(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def body_entry(row):
 return dict(id=row['id'],mass_kg=row['mass_kg'],com_home_m=row['com_world_m'],orientation_home=np.eye(3),inertia_com_kg_m2=row['inertia_about_COM_world_axes_kg_m2'],preceding_joints=1,attached_to='J1_output__J2_stator_fixed_structure',inertia_is_proxy=row['inertia_is_proxy'],mass_basis=row['mass_basis'])

def read_inputs():
 manifest=json.loads((PREV/'part-placements.json').read_text());ready=json.loads((PREV/'ready-manifest.json').read_text());port=json.loads((PORT/'study.json').read_text());proc=json.loads((ROOT/'engineering/generated/shoulder-procurement01/procurement-check.json').read_text());sources=json.loads((ROOT/'docs/engineering/sources/shoulder-procurement01.json').read_text());bom=json.loads((ROOT/'engineering/generated/link12-study/bom.json').read_text())
 files=[PREV/'part-placements.json',PREV/'ready-manifest.json',PREV/'SHOULDER-RAISE02-original-assembly.step',PREV/'continuous-motion.json',PREV/'assembly-paths.json',PREV/'steel-block-paths.json',PREV/'geometry-first.json',PREV/'connections.json',PREV/'study.json',PORT/'study.json',PORT/'verification.json',ROOT/'engineering/generated/shoulder-procurement01/procurement-check.json',ROOT/'docs/engineering/sources/shoulder-procurement01.json',ROOT/'docs/engineering/sources/shoulder-port01.json',ROOT/'docs/engineering/sources/rh-interface-extraction.json',ROOT/'engineering/generated/link12-study/bom.json',ROOT/'engineering/generated/link12-study/screw-stacks.csv',ROOT/'engineering/generated/raised-arm-integration01/model.json',ROOT/'engineering/generated/shoulder-raise-01/part-placements.json']
 old=named_step(PREV/'SHOULDER-RAISE02-original-assembly.step');assert len(old)==39
 geometry={};metadata={};subset={};equivalence={}
 for name,row in manifest['instances'].items():
  p=PREV/row['file'];assert sha(p)==row['sha256'];files.append(p);s=cq.importers.importStep(str(p)).val();assert s.isValid() and len(s.Solids())==1;err=outside(s,old[name])+outside(old[name],s);assert err<1e-4;equivalence[name]=err
  new_id='L12_'+name.lower() if name.startswith('STEEL_') else name
  if name in ['STEEL_THREAD_BLOCK_1','STEEL_THREAD_BLOCK_8']:
   i=int(name.rsplit('_',1)[1]);p=PORT/f'SHOULDER-PORT01-BLOCK-{i}-R38.step';assert sha(p)==port['export_checks'][p.name]['sha256'];files.append(p);s=cq.importers.importStep(str(p)).val()
  geometry[new_id]=s;subset[new_id]=dict(previous_id=name,outside_previous_mm3=outside(s,old[name]),removed_mm3=volume(old[name])-volume(s));assert subset[new_id]['outside_previous_mm3']<1e-4
  steel=name.startswith('STEEL_');mat='42CrMo4+QT_D50_round_bar_candidate' if steel else ('6061-T651_101.6mm_wrought_plate_PROC01' if name=='L12_rear_fork' else '6061-T6_candidate_stock_certificate_unfrozen');rho=7.85e-6 if steel else 2.7e-6
  q=properties(s,mat,rho);q.update(id=new_id,legacy_id=name,kind='original_metal',source=source(p),mass_basis='Nominal CAD volume x nominal material density; not weighed',inertia_is_proxy=False,geometry_is_envelope=False,preceding_joints=1,material_certificate_bound=False)
  metadata[new_id]=q
 # Retrieve the exact frozen hardware placements and partial output-channel proxies.
 hardware_table={}
 with (ROOT/'engineering/generated/link12-study/screw-stacks.csv').open() as f:
  for row in csv.DictReader(f):hardware_table[row['id']]=row
 exact=next(r for r in sources['sources'] if r['id']=='fabory-m4-100');foot=next(r for r in bom['sources'] if r['id']=='M6x35');iface=next(m for m in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models'] if m['id']=='RH25-B')['unified_joint_interface'];fp=np.array([r['xy_mm'] for r in iface['fixed_through_holes']['points']])
 for name,s in old.items():
  if not name.startswith('L12_HW_'):continue
  if name.startswith('L12_HW_FIX_'):
   i=int(name.rsplit('_',1)[1]);seat=(T2@np.r_[fp[i-1],-11.5,1])[:3];s=cylinder(seat,[0,1,0],exact['head_diameter_max_mm']/2,exact['head_height_max_mm']).fuse(cylinder(seat,[0,-1,0],2,exact['length_mm']));new_id=f'L12_HW_FIX_FABORY_07000_040_100_{i}';mass=exact['catalog_mass_g_each']*.001;pn='Fabory '+exact['part_number'];qsource=source(ROOT/'docs/engineering/sources/shoulder-procurement01.json');owner=f'L12_steel_thread_block_{i}';gap=proc['screw_nominal_fit'];stack=dict(seat_world_mm=seat,head_outward_axis=[0,1,0],diameter_mm=4,length_mm=100,head_D_H_mm=[7,4],nominal_thread_b_mm=20,nominal_shank_mm=80,nominal_thread_world_Y_mm=[-111.5,-91.5],grip_mm=93,nominal_geometric_engagement_mm=7,nominal_tip_clearance_mm=1,thread_owner=owner,effective_engagement_mm=None,washers_added=0,socket_AF_mm=3,socket_depth_mm=None)
  else:
   new_id=name;raw=hardware_table[name.removeprefix('L12_HW_')];owner='L12_rear_fork' if name.startswith('L12_HW_FOOT_') else 'J1';stack=dict(seat_world_mm=json.loads(raw['seat_world_mm']),head_outward_axis=json.loads(raw['head_outward_axis']),diameter_mm=6 if name.startswith('L12_HW_FOOT_') else 4,length_mm=35 if name.startswith('L12_HW_FOOT_') else None,modeled_partial_length_mm=None if name.startswith('L12_HW_FOOT_') else 7.5,head_D_H_mm=json.loads(raw['head_D_H_mm']),grip_mm=float(raw['free_grip_mm']),nominal_geometric_engagement_mm=13 if name.startswith('L12_HW_FOOT_') else None,thread_owner=owner,effective_engagement_mm=None)
   mass=foot['weight_100_grams']*.00001 if name.startswith('L12_HW_FOOT_') else None;pn=foot['part'] if name.startswith('L12_HW_FOOT_') else None;qsource=source(ROOT/'engineering/generated/link12-study/bom.json')
  geometry[new_id]=s;g=geometry_properties(s);q=dict(id=new_id,legacy_id=name,kind='fastener_nominal_envelope',source=qsource,part_number=pn,material='class12.9_plain_steel_candidate' if mass is not None else 'unselected',mass_kg=mass,volume_mm3=g['volume_mm3'],com_world_m=g['com_m'] if mass is not None else None,inertia_about_COM_world_axes_kg_m2=mass*g['inertia_per_mass_m2'] if mass is not None else None,geometry_COM_world_m=g['com_m'],mass_basis='Manufacturer catalogue mass, uniformly distributed over nominal external envelope as COM/I proxy' if mass is not None else 'Unknown: partial output channel proxy is not complete screw; no mass inferred',mass_measured=False,inertia_is_proxy=True,geometry_is_envelope=True,geometry_contains_thread_helix=False,preceding_joints=1,stack=stack,source_assembly=source(PREV/'SHOULDER-RAISE02-original-assembly.step'));metadata[new_id]=q
  subset[new_id]=dict(previous_id=name,outside_previous_mm3=outside(s,old[name]),removed_mm3=volume(old[name])-volume(s));assert subset[new_id]['outside_previous_mm3']<1e-4
 assert len(geometry)==39 and sum(x['kind']=='original_metal' for x in metadata.values())==11
 old_sources={k:sha(ROOT/k)==h for k,h in manifest['source_hashes'].items()};assert all(old_sources.values()),[k for k,v in old_sources.items() if not v]
 # Trace all inherited proof inputs and the helpers used here; no old file is written.
 files += [ROOT/k for k in manifest['source_hashes']]
 files += [ROOT/'engineering'/p for p in ['head_mass04_study.py','screen_integrated_collisions.py','shoulder_raise_study.py','build_layout.py','build_link56_study.py','studies/link_interface_tools.py']]
 hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))}
 return geometry,metadata,old,manifest,port,proc,iface,hashes,dict(previous_originals_vs_named_assembly_symmetric_difference_mm3=equivalence,all_new_parts_subset_of_same_pose_previous_part=subset,inherited_source_hash_checks=old_sources)

def mass_models(metadata,previous):
 originals=[r for r in metadata.values() if r['kind']=='original_metal'];known=[r for r in metadata.values() if r['kind']=='fastener_nominal_envelope' and r['mass_kg'] is not None];unknown=[r['id'] for r in metadata.values() if r['mass_kg'] is None];assert len(known)==12 and len(unknown)==16
 metal=aggregate(originals);metal['mass_basis']='Nominal material volume integration of11 original parts';hardware=aggregate(known);hardware['mass_basis']='12 catalogue masses with external-envelope COM/I proxies';quantified=aggregate(originals+known);quantified['mass_basis']='Nominal original metal +12 catalogue fasteners;16 unresolved output screws and other unallocated items excluded'
 assert abs(hardware['mass_kg']-.1276)<1e-12
 priormodel=json.loads((ROOT/'engineering/generated/raised-arm-integration01/model.json').read_text());old_budget=next(x for x in priormodel['arm']['bodies'] if x['id']=='L12_hardware_reserve');assert old_budget['mass_kg']==.2 and old_budget['preceding_joints']==1
 variants={}
 for label,budget in [('primary_preserve_200g_total',.2),('sensitivity_preserve_historical_114_8g_unallocated',.2424)]:
  # Keep the established whole-budget proxy strategy explicit; do NOT add the12 known items again.
  h=dict(id='L12_hardware_reserve',kind='planning_hardware_group',mass_kg=budget,com_world_m=metal['com_world_m'],inertia_about_COM_world_axes_kg_m2=(np.array(old_budget['inertia_com_kg_m2'])*(budget/.2)).tolist(),inertia_is_proxy=True,mass_basis='Whole hardware budget at new metalCOM; inherited50mm-cube inertia proxy, catalogue pieces are bookkeeping allocations inside this total',preceding_joints=1)
  total=aggregate(originals+[h]);total['mass_basis']='Original metal CAD + unweighed whole hardware planning allowance; not a measured assembly'
  variants[label]=dict(aggregate=total,bodies=[body_entry(r) for r in originals+[h]],hardware_ledger=dict(total_planning_kg=budget,known_catalogue_allocation_kg=hardware['mass_kg'],unallocated_planning_kg=budget-hardware['mass_kg'],unallocated_is_guaranteed_upper_bound=False,known_parts_are_NOT_added_again=True),unknown_individual_fastener_ids=unknown)
 old1=json.loads((ROOT/'engineering/generated/shoulder-raise-01/part-placements.json').read_text())['new_L12_original_aggregate'];old2=previous['aggregate_original_metal'];differences={}
 for name,old in [('RAISE01',old1),('RAISE02',old2)]:differences[name]=dict(metal_mass_delta_kg=metal['mass_kg']-old['mass_kg'],metal_COM_delta_world_m=np.array(metal['com_world_m'])-np.array(old['com_world_m']),central_inertia_numeric_delta_kg_m2=np.array(metal['inertia_about_COM_world_axes_kg_m2'])-np.array(old['inertia_about_COM_world_axes_kg_m2']),inertia_delta_note='Difference of each model central tensors in common world axes; centres differ; not the inertia of removed/added material.')
 return dict(revision=REV,original_metal=metal,known_catalogue_hardware=hardware,quantified_subtotal=quantified,quantified_bodies=[body_entry(r) for r in originals+known],planning_models=variants,differences=differences,attachment='Every part/group follows J1 only (preceding_joints=1); none follows J2 output. J1 and J2 OEM masses excluded.',unknown_individual_fastener_mass_kg=None,manufacturing_release=False)

def export(geometry,metadata,hashes,mass):
 asm=cq.Assembly(name=REV+'-original-and-nominal-hardware');originalasm=cq.Assembly(name=REV+'-original-metal-only');checks=[]
 for name,s in geometry.items():
  p=OUT/(name+'.step');cq.exporters.export(s,str(p));t=cq.importers.importStep(str(p)).val();assert t.isValid() and len(t.Solids())==1;g=geometry_properties(s);h=geometry_properties(t);ve=abs(g['volume_mm3']-h['volume_mm3']);ce=float(np.max(abs(g['com_m']-h['com_m'])));ie=float(np.max(abs(g['inertia_per_mass_m2']-h['inertia_per_mass_m2'])));assert ve<1e-4 and ce<1e-8 and ie<1e-9
  row=metadata[name];row.update(file=p.name,sha256=sha(p),T_world_from_part_mm=np.eye(4),source_frame='World-home mm: J1=(0,0,105.2), J2=(0,0,205), no extra translation',bbox_world_mm=bounds(s),attached_to='J1_output__J2_stator_fixed_structure',follows_joints=['J1'],rigid_orientation_home=np.eye(3));asm.add(s,name=name,color=cq.Color('#547f87') if row['kind']=='original_metal' else cq.Color('#9b7a43'))
  if row['kind']=='original_metal':originalasm.add(s,name=name)
  checks.append(dict(id=name,volume_error_mm3=ve,COM_error_m=ce,inertia_per_mass_error_m2=ie))
 for a,file,count in [(asm,'SHOULDER-RAISE03-named-assembly.step',39),(originalasm,'SHOULDER-RAISE03-original-metal.step',11)]:
  a.save(str(OUT/file));r=named_step(OUT/file);assert len(r)==count
  for n,s in r.items():assert abs(volume(s)-volume(geometry[n]))<1e-4
  checks.append(dict(file=file,named_entity_count=len(r),all_names_and_volumes_match=True))
 dump('structure-parts.json',dict(revision=REV,license='CC-BY-NC-4.0',required_notice=NOTICE,world_units='mm for geometry;kg,m,kgm2 for inertial fields',J1_origin_world_mm=[0,0,105.2],J2_origin_world_mm=[0,0,205],baseline_modified=False,parts=list(metadata.values()),integration_policy='Choose exactly one planning model OR explicit quantified-body set plus independently resolved unknowns. Never sum both; do not retain oldL12 metal or0.20kg body alongside replacement.',source_hashes=hashes))
 dump('mass-properties.json',mass);dump('export-qa.json',checks)
 with (OUT/'bom.csv').open('w',newline='') as f:
  fields=['id','quantity','kind','part_number','material','mass_kg','mass_basis','preceding_joints','source_file','nominal_engagement_mm','effective_engagement_mm','manufacturing_release'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in metadata.values():w.writerow(dict(id=r['id'],quantity=1,kind=r['kind'],part_number=r.get('part_number'),material=r['material'],mass_kg=r['mass_kg'],mass_basis=r['mass_basis'],preceding_joints=1,source_file=r['source']['path'],nominal_engagement_mm=r.get('stack',{}).get('nominal_geometric_engagement_mm'),effective_engagement_mm=None,manufacturing_release=False))
 return checks

def inheritance(geometry,old,inputs,hashes,port):
 motion=json.loads((PREV/'continuous-motion.json').read_text());assembly=json.loads((PREV/'assembly-paths.json').read_text());blocks=json.loads((PREV/'steel-block-paths.json').read_text());assert motion['all_full_moving_external_certified'] and motion['own_J2_exposed_no_positive_volume'];assert not assembly['events'] and not blocks['events']
 envelope=cylinder([0,-3.5,205],[0,1,0],85,113.5);checks={n:check(envelope,s,minimum=True) for n,s in geometry.items()};assert not any(c['events'] for c in checks.values());gap=min(c['minimum_BREP_surface_distance_mm'] for c in checks.values());assert gap>3.9999
 rules=[dict(claim='local q2 ±90° external clearance',method='Unchanged moving-set/input hashes; every new fixed part is subset of same-pose frozen02 predecessor. Additionally recheck R85 invariant envelope against all39 local parts.',continuous=True,minimum_local_gap_mm=gap,source=source(PREV/'continuous-motion.json')),dict(claim='J2 +Y motor insertion0..180mm',method='Same controlled OEM/pose/enclosure, reduced-or-identical stationary originals/hardware; frozen continuous sweep remains conservative.',continuous=True,source=source(PREV/'assembly-paths.json')),dict(claim='Eight rear block insertions0..60mm along−Y, one at a time',method='Subset holds at every rigid translation; other blocks/static parts are also subsets. Long FIX screws absent during block insertion as in02.',continuous=True,source=source(PREV/'steel-block-paths.json')),dict(claim='Rear fork / preassembled bracket / front-ring insertion',method='Only frozen sampled poses inherit, with identical path and assembly stage; no new continuous claim.',continuous=False,source=source(PREV/'assembly-paths.json')),dict(claim='Nominal straight tool channels',method='8 long-screw socketAF3/headH4 unchanged; existingD5 shaft probe conservative; tool handles and installedJ3/downstream absent as before.',continuous=False,source=source(PREV/'assembly-paths.json')),dict(claim='PORT01 four aperture-sized rearward60mm access probes',method='Exactly the two frozenR38 blocks; other six blocks and rear fork unchanged. Apertures are not actual plugs.',continuous=True,source=source(PORT/'study.json'),actual_connector_qualified=False)]
 return dict(revision=REV,subset_proofs=inputs['all_new_parts_subset_of_same_pose_previous_part'],strict_conditions=rules,local_invariant_envelope_checks=checks,minimum_local_invariant_gap_mm=gap,unchanged_source_hashes=inputs['inherited_source_hash_checks'],limitations=motion['limits']+' '+assembly['scope'],no_geometric_subset_implies_strength_or_preload=True,FEA01_scope='Aluminium fork geometry unchanged; ideal fork-only FEA01 RAISE02 result can be referenced with original ideal BC only. Steel/block/bolt/contact physics were absent and remain unqualified.')

def verify_long_screw_paths(geometry,metadata,hashes):
 _,rows,newhashes,vendor=load_structure(default_paths());hashes.update(newhashes)
 oldvendor=json.loads((PREV/'study.json').read_text())['vendor_sources'];assert vendor==oldvendor, 'Controlled OEM inputs changed; inherited proofs invalid'
 stationary={n:r['shape'] for n,r in rows.items() if n=='J1' or n.startswith('BASE_')};stationary['J2']=rows['J2']['shape'].translate((0,0,35));stationary.update(geometry);cached={n:cache(s) for n,s in stationary.items()};out={}
 for name,r in metadata.items():
  if not name.startswith('L12_HW_FIX_FABORY'):continue
  seat=np.array(r['stack']['seat_world_mm']);tip=seat-np.array([0,100,0]);sweep=cylinder(seat,[0,1,0],3.5,104).fuse(cylinder(tip,[0,1,0],2,200));engagement=cylinder(tip,[0,1,0],2,7);free=sweep.cut(engagement);assert outside(geometry[name],sweep)<1e-4
  tests={n:check(free if n==r['stack']['thread_owner'] else sweep,c) for n,c in cached.items() if n!=name};events={n:c for n,c in tests.items() if c['events']};assert not events,(name,events)
  out[name]=dict(direction_from_final=[0,1,0],travel_mm=[0,100],whole_screw_contained=True,nominal_engagement_excluded_only_against_named_owner_mm=7,thread_owner=r['stack']['thread_owner'],checks=tests,events=events,proof='Analytic axial union: headR3.5 overY−11.5..92.5; shank/thread outerR2 overY−111.5..88.5; contains every nominal screw pose for t0..100. Only fixed final7mm thread-owner channel subtracted for that owner pair.')
 return dict(revision=REV,continuous_nominal_long_screw_insertion=True,screws=out,vendor_sources=vendor,vendor_hashes_match_frozen02=True,limits='Nominal shaft/thread-envelope path, not physical threading simulation. J3/L23 and downstream absent; no plug/cable/handle/tolerance/lead-in qualification. OEM effective output threads remain unresolved.')

def connection_changes(geometry,metadata,old,port):
 rows={};rear=geometry['L12_rear_fork'];front=geometry['L12_front_ring'];expected_new=math.pi*(3.5**2-2.25**2);expected_old=math.pi*(3.61**2-2.25**2)
 for n,r in metadata.items():
  if not n.startswith('L12_HW_FIX_FABORY'):continue
  i=int(n.rsplit('_',1)[1]);seat=np.array(r['stack']['seat_world_mm']);owner=r['stack']['thread_owner'];block_contact=face_contact(geometry[owner],rear,[seat[0],-104.5,seat[2]],[0,1,0]);bearing=face_contact(geometry[n],front,seat,[0,1,0]);prior_bearing=face_contact(old[r['legacy_id']],front,seat,[0,1,0])
  assert abs(bearing['shared_planar_face_area_mm2']-expected_new)<1e-5 and abs(prior_bearing['shared_planar_face_area_mm2']-expected_old)<1e-5
  entry=dict(block_to_fork=block_contact,nominal_head_to_front_ring=bearing,previous_nominal_head_to_front_ring=prior_bearing,head_bearing_area_ratio=expected_new/expected_old,pressure_ratio_if_same_force=expected_old/expected_new,contact_is_unloaded_nominal_planar_footprint=True)
  if i in [1,8]:
   change=port['modifications'][f'BLOCK_{i}'];assert abs(block_contact['shared_planar_face_area_mm2']-change['common_rear_contact_after']['shared_planar_face_area_mm2'])<1e-5
   removed=old[f'STEEL_THREAD_BLOCK_{i}'].cut(geometry[owner]);protect=cylinder([seat[0],-115,seat[2]],[0,1,0],7,20);v=volume(removed.intersect(protect));assert v<1e-4;entry.update(removed_in_thread_R7_neighbourhood_mm3=v,major_thread_side_ligament_mm=5,major_thread_inner_planar_ligament_mm=11)
  rows[owner]=entry
 return dict(revision=REV,connections=rows,head_bearing_formula='pi*((head_max_D/2)^2-(clearance_D/2)^2); max head diameter is optimistic for actual bearing area, not minimum guaranteed area',clearance_hole_D_mm=4.5,maximum_head_D_mm=7,nominal_new_head_bearing_area_mm2=expected_new,previous_nominal_head_bearing_area_mm2=expected_old,pressure_ratio_at_same_force=expected_old/expected_new,preload_is_selected=False,limits='No contact stiffness, preload, friction, runout, head chamfer, under-head fillet, thread stripping, fatigue or assembly tolerance qualification. No wrench torque is specified.')

def print_parts(geometry,metadata):
 import trimesh
 folder=OUT/'geometry-only-print';folder.mkdir(exist_ok=True);rows=[]
 for n,s in geometry.items():
  if metadata[n]['kind']!='original_metal':continue
  # Each original remains a separate nominal shape. No joining/strength assumptions.
  R=np.eye(4)
  if n.startswith('L12_steel') or n=='L12_front_ring':
   R[:3,:3]=[[1,0,0],[0,0,-1],[0,1,0]]
  spun=moved(s,R);b=spun.BoundingBox();T=np.eye(4);T[:3,3]=[-b.xmin,-b.ymin,-b.zmin];T=T@R;t=moved(s,T);p=folder/(n+'.stl');cq.exporters.export(t,str(p),tolerance=.04,angularTolerance=.08)
  m=trimesh.load(p,force='mesh',process=True);assert m.is_watertight and m.is_winding_consistent and m.volume>0;relative=abs(m.volume-volume(s))/volume(s);assert relative<.005
  corners=np.array(bounds(t));error=float(np.max(abs(m.bounds-corners)));assert error<.06
  rows.append(dict(id=n,file=str(p.relative_to(OUT)),sha256=sha(p),T_print_from_world_mm=T,T_world_from_print_mm=np.linalg.inv(T),bbox_print_mm=corners,watertight=True,winding_consistent=True,triangle_count=len(m.faces),STL_to_CAD_relative_volume_error=relative,bbox_error_mm=error,nominal_CAD_volume_mm3=volume(s),tessellation_tolerance_mm=.04,angular_tolerance_rad=.08))
 return dict(revision=REV,parts=rows,scope='Unpowered geometry-only tabletop fit illustration; nominal metal part geometry split by original part boundaries, no print-process compensation or functional thread representation.',not_authorized=['Carrying a payload','Motor energization','Preload/strength tests using printed material','Treating pilot bores as load-rated printed threads'],slicer_orientation_is_only_a_suggestion=True,thread_inserts_selected=False,printing_material_or_process_qualified=False)

def drawings(geometry,metadata,mass,connections):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.backends.backend_pdf import PdfPages
 from matplotlib.collections import PolyCollection
 from mpl_toolkits.mplot3d.art3d import Poly3DCollection
 meshes={}
 for n,s in geometry.items():
  v,f=s.tessellate(.16,.14);meshes[n]=(np.array([x.toTuple() for x in v]),np.asarray(f))
 colors={n:('#d99131' if n in ['L12_steel_thread_block_1','L12_steel_thread_block_8'] else '#607780' if n.startswith('L12_steel') else '#4c9096' if metadata[n]['kind']=='original_metal' else '#c6ac79') for n in geometry}
 allbounds=np.array([bounds(s) for s in geometry.values()]);lo=allbounds[:,0].min(axis=0);hi=allbounds[:,1].max(axis=0)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
 pdf=OUT/'SHOULDER-RAISE03-assembly-reference.pdf'
 def ortho(ax,indices,view_axis,reverse=False):
  triangles=[];c=[];depth=[]
  for n,(v,f) in meshes.items():
   tri=v[f];tri2=tri[:,:,indices];tri2=tri2.transpose(1,2,0) if tri2.shape[1]!=3 else tri2
   triangles.extend(tri2);c.extend([colors[n]]*len(f));depth.extend(tri[:,:,view_axis].mean(axis=1))
  order=np.argsort(depth);order=order[::-1] if reverse else order;ax.add_collection(PolyCollection([triangles[j] for j in order],facecolors=[c[j] for j in order],edgecolors='none',rasterized=True));ax.autoscale_view();ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('XYZ'[indices[0]]+' [mm]');ax.set_ylabel('XYZ'[indices[1]]+' [mm]')
 def dimension(ax,a,b,text,offset=(0,0)):
  a=np.array(a)+offset;b=np.array(b)+offset;ax.annotate('',b,a,arrowprops={'arrowstyle':'|-|','lw':.8,'color':'#283d48'});m=(a+b)/2;ax.text(*m,text,ha='center',va='bottom',fontsize=8,bbox={'facecolor':'white','edgecolor':'none','alpha':.85})
 with PdfPages(pdf) as pages:
  fig=plt.figure(figsize=(11.7,8.3));fig.suptitle('SHOULDER-RAISE03 | Local assembly reference',fontsize=17,x=.055,ha='left',y=.962);fig.text(.055,.918,'World home [mm]  /  J1 Z105.2  /  J2 Z205.0  /  all 39 parts follow J1 only',color='#405766')
  ax=fig.add_axes([.06,.30,.38,.56]);ortho(ax,(0,2),1,False);ax.set_title('Front X-Z | +Y view');ax.axhline(205,color='#9a5c20',lw=.6,ls='--');ax.axhline(105.2,color='#596c78',lw=.6,ls='--');dimension(ax,[lo[0],hi[2]+9],[hi[0],hi[2]+9],f'{hi[0]-lo[0]:.1f} overall');dimension(ax,[hi[0]+10,105.2],[hi[0]+10,205],'99.8 axis rise');ax.set_xlim(lo[0]-12,hi[0]+28);ax.set_ylim(lo[2]-10,hi[2]+18)
  ax=fig.add_axes([.54,.30,.40,.56]);ortho(ax,(1,2),0,False);ax.set_title('Side Y-Z | +X view');dimension(ax,[lo[1],hi[2]+9],[hi[1],hi[2]+9],f'{hi[1]-lo[1]:.1f} overall');ax.annotate('Rear block / thread owner\nY -112.5 .. -104.5',(-110,237),(-100,280),arrowprops={'arrowstyle':'->'},fontsize=8);ax.axvline(-11.5,color='#b2772d',lw=.7,ls='--');ax.text(-8,150,'M4 head seat\nY -11.5',fontsize=8);ax.set_ylim(lo[2]-10,hi[2]+26)
  fig.text(.055,.225,'Included: 11 original metal parts + 28 nominal hardware envelopes. OEM motors are omitted from public CAD.',fontsize=10)
  fig.text(.055,.182,f'Original metal: {mass["original_metal"]["mass_kg"]:.6f} kg  |  primary planning total: {mass["planning_models"]["primary_preserve_200g_total"]["aggregate"]["mass_kg"]:.6f} kg',fontsize=11)
  fig.text(.055,.135,'Orange: PORT01 trimmed blocks 1 / 8. Gold: hardware envelopes. Shoulder height and forward clearance unchanged.\nNominal geometry only; not a manufacturing drawing. Tolerances, preload, plugs and full thread lengths remain open.',fontsize=9,linespacing=1.6)
  fig.text(.055,.047,NOTICE+'  |  CC BY-NC 4.0  |  1 / 2',fontsize=8,color='#60737c');pages.savefig(fig);fig.savefig(OUT/'assembly-reference.png',dpi=170);plt.close(fig)
  fig=plt.figure(figsize=(11.7,8.3));fig.suptitle('Connections and geometry-only print set',fontsize=17,x=.055,ha='left',y=.962)
  ax=fig.add_axes([.04,.24,.55,.65],projection='3d')
  for n,(v,f) in meshes.items():ax.add_collection3d(Poly3DCollection(v[f],facecolors=colors[n],edgecolors='none',linewidths=0,rasterized=True))
  ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_zlim(lo[2],hi[2]);ax.set_box_aspect(hi-lo);ax.view_init(25,133);ax.set_xlabel('X [mm]');ax.set_ylabel('Y [mm]');ax.set_zlabel('Z [mm]');ax.set_title('Original assembly; motors omitted')
  note=('8 x Fabory 07000.040.100 (candidate)\nM4 x 0.7 x 100, class 12.9, plain\nMax head D7 x H4; AF3; thread b20\n\nY stack [mm]\nHead bearing plane: -11.5\nThread start: -91.5\nBlock entry: -104.5\nScrew tip: -111.5\nBlock rear: -112.5\n\nGrip 93 / geometric entry 7 / tip gap 1\nEffective complete-thread entry: TBD\n\nNominal head bearing footprint\n'+f'{connections["nominal_new_head_bearing_area_mm2"]:.3f} mm2 each at max head diameter\n'+f'Same-force pressure ratio vs old: {connections["pressure_ratio_at_same_force"]:.4f}\n'+ 'No preload / wrench torque selected.')
  fig.text(.63,.875,note,va='top',fontsize=10,linespacing=1.5)
  fig.text(.055,.18,'Geometry-only print set: 11 individual original parts. Each STL has a declared reversible print-frame transform.\nDo not energize motors or apply a payload/preload through printed parts. No inserts or printed threads are qualified.',fontsize=10,linespacing=1.7)
  fig.text(.055,.047,NOTICE+'  |  CC BY-NC 4.0  |  2 / 2',fontsize=8,color='#60737c');pages.savefig(fig);fig.savefig(OUT/'connections-reference.png',dpi=170);plt.close(fig)
 return dict(file=pdf.name,sha256=sha(pdf),pages=2,projection_source='Tessellation of the39 exported original/proxy solids, no supplier geometry',bbox_world_mm=[lo,hi],dimension_units='mm',manufacturing_drawing=False)

def audit_and_freeze():
 from pypdf import PdfReader
 document=ROOT/'docs/engineering/shoulder-raise03.md';qa=json.loads((OUT/'qa.json').read_text());manifest=json.loads((OUT/'structure-parts.json').read_text());m=json.loads((OUT/'mass-properties.json').read_text());path=json.loads((OUT/'long-screw-insertion.json').read_text());printqa=json.loads((OUT/'geometry-only-print/manifest.json').read_text())
 assert qa['long_screw_paths_complete'] and path['vendor_hashes_match_frozen02'];assert qa['generator_sha256']==sha(__file__)
 assert qa['source_hashes']==manifest['source_hashes'];assert all(sha(ROOT/p)==h for p,h in qa['source_hashes'].items())
 parts=manifest['parts'];assert len(parts)==39 and len({p['id'] for p in parts})==39
 assert all(sha(OUT/p['file'])==p['sha256'] and p['preceding_joints']==1 and p['follows_joints']==['J1'] and np.array_equal(p['T_world_from_part_mm'],np.eye(4)) for p in parts)
 assert len([p for p in parts if p['mass_kg'] is None])==16
 for p in parts:
  if p['mass_kg'] is None:assert p['part_number'] is None and p['stack']['length_mm'] is None and p['inertia_about_COM_world_axes_kg_m2'] is None
 # Independent aggregate via origin raw moments, instead of per-part COM shifts.
 def raw_moment_check(bodies,target):
  mass=sum(b['mass_kg'] for b in bodies);c=sum(b['mass_kg']*np.array(b['com_home_m']) for b in bodies)/mass;Jo=np.zeros((3,3));mins=[]
  for b in bodies:
   I=np.array(b['inertia_com_kg_m2']);e=np.linalg.eigvalsh(I);assert np.max(abs(I-I.T))<1e-12 and e.min()>0 and e.max()<=e.sum()-e.max()+1e-12;mins.append(float(e.min()));x=np.array(b['com_home_m']);Jo+=I+b['mass_kg']*((x@x)*np.eye(3)-np.outer(x,x));assert np.array_equal(b['orientation_home'],np.eye(3)) and b['preceding_joints']==1
  Ic=Jo-mass*((c@c)*np.eye(3)-np.outer(c,c));errors=dict(mass_kg=abs(mass-target['mass_kg']),COM_m=float(np.max(abs(c-target['com_world_m']))),inertia_kg_m2=float(np.max(abs(Ic-target['inertia_about_COM_world_axes_kg_m2']))));assert errors['mass_kg']<1e-12 and errors['COM_m']<1e-12 and errors['inertia_kg_m2']<1e-12
  return dict(body_count=len(bodies),minimum_individual_inertia_eigenvalue_kg_m2=min(mins),independent_origin_moment_errors=errors)
 masschecks={'quantified':raw_moment_check(m['quantified_bodies'],m['quantified_subtotal'])}
 for n,v in m['planning_models'].items():
  masschecks[n]=raw_moment_check(v['bodies'],v['aggregate']);assert len(v['bodies'])==12 and sum(b['id']=='L12_hardware_reserve' for b in v['bodies'])==1
  ledger=v['hardware_ledger'];assert abs(ledger['known_catalogue_allocation_kg']+.0-.1276)<1e-12 and abs(ledger['known_catalogue_allocation_kg']+ledger['unallocated_planning_kg']-ledger['total_planning_kg'])<1e-12
 assert len(printqa['parts'])==11 and all(sha(OUT/r['file'])==r['sha256'] and r['watertight'] and r['winding_consistent'] for r in printqa['parts'])
 pd=PdfReader(str(OUT/'SHOULDER-RAISE03-assembly-reference.pdf'));assert len(pd.pages)==2 and all('SHOULDER' in pd.pages[i].extract_text() or 'Connections' in pd.pages[i].extract_text() for i in range(2))
 links=[]
 for target in re.findall(r'\]\(([^)]+)\)',document.read_text()):
  if target.startswith(('https:','http:','#')):continue
  p=(document.parent/target.split('#')[0]).resolve();assert p.exists(),p;links.append(str(p.relative_to(ROOT)))
 checks=sum(sum(c['pair_count'] for c in v['checks'].values()) for v in path['screws'].values());assert len(path['screws'])==8 and checks==1040 and not any(c['events'] for v in path['screws'].values() for c in v['checks'].values())
 result=dict(revision=REV,source_hash_count=len(qa['source_hashes']),source_hash_checks_pass=True,source_frame='World home mm, inertial SI/world axes; all preceding_joints1',part_count=39,original_metal_count=11,catalogue_mass_fastener_count=12,unknown_complete_fastener_count=16,raw_origin_aggregation_checks=masschecks,continuous_screw_solid_pair_count=checks,all_screw_events_empty=True,PDF_pages=2,documentation_local_links=links,print_parts_hashes_and_mesh_checks_pass=True,manufacturing_release=False,physical_payload_qualified=False)
 dump('delivery-audit.json',result)
 files=[Path(__file__).resolve(),document]+sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='ready-manifest.json')
 ready=dict(revision=REV,status='READY_for_root_review_local_geometry_and_mass_only',license='CC-BY-NC-4.0',required_notice=NOTICE,files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in files},total_bytes_excluding_this_manifest=sum(p.stat().st_size for p in files),main_model_modified=False,commit_performed=False,manufacturing_release=False)
 dump('ready-manifest.json',ready);print('READY',len(files),ready['total_bytes_excluding_this_manifest'],sha(OUT/'ready-manifest.json'),flush=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['build','paths','all','audit'],default='all');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 if args.stage=='audit':audit_and_freeze();return
 geometry,metadata,old,previous,port,proc,iface,hashes,inputs=read_inputs();print('READ_FROZEN39',flush=True);mass=mass_models(metadata,previous);export(geometry,metadata,hashes,mass);proof=inheritance(geometry,old,inputs,hashes,port);dump('geometry-inheritance.json',proof);print('GEOMETRY_MASS_READY',mass['original_metal']['mass_kg'],mass['planning_models']['primary_preserve_200g_total']['aggregate']['mass_kg'],flush=True)
 if args.stage in ['paths','all']:dump('long-screw-insertion.json',verify_long_screw_paths(geometry,metadata,hashes))
 connections=connection_changes(geometry,metadata,old,port);dump('connection-changes.json',connections);print('CONTACTS_READY',flush=True)
 printqa=print_parts(geometry,metadata);dump('geometry-only-print/manifest.json',printqa);print('PRINT_GEOMETRY_READY',flush=True)
 drawing=drawings(geometry,metadata,mass,connections);dump('drawing-manifest.json',drawing)
 manifest=json.loads((OUT/'structure-parts.json').read_text());manifest['source_hashes']=hashes;dump('structure-parts.json',manifest)
 unchanged={p:sha(ROOT/p)==h for p,h in hashes.items()};assert all(unchanged.values());dump('qa.json',dict(revision=REV,license='CC-BY-NC-4.0',required_notice=NOTICE,source_hashes=hashes,source_integrity=unchanged,unit_checks=unit_checks(),manufacturing_release=False,physical_payload_qualified=False,generator_sha256=sha(__file__),geometry_and_mass_complete=True,long_screw_paths_complete=args.stage in ['paths','all'],original_parts_print_watertight=all(r['watertight'] for r in printqa['parts']),drawing_pages=drawing['pages']));print('DONE',flush=True)
 if args.stage=='all':audit_and_freeze()
if __name__=='__main__':main()
