# SPDX-License-Identifier: CC-BY-NC-4.0
"""Linear-elastic shoulder-foot screening, not a bolted-joint qualification.

N-mm-MPa units. Actual R6 BREP, three independently generated T4 meshes,
area-weighted minimum-norm nodal wrench with exact six-component equilibrium.
Four rigid washer support patches are an explicitly idealised boundary.
"""
from pathlib import Path
import json,sys
import numpy as np
import gmsh
from scipy.sparse.linalg import splu
from skfem import MeshTet,Basis,ElementTetP1,ElementVector,asm
from skfem.models.elasticity import linear_elasticity,lame_parameters
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/root17'
sys.path.insert(0,str(ROOT/'engineering/arm_a16'));import common as c
if '--gusset' in sys.argv:OUT=HERE/'build/root17-gusset'
if '--thick' in sys.argv:OUT=HERE/'build/root22'

def mesh(path,size):
    gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
    gmsh.model.add('root17');gmsh.model.occ.importShapes(str(path));gmsh.model.occ.synchronize()
    assert len(gmsh.model.getEntities(3))==1
    gmsh.option.setNumber('Mesh.MeshSizeMax',size);gmsh.option.setNumber('Mesh.MeshSizeMin',size*.55)
    gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',12);gmsh.option.setNumber('Mesh.ElementOrder',1)
    gmsh.model.mesh.generate(3);gmsh.model.mesh.optimize('Netgen')
    tags,coords,_=gmsh.model.mesh.getNodes();xyz=np.array(coords).reshape(-1,3);index={int(t):i for i,t in enumerate(tags)}
    typ,_,conn=gmsh.model.mesh.getElements(3);assert list(typ)==[4]
    cells=np.array([index[int(t)] for t in conn[0]]).reshape(-1,4)
    gmsh.write(str(OUT/f'root17-mesh-{size:g}.msh'));gmsh.finalize()
    m=MeshTet(xyz.T,cells.T).oriented();return m

def areas(m,facets):
    tri=m.p[:,m.facets[:,facets]];return np.linalg.norm(np.cross((tri[:,1]-tri[:,0]).T,(tri[:,2]-tri[:,0]).T),axis=1)/2

def solve(m,d):
    basis=Basis(m,ElementVector(ElementTetP1()));lam,mu=lame_parameters(d['material']['E_MPa'],d['material']['poisson_assumption'])
    K=asm(linear_elasticity(lam,mu),basis).tocsc();bound=m.boundary_facets();cent=m.p[:,m.facets[:,bound]].mean(axis=1).T
    # Fixed support annuli beneath four ordinary M5 bolt/washer stations.
    bottom=abs(cent[:,2]-30)<1e-5;patches=[]
    for x in [-38,38]:
        for y in [-28,28]:
            patch=bound[bottom & (np.linalg.norm(cent[:,:2]-[x,y],axis=1)<6.5)]
            assert len(patch)>0;patches.append(patch)
    support=np.unique(m.facets[:,np.concatenate(patches)])
    D=np.sort(basis.nodal_dofs[:,support].ravel());free=np.setdiff1d(np.arange(basis.N),D)
    lu=splu(K[free][:,free]);origin=np.array(d['mount_origin_J1_rotor_mm'])
    motor=bound[(abs(cent[:,1]-68.5)<1e-5)&(np.linalg.norm(cent[:,[0,2]]-[0,114],axis=1)<67.01)&(np.linalg.norm(cent[:,[0,2]]-[0,114],axis=1)>39.99)]
    assert len(motor)>20
    nodes=np.unique(m.facets[:,motor]);weights=np.zeros(m.nvertices)
    for facet,area in zip(m.facets[:,motor].T,areas(m,motor)):weights[facet]+=area/3
    nodes=nodes[weights[nodes]>0];weights=weights[nodes];xyz=m.p[:,nodes].T-origin
    A=np.zeros((6,3*len(nodes)))
    for i,(x,y,z) in enumerate(xyz):
        A[:3,3*i:3*i+3]=np.eye(3);A[3:,3*i:3*i+3]=[[0,-z,y],[z,0,-x],[-y,x,0]]
    W=np.repeat(weights,3);result=[]
    cg=m.p[:,m.t].mean(axis=1).T;near=np.zeros(m.nelements,bool)
    for x in [-38,38]:
        for y in [-28,28]:near|=np.linalg.norm(cg-[x,y,30],axis=1)<10
    X=m.p[:,m.t];vol=abs(np.linalg.det(np.moveaxis(X[:,1:]-X[:,:1],-1,0)))/6
    assert np.min(vol)>0
    for case in d['gravity_load_cases']:
        wrench=np.r_[case['force_N'],case['moment_Nmm']]
        nodal=(W[:,None]*A.T)@np.linalg.solve((A*W)@A.T,wrench)
        assert np.max(abs(A@nodal-wrench))<1e-7
        F=np.zeros(basis.N);F[basis.nodal_dofs[:,nodes].T.ravel()]=nodal
        u=np.zeros(basis.N);u[free]=lu.solve(F[free]);reactions=K@u-F
        rn=reactions[basis.nodal_dofs].T
        reaction_wrench=np.r_[rn.sum(axis=0),np.cross(m.p.T-origin,rn).sum(axis=0)]
        assert np.max(abs(reaction_wrench+wrench))<1e-5
        residual=np.linalg.norm(reactions[free])/max(np.linalg.norm(F),1e-12)
        assert residual<1e-7,(case['id'],residual)
        grad=basis.interpolate(u).grad;eps=(grad+grad.swapaxes(0,1))/2
        trace=np.einsum('iieq->eq',eps);stress=2*mu*eps+lam*np.eye(3)[:,:,None,None]*trace
        dev=stress-np.eye(3)[:,:,None,None]*np.einsum('iieq->eq',stress)[None,None]/3
        vm=np.sqrt(1.5*np.sum(dev*dev,axis=(0,1))).mean(axis=-1)
        disp=np.linalg.norm(u[basis.nodal_dofs],axis=0)
        # T4 cell stress and strain are constant. Energy supplies a second
        # independent integral check, alongside reactions and mesh volume.
        strain_energy=.5*np.sum(stress*eps,axis=(0,1)).mean(axis=-1)@vol
        matrix_energy=.5*u@(K@u);assert abs(strain_energy-matrix_energy)/matrix_energy<1e-8
        result.append(dict(case=case['id'],force_N=case['force_N'],moment_Nmm=case['moment_Nmm'],max_displacement_mm=float(max(disp)),mount_max_displacement_mm=float(max(disp[nodes])),max_T4_cell_VM_MPa=float(max(vm)),max_VM_outside_support_10mm_MPa=float(max(vm[~near])),cell_VM_99_percentile_MPa=float(np.quantile(vm,.99)),strain_energy_Nmm=float(strain_energy),reaction_wrench_N_Nmm=reaction_wrench.tolist(),reaction_balance_max_abs=float(np.max(abs(reaction_wrench+wrench))),free_residual_norm_ratio=float(residual)))
    return dict(vertices=m.nvertices,tetrahedra=m.nelements,DOFs=basis.N,volume_mm3=float(sum(vol)),support_nodes=len(support),support_patch_facets=[len(p) for p in patches],load_nodes=len(nodes),load_area_mm2=float(sum(weights)),cases=result)

def main():
    source=OUT/'manifest.json';d=json.loads(source.read_text());step=ROOT/d['step_path'];assert c.sha(step)==d['step_sha256']
    records=[]
    for size in [4,3,2]:
        m=mesh(step,size);result=solve(m,d);result['target_mesh_size_mm']=size
        result['volume_relative_error']=abs(result['volume_mm3']-d['volume_mm3'])/d['volume_mm3'];assert result['volume_relative_error']<.015
        records.append(result)
        (OUT/f'fea18-mesh-{size:g}.json').write_text(json.dumps(result,indent=2,default=lambda v:v.item())+'\n')
        print('ROOT_FEA',size,result['vertices'],[(p['mount_max_displacement_mm'],p['max_T4_cell_VM_MPa']) for p in result['cases']],flush=True)
    changes=[]
    for a,b in zip(records,records[1:]):
        changes.append(dict(from_mm=a['target_mesh_size_mm'],to_mm=b['target_mesh_size_mm'],mount_displacement_change_fraction=[abs(y['mount_max_displacement_mm']-x['mount_max_displacement_mm'])/y['mount_max_displacement_mm'] for x,y in zip(a['cases'],b['cases'])],energy_change_fraction=[abs(y['strain_energy_Nmm']-x['strain_energy_Nmm'])/y['strain_energy_Nmm'] for x,y in zip(a['cases'],b['cases'])]))
    report=dict(revision='A19-ROOT18-LINEAR-SCREEN',source_manifest_sha256=c.sha(source),step_sha256=c.sha(step),material=d['material'],meshes=records,refinement=changes,boundary='Four bottom washer patches fully fixed to ideal rigid support; whole annular motor face loaded by area-weighted least-norm wrench. No bolt preload/contact/slip, foundation flexibility or anisotropy.',production_release=False,limits=['Static A18 gravity load cases only; new J5, spring attachment, collisions, dynamics and fatigue not included.','Do not use maximum singular support-edge stress as a converged material acceptance. T4 refinement and integral checks are reported, not production qualification.','Actual print and metal samples, material certificate, fastener preload/contact, machined tolerances and load testing are required.'])
    (OUT/'linear-fea18.json').write_text(json.dumps(report,indent=2,default=lambda v:v.item())+'\n')
if __name__=='__main__':main()
