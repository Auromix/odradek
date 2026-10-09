# SPDX-License-Identifier: CC-BY-NC-4.0
"""A16 conventional assembly datums, millimetres. Not a rated product."""
from pathlib import Path
import copy, hashlib, json, sys
import numpy as np
import cadquery as cq
from OCP.gp import gp_Trsf

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).parent
BASE=ROOT.parent/'odradek'
OUT=HERE/'build'
CACHE=ROOT/'work/arm-a16'
sys.path.insert(0,str(ROOT/'engineering/arm_a08'))
import build as cad
SRC=json.loads((ROOT/'docs/engineering/sources/arm-a05-mechanical-sources.json').read_text())
L=copy.deepcopy(json.loads((ROOT/'engineering/arm_a15/shoulder01/build/study.json').read_text())['layout'])
L['id']='A16-CONVENTIONAL02-FLAT-WRIST'
L['joints'][0].update(offset=[0,0,165],motor_center=[0,0,-28.3],length_mm=56.6)
L['joints'][1].update(length_mm=55.7)
L['joints'][1]['offset']=[0,0,114]
L['joints'][1]['motor_center']=[0,94.35,0]
L['joints'][2].update(motor_center=[1.5,0,0])
L['joints'][3].update(motor_center=[0,1.5,0])
L['joints'][4].update(motor_center=[0,70.3,0])
L['joints'][5].update(motor_center=[0,0,0],offset=[55,0,0])
L['joints'][6].update(length_mm=51.4,offset=[75,0,0])
L['mass_assumption']='2026.09.17 catalogue nominal motor masses; geometric midpoint COM proxies, not measured internal mass split.'
L['root_transform_mm']=[[0,-1,0,0],[1,0,0,75],[0,0,1,0],[0,0,0,1]]
L['status']='supported unpowered fit prototype; entire assembly and load qualification pending'
L.pop('shoulder_cross_adapter',None);L.pop('wrist_cross_adapter',None)
L['pedestal']={'mount_plane_z_mm':58,'adapter_od_mm':134,'bore_mm':56,'J1_axis_z_mm':165}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def base_context():
    h=json.loads((BASE/'engineering/base_b06/arm-handoff.json').read_text())
    for v in h['sources'].values():
        assert sha(BASE/v['path'])==v['sha256'],v['path']
    return dict(base_revision=h['base_revision'],base_native_sha256=h['sources']['native']['sha256'],
      base_manifest_sha256=h['sources']['manifest']['sha256'],base_interface_contract_sha256=h['sources']['interface']['sha256'],
      base_priority=True,canonical_checkout='../odradek',base_sources=h['sources'],
      integration_status={'source_sync':'fingerprints verified; native inclusion checked separately','assembly':'pending','wiring':'pending','loads':'pending'})

def transform(s,T):
    t=gp_Trsf();t.SetValues(*map(float,np.asarray(T)[:3,:].flatten()));return s.transformShape(cq.Matrix(t))

def frames(q):
    T=np.array(L['root_transform_mm'],float);f={'world':T.copy()}
    for j,x in zip(L['joints'],q):
        O=np.eye(4);O[:3,3]=j['offset'];T=T@O;f[j['id']+'.fixed']=T.copy()
        a=np.array(j['axis'],float);a/=np.linalg.norm(a);h=np.radians(x+j['zero_deg']);K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
        R=np.eye(4);R[:3,:3]=np.cos(h)*np.eye(3)+(1-np.cos(h))*np.outer(a,a)+np.sin(h)*K
        T=T@R;f[j['id']+'.rotor']=T.copy()
    return f

OUT.mkdir(exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
