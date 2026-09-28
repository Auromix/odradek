# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-WRIST-EROB01: original eRob70I V5 output / removable-head interface study.
Vendor STEP is a local, hash-checked command-line input and is NEVER exported.
All CAD is mm; mechanics N/mm/MPa unless explicitly marked SI. No production release.
"""
from pathlib import Path
import argparse, hashlib, json, math, csv
import cadquery as cq
import numpy as np
import trimesh, ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.BRepGProp import BRepGProp
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from draw_central_display01 import section, curves, dxf_geometry, Sheet, INK, BLUE, GREY
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-wrist-erob01'
SOURCE=ROOT/'docs/engineering/sources/r5-wrist-erob01.json'
X0=-9.774999898159106
OEM_ANGLES=[0,30,90,120,180,210,270,300]
OEM_RELIEF_ANGLES=[15,75,135,195,255,315]
HEAD_ANGLES=[45,135,225,315]
RHO=2700e-9  # kg/mm3: explicit 6061 nominal density assumption

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_json(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def polar(r,angles):return [(r*math.cos(math.radians(t)),r*math.sin(math.radians(t))) for t in angles]
def cyl(r,z,h,xy=(0,0)):return cq.Solid.makeCylinder(r,h,cq.Vector(*xy,z))
def cone(r1,r2,z,h,xy=(0,0)):return cq.Solid.makeCone(r1,r2,h,cq.Vector(*xy,z))
def bb(s):
 b=Bnd_Box();BRepBndLib.AddOptimal_s(s.wrapped,b,False,False);a=b.Get();return [list(a[:3]),list(a[3:])]
def volume(s):return abs(s.Volume())
def contact_area(a,b,t=.0001):return volume(a.intersect(b.translate((0,0,t))))/t

def adapter(gauge=False):
 # Actual CAD major-diameter thread cylinders are NOT drill diameters.
 a=cyl(38,0,8).fuse(cyl(30,-6.5,6.5))
 bore=25.2 if gauge else 25
 a=a.cut(cyl(bore,-6.51,6.51))
 root_edge=[e for e in a.Edges() if abs(e.Length()-2*math.pi*bore)<1e-5 and abs(e.Center().z)<1e-5]
 assert len(root_edge)==1
 a=a.fillet(.1,root_edge)
 # Rear female-register lead-in chamfer; full fit is retained to z=-6.2.
 a=a.cut(cone(bore+.3,bore,-6.5,.3))
 a=a.cut(cyl(9.2 if gauge else 9,-7,16))
 a=a.cut(cyl(19.6 if gauge else 19.5,-.01,.51 if gauge else .31))
 # Unloaded printed gauge deliberately has large clearances, not a metal-fit test.
 for xy in polar(22,OEM_ANGLES):
  r=1.9 if gauge else 1.7
  a=a.cut(cyl(r,-.01,8.02,xy)).cut(cyl(3.1,4.6,3.41,xy))
  a=a.cut(cone(r,r+.2,4.4,.2,xy)) # head-underfillet clearance
 for xy in polar(22,OEM_RELIEF_ANGLES):a=a.cut(cyl(2.8,-.01,.51,xy))
 for xy in polar(32,HEAD_ANGLES):
  r=2.25 if gauge else 2
  a=a.cut(cyl(r,-.01,8.02,xy))
  a=a.cut(cone(r,r+.25,7.75,.25,xy)).cut(cone(r+.25,r,0,.25,xy))
 for y in [-32,32]:a=a.cut(cyl(1.6 if gauge else 1.5,-6.51,14.52,(0,y)))
 # Outer edges of blank remain sharp nominally; deburr without changing register/lands.
 return a.clean()

def mate(gauge=False):
 a=cyl(38,8,4).cut(cyl(9.2 if gauge else 9,7.99,4.02))
 for xy in polar(32,HEAD_ANGLES):
  a=a.cut(cyl(2.25,7.99,4.02,xy)).cut(cone(2.25,2.5,11.75,.25,xy))
 # One round + one radial slot: avoids two-round-hole overconstraint.
 a=a.cut(cyl(1.65 if gauge else 1.51,7.99,4.02,(0,32)))
 a=a.cut(cq.Workplane('XY').workplane(offset=7.99).center(0,-32).slot2D(5,3.3 if gauge else 3.02,90).extrude(4.02).val())
 return a.clean()

def vendor_features(v_native):
 planes=[];cyls=[];pilots=[]
 for i,f in enumerate(v_native.Faces()):
  a=BRepAdaptor_Surface(f.wrapped);b=f.BoundingBox()
  if a.GetType()==GeomAbs_Cylinder:
   c=a.Cylinder();d=c.Axis().Direction();p=c.Location()
   if abs(d.X())>.999999 and math.hypot(p.Y(),p.Z())<1e-5 and any(abs(c.Radius()-r)<1e-5 for r in [9,24.8,25]):
    pilots.append(dict(face_index=i,radius_mm=c.Radius(),z_interval_mm=sorted([X0-b.xmax,X0-b.xmin])))
   if abs(d.X())>.999999 and abs(math.hypot(p.Y(),p.Z())-22)<.001:
    cyls.append(dict(face_index=i,radius_mm=c.Radius(),centre_xy_mm=[p.Y(),-p.Z()],z_interval_mm=sorted([X0-b.xmax,X0-b.xmin]),area_mm2=f.Area()))
  elif a.GetType()==GeomAbs_Plane:
   p=a.Plane();d=p.Axis().Direction()
   if abs(d.X())>.999999 and f.Area()>1 and X0-p.Location().X()>-18:
    planes.append(dict(face_index=i,z_mm=X0-p.Location().X(),area_mm2=f.Area()))
 observed=sorted([(math.degrees(math.atan2(r['centre_xy_mm'][1],r['centre_xy_mm'][0]))%360) for r in cyls if abs(r['radius_mm']-1.8)<1e-5 and abs(r['z_interval_mm'][1])<1e-5])
 assert len(observed)==8
 relief=[r for r in cyls if abs(r['radius_mm']-2.5)<1e-5 and abs(r['z_interval_mm'][1])<1e-5];assert len(relief)==6
 for t in OEM_RELIEF_ANGLES:
  assert min(abs((math.degrees(math.atan2(r['centre_xy_mm'][1],r['centre_xy_mm'][0]))-t+180)%360-180) for r in relief)<1e-7
 assert any(abs(r['radius_mm']-25)<1e-5 and abs(r['z_interval_mm'][1]+4.4)<1e-5 for r in pilots)
 for t in OEM_ANGLES:assert min(abs((a-t+180)%360-180) for a in observed)<1e-7
 return dict(native_output_face_x_mm=X0,transform='joint X=native Y; joint Y=-native Z; joint Z=X0-native X',rotation_determinant=1,output_mount_hole_angles_deg=OEM_ANGLES,matched_native_cylinders=cyls,centred_pilot_and_bore_cylinders=pilots,axial_planes=planes)

def loads(parts):
 g=9.80665;F=3.5*g;M=(2*.2+1.5*.1)*g*1000
 groups={}
 for name,xy in [('OEM8',polar(22,OEM_ANGLES)),('HEAD4',polar(32,HEAD_ANGLES))]:
  P=np.array(xy);P-=P.mean(axis=0);S=P.T@P;inv=np.linalg.inv(S)
  # Axial bolt-group linear elastic increments from arbitrary azimuth bending.
  gains=np.linalg.norm(P@inv,axis=1);fmax=M*gains
  groups[name]=dict(xy_mm=xy,centroid_mm=np.mean(xy,axis=0).tolist(),S_mm2=S.tolist(),M_Nmm=M,max_per_bolt_axial_increment_N=float(fmax.max()),per_bolt_arbitrary_azimuth_N=fmax.tolist(),equal_direct_transverse_share_N=F/len(xy),conditions='Rigid equal-stiffness group, balanced compression/contact, no prying. Not total screw tension or preload. Transverse share is a separate idealization; no friction capacity asserted.')
 slabs=[]
 for name,z in [('adapter',-5),('adapter',.15),('adapter',.65),('adapter',4.7),('adapter',7.7),('mate',10)]:
  dz=.002;s=parts[name].intersect(cq.Solid.makeBox(100,100,dz,cq.Vector(-50,-50,z-dz/2)))
  prop=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,prop);im=prop.MatrixOfInertia();A=prop.Mass()/dz
  # Area second moment tensor for axial bending. Remove slab z-thickness term.
  I=np.array([[im.Value(1,1),im.Value(1,2)],[im.Value(2,1),im.Value(2,2)]])/dz-np.eye(2)*A*dz*dz/12
  lam=np.linalg.eigvalsh(I);rmax=38 if z>0 else 30
  slabs.append(dict(part=name,z_mm=z,area_mm2=A,centroid_mm=list(prop.CentreOfMass().Coord()),inertia_area_tensor_mm4=I.tolist(),lambda_min_mm4=float(lam.min()),section_radius_bound_mm=rmax,axial_section_nominal_stress_bound_MPa=M*rmax/float(lam.min()),conditions='Axial net-section indicator only. Does NOT bound plate radial bending, relief stress concentration, screw prying or bearing contact.'))
 # Independent local strip screen for load transfer from outer head bolt R32 to OEM bolt R22.
 P=groups['HEAD4']['max_per_bolt_axial_increment_N'];L=max(min(math.dist(h,o) for o in polar(22,OEM_ANGLES)) for h in polar(32,HEAD_ANGLES));b=8;t=4.4;E=69000
 strip=dict(assumed_each_strip_width_mm=b,assumed_thickness_mm=t,span_to_nearest_OEM_screw_mm=L,force_N=P,sigma_MPa=6*P*L/(b*t*t),tip_deflection_mm=4*P*L**3/(E*b*t**3),assumed_E_MPa=E,not_a_bound='Selected cantilever strip, ignores ring load sharing and prying. No material allowable or release assigned.')
 return dict(g_m_s2=g,payload_kg=2,head_budget_kg=1.5,payload_offset_m=.2,head_com_offset_m=.1,force_N=F,moment_Nm=M/1000,offset_origin='OEM output contact plane A, not front of new adapter. If offsets start at mate front add F*0.012.',if_offsets_from_mate_face_moment_Nm=M/1000+F*.012,bolt_groups=groups,net_sections=slabs,local_strip=strip,exclusions=['Dynamics/shock/fatigue','In- and out-of-plane plate FEA','Thread stripping/engagement and preload','Dowel retention','OEM bearing moment capability','Actual head/part attachment and moving cable','6061 certified stock, temperature and surface treatment'])

def export_part(name,s):
 assert s.isValid() and len(s.Solids())==1
 step=OUT/'STEP'/(name+'.step');stl=OUT/'STL'/(name+'.stl')
 cq.exporters.export(s,str(step));cq.exporters.export(s,str(stl),tolerance=.01,angularTolerance=.05)
 rs=cq.importers.importStep(str(step)).val();mesh=trimesh.load(str(stl),force='mesh',process=True)
 result=dict(step_sha256=sha(step),stl_sha256=sha(stl),valid=s.isValid(),solids=len(s.Solids()),volume_mm3=volume(s),bbox_mm=bb(s),centre_of_mass_mm=list(s.Center().toTuple()),density_assumption_kg_m3=2700,mass_if_6061_kg=volume(s)*RHO,step_volume_relative_error=abs(volume(rs)-volume(s))/volume(s),mesh_watertight=bool(mesh.is_watertight),mesh_winding_consistent=bool(mesh.is_winding_consistent),mesh_volume_relative_error=abs(mesh.volume-volume(s))/volume(s),mesh_bbox_max_error_mm=float(np.max(np.abs(mesh.bounds-np.array(bb(s))))),stl_chordal_tolerance_mm=.01,stl_angular_tolerance_rad=.05)
 print(name, json.dumps(result),flush=True)
 assert result['step_volume_relative_error']<1e-8 and result['mesh_watertight'] and result['mesh_winding_consistent'] and result['mesh_volume_relative_error']<.001 and result['mesh_bbox_max_error_mm']<.02
 return result

def drawing_dxf(name,views,notes):
 d=ezdxf.new('R2013');d.units=4;d.header['$INSUNITS']=4
 for n,color in [('BOUNDARY',7),('NOTE',3),('DIM',2)]:d.layers.new(n,dxfattribs={'color':color})
 m=d.modelspace()
 for i,(label,cs) in enumerate(views.items()):
  off=(i*100,0);dxf_geometry(m,cs,off)
  m.add_text(label,dxfattribs={'height':2.5,'insert':(off[0]-38,45),'layer':'NOTE'})
 for i,note in enumerate(notes):m.add_text(note,dxfattribs={'height':2.1,'insert':(-38,-50-4*i),'layer':'NOTE'})
 dim=m.add_linear_dim(base=(-38,52),p1=(-38,0),p2=(38,0),angle=0,text='76',dimstyle='EZDXF',override={'dimtxt':2.4,'dimasz':1.4},dxfattribs={'layer':'DIM'});dim.render()
 p=OUT/'DXF'/(name+'.dxf');d.saveas(p);r=ezdxf.readfile(p);assert not r.audit().has_errors
 return dict(sha256=sha(p),units_mm=r.units==4,audit_errors=0)

class Page(Sheet):
 def header(self,n,title,sub):
  self.text(14,282,'ODRADEK / R5-WRIST-EROB01',18);self.text(405,282,f'{n} / 4',10,align='right')
  self.text(14,271,title,12,BLUE);self.text(405,271,sub,9,align='right');self.line((14,266),(406,266),BLUE,.8)
 def footer(self,n):
  self.line((14,20),(406,20),GREY,.5);self.text(14,13,'mm / A3 | 原创名义几何与条件载荷研究 | 未制造放行 | 打印件仅无电、无载试装',8);self.text(406,13,f'2026-09-27 / {n}',8,align='right')

def pdf(parts,views,study):
 path=OUT/'ODR-R5-WRIST-EROB01.pdf';c=canvas.Canvas(str(path),pagesize=landscape(A3));c.setTitle('Odradek R5 eRob70I V5 detachable head interface study');s=Page(c)
 s.header(1,'A01 / 原厂接口与原创装配基准','真实原创剖面 3:1；坐标均为统一 joint frame')
 for name,col in [('adapter',BLUE),('mate','#7F8C44')]:s.geo(curves(section(parts[name],'XZ',0),'XZ'),(143,156),3,col,.85)
 for y in [-32,32]:
  # Pins are on the Y axis; not in the Y=0 section. List their position explicitly.
  pass
 s.line((20,156),(266,156),GREY,.3,[6,2,1,2]);s.line((143,117),(143,202),GREY,.3,[6,2,1,2])
 s.text(16,250,'A-A / Y=0；视图横轴=X、纵轴=Z；不含原厂CAD曲线',10,BLUE)
 s.dim_h(29,257,213,180,180,'Ø76')
 s.dim_h(68,218,127,136.5,136.5,'Ø50 +0.016/0 后伸母止口')
 s.dim_v(136.5,156,270,233,'6.5')
 s.dim_v(156,180,281,257,'8.0')
 s.dim_v(180,192,292,257,'4.0')
 s.lead((143+19.5*3,156.9),(218,222),(234,222),'Ø39 × 0.3 禁承力避空')
 s.lead((143+9*3,174),(205,239),(235,239),'Ø18 贯通（线束未放行）')
 s.lead((143+25*3,143),(204,108),(230,108),'裙OD60；后口C0.3 / 内根R0.1')
 s.text(305,249,'基准与安装面',11,BLUE)
 s.rows(305,238,['A：OEM输出接触面 Z=0','B：Ø50止口轴线','+Z：输出/头部方向','+X = 原厂 native +Y','+Y = 原厂 native -Z','原点native X=-9.775','旋转det=+1，不镜像','头侧接触面 Z=8','样片前面 Z=12','销坐标 (0,±32)','销名义Z=4…12'],7,8.8)
 s.rows(16,85,['原厂要求：止口Ø50 +0.016/0、深度≥6、圆度0.01/平面度0.01；本候选后伸6.5。',
  'OEM Ø49.6薄输出端约4长，真正Ø50定位段更靠后；后裙到Z=-6.5，实际圆柱搭接约1.8。',
  'OEM中心Ø39区域不得承受法兰压紧；本候选另让开6个原厂齐平螺钉，禁止拆这些螺钉。',
  'eRob70I V5手册：8×M3×0.35、12.9黑氧化圆柱头；最小有效牙3.0，不等于允许旋入3.0。',
  '完整牙起止/允许深入未公开，OEM螺钉长度与SKU未定；普通M3×0.5不可替代。',
  '候选电机订货码 eRob70H100I-BS-18EN 尚需受控确认；本研究不是整臂换型。'],7,9)
 s.footer(1);c.showPage()
 s.header(2,'A01 / 转接盘完整名义特征','正向XY视图 1.7:1；A面层切片是同向视图，不镜像')
 s.geo(views['adapter']['FRONT z7.9'],(95,187),1.7);s.axes((95,187),42,1.7)
 s.geo(views['adapter']['REAR-LAND z0.1'],(251,187),1.7);s.axes((251,187),42,1.7)
 s.text(95,256,'前面层 Z=7.9',10,BLUE,align='center');s.text(251,256,'A面层 Z=0.1',10,BLUE,align='center')
 s.dim_h(30.4,159.6,111,187,187,'Ø76')
 s.lead((95+22*1.7,187),(147,234),(151,234),'8×Ø3.4 / PCD44')
 s.lead((251+22*math.cos(math.pi/12)*1.7,187+22*math.sin(math.pi/12)*1.7),(285,258),(296,258),'6×Ø5.6×0.5浅避空')
 s.text(324,250,'孔位：半径/角度',10,BLUE)
 s.rows(324,239,['OEM r22：','0,30,90,120,','180,210,270,300°','原厂螺钉避空 r22：','15,75,135,195,','255,315°','头部4孔 r32：','45,135,225,315°','角度由+X逆时针','坐标表见第4页'],7,8.7)
 s.rows(16,96,['材料候选：6061-T6，密度2700kg/m³仅质量计算假设；须确认板材证书与加工/表处状态。',
  '主盘Z0…8；后裙Z-6.5…0、OD60/ID50，后孔入口C0.3 / 内根R0.1；未列边仅去毛刺。',
  '8×Ø3.4贯通主盘，前沉孔Ø6.2深3.4（底Z4.6）；底部孔口C0.2，实际承压底面Z4.6。',
  '6×Ø5.6避空从A面深0.5；中心Ø39从A面深0.3，继以Ø18贯通；不接触原厂中心盖。',
  '4×M4×0.7贯穿Z0…8，入口两面C0.25；STEP用Ø4大径简化，不得照其钻Ø4后直接攻牙。',
  '2×定位销孔(0,±32)：Ø3.000…3.003，贯穿主盘Z0…8；销装入深度需工装与实测确认。',
  '建议试制尺寸：主厚8±0.05、后伸6.5±0.05、OD76±0.1、孔位位置度Ø0.10相对A/B/C。',
  '上述是候选工艺目标；OEM母止口/平面度按原厂要求；未定义的公差不得由模型自动默认。'],7,8.8)
 s.footer(2);c.showPage()
 s.header(3,'H01 / 头侧接口样片与装拆通道','XY 2:1；原创头部接口候选，不是ISO标准法兰')
 s.geo(views['mate']['PLAN z10'],(113,178),2);s.axes((113,178),41,2)
 s.dim_h(37,189,259,178,178,'Ø76')
 s.dim_v(114,242,202,113,'64  两销中心距')
 s.lead((113,242),(148,250),(190,245),'Ø3.020…3.035 圆孔')
 s.lead((113,114),(144,110),(177,116),'径向槽 3.020…3.035 × 5')
 s.lead((113+32/math.sqrt(2)*2,178+32/math.sqrt(2)*2),(195,211),(217,211),'4×Ø4.5 / PCD64')
 s.text(235,249,'H01  /  6061候选，厚4±0.05',11,BLUE)
 s.rows(235,237,['Z=8…12；中心Ø18贯通。','四个螺钉孔前面C0.25，让开头下圆角。','一圆孔+一沿Y槽：两销不重复约束销距。','销候选 MISUMI MS3-8，Ø3 +0.005/+0.010。','A01名义压入4，露出4；保持力/热尚未确认。','4×NBK SNS-M4-12，M4×0.7，12.9黑氧化。','螺钉头最大Ø7.22×4，3mm内六角。','头底Z12；12mm名义螺钉末端Z0。','名义板厚时长度极限使末端Z±0.35。','按±0.05板厚、1.4端部不完整牙保守扣除，','可重叠完整牙最低估算约5.9mm；需实件验证。','无垫片；预紧/防松/铝牙强度未发布。'],7,9)
 s.rows(16,89,['安装：无电无载固定关节 → 确认原厂牙深/配套螺钉 → A01沿-Z平移套入并接触A面。',
  '先从+Z装八颗OEM螺钉，分次交叉拧紧；原厂2.0±0.2Nm仅适用于其确认规格的干装螺钉。',
  '装销时必须在台架压装并承托A01，不得把压入力传入关节轴承；再放H01并锁4颗M4。',
  '取头：先卸载/断电、解绑或拔下中心线束，再松4颗M4，从+Z移出H01；不要拉电缆拔头。',
  'OEM沉孔工具探针Ø5.8沿+Z开放，H01装好后遮挡，必须先卸H01；Ø7.8为M4头/工具空间探针。',
  '探针证明直向空间，不是具体扳手/手柄已选型；真实头框必须保留四个从+Z进入的工具通道。'],7,9)
 s.footer(3);c.showPage()
 s.header(4,'载荷筛查、孔位与无载打印件','实际数值由本脚本计算；不赋予制造额定')
 L=study['loads'];s.text(15,250,f"2kg工件×200mm + 1.5kg预算头×100mm：M={L['moment_Nm']:.6f}Nm；F={L['force_N']:.4f}N",11,BLUE)
 s.rows(15,236,[f"OEM八螺钉任意弯矩方位最大增量 {L['bolt_groups']['OEM8']['max_per_bolt_axial_increment_N']:.3f}N/颗；头侧四颗 {L['bolt_groups']['HEAD4']['max_per_bolt_axial_increment_N']:.3f}N/颗。",
  '这是等刚度、无撬力、接触维持下的增量；不含预紧；不能与螺钉拉断值直接比较即放行。',
  f"若200/100mm从H01前面计起，额外12mm使M={L['if_offsets_from_mate_face_moment_Nm']:.6f}Nm，必须另行计入。",
  f"假定8mm宽×4.4mm厚×{L['local_strip']['span_to_nearest_OEM_screw_mm']:.2f}mm长局部条带：σ={L['local_strip']['sigma_MPa']:.2f}MPa、δ={L['local_strip']['tip_deflection_mm']:.4f}mm。",
  '条带与轴向净截面仅筛查指标：没有证明圆盘实际弯曲/孔口应力/铝牙剥离/疲劳或OEM轴承寿命。'],7,9)
 s.text(15,185,'OEM孔中心：joint X / Y mm （PCD44非均布）',10,BLUE)
 for i,(xy,a) in enumerate(zip(polar(22,OEM_ANGLES),OEM_ANGLES)):s.text(15,175-6*i,f'{i+1}:  {xy[0]:+.6f}   {xy[1]:+.6f}    {a}°',9)
 s.text(143,185,'头侧孔 / 定位',10,BLUE)
 for i,xy in enumerate(polar(32,HEAD_ANGLES)):s.text(143,175-7*i,f'M4-{i+1}: {xy[0]:+.6f} / {xy[1]:+.6f}',9)
 s.rows(143,140,['D1：0 / +32 圆孔','D2：0 / -32 径向槽','销孔与轴B定义clocking','孔位表CSV为真值来源'],7,9)
 s.text(269,185,'无载打印 A01-G / H01-G',10,BLUE)
 s.rows(269,173,['A01-G母止口Ø50.4，Ø18.4中心孔；','OEM孔Ø3.8、头侧孔Ø4.5、销孔Ø3.2。','H01-G中心Ø18.4，销孔/槽宽3.3。','不测量金属Ø50配合/定位精度。','PLA/PETG仅空载；绝不代替金属承力。','打印A01-G前面Z8朝下，Z负向建高；','H01-G后面Z8朝下；先打孔径试片。','STL导出误差0.01mm/0.05rad；','勿全局缩放，用试片修正局部孔径。'],7,8.7)
 s.rows(15,99,[f"名义原创金属质量：A01 {study['parts']['adapter']['mass_if_6061_kg']*1000:.2f}g；H01 {study['parts']['mate']['mass_if_6061_kg']*1000:.2f}g（不含真实头/螺钉/销）。",
  f"真实OEM CAD静态相交体积 {study['checks']['adapter_vendor_intersection_mm3']:.3g}mm³；后裙连续直插包含体相交 {study['checks']['skirt_swept_vendor_intersection_mm3']:.3g}mm³。",
  f"A面实际可接触面积 {study['checks']['contact_area_mm2']:.3f}mm²；不是均匀接触压强保证。",
  '打印件全部重读为有效单实体、watertight三角网格；STEP与STL体积偏差见study.json。',
  '螺纹长度、预紧、材料证书、表处后的止口配合、动态负载/线束/工具实物仍需闭合。',
  '原厂CAD只在本地参与相交计算；发布文件均为原创几何/接口事实/来源hash。'],7,9)
 s.footer(4);c.save();assert len(PdfReader(path).pages)==4
 return path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--vendor-step',type=Path,required=True);args=ap.parse_args()
 sources=json.loads(SOURCE.read_text());expected=next(s['sha256'] for s in sources['sources'] if s['id']=='vendor_step');assert sha(args.vendor_step)==expected
 for folder in ['STEP','STL','DXF']:(OUT/folder).mkdir(parents=True,exist_ok=True)
 pdfmetrics.registerFont(TTFont('CN','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
 native=cq.importers.importStep(str(args.vendor_step)).val();vendor=native.rotate((0,0,0),(1,1,-1),120).translate((0,0,X0))
 features=vendor_features(native);write_json(OUT/'vendor-interface-extraction.json',features)
 parts={'adapter':adapter(),'mate':mate(),'adapter-gauge':adapter(True),'mate-gauge':mate(True)}
 print('Built originals',flush=True)
 exports={name:export_part(name,s) for name,s in parts.items()}
 print_meshes={}
 for name in ['adapter-gauge','mate-gauge']:
  solid=parts[name].rotate((0,0,0),(1,0,0),180).translate((0,0,8)) if name=='adapter-gauge' else parts[name].translate((0,0,-8))
  path=OUT/'STL'/(name+'-print-oriented.stl');cq.exporters.export(solid,str(path),tolerance=.01,angularTolerance=.05)
  mesh=trimesh.load(path,force='mesh',process=True);assert mesh.is_watertight and mesh.is_winding_consistent and abs(mesh.bounds[0,2])<1e-5
  print_meshes[name]=dict(file=str(path.relative_to(OUT)),sha256=sha(path),mesh_watertight=bool(mesh.is_watertight),bbox_mm=mesh.bounds.tolist(),rotation='Rx180 then Tz8' if name=='adapter-gauge' else 'Tz-8',no_mirror=True)

 # Continuous translation proof: annular superset contains the skirt for insertion translations0..50; beyond50 all of it is ahead of OEM z<=0.
 sweep=cyl(30,-6.5,70).cut(cyl(25,-6.51,70.02)).fuse(cyl(30,-.1,70).cut(cyl(24.9,-.101,70.002)))
 checks={'vendor_valid':vendor.isValid(),'vendor_solids':len(vendor.Solids()),'adapter_vendor_intersection_mm3':volume(parts['adapter'].intersect(vendor)),'skirt_swept_vendor_intersection_mm3':volume(sweep.intersect(vendor)),'mate_vendor_intersection_mm3':volume(parts['mate'].intersect(vendor)),'adapter_mate_intersection_mm3':volume(parts['adapter'].intersect(parts['mate'])),'contact_area_mm2':contact_area(parts['adapter'],vendor),'mate_contact_area_mm2':contact_area(parts['mate'],parts['adapter'])}
 assert max(checks[k] for k in checks if 'intersection_mm3' in k)<1e-5
 tools=[]
 for label,xylist,r,z in [('OEM',polar(22,OEM_ANGLES),2.9,4.6),('M4',polar(32,HEAD_ANGLES),3.9,12)]:
  for i,xy in enumerate(xylist):
   # Tool opening starts at bearing floor; head is removed / tool engages socket, not intersected as obstruction.
   probe=cyl(r,z+.0001,50,xy);obs=[vendor,parts['adapter']]+([parts['mate']] if label=='M4' else [])
   vols=[volume(probe.intersect(o)) for o in obs];assert max(vols)<1e-5;tools.append(dict(id=f'{label}{i+1}',probe_diameter_mm=2*r,from_z_mm=z,to_z_mm=z+50,obstacle_intersections_mm3=vols))
 checks['tool_space_probes']=tools
 # Pin/body and M4 screws: exact exterior envelope except thread/fillets; nominal positions plus length extrema.
 hardware=[]
 for i,xy in enumerate(polar(32,HEAD_ANGLES)):
  for length in [11.65,12,12.35]:
   bolt=cyl(2,12-length,length,xy).fuse(cyl(3.61,12,4,xy))
   vals=[volume(bolt.intersect(o)) for o in [vendor,parts['adapter'],parts['mate']]];assert max(vals)<1e-5
   hardware.append(dict(id=f'SNS-M4-12_{i+1}',length_mm=length,exterior_head_max_mm=[7.22,4],intersection_mm3=vals))
 checks['head_bolt_envelopes']=hardware
 # Continuous insertion: shaft and head swept supersets for all +Z translations.
 checks['head_bolt_swept_intersections_mm3']=[]
 for xy in polar(32,HEAD_ANGLES):
  sw=cyl(2,-.35,62.35,xy).fuse(cyl(3.61,12,54,xy))
  vals=[volume(sw.intersect(o)) for o in [vendor,parts['adapter'],parts['mate']]];assert max(vals)<1e-5
  checks['head_bolt_swept_intersections_mm3'].append(vals)
 # Mate with retained pins inserts above the open adapter face; only pin/hole pair is fit-related.
 checks['mate_translation']={'all_main_material_z_ge_mm':8,'adapter_z_max_mm':8,'pin_round_min_diametral_clearance_mm':.010,'slot_width_min_diametral_clearance_mm':.010,'scope':'Coaxial +Z to contact. Position/fit tolerances and live harness are not certified.'}
 checks['head_thread_engagement_screen']={'length_min_mm':11.65,'length_max_mm':12.35,'mate_thickness_max_mm':4.05,'assumed_tip_incomplete_max_mm':1.4,'female_entrance_chamfer_mm':.25,'geometric_full_overlap_min_mm':11.65-4.05-1.4-.25,'requires':'Through tapped M4x.7 full form outside modeled end chamfers; no thread stripping or preload release.'}

 # Nominal pin OD in metal is intentionally interference; it is not treated as a CAD collision error.
 checks['pin_contract']={'nominal_z_mm':[4,12],'diameter_mm':[3.005,3.010],'press_bore_proposal_mm':[3,3.003],'nominal_interference_um':[2,10],'nominal_round_mate_clearance_um':[10,30],'full_ending_geometry_and_retention':'TBD; exact vendor end/length bounds not yet available'}
 checks['insertion_proof_scope']='Aligned +Z translation0..50mm to seated only; beyond50mm skirt z>=43.5, ahead of OEM z<=0. Main body always z>=0; swept skirt superset checked exactly. No tilted insertion, tolerances, printed fit or assembled motor rotation certification.'
 views={
 'adapter':{'FRONT z7.9':curves(section(parts['adapter'],'XY',7.9),'XY'),'REAR-LAND z0.1':curves(section(parts['adapter'],'XY',.1),'XY'),'SECTION Y0':curves(section(parts['adapter'],'XZ',0),'XZ')},
 'mate':{'PLAN z10':curves(section(parts['mate'],'XY',10),'XY'),'SECTION Y0':curves(section(parts['mate'],'XZ',0),'XZ')}}
 notesA=['A01: units mm / original study / NO PRODUCTION RELEASE','OD76 Z0..8; rear skirt OD60/ID50 Z-6.5..0; rear lead-in C0.3 / internal rootR0.1','Female ID50 +0/+0.016; OEM requires depth>=6, roundness .01, flatness .01','Centre ID18; rear recess ID39 depth .3; six OEM-head reliefs ID5.6 depth .5','OEM8: PCD44 at0,30,90,120,180,210,270,300deg; ID3.4 THRU','OEM8 front counterbore ID6.2 depth3.4; underhead bore C.2','Head4: M4x.7 THRU Z0..8, major diameter simplified CAD4, drill/tap separately','Head4 PCD64 at45,135,225,315deg; both face entry C.25','Pin2: (0,+/-32) bore3.000..3.003 THRU Z0..8; retention requires verification','OEM screw M3x.35 length/SKU TBD; DO NOT install ordinary M3x.5']
 notesH=['H01: 6061 candidate interface coupon, NOT final head load frame','OD76; Z8..12 (4 thick); centre ID18','4xID4.5 PCD64 at45,135,225,315deg; front entry C.25','Round pin hole(0,32): ID3.020..3.035; radial slot(0,-32): same width x5 long alongY','4xNBK SNS-M4-12; no washer; preload not defined','Nominal geometry only. See PDF and study.json for limits.']
 dxfs={n:drawing_dxf(n,views[n],notesA if n=='adapter' else notesH) for n in views}
 with (OUT/'hole-coordinates.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['group','index','x_mm','y_mm','angle_deg','feature'])
  for group,r,aa,feature in [('OEM',22,OEM_ANGLES,'ID3.4 / CB6.2x3.4'),('OEM_HEAD_RELIEF',22,OEM_RELIEF_ANGLES,'ID5.6x.5'),('HEAD',32,HEAD_ANGLES,'M4x.7 / mateID4.5')]:
   for i,(a,xy) in enumerate(zip(aa,polar(r,aa))):w.writerow([group,i+1,*xy,a,feature])
  for i,y in enumerate([32,-32]):w.writerow(['PIN',i+1,0,y,'','adapter3.000..3.003; mate round/slot3.020..3.035'])
 study=dict(revision='R5-WRIST-EROB01',status='conditional original adapter candidate; not production release',license='CC-BY-NC-4.0',source_hashes=[dict(path=str(SOURCE.relative_to(ROOT)),sha256=sha(SOURCE)),dict(path=str(Path(__file__).relative_to(ROOT)),sha256=sha(__file__)),dict(path='engineering/draw_central_display01.py',sha256=sha(ROOT/'engineering/draw_central_display01.py')),dict(path='local-only OEM STEP; --vendor-step',sha256=expected)],unit='mm',parts=exports,print_oriented_meshes=print_meshes,checks=checks,loads=loads(parts),dxfs=dxfs)
 pp=pdf(parts,views,study);study['pdf']={'file':pp.name,'sha256':sha(pp),'pages':4,'render_review':'pending independent visual readback'}
 write_json(OUT/'study.json',study)
 write_json(OUT/'manifest.json',{'revision':'R5-WRIST-EROB01','outputs':[{'path':str(p.relative_to(OUT)),'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['manifest.json','visual-qa.json'] and p.suffix.lower()!='.png']})
 print(json.dumps({'mass_kg':{n:exports[n]['mass_if_6061_kg'] for n in ['adapter','mate']},'checks':checks,'load':study['loads']['bolt_groups']},indent=2),flush=True)

if __name__=='__main__':main()
