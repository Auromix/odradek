#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Native coordinates, net assignment, copper continuity and via/solder-land audit."""
from pathlib import Path
from collections import Counter,defaultdict
import wx,pcbnew,sys,json,math,hashlib
app=wx.App(False);D=Path(sys.argv[1]).resolve();S=D.parent;P=S.parent
b=pcbnew.LoadBoard(str(D/'central.kicad_pcb'));n=json.loads((S/'netlist.json').read_text());cc={c['ref']:c for c in n['components']};pn={(p['ref'],p['pin']):p['net'] for p in n['pins']};issues=[];actual=[];gh=[]
for fp in b.GetFootprints():
 ref=fp.GetReference();c=cc[ref];p=fp.GetPosition();xy=[p.x/1e6-40,40-p.y/1e6];side='B' if fp.IsFlipped() else 'F';pads=[]
 if math.dist(xy,[c['x_mm'],c['y_mm']])>1.01e-6 or side!=c['side']:issues.append(dict(ref=ref,placement=xy,side=side))
 native_projection=(180-fp.GetOrientationDegrees())%360 if side=='B' else (-fp.GetOrientationDegrees())%360
 if abs((native_projection-c.get('projection_rotation_deg',0)+180)%360-180)>1e-7:issues.append(dict(ref=ref,actual_projection_rotation=native_projection,expected_projection_rotation=c.get('projection_rotation_deg',0)))
 for pd in fp.Pads():
  num=pd.GetNumber()
  if not num:continue
  pos=pd.GetPosition();net=pd.GetNetname();exp=pn[ref,num]
  if (exp and net!=exp) or (not exp and not net.startswith('unconnected-')):issues.append(dict(ref=ref,pin=num,net=net,expected=exp))
  pads.append(dict(pin=num,head_xy_mm=[pos.x/1e6-40,40-pos.y/1e6],net=net))
 actual.append(dict(ref=ref,head_xy_mm=xy,side=side,rotation_deg=fp.GetOrientationDegrees(),pads=pads))
 if ref=='J1':
  expected=json.loads((P/'mechanical-packing.json').read_text())['connector']['pad_centers_head_mm']
  for pp in pads:
   e=next(x for x in expected if str(x['pad'])==pp['pin']);delta=math.dist(pp['head_xy_mm'],e['center_head_mm'][:2]);gh.append(dict(pin=pp['pin'],delta_mm=delta,head_xy_mm=pp['head_xy_mm']))
   if delta>1.01e-6:issues.append(gh[-1])
layers=Counter();vias=[];via_solder=[];stats={};pads=[(f.GetReference(),p) for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()]
for t in b.GetTracks():
 name=t.GetNetname();d=stats.setdefault(name,dict(length_mm=0.,widths_mm=set(),trace_only_Rsum_20C_ohm=0.,vias=0))
 if isinstance(t,pcbnew.PCB_VIA):
  p=t.GetPosition();d['vias']+=1;entry=dict(uuid=t.m_Uuid.AsString(),head_xy_mm=[p.x/1e6-40,40-p.y/1e6],diameter_mm=t.GetWidth(pcbnew.F_Cu)/1e6,drill_mm=t.GetDrillValue()/1e6,net=name);vias.append(entry)
  overlaps=[]
  for ref,pd in pads:
   if pcbnew.SHAPE.Collide(t.GetEffectiveShape(pd.GetLayer()),pd.GetEffectiveShape(pd.GetLayer()),0):overlaps.append(dict(ref=ref,pin=pd.GetNumber()))
  if overlaps:
   for o in overlaps:
    pd=next(pd for ref,pd in pads if ref==o['ref'] and pd.GetNumber()==o['pin']);drill=pcbnew.SHAPE_CIRCLE(t.GetPosition(),int(t.GetDrillValue()/2));o['drill_intersects_copper_land']=pcbnew.SHAPE.Collide(drill,pd.GetEffectiveShape(pd.GetLayer()),0);o['drill_intersects_mask_opening']=pcbnew.SHAPE.Collide(drill,pd.GetEffectiveShape(pd.GetLayer()),pcbnew.FromMM(.05))
   via_solder.append(dict(entry,overlaps=overlaps))
 else:
  length=t.GetLength()/1e6;width=t.GetWidth()/1e6;copper_mm=.035 if t.GetLayer() in [pcbnew.F_Cu,pcbnew.B_Cu] else .0175;layers[b.GetLayerName(t.GetLayer())]+=1;d['length_mm']+=length;d['widths_mm'].add(width);d['trace_only_Rsum_20C_ohm']+=1.724e-8*length*.001/(width*.001*copper_mm*.001)
for name,s in stats.items():
 s['widths_mm']=sorted(s['widths_mm']);current=.52 if name=='LED_POWER4' else .26 if '_SW' in name else .02 if '_CS' in name else None
 if current:s.update(assumed_peak_A=current,all_segments_in_series_trace_bound_V=s['trace_only_Rsum_20C_ohm']*current)
zones=[dict(net=z.GetNetname(),layer=b.GetLayerName(z.GetLayer()),islands=z.GetFilledPolysList(z.GetLayer()).OutlineCount()) for z in b.Zones() if not z.GetIsRuleArea()];ground=[z for z in zones if z['layer']=='In2.Cu' and z['net']=='GND'];plane_ok=len(ground)==1 and ground[0]['islands']==1 and layers.get('In2.Cu',0)==0
if not plane_ok:issues.append(dict(ground_reference_unproven=ground))
# Real footprint pads and package source nominal max-body union, not just centre radius.
mechanical=[]
for fp in b.GetFootprints():
 ref=fp.GetReference();c=cc[ref];p=fp.GetPosition();x,y=p.x/1e6-40,40-p.y/1e6
 if ref=='J1':lo=[-9.225,-19.55];hi=[9.225,-11.3];depth=4.45 # .10mm solder allowance beyond catalogue reference height
 else:
  w,h,depth={'TI_RKP0040B':(5.4,5.4,1.1),'WE_150060YS75000':(2.4,.9,.9),'C0603':(2.2,1,1.05),'C0805':(2.9,1.45,1.55),'R0603':(2.5,.95,.65),'NTC0603':(2.1,.95,1.05)}[c['footprint']];margin=.25 if c['side']=='B' else 0
  if c.get('projection_rotation_deg',0)%180==90:w,h=h,w
  lo=[x-w/2-margin,y-h/2-margin];hi=[x+w/2+margin,y+h/2+margin]
 rmax=max(math.hypot(xx,yy) for xx in [lo[0],hi[0]] for yy in [lo[1],hi[1]]);limit=28 if c['side']=='B' else 28.5
 if rmax>limit+1e-6:issues.append(dict(ref=ref,radial_envelope_mm=rmax,limit=limit))
 mechanical.append(dict(ref=ref,head_xy_mm=[x,y],side=c['side'],min_xy_mm=lo,max_xy_mm=hi,max_radius_mm=rmax,head_z_mm=[-3-depth,-3] if c['side']=='B' else [-2,-2+depth]))
report=dict(revision='CD-PCB01',board_sha256=hashlib.sha256((D/'central.kicad_pcb').read_bytes()).hexdigest(),components=len(actual),pin_count=sum(len(a['pads']) for a in actual),LED_count=sum(a['ref'].startswith('D') for a in actual),placement_and_net_issues=issues,GH12_native_pad_transform=gh,component_placement=actual,mechanical_envelopes=mechanical,routing=dict(segment_counts_by_layer=dict(layers),via_count=len(vias),net_statistics=stats),ground_zones=zones,continuous_ground_reference_geometry=plane_ok,via_solder_land_overlaps=via_solder,via_note='All LED lands deliberately excluded from new via placement; exact readback determines compliance. Any overlap needs deliberate solder-wicking/paste/fill-cap review; all through vias are candidates until actual process agreed.',resistance_model='35um outer /17.5um inner nominal copper,20C; sum ALL net segments in series is conservative trace-only bound after connectivity passes, not a network simulation. Excludes vias, pads, junctions, ground return, contact/wire/temperature. No temperature-rise qualification.',fabrication_release=False,hardware_tested=False)
(D/'checks/native-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(parts=len(actual),issues=issues,ground_ok=plane_ok,via_count=len(vias),via_solder_overlap_count=len(via_solder)),indent=2))

# MCAD contract derives every pose from native readback; no mirrored left-hand PCB.
body_sources=json.loads((S/'package-body-dimensions.json').read_text())
mc=[]
for a in actual:
 if a['side']!='B':continue
 c=cc[a['ref']];r=math.radians((180-a['rotation_deg'])%360);en=next(e for e in mechanical if e['ref']==a['ref'])
 matrix=[[-math.cos(r),math.sin(r),0],[math.sin(r),math.cos(r),0],[0,0,-1]]
 mc.append(dict(ref=a['ref'],manufacturer_part_number=c['manufacturer_part_number'],footprint=c['footprint'],origin_head_mm=[*a['head_xy_mm'],-3],mount_uvh_to_head_rotation=matrix,projection_rotation_deg=c.get('projection_rotation_deg',0),native_board_rotation_deg=a['rotation_deg'],envelope_head_min_mm=[*en['min_xy_mm'],en['head_z_mm'][0]],envelope_head_max_mm=[*en['max_xy_mm'],en['head_z_mm'][1]],radial_corner_mm=en['max_radius_mm'],height_from_board_including_0p1_solder_allowance_mm=-3-en['head_z_mm'][0],basis='Conservative max-body/land union plus0.25mm XY assembly allowance, except GH exact catalogue mated union; catalogue reference/dimension tolerance not controlled',source_url=c['source_url']))
# Keep package material-space and PCB land / assembly planning envelopes distinct.
for item in mc:
 key=item['manufacturer_part_number']
 if key.startswith('CRCW0603'):key='CRCW0603*FKEA'
 spec=body_sources['entries'][key]
 is_gh=item['ref']=='J1'
 if is_gh:
  lo=spec['reference_local_min_uvh_mm'][:];hi=spec['reference_local_max_uvh_mm'][:]
 else:
  u,v,h=spec['max_dimensions_uvh_mm'];lo=[-u/2,-v/2,0];hi=[u/2,v/2,h]
 # A 0.10 mm solder seating allowance shifts the package away from PCB only in h.
 lo[2]+=.1;hi[2]+=.1
 corners=[]
 for u in [lo[0],hi[0]]:
  for v in [lo[1],hi[1]]:
   for h in [lo[2],hi[2]]:
    corners.append([round(item['origin_head_mm'][i]+sum(item['mount_uvh_to_head_rotation'][i][j]*[u,v,h][j] for j in range(3)),9) for i in range(3)])
 body=dict(kind='catalogue_mated_reference_box' if is_gh else 'published_package_maximum_box',local_min_uvh_mm=lo,local_max_uvh_mm=hi,dimensions_uvh_mm=spec.get('max_dimensions_uvh_mm',spec.get('reference_dimensions_uvh_mm')),head_min_mm=[min(p[i] for p in corners) for i in range(3)],head_max_mm=[max(p[i] for p in corners) for i in range(3)],head_corners_mm=corners,solder_height_translation_h_mm=.1,xy_assembly_allowance_mm=0,includes_PCB_copper_lands=False,includes_courtyard=False,not_vendor_BREP=True,source_key=key,source_url=spec['source_url'],source_locator=spec['source_locator'],source_status=spec['source_status'])
 item['max_body']=None if is_gh else body
 item['mated_reference']=body if is_gh else None
 item['mcad_material_envelope']=body
 item['planning_envelope']=dict(head_min_mm=item['envelope_head_min_mm'],head_max_mm=item['envelope_head_max_mm'],basis=item['basis'],material_solid=False,includes_PCB_lands_and_XY_assembly_margin=True)
 item['legacy_envelope_fields_mean']='planning_envelope only; do not use as actual package material. Use max_body, or mated_reference for GH.'
body_overlaps=[]
for i,a in enumerate(mc):
 for bitem in mc[i+1:]:
  aa=a['mcad_material_envelope'];bb=bitem['mcad_material_envelope'];intersection=[min(aa['head_max_mm'][j],bb['head_max_mm'][j])-max(aa['head_min_mm'][j],bb['head_min_mm'][j]) for j in range(3)]
  if min(intersection)>1e-8:body_overlaps.append(dict(refs=[a['ref'],bitem['ref']],intersection_xyz_mm=intersection))
contract=dict(revision='CD-PCB01',board_sha256=report['board_sha256'],coordinates='head frame. Native PCB XY=(40+headX,40-headY). PCB bottom Z=-3,topZ=-2.',PCB=dict(diameter_mm=60,thickness_mm=1,head_z_mm=[-3,-2]),components_back=mc,package_dimensions_source='package-body-dimensions.json',package_dimensions_sha256=hashlib.sha256((S/'package-body-dimensions.json').read_bytes()).hexdigest(),mcad_body_bbox_overlaps=body_overlaps,body_geometry_semantics='Package maximum/reference boxes only; transform includes actual native pose, no XY allowance, and 0.10 mm solder translation in h. Planning envelopes are NOT material solids. GH remains reference-only. Mounted solder menisci/PCB lands not modelled as package volumes.',front_LED=dict(count=285,head_z_mm=[-2,-1.1],land_union_max_mm=[2.4,.9],body_max_mm=[1.7,.9,.8],solder_height_planning_mm=.1,pixel_map='../pixel-map.csv'),thermal_regions=[dict(center_head_xy_mm=[x,15],size_mm=[4,4],net='GND',status='bare B copper reservation; no engineered heat strap or thermal-performance claim') for x in [-10,10]],native_mounts=[],mount_status='CD-MOUNT01 mechanical support contract remains separate. No added screw holes.',unknowns=['GH controlled tolerances and actual mated CAD','solder height distribution','board thickness and bow','heat-bridge material/clamp load','wire/latch/unmate envelope','physical part/assembly mass'],not_vendor_BREP=True,fabrication_release=False)
(S/'mechanical-interface.json').write_text(json.dumps(contract,indent=2)+'\n')
import csv
with (S/'component-positions.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['ref','MPN','side','head_x_mm','head_y_mm','mount_z_mm','projection_rotation_deg','native_rotation_deg','status'])
 for a in sorted(actual,key=lambda a:a['ref']):
  c=cc[a['ref']];w.writerow([a['ref'],c['manufacturer_part_number'],a['side'],*a['head_xy_mm'],-3 if a['side']=='B' else -2,c.get('projection_rotation_deg',0),a['rotation_deg'],'candidate-not-fabrication-release'])
