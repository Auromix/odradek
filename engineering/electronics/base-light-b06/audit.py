# SPDX-License-Identifier: CC-BY-NC-4.0
"""Read actual native manufacturing outputs; check pin map and hole coordinates."""
import csv,hashlib,json,re,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;M=HERE/'manufacturing'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
nets=json.loads((HERE/'pin-nets.json').read_text())
native=json.loads((M/'netlist.enet').read_text())
actual={c['props']['Designator']:{n:p['net'] for n,p in c['pinInfoMap'].items()} for c in native['components'].values()}
assert actual==nets,(actual,nets)
rows=list(csv.DictReader((M/'bom.csv').read_text().splitlines(),delimiter='\t'))
assert sum(int(r['Quantity']) for r in rows)==12
assert all(r['Manufacturer Part'] and r['Supplier Part'] for r in rows)
assert {r['Value'] for r in rows if r['Designator'].startswith('R')}=={'470Ω','1kΩ','47kΩ'}
schematic=json.loads((HERE/'reports/schematic-current.json').read_text())
routed=json.loads((HERE/'reports/routed-native-50x14.json').read_text())
assert schematic['ok'] and schematic['value']['saved'] and schematic['value']['drc']==[]
assert routed['ok'] and routed['value']['saved'] and routed['value']['drc']==[]
assert len(routed['value']['lines'])==45 and len(routed['value']['vias'])==8
with zipfile.ZipFile(M/'B06-LIGHT-PWM-Gerber.zip') as z:
 assert z.testzip() is None
 outline=z.read('Gerber_BoardOutlineLayer.GKO').decode()
 assert '%MOMM*%' in outline and 'X5000000Y-1400000D01*' in outline
 drill=z.read('Drill_NPTH_Through.DRL').decode()
 assert 'T01C2.40000' in drill and 'T02C3.20000' in drill
 assert all(s in drill for s in ['X2.0Y-5.0','X48.0Y-5.0','X8.0Y-4.0','X42.0Y-4.0'])
 pth=z.read('Drill_PTH_Through.DRL').decode()
 assert len(re.findall(r'^X',pth,re.M))==8 and 'T01C0.30000' in pth
 assert 'Gerber_TopLayer.GTL' in z.namelist() and 'Gerber_BottomLayer.GBL' in z.namelist()
 archive_entries=z.namelist()
source=HERE.parent/'base-io-b05/base-io-b05'
report=dict(pass_=True,board_mm=[50,14,1.6],native_schematic_drc=0,native_pcb_drc=0,components=12,
 native_lines=45,native_vias=8,pin_map_exact=True,bom_component_count=12,npth=[{'x':2,'y':-5,'d':2.4},{'x':48,'y':-5,'d':2.4},{'x':8,'y':-4,'d':3.2},{'x':42,'y':-4,'d':3.2}],
 archive_crc_pass=True,archive_entries=archive_entries,
 manufacturing_sha256={p.name:digest(p) for p in sorted(M.iterdir()) if p.is_file()},
 native_source_sha256={str(p.relative_to(source)):digest(p) for p in [source/'pcb/PCB1.epcb2',source/'sch/Schematic1/P1.esch2']},
 electrical_screen={'supply_V':[4.75,5.25],'pwm_V':[3.3,5], 'nominal_total_LED_mA':3*(5-.4-2)/470*1000,
  'absolute_resistor_limited_total_mA':3*5.25/(470*.99)*1000,'maximum_resistor_power_mW':5.25**2/(470*.99)*1000,
  'resistor_rating_mW':100,'gate_V_at_3_3V':3.3*47/48},
 limits=['Native DRC and exported data consistency, not physical PCB assembly qualification.',
 'Typical LED/drop assumptions only; brightness, derating, temperature and EMC need prototypes.',
 'External regulated/current-limited 5V and PWM source not selected; never attach to 48V.',
 'Rear auxiliary lead/interface decision pending; no full harness release.'])
(HERE/'reports/manufacturing-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('LIGHT_NATIVE_AUDIT_PASS',report['electrical_screen'])
