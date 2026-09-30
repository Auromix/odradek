#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Original package envelopes, not redistributed vendor CAD or a photometric model."""
from pathlib import Path
import json,hashlib,math
import cadquery as cq
D=Path(__file__).resolve().parents[1];O=D/'mechanical';O.mkdir(exist_ok=True)
C=json.loads((D/'mechanical-interface.json').read_text())
def box(x,y,z,dx,dy,dz):return cq.Workplane('XY').box(dx,dy,dz,centered=(False,False,False)).translate((x,y,z)).val()
board=box(0,0,0,50,12,1.6)
for h in C['mounts']:board=board.cut(cq.Solid.makeCylinder(1.1,1.6,cq.Vector(*h['uv_mm'],0)))
parts=[dict(name='PCB',shape=board,color=(.06,.18,.14,1))]
# Reference envelope includes explicit XY planning margin, specified max height,
# and selected solder allowance. Its lower face is PCB top +0.10 mm.
led=box(-1.7,-.85,.1,3.4,1.7,.78)
cq.exporters.export(led,str(O/'led-envelope.step'))
for d in C['LEDs']:
 u,v=d['center_uv_mm'];parts.append(dict(name=d['ref']+'_'+d['role'],shape=led.translate((u,v,1.6)),color=(1,.55,.04,1)))
# Real copper-land geometry shown separately; plated finish, solder and wires
# are not volume-complete production models.
for p in C['harness']['J1_pads']:
 u,v=p['center_uv_mm'];parts.append(dict(name='J1_pad'+p['pin'],shape=box(u-1.25,v-1.5,-.035,2.5,3,.035),color=(.72,.54,.21,1)))
checks=[]
for name,shift in [('base-light-b04-local',(0,0,0)),('base-light-b04-assembly',tuple(C['PCB']['global_min_mm']))]:
 a=cq.Assembly(name=name)
 for d in parts:a.add(d['shape'].translate(shift),name=d['name'],color=cq.Color(*d['color']))
 path=O/(name+'.step');a.save(str(path));r=cq.importers.importStep(str(path)).val();expected=sum(d['shape'].Volume() for d in parts)
 assert r.isValid() and len(r.Solids())==8 and abs(r.Volume()-expected)<1e-5
 b=r.BoundingBox();checks.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),solid_count=len(r.Solids()),valid=r.isValid(),volume_mm3=r.Volume(),volume_delta_mm3=r.Volume()-expected,bbox_min_mm=[b.xmin,b.ymin,b.zmin],bbox_max_mm=[b.xmax,b.ymax,b.zmax]))
 if not any(shift):a.save(str(O/'base-light-b04-local.glb'))
lo=C['harness']['local_reservation_global_min_mm'];hi=C['harness']['local_reservation_global_max_mm'];probe=box(*lo,*[hi[i]-lo[i] for i in range(3)]);cq.exporters.export(probe,str(O/'wire-reservation-only-assembly.step'))
# Board substrate-only DXF/STEP/STL for footprint jig; no copper/LED substitutions.
cq.exporters.export(board,str(O/'board-only.step'));cq.exporters.export(board,str(O/'board-only.stl'),tolerance=.02,angularTolerance=.1)
section=cq.Workplane('XY').add(board).section(0.8);cq.exporters.export(section,str(O/'board-outline.dxf'))
compound=cq.Compound.makeCompound([d['shape'] for d in parts]);cq.exporters.export(compound.rotate((0,0,0),(0,0,1),90),str(D/'previews'/'assembly-isometric.svg'),opt={'width':1000,'height':360,'projectionDir':(0.25,-1,1.3),'showHidden':False,'showAxes':False,'strokeWidth':.3})
report=dict(revision=C['revision'],license='CC-BY-NC-4.0',input_contract_sha256=hashlib.sha256((D/'mechanical-interface.json').read_bytes()).hexdigest(),export_checks=checks,highest_LED_global_z_mm=30.48,required_ceiling_mm=32.0,margin_to_ceiling_mm=1.52,models='Original nominal board and LED planning boxes; wire reservation separate; no detailed internal LED die/lens or photometric simulation',mass='not evaluated; no assumed package density')
(O/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('MCAD',report['highest_LED_global_z_mm'],'8 solid assembly valid')
