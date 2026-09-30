#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import argparse,subprocess,sys,json
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--kicad-python',required=True);p.add_argument('--kicad-cli',required=True);p.add_argument('--cadquery-python');p.add_argument('--check-only',action='store_true');a=p.parse_args();records=[]
def run(exe,args):
 r=subprocess.run([exe]+args,cwd=D,capture_output=True,text=True);records.append(dict(command=[Path(exe).name]+args,returncode=r.returncode,output=(r.stdout+r.stderr).replace(str(D),"${MODULE_DIR}")));assert r.returncode==0,records[-1];print(r.stdout.strip())
if not a.check_only:
 for s in ['build_source.py','tools/build_schematic.py']:run(sys.executable,[s])
 run(a.kicad_python,['tools/build_board.py'])
 if a.cadquery_python:run(a.cadquery_python,['tools/build_mechanical.py'])
run(a.kicad_cli,['sch','erc','--severity-all','--format','json','-o','kicad/checks/erc.json','kicad/base-light-b04.kicad_sch'])
run(a.kicad_cli,['sch','export','svg','--exclude-drawing-sheet','-o','previews/','kicad/base-light-b04.kicad_sch'])
run(a.kicad_cli,['sch','export','netlist','--format','kicadxml','-o','kicad/checks/base-light-b04.xml','kicad/base-light-b04.kicad_sch'])
run(a.kicad_cli,['pcb','drc','--all-track-errors','--schematic-parity','--severity-all','--format','json','-o','kicad/checks/drc.json','kicad/base-light-b04.kicad_pcb'])
for layer,f in [('F.Cu,F.Silkscreen,Edge.Cuts','board-front'),('B.Cu,B.Silkscreen,Edge.Cuts','board-back')]:run(a.kicad_cli,['pcb','export','svg','--layers',layer,'--mode-single','--page-size-mode','2','--exclude-drawing-sheet','-o','previews/'+f+'.svg','kicad/base-light-b04.kicad_pcb'])
run(a.kicad_cli,['pcb','export','gerbers','--layers','F.Cu,B.Cu,F.Paste,B.Paste,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts','-o','fabrication/','kicad/base-light-b04.kicad_pcb'])
run(a.kicad_cli,['pcb','export','drill','--excellon-separate-th','--generate-map','--map-format','svg','--generate-report','-o','fabrication/','kicad/base-light-b04.kicad_pcb'])
if (D/'mechanical'/'led-envelope.step').exists():run(a.kicad_cli,['pcb','export','step','--force','--subst-models','-o','mechanical/native-kicad.step','kicad/base-light-b04.kicad_pcb'])
run(a.kicad_python,['tools/verify_native.py'])
(D/'cli-report.json').write_text(json.dumps(records,indent=2)+'\n')
