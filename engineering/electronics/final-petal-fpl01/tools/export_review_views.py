# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Native board review composites; rear view is mirrored for reading."""
import argparse,subprocess,json,re,xml.etree.ElementTree as ET
from pathlib import Path
D=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--kicad-cli',required=True);a=p.parse_args();runs=[]
for k in ['upper','lower']:
 for side,layers in [('front','F.Cu,F.Fab,F.SilkS,Edge.Cuts'),('back','B.Cu,B.Fab,B.SilkS,Edge.Cuts')]:
  cmd=['pcb','export','svg','--layers',layers,'--page-size-mode','2','--exclude-drawing-sheet','--mode-single','--output','plots/'+side+'-review.svg']
  if side=='back':cmd.append('--mirror')
  cmd.append('petal.kicad_pcb');r=subprocess.run([a.kicad_cli,*cmd],cwd=D/k/'kicad',capture_output=True,text=True)
  runs.append({'panel':k,'view':side,'command':['kicad-cli',*cmd],'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
  if r.returncode:raise RuntimeError(runs[-1])
  # Value strings can overlap densely populated assemblies. Hide only their display
  # in this review derivative; retain raw native per-layer SVGs and native board.
  dest=D/k/'kicad/plots'/(side+'-review.svg');root=ET.fromstring(dest.read_text());removed=[]
  for parent in root.iter():
   for child in list(parent):
    desc=child.find('{http://www.w3.org/2000/svg}desc')
    if child.tag.endswith('g') and child.get('class')=='stroked-text' and desc is not None and not re.fullmatch(r'(?:D|R|C|U|J|TH|MH)\d+',desc.text or ''):removed.append(desc.text);parent.remove(child)
    elif child.tag.endswith('text') and not re.fullmatch(r'(?:D|R|C|U|J|TH|MH)\d+',child.text or ''):parent.remove(child)
  ET.register_namespace('','http://www.w3.org/2000/svg');dest.write_text(ET.tostring(root,encoding='unicode'))
  runs[-1]['review_derivative_value_labels_hidden']=removed
(D/'preview-export-report.json').write_text(json.dumps({'source':'native KiCad plots; not physical render','back_view':'mirrored native plot (not a mirrored PCB design)','runs':runs},indent=2)+'\n')
