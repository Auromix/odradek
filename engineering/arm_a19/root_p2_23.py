# SPDX-License-Identifier: CC-BY-NC-4.0
"""Quadratic displacement refinement with consistent distributed wrench loads."""
from pathlib import Path
import json,sys
import numpy as np
import meshio
from scipy.sparse.linalg import splu
from skfem import MeshTet,Basis,FacetBasis,ElementVector,ElementTetP2,asm,LinearForm
from skfem.helpers import dot
from skfem.models.elasticity import linear_elasticity,lame_parameters
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/root22'
sys.path.insert(0,str(ROOT/'engineering/arm_a16'));import common as c

def solve(size,d):
    path=OUT/f'root17-mesh-{size:g}.msh';data=meshio.read(path);m=MeshTet(data.points.T,data.cells_dict['tetra'].T).oriented()
    e=ElementVector(ElementTetP2());basis=Basis(m,e,intorder=4);lam,mu=lame_parameters(d['material']['E_MPa'],d['material']['poisson_assumption'])
    K=asm(linear_elasticity(lam,mu),basis).tocsc();bd=m.boundary_facets();centre=m.p[:,m.facets[:,bd]].mean(axis=1).T
    support=[]
    for x in [-38,38]:
        for y in [-28,28]:
            patch=bd[(abs(centre[:,2]-30)<1e-5)&(np.linalg.norm(centre[:,:2]-[x,y],axis=1)<6.5)];assert len(patch)>0;support.extend(patch)
    D=basis.get_dofs(facets=np.unique(support)).all();free=np.setdiff1d(np.arange(basis.N),D);lu=splu(K[free][:,free])
    motor=bd[(abs(centre[:,1]-68.5)<1e-5)&(np.linalg.norm(centre[:,[0,2]]-[0,114],axis=1)>39.99)&(np.linalg.norm(centre[:,[0,2]]-[0,114],axis=1)<67.01)]
    fb=FacetBasis(m,e,facets=motor,intorder=4);origin=np.array(d['mount_origin_J1_rotor_mm']);components=basis.split_indices();xyz=basis.doflocs[:,components[0]].T
    def wrench(vector):
        forces=np.column_stack([vector[z] for z in components]);return np.r_[forces.sum(axis=0),np.cross(xyz-origin,forces).sum(axis=0)]
    loads=[]
    for i in range(6):
        axis=np.eye(3)[i%3]
        @LinearForm
        def traction(v,w):
            force=np.broadcast_to(axis[:,None,None],w.x.shape) if i<3 else np.moveaxis(np.cross(np.moveaxis(np.broadcast_to(axis[:,None,None],w.x.shape),0,-1),np.moveaxis(w.x-origin[:,None,None],0,-1)),-1,0)
            return dot(force,v)
        loads.append(asm(traction,fb))
    B=np.array(loads).T;G=np.column_stack([wrench(F) for F in loads]);results=[]
    for case in d['gravity_load_cases']:
        target=np.r_[case['force_N'],case['moment_Nmm']];F=B@np.linalg.solve(G,target);assert np.max(abs(wrench(F)-target))<1e-7
        u=np.zeros(basis.N);u[free]=lu.solve(F[free]);R=K@u-F;balance=np.max(abs(wrench(R)+target));residual=np.linalg.norm(R[free])/np.linalg.norm(F);assert balance<1e-5 and residual<1e-7
        grad=basis.interpolate(u).grad;eps=(grad+grad.swapaxes(0,1))/2;stress=2*mu*eps+lam*np.eye(3)[:,:,None,None]*np.einsum('iieq->eq',eps)
        dev=stress-np.eye(3)[:,:,None,None]*np.einsum('iieq->eq',stress)[None,None]/3;vm=np.sqrt(1.5*np.sum(dev*dev,axis=(0,1)))
        energy=float(np.sum(.5*np.sum(stress*eps,axis=(0,1))*basis.dx));matrix_energy=float(.5*u@(K@u));assert abs(energy-matrix_energy)/matrix_energy<1e-8
        disp=np.linalg.norm(np.column_stack([u[z] for z in components]),axis=1)
        results.append(dict(case=case['id'],maximum_all_dof_displacement_mm=float(max(disp)),strain_energy_Nmm=energy,max_quadrature_VM_MPa=float(vm.max()),reaction_balance_max_abs=float(balance),free_residual_norm_ratio=float(residual)))
    return dict(target_mesh_size_mm=size,mesh_sha256=c.sha(path),vertices=int(m.nvertices),tetrahedra=int(m.nelements),quadratic_displacement_DOFs=int(basis.N),geometric_mesh='straight-sided tetrahedra from exact BREP boundary tessellation; displacement quadratic, not quadratic geometry',cases=results)

def main():
    path=OUT/'manifest.json';d=json.loads(path.read_text());linear=json.loads((OUT/'linear-fea18.json').read_text());assert linear['source_manifest_sha256']==c.sha(path)
    records=[]
    for size in [4,3]:
        result=solve(size,d);records.append(result);(OUT/f'quadratic23-mesh-{size}.json').write_text(json.dumps(result,indent=2)+'\n');print('ROOT_P2',size,[(r['maximum_all_dof_displacement_mm'],r['strain_energy_Nmm']) for r in result['cases']],flush=True)
    change=[dict(case=b['case'],displacement_change_fraction=abs(b['maximum_all_dof_displacement_mm']-a['maximum_all_dof_displacement_mm'])/b['maximum_all_dof_displacement_mm'],energy_change_fraction=abs(b['strain_energy_Nmm']-a['strain_energy_Nmm'])/b['strain_energy_Nmm']) for a,b in zip(records[0]['cases'],records[1]['cases'])]
    report=dict(revision='A19-ROOT23-P2-SCREEN',source_manifest_sha256=c.sha(path),material=d['material'],meshes=records,refinement=change,boundary='Same four rigid bottom washer patches. Consistent surface integration of linear traction fields on motor annulus, coefficient solve imposes exact six-component wrench. All quadratic edge DOFs included in clamp/load integration.',production_release=False,limits=linear['limits']+['Refinement is not a bolt/contact/preload or foundation validation; singular peak stress not accepted as yield/fatigue qualification.'])
    (OUT/'quadratic23.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
