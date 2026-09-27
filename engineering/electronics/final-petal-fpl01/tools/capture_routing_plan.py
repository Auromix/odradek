# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Freeze actual native routes for reproducible replay; not manufacturing release."""
import json,hashlib
from pathlib import Path
import wx,pcbnew
app=wx.App(False);D=Path(__import__("sys").argv[1]).resolve();b=pcbnew.LoadBoard(str(D/'petal.kicad_pcb'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def xy(p):return [p.x/1e6,p.y/1e6]
tracks=[]
for t in b.GetTracks():
 d={'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'width_mm':(t.GetWidth(pcbnew.F_Cu) if isinstance(t,pcbnew.PCB_VIA) else t.GetWidth())/1e6,'locked':t.IsLocked()}
 if isinstance(t,pcbnew.PCB_VIA):d.update(kind='via',xy_mm=xy(t.GetPosition()),drill_mm=t.GetDrillValue()/1e6)
 else:d.update(kind='track',start_mm=xy(t.GetStart()),end_mm=xy(t.GetEnd()),layer=b.GetLayerName(t.GetLayer()))
 tracks.append(d)
parts={f.GetReference():{'xy_mm':xy(f.GetPosition()),'side':'B' if f.IsFlipped() else 'F','rotation_deg':f.GetOrientationDegrees()} for f in b.GetFootprints()}
report={'revision':'FPL-01','status':'native geometrically checked routing snapshot; digital checks and physical qualification separate','provenance':'physical matrix buses, deterministic QFN exits, native-shape-tested A* for remaining connections; unused stubs removed only after zero missing connections was established','source_netlist_sha256':sha(D.parent/'netlist.json'),'footprint_hashes':{p.name:sha(p) for p in sorted((D/'FPL.pretty').glob('*.kicad_mod'))},'no_LED_coordinate_changes':True,'positions':parts,'copper_items':tracks,'copper_layer_count':b.GetCopperLayerCount(),'total_board_thickness_mm':b.GetDesignSettings().GetBoardThickness()/1e6,'stackup_status':'six-layer 0.8mm candidate; exact dielectric and copper construction not agreed','GND_reference_layer':'In2.Cu','copper_zones':[{'net':z.GetNetname(),'layer':b.GetLayerName(z.GetLayer()),'clearance_mm':z.GetLocalClearance()/1e6,'outlines_mm':[[xy(z.Outline().COutline(i).CPoint(k)) for k in range(z.Outline().COutline(i).PointCount())] for i in range(z.Outline().OutlineCount())]} for z in b.Zones() if not z.GetIsRuleArea()],'fabrication_release':False}
(D/'routing-plan.json').write_text(json.dumps(report,indent=2)+'\n');print('Frozen actual routes',len(tracks))
