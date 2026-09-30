#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Replay real final copper, no temporary router terminals or router artifacts."""
from pathlib import Path
import wx,pcbnew as p,json,re
app=wx.App(False);D=Path(__file__).resolve().parents[1];K=D/'kicad';path=K/'base-rear-interface01.kicad_pcb';pr=K/'base-rear-interface01.kicad_pro';proj=pr.read_text();b=p.LoadBoard(str(path));R=json.loads((D/'routing-plan.json').read_text());u=lambda value:int(round(value*1000000));v=lambda z:p.VECTOR2I(u(z[0]),u(z[1]));layers={b.GetLayerName(i):i for i in[p.F_Cu,p.B_Cu,p.In1_Cu,p.In2_Cu]}
assert len(list(b.GetTracks()))==0,'Replay requires fresh build_board placement'
for x in R['tracks']:
 t=p.PCB_TRACK(b);t.SetStart(v(x['start_uv_mm']));t.SetEnd(v(x['end_uv_mm']));t.SetWidth(u(x['width_mm']));t.SetLayer(b.GetLayerID(x['layer']));t.SetNet(b.FindNet(x['net']));t.SetLocked(x['locked']);b.Add(t);t.thisown=False
for x in R['vias']:
 t=p.PCB_VIA(b);t.SetPosition(v(x['uv_mm']));t.SetWidth(u(x['diameter_mm']));t.SetDrill(u(x['drill_mm']));t.SetViaType(p.VIATYPE_THROUGH);t.SetLayerPair(p.F_Cu,p.B_Cu);t.SetNet(b.FindNet(x['net']));t.SetLocked(x['locked']);b.Add(t);t.thisown=False
b.BuildConnectivity();filler=p.ZONE_FILLER(b);zones=b.Zones();filler.Fill(zones);p.SaveBoard(str(path),b);pr.write_text(proj)
# Explicit nominal candidate stack, based on JLC04161H-7628 official table.
# No fabricated impedance/copper/plating/tolerance result is implied.
s=path.read_text();stack='''
  (stackup
   (layer "F.SilkS" (type "Top Silk Screen"))
   (layer "F.Mask" (type "Top Solder Mask"))
   (layer "F.Cu" (type "copper") (thickness 0.035))
   (layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4))
   (layer "In1.Cu" (type "copper") (thickness 0.0152))
   (layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6))
   (layer "In2.Cu" (type "copper") (thickness 0.0152))
   (layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4))
   (layer "B.Cu" (type "copper") (thickness 0.035))
   (layer "B.Mask" (type "Bottom Solder Mask"))
   (layer "B.SilkS" (type "Bottom Silk Screen"))
   (copper_finish "ENIG candidate") (dielectric_constraints no)
  )
'''
# Fresh board frombuild_board has no existing stack; do not append duplicate on repeatedcheck.
if '(stackup' not in s:s=s.replace('(setup','(setup'+stack,1)
path.write_text(s)
print('replayed',len(R['tracks']),'tracks',len(R['vias']),'vias')
