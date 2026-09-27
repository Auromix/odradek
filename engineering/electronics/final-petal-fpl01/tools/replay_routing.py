# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Replay only the source-matched FPL01 route snapshot. Re-run actual ERC/DRC."""
import json,hashlib
from pathlib import Path
import wx,pcbnew
app=wx.App(False);D=Path(__import__("sys").argv[1]).resolve();j=json.loads((D/'routing-plan.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(D.parent/'netlist.json')==j['source_netlist_sha256'],'Netlist changed: routing is stale'
for name,digest in j['footprint_hashes'].items():assert sha(D/'FPL.pretty'/name)==digest,'Footprint changed: '+name
b=pcbnew.LoadBoard(str(D/'petal.kicad_pcb'));u=pcbnew.FromMM
assert b.GetCopperLayerCount()==j['copper_layer_count']
assert abs(b.GetDesignSettings().GetBoardThickness()/1e6-j['total_board_thickness_mm'])<1e-6
vec=lambda p:pcbnew.VECTOR2I(u(p[0]),u(p[1]))
for fp in b.GetFootprints():
 pos=j['positions'][fp.GetReference()];assert ('B' if fp.IsFlipped() else 'F')==pos['side'];assert abs(fp.GetOrientationDegrees()-pos['rotation_deg'])<1e-6
 fp.SetPosition(vec(pos['xy_mm']))
for t in list(b.GetTracks()):b.Remove(t);t.thisown=False
for z in list(b.Zones()):
 if not z.GetIsRuleArea():b.Remove(z);z.thisown=False
for rec in j['copper_zones']:
 z=pcbnew.ZONE(b);z.SetLayer(b.GetLayerID(rec['layer']));z.SetNet(b.FindNet(rec['net']));z.SetLocalClearance(u(rec['clearance_mm']));z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
 for points in rec['outlines_mm']:
  z.Outline().NewOutline()
  for point in points:z.Outline().Append(vec(point))
 b.Add(z);z.thisown=False
for r in j['copper_items']:
 if r['kind']=='via':
  t=pcbnew.PCB_VIA(b);t.SetPosition(vec(r['xy_mm']));t.SetDrill(u(r['drill_mm']));t.SetViaType(pcbnew.VIATYPE_THROUGH);t.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
 else:t=pcbnew.PCB_TRACK(b);t.SetStart(vec(r['start_mm']));t.SetEnd(vec(r['end_mm']));t.SetLayer(b.GetLayerID(r['layer']))
 t.SetWidth(u(r['width_mm']));t.SetNet(b.FindNet(r['net']));t.SetLocked(r['locked']);t.SetUuid(pcbnew.KIID(r['uuid']));b.Add(t);t.thisown=False
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(D/'petal.kicad_pcb'),b)
print('Replayed source-matched routing snapshot; actual KiCad checks remain required')
