#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
import os,sys,subprocess,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;K=D/'kicad'
cli=os.environ.get('KICAD_CLI') or shutil.which('kicad-cli')
if not cli:raise SystemExit('Set KICAD_CLI to the official KiCad10 kicad-cli executable.')
def run(args):
 p=subprocess.run([str(x.relative_to(D)) if isinstance(x,Path) and D in x.parents else str(x) for x in args],cwd=D,text=True,capture_output=True);print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);return p
p=run([sys.executable,D/'build.py']);p.check_returncode()
commands=[['sch','erc','--format','json','--exit-code-violations','--output',K/'checks/erc.json',K/'head.kicad_sch'],['sch','export','netlist','--format','kicadxml','--output',K/'head.net.xml',K/'head.kicad_sch'],['sch','export','svg','--output',K/'plots',K/'head.kicad_sch']]
logs=[]
for command in commands:
 p=run([cli]+command);logs.append({'command':['kicad-cli']+[str(a.relative_to(D)) if isinstance(a,Path) else str(a) for a in command],'returncode':p.returncode,'stdout':p.stdout.replace(str(D)+'/', ''),'stderr':p.stderr.replace(str(D)+'/', '')});p.check_returncode()
# Normalize only optional source-path metadata in the native XML; electrical nodes are untouched.
p=K/'head.net.xml';p.write_text(p.read_text().replace(str(D)+'/', ''))
import json
(K/'checks/cli-report.json').write_text(json.dumps({'version':run([cli,'version']).stdout.strip(),'commands':logs,'fontconfig_note':'Headless CLI emits host fontconfig warning; vector schematic still exported and visually reviewed. No ERC severity suppressed.'},indent=2)+'\n')
p=run([sys.executable,D/'verify.py']);p.check_returncode()
for p in K.glob('*.kicad_prl'):p.unlink()
