#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Independent native net, mount clearance, via-in-pad, and units audit."""
from pathlib import Path
import json,math,hashlib,xml.etree.ElementTree as E
D=Path(__file__).resolve().parent;K=D/'kicad';N=json.loads((D/'netlist.json').read_text());R=json.loads((D/'native-readback.json').read_text());M=json.loads((D/'mechanical-interface.json').read_text());C=json.loads((D/'calculation.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
drc=json.loads((K/'checks/drc.json').read_text());erc=json.loads((K/'checks/erc.json').read_text());counts={k:len(drc[k]) for k in ['violations','unconnected_items','schematic_parity','ignored_checks']};assert not any(counts.values()),counts;assert not erc['ignored_checks'];assert not sum(len(s['violations']) for s in erc['sheets'])
pr=json.loads((K/'base-b04.kicad_pro').read_text());assert not pr['board']['design_settings'].get('drc_exclusions');assert not pr.get('erc',{}).get('erc_exclusions')
xml=E.parse(K/'checks/base-b04.xml').getroot();xn={n.attrib['name']:sorted([v.attrib['ref'],v.attrib['pin']] for v in n.findall('node')) for n in xml.findall('nets/net')};en={k:sorted(v) for k,v in N['nets'].items()};assert xn==en
np={}
for p in R['pads']:
 if p['pin'] and p['net']:np.setdefault(p['net'],[]).append([p['ref'],p['pin']])
assert {k:sorted(v) for k,v in np.items()}==en
nc={c['ref']:c for c in N['components']}
for f in R['footprints']:assert f['MPN']==nc[f['ref']]['MPN'] and f['value']==nc[f['ref']]['value']
assert R['board_sha256']==sha(K/'base-b04.kicad_pcb')==M['native_board_sha256'];assert R['thickness_mm']==1.6
# Independent circle-to-rotated-pad and circle-to-axis-aligned-package audit of mounting keepouts.
def pad_dist(pt,p):
 a=math.radians(p['rotation_ccw_deg']);dx,dy=[pt[i]-p['uv_mm'][i] for i in range(2)];x=dx*math.cos(a)+dy*math.sin(a);y=-dx*math.sin(a)+dy*math.cos(a);return math.hypot(max(0,abs(x)-p['size_mm'][0]/2),max(0,abs(y)-p['size_mm'][1]/2))
mount=[]
for h in M['mount_holes_uv_mm']:
 pd=min(pad_dist(h,p) for p in R['pads'] if not p['ref'].startswith('H'));bd=min(math.hypot(*[max(c['body_bbox_board_min_mm'][i]-h[i],0,h[i]-c['body_bbox_board_max_mm'][i]) for i in range(2)]) for c in M['components']);assert min(pd,bd)>=3.5;mount.append(dict(hole_uv=h,minimum_nonmount_pad_to_axis_mm=pd,minimum_component_to_axis_mm=bd))
assert max(c['body_bbox_board_max_mm'][2] for c in M['components'])<=21.6
vip=[]
for v in R['vias']:
 hit=[p['ref']+'.'+p['pin'] for p in R['pads'] if p['type']=='SMD' and not p['ref'].startswith('TP') and pad_dist(v['uv_mm'],p)<v['drill_mm']/2]
 if hit:vip.append(dict(uv_mm=v['uv_mm'],drill_mm=v['drill_mm'],intersected_smd_pads=hit))
assert len(vip)==6 and all('U1.9' in v['intersected_smd_pads'] for v in vip)
# Independently compute from TI Eq15 in kOhm/kHz, and from inductor volt-seconds.
vout=1.2*(1+158000/49900);f_khz=vout*2500/41.2;period=1/(f_khz*1000);assert math.isclose(f_khz*1000,C['buck']['fsw_Hz'],rel_tol=1e-12)
checks=[]
for case in C['buck']['cases']:
 vin=case['Vin'];on=period*vout/vin;rise=(vin-vout)/68e-6*on;fall=vout/68e-6*(period-on);assert abs(rise-fall)<1e-12;assert math.isclose(rise,case['deltaIL_A'],rel_tol=1e-12);assert .1<rise<.3;assert 250<on*1e9<1000;checks.append(dict(Vin=vin,frequency_Hz=f_khz*1000,ton_ns=on*1e9,deltaIL_A=rise,peak_at025A_A=.25+rise/2))
assert C['buck']['CB_F']>C['buck']['CB_min_75us_F'];assert C['buck']['CA_F']>C['buck']['CA_min_F'];assert C['buck']['bootstrap_min_F']>1.5e-9 and C['buck']['bootstrap_max_F']<2.5e-9
q=dict(revision='B04-SERVICE01',stage='manufacturing review candidate; no powered prototype test',native_counts=counts,ERC_violations=0,ERC_ignored_checks=[],exclusions=[],actual_component_count=len(R['footprints']),purchased_board_part_count=len(M['components']),pin_net_count=len(N['pins']),nets=len(en),netlist_native_parity=True,mount_clearance_audit=mount,units_audit=checks,via_in_paste=vip,via_in_paste_process='6 thermal via holes must be resin-filled/copper-capped or a separately reviewed assembler process; no unapproved open-via stencil assembly',three_dimensional_hardware_model='mechanical/base-b04-assembly.step',board_sha256=sha(K/'base-b04.kicad_pcb'),input_power_limit_is_test_budget_not_hard_limit=True,prototype_powered=False,thermal_EMC_validated=False,manufacturing_release=False)
if (D/'mechanical/verification.json').exists():
 mj=json.loads((D/'mechanical/verification.json').read_text());assert mj['board_sha256']==q['board_sha256'];assert mj['board_solid_valid'];q['mechanical']=mj
q['artifact_sha256']={str(p.relative_to(D)):sha(p) for p in sorted(D.rglob('*')) if p.is_file() and p.name not in ['verification.json','cli-report.json'] and '__pycache__' not in p.parts and p.suffix not in ['.prl','.bak']}
(D/'verification.json').write_text(json.dumps(q,indent=2)+'\n');print('PASS: native nets, zero ERC/DRC, exact M3 keepouts, six thermal VIP and independent units audit')
