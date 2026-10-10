# SPDX-License-Identifier: CC-BY-NC-4.0
"""Issue only two unpowered IF09 fit parts, with source hashes and nominal PDF."""
from pathlib import Path
import json, shutil, zipfile, sys
import cadquery as cq
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/contacts09'
PACK=ROOT/'manufacturing/candidates/arm-a18-contact09'
sys.path.insert(0,str(ROOT/'engineering/arm_a16'));import common as c

def main():
    d=json.loads((OUT/'manifest.json').read_text());assert d['review']['sampled_clear']
    for path,digest in d['sources'].items():assert c.sha(ROOT/path)==digest,path
    PACK.mkdir(parents=True,exist_ok=True)
    for folder in ['step','print-bed','nominal-PCB-mechanical-only']:(PACK/folder).mkdir(exist_ok=True)
    for name in ['manifest.json','pin-map.csv']:shutil.copy2(OUT/name,PACK/name)
    # Exact nominal own PCB shape is retained for fit, explicitly NOT Gerbers.
    for p in d['parts']:
        assert c.sha(ROOT/p['step_path'])==p['step_sha256']
        if p['role']=='PCB_geometry_only':shutil.copy2(ROOT/p['step_path'],PACK/'nominal-PCB-mechanical-only'/Path(p['step_path']).name)
    pdf=canvas.Canvas(str(PACK/'two-part-contact-fit-drawings.pdf'),pagesize=landscape(A3))
    pdf.setTitle('IF09 contact insert and mating distance gauge - unpowered fit only')
    def text(x,y,t,size=9):pdf.setFont('Helvetica',size);pdf.drawString(x*mm,y*mm,t)
    for page,id in enumerate(d['printed_parts'],1):
        p=next(x for x in d['parts'] if x['id']==id);f=ROOT/p['step_path'];s=cq.importers.importStep(str(f)).val()
        shutil.copy2(f,PACK/'step'/f.name)
        stl=OUT/'print-bed'/(id+'.stl');assert c.sha(stl)==p['print_bed_sha256'];shutil.copy2(stl,PACK/'print-bed'/stl.name)
        bb=s.BoundingBox();lo=np.array([bb.xmin,bb.ymin,bb.zmin]);hi=np.array([bb.xmax,bb.ymax,bb.zmax])
        curves=[np.array([e.positionAt(float(t)).toTuple() for t in np.linspace(0,1,2 if e.geomType()=='LINE' else 80)]) for e in s.Edges()]
        pdf.setLineWidth(.12*mm);pdf.rect(10*mm,10*mm,400*mm,277*mm)
        text(16,276,id,16);text(16,263,'IF09 | mm | J7.rotor local coordinates | supported, unpowered, unloaded',10)
        text(16,254,'Nominal fit drawing. All CAD edges shown; hidden edges not distinguished. Not a production GD&T drawing.',9)
        for i,(label,axes) in enumerate([('YZ / tool face',(1,2)),('XZ / side',(0,2)),('XY / top',(0,1))]):
            origin=np.array([22+132*i,134]);span=(hi-lo)[list(axes)];scale=min(1,105/max(span[0],1),100/max(span[1],1))
            text(origin[0],244,label,10)
            for e in curves:
                points=(e[:,axes]-lo[list(axes)])*scale+origin;path=pdf.beginPath();path.moveTo(*(points[0]*mm))
                for pt in points[1:]:path.lineTo(*(pt*mm))
                pdf.drawPath(path)
            text(origin[0],128,f'BREP extents {span[0]:.3f} x {span[1]:.3f}; scale {scale:.3f}',8)
        lines=(
          ['Insert body: nominal D52, X103..106; local rear bosses extend to X100.',
           'Original mounting: 2x D3.5 through at Y=-29/+29, Z=0; retain existing M3 hardware.',
           'Camera windows: 2x11.6 square, centres (Y,Z)=(-9,-12)/(9,-12); HFM retention NOT released.',
           'PCB pocket: 34.4 x18.4, Y=-17.2..17.2, Z=-0.2..18.2; floor X104.4, nominal depth1.6.',
           'Arm PCB mounts: 2xD2.7 at Y=-14/+14, Z=9; rear nut pockets AF5.2, X100..102.2.',
           'Rear wire slot: 10 x3 at Y=-5..5, Z=7.5..10.5; solder/cable retention pending.']
          if page==1 else
          ['TEST FIXTURE ONLY: nominal OD86, X110..114.6; not the four-petal tool or a load-rated adaptor.',
           'Recess: nominal female D76.2, X110..112.2; nominal diametral gap0.2 to arm D76 pilot.',
           'Mechanical screw holes: 4xD4.5 through, PCD72, phase45deg; D3.3 key at Y=0,Z=31.',
           'Tool PCB supports at X111.6; mounts2xD2.7 at Y=-14/+14,Z=3 (offset from arm Z9).',
           'Rear nut pockets AF5.2, X112.4..114.6; same nominal M2.5x6 screws, tips exit rear.',
           'Tool PCB pin mounting plane X110; arm pads X106; nominal working height4/free5.'])
        for i,line in enumerate(lines):text(16,112-10*i,line,9)
        text(16,45,'Both parts need slicer support review. Protect pilots, PCB seats and screw holes; print fit coupons first.',9)
        text(16,35,'Only plastic101/102 may be printed. PCB, pins and standard fasteners must not be printed.',9)
        text(16,25,'No electrical release: no PCB routing, no pin travel qualification, no GMSL mating/EMI qualification.',9)
        text(16,15,f'IF09  |  page {page}/2  |  production_release=false  |  source SHA in manifest.json',8);pdf.showPage()
    pdf.save()
    readme='''# IF09 接触接口试配包

这是独立候选包，不覆写A16或A17打印包。保留裸臂工具机械面X110、Ø76定位、Ø54中央空间、四M4 PCD72相位45°及唯一定位销。仅以101接触板替换旧A13-IF-303，102为工具端接触距离量规，不能作为承载末端使用。

## 包中可用内容

- `step/`：两件名义塑料CAD。
- `print-bed/`：两件毫米贴床STL；坐标变换见manifest。
- `two-part-contact-fit-drawings.pdf`：两页名义投影与关键坐标，不是金属公差／GD&T生产图。
- `nominal-PCB-mechanical-only/`：板厚与安装孔试配包络；没有电气布线、Gerber或板厂发行。
- `pin-map.csv`：十针功能与位置草案；电压未冻结，TOOL_ENABLE不是认证安全回路。

## 装配与试配

1. 固定并支撑机械臂，切断工具供电、相机PoC及关节电源，移除工具。保留原法兰、轴承、M4和定位销。
2. 打印101和102前检查切片：PETG／PA12，0.4mm喷嘴、0.2mm层高、4圈壁、30%填充为起点；101的主体从两只后凸台上方形成，102桥板形成跨越，两者都需要支持检查。打印方向有意保留关节X轴垂直打印床，不是已经通过切片的最优方向。不能仅凭网格闭合就跳过支撑。
3. 去掉支撑，检查Ø76.2量规、面板两M3孔、两相机窗口、板座和螺母口；孔径受材料／打印机影响，按实测修整，不用强拧螺钉把塑料拉到位。
4. 101背面先装两M2.5螺母，装入34x18x1.6mm的臂侧板样，用两M2.5x6螺钉固定，孔中心Y±14/Z9。以原M3硬件装回腕仓，检查服务螺钉操作空间。
5. 102背面装两M2.5螺母，工具侧板孔中心Y±14/Z3，和臂侧孔错开6mm，避免对向螺钉头相撞。工具侧弹簧针基面X110；十触点名义工作高4mm，臂侧焊盘X106。
6. 接合量规并检查机械硬止挡、针压缩和焊盘对准。普通相机插头仍需在服务仓中手动插拔；外形包络未确认锁扣保持，禁止硬推盲插。

名义压缩1mm。假设工艺叠加±0.45mm后范围0.55..1.45mm，这不是原厂允许行程证明；最终必须核对弹簧针最大工作行程、力值、安装高度和PCB实测厚度。打印粗精度不能当作量产公差。

本包只允许有外部支撑、断电、无工具载荷的尺寸试配。两针并联不自动提高额定电流；未来低功率触点试样整个工具支路先限流1A，须在独立保护试验台上完成，不在未放行臂上直接通电。GMSL2不走普通触点。真实同轴、锁扣、弯曲半径、释放空间、屏蔽、误码、PoC与连接器寿命仍需验证。
'''
    (PACK/'README.md').write_text(readme)
    native=OUT/'native-audit.json'
    if native.exists():
        audit=json.loads(native.read_text());assert audit['manifest_sha256']==c.sha(OUT/'manifest.json')
        shutil.copy2(native,PACK/native.name)
        for name,h in audit['images'].items():
            file=OUT/(name+'.png');assert c.sha(file)==h;shutil.copy2(file,PACK/file.name)
    files={str(p.relative_to(PACK)):c.sha(p) for p in sorted(PACK.rglob('*')) if p.is_file() and p.name not in ['SHA256SUMS.json','IF09-supported-unpowered-fit.zip']}
    (PACK/'SHA256SUMS.json').write_text(json.dumps(files,indent=2)+'\n')
    zipfile_path=PACK/'IF09-supported-unpowered-fit.zip'
    with zipfile.ZipFile(zipfile_path,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(PACK.rglob('*')):
            if path.is_file() and path!=zipfile_path:z.write(path,str(path.relative_to(PACK)))
    with zipfile.ZipFile(zipfile_path) as z:
        assert z.testzip() is None
        for name,h in files.items():
            import hashlib
            assert hashlib.sha256(z.read(name)).hexdigest()==h
    print('IF09_PACK_DONE',len(files),'files',flush=True)

if __name__=='__main__':main()
