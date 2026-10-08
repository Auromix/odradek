# SPDX-License-Identifier: CC-BY-NC-4.0
"""Read-only A10/B05 packaging study; no assembly or load qualification.

Needs numpy and the adjacent odradek-arm-body checkout. Source geometry is
read from its original manifest; no supplier geometry is redistributed.
"""
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARM = ROOT.parent / 'odradek-arm-body'
arm_ref = '939b772baf1fb0d05439f3f7b1f5bd1df993ba04'
base_ref = '075e799'
arm_path = 'engineering/arm_a10/build/manifest.json'
base_path = 'engineering/base_b05/build/exterior/exterior-manifest.json'
arm_bytes = subprocess.check_output(['git', 'show', f'{arm_ref}:{arm_path}'], cwd=ARM)
base_bytes = subprocess.check_output(['git', 'show', f'{base_ref}:{base_path}'], cwd=ROOT)
arm = json.loads(arm_bytes)
base = json.loads(base_bytes)
neck_radius = base['parameters']['collar_radius_mm'][0]
rows = []
translation_z = arm['base_interface']['translation_mm'][2]
ids = ['P00-root-open', 'P00-J1-top-ring', 'S00-waist-A', 'S00-waist-B']
for z in [58., 66., 74., 90., 110., 130., 164.6]:
    for part in arm['parts']:
        if part['id'] not in ids:
            continue
        vertices = np.array(part['vertices_mm'], dtype=float)
        vertices[:, 2] += translation_z
        triangles = vertices[np.array(part['triangles'])]
        samples = []
        for start, end in [(0, 1), (1, 2), (2, 0)]:
            a, b = triangles[:, start], triangles[:, end]
            dz = b[:, 2] - a[:, 2]
            mask = (abs(dz) > 1e-9) & ((a[:, 2]-z)*(b[:, 2]-z) <= 0)
            if np.any(mask):
                samples.append((a[mask] + ((z-a[mask, 2])/dz[mask])[:, None]
                                * (b[mask]-a[mask]))[:, :2])
        if samples:
            points = np.concatenate(samples)
            rows.append(dict(base_z_mm=z, part=part['id'],
                max_radius_about_axis_mm=float(np.linalg.norm(points, axis=1).max()),
                section_bbox_local_xy_mm=np.ptp(points, axis=0).tolist()))

at_neck = [r for r in rows if r['base_z_mm'] == 74.]
structure = [r for r in at_neck if r['part'].startswith('P00')]
radius_structure = max(r['max_radius_about_axis_mm'] for r in structure)
radius_all = max(r['max_radius_about_axis_mm'] for r in at_neck)
mount = arm['joint_mounting'][0]
assert mount['model'] == arm['layout']['joints'][0]['model'] == 'RS03'
report = dict(
    schema='odradek.base-compact-fit-study.v1', date='2026-10-08',
    status='packaging_constraints_only_not_new_cad_or_assembly_qualification',
    confirmed_print_volume_mm=[256, 256, 256],
    candidate_outer_upper_target_mm=[240, 230],
    centered_xy_margin_without_support_mm=[8, 13],
    source_snapshots=[dict(repository='odradek-arm-body', ref=arm_ref, path=arm_path,
                           sha256=hashlib.sha256(arm_bytes).hexdigest()),
                      dict(repository='odradek', ref=base_ref, path=base_path,
                           sha256=hashlib.sha256(base_bytes).hexdigest())],
    source_base_transform=arm['base_interface'],
    current_j1=arm['layout']['joints'][0], current_j1_mounting=mount,
    old_b05_neck=dict(revision=base['revision'], inner_d_mm=2*neck_radius, outer_d_mm=170, top_z_mm=74,
                     axis_xy_mm=[0, 75]),
    sections=rows,
    neck_z74=dict(structure_circular_envelope_d_mm=2*radius_structure,
                 with_old_waist_circular_envelope_d_mm=2*radius_all,
                 old_opening_radial_difference_structure_mm=neck_radius-radius_structure,
                 old_opening_radial_difference_with_waist_mm=neck_radius-radius_all,
                 interpretation='Negative radial differences reject concentric circular-envelope fit; not a solid-volume collision test'),
    old_b04_chassis=dict(deck_bbox_xy_mm=[220, 256],
                        c_plate_total_width_mm=240,
                        fits_240x230_without_redesign=False),
    proposal=dict(main_cover='nose + both wings in one part; bottom fasteners',
                  collar='redesign around A10 root and waist; do not scale 104mm aperture',
                  load_interface='retain 8xM6 on PCD120, flange OD160; no automatic load qualification',
                  pcb_reservation_mm=[116, 56],
                  electronics='A10 uses CAN motors; historic EtherCAT panel is not verified CAN wiring'),
    limits=['Only listed horizontal mesh sections were measured; no continuous height or motion envelope proof.',
            'A10 XY rotation does not alter radius; axis relocation must be explicit in new CAD.',
            'No new compact clamp/chassis geometry, mated connectors, tool paths, tolerances, thermal or load checks.',
            'Print margin excludes supports, brim, calibration and excluded bed areas.'])
out = HERE / 'build/compact-study'
out.mkdir(parents=True, exist_ok=True)
(out/'packaging-constraints.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(report['neck_z74'], ensure_ascii=False))
