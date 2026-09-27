# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Explicit hybrid model: real LINK56 solids, other baseline mass proxies.

Only LINK56 inertia is derived from CAD; the result is not a measured full-arm
inertia model. Consumers must retain the scope and provenance information.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import cadquery as cq
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from arm_screening import arm_parameters

ROOT=Path(__file__).resolve().parents[1]


def link56_bodies():
    folder=ROOT/'engineering/generated/link56-study'
    placements_path=folder/'part-placements.json';placements=json.loads(placements_path.read_text())
    evidence_path=folder/'evidence.json';e=json.loads(evidence_path.read_text())
    bodies=[];hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [placements_path,evidence_path]}
    for instance,entry in placements['instances'].items():
        path=folder/(entry['part_id']+'.step');digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==e['export_checks'][entry['part_id']]['sha256'][path.name]
        shape=cq.importers.importStep(str(path)).val();assert shape.isValid() and len(shape.Solids())==1
        props=GProp_GProps();BRepGProp.VolumeProperties_s(shape.wrapped,props)
        density_kg_mm3=2.7e-6;m=props.Mass()*density_kg_mm3
        com=props.CentreOfMass();local=np.array([com.X(),com.Y(),com.Z()]);T=np.array(entry['T_world_from_part_mm'])
        world=(T@np.r_[local,1.])[:3];tensor=props.MatrixOfInertia()
        inertia=np.array([[tensor.Value(i,j) for j in [1,2,3]] for i in [1,2,3]])*density_kg_mm3*1e-6
        assert np.max(abs(world-entry['estimated_COM_world_mm']))<1e-7
        assert abs(m-entry['mass_kg_6061'])<1e-9
        assert np.linalg.eigvalsh(inertia).min()>0
        bodies.append({'id':'L56_'+instance,'mass_kg':m,'preceding_joints':5,
                       'com_home_m':(world*.001).tolist(),'orientation_home':T[:3,:3].tolist(),
                       'inertia_com_kg_m2':inertia.tolist(),'mass_source':str(path.relative_to(ROOT)),
                       'material_assumption':'homogeneous 6061 at 2700 kg/m3; thread helix omitted'})
        hashes[str(path.relative_to(ROOT))]=digest
    mass=sum(b['mass_kg'] for b in bodies);com=sum(b['mass_kg']*np.array(b['com_home_m']) for b in bodies)/mass
    # Hardware locations are not all frozen. Place an explicit 100 g reserve at
    # the metal COM; the small cube inertia is a placeholder, not CAD evidence.
    bodies.append({'id':'L56_fasteners_wiring_reserve','mass_kg':.1,'preceding_joints':5,
        'com_home_m':com.tolist(),'orientation_home':np.eye(3).tolist(),
        'inertia_com_kg_m2':(np.eye(3)*.1*.05**2/6).tolist(),
        'mass_source':'unweighed 0.1 kg reserve at metal COM; 50 mm cube inertia proxy'})
    info={'original_metal_kg':mass,'reserve_kg':.1,'replacement_mass_kg':mass+.1,
          'metal_COM_home_mm':(com*1000).tolist(),'input_hashes':hashes,
          'reserve_inertia_is_proxy':True,'replaces':'L5_budget'}
    return bodies,info


def candidate_model(p,head_mass,head_offset_mm=(0,0,0)):
    model=arm_parameters(p,head_mass);bodies,info=link56_bodies()
    model['bodies']=[b for b in model['bodies'] if b['id']!='L5_budget']+bodies
    head=next(b for b in model['bodies'] if b['id']=='head_budget')
    head['com_home_m']=(np.asarray(head['com_home_m'])+np.asarray(head_offset_mm)*.001).tolist()
    return model,info

if __name__=='__main__':
    b,i=link56_bodies();print(json.dumps({'bodies':b,'provenance':i},indent=2))
