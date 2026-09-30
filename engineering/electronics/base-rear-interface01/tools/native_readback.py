#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Independent readback from delivered KiCad file; capture only completed real routing."""
from pathlib import Path
import wx,pcbnew as p,json,sys,hashlib,math
app=wx.App(False);D=Path(__file__).resolve().parents[1];K=D/'kicad';b=p.LoadBoard(str(K/'base-rear-interface01.kicad_pcb'));mm=p.ToMM
xy=lambda pt:[mm(pt.x),mm(pt.y)]
N=json.loads((D/'netlist.json').read_text());C={c['ref']:c for c in N['components']};fps=[];pads=[]
for fp in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
 ref=fp.GetReference();c=C[ref];pos=xy(fp.GetPosition());assert max(abs(pos[i]-[c['u_mm'],c['v_mm']][i])for i in range(2))<1e-5
 fps.append(dict(ref=ref,MPN=fp.GetField('MPN').GetText(),value=fp.GetValue(),footprint=str(fp.GetFPID().GetLibItemName()),uv_mm=pos,rotation_KiCad_deg=fp.GetOrientationDegrees()))
 for pd in fp.Pads():pads.append(dict(ref=ref,pin=pd.GetNumber(),net=pd.GetNetname(),uv_mm=xy(pd.GetPosition()),size_mm=xy(pd.GetSize()),drill_mm=xy(pd.GetDrillSize()),type='NPTH'if pd.GetAttribute()==p.PAD_ATTRIB_NPTH else'PTH'))
tracks=[];vias=[]
for t in b.GetTracks():
 if isinstance(t,p.PCB_VIA):vias.append(dict(uv_mm=xy(t.GetPosition()),diameter_mm=mm(t.GetWidth(p.F_Cu)),drill_mm=mm(t.GetDrill()),net=t.GetNetname(),locked=t.IsLocked()))
 else:tracks.append(dict(start_uv_mm=xy(t.GetStart()),end_uv_mm=xy(t.GetEnd()),width_mm=mm(t.GetWidth()),net=t.GetNetname(),layer=t.GetLayerName(),locked=t.IsLocked()))
tracks.sort(key=lambda x:(x['net'],x['layer'],x['start_uv_mm'],x['end_uv_mm']));vias.sort(key=lambda x:(x['net'],x['uv_mm']))
assert not any(t['layer']in['In1.Cu','In2.Cu']for t in tracks),'Inner references must have no tracks'
lengths={n:sum(math.dist(t['start_uv_mm'],t['end_uv_mm'])for t in tracks if t['net']==n)for n in ['ETH_'+str(i)for i in range(1,9)]}
pairs=[]
for a,c in [(1,2),(3,6),(4,5),(7,8)]:
 pair=['ETH_'+str(a),'ETH_'+str(c)];pairs.append(dict(nets=pair,copper_track_length_mm=[lengths[n]for n in pair],track_length_difference_mm=abs(lengths[pair[0]]-lengths[pair[1]]),through_vias=[sum(v['net']==n for v in vias)for n in pair],coupled_trunk_mm=22,limitations='track sum excludes barrel electrical length; fanout not impedance-tuned; no fabricatedchannel qualification'))
keepouts=[dict(all_copper=z.GetLayerSet().Contains(p.F_Cu)and z.GetLayerSet().Contains(p.B_Cu)and z.GetLayerSet().Contains(p.In1_Cu)and z.GetLayerSet().Contains(p.In2_Cu),tracks=z.GetDoNotAllowTracks(),vias=z.GetDoNotAllowVias(),fills=z.GetDoNotAllowZoneFills())for z in b.Zones()if z.GetIsRuleArea()]
read=dict(mount_keepouts=keepouts,revision='BRI01',board_sha256=hashlib.sha256((K/'base-rear-interface01.kicad_pcb').read_bytes()).hexdigest(),thickness_mm=mm(b.GetDesignSettings().GetBoardThickness()),footprints=fps,pads=pads,tracks=tracks,vias=vias,pair_audit=pairs,inner_track_count=0,unconnected_via_or_tracks_checked_by='reports/drc.json')
(D/'native-readback.json').write_text(json.dumps(read,indent=2)+'\n')
if '--capture-routing'in sys.argv:(D/'routing-plan.json').write_text(json.dumps(dict(tracks=tracks,vias=vias),indent=2)+'\n')
print(len(fps),'footprints',len(pads),'pads',len(tracks),'tracks',len(vias),'vias');print(json.dumps(pairs))
