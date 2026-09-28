# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""CD-DRAW01. Exact STEP sections, nominal prototype drawings and printable dummies.

No change to CD-MOUNT01. Millimetres, no general manufacturing tolerance.
The rear cup pocket retains the two actual X=+/-30 mm bridge flats.
"""
from pathlib import Path
import argparse, hashlib, json, math, itertools
import cadquery as cq
import ezdxf
import numpy as np
import trimesh
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Circle
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'engineering/generated/central-display-mount01'
OUT=ROOT/'engineering/generated/central-display-drawings01'
INK='#16354A'; GREY='#6E7E87'; BLUE='#006C8D'; LIGHT='#D9E3E8'
PARTS=['cup','bezel','insulating-spacer','window','PCB-outline']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bbox(s):
 b=s.BoundingBox();return [[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]
def section(s,plane,value):
 origin=(0,0,value) if plane=='XY' else (0,value,0)
 normal=(0,0,1) if plane=='XY' else (0,1,0)
 op=BRepAlgoAPI_Section(s.wrapped,gp_Pln(gp_Pnt(*origin),gp_Dir(*normal)),False);op.Build()
 assert op.IsDone()
 return list(cq.Shape(op.Shape()).Edges())
def curves(edges,plane):
 ix=[0,1] if plane=='XY' else [0,2];out=[]
 def xy(p):return [float(p.Coord()[i]) for i in ix]
 for e in edges:
  a=BRepAdaptor_Curve(e.wrapped);t0,t1=a.FirstParameter(),a.LastParameter()
  p,q,m=xy(a.Value(t0)),xy(a.Value(t1)),xy(a.Value((t0+t1)/2))
  if a.GetType()==GeomAbs_Line:
   if math.dist(p,q)>1e-7:out.append(dict(kind='LINE',p=p,q=q))
  elif a.GetType()==GeomAbs_Circle:
   c=xy(a.Circle().Location());r=float(a.Circle().Radius())
   if math.dist(p,q)<1e-6 and abs(t1-t0)>6:
    out.append(dict(kind='CIRCLE',c=c,r=r))
   else:
    deg=lambda v:math.degrees(math.atan2(v[1]-c[1],v[0]-c[0]))%360
    start,mid,end=deg(p),deg(m),deg(q)
    if (mid-start)%360>(end-start)%360+1e-6:start,end=end,start
    out.append(dict(kind='ARC',c=c,r=r,start=start,end=end))
  else:raise ValueError('Unapproved curve type '+str(a.GetType()))
 return out

def dxf_geometry(m,cs,offset=(0,0),layer='BOUNDARY'):
 o=np.array(offset)
 for r in cs:
  a={'layer':layer}
  if r['kind']=='LINE':m.add_line(np.array(r['p'])+o,np.array(r['q'])+o,dxfattribs=a)
  elif r['kind']=='CIRCLE':m.add_circle(np.array(r['c'])+o,r['r'],dxfattribs=a)
  else:m.add_arc(np.array(r['c'])+o,r['r'],r['start'],r['end'],dxfattribs=a)

def write_dxf(name,views,notes,dims=()):
 doc=ezdxf.new('R2013');doc.units=4
 for n,col in [('BOUNDARY',7),('SECTION',5),('NOTE',3),('DIM',2),('CENTRE',8)]:doc.layers.new(n,dxfattribs={'color':col})
 doc.header['$INSUNITS']=4;doc.header['$MEASUREMENT']=1
 m=doc.modelspace()
 for label,cs,offset in views:
  dxf_geometry(m,cs,offset,'SECTION' if 'SECTION' in label else 'BOUNDARY')
  m.add_text(label,dxfattribs={'height':2.3,'layer':'NOTE','insert':(offset[0]-40,offset[1]+39)})
 for i,t in enumerate(notes):m.add_text(t,dxfattribs={'height':2.1,'layer':'NOTE','insert':(-42,-105-4*i)})
 for p1,p2,base,angle,label in dims:
  d=m.add_linear_dim(base=base,p1=p1,p2=p2,angle=angle,text=label,dimstyle='EZDXF',override={'dimtxt':2.4,'dimasz':1.3},dxfattribs={'layer':'DIM'});d.render()
 path=OUT/'DXF'/(name+'.dxf');doc.saveas(path)
 back=ezdxf.readfile(path);audit=back.audit();assert not audit.has_errors
 return dict(file=str(path.relative_to(OUT)),sha256=sha(path),insunits=back.units,entities=len(back.modelspace()),audit_errors=len(audit.errors))

class Sheet:
 def __init__(self,c):self.c=c
 def text(self,x,y,t,size=9,color=INK,align='left'):
  c=self.c;c.setFont('CN',size);c.setFillColor(HexColor(color));getattr(c,{'left':'drawString','center':'drawCentredString','right':'drawRightString'}[align])(x*mm,y*mm,str(t))
 def line(self,p,q,color=INK,width=.5,dash=None):
  c=self.c;c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.setDash(dash or []);c.line(p[0]*mm,p[1]*mm,q[0]*mm,q[1]*mm);c.setDash([])
 def arrow(self,p,d):
  p=np.array(p);d=np.array(d,dtype=float);d/=np.linalg.norm(d);n=np.array([-d[1],d[0]])
  self.line(p,p+1.6*d+.5*n,width=.5);self.line(p,p+1.6*d-.5*n,width=.5)
 def dim_h(self,x1,x2,y,from1,from2,label):
  for x,f in [(x1,from1),(x2,from2)]:self.line((x,f),(x,y+2),GREY,.3)
  self.line((x1,y),(x2,y),GREY,.4);self.arrow((x1,y),(1,0));self.arrow((x2,y),(-1,0));self.text((x1+x2)/2,y+2,label,8.5,align='center')
 def dim_v(self,y1,y2,x,fromx,label,right=True):
  for y in [y1,y2]:self.line((fromx,y),(x+2,y),GREY,.3)
  self.line((x,y1),(x,y2),GREY,.4);self.arrow((x,y1),(0,1));self.arrow((x,y2),(0,-1));self.text(x+(3 if right else -3),(y1+y2)/2,label,8.5,align='left' if right else 'right')
 def lead(self,p,elbow,end,label):
  self.line(p,elbow,BLUE,.4);self.line(elbow,end,BLUE,.4);self.arrow(p,np.array(elbow)-np.array(p));self.text(end[0],end[1]+2,label,8.2,BLUE)
 def geo(self,cs,origin=(0,0),scale=1,color=INK,width=.65,dash=None):
  c=self.c;c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.setDash(dash or [])
  o=np.array(origin)
  for r in cs:
   if r['kind']=='LINE':
    p=o+scale*np.array(r['p']);q=o+scale*np.array(r['q']);c.line(*(list(p*mm)+list(q*mm)))
   else:
    centre=o+scale*np.array(r['c']);rad=scale*r['r'];box=[*(centre-rad),*(centre+rad)]
    if r['kind']=='CIRCLE':c.circle(centre[0]*mm,centre[1]*mm,rad*mm,stroke=1,fill=0)
    else:c.arc(*[v*mm for v in box],startAng=r['start'],extent=(r['end']-r['start'])%360)
  c.setDash([])
 def axes(self,o,extent,scale):
  self.line((o[0]-extent*scale,o[1]),(o[0]+extent*scale,o[1]),GREY,.3,[6,2,1,2]);self.line((o[0],o[1]-extent*scale),(o[0],o[1]+extent*scale),GREY,.3,[6,2,1,2])
 def header(self,n,title,sub):
  self.text(14,282,'ODRADEK  /  CD-DRAW01',19);self.text(405,282,f'{n} / 4',10,align='right')
  self.text(14,271,title,12,BLUE);self.text(405,271,sub,9,align='right');self.line((14,266),(406,266),BLUE,.8)
 def footer(self,number):
  self.line((14,20),(406,20),GREY,.5);self.text(14,13,'单位 mm | A3 横向 | 名义几何样件图 | 无电、无载 | 无统一加工公差；非金属制造放行',8)
  self.text(406,13,f'2026-09-27 / {number}',8,align='right')
 def rows(self,x,y,data,gap=7,size=9):
  for i,t in enumerate(data):self.text(x,y-i*gap,t,size)

def offset_curves(cs,dy):
 out=[]
 for r in cs:
  r=json.loads(json.dumps(r))
  for k in ['p','q','c']:
   if k in r:r[k][1]+=dy
  out.append(r)
 return out

def create_pdf(shapes,views,features):
 path=OUT/'ODR-CD01-geometry-prototype.pdf';c=canvas.Canvas(str(path),pagesize=landscape(A3));c.setTitle('Odradek CD01 nominal geometry prototype drawings');s=Sheet(c)
 # Page 1 - all section curves are directly cut from the delivered STEP files.
 s.header(1,'装配与基准 / ASSEMBLY SECTION','装配比例 3:1；所有尺寸为真值')
 colors={'optical-frame':'#98A7AF','cup':'#006C8D','bezel':'#213E55','PCB-outline':'#21846C','insulating-spacer':'#9064A8','window':'#69A7B7'}
 for name in ['optical-frame','cup','PCB-outline','insulating-spacer','window','bezel']:
  cs=curves(section(shapes[name],'XZ',0),'XZ');s.geo(cs,(135,191),3,colors[name],.85)
 for side in ['L','R']:
  for end in ['M2x20-envelope','front-washer','rear-washer','M2-nut-envelope']:
   s.geo(curves(section(shapes[f'{side}-{end}'],'XZ',0),'XZ'),(135,191),3,'#6B6B6B',.6)
 s.text(17,248,'A-A  /  Y=0真实剖面；+Z朝向物体，X向右',10,BLUE)
 s.dim_h(135-35.25*3,135+35.25*3,216,203.3,203.3,'70.5  两孔中心距')
 s.dim_h(135-38.25*3,135+38.25*3,226,191.75,191.75,'76.5  杯/框总宽')
 s.dim_v(191-15*3,191-11*3,257,249.75,'4  原框')
 s.dim_v(191-11*3,191+.25*3,267,249.75,'11.25 杯')
 s.lead((135,183.5),(148,171),(166,171),'PCB 1 / 台阶接触 Z-3')
 s.lead((135,189.5),(148,184),(166,184),'窗口 0.75 / Z-0.5…0.25')
 s.lead((135-29.2*3,187),(35,177),(15,177),'绝缘圈 1.5')
 s.text(292,244,'HEAD 坐标叠层',11,BLUE)
 stack=[('螺钉头','2.1…4.1'),('前垫片','1.75…2.1'),('前压框','0.25…1.75'),('窗口','-0.5…0.25'),('绝缘圈','-2…-0.5'),('PCB轮廓','-3…-2'),('PCB座台阶','-4…-3'),('杯体总高','-11…0.25'),('既有后框','-15…-11'),('后垫片','-15.35…-15'),('M2螺母','-16.95…-15.35'),('M2x20末端','-17.9')]
 for i,(a,b) in enumerate(stack):s.text(292,234-i*6,a,8.4);s.text(401,234-i*6,b,8.4,align='right')
 s.rows(16,129,['基准：全部XY尺寸以屏中心为O；轴线X/Y是光学架HEAD坐标，不随背视镜像。',
  '安装孔：2×Ø2.2贯通，中心(-35.25,0)、(+35.25,0)；现有光学柱不改。',
  '杯筒底圈与旧框不相接，承压经左右耳；后垫Ø5对R32.5…38支承环两边各余0.25。',
  'M2×20、垫片与螺母为CD-HW01候选；名义突出0.95，不等于有效牙/预紧已确认。'],7,9)
 s.rows(16,87,['样件装配：先在开放台架放入PCB dummy/绝缘圈/窗口，再装前框与两螺钉。',
  '若装带线PCB：先接插、释放线束和确认锁扣可达；禁止拉线强拆。实际GH不在Y=0剖面内。',
  '拆卸前必须断电、卸载、释放GH导线；后螺母与垫片拆除后，依次从前方取出叠层。',
  '既有光学框是上下文零件：本册只规定新增两孔，完整旧外形以已冻结原STEP为准。'],7,9)
 s.rows(16,47,['图线来自STEP真实边界；不含线程牙型、材料变形、夹紧公差或透明片光学性能。',
  '杯/框与光学叠层有并联硬限位，不能把名义齐平当成有保证的压紧力。'],7,9)
 s.footer(1);c.showPage()
 # Page 2 - cup with two DIFFERENT pockets, not a fictitious round rear bore.
 s.header(2,'CD01-CUP / 杯座','前/后层XY 1.6:1；A-A 3:1；局部D 10:1')
 for label,cs,o in [('前侧层 Z=0.15',views['cup-front'],(108,185)),('后侧层 Z=-10.9，同向XY投影',views['cup-rear'],(307,185))]:
  s.geo(cs,o,1.6);s.axes(o,35,1.6);s.text(o[0],246,label,10,BLUE,align='center')
 s.dim_h(108-38.25*1.6,108+38.25*1.6,256,191.4,191.4,'76.5')
 s.dim_h(108-35.25*1.6,108+35.25*1.6,121,185,185,'70.5')
 s.dim_v(178.6,191.4,177,169.2,'8')
 s.lead((108+30.1*1.6,185),(168,223),(178,223),'Ø60.2 前腔')
 s.lead((108-35.25*1.6,185),(43,211),(15,211),'2×Ø2.2 THRU')
 s.lead((108,185+32*1.6),(122,235),(148,235),'R32 外轮廓')
 s.lead((307+30*1.6,185),(366,215),(371,215),'X=+30平面')
 s.lead((307-30*1.6,185),(248,216),(216,216),'X=-30平面')
 s.text(225,124,'后腔＝R30.1圆 ∩ |X|≤30；不是完整Ø60.2',9,BLUE)
 s.geo(offset_curves(views['cup-section'],11),(210,68),3)
 s.text(210,110,'A-A / Y=0，局部A=杯底 Z-11',9,BLUE,align='center')
 s.dim_h(210-38.25*3,210+38.25*3,58,68,68,'76.5')
 s.dim_v(68,101.75,333,324.75,'11.25')
 s.dim_v(68,89,88,95.25,'7',False);s.dim_v(89,92,79,95.25,'1',False)
 s.dim_v(92,101.75,344,324.75,'3.25')
 s.lead((210+28*3,90.5),(294,109),(329,109),'Ø56贯穿座口')
 # Magnified actual right-hand rear flat, clipped only for the labelled detail view.
 c.saveState();clip=c.beginPath();clip.rect(21*mm,49*mm,31*mm,55*mm);c.clipPath(clip,stroke=0)
 s.geo(views['cup-rear'],(36-30*10,76),10,INK,.6);c.restoreState()
 s.line((21,49),(52,49),GREY,.3);s.line((21,104),(52,104),GREY,.3)
 s.text(15,110,'D / 后腔平面 10:1',8.5,BLUE)
 s.lead((36,76),(44,83),(51,83),'X30')
 s.text(15,42,'D端点 Y±2.451530',8)
 s.rows(108,43,['外形：Ø64圆 ∪ 76.5×8中心矩形；无新增圆角/倒角。',
  '圆/耳交点：X±31.749016，Y±4（参考）；后腔平面深7，前腔深3.25。'],7,8.7)
 s.footer(2);c.showPage()
 # Page 3 bezel, exact same outer profile but a different clear aperture.
 s.header(3,'CD01-BEZEL / 前压框','主视/剖面 2:1；右耳局部 5:1')
 s.geo(views['bezel-plan'],(112,185),2);s.axes((112,185),35,2)
 s.dim_h(112-38.25*2,112+38.25*2,258,193,193,'76.5')
 s.dim_h(112-35.25*2,112+35.25*2,111,185,185,'70.5')
 s.dim_v(177,193,196,188.5,'8')
 s.lead((112,242),(138,238),(174,238),'Ø57 通光孔')
 s.lead((112-35.25*2,185),(35,217),(16,217),'2×Ø2.2贯通')
 s.text(15,99,'A-A / Y=0；局部A=背面 Z0.25',9,BLUE)
 s.geo(offset_curves(views['bezel-section'],-.25),(112,77),2)
 s.dim_v(77,80,196,188.5,'1.5')
 s.text(235,251,'全部名义特征',11,BLUE)
 s.rows(235,240,['外形 = Ø64圆 ∪ 76.5×8中心矩形',
  '孔中心 = (±35.25,0)，2×Ø2.2贯通',
  '中心Ø57贯通；总厚1.5',
  'HEAD Z=0.25…1.75；局部A为Z0.25',
  '外圆/矩形相交X±31.749016，Y±4',
  '所有相交边保持原STEP锐边，没有隐含R',
  '材料与加工/打印补偿均未选定'],9,9)
 c.saveState();clip=c.beginPath();clip.rect(239*mm,75*mm,138*mm,58*mm);c.clipPath(clip,stroke=0)
 s.geo(offset_curves(views['bezel-section'],-.25),(100,99),5);c.restoreState()
 s.text(244,141,'B / 右耳真实剖面（5:1）',9,BLUE)
 s.dim_v(99,106.5,321,291.25,'1.5')
 s.dim_h(100+34.15*5,100+36.35*5,88,99,99,'Ø2.2')
 s.rows(15,49,['前框用两颗M2夹住cup耳；中间窗口/绝缘圈是独立叠层，不能用耳螺钉直接压PCB。',
  '本页未赋予刚性材料公差或规定倒角。打印毛刺须通过无载试装处理并记录，不能偷偷更改名义文件。'],7,9)
 s.footer(3);c.showPage()
 # Page 4 flat pieces.
 s.header(4,'平面分件 / SPACER · WINDOW · PCB DUMMY','平面/侧面 1.5:1；无元件PCB替身')
 entries=[('insulating-spacer','绝缘圈',75,59.8,57,1.5,-2),('window','窗口片材轮廓',211,59.8,None,.75,-.5),('PCB-outline','PCB外形替身',347,60,None,1,-3)]
 for name,label,x,D,inner,H,z in entries:
  s.text(x,250,label+' / '+name,10,BLUE,align='center');s.geo(views[name+'-plan'],(x,185),1.5);s.axes((x,185),32,1.5)
  s.dim_h(x-D/2*1.5,x+D/2*1.5,132,185,185,'Ø'+str(D))
  if inner:s.lead((x,185+inner/2*1.5),(x+17,235),(x+30,235),'Ø57')
  s.geo(offset_curves(views[name+'-section'],-z),(x,112),1.5)
  s.text(x,104,'厚 '+str(H)+'；HEAD Z '+str(z)+'…'+str(z+H),8.5,align='center')
  s.text(x,96,'基准A=该件后平面；中心O与屏同轴',8.1,align='center')
 s.rows(16,78,['绝缘圈：R28.5…29.9、厚1.5；本阶段打印件只验证尺寸，未获绝缘/耐温认证。',
  '窗口：提供完整Ø59.8二维切割轮廓与0.75名义厚度，供片材样件；未选定透明材料或涂层，不以打印透明片替代。',
  'PCB dummy：Ø60×1纯轮廓，未含285颗LED、铜层、GH12和背面驱动；不当作可通电PCB。',
  '先以同批材料/方向做独立孔、厚度和环间隙试片，记录实测，再设置本机切片补偿。禁止整体缩放本套名义模型。',
  '四个STL均移到各自基准A=打印Z0；朝向+Z。cup内环台阶需单独核对切片支撑和去支撑可达。',
  '首层压扁/象脚、孔径偏差、翘曲和厚度需记录；通过无电、无载手装复核后再迭代打印参数。'],7,8.7)
 s.footer(4);c.showPage();c.save()
 reader=PdfReader(path);assert len(reader.pages)==4
 for page in reader.pages:assert len(page.extract_text())>300
 return path


def dxf_plan_area(path,start,count,expected_wires,expected_area):
 doc=ezdxf.readfile(path);items=[e for e in doc.modelspace() if e.dxf.layer=='BOUNDARY'][start:start+count];edges=[]
 assert len(items)==count
 for e in items:
  if e.dxftype()=='LINE':edges.append(cq.Edge.makeLine(tuple(e.dxf.start),tuple(e.dxf.end)))
  elif e.dxftype()=='CIRCLE':edges.append(cq.Edge.makeCircle(e.dxf.radius,tuple(e.dxf.center)))
  elif e.dxftype()=='ARC':
   b=e.dxf.end_angle
   if b<e.dxf.start_angle:b+=360
   edges.append(cq.Edge.makeCircle(e.dxf.radius,tuple(e.dxf.center),angle1=e.dxf.start_angle,angle2=b))
  else:raise ValueError(e.dxftype())
 wires=cq.Wire.combine(edges,tol=1e-6);assert len(wires)==expected_wires and all(w.IsClosed() for w in wires)
 areas=sorted([cq.Face.makeFromWires(w).Area() for w in wires],reverse=True);net=areas[0]-sum(areas[1:]);assert abs(net-expected_area)<1e-5,(net,expected_area)
 return dict(file=str(path.relative_to(OUT)),start_entity=start,edge_count=count,closed_wires=len(wires),DXF_rebuilt_area_mm2=net,independent_analytic_area_mm2=expected_area,absolute_error_mm2=abs(net-expected_area),method='Re-read LINE/CIRCLE/ARC entities, reconstruct closed CQ wires and exact face areas; largest loop less all contained holes.')

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--font',type=Path,default=Path('/Library/Fonts/Arial Unicode.ttf'));a=parser.parse_args()
 for d in ['DXF','STL','qa']: (OUT/d).mkdir(parents=True,exist_ok=True)
 pdfmetrics.registerFont(TTFont('CN',str(a.font)))
 review=json.loads((SRC/'independent-review.json').read_text())
 for p,h in review['source_sha256'].items():assert sha(ROOT/p)==h,('frozen source changed',p)
 names=PARTS+['optical-frame']+[f'{side}-{p}' for side in ['L','R'] for p in ['M2x20-envelope','front-washer','rear-washer','M2-nut-envelope']]
 shapes={n:cq.importers.importStep(str(SRC/f'CD01-{n}.step')).val() for n in names}
 assert all(s.isValid() and len(s.Solids())==1 for s in shapes.values())
 views={}
 for name in PARTS:
  zhi=bbox(shapes[name])[1][2];views[name+'-plan']=curves(section(shapes[name],'XY',zhi-.01),'XY')
  views[name+'-section']=curves(section(shapes[name],'XZ',0),'XZ')
 views['cup-front']=curves(section(shapes['cup'],'XY',.15),'XY');views['cup-rear']=curves(section(shapes['cup'],'XY',-10.9),'XY')
 # Independent scalar/analytic volume checks catch omitted rear flats and idealised contours.
 junction=math.sqrt(32**2-4**2);flat_end=math.sqrt(30.1**2-30**2)
 area_outer=math.pi*32**2+76.5*8-2*(4*junction+32**2*math.asin(4/32))
 rear_area=math.pi*30.1**2-2*(30.1**2*math.acos(30/30.1)-30*flat_end)
 harea=2*math.pi*1.1**2
 expected={'cup':area_outer*11.25-rear_area*7-math.pi*28**2-math.pi*30.1**2*3.25-harea*11.25,
 'bezel':(area_outer-math.pi*28.5**2-harea)*1.5,
 'insulating-spacer':math.pi*(29.9**2-28.5**2)*1.5,'window':math.pi*29.9**2*.75,'PCB-outline':math.pi*30**2}
 expected_bbox={'cup':[[-38.25,-32,-11],[38.25,32,.25]],'bezel':[[-38.25,-32,.25],[38.25,32,1.75]],'insulating-spacer':[[-29.9,-29.9,-2],[29.9,29.9,-.5]],'window':[[-29.9,-29.9,-.5],[29.9,29.9,.25]],'PCB-outline':[[-30,-30,-3],[30,30,-2]]}
 feature_checks=[]
 for n,v in expected.items():
  got=shapes[n].Volume();assert abs(got-v)<1e-5,(n,got,v);err=np.max(np.abs(np.array(bbox(shapes[n]))-expected_bbox[n]));assert err<1e-6
  feature_checks.append(dict(part=n,analytic_volume_mm3=v,STEP_volume_mm3=got,absolute_error_mm3=abs(got-v),bbox_head_mm=bbox(shapes[n]),bbox_error_mm=float(err)))
 rear_flats=[r for r in views['cup-rear'] if r['kind']=='LINE' and abs(abs(r['p'][0])-30)<1e-5 and abs(r['q'][0]-r['p'][0])<1e-6]
 assert len(rear_flats)==2
 for r in rear_flats:assert abs(abs(r['p'][1])-flat_end)<1e-6 and abs(abs(r['q'][1])-flat_end)<1e-6
 for n in ['cup-front','cup-rear','bezel-plan']:
  hs=[x for x in views[n] if x['kind']=='CIRCLE' and abs(x['r']-1.1)<1e-7];assert len(hs)==2
  assert sorted(round(x['c'][0],6) for x in hs)==[-35.25,35.25] and all(abs(x['c'][1])<1e-6 for x in hs)
 dxfs=[]
 dxfs.append(write_dxf('CD01-cup', [('FRONT LAYER HEAD Z0.15 / XY',views['cup-front'],(0,0)),('REAR LAYER HEAD Z-10.9 / XY',views['cup-rear'],(110,0)),('SECTION Y0 / XZ LOCAL A=HEAD Z-11',offset_curves(views['cup-section'],11),(0,-75))],['CD-DRAW01 NOMINAL GEOMETRY PROTOTYPE / mm / NO POWER OR LOAD','OD profile = D64 circle UNION centred76.5x8 rectangle; no fillets','2xD2.2 THRU at X+/-35.25,Y0 / total H11.25','Rear pocket depth7: R30.1 circle INTERSECT |X|<=30','Front pocket D60.2 depth3.25; middle D56 throat H1','Native line/arc entities copied from actual frozen STEP sections'], [((-38.25,4),(38.25,4),(0,43),0,'76.5'),((-35.25,0),(35.25,0),(0,-43),0,'70.5')]))
 dxfs.append(write_dxf('CD01-bezel',[('PLAN / XY',views['bezel-plan'],(0,0)),('SECTION Y0 / LOCAL A=HEAD Z0.25',offset_curves(views['bezel-section'],-.25),(0,-75))],['CD-DRAW01 NOMINAL GEOMETRY PROTOTYPE / mm','D64 circle UNION centred76.5x8 rectangle; inner D57','2xD2.2 THRU at X+/-35.25,Y0; thickness1.5 / no fillets'],[((-38.25,4),(38.25,4),(0,43),0,'76.5'),((-35.25,0),(35.25,0),(0,-43),0,'70.5')]))
 for n in ['insulating-spacer','window','PCB-outline']:
  z=bbox(shapes[n])[0][2];D=59.8 if n!='PCB-outline' else 60;H={'insulating-spacer':1.5,'window':.75,'PCB-outline':1}[n]
  dxfs.append(write_dxf('CD01-'+n,[('PLAN / XY',views[n+'-plan'],(0,0)),('SECTION / LOCAL A=BACK PLANE',offset_curves(views[n+'-section'],-z),(0,-75))],[f'CD-DRAW01 / {n} / D{D} / thickness{H} / mm','NOMINAL GEOMETRY ONLY; no material or tolerance approval','Inner D57 THRU' if n=='insulating-spacer' else 'Closed circular planar outline']))
 dxf_areas=[]
 dxf_areas.append(dxf_plan_area(OUT/'DXF/CD01-cup.dxf',0,len(views['cup-front']),4,area_outer-math.pi*30.1**2-harea))
 dxf_areas.append(dxf_plan_area(OUT/'DXF/CD01-cup.dxf',len(views['cup-front']),len(views['cup-rear']),4,area_outer-rear_area-harea))
 dxf_areas.append(dxf_plan_area(OUT/'DXF/CD01-bezel.dxf',0,len(views['bezel-plan']),4,expected['bezel']/1.5))
 for n,H,nw in [('insulating-spacer',1.5,2),('window',.75,1),('PCB-outline',1,1)]:
  dxf_areas.append(dxf_plan_area(OUT/'DXF'/('CD01-'+n+'.dxf'),0,len(views[n+'-plan']),nw,expected[n]/H))
 # Clean standalone cutting outlines at true XY origin, without notes or duplicate projected edges.
 for n in ['insulating-spacer','window','PCB-outline']:
  doc=ezdxf.new('R2013');doc.units=4;doc.layers.new('BOUNDARY');dxf_geometry(doc.modelspace(),views[n+'-plan']);path=OUT/'DXF'/('CD01-'+n+'-cut-outline.dxf');doc.saveas(path)
  q=ezdxf.readfile(path);assert not q.audit().has_errors;dxfs.append(dict(file=str(path.relative_to(OUT)),sha256=sha(path),insunits=q.units,entities=len(q.modelspace()),audit_errors=0))
 # Assembly XZ section contains the actual part outlines at actual HEAD coordinates, not exploded.
 assem=[('ASSEMBLY SECTION Y0 / XZ HEAD FRAME',[r for n in names for r in curves(section(shapes[n],'XZ',0),'XZ')],(0,0))]
 dxfs.append(write_dxf('CD01-assembly-section',assem,['CD-MOUNT01 ACTUAL SECTION Y0 / XZ HEAD COORDINATES / mm','X+/-35.25 holes;70.5 pitch; all stack elevations per PDF page1','Existing frame context only; not a full re-release of that older part']))
 stls=[]
 for n in ['cup','bezel','insulating-spacer','PCB-outline']:
  s=shapes[n];zmin=bbox(s)[0][2];t=s.translate((0,0,-zmin));path=OUT/'STL'/('CD01-'+n+'-print-mm.stl')
  t.exportStl(str(path),tolerance=.005,angularTolerance=.05,ascii=False,relative=False)
  mesh=trimesh.load_mesh(path,process=True);assert mesh.is_watertight and mesh.is_winding_consistent
  err=float(np.max(np.abs(mesh.bounds-np.array(bbox(t)))));verr=abs(abs(mesh.volume)-t.Volume());rel=verr/t.Volume();assert err<=.011 and rel<.002,(n,err,rel)
  stls.append(dict(part=n,file=str(path.relative_to(OUT)),sha256=sha(path),units='mm (STL itself is unitless)',translation_head_to_print_mm=[0,0,-zmin],no_rotation=True,CAD_bbox_print_mm=bbox(t),reloaded_mesh_bbox_mm=mesh.bounds.tolist(),max_bbox_error_mm=err,CAD_volume_mm3=t.Volume(),mesh_volume_mm3=float(mesh.volume),absolute_volume_error_mm3=verr,relative_volume_error=rel,watertight=bool(mesh.is_watertight),winding_consistent=bool(mesh.is_winding_consistent),vertices=len(mesh.vertices),triangles=len(mesh.faces),euler_number=int(mesh.euler_number),linear_deflection_mm=.005,angular_deflection_rad=.05,relative_deflection=False,parser_processing='trimesh process=True welds coincident STL triangle vertices; no hole filling or mesh repair invoked'))
 pdf=create_pdf(shapes,views,feature_checks)
 report=dict(revision='CD-DRAW01',date='2026-09-27',license='CC-BY-NC-4.0',manufacturing_release=False,scope='Unpowered unloaded nominal geometry prototype; no source CAD changes',units='mm',source_sha256={**review['source_sha256'],'engineering/generated/central-display-mount01/independent-review.json':sha(SRC/'independent-review.json'),**{str((SRC/f'CD01-{n}.step').relative_to(ROOT)):sha(SRC/f'CD01-{n}.step') for n in names},str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},feature_checks=feature_checks,view_section_planes=dict(cup_front_HEAD_Z_mm=.15,cup_rear_HEAD_Z_mm=-10.9,other_plan_HEAD_Z_mm={n:bbox(shapes[n])[1][2]-.01 for n in PARTS},all_XZ_section_HEAD_Y_mm=0),exact_BREP_view_curves=views,analytic_definitions=dict(outer='union(D64 circle, centred76.5x8 rectangle)',ear_junction_abs_xy_mm=[junction,4],rear_flat_abs_xy_endpoint_mm=[30,flat_end],rear_cavity='intersection(R30.1 circle, |X|<=30); depth7 from headZ-11',cup_front='D60.2 depth3.25 from headZ0.25',cup_throat='D56 at headZ-4..-3',rear_flat_redundant_arc_references='No rear D60.2 full-circle substitution. Flats and intersected arcs retained.'),DXF=dxfs,DXF_area_roundtrip=dxf_areas,STL=stls,PDF=dict(file=pdf.name,sha256=sha(pdf),pages=4,page_size='A3 landscape',render_QA='External visual-qa.json records actual raster inspection against this PDF hash; the generator does not self-certify visual review'),exclusions=['No power, no payload, no fastener preload qualification','No ISO general machining tolerance assigned','No selected optical or insulating material','No real populated PCB/connector/wire STL','No transparent window STL: planar cutting outline only','Existing optical-frame geometry is context, not fully redimensioned/released here'])
 (OUT/'drawing-evidence.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(stls),'STLs',len(dxfs),'DXFs',len(feature_checks),'analytic volume/bbox matches; PDF',pdf)
if __name__=='__main__':main()
