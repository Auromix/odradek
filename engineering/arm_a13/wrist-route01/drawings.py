# SPDX-License-Identifier: CC-BY-NC-4.0
"""CAD projection and controlled feature dimensions for replacement carrier."""
from pathlib import Path
import json,hashlib,html
import cadquery as cq
HERE=Path(__file__).parent;OUT=HERE/'build';DRAW=OUT/'drawings';DRAW.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((OUT/'carrier-manifest.json').read_text());step=OUT/'step'/(p['id']+'.step');assert sha(step)==p['step_sha256']
s=cq.importers.importStep(str(step)).val();views=[]
for direction in [(0,0,1),(0,1,0)]:
 svg=cq.exporters.getSVG(s,dict(width=475,height=330,marginLeft=25,marginTop=25,projectionDir=direction,showAxes=False,showHidden=True,strokeColor=(35,55,65),hiddenColor=(160,174,183),strokeWidth=.6));views.append(svg[svg.index('<svg'):])
notes=['J7.fixed coordinates in mm; J6 axis is +Z through (X,Y)=(-25,0)',
 'Complete annular cutter R21.10..28.90; Z=34.80..39.10 (depth4.30)',
 'Nominal head/washer radial envelope R21.50..28.50; clearance0.40 each side',
 'Nominal head lower Z35.20; washer upper Z38.70; clearance0.40 each side',
 'Original RS00/J6 interfaces and all upstream axes retained; STEP defines other features',
 'One closed solid; volume removed188.50 mm3 (0.347%); not a strength qualification',
 'Use108 IN PLACE OF105. Do not stack; old105 has intermediate-angle collision',
 'Bed orientation is a candidate: 88.30 x88.00 x75.80; support/fit trial required',
 '73 sampled whole-wrist poses clear after revision; not continuous all-body clearance',
 'Supported, unpowered, unloaded plastic trial only; no metal tolerances/CNC release']
text=''.join(f'<text x="35" y="{505+26*k}">{html.escape(n)}</text>' for k,n in enumerate(notes))
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="850" viewBox="0 0 1080 850">
<rect width="1080" height="850" fill="#f8f9f8"/><style>text{{font-family:Arial,sans-serif;fill:#233d48;font-size:16px}}</style>
<text x="35" y="42" style="font-size:25px;font-weight:bold">{p['id']} / WRIST-ROUTE01</text>
<text x="35" y="72">PLASTIC FIT WORKING DRAWING / mm / dimensions override projection scale</text>
<text x="35" y="97">Exact CAD projections. STEP and datum table authoritative; no manufacturing release.</text>
<g transform="translate(35,115)">{views[0]}</g><g transform="translate(555,115)">{views[1]}</g>
<text x="35" y="470">TOP VIEW (+Z) / full circular head-sweep relief</text><text x="555" y="470">SIDE VIEW (+Y)</text>
{text}<text x="35" y="825" style="font-size:12px">STEP SHA256: {p['step_sha256']}</text></svg>'''
f=DRAW/(p['id']+'.svg');f.write_text('\n'.join(t.rstrip() for t in svg.splitlines())+'\n')
(DRAW/'sources.json').write_text(json.dumps(dict(carrier_manifest_sha256=sha(OUT/'carrier-manifest.json'),step_sha256=sha(step),drawing_sha256=sha(f)),indent=2)+'\n')
print('DRAWING_PASS')
