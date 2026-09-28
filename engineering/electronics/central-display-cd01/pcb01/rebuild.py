#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Rebuild only PCB01 from read-only CD-EC01 and replay proven native routes."""
from pathlib import Path
import argparse,subprocess,json,hashlib,sys
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--kicad-cli',required=True);p.add_argument('--kicad-python',required=True);a=p.parse_args();a.kicad_cli=str(Path(a.kicad_cli).resolve());a.kicad_python=str(Path(a.kicad_python).resolve());records=[]
# Capture existing read-only parent digests before touching this child directory.
contract=json.loads((D/'baseline-inputs.json').read_text())
for n,h in contract['sha256'].items():assert hashlib.sha256((D.parent/n).read_bytes()).hexdigest()==h,('Parent baseline changed',n)
def run(exe,args):
 r=subprocess.run([exe,*args],cwd=D,capture_output=True,text=True);safe=['<kicad-cli>' if str(x)==a.kicad_cli else '<kicad-python>' if str(x)==a.kicad_python else str(x) for x in args];records.append({'program':Path(exe).name,'args':safe,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if r.returncode:raise RuntimeError(records[-1])
 print(Path(exe).name,*safe,flush=True)
try:
 run(sys.executable,['build_source.py']);run(sys.executable,['tools/build_schematic.py','kicad']);run(sys.executable,['tools/build_board.py','kicad'])
 run(a.kicad_python,['tools/prepare_native.py','kicad'])
 run(a.kicad_cli,['sch','export','netlist','--format','kicadxml','--output','kicad/checks/central.xml','kicad/central.kicad_sch'])
 # Normalize only the machine-local source-path metadata; all exported pins/nets remain exact.
 xml_path=D/'kicad/checks/central.xml';xml_text=xml_path.read_text();xml_text=xml_text.replace('<source>'+str(D/'kicad/central.kicad_sch')+'</source>','<source>kicad/central.kicad_sch</source>');xml_path.write_text(xml_text)
 run(a.kicad_cli,['sch','erc','--format','json','--output','kicad/checks/erc.json','kicad/central.kicad_sch'])
 run(a.kicad_python,['tools/finalize_native.py','kicad']);run(a.kicad_python,['tools/replay_routing.py','kicad'])
 run(a.kicad_cli,['pcb','drc','--schematic-parity','--format','json','--output','kicad/checks/drc.json','kicad/central.kicad_pcb'])
 run(a.kicad_python,['tools/audit_board.py','kicad']);run(sys.executable,['tools/dfm_evidence.py'])
 run(sys.executable,['tools/export_review_views.py','--kicad-cli',a.kicad_cli])
 for temp in (D/'kicad').glob('central-unrouted.*'):temp.unlink()
 for temp in (D/'kicad').glob('*.kicad_prl'):temp.unlink()
 run(sys.executable,['verify.py'])
finally:(D/'cli-report.json').write_text(json.dumps({'revision':'CD-PCB01','parent_generation_invoked':False,'netlist_path_metadata_normalized_to_project_relative':True,'runtime_version':subprocess.check_output([a.kicad_cli,'--version'],text=True).strip(),'runs':records},indent=2)+'\n')
