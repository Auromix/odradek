# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent native saved-data / Gerber / drill audit, not signal qualification."""
import json,hashlib,math,re,zipfile,shutil
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
R=Path(__file__).resolve().parent
final=json.loads((R/'controller/native-readback.json').read_text())
r=final['value']
assert final['ok'] and r['drc']==[] and final['verification']['native_reopened']
for name,expected in final['source_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==expected, 'Stale native readback: '+name
bom=R/'manufacturing/b06-io-control01/B06-IO-CONTROL01-BOM.csv'
assert bom.read_text()==r['bom']
import csv,runpy
rows=list(csv.DictReader(bom.open(encoding='utf-8-sig'),delimiter='\t'))
assert sum(int(row['Quantity']) for row in rows)==26
assert all(row['Manufacturer Part'] for row in rows)
components={c['designator']:c for c in r['components']}
exported=set()
for row in rows:
    refs=row['Designator'].split(',')
    assert len(refs)==int(row['Quantity'])
    for ref in refs:
        assert ref not in exported
        exported.add(ref); c=components[ref]
        assert c['addIntoBom'] and c['manufacturerId']==row['Manufacturer Part'], 'BOM MPN drift '+ref
        assert (c.get('supplierId') or '')==row['Supplier Part'], 'BOM supplier-part drift '+ref
assert exported=={c['designator'] for c in r['components'] if c['addIntoBom']}
placements=list(csv.DictReader((R/'manufacturing/b06-io-control01/B06-IO-CONTROL01-PickPlace.csv').open(),delimiter='\t'))
assert {p['Designator'] for p in placements}==set(components)
for p in placements:
    c=components[p['Designator']]
    assert p['Layer']=='T'
    assert abs(float(p['Ref X'].removesuffix('mm'))-c['x']*.0254)<.002
    assert abs(float(p['Ref Y'].removesuffix('mm'))-c['y']*.0254)<.002
    assert abs((float(p['Rotation'])-c['rotation'])%360)<.0001
runpy.run_path(str(R/'controller/check_native.py'))
expected_lines=len(r['lines']); expected_vias=39
assert len(r['vias'])==39 and len(r['pads'])==121
r['pins']={c['designator']:[p for p in r['attached_pins'] if p['parentComponentPrimitiveId']==c['primitiveId']] for c in r['components']}
def geometries(ls):return sorted((l['net'],l['layer'],*[round(l[k],4) for k in ['startX','startY','endX','endY','lineWidth']]) for l in ls)
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
M=R/'manufacturing/b06-io-control01';z=zipfile.ZipFile(M/'B06-IO-CONTROL01-Gerber.zip');assert z.testzip() is None
assert all(n in z.namelist() for n in ['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2','Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL','Drill_PTH_Through_Via.DRL'])
via_txt=z.read('Drill_PTH_Through_Via.DRL').decode();hits=[(float(a),float(b)) for a,b in re.findall(r'^X(-?[\d.]+)Y(-?[\d.]+)$',via_txt,re.M)]
assert len(hits)==expected_vias and len(set(hits))==expected_vias and 'C0.60000' in via_txt and 'C0.30000' in via_txt
assert sorted(hits)==sorted((round(v['x']*.0254,5),round(v['y']*.0254,5)) for v in r['vias'])
via_tools={k:float(v) for k,v in re.findall(r'^T(\d+)C([\d.]+)$',via_txt,re.M)}
active=None;via_hits=[]
for line in via_txt.splitlines():
    if re.fullmatch(r'T\d+',line):active=line[1:]
    m=re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)',line)
    if m:via_hits.append((float(m[1]),float(m[2]),via_tools[active]))
for v in r['vias']:
    pos=(v['x']*.0254,v['y']*.0254)
    matches=[d for d in via_hits if math.dist(pos,d[:2])<.002]
    assert len(matches)==1 and abs(matches[0][2]-v['holeDiameter']*.0254)<.002, 'Via drill tool drift'
assert (M/'B06-IO-CONTROL01-IPC356.ipc').exists()
# Native component pad DTO hole units differ from raw footprint units in this
# client. Check real Excellon tools, never infer diameter from that DTO.
pth=z.read('Drill_PTH_Through.DRL').decode();tool_sizes={k:float(v) for k,v in re.findall(r'^T(\d+)C([\d.]+)$',pth,re.M)}
active=None;drills=[]
for line in pth.splitlines():
    if re.fullmatch(r'T\d+',line):active=line[1:]
    m=re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)',line)
    if m:drills.append((float(m[1]),float(m[2]),tool_sizes[active]))
for p in r['pins']['U1']:
    target=(p['x']*.0254,p['y']*.0254)
    matches=[d for d in drills if math.dist(target,d[:2])<.002]
    assert len(matches)==1 and abs(matches[0][2]-1.10)<1e-6, 'U1 permanent drill regression'
# Confirm the exported annular lands, independently of inconsistent DTO units.
gtl=z.read('Gerber_TopLayer.GTL').decode();assert '%FSLAX45Y45*%' in gtl
apertures={n:shape for n,shape in re.findall(r'%ADD(\d+)([^*]+)\*%',gtl)}
active=None;flashes={}
for line in gtl.splitlines():
    m=re.fullmatch(r'(?:G54)?D(\d+)\*',line)
    if m:active=m[1]
    m=re.fullmatch(r'G01X(-?\d+)Y(-?\d+)D03\*',line)
    if m:flashes[(int(m[1])/1e5,int(m[2])/1e5)]=apertures[active]
for p in r['pins']['U1']:
    pos=(p['x']*.0254,p['y']*.0254)
    matches=[shape for point,shape in flashes.items() if math.dist(point,pos)<.002]
    assert matches==[('R,1.6X1.6' if p['padNumber']=='1' else 'C,1.6')], 'U1 land regression'
exports=json.loads((M/'export-manifest.json').read_text())
assert exports['native_source_sha256']==final['source_sha256'] and exports['step_valid_solids']>0
for name,h in exports['files'].items():assert hashlib.sha256((M/name).read_bytes()).hexdigest()==h, 'Stale export '+name
assert all(p['metallization'] for p in r['pins']['U1'])
expected={'U1':{'1':'LAMP_VIN','2':'RETURN48','3':'LAMP5V'},'F1':{'1':'LAMP_FUSED48','2':'VIN48'},'D1':{'1':'LAMP_VIN','2':'LAMP_FUSED48'},'C1':{'1':'RETURN48','2':'LAMP_VIN'},'C2':{'1':'RETURN48','2':'LAMP5V'},'R1':{'1':'RETURN48','2':'LAMP5V'},'J7':{'1':'LAMP5V','2':'LAMP_PWM','3':'RETURN48','4':'RETURN48','5':'RETURN48'}}
for d,nets in expected.items():assert {p['padNumber']:p['net'] for p in r['pins'][d]}==nets
assert any(l['net']=='LAMP_PWM' for l in r['lines'])
report={'date':'2026-10-09','native_reopened_DRC':0,'lines':expected_lines,'route_union_matches_plan':True,'vias':expected_vias,'pads':121,'legacy_pads_unchanged':True,'legacy_copper_unchanged':True,'U1_PTH_diameter_mm':1.10,'U1_land_mm':1.60,'local_supply_native_implemented':True,'controller_native_implemented':True,'component_quantity':26,'PWM_implemented':True,'BOM_MPN_and_supplier_match_native':True,'PickPlace_reference_and_rotation_match_native':True,
 'trace_length_mm':data_lengths,'same_via_count_per_signal':data_vias,'pair_trace_skew_mm':skew,
 'stack_native_last_records':stack,'stack_total_with_mask_mm':sum(s['thickness_mm'] for s in stack.values()),
 'gerber_crc_pass':True,'gerber_layers':z.namelist(),'via_drill_matches_native':True,
 'limits':['Length tuning includes uncoupled fanout/meander sections; no controlled impedance or Ethernet category claim','Signal channel needs TDR/traffic test at intended protocol/speed','Power path needs current and thermal tests; no current rating inferred','Connector model and complete clamp assembly not yet released'],
 'release':'PCB fabrication candidate only; base assembly release remains blocked',
 'hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [native,R/'controller/native-readback.json',M/'B06-IO-CONTROL01-Gerber.zip',M/'B06-IO-CONTROL01-IPC356.ipc']}}
(R/'reports/b06-routed-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['native_reopened_DRC','trace_length_mm','pair_trace_skew_mm','stack_total_with_mask_mm','gerber_crc_pass','via_drill_matches_native']},indent=2))
