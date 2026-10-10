# SPDX-License-Identifier: CC-BY-NC-4.0
"""Two-part source-bound root supported-fit packet, not a production release."""
from pathlib import Path
import json,sys,csv,shutil,xml.etree.ElementTree as ET
import numpy as np
import cadquery as cq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/root22';PACK=ROOT/'manufacturing/candidates/arm-a19-root22-fit'
sys.path.insert(0,str(ROOT/'engineering/arm_a16'));import common as c
from vendor import interfaces
from hardware01 import points

def main():
    path=OUT/'manifest.json';d=json.loads(path.read_text());review=json.loads((OUT/'review20.json').read_text())
    assert review['changed_pair_sampled_clear'] and review['source_sha256'][str(path.relative_to(ROOT))]==c.sha(path)
    fea=json.loads((OUT/'linear-fea18.json').read_text());assert fea['source_manifest_sha256']==c.sha(path)
    PACK.mkdir(parents=True,exist_ok=True)
    for p in d['parts']:
        src=ROOT/p['step_path'];shutil.copy2(src,PACK/src.name);stl=OUT/(p['id']+'-fit.stl');shutil.copy2(stl,PACK/stl.name)
    s=cq.importers.importStep(str(ROOT/d['step_path'])).val();bb=s.BoundingBox()
    header='''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1000" viewBox="0 0 1400 1000"><rect width="1400" height="1000" fill="white"/><g font-family="Arial,sans-serif" fill="#1f2933"><text x="45" y="45" font-size="25">A19 ROOT22 / SHOULDER FOOT — SUPPORTED FIT DRAWING</text><text x="45" y="74" font-size="16">Millimetres · Exact STEP projections · Nominal geometry · Not a metal production release</text>'''
    drawings=[]
    for name,projection,x,y in [('FRONT / XZ',(0,-1,0),30,110),('SIDE / YZ',(-1,0,0),480,110),('TOP / XY',(0,0,1),940,110)]:
        svg=cq.exporters.getSVG(s,opts=dict(width=420,height=430,marginLeft=25,marginTop=25,projectionDir=projection,showHidden=False,showAxes=False,strokeWidth=.5,strokeColor=(31,41,51)))
        element=ET.fromstring(svg);element.set('x',str(x));element.set('y',str(y));element.set('width','420');element.set('height','430')
        drawings.append(f'<text x="{x+25}" y="{y-10}" font-size="17">{name}</text>'+ET.tostring(element,encoding='unicode'))
    lines=[f'Actual CAD extents: X {bb.xmin:.2f}…{bb.xmax:.2f}; Y {bb.ymin:.2f}…{bb.ymax:.2f}; Z {bb.zmin:.2f}…{bb.zmax:.2f}',
           'Foot: 110 ×104.5 ×8; bottom Z30. 4× Ø5.6 at X±38 / Y±28.',
           'Motor face: Y68.5; shoulder axis X0 / Z114. Outer Ø134 / inner Ø80. Face thickness12.',
           '10× Ø4.5 native mounting holes: see exact coordinate CSV. Ø9.8 counterbore depth4 on front.',
           'Motor bolts retain original M4×12 +0.8 washer +8 grip →3.2 insertion; minimum source depth5.',
           'Cover seats retain4× Ø3.5 at R64,45/135/225/315°. Four open radial Ø12-cutter pockets, depth4.',
           'Root inside blendR6. No added linkage, weld, enclosed pocket or plastic tapped load thread.',
           f'Nominal 6061 density estimate: {d["nominal_6061_mass_kg"]:.3f} kg. Material certificate, tolerances, preload and loads unqualified.',
           'Plastic prototype: external support, all power off, no payload. Drill/gauge critical holes after print calibration.',
           'Metal candidate: certified6061-T651 plate, proposed billet140×110×160; independent vendor DFM/CAM still required.',
           'Projections for identification; coordinate CSV and STEP define nominal features. No printed ruler scale.',
           'Root bracket is conditional on current A18 assembly context; updated wrist mass/loads need integrated verification.']
    footer=''.join(f'<text x="45" y="{590+31*i}" font-size="17">{line.replace("&","&amp;").replace("<","&lt;")}</text>' for i,line in enumerate(lines))
    text=header+''.join(drawings)+footer+'</g></svg>'
    (PACK/'root22-three-view.svg').write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')
    features=[];inf=interfaces()[1];normal=np.array(inf['n']);fixed=np.array(inf['fixed_mm'])+[0,0,114]
    for i,delta in enumerate(points(inf,'fixed_front_fasteners'),1):features.append(dict(id=f'motor-fixed-{i}',frame='J1.rotor',x_mm=(fixed+delta)[0],y_mm=(fixed+delta)[1],z_mm=(fixed+delta)[2],axis_x=normal[0],axis_y=normal[1],axis_z=normal[2],diameter_mm=4.5,depth_mm=12,additional_feature='FrontD9.8 counterboredepth4; bolt grip8 remains'))
    for i,(x,y) in enumerate([(x,y) for x in [-38,38] for y in [-28,28]],1):features.append(dict(id=f'foot-M5-clearance-{i}',frame='J1.rotor',x_mm=x,y_mm=y,z_mm=30,axis_x=0,axis_y=0,axis_z=1,diameter_mm=5.6,depth_mm=8,additional_feature='Unchanged shoulder-foot bolt stations'))
    for angle in [45,135,225,315]:
        a=np.radians(angle);features.append(dict(id=f'cover-seat-{angle}',frame='J1.rotor',x_mm=64*np.cos(a),y_mm=68.5,z_mm=114+64*np.sin(a),axis_x=0,axis_y=-1,axis_z=0,diameter_mm=3.5,depth_mm=8,additional_feature='Original8mm seat beneath radial open pocket in added4mm layer'))
    with (PACK/'root22-hole-coordinates.csv').open('w') as fp:
        writer=csv.DictWriter(fp,fieldnames=list(features[0]));writer.writeheader();writer.writerows(features)
    for name in ['manifest.json','review20.json','linear-fea18.json']:
        shutil.copy2(OUT/name,PACK/name)
    if (OUT/'quadratic23.json').exists():
        q=json.loads((OUT/'quadratic23.json').read_text());assert q['source_manifest_sha256']==c.sha(path);shutil.copy2(OUT/'quadratic23.json',PACK/'quadratic23.json')
    (PACK/'README.md').write_text('''# A19 ROOT22两件局部试配包

这是肩部L支架及其下护罩的局部收敛候选，保持B06同源底座、原有轴位置和原紧固件。不是完整新腕部整臂制造包，也不是金属生产放行版。

支架固定面从8增加到12 mm；原厂固定螺钉位置采用Ø9.8、深4沉孔，继续使用原M4×12、0.8 mm垫圈及3.2 mm旋入，不将螺钉头推向J3。外罩四个原安装座位于四个Ø12刀具形成的开放径向槽内，仍保留8 mm原座厚度及原M3五金。脚板厚8、内根R6，金属候选为常规单件铣削，没有增加传动机构或焊接。

两件STEP和落床STL是一一对应的新件；替换原A16-C04-J2-mount-plate及A17-C04-J2-cowl-b。其余零件、上罩和五金按A18完整装配包，不混入本目录的研究失败件。先支撑并断开电源，再拆罩和肩部原固定螺钉；核对真实电机孔深后，装支架并恢复原螺钉，最后安装下罩。不能用未测打印件承载整臂自重。

64个有限姿态的新件检查无大于0.08mm³相交；不代表整臂全域、底座内件、线束、公差、工具插拔或实际装配通过。三组直边四面体线性有限元使用A18旧质量的四个静重力载荷；四个理想刚性垫圈支承，不包含接触、滑移、螺钉预紧、动力、气弹簧支座、疲劳、新J5增加的质量或桌夹柔度。网格细化及独立反力／能量核对见报告，奇异边缘峰值应力不能用作生产材料验收。

SVG是原STEP的三向投影和名义特征说明，孔坐标CSV与STEP共同定义几何；尚未发行金属加工公差及GD&T、供应商CAM或检验放行图。当前打印只用于外部支撑下、断电、无载试配。塑料与金属不是同一强度等级。
''')
    hashes={p.name:c.sha(p) for p in PACK.iterdir() if p.is_file() and p.name!='SHA256SUMS.json'};(PACK/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('ROOT_PACK24',len(hashes),flush=True)
if __name__=='__main__':main()
