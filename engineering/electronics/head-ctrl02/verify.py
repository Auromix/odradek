#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent native-net comparison and structural engineering checks, not hardware tests."""
from pathlib import Path
import csv,json,hashlib,xml.etree.ElementTree as ET
D=Path(__file__).resolve().parent;K=D/'kicad';src=json.loads((D/'netlist.json').read_text());xml=ET.parse(K/'head.net.xml');actual={}
for net in xml.findall('.//nets/net'):
 name=net.attrib['name']
 for node in net.findall('node'):actual[(node.attrib['ref'],node.attrib['pin'])]=name
expected={(p['ref'],p['pin']):p['net'] for p in src['pins'] if p['net'] is not None}
differences=[{'pin':list(k),'expected':v,'actual':actual.get(k)} for k,v in expected.items() if actual.get(k)!=v]
# XML libraries may list intentional NC as unconnected-(...) nodes. They are not active nets.
unexpected=[{'pin':list(k),'net':v} for k,v in actual.items() if not k[0].startswith('#') and k not in expected and not v.startswith('unconnected-')]
mcu=list(csv.DictReader((D/'pinmux.csv').open()));assert len(mcu)==100
assert len({r['package_pin'] for r in mcu})==100
by_pad={r['pad_name']:r for r in mcu if r['pad_name'] not in ['VSS','VDD']}
# Independent known official assignments: DS12288 Table12/13.
checks={p:(pin,af,per) for p,pin,af,per in [('PA5',27,'AF5','SPI1'),('PA6',28,'AF5','SPI1'),('PA7',29,'AF5','SPI1'),('PB13',52,'AF5','SPI2'),('PB14',53,'AF5','SPI2'),('PB15',54,'AF5','SPI2'),('PD12',59,'AF2','TIM4_CH1'),('PD13',60,'AF2','TIM4_CH2'),('PD14',61,'AF2','TIM4_CH3'),('PD15',62,'AF2','TIM4_CH4'),('PA9',70,'AF7','USART1_TX'),('PA10',71,'AF7','USART1_RX')]}
for p,(pin,af,per) in checks.items():
 r=by_pad[p];assert (int(r['package_pin']),r['alternate_function'],r['peripheral'])==(pin,af,per)
for p,pin,ch in [('PA0',20,1),('PA1',21,2),('PA2',22,3),('PA3',25,4),('PC0',15,6),('PC1',16,7),('PC2',17,8),('PC3',18,9)]:assert (int(by_pad[p]['package_pin']),by_pad[p]['peripheral'])==(pin,f'ADC1_IN{ch}')
for p,pin,ch in [('PE7',38,4),('PE8',39,6),('PE9',40,2),('PE10',41,14),('PE11',42,15),('PE12',43,16),('PE13',44,3)]:assert (int(by_pad[p]['package_pin']),by_pad[p]['peripheral'])==(pin,f'ADC3_IN{ch}')
for adc in ['ADC1','ADC3']:
 channels=[r['peripheral'] for r in mcu if r['peripheral'].startswith(adc+'_')];assert len(channels)==len(set(channels))
assert by_pad['PB11']['package_pin']=='50'
assert by_pad['PB8_BOOT0']['package_pin']=='95'
# OUT2 cannot be shorted to system ground; chargepump caps must not be substituted with ground caps.
for i in range(1,5):
 assert expected[(f'U{10+i}','10')]==f'M{i}_OUT2'
 assert expected[(f'U{10+i}','16')]=='GND'
 assert next(p for p in src['pins'] if p['ref']==f'U{10+i}' and p['pin']=='7')['net'] is None
 for sig in ['SLEEP','EN','PH']:assert expected[(f'U{10+i}',{'SLEEP':'3','EN':'1','PH':'2'}[sig])]==f'M{i}_{sig}'
# LAN power rails and straps verified separately from symbol generation.
for pin,net in [('1','OSC_25M'),('6','LAN_1V2'),('7','3V3_LOGIC'),('11','ESC_RESET_N'),('13','ESC_MISO'),('17','ESC_MOSI'),('19','ESC_SCK'),('50','ESC_CS_N'),('56','PHY_1V2'),('59','PHY_1V2'),('65','GND')]:assert expected[('U2',pin)]==net
assert expected[('U1','14')]=='MCU_RESET_N' and expected[('U1','68')]=='ESC_RESET_N'
for pp,nn in [('1','SYS_RESET_N'),('2','GND'),('3','SYS_RESET_N'),('4','ESC_RESET_N'),('5','3V3_LOGIC'),('6','MCU_RESET_N')]:assert expected[('U23',pp)]==nn
assert expected[('U15','1')]=='SYS_RESET_N'
assert next(p for p in src['pins'] if p['ref']=='U2' and p['pin']=='2')['net'] is None
assert next(p for p in src['pins'] if p['ref']=='U2' and p['pin']=='3')['net'] is None
comp={c['ref']:c for c in src['components']}
# Make FPL pin compatibility an actual join of authoritative tables, not prose.
fpl=json.loads((D.parent/'final-petal-fpl01/upper/netlist.json').read_text())
fplpins={p['pin']:p['pin_name'] for p in fpl['pins'] if p['ref']=='J1' and p['pin'].isdigit()}
ours={c['functional_reference']:c['ref'] for c in src['components']}
for i in range(1,5):
 j=ours[f'J_L{i}'];p={p['pin']:p['net'] for p in src['pins'] if p['ref']==j}
 assert p=={'1':f'LED_POWER{i-1}','2':'GND','3':'3V3_LOGIC','4':'LED_SCK','5':'LED_MOSI','6':'LED_MISO_BUS','7':f'LED_CS{i-1}','8':'LED_VSYNC','9':'LED_VIO','10':f'NTC_P{i}','M1':'GND','M2':'GND'}
assert list(fplpins.values())==['VLED_3V3','GND','VCC_3V3','SCLK','MOSI','MISO_HOST','SS_N','VSYNC','VIO_EN','NTC_RETURN']
erc=json.loads((K/'checks/erc.json').read_text());violations=[x for s in erc['sheets'] for x in s['violations']]
assert not differences and not unexpected and not violations,(differences,unexpected,violations)
# Every output artifact proof is hash-bound; no imported DRC report exists because noPCBexists.
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report={'revision':'HEAD-CTRL02','status':'schematic candidate only','components':len(comp),'pins':len(src['pins']),'mcu_package_pins':len(mcu),'connected_pins_compared':len(expected),'pin_net_differences':differences,'unexpected_native_nets':unexpected,'erc_violations':len(violations),'erc_exclusions':[],'native_default_ignored_checks':erc.get('ignored_checks',[]),'af_adc_assertions':'pass: independently enumerated selected ST Table12/13 cases','driver_pin_assertions':'pass','FPL01_GH10_pin_contract':'pass','PCB_created':False,'DRC_run':False,'assigned_footprints':0,'candidate_footprint_metadata':True,'no_hardware_tests':True,'sources_read_scope':'officialdatasheets+existingrepoP16/RH/FPL; not vendor schematic review','sha256':{str(p.relative_to(D)):sha(p) for p in [D/'build.py',D/'pinmux.csv',D/'bom.csv',D/'pin-net.csv',D/'netlist.json',D/'calculations.json',D/'sources.json',D/'control-contract.json',D/'verify.py',D/'rebuild.py',K/'head.kicad_sch',K/'head.net.xml',K/'checks/erc.json']},'FPL_source_sha256':sha(D.parent/'final-petal-fpl01/upper/netlist.json')}
(K/'checks/verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sha256','FPL_source_sha256']},indent=2))
