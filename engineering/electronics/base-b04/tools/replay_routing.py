#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Replay checked actual tracks after build_board; no stochastic autorouter required."""
from pathlib import Path
import wx,pcbnew as p,json
app=wx.App(False);D=Path(__file__).resolve().parents[1];K=D/'kicad';R=json.loads((D/'routing-plan.json').read_text());b=p.LoadBoard(str(K/'base-b04.kicad_pcb'));u=p.FromMM;v=lambda a:p.VECTOR2I(u(a[0]),u(50-a[1]));assert len(list(b.GetTracks()))==0,'Replay requires freshly placed board'
for z in R['tracks']:
 t=p.PCB_TRACK(b);t.SetStart(v(z['start_uv_mm']));t.SetEnd(v(z['end_uv_mm']));t.SetWidth(u(z['width_mm']));t.SetLayer(b.GetLayerID(z['layer']));t.SetNet(b.FindNet(z['net']));t.SetLocked(z['locked']);b.Add(t);t.thisown=False
for z in R['vias']:
 t=p.PCB_VIA(b);t.SetPosition(v(z['uv_mm']));t.SetWidth(u(z['diameter_mm']));t.SetDrill(u(z['drill_mm']));t.SetViaType(p.VIATYPE_THROUGH);t.SetLayerPair(p.F_Cu,p.B_Cu);t.SetNet(b.FindNet(z['net']));t.SetLocked(z['locked']);b.Add(t);t.thisown=False
for z in R['silk']:
 t=p.PCB_TEXT(b);t.SetText(z['text']);t.SetPosition(v(z['uv_mm']));t.SetTextSize(p.VECTOR2I(u(z['size_mm']),u(z['size_mm'])));t.SetTextThickness(u(z['thickness_mm']));t.SetLayer(b.GetLayerID(z['layer']));b.Add(t);t.thisown=False
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(K/'base-b04.kicad_pcb'),b);(K/'base-b04.kicad_pro').write_text(json.dumps(R['project'],indent=2)+'\n')
