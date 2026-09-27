#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""HEAD-INTEGRATED03: compose original carrier/root, lamp pocket, keyed pads and EXT24.
Supplier geometry is not redistributed. Electronic boxes remain explicit envelopes.
"""
from pathlib import Path
import argparse,csv,hashlib,itertools,json,math
import numpy as np
import cadquery as cq
import p16_carrier02_study as c2
import p16_carrier02_envelope as env2
c01,p16,st=c2.c01,c2.p16,c2.st
ROOT=c2.ROOT;OUT=ROOT/'engineering/generated/head-integrated-03';INP=OUT/'inputs';FPL=ROOT/'engineering/electronics/final-petal-fpl01';POCKET=ROOT/'engineering/generated/led-petal-pocket';RET=ROOT/'engineering/generated/pad-retention-study';B,C,union=c2.B,c2.C,c2.union
FACE=np.array([0.,55.,804.]);DENSITY={**st.DENSITY,'silicone_DS30':.00108,'PCB_laminate_assumed':.00185,'optical_sheet_assumed_PC':.00120,'insulating_ring_assumed':.00120}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readshape(p):return cq.importers.importStep(str(p)).val()
def dump(name,obj):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(obj,indent=2)+'\n')

def snapshot(refresh=False):
 INP.mkdir(parents=True,exist_ok=True);inputs={}
 paths={'mechanical-interface-candidate.json':FPL/'mechanical-interface-candidate.json','component-envelope-reference.json':ROOT/'docs/engineering/sources/final-petal-board-fit-analysis.json'}
 for v in ['upper','lower']:
  for name in ['mechanical-power-budget.json','footprint-constraints.json','led-placement-reference.csv','bom.csv']:
   paths[v+'-'+name]=FPL/v/name
  paths[v+'-placement-map.json']=FPL/v/'kicad/placement-map.json'
 for name,src in paths.items():
  dst=INP/name
  if refresh or not dst.exists():dst.write_bytes(src.read_bytes())
  inputs[name]=dict(source=str(src.relative_to(ROOT)),snapshot=str(dst.relative_to(ROOT)),sha256=sha(dst),source_current_matches=sha(dst)==sha(src))
 dump('input-snapshot.json',dict(revision='HEAD-INTEGRATED03',files=inputs,status='FPL01 placement snapshot; ordinary back parts may be superseded by final electrical export; not ECAD release.'))
 return inputs

def component_props():
 # Plan widths are the old fit study's max-body/land rectangle plus0.25 each side.
 # Use only its size library; placement comes from FPL01, never the old fit packing.
 old=json.loads((INP/'component-envelope-reference.json').read_text())['boards']['UPPER']['back_components_fit_only']['parts'];sizes={}
 for r in old:
  dim=r['envelope_size_mm'];sizes[r['footprint']]=sorted(dim,reverse=True)
 heights={'TI_RKP0040B':1.,'C0805':1.45,'C0603':.8,'R0603':.55,'NTC0603':.95}
 return sizes,heights

def finger_parts(f,index):
 p,mat=c2.root_parts(f);old=dict(p);meta={n:dict(material=mat[n],representation='original nominal solid',mass_method='volume*density',source='P16-CARRIER-02') for n in p}
 for n,mg in [('tip_SBSM_pin',3.5),('KM1',6.),('MB1',2.)]:meta[n].update(catalog_mass_g=mg,mass_method='catalog')
 for n in ['LED_window_placeholder','contact02_pad_0','contact02_pad_1']:
  p.pop(n);meta.pop(n)
 variant='UPPER' if index<2 else 'LOWER';var=variant.lower();L=f['length_mm'];sign=st.SIGNS[index]
 interface=json.loads((INP/'mechanical-interface-candidate.json').read_text());budget=json.loads((INP/(var+'-mechanical-power-budget.json')).read_text());place=json.loads((INP/(var+'-placement-map.json')).read_text())['components']
 distal=readshape(POCKET/(variant+'-metal.step'));near=old['metal_blade_with_narrow_tongue'].intersect(B(-200,25,-100,100,-20,20));body=near.fuse(distal.intersect(B(25,200,-100,100,-20,20))).clean()
 before=body.Volume();cuts=[]
 for rec in interface['high_capacitor_recesses_candidate']:
  lo,hi=np.array(rec['plan_envelope_xy_mm']);pad=.25
  # An enlarged corner-rounded pocket contains the complete planning rectangle.
  cut=cq.Workplane('XY').box(hi[0]-lo[0]+2*pad,hi[1]-lo[1]+2*pad,4.4).edges('|Z').fillet(.25).translate(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,4.)).val()
  body=body.cut(cut);cuts.append(dict(ref=rec['ref'],pocket_bbox_mm=[x.tolist() for x in st.bb(cut)],floor_z_mm=1.8,component_bottom_z_mm=2.05,nominal_bottom_gap_mm=.25))
 body=body.clean();assert body.isValid() and len(body.Solids())==1
 # Electronic parts are NOT mirrored between left/right boards. Pre-reflect their
 # canonical shapes because st.place applies the mechanical-module reflection.
 def board(s):return s if sign>0 else s.mirror('XZ')
 p['metal_blade_with_narrow_tongue']=board(body);meta['metal_blade_with_narrow_tongue'].update(source='CARRIER02 x<=25 + LED-POCKET01 x>25 + local C1/C2 recesses',electrical_mirroring_compensation=sign<0)
 for suffix,material in [('PCB_outline','PCB_laminate_assumed'),('optical_sheet','optical_sheet_assumed_PC')]+[(f'insulating_ring{j}','insulating_ring_assumed') for j in [1,2,3]]+[(f'SSH_M2_4_{j}','steel') for j in [1,2,3]]:
  key='lamp_'+suffix;s=readshape(POCKET/(variant+'-'+suffix+'.step'));p[key]=board(s);meta[key]=dict(material=material,representation='original nominal solid',mass_method='volume*density',source='LED-POCKET01',electrical_mirroring_compensation=sign<0)
 for side in ['MINUS','PLUS']:
  key='retained_pad_'+side.lower();p[key]=board(readshape(RET/f'ODR-RET-{variant}-PAD-{side}.step').translate((L,0,0)));meta[key]=dict(material='silicone_DS30',representation='original molded pad and through-key candidate',mass_method='volume*density',source='PAD-RETENTION01')
 # Boxes include package/land projection and solder-height allowance; they are
 # honest assembly/clearance envelopes, not supplier BREP or uniform material.
 sizes,heights=component_props();parts_bom=list(csv.DictReader((INP/(var+'-bom.csv')).open()))
 for row in parts_bom:
  ref=row['ref']
  if ref.startswith('D') or ref=='J1':continue
  pos=place[ref];x,y=pos['x_mm'],pos['source_y_mm'];a=pos['projection_rotation_deg'];foot=row['footprint'];dx,dy=sizes[foot];height=heights[foot]+.10
  s=B(-dx/2,dx/2,-dy/2,dy/2,3.6-height,3.6).rotate((0,0,0),(0,0,1),a).translate((x,y,0));key='PCBA_'+ref
  p[key]=board(s);meta[key]=dict(material='electronic_mass_TBD',representation='body/land envelope +0.25 plan margin and0.10 assumed solder height',mass_method='unknown; no density applied to envelope',mpn=row['manufacturer_part_number'],source='FPL01 placement snapshot',electrical_mirroring_compensation=sign<0,position_xy_mm=[x,y],rotation_deg=a)
 leds=list(csv.DictReader((INP/(var+'-led-placement-reference.csv')).open()))
 for r in leds:
  x,y=float(r['x_mm']),float(r['y_mm']);key='LED_'+r['ref'];s=B(x-1.2,x+1.2,y-.45,y+.45,4.4,5.3);p[key]=board(s);meta[key]=dict(material='electronic_mass_TBD',representation='max land/body assembly envelope incl0.10 solder allowance',mass_method='unknown; no density applied',mpn='150060YS75000',source='FPL01 exact LED centers',LED_index=int(r['dot_index']),electrical_mirroring_compensation=sign<0)
 lo,hi=np.array(interface['mated_reference_xyz_bounds_mm']);header_x=interface['footprint_origin_mechanical_xyz_mm'][0]+interface['header_body_uv_bounds_mm'][0][1]
 for name,x0,x1 in [('JST_header_reference',header_x,hi[0]),('JST_plug_reference',lo[0],header_x)]:
  p[name]=board(B(x0,x1,lo[1],hi[1],lo[2],hi[2]));meta[name]=dict(material='electronic_mass_TBD',representation='catalog mated reference rectangular split, NOT controlled supplier CAD',mass_method='unknown; no density applied',source='FPL01 mechanical interface',electrical_mirroring_compensation=sign<0)
 # Audits use PCB-local (unmirrored) geometry and report physical intended thread contact separately.
 gate=B(-200,25-1e-5,-100,100,-30,30);newnear=body.intersect(gate);oldnear=old['metal_blade_with_narrow_tongue'].intersect(gate)
 neardelta=newnear.Volume()+oldnear.Volume()-2*newnear.intersect(oldnear).Volume();assert abs(neardelta)<1e-5
 actualPCB=readshape(POCKET/(variant+'-PCB_outline.step'));poly=cq.Workplane('XY').polyline(budget['board_outline_reference_mm']).close().extrude(.8).translate((0,0,3.6)).val()
 for x,y in budget['mounts_xy_mm']:poly=poly.cut(C(1.2,1.,(x,y,3.5),(0,0,1)))
 pcbdelta=actualPCB.Volume()+poly.Volume()-2*actualPCB.intersect(poly).Volume();assert abs(pcbdelta)<1e-4
 return p,meta,dict(finger=f['id'],variant=variant,part_count=len(p),near_x_less_than25_symmetric_difference_mm3=neardelta,PCB_outline_vs_FPL01_budget_symmetric_difference_mm3=pcbdelta,metal_volume_mm3=body.Volume(),capacitor_recess_removed_volume_mm3=before-body.Volume(),capacitor_recesses=cuts,LED_count=len(leds),back_components=len([n for n in p if n.startswith('PCBA_')]),PCB_transform='at q0: x=e_r along petal, y=e_t=(-sin(phi),cos(phi),0), LED side+z; identical same-variant PCB reused left/right, NOT mirrored',root_transform='carrier02 mechanical module mirror retained; electronic parts pre-compensate that reflection')

def fixed_parts():
 f,rr,base,fixed,mods,om=c01.nominal();out={};meta={}
 for n,s in fixed.items():
  if n=='J7_existing_adapter':s=s.translate((0,0,-24))
  if n.startswith('J7_to_carrier_M4x16_'):
   i=int(n.rsplit('_',1)[1]);x,y=[(30,0),(0,30),(-30,0),(0,-30)][i];n=n.replace('M4x16','M4x40');s=C(2,40,(x,y,-161.2),(0,0,1)).fuse(C(3.61,4,(x,y,-121.2),(0,0,1)))
  material=om.get(n,'aluminum' if n in ['main_carrier','J7_existing_adapter'] or n.endswith(('base_bracket','bearing_outer_cap')) else 'steel');mg=None;method='volume*density';rep='original nominal solid'
  if 'keepout' in n or 'reservation' in n:material='space_reservation';method='excluded reservation';rep='original conservative envelope'
  if n.endswith(('bearing_A','bearing_B')):mg=36.;method='SKF catalog';rep='bearing ring envelope'
  if n.endswith('base_SBSM_pin'):mg=4.;method='NBK catalog'
  if n.startswith('J7_to_carrier_M4x40_'):mg=4.7;method='Accu catalog; max head envelope'
  if n.endswith('physical_keepout'):mg=36.;method='Stereolabs catalog; envelope centroid proxy';material='catalog_camera'
  out[n]=s;meta[n]=dict(material=material,representation=rep,mass_method=method,source='CARRIER01 unchanged fixed hardware / EXT24 placement')
  if mg is not None:meta[n]['catalog_mass_g']=mg
 ext=readshape(ROOT/'engineering/generated/wrist-extension-01/ODR-J7-EXT24.step').translate((0,0,-154));out['J7_extension24']=ext;meta['J7_extension24']=dict(material='aluminum',representation='original nominal solid',mass_method='volume*density',source='WRIST-EXTENSION01')
 return f,base,out,meta

def nominal():
 f,base,fixed,fmeta=fixed_parts();roots=[];rmeta=[];audits=[]
 for i,ff in enumerate(f):
  p,m,a=finger_parts(ff,i);roots.append(p);rmeta.append(m);audits.append(a)
 return f,roots,rmeta,base,fixed,fmeta,audits

def intersection(a,b):
 if st.gap_bounds(st.bb(a),st.bb(b))>1e-6:return 0.
 return sum(x.intersect(y).Volume() for x in a.Solids() for y in b.Solids())

def own_interfaces(f,roots):
 rows=[]
 for i in range(4):
  ff=f[i];p=roots[i];hits=[];count=0;intended=[];n=list(p)
  for a,b in itertools.combinations(n,2):
   if st.gap_bounds(st.bb(p[a]),st.bb(p[b]))>1e-6:continue
   count+=1;v=intersection(p[a],p[b])
   if v<1e-5:continue
   screw=(a.startswith('lamp_SSH_') and b=='metal_blade_with_narrow_tongue') or (b.startswith('lamp_SSH_') and a=='metal_blade_with_narrow_tongue')
   row=dict(a=a,b=b,positive_intersection_mm3=v)
   (intended if screw else hits).append(row)
  gaps={name:float(p[name].distance(p['metal_blade_with_narrow_tongue'])) for name in ['PCBA_C1','PCBA_C2','JST_header_reference','JST_plug_reference']}
  rows.append(dict(finger=ff['id'],boolean_tests=count,unintended_intersections=hits,intended_M2_minor_pilot_thread_envelope_intersections=intended,key_component_to_metal_gap_mm=gaps,nominal_no_unintended_intersections=not hits))
 return rows

def motion(f,roots,base,fixed):
 # Publish explicit containment evidence before using a conservative legacy envelope.
 containment=[];bounded=[]
 for i,ff in enumerate(f):
  old,_=c2.root_parts(ff);old_distal=union([old[n] for n in ['metal_blade_with_narrow_tongue','LED_window_placeholder','contact02_pad_0','contact02_pad_1']]);outside=[]
  for name,s in roots[i].items():
   if name in old and name!='metal_blade_with_narrow_tongue':continue
   if name.startswith('JST_'):continue
   # A Boolean check against the exact old distal union, not a box-only test.
   v=s.Volume()-s.intersect(old_distal).Volume();outside.append(dict(part=name,outside_carrier02_distal_union_mm3=v));assert abs(v)<1e-4,(ff['id'],name,v)
  enclosure={**old,**{n:s for n,s in roots[i].items() if n.startswith('JST_')}};bounded.append((enclosure,{}));containment.append(dict(finger=ff['id'],checks=outside,all_contained=True))
 dump('motion-containment.json',containment)
 result=c01.run_motion(f,bounded,base,fixed)
 result.pop('unchanged_interfaces',None)
 beta=26*(123+26)/p16.kin(0)[2]**2;V=26+160*beta;gh=union([s for n,s in roots[0].items() if n.startswith('JST_')]);rot=lambda q:gh.rotate((0,0,0),(0,1,0),-q)
 result['GH_vs_own_P16']=p16.certificate(lambda q:st.comp(p16.envelopes(q).values()),rot,V+p16.radius(gh),122.,step=2)
 result['proof_scope']='Actual integrated distal solids contained in carrier02 rigid distal envelope, except symmetric GH mated reference boxes added explicitly. Identical PCB is not mirrored. All c01 global motion tests recomputed on this superset with actual EXT24 placement. Supplier reference boxes do not cover cable/mating access, tolerances or distortion.'
 result['inherited_unchanged_P16_crank_interface']=dict(source='engineering/generated/p16-carrier-02/motion.json',sha256=sha(c2.OUT/'motion.json'))
 # Recompute each integrated moving-part height over its own angle domain.
 zrows=[]
 for i,ff in enumerate(f):
  each=[dict(part=n,**env2.extrema(s,0,ff['closure_study_deg'],ff['root_z_mm'])) for n,s in roots[i].items()]
  zrows.append(dict(finger=ff['id'],q_range_deg=[0,ff['closure_study_deg']],minimum_world_z_bound_mm=804+min(r['z_lower_bound_mm'] for r in each),parts=each))
 fixed_min=min(s.BoundingBox().zmin+804 for n,s in fixed.items() if n!='J7_existing_adapter' and not n.startswith('J7_to_carrier_'))
 result['wrist_extension_inheritance']=dict(integrated_rotor_bounds=zrows,minimum_fixed_world_z_mm=fixed_min,minimum_rotor_world_z_mm=min(x['minimum_world_z_bound_mm'] for x in zrows),unchanged_P16_bodies='P16-PACK01 geometry/kinematics unchanged; native-contained envelopes and speed bound inherited.',extension_evidence_sha256=sha(ROOT/'engineering/generated/wrist-extension-01/study.json'),scope='Retain parent EXT24 q5/q6/q7 +/-90 head-to-wrist support-plane certificate only after these integrated head bounds. Fixed wrist bodies and low adapter/long bolts identical to EXT24. Does not qualify entire arm, LINK67 self-motion, cable/armor or q6 outer90..100 bands.')
 assert fixed_min>=650-1e-6 and min(x['minimum_world_z_bound_mm'] for x in zrows)>650
 dump('motion.json',result);return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--refresh-inputs',action='store_true');ap.add_argument('--motion',action='store_true');args=ap.parse_args();snapshot(args.refresh_inputs)
 assert sha(ROOT/'engineering/parameters/r4-layout.json')==st.EXPECTED
 f,roots,rmeta,base,fixed,fmeta,audits=nominal();report=dict(revision='HEAD-INTEGRATED03',manufacturing_release=False,coordinate_contract=dict(face_world_mm=FACE.tolist(),J7_output_world_mm=[0,55,640],J7_output_head_z_mm=-164,original_adapter_main_plate_world_z_range_mm=[640,650],original_adapter_complete_nominal_world_z_range_mm=[637.5,650],extension_head_z_range_mm=[-154,-130],carrier_original_head_coordinates_retained=True),finger_interfaces=audits,own_interfaces=own_interfaces(f,roots),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'engineering/p16_carrier02_study.py',ROOT/'engineering/generated/p16-carrier-02/study.json',ROOT/'engineering/generated/wrist-extension-01/study.json',POCKET/'study.json',RET/'verification.json']})
 assert all(x['nominal_no_unintended_intersections'] for x in report['own_interfaces'])
 dump('interfaces.json',report)
 for i in [0,2]:
  for name in ['metal_blade_with_narrow_tongue','lamp_PCB_outline','retained_pad_minus','retained_pad_plus']:
   cq.exporters.export(roots[i][name],str(OUT/(f[i]['id']+'_'+name+'.step')))
 print(json.dumps(dict(audits=audits,own=report['own_interfaces']),indent=2),flush=True)
 if args.motion:motion(f,roots,base,fixed)
if __name__=='__main__':main()
