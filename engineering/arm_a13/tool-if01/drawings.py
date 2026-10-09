# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import importlib.util,json,hashlib
HERE=Path(__file__).resolve().parent;OUT=HERE/'build'
spec=importlib.util.spec_from_file_location('fit_drawing',HERE.parent/'j7-fit01/drawings.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
d.OUT=OUT;d.DRAW=OUT/'drawings'
d.FEATURES={
 '107':['Datum A: body contact plane X=65.7; datum B: axis +X',
 'Inherited D60 x 8 body; rear journal pilot is unchanged',
 'New tool pilot D18.00 x 2.00; front tip X=67.7',
 'Unique pin at (Y,Z)=(24,0): D3.10 blind bore, depth 3.00',
 'Pin bore starts X=62.7, opens at body contact face',
 'Six original output M3 stations and three M4/PCD45 nut stations unchanged',
 'D3x6 steel pin nominal front end X=68.7; prototype retention pending'],
 '201':['Datum A: rear mating face X=65.7; datum B: axis +X',
 'D60 main body x 11.00; front X=76.7',
 'Rear locating bore D18.30 x 2.20; test D18.2/18.3/18.4 coupons',
 'Unique pin bore D3.30 x 4.00 at (Y,Z)=(24,0)',
 '3 x D4.50 through, PCD45, first angle30 deg (0=+Y)',
 'Tray mounts: 2 x D3.50 axial at Y=+/-14, Z=24',
 'Tray captive M3 nut pockets: circumscribed hex D6.80, X=70.2..72.7',
 'Nut insertion chutes open toward +Z; pocket is a plastic trial fit',
 'Separate tool fasteners from the six RS00 output bolts'],
 '202':['Datum: J7 rotor; candidate print on bottom Z=27',
 'Floor X=76.7..144.7; Y=-42..42; thickness2.50',
 'Sidewalls inside Y=+/-37.5, outside +/-42; top Z=55.5',
 'Rear mounting plate X=76.7..80.7; 2 x D3.50 at Y=+/-14,Z=24',
 'Washer relief R3.70 x 0.70 at X=80.6 on rear mounts',
 'Panel grooves X=96.55..99.85; half-width39.15; insert from +Z',
 '4 x lid D3.50 at X=86.7/133.7, Y=+/-40; nut pockets from below',
 'Strain relief: 2x8 tie windows at X=137.7/141.7 per channel',
 'Channel centres Y=-28.5,-9.5,9.5,26.5; cable saddle shape pending'],
 '203':['Datum: J7 rotor; X=96.7..99.7, thickness3.00',
 'Outer Y=+/-39; Z=29.8..55.2',
 'PWR: centre(Y,Z)=(-28.5,41), opening14x16',
 'CTRL: centre(Y,Z)=(-9.5,40.5), opening18x18',
 'CAM_UP: centre(Y,Z)=(9.5,41), opening14x16',
 'CAM_DOWN: centre(Y,Z)=(26.5,41), opening14x16',
 'Openings are design allocations, NOT final connector mounting cutouts',
 'Slide from +Z after removing lid; remake panel for exact chosen PNs'],
 '204':['Datum: J7 rotor; roof Z=55.5..58.0, thickness2.50',
 'Faceted outline X=76.7..144.7, Y=+/-44; edge-corner offsets per STEP',
 '4 x D3.50 through: X=86.7/133.7, Y=+/-40',
 'M3x10 + 0.5 washer; four captive M3 nuts in tray side bosses',
 'Remove toward +Z for latch access; top clearance still required in head cover']}
d.main()
# Replace the inherited backend-only stack diagram with the current port map.
(d.DRAW/'J7-axial-stack.svg').unlink()
rows=json.loads((OUT/'interface.json').read_text())['ports']
shapes='';labels=''
for p in rows:
 w,h=p['opening'];x=540+p['y']*8;y=390-p['z']*5
 shapes+=f'<rect x="{x-w*4}" y="{y-h*2.5}" width="{w*8}" height="{h*5}" fill="#dfba72" stroke="#243d4a"/>'
 labels+=f'<text x="{x}" y="{y+5}" text-anchor="middle">{p["id"]}</text>'
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="600">
<rect width="1080" height="600" fill="#f7f8f8"/><style>text{{font-family:Arial,sans-serif;font-size:18px;fill:#243d4a}}</style>
<text x="35" y="45" style="font-size:28px;font-weight:bold">Tool interface / four independent channels</text>
<text x="35" y="80">End-view schematic, Y horizontal / Z up. Connector mounting PNs are not frozen.</text>
<rect x="228" y="114" width="624" height="127" fill="none" stroke="#243d4a"/>{shapes}{labels}
<text x="35" y="305">Body mating plane X65.7; tool receiver front X76.7. D18 pilot + off-centre D3 pin.</text>
<text x="35" y="345">PWR: supply only. CTRL: CAN or separate RJ45/EtherCAT insert; different electrical contract.</text>
<text x="35" y="385">CAM_UP and CAM_DOWN: independent coax channels. PoC is conditional on actual camera chain.</text>
<text x="35" y="425">Unplug budget +X 25 mm. Remove lid +Z; panel slides out +Z. Each channel has tie slots.</text>
<text x="35" y="465">Amber apertures/blocks are space allocations, not qualified vendor mounts or pinouts.</text>
<text x="35" y="505">No hollow RS00, live power, hotplug or dynamic bend qualification is assumed.</text>
<text x="35" y="550">Exact current part features and clocking are in STEP and interface.json. Supported trial only.</text></svg>'''
p=d.DRAW/'port-map.svg';p.write_text(svg)
r=json.loads((d.DRAW/'sources.json').read_text());r.pop('stack_svg_sha256');r['port_map_svg_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
for row in r['parts']:
 sheet=d.DRAW/(row['id']+'.svg')
 text=sheet.read_text().replace(' / FIT01',' / TOOL-IF01')
 sheet.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')
 row['svg_sha256']=hashlib.sha256(sheet.read_bytes()).hexdigest()
(d.DRAW/'sources.json').write_text(json.dumps(r,indent=2)+'\n')
