# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Export checked LINK67 original solids and dimensioned fit-study drawings."""
from pathlib import Path
import argparse,csv,json,hashlib
import cadquery as cq
import numpy as np
import ezdxf,trimesh
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from build_link67_study import ROOT,OUT,REV,PARAM_SHA,POST,make_parts,sha
from build_layout import frame,moved
from build_link56_study import projected_edges
from build_base_study import export_parts
from candidate_mass_model import candidate_model
from review_arm_screening import triangle_bounds

def features(op,fp):
    rows=[]
    def add(part,feature,points,axis,D,start,depth,thread=''):
        for i,(x,y) in enumerate(points,1):
            rows.append(dict(part=part,feature=feature,number=i,x_mm=float(x),y_mm=float(y),axis=axis,diameter_mm=D,axial_start_mm=start,depth_mm=depth,thread=thread))
    add('OUT','central_through',[[0,0]],'+Z',44,0,6)
    add('OUT','rear_boss_relief',[[0,0]],'+Z',47.6,0,2.5)
    add('OUT','J6_output_clearance',op,'+Z',3.5,0,22)
    add('OUT','J6_cap_relief',op,'+Z',6.4,4,18)
    add('OUT','post_blind_pilot',POST,'+Z',4.2,3,19,'M5x0.8 effective tap>=14 from Z22; candidate6H')
    add('CARRIER','J7_rear_through_tap',fp,'+Z',2.5,0,14,'M3x0.5 THRU; candidate6H')
    # Carrier local: centre x0,y0 at J7 axis, Z0=world595.5. Side holes are X/Z coordinates.
    add('CARRIER','post_side_clearance_XZ',[[x,9.5-v] for x,v in POST],'+Y',5.5,-33,12)
    add('FRONT','J7_fixed_clearance',fp,'+Z',3.5,0,3)
    add('FRONT','OEM_head_relief',[[32,0],[-32,0],[0,32],[0,-32]],'+Z',6.2,0,3)
    return rows

def loads(a,op,fp):
    p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
    model,_=candidate_model(p,4.5)
    model['bodies']=[b for b in model['bodies'] if b['id']!='L6_budget']
    mass=sum(s.Volume()*2.7e-6 for s in a.values());com=sum(s.Volume()*np.array(s.Center().toTuple()) for s in a.values())/sum(s.Volume() for s in a.values())
    for n,s in a.items():model['bodies'].append(dict(id='L67_'+n,mass_kg=s.Volume()*2.7e-6,preceding_joints=6,com_home_m=(np.array(s.Center().toTuple())*.001).tolist()))
    model['bodies'].append(dict(id='L67_fastener_reserve',mass_kg=.1,preceding_joints=6,com_home_m=(com*.001).tolist()))
    G=9.80665;bound={};downstream=sum(b['mass_kg'] for b in model['bodies'] if b['preceding_joints']>=6)
    for label,P in {'output':[0,0,605],'posts':[0,22,605],'rear':[0,55,609.5],'front':[0,55,630]}.items():
        P=np.array(P)*.001;B=0
        for b in model['bodies']:
            n=b['preceding_joints']
            if n<6:continue
            c=np.array(b['com_home_m']);nodes=[P]+[np.array(model['joints'][k]['origin_m']) for k in range(6,n)]+[c]
            B+=b['mass_kg']*G*sum(np.linalg.norm(y-x) for x,y in zip(nodes,nodes[1:]))
        bound[label]=float(B)
    allowance=G*(4.5*.05+2*.1+.1*.10)
    design=1.5*(max(bound.values())+allowance);force=1.5*G*downstream
    groups={}
    for name,pts in [('output16',op),('posts4',POST),('fixed4',fp)]:
        # Equal axial spring stiffness, rigid plates; all in-plane moment directions.
        coef=pts@np.linalg.inv(pts.T@pts)
        groups[name]={'maximum_moment_coefficient_per_mm':float(np.linalg.norm(coef,axis=1).max()),
          'maximum_abs_axial_external_force_N':float(force/len(pts)+design*1000*np.linalg.norm(coef,axis=1).max()),
          'direct_equal_shear_force_N':force/len(pts)}
    return {'metal_mass_kg':mass,'reserve_kg':.1,'COM_world_mm':com.tolist(),'preceding_joints':6,
      'loadcase':{'head_mass_kg':4.5,'object_mass_kg':2,'head_COM_shift_from_baseline_mm':[0,0,0],
       'head_COM_uncertainty_mm':50,'object_COM_uncertainty_mm':100,'reserve_COM_uncertainty_mm':100},
      'downstream_mass_kg':downstream,'nominal_cut_moment_triangle_bounds_Nm':bound,'COM_allowance_Nm':allowance,
      'study_factor':1.5,'study_moment_Nm':design,'study_force_N':force,'fastener_group_external_demand':groups,
      'J6_J7_torque_triangle_Nm':triangle_bounds(model)[0][5:].tolist(),
      'limits':['Static triangle moment bounds; not trajectory RMS, impact, stall or fatigue.',
       'Head4.5kg and baseline COM are a sensitivity case, not a new complete head measurement; proposed extension is excluded.',
       'Bolt-group numbers assume equal axial stiffness and rigid plates; no preload/contact separation/prying/friction/thread pull-out qualification.',
       'No solid stress or flexibility result claimed for these rib/ring parts; full contact FEA and root radii remain unresolved.']}

def export(a,op,fp,out):
    frames={'output_adapter':frame([0,0,605],[0,1,0]),'rear_carrier':frame([0,55,595.5],[0,0,1]),'front_ring':frame([0,55,630],[0,0,1])}
    ids={'output_adapter':'ODR-L67-OUT-R4','rear_carrier':'ODR-L67-CARRIER-R4','front_ring':'ODR-L67-FRONT-R4'}
    parts={ids[n]:moved(s,np.linalg.inv(frames[n])) for n,s in a.items()};info=export_parts(out,parts);meshes={};places={}
    frows=features(op,fp);XY=np.array([[1,0,0],[0,1,0]]);XZ=np.array([[1,0,0],[0,0,1]]);YZ=np.array([[0,1,0],[0,0,1]])
    for n,s in a.items():
        name=ids[n];mesh=trimesh.load_mesh(out/(name+'.stl'),process=True);meshes[name]=mesh
        pr=GProp_GProps();BRepGProp.VolumeProperties_s(parts[name].wrapped,pr)
        I=np.array([[pr.MatrixOfInertia().Value(i,j) for j in [1,2,3]] for i in [1,2,3]])*2.7e-12
        places[n]={'part_id':name,'T_world_from_part_mm':frames[n].tolist(),'preceding_joints':6,
           'estimated_COM_world_mm':list(s.Center().toTuple()),'mass_kg_6061':s.Volume()*2.7e-6,
           'inertia_about_COM_in_part_axes_kg_m2':I.tolist()}
        assert np.linalg.eigvalsh(I).min()>0
        d=ezdxf.new('R2010');d.units=ezdxf.units.MM;ms=d.modelspace()
        for label,basis,off in zip(['XY','XZ','YZ'],[XY,XZ,YZ],[[0,0],[0,-130],[140,-130]]):
            d.layers.new(label)
            for line in projected_edges(mesh,basis):ms.add_line(tuple(line[0]+off),tuple(line[1]+off),dxfattribs={'layer':label})
        for r in frows:
            if r['part']==name.split('-')[2] and r['axis']=='+Z':ms.add_circle((r['x_mm'],r['y_mm']),r['diameter_mm']/2)
        ms.add_text(name+' / mm / FIT STUDY; NOT PRODUCTION / SEE PDF AND CSV',dxfattribs={'height':2.5}).set_placement((-55,-160))
        dp=out/(name+'.dxf');d.saveas(dp);rd=ezdxf.readfile(dp);assert not rd.audit().errors and rd.units==ezdxf.units.MM
        info[name]['dxf_audit_passed']=True;info[name]['sha256'][dp.name]=sha(dp)
    with (out/'hole-features.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(frows[0]));w.writeheader();w.writerows(frows)
    (out/'part-placements.json').write_text(json.dumps({'revision':REV,'parameters_sha256':PARAM_SHA,'status':'independent candidate; nominal fit only','instances':places},indent=2)+'\n')
    ap=out/'ODR-LINK67-original-assembly.step';cq.exporters.export(cq.Compound.makeCompound(list(a.values())),str(ap))
    read=cq.importers.importStep(str(ap)).val();assert read.isValid() and len(read.Solids())==3
    return parts,meshes,info

def pdf(path,font,a,parts,meshes,e,op,fp):
    from reportlab.lib.pagesizes import A3,landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader
    from draw_layout import Sheet,TEAL,GRAY
    pdfmetrics.registerFont(TTFont('L67CN',str(font)));c=canvas.Canvas(str(path),pagesize=landscape(A3));s=Sheet(c,'L67CN')
    c.setTitle('Odradek LINK67 fit-study dimensions; NOT PRODUCTION');c.setAuthor('Auromix contributors')
    XY=np.array([[1,0,0],[0,1,0]]);XZ=np.array([[1,0,0],[0,0,1]]);YZ=np.array([[0,1,0],[0,0,1]])
    def text(x,y,lines,size=9):
        for i,t in enumerate(lines):s.text(x,y-i*7,t,size)
    def view(name,basis,origin,scale=1):
        for line in projected_edges(meshes[name],basis):s.line(*(line*scale+origin),TEAL,.45)
    def foot(n):
        s.line((15,19),(405,19),GRAY,.4);s.text(15,12,'单位mm | 6061-T6候选 | 名义试装图，未放行制造/承载 | 原厂CAD不分发',8);s.text(405,12,f'{n}/4 | {REV}',8,align='right');c.showPage()
    s.header('J6 → J7 腕部承力连接','保持 R4-layout-03 轴原点；三件原创实体、24螺钉与分阶段工具检查',REV)
    # Dimension-derived assembly view, original geometry only.
    for n,shape in a.items():
        vs,ts=shape.tessellate(.05,.12);mesh=trimesh.Trimesh(vertices=np.array([p.toTuple() for p in vs]),faces=ts,process=True)
        for line in projected_edges(mesh,YZ):s.line(*((line-[25,605])*1.5+[115,177]),TEAL,.45)
    text(225,248,['J6 输出中心 [0,0,605]，轴 +Y。','J7 输出中心 [0,55,640]，轴 +Z。','J7 后安装接触面 Z609.5；前面 Z630。',
      '输出板 Y0…6；四支柱到 Y22。','后架脚 Y22…34；整体后环 Z595.5…609.5。','前压环 Z630…633；原厂通孔夹持。',
      '16×J6输出M3：有效牙起点未知，长度TBD。','4×M5×25：自由12，几何啮合13，盲孔余6。','4×M3×40：自由23.5，后环啮合14，后伸2.5。'])
    text(25,83,['装配：先输出板及16颗M3，再+Y装后架并拧4颗M5；J7从+Z插入，最后装前环和4颗M3。',
      '工具检查假设尚未安装头部。J7本体0…140mm插入使用连续包含包络；其余三步为离散样本。',
      '零位fit通过不等于运行可达。新头架在q7=±90°会碰J6；加长/重布及全臂运动验证仍待完成。',
      '仅尺寸与原始实体供设计审查；基准形位、公差链、预紧、材料批证和接触强度未冻结。'])
    foot(1)
    s.header('输出板 / ODR-L67-OUT-R4','局部 +Z = 世界 +Y；A为背面Z0，B为中央轴线，C为局部+X方向',REV)
    view('ODR-L67-OUT-R4',XY,[100,191],1.3);view('ODR-L67-OUT-R4',XZ,[100,95],1.3)
    text(205,250,['主板：Ø72并104×48矩形联合外形，厚6。','中央贯通Ø44；背面Ø47.6沉台深2.5。','四柱中心 (X,Y)=(±44,±16)，柱Ø14。','柱端Z22；底孔Ø4.2，从Z22向下深19。','M5×0.8有效牙深至少14；平底余厚3。','四条筋：宽12，自r27.5延伸至四柱。',
      '筋截面(r,z)：(27.5,6)→(r柱,6)→(r柱,22)→(27.5,12)。','筋根圆角/刀路未冻结；不可把尖角CAD用于疲劳放行。','16×Ø3.5贯通；头让位Ø6.4，底面Z4。','PCD54真实孔位为下表；不按均分孔代替。'],8.5)
    for i,(x,y) in enumerate(op):s.text(205+(i//8)*96,170-(i%8)*8,f'{i+1:02}: {x:+.5f}, {y:+.5f}',8)
    text(205,94,['上表是局部 X,Y，CSV保留原始精度。','螺纹只画底孔；不把名义插入深度当有效啮合。','中央孔/沉台是避让，不声称已定定位配合。'])
    foot(2)
    s.header('带脚后环 / ODR-L67-CARRIER-R4','局部原点=[0,55,595.5]；A为环顶面Z14，B为中心轴线，C为X方向',REV)
    view('ODR-L67-CARRIER-R4',XY,[95,194],1.4);view('ODR-L67-CARRIER-R4',XZ,[95,89],1.4)
    text(205,250,['后环：Ø76 / Ø58.6，厚14。','整体两侧脚：14×12×48，中心(±44,−27,9.5)。','桥体：24×24×14，中心(±37,−21,7)。','中心Ø58.6去除联合体内部重叠材料。','4×M3×0.5贯通；底孔Ø2.5，孔圈PCD64。',
      '孔坐标(X,Y)=(±22.627417, ±22.627417)。','后环内缘至Ø2.5底孔的名义最薄径向壁1.45。','4×Ø5.5沿+Y贯通脚，Y−33…−21。','侧孔(X,Z)=(±44,−6.5)、(±44,25.5)。','M5螺钉从世界+Y拧入，帽座世界Y34。'])
    text(205,158,['此件从实体毛坯铣削；不是三块相碰的悬空构造。','原始CAD只有一体实体，无焊缝假设。','环与桥、脚连接根部圆角和刀具半径未冻结。','不能用金属候选材料名替代局部应力/拉脱验算。','打印STL仅供无动力手动试装，孔需按实测修配。'])
    foot(3)
    s.header('前压环与接口载荷 / ODR-L67-FRONT-R4','前压环局部原点=[0,55,630]；A为底面Z0，B为中心轴线，C为X方向',REV)
    view('ODR-L67-FRONT-R4',XY,[95,196],1.6);view('ODR-L67-FRONT-R4',XZ,[95,100],1.6)
    L=e['load_screening']
    text(205,252,['Ø76 / Ø59.2，厚3；4×Ø3.5在(±22.627417,±22.627417)。','原厂四个头让位Ø6.2，坐标(±32,0)/(0,±32)。','固定孔与内径名义径向余壁0.65，仍须公差/强度验证。',
      '候选紧固件：Accu SSC-M5-25-12.9 / SSC-M3-40-12.9。','两种头包络分别Ø8.72×5 / Ø5.68×3。','M5全牙；M3最小牙长18，可覆盖14mm后环。',
      f'三件金属 {L["metal_mass_kg"]:.6f} kg；另留0.100kg硬件预算。',
      f'金属COM世界 {np.array(L["COM_world_mm"]).round(4).tolist()} mm。',
      f'归属前6个关节；头4.5kg+工件2kg，静态研究倍率1.5。',
      f'最大接口力矩研究值 {L["study_moment_Nm"]:.3f} Nm；合力 {L["study_force_N"]:.3f} N。'],8.5)
    for i,(n,r) in enumerate(L['fastener_group_external_demand'].items()):s.text(205,174-i*8,f'{n}: 外载轴向需求 {r["maximum_abs_axial_external_force_N"]:.1f} N/颗',9)
    text(205,138,['螺钉数值为刚板/等刚度分担敏感性，不是预紧力。','没有声称环、筋、铝牙、原厂轴承或疲劳已满足载荷。','本载荷仍用原face780/TCP890；头部加长后要重算。','形位与尺寸公差、表处厚度、止口与刀路待生产设计。'])
    foot(4);c.save();assert len(PdfReader(path).pages)==4

def main():
    p=argparse.ArgumentParser();p.add_argument('--font',type=Path,required=True);args=p.parse_args()
    e=json.loads((OUT/'geometry-probe.json').read_text());assert not e['errors'] and 'insertions' in e['checks']
    assert e['generator_sha256']==sha(ROOT/'engineering/build_link67_study.py')
    models={m['id']:m for m in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models']}
    a,op,fp,*_=make_parts(models['RH17-B']['unified_joint_interface'],models['RH14-N']['unified_joint_interface'])
    parts,meshes,checks=export(a,op,fp,OUT);e['export_checks']=checks;e['load_screening']=loads(a,op,fp);e['drawing_generator_sha256']=sha(Path(__file__))
    e['limits']=['Nominal home geometry and insertion only; main carrier violates q7 +-90 deg against J6.',
      'No complete electronic/cable geometry; no tolerances, fatigue, preload, bearing-load or physical strength qualification.',
      'Vendor output screw effective thread length remains unknown; modeled7mm shank is only a first3mm-channel geometric probe.',
      'Rib-root manufacturing radii and toolpath are not finalized; drawing is a review candidate, not a complete production release.']
    pdf(OUT/'ODR-LINK67-candidate-dimensions.pdf',args.font,a,parts,meshes,e,op,fp);e['pdf_sha256']=sha(OUT/'ODR-LINK67-candidate-dimensions.pdf')
    sources={'M5x25':{'part':'Accu SSC-M5-25-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/16048-SSC-M5-25-12-9','head_D_H_mm':[8.72,5],'full_thread':True,'mass_g':4.8},
       'M3x40':{'part':'Accu SSC-M3-40-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/16011-SSC-M3-40-12-9','head_D_H_mm':[5.68,3],'minimum_thread_mm':18,'mass_g':3.1},
       'vendor':{'url':'https://www.myactuator.com/downloads-rhseries','files':['RH-17-100-E-B-D 3D-A.STEP','RH-14-100-E-N-D 3D-A0.STEP']}}
    bom={'revision':REV,'sources':sources,'original_parts':[dict(id=n,qty=1,candidate_material='6061-T6',mass_kg=s.Volume()*2.7e-6) for n,s in parts.items()],
        'screws':[{'source':'M5x25','qty':4,'nominal_engagement_mm':13,'blind_bottom_clearance_mm':6},{'source':'M3x40','qty':4,'nominal_engagement_mm':14,'rear_protrusion_mm':2.5},{'source':'J6_output_M3_length_TBD','qty':16}],
        'known_eight_screws_mass_kg':.0316,'all_hardware_mass_budget_kg':.1,'no_purchase_made':True,'preload_selected':False}
    (OUT/'bom.json').write_text(json.dumps(bom,indent=2)+'\n')
    with (OUT/'screw-stacks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(e['hardware'][0]));w.writeheader();w.writerows(e['hardware'])
    (OUT/'evidence.json').write_text(json.dumps(e,indent=2)+'\n')
    print(json.dumps(e['load_screening'],indent=2))

if __name__=='__main__':main()
