# SPDX-License-Identifier: CC-BY-NC-4.0
"""Small J7 nominal fit gauges, separate from current body parts."""
from pathlib import Path
import sys,json
import numpy as np
import cadquery as cq
import trimesh
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25';PACK=ROOT/'manufacturing/candidates/arm-body-a19-integrated-fit/j7-bearing-calibration'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c;g=c.cad

def main():
 PACK.mkdir(exist_ok=True);path=OUT/'manifest.json';d=json.loads(path.read_text());sources={};records=[]
 for id in ['A16-C05-J7-bearing-housing','A13-J7-103-output-journal']:
  p=next(x for x in d['parts']if x['id']==id);assert c.sha(ROOT/p['step_path'])==p['step_sha256'];sources[id]=dict(step=p['step_path'],sha256=p['step_sha256'])
 def save(id,s,feature,nominal):
  assert s.isValid()and len(s.Solids())==1
  f=PACK/(id+'.step');cq.exporters.export(s,str(f));v,t=s.tessellate(.025,.08);m=trimesh.Trimesh([p.toTuple()for p in v],t,process=True);assert m.is_watertight and m.is_winding_consistent and len(m.split())==1 and m.volume>0
  translation=-m.bounds[0];m.apply_translation(translation);stl=PACK/(id+'.stl');m.export(stl);m=trimesh.load(stl,force='mesh',process=True);assert max(m.extents)<65 and abs(m.bounds[0,2])<1e-5
  records.append(dict(id=id,feature=feature,nominal_mm=nominal,step_sha256=c.sha(f),stl_sha256=c.sha(stl),bed_translation_mm=translation.tolist(),bed_size_mm=m.extents.tolist(),body_replacement=False));print('BEARING40',id,m.extents,flush=True)
 for diameter in [47.10,47.20,47.35]:
  save(f'A19-F40-6807-seat-{diameter:.2f}',g.ring([0,0,0],[0,0,1],28,diameter/2,7),'outer-ring bore ID; current nominal47.20',diameter)
 for diameter in [34.85,34.95,35.05]:
  shape=g.cyl([0,0,0],[0,0,1],21,2).fuse(g.cyl([0,0,2],[0,0,1],diameter/2,7)).clean().fix()
  save(f'A19-F40-6807-journal-{diameter:.2f}',shape,'journal OD; current nominal34.95',diameter)
 report=dict(revision='A19-J7-UNLOADED-GAUGES40',source_assembly_sha256=c.sha(path),source_current_body_parts=sources,source_checker_sha256=c.sha(Path(__file__)),nominal_bearing=dict(model='6807',ID_mm=35,OD_mm=47,width_mm=7),coupons=records,physical_print_completed=False,production_release=False)
 (PACK/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 (PACK/'measurements-template.csv').write_text('coupon,printer,material,layer_mm,bearing_vendor,bearing_lot,bearing_actual_mm,gauge_actual_mm,fit_result,notes\n')
 (PACK/'README.md').write_text('''# J7先行轴承配合小样

六件独立无载夹具：座孔47.10／47.20／47.35 mm和轴颈34.85／34.95／35.05 mm。当前机身仍为座孔47.20、轴颈34.95；小样只比较实际打印、轴承与量具，不是机身替换件，也不计入41件打印清单。

使用与机身相同材料、打印机和轴线竖直方向，记录打印尺寸以及所购6807实际ID／OD／宽度。用手轻推比较，不敲打、不夹滚珠、不按金属轴承过盈经验强压塑料。轴颈夹具的宽底边便于卸下轴承；不能把小样轻松套入解释为整臂刚度或预紧通过。

每件STEP／STL单实体、闭合、正体积、单连通、已落床；参考切片另见整包slice45，没有实际打印。完成小样后再按assembly-stages38的两端轴承、后侧轴颈顺序试配J7；测量轴向游隙，再确定金属垫片，避免用塑料变形取得预紧。任何机身配合尺寸调整必须修改源CAD并重做受影响证据。
''')
 (PACK/'SHA256SUMS.json').write_text(json.dumps({p.name:c.sha(p)for p in PACK.iterdir()if p.is_file()and p.name!='SHA256SUMS.json'},indent=2)+'\n')
if __name__=='__main__':main()
