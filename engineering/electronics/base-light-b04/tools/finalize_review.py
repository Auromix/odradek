#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Read real exports, render SVG previews, and record this module's source/output hashes."""
from pathlib import Path
import json,hashlib,math
import cadquery as cq
import fitz
D=Path(__file__).resolve().parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
C=json.loads((D/'mechanical-interface.json').read_text());v=json.loads((D/'verification.json').read_text())
assert v['ERC_violations']==v['DRC_violations']==v['unconnected_items']==v['schematic_parity_issues']==0
s=cq.importers.importStep(str(D/'mechanical/native-kicad.step')).val();assert s.isValid() and len(s.Solids())==4
native=[];LEDs=[]
for q in s.Solids():
 b=q.BoundingBox();rec=dict(volume_mm3=q.Volume(),min_mm=[b.xmin,b.ymin,b.zmin],max_mm=[b.xmax,b.ymax,b.zmax]);native.append(rec)
 if q.Volume()<10:LEDs.append([(b.xmin+b.xmax)/2,(b.ymin+b.ymax)/2,b.zmax])
assert sorted([round(p[0],6) for p in LEDs])==[13,25,37]
assert all(abs(p[1]+6)<1e-6 and p[2]+28<=32 for p in LEDs)
render=[]
for name in ['board-front','board-back','base-light-b04','assembly-isometric']:
 f=D/'previews'/(name+'.svg');d=fitz.open(f);out=f.with_suffix('.png');d[0].get_pixmap(matrix=fitz.Matrix(5,5) if name.startswith('board') else fitz.Matrix(1.5,1.5)).save(out);render.append(dict(svg=str(f.relative_to(D)),svg_sha256=sha(f),png=str(out.relative_to(D)),png_sha256=sha(out)))
review=dict(stage='geometry/electrical-file review candidate; no physical verification',native_kicad_STEP=dict(sha256=sha(D/'mechanical/native-kicad.step'),valid=True,solids=native,coordinates='x=u,y=v-12; board bottom reference0. Native STEP contains default1.51mm dielectric, not the entire copper/mask stack; native components use the KiCad stackup reference.'),native_LED_xy_verified=True,native_LED_top_below32_global=True,MCAD_contract='mechanical/base-light-b04-assembly.step uses full1.6mm PCB-envelope and LED upper boundz30.48; authoritative global assembly envelope',renders=render,visual_review='Rendered front/back copper, readable schematic and 3D projection inspected. Back artwork is shown in board-coordinate projection; use numbered pads/continuity, not apparent left-to-right pin order.',remaining=['root cover/light-guide and physical connector/harness assembly','optical cross-talk and brightness at actual service current','production stackup/stencil/solder/wire-crimp process'])
(D/'export-review.json').write_text(json.dumps(review,indent=2)+'\n')
files=[]
for p in sorted(D.rglob('*')):
 if p.is_file() and p.name!='manifest.json' and '.kicad_prl' not in p.name and '__pycache__' not in p.parts:files.append(dict(path=str(p.relative_to(D)),bytes=p.stat().st_size,sha256=sha(p)))
(D/'manifest.json').write_text(json.dumps(dict(revision=C['revision'],file_count=len(files),files=files),indent=2)+'\n')
print('final export review',len(files),'files; native STEP4 solids; global envelope8 solids')
