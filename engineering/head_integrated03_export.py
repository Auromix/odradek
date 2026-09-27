#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Fresh per-part mass/COM, original STEP and Blender-readable GLB/manifest."""
import csv,hashlib,json,math
from pathlib import Path
import cadquery as cq
import numpy as np
import trimesh
import head_integrated03_study as hi
ROOT,OUT,st,p16=hi.ROOT,hi.OUT,hi.st,hi.p16

def colour(n,mat):
 if n.startswith('LED_'):return [245,166,38,255]
 if 'optical_sheet' in n:return [242,222,160,95]
 if 'PCB_outline' in n:return [27,94,72,255]
 if mat=='silicone_DS30':return [56,151,129,255]
 if mat in ['electronic_mass_TBD','catalog_camera']:return [34,38,43,255]
 if mat=='space_reservation':return [121,97,140,65]
 if mat=='aluminum':return [99,124,139,255]
 return [171,184,190,255]

def rows_at(f,roots,rmeta,fixed,fmeta,closed):
 rows=[]
 for n,s in fixed.items():rows.append(dict(id=n,shape=s,group='head_fixed',meta=fmeta[n],finger=None))
 for i,ff in enumerate(f):
  q=ff['closure_study_deg'] if closed else 0.
  for n,s in roots[i].items():rows.append(dict(id=ff['id']+'_'+n,shape=st.place(s,ff,st.SIGNS[i],q),group=ff['id']+'_rotor',meta=rmeta[i][n],finger=ff['id'],local_name=n))
  for n,s in p16.envelopes(q).items():rows.append(dict(id=ff['id']+'_P16_envelope_'+n,shape=st.place(s,ff,st.SIGNS[i]),group=ff['id']+'_P16_kinematic',meta=dict(material='P16_envelope',representation='original envelope contains checked supplier CAD',mass_method='four envelope primitives share single catalog95g, not individually weighed',source='P16-PACK01 native-contained original envelope'),finger=ff['id'],local_name=n))
 return rows

def mass(rows):
 ledger=[];unknown=[];actors={}
 for r in rows:
  n,s,m=r['id'],r['shape'],r['meta'];material=m['material'];p=np.array(s.Center().toTuple())
  if material=='P16_envelope':actors.setdefault(r['finger'],[]).append(s);continue
  if 'catalog_mass_g' in m:mg=m['catalog_mass_g'];method=m['mass_method']
  elif material in hi.DENSITY:mg=s.Volume()*hi.DENSITY[material];method=m['mass_method']+'; rho='+str(hi.DENSITY[material])+' g/mm3'
  else:unknown.append(dict(part=n,material=material,reason=m['mass_method'],center_head_mm=p.tolist()));continue
  ledger.append(dict(part=n,mass_g=mg,center_head_mm=p.tolist(),center_world_mm=(p+hi.FACE).tolist(),method=method))
 for finger,sh in actors.items():
  p=np.array(st.comp(sh).Center().toTuple());ledger.append(dict(part=finger+'_P16_complete',mass_g=95.,center_head_mm=p.tolist(),center_world_mm=(p+hi.FACE).tolist(),method='Actuonix catalog95g; combined envelope-volume centroid proxy only'))
 total=sum(r['mass_g'] for r in ledger);com=sum(r['mass_g']*np.array(r['center_head_mm']) for r in ledger)/total
 # Keep unweighed, unselected remainder visible instead of massing space boxes.
 budget=[dict(item='Four PCBA discrete components, GH pairs, copper/plating/solder',mass_g=[20,60],basis='planning5..15g per board; no verified individual vendor masses',COM_head_box_mm=[[-25,-15,0],[25,30,125]]),dict(item='Central display/optics and its mounting',mass_g=[25,60],basis='planning only',COM_head_box_mm=[[-8,-8,-12],[8,8,1]]),dict(item='Head harness / FAKRA / strain relief',mass_g=[50,120],basis='planning only',COM_head_box_mm=[[-30,-30,-100],[30,30,-10]]),dict(item='Armor / guards / remaining structural small hardware',mass_g=[80,180],basis='planning only',COM_head_box_mm=[[-15,-15,-65],[15,15,40]]),dict(item='Four optical-sheet retention frames or equivalent',mass_g=[10,30],basis='planning only; no physical retainer designed',COM_head_box_mm=[[-20,-10,5],[20,30,100]])]
 return dict(modeled_mass_g=total,COM_proxy_head_mm=com.tolist(),COM_proxy_world_mm=(com+hi.FACE).tolist(),ledger=ledger,unweighed_parts=unknown,planning_remainder=budget,whole_head_planning_g=[total+sum(x['mass_g'][k] for x in budget) for k in [0,1]],excludes='J7 motor itself; full arm; workpiece. Unknown discrete component masses not set to zero. Density-based PC/FR4/insulator are assumptions, not purchased material or actual board weights.',limits='Fresh sum from every present part solid and controlled catalogue masses; no old whole-head mass copied or simply shifted. Vendor internal COM and exact finished screw mass distribution unavailable; proxies flagged. Real cable and sheet retainers not modeled.')

def exportSTEP(rows,label):
 name='HEAD-INTEGRATED03-'+label+'.step';a=cq.Assembly(name=name[:-5])
 for r in rows:
  rgba=colour(r.get('local_name',r['id']),r['meta']['material']);a.add(r['shape'],name=r['id'],color=cq.Color(*(x/255 for x in rgba)))
 a.save(str(OUT/name));rt=cq.importers.importStep(str(OUT/name)).val();expected=sum(len(r['shape'].Solids()) for r in rows);assert rt.isValid() and len(rt.Solids())==expected
 return dict(path=name,parts=len(rows),solids=len(rt.Solids()),valid=True,roundtrip_volume_delta_mm3=rt.Volume()-sum(r['shape'].Volume() for r in rows),sha256=hi.sha(OUT/name))

def exportBlender(rows,f,label,mass_report):
 scene=trimesh.Scene();manifest=[];allvalid=True; ledger={r['part']:r for r in mass_report['ledger']}
 for r in rows:
  s=r['shape'];v,t=s.tessellate(.12,.05);mesh=trimesh.Trimesh(np.array([x.toTuple() for x in v]),np.array(t),process=True);mesh.merge_vertices(digits_vertex=6);watertight=bool(mesh.is_watertight);allvalid &=watertight
  mesh.vertices*=.001;rgba=colour(r.get('local_name',r['id']),r['meta']['material']);material=trimesh.visual.material.PBRMaterial(name=r['meta']['material'],baseColorFactor=rgba,metallicFactor=.6 if r['meta']['material'] in ['steel','aluminum'] else 0,roughnessFactor=.55,alphaMode='BLEND' if rgba[3]<255 else 'OPAQUE',doubleSided=False)
  mesh.visual=trimesh.visual.TextureVisuals(material=material);scene.add_geometry(mesh,node_name=r['id'],geom_name=r['id'])
  mr=ledger.get(r['id']); actor=r['meta']['material']=='P16_envelope'; q=next((ff['closure_study_deg'] for ff in f if ff['id']==r['finger']),0) if label=='closed' else 0; pos=np.array(s.Center().toTuple()); world_transform=np.eye(4);world_transform[:3,3]=hi.FACE*.001
  manifest.append(dict(id=r['id'],world_from_baked_mesh_transform_m=world_transform.tolist(),attachment=dict(arm_parent='J7_output',kind='independent_P16_linkage' if actor else 'finger_rigid_rotor' if r['finger'] else 'rigid_head',finger_q_deg=q,local_part=r.get('local_name'),axis_and_pivot_in_finger_joints=True),mass_g=mr['mass_g'] if mr else None,mass_group=r['finger']+'_P16_complete' if actor else None,mass_status=mr['method'] if mr else 'grouped catalog95g; do not count four times' if actor else 'unweighed envelope/reservation',COM_head_mm=mr['center_head_mm'] if mr else None,COM_world_mm=mr['center_world_mm'] if mr else None,COM_status='uniform-solid volume centroid assumption' if mr and 'rho=' in mr['method'] else 'catalog mass placed at envelope centroid proxy' if mr else 'group COM supplied separately' if actor else 'unknown',inertia_kg_m2=None,inertia_status='not computed / not identified; do not infer dynamics from display mesh',glb_node=r['id'],group=r['group'],finger=r['finger'],shape_volume_mm3=s.Volume(),bbox_head_mm=[x.tolist() for x in st.bb(s)],mesh_watertight=watertight,mesh_body_count=int(mesh.body_count),**r['meta']))
 scene.metadata['units']='meters';path=OUT/('HEAD-INTEGRATED03-'+label+'.glb');scene.export(str(path));roundtrip=trimesh.load(path,force='scene');assert len(roundtrip.geometry)==len(rows);assert allvalid
 joints=[]
 for i,ff in enumerate(f):
  a=math.radians(ff['phi_deg']);joints.append(dict(id=ff['id'],pivot_head_mm=[70*math.cos(a),70*math.sin(a),ff['root_z_mm']],closing_axis_head=[math.sin(a),-math.cos(a),0.],range_deg=[0,ff['closure_study_deg']],moving_group=ff['id']+'_rotor',mechanical_mirror_sign=st.SIGNS[i],PCB_same_variant_not_mirrored=True,P16=dict(group=ff['id']+'_P16_kinematic',D_mm=123,a_mm=26,phase_deg=68,base_local_xuz_mm=[0,-18,-123],tip_local_xuz_formula=['26*cos(q-68deg)',-18,'26*sin(q-68deg)'],body_frame='p16_packaging_study.kin(q): native envelope case/guide and slider/tip follow changing L and R, then mechanical mirror/azimuth/root placement',not_rigid_child_of_finger=True)))
 result=dict(revision='HEAD-INTEGRATED03',units_glb='m',units_manifest_geometry='mm',state=label,mesh_coordinate_frame='head face, all nodes baked in reported state head coordinates; no world shift baked',head_face_world_mm=hi.FACE.tolist(),J7_pivot_head_mm=[0,0,-164],J7_axis_head=[0,0,1],original_adapter_main_plate_world_z_range_mm=[640,650],original_adapter_complete_nominal_world_z_range_mm=[637.5,650],original_adapter_complete_mesh_bbox_world_mm=[(x+hi.FACE).tolist() for x in st.bb(next(r['shape'] for r in rows if r['id']=='J7_existing_adapter'))],mass_groups=[r for r in mass_report['ledger'] if r['part'].endswith('_P16_complete')],parts=manifest,finger_joints=joints,GLB_import_notes='Keep names; if animating finger groups, set each group origin to the given pivot and rotate about closing axis. P16 is an independent endpoint linkage, not a rigid finger child. Same PCB variant is used on each left/right pair without reflection.',glb_path=path.name,glb_sha256=hi.sha(path),glb_geometry_count=len(roundtrip.geometry),all_meshes_watertight=allvalid,vendor_BREP_redistributed=False,hardware_release=False)
 hi.dump('blender-parts-manifest'+('' if label=='open' else '-'+label)+'.json',result);return dict(file=path.name,geometry_count=len(rows),all_watertight=allvalid)

def sync_address_annotations():
 """Only permit electrical addresses/notes to change, never geometry or MPN."""
 changes=[]
 for variant in ['upper','lower']:
  for file in ['led-placement-reference.csv','bom.csv']:
   dest=hi.INP/(variant+'-'+file);source=hi.FPL/variant/file
   old=list(csv.DictReader(dest.open()));raw=source.read_text();new=list(csv.DictReader(raw.splitlines()));a={r['ref']:r for r in old};b={r['ref']:r for r in new};assert a.keys()==b.keys()
   allowed={'cs','sw','dot_index','dc_address','pwm_low_address','pwm_high_address'} if file.startswith('led-') else {'notes'}
   delta=[]
   for ref,n in b.items():
    fields={k:dict(old=a[ref].get(k),new=v) for k,v in n.items() if a[ref].get(k)!=v};assert not (fields.keys()-allowed),(variant,ref,fields)
    if fields:delta.append(dict(ref=ref,changed=fields))
   changes.append(dict(snapshot=dest.name,previous_sha256=hi.sha(dest),current_sha256=hashlib.sha256(raw.encode()).hexdigest(),geometry_fields_equal=True,changes=delta));dest.write_text(raw)
 hi.snapshot(False);hi.dump('electrical-address-update.json',dict(revision='HEAD-INTEGRATED03',geometry_unchanged=True,method='Identical ref sets; only electrical address and BOM notes fields permitted to change. Any placement/footprint/MPN change rejects this metadata-only operation.',updates=changes))

def refresh_manifest_metadata():
 """Refresh explicit handoff annotations only; never regenerate geometry/mass."""
 snapshot=json.loads((OUT/'input-snapshot.json').read_text())
 for label in ['open','closed']:
  name='blender-parts-manifest'+('' if label=='open' else '-'+label)+'.json'
  data=json.loads((OUT/name).read_text())
  assert data['glb_sha256']==hi.sha(OUT/data['glb_path'])
  data['electrical_placement_frozen']=False
  led_maps={v:{x['ref']:int(x['dot_index']) for x in csv.DictReader((hi.INP/(v+'-led-placement-reference.csv')).open())} for v in ['upper','lower']}
  for part in data['parts']:
   if 'LED_index' in part:
    ref=part['id'].split('_LED_',1)[1];variant='upper' if part['finger'] in ['UR','UL'] else 'lower';part['LED_index']=led_maps[variant][ref]
  data['electrical_snapshot']=dict(path='input-snapshot.json',sha256=hi.sha(OUT/'input-snapshot.json'),placement_maps={k:v['sha256'] for k,v in snapshot['files'].items() if 'placement-map' in k})
  data['geometry_baked_q_deg_by_finger']={r['id']:r['range_deg'][1] if label=='closed' else 0 for r in data['finger_joints']}
  data['GLB_import_notes']='Keep node names. Meshes are already baked at the stated per-finger q; any new rotor animation must use delta(q - baked_q), NOT add the absolute q again. Use pivot and closing axis from finger_joints. P16 needs recomputation from both endpoints, not a rigid finger child. Same PCB variant is used on each left/right pair without reflection.'
  hi.dump(name,data)
 report=json.loads((OUT/'export-mass.json').read_text());report['sources_sha256'][str(Path(__file__).relative_to(ROOT))]=hi.sha(Path(__file__));report['sources_sha256'][str((OUT/'input-snapshot.json').relative_to(ROOT))]=hi.sha(OUT/'input-snapshot.json');hi.dump('export-mass.json',report)

def main():
 hi.snapshot();f,roots,rmeta,base,fixed,fmeta,audits=hi.nominal();report=dict(revision='HEAD-INTEGRATED03',manufacturing_release=False,states={})
 for closed in [False,True]:
  name='closed' if closed else 'open';rows=rows_at(f,roots,rmeta,fixed,fmeta,closed);qa=exportSTEP(rows,name);m=mass(rows);report['states'][name]=dict(STEP=qa,mass=m);print(name,qa['parts'],m['modeled_mass_g'],m['COM_proxy_world_mm'],flush=True)
  with (OUT/('mass-ledger-'+name+'.csv')).open('w',newline='') as fp:
   w=csv.writer(fp);w.writerow(['part','mass_g','COM_head_x_mm','COM_head_y_mm','COM_head_z_mm','COM_world_x_mm','COM_world_y_mm','COM_world_z_mm','method'])
   for r in m['ledger']:w.writerow([r['part'],r['mass_g'],*r['center_head_mm'],*r['center_world_mm'],r['method']])
  report.setdefault('blender',{})[name]=exportBlender(rows,f,name,m)
 assert abs(report['states']['open']['mass']['modeled_mass_g']-report['states']['closed']['mass']['modeled_mass_g'])<1e-5
 report['sources_sha256']={str(p.relative_to(ROOT)):hi.sha(p) for p in [Path(__file__),ROOT/'engineering/head_integrated03_study.py',OUT/'input-snapshot.json']};hi.dump('export-mass.json',report)
if __name__=='__main__':
 import sys
 if '--sync-addresses' in sys.argv:sync_address_annotations()
 elif '--metadata-only' not in sys.argv:main()
 refresh_manifest_metadata()
