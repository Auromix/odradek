# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Original EXT24 dimensioned drawing and machine-readable QA; no vendor CAD export."""
from pathlib import Path
import json,hashlib,math,csv,argparse
import numpy as np
import cadquery as cq
import trimesh,ezdxf
from pypdf import PdfReader
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from draw_layout import Sheet,TEAL,GRAY,NAVY
from wrist_extension_study import ROOT,OUT,sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rh17-step',type=Path,required=True);args=ap.parse_args()
    e=json.loads((OUT/'study.json').read_text());proof=e['continuous_head_to_wrist']
    assert not e['errors'] and proof['head_to_wrist_certified']
    assert e['generator_sha256']==sha(ROOT/'engineering/wrist_extension_study.py')
    for name,h in e['source_hashes'].items():assert sha(ROOT/name)==h,name
    # J5 housing precedes q5, whereas the head/L56/J6 follow q5. Verify its
    # rotationally invariant cylinder before extending the q6 plane proof to q5.
    from mount_interface_study import load_vendor
    from build_layout import frame,moved
    import p16_carrier_study as cs
    assert sha(args.rh17_step)==e['private_vendor_hashes']['RH17']
    model=next(x for x in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models'] if x['id']=='RH17-B')
    j5=moved(load_vendor(args.rh17_step,model),frame([0,-55,450],[0,0,1]));b=j5.BoundingBox()
    q5env=cs.C(42.1,b.zmax-b.zmin,(0,-55,b.zmin),(0,0,1))
    outside=[sum(x.Volume() for x in so.cut(q5env).Solids()) for so in j5.Solids()]
    assert max(outside)<1e-4 and b.zmax<605 and -55+42.1<2.1
    q5={'source_vendor_sha256':sha(args.rh17_step),'source_solids':len(outside),'outside_by_solid_mm3':outside,
      'envelope_axis_world':[0,0,1],'envelope_center_XY_mm':[0,-55],'radius_mm':42.1,'world_Z_range_mm':[b.zmin,b.zmax],
      'q5_interval_deg':[-90,90],'nominal_head_to_wrist_extension_valid':True,
      'proof':'The actual J5 housing fits a coaxial cylinder invariant under inverse q5. Its entire Z range is below J6 and |X|<=42.1, hence it remains inside the lower support strip for every q5. Its Ymax=-12.9 also preserves the adapter/bolt positive-Y separation. L56/J6 and head share q5, so their mutual q6/q7 proof is unchanged. Upstream geometry is not included.'}
    path=OUT/'ODR-J7-EXT24.step';solid=cq.importers.importStep(str(path)).val()
    assert solid.isValid() and len(solid.Solids())==1
    mesh=trimesh.load_mesh(OUT/'ODR-J7-EXT24.stl',process=True);assert mesh.is_watertight
    holes=[(30,0),(0,30),(-30,0),(0,-30)]
    doc=ezdxf.new('R2010');doc.units=ezdxf.units.MM;ms=doc.modelspace()
    for d in [70,52]:ms.add_circle((0,0),d/2)
    for xy in holes:ms.add_circle(xy,2.25)
    ms.add_lwpolyline([(-35,-65),(35,-65),(35,-41),(-35,-41)],close=True)
    for x in [-26,26]:ms.add_line((x,-65),(x,-41))
    for x in [-32.25,-27.75,-2.25,2.25,27.75,32.25]:ms.add_line((x,-65),(x,-41),dxfattribs={'linetype':'CONTINUOUS'})
    ms.add_text('ODR-J7-EXT24 / mm / FIT STUDY; NOT PRODUCTION / SEE PDF',dxfattribs={'height':2.3}).set_placement((-35,-74))
    dp=OUT/'ODR-J7-EXT24.dxf';doc.saveas(dp);assert not ezdxf.readfile(dp).audit().errors
    with (OUT/'hole-features.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['feature','x_mm','y_mm','diameter_mm','z_start_mm','depth_mm'])
        w.writerow(['central_through',0,0,52,0,24])
        for i,(x,y) in enumerate(holes):w.writerow([f'M4_clearance_{i+1}',x,y,4.5,0,24])
    # Ideal prismatic net section; this does not include local hole contact,
    # bolt preload/prying or aluminum threads in the adjoining adapter.
    A=math.pi*(35**2-26**2)-4*math.pi*2.25**2
    I=math.pi/4*(35**4-26**4)-4*math.pi*2.25**4/4-2*math.pi*2.25**2*30**2
    F=1.5*9.80665*6.5
    M=1.5*9.80665*(4.5*(.134+.05)+2*(.264+.1))
    sec={'cut_world_Z_mm':650,'area_mm2':A,'Ixx_Iyy_mm4':I,'case_head_kg':4.5,'case_head_COM_world_mm':[0,55,784],
      'case_object_kg':2,'case_object_COM_world_mm':[0,55,914],'head_COM_allowance_mm':50,'object_COM_allowance_mm':100,
      'study_factor':1.5,'force_N':F,'bending_Nm':M,'ideal_extreme_normal_stress_MPa':F/A+M*1000*35/I,
      'equal_stiffness_bolt_max_external_axial_N':F/4+M*1000/60,
      'scope':'Sensitivity load case only; ideal net section and equal-stiffness rigid bolt group. Not preload, contact opening, prying, thread pull-out, torsion, fatigue, material allowables, thermal or physical qualification.'}
    pdfmetrics.registerFont(TTFont('EXTCN','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
    pdf=OUT/'ODR-J7-EXT24-candidate-dimensions.pdf';c=canvas.Canvas(str(pdf),pagesize=landscape(A3));s=Sheet(c,'EXTCN')
    c.setTitle('Odradek EXT24 original dimensions and continuous wrist envelope study');c.setAuthor('Auromix contributors')
    def txt(x,y,lines,size=9):
        for i,t in enumerate(lines):s.text(x,y-7*i,t,size)
    def footer(n):
        s.line((15,19),(405,19),GRAY,.4);s.text(15,12,'单位mm | 原创结构 | 6061-T6候选 | 名义设计评审图，未放行制造/承载',8);s.text(405,12,f'{n}/2 | WRIST-EXTENSION-01',8,align='right');c.showPage()
    s.header('J7 末端加高环 / ODR-J7-EXT24','A：后端面Z0；B：中心轴；C：+X孔方向。所有坐标为零件坐标，名义尺寸。','EXT24-01')
    origin=np.array([99,197.]);scale=1.65
    for r in [35,26]:s.circle(origin,r*scale,TEAL,.65)
    for xy in holes:s.circle(origin+np.array(xy)*scale,2.25*scale,TEAL,.55)
    s.line((30,197),(169,197),GRAY,.25,dash=[2,2]);s.line((99,131),(99,262),GRAY,.25,dash=[2,2])
    s.arrow([132,239],[139.84,237.84]);s.text(126,246,'Ø70',10)
    s.arrow([73.,180.],[69.,167.]);s.text(44,171,'Ø52 贯通',10)
    # XZ nominal side projection, edges/cut surfaces use exact circle extrema.
    oy=77
    for a,b in [([-35,0],[35,0]),([35,0],[35,24]),([35,24],[-35,24]),([-35,24],[-35,0])]:s.line(np.array(a)*scale+[99,oy],np.array(b)*scale+[99,oy],TEAL,.65)
    for x in [-26,26]:s.line([99+x*scale,oy],[99+x*scale,oy+24*scale],GRAY,.35,dash=[2,2])
    s.line([169,oy],[169,oy+24*scale],GRAY,.4);s.arrow([169,oy+12*scale],[169,oy]);s.arrow([169,oy+12*scale],[169,oy+24*scale]);s.text(173,oy+12*scale,'24',10)
    txt(206,249,['材料候选：6061-T6，单件环状毛坯铣/车组合加工。','外径Ø70；中心贯通Ø52；厚24。','4×Ø4.5贯通，PCD60：','(X,Y)=(30,0)、(0,30)、(−30,0)、(0,−30)。',
      '孔内缘至中心孔最薄名义径向壁1.75；外侧2.75。','去锐边/表处/平面度/平行度/孔位置度待公差链冻结。','当前STEP未用螺纹模型代替通孔。','安装世界Z650…674，中心X0/Y55。','原J7转轴仍在世界[0,55,640]，轴向+Z。','原10mm转接盘保持原位；整头其余零件前移24。',
      '夹紧链：环24 + 主载体8 + 垫圈0.8 = 32.8。','4×M4×40，名义进入原转接盘7.2。','候选Accu SSC-M4-40-12.9；最小牙长20。','螺帽最大Ø7.22×4，内六角3；目录单颗4.7g。','有效完整牙、预紧、锁固与工具包络仍需合并复核。'],8.5)
    txt(206,130,[f'环体积估重 {e["spacer"]["mass_g"]:.3f} g；密度2.7g/cm³。',f'环两端名义接触面积 {e["contact_areas_mm2"]["adapter_spacer"]:.3f} mm²。',
      f'已建头部质量 {e["mass"]["modeled_g"]:.3f} g；新增 {e["mass"]["increase_vs_carrier01_g"]:.3f} g。',f'未建件预算后 {e["mass"]["planning_head_mass_range_g"][0]/1000:.3f}…{e["mass"]["planning_head_mass_range_g"][1]/1000:.3f} kg。',
      '预算不等于实重；原厂件质心使用几何代理。','面中心迁至[0,55,804]；旧示例TCP迁至[0,55,914]。','接触TCP应按物体另定；未改主参数/历史Blender。'],8.5)
    txt(25,43,['DXF为毫米投影线稿；STEP为名义实体。尺寸公差、装配变形及整机验证未冻结，不能直接认定可带2kg运行。'],8.2);footer(1)
    s.header('连续腕部避让范围与截面研究','原P16-CARRIER01主架在q7=±90°与J6碰撞；本页仅说明加高后的明确检查范围。','EXT24-01')
    # XZ support bound illustration, representative only, labels preserve mm.
    center=np.array([101,203]);k=.65;R=42.1
    for a,b in [([-R,-80],[-R,0]),([R,-80],[R,0]),([-R,-80],[R,-80])]:s.line(np.array(a)*k+center,np.array(b)*k+center,TEAL,.7)
    pts=[center+k*R*np.array([math.cos(q),math.sin(q)]) for q in np.linspace(0,math.pi,100)]
    for a,b in zip(pts,pts[1:]):s.line(a,b,TEAL,.7)
    h=proof['minimum_head_Z_in_q6_zero_frame_mm']-605
    s.line([36,center[1]+k*h],[172,center[1]+k*h],NAVY,.7)
    s.line([36,center[1]+k*R],[172,center[1]+k*R],GRAY,.3,dash=[2,2])
    s.circle(center,1,NAVY,.5);s.text(108,196,'J6轴(+Y)',9);s.text(47,246,f'头部 Z−605 ≥ {h:.3f}',9);s.text(44,141,'固定结构包含域：下部|X|≤42.1；上部半圆R42.1',8)
    txt(206,251,[f'静止J5/J6/L56共 {len(proof["stationary_containment"])} 组真实实体逐件减去包含域：外逸均0。',
      'q6在[−90°,90°]时cos(q6)≥0。','将固定件变换到腕部坐标：Z′−605 = X·sin(q6)+(Z−605)·cos(q6)。','下部条带与上部半圆的支持函数均≤42.1。','q7绕+Z旋转不改变头部Z；四指独立角域分别求界。',
      f'新头部全角最低Z {proof["minimum_head_Z_in_q6_zero_frame_mm"]:.6f}。',f'因此头部对上述固定腕/前臂的连续下界 {proof["head_to_stationary_arm_lower_bound_mm"]:.6f} mm。',
      f'对同随q6转动的L67/J7，轴向分离下界 {proof["head_to_L67_J7_axial_lower_bound_mm"]:.6f} mm。','低位盘/长螺钉以恒定Y分离及完整圆柱扫掠对L67独立核查。',
      '上指q=0…109°；下指q=0…122°；q7=−90…90°。','J5原厂34实体另含于R42.1旋转不变圆柱，覆盖q5=−90…90°。','此处q6只证明−90…90°；原研究±100°的外侧10°仍未证明。','45个主架/J6离散样本没有交集，不补成外侧角域证明。'],8.0)
    txt(24,126,['该图是包含域示意，不是原厂零件轮廓。','指根用包围盒角点正弦极值；推杆用1°网格及点速度上界补足区间。','全臂、腕连接自身转动、对象、灯板、线束、外甲、公差和变形不在证明内。','原J7转接盘与输出转子的预定配合另沿用原接口研究。'],8.2)
    txt(206,155,[f'环净面积 A={A:.3f} mm²；Ixx=Iyy={I:.3f} mm⁴。',
      '敏感性例：4.5kg头部COM Z784，2kg物体COM Z914；','质心另加50/100mm不确定量，静载研究倍率1.5。',
      f'后端Z650截面合力 {F:.3f} N，力矩 {M:.3f} Nm。',f'理想净截面F/A+Mc/I = {sec["ideal_extreme_normal_stress_MPa"]:.3f} MPa。',
      f'四颗等刚度螺钉：最大外载轴向需求 {sec["equal_stiffness_bolt_max_external_axial_N"]:.3f} N/颗。','这些数值不含预紧/撬力/螺纹拉脱/接触开缝/疲劳，不是强度通过。','本研究增加了臂长和质量，后续整机动力学需重新集成。'],8.3)
    txt(24,38,['逐实体检查阈值1e−4mm³；所有来源哈希、质量明细、解析参数及角域在study.json；非硬件测试结果。'],8.3);footer(2);c.save();assert len(PdfReader(pdf).pages)==2
    qa={'revision':'WRIST-EXTENSION-01','drawing_generator_sha256':sha(Path(__file__)),'study_sha256':sha(OUT/'study.json'),
      'STEP':{'valid':True,'solids':1,'volume_mm3':solid.Volume()},'STL':{'watertight':True,'volume_relative_error':abs(mesh.volume-solid.Volume())/solid.Volume()},'DXF':{'units':'mm','audit_errors':0},'PDF':{'pages':2},
      'J5_q5_extension':q5,'net_section_study':sec,'files_sha256':{p.name:sha(p) for p in OUT.iterdir() if p.suffix in ['.step','.stl','.pdf','.csv','.dxf']}}
    (OUT/'drawing-qa.json').write_text(json.dumps(qa,indent=2)+'\n');print(json.dumps({k:v for k,v in qa.items() if k not in ['files_sha256','net_section_study']},indent=2))

if __name__=='__main__':main()
