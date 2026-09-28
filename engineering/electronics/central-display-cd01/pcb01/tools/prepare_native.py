#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Canonical footprint loading/back flip, exact native pad comparison, GND reference."""
import wx,pcbnew,json,math,sys
from pathlib import Path
app=wx.App(False);D=Path(sys.argv[1]).resolve();P=D.parent
b=pcbnew.LoadBoard(str(D/'central-unrouted.kicad_pcb'));N=json.loads((P/'netlist.json').read_text());expected={(p['ref'],p['pin']):p['net'] for p in N['pins']};C={c['ref']:c for c in N['components']};checks=[]
for old in list(b.GetFootprints()):
 ref=old.GetReference();c=C[ref];fp=pcbnew.FootprintLoad(str(D/'CD.pretty'),c['footprint']);fp.SetReference(ref);fp.SetValue(c['manufacturer_part_number']);fp.SetPosition(old.GetPosition());fp.SetPath(old.GetPath());fp.SetUuid(old.m_Uuid);b.Add(fp);fp.thisown=False
 if c['side']=='B':fp.Flip(fp.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
 fp.SetOrientationDegrees(fp.GetOrientationDegrees()-c.get('projection_rotation_deg',0))
 oldpads={p.GetNumber():p for p in old.Pads() if p.GetNumber()};diffs=[]
 for pd in fp.Pads():
  num=pd.GetNumber()
  if not num:continue
  net=expected[ref,num]
  if net:pd.SetNet(b.FindNet(net))
  a=pd.GetPosition();z=oldpads[num].GetPosition();delta=math.hypot(a.x-z.x,a.y-z.y)/1e6
  if delta>1e-6:diffs.append(dict(pin=num,delta_mm=delta))
 checks.append(dict(ref=ref,pad_differences=diffs));b.Remove(old);old.thisown=False
assert not any(c['pad_differences'] for c in checks),checks
z=pcbnew.ZONE(b);z.SetLayer(pcbnew.In2_Cu);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(pcbnew.FromMM(.127));z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL);o=z.Outline();o.NewOutline()
for i in range(256):t=2*math.pi*i/256;o.Append(pcbnew.FromMM(40+30*math.cos(t)),pcbnew.FromMM(40+30*math.sin(t)))
b.Add(z);z.thisown=False
# Optional future thermal patch stays free of non-ground B-side copper, vias and parts.
for x in [30,50]:
 z=pcbnew.ZONE(b);z.SetLayer(pcbnew.B_Cu);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(pcbnew.FromMM(.127));z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL);o=z.Outline();o.NewOutline()
 for xx,yy in [(x-2,23),(x+2,23),(x+2,27),(x-2,27)]:o.Append(pcbnew.FromMM(xx),pcbnew.FromMM(yy))
 b.Add(z);z.thisown=False
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(D/'central.kicad_pcb'),b)
(D/'checks/native-footprint-comparison.json').write_text(json.dumps(dict(revision='CD-PCB01',native_Flip_checked_against_generator=True,comparisons=checks),indent=2)+'\n')
print('Canonical all318 footprints; explicit native flip parity; ground reference In2')
