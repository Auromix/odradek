#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import json,math
import wx
app=wx.App(False)
import pcbnew as p
D=Path(__file__).resolve().parents[1];K=D/'kicad';L=K/'BRI01.pretty';L.mkdir(exist_ok=True)
N=json.loads((D/'netlist.json').read_text());M=json.loads((K/'schematic-build-map.json').read_text())
u=p.FromMM;vec=lambda a:p.VECTOR2I(u(a[0]),u(a[1]));q=lambda s:json.dumps(str(s))
# Coordinates: localPCB u,v match KiCad x,y. All footprints shown from component side.
# RJ drawing pin orientation independently matched to vendor rev26c KiCad library.
F={
'RJ45_615008160221':dict(body=[-7.5,0,7.5,13.45],courtyard=[-9.0,-.4,9.0,14],height=16.1,pads=[[str(i+1),-3.57+1.02*i,6.36+(4 if i%2 else 0),1.3,1.3,.8,'PTH']for i in range(8)]+[['S1',7.4,4.01,1.5,2.5,[1,2],'PTH'],['S2',-7.4,4.01,1.5,2.5,[1,2],'PTH'],['',-6.85,7.06,3.18,3.18,3.18,'NPTH'],['',6.85,7.06,3.18,3.18,3.18,'NPTH']]),
'PC5_2_762':dict(body=[-9.02,0,9.02,29.25],courtyard=[-9.5,-.5,9.5,29.75],height=14.29,pads=[[str(k+1),-3.81+7.62*k,[19.80,22.34,27.42][j],2.7,2.7,1.3,'PTH']for k in range(2)for j in range(3)]),
'THR_M3_74651173':dict(body=[-3.5,-3.5,3.5,3.5],courtyard=[-5,-5,5,5],height=8.7,pads=[['1',x,y,3.2,3.2,1.85,'PTH']for x in[-2.935,2.935]for y in[-2.935,2.935]]),
'M3':dict(body=[-1.6,-1.6,1.6,1.6],courtyard=[-3.5,-3.5,3.5,3.5],height=0,pads=[['',0,0,3.2,3.2,3.2,'NPTH']])}
for name,f in F.items():
 b=f['body'];c=f['courtyard'];s=[f'(footprint "{name}" (version 20240108) (generator "pcbnew") (layer "F.Cu") (attr through_hole)',f'(property "Reference" "REF**" (at 0 {c[1]-1} 0) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))',f'(property "Value" "{name}" (at 0 {c[3]+1} 0) (layer "F.Fab") (effects (font (size .7 .7) (thickness .1))))',f'(fp_rect (start {b[0]} {b[1]}) (end {b[2]} {b[3]}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))',f'(fp_rect (start {c[0]} {c[1]}) (end {c[2]} {c[3]}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))']
 for num,x,y,w,h,d,typ in f['pads']:
  dr=f'(drill oval {d[0]} {d[1]})'if isinstance(d,list)else f'(drill {d})';shape='oval'if isinstance(d,list)else'circle';s.append(f'(pad "{num}" {"np_thru_hole"if typ=="NPTH"else"thru_hole"} {shape} (at {x} {y}) (size {w} {h}) {dr} (layers "*.Cu" "*.Mask"))')
 s.append(')');(L/(name+'.kicad_mod')).write_text('\n'.join(s)+'\n')
(D/'footprint-dimensions.json').write_text(json.dumps(F,indent=2)+'\n')
proj=dict(board={'design_settings':{'rule_severities':{k:'error'for k in['missing_courtyard','track_not_centered_on_via','tuning_profile_track_geometries','footprint_filters_mismatch','footprint_type_mismatch']},'rules':{'min_clearance':.2,'min_track_width':.2,'min_via_diameter':.65,'min_through_hole_diameter':.3,'min_hole_to_hole':.25,'min_hole_clearance':.25,'min_copper_edge_clearance':.3}}},net_settings={'classes':[{'name':'Default','clearance':.2,'track_width':.24,'via_diameter':.7,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.24,'diff_pair_gap':.2,'diff_pair_via_gap':.25}]},meta={'filename':'base-rear-interface01.kicad_pro','version':1})
b=p.BOARD();b.SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(u(1.6));b.GetDesignSettings().m_TrackMinWidth=u(.2);b.GetDesignSettings().m_MinClearance=u(.2);b.SetFileName(str(K/'base-rear-interface01.kicad_pcb'))
for n in N['nets']:ni=p.NETINFO_ITEM(b,n);b.Add(ni);ni.thisown=False
fps={};meta=[]
for c in N['components']:
 fp=p.FootprintLoad(str(L),c['footprint']);fp.SetReference(c['ref']);fp.SetValue(c['value']);fp.SetFPIDAsString('BRI01:'+c['footprint']);fp.SetPosition(vec([c['u_mm'],c['v_mm']]));fp.SetOrientationDegrees(c['rotation_deg']);fp.SetPath(p.KIID_PATH('/'+M['root_uuid']+'/'+M['reference_uuids'][c['ref']]));fp.SetField('MPN',c['MPN']);fp.GetField('MPN').SetVisible(False);fp.SetField('Datasheet',c['source_url']);fp.GetField('Datasheet').SetVisible(False)
 for pd in fp.Pads():
  pn=next((x for x in N['pins']if x['ref']==c['ref']and x['pin']==pd.GetNumber()),None)
  if pn:pd.SetNet(b.FindNet(pn['net']));pd.SetPinFunction(pn['name']);pd.SetPinType(pn['role'])
 b.Add(fp);fp.thisown=False;fps[c['ref']]=fp
 f=F[c['footprint']];a=math.radians(-c['rotation_deg']);pts=[(c['u_mm']+x*math.cos(a)-y*math.sin(a),c['v_mm']+x*math.sin(a)+y*math.cos(a))for x in[f['body'][0],f['body'][2]]for y in[f['body'][1],f['body'][3]]];mi=[min(z[0]for z in pts),min(z[1]for z in pts),1.6];ma=[max(z[0]for z in pts),max(z[1]for z in pts),1.6+f['height']];meta.append(dict(ref=c['ref'],MPN=c['MPN'],origin_uv=[c['u_mm'],c['v_mm']],rotation_KiCad_deg=c['rotation_deg'],body_bbox_local=[mi,ma],basis='original catalogue envelope; spring maxheight budget forRJ; not supplier detailedBREP'))
for a,c in[([0,0],[116,0]),([116,0],[116,56]),([116,56],[0,56]),([0,56],[0,0])]:
 s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(vec(a));s.SetEnd(vec(c));s.SetLayer(p.Edge_Cuts);s.SetWidth(u(.05));b.Add(s);s.thisown=False
for c in N['components']:
 if c['footprint']!='M3':continue
 z=p.ZONE(b);z.SetIsRuleArea(True);z.SetLayerSet(p.LSET.AllCuMask());z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowZoneFills(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);o=z.Outline();o.NewOutline()
 for i in range(64):a=i*math.tau/64;o.Append(vec([c['u_mm']+3.5*math.cos(a),c['v_mm']+3.5*math.sin(a)]))
 b.Add(z);z.thisown=False
for layer in[p.In1_Cu,p.In2_Cu]:
 z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('CHASSIS'));z.SetLocalClearance(u(.3));z.SetPadConnection(p.ZONE_CONNECTION_FULL);o=z.Outline();o.NewOutline()
 for a in[[.5,.5],[73,.5],[73,55.5],[.5,55.5]]:o.Append(vec(a))
 b.Add(z);z.thisown=False
# Final copper is replayed by tools/replay_routing.py; this placed board is deliberately unrouted.
# Signal-free right-hand main-power region: wide dual-outer-layer short copper.
# Pin mapping deliberately identity, no bond toCHASSIS. Additional routing fills are added only after layout audit.
for txt,xy in[('BRI01 REVIEW',[57,24]),('ETHERCAT',[20,36]),('48V',[100,48]),('CHASSIS',[46,20]),('+ ARM',[101,20]),('RETURN',[85,20])]:
 t=p.PCB_TEXT(b);t.SetText(txt);t.SetPosition(vec(xy));t.SetLayer(p.F_SilkS);t.SetTextSize(vec([1,1]));t.SetTextThickness(u(.15));b.Add(t);t.thisown=False
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(K/'base-rear-interface01.kicad_pcb'),b)
(K/'base-rear-interface01.kicad_pro').write_text(json.dumps(proj,indent=2)+'\n')
(D/'placement-envelopes.json').write_text(json.dumps(dict(revision='BRI01',status='initial placed PCB; native routing/checks pending',transform='X=u-58;Y=z-27;Z=-9-v',board_size_mm=[116,56,1.6],components=meta,connector_contract='connector-contract.json',mount_holes_mm=[[6,6],[110,6],[110,50],[6,50]],bracket_holes_mm=[[48,38],[68,38]],not_mass_model=True),indent=2)+'\n')
print('placed',len(fps))
