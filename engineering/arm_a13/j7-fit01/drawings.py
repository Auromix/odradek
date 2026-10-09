# SPDX-License-Identifier: CC-BY-NC-4.0
"""Exact CAD projections with feature tables; plastic-fit working drawings."""
from pathlib import Path
import json,hashlib,html
import cadquery as cq

HERE=Path(__file__).resolve().parent;OUT=HERE/'build';DRAW=OUT/'drawings'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
FEATURES={
 '101':[
  'Datum A: rear plane X=33.3; datum B: bearing axis +X',
  'Axial housing length 20.9; max outer diameter 84 (unchanged)',
  'Bearing seat diameter 47.20 nominal; stops bore diameter 44.80',
  'Rear bearing contact X=36.2..43.2; front contact X=47.2..54.2',
  'Outer-ring central stop X=43.2..47.2 (4.0 axial length)',
  '6 x diameter 3.50 through; PCD70; angles 30 + 60k deg about X',
  '6 x radial windows: cutter R8.5 at radial distance 41',
  'Window centres: angles 0 + 60k deg; axial X=36.3..51.2',
  'Axial end webs 3.0 nominal; window inner radius 32.5',
  'Inherited six fixed-motor head reliefs: exact STEP is authoritative',
  'Coupon gauge selection required; 47.20 is provisional for FDM'],
 '102':[
  'Datum A: rear plane X=54.2; datum B: bearing axis +X',
  'Plate thickness 2.50; inner opening diameter 44.80',
  'Max envelope diameter 84; six-lobed rim, not a full outer disk',
  '6 x diameter 3.50 through; PCD70; angles 30 + 60k deg',
  '6 x scallops: cutter R13 at radial distance 45',
  'Scallop centres: angles 0 + 60k deg; full-thickness cut',
  'Front plane X=56.7; rotating flange rear plane X=57.7',
  'Nominal gap 1.00: measure axial stack before rotating'],
 '103':[
  'Datum A: motor output face X=25.7; datum B: axis +X',
  'Main journal diameter 34.95; end X=57.7',
  'Integral rear inner-ring stop: diameter 37; X=34.2..36.2',
  'New front pilot: diameter 20.00; X=57.7..59.7',
  '6 x diameter 3.50 axial through; actual RS00 PCD27',
  'Hole yz: (+/-11.69134,+/-6.75), (0,+/-13.5)',
  'Front flange is separate; both ID35 bearings insert from +X',
  'Journal fit nominal is provisional: test 34.85/34.95/35.05 coupons'],
 '104':[
  'Datum A: rear plane X=54.2; datum B: bearing axis +X',
  'Thickness 3.50; OD37.00; ID35.10',
  'Front plane X=57.7; abuts detachable flange rear face',
  'Measure endplay; shim after measurement, do not bend plastic for preload'],
 '105':[
  'Inherited P06-yaw-to-roll from A11; unchanged geometry',
  'Local J7 coordinate = source J6.rotor coordinate minus (25,0,0)',
  'J7 fixed face X=25.3; original motor hole positions retained',
  'Cage 6 x diameter 3.50; PCD70; 30 + 60k deg about +X',
  'Rear captive nuts / inherited mounting reliefs: see exact STEP',
  'Carrier is a fit fixture here; not newly released manufacturing structure'],
 '106':[
  'Datum A: rear plane X=57.7; datum B: axis +X',
  'OD60; thickness 8.00; front plane X=65.7',
  'New rear pilot bore: diameter 20.20, depth 2.20',
  '6 x diameter 3.50 through on actual RS00 PCD27',
  'Head access diameter 7.60 starts X=61.2; recess depth 4.50',
  'Output M3x40 bolts clamp both journal and separate flange',
  '3 x diameter 4.50 through; PCD45; 30 + 120k deg',
  'Inherited rear M4 nut traps: hex circumscribed diameter 8.30, depth 3.50',
  'Locate on journal pilot; inspect screw bottoming before tightening']}


def main():
 DRAW.mkdir(exist_ok=True)
 D=json.loads((OUT/'manifest.json').read_text());rows=[]
 for p in D['parts']:
  if p['role']=='fit_coupon':continue
  step=OUT/'step'/(p['id']+'.step');assert sha(step)==p['step_sha256']
  s=cq.importers.importStep(str(step)).val()
  svgs=[]
  for direction in [(1,0,0),(0,1,0)]:
   svg=cq.exporters.getSVG(s,dict(width=475,height=345,marginLeft=25,marginTop=25,
       projectionDir=direction,showAxes=False,showHidden=True,
       strokeColor=(35,55,65),hiddenColor=(160,174,183),strokeWidth=.6))
   svg=svg[svg.index('<svg'):];svgs.append(svg)
  key=p['id'].split('-')[2];lines=FEATURES[key]
  text=''.join(f'<text x="35" y="{520+26*k}">{html.escape(line)}</text>' for k,line in enumerate(lines))
  svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="880" viewBox="0 0 1080 880">
<rect width="1080" height="880" fill="#f8f9f8"/><style>text{{font-family:Arial,sans-serif;fill:#233d48;font-size:16px}}.title{{font-size:25px;font-weight:bold}}.small{{font-size:12px}}</style>
<text x="35" y="42" class="title">{p['id']} / FIT01</text>
<text x="35" y="71">PLASTIC FIT WORKING DRAWING / mm / dimensions override view scale</text>
<text x="35" y="97">CAD projections; STEP authoritative. Angle 0 = +Y, positive toward +Z. No CNC release.</text>
<g transform="translate(35,115)">{svgs[0]}</g><g transform="translate(555,115)">{svgs[1]}</g>
<text x="35" y="475">AXIAL VIEW (+X)</text><text x="555" y="475">SIDE VIEW (+Y)</text>
{text}<text x="35" y="852" class="small">STEP SHA256: {p['step_sha256']}</text></svg>'''
  path=DRAW/(p['id']+'.svg');path.write_text(svg)
  rows.append(dict(id=p['id'],step_sha256=p['step_sha256'],svg_sha256=sha(path)))
 # Axial stack schematic is explicitly separate from exact part projections.
 features=[('Motor output',25.7,25.7,'#63727d'),('Journal rear stop',34.2,36.2,'#527086'),
           ('Rear bearing',36.2,43.2,'#9ca8b2'),('Outer-ring stop',43.2,47.2,'#243b50'),
           ('Front bearing',47.2,54.2,'#9ca8b2'),('Inner spacer',54.2,57.7,'#d89b42'),
           ('Front retainer',54.2,56.7,'#243b50'),('Detachable flange',57.7,65.7,'#527086')]
 labels='';shapes=''
 for k,(name,a,z,color) in enumerate(features):
  y=135+k*63;x=350+(a-25)*15;width=max(2,(z-a)*15)
  labels+=f'<text x="35" y="{y+24}">{name}</text><text x="940" y="{y+24}">{a:g}..{z:g}</text>'
  shapes+=f'<rect x="{x}" y="{y}" width="{width}" height="38" rx="2" fill="{color}"/>'
 drawing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="830">
<rect width="1080" height="830" fill="#f8f9f8"/><style>text{{font-family:Arial,sans-serif;fill:#233d48;font-size:18px}}</style>
<text x="35" y="45" style="font-size:28px;font-weight:bold">J7 axial stack / +X / mm</text>
<text x="35" y="80">Stack schematic only; part geometry comes from the six STEP projections.</text>
<text x="940" y="117">X span mm</text>{labels}{shapes}
<text x="35" y="695">Assembly: bearings enter opposite housing ends; cartridge enters journal from +X.</text>
<text x="35" y="728">Then fit retainer + inner spacer + detachable flange; output bolts secure the rotor.</text>
<text x="35" y="761">Nominal rotor/retainer gap 1.0; actual endplay and thread bottoming must be measured.</text>
<text x="35" y="794">Supported unpowered plastic fit only; motor housing has no assumed cable through-bore.</text></svg>'''
 path=DRAW/'J7-axial-stack.svg';path.write_text(drawing)
 (DRAW/'sources.json').write_text(json.dumps(dict(manifest_sha256=sha(OUT/'manifest.json'),parts=rows,
      stack_svg_sha256=sha(path),scope='Exact CAD projections with plastic fit feature dimensions; no metal tolerances or CNC release'),indent=2)+'\n')
 print('DRAWINGS',len(rows),'part sheets + axial stack')


if __name__=='__main__':main()
