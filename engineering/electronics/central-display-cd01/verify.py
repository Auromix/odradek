#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Independent native XML/circuit/map/package coordinate assertions."""
from pathlib import Path
import json,csv,hashlib,math,xml.etree.ElementTree as ET
D=Path(__file__).resolve().parent;ROOT=D.parents[2];K=D/'kicad';n=json.loads((D/'netlist.json').read_text());pins={(p['ref'],p['pin']):p['net'] for p in n['pins']};expected={k:v for k,v in pins.items() if v};actual={}
xml=ET.parse(K/'central.net.xml')
for net in xml.findall('.//nets/net'):
 for node in net.findall('node'):actual[(node.attrib['ref'],node.attrib['pin'])]=net.attrib['name']
diff=[dict(pin=list(k),expected=v,actual=actual.get(k)) for k,v in expected.items() if actual.get(k)!=v];unexpected=[dict(pin=list(k),net=v) for k,v in actual.items() if k not in expected and not k[0].startswith('#') and not v.startswith('unconnected-')]
assert not diff and not unexpected,(diff,unexpected)
# Package pins independently enumerated from TI Table6-1, not reused generator lookup.
for u,g,cs in [('U1','A','LED_CS4'),('U2','B','LED_CS5')]:
 for i in range(18):assert pins[(u,str(i+1 if i<9 else i+13))]==(f'{g}_CS{i}' if i<13 else None)
 for i in range(11):assert pins[u,str(i+10 if i<6 else i+11)]==f'{g}_SW{i}'
 for pin,net in [('16','LED_POWER4'),('31','GND'),('32',g+'_VCAP'),('33',g+'_IFS'),('34','LED_VSYNC'),('35','LED_SCK'),('36','LED_MOSI'),('37',g+'_MISO_IC'),('38',cs),('39','LED_VIO'),('40','3V3_LOGIC'),('41','GND')]:assert pins[u,pin]==net
 # Independent checks of VCAP separation and SPI strap presence.
 assert any({p['net'] for p in n['pins'] if p['ref']==c['ref']}=={g+'_VCAP','GND'} and c['value'].startswith('1uF') for c in n['components'] if c['ref'].startswith('C'))
 assert any({p['net'] for p in n['pins'] if p['ref']==c['ref']}=={g+'_IFS','LED_VIO'} and c['value'].startswith('4.7k') for c in n['components'] if c['ref'].startswith('R'))
head={p['pin']:p['net'] for p in csv.DictReader((D.parent/'head-ctrl02/pin-net.csv').open()) if p['ref']=='J15'}
assert {p['pin']:p['net'] for p in n['pins'] if p['ref']=='J1'}==head
mp=list(csv.DictReader((D/'pixel-map.csv').open()));raw={int(r['index']):r for r in csv.DictReader((ROOT/'engineering/generated/central-display-mount01/led-centres.csv').open())};assert len(mp)==285 and len({p['index'] for p in mp})==285
for p in mp:
 o=raw[int(p['index'])];assert float(p['x_mm'])==float(o['x_mm']) and float(p['y_mm'])==float(o['y_mm'])
 assert pins[p['ref'],'1']==f'{p["driver"]}_CS{p["cs"]}' and pins[p['ref'],'2']==f'{p["driver"]}_SW{p["sw"]}'
 assert int(p['dot_index'])==int(p['sw'])*18+int(p['cs'])
for g in 'AB':
 r=json.loads((D/f'register-plan-{g}.json').read_text());ops={p['register']:p['bytes'] for p in r['operations']};pts=[p for p in mp if p['driver']==g];inds={int(p['dot_index']) for p in pts};assert len(inds)==len(pts)
 assert ops['0x001']==[0x5c] and ops['0x004']==[0x51] and not any(ops['0x200'])
 for i in range(198):
  en=(ops['0x043'][3*(i//18)+(i%18)//8]>>((i%18)%8))&1;assert bool(en)==(i in inds) and ops['0x100'][i]==(255 if en else 0)
m=json.loads((D/'mechanical-packing.json').read_text());assert len(m['components'])==33 and not m['backpacking']['XY_overlaps'] and m['backpacking']['max_corner_radius_mm']<28
for a in m['components']:
 assert a['envelope_head_min_mm'][2]>=-10 and a['envelope_head_max_mm'][2]<=-3
 for t in m['thermal_bridge_candidate_regions']:
  x,y=t['center_xy_mm'];gaps=[max(a['envelope_head_min_mm'][0]-(x+2),(x-2)-a['envelope_head_max_mm'][0]),max(a['envelope_head_min_mm'][1]-(y+2),(y-2)-a['envelope_head_max_mm'][1])];assert max(gaps)>=0,(a,t)
for p in m['connector']['pads']:
 u,v=p['center_uv_mm'];h=next(x for x in m['connector']['pad_centers_head_mm'] if x['pad']==p['pad']);assert h['center_head_mm']==[-u,-14+v,-3]
assert m['connector']['CD01_parent_layout_input']['pin1_land_center_head_mm']==[6.875,-12.15,-3]
erc=json.loads((K/'checks/erc.json').read_text());viol=[x for s in erc['sheets'] for x in s['violations']];assert not viol
src=json.loads((D/'sources.json').read_text())
for name,h in src['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
# This report freezes the schematic baseline.  Later PCB revisions own their
# own provenance and must not be silently swept into this report's hash scope.
candidates=[*D.glob('*'),*(D/'kicad').rglob('*')]
files=[p for p in candidates if p.is_file() and p.suffix in ['.py','.csv','.json','.c','.h','.kicad_sch','.kicad_sym','.kicad_pro','.xml','.svg'] and p.name not in ['verification.json','cli-report.json']]
report=dict(revision='CD-EC01',maturity='schematic and component packing only',component_count=len(n['components']),pin_count=len(n['pins']),connected_pins_compared=len(expected),differences=diff,unexpected_native_nets=unexpected,erc_violations=0,custom_erc_exclusions=[],native_default_ignored_checks=erc.get('ignored_checks'),exact_XY_preservation=True,LP5860_pin_assertions='pass',GH12_HEADCTRL02_and_mirror_transform='pass',backpacking='33 AABB envelopes, all pairs non-overlapping, corners insideR28 andZ-10..-3',firmware_mock=json.loads((D/'firmware-check.json').read_text())['result'],PCB_created=False,DRC_run=False,assigned_footprints=0,route_feasibility_established=False,hardware_tests=False,sha256={str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)})
(K/'checks/verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
