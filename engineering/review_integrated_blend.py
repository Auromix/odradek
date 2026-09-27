# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Reopen the saved blend with --disable-autoexec and verify native drivers.

Run Blender --background --disable-autoexec <blend> --python this.py --
    --mesh-json <private intermediate> --report <report.json>
This checks file persistence/geometry, not executable trajectories.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mesh-json',required=True,type=Path)
parser.add_argument('--report',required=True,type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
source=json.loads(args.mesh_json.read_text())
scene=bpy.context.scene


def pose(q,closed=False):
    for i,a in enumerate(q):
        ob=bpy.data.objects['J'+str(i+1)];ob['q_deg']=float(a);ob.update_tag()
    for f in source['finger_joints']:
        ob=bpy.data.objects['FINGER_'+f['id']]
        ob['q_deg']=float(f['range_deg'][1]) if closed else 0.;ob.update_tag()
    scene.frame_set(scene.frame_current);bpy.context.view_layer.update()


errors=[]
for name,q in source['poses_deg'].items():
    pose(q)
    for row in [r for r in source['arm_vertex_checks'] if r['pose']==name]:
        ob=bpy.data.objects[row['part']]
        error=(ob.matrix_world@ob.data.vertices[0].co-Vector(row['expected_vertex_world_m'])).length*1000
        assert error<.005,(name,row['part'],error)
        errors.append(error)
pose([0]*7,closed=True)
closed_errors=[]
for name,wanted in source['independent_closed_CAD_bounds_head_mm'].items():
    ob=bpy.data.objects[name];T=np.array(ob.matrix_world)
    local=np.array([tuple(x.co) for x in ob.data.vertices])
    assert np.all(np.isfinite(local)) and np.all(np.isfinite(T))
    # Explicit tensor contraction avoids a host BLAS floating-status warning
    # observed after Blender dependency-graph evaluation on this macOS build.
    v=np.einsum('ij,nj->ni',T[:3,:3],local)+T[:3,3]
    assert np.all(np.isfinite(v))
    actual=np.array([v.min(axis=0),v.max(axis=0)])*1000-np.array(source['head_face_world_mm'])
    error=float(np.max(abs(actual-np.array(wanted))))
    assert error<.20,(name,error)
    closed_errors.append(error)
drivers=[]
for ob in bpy.data.objects:
    if ob.animation_data:
        for fc in ob.animation_data.drivers:
            d=fc.driver
            assert d.is_valid,(ob.name,fc.data_path)
            assert d.is_simple_expression,(ob.name,d.expression)
            drivers.append(dict(object=ob.name,path=fc.data_path,array_index=fc.array_index,expression=d.expression,valid=d.is_valid,simple=d.is_simple_expression))
assert len(drivers)==27,len(drivers)
assert not bpy.app.autoexec_fail
result=dict(revision=source['revision'],passed=True,
            reopened_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
            reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            python_autoexec_enabled=bpy.context.preferences.filepaths.use_scripts_auto_execute,
            handlers_required=False,drivers=drivers,arm_vertex_checks=len(errors),max_arm_vertex_error_mm=max(errors),
            independent_closed_CAD_checks=len(closed_errors),max_closed_bound_error_mm=max(closed_errors),
            file_resaved=False,manufacturing_release=False,
            warning=('Home/inspect/reach used only for transformation validation; reach has documented real shoulder collisions and must not be executed.' if source['revision']=='ARM-INTEGRATED-PREVIEW01' else 'Pose controls are geometric only. Consult the candidate-specific collision report; discrete checks do not qualify motion paths or hardware limits.'))
assert not result['python_autoexec_enabled']
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(result,indent=2)+'\n')
print('Reopened native blend:',len(drivers),'simple-expression drivers;',len(errors),'arm checks;',len(closed_errors),'closed CAD comparisons passed. No file modification.')
