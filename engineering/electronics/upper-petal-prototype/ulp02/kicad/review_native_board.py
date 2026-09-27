# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Independent native-board source/placement and coarse resistance audit.
Run with KiCad bundled Python; reports are not a thermal qualification.
"""
import argparse,hashlib,json,math,collections
from pathlib import Path
import wx,pcbnew
app=wx.App(False)
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--board',default='upper-petal.kicad_pcb');a=p.parse_args()
b=pcbnew.LoadBoard(str(D/a.board));N=json.loads((D.parent/'netlist.json').read_text());C={x['ref']:x for x in N['components']};P={(x['ref'],x['pin']):x['net'] for x in N['pins']};M=json.loads((D/'handfanout-placement-map.json').read_text())['components']
issues=[];leds=[];pins=0
for fp in b.GetFootprints():
 r=fp.GetReference();c=C[r];pos=fp.GetPosition();actual=[pos.x/1e6,pos.y/1e6];expected=M[r]['board_xy_mm']
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
rho=1.724e-8;t_mm=.035
nets={};layers=collections.Counter();vias=0
for track in b.GetTracks():
 name=track.GetNetname();s=nets.setdefault(name,{'trace_length_mm':0.,'sum_trace_resistance_20C_35um_ohm':0.,'widths_mm':set(),'via_count':0})
 if isinstance(track,pcbnew.PCB_VIA):s['via_count']+=1;vias+=1;continue
 length=track.GetLength()/1e6;width=track.GetWidth()/1e6;s['trace_length_mm']+=length;s['widths_mm'].add(width);layers[b.GetLayerName(track.GetLayer())]+=1
 s['sum_trace_resistance_20C_35um_ohm']+=rho*(length*.001)/(width*.001*t_mm*.001)
for name,s in nets.items():
 s['widths_mm']=sorted(s['widths_mm']);imax=.28 if name.startswith('SW') or name=='VLED_3V3' else .02 if name.startswith('CS') else None
 if imax:
  s['assumed_peak_A']=imax;s['all_segment_series_drop_bound_V']=imax*s['sum_trace_resistance_20C_35um_ohm'];s['all_segment_series_loss_bound_W']=imax**2*s['sum_trace_resistance_20C_35um_ohm']
report={'status':'native KiCad board audit; not electrical or fabrication acceptance','board':a.board,'board_sha256':hashlib.sha256((D/a.board).read_bytes()).hexdigest(),'components':len(list(b.GetFootprints())),'pin_records':pins,'LED_count':len(leds),'issues':issues,'passed_source_placement_polarity_check':not issues,'LEDs':leds,'ground_zones':[{'net':z.GetNetname(),'layer':b.GetLayerName(z.GetLayer()),'filled_polygon_islands':z.GetFilledPolysList(z.GetLayer()).OutlineCount()} for z in b.Zones()],'routing':{'segment_count_by_layer':dict(layers),'via_count':vias,'net_statistics':nets},'resistance_model':{'copper_resistivity_20C_ohm_m':rho,'assumed_copper_thickness_mm':t_mm,'copper_thickness_status':'35um candidate only; no fabricator stackup agreed','meaning':'Sum of ALL segment resistances in a net gives a conservative trace-only series bound once KiCad proves connectivity; parallel branches reduce actual resistance. It is not a voltage-drop simulation. Via barrel/contact/pad/constriction/temperature effects omitted; zero-connectivity proof is separate.','GND':'Zone return impedance and ground bounce not modeled','thermal':'No temperature rise or LED thermal qualification inferred from this calculation'}}
(D/'checks'/'native-board-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'parts':report['components'],'pins':pins,'LEDs':len(leds),'issues':issues,'vias':vias,'segments':dict(layers)},indent=2))
