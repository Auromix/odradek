#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Read-only snapshot of frozen CD-EC01. PCB01-only placements and constraints."""
from pathlib import Path
import json,math,hashlib
D=Path(__file__).resolve().parent;P=D.parent
for name in ['netlist.json','footprint-constraints.json','pixel-map.csv']:(D/name).write_bytes((P/name).read_bytes())
# PCB01 placement-only change: local hot pads face VCC/VCAP/VIO; no net changes.
n=json.loads((D/'netlist.json').read_text())
poses={'C4':(-6,6.7,180),'C7':(-3.2,6.5,180),'C5':(-11.4,8.0,90),'C8':(-8.6,8.0,90),'C13':(14,6.7,180),'C16':(16.8,6.5,180),'C14':(8.6,8.0,90),'C17':(11.4,8.0,90)}
changes=[]
for c in n['components']:
 if c['ref'] in poses:
  old=[c['x_mm'],c['y_mm'],c.get('projection_rotation_deg',0)];x,y,r=poses[c['ref']];c.update(x_mm=x,y_mm=y,projection_rotation_deg=r)
  changes.append({'ref':c['ref'],'parent_xyz_rotation':[old[0],old[1],old[2]],'pcb01_xy_projection_rotation':[x,y,r]})
(D/'netlist.json').write_text(json.dumps(n,indent=2)+'\n')
(D/'placement-changes.json').write_text(json.dumps({'revision':'CD-PCB01','no_LED_or_GH_changes':True,'changes':changes},indent=2)+'\n')
# Final candidate electrical changes, if any, must be separate explicitly reviewed revision.
b={'board_outline_reference_mm':[[30*math.cos(i*2*math.pi/256),30*math.sin(i*2*math.pi/256)] for i in range(256)],'mounts_xy_mm':[],'status':'True circle used in native Edge.Cuts; polygon only zone outline; source geometry unchanged','thickness_mm':1.0,'thermal_regions_head_xy_mm':[[[-12,13],[-8,17]],[[8,13],[12,17]]]}
(D/'mechanical-power-budget.json').write_text(json.dumps(b,indent=2)+'\n')
(D/'baseline-inputs.json').write_text(json.dumps({'revision':'CD-PCB01','frozen_parent_read_only':True,'sha256':{name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in ['netlist.json','footprint-constraints.json','pixel-map.csv','pin-net.csv','mechanical-packing.json','kicad/central.kicad_sch']}},indent=2)+'\n')
