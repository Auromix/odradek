#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
import os,sys,subprocess,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;K=D/'kicad'
cli=os.environ.get('KICAD_CLI') or shutil.which('kicad-cli')
if not cli:raise SystemExit('Set KICAD_CLI to the official KiCad10 kicad-cli executable.')
def run(args):
 p=subprocess.run([str(x.relative_to(D)) if isinstance(x,Path) and D in x.parents else str(x) for x in args],cwd=D,text=True,capture_output=True);print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);return p
for script in ['build.py','build_firmware.py','firmware_check.py','draw_packing.py']:
 p=run([sys.executable,D/script]);p.check_returncode()
p=run([sys.executable,D/'build_schematic.py',K]);p.check_returncode()
commands=[['sch','erc','--format','json','--exit-code-violations','--output',K/'checks/erc.json',K/'central.kicad_sch'],['sch','export','netlist','--format','kicadxml','--output',K/'central.net.xml',K/'central.kicad_sch'],['sch','export','svg','--output',K/'plots',K/'central.kicad_sch']]
logs=[]
for command in commands:
 p=run([cli]+command);logs.append({'command':['kicad-cli']+[str(a.relative_to(D)) if isinstance(a,Path) else str(a) for a in command],'returncode':p.returncode,'stdout':p.stdout.replace(str(D)+'/', ''),'stderr':p.stderr.replace(str(D)+'/', '')});p.check_returncode()
# Normalize only optional source-path metadata in the native XML; electrical nodes are untouched.
p=K/'central.net.xml';p.write_text(p.read_text().replace(str(D)+'/', ''))
import json
(K/'checks/cli-report.json').write_text(json.dumps({'version':run([cli,'version']).stdout.strip(),'commands':logs,'fontconfig_note':'Headless CLI emits host fontconfig warning; vector schematic still exported and visually reviewed. No ERC severity suppressed.'},indent=2)+'\n')
p=run([sys.executable,D/'verify.py']);p.check_returncode()
for p in K.glob('*.kicad_prl'):p.unlink()
