# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Draw B04 from reimported STEP and its manifest, never from concept artwork.

Each part has four actual BREP edge projections, global-coordinate extents,
and a complete manifest feature schedule. Curved edges are sampled at 0.01 mm
deflection for vector output; dimensions are read from BREP/manifest, not from
the samples. Visible and hidden edges are both drawn (no hidden-line removal).
The result is an engineering drawing review, not a manufacturing release when
material condition, tolerances, surface finish or supplier interfaces are open.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

import cadquery as cq
import numpy as np
from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD = Path(__file__).resolve().parent / 'build'
INK = '#17333E'
TEAL = '#127482'
GRAY = '#607782'
PALE = '#DDE5E8'
AMBER = '#9A5E19'
FONT = 'B04CN'
EDGE_DEFLECTION = .01
VIEWS = [
    ('俯视 / XY', np.array([[1., 0, 0], [0, 1, 0]]), ('X', 'Y')),
    ('正视 / XZ', np.array([[1., 0, 0], [0, 0, 1]]), ('X', 'Z')),
    ('侧视 / YZ', np.array([[0., 1, 0], [0, 0, 1]]), ('Y', 'Z')),
    ('轴测 / 几何关系', np.array([[1., -1, 0], [1., 1, 2]]) /
     np.array([[math.sqrt(2)], [math.sqrt(6)]]), None),
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def num(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (float, np.floating)):
        return f'{value:.5f}'.rstrip('0').rstrip('.')
    return str(value)


def flatten(value, prefix=''):
    """Preserve every manifest value, including unrecognized feature fields."""
    if isinstance(value, dict):
        rows = []
        for key, item in value.items():
            rows.extend(flatten(item, f'{prefix}.{key}' if prefix else str(key)))
        return rows
    if isinstance(value, list):
        if all(not isinstance(x, (dict, list)) for x in value):
            return [(prefix, '[' + ', '.join(num(x) for x in value) + ']')]
        rows = []
        for index, item in enumerate(value):
            rows.extend(flatten(item, f'{prefix}[{index + 1}]'))
        return rows
    return [(prefix, num(value))]


def linewrap(text, width_mm, size):
    lines, current = [], ''
    limit = width_mm * mm
    for token in re.findall(r'\n|[^\S\n]+|[^\s]+', str(text)):
        if token == '\n':
            lines.append(current.rstrip())
            current = ''
            continue
        if not current and token.isspace():
            continue
        if pdfmetrics.stringWidth(current + token, FONT, size) <= limit:
            current += token
            continue
        if current:
            lines.append(current.rstrip())
            current = ''
        token = token.lstrip()
        if pdfmetrics.stringWidth(token, FONT, size) <= limit:
            current = token
            continue
        # Unspaced Chinese or unusually long identifiers may wrap by glyph;
        # ordinary decimal coordinates and English words remain intact.
        for ch in token:
            if current and pdfmetrics.stringWidth(current + ch, FONT, size) > limit:
                lines.append(current)
                current = ''
            current += ch
    return lines + [current.rstrip()]


def shape_polylines(shape):
    lines = []
    for edge in shape.Edges():
        points, _ = edge.sample(EDGE_DEFLECTION)
        pts = np.asarray([v.toTuple() for v in points], dtype=float)
        if len(pts) < 2:
            continue
        if edge.IsClosed():
            pts = np.vstack([pts, pts[0]])
        lines.append(pts)
    return lines


def bounds(shape):
    b = shape.BoundingBox()
    return np.array([[b.xmin, b.ymin, b.zmin], [b.xmax, b.ymax, b.zmax]])


def resolve_step(entry, manifest_path):
    raw = entry.get('step') or entry.get('step_path')
    if not raw:
        raise ValueError(f"{entry.get('id')}: manifest has no STEP path")
    path = Path(raw)
    candidates = [path] if path.is_absolute() else [manifest_path.parent / path, ROOT / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f'STEP not found: {raw}')


class Book:
    def __init__(self, path, revision, source_hash):
        self.c = canvas.Canvas(str(path), pagesize=landscape(A3), pageCompression=1)
        self.c.setTitle('Odradek B04 - STEP fabrication and assembly review')
        self.c.setAuthor('Auromix contributors')
        self.revision, self.source_hash, self.pages = revision, source_hash, 0

    def text(self, x, y, text, size=9, color=INK, align='left'):
        self.c.setFont(FONT, size)
        self.c.setFillColor(HexColor(color))
        fn = {'left': self.c.drawString, 'right': self.c.drawRightString,
              'center': self.c.drawCentredString}[align]
        fn(x * mm, y * mm, str(text))

    def line(self, a, b, color=GRAY, width=.35):
        self.c.setStrokeColor(HexColor(color))
        self.c.setLineWidth(width)
        self.c.line(a[0] * mm, a[1] * mm, b[0] * mm, b[1] * mm)

    def paragraph(self, x, y, text, width, size=8.5, leading=4.4, color=INK):
        for line in linewrap(text, width, size):
            self.text(x, y, line, size, color)
            y -= leading
        return y

    def page(self, title, subtitle):
        if self.pages:
            self.c.showPage()
        self.pages += 1
        self.text(15, 282, 'ODRADEK / ' + title, 18)
        self.text(15, 272, subtitle, 9, TEAL)
        self.text(405, 282, self.revision, 10, align='right')
        self.line((15, 267), (405, 267), TEAL, .8)
        self.line((15, 21), (405, 21), GRAY, .4)
        self.text(15, 14, 'mm | STEP 实体投影 | 边线不消隐 | 数值尺寸优先 | 未经制造放行', 8)
        self.text(405, 14, f'A3 / {self.pages:02d}', 8, align='right')
        self.text(15, 25, 'manifest SHA256 ' + self.source_hash, 6.8, GRAY)

    def save(self):
        self.c.save()


def project_view(book, lines, basis, rect, title, axes, svg_path=None, world_bbox=None):
    x, y, w, h = rect
    projected = [line @ basis.T for line in lines]
    allpoints = np.vstack(projected)
    lo, hi = allpoints.min(axis=0), allpoints.max(axis=0)
    if axes is not None and world_bbox is not None:
        # Orthographic overall dimensions use the actual BREP bounding box,
        # never the sampled curve extrema used only for vector display.
        corners = np.asarray(list(itertools.product(*zip(world_bbox[0], world_bbox[1])))) @ basis.T
        lo, hi = corners.min(axis=0), corners.max(axis=0)
    size = np.maximum(hi - lo, .01)
    fit = min((w - 30) / size[0], (h - 27) / size[1])
    scale = next((s for s in [4, 3, 2, 1.5, 1, .75, .5, .4, .25, .2, .1, .05] if s <= fit), fit)
    center = np.array([x + w / 2 - 1, y + h / 2 - 2])
    projected_center = (lo + hi) / 2
    book.text(x + 2, y + h - 5, title + f'  比例 {num(scale)}:1', 8.5, TEAL)
    for line in projected:
        paper = center + scale * (line - projected_center)
        for a, b in zip(paper[:-1], paper[1:]):
            if np.linalg.norm(a - b) > 1e-6:
                book.line(a, b, INK, .35)
    if axes:
        bx0, by0 = center + scale * (lo - projected_center)
        bx1, by1 = center + scale * (hi - projected_center)
        for bx in [bx0, bx1]:
            book.line((bx, by0 - 2), (bx, by0 - 7), GRAY, .25)
        book.line((bx0, by0 - 6), (bx1, by0 - 6), TEAL, .3)
        for bx in [bx0, bx1]:
            book.line((bx - .7, by0 - 6.7), (bx + .7, by0 - 5.3), TEAL, .4)
        book.text((bx0 + bx1) / 2, by0 - 10, f'{axes[0]} 跨度 {num(size[0])}', 7.4, align='center')
        book.text(x + 2, y + 2, f'全局 {axes[0]}[{num(lo[0])}, {num(hi[0])}]  {axes[1]}[{num(lo[1])}, {num(hi[1])}]', 7.1, GRAY)
    if svg_path:
        # SVG uses true model millimetres, and a Y-flip only for screen display.
        margin = 5.
        elements = []
        for line in projected:
            points = ' '.join(f'{q[0]:.6f},{-q[1]:.6f}' for q in line)
            elements.append(f'<polyline points="{points}"/>')
        text = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0] + 2*margin}mm" height="{size[1] + 2*margin}mm" '
                f'viewBox="{lo[0]-margin} {-hi[1]-margin} {size[0]+2*margin} {size[1]+2*margin}">'
                f'<title>{escape(title)} - STEP edges, millimetres, no hidden-line removal</title>'
                '<g fill="none" stroke="#17333e" stroke-width="0.16">' + ''.join(elements) + '</g></svg>')
        svg_path.write_text(text)
    return {'title': title, 'scale': scale, 'projected_bounds_mm': [lo.tolist(), hi.tolist()]}


def row_pages(book, title, rows, subtitle='manifest 特征原文 / 坐标均为建模全局基准，不另造尺寸'):
    page_rows = []
    remaining = 205.
    for key, value in rows:
        klines, vlines = linewrap(key, 125, 8), linewrap(value, 248, 8)
        height = max(len(klines), len(vlines)) * 4.4 + 3
        if height > 210:
            raise ValueError(f'Feature row too long for page: {key}')
        if height > remaining and page_rows:
            _draw_rows(book, title, subtitle, page_rows)
            page_rows, remaining = [], 205.
        page_rows.append((klines, vlines, height))
        remaining -= height
    if page_rows:
        _draw_rows(book, title, subtitle, page_rows)


def _draw_rows(book, title, subtitle, rows):
    book.page(title, subtitle)
    book.text(18, 256, '特征 / 属性路径', 9, TEAL)
    book.text(151, 256, '数值、方向和限定说明（长度默认 mm；其他单位以字段名为准）', 9, TEAL)
    y = 247.
    for klines, vlines, height in rows:
        for index, line in enumerate(klines):
            book.text(18, y - index * 4.4, line, 8)
        for index, line in enumerate(vlines):
            book.text(151, y - index * 4.4, line, 8)
        y -= height
        book.line((18, y + 1.7), (402, y + 1.7), PALE, .25)


def compact_features(item):
    """Group identical callouts without discarding individual hole coordinates."""
    groups = {}
    features = item.get('features', [])
    if not isinstance(features, list):
        return flatten(features, str(item['id']))
    for feature in features:
        if not isinstance(feature, dict):
            groups.setdefault(str(feature), []).append('')
            continue
        description = {key: value for key, value in feature.items() if key not in ('entry_xyz', 'center', 'id')}
        signature = json.dumps(description, ensure_ascii=False, sort_keys=True)
        coordinate = feature.get('entry_xyz', feature.get('center'))
        groups.setdefault(signature, []).append(coordinate)
    rows = []
    for signature, points in groups.items():
        try:
            description = json.loads(signature)
        except json.JSONDecodeError:
            description = {'note': signature}
        callout = description.get('callout', description.get('type', 'feature'))
        extras = ', '.join(f'{key}={num(value) if not isinstance(value, list) else str(value)}'
                           for key, value in description.items() if key not in ('callout', 'type'))
        coords = '; '.join('(' + ', '.join(map(num, point)) + ')' for point in points if isinstance(point, list))
        rows.append((str(item['id']) + '\n' + callout,
                     extras + ('\n全局入口坐标 XYZ: ' + coords if coords else '')))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_BUILD / 'manifest.json')
    parser.add_argument('--output', type=Path, default=DEFAULT_BUILD / 'drawings')
    parser.add_argument('--font', type=Path, default=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
    parser.add_argument('--individual-parts', action='store_true', help='Add four-view sheets and full raw schedules for each part; default is compact auxiliary review.')
    args = parser.parse_args()
    manifest_bytes = args.manifest.read_bytes()
    source_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    entries = manifest['parts']
    if isinstance(entries, dict):
        entries = [{'id': k, **v} for k, v in entries.items()]
    if not entries:
        raise ValueError('No parts in manifest')
    pdfmetrics.registerFont(TTFont(FONT, str(args.font)))
    args.output.mkdir(parents=True, exist_ok=True)
    loaded = []
    excluded = []
    for item in entries:
        if not item.get('step'):
            if item.get('category') == 'custom':
                raise ValueError(f"Custom part without STEP: {item.get('id')}")
            excluded.append({'id': item['id'], 'category': item.get('category'), 'reason': 'No fabrication STEP; omitted from per-part schedules'})
            continue
        path = resolve_step(item, args.manifest)
        wp = cq.importers.importStep(str(path))
        shape = cq.Compound.makeCompound(wp.vals())
        if not shape.isValid() or not shape.Solids():
            raise ValueError(f'Invalid or empty STEP: {path}')
        loaded.append({**item, '_path': path, '_step_hash': digest(path), '_shape': shape, '_lines': shape_polylines(shape), '_bounds': bounds(shape)})
    pdf_path = args.output / 'base-b04-manufacturing-review.pdf'
    revision = manifest.get('revision', 'BASE-B04')
    book = Book(pdf_path, revision, source_hash)
    book.page('底座加工与装配审查', '真实 STEP 重读 / 全局坐标 X 左右、+Y 向桌内、+Z 向上 / 原创零件名义几何')
    assembly_path = args.manifest.parent / 'ODR-BASE-B04-P1.step'
    assembly_hash = digest(assembly_path) if assembly_path.is_file() else None
    if assembly_path.is_file():
        assembly_shape = cq.Compound.makeCompound(cq.importers.importStep(str(assembly_path)).vals())
        all_lines = shape_polylines(assembly_shape)
    else:
        all_lines = [line for item in loaded for line in item['_lines']]
    project_view(book, all_lines, VIEWS[3][1], (16, 65, 264, 193), '名义装配 / 同一全局坐标', None, args.output / 'assembly-isometric.svg')
    y = 253
    for text in ['本图册的用途', '以实体投影和特征表支持零件报价、工艺及装配审查。尺寸由 STEP 或 manifest 读取，不从概念图估算。',
                 '读图约定', '曲边按 0.01 mm 弦偏差采样；边线不消隐。各正交视图注明坐标平面与比例，不按三角法排图。',
                 '基准与制造状态', '采用同一装配全局原点。各零件给出全局极值；manifest 中 local_bbox 按原字段保留。未定义的公差、表面处理、有效牙深及供应商接口不得由本图补定。',
                 '实体不等于总装通过', 'PCB、插头、线缆和采购件是否进入实体须看 manifest。简化包络不作为真实供应商模型。尺寸表不提供承载或电气验收结论。']:
        y = book.paragraph(288, y, text, 113, 9 if len(text) < 12 else 8.2, 4.6,
                           TEAL if len(text) < 12 else INK) - 5
    book.paragraph(18, 53, '原点与接口须在加工前共同确认。紧固扭矩、公差等级、材料状态、线束弯曲半径和压接规范若未在原始清单中给出，均保持待确认。', 260, 8.2)
    bom_rows = []
    for item in loaded:
        label = str(item['id'])
        bom_rows.append((label, f"数量 {item.get('quantity', 1)} | 材料 {item.get('material', '未定义')} | 工艺 {item.get('process', '未定义')} | {item['_path'].name}"))
    row_pages(book, '加工件与来源清单', bom_rows, '仅列 manifest 中带加工 STEP 的零件；采购件、紧固件和 PCB 另见对应清单')
    parameter_path = Path(__file__).resolve().parent / 'parameters.json'
    parameter_data = json.loads(parameter_path.read_text()) if parameter_path.exists() else {}
    if parameter_data:
        meta_rows = []
        for key in ['coordinates', 'tolerances', 'notes']:
            if key in parameter_data:
                meta_rows.extend(flatten(parameter_data[key], key))
        grouped_notes = {}
        for item in loaded:
            note = item.get('notes', [])
            note = '\n'.join(map(str, note)) if isinstance(note, list) else str(note)
            if note:
                grouped_notes.setdefault(note, []).append(str(item['id']))
        for note, identifiers in grouped_notes.items():
            meta_rows.append((', '.join(identifiers), note))
        row_pages(book, '共用基准与声明', meta_rows, '逐字沿用参数声明；孔位置公差的具体基准与检验方法仍需制造评审')
    audit_parts, csv_rows, compact_rows = [], [], []
    for item in loaded:
        label = str(item['id'])
        bb = item['_bounds']
        projections = []
        if args.individual_parts:
            book.page(label, f"材料 {item.get('material', '未定义')} | 工艺 {item.get('process', '未定义')} | 数量 {item.get('quantity', 1)}")
            rects = [(16, 148, 129, 107), (16, 40, 129, 100), (153, 40, 129, 100), (153, 148, 129, 107)]
            for index, ((title, basis, axes), rect) in enumerate(zip(VIEWS, rects)):
                projections.append(project_view(book, item['_lines'], basis, rect, title, axes,
                                                args.output / f'{label}-view-{index+1}.svg', bb))
            y = book.paragraph(290, 253, '全局坐标极值 / STEP 重读', 112, 10, color=TEAL) - 4
            for k, axis in enumerate('XYZ'):
                y = book.paragraph(290, y, f'{axis}: {num(bb[0,k])} 至 {num(bb[1,k])}  / 跨度 {num(bb[1,k]-bb[0,k])}', 112, 8.5) - 2
            y = book.paragraph(290, y - 5, f"实体数 {len(item['_shape'].Solids())}；体积 {item['_shape'].Volume():.3f} mm³", 112, 8.5) - 6
            y = book.paragraph(290, y, '特征尺寸与工艺要求', 112, 10, color=TEAL) - 5
            y = book.paragraph(290, y, '逐项数值见后续特征表。表中坐标直接保留 manifest 定义；未给出的孔深、螺纹长度、倒角与公差均未确定。', 112, 8.5) - 6
            notes = item.get('notes', [])
            notes = '\n'.join(map(str, notes)) if isinstance(notes, list) else str(notes)
            note_lines = linewrap(notes, 112, 8)
            if len(note_lines) * 4.3 <= y - 42:
                book.paragraph(290, y, notes, 112, 8, 4.3)
            else:
                book.paragraph(290, y, '完整 notes 见后续特征表。', 112, 8)
        rows = [('STEP.global_min_xyz_mm', ', '.join(map(num, bb[0]))),
                ('STEP.global_max_xyz_mm', ', '.join(map(num, bb[1]))),
                ('STEP.volume_mm3', num(item['_shape'].Volume()))]
        for key in ['local_bbox', 'features', 'notes', 'datums', 'tolerances', 'finish', 'drawing_notes']:
            if key in item:
                rows.extend(flatten(item[key], key))
        if 'features' not in item:
            rows.append(('features', '未提供：不得仅按外形投影加工孔位或接口'))
        if args.individual_parts:
            row_pages(book, label + ' / 特征表', rows)
        if item.get('category', 'custom') == 'custom':
            compact_rows.extend(compact_features(item))
        csv_rows.extend([(label, key, value) for key, value in rows])
        audit_parts.append({'id': label, 'step': str(item['_path'].relative_to(ROOT)),
                            'step_sha256': item['_step_hash'], 'bbox_global_mm': bb.tolist(),
                            'volume_mm3': item['_shape'].Volume(), 'solid_count': len(item['_shape'].Solids()),
                            'valid': item['_shape'].isValid(), 'projections': projections,
                            'feature_attribute_count': len(rows)})
    if not args.individual_parts:
        row_pages(book, '加工特征与全局入口坐标', compact_rows,
                  '相同标注已成组；全部入口坐标保留 / 本表不含采购包络的伪加工尺寸')
    book.save()
    pages = PdfReader(str(pdf_path)).pages
    if len(pages) != book.pages or any(not page.extract_text() for page in pages):
        raise ValueError('PDF page/text verification failed')
    if digest(args.manifest) != source_hash or any(digest(x['_path']) != x['_step_hash'] for x in loaded):
        raise RuntimeError('Input geometry changed during drawing generation; rerun on a stable build')
    if assembly_hash is not None and digest(assembly_path) != assembly_hash:
        raise RuntimeError('Assembly STEP changed during drawing generation; rerun on a stable build')
    with (args.output / 'feature-coordinates.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['part_id', 'attribute', 'value_in_manifest_global_coordinates'])
        writer.writerows(csv_rows)
    evidence = {'revision': revision, 'manifest_sha256': source_hash,
                'generator_sha256': digest(__file__), 'pdf_sha256': digest(pdf_path),
                'pages': book.pages, 'part_count': len(loaded), 'parts': audit_parts,
                'excluded_nonfabrication_entries': excluded,
                'assembly_step_sha256': assembly_hash,
                'projection_source': 'Reimported STEP BREP edges; no concept artwork',
                'curve_sampling_deflection_mm': EDGE_DEFLECTION,
                'parameters_sha256': digest(parameter_path) if parameter_path.exists() else None,
                'individual_part_sheets': args.individual_parts,
                'hidden_line_removal': False, 'visual_review': 'pending; render and inspect final PDF',
                'manufacturing_release': False}
    (args.output / 'drawing-evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pdf': str(pdf_path), 'pages': book.pages, 'parts': len(loaded), 'visual_review': 'pending'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
