#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Rebuild BRI01 candidate; no autorouter or supplier CAD required for replay."""
from pathlib import Path
import subprocess,argparse,json,sys
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--kicad-python',required=True);p.add_argument('--kicad-cli',required=True);p.add_argument('--cadquery-python');p.add_argument('--check-only',action='store_true');a=p.parse_args();records=[]
def run(exe,args):
 r=subprocess.run([exe]+args,cwd=D,capture_output=True,text=True);records.append(dict(command=[Path(exe).name]+args,returncode=r.returncode,output=r.stdout+r.stderr));assert r.returncode==0,records[-1];print(r.stdout.strip())
if not a.check_only:
 for f in ['build_source.py','tools/build_schematic.py','tools/calculate.py']:run(sys.executable,[f])
 for f in ['tools/build_board.py','tools/replay_routing.py']:run(a.kicad_python,[f])
run(a.kicad_cli,['sch','erc','--severity-all','--format','json','-o','reports/erc.json','kicad/base-rear-interface01.kicad_sch'])
run(a.kicad_cli,['sch','export','netlist','--format','kicadxml','-o','reports/netlist.xml','kicad/base-rear-interface01.kicad_sch'])
xml=D/'reports/netlist.xml';xml.write_text(xml.read_text().replace(str(D.resolve())+'/', ''))  # redact machine-specific source path only
run(a.kicad_cli,['sch','export','pdf','-o','previews/schematic.pdf','kicad/base-rear-interface01.kicad_sch'])
run(a.kicad_cli,['pcb','drc','--all-track-errors','--schematic-parity','--severity-all','--format','json','-o','reports/drc.json','kicad/base-rear-interface01.kicad_pcb'])
run(a.kicad_python,['tools/native_readback.py'])
if a.cadquery_python:run(a.cadquery_python,['tools/build_mechanical.py'])
for layers,file in [('F.Cu,F.Silkscreen,Edge.Cuts','front'),('B.Cu,Edge.Cuts','back'),('In1.Cu,Edge.Cuts','inner1'),('In2.Cu,Edge.Cuts','inner2')]:run(a.kicad_cli,['pcb','export','svg','--layers',layers,'--mode-single','--page-size-mode','2','--exclude-drawing-sheet','-o','previews/board-'+file+'.svg','kicad/base-rear-interface01.kicad_pcb'])
for layers,file in [('F.Cu,F.Silkscreen,Edge.Cuts','front'),('B.Cu,Edge.Cuts','back'),('In1.Cu,Edge.Cuts','inner1'),('In2.Cu,Edge.Cuts','inner2')]:run(a.kicad_cli,['pcb','export','pdf','--layers',layers,'--mode-single','--scale','2','-o','previews/board-'+file+'.pdf','kicad/base-rear-interface01.kicad_pcb'])
run(a.kicad_cli,['pcb','export','gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts','-o','fabrication/','kicad/base-rear-interface01.kicad_pcb'])
run(a.kicad_cli,['pcb','export','drill','--excellon-separate-th','--generate-map','--map-format','svg','--generate-report','-o','fabrication/','kicad/base-rear-interface01.kicad_pcb'])
(D/'reports/cli-report.json').write_text(json.dumps(records,indent=2)+'\n')
run(sys.executable,['verify.py'])
