# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Prepare original six-link/base/head meshes for a native 7+4 Blender review.

This consumes reviewed candidate artifacts. It does not export supplier BREP,
freeze tolerances or qualify collision-free poses. Mesh JSON is an intermediate.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json

import cadquery as cq
import numpy as np
import trimesh
from build_layout import moved
from build_base_study import LEG_XY
from arm_screening import arm_parameters
from kinematics import Arm

ROOT = Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    parts, sources = [], {}
    pp = ROOT/'engineering/parameters/r4-layout.json'
    p = json.loads(pp.read_text()); sources[str(pp.relative_to(ROOT))] = sha(pp)

    def add_step(path, name, transform, attachment, material='structure'):
        sources[str(path.relative_to(ROOT))] = sha(path)
        s = cq.importers.importStep(str(path)).val()
        assert s.isValid() and len(s.Solids()) == 1
        s = moved(s, transform)
        vertices, triangles = s.tessellate(.08, .10)
        parts.append({'id': name, 'vertices_m': [[c*.001 for c in v.toTuple()] for v in vertices],
                      'triangles': triangles, 'material': material, 'attachment': attachment,
                      'group': 'arm_structure', 'source': str(path.relative_to(ROOT)), 'volume_mm3': s.Volume()})

    for link in ['12', '23', '34', '45', '56', '67']:
        folder = ROOT/f'engineering/generated/link{link}-study'
        placement_path = folder/'part-placements.json'
        evidence_path = folder/'evidence.json'
        placement = json.loads(placement_path.read_text());evidence = json.loads(evidence_path.read_text())
        assert not evidence['errors']
        assert placement['parameters_sha256'] == sha(pp)
        for file in [placement_path,evidence_path]:sources[str(file.relative_to(ROOT))] = sha(file)
        for name, entry in placement['instances'].items():
            file = folder/(entry['part_id']+'.step')
            assert sha(file) == evidence['export_checks'][entry['part_id']]['sha256'][file.name]
            add_step(file, 'L'+link+'_'+name, np.asarray(entry['T_world_from_part_mm']), int(link[0]))

    folder = ROOT/'engineering/generated/base-study'
    bases = [('base_plate','ODR-BASE-PLATE-R4',[0,0,0]), ('backing_plate','ODR-BASE-BACK-R4',[0,0,-38]),
             ('rear_ring','ODR-J1-REAR-R4',[0,0,49.5]), ('front_ring','ODR-J1-FRONT-R4',[0,0,89.7])]
    bases += [(f'leg_{i+1}','ODR-BASE-LEG-R4',[float(x),float(y),16]) for i,(x,y) in enumerate(LEG_XY)]
    for name, file, xyz in bases:
        T=np.eye(4);T[:3,3]=xyz
        add_step(folder/(file+'.step'), 'BASE_'+name, T, 0, 'base')

    # Catalog-size original envelopes are deliberately separate from true CAD
    # links. They are not precise vendor surface models or collision witnesses.
    folder=ROOT/'engineering/generated/layout'
    for i,j in enumerate(p['joints']):
        add_step(folder/'parts-step'/(j['id']+'_housing_envelope.step'), j['id']+'_CATALOG_ENVELOPE', np.eye(4), i, 'joint_envelope')

    folder=ROOT/'engineering/generated/head-integrated-03'
    mp=folder/'blender-parts-manifest.json'
    head=json.loads(mp.read_text());gp=folder/head['glb_path']
    assert sha(gp)==head['glb_sha256']
    for file in [mp,gp]:sources[str(file.relative_to(ROOT))]=sha(file)
    closed_path=folder/'blender-parts-manifest-closed.json'
    closed=json.loads(closed_path.read_text())
    sources[str(closed_path.relative_to(ROOT))]=sha(closed_path)
    assert closed['head_face_world_mm']==head['head_face_world_mm']
    closed_bounds={'HEAD_'+e['id']:e['bbox_head_mm'] for e in closed['parts']}
    scene=trimesh.load(gp,force='scene')
    face=np.asarray(head['head_face_world_mm'])*.001
    for entry in head['parts']:
        T,geom=scene.graph.get(entry['glb_node'])
        mesh=scene.geometry[geom].copy();mesh.apply_transform(T)
        # Trimesh reads numerical file coordinates without a Blender glTF Y-up
        # conversion. These exported coordinates are explicitly head-Z-up.
        vertices=mesh.vertices+face
        parts.append({'id':'HEAD_'+entry['id'], 'head_id':entry['id'], 'vertices_m':vertices.tolist(),
                      'triangles':mesh.faces.tolist(), 'material':entry['material'],
                      'attachment':7, 'group':entry['group'], 'finger':entry['finger'],
                      'source':str(gp.relative_to(ROOT))+'#'+entry['glb_node'],
                      'volume_mm3':entry['shape_volume_mm3'], 'representation':entry.get('representation','')})

    # A separately labelled visual UI, not a manufactured central display.
    # Only the historic central pixel coordinates are used; the old petal LED
    # matrices are deliberately excluded because FPL01 replaces them.
    lighting=ROOT/'engineering/generated/lighting-layout/led-coordinate-reference.csv'
    with lighting.open() as f:
        pixels=[[float(r['panel_x_mm']),float(r['panel_y_mm'])] for r in csv.DictReader(f) if r['panel']=='circle']
    assert len(pixels)==285
    sources[str(lighting.relative_to(ROOT))]=sha(lighting)

    arm=Arm(arm_parameters(p))
    poses={'home':[0]*7, 'inspect':p['poses_deg']['inspect'], 'reach':p['poses_deg']['reach']}
    checks=[]
    for name,q in poses.items():
        frames=arm.prefixes(np.deg2rad(q))
        for entry in parts:
            if entry['group'] not in ['arm_structure','head_fixed']:continue
            v=np.asarray(entry['vertices_m'][0]);expected=(frames[entry['attachment']]@np.r_[v,1.])[:3]
            checks.append({'pose':name,'part':entry['id'],'expected_vertex_world_m':expected.tolist()})
    result={'revision':'ARM-INTEGRATED-PREVIEW01','parts':parts,'joints':p['joints'],'poses_deg':poses,
            'head_face_world_mm':head['head_face_world_mm'],'finger_joints':head['finger_joints'],
            'central_pixel_preview_mm':pixels,
            'independent_closed_CAD_bounds_head_mm':closed_bounds,
            'arm_vertex_checks':checks,'source_hashes':sources,'generator_sha256':sha(Path(__file__)),
            'manufacturing_release':False,
            'omissions':['Arm and base fasteners are not mesh-integrated; head hardware is included per its manifest','Internal harness, exterior guards and armor remain unbuilt','Central display is a separate visual pixel preview'],
            'scope':'Six original structural connections + original base + integrated head. Joint housings remain original catalog envelopes. Pose/animation is geometric review, not a collision or torque qualified trajectory.'}
    args.output.parent.mkdir(exist_ok=True,parents=True)
    args.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('Prepared parts:',len(parts),'sources:',len(sources),'bytes:',args.output.stat().st_size)


if __name__=='__main__':main()
