#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""HEAD04: frozen HEAD03 + CD-MOUNT01 + reviewed CD-PCB01, in head coordinates.

Read-only upstream composition. Electronic clearance envelopes never gain a
material density. CAD density inputs below are conditional, not released stock.
"""
import argparse, copy, csv, hashlib, itertools, json
from pathlib import Path
import cadquery as cq
import numpy as np
import trimesh
from screen_integrated_collisions import named_step
from build_layout import moved
import head_mass04_study as mass04
import gripper_root_support_study as st
import central_display_mount01 as cd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/head-integrated04'
BASE=ROOT/'engineering/generated/head-integrated-03'
MOUNT=ROOT/'engineering/generated/central-display-mount01'
PCB=ROOT/'engineering/electronics/central-display-cd01/pcb01'
REV='HEAD-INTEGRATED04'
NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)'
REMOVED={'removable_optical_frame','display_including_candidate_GH_keepout'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(name,data):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,indent=2)+'\n')
def volume(s):return sum(x.Volume() for x in s.Solids())
def common(a,b):return sum(x.intersect(y).Volume() for x in a.Solids() for y in b.Solids())
def box(lo,hi):return st.B(lo[0],hi[0],lo[1],hi[1],lo[2],hi[2])
def shape_meta(n,s,material,density=None,**extra):
 return dict(id=n,group='head_fixed',finger=None,material=material,source=extra.pop('source','CD-MOUNT01 frozen nominal BREP'),representation=extra.pop('representation','original nominal shape'),shape_volume_mm3=volume(s),bbox_head_mm=[v.tolist() for v in st.bb(s)],mass_g=volume(s)*density if density is not None else None,mass_status=f'nominal assumed uniform density rho={density} g/mm3; not measured or manufacturing selected' if density is not None else 'unknown physical mass; no density assigned to electronic envelope',density_g_mm3=density,**extra)

def public_part_metadata(p):
 # Old HEAD03 contains historical face804 world transforms. They cannot be
 # offered as usable world placements in a head-local/raised-face839 handoff.
 q={k:v for k,v in p.items() if k not in ['world_from_baked_mesh_transform_m','COM_world_mm']}
 q['metadata_frame_note']='Head-local source metadata; historical world placement fields removed. Actual baked state is defined at the top level. Source mass/COM annotations describe home geometry, not an independently recomputed closed-state ledger.'
 return q

def annotate_budget(model):
 vals=model.get('quantified_subtotal_with_listed_allowances_kg_interval') or model['whole_head_planning_mass_kg_interval']
 model['quantified_subtotal_with_listed_allowances_kg_interval']=vals
 model['whole_head_planning_mass_kg_interval']=None
 model['unallocated_items']=[dict(item='Head controller PCBs and their components, local power converters, their mounts and interconnects',mass_kg_interval=None,basis='HEAD-CTRL02/PASSIVES01/POWER01 layouts and installed masses not integrated. No invented density for reserved volumes; listed earlier lamp-board allowances do not cover this controller assembly.')]
 model['route_status']='Archived P16 head integration. Superseded as active drive route by confirmed <=1s empty full opening/closing cycle and illuminated-face gripping requirement.'
 model['whole_mass_note']='2.830643kg modeled nominal/proxy head plus185..450g listed planning allowances is a partial subtotal only. Unallocated controller/power hardware prevents a complete head planning mass bound.'
 return model

def load():
 paths=[BASE/n for n in ['HEAD-INTEGRATED03-open.step','HEAD-INTEGRATED03-closed.step','blender-parts-manifest.json','blender-parts-manifest-closed.json','qa.json']]
 paths += [MOUNT/'study.json',MOUNT/'led-centres.csv',PCB/'mechanical-interface.json',PCB/'kicad/central.kicad_pcb',ROOT/'engineering/generated/head-mass04/mass-properties.json']
 paths += [ROOT/'engineering'/n for n in ['head_mass04_study.py','screen_integrated_collisions.py','build_layout.py','gripper_root_support_study.py','central_display_mount01.py']]
 report=read(MOUNT/'study.json');paths += [MOUNT/n for n in report['artifact_sha256'] if n.endswith('.step')]
 hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
 assert read(BASE/'qa.json')['artifact_integrity_passed']
 for path,digest in read(ROOT/'engineering/generated/head-mass04/mass-properties.json')['source_hashes'].items():assert sha(ROOT/path)==digest,(path,'inertial baseline provenance')
 for n,h in report['artifact_sha256'].items():assert sha(MOUNT/n)==h,(n,'mount hash')
 pcb=read(PCB/'mechanical-interface.json');assert pcb['board_sha256']==sha(PCB/'kicad/central.kicad_pcb')
 original=named_step(BASE/'HEAD-INTEGRATED03-open.step');manifest=read(BASE/'blender-parts-manifest.json')
 oldmeta={p['id']:p for p in manifest['parts']};assert original.keys()==oldmeta.keys() and len(original)==697
 shapes={n:s for n,s in original.items() if n not in REMOVED};meta={n:copy.deepcopy(p) for n,p in oldmeta.items() if n not in REMOVED}
 added={};ameta={}
 for n in report['artifact_sha256']:
  if not n.endswith('.step'):continue
  key=Path(n).stem;s=cq.importers.importStep(str(MOUNT/n)).val();added[key]=s
  if key=='CD01-GH12-mated-reference':material,density='electronic_mass_TBD',None
  elif key=='CD01-PCB-outline':material,density='PCB_laminate_assumed',.00185
  elif key in ['CD01-window','CD01-insulating-spacer']:material,density='polycarbonate_assumed',.0012
  elif key in ['CD01-cup','CD01-bezel','CD01-optical-frame']:material,density='aluminum_assumed',.0027
  else:material,density='steel_assumed',.00785
  ameta[key]=shape_meta(key,s,material,density)
 pixels=list(csv.DictReader((MOUNT/'led-centres.csv').open()))
 for r in pixels:
  i=int(r['index']);x,y=float(r['x_mm']),float(r['y_mm']);n=f'CD01-LED-{i:03}'
  added[n]=st.B(x-1.2,x+1.2,y-.45,y+.45,-2,-1.1)
  ameta[n]=shape_meta(n,added[n],'electronic_mass_TBD',representation='max body/land assembly envelope',source='CD-MOUNT01 LED centres, CD-PCB01 front contract',mpn='150060YS75000',LED_index=i)
 assert len(pixels)==285 and len(added)==300
 # The original CD-MOUNT envelope is larger than the board's GH reference and
 # remains the clearance representation; do not count a second connector.
 for r in pcb['components_back']:
  if r['ref']=='J1':
   gh=box(r['envelope_head_min_mm'],r['envelope_head_max_mm']);assert volume(gh.cut(added['CD01-GH12-mated-reference']))<1e-6
   ameta['CD01-GH12-mated-reference'].update(mpn=r['manufacturer_part_number'],ecad_reference='J1',ecad_component=r)
   continue
  n='CD01-PCBA-'+r['ref'];body=r['mcad_material_envelope'];s=box(body['head_min_mm'],body['head_max_mm']);added[n]=s
  assert volume(s.cut(box(r['envelope_head_min_mm'],r['envelope_head_max_mm'])))<1e-6
  ameta[n]=shape_meta(n,s,'electronic_mass_TBD',source='CD-PCB01 native-board placement; mechanical-interface.json',representation='published maximum package box, only Z translated by0.10mm planned solder height; no lands/XY allowance; not vendor BREP',mpn=r['manufacturer_part_number'],ecad_reference=r['ref'],ecad_component=r)
 assert len(pcb['components_back'])==33 and len(added)==332
 shapes.update(added);meta.update(ameta);assert len(shapes)==1027
 assert all(s.isValid() and len(s.Solids())==1 for s in shapes.values())
 return shapes,meta,original,oldmeta,manifest,report,pcb,hashes

def clearance(shapes,meta,original,oldmeta,manifest,mount,pcb):
 obstacle=cd.union([st.C(32,12.75,(0,0,-11),(0,0,1)),st.B(-38.25,-30,-4,4,-11,1.75),st.B(30,38.25,-4,4,-11,1.75)]+[st.C(2.5,22,(x,0,-17.9),(0,0,1)) for x in [-35.25,35.25]])
 containment=[]
 for n,s in shapes.items():
  if not n.startswith('CD01-') or n=='CD01-optical-frame':continue
  outside=volume(s.cut(obstacle));assert outside<1e-4,(n,outside)
  containment.append(dict(id=n,outside_previously_certified_obstacle_mm3=outside))
 frame_added=volume(shapes['CD01-optical-frame'].cut(original['removable_optical_frame']));assert frame_added<1e-4
 # Structural body checks use complete plan envelopes (stronger than body-only
 # clearance). Inter-component plan-envelope overlaps are reported separately.
 mechanics={n:s for n,s in shapes.items() if n.startswith('CD01-') and meta[n]['mass_g'] is not None}
 back={}
 for n,s in shapes.items():
  if n.startswith('CD01-PCBA-'):
   r=meta[n]['ecad_component'];back[n]=box(r['envelope_head_min_mm'],r['envelope_head_max_mm'])
  elif n=='CD01-GH12-mated-reference':back[n]=s
 checks=[]
 for n,s in back.items():
  for k,t in mechanics.items():
   d=s.distance(t);v=0. if d>1e-5 else common(s,t)
   assert v<1e-4,(n,k,v);checks.append(dict(a=n,b=k,gap_mm=d,intersection_mm3=v))
 margin_overlaps=[]
 for (n,s),(k,t) in itertools.combinations(back.items(),2):
  if st.gap_bounds(st.bb(s),st.bb(t))>1e-6:continue
  v=common(s,t)
  if v>1e-4:margin_overlaps.append(dict(a=n,b=k,plan_allowance_envelope_overlap_mm3=v,interpretation='Assembly allowance/land envelope overlap; use CD-PCB01 independent actual package/body audit for physical assembly clearance.'))
 return dict(prior_CD_MOUNT_obstacle_containment=containment,replacement_frame_added_volume_mm3=frame_added,unchanged_fingers_and_P16=True,inherited_continuous_motion=mount['continuous_motion'],inheritance_logic='Every newly introduced object lies inside the exact previously certified display obstacle; replacement frame only loses material. All moving HEAD03 solids and kinematics are unchanged. Consequently the parent nominal continuous clearance lower bounds still apply to this integration.',electronics_to_nominal_mount_checks=checks,inter_component_planning_envelope_overlaps=margin_overlaps,scope='CAD nominal clearance only. No wires, tolerances, strain, conductive seating or physical assembly validation.')

def inertial(shapes,meta,manifest):
 previous=read(ROOT/'engineering/generated/head-mass04/mass-properties.json')
 parts=[copy.deepcopy(p) for p in previous['bodies'] if p['id'][5:] not in REMOVED]
 unknown=[copy.deepcopy(p) for p in previous['unweighed_parts'] if p['id'][5:] not in REMOVED]
 additions=[]
 for n,p in meta.items():
  if not n.startswith('CD01-'):continue
  gp=mass04.geometry_properties(shapes[n]);base=dict(id='HEAD_'+n,body_id='HEAD_head_fixed',kinematic_group='head_fixed',finger=None,material=p['material'],shape_volume_mm3=gp['volume_mm3'],mass_measured=False,source=p['source'])
  if p['mass_g'] is None:
   unknown.append(dict(**base,mass_kg=None,com_head_home_m=None,inertia_about_COM_head_axes_kg_m2=None,envelope_centroid_head_m=gp['com_m'].tolist(),assumption='Unweighed electronic envelope, not zero physical mass.',inertia_is_proxy=None));continue
  m=p['mass_g']*.001;I=m*gp['inertia_per_mass_m2'];r=dict(**base,mass_kg=m,com_head_home_m=gp['com_m'].tolist(),inertia_about_COM_head_axes_kg_m2=I.tolist(),mass_inertia_basis='nominal_CAD_uniform_assumed_material',inertia_is_proxy=True,assumption=p['mass_status'],tensor_check=mass04.tensor_check(I));parts.append(r);additions.append(r)
 bodies=[]
 for bid in dict.fromkeys(x['body_id'] for x in parts):
  members=[p for p in parts if p['body_id']==bid];first=members[0];agg=mass04.combine(members)
  bodies.append(dict(id=bid,**agg,kinematic_group=first['kinematic_group'],finger=first['finger'],source=[p['id'] for p in members],contains_proxy=any(p['inertia_is_proxy'] for p in members),mass_measured=False,tensor_check=mass04.tensor_check(np.array(agg['inertia_about_COM_head_axes_kg_m2']))))
 assert len(bodies)==13
 joints={p['id']:p for p in manifest['finger_joints']};qs={f:np.deg2rad(j['range_deg'][1]) for f,j in joints.items()}
 totals={'open':mass04.combine(parts),'closed':mass04.combine([mass04.transform_body(p,qs.get(p['finger'],0),joints) for p in parts])}
 budget=copy.deepcopy(previous['planning_remainder'])
 central=next(p for p in budget if p['item']=='Central display/optics and its mounting')
 central.update(item='Central display unweighed electronic components, copper/solder and future thermal/insulating hardware',basis='NEW conservative planning allocation retaining25..60g numerically after CAD-added cup/PCB/window/fasteners; no supplier mass or proven bound. Old complete central-module allocation is retired; modeled parts are not included again.',COM_head_home_box_m=[[-.025,-.025,-.011],[.025,.025,.002]])
 low,high=[sum(p['mass_kg_interval'][i] for p in budget) for i in [0,1]]
 return dict(revision=REV,license='CC-BY-NC-4.0',required_notice=NOTICE,units={'length':'m','mass':'kg','inertia':'kg*m^2'},coordinate_contract={'frame':'head face home','inertia_reference':'each COM resolved in head home axes','raised_parent_face_world_m':[0,.055,.839],'J7_pivot_head_home_m':[0,0,-.164]},bodies=parts,unweighed_parts=unknown,aggregated_bodies=bodies,finger_joints=manifest['finger_joints'],whole_head_nominal_proxy=totals,planning_remainder=budget,planning_remainder_total_kg_interval=[low,high],whole_head_planning_mass_kg_interval=[totals['open']['mass_kg']+low,totals['open']['mass_kg']+high],change_from_HEAD_MASS04={'removed_modeled_mass_kg':sum(p['mass_kg'] for p in previous['bodies'] if p['id'][5:] in REMOVED),'added_modeled_mass_kg':sum(p['mass_kg'] for p in additions),'delta_modeled_mass_kg':totals['open']['mass_kg']-previous['whole_head_nominal_proxy']['open']['mass_kg']},integration_rule='Choose primitive bodies OR 13 aggregate bodies, never both. Unknown entries are not physical zero. This head has not yet replaced the raised full-arm model.',manufacturing_release=False)

def colour(n,p):
 if '_LED_' in n or n.startswith('CD01-LED-'):return [245,166,38,255]
 if 'optical_sheet' in n or n=='CD01-window':return [242,222,160,90]
 if 'PCB' in n and 'PCBA' not in n:return [27,94,72,255]
 m=p['material']
 if m.startswith('silicone'):return [56,151,129,255]
 if m in ['electronic_mass_TBD','P16_envelope','catalog_camera']:return [34,38,43,255]
 if m=='space_reservation':return [121,97,140,65]
 if m.startswith('aluminum'):return [99,124,139,255]
 return [171,184,190,255]

def export(shapes,meta,label,manifest,inertia):
 assembly=cq.Assembly(name=REV+'-'+label);scene=trimesh.Scene();rows=[]
 for n,s in shapes.items():
  p=meta[n];rgba=colour(n,p);assembly.add(s,name=n,color=cq.Color(*(v/255 for v in rgba)))
  vs,fs=s.tessellate(.12,.05);mesh=trimesh.Trimesh(np.array([v.toTuple() for v in vs])*.001,np.array(fs),process=True);mesh.merge_vertices(digits_vertex=9);assert mesh.is_watertight,(n,'mesh not closed')
  mesh.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(name=p['material'],baseColorFactor=rgba,metallicFactor=.5 if p['material'].startswith(('aluminum','steel')) else 0,roughnessFactor=.55,alphaMode='BLEND' if rgba[3]<255 else 'OPAQUE'))
  scene.add_geometry(mesh,node_name=n,geom_name=n)
  rows.append(dict(id=n,group=p['group'],finger=p['finger'],material=p['material'],source=p['source'],representation=p.get('representation'),shape_volume_mm3=volume(s),bbox_head_mm=[v.tolist() for v in st.bb(s)],mesh_watertight=True,source_metadata=public_part_metadata(p)))
 path=OUT/(REV+'-'+label+'.step');assembly.save(str(path));back=named_step(path);assert back.keys()==shapes.keys()
 errors=[]
 for n,s in shapes.items():
  dv=volume(back[n])-volume(s);dc=np.linalg.norm(np.array(back[n].Center().toTuple())-np.array(s.Center().toTuple()));assert abs(dv)<max(1e-4,volume(s)*1e-7) and dc<1e-6,(n,dv,dc);errors.append([dv,dc])
 glb=OUT/(REV+'-'+label+'.glb');scene.metadata['units']='meters';scene.export(str(glb));rt=trimesh.load(glb,force='scene');assert set(rt.geometry)==set(shapes)
 result=dict(revision=REV,state=label,head_face_world_mm=[0,55,839],mesh_frame='head face, metres, baked at stated q',geometry_baked_q_deg_by_finger={j['id']:j['range_deg'][1] if label=='closed' else 0 for j in manifest['finger_joints']},finger_joints=manifest['finger_joints'],parts=rows,GLB=glb.name,GLB_sha256=sha(glb),STEP=path.name,STEP_sha256=sha(path),all_meshes_watertight=True,STEP_roundtrip_max_volume_error_mm3=max(abs(x[0]) for x in errors),STEP_roundtrip_max_COM_error_mm=max(x[1] for x in errors),manufacturing_release=False)
 save('parts-'+label+'.json',result);print(label,len(rows),'STEP/GLB reimport passed',flush=True)
 return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--no-export',action='store_true');parser.add_argument('--annotations-only',action='store_true');parser.add_argument('--blender-mesh-output',type=Path);args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 if args.annotations_only:
  record=read(OUT/'study.json')
  assert all(sha(ROOT/p)==h for p,h in record['source_hashes'].items())
  for state in ['open','closed']:
   data=read(OUT/f'parts-{state}.json')
   assert sha(OUT/data['GLB'])==data['GLB_sha256'] and sha(OUT/data['STEP'])==data['STEP_sha256']
   for row in data['parts']:row['source_metadata']=public_part_metadata(row['source_metadata'])
   data['route_status']='Archived P16 reference, superseded by confirmed1s empty full-cycle requirement';save(f'parts-{state}.json',data)
  save('mass-properties.json',annotate_budget(read(OUT/'mass-properties.json')))
  record['geometry_generator_sha256_before_annotation']=record.get('geometry_generator_sha256_before_annotation',record['script_sha256']);record['script_sha256']=sha(__file__);record['annotation_refresh_only']='No STEP/GLB or numerical mass/COM/inertia changes; world metadata stripped and incomplete mass budget identified.';record['route_status']='Archived P16 integration; no current1s cycle capability';save('study.json',record);return
 shapes,meta,original,oldmeta,manifest,mount,pcb,hashes=load();print('Loaded frozen1027-object assembly',flush=True)
 cl=clearance(shapes,meta,original,oldmeta,manifest,mount,pcb);save('clearance.json',cl)
 inertia=annotate_budget(inertial(shapes,meta,manifest));save('mass-properties.json',inertia);print('Nominal/proxy kg',inertia['whole_head_nominal_proxy']['open']['mass_kg'],flush=True)
 states={}
 if not args.no_export:
  states['open']=export(shapes,meta,'open',manifest,inertia)
  closed0=named_step(BASE/'HEAD-INTEGRATED03-closed.step');closed={n:s for n,s in closed0.items() if n not in REMOVED};closed.update({n:s for n,s in shapes.items() if n.startswith('CD01-')})
  states['closed']=export(closed,meta,'closed',manifest,inertia)
  # Independent exported closed-solid integration versus kinematic transform.
  comparisons=[]
  for p in inertia['bodies']:
   n=p['id'][5:];gp=mass04.geometry_properties(closed[n]);joints={j['id']:j for j in manifest['finger_joints']};q=np.deg2rad(joints[p['finger']]['range_deg'][1]) if p['finger'] else 0
   predicted=mass04.transform_body(p,q,joints);dc=float(np.linalg.norm(gp['com_m']-np.array(predicted['com_head_home_m'])));di=float(np.max(abs(gp['inertia_per_mass_m2']*p['mass_kg']-np.array(predicted['inertia_about_COM_head_axes_kg_m2']))));assert dc<1e-7 and di<1e-10,(n,dc,di);comparisons.append(dict(id=n,closed_COM_error_m=dc,closed_inertia_error_kg_m2=di))
  save('closed-transform-check.json',comparisons)
  if args.blender_mesh_output:
   scene=trimesh.load(OUT/states['open']['GLB'],force='scene');parts=[]
   for p in states['open']['parts']:
    n=p['id'];T,g=scene.graph.get(n);mesh=scene.geometry[g].copy();mesh.apply_transform(T)
    parts.append(dict(id=n,vertices_m=mesh.vertices.tolist(),triangles=mesh.faces.tolist(),material=p['material'],group=p['group'],finger=p['finger'],source=p['source']))
   meshdata=dict(revision=REV,parts=parts,finger_joints=manifest['finger_joints'],closed_bounds_head_mm={p['id']:p['bbox_head_mm'] for p in states['closed']['parts']},GLB_sha256=states['open']['GLB_sha256'],source_hashes=hashes,scope='Head04 only, head face at origin. J7 geometric roll pivot at Z=-164mm. External arm not included. P16 remains conditional duty route.')
   args.blender_mesh_output.parent.mkdir(parents=True,exist_ok=True);args.blender_mesh_output.write_text(json.dumps(meshdata,separators=(',',':'))+'\n')
 assert all(sha(ROOT/p)==h for p,h in hashes.items()),'Upstream changed during integration'
 save('study.json',dict(revision=REV,status='nominal CAD and inertial integration; no manufacturing release',license='CC-BY-NC-4.0',required_notice=NOTICE,source_hashes=hashes,script_sha256=sha(__file__),upstream_unchanged=True,part_count=len(shapes),new_CAD_parts_and_envelopes=332,removed_old_parts=sorted(REMOVED),unchanged_old_parts=695,LED_count_total=629,coordinate_contract='Head-local geometry, +Z toward workpiece. Head03 face804 is not baked; raised parent places face at839mm. J7 pivot remains headZ=-164mm.',exports={k:{q:v[q] for q in ['STEP','STEP_sha256','GLB','GLB_sha256','STEP_roundtrip_max_volume_error_mm3','STEP_roundtrip_max_COM_error_mm']} for k,v in states.items()},exclusions=['Head controller/power PCB and actual harness not integrated','Plan allowance envelopes are not physical package solids or vendor BREP','No material procurement, full stack tolerance, insulation, thermal path or manufacturing release','No change to full-arm mass/Blender until separately integrated','P16 duty/force and actual gripper validation remain open']))

if __name__=='__main__':main()
