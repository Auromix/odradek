# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import importlib.util,json,hashlib
import cadquery as cq
HERE=Path(__file__).resolve().parent;OUT=HERE/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('fit_draw',HERE.parent/'j7-fit01/drawings.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
d.OUT=OUT;d.DRAW=OUT/'drawings'
d.FEATURES={
'301':['Datum A: rear core plane X65.7; datum B: axis +X',
'16-facet outer profile circumscribed D88; body X65.7..110',
'Internal pocket D64 from X76.7..106; face opening D54',
'Three lower ribs retained; thin lower shell relief R40 per STEP',
'Outer tool pilot: OD76 / ID54 x2, X110..112',
'Internal rear bore D18.30 x2.20; core index bore D3.30 at Y24,Z0',
'Core screws: 3 x D4.50, PCD45, first angle30deg',
'Tool screws: 4 x D4.50, PCD72, first angle45deg; rear hex nut slots',
'Unique tool key: D3.10 bore X107..112, Y0,Z31; D3x8 steel pin',
'Rear side wire opening: X70..85, Y-46..-24, Z+/-7; not dynamic routing',
'Cover: front Y+/-14,Z33; rear vertical X84,Y+/-10; insert Y+/-29,Z0'],
'302':['Datum: J7 rotor; thin upper shell from X76.7..105.8',
'Cut plane Z20; outer 16-facet D88; nominal inside R41',
'Front axial tabs: X102.7..105.7, holes Y+/-14,Z33',
'Rear vertical D3.50: X84,Y+/-10; washer seat Z40, underside Z38',
'Rear D7.60 counterbores; M3x10 button heads +0.5 washer; nuts Z34..36.5',
'Front M3x10 socket heads +0.5 washer; nut traps X103.2..105.7',
'Lift +Z after four screws removed; first detach tool cup'],
'303':['Datum: J7 rotor; X103..106, thickness3.00',
'D52 disk + mounting ears centred Y+/-29,Z0, R4',
'2 x D3.50 through on the ears; M3x12',
'PWR opening12x14 at Y=-10,Z=11; allocation only',
'CTRL opening16x16 at Y=10,Z=10; actual protocol/PN pending',
'CAM openings11.6x11.6 at Y=+/-9,Z=-12; no qualified HFM hold-down',
'Connector holes are prototype spaces, not vendor panel piercings'],
'304':['Datum A: tool mating plane X110; axis +X',
'Dummy tool rear pocket from X110..133; D54 through',
'Rear annular recess: OD76.30 / ID54, depth2.20',
'4 x D4.50 through, PCD72, first angle45deg',
'Unique key bore D3.30, centre Y0,Z31, X109.9..116.2',
'Four service-head pockets D7.60, X109.9..114.2, per STEP',
'Verification cup only: real four-petal rear cover must provide this pocket'],
'305':['Datum: X133..136; thickness3.00; 16-facet D88 outline',
'Central straight wire exit D42; no dynamic bending inside',
'4 x D4.50 through on PCD72; first angle45deg',
'M4x35 attaches cap, cup and carrier; 0.8 washer',
'Part is a tool-side verification cap, not actual petal-head mounting']}
d.main();(d.DRAW/'J7-axial-stack.svg').unlink()
info=json.loads((d.DRAW/'sources.json').read_text());info.pop('stack_svg_sha256')
for row in info['parts']:
 p=d.DRAW/(row['id']+'.svg');text=p.read_text().replace(' / FIT01',' / TOOL-IF02')
 p.write_text('\n'.join(t.rstrip() for t in text.splitlines())+'\n');row['svg_sha256']=sha(p)
# Exact owned-solid section at Y=-9 mm. Supplier CAD is not published.
clip=cq.Solid.makeBox(300,200,200,cq.Vector(-100,-9,-100));sections=[]
D=json.loads((OUT/'manifest.json').read_text())
for p in D['parts']:
 if p['role']=='fit_coupon':continue
 s=cq.importers.importStep(str(OUT/'step'/(p['id']+'.step'))).val().intersect(clip)
 if s.Solids():sections.extend(s.Solids())
shape=cq.Compound.makeCompound(sections)
svg=cq.exporters.getSVG(shape,dict(width=980,height=440,marginLeft=30,marginTop=30,projectionDir=(0,-1,0),showAxes=False,showHidden=False,strokeColor=(35,55,65),strokeWidth=.6))
svg=svg[svg.index('<svg'):]
page=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="800"><rect width="1080" height="800" fill="#f8f9f8"/>
<style>text{{font-family:Arial,sans-serif;font-size:18px;fill:#233d48}}</style>
<text x="35" y="45" style="font-size:26px;font-weight:bold">TOOL-IF02 / owned CAD section Y=-9 mm</text>
<text x="35" y="80">+X tool direction; mm. Parts only, connector blocks omitted; STEP authoritative.</text>
<g transform="translate(35,100)">{svg}</g>
<text x="35" y="585">X65.7 core joint | X76.7 pocket starts | X103..106 insert | X110 tool joint | X136 dummy cap</text>
<text x="35" y="630">Central aperture D54; annular tool pilot OD76. RS00 is not hollow.</text>
<text x="35" y="675">Side entry is after motor. Cup/cap verify head rear space; actual head and dynamic wires pending.</text>
<text x="35" y="720">Supported, unloaded and unpowered plastic-fit drawing; no metal/load/electrical release.</text></svg>'''
p=d.DRAW/'recessed-section.svg';p.write_text('\n'.join(t.rstrip() for t in page.splitlines())+'\n');info['section_svg_sha256']=sha(p)
(d.DRAW/'sources.json').write_text(json.dumps(info,indent=2)+'\n')
print('DRAWINGS_IF02',len(info['parts'])+1,flush=True)
