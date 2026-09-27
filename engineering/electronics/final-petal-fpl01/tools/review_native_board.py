# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Independent native-board source/placement and coarse resistance audit.
Run with KiCad bundled Python; reports are not a thermal qualification.
"""
import argparse,hashlib,json,math,collections
from pathlib import Path
import wx,pcbnew
app=wx.App(False)
import sys
D=Path(sys.argv.pop(1)).resolve()
p=argparse.ArgumentParser();p.add_argument('--board',default='petal.kicad_pcb');a=p.parse_args()
b=pcbnew.LoadBoard(str(D/a.board));N=json.loads((D.parent/'netlist.json').read_text());C={x['ref']:x for x in N['components']};P={(x['ref'],x['pin']):x['net'] for x in N['pins']};M=json.loads((D/'placement-map.json').read_text())['components']
issues=[];leds=[];pins=0
for fp in b.GetFootprints():
 r=fp.GetReference()
 if r.startswith('MH'):continue
 c=C[r];pos=fp.GetPosition();actual=[pos.x/1e6,pos.y/1e6];expected=M[r]['board_xy_mm']
 if math.dist(actual,expected)>1e-6:issues.append({'ref':r,'position':actual,'expected':expected})
 side='B' if fp.IsFlipped() else 'F'
 if side!=c['side']:issues.append({'ref':r,'side':side,'expected':c['side']})
 if r.startswith('D'):
  if math.dist(actual,[c['x_mm'],40-c['y_mm']])>1e-6:issues.append({'ref':r,'LED_source_coordinates_changed':True})
  pads={p.GetNumber():p for p in fp.Pads() if p.GetNumber()}
  leds.append({'ref':r,'xy_mm':actual,'cathode_pin':'1','anode_pin':'2','cathode_net':pads['1'].GetNetname(),'anode_net':pads['2'].GetNetname()})
 for pd in fp.Pads():
  number=pd.GetNumber()
  if not number:continue
  pins+=1;expectednet=P[(r,number)];actualnet=pd.GetNetname()
  if expectednet is None:
   if not actualnet.startswith('unconnected-'):issues.append({'ref':r,'pin':number,'expected_nc':True,'actual':actualnet})
  elif actualnet!=expectednet:issues.append({'ref':r,'pin':number,'expected':expectednet,'actual':actualnet})
interface=json.loads((D.parent.parent/'mechanical-interface-candidate.json').read_text())
connector=next(fp for fp in b.GetFootprints() if fp.GetReference()=='J1');expectedGH={str(p['pad']):p['mechanical_xy_mm'] for p in interface['projected_pads']};gh=[]
for pd in connector.Pads():
 num=pd.GetNumber();p=pd.GetPosition();xy=[p.x/1e6,40-p.y/1e6]
 delta=math.dist(xy,expectedGH[num]);gh.append({'pin':num,'mechanical_xy_mm':xy,'expected':expectedGH[num],'delta_mm':delta})
 if delta>1e-6:issues.append({'GH_pin':num,'delta_mm':delta})
mounts=[]
for fp in b.GetFootprints():
 if not fp.GetReference().startswith('MH'):continue
 for pd in fp.Pads():mounts.append({'ref':fp.GetReference(),'drill_mm':pd.GetDrillSize().x/1e6,'xy_mm':[pd.GetPosition().x/1e6,40-pd.GetPosition().y/1e6],'attribute':pd.GetAttribute()})
assert len(mounts)==3 and all(abs(p['drill_mm']-2.4)<1e-6 for p in mounts)
rho=1.724e-8;t_mm=.035
nets={};layers=collections.Counter();vias=0
for track in b.GetTracks():
 name=track.GetNetname();s=nets.setdefault(name,{'trace_length_mm':0.,'sum_trace_resistance_20C_35um_ohm':0.,'widths_mm':set(),'via_count':0})
 if isinstance(track,pcbnew.PCB_VIA):s['via_count']+=1;vias+=1;continue
 length=track.GetLength()/1e6;width=track.GetWidth()/1e6;s['trace_length_mm']+=length;s['widths_mm'].add(width);layers[b.GetLayerName(track.GetLayer())]+=1
 s['sum_trace_resistance_20C_35um_ohm']+=rho*(length*.001)/(width*.001*t_mm*.001)
for name,s in nets.items():
 s['widths_mm']=sorted(s['widths_mm']);imax=json.loads((D.parent/'mechanical-power-budget.json').read_text())['I_LED_peak_A_at20mA'] if name.startswith('SW') or name=='VLED_3V3' else .02 if name.startswith('CS') else None
 if imax:
  s['assumed_peak_A']=imax;s['all_segment_series_drop_bound_V']=imax*s['sum_trace_resistance_20C_35um_ohm'];s['all_segment_series_loss_bound_W']=imax**2*s['sum_trace_resistance_20C_35um_ohm']
report={'status':'native KiCad board audit; not electrical or fabrication acceptance','board':a.board,'board_sha256':hashlib.sha256((D/a.board).read_bytes()).hexdigest(),'components':len(list(b.GetFootprints())),'pin_records':pins,'LED_count':len(leds),'issues':issues,'passed_source_placement_polarity_check':not issues,'LEDs':leds,'ground_zones':[{'net':z.GetNetname(),'layer':b.GetLayerName(z.GetLayer()),'filled_polygon_islands':z.GetFilledPolysList(z.GetLayer()).OutlineCount()} for z in b.Zones() if not z.GetIsRuleArea()],'routing':{'segment_count_by_layer':dict(layers),'via_count':vias,'net_statistics':nets},'resistance_model':{'copper_resistivity_20C_ohm_m':rho,'assumed_copper_thickness_mm':t_mm,'copper_thickness_status':'35um candidate only; no fabricator stackup agreed','meaning':'Sum of ALL segment resistances in a net gives a conservative trace-only series bound once KiCad proves connectivity; parallel branches reduce actual resistance. It is not a voltage-drop simulation. Via barrel/contact/pad/constriction/temperature effects omitted; zero-connectivity proof is separate.','GND':'Zone return impedance and ground bounce not modeled','thermal':'No temperature rise or LED thermal qualification inferred from this calculation'}}
report['GH_projection_check']=gh;report['mount_NPTH']=mounts;report['component_count_excluding_mounts']=len(C)
# Mechanical outline/mount envelope and reserved heat-bridge audit use actual native pads.
poly=json.loads((D.parent/'mechanical-power-budget.json').read_text())['board_outline_reference_mm'];poly=[[x,40-y] for x,y in poly]
area=sum(a[0]*z[1]-z[0]*a[1] for a,z in zip(poly,poly[1:]+poly[:1]));sign=1 if area>0 else -1
bridge=[62,43,66,47];mechanical=[];bridge_items=[]
for fp in b.GetFootprints():
 ref=fp.GetReference()
 if ref.startswith('MH'):continue
 c=C[ref];r=math.radians(c.get('projection_rotation_deg',0));cx,cy=fp.GetPosition().x/1e6,fp.GetPosition().y/1e6
 sizes={'TI_RKP0040B':[5,5],'WE_150060YS75000':[1.7,.9],'C0603':[1.8,1.0],'C0805':[2.2,1.45],'R0603':[1.7,.95],'NTC0603':[1.75,.95]}
 if ref=='J1':box=[42.525,40-7.875,46.575,40+7.875]
 else:
  w,h=sizes[c['footprint']]
  if abs(c.get('projection_rotation_deg',0))%180==90:w,h=h,w
  box=[cx-w/2,cy-h/2,cx+w/2,cy+h/2]
 for pd in fp.Pads():
  if not pd.GetNumber():continue
  bb=pcbnew.SHAPE.BBox(pd.GetEffectiveShape(pd.GetLayer()));box=[min(box[0],bb.GetLeft()/1e6),min(box[1],bb.GetTop()/1e6),max(box[2],bb.GetRight()/1e6),max(box[3],bb.GetBottom()/1e6)]
 box=[box[0]-.25,box[1]-.25,box[2]+.25,box[3]+.25]
 clearance=min(sign*((z[0]-a[0])*(q[1]-a[1])-(z[1]-a[1])*(q[0]-a[0]))/math.dist(a,z) for q in [(box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3])] for a,z in zip(poly,poly[1:]+poly[:1]))
 holeclear=min(math.hypot(max(box[0]-p['xy_mm'][0],0,p['xy_mm'][0]-box[2]),max(box[1]-(40-p['xy_mm'][1]),0,(40-p['xy_mm'][1])-box[3]))-3.25 for p in mounts)
 mechanical.append({'ref':ref,'body_land_plus_025mm_box_board_mm':box,'min_outline_halfspace_clearance_mm':clearance,'min_mount_keepout_clearance_mm':holeclear})
 if clearance<-1e-6 or holeclear<-1e-6:issues.append({'ref':ref,'mechanical_envelope_clearance_mm':[clearance,holeclear]})
 if fp.IsFlipped() and not(box[2]<=bridge[0] or box[0]>=bridge[2] or box[3]<=bridge[1] or box[1]>=bridge[3]):bridge_items.append({'ref':ref,'kind':'back-component-envelope'})
bridge_shape=pcbnew.SHAPE_RECT(pcbnew.VECTOR2I(pcbnew.FromMM(62),pcbnew.FromMM(43)),pcbnew.FromMM(4),pcbnew.FromMM(4))
via_paste=[];allpads=[(f.GetReference(),p) for f in b.GetFootprints() for p in f.Pads() if p.GetNumber() and p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD]
for tr in b.GetTracks():
 if isinstance(tr,pcbnew.PCB_VIA):
  if pcbnew.SHAPE.Collide(tr.GetEffectiveShape(pcbnew.B_Cu),bridge_shape,0):bridge_items.append({'kind':'via','uuid':tr.m_Uuid.AsString()})
  overlap=[]
  for ref,pd in allpads:
   if pcbnew.SHAPE.Collide(tr.GetEffectiveShape(pd.GetLayer()),pd.GetEffectiveShape(pd.GetLayer()),0):overlap.append({'ref':ref,'pin':pd.GetNumber(),'net':pd.GetNetname()})
  if overlap:via_paste.append({'uuid':tr.m_Uuid.AsString(),'xy_mm':[tr.GetPosition().x/1e6,tr.GetPosition().y/1e6],'drill_mm':tr.GetDrillValue()/1e6,'overlaps':overlap})
 elif tr.GetLayer()==pcbnew.B_Cu and tr.GetNetname()!='GND' and pcbnew.SHAPE.Collide(tr.GetEffectiveShape(),bridge_shape,0):bridge_items.append({'kind':'back-signal','uuid':tr.m_Uuid.AsString()})
if bridge_items:issues.append({'heat_bridge_intrusions':bridge_items})
report['mechanical_envelopes']=mechanical;report['heat_bridge_reserve']={'board_xy_mm':bridge,'intrusions':bridge_items,'mechanical_reference_xy_mm':[[62,-7],[66,-3]],'TIM_or_pedestal_design_complete':False}
report['via_in_solder_land']=via_paste;report['via_in_solder_land_requirement']='These vias intersect solder lands: resin fill and copper cap / planarization process must be agreed and qualified with fabricator and assembler; ordinary open through-vias are not acceptable production substitution. Four QFN exposed-pad vias also require stencil qualification.'
ground_reference=[z for z in report['ground_zones'] if z['layer']=='In2.Cu' and z['net']=='GND']
if len(ground_reference)!=1 or ground_reference[0]['filled_polygon_islands']!=1:issues.append({'continuous_ground_reference_not_proven':ground_reference})
if layers.get('In2.Cu',0):issues.append({'signal_or_track_on_reserved_GND_layer':layers['In2.Cu']})
report['ground_reference_check']={'layer':'In2.Cu','single_filled_island_required':True,'non_zone_tracks_permitted':False,'passed':len(ground_reference)==1 and ground_reference[0]['filled_polygon_islands']==1 and not layers.get('In2.Cu',0),'boundary':'Connected copper island is a geometric test, not high-frequency return-path or ground-bounce qualification.'}
refs={f.GetReference():f for f in b.GetFootprints()}
def padxy(ref,pin):
 p=next(p for p in refs[ref].Pads() if p.GetNumber()==pin).GetPosition();return [p.x/1e6,p.y/1e6]
pa,pz=padxy('U1','16'),padxy('C3','1');leads=[]
for tr in b.GetTracks():
 if isinstance(tr,pcbnew.PCB_VIA) or tr.GetNetname()!='VLED_3V3':continue
 a,z=tr.GetStart(),tr.GetEnd();a=[a.x/1e6,a.y/1e6];z=[z.x/1e6,z.y/1e6]
 if (math.dist(a,pa)<1e-6 and math.dist(z,pz)<1e-6) or (math.dist(z,pa)<1e-6 and math.dist(a,pz)<1e-6):leads.append({'length_mm':tr.GetLength()/1e6,'width_mm':tr.GetWidth()/1e6,'layer':b.GetLayerName(tr.GetLayer())})
report['decoupling_layout_boundary']={'U1_VLED_pad_board_xy_mm':pa,'C3_VLED_pad_board_xy_mm':pz,'pad_centre_distance_mm':math.dist(pa,pz),'direct_unsplit_lead_segments':leads,'measurement':'Native pad and segment coordinates. Split branches may divide this segment without changing its copper. No package ESL, capacitor impedance, trace inductance or switching transient has been measured.','qualification_required':'Scope VLED/VCC/VCAP at IC under maximum changing image; current limited 3mA first light precedes 20mA tests.'}
report['issues']=issues;report['passed_source_placement_polarity_check']=not issues

(D/'checks'/'native-board-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'parts':report['components'],'pins':pins,'LEDs':len(leds),'issues':issues,'vias':vias,'segments':dict(layers)},indent=2))
