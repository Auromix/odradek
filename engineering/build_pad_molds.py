# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Generate four-cavity open molds for the R4 upper/lower silicone wedge pads.

This standalone tool reads, but never changes, the shared layout. Outputs are
prototype casting tools and nominal pad references, not a load qualification.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
import ezdxf
import numpy as np
import trimesh
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

MOLD_X, MOLD_Y, MOLD_Z = 30., 42., 12.
PAD_X, PAD_Y, PAD_MEAN = 18., 5., 5.
CENTERS = [-12., -4., 4., 12.]
BLUE = (.05, .20, .31)
GREY = (.42, .46, .50)
TEAL = (.03, .46, .48)
PT_MM = 72 / 25.4


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(v):
    a = np.asarray(v, dtype=float)
    return a / np.linalg.norm(a)


def prism_xz(profile, center_y=0.):
    # CadQuery XZ normal is -Y: move the 5 mm extrusion to center_y.
    return cq.Workplane('XZ').polyline(profile).close().extrude(PAD_Y).translate(
        (0, center_y + PAD_Y/2, 0)).val()


def make_variant(name, fingers):
    q = fingers[0]['pad_target_q_deg']
    assert all(abs(f['pad_target_q_deg'] - q) < 1e-12 for f in fingers)
    assert all(abs(f['thickness_mm'] - 6) < 1e-12 for f in fingers)
    k = 1 / math.tan(math.radians(q))
    t_minus, t_plus = PAD_MEAN - PAD_X/2*k, PAD_MEAN + PAD_X/2*k
    assert min(t_minus, t_plus) > 0 and max(t_minus, t_plus) < MOLD_Z
    profile = [(-9, MOLD_Z-t_minus), (9, MOLD_Z-t_plus), (9, MOLD_Z), (-9, MOLD_Z)]
    blank = cq.Workplane('XY').box(MOLD_X, MOLD_Y, MOLD_Z, centered=(True, True, False)).val()
    cavities = [prism_xz(profile, yc) for yc in CENTERS]
    mold = blank
    for cavity in cavities:
        mold = mold.cut(cavity)
    mold = mold.clean()
    reference = prism_xz([(-9, 0), (9, 0), (9, t_plus), (-9, t_minus)])
    n_floor = normalized([k, 0, 1])
    n_pad = normalized([-k, 0, 1])
    angled_floors = [f for f in mold.Faces() if np.dot(np.asarray(f.normalAt().toTuple()), n_floor) > 1-1e-10]
    screed_faces = [f for f in mold.Faces() if abs(f.Center().z-MOLD_Z) < 1e-9
                    and np.dot(np.asarray(f.normalAt().toTuple()), [0, 0, 1]) > 1-1e-10]
    pad_top = [f for f in reference.Faces() if np.dot(np.asarray(f.normalAt().toTuple()), n_pad) > 1-1e-10]
    assert len(angled_floors) == 4 and len(screed_faces) == 1 and len(pad_top) == 1
    assert len(screed_faces[0].Wires()) == 5
    assert abs(screed_faces[0].Area() - (30*42-4*18*5)) < 1e-7
    cavity_records = []
    for i, (yc, cavity) in enumerate(zip(CENTERS, cavities), 1):
        # Subtract the cavity's Y center before the rotation: avoid a silent mirror in X.
        flipped = cavity.translate((0, -yc, 0)).rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, 12))
        symmetric_difference = flipped.cut(reference).Volume() + reference.cut(flipped).Volume()
        assert abs(cavity.Volume()-450) < 1e-7
        assert symmetric_difference < 1e-7
        floor = min(cavity.Faces(), key=lambda f: np.dot(np.asarray(f.normalAt().toTuple()), n_floor))
        flipped_normal = np.diag([1, -1, -1]) @ np.asarray(floor.normalAt().toTuple())
        assert np.linalg.norm(flipped_normal-n_pad) < 1e-10
        cavity_records.append({'cavity': i, 'center_xy_mm': [0, yc], 'volume_mm3': cavity.Volume(),
            'flip_reference_symmetric_difference_mm3': symmetric_difference,
            'cast_floor_outward_normal': list(floor.normalAt().toTuple()),
            'normal_after_flip': flipped_normal.tolist()})
    minimum_walls = {'outer_x': 6., 'outer_y': 6.5, 'between_cavities': 3.,
                     'bottom': MOLD_Z-max(t_minus, t_plus)}
    # Verify analytic distances directly on the exact cavity solids as well.
    pair_distances = [cavities[i].distance(cavities[i+1]) for i in range(3)]
    assert all(abs(d-3) < 1e-8 for d in pair_distances)
    assert abs(min(v.Center().z for cv in cavities for v in cv.Vertices())-minimum_walls['bottom']) < 1e-8
    assert mold.isValid() and len(mold.Solids()) == 1 and abs(mold.Volume()-13320) < 1e-7
    return {'name': name, 'part': 'ODR-MOLD-'+name+'-R4', 'finger_ids': [f['id'] for f in fingers],
        'target_q_deg': q, 'cot_q': k, 'cavity_profile_xz_mm': profile,
        'pad_thickness_x_minus9_mm': t_minus, 'pad_thickness_x_plus9_mm': t_plus,
        'minimum_wall_mm': minimum_walls, 'minimum_wall_overall_mm': min(minimum_walls.values()),
        'cavities': cavity_records, 'cavity_adjacent_distances_mm': pair_distances,
        'mold_screed_outward_normal': list(screed_faces[0].normalAt().toTuple()),
        'mold_screed_area_mm2': screed_faces[0].Area(),
        'mold_screed_wire_count': len(screed_faces[0].Wires()),
        'cavity_floor_mold_outward_normal': n_floor.tolist(),
        'pad_top_outward_normal': n_pad.tolist(), 'mold': mold, 'reference': reference}


def export_solid(shape, path_base, expected_volume):
    step = path_base.with_suffix('.step'); stl = path_base.with_suffix('.stl')
    cq.exporters.export(shape, str(step))
    cq.exporters.export(shape, str(stl), tolerance=.015, angularTolerance=.05)
    back = cq.importers.importStep(str(step)).val()
    mesh = trimesh.load(stl, force='mesh', process=True)
    check = {'step_valid': back.isValid(), 'step_solids': len(back.Solids()),
        'step_volume_mm3': back.Volume(), 'step_volume_error_mm3': abs(back.Volume()-expected_volume),
        'stl_watertight': bool(mesh.is_watertight), 'stl_winding_consistent': bool(mesh.is_winding_consistent),
        'stl_body_count': int(mesh.body_count), 'stl_euler_number': int(mesh.euler_number),
        'stl_volume_mm3': float(mesh.volume), 'stl_volume_error_mm3': abs(float(mesh.volume)-expected_volume),
        'stl_bounds_mm': mesh.bounds.tolist(), 'stl_faces': len(mesh.faces)}
    assert check['step_valid'] and check['step_solids'] == 1 and check['step_volume_error_mm3'] < 1e-5
    assert check['stl_watertight'] and check['stl_winding_consistent'] and check['stl_body_count'] == 1
    assert check['stl_euler_number'] == 2 and check['stl_volume_error_mm3'] < .003
    return check


def export_dxf(d, path):
    doc = ezdxf.new('R2010'); doc.units = ezdxf.units.MM
    for layer, color in [('MOLD_PLAN', 7), ('CAVITY_OPENING', 3), ('SECTION_A_A', 2), ('PAD_REFERENCE', 4), ('TEXT', 7)]:
        doc.layers.new(layer, dxfattribs={'color': color})
    ms = doc.modelspace()
    ms.add_lwpolyline([(-15, -21), (15, -21), (15, 21), (-15, 21)], close=True, dxfattribs={'layer': 'MOLD_PLAN'})
    for yc in CENTERS:
        ms.add_lwpolyline([(-9, yc-2.5), (9, yc-2.5), (9, yc+2.5), (-9, yc+2.5)], close=True,
                          dxfattribs={'layer': 'CAVITY_OPENING'})
    # A-A is a true XZ section through any one cavity; placed at drawing offset X=60, Z=0.
    section = [(-15, 0), (15, 0), (15, 12), (9, 12), (9, 12-d['pad_thickness_x_plus9_mm']),
               (-9, 12-d['pad_thickness_x_minus9_mm']), (-9, 12), (-15, 12)]
    ms.add_lwpolyline([(60+x, z) for x, z in section], close=True, dxfattribs={'layer': 'SECTION_A_A'})
    pad = [(-9, 0), (9, 0), (9, d['pad_thickness_x_plus9_mm']), (-9, d['pad_thickness_x_minus9_mm'])]
    ms.add_lwpolyline([(60+x, -20+z) for x, z in pad], close=True, dxfattribs={'layer': 'PAD_REFERENCE'})
    for txt, point in [(d['part']+' - units mm; prototype only', (-15, 28)), ('A-A: y=-12, drawing offset (60,0)', (40, 18)),
                       ('CAST PAD - reference only; offset (60,-20)', (40, -26))]:
        ms.add_text(txt, dxfattribs={'height': 1.7, 'layer': 'TEXT'}).set_placement(point)
    doc.saveas(path)
    back = ezdxf.readfile(path); audit = back.audit()
    openings = list(back.modelspace().query('LWPOLYLINE[layer=="CAVITY_OPENING"]'))
    assert len(openings) == 4 and not audit.errors and back.units == ezdxf.units.MM
    for poly, yc in zip(openings, CENTERS):
        xy = np.asarray(list(poly.get_points('xy')))
        assert poly.closed and np.allclose(xy.min(axis=0), [-9, yc-2.5]) and np.allclose(xy.max(axis=0), [9, yc+2.5])
    return {'dxf_units': back.units, 'dxf_audit_errors': len(audit.errors), 'dxf_cavity_rectangles': 4,
            'dxf_section_offset_xz_mm': [60, 0], 'dxf_pad_reference_offset_xz_mm': [60, -20]}


def check_layout_pads(root, params, variants):
    """Compare placed cast references to all eight existing exact STEP pads."""
    layout = root/'engineering/generated/layout'
    manifest_path = layout/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['revision'] == params['revision']
    fingers = {f['id']: f for f in params['head']['fingers']}
    face = np.asarray(params['head']['face_center_mm'], dtype=float)
    records = []
    for d in variants:
        for fid in d['finger_ids']:
            f = fingers[fid]; phi = math.radians(f['phi_deg'])
            er = np.array([math.cos(phi), math.sin(phi), 0])
            origin = face+f['root_radius_mm']*er+[0, 0, f['root_z_mm']]
            for side in [-1, 1]:
                part = f'F_{fid}_pad_{side}'
                source = layout/'parts-step'/(part+'.step')
                nominal = d['reference'].translate((f['contact_along_mm'], side*f['width_mm']*.08, 6))
                nominal = nominal.rotate((0, 0, 0), (0, 0, 1), f['phi_deg']).translate(origin.tolist())
                existing = cq.importers.importStep(str(source)).val()
                delta = nominal.cut(existing).Volume()+existing.cut(nominal).Volume()
                assert delta < 1e-5 and abs(existing.Volume()-450) < 1e-5
                records.append({'part': part, 'step_sha256': sha(source), 'volume_mm3': existing.Volume(),
                                'symmetric_difference_mm3': delta})
    return {'manifest_sha256': sha(manifest_path), 'manifest_parameters_sha256': manifest['parameters_sha256'],
            'pad_count': len(records), 'records': records}


def txt(c, x, y, s, size=9, color=BLUE, font='CJK'):
    c.setFont(font, size); c.setFillColorRGB(*color); c.drawString(x, y, s)


def line(c, x1, y1, x2, y2, color=BLUE, width=.7, dash=None):
    c.setStrokeColorRGB(*color); c.setLineWidth(width); c.setDash(dash or [])
    c.line(x1, y1, x2, y2); c.setDash([])


def arrow(c, x, y, dx, dy, size=4):
    r = math.hypot(dx, dy); ux, uy = dx/r, dy/r
    p = c.beginPath(); p.moveTo(x, y)
    p.lineTo(x+ux*size-uy*size*.35, y+uy*size+ux*size*.35)
    p.lineTo(x+ux*size+uy*size*.35, y+uy*size-ux*size*.35); p.close()
    c.setFillColorRGB(*BLUE); c.drawPath(p, stroke=0, fill=1)


def dim_h(c, a, b, y, base, label):
    for x in [a, b]: line(c, x, base, x, y+5, GREY, .4)
    line(c, a, y, b, y); arrow(c, a, y, 1, 0); arrow(c, b, y, -1, 0)
    w = pdfmetrics.stringWidth(label, 'CJK', 8)
    c.setFillColorRGB(1, 1, 1); c.rect((a+b-w)/2-3, y-4, w+6, 12, fill=1, stroke=0)
    txt(c, (a+b-w)/2, y-2, label, 8)


def dim_v(c, a, b, x, base, label):
    for y in [a, b]: line(c, base, y, x+5, y, GREY, .4)
    line(c, x, a, x, b); arrow(c, x, a, 0, 1); arrow(c, x, b, 0, -1)
    c.saveState(); c.translate(x-5, (a+b)/2); c.rotate(90)
    w = pdfmetrics.stringWidth(label, 'CJK', 8)
    c.setFillColorRGB(1, 1, 1); c.rect(-w/2-3, -3, w+6, 12, fill=1, stroke=0)
    txt(c, -w/2, 0, label, 8); c.restoreState()


def polygon(c, points, fill=(.92, .95, .96)):
    p = c.beginPath(); p.moveTo(*points[0])
    for point in points[1:]: p.lineTo(*point)
    p.close(); c.setFillColorRGB(*fill); c.setStrokeColorRGB(*BLUE); c.setLineWidth(.8)
    c.drawPath(p, stroke=1, fill=1)


def pdf_page(c, d, number):
    W, H = landscape(A4)
    title = 'UPPER / 上指' if d['name'] == 'UPPER' else 'LOWER / 下指'
    txt(c, 30, H-32, 'ODRADEK  /  FOUR-CAVITY PAD MOLD', 19, font='Helvetica-Bold')
    txt(c, 30, H-54, title+'  |  '+d['part']+'  |  原型浇注工具 · 非载荷资格证明', 10, TEAL)
    txt(c, 30, H-72, '单位 mm；名义尺寸，不含收缩、涂层和打印补偿；所有主视图比例 2:1。', 9)
    line(c, 30, H-82, W-30, H-82, TEAL, 1)
    s = 2*PT_MM; cx, cy = 180, 358
    # Top projection; top openings do not change when wedge angle changes.
    txt(c, 80, 495, '俯视：沿 -Z 观察；原点在模底中心', 9)
    polygon(c, [(cx-15*s, cy-21*s), (cx+15*s, cy-21*s), (cx+15*s, cy+21*s), (cx-15*s, cy+21*s)])
    for i, yc in enumerate(CENTERS, 1):
        c.setFillColorRGB(1, 1, 1); c.setStrokeColorRGB(*BLUE)
        c.rect(cx-9*s, cy+(yc-2.5)*s, 18*s, 5*s, fill=1, stroke=1)
        line(c, cx-11*s, cy+yc*s, cx+11*s, cy+yc*s, GREY, .4, [3, 2])
        txt(c, cx+20.5*s, cy+yc*s-3, f'C{i}   y={yc:+.0f}', 8, font='Helvetica')
    line(c, cx, cy-22*s, cx, cy+22*s, GREY, .4, [5, 2, 1, 2])
    line(c, cx-16*s, cy, cx+16*s, cy, GREY, .4, [5, 2, 1, 2])
    txt(c, cx+15*s+4, cy+6, '+X', 7, font='Helvetica')
    txt(c, cx+5, cy+22*s, '+Y', 7, font='Helvetica')
    dim_h(c, cx-15*s, cx+15*s, cy-21*s-23, cy-21*s, '30.00')
    dim_v(c, cy-21*s, cy+21*s, cx-15*s-27, cx-15*s, '42.00')
    dim_h(c, cx-9*s, cx+9*s, cy+17.5*s, cy+14.5*s, '18.00')
    dim_v(c, cy-14.5*s, cy-9.5*s, cx-9*s-13, cx-9*s, '5.00')
    # Section designation at the lowest cavity, no ambiguous hidden slopes in plan.
    ay = cy-12*s
    line(c, cx-18*s, ay, cx-11*s, ay, TEAL, 1)
    arrow(c, cx-18*s, ay, 0, 1); txt(c, cx-18*s-4, ay-16, 'A', 9, font='Helvetica')
    line(c, cx+11*s, ay, cx+18*s, ay, TEAL, 1)
    arrow(c, cx+18*s, ay, 0, 1); txt(c, cx+18*s-3, ay-16, 'A', 9, font='Helvetica')
    txt(c, 80, 192, '腔中心：x=0；y=-12, -4, +4, +12', 9)
    txt(c, 80, 177, '腔距 8.00；腔间壁 3.00；外侧壁 X=6.00 / Y=6.50', 8)
    # True section through y=-12.
    sx, sz = 536, 404
    txt(c, 433, 495, 'A-A 剖面 / XZ；四腔截面相同', 9)
    tm, tp = d['pad_thickness_x_minus9_mm'], d['pad_thickness_x_plus9_mm']
    profile = [(-15, 0), (15, 0), (15, 12), (9, 12), (9, 12-tp), (-9, 12-tm), (-9, 12), (-15, 12)]
    polygon(c, [(sx+x*s, sz+z*s) for x, z in profile])
    dim_v(c, sz, sz+12*s, sx+15*s+25, sx+15*s, '12.00')
    line(c, sx-15*s-10, sz+12*s, sx+15*s+12, sz+12*s, TEAL, .6, [4, 2])
    txt(c, 682, 474, '刮平面 z=12', 8)
    txt(c, 433, 388, f'腔底：z = 7 - x cot(q)；cot(q)={d["cot_q"]:+.9f}', 8)
    txt(c, 433, 374, f'底厚最小 {d["minimum_wall_mm"]["bottom"]:.4f}；打印床接触面 z=0', 8)
    # Reference pad after demolding and flipping.
    px, pz = 505, 307
    points = [(-9, 0), (9, 0), (9, tp), (-9, tm)]
    polygon(c, [(px+x*s, pz+z*s) for x, z in points], (.87, .96, .94))
    line(c, px-12*s, pz, px+12*s, pz, TEAL, .6, [4, 2])
    txt(c, 608, 343, '脱模 → 绕 X 轴翻转 180°', 8)
    txt(c, 608, 328, '平背朝下，楔形接触面朝上', 8)
    txt(c, 608, 313, '+X 厚度减小；不可反装', 8)
    txt(c, 433, 287, '成品参考：z = 5 + x cot(q)，背面 z=0', 8)
    # Explicit numerical dimensions define the slope without protractor precision.
    rows = [('x=-9 端厚 / t(-9)', f'{tm:.6f}'), ('x=+9 端厚 / t(+9)', f'{tp:.6f}'),
            ('目标姿态 q / 楔角 q-90', f'{d["target_q_deg"]:.6f}° / {d["target_q_deg"]-90:.6f}°'),
            ('单腔体积 / 每模硅胶净量', '450 mm³ / 1.800 cm³')]
    for i, (label, value) in enumerate(rows):
        y = 266-i*20
        if i % 2 == 0:
            c.setFillColorRGB(.95, .97, .98); c.rect(428, y-5, 377, 19, fill=1, stroke=0)
        txt(c, 433, y, label, 8); txt(c, 614, y, value, 8)
    line(c, 30, 157, W-30, 157, TEAL, .8)
    left = ['打印：模底 z=0 朝下；腔口朝上，无支撑进入腔内。',
            '建议初样 PLA 或 PETG，0.10 mm 层高、100% 填充。',
            '打印材料、封孔/脱模处理都须先做固化接触小样。',
            '无拔模斜度/圆角/缩放补偿；实际脱模与公差未验证。',
            '图上腔号与坐标不刻入实体，打印后在外壁记录类型。']
    right = ['Dragon Skin 30 仅为候选；工艺与 SDS 见配套文档。',
             '八垫净体积 3.600 cm³；按 1.08 g/cm³ 为 3.888 g。',
             '不含杯壁、刮平和气泡损失；不是建议一次配料质量。',
             '楔垫无机械保持设计；本图不认可胶粘或 2 kg 抓取。',
             '单指定位试验必须另用独立托架托住物体。']
    for i, (a, b) in enumerate(zip(left, right)):
        txt(c, 30, 140-i*16, a, 8); txt(c, 433, 140-i*16, b, 8)
    line(c, 30, 47, W-30, 47, GREY, .6)
    txt(c, 30, 31, 'CC-BY-NC-4.0 | Auromix contributors | Nominal prototype tooling; no manufacturing or payload release.', 7.5, font='Helvetica')
    txt(c, W-139, 17, f'R4-PAD-MOLD-01 | {number}/2', 7.5, font='Helvetica')
    c.showPage()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, default=root/'engineering/parameters/r4-layout.json')
    parser.add_argument('--output', type=Path, default=root/'engineering/generated/pad-molds')
    parser.add_argument('--font', type=Path, required=True, help='TrueType Chinese font (not redistributed)')
    args = parser.parse_args()
    params = json.loads(args.parameters.read_text())
    assert params['revision'] == 'R4-layout-03'
    assert params['head']['contact_study']['pad_surface_center_normal_mm'] == 11
    fingers = {f['id']: f for f in params['head']['fingers']}
    variants = [make_variant('UPPER', [fingers['UR'], fingers['UL']]),
                make_variant('LOWER', [fingers['LL'], fingers['LR']])]
    layout_check = check_layout_pads(root, params, variants)
    assert layout_check['manifest_parameters_sha256'] == sha(args.parameters)
    out = args.output
    for directory in ['molds', 'pad-references', 'DXF', 'PDF']: (out/directory).mkdir(parents=True, exist_ok=True)
    parts = []
    for d in variants:
        result = {k: v for k, v in d.items() if k not in ['mold', 'reference']}
        result['mold_export'] = export_solid(d['mold'], out/'molds'/d['part'], 13320)
        result['reference_pad_export'] = export_solid(d['reference'], out/'pad-references'/('ODR-PAD-'+d['name']+'-REFERENCE'), 450)
        result['dxf_export'] = export_dxf(d, out/'DXF'/(d['part']+'.dxf'))
        parts.append(result)
    pdfmetrics.registerFont(TTFont('CJK', str(args.font)))
    pdf = out/'PDF'/'ODR-contact-pad-molds-R4.pdf'
    c = canvas.Canvas(str(pdf), pagesize=landscape(A4), pageCompression=1, invariant=1)
    c.setTitle('Odradek R4 upper and lower four-cavity silicone pad molds')
    c.setAuthor('Auromix contributors')
    for i, d in enumerate(variants, 1): pdf_page(c, d, i)
    c.save()
    read = PdfReader(pdf); assert len(read.pages) == 2
    for page in read.pages: assert 'ODRADEK' in page.extract_text() and '450' in page.extract_text()
    result = {'revision': 'R4-PAD-MOLD-01', 'status': 'analytical CAD/export checks passed; not printed or cast',
        'spdx_license': 'CC-BY-NC-4.0', 'units': 'mm', 'parameter_revision': params['revision'],
        'input_sha256': {'engineering/parameters/r4-layout.json': sha(args.parameters),
                         'engineering/build_layout.py': sha(root/'engineering/build_layout.py'),
                         'engineering/build_pad_molds.py': sha(Path(__file__))},
        'mold_bounds_mm': [[-15, -21, 0], [15, 21, 12]], 'cavity_dimensions_xy_mm': [18, 5],
        'cavity_centers_y_mm': CENTERS, 'mold_nominal_volume_mm3': 13320,
        'all_eight_pads_volume_cm3': 3.6, 'density_candidate_g_cm3': 1.08,
        'all_eight_pads_mass_g_excluding_losses': 3.888,
        'flip_formula': 'center cavity Y; R_x(180 deg); translate Z by +12 mm => (x,-y,12-z)',
        'layout_formula': 'translate reference pad X by contact_along_mm and Z by +6 mm; place Y at each original pad center',
        'manufacturing_scope': 'open-face prototype casting tools only; no draft, shrinkage, coating or print compensation',
        'unverified': ['printer tolerances', 'leak tightness', 'cure compatibility', 'demolding', 'friction coefficient',
                       'mechanical retention or bonding', 'compression stiffness', 'wear', '2 kg payload'],
        'parts': parts, 'existing_layout_comparison': layout_check, 'pdf_pages': len(read.pages),
        'sources': [
            {'url': 'https://www.smooth-on.com/products/dragon-skin-30/', 'role': 'official product data', 'accessed': '2026-09-27'},
            {'url': 'https://www.smooth-on.com/tb/files/DRAGON_SKIN_SERIES_TB.pdf', 'role': 'technical bulletin; 040825PA', 'accessed': '2026-09-27'},
            {'url': 'https://www.smooth-on.com/sds/10000306-10000271.pdf', 'role': 'US SDS A/B; revisions 2025-06-10 and 2025-06-11', 'accessed': '2026-09-27'}],
        'artifacts_sha256': {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                             if p.is_file() and p.suffix in ['.step', '.stl', '.dxf', '.pdf']}}
    (out/'verification.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'parts': len(parts), 'checks': 'PASS', 'pdf_pages': len(read.pages),
          'bottom_min_mm': {p['name']: p['minimum_wall_mm']['bottom'] for p in parts},
          'output': str(out)}, indent=2))


if __name__ == '__main__': main()
