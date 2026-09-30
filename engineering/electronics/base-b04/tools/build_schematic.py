#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
import json,uuid,math
from pathlib import Path
D=Path(__file__).resolve().parents[1];K=D/'kicad';N=json.loads((D/'netlist.json').read_text())
q=lambda s:json.dumps(str(s));uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/Auromix/odradek/B04/'+s))
def eff(sz=1,hide=False):return '(effects (font (size %g %g))%s)'%(sz,sz,' hide' if hide else '')
def prop(k,v,x,y,hidden=False):return f'(property {q(k)} {q(v)} (at {x} {y} 0) {eff(1,hidden)})'
lib=[];inst=[];wires=[];ids={};root=uid('root');name='base-b04'
for j,c in enumerate(N['components']):
 ref=c['ref'];pins=[p for p in N['pins'] if p['ref']==ref];px=round((52+(j%6)*94)/1.27)*1.27;py=round((52+(j//6)*41)/1.27)*1.27
 nh=math.ceil(len(pins)/2);top=max(3.81,(nh+1)*1.27);left=7.62;loc=[];sid=uid(ref);ids[ref]=sid
 for i,p in enumerate(pins):
  isleft=i<nh;idx=i if isleft else i-nh;loc.append((p,-10.16 if isleft else 10.16,((nh-1)/2-idx)*2.54,0 if isleft else 180))
 l=[f'(symbol "B04:{ref}" (pin_names (offset .762)) (in_bom yes) (on_board yes)',prop('Reference',ref,0,top+2.54),prop('Value',c['value'],0,-top-2.54),f'(symbol "{ref}_0_1" (rectangle (start {-left} {top}) (end {left} {-top}) (stroke (width .254) (type default)) (fill (type background))))',f'(symbol "{ref}_1_1"']
 for p,x,y,a in loc:l.append(f'(pin {p["role"]} line (at {x} {y} {a}) (length 2.54) (name {q(p["name"])} {eff(.8)}) (number {q(p["pin"])} {eff(.85)}))')
 l.extend([')',')']);lib.append('\n'.join(l))
 v=[f'(symbol (lib_id "B04:{ref}") (at {px} {py} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {sid})',prop('Reference',ref,px,py-top-4.2),prop('Value',c['value'],px,py-top-2.1),prop('Footprint','B04:'+c['footprint'],px,py,True),prop('Datasheet',c['source_url'],px,py,True),prop('MPN',c['MPN'],px,py,True)]
 for p,x,y,a in loc:
  v.append(f'(pin {q(p["pin"])} (uuid {uid(ref+"pin"+p["pin"])}))');xx=px+x;yy=py-y;ex=xx+(-3.81 if a==0 else 3.81)
  wires += [f'(wire (pts (xy {xx} {yy}) (xy {ex} {yy})) (stroke (width 0) (type default)) (uuid {uid(ref+"wire"+p["pin"])}))',f'(global_label {q(p["net"])} (shape bidirectional) (at {ex} {yy} {0 if a==0 else 180}) (effects (font (size .9 .9)) (justify {"right" if a==0 else "left"} bottom)) (uuid {uid(ref+"label"+p["pin"])}))']
 v.append(f'(instances (project {q(name)} (path "/{root}" (reference {q(ref)}) (unit 1)))))');inst.append('\n'.join(v))
lib.append('(symbol "B04:PWR_FLAG" (power) (pin_names (offset 0)) (in_bom no) (on_board no) '+prop('Reference','#FLG',0,0,True)+prop('Value','PWR_FLAG',0,0,True)+' (symbol "PWR_FLAG_0_1" (polyline (pts (xy 0 0) (xy -1 1) (xy 0 2) (xy 1 1) (xy 0 0)) (stroke (width .2) (type default)) (fill (type none)))) (symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0) (name "PWR" '+eff()+') (number "1" '+eff()+'))))')
for j,n in enumerate(['GND','VIN_PROT','BST']):
 x=round((25+j*45)/1.27)*1.27;y=round(389/1.27)*1.27;ref='#FLG'+str(j+1)
 inst.append(f'(symbol (lib_id "B04:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (uuid {uid(ref)}) {prop("Reference",ref,x,y,True)} {prop("Value","PWR_FLAG",x,y,True)} (pin "1" (uuid {uid(ref+"p")})) (instances (project {q(name)} (path "/{root}" (reference {q(ref)}) (unit 1)))))')
 wires.append(f'(global_label {q(n)} (shape bidirectional) (at {x} {y} 0) {eff()} (uuid {uid(ref+"l")}))')
text=[]
for j,t in enumerate(['B04 SERVICE01 | 48V low-power branch + two isolated 24V status inputs | CC-BY-NC-4.0','20..55V / input target <=2W / 5V bench load <=0.25A / J3 bare LEDs only','No motor-power path; no EtherCAT/GMSL traces; no safety stop logic. POWER=local5V, not verified zero-energy.']):text.append(f'(text {q(t)} (at 15 {14+j*5} 0) (effects (font (size {1.8 if j==0 else 1.3} {1.8 if j==0 else 1.3})) (justify left)) (uuid {uid("title"+str(j))}))')
text.append(f'(text "PWR_FLAG: external return, protected VIN; BST has internal diode bias through C3. No extra external supply." (at 15 398 0) (effects (font (size 1.1 1.1)) (justify left)) (uuid {uid("flag-note")}))')
(K/'base-b04.kicad_sch').write_text('\n'.join(['(kicad_sch (version 20250114) (generator "eeschema")',f'(uuid {root}) (paper "A2")','(title_block (title "B04 base service board") (date "2026-09-30") (rev "B04-SERVICE01") (company "Auromix / CC-BY-NC-4.0"))','(lib_symbols',*lib,')',*text,*wires,*inst,'(sheet_instances (path "/" (page "1")))',')']))
(K/'B04.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'+'\n'.join(s.replace('"B04:','"',1) for s in lib)+'\n)')
(K/'sym-lib-table').write_text('(sym_lib_table (lib (name "B04") (type "KiCad") (uri "${KIPRJMOD}/B04.kicad_sym") (options "") (descr "B04 original pin-exact symbols")))\n')
(K/'fp-lib-table').write_text('(fp_lib_table (lib (name "B04") (type "KiCad") (uri "${KIPRJMOD}/B04.pretty") (options "") (descr "B04 original dimensional footprints")))\n')
(K/'schematic-build-map.json').write_text(json.dumps(dict(root_uuid=root,reference_uuids=ids),indent=2)+'\n')
print('schematic generated',len(inst))
