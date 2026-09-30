#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Build B04 native 2-layer PCB. All custom footprint dimensions are explicit."""
from pathlib import Path
import json,math,uuid,sys
import wx
app=wx.App(False)
import pcbnew as p
D=Path(__file__).resolve().parents[1];K=D/'kicad';L=K/'B04.pretty';L.mkdir(exist_ok=True)
N=json.loads((D/'netlist.json').read_text());M=json.loads((K/'schematic-build-map.json').read_text())
q=lambda s:json.dumps(str(s));u=p.FromMM;vec=lambda xy:p.VECTOR2I(u(xy[0]),u(xy[1]));xy=lambda uv:[uv[0],50-uv[1]]
# local footprints in viewed-from-front physical u/v; converted to KiCad y-down.
# Each pad: number,x,y,width,height,drill or0; z values in other JSON.
F={
'R0603':dict(body=[-0.8,-.425,.8,.425],pads=[['1',-.85,0,.9,.95,0],['2',.85,0,.9,.95,0]]),
'C0603':dict(body=[-.85,-.45,.85,.45],pads=[['1',-.8,0,.8,.9,0],['2',.8,0,.8,.9,0]]),
'R1206':dict(body=[-1.6,-.8,1.6,.8],pads=[['1',-1.5,0,1.1,1.9,0],['2',1.5,0,1.1,1.9,0]]),
'R2512':dict(body=[-3.15,-1.6,3.15,1.6],pads=[['1',-2.85,0,1.6,3.5,0],['2',2.85,0,1.6,3.5,0]]),
'C1210':dict(body=[-1.85,-1.4,1.85,1.4],pads=[['1',-1.65,0,1.1,2.5,0],['2',1.65,0,1.1,2.5,0]]),
'F2410':dict(body=[-3.05,-1.345,3.05,1.345],pads=[['1',-2.8,0,2.4,3.2,0],['2',2.8,0,2.4,3.2,0]]),
'SMA':dict(body=[-2.3,-1.475,2.3,1.475],pads=[['1',-2.2,0,2.0,2.0,0],['2',2.2,0,2.,2.,0]]),
'SMB':dict(body=[-2.285,-1.97,2.285,1.97],pads=[['1',-2.4,0,2.2,2.3,0],['2',2.4,0,2.2,2.3,0]]),
'SOD323':dict(body=[-.9,-.675,.9,.675],pads=[['1',-1.2,0,.8,.9,0],['2',1.2,0,.8,.9,0]]),
'SOT23':dict(body=[-.7,-1.5,.7,1.5],pads=[['1',-1.05,.95,1.,.95,0],['2',-1.05,-.95,1.,.95,0],['3',1.05,0,1.,.95,0]]),
'TI_DDA8':dict(body=[-1.99,-2.45,1.99,2.45],pads=[[str(i+1),-2.875,1.905-i*1.27,2.2,.5,0] for i in range(4)]+[[str(i+5),2.875,-1.905+i*1.27,2.2,.5,0] for i in range(4)]+[['9',0,0,2.95,4.9,0]]),
'MSS1246T':dict(body=[-6.15,-6.15,6.15,6.15],pads=[['1',-5.2,0,2.4,5.6,0],['2',5.2,0,2.4,5.6,0]]),
'DIP4':dict(body=[-1.145,-3.685,8.765,1.145],pads=[['1',0,0,1.8,2.0,.8],['2',0,-2.54,1.8,2.0,.8],['3',7.62,-2.54,1.8,2.0,.8],['4',7.62,0,1.8,2.0,.8]]),
'MC2':dict(body=[-8,-2.6,1.2,6.41],pads=[[str(i+1),0,i*3.81,3.6,1.8,1.2] for i in range(2)]),
'MC4':dict(body=[-8,-2.6,1.2,14.03],pads=[[str(i+1),0,i*3.81,3.6,1.8,1.2] for i in range(4)]),
'XH4':dict(body=[-2.3,-2.45,9.2,9.95],pads=[[str(i+1),0,i*2.5,1.7,1.7,1.0] for i in range(4)]),
'TP':dict(body=[-.75,-.75,.75,.75],pads=[['1',0,0,1.5,1.5,0]]),
'M3':dict(body=[-3.5,-3.5,3.5,3.5],pads=[['',0,0,3.2,3.2,3.2]])}
for name,f in F.items():
 pads=f['pads'];lo=f['body'];bbox=[min(lo[0],min(v[1]-v[3]/2 for v in pads))-.25,min(lo[1],min(v[2]-v[4]/2 for v in pads))-.25,max(lo[2],max(v[1]+v[3]/2 for v in pads))+.25,max(lo[3],max(v[2]+v[4]/2 for v in pads))+.25]
 if name=='M3':bbox=[-3.5,-3.5,3.5,3.5]
 lines=[f'(footprint {q(name)} (version 20240108) (generator "pcbnew") (layer "F.Cu") (attr {"through_hole" if any(v[-1] for v in pads) else "smd"})',f'(property "Reference" "REF**" (at 0 {-bbox[3]-1} 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness .12))))',f'(property "Value" {q(name)} (at 0 {-bbox[1]+1} 0) (layer "F.Fab") (effects (font (size .7 .7) (thickness .1))))',f'(fp_rect (start {lo[0]} {-lo[3]}) (end {lo[2]} {-lo[1]}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))',f'(fp_rect (start {bbox[0]} {-bbox[3]}) (end {bbox[2]} {-bbox[1]}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))']
 for num,x,y,w,h,dr in pads:
  attr='np_thru_hole' if name=='M3' else 'thru_hole' if dr else 'smd';shape='circle' if name in ['M3','TP'] else 'oval' if dr and num!='1' else 'roundrect';layer='"*.Cu" "*.Mask"' if dr else '"F.Cu" "F.Mask"'+(' "F.Paste"' if name not in ['TP','TI_DDA8'] or num!='9' and name!='TP' else '')
  if name=='TI_DDA8' and num=='9':layer='"F.Cu"'
  lines.append(f'(pad {q(num)} {attr} {shape} (at {x} {-y}) (size {w} {h}) '+(f'(drill {dr})' if dr else '')+f' (layers {layer})'+(' (roundrect_rratio .1)' if shape=='roundrect' else '')+')')
 if name=='TI_DDA8':
  lines.append('(pad "" smd rect (at 0 0) (size 2.4 3.1) (layers "F.Mask" "F.Paste"))')
 if name in ['SMA','SMB','SOD323','TI_DDA8','MC2','MC4','XH4','DIP4']:
  v=pads[0];lines.append(f'(fp_circle (center {v[1]} {-v[2]-.0}) (end {v[1]+.15} {-v[2]}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))')
 lines+=[')'];(L/(name+'.kicad_mod')).write_text('\n'.join(lines)+'\n')
(D/'footprint-dimensions.json').write_text(json.dumps(F,indent=2)+'\n')
proj={'board':{'design_settings':{'rule_severities':{k:'error' for k in ['missing_courtyard','track_not_centered_on_via','tuning_profile_track_geometries','footprint_filters_mismatch','footprint_type_mismatch']},'rules':{'min_clearance':.25,'min_track_width':.25,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_hole_to_hole':.25,'min_hole_clearance':.25,'min_copper_edge_clearance':.3}}},'net_settings':{'classes':[{'name':'Default','clearance':.25,'track_width':.3,'via_diameter':.7,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.25,'diff_pair_gap':.25,'diff_pair_via_gap':.25}]},'meta':{'filename':'base-b04.kicad_pro','version':1}}
(K/'base-b04.kicad_pro').write_text(json.dumps(proj,indent=2)+'\n')
b=p.BOARD();b.SetCopperLayerCount(2);b.GetDesignSettings().SetBoardThickness(u(1.6));b.GetDesignSettings().m_TrackMinWidth=u(.25);b.GetDesignSettings().m_MinClearance=u(.25);b.SetFileName(str(K/'base-b04.kicad_pcb'))
for n in sorted(N['nets']):ni=p.NETINFO_ITEM(b,n);b.Add(ni);ni.thisown=False
maps={};meta=[]
for c in N['components']:
 ref=c['ref'];fp=p.FootprintLoad(str(L),c['footprint']);fp.SetReference(ref);fp.SetValue(c['value']);fp.SetFPIDAsString('B04:'+c['footprint']);fp.SetPosition(vec(xy([c['u_mm'],c['v_mm']])));fp.SetOrientationDegrees(c['rotation_ccw_deg']);fp.SetPath(p.KIID_PATH('/'+M['root_uuid']+'/'+M['reference_uuids'][ref]));fp.SetField('MPN',c['MPN']);fp.GetField('MPN').SetVisible(False);fp.SetField('Datasheet',c['source_url']);fp.GetField('Datasheet').SetVisible(False)
 for pd in fp.Pads():
  num=pd.GetNumber();pn=next((v for v in N['pins'] if v['ref']==ref and v['pin']==num),None)
  if pn:pd.SetNet(b.FindNet(pn['net']));pd.SetPinFunction(pn['name']);pd.SetPinType(pn['role'])
 fp.Reference().SetLayer(p.F_Fab);b.Add(fp);fp.thisown=False;maps[ref]=fp
 lo=F[c['footprint']]['body'];t=math.radians(c['rotation_ccw_deg']);pts=[[c['u_mm']+x*math.cos(t)-y*math.sin(t),c['v_mm']+x*math.sin(t)+y*math.cos(t)] for x in [lo[0],lo[2]] for y in [lo[1],lo[3]]]
 meta.append(dict(ref=ref,MPN=c['MPN'],origin_uv_mm=[c['u_mm'],c['v_mm']],rotation_ccw_deg=c['rotation_ccw_deg'],body_bbox_board_min_mm=[min(x for x,y in pts),min(y for x,y in pts),1.6],body_bbox_board_max_mm=[max(x for x,y in pts),max(y for x,y in pts),1.6+c['height_mm']],body_basis='official package/catalogue outer envelope plus explicitly selected max height; no generic density mass',footprint=c['footprint']))
for a,z in [([0,0],[80,0]),([80,0],[80,50]),([80,50],[0,50]),([0,50],[0,0])]:
 s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(vec(a));s.SetEnd(vec(z));s.SetLayer(p.Edge_Cuts);s.SetWidth(u(.05));b.Add(s);s.thisown=False
# True rules at metal mounting screws. All copper/parts forbidden insideR3.5.
for xx,yy in [(5,5),(75,5),(75,45),(5,45)]:
 z=p.ZONE(b);z.SetIsRuleArea(True);z.SetLayerSet(p.LSET.AllCuMask());z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowZoneFills(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);o=z.Outline();o.NewOutline()
 for i in range(64):t=2*math.pi*i/64;o.Append(vec([xx+3.5*math.cos(t),yy+3.5*math.sin(t)]))
 b.Add(z);z.thisown=False
# Local ground plane deliberately excludes two isolated field-input islands.
z=p.ZONE(b);z.SetLayer(p.B_Cu);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(u(.4));z.SetPadConnection(p.ZONE_CONNECTION_FULL);o=z.Outline();o.NewOutline()
for a in [[.5,.5],[79.5,.5],[79.5,49.5],[.5,49.5],[.5,44.5],[30.8,44.5],[30.8,23],[.5,23]]:o.Append(vec(xy(a)))
b.Add(z);z.thisown=False
# Reproducible low-inductance critical buck tracks are added separately after placement audit.
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(K/'base-b04.kicad_pcb'),b)
(D/'mechanical-interface.json').write_text(json.dumps(dict(revision='B04-SERVICE01',stage='placed native board; final DRC and rotation audit pending',coordinates='PCB bottom z0; u right,v towards tableinside; assembly[−40+u,-2+v,23+z]; nativeKiCad[x=u,y=50−v]',board_size_mm=[80,50,1.6],global_origin_mm=[-40,-2,23],components=meta,connector_contract='connector-contract.json',not_included=['connector plugs represented separately in connector-contract.json','solder max0.1mm SMD and underboardlead solder added during assembly process','externalLED indicators, harness, strain relief','thermal proof','mass']),indent=2)+'\n')
print('native PCB',len(maps),'footprints')
