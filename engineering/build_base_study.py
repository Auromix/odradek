# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Original anchored J1 base candidate; nominal study, not manufacturing release.

Vendor geometry is imported ONLY for local checks and an explicitly requested
private assembly outside this repository. Public CAD contains original parts.
No threads are modeled: tapping holes show pilot drills; screw free portions
are checked separately, never treating intended thread engagement as collision.
"""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

import cadquery as cq
import ezdxf
import numpy as np
import trimesh
from pypdf import PdfReader
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from arm_screening import arm_parameters
from review_arm_screening import reference_gravity, triangle_bounds
from mount_interface_study import load_vendor, collision, bores, ring, rect
from draw_layout import Sheet, TEAL, GRAY, LIGHT, AMBER, projected_edges

ROOT = Path(__file__).resolve().parents[1]
PARAM_SHA = '4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
REVISION = 'R4-BASE-01'
G = 9.80665
DENSITY = 2.70e-6  # kg/mm3, source thyssenkrupp EN AW-6061 p3
E = 70000.0       # N/mm2, same source, guidance value not certification
LEG_RADIUS = 65.0
LEG_X = LEG_RADIUS / np.sqrt(2)
LEG_XY = np.array([[LEG_X, LEG_X], [-LEG_X, LEG_X], [-LEG_X, -LEG_X], [LEG_X, -LEG_X]])
ANCHOR_XY = np.array([[110.,110.],[-110.,110.],[-110.,-110.],[110.,-110.]])
SOURCES = [
 {'id':'M4-45','part':'Accu SSC-M4-45-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/16031-SSC-M4-45-12-9','role':'8 existing interface screws; head 7.22 x 4, min thread20; nominal stack44.2'},
 {'id':'M6-20','part':'Accu SSCF-M6-20-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/16076-SSCF-M6-20-12-9','role':'4 top screws; full thread, head max10.22 x 6, pitch1, key5; catalogue listing, stock not confirmed'},
 {'id':'M6-25','part':'Accu SSC-M6-25-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/16077-SSC-M6-25-12-9','role':'4 bottom screws; full thread, head max10.22 x 6, pitch1, key5'},
 {'id':'M8-70','part':'Accu SSC-M8-70-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/16118-SSC-M8-70-12-9','role':'4 conditional anchors for the 30mm desk example only; max head13.27 x 8, min thread28, pitch1.25; webpage head max13.27 conservatively exceeds linked older PDF13'},
 {'id':'M8-nut','part':'RS PRO 2867149','url':'https://docs.rs-online.com/c3e3/A700000011204644.pdf','page':2,'role':'4 DIN934 Class12 M8 nuts; AF13, height6.5; external CAD hex circumscribed from AF13'},
 {'id':'M8-washer','part':'Wurth 515002018','url':'https://www.wurth.es/arn-iso7089-a4-300hv-8','role':'8 ISO7089 A4 300HV washers, 8.4 x16 x1.6; material/finish compatibility not released'},
 {'id':'material','part':'thyssenkrupp EN AW-6061 data sheet, 06.2018','url':'https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf','pages':[2,3],'role':'plate/bar T6 minimum yield240MPa in relevant size ranges; E70000MPa and density2.70 guidance only; purchased batch material certificate still required'},
 {'id':'RH','part':'MYACTUATOR RH25-B vendor STEP/2D-A0','url':'https://www.myactuator.com/downloads-rhseries','role':'local source hashes inherited from independently extracted interface records'}]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def box(w, d, h, z=0):
    return cq.Workplane('XY').workplane(offset=z).rect(w,d).extrude(h)


def make_parts(tdesk):
    # J1 world datum unchanged: output plane105.2, fixed rear contact59.5.
    bottom = box(260,260,16).cut(bores([[0,0]],55,-1,18))
    bottom = bottom.cut(bores(ANCHOR_XY.tolist(),4.5,-1,18))
    bottom = bottom.cut(bores(LEG_XY.tolist(),3.3,-1,18)).cut(bores(LEG_XY.tolist(),5.5,-1,8))
    # Through M6x1 tapping pilot. Nominal bolt ends remain 7.5mm apart.
    leg = box(24,24,33.5).cut(bores([[0,0]],2.5,-1,36)).val()
    backing = box(260,260,8).cut(bores([[0,0]],55,-1,10)).cut(bores(ANCHOR_XY.tolist(),4.5,-1,10)).val()
    rear = cq.importers.importStep(str(ROOT/'engineering/generated/mount-study/ODR-J1-REAR-R4.step')).val()
    front = cq.importers.importStep(str(ROOT/'engineering/generated/mount-study/ODR-J1-FRONT-R4.step')).val()
    parts = {'ODR-BASE-PLATE-R4':bottom.val(),'ODR-BASE-LEG-R4':leg,'ODR-BASE-BACK-R4':backing,
             'ODR-J1-REAR-R4':rear.translate((0,0,55.7)), 'ODR-J1-FRONT-R4':front.translate((0,0,15.5))}
    assembled = {'base_plate':bottom.val(),'backing_plate':backing.translate((0,0,-tdesk-8)),
                 'rear_ring':rear.translate((0,0,105.2)), 'front_ring':front.translate((0,0,105.2))}
    for i,(x,y) in enumerate(LEG_XY):assembled[f'leg_{i+1}']=leg.translate((x,y,16))
    return parts, assembled


def export_parts(out, parts):
    checks = {}
    for name,shape in parts.items():
        assert shape.isValid() and len(shape.Solids()) == 1
        step,stl = [out/f'{name}.{ext}' for ext in ['step','stl']]
        cq.exporters.export(shape,str(step))
        cq.exporters.export(shape,str(stl),tolerance=.025,angularTolerance=.08)
        reread=cq.importers.importStep(str(step)).val()
        mesh=trimesh.load_mesh(stl,process=True)
        assert reread.isValid() and len(reread.Solids())==1 and abs(reread.Volume()-shape.Volume())<1e-4
        assert mesh.is_watertight and mesh.body_count==1
        checks[name]={'volume_mm3':shape.Volume(),'mass_kg_6061':shape.Volume()*DENSITY,
                     'valid_single_solid':True,'step_roundtrip_volume_error_mm3':abs(reread.Volume()-shape.Volume()),
                     'stl_watertight':True,'stl_body_count':int(mesh.body_count),'bbox_mm':[shape.BoundingBox().xlen,shape.BoundingBox().ylen,shape.BoundingBox().zlen],
                     'sha256':{p.name:sha(p) for p in [step,stl]}}
    return checks


def circle_feature(dxf, point, radius, layer):
    if layer not in dxf.layers:dxf.layers.new(layer)
    dxf.modelspace().add_circle(point,radius,dxfattribs={'layer':layer})


def make_dxf(path,name,parts,interface):
    d=ezdxf.new('R2010');d.units=ezdxf.units.MM;m=d.modelspace()
    if name in ['ODR-BASE-PLATE-R4','ODR-BASE-BACK-R4']:
        m.add_lwpolyline([(-130,-130),(130,-130),(130,130),(-130,130)],close=True)
        circle_feature(d,(0,0),55,'CENTRE_THRU')
        for p in ANCHOR_XY:circle_feature(d,p,4.5,'M8_THRU')
        if name=='ODR-BASE-PLATE-R4':
            for p in LEG_XY:
                circle_feature(d,p,3.3,'M6_THRU');circle_feature(d,p,5.5,'BOTTOM_CBORE_D11_DEEP7')
    elif name=='ODR-BASE-LEG-R4':
        m.add_lwpolyline([(-12,-12),(12,-12),(12,12),(-12,12)],close=True)
        circle_feature(d,(0,0),2.5,'M6x1_THROUGH_TAP_DRILL')
    else:
        rear=name=='ODR-J1-REAR-R4'
        circle_feature(d,(0,0),75 if rear else 58,'OUTLINE')
        circle_feature(d,(0,0),47.7 if rear else 45,'CENTRE_THRU')
        for p in interface['RH25_fixed_holes_xy_mm']:circle_feature(d,p,1.65 if rear else 2.25,'M4_TAP_DRILL' if rear else 'M4_CLEAR')
        for p in (LEG_XY if rear else interface['RH25_original_screw_head_relief_xy_mm']):
            circle_feature(d,p,3.3 if rear else 3.8,'LEG_M6_CLEAR' if rear else 'OEM_HEAD_RELIEF')
    # Exact orthographic feature edges, separate from authoritative face circles.
    shape=parts[name];bb=shape.BoundingBox()
    m.add_lwpolyline([(bb.xmin,-180),(bb.xmax,-180),(bb.xmax,-180+bb.zlen),(bb.xmin,-180+bb.zlen)],close=True)
    m.add_text(name+' / mm / MODEL SPACE 1:1 / CANDIDATE ONLY',dxfattribs={'height':3}).set_placement((-130,-195))
    m.add_text('TOP VIEW + OUTLINE SIDE VIEW; axial holes/threads per PDF; no manufacturing release.',dxfattribs={'height':2.3}).set_placement((-130,-201))
    d.saveas(path);read=ezdxf.readfile(path);assert not read.audit().errors and read.units==ezdxf.units.MM
    return {'circle_count':len(read.modelspace().query('CIRCLE')),'audit_passed':True,'sha256':sha(path)}


def pressure_footprint(ro,ri):
    # Unit-height intersection yields actual contact area and centroid.
    foot=box(24,24,1).translate((LEG_X,LEG_X,0)).val()
    support=ring(ro,ri,0,1).val()
    patch=foot.intersect(support).cut(bores([LEG_XY[0].tolist()],3.3,-1,3).val())
    centre=patch.Center()
    return {'area_mm2':patch.Volume(),'centroid_xy_mm':[centre.x,centre.y],
            'radial_eccentricity_mm':np.linalg.norm(np.array([centre.x,centre.y])-LEG_XY[0])}


def calculate_loads(p,parts):
    model=arm_parameters(p)
    origins=np.asarray([j['origin_m'] for j in model['joints']])
    shoulder_bound=triangle_bounds(model)[0][1]
    # Horizontal distance of all parts preceding J2 is invariant under J1 yaw.
    extra=sum(b['mass_kg']*G*np.linalg.norm(np.asarray(b['com_home_m'])[:2]) for b in model['bodies'] if b['preceding_joints']<=1)
    base_bound=shoulder_bound+extra
    head_path=sum(np.linalg.norm(origins[k+1]-origins[k]) for k in range(1,6))+np.linalg.norm(np.array(p['head']['head_com_home_mm'])*.001-origins[6])
    uncertainty={'object_COM_100mm_Nm':2*G*.1,'head_COM_50mm_at_2_2kg_Nm':2.2*G*.05,
                 'extra_head_0_2kg_Nm':.2*G*head_path}
    expanded=base_bound+sum(uncertainty.values());design=1.5*expanded
    mass_arm=sum(b['mass_kg'] for b in model['bodies'])
    base_mass=sum(s.Volume()*DENSITY*(4 if name=='ODR-BASE-LEG-R4' else 1) for name,s in parts.items())
    # Add 0.5kg explicit hardware/wiring reserve; upper loads deliberately include
    # all base parts, even those below the posts, as a simple conservative N budget.
    n=1.5*G*(mass_arm+.2+base_mass+.5)
    fpost=n/4+design*1000/(2*LEG_RADIUS)
    fM4=n/8+design*1000/(4*51)
    # Equal-stiffness four-point group. Maximum over arbitrary moment azimuth.
    fanchor=design*1000/(4*110**2)*np.hypot(110,110)  # no gravity relief
    post_area=24**2-np.pi*3**2
    post_I=24**4/12-np.pi*3**4/4
    top=pressure_footprint(75,47.7);bottom=pressure_footprint(1000,55)
    ecc=top['radial_eccentricity_mm']+bottom['radial_eccentricity_mm']
    post_stress=fpost/post_area+fpost*ecc*12/post_I
    # Strip model is a sensitivity estimate, NOT proven conservative plate bound.
    span=np.linalg.norm(ANCHOR_XY[0]-LEG_XY[0]);width=24.;thickness=16.
    plate_sigma=6*fpost*span/(width*thickness**2)
    plate_delta=fpost*span**3/(3*E*(width*thickness**3/12))
    I=post_I;K=1.;L=33.5
    slenderness=K*L/np.sqrt(I/post_area)
    # Numerical validation of moment bound, independently transformed COMs.
    rng=np.random.default_rng(705)
    lo,hi=np.deg2rad(np.array([j['limit_deg'] for j in p['joints']])).T
    q=np.vstack([rng.uniform(lo,hi,(5000,7)),np.deg2rad([0,90,0,0,0,0,0])])
    _,(_,_,_,states)=reference_gravity(model,q)
    torque=np.zeros((len(q),3))
    for b,point in states:torque+=np.cross(point,b['mass_kg']*np.array([0,0,-G]))
    magnitude=np.linalg.norm(torque[:,:2],axis=1)
    assert np.max(magnitude)<base_bound+1e-10
    # Rigid equal-stiffness group conserves imposed moment for arbitrary azimuth.
    errors=[]
    for xy in [LEG_XY,ANCHOR_XY]:
        for angle in np.linspace(0,2*np.pi,721):
            M=np.array([np.cos(angle),np.sin(angle)])*design*1000
            F=(M[0]*xy[:,1]-M[1]*xy[:,0])/np.sum(xy[:,0]**2)
            recovered=np.array([sum(F*xy[:,1]),-sum(F*xy[:,0])])
            errors.append(float(np.max(abs(recovered-M))))
    assert max(errors)<1e-8
    return {'model_mass_arm_kg':mass_arm,'base_original_mass_kg':base_mass,'hardware_wiring_reserve_kg':.5,
      'shoulder_triangle_Nm':shoulder_bound,'upstream_off_axis_weight_bound_Nm':extra,'nominal_base_overturning_bound_Nm':base_bound,
      'uncertainty_increment':uncertainty,'expanded_static_base_bound_Nm':expanded,'study_multiplier':1.5,
      'study_design_moment_Nm':design,'study_vertical_budget_N':n,
      'post_max_abs_force_equal_stiffness_N':fpost,'M4_max_abs_external_force_N':fM4,
      'anchor_max_tension_equal_stiffness_no_weight_relief_N':fanchor,
      'anchor_one_fastener_all_moment_over_110mm_no_load_sharing_N':design*1000/110,
      'single_anchor_110mm_assumption':'Tension/compression resultant lines remain at least110mm apart; no prying amplification. Not a universal upper bound.',
      'post_area_net_major_diameter_mm2':post_area,'post_I_net_mm4':post_I,
      'post_support_top':top,'post_support_bottom':bottom,'post_nominal_axial_plus_contact_eccentric_stress_MPa':post_stress,
      'post_contact_nominal_pressure_MPa':fpost/min(top['area_mm2'],bottom['area_mm2']),
      'post_slenderness_pinned':slenderness,'post_Euler_N_not_applicable_as_short_column_capacity':np.pi**2*E*I/(K*L)**2,
      'post_M6_thread_geometric_penetration_top_bottom_mm':[10,16],
      'M6_external_stress_at_20_1mm2_MPa':fpost/20.1,'M4_external_stress_at_8_78mm2_MPa':fM4/8.78,
      'plate_strip_span_mm':span,'plate_strip_width_mm':width,'plate_strip_sigma_MPa':plate_sigma,'plate_strip_deflection_mm':plate_delta,
      'plate_strip_sensitivity_only':'No guaranteed load spread width; holes, contact, prying, desk compliance, preloads and torsion omitted.',
      'rear_M4_min_ligament_to_major_thread_mm':51-47.7-2,
      'unanchored_favourable_centred_weight_restoring_Nm':(mass_arm+base_mass+.5)*G*.13,
      'sample_count':len(q),'sampled_max_base_overturning_Nm':float(np.max(magnitude)),
      'sampled_worst_q_deg':np.rad2deg(q[np.argmax(magnitude)]).tolist(),'horizontal_pose_base_moment_vector_Nm':torque[-1].tolist(),
      'sampled_worst_base_moment_vector_Nm':torque[np.argmax(magnitude)].tolist(),
      'nominal_bound_assert_passed':True,'force_group_reconstruction_max_error_Nmm':max(errors),
      'limits':['55.945 is not directly a base-bearing bound; upstream J2 housing added explicitly.',
        'Expanded uncertainties are stated budgets, not limits on every body COM or load.',
        '1.5 multiplier is an interim study choice, not a certified safety factor.',
        'No inertial/contact/cable/impact/J1 yaw torque or preload force included.',
        'Equal-stiffness reactions are not upper bounds if contacts lift or stiffness differs.',
        'Material batch, fatigue, fastener preload, thread-edge failure, prying and desk/frame anchorage remain unqualified.']}


def hardware(tdesk,p25):
    full={};free={};tools={}
    for i,xy in enumerate(LEG_XY):
        pts=[xy.tolist()]
        full[f'M6top_{i}']=bores(pts,3,39.5,20).union(bores(pts,5.11,59.5,6)).val()
        free[f'M6top_free_{i}']=bores(pts,3,49.5,10).union(bores(pts,5.11,59.5,6)).val()
        full[f'M6bottom_{i}']=bores(pts,3,7,25).union(bores(pts,5.11,1,6)).val()
        free[f'M6bottom_free_{i}']=bores(pts,3,7,9).union(bores(pts,5.11,1,6)).val()
        tools[f'M6top_driver_{i}']=bores(pts,3,65.5,30).val()
        tools[f'M6bottom_driver_{i}']=bores(pts,3,-30,31).val()
    for i,xy in enumerate(np.asarray(p25)):
        pts=[xy.tolist()]
        full[f'M4_{i}']=bores(pts,2,48.7,45).union(bores(pts,3.61,93.7,4)).val()
        # Rear ring is threaded at49.5..59.5; only confirmed free regions checked.
        free[f'M4_free_{i}']=bores(pts,2,59.5,34.2).union(bores(pts,2,48.7,.8)).union(bores(pts,3.61,93.7,4)).val()
        tools[f'M4_driver_{i}']=bores(pts,3,97.7,35).val()
    # Nominal desk sample30; general hardware stack length is conditional.
    for i,xy in enumerate(ANCHOR_XY):
        pts=[xy.tolist()];x,y=xy
        full[f'M8_{i}']=bores(pts,4,17.6-70,70).union(bores(pts,13.27/2,17.6,8)).val()
        free[f'M8_free_{i}']=full[f'M8_{i}']
        full[f'washer_upper_{i}']=ring(8,4.2,16,1.6).val().translate((x,y,0))
        full[f'washer_lower_{i}']=ring(8,4.2,-tdesk-9.6,1.6).val().translate((x,y,0))
        # Nut major-ID removes the screw's nominal major cylinder; helix omitted.
        full[f'nut_{i}']=cq.Workplane('XY').workplane(offset=-tdesk-16.1).polygon(6,13/np.cos(np.pi/6)).extrude(6.5).cut(bores([[0,0]],4,-tdesk-17,9)).val().translate((x,y,0))
        tools[f'M8_top_driver_{i}']=bores(pts,4,25.6,30).val()
        # Socket envelope ring ID7.6 (around AF13 hex) / OD22, no nut collision.
        tools[f'M8_nut_socket_{i}']=ring(11,7.6,-tdesk-45,35.4).val().translate((x,y,0))
    for k in full:
        if k.startswith(('washer','nut')):free[k]=full[k]
    return full,free,tools


def draw_page_end(s,n):
    s.line((15,16),(405,16),GRAY,.5)
    s.text(15,10,'mm | 名义结构研究 / 非制造放行 | 打印件仅无载手动试装 | 必须桌面锚固',8)
    s.text(405,10,f'{n}/4 | A3 横向 | '+REVISION,8,align='right')


def render_meshes(s,shapes,basis,origin,scale):
    for name,shape in shapes.items():
        vertices,faces=shape.tessellate(.25)
        mesh=trimesh.Trimesh(np.array([v.toTuple() for v in vertices]),np.array(faces),process=False)
        for ends in projected_edges(mesh,np.asarray(basis)):
            a,b=np.asarray(origin)+scale*ends
            s.line(a,b,AMBER if 'ring' in name else TEAL,.23)


def dim(s,a,b,label,offset=7):
    a,b=np.array(a,float),np.array(b,float);v=b-a;normal=np.array([-v[1],v[0]])/np.linalg.norm(v)
    x,y=a+offset*normal,b+offset*normal
    s.line(a,x,GRAY,.25);s.line(b,y,GRAY,.25);s.arrow(x,y,GRAY,.35);s.arrow(y,x,GRAY,.35)
    centre=(x+y)/2+2*normal;s.text(*centre,label,8,align='center')


def make_pdf(path,font,parts,assembled,e):
    pdfmetrics.registerFont(TTFont('BaseCN',str(font)))
    c=canvas.Canvas(str(path),pagesize=landscape(A3),pageCompression=1)
    c.setTitle('Odradek anchored J1 base candidate - NOT FOR MANUFACTURE');c.setAuthor('Auromix contributors')
    s=Sheet(c,'BaseCN');loads=e['loads']
    s.header('J1 桌面开腔底座候选','世界 Z=0 为桌面上表面；J1 输出面 Z=105.2 保持不变；原厂 CAD 仅本地核验',REVISION)
    render_meshes(s,assembled,[[1,0,0],[0,1,0]],[101,169],.55)
    s.text(20,253,'俯视 1:1.818 / 原创零件边线，未消隐',10,TEAL)
    dim(s,(29.5,97.5),(172.5,97.5),'260')
    s.text(20,80,'底板 260×260×16；中央Ø110贯通；桌面需对应开孔。',9)
    s.text(20,73,'4×M8锚固中心 (±110,±110)；桌下背板260×260×8。',8)
    s.text(20,66,'桌厚30仅作螺钉堆叠示例；桌板、支架、地面约束未选定。',8)
    render_meshes(s,assembled,[[1,0,0],[0,0,1]],[306,154],.65)
    s.text(220,253,'正视 1:1.538 / 原厂外形以尺寸剖示表达',10,TEAL)
    # Dimension-based OEM envelope only, not copied vendor CAD.
    ox,oz,k=306,154,.65
    rect(s,ox-k*47.4,oz+k*2,k*94.8,k*57.5,LIGHT,GRAY)
    rect(s,ox-k*55,oz+k*59.5,k*110,k*30.2,LIGHT,GRAY)
    rect(s,ox-k*42.5,oz+k*89.7,k*85,k*15.5,LIGHT,GRAY)
    for z,lab in [(105.2,'J1输出105.2'),(59.5,'后接触59.5'),(49.5,'后环底49.5'),(16,'底板顶16'),(2,'后壳最低2'),(0,'桌面0')]:
        y=oz+k*z;ty={16:174,2:163,0:152}.get(z,y)
        s.line((ox+40,y),(378,ty),GRAY,.3);s.line((378,ty),(390,ty),GRAY,.3);s.text(392,ty-1,lab,7)
    s.text(220,112,'4×24方柱高33.5，中心PCD130；支柱不接触后壳。',8)
    s.text(220,105,'后壳离桌面仅2；中央桌面孔提供接插件/线束下引空间。',8)
    s.text(220,98,'图中的净空不是已选择接头的弯曲半径或维护可达证明。',8)
    s.text(220,85,f'名义基座倾覆上界 {loads["nominal_base_overturning_bound_Nm"]:.3f} N·m；',10,TEAL)
    s.text(220,77,f'含指定不确定性并乘1.5：{loads["study_design_moment_Nm"]:.3f} N·m。',10,TEAL)
    s.text(220,66,'桌面锚固必需；整桌抗倾覆与桌板局部强度仍待校核。',9)
    s.text(20,39,'状态：原创几何名义无穿透；受力为手算筛查。未包含负载运行、碰撞冲击、停止惯量、疲劳及紧固预紧验收。',8)
    s.text(20,31,'参数 SHA256 '+PARAM_SHA,6.8,GRAY)
    draw_page_end(s,1);c.showPage()

    s.header('底板与桌下背板','零件局部原点位于底面中心；X/Y 对称轴；正视孔坐标为主，侧视显示轴向特征',REVISION)
    o=np.array([99.,174.]);k=.5
    for a,b in [((-130,-130),(130,-130)),((130,-130),(130,130)),((130,130),(-130,130)),((-130,130),(-130,-130))]:s.line(o+k*np.array(a),o+k*np.array(b),TEAL)
    s.circle(o,55*k,TEAL)
    for i,p in enumerate(ANCHOR_XY):s.circle(o+k*p,4.5*k,TEAL);s.text(*(o+k*p+[3,2]),f'A{i+1}',7)
    for i,p in enumerate(LEG_XY):
        s.circle(o+k*p,3.3*k,AMBER);s.circle(o+k*p,5.5*k,AMBER);s.text(*(o+k*p+[4,2]),f'L{i+1}',7)
    dim(s,o+[-65,-65],o+[65,-65],'260')
    dim(s,o+[-65,-65],o+[-65,65],'260',-10)
    s.text(20,253,'ODR-BASE-PLATE-R4 / 数量1 / 1:2',10,TEAL)
    s.text(20,84,'中央Ø110通；4×Ø9通；4×Ø6.6通+底侧Ø11沉孔深7。',8.5)
    s.text(20,76,'基准A底面 Z=0；B中心X=0；C中心Y=0；厚16。',8.5)
    # Base bolt stack section.
    ox,oy,k2=273,151,3
    rect(s,ox-18*k2,oy,36*k2,16*k2,'#D2E9EA',TEAL)
    rect(s,ox-5.5*k2,oy,11*k2,7*k2,'#FFFFFF',GRAY)
    rect(s,ox-3.3*k2,oy+7*k2,6.6*k2,9*k2,'#FFFFFF',GRAY)
    rect(s,ox-5.11*k2,oy+1*k2,10.22*k2,6*k2,'#F7E1BF',AMBER)
    rect(s,ox-3*k2,oy+7*k2,6*k2,25*k2,'#F7E1BF',AMBER)
    for z,lab in [(0,'A / 底0'),(1,'头底1'),(7,'座面7'),(16,'板顶16'),(32,'M6×25尖端32')]:
        y=oy+k2*z;s.line((ox+19*k2,y),(355,y),GRAY,.3);s.text(357,y-1,lab,8)
    s.text(220,253,'底部 M6×25 螺钉局部剖示 3:1',10,TEAL)
    s.text(220,136,'杆进入柱16 mm；无垫圈；螺钉头低于底板底面1 mm。',8)
    s.text(220,129,'底侧沉孔留下9 mm板厚；装上桌面前从下方紧固。',8)
    s.text(220,113,'ODR-BASE-BACK-R4 / 数量1',10,TEAL)
    s.text(220,105,'260×260×8；中央Ø110通；4×Ø9通 (±110,±110)。',9)
    s.text(220,97,'背板无支柱孔/沉孔；局部原点在底面，装配Z=-T-8。',8)
    s.text(220,88,'材料候选：6061-T6/T651板；按批材证和工艺再冻结。',8)
    s.text(20,64,'孔坐标表 / mm',9,TEAL)
    for i,(a,l) in enumerate(zip(ANCHOR_XY,LEG_XY)):
        s.text(20,56-i*7,f'A{i+1}: X{a[0]:+.3f} Y{a[1]:+.3f}   L{i+1}: X{l[0]:+.5f} Y{l[1]:+.5f}',8)
    s.text(220,65,'建议复核目标（非已批准公差）：支柱组位置Ø0.10；',8)
    s.text(220,57,'接触平面平面度0.05；沉孔深±0.05；外廓±0.2。',8)
    s.text(220,49,'孔边与外缘去毛刺C0.3建议；CAD未加入通用倒角。',8)
    s.text(220,41,'桌面材质、厚度、挠度、孔边距和桌架固定仍须确认。',8)
    draw_page_end(s,2);c.showPage()

    s.header('支柱、安装环与紧固件','四根支柱相同；上下螺钉同轴，实体牙型未建模；完整有效啮合需扣倒角和不完整牙',REVISION)
    ox,oy,k=64,141,2.7
    rect(s,ox-12*k,oy,24*k,33.5*k,'#D2E9EA',TEAL)
    rect(s,ox-2.5*k,oy,5*k,33.5*k,'#FFFFFF',GRAY)
    dim(s,(ox-12*k,oy),(ox+12*k,oy),'24')
    dim(s,(ox+12*k,oy),(ox+12*k,oy+33.5*k),'33.5',-12)
    s.text(20,253,'ODR-BASE-LEG-R4 / 数量4 / 2.7:1',10,TEAL)
    s.text(20,119,'24×24×33.5；轴向 M6×1 贯通螺纹，CAD底孔Ø5。',8.5)
    s.text(20,111,'材料6061-T6候选；上下端平行度建议0.03；组高差≤0.03。',8)
    s.text(20,103,'孔中心(0,0)；局部底面0；组装世界Z16～49.5。',8)
    s.text(20,91,'上 M6×20 穿后环10，柱内名义10；下 M6×25',8)
    s.text(20,83,'从座面Z7进入柱至Z32，柱内16；两杆端距7.5。',8)
    s.text(20,71,'柱端与环/底板并非24方全接触：中央孔和环外圆',8)
    s.text(20,63,'会削去部分支撑区，实际接触面积及偏心已写入证据。',8)
    s.text(220,253,'沿用真实接口的两件安装环',10,TEAL)
    s.text(220,240,'后环 ODR-J1-REAR-R4：Ø150 / Ø95.4 / 厚10',9)
    s.text(220,231,'8×M4×0.7通牙（Ø3.3底孔）真实PCD102非均布；',8)
    s.text(220,223,'4×Ø6.6 PCD130/45°；固定在支柱顶。',8)
    s.text(220,211,'前环 ODR-J1-FRONT-R4：Ø116 / Ø90 / 厚4',9)
    s.text(220,203,'8×Ø4.5 + 4×Ø7.6原厂螺钉头避让；不拆原厂螺钉。',8)
    s.text(220,191,'世界Z：后环49.5～59.5；原厂法兰59.5～89.7；',8)
    s.text(220,183,'前环89.7～93.7；M4×45头93.7～97.7。',8)
    s.text(220,167,'真实固定孔坐标（mm；原装相位不等于电气零位）',9,TEAL)
    for i,p in enumerate(e['fixed_holes_xy_mm']):s.text(220+(i//4)*88,157-(i%4)*8,f'{i+1}: {p[0]:+.4f}, {p[1]:+.4f}',8)
    s.text(220,111,'原厂头避让中心见 CSV；不得由均分角推测固定孔。',8)
    s.text(220,100,'可购目录件 / 数量',9,TEAL)
    rows=['8× Accu SSC-M4-45-12.9','4× Accu SSCF-M6-20-12.9；4× SSC-M6-25-12.9',
          '4× Accu SSC-M8-70-12.9（仅桌厚30的示例）',
          '4× RS PRO 2867149 M8 Class12；8× Wurth 515002018']
    for i,row in enumerate(rows):s.text(220,91-i*8,row,8)
    s.text(20,43,'M4内缘到螺纹大径剩约1.3；薄壁螺纹、原厂法兰压力和预紧需要单独校核。此处没有给出拧紧扭矩。',8,AMBER)
    s.text(20,33,'打印：零件大平面朝下；PLA/PETG无载手动验证。支柱样件可用Ø6.6贯通+手持销，禁止承托整臂。',8)
    draw_page_end(s,3);c.showPage()

    s.header('受力筛查与装配验证','公式使用 N、mm、MPa；静载/材料数据与未冻结项分列；这些数值不是承载认证',REVISION)
    text_rows=[
      f'肩关节triangle = {loads["shoulder_triangle_Nm"]:.6f} N·m',
      f'上游偏心质量补项 = {loads["upstream_off_axis_weight_bound_Nm"]:.6f} N·m',
      f'基座名义倾覆界 = {loads["nominal_base_overturning_bound_Nm"]:.6f} N·m',
      f'2kg物体COM±100mm；2.2kg头COM±50mm；头质量+0.2kg',
      f'指定不确定性后 = {loads["expanded_static_base_bound_Nm"]:.3f} N·m',
      f'研究倍率1.5 → M = {loads["study_design_moment_Nm"]:.3f} N·m；N预算={loads["study_vertical_budget_N"]:.2f} N',
      f'四柱等刚度：|F|max ≤ N/4 + M/(2r) = {loads["post_max_abs_force_equal_stiffness_N"]:.1f} N',
      f'8个M4：N/8 + M/(4×51) = {loads["M4_max_abs_external_force_N"]:.1f} N',
      f'四锚等刚度且不减重力：Tmax = {loads["anchor_max_tension_equal_stiffness_no_weight_relief_N"]:.1f} N',
      f'单锚 M/110 = {loads["anchor_one_fastener_all_moment_over_110mm_no_load_sharing_N"]:.1f} N（假定反力臂≥110）',
      f'柱含接触偏心名义应力 = {loads["post_nominal_axial_plus_contact_eccentric_stress_MPa"]:.2f} MPa',
      f'板24宽条带/16厚/跨度{loads["plate_strip_span_mm"]:.2f}: σ={loads["plate_strip_sigma_MPa"]:.1f} MPa',
      f'同一条带挠度估算 = {loads["plate_strip_deflection_mm"]:.3f} mm（不是严格上界）',
      f'自立有利恢复矩只有 {loads["unanchored_favourable_centred_weight_restoring_Nm"]:.2f} N·m < 名义倾覆界']
    for i,row in enumerate(text_rows):s.text(20,251-i*11,row,8.8)
    s.text(220,251,'装配顺序（打印验证必须独立支撑关节）',11,TEAL)
    notes=[
     '1. 核实桌面/桌架可承载，加工中央孔与4个锚孔。',
     '2. 底板翻面：用4个M6×25把四柱从底侧装好。',
     '3. 放后环，用4个M6×20由上方连接支柱。',
     '4. 独立托住关节，从上方使后壳穿过后环与底孔。',
     '5. 保留原厂4螺钉，放前压环；装8个M4×45。',
     '6. 放桌面，装背板/垫圈/M8螺钉螺母；预紧另定。',
     '7. 下引线束，补应变释放；先检查接口与维护可达。',
     '8. 打印试装只验证孔位/净空，禁止动力和整臂承载。']
    for i,row in enumerate(notes):s.text(220,238-i*10,row,8)
    s.text(220,146,'已经做的检查',10,TEAL)
    for i,row in enumerate(['原厂42个solid逐对求交；原创部件两两无穿透；',
      '自由螺杆、头部、直驱杆/套筒名义通道无穿透；',
      '每件有效单体、STEP重读体积、STL水密、DXF审计；',
      '底部直驱杆需桌前装配；接头使用30宽预留体积，',
      '尚不是某一真实接插件/电缆的装配验收。']):s.text(220,136-i*9,row,8)
    s.text(220,80,'仍需关闭：预紧/防松/薄壁M4；公差与材料批证；',8.5,AMBER)
    s.text(220,71,'桌板压溃与桌架/地面稳定；动态/接触力；完整线束。',8.5,AMBER)
    s.text(20,76,'材料参考：6061-T6/T651对应规格Rp0.2≥240MPa；E=70000MPa。',8)
    s.text(20,67,'这些值不覆盖局部螺纹、孔边、接触翘起和疲劳；不发布允许载荷。',8)
    s.text(20,45,'一手依据：MYACTUATOR RH25 2D-A0/STEP；Accu螺钉目录；RS PRO螺母datasheet p2；Wurth垫圈；',7.5)
    s.text(20,37,'thyssenkrupp EN AW-6061 (06.2018) p2–3。完整URL、源文件SHA及逐对碰撞记录见 evidence.json / 指南。',7.5)
    draw_page_end(s,4);c.save()
    assert len(PdfReader(str(path)).pages)==4


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rh25-step',type=Path,required=True)
    parser.add_argument('--font',type=Path,required=True)
    parser.add_argument('--parameters',type=Path,default=ROOT/'engineering/parameters/r4-layout.json')
    parser.add_argument('--interfaces',type=Path,default=ROOT/'docs/engineering/sources/rh-interface-extraction.json')
    parser.add_argument('--output',type=Path,default=ROOT/'engineering/generated/base-study')
    parser.add_argument('--private-assembly',type=Path,required=True,help='Must be outside repository; includes vendor geometry.')
    parser.add_argument('--desk-thickness-mm',type=float,default=30.)
    args=parser.parse_args()
    assert not args.private_assembly.resolve().is_relative_to(ROOT.resolve()),'Never publish vendor assembly in repository.'
    assert sha(args.parameters)==PARAM_SHA,'This candidate was reviewed only against the fixed R4 parameter snapshot.'
    assert args.desk_thickness_mm==30,'Only the 30mm illustrative bolt stack is validated. Revise hardware for other desks.'
    args.output.mkdir(parents=True,exist_ok=True);args.private_assembly.parent.mkdir(parents=True,exist_ok=True)
    p=json.loads(args.parameters.read_text());interface=json.loads((ROOT/'engineering/generated/mount-study/evidence.json').read_text())
    source=[m for m in json.loads(args.interfaces.read_text())['models'] if m['id']=='RH25-B'][0]
    vendor=load_vendor(args.rh25_step,source).translate((0,0,105.2))
    parts,assembled=make_parts(args.desk_thickness_mm)
    checks=export_parts(args.output,parts)
    for name in parts:checks[name]['dxf']=make_dxf(args.output/f'{name}.dxf',name,parts,interface)
    # Print-only leg without tapped holes; straight clearance for loose pins.
    print_leg=box(24,24,33.5).cut(bores([[0,0]],3.3,-1,36)).val()
    cq.exporters.export(print_leg,str(args.output/'ODR-BASE-LEG-PRINT-NOLOAD.stl'),tolerance=.025,angularTolerance=.08)
    mesh=trimesh.load_mesh(args.output/'ODR-BASE-LEG-PRINT-NOLOAD.stl');assert mesh.is_watertight and mesh.body_count==1
    print_quadrant=parts['ODR-BASE-PLATE-R4'].intersect(box(130,130,20,-1).translate((65,65,0)).val())
    cq.exporters.export(print_quadrant,str(args.output/'ODR-BASE-QUADRANT-PRINT-NOLOAD.stl'),tolerance=.025,angularTolerance=.08)
    mesh=trimesh.load_mesh(args.output/'ODR-BASE-QUADRANT-PRINT-NOLOAD.stl');assert mesh.is_watertight and mesh.body_count==1
    full,free,tools=hardware(args.desk_thickness_mm,interface['RH25_fixed_holes_xy_mm'])
    collision_results={}
    def probe(name,a,b,expect_zero=True):
        result=collision(a,b);collision_results[name]=result
        if result['events']:print(name,result,flush=True)
        if expect_zero:assert result['pair_intersection_sum_mm3']<1e-4,name
    for name,shape in assembled.items():probe(name+'_to_vendor',shape,vendor)
    for (na,a),(nb,b) in itertools.combinations(assembled.items(),2):probe(na+'_to_'+nb,a,b)
    for name,shape in free.items():
        probe(name+'_to_vendor',shape,vendor)
        for oname,obstacle in assembled.items():probe(name+'_to_'+oname,shape,obstacle)
    # Full shafts intentionally enter specified tap holes; they still may not
    # hit vendor or any other screw. Nuts use a smooth major-diameter hole.
    for name,shape in full.items():probe(name+'_full_to_vendor',shape,vendor)
    for (na,a),(nb,b) in itertools.combinations(full.items(),2):probe(na+'_to_'+nb,a,b)
    for name,shape in tools.items():
        probe(name+'_to_vendor',shape,vendor)
        for oname,obstacle in assembled.items():probe(name+'_to_'+oname,shape,obstacle)
        for oname,obstacle in full.items():probe(name+'_to_'+oname,shape,obstacle)
    # Current rejected solid plate reproduces the original 12mm-layout flaw.
    probe('REJECTED_solid_12mm_base_to_vendor',box(220,220,12).val(),vendor,False)
    assert collision_results['REJECTED_solid_12mm_base_to_vendor']['pair_intersection_sum_mm3']>100
    # Provisional connector/cable service envelope below the rear end. It is
    # NOT claimed to represent any selected connector. Does not enter vendor.
    service=box(30,30,100,-98).val()
    for oname,obstacle in assembled.items():probe('service_30square_to_'+oname,service,obstacle)
    probe('service_30square_to_vendor',service,vendor)
    loads=calculate_loads(p,parts)
    private=cq.Assembly(name='LOCAL-ONLY-RH25-BASE')
    public=cq.Assembly(name='ODR-BASE-ORIGINAL-ONLY')
    for name,shape in assembled.items():public.add(shape,name=name);private.add(shape,name=name)
    private.add(vendor,name='VENDOR_LOCAL_ONLY_RH25_B')
    for name,shape in full.items():private.add(shape,name=name)
    public.save(str(args.output/'ODR-BASE-ORIGINAL-ASSEMBLY.step'))
    private.save(str(args.private_assembly))
    assert len(cq.importers.importStep(str(args.output/'ODR-BASE-ORIGINAL-ASSEMBLY.step')).val().Solids())==8
    # Local-only assembly contains explicitly modeled threaded engagement;
    # it is a visual packaging document, not a free-intersection aggregate.
    e={'revision':REVISION,'status':'nominal anchored base candidate; NOT manufacturing or load release','units':'mm,N,Nm,MPa,kg',
      'parameters_sha256':PARAM_SHA,'vendor_step_filename':args.rh25_step.name,'vendor_step_sha256':sha(args.rh25_step),
      'vendor_solid_count':len(vendor.Solids()),'source_interface_sha256':sha(args.interfaces),
      'mount_evidence_sha256':sha(ROOT/'engineering/generated/mount-study/evidence.json'),
      'sources_accessed':'2026-09-27','sources':SOURCES,'parts':checks,'loads':loads,
      'fixed_holes_xy_mm':interface['RH25_fixed_holes_xy_mm'],'original_head_relief_xy_mm':interface['RH25_original_screw_head_relief_xy_mm'],
      'leg_centres_xy_mm':LEG_XY.tolist(),'anchor_centres_xy_mm':ANCHOR_XY.tolist(),
      'world_z_mm':{'desk_top':0,'plate_top':16,'rear_housing_bottom':2,'leg_top_rear_ring_bottom':49.5,'rear_ring_top_fixed_rear':59.5,'fixed_front':89.7,'front_ring_top':93.7,'J1_output':105.2},
      'desk_example_mm':30,'anchor_stack_mm':{'plate':16,'desk':30,'back':8,'two_washers':3.2,'nut':6.5,'bolt_underhead':70,'protrusion_below_nut':6.3,'min_thread':28},
      'geometric_clearances_mm':{'rear_body_to_plate_centre_hole_radial':55-47.4,'rear_body_to_leg_nearest_corner':np.sqrt(2)*(LEG_X-12)-47.4,'leg_screw_end_gap':7.5,'M6_bottom_head_recess':1,'M6_bottom_head_to_cbores_radial':5.5-5.11},
      'collision_method':'Every solid pair after AABB; 1e-4 mm3 detection threshold, not guaranteed real-world clearance.',
      'collision_checks':collision_results,'unqualified_service_envelope_mm':[30,30,100],'vendor_CAD_published':False,
      'print_only_samples':{'ODR-BASE-LEG-PRINT-NOLOAD.stl':{'hole_mm':6.6,'sha256':sha(args.output/'ODR-BASE-LEG-PRINT-NOLOAD.stl'),'watertight_single_body':True},
                            'ODR-BASE-QUADRANT-PRINT-NOLOAD.stl':{'bbox_xy_mm':[130,130],'quantity':4,'rotate_increments_deg':90,'assembly':'loose unjoined panels, NO LOAD','sha256':sha(args.output/'ODR-BASE-QUADRANT-PRINT-NOLOAD.stl'),'watertight_single_body':True}},
      'thread_CAD':'Smooth pilot drills in own parts. Free shanks checked; intentional thread engagement not treated as an interference.'}
    pdf=args.output/'ODR-base-structure-study.pdf';make_pdf(pdf,args.font,parts,assembled,e);e['pdf_sha256']=sha(pdf)
    with (args.output/'hole-coordinates.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['group','number','x_mm','y_mm','feature'])
        for group,xy,feature in [('anchor',ANCHOR_XY,'D9 through base/back; table bore needs confirmation'),('leg',LEG_XY,'D6.6 through + D11 deep7 bottom counterbore'),('fixed',e['fixed_holes_xy_mm'],'rear M4 tap / front D4.5'),('relief',e['original_head_relief_xy_mm'],'front D7.6 OEM screw clearance')]:
            for i,(x,y) in enumerate(xy):writer.writerow([group,i+1,f'{x:.8f}',f'{y:.8f}',feature])
    e['generator_sha256']=sha(Path(__file__))
    with (args.output/'base-bom.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['part','qty','role','status'])
        for name in parts:writer.writerow([name,4 if name=='ODR-BASE-LEG-R4' else 1,'original machined candidate','NOT manufacturing release'])
        for part,qty,role in [('SSCF-M6-20-12.9',4,'leg top'),('SSC-M6-25-12.9',4,'leg bottom'),('SSC-M4-45-12.9',8,'RH25 fixed flange'),('SSC-M8-70-12.9',4,'desk anchors ONLY30mm desk example'),('RS PRO 2867149',4,'M8 Class12 nuts'),('Wurth 515002018',8,'M8 washers')]:
            writer.writerow([part,qty,role,'catalogue candidate; procurement/preload not qualified'])
    (args.output/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'parts':len(parts),'assembled_original_solids':len(assembled),'collision_checks':len(collision_results),
       'loads':loads,'pdf_pages':4,'private_assembly_written':True,'status':'CAD/math checks passed; visual PDF inspection still required'},indent=2),flush=True)


if __name__=='__main__':main()
