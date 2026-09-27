# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read actual original link STEP inertias; keep all remaining proxies explicit."""
from pathlib import Path
import copy
import hashlib
import json

import cadquery as cq
import numpy as np
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from arm_screening import arm_parameters

ROOT = Path(__file__).resolve().parents[1]
RESERVES = {'12': .20, '23': .15, '34': .15, '45': .15, '56': .10, '67': .10}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def link_bodies(link):
    """Do not silently skip missing parts or substitute a budget for failed CAD."""
    folder = ROOT / f'engineering/generated/link{link}-study'
    placement_path = folder / 'part-placements.json'
    evidence_path = folder / 'evidence.json'
    placement = json.loads(placement_path.read_text())
    evidence = json.loads(evidence_path.read_text())
    baseline = ROOT / 'engineering/parameters/r4-layout.json'
    assert placement['parameters_sha256'] == sha(baseline)
    assert evidence['parameters_sha256'] == sha(baseline)
    assert not evidence['errors'], 'Link geometry evidence must be reviewed first'
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in [placement_path, evidence_path]}
    bodies = []
    for name, entry in placement['instances'].items():
        part = folder / (entry['part_id'] + '.step')
        digest = sha(part)
        assert digest == evidence['export_checks'][entry['part_id']]['sha256'][part.name]
        s = cq.importers.importStep(str(part)).val()
        assert s.isValid() and len(s.Solids()) == 1
        prop = GProp_GProps()
        BRepGProp.VolumeProperties_s(s.wrapped, prop)
        mass = prop.Mass() * 2.7e-6
        local = np.array([prop.CentreOfMass().X(), prop.CentreOfMass().Y(), prop.CentreOfMass().Z()])
        transform = np.array(entry['T_world_from_part_mm'])
        world = (transform @ np.r_[local, 1.])[:3]
        tensor = prop.MatrixOfInertia()
        inertia = np.array([[tensor.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)]) * 2.7e-12
        assert abs(mass - entry['mass_kg_6061']) < 1e-8
        assert np.max(abs(world - entry['estimated_COM_world_mm'])) < 1e-5
        assert entry['preceding_joints'] == int(link[0])
        assert np.linalg.eigvalsh(inertia).min() > 0
        assert np.max(abs(transform[:3, :3].T @ transform[:3, :3] - np.eye(3))) < 1e-10
        bodies.append({'id': f'L{link}_{name}', 'mass_kg': mass, 'preceding_joints': int(link[0]),
                       'com_home_m': (world * .001).tolist(), 'orientation_home': transform[:3, :3].tolist(),
                       'inertia_com_kg_m2': inertia.tolist(), 'mass_source': str(part.relative_to(ROOT)),
                       'scope': 'Nominal homogeneous6061 CAD integration; no thread helix or measured mass'})
        hashes[str(part.relative_to(ROOT))] = digest
    mass = sum(b['mass_kg'] for b in bodies)
    com = sum(b['mass_kg'] * np.array(b['com_home_m']) for b in bodies) / mass
    reserve = RESERVES[link]
    bodies.append({'id': f'L{link}_hardware_reserve', 'mass_kg': reserve, 'preceding_joints': int(link[0]),
                   'com_home_m': com.tolist(), 'orientation_home': np.eye(3).tolist(),
                   'inertia_com_kg_m2': (np.eye(3) * reserve * .05**2 / 6).tolist(),
                   'mass_source': 'Unweighed hardware allowance at metalCOM;50mm cube inertia proxy'})
    return bodies, {'metal_mass_kg': mass, 'reserve_kg': reserve, 'metal_COM_home_mm': (com*1000).tolist(),
                    'CAD_parts': len(bodies)-1, 'source_hashes': hashes}


def structural_model(parameters, links=('12', '23', '34', '56', '67'), head_mass=4.5, extension_mm=0.):
    p = copy.deepcopy(parameters)
    # This is a budget-head scenario, NOT a translation of a real head assembly.
    # Its independent L7 0.15kg allowance stays at the original mount location.
    p['head']['tcp_home_mm'][2] += extension_mm
    p['head']['head_com_home_mm'][2] += extension_mm
    model = arm_parameters(p, head_mass)
    info = {}
    for link in links:
        bodies, source = link_bodies(link)
        old = f'L{link[0]}_budget'
        assert sum(b['id'] == old for b in model['bodies']) == 1
        model['bodies'] = [b for b in model['bodies'] if b['id'] != old] + bodies
        info[link] = source
    model['model_scope'] = {
        'links_with_CAD': list(links), 'head_is_budget': True, 'head_mass_kg': head_mass,
        'budget_head_and_TCP_shift_mm': extension_mm,
        'L7_allowance': 'Legacy0.15kg remains separate; remove when real head includes adapter/extension',
        'joint_mass': 'Catalog module mass assigned upstream with cylinder inertia and midpoint COM proxies',
        'rotor_inertia': 'Unknown, not qualified by setting absent entries to zero',
        'fingers': 'Head is rigid lump; four moving fingers and their coupling are not represented',
        'manufacturing_release': False}
    return model, info
