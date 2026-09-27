# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Run actual KiCad tools and compare exported nets to reviewed source.
No suppressed ERC/DRC violations are accepted by this script.
"""
import argparse,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--kicad-cli',required=True);p.add_argument('--board',default='upper-petal.kicad_pcb');args=p.parse_args()
R=D/'checks';R.mkdir(exist_ok=True)
def run(arg,name):
 r=subprocess.run([args.kicad_cli,*arg],cwd=D,text=True,capture_output=True)
 stdout=r.stdout.replace(str(D)+'/','');stderr=r.stderr.replace(str(D)+'/','')
 (R/(name+'.log')).write_text(stdout+stderr)
 return {'command':['kicad-cli',*arg],'returncode':r.returncode,'stdout':stdout,'stderr':stderr}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
record={'commands':{}}
record['commands']['version']=run(['version'],'version')
record['commands']['export_netlist']=run(['sch','export','netlist','--format','kicadxml','-o','checks/upper-petal.xml','upper-petal.kicad_sch'],'export-netlist')
if record['commands']['export_netlist']['returncode']==0:
 xp=R/'upper-petal.xml';xp.write_text(xp.read_text().replace(str(D)+'/',''));xml=ET.parse(xp);actual={}
 for net in xml.findall('./nets/net'):
  for node in net.findall('node'):
   if not node.attrib['ref'].startswith('#'):actual[(node.attrib['ref'],node.attrib['pin'])]=net.attrib['name']
 source=json.loads((D.parent/'netlist.json').read_text());expected={(p['ref'],p['pin']):p['net'] for p in source['pins']}
 mismatches=[]
 for key,net in expected.items():
  found=actual.get(key)
  if net is None:
   if found and not found.startswith('unconnected-'):mismatches.append({'ref_pin':list(key),'expected':None,'actual':found})
  elif found!=net:mismatches.append({'ref_pin':list(key),'expected':net,'actual':found})
 unexpected=[list(k) for k in actual if k not in expected]
 record['netlist_comparison']={'expected_pin_records':len(expected),'exported_pin_records':len(actual),'mismatches':mismatches,'unexpected':unexpected,'passed':not mismatches and not unexpected}
record['commands']['erc']=run(['sch','erc','--format','json','--exit-code-violations','-o','checks/erc.json','upper-petal.kicad_sch'],'erc')
record['commands']['drc']=run(['pcb','drc','--schematic-parity','--format','json','--exit-code-violations','-o','checks/drc.json',args.board],'drc')
record['input_hashes']={f:sha(D/f) for f in ['upper-petal.kicad_sch',args.board,'upper-petal.kicad_pro','build_ecad.py','build_board.py','check_ecad.py','finalize_native.py','review_native_board.py','prepare_native.py','replay_routing.py','routing-plan.json','../mapping-revision.json','../register-plan.json']}
record['report_counts']={}
for report in ['erc','drc']:
 data=json.loads((R/(report+'.json')).read_text())
 if report=='erc':record['report_counts'][report]={'violations':sum(len(sh.get('violations',[])) for sh in data['sheets'])}
 else:record['report_counts'][report]={k:len(data[k]) for k in ['violations','unconnected_items','schematic_parity']}
 record.setdefault('ignored_default_checks',{})[report]=data.get('ignored_checks',[])
record['input_hashes']['../netlist.json']=sha(D.parent/'netlist.json')
for fp in sorted((D/'ULP.pretty').glob('*.kicad_mod')):record['input_hashes'][str(fp.relative_to(D))]=sha(fp)
record['digital_checks_all_passed']=record.get('netlist_comparison',{}).get('passed',False) and all(v==0 for r in record['report_counts'].values() for v in r.values()) and all(c['returncode']==0 for c in record['commands'].values())
record['fabrication_release']=False
record['status']='Actual tool results; engineering/thermal/manufacturing validation separate'
record['report_sanitization']='Only absolute current-project directory prefix is removed from XML and stdout/stderr; electrical records and check findings unchanged.'
(R/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'commands':{k:v['returncode'] for k,v in record['commands'].items()},'netlist_comparison':record.get('netlist_comparison')},indent=2))

sys.exit(0 if record["digital_checks_all_passed"] else 1)
