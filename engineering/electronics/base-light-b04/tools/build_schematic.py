#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import json,uuid
D=Path(__file__).resolve().parents[1];K=D/'kicad';N=json.loads((D/'netlist.json').read_text())
q=lambda s:json.dumps(str(s));uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/Auromix/odradek/BASE-LIGHT-B04/'+s))
def eff(sz=1,hide=False):return '(effects (font (size %g %g))%s)'%(sz,sz,' hide' if hide else '')
def prop(k,v,x,y,hidden=False):return f'(property {q(k)} {q(v)} (at {x} {y} 0) {eff(1,hidden)})'
lib=[];inst=[];wires=[];ids={};root=uid('root');name='base-light-b04'
pos={'J1':(55.88,66.04),'D1':(121.92,55.88),'D2':(121.92,91.44),'D3':(121.92,127),'H1':(55.88,121.92),'H2':(55.88,142.24)}
for c in N['components']:
 ref=c['ref'];pins=[p for p in N['pins'] if p['ref']==ref];px,py=pos[ref];sid=uid(ref);ids[ref]=sid;loc=[]
 for i,p in enumerate(pins):loc.append((p,-10.16,(len(pins)-1)*1.27-i*2.54,0))
 if ref.startswith('D'):loc=[(pins[0],-10.16,0,0),(pins[1],10.16,0,180)]
 body=f'(rectangle (start -7.62 6.35) (end 7.62 -6.35) (stroke (width .254) (type default)) (fill (type background)))'
 if ref.startswith('D'):body='(polyline (pts (xy 2.54 2.54) (xy 2.54 -2.54) (xy -2.54 0) (xy 2.54 2.54)) (stroke (width .254) (type default)) (fill (type none))) (polyline (pts (xy -2.54 2.54) (xy -2.54 -2.54)) (stroke (width .254) (type default)) (fill (type none))) (polyline (pts (xy -7.62 0) (xy -2.54 0)) (stroke (width .254) (type default)) (fill (type none))) (polyline (pts (xy 2.54 0) (xy 7.62 0)) (stroke (width .254) (type default)) (fill (type none)))'
 # Symbol pins carry explicit names and pin numbers; graphic is illustrative only.
 l=[f'(symbol "BL:{ref}" (pin_names (offset .762)) (in_bom yes) (on_board yes)',prop('Reference',ref,0,9),prop('Value',c['value'],0,-9),f'(symbol "{ref}_0_1" {body})',f'(symbol "{ref}_1_1"']
 for p,x,y,a in loc:l.append(f'(pin passive line (at {x} {y} {a}) (length 2.54) (name {q(p["name"])} {eff(.8)}) (number {q(p["pin"])} {eff(.85)}))')
 l+=[')',')'];lib.append('\n'.join(l))
 v=[f'(symbol (lib_id "BL:{ref}") (at {px} {py} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {sid})',prop('Reference',ref,px,py-11),prop('Value',c['value'],px,py-8),prop('Footprint','BL:'+c['footprint'],px,py,True),prop('Datasheet',c['source_url'],px,py,True),prop('MPN',c['MPN'],px,py,True)]
 for p,x,y,a in loc:
  v.append(f'(pin {q(p["pin"])} (uuid {uid(ref+"pin"+p["pin"])}))');xx=px+x;yy=py-y;ex=xx+(-3.81 if a==0 else 3.81)
  wires += [f'(wire (pts (xy {xx} {yy}) (xy {ex} {yy})) (stroke (width 0) (type default)) (uuid {uid(ref+"wire"+p["pin"])}))',f'(global_label {q(p["net"])} (shape passive) (at {ex} {yy} {a}) (effects (font (size .9 .9)) (justify {"right" if a==0 else "left"} bottom)) (uuid {uid(ref+"label"+p["pin"])}))']
 v.append(f'(instances (project {q(name)} (path "/{root}" (reference {q(ref)}) (unit 1)))))');inst.append('\n'.join(v))
texts=['BASE-LIGHT-B04-01 | 3 AMBER LEDs | 4 nets | 50x12mm','Connect ONLY to service B04 J3 (already resistor-limited).','J1: 1 GND, 2 POWER, 3 RUN, 4 FAULT. Back solder lands.','Each LED: pin1 K / pin2 A. No local resistor.','Low-current optical sample; no uniformity or safety indication claim.']
txt=[f'(text {q(t)} (at 20 {18+i*5} 0) (effects (font (size {1.5 if i==0 else 1.1} {1.5 if i==0 else 1.1})) (justify left)) (uuid {uid("title"+str(i))}))' for i,t in enumerate(texts)]
(K/(name+'.kicad_sch')).write_text('\n'.join(['(kicad_sch (version 20250114) (generator "eeschema")',f'(uuid {root}) (paper "A4")','(title_block (title "Front light module") (date "2026-09-30") (rev "B04-LIGHT01") (company "Auromix / CC-BY-NC-4.0"))','(lib_symbols',*lib,')',*txt,*wires,*inst,'(sheet_instances (path "/" (page "1")))',')']))
(K/'BL.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'+'\n'.join(s.replace('"BL:','"',1) for s in lib)+'\n)')
(K/'sym-lib-table').write_text('(sym_lib_table (lib (name "BL") (type "KiCad") (uri "${KIPRJMOD}/BL.kicad_sym") (options "") (descr "Original front light symbols")))\n')
(K/'fp-lib-table').write_text('(fp_lib_table (lib (name "BL") (type "KiCad") (uri "${KIPRJMOD}/BL.pretty") (options "") (descr "Original source-dimensioned footprints")))\n')
(K/'schematic-build-map.json').write_text(json.dumps(dict(root_uuid=root,reference_uuids=ids),indent=2)+'\n')
print('schematic ready')
