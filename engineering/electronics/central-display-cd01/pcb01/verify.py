#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Readback assertions; native reports are mandatory, no DRC exclusions allowed."""
from pathlib import Path
import json,csv,hashlib,xml.etree.ElementTree as ET,math
D=Path(__file__).resolve().parent;P=D.parent;K=D/'kicad';R=D.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
n=json.loads((D/'netlist.json').read_text());base=json.loads((P/'netlist.json').read_text());assert n['pins']==base['pins'];assert (D/'pixel-map.csv').read_bytes()==(P/'pixel-map.csv').read_bytes()
expected={(p['ref'],p['pin']):p['net'] for p in n['pins'] if p['net']};actual={}
x=ET.parse(K/'checks/central.xml')
for net in x.findall('.//nets/net'):
 for pin in net.findall('node'):actual[pin.attrib['ref'],pin.attrib['pin']]=net.attrib['name']
diff=[{'ref':k[0],'pin':k[1],'expected':v,'actual':actual.get(k)} for k,v in expected.items() if actual.get(k)!=v]
extra=[{'ref':k[0],'pin':k[1],'net':v} for k,v in actual.items() if k not in expected and not k[0].startswith('#') and not v.startswith('unconnected-')]
assert not diff and not extra,(diff,extra)
mp=list(csv.DictReader((D/'pixel-map.csv').open()));raw={int(r['index']):r for r in csv.DictReader((R/'engineering/generated/central-display-mount01/led-centres.csv').open())}
for r in mp:
 a=raw[int(r['index'])];assert float(r['x_mm'])==float(a['x_mm']) and float(r['y_mm'])==float(a['y_mm'])
assert len(mp)==285
fp={c.attrib['ref']:c.findtext('footprint') for c in x.findall('.//components/comp')};assert len(fp)==318 and all(v.startswith('CD:') for v in fp.values())
erc=json.loads((K/'checks/erc.json').read_text());errs=[v for s in erc['sheets'] for v in s['violations']];assert not errs,errs
drc=json.loads((K/'checks/drc.json').read_text());counts={k:len(drc[k]) for k in ['violations','unconnected_items','schematic_parity']};assert all(v==0 for v in counts.values()),counts;assert not drc.get('ignored_checks'),drc.get('ignored_checks')
prj=json.loads((K/'central.kicad_pro').read_text());ex=prj.get('board',{}).get('design_settings',{}).get('drc_exclusions',[]);assert not ex,ex
assert not prj.get('erc',{}).get('erc_exclusions',[])
a=json.loads((K/'checks/native-audit.json').read_text());assert a['board_sha256']==sha(K/'central.kicad_pcb');assert not a['placement_and_net_issues'];assert a['continuous_ground_reference_geometry'];assert a['components']==318 and a['pin_count']==726
assert not any(any(o['ref'].startswith('D') for o in v['overlaps']) for v in a['via_solder_land_overlaps']),'Unplanned LED via-in-pad'
back=[p for p in a['mechanical_envelopes'] if p['side']=='B'];over=[]
for i,p in enumerate(back):
 for q in back[i+1:]:
  dx=min(p['max_xy_mm'][0],q['max_xy_mm'][0])-max(p['min_xy_mm'][0],q['min_xy_mm'][0]);dy=min(p['max_xy_mm'][1],q['max_xy_mm'][1])-max(p['min_xy_mm'][1],q['min_xy_mm'][1])
  if dx>1e-6 and dy>1e-6:over.append({'refs':[p['ref'],q['ref']],'overlap_mm':[dx,dy]})
assert not over,over
for p in back:
 assert p['head_z_mm'][0]>=-10 and p['max_radius_mm']<=28
 for xc in [-10,10]:
  assert max(p['min_xy_mm'][0]-(xc+2),(xc-2)-p['max_xy_mm'][0],p['min_xy_mm'][1]-17,13-p['max_xy_mm'][1])>=0,(p['ref'],'thermal patch')
mc=json.loads((D/'mechanical-interface.json').read_text())
assert mc['board_sha256']==sha(K/'central.kicad_pcb')
assert mc['package_dimensions_sha256']==sha(D/'package-body-dimensions.json')
assert len(mc['components_back'])==33 and not mc['mcad_body_bbox_overlaps']
for c in mc['components_back']:
 body=c['mcad_material_envelope'];plan=c['planning_envelope']
 assert body['xy_assembly_allowance_mm']==0 and body['solder_height_translation_h_mm']==.1
 assert not body['includes_PCB_copper_lands'] and not plan['material_solid']
 assert (c['max_body'] is None)==(c['ref']=='J1')
 for i in range(3):
  assert body['head_min_mm'][i]>=plan['head_min_mm'][i]-1e-6 and body['head_max_mm'][i]<=plan['head_max_mm'][i]+1e-6,c['ref']
for name,digest in json.loads((D/'baseline-inputs.json').read_text())['sha256'].items():assert sha(P/name)==digest,('frozen parent changed',name)
report={'revision':'CD-PCB01','maturity':'native routed manufacturing candidate; not fabrication release','components':318,'LEDs':285,'pins':726,'connected_pins_compared':len(expected),'assigned_footprints':len(fp),'exact_pixel_XY':True,'parent_pin_net_mapping_unchanged':True,'native_counts':counts,'ERC_violations':0,'custom_ERC_exclusions':[],'custom_DRC_exclusions':[],'DRC_ignored_checks':drc.get('ignored_checks',[]),'default_ERC_ignored_checks':erc.get('ignored_checks'),'backside_envelope_overlap_count':0,'backside_body_bbox_overlap_count':0,'package_only_body_records':32,'catalogue_mated_reference_records':1,'continuous_GND_geometry':True,'hardware_tested':False,'manufacturing_approved':False,'board_sha256':sha(K/'central.kicad_pcb'),'input_sha256':json.loads((D/'baseline-inputs.json').read_text())['sha256'],'artifact_sha256':{str(p.relative_to(D)):sha(p) for p in sorted(D.rglob('*')) if p.is_file() and p.suffix in ['.py','.json','.csv','.kicad_mod','.kicad_sym','.kicad_pcb','.kicad_sch','.kicad_pro','.xml','.svg','.png'] and p.name not in ['verification.json','cli-report.json'] and '__pycache__' not in p.parts}}
(K/'checks/verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if 'sha256' not in k},indent=2))
