# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Create reviewable native KiCad schematic from CD-EC01 pin-level input.
Routing and KiCad checks are separate stages; generated files are not released.
"""
import json, math, uuid
from pathlib import Path
import sys
OUT=Path(sys.argv[1]).resolve()
SRC=OUT.parent
NET=json.loads((SRC/'netlist.json').read_text())
FP=json.loads((SRC/'footprint-constraints.json').read_text())

PROJECT='central'
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/Auromix/odradek/CD-EC01/'+s))
def q(s):return json.dumps(str(s),ensure_ascii=False)
def f(x):return f'{float(x):.5f}'.rstrip('0').rstrip('.') if x else '0'
def prop(key,value,x,y,hide=False):
 return f'(property {q(key)} {q(value)} (at {f(x)} {f(y)} 0) (effects (font (size 1.0 1.0))'+(' hide' if hide else '')+'))'
def eff(size=1.,justify=''):
 return f'(effects (font (size {size} {size}))'+(f' (justify {justify})' if justify else '')+')'
def text(s,x,y,size=1.5):
 return f'(text {q(s)} (at {f(x)} {f(y)} 0) {eff(size,"left")} (uuid {uid("text"+s)}))'
ROOT=uid('root');lib=[];placed=[];wires=[]
byref={c['ref']:c for c in NET['components']}
pinmap={r:[p for p in NET['pins'] if p['ref']==r] for r in byref}
positions={}

def symbol(c,px,py,kind):
 px=round(px/1.27)*1.27;py=round(py/1.27)*1.27
 ref=c['ref'];name=ref if kind in ['U','J'] else kind
 libid='CD:'+name
 pins=pinmap[ref];locations=[]
 if kind in ['U','J']:
  nhalf=21 if kind=='U' else 7;halfw=15.24 if kind=='U' else 8.89;step=2.54
  for i,p in enumerate(pins):
   left=i<nhalf;j=i if left else i-nhalf
   lx=-(halfw+2.54) if left else halfw+2.54;ly=((nhalf-1)/2-j)*step
   locations.append((p,lx,ly,0 if left else 180))
  top=nhalf*step/2;bot=-top
  graphic=f'(rectangle (start {-halfw} {top}) (end {halfw} {bot}) (stroke (width .254) (type default)) (fill (type background)))'
 else:
  locations=[(pins[0],-5.08,0,0),(pins[1],5.08,0,180)]
  if kind=='D':
   graphic='(polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27) (xy -1.27 0) (xy 1.27 1.27)) (stroke (width .254) (type default)) (fill (type none))) (polyline (pts (xy -1.27 -1.27) (xy -1.27 1.27)) (stroke (width .254) (type default)) (fill (type none)))'
  elif kind=='C':
   graphic='(polyline (pts (xy -.635 -1.27) (xy -.635 1.27)) (stroke (width .254) (type default)) (fill (type none))) (polyline (pts (xy .635 -1.27) (xy .635 1.27)) (stroke (width .254) (type default)) (fill (type none)))'
  else:
   graphic='(rectangle (start -2.54 -1.016) (end 2.54 1.016) (stroke (width .254) (type default)) (fill (type none)))'
  top=3
 if libid not in [v[0] for v in lib]:
  block=[f'(symbol {q(libid)} (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',prop('Reference',kind,0,top+2.54),prop('Value',name,0,-top-2.54),f'(symbol {q(name+"_0_1")} {graphic})',f'(symbol {q(name+"_1_1")}']
  for p,lx,ly,ang in locations:
   role=p['electrical_role']; role='power_out' if p['pin_name']=='VCAP' else role
   # MISO is tri-state. Other connector pins remain physically passive.
   if p['pin_name']=='ADDR0_MISO':role='tri_state'
   length=2.54 if kind in ['U','J'] else (3.81 if kind=='D' else 4.445 if kind=='C' else 2.54)
   block.append(f'(pin {role} line (at {f(lx)} {f(ly)} {ang}) (length {f(length)}) (name {q(p["pin_name"])} {eff(.85)}) (number {q(p["pin"])} {eff(.85)}))')
  block.extend([')',')']);lib.append((libid,'\n'.join(block)))
 sid=uid('sym'+ref);positions[ref]=sid
 visible_value=c['value'] if kind not in ['U','J','D'] else ('LP5860RKPR' if kind=='U' else 'GH12 SIDE + fixed tabs' if kind=='J' else '590 nm')
 topoffset=top+5.08 if kind in ['U','J'] else 3.81
 inst=[f'(symbol (lib_id {q(libid)}) (at {f(px)} {f(py)} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {sid})',prop('Reference',ref,px,py-topoffset),prop('Value',visible_value,px,py-topoffset+1.7),prop('Footprint','',px,py,True),prop('CandidateFootprint','CD:'+c['footprint'],px,py,True),prop('Datasheet',c['source_url'],px,py,True),prop('MPN',c['manufacturer_part_number'],px,py,True)]
 for p,lx,ly,ang in locations:
  inst.append(f'(pin {q(p["pin"])} (uuid {uid(ref+"pin"+p["pin"])}))')
  x=px+lx;y=py-ly;extend=-15.24 if ang==0 else 12.7;ex=x+extend
  if p['net'] is None:wires.append(f'(no_connect (at {f(x)} {f(y)}) (uuid {uid("nc"+ref+p["pin"])}))');continue
  wires.append(f'(wire (pts (xy {f(x)} {f(y)}) (xy {f(ex)} {f(y)})) (stroke (width 0.1524) (type default)) (uuid {uid("wire"+ref+p["pin"])}))')
  # Global-label anchors are separated from symbols to keep long net names clear.
  angle=180 if ang==0 else 0
  wires.append(f'(global_label {q(p["net"])} (shape bidirectional) (at {f(ex)} {f(y)} {angle}) {eff(.95,"right" if ang==0 else "left")} (uuid {uid("label"+ref+p["pin"])}))')
 inst.append(f'(instances (project {q(PROJECT)} (path {q("/"+ROOT)} (reference {q(ref)}) (unit 1))))');inst.append(')');placed.append('\n'.join(inst))

symbol(byref['U1'],75,67,'U');symbol(byref['U2'],240,67,'U');symbol(byref['J1'],405,63,'J')
others=[c for c in NET['components'] if c['ref'] not in ['U1','U2','J1'] and not c['ref'].startswith('D')]
for i,c in enumerate(others):symbol(c,550+(i%4)*120,43+(i//4)*20,'TH' if c['ref'].startswith('TH') else c['ref'][0])
for c in NET['components']:
 if c['ref'].startswith('D'):
  p=next(p for p in pinmap[c['ref']] if p['pin']=='2');g=p['net'][0];sw=int(p['net'].split('_SW')[1]);cs=int(next(p['net'].split('_CS')[1] for p in pinmap[c['ref']] if p['pin']=='1'))
  symbol(c,40+cs*75,(255 if g=='A' else 530)+sw*20,'D')
# Explicit external-supply flags mark the bench supply contract, not an on-board source.
flag='CD:PWR_FLAG'
lib.append((flag,'(symbol "CD:PWR_FLAG" (power) (pin_names (offset 0)) (in_bom no) (on_board no) '+prop('Reference','#FLG',0,2,True)+prop('Value','PWR_FLAG',0,-2,True)+' (symbol "PWR_FLAG_0_1" (polyline (pts (xy -1 1) (xy 0 2) (xy 1 1) (xy 0 0) (xy -1 1)) (stroke (width .254) (type default)) (fill (type none)))) (symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))'))
for i,net in enumerate(['GND','LED_POWER4','3V3_LOGIC','LED_VIO']):
 ref=f'#FLG0{i+1}';x=round((30+i*35)/1.27)*1.27;y=round(123/1.27)*1.27
 placed.append(f'(symbol (lib_id {q(flag)}) (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (uuid {uid(ref)}) {prop("Reference",ref,x,y,True)} {prop("Value","PWR_FLAG",x,y,True)} (pin "1" (uuid {uid(ref+"pin")})) (instances (project {q(PROJECT)} (path {q("/"+ROOT)} (reference {q(ref)}) (unit 1)))))')
 wires.append(f'(global_label {q(net)} (shape bidirectional) (at {x} {y} 0) {eff(.95,"left")} (uuid {uid("flaglabel"+net)}))')
content=['(kicad_sch (version 20231120) (generator "odradek_cd01_generator")',f'(uuid {ROOT}) (paper "{"A0"}")','(title_block (title "CD-EC01 central LED schematic candidate") (date "2026-09-27") (rev "CD-EC01") (company "Auromix contributors / CC-BY-NC-4.0") (comment 1 "Candidate. Catalogue connector geometry; solder and thermal validation pending."))','(lib_symbols',*[v[1] for v in lib],')',text('CD-EC01 / 285 discrete LEDs / two LP5860 / GH12 / schematic only',20,15,2),text('External 3.3V supplies; VIO_EN is IO supply + enable. Host outputs low/high-Z before VIO off.',20,22,1.5),text('Power flags describe external supplies through J1; no power conversion on this board.',20,136,1.3),text('11 scan rows fixed / 13 sinks fitted / 3mA first light / 20mA conditional / no PCB or fabrication data',20,144,1.4),text('A / U1 / 142 pixels / pin7 = CS_A',20,231,2),text('B / U2 / 143 pixels / pin11 = CS_B',20,506,2),*wires,*placed,f'(sheet_instances (path "/" (page "1")))',')']
(OUT/(PROJECT+'.kicad_sch')).write_text('\n'.join(content)+'\n')
(OUT/'CD.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "odradek_cd01_generator")\n'+'\n'.join(v[1].replace('"CD:', '"',1) for v in lib)+'\n)\n')
(OUT/'sym-lib-table').write_text('(sym_lib_table (lib (name "CD") (type "KiCad") (uri "${KIPRJMOD}/CD.kicad_sym") (options "") (descr "Project symbols")))\n')
(OUT/'central.kicad_pro').write_text(json.dumps({'meta':{'filename':'central.kicad_pro','version':1}},indent=2)+'\n')
(OUT/'schematic-build-map.json').write_text(json.dumps({'root_uuid':ROOT,'reference_uuids':positions,'status':'generated source map; actual validation results live in checks/verification.json'},indent=2)+'\n')
print('Generated native schematic',len(placed),'symbols including 4 external-power flags')
