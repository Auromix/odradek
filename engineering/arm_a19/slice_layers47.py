# SPDX-License-Identifier: CC-BY-NC-4.0
"""Plot actual linear extrusion segments from private reference G-code."""
from pathlib import Path
import re,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];WORK=ROOT/'work/arm-a19/slice45';PACK=ROOT/'manufacturing/candidates/arm-body-a19-integrated-fit'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
 pos=np.zeros(3);etype='Custom';relative=True;E=0;layers={};arcs=0;layer=None
 for raw in p.read_text().splitlines():
  if raw.startswith(';Z:'):layer=float(raw[3:]);continue
  if raw.startswith(';TYPE:'):etype=raw[6:];continue
  line=raw.split(';')[0].strip()
  if not line:continue
  code=line.split()[0];vals={k:float(v)for k,v in re.findall(r'([XYZE])(-?(?:\d+(?:\.\d*)?|\.\d+))',line)}
  if code=='M83':relative=True
  elif code=='M82':relative=False
  elif code=='G92'and'E'in vals:E=vals['E']
  elif code in ['G0','G1','G2','G3']:
   new=pos.copy()
   for i,k in enumerate('XYZ'):
    if k in vals:new[i]=vals[k]
   ex=vals.get('E',0)if relative else vals.get('E',E)-E
   if 'E'in vals:E=E+vals['E']if relative else vals['E']
   if ex>0 and etype!='Custom'and np.linalg.norm(new[:2]-pos[:2])>1e-6:
    if code in ['G2','G3']:arcs+=1
    elif layer is not None:layers.setdefault(layer,[]).append((pos[:2].copy(),new[:2].copy(),etype))
   pos=new
 return layers,arcs

def main():
 ids=['A19-S22-shoulder-foot-12mm-R6-fit','A19-C21-J5-cowl-a','A16-C05-J7-bearing-housing','A13-IF-301-recessed-carrier'];fig,ax=plt.subplots(4,3,figsize=(14,17));audits=[]
 for row,id in enumerate(ids):
  p=WORK/'parts'/id/'plate_1.gcode';layers,arcs=read(p);assert arcs==0;zs=sorted(layers);targets=[zs[0],zs[len(zs)//2],zs[max(0,len(zs)-3)]]
  for col,z in enumerate(targets):
   segments=layers[z];a=ax[row,col]
   for group,color in [('model','#243746'),('support','#e69c21'),('brim','#aab4bc')]:
    lines=[[s[0],s[1]]for s in segments if ('support'if'Support'in s[2]else'brim'if s[2]=='Brim'else'model')==group]
    if lines:a.add_collection(LineCollection(lines,colors=color,linewidths=.55,label=group))
   a.autoscale();a.set_aspect('equal');a.set_title(f'{id}\nZ={z:.2f} mm, layer {zs.index(z)+1}/{len(zs)}',fontsize=8);a.set_xlabel('X mm');a.set_ylabel('Y mm');a.legend(loc='best',fontsize=7)
  audits.append(dict(id=id,gcode_sha256=sha(p),sampled_layer_heights_mm=targets,parsed_noncustom_extrusion_layers=len(zs),arc_extrusions_not_plotted=arcs))
 fig.suptitle('A19 reference slicing: actual extrusion segments\nModel navy / supports amber / brim grey. Layer samples do not prove physical printability.',fontsize=14);fig.tight_layout(rect=(0,0,1,.96));target=PACK/'slice47-layer-review.png';fig.savefig(target,dpi=150);plt.close(fig)
 report=dict(source_slice45_sha256=sha(HERE/'build/assembly25/slice45.json'),source_checker_sha256=sha(Path(__file__)),image_sha256=sha(target),records=audits,scope='12 sampled XY layers for4 parts; linear extrusion segments only,0arc extrusion omitted. No physical support removal, complete layer coverage, adhesion, dimensions or structural release.')
 (PACK/'slice47-layer-review.json').write_text(json.dumps(report,indent=2)+'\n');print('LAYERS47',len(audits))
if __name__=='__main__':main()
