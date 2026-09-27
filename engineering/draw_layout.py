# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Orthographic assembly review sheets, explicitly not manufacturing drawings.

Uses the layout manifest's actual zero-pose STL meshes. Projected silhouette
and sharp edges are shown without hidden-line removal. Mesh edges are only
visual references; all reported dimensions come from the JSON parameters or
verified interface data. DXF modelspace views use millimetres at 1:1.
"""
import argparse
import hashlib
import json
from pathlib import Path

import ezdxf
import numpy as np
import trimesh
from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
NAVY = '#11364C'
TEAL = '#007D86'
GRAY = '#75848B'
LIGHT = '#D9E2E7'
AMBER = '#BC781F'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def projected_edges(mesh, basis):
    """Return actual projected mesh feature edges, no perspective scaling."""
    normal = np.cross(basis[0], basis[1])
    adjacent = mesh.face_adjacency
    normals = mesh.face_normals
    dot_pair = np.einsum('ij,ij->i', normals[adjacent[:, 0]], normals[adjacent[:, 1]])
    view_dot = normals @ normal
    silhouette = view_dot[adjacent[:, 0]] * view_dot[adjacent[:, 1]] < -1e-12
    sharp = dot_pair < np.cos(np.deg2rad(25))
    edges = mesh.face_adjacency_edges[silhouette | sharp]
    counts = np.bincount(mesh.edges_unique_inverse, minlength=len(mesh.edges_unique))
    edges = np.vstack([edges, mesh.edges_unique[counts == 1]])
    points = mesh.vertices[edges] @ basis.T
    points = points[np.linalg.norm(points[:, 1] - points[:, 0], axis=1) > 1e-6]
    # Remove coincident front/back projected edges, preserving true coordinates.
    seen, result = set(), []
    for line in points:
        ends = sorted(tuple(v) for v in np.round(line, 6))
        key = tuple(ends[0] + ends[1])
        if key not in seen:
            result.append(line)
            seen.add(key)
    return np.asarray(result)


class Sheet:
    def __init__(self, pdf, font):
        self.c = pdf
        self.font = font

    def text(self, x, y, value, size=9, color=NAVY, align='left'):
        self.c.setFont(self.font, size)
        self.c.setFillColor(HexColor(color))
        function = {'left': self.c.drawString, 'center': self.c.drawCentredString, 'right': self.c.drawRightString}[align]
        function(x * mm, y * mm, str(value))

    def line(self, a, b, color=GRAY, width=.35, dash=None):
        self.c.setStrokeColor(HexColor(color))
        self.c.setLineWidth(width)
        self.c.setDash(dash or [])
        self.c.line(a[0] * mm, a[1] * mm, b[0] * mm, b[1] * mm)
        self.c.setDash([])

    def circle(self, xy, radius, color=TEAL, width=.5):
        self.c.setStrokeColor(HexColor(color))
        self.c.setLineWidth(width)
        self.c.circle(xy[0] * mm, xy[1] * mm, radius * mm, stroke=1, fill=0)

    def arrow(self, start, end, color=TEAL, width=.6):
        a, b = np.asarray(start), np.asarray(end)
        self.line(a, b, color, width)
        d = b - a
        d /= np.linalg.norm(d)
        perpendicular = np.array([-d[1], d[0]])
        for sign in [-1, 1]:
            self.line(b, b - 1.8 * d + sign * .65 * perpendicular, color, width)

    def header(self, title, subtitle, revision):
        self.text(15, 282, 'ODRADEK / ' + title, 20)
        self.text(15, 272, subtitle, 10, TEAL)
        self.text(405, 282, revision, 11, align='right')
        self.line((15, 267), (405, 267), TEAL, .8)

    def footer(self, number, hashes):
        self.line((15, 16), (405, 16), GRAY, .5)
        self.text(15, 10, '单位 mm | 正交布局审查 | 原始边线不消隐 | 不用于孔位加工、制造放行或负载验收', 8)
        self.text(405, 10, f'{number}/2 | A3 横向 | 2026-09-27', 8, align='right')
        self.text(15, 20, f'参数 SHA256 {hashes[0][:16]}…  /  几何清单 SHA256 {hashes[1][:16]}…', 7, GRAY)


def render_view(sheet, parts, basis, origin_paper, scale, shift_world=None):
    shift_world = np.zeros(3) if shift_world is None else np.asarray(shift_world)
    shift_2d = shift_world @ basis.T
    for part in parts:
        color = AMBER if part['category'] in ['finger_light', 'screen', 'trim'] else GRAY
        for edge in projected_edges(part['loaded_mesh'], basis):
            xy = np.asarray(origin_paper) + scale * (edge - shift_2d)
            sheet.line(*xy, color=color, width=.28)


def draw_axes(sheet, p, basis, origin, scale, labels=True):
    normal = np.cross(basis[0], basis[1])
    for joint in p['joints']:
        centre = np.asarray(origin) + scale * (basis @ np.asarray(joint['origin_mm']))
        direction = basis @ np.asarray(joint['axis'])
        sheet.circle(centre, 1.4)
        if np.linalg.norm(direction) > 1e-8:
            sheet.arrow(centre, centre + 7 * direction / np.linalg.norm(direction))
        elif normal @ joint['axis'] > 0:
            sheet.circle(centre, .35)
        else:
            for sign in [-1, 1]:
                sheet.line(centre + [-.7, sign * -.7], centre + [.7, sign * .7], TEAL, .5)
        if labels:
            sheet.text(centre[0] + 9, centre[1] - 1, joint['id'], 8, TEAL)


def dxf_view(space, parts, basis, offset, layer, shift_world=None):
    shift_world = np.zeros(3) if shift_world is None else np.asarray(shift_world)
    count = 0
    for part in parts:
        for line in projected_edges(part['loaded_mesh'], basis):
            xy = line - shift_world @ basis.T + offset
            space.add_line(xy[0], xy[1], dxfattribs={'layer': layer})
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, default=ROOT / 'engineering/parameters/r4-layout.json')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'engineering/generated/layout/manifest.json')
    parser.add_argument('--interfaces', type=Path, default=ROOT / 'docs/engineering/sources/rh-interface-extraction.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'engineering/generated/layout')
    parser.add_argument('--font', type=Path, required=True, help='Chinese-capable TrueType font')
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    manifest = json.loads(args.manifest.read_text())
    interface_source = json.loads(args.interfaces.read_text())
    interfaces = {m['id']: m['unified_joint_interface'] for m in interface_source['models']}
    assert p['revision'] == manifest['revision'], 'Regenerate geometry after a parameter revision.'
    assert manifest['length_unit'] == p['length_unit'] == 'mm'
    parts = []
    for data in manifest['parts']:
        mesh = trimesh.load_mesh(args.manifest.parent / data['mesh'], process=True)
        assert isinstance(mesh, trimesh.Trimesh) and len(mesh.vertices) > 0
        parts.append({**data, 'loaded_mesh': mesh})
    head_parts = [x for x in parts if x['attachment'] == 7 and not x['name'].startswith('J7_')]
    assert head_parts
    h = p['head']
    front = np.array([[1., 0, 0], [0, 0, 1]])
    side = np.array([[0., 1, 0], [0, 0, 1]])
    top = np.array([[1., 0, 0], [0, 1, 0]])
    head_side = np.array([[0., 0, 1], [0, 1, 0]])
    hashes = [digest(args.parameters), digest(args.manifest)]
    args.output.mkdir(parents=True, exist_ok=True)
    pdf_path = args.output / 'ODR-R4-assembly-review.pdf'
    dxf_path = args.output / 'ODR-R4-assembly-review.dxf'
    pdfmetrics.registerFont(TTFont('DrawingCN', str(args.font)))
    pdf = canvas.Canvas(str(pdf_path), pagesize=landscape(A3), pageCompression=1)
    pdf.setTitle('Odradek R4 orthographic assembly layout review - NOT FOR MANUFACTURE')
    pdf.setAuthor('Auromix contributors')
    s = Sheet(pdf, 'DrawingCN')
    s.header('工程装配布局', '零位 / 四片展开 / 实际模型正交投影 / 未完成实体可达及承载验证', p['revision'])
    positions = [(70, 35), (205, 35), (339, 211)]
    for basis, pos in zip([front, side, top], positions):
        render_view(s, parts, basis, pos, .25)
    draw_axes(s, p, front, positions[0], .25)
    draw_axes(s, p, side, positions[1], .25)
    s.text(24, 260, '正视 1:4 | 从 -Y 看向 +Y', 9, TEAL)
    s.text(158, 260, '侧视 1:4 | 从 +X 看向 -X', 9, TEAL)
    s.text(291, 260, '俯视 1:4 | 从 +Z 看向 -Z', 9, TEAL)
    for basis, pos in zip([front, side], positions[:2]):
        tcp = np.asarray(pos) + .25 * (basis @ h['tcp_home_mm'])
        s.line(tcp + [-2, 0], tcp + [2, 0], AMBER, .8)
        s.line(tcp + [0, -2], tcp + [0, 2], AMBER, .8)
        s.text(tcp[0] + 4, tcp[1] - 1, 'TCP', 8, AMBER)
    # True z span, deliberately distinct from the shoulder-to-TCP 3-D distance.
    z0 = p['joints'][1]['origin_mm'][2]
    z1 = h['tcp_home_mm'][2]
    dim_x = 130
    for z in [z0, z1]:
        s.line((119, 35 + .25 * z), (dim_x + 2, 35 + .25 * z), GRAY, .3)
    s.arrow((dim_x, 35 + .25 * z0), (dim_x, 35 + .25 * z1), GRAY, .4)
    s.arrow((dim_x, 35 + .25 * z1), (dim_x, 35 + .25 * z0), GRAY, .4)
    s.text(133, 163, f'ΔZ {z1 - z0:.0f}', 8)
    s.text(133, 158, '非工作半径', 7, GRAY)
    s.text(285, 158, '轴线原点与正转方向 / 零位基座坐标', 10, TEAL)
    columns = [285, 299, 323, 347, 377]
    for x, label in zip(columns, ['轴', 'X', 'Y', 'Z', '方向']):
        s.text(x, 150, label, 8)
    axis_names = {(0, 0, 1): '+Z', (0, 1, 0): '+Y', (0, -1, 0): '-Y'}
    for i, j in enumerate(p['joints']):
        y = 143 - i * 6
        s.line((285, y - 1.5), (402, y - 1.5), LIGHT, .3)
        row = [j['id'], *[f'{v:g}' for v in j['origin_mm']], axis_names.get(tuple(j['axis']), str(j['axis']))]
        for x, value in zip(columns, row):
            s.text(x, y, value, 8)
    s.text(285, 91, '原点为输出安装接触面与转轴交点。', 8)
    s.text(285, 85, '箭头示正轴；正角按右手规则；点向前、叉向后。', 8)
    s.text(285, 79, '本表定义轴姿态，不定义安装孔阵或电气零位。', 8)
    for y, name, key in [(68, '末端安装面', 'mount_origin_mm'), (62, '前脸中心', 'face_center_mm'), (56, '名义 TCP', 'tcp_home_mm')]:
        s.text(285, y, f'{name}: {h[key]}', 8)
    reach = np.linalg.norm(np.asarray(h['tcp_home_mm']) - p['joints'][1]['origin_mm'])
    s.text(285, 45, f'肩轴点至 TCP 直线距离 {reach:.2f} mm', 8)
    s.text(285, 39, '当前零位几何距离，非已验证的可达工作半径。', 8, GRAY)
    s.footer(1, hashes)
    pdf.showPage()

    s.header('末端与接口布局', '四独立灯片 / 上长下短 / 下根向前错层 / 仅审查装配空间', p['revision'])
    head_origin = np.asarray(h['face_center_mm'])
    front_pos, side_pos = (109, 176), (306, 176)
    render_view(s, head_parts, top, front_pos, .5, head_origin)
    render_view(s, head_parts, head_side, side_pos, .5, head_origin)
    s.text(18, 259, '末端正视 1:2 | 从 +Z 看向 -Z', 10, TEAL)
    s.text(232, 259, '末端侧视 1:2 | 从 -X 看向 +X', 10, TEAL)
    for f in h['fingers']:
        phi = np.deg2rad(f['phi_deg'])
        root = np.array([f['root_radius_mm'] * np.cos(phi), f['root_radius_mm'] * np.sin(phi), f['root_z_mm']])
        label = np.array(front_pos) + .5 * (root[:2] + (f['length_mm'] + 13) * np.array([np.cos(phi), np.sin(phi)]))
        s.text(*label, f['id'], 9, TEAL, 'center')
        for basis, pos in [(top, front_pos), (head_side, side_pos)]:
            s.circle(np.asarray(pos) + .5 * (basis @ root), 1.1)
    for pos in [front_pos, side_pos]:
        s.line(np.asarray(pos) + [-7, 0], np.asarray(pos) + [7, 0], TEAL, .35, [2, 2])
        s.line(np.asarray(pos) + [0, -7], np.asarray(pos) + [0, 7], TEAL, .35, [2, 2])
    upper_z = h['fingers'][0]['root_z_mm']
    lower_z = h['fingers'][2]['root_z_mm']
    # Axial root separation shown at a clear Y location, with true scale.
    dim_y = 249
    ux, lx = side_pos[0] + .5 * upper_z, side_pos[0] + .5 * lower_z
    for x in [ux, lx]:
        s.line((x, 235), (x, dim_y + 2), GRAY, .35)
    s.arrow((ux, dim_y), (lx, dim_y), TEAL, .6)
    s.arrow((lx, dim_y), (ux, dim_y), TEAL, .6)
    s.text((ux + lx) / 2, dim_y + 3, f'根轴向错层 {lower_z - upper_z:g}', 8, TEAL, 'center')
    mount_delta = np.asarray(h['mount_origin_mm']) - head_origin
    mx = side_pos[0] + .5 * mount_delta[2]
    s.line((mx, 107), (side_pos[0], 107), GRAY, .4)
    for x in [mx, side_pos[0]]:
        s.line((x, 104), (x, 117), GRAY, .3)
    s.text((mx + side_pos[0]) / 2, 102, f'安装面至前脸 {abs(mount_delta[2]):g}', 8, align='center')
    s.text(15, 94, '关节外廓与输出界面参考 / 不包含客户接插件和线束弯曲空间', 9, TEAL)
    column2 = [15, 48, 75, 102, 136, 181]
    for x, label in zip(column2, ['型号', '本体 Ø', '轴长', '输出外圆', '中央凸台 Ø×高', '过孔 Ø']):
        s.text(x, 87, label, 7.5)
    model_rows = {j['model']: j for j in reversed(p['joints'])}
    for i, model in enumerate(['RH14-N', 'RH17-B', 'RH20-B', 'RH25-B']):
        j, interface = model_rows[model], interfaces[model]
        boss = interface['central_clearance_boss']
        vals = [model, f'{j["diameter_mm"]:g}', f'{j["length_mm"]:g}', f'{interface["outer_output_pilot"]["diameter_mm"]:g} h6',
                f'{boss["diameter_mm"]:g} × {boss["height_above_output_contact_mm"]:g}', f'{j["bore_mm"]:g}']
        y = 80 - i * 6
        s.line((15, y - 2), (203, y - 2), LIGHT, .3)
        for x, value in zip(column2, vals):
            s.text(x, y, value, 8)
    s.text(15, 53, '外圆定位配合、固定侧接触面、孔深与紧固件须单独设计确认。', 7.5)
    s.text(15, 47, '孔阵使用原厂提取坐标及无载试装样片，不从本正交线框量取。', 7.5)
    s.text(222, 94, '末端当前尺寸与待定空间', 9, TEAL)
    dimensions = [
        f'根半径 {h["fingers"][0]["root_radius_mm"]:g}；上片长度 {h["fingers"][0]["length_mm"]:g}；下片长度 {h["fingers"][2]["length_mm"]:g}。',
        f'中央核心 Ø{h["central_core_diameter_mm"]:g}，显示区 Ø{h["screen_diameter_mm"]:g}；相机安装区域另向上下伸出。',
        f'相机基线 {h["camera_baseline_mm"]:g}；上下外倾各 {h["camera_outward_pitch_deg"]:g}°，光学视场尚未验证。',
        f'驱动空间预算 Ø{h["drive_envelope_diameter_mm"]:g} × {h["drive_envelope_depth_mm"]:g}；不表示所有内部件已装配。',
        '电机、减速/同步带、轴承、硬限位和可拆接插件以最终装配结果为准。',
        '四片展开姿态不证明独立闭合无碰撞，也不证明能夹持 2 kg。']
    for i, text in enumerate(dimensions):
        s.text(222, 86 - i * 6, text, 8)
    s.text(15, 34, '图面状态：模型边线来自清单所列 STL；圆弧离散化，边线不消隐。图示相交须结合实体碰撞分析解释。', 8, TEAL)
    s.text(15, 28, '未定义：承力支架截面、公差链、表面处理、紧固预紧、线束路径和热设计。禁止据此下发金属加工或装机负载测试。', 8)
    s.footer(2, hashes)
    pdf.save()

    dxf = ezdxf.new('R2010')
    dxf.units = ezdxf.units.MM
    dxf.header['$MEASUREMENT'] = 1
    space = dxf.modelspace()
    view_settings = [('FRONT', parts, front, np.array([0., 0.]), None),
                     ('SIDE', parts, side, np.array([600., 0.]), None),
                     ('TOP', parts, top, np.array([1200., 450.]), None),
                     ('HEAD_FRONT', head_parts, top, np.array([0., -450.]), head_origin),
                     ('HEAD_SIDE', head_parts, head_side, np.array([600., -450.]), head_origin)]
    line_count = 0
    for name, selected, basis, offset2, shift in view_settings:
        dxf.layers.new(name, dxfattribs={'color': 8})
        line_count += dxf_view(space, selected, basis, offset2, name, shift)
        space.add_text(name + ' - ORTHOGRAPHIC / MILLIMETRES / NO HIDDEN-LINE REMOVAL', dxfattribs={'height': 9}).set_placement(offset2 + [-180, -195])
    dxf.layers.new('AXIS_CENTRES', dxfattribs={'color': 4})
    for basis, offset2 in [(front, np.array([0., 0.])), (side, np.array([600., 0.]))]:
        for j in p['joints']:
            xy = basis @ np.asarray(j['origin_mm']) + offset2
            space.add_circle(xy, 3, dxfattribs={'layer': 'AXIS_CENTRES'})
            space.add_text(j['id'], dxfattribs={'height': 9, 'layer': 'AXIS_CENTRES'}).set_placement(xy + [10, 2])
    texts = [f'ODRADEK {p["revision"]} - ASSEMBLY REVIEW ONLY - NOT FOR MANUFACTURE',
             'Modelspace 1:1 mm. View origins are deliberately separated; not a drilling template.',
             'Joint origins denote output contact plane centres. No electrical zero or hole coordinates implied.',
             f'Parameters SHA256 {hashes[0]}', f'Manifest SHA256 {hashes[1]}']
    for i, value in enumerate(texts):
        space.add_text(value, dxfattribs={'height': 11 if i == 0 else 8}).set_placement((-180, 960 - i * 18))
    for i, j in enumerate(p['joints']):
        space.add_text(f'{j["id"]}  XYZ={j["origin_mm"]} mm  axis={j["axis"]}  {j["model"]}', dxfattribs={'height': 9}).set_placement((1020, 210 - i * 18))
    space.add_text(f'Head root axial separation: {lower_z-upper_z:g} mm; upper L={h["fingers"][0]["length_mm"]:g}, lower L={h["fingers"][2]["length_mm"]:g} mm.', dxfattribs={'height': 9}).set_placement((-180, -660))
    dxf.saveas(dxf_path)
    reread = ezdxf.readfile(dxf_path)
    assert not reread.audit().errors and reread.units == ezdxf.units.MM
    assert len(reread.modelspace().query('LINE')) == line_count
    assert len(reread.modelspace().query('CIRCLE[layer=="AXIS_CENTRES"]')) == 14
    reader = PdfReader(pdf_path)
    assert len(reader.pages) == 2
    for page in reader.pages:
        assert np.allclose([float(page.mediabox.width), float(page.mediabox.height)], landscape(A3), atol=.01)
        assert 'ODRADEK' in page.extract_text()
    # Fail rather than silently publish while another process changes the inputs.
    assert hashes == [digest(args.parameters), digest(args.manifest)], 'Inputs changed during generation; rerun.'
    print(json.dumps({'revision': p['revision'], 'parts_projected': len(parts), 'head_parts_projected': len(head_parts),
                      'dxf_line_count': line_count, 'dxf_audit': 'pass', 'dxf_units': 'mm',
                      'pdf_pages': 2, 'pdf_page_size': 'A3 landscape', 'scales': ['1:4 assembly', '1:2 head'],
                      'pdf_sha256': digest(pdf_path), 'dxf_sha256': digest(dxf_path),
                      'remaining_check': 'Render both PDF pages and inspect visually before delivery.'}, indent=2))


if __name__ == '__main__':
    main()
