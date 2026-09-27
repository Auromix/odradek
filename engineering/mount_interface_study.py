# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Original interface candidates checked against local-only vendor solids.

No vendor BREP, STEP, mesh, assembly or drawing is exported. The output contains
our own three adapter solids, coordinate tables and dimension-based schematics.
Thread-free bores are modeled: tapped-hole CAD uses the nominated pilot drill;
the M4 thread specification remains a drawing requirement, not a modeled helix.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import cadquery as cq
import ezdxf
import numpy as np
import trimesh
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Plane
from OCP.gp import gp_Trsf
from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from draw_layout import Sheet, NAVY, TEAL, GRAY, LIGHT, AMBER

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ring(ro, ri, z0, thickness):
    return cq.Workplane('XY').workplane(offset=z0).circle(ro).circle(ri).extrude(thickness)


def bores(points, radius, z0, height):
    return cq.Workplane('XY').workplane(offset=z0).pushPoints(points).circle(radius).extrude(height)


def bounding_overlap(a, b):
    aa, bb = a.BoundingBox(), b.BoundingBox()
    return all(min(getattr(aa, k + 'max'), getattr(bb, k + 'max')) -
               max(getattr(aa, k + 'min'), getattr(bb, k + 'min')) > 1e-7 for k in 'xyz')


def collision(candidate, vendor):
    """OCCT Compound common can miss intersections: always test solid pairs."""
    events = []
    for ci, a in enumerate(candidate.Solids()):
        for vi, b in enumerate(vendor.Solids()):
            if bounding_overlap(a, b):
                volume = a.intersect(b).Volume()
                if volume > 1e-4:
                    events.append({'candidate_solid': ci, 'vendor_solid': vi, 'intersection_mm3': volume})
    return {'pair_intersection_sum_mm3': sum(x['intersection_mm3'] for x in events),
            'events': events, 'method': 'solid-by-solid common; pair sum is not a union volume'}


def load_vendor(path, measured):
    assert sha(path) == measured['input_sha256'], 'Vendor file differs from independently extracted source.'
    transform = np.linalg.inv(measured['unified_joint_interface']['T_world_from_joint_mm'])
    trsf = gp_Trsf()
    trsf.SetValues(*transform[:3].ravel().tolist())
    shape = cq.importers.importStep(str(path)).val().moved(cq.Location(trsf))
    assert shape.isValid()
    return shape


def circular_features(shape):
    cylinders, planes = [], []
    for i, face in enumerate(shape.Faces()):
        surf = BRepAdaptor_Surface(face.wrapped)
        if surf.GetType() == GeomAbs_Cylinder:
            c = surf.Cylinder()
            if abs(abs(c.Axis().Direction().Z()) - 1) > 1e-7:
                continue
            point = c.Location()
            bb = face.BoundingBox()
            cylinders.append({'face_index': i, 'radius_mm': c.Radius(), 'xy_mm': [point.X(), point.Y()],
                              'z_mm': [bb.zmin, bb.zmax]})
        elif surf.GetType() == GeomAbs_Plane:
            pl = surf.Plane()
            if abs(abs(pl.Axis().Direction().Z()) - 1) > 1e-7 or face.Area() < 50:
                continue
            circles = []
            for edge in face.Edges():
                curve = BRepAdaptor_Curve(edge.wrapped)
                if curve.GetType() == GeomAbs_Circle:
                    c = curve.Circle()
                    circles.append({'radius_mm': c.Radius(), 'xy_mm': [c.Location().X(), c.Location().Y()]})
            planes.append({'face_index': i, 'z_mm': pl.Location().Z(), 'area_mm2': face.Area(),
                           'wire_count': len(face.Wires()), 'boundary_circle_features': circles})
    return cylinders, planes


def contact(planes, z):
    selected = [x for x in planes if abs(x['z_mm'] - z) < 1e-5]
    assert len(selected) == 1
    result = dict(selected[0])
    radii = sorted(set(round(c['radius_mm'], 5) for c in result['boundary_circle_features']
                       if np.linalg.norm(c['xy_mm']) < 1e-5))
    result['coaxial_boundary_radii_mm'] = radii
    return result


def write_csv(path, points, role):
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['number', 'x_mm', 'y_mm', 'role'])
        for i, p in enumerate(points):
            writer.writerow([i + 1, *p, role])


def export_part(out, name, shape, holes):
    assert shape.isValid() and len(shape.Solids()) == 1
    step, stl, dxf_path = [out / f'{name}.{ext}' for ext in ['step', 'stl', 'dxf']]
    cq.exporters.export(shape, str(step))
    cq.exporters.export(shape, str(stl), tolerance=.025, angularTolerance=.07)
    reread = cq.importers.importStep(str(step)).val()
    assert reread.isValid() and len(reread.Solids()) == 1
    assert abs(reread.Volume() - shape.Volume()) < 1e-4
    mesh = trimesh.load_mesh(stl, process=True)
    assert mesh.is_watertight and mesh.body_count == 1
    drawing = ezdxf.new('R2010')
    drawing.units = ezdxf.units.MM
    space = drawing.modelspace()
    for name2, radius, points in holes:
        drawing.layers.new(name2)
        for point in points:
            space.add_circle(point, radius, dxfattribs={'layer': name2})
    space.add_text(name + ' / NOMINAL INTERFACE STUDY / NOT FOR MANUFACTURE', dxfattribs={'height': 3}).set_placement((-80, -90))
    space.add_text('Tapped holes are pilot-drill circles; see PDF and guide for thread and axial features.', dxfattribs={'height': 2.3}).set_placement((-80, -96))
    drawing.saveas(dxf_path)
    d = ezdxf.readfile(dxf_path)
    assert not d.audit().errors and d.units == ezdxf.units.MM
    return {'volume_mm3': shape.Volume(), 'estimated_6061_mass_kg_at_2700kg_m3': shape.Volume() * 2.7e-6,
            'step_valid': True, 'single_solid': True, 'stl_watertight': True,
            'dxf_circle_count': len(d.modelspace().query('CIRCLE')),
            'sha256': {p.name: sha(p) for p in [step, stl, dxf_path]}}


def rect(s, x, y, w, h, fill=LIGHT, border=GRAY):
    s.c.setFillColor(HexColor(fill)); s.c.setStrokeColor(HexColor(border)); s.c.setLineWidth(.45)
    s.c.rect(x * mm, y * mm, w * mm, h * mm, fill=1, stroke=1)


def footer(s, page):
    s.line((15, 16), (405, 16), GRAY, .5)
    s.text(15, 10, '单位 mm | 原创安装候选 / 原厂 CAD 仅本地核验 | 禁止制造放行或承载验收', 8)
    s.text(405, 10, f'{page}/3 | A3 横向 | R4-MOUNT-01', 8, align='right')


def make_pdf(path, font, evidence, p25, p14, relief, pedestal):
    pdfmetrics.registerFont(TTFont('MountCN', str(font)))
    pdf = canvas.Canvas(str(path), pagesize=landscape(A3), pageCompression=1)
    pdf.setTitle('Odradek mount interface candidates - NOT FOR MANUFACTURE')
    pdf.setAuthor('Auromix contributors')
    s = Sheet(pdf, 'MountCN')
    s.header('J1 固定侧安装候选', '基准 A：原厂固定后接触面 z=-45.7；轴向 +Z 指向输出；孔位保持 STEP 装配相位', 'R4-MOUNT-01')
    c = np.array([103., 179.])
    for r in [75, 47.7, 51, 65]:
        s.circle(c, r, TEAL if r in [75, 47.7] else LIGHT, .65 if r in [75, 47.7] else .35)
    for k, point in enumerate(p25):
        xy = c + point
        s.circle(xy, 1.65, TEAL)
        s.text(xy[0] + 3, xy[1] + 1, str(k + 1), 7)
    for point in pedestal:
        s.circle(c + point, 3.3, AMBER)
    s.text(20, 259, '后环正视 1:1 / ODR-J1-REAR-R4', 10, TEAL)
    s.text(20, 96, 'Ø150 / 中央 Ø95.4 避让 / 厚10 / 8×M4×0.7 通孔螺纹', 9)
    s.text(20, 90, '外侧 4×Ø6.6 / PCD130：连接支架；支架与桌面紧固另行设计。', 8)
    s.text(20, 84, '6061-T6 候选；图中 M4 以Ø3.3底孔表示，不是已建模的螺纹。', 8)
    # Dimension-derived axial section, not a vendor internal section.
    ox, oy, scale = 305., 243., 1.1
    def rpart(x0, z0, width, depth, fill=LIGHT, border=GRAY):
        rect(s, ox + scale * x0, oy + scale * z0, scale * width, scale * depth, fill, border)
    rpart(-47.4, -103.2, 94.8, 57.5)
    rpart(-55, -45.7, 110, 30.2)
    rpart(-42.5, -15.5, 85, 15.5)
    for sign in [-1, 1]:
        lo, hi = (47.7, 75) if sign > 0 else (-75, -47.7)
        rpart(lo, -55.7, hi - lo, 10, '#D2E9EA', TEAL)
        lo, hi = (45, 58) if sign > 0 else (-58, -45)
        rpart(lo, -15.5, hi - lo, 4, '#F7E1BF', AMBER)
    s.text(220, 259, '轴向包络剖示 / 约1.1:1 / 内部结构未复刻', 10, TEAL)
    for z, label in [(0, '输出接触面 z=0'), (-15.5, '固定前面 -15.5'), (-45.7, '固定后面 -45.7'), (-55.7, '后环底 -55.7'), (-103.2, '后端最低 -103.2')]:
        y = oy + scale * z
        s.line((ox + 60, y), (ox + 84, y), GRAY, .3)
        s.text(ox + 85, y - 1, label, 7)
    s.text(225, 118, '后壳必须穿过安装环；原厂后端还低于后环47.5。', 8)
    s.text(225, 112, '接头/线束弯曲及维护空间另留；不能把环直接平贴桌面。', 8)
    s.text(225, 100, '前压环 ODR-J1-FRONT-R4：Ø116 / Ø90 / 厚4', 9, TEAL)
    s.text(225, 94, '8×Ø4.5通孔 + 4×Ø7.6原装螺钉头让位孔。', 8)
    s.text(225, 88, 'M4×45候选从 +Z 侧向 -Z 装入：4+30.2+10=44.2。', 8)
    s.text(225, 82, '自制后环螺纹贯通；名义端部伸出0.8，不借用原厂螺纹。', 8)
    s.text(20, 70, '真实孔位 / 固定侧PCD102（非均布）', 9, TEAL)
    for i, point in enumerate(p25):
        col, row = i // 4, i % 4
        s.text(20 + col * 99, 63 - row * 7, f'{i+1}: X {point[0]:+.4f} / Y {point[1]:+.4f}', 8)
    s.text(225, 69, '接触圈：后侧 r47.4～54.7；前侧 r48.0～54.2。', 8)
    s.text(225, 62, 'Ø110外壳和Ø94.8后壳并不等于各接触平面的可用外径。', 8)
    s.text(225, 55, '原厂4个装配孔/螺钉保留，不拆用，也不改作固定孔。', 8)
    s.text(225, 48, 'M4夹紧力、摩擦传矩、薄边螺纹与底座刚度未验算放行。', 8)
    s.text(20, 28, '几何候选已逐实体排查静态交叠；配合、平面度、螺纹工艺和预紧值仍需制造设计与实物核验。', 8, TEAL)
    footer(s, 1); pdf.showPage()

    s.header('J7 输出至可拆头候选', '基准 A：输出接触面 z=0；中央凸台避让；前端接触面 z=10，匹配当前布局的10mm安装距离', 'R4-MOUNT-01')
    c = np.array([97., 184.]); scale = 1.8
    for radius in [35, 26, 25.025, 18.8]:
        s.circle(c, radius * scale, TEAL if radius in [35, 18.8] else GRAY, .5)
    for i, point in enumerate(p14):
        xy = c + scale * point
        s.circle(xy, 1.75 * scale, TEAL)
        s.text(xy[0] + 4, xy[1], str(i + 1), 8)
    for point in [(30, 0), (0, 30), (-30, 0), (0, -30)]:
        s.circle(c + scale * np.array(point), 1.65 * scale, AMBER)
    s.text(20, 258, '正视1.8:1 / ODR-J7-TOOL-R4', 10, TEAL)
    s.text(20, 113, '外径70；主板厚6；前环高4 / 内径52；后裙深2.5。', 9)
    s.text(20, 106, '后裙内径50.05（候选 +0.02/0）；中央通孔37.6。', 8)
    s.text(20, 99, '8×Ø3.5真实输出孔；前端4×M4×0.7通孔螺纹 / PCD60。', 8)
    # Enlarged radial/axial section through a mounting hole (schematic angular cut).
    ox, oy, k = 253., 170., 2.7
    def sec(r, z, w, h, color):
        rect(s, ox + k*r, oy + k*z, k*w, k*h, color)
    sec(18.5, -3, 6.5, 3, LIGHT)
    sec(0, 0, 18.5, 2, LIGHT)
    sec(25.025, -2.5, 9.975, 2.5, '#D2E9EA')
    sec(18.8, 0, 16.2, 6, '#D2E9EA')
    sec(26, 6, 9, 4, '#D2E9EA')
    sec(22-1.75, 0, 3.5, 6, '#FFFFFF')
    sec(22-2.84, 6, 5.68, 3, '#F7E1BF')
    s.text(217, 257, '孔位径向剖示 / 2.7:1 / 非完整内部结构图', 10, TEAL)
    s.text(220, 237, '前环使头部避开 M3 螺钉头；名义净隙1 mm。', 9)
    s.text(220, 230, '头部可拆界面为4个M4螺纹，非已定版快换锁扣。', 8)
    for z, lab in [(-2.5, '后裙 -2.5'), (0, 'A / z=0'), (6, '螺钉座 z=6'), (10, '头部接触 z=10')]:
        y = oy + k*z
        s.line((ox + k*35 + 2, y), (ox + k*35 + 8, y), GRAY, .3)
        s.text(ox + k*35 + 10, y-1, lab, 7)
    s.text(220, 143, '中央Ø37×2凸台与后裙Ø50定位外圆是两个不同特征。', 8)
    s.text(220, 136, '原厂Ø50 h6；本候选裙孔径向名义间隙0.025。', 8)
    s.text(220, 129, '此间隙不是最终重复定位精度；配合和同轴度需单独定版。', 8)
    s.text(220, 115, 'M3长度未选：L = 主板6 + 完整螺纹始端深度d + 啮合e。', 9, TEAL)
    s.text(220, 108, '图纸的9mm沉入与5mm螺纹深度，不足以给出全牙始端公差。', 8)
    s.text(220, 101, '不可把M3深5理解成“从输出面直接啮合5mm”。', 8)
    s.text(20, 84, '真实输出孔位 / PCD44（非均布）', 9, TEAL)
    for i, point in enumerate(p14):
        col, row = i // 4, i % 4
        s.text(20 + col * 99, 76 - row * 7, f'{i+1}: X {point[0]:+.4f} / Y {point[1]:+.4f}', 8)
    s.text(220, 84, '6061-T6候选；M4 CAD显示Ø3.3底孔，后续加工螺纹。', 8)
    s.text(220, 77, '头部侧M4螺钉进入适配件长度暂限制≤8mm，避免后方干涉。', 8)
    s.text(220, 70, '原厂零位螺钉、配合面与电气零位之间的关系仍需装配标定。', 8)
    s.text(220, 63, '无密封、接插件、止转销或预紧认证；不宣称2kg承载达标。', 8)
    s.text(20, 29, '检查对象只含所列关节与本候选；工具可达性还须在整机安装顺序、线束和后续头部实装中重查。', 8, TEAL)
    footer(s, 2); pdf.showPage()

    s.header('剖视与碰撞证据', '参考原厂2D-A0第1页与匹配SHA256的STEP；只输出尺寸示意和数值，不再分发原厂CAD', 'R4-MOUNT-01')
    s.text(18, 257, 'A / 后侧实心板错误', 12, TEAL)
    s.text(215, 257, 'B / 前环漏掉原装螺钉', 12, TEAL)
    # Schematics intentionally use physical radii but are not detail CAD sections.
    rect(s, 58, 174, 94.8, 60, LIGHT)
    rect(s, 30, 214, 150, 10, '#F8D6D4', '#B64035')
    rect(s, 94.1, 214, 22.6, 10, '#FFFFFF')
    s.text(19, 160, f'仅留Ø22.6时，逐实体交叠和 {evidence["collision"]["J1_wrong_solid_plate"]["pair_intersection_sum_mm3"]:,.2f} mm³。', 9)
    s.text(19, 153, '后壳Ø94.8进入板厚范围，必须改为Ø95.4避让。', 9)
    s.text(19, 146, '图示灰色是轴向包络，不复刻内部零件。', 8, GRAY)
    cc = np.array([292., 206.]); ss = .7
    for rad in [58,45]: s.circle(cc, ss*rad, TEAL)
    for point in relief:
        s.circle(cc + ss*point, 3.8*ss, '#B64035', .8)
    for point in p25:s.circle(cc+ss*point,2.25*ss,GRAY)
    s.text(215, 160, f'未避让原4颗螺钉：交叠和 {evidence["collision"]["J1_front_without_reliefs"]["pair_intersection_sum_mm3"]:.2f} mm³。', 9)
    s.text(215, 153, '新增4×Ø7.6后，逐实体交叠为0；原螺钉保持不动。', 9)
    s.text(215, 146, 'Compound一次相交可误返0，本脚本逐一检测实体对。', 8, '#B64035')
    s.line((15, 137), (405, 137), LIGHT, .5)
    s.text(18, 127, 'C / RH14单孔轴向证据：深度从输出接触面起算', 12, TEAL)
    # Depth chart, each independent band is explicitly a measured cylinder.
    ox, oy, k = 39., 110., 3.9
    bands = [(0,3,3.4,'Ø3.4 / 0～3'),(3,9,3.5,'Ø3.5 / 3～9'),(9.6,17.5,2.5,'Ø2.5底孔 / 9.6～17.5')]
    for d0,d1,diam,label in bands:
        rect(s,ox,oy-k*d1,diam*k,k*(d1-d0),'#D2E9EA')
        s.text(ox+22,oy-k*(d0+d1)/2,label,9)
    rect(s,ox,oy-k*9.6,3.5*k,k*.6,'#F7E1BF')
    s.text(215, 113, '原厂2D标注：8× Ø3.4 沉入9；M3深5。', 10)
    s.text(215, 104, 'STEP未建真实螺纹牙型；Ø2.5只是底孔。', 9)
    s.text(215, 95, '完整牙始端、导入牙、末端不完整牙及钻尖余量未被独立定义。', 8.5)
    maximum = max(x['lateral_offset_mm'] for x in evidence['RH14_thread_minor_bore_alignment'])
    s.text(215, 86, f'前孔轴与最近底孔轴存在最大 {maximum:.4f} mm CAD偏移。', 9)
    s.text(215, 77, '不能凭光顺装配图假定同轴；需供应商解释并用实物通规检查。', 8.5)
    s.text(215, 64, '缺失的放行证据：M3有效全牙起点/长度/底孔深度公差；', 9, TEAL)
    s.text(215, 57, '接触面平面度与允许预紧；输出/固定侧载荷与轴承力矩限制。', 9, TEAL)
    s.text(215, 45, '候选实体有效、STEP重读与STL水密通过；几何通过不等于强度通过。', 8)
    s.text(18, 28, '来源文件名、哈希、面索引、实际孔中心、逐实体交叠记录与导出检查均保存在 evidence.json。', 8)
    footer(s, 3); pdf.save()
    assert len(PdfReader(path).pages) == 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rh14-step', type=Path, required=True)
    parser.add_argument('--rh25-step', type=Path, required=True)
    parser.add_argument('--rh14-drawing', type=Path, required=True)
    parser.add_argument('--rh25-drawing', type=Path, required=True)
    parser.add_argument('--interfaces', type=Path, default=ROOT / 'docs/engineering/sources/rh-interface-extraction.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'engineering/generated/mount-study')
    parser.add_argument('--font', type=Path, required=True)
    args = parser.parse_args()
    measured = {m['id']: m for m in json.loads(args.interfaces.read_text())['models']}
    v14 = load_vendor(args.rh14_step, measured['RH14-N'])
    v25 = load_vendor(args.rh25_step, measured['RH25-B'])
    c14, f14 = circular_features(v14)
    c25, f25 = circular_features(v25)
    i14, i25 = [measured[n]['unified_joint_interface'] for n in ['RH14-N','RH25-B']]
    p14 = np.asarray([p['xy_mm'] for p in i14['output_holes']['points']])
    p25 = np.asarray([p['xy_mm'] for p in i25['fixed_through_holes']['points']])
    # Derive original screw-head centres from the measured CAD, not a guessed PCD.
    existing_heads = [c for c in c25 if abs(c['radius_mm']-3.5)<1e-5 and
                      abs(c['z_mm'][0]+15.5)<1e-5 and abs(c['z_mm'][1]+11.7)<1e-5]
    relief = np.unique(np.round([x['xy_mm'] for x in existing_heads],6), axis=0)
    assert len(relief)==4
    pedestal = np.array([[65*np.cos(t),65*np.sin(t)] for t in np.deg2rad([45,135,225,315])])
    rear = ring(75,47.7,-55.7,10).cut(bores(p25.tolist(),1.65,-56,11)).cut(bores(pedestal.tolist(),3.3,-56,11)).val()
    front_unrelieved = ring(58,45,-15.5,4).cut(bores(p25.tolist(),2.25,-16,5)).val()
    front = ring(58,45,-15.5,4).cut(bores(p25.tolist(),2.25,-16,5)).cut(bores(relief.tolist(),3.8,-16,5)).val()
    wrong = ring(75,11.3,-55.7,10).val()
    adapter_unbored = ring(35,25.025,-2.5,2.5).union(ring(35,18.8,0,6)).union(ring(35,26,6,4))
    head_mount = [[30,0],[0,30],[-30,0],[0,-30]]
    adapter = adapter_unbored.cut(bores(p14.tolist(),1.75,-3,14)).cut(bores(head_mount,1.65,-3,14)).val()
    pieces = {'ODR-J1-REAR-R4': rear, 'ODR-J1-FRONT-R4': front, 'ODR-J7-TOOL-R4': adapter}
    probes = [
        ('J1_rear_ring', rear, v25), ('J1_front_with_reliefs', front, v25),
        ('J1_front_without_reliefs', front_unrelieved,v25), ('J1_wrong_solid_plate',wrong,v25),
        ('J1_M4_shaft_45mm',bores(p25.tolist(),2,-56.5,45).val(),v25),
        ('J1_M4_head_envelope_D7_22_H4',bores(p25.tolist(),3.61,-11.5,4).val(),v25),
        ('J1_driver_envelope_D6',bores(p25.tolist(),3,-7.5,35).val(),v25),
        ('J7_adapter',adapter,v14), ('J7_axisymmetric_unbored_envelope',adapter_unbored.val(),v14),
        ('J7_M3_head_envelope_D6_H3_2',bores(p14.tolist(),3,6,3.2).val(),v14),
        ('J7_driver_envelope_D6',bores(p14.tolist(),3,9.2,25).val(),v14),
        ('J7_M3_free_shank_to_recess_bottom_only',bores(p14.tolist(),1.5,-9,15).val(),v14)]
    results = {}
    for name, shape, vendor in probes:
        results[name] = collision(shape,vendor)
        print(name,round(results[name]['pair_intersection_sum_mm3'],6),flush=True)
        if name not in ['J1_front_without_reliefs','J1_wrong_solid_plate']:
            assert results[name]['pair_intersection_sum_mm3'] < 1e-4
    assert results['J1_front_without_reliefs']['pair_intersection_sum_mm3'] > 500
    assert results['J1_wrong_solid_plate']['pair_intersection_sum_mm3'] > 60000
    minor = [c for c in c14 if abs(c['radius_mm']-1.25)<1e-5 and abs(c['z_mm'][0]+17.5)<1e-5 and abs(c['z_mm'][1]+9.6)<1e-5]
    thread_probes=[]
    for point in p14:
        nearest=min(minor,key=lambda c:np.linalg.norm(np.asarray(c['xy_mm'])-point))
        thread_probes.append({'front_hole_xy_mm':point.tolist(), 'nearest_minor_bore':nearest,
                              'lateral_offset_mm':float(np.linalg.norm(np.asarray(nearest['xy_mm'])-point))})
    # A real screw follows the threaded-hole axis, not necessarily the front
    # clearance-hole axis. Verify the free shank at these shifted CAD centres.
    minor_centres=[x['nearest_minor_bore']['xy_mm'] for x in thread_probes]
    shifted_shanks=bores(minor_centres,1.5,-9,15).val()
    for name,obstacle in [('J7_minor_axis_aligned_free_shank_to_vendor',v14),
                          ('J7_minor_axis_aligned_free_shank_to_adapter',adapter)]:
        results[name]=collision(shifted_shanks,obstacle)
        print(name,round(results[name]['pair_intersection_sum_mm3'],6),flush=True)
        assert results[name]['pair_intersection_sum_mm3'] < 1e-4
    args.output.mkdir(parents=True,exist_ok=True)
    export_results={}
    shapes_holes={
        'ODR-J1-REAR-R4':[('OUTLINE',75,[[0,0]]),('BODY_CLEARANCE',47.7,[[0,0]]),('M4_TAP_DRILL',1.65,p25),('PEDESTAL_M6_CLEARANCE',3.3,pedestal)],
        'ODR-J1-FRONT-R4':[('OUTLINE',58,[[0,0]]),('CENTRE_CLEARANCE',45,[[0,0]]),('M4_CLEARANCE',2.25,p25),('OEM_HEAD_RELIEF',3.8,relief)],
        'ODR-J7-TOOL-R4':[('OUTLINE',35,[[0,0]]),('CENTRE_CLEARANCE',18.8,[[0,0]]),('REAR_SKIRT_ID',25.025,[[0,0]]),('FRONT_SPACER_ID',26,[[0,0]]),('M3_CLEARANCE',1.75,p14),('HEAD_M4_TAP_DRILL',1.65,head_mount)]}
    for name,shape in pieces.items():export_results[name]=export_part(args.output,name,shape,shapes_holes[name])
    for name, points, role in [('J1-fixed-hole-coordinates',p25,'vendor through / our rear M4 / front clearance'),
                               ('J1-oem-head-reliefs',relief,'clearance only, not mounting holes'),
                               ('J7-output-hole-coordinates',p14,'vendor M3 screw clearance, length unresolved')]:
        write_csv(args.output/(name+'.csv'),points,role)
    evidence={'revision':'R4-MOUNT-01','status':'nominal interface candidates; no manufacturing or load release',
        'units':'mm, mm3, kg','coordinate_frame':'+Z output, z=0 output contact plane; XY from independent vendor extraction',
        'source_files':{name:{'filename':path.name,'sha256':sha(path)} for name,path in
                         [('RH14_STEP',args.rh14_step),('RH25_STEP',args.rh25_step),('RH14_2D_page1',args.rh14_drawing),('RH25_2D_page1',args.rh25_drawing)]},
        'vendor_CAD_exported':False,'vendor_solid_count':{'RH14-N':len(v14.Solids()),'RH25-B':len(v25.Solids())},
        'contact_faces':{'RH25_fixed_front':contact(f25,-15.5),'RH25_fixed_rear':contact(f25,-45.7),'RH14_output':contact(f14,0)},
        'RH25_fixed_holes_xy_mm':p25.tolist(),'RH25_original_screw_head_relief_xy_mm':relief.tolist(),
        'RH14_output_holes_xy_mm':p14.tolist(),'RH14_thread_minor_bore_alignment':thread_probes,
        'RH14_conservative_nominal_front_shank_radial_clearance_mm':1.7-1.5-max(x['lateral_offset_mm'] for x in thread_probes),
        'collision':results,'parts':export_results,
        'screw_envelopes':{'M4':'Accu SSC-M4-45-12.9: head max7.22, H4, minimum thread20; candidate only',
                          'M3':'Accu SSC-M3-20-12.9 supplies head dimensions5.68x3 only; length20 explicitly NOT selected',
                          'tool':'D6 cylindrical approach envelope, not a selected complete tool/handle'},
        'source_urls':['https://www.myactuator.com/downloads-rhseries',
            'https://www.accu.co.uk/metric-cap-head-screws/16031-SSC-M4-45-12-9',
            'https://www.accu.co.uk/metric-cap-head-screws/16008-SSC-M3-20-12-9'],
        'unresolved':['RH14 complete thread start, lead-in, runout and drill-bottom tolerances',
          'vendor contact flatness/finish and allowed preload', 'adapter stress/deflection and tapped-edge strength',
          'complete pedestal/desk anchorage and connector/bend access', 'assembly sequence with real head and cables']}
    pdf=args.output/'ODR-mount-interface-study.pdf'
    make_pdf(pdf,args.font,evidence,p25,p14,relief,pedestal)
    evidence['pdf_sha256']=sha(pdf)
    (args.output/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'parts':list(pieces),'PDF_pages':3,'max_RH14_bore_axis_offset_mm':max(x['lateral_offset_mm'] for x in thread_probes),
                      'status':'geometry/export checks passed; visual PDF review still required'},indent=2))


if __name__=='__main__':main()
