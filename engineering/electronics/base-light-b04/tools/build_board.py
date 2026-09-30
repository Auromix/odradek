#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Native KiCad 10 PCB with explicit four-net routing and R3 mounting keepouts."""
from pathlib import Path
import json,math
import wx
app=wx.App(False)
import pcbnew as p
D=Path(__file__).resolve().parents[1];K=D/'kicad';L=K/'BL.pretty';L.mkdir(exist_ok=True)
N=json.loads((D/'netlist.json').read_text());M=json.loads((K/'schematic-build-map.json').read_text())
u=p.FromMM;vec=lambda a:p.VECTOR2I(u(a[0]),u(a[1]));xy=lambda uv:[uv[0],12-uv[1]];q=lambda s:json.dumps(str(s))
F={
'WE_150120AS75000':dict(layer='F',body=[-1.6,-.8,1.6,.8],courtyard=[-2.45,-1.1,2.45,1.1],pads=[['1',-1.5,0,1.4,1.6,0],['2',1.5,0,1.4,1.6,0]]),
'Wire4_Back':dict(layer='B',body=[-7.25,-1.5,7.25,1.5],courtyard=[-7.5,-1.75,7.5,1.75],pads=[[str(i+1),-6+i*4,0,2.5,3,0] for i in range(4)]),
'Mount_M2_R3':dict(layer='F',body=[-3,-3,3,3],courtyard=[-3,-3,3,3],pads=[['',0,0,2.2,2.2,2.2]])}
for name,f in F.items():
 layer=f['layer'];lo=f['body'];bb=f['courtyard'];lines=[f'(footprint {q(name)} (version 20240108) (generator "pcbnew") (layer "{layer}.Cu") (attr {"through_hole" if name.startswith("Mount") else "smd"})',f'(property "Reference" "REF**" (at 0 -2.5) (layer "{layer}.Fab") (effects (font (size .8 .8) (thickness .1))))',f'(property "Value" {q(name)} (at 0 2.5) (layer "{layer}.Fab") (effects (font (size .5 .5) (thickness .1))))',f'(fp_rect (start {lo[0]} {-lo[3]}) (end {lo[2]} {-lo[1]}) (stroke (width .1) (type default)) (fill none) (layer "{layer}.Fab"))']
 if name.startswith('Mount'):lines.append('(fp_circle (center 0 0) (end 3 0) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))')
 else:lines.append(f'(fp_rect (start {bb[0]} {-bb[3]}) (end {bb[2]} {-bb[1]}) (stroke (width .05) (type default)) (fill none) (layer "{layer}.CrtYd"))')
 for num,x,y,w,h,dr in f['pads']:
  layers='"*.Cu" "*.Mask"' if dr else f'"{layer}.Cu" "{layer}.Mask"'+(' "F.Paste"' if layer=='F' else '')
  lines.append(f'(pad {q(num)} {"np_thru_hole circle" if dr else "smd rect"} (at {x} {-y}) (size {w} {h}) '+(f'(drill {dr}) ' if dr else '')+f'(layers {layers}))')
 if name.startswith('WE_'):
  lines.append('(fp_line (start -2.5 -1.0) (end -2.5 1.0) (stroke (width .15) (type default)) (layer "F.SilkS"))')
  lines.append('(model "${KIPRJMOD}/../mechanical/led-envelope.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
 (L/(name+'.kicad_mod')).write_text('\n'.join(lines+[')'])+'\n')
proj={'board':{'design_settings':{'rule_severities':{'missing_courtyard':'error'},'rules':{'min_clearance':.25,'min_track_width':.25,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_hole_to_hole':.25,'min_hole_clearance':.25,'min_copper_edge_clearance':.3}}},'net_settings':{'classes':[{'name':'Default','clearance':.25,'track_width':.3,'via_diameter':.7,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.25,'diff_pair_gap':.25,'diff_pair_via_gap':.25}]},'meta':{'filename':'base-light-b04.kicad_pro','version':1}}
(K/'base-light-b04.kicad_pro').write_text(json.dumps(proj,indent=2)+'\n')
b=p.BOARD();b.SetCopperLayerCount(2);b.GetDesignSettings().SetBoardThickness(u(1.6));b.GetDesignSettings().m_TrackMinWidth=u(.25);b.GetDesignSettings().m_MinClearance=u(.25);b.SetFileName(str(K/'base-light-b04.kicad_pcb'))
for n in N['nets']:ni=p.NETINFO_ITEM(b,n);b.Add(ni);ni.thisown=False
for c in N['components']:
 ref=c['ref'];fp=p.FootprintLoad(str(L),c['footprint']);fp.SetReference(ref);fp.SetValue(c['value']);fp.SetFPIDAsString('BL:'+c['footprint']);fp.SetPosition(vec(xy([c['u_mm'],c['v_mm']])));fp.SetPath(p.KIID_PATH('/'+M['root_uuid']+'/'+M['reference_uuids'][ref]));fp.SetField('MPN',c['MPN']);fp.GetField('MPN').SetVisible(False);fp.SetField('Datasheet',c['source_url']);fp.GetField('Datasheet').SetVisible(False)
 for pd in fp.Pads():
  pn=next((v for v in N['pins'] if v['ref']==ref and v['pin']==pd.GetNumber()),None)
  if pn:pd.SetNet(b.FindNet(pn['net']));pd.SetPinFunction(pn['name']);pd.SetPinType('passive')
 if c['side']=='B':
  fp.Reference().SetMirrored(True);fp.Value().SetMirrored(True)
 b.Add(fp);fp.thisown=False
for a,c in [([0,0],[50,0]),([50,0],[50,12]),([50,12],[0,12]),([0,12],[0,0])]:
 s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(vec(a));s.SetEnd(vec(c));s.SetLayer(p.Edge_Cuts);s.SetWidth(u(.05));b.Add(s);s.thisown=False
# Circumscribed 96-gon encloses the full R3 forbidden copper disk. Pads and parts
# are independently checked analytically; NPTH mounting footprint is exempt.
for xx in [3,47]:
 z=p.ZONE(b);z.SetIsRuleArea(True);z.SetLayerSet(p.LSET.AllCuMask());z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowZoneFills(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);o=z.Outline();o.NewOutline()
 for i in range(96):t=2*math.pi*i/96;o.Append(vec(xy([xx+3/math.cos(math.pi/96)*math.cos(t),6+3/math.cos(math.pi/96)*math.sin(t)])))
 b.Add(z);z.thisown=False
routes=[]
def route(net,layer,points):
 for a,c in zip(points,points[1:]):
  t=p.PCB_TRACK(b);t.SetStart(vec(xy(a)));t.SetEnd(vec(xy(c)));t.SetWidth(u(.3));t.SetLayer(p.F_Cu if layer=='F' else p.B_Cu);t.SetNet(b.FindNet(net));b.Add(t);t.thisown=False
 routes.append(dict(net=net,layer=layer,uv_mm=points,width_mm=.3))
def via(net,uv):
 v=p.PCB_VIA(b);v.SetPosition(vec(xy(uv)));v.SetWidth(u(.7));v.SetDrill(u(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));b.Add(v);v.thisown=False
route('GND','B',[[19,2.5],[19,1],[8,1],[8,9]]);via('GND',[8,9])
route('GND','F',[[8,9],[35.5,9]])
for x in [11.5,23.5,35.5]:route('GND','F',[[x,9],[x,6]])
for net,pp,vu,path in [('LED_PWR_A',[14.5,6],[16,6],[[16,6],[16,4.8],[23,4.8],[23,2.5]]),('LED_RUN_A',[26.5,6],[28,6],[[28,6],[28,4.8],[27,3.8],[27,2.5]]),('LED_FAULT_A',[38.5,6],[40,6],[[40,6],[40,4.8],[31,4.8],[31,2.5]])]:
 route(net,'F',[pp,vu]);via(net,vu);route(net,'B',path)
for text,pos,sz in [('POWER',[13,10.5],.8),('RUN',[25,10.5],.8),('FAULT',[37,10.5],.8),('B04 LIGHT01',[10,2.7],.8)]:
 t=p.PCB_TEXT(b);t.SetText(text);t.SetPosition(vec(xy(pos)));t.SetTextSize(vec([sz,sz]));t.SetTextThickness(u(.12));t.SetLayer(p.F_SilkS);b.Add(t);t.thisown=False
# Back-view mirrored silkscreen pin numbers, placed inside the board boundary.
for i in range(4):
 t=p.PCB_TEXT(b);t.SetText(str(i+1));t.SetPosition(vec(xy([19+4*i,5])));t.SetTextSize(vec([.8,.8]));t.SetTextThickness(u(.12));t.SetLayer(p.B_SilkS);t.SetMirrored(True);b.Add(t);t.thisown=False
b.BuildConnectivity();p.SaveBoard(str(K/'base-light-b04.kicad_pcb'),b)
(D/'routing-plan.json').write_text(json.dumps(routes,indent=2)+'\n');(D/'footprint-dimensions.json').write_text(json.dumps(F,indent=2)+'\n')
print('routed',len(N['components']),'footprints / 4 nets')
