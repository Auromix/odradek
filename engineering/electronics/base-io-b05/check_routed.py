# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent native saved-data / Gerber / drill audit, not signal qualification."""
import json,hashlib,math,re,zipfile,shutil
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
R=Path(__file__).resolve().parent
r=json.loads((R/'reports/b06-data-reopened.json').read_text())['value']
assert r['drc']==[]
assert len(r['vias'])==16 and len(r['lines'])==217 and len(r['pads'])==48
old=json.loads((R/'reports/b06-power-reopened.json').read_text())['value']
assert r['pads']==old['pads']
power=[l for l in r['lines'] if l['net'] in ['VIN48','RETURN48']]
def geometries(ls):return sorted((l['net'],l['layer'],*[round(l[k],4) for k in ['startX','startY','endX','endY','lineWidth']]) for l in ls)
assert geometries(power)==geometries(old['lines'])
def xy(x,y):return x*.0254,-y*.0254
regions={};data_lengths={};data_vias={}
for n in range(1,9):
 net=f'ETH_{n}';ls=[l for l in r['lines'] if l['net']==net];vs=[v for v in r['vias'] if v['net']==net];ps=[p for p in r['pads'] if p['net']==net]
 assert len(vs)==2 and len(ps)==2
 data_lengths[net]=sum(math.dist(xy(l['startX'],l['startY']),xy(l['endX'],l['endY'])) for l in ls);data_vias[net]=2
 # A two-layer copper graph. Through-hole copper joins both layers.
 polys={}
 for layer in [1,2]:
  shapes=[LineString([xy(l['startX'],l['startY']),xy(l['endX'],l['endY'])]).buffer(l['lineWidth']*.0254/2) for l in ls if l['layer']==layer]
  shapes += [Point(xy(p['x'],p['y'])).buffer(min(p['pad'][1:])*.0254/2) for p in ps]
  shapes += [Point(xy(v['x'],v['y'])).buffer(v['diameter']*.0254/2) for v in vs]
  polys[layer]=unary_union(shapes)
 regions[net]=polys
 # Union across projected layers is only a conservative continuity aid;
 # native connectivity DRC is the authoritative layer-aware check.
 assert unary_union(list(polys.values())).geom_type=='Polygon'
skew={f'{a}/{b}':abs(data_lengths[f'ETH_{a}']-data_lengths[f'ETH_{b}']) for a,b in [(1,2),(3,6),(4,5),(7,8)]}
assert max(skew.values())<=.254
for a in range(1,9):
 for b in range(a+1,9):
  for layer in [1,2]:assert regions[f'ETH_{a}'][layer].distance(regions[f'ETH_{b}'][layer])>.126
# Native project is journaled: the last LAYER_PHYS record for each id is current.
native=R/'base-io-b05/pcb/base-rear-interface01.epcb2';phys={}
for line in native.read_text().splitlines():
 try:h,s=line.split('||');h=json.loads(h);s=json.loads(s.rstrip('|'))
 except (ValueError,json.JSONDecodeError):continue
 if h['type']=='LAYER_PHYS':phys[json.loads(h['id'])[1]]=s
stack={i:{**p,'thickness_mm':p['thickness']*.0254} for i,p in phys.items()}
for i,t in {1:.035,15:.0152,16:.0152,2:.035,361:.2104,362:1.065,363:.2104,5:.01524,6:.01524}.items():assert abs(stack[i]['thickness_mm']-t)<.00002
M=R/'manufacturing/b06-io-prototype';z=zipfile.ZipFile(M/'B06-IO-PROTOTYPE-Gerber.zip');assert z.testzip() is None
assert all(n in z.namelist() for n in ['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2','Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL','Drill_PTH_Through_Via.DRL'])
via_txt=z.read('Drill_PTH_Through_Via.DRL').decode();hits=[(float(a),float(b)) for a,b in re.findall(r'^X(-?[\d.]+)Y(-?[\d.]+)$',via_txt,re.M)]
assert len(hits)==16 and len(set(hits))==16 and 'T01C0.60000' in via_txt
assert sorted(hits)==sorted((round(v['x']*.0254,5),round(v['y']*.0254,5)) for v in r['vias'])
ipc=Path('/Users/hermanye/Downloads/B06-IO-PROTOTYPE-IPC356.ipc')
if ipc.exists():shutil.copy2(ipc,M/ipc.name)
assert (M/'B06-IO-PROTOTYPE-IPC356.ipc').exists()
report={'date':'2026-10-09','native_reopened_DRC':0,'lines':217,'vias':16,'pads_unchanged':True,'power_copper_unchanged':True,
 'trace_length_mm':data_lengths,'same_via_count_per_signal':data_vias,'pair_trace_skew_mm':skew,
 'stack_native_last_records':stack,'stack_total_with_mask_mm':sum(s['thickness_mm'] for s in stack.values()),
 'gerber_crc_pass':True,'gerber_layers':z.namelist(),'via_drill_matches_native':True,
 'limits':['Length tuning includes uncoupled fanout/meander sections; no controlled impedance or Ethernet category claim','Signal channel needs TDR/traffic test at intended protocol/speed','Power path needs current and thermal tests; no current rating inferred','Connector model and complete clamp assembly not yet released'],
 'release':'PCB fabrication candidate only; base assembly release remains blocked',
 'hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [native,R/'reports/b06-data-reopened.json',M/'B06-IO-PROTOTYPE-Gerber.zip',M/'B06-IO-PROTOTYPE-IPC356.ipc']}}
(R/'reports/b06-routed-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['native_reopened_DRC','trace_length_mm','pair_trace_skew_mm','stack_total_with_mask_mm','gerber_crc_pass','via_drill_matches_native']},indent=2))
