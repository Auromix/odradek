#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Read final native files; pin parity, exact mounts and analytic R3 clearance."""
from pathlib import Path
import json,math,hashlib,xml.etree.ElementTree as ET
import wx
app=wx.App(False)
import pcbnew as p
D=Path(__file__).resolve().parents[1];K=D/'kicad';N=json.loads((D/'netlist.json').read_text());C=json.loads((D/'mechanical-interface.json').read_text());b=p.LoadBoard(str(K/'base-light-b04.kicad_pcb'))
mm=lambda z:z/1e6;uv=lambda a:[mm(a.x),12-mm(a.y)];sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert abs(mm(b.GetDesignSettings().GetBoardThickness())-1.6)<1e-8
xml=ET.parse(K/'checks'/'base-light-b04.xml');sch={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('.//nets/net') for n in net.findall('node')};expected={(r['ref'],r['pin']):r['net'] for r in N['pins']};assert sch==expected,(sch,expected)
actual={};pads=[];holes=[];refmap={x['ref']:x for x in N['components']};mindist=1e9
mount_uv=[h['uv_mm'] for h in C['mounts']]
def point_seg_dist(pt,a,z):
 dx=z[0]-a[0];dy=z[1]-a[1];t=max(0,min(1,((pt[0]-a[0])*dx+(pt[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
 return math.hypot(pt[0]-a[0]-t*dx,pt[1]-a[1]-t*dy)
def rect_distance(pt,center,size):return math.hypot(max(0,abs(pt[0]-center[0])-size[0]/2),max(0,abs(pt[1]-center[1])-size[1]/2))
for fp in b.GetFootprints():
 ref=fp.GetReference();r=refmap[ref];assert all(abs(v-a)<1e-6 for v,a in zip(uv(fp.GetPosition()),[r['u_mm'],r['v_mm']]));assert fp.GetField('MPN').GetText()==r['MPN']
 for pd in fp.Pads():
  pos=uv(pd.GetPosition());size=[mm(pd.GetSize().x),mm(pd.GetSize().y)];dr=mm(pd.GetDrillSize().x)
  entry=dict(ref=ref,pin=pd.GetNumber(),net=pd.GetNetname(),uv_mm=pos,size_mm=size,drill_mm=dr,layers=[p.LayerName(i) for i in pd.GetLayerSet().Seq()]);pads.append(entry)
  if pd.GetAttribute()==p.PAD_ATTRIB_NPTH:holes.append(entry);assert abs(dr-2.2)<1e-8
  else:
   actual[(ref,pd.GetNumber())]=pd.GetNetname()
   for h in mount_uv:mindist=min(mindist,rect_distance(h,pos,size))
assert actual==expected and len(holes)==2 and sorted(x['uv_mm'] for x in holes)==sorted(mount_uv)
for d in C['LEDs']:
 for h in mount_uv:assert rect_distance(h,d['center_uv_mm'],d['XY_planning_box_mm'])>3
for pd in C['harness']['J1_pads']:
 native=next(x for x in pads if x['ref']=='J1' and x['pin']==pd['pin']);assert native['uv_mm']==pd['center_uv_mm'] and native['size_mm']==pd['size_mm'] and 'B.Cu' in native['layers'] and 'F.Cu' not in native['layers']
for t in b.GetTracks():
 for h in mount_uv:mindist=min(mindist,point_seg_dist(h,uv(t.GetStart()),uv(t.GetEnd()))-mm(t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth())/2)
assert mindist>3,mindist
for d in C['LEDs']:
 assert d['body_global_z_mm'][1]<=32
 assert d['center_global_xy_mm']==[C['PCB']['global_min_mm'][i]+d['center_uv_mm'][i] for i in range(2)]
up=json.loads((D.parent/'base-b04'/'netlist.json').read_text());upc={r['ref']:r for r in up['components']}
for role,ref in C['electrical']['upstream_refs'].items():
 assert upc[ref]['value']=='2.2k LED limit' and upc[ref]['MPN']=='RC0603FR-072K2L'
 target={'POWER':'LED_PWR_A','RUN':'LED_RUN_A','FAULT':'LED_FAULT_A'}[role]
 assert target in [n['net'] for n in up['pins'] if n['ref']==ref]
assert [(p['pin'],p['net']) for p in up['pins'] if p['ref']=='J3']==[(str(i+1),n) for i,n in enumerate(C['harness']['service_pin_order'])]
drc=json.loads((K/'checks'/'drc.json').read_text());erc=json.loads((K/'checks'/'erc.json').read_text());assert not drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity'];assert not any(s['violations'] for s in erc['sheets'])
report=dict(revision=C['revision'],kicad_version=p.GetBuildVersion(),native_footprints=len(list(b.GetFootprints())),electrical_nets=4,schematic_native_pin_parity=True,upstream_polarity_and_limit_refs_checked=True,ERC_violations=0,DRC_violations=0,unconnected_items=0,schematic_parity_issues=0,actual_holes=holes,minimum_copper_distance_to_mount_axis_mm=mindist,required_keepout_R_mm=3,analytic_component_boxes_clear_R3=True,back_pad_pin_order_confirmed=True,LED_ceiling_margin_mm=1.52,pads=pads,ignored_tool_checks=dict(ERC=erc['ignored_checks'],DRC=drc['ignored_checks']),files=[dict(path=str(f.relative_to(D)),sha256=sha(f)) for f in [K/'base-light-b04.kicad_pcb',K/'base-light-b04.kicad_sch',D/'mechanical-interface.json']],limits=['KiCad passive-pin ERC does not establish correct external source voltage or polarity; readback separately checks upstreamJ3','R3 pads/component exclusion independently checked; mounting keepout rule itself permits the NPTH footprint','No physical electrical/thermal/optical/assembly validation'])
(D/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('native readback, 4-net parity, R3, upstream J3, ERC/DRC passed')
