# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Rebuild both native candidate boards and replay source-matched checked routes."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--kicad-cli',required=True);p.add_argument('--kicad-python',required=True);p.add_argument('--skip-export',action='store_true');a=p.parse_args()
for key in ('kicad_cli','kicad_python'):
 v=getattr(a,key);r=Path(shutil.which(v) or v).expanduser().resolve()
 if not r.is_file():p.error(key+': executable not found')
 setattr(a,key,str(r))
runs=[]
def run(cmd,cwd=D):
 r=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
 clean=lambda v:v.replace(str(D)+'/','').replace(a.kicad_cli,'kicad-cli').replace(a.kicad_python,'kicad-python')
 runs.append({'command':[Path(cmd[0]).name,*[clean(x) for x in cmd[1:]]],'cwd':str(cwd.relative_to(D)), 'returncode':r.returncode,'stdout':clean(r.stdout),'stderr':clean(r.stderr)})
 if r.returncode:raise RuntimeError(runs[-1])
run([sys.executable,'build.py'])
for kind in ['upper','lower']:
 b=D/kind/'kicad';rel=str(b.relative_to(D));(b/'checks').mkdir(exist_ok=True)
 run([sys.executable,'build_firmware_example.py'],b.parent)
 run([sys.executable,'tools/build_schematic.py',rel]);run([sys.executable,'tools/build_board.py',rel]);run([a.kicad_python,'tools/prepare_native.py',rel])
 run([a.kicad_cli,'sch','export','netlist','--format','kicadxml','-o','checks/petal.xml','petal.kicad_sch'],b)
 run([a.kicad_python,'tools/finalize_native.py',rel]);run([a.kicad_python,'tools/replay_routing.py',rel])
 run([sys.executable,'tools/check_ecad.py',rel,'--kicad-cli',a.kicad_cli]);assert json.loads((b/'checks/verification.json').read_text())['digital_checks_all_passed']
 run([a.kicad_python,'tools/review_native_board.py',rel]);assert json.loads((b/'checks/native-board-audit.json').read_text())['passed_source_placement_polarity_check']
 clang=shutil.which('clang')
 if clang:run([clang,'-std=c99','-Wall','-Wextra','-Werror','-fsyntax-only','fpl01_'+kind+'_example.c'],b.parent)
 if not a.skip_export:
  run([a.kicad_cli,'sch','export','svg','--output','plots/schematic','petal.kicad_sch'],b)
  run([a.kicad_cli,'pcb','export','svg','--layers','F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.SilkS,B.SilkS,F.Fab,B.Fab','--common-layers','Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','--mode-multi','--output','plots','petal.kicad_pcb'],b)
 for f in ['petal-unrouted.kicad_pcb','petal-unrouted.kicad_pro','petal.dsn','petal-seeded.dsn','petal.kicad_prl']:(b/f).unlink(missing_ok=True)
run([sys.executable,'tools/firmware_mock_check.py'])
if not a.skip_export:run([sys.executable,'tools/export_review_views.py','--kicad-cli',a.kicad_cli])
report={'revision':'FPL-01','status':'actual source rebuild and native digital gates passed','runs':runs,'hardware_execution':False,'fabrication_release':False,'artifacts':{str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for kind in ['upper','lower'] for p in sorted((D/kind/'kicad').rglob('*')) if p.is_file() and p.name in ['petal.kicad_pcb','petal.kicad_sch','routing-plan.json','verification.json','native-board-audit.json']}}
(D/'rebuild-report.json').write_text(json.dumps(report,indent=2)+'\n');print('FPL01 two-board actual rebuild and digital checks passed')
