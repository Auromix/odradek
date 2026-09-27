# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Normalize T-junction segments before pruning native-reported dead ends."""
import json,math
from pathlib import Path
import wx,pcbnew
app=wx.App(False);D=Path(__import__("sys").argv[1]).resolve();b=pcbnew.LoadBoard(str(D/'petal.kicad_pcb'))
restored=[]
tracks=[t for t in b.GetTracks() if not isinstance(t,pcbnew.PCB_VIA)];splits=0
for t in tracks:
 a=t.GetStart();z=t.GetEnd();dx,dy=z.x-a.x,z.y-a.y;d2=dx*dx+dy*dy
 if d2==0:continue
 sites=[]
 for other in tracks:
  if other==t or other.GetNetCode()!=t.GetNetCode() or other.GetLayer()!=t.GetLayer():continue
  for p in [other.GetStart(),other.GetEnd()]:
   f=((p.x-a.x)*dx+(p.y-a.y)*dy)/d2
   if not 1e-7<f<1-1e-7:continue
   d=abs((p.x-a.x)*dy-(p.y-a.y)*dx)/math.sqrt(d2)
   if d<=5:sites.append((f,p)) # <=5nm numerical interpolation tolerance only
 if not sites:continue
 sites=sorted({(p.x,p.y):(f,p) for f,p in sites}.values(),key=lambda r:r[0]);pts=[a]+[p for f,p in sites]+[z]
 for p,q in zip(pts,pts[1:]):
  if p==q:continue
  n=pcbnew.PCB_TRACK(b);n.SetStart(p);n.SetEnd(q);n.SetLayer(t.GetLayer());n.SetWidth(t.GetWidth());n.SetNet(b.FindNet(t.GetNetname()));n.SetLocked(t.IsLocked());b.Add(n);n.thisown=False
 b.Remove(t);t.thisown=False;splits+=1
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(D/'petal.kicad_pcb'),b)
(D/'checks/branch-normalization.json').write_text(json.dumps({'restored_before_normalization':restored,'split_source_segments':splits,'tolerance_nm':5,'purpose':'preserve required T-junction trunk while allowing only the unused continuation to be removed; rerun native DRC required'},indent=2)+'\n');print('Restored',len(restored),'split',splits)
