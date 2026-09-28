#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""True native layer plots plus label-cleaned review derivatives."""
import argparse,subprocess,json,re,xml.etree.ElementTree as ET
from pathlib import Path
D=Path(__file__).resolve().parents[1];K=D/'kicad';p=argparse.ArgumentParser();p.add_argument('--kicad-cli',required=True);a=p.parse_args();runs=[];(K/'plots/layers').mkdir(parents=True,exist_ok=True)
cmd=['pcb','export','svg','--layers','F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Fab,B.Fab','--common-layers','Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','--mode-multi','--output','plots/layers/','central.kicad_pcb'];r=subprocess.run([a.kicad_cli,*cmd],cwd=K,capture_output=True,text=True);assert r.returncode==0,r.stderr;runs.append(dict(command=['kicad-cli',*cmd],returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
for side,layers in [('front','F.Cu,F.Fab,F.SilkS,Edge.Cuts'),('back','B.Cu,B.Fab,B.SilkS,Edge.Cuts')]:
 cmd=['pcb','export','svg','--layers',layers,'--page-size-mode','2','--exclude-drawing-sheet','--mode-single','--output','plots/'+side+'-review.svg']
 if side=='back':cmd.append('--mirror')
 cmd.append('central.kicad_pcb');r=subprocess.run([a.kicad_cli,*cmd],cwd=K,capture_output=True,text=True);assert r.returncode==0,r.stderr
 dest=K/'plots'/(side+'-review.svg');root=ET.fromstring(dest.read_text());removed=[]
 for parent in root.iter():
  for child in list(parent):
   desc=child.find('{http://www.w3.org/2000/svg}desc')
   if child.tag.endswith('g') and child.get('class')=='stroked-text' and desc is not None and (not re.fullmatch(r'(?:D|R|C|U|J|TH)\d+',desc.text or '') or side=='front' and re.fullmatch(r'D\d+',desc.text or '')):removed.append(desc.text);parent.remove(child)
   elif child.tag.endswith('text') and (not re.fullmatch(r'(?:D|R|C|U|J|TH)\d+',child.text or '') or side=='front' and re.fullmatch(r'D\d+',child.text or '')):parent.remove(child)
 ET.register_namespace('','http://www.w3.org/2000/svg');dest.write_text(ET.tostring(root,encoding='unicode'))
 runs.append(dict(command=['kicad-cli',*cmd],returncode=r.returncode,review_only_hidden_values=removed))
(D/'plot-report.json').write_text(json.dumps(dict(revision='CD-PCB01',source='native KiCad export; layer SVGs unmodified; review composites hide values; front review also hides dense LED references, preserved in raw layer SVG and placement CSV',back_view='native mirror for reading, physical PCB is not mirrored',runs=runs),indent=2)+'\n')
