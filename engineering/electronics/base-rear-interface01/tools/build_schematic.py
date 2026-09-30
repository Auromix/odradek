#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import json,uuid,math
D=Path(__file__).resolve().parents[1];K=D/'kicad';N=json.loads((D/'netlist.json').read_text())
q=lambda s:json.dumps(str(s));uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/Auromix/odradek/BRI01/'+s))
def eff(sz=1,h=False):return '(effects (font (size %g %g))%s)'%(sz,sz,' hide'if h else'')
def prop(k,v,x,y,h=False):return f'(property {q(k)} {q(v)} (at {x} {y} 0) {eff(1,h)})'
lib=[];inst=[];wires=[];ids={};root=uid('root');name='base-rear-interface01'
for j,c in enumerate(N['components']):
 ref=c['ref'];pins=[p for p in N['pins']if p['ref']==ref];px=round((48+j%3*94)/1.27)*1.27;py=round((45+j//3*36)/1.27)*1.27;nh=math.ceil(len(pins)/2);top=max(3.81,(nh+1)*1.27);loc=[];sid=uid(ref);ids[ref]=sid
 for i,p in enumerate(pins):
  il=i<nh;idx=i if il else i-nh;loc.append((p,-10.16 if il else 10.16,((nh-1)/2-idx)*2.54,0 if il else 180))
 s=[f'(symbol "BRI01:{ref}" (pin_names (offset .762)) (in_bom yes) (on_board yes)',prop('Reference',ref,0,top+2.54),prop('Value',c['value'],0,-top-2.54),f'(symbol "{ref}_0_1" (rectangle (start -7.62 {top}) (end 7.62 {-top}) (stroke (width .254) (type default)) (fill (type background))))',f'(symbol "{ref}_1_1"']
 for p,x,y,a in loc:s.append(f'(pin passive line (at {x} {y} {a}) (length 2.54) (name {q(p["name"])} {eff(.8)}) (number {q(p["pin"])} {eff(.85)}))')
 s+=[')',')'];lib.append('\n'.join(s));v=[f'(symbol (lib_id "BRI01:{ref}") (at {px} {py} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {sid})',prop('Reference',ref,px,py-top-4.2),prop('Value',c['value'],px,py-top-2.1),prop('Footprint','BRI01:'+c['footprint'],px,py,True),prop('Datasheet',c['source_url'],px,py,True),prop('MPN',c['MPN'],px,py,True)]
 for p,x,y,a in loc:
  v.append(f'(pin {q(p["pin"])} (uuid {uid(ref+p["pin"])}))');xx=px+x;yy=py-y;ex=xx+(-3.81 if a==0 else 3.81)
  wires +=[f'(wire (pts (xy {xx} {yy}) (xy {ex} {yy})) (stroke (width 0) (type default)) (uuid {uid(ref+"w"+p["pin"])}))',f'(global_label {q(p["net"])} (shape bidirectional) (at {ex} {yy} {0 if a==0 else 180}) (effects (font (size .9 .9)) (justify {"right"if a==0 else"left"} bottom)) (uuid {uid(ref+"l"+p["pin"])}))']
 v.append(f'(instances (project "{name}" (path "/{root}" (reference "{ref}") (unit 1)))))');inst.append('\n'.join(v))
texts=[]
for j,t in enumerate(['BRI01 | passive EtherCAT + 48V interface | CC-BY-NC-4.0','J1 -> J2 pin1..8 identity; SHIELD -> J6 CHASSIS; no PHY/magnetics/PoE','J3 -> J4/J5 48V/RETURN; 10A test target, not qualified rating','X1/X2 are true50ohm coax adapters on shared bracket; NOT PCB signal nets']):texts.append(f'(text {q(t)} (at 12 {15+j*4} 0) (effects (font (size {1.6 if j==0 else 1.1} {1.6 if j==0 else 1.1})) (justify left)) (uuid {uid("t"+str(j))}))')
(K/(name+'.kicad_sch')).write_text('\n'.join(['(kicad_sch (version 20250114) (generator "eeschema")',f'(uuid {root}) (paper "A4")','(title_block (title "BRI01 base physical interface candidate") (date "2026-09-30") (rev "BRI01") (company "Auromix / CC-BY-NC-4.0"))','(lib_symbols',*lib,')',*texts,*wires,*inst,'(sheet_instances (path "/" (page "1")))',')']))
(K/'BRI01.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'+'\n'.join(s.replace('"BRI01:','"',1)for s in lib)+'\n)')
(K/'sym-lib-table').write_text('(sym_lib_table (lib (name "BRI01") (type "KiCad") (uri "${KIPRJMOD}/BRI01.kicad_sym") (options "") (descr "Original symbols")))')
(K/'fp-lib-table').write_text('(fp_lib_table (lib (name "BRI01") (type "KiCad") (uri "${KIPRJMOD}/BRI01.pretty") (options "") (descr "Original dimensional footprints")))')
(K/'schematic-build-map.json').write_text(json.dumps(dict(root_uuid=root,reference_uuids=ids),indent=2)+'\n')
