# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Run with KiCad's bundled Python. Canonical footprints and DSN export."""
import json,math,re
from pathlib import Path
import wx,pcbnew
app=wx.App(False)
D=Path(__file__).resolve().parent
b=pcbnew.LoadBoard(str(D/'upper-petal-unrouted.kicad_pcb'))
N=json.loads((D.parent/'netlist.json').read_text());F=json.loads((D/'placement-map.json').read_text())['components']
expected={(p['ref'],p['pin']):p['net'] for p in N['pins']}
comp={c['ref']:c for c in N['components']}
comparisons=[]
for old in list(b.GetFootprints()):
 ref=old.GetReference();c=comp[ref];p=F[ref]
 fp=pcbnew.FootprintLoad(str(D/'ULP.pretty'),c['footprint']);fp.SetReference(ref);fp.SetValue(c['manufacturer_part_number']);fp.SetPosition(old.GetPosition())
 fp.SetPath(old.GetPath());fp.SetUuid(old.m_Uuid)
 b.Add(fp) # Flip requires a BOARD parent to resolve copper layers in KiCad 10.
 fp.thisown=False
 if p['side']=='B':fp.Flip(fp.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
 if p['projection_rotation_deg']:fp.SetOrientationDegrees(fp.GetOrientationDegrees()-p['projection_rotation_deg'])
 oldpads={x.GetNumber():x for x in old.Pads() if x.GetNumber()}
 diffs=[]
 for pad in fp.Pads():
  num=pad.GetNumber()
  if not num:continue
  net=expected[(ref,num)]
  if net:pad.SetNet(b.FindNet(net))
  a=pad.GetPosition();z=oldpads[num].GetPosition();delta=math.hypot(a.x-z.x,a.y-z.y)/1e6
  if delta>1e-6:diffs.append({'pin':num,'delta_mm':delta,'native_xy_mm':[a.x/1e6,a.y/1e6],'initial_xy_mm':[z.x/1e6,z.y/1e6]})
 comparisons.append({'ref':ref,'pad_differences':diffs})
 b.Remove(old);old.thisown=False
# Full ground reference on In2; remaining layers may carry routes.
zone=pcbnew.ZONE(b);zone.SetLayer(pcbnew.In2_Cu);zone.SetNet(b.FindNet('GND'));zone.SetLocalClearance(pcbnew.FromMM(.15));zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
outline=zone.Outline();outline.NewOutline()
for x,y in json.loads((D.parent/'mechanical-power-budget.json').read_text())['board_outline_reference_mm']:outline.Append(pcbnew.FromMM(x),pcbnew.FromMM(40-y))
b.Add(zone);b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(str(D/'upper-petal.kicad_pcb'),b)
(D/'checks'/'native-footprint-comparison.json').write_text(json.dumps({'purpose':'Canonical KiCad library load/Flip versus generator front-projection pads','comparisons':comparisons,'changed_components':[r['ref'] for r in comparisons if r['pad_differences']]},indent=2)+'\n')
assert all(not r['pad_differences'] for r in comparisons),'Native flip differs from placement plan; inspect before routing'
ok=pcbnew.ExportSpecctraDSN(b,str(D/'upper-petal.dsn'))
if ok:
 p=D/'upper-petal.dsn';p.write_text(re.sub(r'^\(pcb .*?\n','(pcb \"upper-petal.dsn\"\n',p.read_text(),count=1))
print('Canonical footprints, GND zone, DSN export',ok)
