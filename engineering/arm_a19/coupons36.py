# SPDX-License-Identifier: CC-BY-NC-4.0
"""Small unloaded coupons before whole-body prints; not body replacement parts."""
from pathlib import Path
import sys,json,math
import numpy as np
import cadquery as cq
import trimesh
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25';PACK=ROOT/'manufacturing/candidates/arm-body-a19-integrated-fit/calibration-coupons'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c;g=c.cad

def main():
 PACK.mkdir(exist_ok=True);d=json.loads((OUT/'manifest.json').read_text());core=json.loads((HERE/'build/wrist-core19/manifest.json').read_text());inf=core['motor_interface'];n=np.array(inf['n']);records=[]
 def save(id,shape,note,source=None,R=np.eye(3)):
  shape=shape.fix();assert shape.isValid() and len(shape.Solids())==1,id
  path=PACK/(id+'.step');cq.exporters.export(shape,str(path));vs,ts=shape.tessellate(.03,.10);m=trimesh.Trimesh([v.toTuple()for v in vs],ts,process=True);assert m.is_watertight and m.is_winding_consistent and m.volume>0 and len(m.split())==1,id
  m.vertices=m.vertices@R.T;t=-m.bounds[0];m.apply_translation(t);stl=PACK/(id+'.stl');m.export(stl);reload=trimesh.load(stl,force='mesh',process=True);assert max(reload.extents)<250 and abs(reload.bounds[0,2])<1e-5 and reload.is_watertight
  rec=dict(id=id,purpose=note,step_sha256=c.sha(path),stl_sha256=c.sha(stl),R_bed_from_CAD=R.tolist(),bed_translation_mm=t.tolist(),size_mm=reload.extents.tolist(),source_part=source,body_replacement=False,production_release=False);records.append(rec);print('COUPON36',id,reload.extents,flush=True)
 def load(id):
  p=next(x for x in d['parts']if x['id']==id);path=ROOT/p['step_path'];assert c.sha(path)==p['step_sha256'];return cq.importers.importStep(str(path)).val(),dict(id=id,step_sha256=c.sha(path),frame=p['frame'])
 # Intersection with source mating slabs preserves actual bores and seal relief.
 # It does not substitute an ideal generic bolt circle for the native pattern.
 R=np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
 fixed=np.array(inf['fixed_mm'])+[185,62,0];shape,source=load('A19-S19-fore-spine-RS03-ring');save('A19-F36-RS03-fixed-face',shape.intersect(g.cyl(fixed,n,61,8)),'Exact current source mating slab: eight native M4 holes, raised-seal relief and cover stations. Fit only; never carry arm weight.',source,R)
 output=np.array(inf['out_mm']);shape,source=load('A19-S19-RS03-to-J6-L');save('A19-F36-RS03-output-face',shape.intersect(g.cyl(output,n,35,10)),'Exact current source D70x10 output slab and six native holes. Check real motor flange and nominal screw insertion.',source,R)
 for gap in [.2,.4,.6]:
  width=20+gap;height=40+gap;shape=cq.Solid.makeBox(width+6,height+6,20).cut(cq.Solid.makeBox(width,height,20.2,g.V([3,3,-.1]))).fix();save(f'A19-F36-tube-socket-{int(gap*10):02d}',shape,f'Unloaded tube20x40 socket total clearance{gap:.1f}mm. Current body uses20.4x40.4 nominal. Do not change body geometry without a revised source/check set.')
 # Thin cosmetic ear exactly reproduces current nominal clearance/counterbore.
 shape=cq.Solid.makeBox(22,22,3);shape=g.drill(shape,[11,11,-.1],[0,0,1],3.5,3.2);shape=g.drill(shape,[11,11,2],[0,0,1],7.4,1.1);save('A19-F36-cover-ear-3mm',shape,'Thin3mm cosmetic tab: D3.5 clearance, D7.4 counterboredepth1, floor2. Use actual DIN7984 M3x16 washer/nut; compare with source assembly stack, not a load test.')
 shape=cq.Solid.makeBox(105,28,8)
 for row,diameters in enumerate([[3.2,3.4,3.5,3.6,3.8],[4.2,4.4,4.5,4.6,4.8]]):
  for k,diameter in enumerate(diameters):shape=g.drill(shape,[12+20*k,8+12*row,-.1],[0,0,1],diameter,8.2)
 save('A19-F36-hole-gauge',shape,'CAD hole targets: rowY8 D3.2/3.4/3.5/3.6/3.8; rowY20 D4.2/4.4/4.5/4.6/4.8, X12/32/52/72/92. Measure printed diameters; no automatic shrink correction applied.')
 report=dict(revision='A19-UNLOADED-CALIBRATION36',source_assembly_sha256=c.sha(OUT/'manifest.json'),source_core_sha256=c.sha(HERE/'build/wrist-core19/manifest.json'),coupons=records,production_release=False,physical_print_completed=False)
 (PACK/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 (PACK/'measurements-template.csv').write_text('coupon,printer,material,layer_mm,orientation,feature,nominal_mm,measured_mm,fit_result,notes\n')
 (PACK/'README.md').write_text('''# 先打印的小型无载试配件

本目录7件是校准／测量夹具，不计入41件机身打印清单，也不能替换机身承力件。电机面两件由当前实际支架STEP截取，保留原生孔位和密封边避让；没有重新猜测孔圈。

建议顺序：孔径板→三个管套→3 mm外罩耳座→两个RS03真实配合面。STL已单连通、闭合、落床、正体积和小于250 mm包络；尚未指定打印机／切片参数，也没有实际打印结果。使用后续整臂相同的材料与打印方向记录尺寸，孔径与管套偏差不要靠大力压装补偿。

管套的20.2/40.2、20.4/40.4、20.6/40.6是三组试验，总间隙不是单侧间隙；当前机身仍使用20.4/40.4，测量前不自动修改。孔径板的CAD孔位与标称直径见manifest；使用针规／卡尺与真实螺钉比较，记录measurements-template.csv。薄耳座比较真实低头M3、垫圈和螺母；此件不模拟夹持预紧保持或疲劳。

电机试配全程断电，电机和夹具各自支撑。固定面使用当前8 mm夹持板与M4×14／0.8 mm垫圈，输出面10 mm与M4×16／0.8 mm垫圈，名义旋入均5.2 mm。先量真实有效螺纹和入口倒角，防止顶孔；本包未发行拧紧扭矩。贴合面不应压到凸起密封边或电机活动部分。观察／记录平面接触、止口间隙、孔位、拧入长度及插头退出空间。

此处没有验证强度、负载、热、动态走线、通电或金属制造公差。试配测量必须回到同源CAD修订，任何尺寸改动均重做受影响装配证据。
''')
 (PACK/'SHA256SUMS.json').write_text(json.dumps({p.name:c.sha(p)for p in PACK.iterdir()if p.is_file()and p.name!='SHA256SUMS.json'},indent=2)+'\n')
 print('COUPONS36_DONE',len(records),flush=True)
if __name__=='__main__':main()
