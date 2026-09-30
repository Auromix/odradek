#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Read actual native placement/pads/drills/routes; optionally capture replay plan."""
from pathlib import Path
import wx,pcbnew as p,json,math,hashlib,sys
app=wx.App(False);D=Path(__file__).resolve().parents[1];K=D/'kicad';b=p.LoadBoard(str(K/'base-b04.kicad_pcb'));N=json.loads((D/'netlist.json').read_text());F=json.loads((D/'footprint-dimensions.json').read_text());C={c['ref']:c for c in N['components']}
mm=lambda z:z/1e6
uv=lambda a:[mm(a.x),50-mm(a.y)]
fps=[];pads=[];holes=[];components=[]
for fp in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
 ref=fp.GetReference();c=C[ref];xy=uv(fp.GetPosition());ang=fp.GetOrientationDegrees();a=math.radians(ang)
 assert max(abs(xy[i]-[c['u_mm'],c['v_mm']][i]) for i in range(2))<1e-5
 fps.append(dict(ref=ref,MPN=fp.GetField('MPN').GetText(),value=fp.GetValue(),footprint=str(fp.GetFPID().GetLibItemName()),uv_mm=xy,rotation_ccw_deg=ang))
 for pd in fp.Pads():
  z=dict(ref=ref,pin=pd.GetNumber(),net=pd.GetNetname(),uv_mm=uv(pd.GetPosition()),size_mm=[mm(pd.GetSize().x),mm(pd.GetSize().y)],drill_mm=[mm(pd.GetDrillSize().x),mm(pd.GetDrillSize().y)],rotation_ccw_deg=pd.GetOrientationDegrees(),type='NPTH' if pd.GetAttribute()==p.PAD_ATTRIB_NPTH else 'PTH' if pd.GetDrillSize().x else 'SMD');pads.append(z)
  if z['drill_mm'][0]:holes.append(z)
 if ref[0]=='H' or ref.startswith('TP'):continue
 # Corrected maximum package/lead projections, independently kept separate from copper lands.
 lo=F[c['footprint']]['body'];basis='catalogue outer package reference envelope; NOT detailed vendor BREP'
 if c['footprint']=='TI_DDA8':lo=[-3.1,-2.5,3.1,2.5]
 if c['footprint']=='SOT23':lo=[-1.25,-1.5,1.25,1.5]
 if c['footprint']=='SMA':lo=[-2.8,-1.475,2.8,1.475]
 if c['footprint']=='SMB':lo=[-2.795,-1.97,2.795,1.97]
 if c['footprint']=='SOD323':lo=[-1.35,-.675,1.35,.675]
 if c['footprint']=='DIP4':lo=[-1.18,-3.71,8.80,1.17];basis='conservative full lead/body projection; installed height4.55 includes planning seating allowance, not a guaranteed maximum'
 if c['footprint']=='C1210':ll,ww=c['body_mm'];lo=[-ll/2,-ww/2,ll/2,ww/2]
 pts=[[xy[0]+x*math.cos(a)-y*math.sin(a),xy[1]+x*math.sin(a)+y*math.cos(a)] for x in [lo[0],lo[2]] for y in [lo[1],lo[3]]]
 solder=0 if c['footprint'] in ['DIP4','MC2','MC4','XH4'] else .1
 bblo=[min(x for x,y in pts),min(y for x,y in pts),1.6];bbhi=[max(x for x,y in pts),max(y for x,y in pts),1.6+c['height_mm']+solder]
 components.append(dict(ref=ref,MPN=c['MPN'],origin_uv_mm=xy,rotation_ccw_deg=ang,body_local_uv_bbox_mm=lo,body_bbox_board_min_mm=bblo,body_bbox_board_max_mm=bbhi,height_above_PCB_top_mm=c['height_mm']+solder,solder_height_planning_mm=solder,body_basis=basis,source_url=c['source_url'],catalogue_dimension_tolerance_status='specific package tolerances included where supplied; connector catalogue reference dimensions require physical fit check',footprint=c['footprint']))
tracks=[];vias=[]
for t in b.GetTracks():
 if isinstance(t,p.PCB_VIA):vias.append(dict(uv_mm=uv(t.GetPosition()),diameter_mm=mm(t.GetWidth(p.F_Cu)),drill_mm=mm(t.GetDrill()),net=t.GetNetname(),locked=t.IsLocked()))
 else:tracks.append(dict(start_uv_mm=uv(t.GetStart()),end_uv_mm=uv(t.GetEnd()),width_mm=mm(t.GetWidth()),net=t.GetNetname(),layer=t.GetLayerName(),locked=t.IsLocked()))
silk=[]
for t in b.GetDrawings():
 if isinstance(t,p.PCB_TEXT):silk.append(dict(text=t.GetText(),uv_mm=uv(t.GetPosition()),size_mm=mm(t.GetTextSize().x),thickness_mm=mm(t.GetTextThickness()),layer=t.GetLayerName()))
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
read=dict(revision='B04-SERVICE01',board_sha256=sha(K/'base-b04.kicad_pcb'),thickness_mm=mm(b.GetDesignSettings().GetBoardThickness()),footprints=fps,pads=pads,holes=holes,tracks=tracks,vias=vias,silk=silk)
(D/'native-readback.json').write_text(json.dumps(read,indent=2)+'\n')
if '--capture-routing' in sys.argv:
 (D/'routing-plan.json').write_text(json.dumps(dict(tracks=tracks,vias=vias,silk=silk,project=json.loads((K/'base-b04.kicad_pro').read_text())),indent=2)+'\n')
conn=json.loads((D/'connector-contract.json').read_text())
mech=dict(revision='B04-SERVICE01',stage='native routed PCB reference assembly; not thermal/physical qualification',coordinates='u/v board mm,z=0 PCB bottom; assembly X=-40+u,Y=-2+v,Z=23+z; KiCad x=u,y=50-v',board_size_mm=[80,50,1.6],global_origin_mm=[-40,-2,23],mount_holes_uv_mm=[[5,5],[75,5],[75,45],[5,45]],mount_diameter_mm=3.2,mount_no_copper_radius_mm=3.5,components=components,connectors=conn['connectors'],native_board_sha256=read['board_sha256'],underboard=dict(component_parts='PTH pins; original contact geometry approximated by finished drill cylinders',planned_trim_and_solder_bottom_z_mm=-2.5,max_permitted_bottom_z_mm=-3,process='trim optocoupler leads and inspect all solder joints; no untrimmed universal lead-length assumption'),service_volumes=[dict(edge='u0',bbox_min_mm=[-30,0,-3],bbox_max_mm=[0,50,21.6]),dict(edge='u80',bbox_min_mm=[80,0,-3],bbox_max_mm=[100,50,21.6])],not_included=['wire loops beyond service volumes','external LED/panel mounts','screw heads and metal standoffs supplied in mechanical assembly','mass or system load qualification'],model_scope='STEP reproduces native drill locations, board thickness, actual placed component package-height envelopes and mated-connector reference envelopes; not vendor detailed CAD')
(D/'mechanical-interface.json').write_text(json.dumps(mech,indent=2)+'\n')
print(len(fps),'footprints',len(pads),'pads',len(tracks),'tracks',len(vias),'vias',len(components),'physical component envelopes')
