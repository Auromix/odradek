# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Generate native PCB/library candidate, un-routed. All LED coordinates preserved.
The companion check script must compare the KiCad netlist and run ERC/DRC.
"""
import json,math,uuid
from pathlib import Path
OUT=Path(__file__).resolve().parent;SRC=OUT.parent
N=json.loads((SRC/'netlist.json').read_text());F=json.loads((SRC/'footprint-constraints.json').read_text());B=json.loads((SRC/'mechanical-power-budget.json').read_text())
M=json.loads((OUT/'schematic-build-map.json').read_text())
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/Auromix/odradek/ULP-02/pcb/'+s))
def q(s):return json.dumps(str(s))
def fmt(v):return f'{float(v):.5f}'.rstrip('0').rstrip('.') if v else '0'
netnums={net:i+1 for i,net in enumerate(sorted(N['nets']))};netpins={(p['ref'],p['pin']):p['net'] for p in N['pins']}
footprints={}
for name,fp in F.items():
 if name not in ['TI_RKP0040B','WE_150060YS75000','C0603','C0805','R0603','NTC0603','JST_GH_10_TOP']:continue
 pads=fp.get('pads') or fp.get('candidate_pads')
 if name=='NTC0603':pads=[{'pad':1,'xy_mm':[-.725,0],'size_mm':[.65,.7]},{'pad':2,'xy_mm':[.725,0],'size_mm':[.65,.7]}]
 body={'TI_RKP0040B':[5,5],'WE_150060YS75000':[1.6,.8],'C0603':[1.6,.8],'C0805':[2,1.25],'R0603':[1.6,.85],'NTC0603':[1.6,.8],'JST_GH_10_TOP':[15.75,4.25]}[name]
 footprints[name]={'pads':pads,'body':body}
(OUT/'ULP.pretty').mkdir(exist_ok=True)
def rect(a,b,layer,w=.05):return f'(fp_rect (start {fmt(a[0])} {fmt(a[1])}) (end {fmt(b[0])} {fmt(b[1])}) (stroke (width {w}) (type default)) (fill none) (layer {q(layer)}))'
def makefp(name,ref='REF**',part='',side='F',center=None,rot=0):
 fp=footprints[name];pads=fp['pads'];layer=side+'.Cu';front=side=='F'
 # Input dimensions: mounting-side X-right/Y-up. Native footprint uses Y-down.
 # Backside projection mirrors X, then rotates about footprint origin.
 def local(a):
  x,y=a;x=x if front else -x;y=-y
  t=math.radians(rot);return [x*math.cos(t)-y*math.sin(t),x*math.sin(t)+y*math.cos(t)]
 s=[f'(footprint {q("ULP:"+name if center else name)} (version 20240108) (generator "odradek_ulp_generator") (layer {q(layer)})']
 if center:s.extend([f'(at {fmt(center[0])} {fmt(center[1])})',f'(uuid {uid(ref)})',f'(path {q(M["reference_uuids"][ref])})'])
 s.extend(['(attr smd)',f'(property "Reference" {q(ref)} (at 0 -3 0) (layer {q(side+".Fab")}) (effects (font (size .8 .8) (thickness .12))'+(' (justify mirror)' if not front else '')+'))',f'(property "Value" {q(part or name)} (at 0 3 0) (layer {q(side+".Fab")}) (effects (font (size .65 .65) (thickness .1))'+(' (justify mirror)' if not front else '')+'))'])
 allrect=[]
 for p in pads:
  num=str(p['pad']);x,y=local(p['xy_mm']);w,h=p['size_mm'];
  if abs(rot)%180==90:w,h=h,w
  net=netpins.get((ref,num));nt=f' (net {netnums[net]} {q(net)})' if net else ''
  allrect.extend([(x-w/2,y-h/2),(x+w/2,y+h/2)])
  # Rounded corners are a fabrication candidate, not a library datum change.
  paste='' if name=='TI_RKP0040B' and num=='41' else q(side+'.Paste')
  s.append(f'(pad {q(num)} smd roundrect (at {fmt(x)} {fmt(y)}) (size {fmt(w)} {fmt(h)}) (layers {q(layer)} {paste} {q(side+".Mask")}) (roundrect_rratio .2){nt})')
 if name=='TI_RKP0040B':
  # Four paste-only windows: 55.2% nominal area, assembler review required.
  for x0 in [-.8,.8]:
   for y0 in [-.8,.8]:
    x,y=local([x0,y0]);s.append(f'(pad "" smd rect (at {fmt(x)} {fmt(y)}) (size 1.3 1.3) (layers {q(side+".Paste")}))')
 bw,bh=fp['body'];p0=local([-bw/2,-bh/2]);p1=local([bw/2,bh/2]);s.append(rect(p0,p1,side+'.Fab',.1))
 xmin=min(x for x,y in allrect)-.25;xmax=max(x for x,y in allrect)+.25;ymin=min(y for x,y in allrect)-.25;ymax=max(y for x,y in allrect)+.25
 s.append(rect([xmin,ymin],[xmax,ymax],side+'.CrtYd'))
 # Unique pin-1 polarity mark outside solder mask, essential for 113 LEDs.
 if name=='TI_RKP0040B':
  x,y=local([-3.2,2.8]);s.append(f'(fp_circle (center {fmt(x)} {fmt(y)}) (end {fmt(x+.15)} {fmt(y)}) (stroke (width .12) (type default)) (fill none) (layer {q(side+".SilkS")}))')
 if name=='WE_150060YS75000':s.append('(fp_line (start -1.45 -.55) (end -1.45 .55) (stroke (width .12) (type default)) (layer "F.SilkS"))')
 s.append(')');return '\n'.join(s)
for name in footprints:(OUT/'ULP.pretty'/(name+'.kicad_mod')).write_text(makefp(name)+'\n')
lines=['(kicad_pcb (version 20240108) (generator "odradek_ulp_generator")','(general (thickness .8))','(paper "A4")','(layers (0 "F.Cu" signal) (1 "In1.Cu" signal) (2 "In2.Cu" signal) (31 "B.Cu" signal) (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive") (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments") (44 "Edge.Cuts" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard") (48 "B.Fab" user) (49 "F.Fab" user))','(setup (pad_to_mask_clearance 0))','(net 0 "")']
lines += [f'(net {num} {q(net)})' for net,num in netnums.items()]
component_locations={}
for c in N['components']:
 ref=c['ref'];x=c['x_mm'];y=c['y_mm'];
 if ref=='C9':x=79 # avoid R9/cap land overlap; LED coordinates remain invariant.
 if ref=='C5':x=47.5 # leave separation from U1 courtyard.
 if ref=='R8':x=72.8 # leave separation from R9 courtyard.
 side=c['side'];rot=90 if ref=='J1' else 0;center=[x,40-y]
 component_locations[ref]={'x_mm':x,'source_y_mm':y,'board_xy_mm':center,'side':side,'projection_rotation_deg':rot}
 lines.append(makefp(c['footprint'],ref,c['manufacturer_part_number'],side,center,rot))
poly=B['board_outline_reference_mm'];boardpoly=[[x,40-y] for x,y in poly]
for a,b in zip(boardpoly,boardpoly[1:]+boardpoly[:1]):lines.append(f'(gr_line (start {fmt(a[0])} {fmt(a[1])}) (end {fmt(b[0])} {fmt(b[1])}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))')
lines.append('(gr_text "HLIO-R03 ELECTRICAL COUPON / NOT ARM RELEASE" (at 76 63) (layer "Dwgs.User") (effects (font (size 1 1) (thickness .15))))')
# Exposed-pad thermal vias: candidate only; tent/fill policy must be agreed with assembler.
for dx in [-.8,.8]:
 for dy in [-1.1,1.1]:lines.append(f'(via (at {43+dx} {40+dy}) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {netnums["GND"]}))')
lines.append(')');(OUT/'upper-petal-unrouted.kicad_pcb').write_text('\n'.join(lines)+'\n')
proj={'board':{'design_settings':{'rules':{'min_clearance':.15,'min_track_width':.15,'min_via_diameter':.5,'min_through_hole_diameter':.25,'min_hole_to_hole':.25,'min_copper_edge_clearance':.25}}},'net_settings':{'classes':[{'name':'Default','clearance':.15,'track_width':.2,'via_diameter':.6,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.2,'diff_pair_gap':.25,'diff_pair_via_gap':.25}]},'meta':{'filename':'upper-petal.kicad_pro','version':1}}
(OUT/'upper-petal.kicad_pro').write_text(json.dumps(proj,indent=2)+'\n')
(OUT/'upper-petal-unrouted.kicad_pro').write_text(json.dumps(proj,indent=2)+'\n')
(OUT/'placement-map.json').write_text(json.dumps({'status':'unrouted PCB candidate; no mechanical integration release','board_y_formula':'Y_board=40-y_source; x unchanged; mounting-side component pads mirrored for backside','back_component_adjustments':{'C9':'x78 to79 to separate land envelopes from R9','C5':'x47 to47.5, U1 courtyard separation','R8':'x73 to72.8, R9 courtyard separation'},'no_LED_coordinate_changes':True,'components':component_locations},indent=2)+'\n')
print('Generated native unrouted PCB,',len(component_locations),'components; source LED coordinates unchanged')
