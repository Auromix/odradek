# SPDX-License-Identifier: CC-BY-NC-4.0
"""Numerical interface contract vs actual exported base CAD and native scene."""
import json,math,hashlib
from pathlib import Path
import cadquery as cq
HERE=Path(__file__).resolve().parent;C=HERE/'interface-contract.json';c=json.loads(C.read_text());m=c['mechanical']
F=HERE/'build/load-frame';E=HERE/'build/exterior'
cad=json.loads((F/'manifest.json').read_text());scene=json.loads((E/'manifest.json').read_text())
assert not scene['arm_reference_included'] and scene['module']=='standalone_base'
assert scene['interface_contract_sha256']==hashlib.sha256(C.read_bytes()).hexdigest()
flange=next(p for p in cad['parts'] if p['id']=='B06-104-LOAD-FLANGE')
b=flange['bbox_mm'];assert abs(b[1][2]-m['base_mating_plane_z'])<1e-6
assert abs(b[1][0]-b[0][0]-m['flange_outer_diameter'])<1e-6
features=[p for p in flange['features'] if p['callout'].startswith('M6x1-6H')]
assert len(features)==m['hole_count']
for i,p in enumerate(features):
    a=math.radians(m['first_hole_deg']+i*m['hole_step_deg']);r=m['bolt_circle_diameter']/2
    assert math.dist(p['entry_mm'][:2],[r*math.cos(a),75+r*math.sin(a)])<1e-6
    assert abs(p['entry_mm'][2]+p['depth_mm']-m['base_mating_plane_z'])<1e-6
shape=cq.importers.importStep(str(F/flange['step'])).val()
probe=cq.Solid.makeCylinder(m['cable_bore_diameter']/2-.001,12,cq.Vector(0,75,46))
assert shape.intersect(probe).Volume()<.001
p=scene['parameters'];assert p['collar_radius_mm'][0]*2==m['cover_neck_inner_diameter']
assert p['collar_top_z_mm'][0]==m['cover_neck_top_z']
assert cad['desk_thickness_mm']==m['desk_thickness_mm']
box=next(p for p in cad['parts'] if p['id']=='REF-BOX')['bbox_mm']
assert [box[1][i]-box[0][i] for i in range(3)]==m['shelf_box_budget_mm']
assert not any(p['id'].startswith('HW-ROOT-') for p in cad['parts'])
report={'pass':True,'interface_contract_sha256':hashlib.sha256(C.read_bytes()).hexdigest(),
 'load_frame_manifest_sha256':hashlib.sha256((F/'manifest.json').read_bytes()).hexdigest(),
 'manifest_sha256':hashlib.sha256((E/'manifest.json').read_bytes()).hexdigest(),
 'checked':['flange plane','OD160','PCD120 eight M6 phase22.5','56mm cable bore','neck ID136/Z74','desk thickness','box budget','base-only part membership'],
 'limits':['Nominal geometry/definition consistency; no mating tolerances, wiring clearance or measured load qualification']}
(E/'interface-contract-checks.json').write_text(json.dumps(report,indent=2)+'\n');print('BASE_INTERFACE_CONTRACT_PASS')
