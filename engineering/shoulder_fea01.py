#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent ideal-boundary small-strain elasticity comparison. No strength release."""
from pathlib import Path
import argparse,hashlib,json,time,math
import numpy as np
import scipy,scipy.sparse as sp
from scipy.sparse.linalg import spsolve,cg
import skfem,pyamg,meshio,gmsh
from skfem import MeshTet,Basis,FacetBasis,ElementVector,ElementTetP2,LinearForm,asm
from skfem.helpers import dot,sym_grad
from skfem.models.elasticity import linear_elasticity,lame_parameters,linear_stress
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/shoulder-fea01'
NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)';REV='SHOULDER-FEA01'
E=70000.;NU=.33
RAW=ROOT.parents[1]/'work/shoulder-fea01-raw'
RAW.mkdir(parents=True,exist_ok=True)
def rawpath(name):return RAW/name if (RAW/name).exists() else OUT/name

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def native(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,(np.floating,np.integer,np.bool_)):return x.item()
 raise TypeError(type(x).__name__)
def dump(n,d):OUT.mkdir(parents=True,exist_ok=True);(OUT/n).write_text(json.dumps(d,indent=2,default=native)+'\n')
def oriented_mesh(points,tets):
 p=np.asarray(points,float);t=np.asarray(tets,np.int32);J=np.stack([p[t[:,i]]-p[t[:,0]] for i in [1,2,3]],axis=-1);det=np.linalg.det(J);neg=det<0;t[neg,1],t[neg,2]=t[neg,2].copy(),t[neg,1].copy();return MeshTet(p.T,t.T,sort_t=False)
def mesh_quality(m):
 x=m.p.T[m.t.T];D=np.linalg.det(np.stack([x[:,i]-x[:,0] for i in [1,2,3]],axis=-1));assert min(D)>0
 V=D/6;edge2=sum(np.sum((x[:,i]-x[:,j])**2,axis=1) for i in range(4) for j in range(i));quality=12*(3*V)**(2/3)/edge2
 return dict(nodes=m.nvertices,tetrahedra=m.nelements,min_jacobian_determinant_mm3=float(min(D)),min_volume_mm3=float(min(V)),mesh_volume_mm3=float(sum(V)),mean_ratio_min=float(min(quality)),mean_ratio_percentiles=np.percentile(quality,[1,5,50,95,99]).tolist(),nonpositive_elements=0)
def basis_and_matrix(m,Evalue=E):
 b=Basis(m,ElementVector(ElementTetP2()),intorder=4);K=asm(linear_elasticity(*lame_parameters(Evalue,NU)),b).tocsr();diff=K-K.T;err=max(abs(diff.data)) if diff.nnz else 0.;assert err/max(abs(K.data))<1e-12
 return b,K,dict(dofs=b.N,order=2,quadrature_order=4,geometry_order=1,stiffness_symmetry_relative_error=err/max(abs(K.data)))
def rigid_modes(b):
 B=np.zeros((b.N,6));indices=b.split_indices();p=b.doflocs[:,indices[0]].T;p-=p.mean(axis=0)
 for c in range(3):B[indices[c],c]=1
 for axis in range(3):
  u=np.cross(np.eye(3)[axis],p)
  for c in range(3):B[indices[c],axis+3]=u[:,c]
 return B

def solver(K,b,D):
 free=np.setdiff1d(np.arange(b.N),D);A=K[free][:,free].tocsr();B=rigid_modes(b)[free]
 if len(free)<24000:
  from scipy.sparse.linalg import splu
  lu=splu(A.tocsc());return free,lambda r:(lu.solve(r),dict(method='SuperLU',iterations=None))
 ml=pyamg.smoothed_aggregation_solver(A,B=B,symmetry='symmetric',max_coarse=600);M=ml.aspreconditioner(cycle='V')
 def solve(r):
  count=[0]
  def cb(x):count[0]+=1
  x,info=cg(A,r,rtol=2e-10,atol=0.,M=M,maxiter=2000,callback=cb);assert info==0,('CG',info,count);return x,dict(method='CG+smoothed-aggregation AMG sixrigid modes',iterations=count[0],AMG_levels=len(ml.levels))
 return free,solve

def dof_resultant(b,f,origin):
 idx=b.split_indices();forces=np.column_stack([f[i] for i in idx]);x=b.doflocs[:,idx[0]].T-np.array(origin);return forces.sum(axis=0),np.cross(x,forces).sum(axis=0)
def surface_wrench(b,facets,F,M,origin):
 fb=FacetBasis(b.mesh,b.elem,facets=facets,intorder=4,dofs=b.dofs);x=np.asarray(fb.global_coordinates());w=fb.dx;A=w.sum();c=(x*w[None]).sum(axis=(1,2))/A;r=x-c[:,None,None];Q=np.einsum('ifq,jfq,fq->ij',r,r,w);polar=np.trace(Q)*np.eye(3)-Q;a=np.asarray(F)/A;correctedM=np.asarray(M)+np.cross(np.asarray(origin)-c,np.asarray(F));omega=np.linalg.solve(polar,correctedM)
 @LinearForm
 def traction(v,w):
  rr=w.x-c[:,None,None];t=a[:,None,None]+np.moveaxis(np.cross(omega,np.moveaxis(rr,0,-1)), -1,0);return dot(t,v)
 f=asm(traction,fb);ff,mm=dof_resultant(b,f,origin);assert np.linalg.norm(ff-F)<1e-8*max(np.linalg.norm(F),1);assert np.linalg.norm(mm-M)<1e-8*max(np.linalg.norm(M),1)
 return f,dict(area_mm2=float(A),centroid_world_mm=c,area_second_moment_mm4=Q,traction_constant_N_mm2=a,traction_rotation_coefficient_N_mm3=omega,assembled_force_N=ff,assembled_moment_Nmm=mm,force_error_N=float(np.linalg.norm(ff-F)),moment_error_Nmm=float(np.linalg.norm(mm-M)),face_count=len(facets)),fb

def solve_case(b,K,free,solve,D,f,origin,prescribed=None):
 u=np.zeros(b.N)
 if prescribed is not None:u[D]=np.asarray(prescribed)[D]
 rhs=f[free]-K[free]@u;x,info=solve(rhs);u[free]+=x;reaction=K@u-f;res=float(np.linalg.norm(reaction[free])/max(np.linalg.norm(f[free]),np.linalg.norm((K@u)[free]),1.));assert res<1e-7,(res,info)
 force,moment=dof_resultant(b,np.where(np.isin(np.arange(b.N),D),reaction,0),origin);af,am=dof_resultant(b,f,origin);length=max(np.linalg.norm(np.ptp(b.mesh.p,axis=1)),1.);force_scale=max(np.linalg.norm(af),np.linalg.norm(am)/length,1.);moment_scale=max(np.linalg.norm(am),np.linalg.norm(af)*length,1.);assert np.linalg.norm(force+af)<1e-6*force_scale;assert np.linalg.norm(moment+am)<1e-6*moment_scale
 energy=.5*float(u@(K@u));external=float(u@f+u[D]@reaction[D]);assert abs(2*energy-external)<1e-7*max(abs(external),1)
 return u,dict(**info,free_residual_relative=res,reaction_force_N=force,reaction_moment_Nmm=moment,force_balance_error_N=float(np.linalg.norm(force+af)),moment_balance_error_Nmm=float(np.linalg.norm(moment+am)),force_balance_normalized=float(np.linalg.norm(force+af)/force_scale),moment_balance_normalized=float(np.linalg.norm(moment+am)/moment_scale),balance_length_scale_mm=length,strain_energy_Nmm=energy,total_external_work_Nmm=external,energy_balance_relative_error=abs(2*energy-external)/max(abs(external),1))

def stress_metrics(b,u):
 uh=b.interpolate(u);eps=sym_grad(uh);sig=linear_stress(*lame_parameters(E,NU))(eps);tr=np.einsum('iieq->eq',sig);dev=sig-np.eye(3)[:,:,None,None]*tr[None,None]/3;vm=np.sqrt(1.5*np.einsum('ijeq,ijeq->eq',dev,dev));weights=b.dx;avg=(vm*weights).sum(axis=1)/weights.sum(axis=1)
 return dict(von_mises_quadrature_max_MPa=float(vm.max()),element_mean_von_mises_MPa=avg,stress_tensor_quadrature_MPa=sig)
def vtu(name,m,b,u,cell_vm=None):
 scalar=Basis(m,ElementTetP2(),intorder=4);idx=b.split_indices();assert all(np.allclose(b.doflocs[:,i],scalar.doflocs) for i in idx);ud=np.column_stack([u[i] for i in idx]);assert np.allclose(ElementTetP2().doflocs,np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[.5,0,0],[.5,.5,0],[0,.5,0],[0,0,.5],[.5,0,.5],[0,.5,.5]]))
 data={} if cell_vm is None else {'mean_von_mises_MPa':[cell_vm]};meshio.write(RAW/name,meshio.Mesh(scalar.doflocs.T,[('tetra10',scalar.element_dofs.T)],point_data={'displacement_mm':ud,'displacement_norm_mm':np.linalg.norm(ud,axis=1)},cell_data=data),binary=True,compression='zlib')

def benchmarks():
 start=time.time();raw=MeshTet.init_tensor(np.linspace(0,10,4),np.linspace(0,8,4),np.linspace(0,6,4));m=oriented_mesh(raw.p.T,raw.t.T.copy());b,K,assembly=basis_and_matrix(m);D=b.get_dofs().all();free,solve=solver(K,b,D);eps=.001;u0=np.zeros(b.N);ids=b.split_indices()
 for c,factor in enumerate([eps,-NU*eps,-NU*eps]):u0[ids[c]]=factor*b.doflocs[c,ids[c]]
 u,qa=solve_case(b,K,free,solve,D,np.zeros(b.N),[0,0,0],u0.copy());err=float(max(abs(u-u0)));assert err<1e-9
 sig=stress_metrics(b,u)['stress_tensor_quadrature_MPa'];expected=np.zeros((3,3,1,1));expected[0,0]=E*eps;serr=float(np.max(abs(sig-expected)));assert serr<1e-6
 volume=mesh_quality(m)['mesh_volume_mm3'];expected_energy=.5*E*eps**2*volume;assert abs(qa['strain_energy_Nmm']/expected_energy-1)<1e-9
 # Independent mm/MPa versus m/Pa stiffness scaling on the same discretization.
 sm=oriented_mesh(m.p.T*.001,m.t.T.copy());sb,KS,sa=basis_and_matrix(sm,E*1e6);scale_error=float(np.linalg.norm((KS-1000*K).data)/np.linalg.norm((1000*K).data));assert scale_error<1e-12
 patch=dict(mesh=mesh_quality(m),assembly=assembly,solver=qa,affine_displacement_max_error_mm=err,constant_stress_max_error_MPa=serr,analytical_energy_Nmm=expected_energy,SI_vs_mm_stiffness_scaling_relative_error=scale_error);vtu('patch.vtu',m,b,u)
 beam=[];L=100.;h=10.;width=10.;F=100.;I=width*h**3/12;EB=F*L**3/(3*E*I);Timo=EB+F*L/((5/6)*(E/(2*(1+NU)))*width*h)
 for size in [5.,2.5,5/3]:
  raw=MeshTet.init_tensor(np.linspace(0,L,round(L/size)+1),np.linspace(0,width,round(width/size)+1),np.linspace(0,h,round(h/size)+1));m=oriented_mesh(raw.p.T,raw.t.T.copy());b,K,ass=basis_and_matrix(m);fixed=m.facets_satisfying(lambda x:np.isclose(x[0],0));loaded=m.facets_satisfying(lambda x:np.isclose(x[0],L));D=b.get_dofs(facets=fixed).all();free,solve=solver(K,b,D);f,load,fb=surface_wrench(b,loaded,[0,0,F],[0,0,0],[L,width/2,h/2]);u,qa=solve_case(b,K,free,solve,D,f,[L,width/2,h/2]);tip=float(f@u/F);stress=stress_metrics(b,u);r=dict(target_size_mm=size,mesh=mesh_quality(m),assembly=ass,load=load,solver=qa,work_conjugate_tip_displacement_mm=tip,Euler_Bernoulli_mm=EB,Timoshenko_reference_mm=Timo,relative_to_Timoshenko=tip/Timo-1,von_mises_quadrature_max_MPa=stress['von_mises_quadrature_max_MPa']);beam.append(r);vtu('beam-'+str(size)+'.vtu',m,b,u,stress['element_mean_von_mises_MPa']);print('BENCH beam',size,b.N,tip,Timo,flush=True)
 assert abs(beam[-1]['relative_to_Timoshenko'])<.03;change=abs(beam[-1]['work_conjugate_tip_displacement_mm']/beam[-2]['work_conjugate_tip_displacement_mm']-1);assert change<.02
 result=dict(revision=REV,license='CC-BY-NC-4.0',required_notice=NOTICE,units='mm,N,MPa,Nmm; SI crosscheck separatelym,N,Pa',material_nominal=dict(E_MPa=E,nu=NU,yield_MPa=None),versions=dict(gmsh=gmsh.__version__,skfem=skfem.__version__,scipy=scipy.__version__,numpy=np.__version__,pyamg=pyamg.__version__),patch=patch,beam=beam,beam_last_refinement_relative_change=change,elapsed_seconds=time.time()-start,generator_sha256=sha(__file__),limits='Patch verifies linear completeness and unit scaling. Cantilever has3Dclamp/end effects; EB/Timoshenko are reference solutions, not exact3D. No physical material/assembly/strength validation.');dump('benchmarks.json',result);print('BENCHMARK_READY',time.time()-start,flush=True)

ORIGIN=np.array([0.,-45.7,205.])
CASES={'Fz':([0,0,269.9137325096238],[0,0,0],269.9137325096238,'mm'),
       'Mx':([0,0,0],[100000,0,0],100000.,'rad'),
       'My':([0,0,0],[0,100000,0],100000.,'rad')}

def import_original(which):
 import cadquery as cq
 folder=ROOT/'engineering/generated'/('shoulder-raise-01' if which=='01' else 'shoulder-raise02');mp=folder/'part-placements.json';j=json.loads(mp.read_text());row=j['original_L12_instances']['rear_fork'] if which=='01' else j['instances']['L12_rear_fork'];p=folder/row['file'];assert sha(p)==row['sha256'];s=cq.importers.importStep(str(p)).val();T=np.array(row['T_world_from_part_mm']);assert np.allclose(T[:3,:3],np.eye(3));s=s.translate(tuple(T[:3,3]));assert s.isValid() and len(s.Solids())==1;assert abs(s.Volume()/row['volume_mm3']-1)<1e-8
 dst=OUT/('RAISE'+which+'-rear-fork-world.step')
 if not dst.exists():cq.exporters.export(s,str(dst))
 cached=cq.importers.importStep(str(dst)).val();assert abs(cached.Volume()/s.Volume()-1)<1e-8;assert np.linalg.norm(np.array(cached.Center().toTuple())-np.array(s.Center().toTuple()))<1e-6
 return dst,dict(source=str(p.relative_to(ROOT)),source_sha256=sha(p),placement_manifest=str(mp.relative_to(ROOT)),placement_manifest_sha256=sha(mp),T_world_from_part_mm=T,world_STEP_sha256_at_mesh_generation=sha(dst),CAD_volume_mm3=s.Volume(),nominal_mass_kg=row['mass_kg'])

def cadmesh(which,size,support="full"):
 step,source=import_original(which);gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.model.add('RAISE'+which);occ=gmsh.model.occ;volumes=occ.importShapes(str(step));assert len(volumes)==1 and volumes[0][0]==3
 # Explicit ideal annulus, not a claim that the complete patch is actual OEM contact.
 outer=occ.addDisk(0,0,0,54.7,54.7);inner=occ.addDisk(0,0,0,47.7,47.7);holes=[]
 for deg in [30,60,120,150,210,240,300,330]:
  a=math.radians(deg);holes.append((2,occ.addDisk(51*math.cos(a),51*math.sin(a),0,2.25,2.25)))
 mask,_=occ.cut([(2,outer)],[(2,inner)]+holes);assert len(mask)==1;occ.rotate(mask,0,0,0,1,0,0,-math.pi/2);occ.translate(mask,*ORIGIN)
 post_masks=[]
 if support=='posts':
  for x,y in [(57,-52),(-57,-52),(-57,-26),(57,-26)]:
   disk=occ.addDisk(x,y,127.2,8,8);hole=occ.addDisk(x,y,127.2,3.3,3.3);patch,_=occ.cut([(2,disk)],[(2,hole)]);assert len(patch)==1;post_masks+=patch
 result,mapping=occ.fragment(volumes,mask+post_masks);occ.synchronize();vols=gmsh.model.getEntities(3);assert len(vols)==1;vol=vols[0];boundary=set(gmsh.model.getBoundary(vols,oriented=False));load=[t for d,t in mapping[1] if d==2 and (d,t) in boundary];assert len(load)>0
 fixed=[]
 for d,t in boundary:
  bb=gmsh.model.getBoundingBox(d,t)
  if abs(bb[2]-127.2)<1e-5 and abs(bb[5]-127.2)<1e-5:fixed.append(t)
 assert len(fixed)>=2,(fixed,load)
 if support=='posts':
  fixed=[t for entry in mapping[2:] for d,t in entry if d==2 and (d,t) in boundary];assert len(fixed)==4
 volume=occ.getMass(*vol);assert abs(volume/source['CAD_volume_mm3']-1)<1e-8
 for tags,dim,name,tag in [(load,2,'IDEAL_LOAD_ANNULUS',1),(fixed,2,'FOOT_'+support.upper()+'_FIXED',2),([vol[1]],3,'ORIGINAL_ALUMINIUM_FORK',3)]:gmsh.model.addPhysicalGroup(dim,tags,tag);gmsh.model.setPhysicalName(dim,tag,name)
 gmsh.option.setNumber('Mesh.MeshSizeMax',size);gmsh.option.setNumber('Mesh.MeshSizeMin',size/10);gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',16);gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',1);gmsh.option.setNumber('Mesh.Algorithm3D',1);gmsh.option.setNumber('Mesh.Optimize',1);gmsh.option.setNumber('Mesh.OptimizeNetgen',1);gmsh.option.setNumber('Mesh.ElementOrder',1);gmsh.option.setNumber('General.NumThreads',4)
 gmsh.model.mesh.setSize(gmsh.model.getEntities(0),size)
 if support=='posts':
  # Resolve the identical small support annuli explicitly; do not allow16-segment circles to remove2.5% support area.
  curves={t for d,t in gmsh.model.getBoundary([(2,t) for t in fixed],oriented=False) if d==1}
  for tag in curves:gmsh.model.mesh.setTransfiniteCurve(tag,max(3,math.ceil(occ.getMass(1,tag)/.75)+1))
 gmsh.model.mesh.generate(3)
 nodetags,coords,_=gmsh.model.mesh.getNodes();coords=np.array(coords).reshape(-1,3);types,etags,enodes=gmsh.model.mesh.getElements(3,vol[1]);assert list(types)==[4];tetnodes=np.array(enodes[0]).reshape(-1,4);used=np.unique(tetnodes);tag_to_row={int(t):i for i,t in enumerate(nodetags)};tag_to_used={int(t):i for i,t in enumerate(used)};points=coords[[tag_to_row[int(t)] for t in used]];tets=np.array([[tag_to_used[int(t)] for t in row] for row in tetnodes]);m=oriented_mesh(points,tets)
 boundary_facets=m.boundary_facets();lookup={tuple(sorted(m.facets[:,f])):f for f in boundary_facets}
 def surface_facets(tags):
  fs=[]
  for tag in tags:
   ty,_,ns=gmsh.model.mesh.getElements(2,tag);assert list(ty)==[2]
   for row in np.array(ns[0]).reshape(-1,3):fs.append(lookup[tuple(sorted(tag_to_used[int(t)] for t in row))])
  return np.array(sorted(set(fs)),dtype=np.int32)
 fixedfacets=surface_facets(fixed);loadfacets=surface_facets(load);qual=mesh_quality(m);qual['CAD_volume_relative_error']=qual['mesh_volume_mm3']/volume-1
 meshname=f'RAISE{which}-h{size:g}'+('-posts' if support=='posts' else '')+'.msh';gmsh.option.setNumber('Mesh.Binary',1);gmsh.write(str(RAW/meshname));areas=dict(load_CAD_area_mm2=sum(occ.getMass(2,t) for t in load),fixed_CAD_area_mm2=sum(occ.getMass(2,t) for t in fixed),load_surface_entity_ids=load,fixed_surface_entity_ids=fixed);gmsh.finalize()
 return m,fixedfacets,loadfacets,dict(source=source,mesh=qual,raw_mesh=meshname,raw_mesh_sha256=sha(rawpath(meshname)),**areas)

def actual(which,size,support="full"):
 start=time.time();m,fixed,loaded,metadata=cadmesh(which,size,support);print('MESH_READY',which,size,m.nvertices,m.nelements,metadata['mesh']['CAD_volume_relative_error'],flush=True);b,K,ass=basis_and_matrix(m);print('ASSEMBLY_READY',which,size,b.N,K.nnz,flush=True);D=b.get_dofs(facets=fixed).all();free,solve=solver(K,b,D);print('PRECONDITIONER_READY',which,size,flush=True);fixedarea=FacetBasis(m,b.elem,facets=fixed,intorder=4,dofs=b.dofs).dx.sum();results={};forces=[];solutions=[]
 for name,(F,M,scale,unit) in CASES.items():
  f,load,fb=surface_wrench(b,loaded,F,M,ORIGIN);u,qa=solve_case(b,K,free,solve,D,f,ORIGIN);stress=stress_metrics(b,u);filename=f'RAISE{which}-h{size:g}'+('-posts' if support=='posts' else '')+f'-{name}.vtu';vtu(filename,m,b,u,stress['element_mean_von_mises_MPa']);response=float(f@u/scale);results[name]=dict(load=load,solver=qa,work_conjugate_response=response,response_unit=unit,max_displacement_norm_mm=float(np.linalg.norm(np.column_stack([u[i] for i in b.split_indices()]),axis=1).max()),von_mises_quadrature_max_MPa=stress['von_mises_quadrature_max_MPa'],result_vtu=filename,result_sha256=sha(rawpath(filename)));forces.append(f/scale);solutions.append(u/scale);print('SOLVED',which,size,name,response,qa['iterations'],flush=True)
 compliance=np.array([[f@u for u in solutions] for f in forces]);reciprocity=float(np.max(abs(compliance-compliance.T))/max(np.max(abs(compliance)),1e-30));assert reciprocity<1e-7;assert min(np.linalg.eigvalsh(compliance))>0
 result=dict(revision=REV,license='CC-BY-NC-4.0',required_notice=NOTICE,variant='RAISE'+which,support_mode=support,target_mesh_size_mm=size,material_nominal=dict(E_MPa=E,nu=NU,yield_MPa=None),units='mm,N,MPa,Nmm',load_origin_world_mm=ORIGIN,foot_z_world_mm=127.2,axis_z_world_mm=205,span_mm=77.8,assembly=ass,fixed_dofs=len(D),fixed_mesh_area_mm2=float(fixedarea),**metadata,cases=results,normalized_compliance_matrix=compliance,compliance_diagonal_units=['mm/N','rad/Nmm','rad/Nmm'],generalized_load_order=['Fz_N','Mx_Nmm','My_Nmm'],generalized_response_order=['conjugate_translation_z_mm','conjugate_rotation_x_rad','conjugate_rotation_y_rad'],Maxwell_Betti_relative_error=reciprocity,elapsed_seconds=time.time()-start,generator_sha256=sha(__file__),limitations=['Ideal Dirichlet support: '+support+'; no contact separation/slip or bolt compliance.','Ideal annular rear load excludes eight4.5mm holes; not exact OEM rear contact footprint.','Only original aluminium fork; no tied steel blocks, OEM joint, bolts, preload or contact.','Linear isotropic smallstrain stiffness, not payload qualification or yield/fatigue assessment.','Quadratic displacement on linear faceted geometry. Singular clamp/corner stress peaks not design allowables.']);dump(f'RAISE{which}-h{size:g}'+('-posts' if support=='posts' else '')+'.json',result);print('CASE_READY',which,size,time.time()-start,flush=True)

def report():
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from mpl_toolkits.mplot3d.art3d import Poly3DCollection
 sizes=[6.,4.,2.8];data={v:[json.loads((OUT/f'RAISE{v}-h{h:g}.json').read_text()) for h in sizes] for v in ['01','02']};checks=[];comparison={}
 for v,rows in data.items():
  for r in rows:
   assert sha(ROOT/r['source']['source'])==r['source']['source_sha256'];assert sha(ROOT/r['source']['placement_manifest'])==r['source']['placement_manifest_sha256'];assert sha(rawpath(r['raw_mesh']))==r['raw_mesh_sha256'];assert r['mesh']['nonpositive_elements']==0;assert abs(r['mesh']['CAD_volume_relative_error'])<.002
   for c in r['cases'].values():assert sha(rawpath(c['result_vtu']))==c['result_sha256']
  for name in CASES:
   response=[r['cases'][name]['work_conjugate_response'] for r in rows];change=abs(response[-1]/response[-2]-1);checks.append(dict(variant=v,case=name,responses=response,last_refinement_relative_change=change,criterion=.02,pass_under_declared_criterion=change<.02))
 for name in CASES:
  a=data['01'][-1]['cases'][name]['work_conjugate_response'];b=data['02'][-1]['cases'][name]['work_conjugate_response'];comparison[name]=dict(RAISE01=a,RAISE02=b,response_unit=CASES[name][3],RAISE02_over_RAISE01=b/a,response_reduction_percent=100*(1-b/a),stiffness_factor=a/b)
 assert all(c['pass_under_declared_criterion'] for c in checks),checks
 fig,axs=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
 for ax,name in zip(axs,CASES):
  for v,col in [('01','#c8583a'),('02','#157e85')]:
   vals=[r['cases'][name]['work_conjugate_response'] for r in data[v]];fac=1000 if name!='Fz' else 1;ax.plot(sizes,np.array(vals)*fac,'o-',label='RAISE'+v,color=col)
  ax.set(xlabel='Target maximum element size (mm)',ylabel='Displacement (mm)' if name=='Fz' else 'Rotation (mrad)',title=f'{name}: '+('269.914 N' if name=='Fz' else '100 N m'));ax.invert_xaxis();ax.grid(alpha=.25);ax.legend()
 fig.suptitle('P2 solid elasticity | full feet fixed | ideal rear annulus load | E = 70 GPa, nu = 0.33');fig.text(.995,.001,NOTICE+' | CC BY-NC 4.0',ha='right',fontsize=5,color='0.35');fig.savefig(OUT/'convergence.png',dpi=180);fig.savefig(OUT/'convergence.pdf');plt.close(fig)
 # Clear boundary-condition illustration and displacement maps, all in undeformed world coordinates.
 meshes={}
 for v in data:
  r=data[v][-1];vm=meshio.read(rawpath(r['cases']['Mx']['result_vtu']));t=vm.cells_dict['tetra10'][:,:4];used=np.unique(t);idx=np.full(len(vm.points),-1,dtype=int);idx[used]=np.arange(len(used));m=oriented_mesh(vm.points[used],idx[t]);facets=m.facets[:,m.boundary_facets()].T;meshes[v]=(m,facets,used)
 fig=plt.figure(figsize=(10,5),constrained_layout=True)
 for n,v in enumerate(data):
  m,fs,used=meshes[v];tris=m.p.T[fs];cent=tris.mean(axis=1);rad=np.sqrt(cent[:,0]**2+(cent[:,2]-205)**2);load=(np.max(abs(tris[:,:,1]+45.7),axis=1)<1e-6)&(rad>47.7)&(rad<54.7);fix=np.max(abs(tris[:,:,2]-127.2),axis=1)<1e-6;cols=np.tile([.68,.72,.74,1.],(len(fs),1));cols[load]=[.9,.35,.08,1];cols[fix]=[.05,.35,.85,1]
  ax=fig.add_subplot(1,2,n+1,projection='3d');ax.add_collection3d(Poly3DCollection(tris,facecolors=cols,linewidths=0,rasterized=True));ax.set(xlim=(-70,70),ylim=(-108,-10),zlim=(125,272),xlabel='X (mm)',ylabel='Y (mm)',zlabel='Z (mm)',title='RAISE'+v);ax.set_title('RAISE'+v,y=.02,pad=0);ax.set_axis_off();ax.set_box_aspect((140,98,147));ax.view_init(-15,65)
 fig.suptitle('Ideal boundaries: blue = full foot fixed; orange = distributed annulus load\nOnly aluminium rear fork included; no bolts, OEM or steel blocks');fig.text(.995,.001,NOTICE+' | CC BY-NC 4.0',ha='right',fontsize=5,color='0.35');fig.savefig(OUT/'boundary-conditions.png',dpi=180);fig.savefig(OUT/'boundary-conditions.pdf');plt.close(fig)
 fig=plt.figure(figsize=(13,8),constrained_layout=True)
 for k,name in enumerate(CASES):
  maxu=max(data[v][-1]['cases'][name]['max_displacement_norm_mm'] for v in data);norm=matplotlib.colors.Normalize(0,maxu)
  for row,v in enumerate(data):
   r=data[v][-1];vm=meshio.read(rawpath(r['cases'][name]['result_vtu']));m,fs,used=meshes[v];values=vm.point_data['displacement_norm_mm'][used][fs].mean(axis=1);ax=fig.add_subplot(2,3,row*3+k+1,projection='3d');ax.add_collection3d(Poly3DCollection(m.p.T[fs],facecolors=plt.cm.viridis(norm(values)),linewidths=0,rasterized=True));ax.set(xlim=(-70,70),ylim=(-108,-10),zlim=(125,272),title=f'RAISE{v} / {name}');ax.set_box_aspect((140,98,147));ax.view_init(22,-62);ax.set_axis_off();fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=ax,shrink=.6,label='|u| (mm)')
 fig.suptitle('Displacement magnitude on undeformed geometry | same colour scale within each load case\nIdeal linear-elastic boundary comparison; no strength acceptance');fig.text(.995,.001,NOTICE+' | CC BY-NC 4.0',ha='right',fontsize=5,color='0.35');fig.savefig(OUT/'displacement-comparison.png',dpi=180);fig.savefig(OUT/'displacement-comparison.pdf');plt.close(fig)
 # Export a compact quadratic boundary subset, retaining exact solved P2 surface DOFs.
 surface_exports=[]
 for v in data:
  r=data[v][-1];vol=meshio.read(rawpath(r['cases']['Fz']['result_vtu']));t=vol.cells_dict['tetra10'];edge_index={}
  for a,b,j in [(0,1,4),(1,2,5),(0,2,6),(0,3,7),(1,3,8),(2,3,9)]:
   for row in t:edge_index[tuple(sorted([int(row[a]),int(row[b])]))]=int(row[j])
  # Recover external faces directly in the original volume point numbering.
  faces={}
  for local in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)]:
   for ci,row in enumerate(t[:,local]):
    key=tuple(sorted(map(int,row)))
    if key in faces:faces[key]=None
    else:
     oriented=row.copy();opposite=t[ci,next(i for i in range(4) if i not in local)];x=vol.points[oriented]
     if np.dot(np.cross(x[1]-x[0],x[2]-x[0]),vol.points[opposite]-x[0])>0:oriented[[1,2]]=oriented[[2,1]]
     faces[key]=oriented
  faces=[row for row in faces.values() if row is not None];tri=np.array([[*row,edge_index[tuple(sorted([int(row[0]),int(row[1])]))],edge_index[tuple(sorted([int(row[1]),int(row[2])]))],edge_index[tuple(sorted([int(row[2]),int(row[0])]))]] for row in faces]);used=np.unique(tri);index=np.full(len(vol.points),-1,dtype=int);index[used]=np.arange(len(used));fields={}
  for name in CASES:
   field=meshio.read(rawpath(r['cases'][name]['result_vtu']));assert np.array_equal(field.cells_dict['tetra10'],t);assert np.array_equal(field.points,vol.points);fields[name+'_displacement_mm']=field.point_data['displacement_mm'][used];fields[name+'_norm_mm']=field.point_data['displacement_norm_mm'][used]
  fn=f'RAISE{v}-finest-surface-fields.vtu';meshio.write(OUT/fn,meshio.Mesh(vol.points[used],[('triangle6',index[tri])],point_data=fields),binary=True,compression='zlib');again=meshio.read(OUT/fn);assert np.array_equal(again.points,vol.points[used]);assert all(np.array_equal(again.point_data[k],val) for k,val in fields.items());import gzip
  original_bytes=(OUT/fn).read_bytes();original_hash=sha(OUT/fn);gz=fn+'.gz';(OUT/gz).write_bytes(gzip.compress(original_bytes,compresslevel=9,mtime=0));assert gzip.decompress((OUT/gz).read_bytes())==original_bytes;(OUT/fn).unlink();surface_exports.append(dict(file=gz,sha256=sha(OUT/gz),bytes=(OUT/gz).stat().st_size,uncompressed_file=fn,uncompressed_sha256=original_hash,uncompressed_bytes=len(original_bytes),lossless_gzip_roundtrip_verified=True,nodes=len(used),quadratic_surface_triangles=len(tri),meaning='Exact subset of solved straight-geometry P2 boundary DOFs; no internal stress field or deformed geometry. Decompress gzip before VTU viewing.'))
 # One-level support sensitivity uses exactly the same four annuli on both variants.
 sensitivity={v:json.loads((OUT/f'RAISE{v}-h6-posts.json').read_text()) for v in data}
 for v,r in sensitivity.items():
  assert abs(r['fixed_CAD_area_mm2']-4*np.pi*(8**2-3.3**2))<1e-5
  for c in r['cases'].values():assert sha(rawpath(c['result_vtu']))==c['result_sha256']
 support_comparison={name:dict(RAISE01=sensitivity['01']['cases'][name]['work_conjugate_response'],RAISE02=sensitivity['02']['cases'][name]['work_conjugate_response'],RAISE02_over_RAISE01=sensitivity['02']['cases'][name]['work_conjugate_response']/sensitivity['01']['cases'][name]['work_conjugate_response'],RAISE01_posts_over_full=sensitivity['01']['cases'][name]['work_conjugate_response']/data['01'][0]['cases'][name]['work_conjugate_response'],RAISE02_posts_over_full=sensitivity['02']['cases'][name]['work_conjugate_response']/data['02'][0]['cases'][name]['work_conjugate_response']) for name in CASES}
 # Re-read output mesh payloads independently; no negative quadratic straight-geometry mapping.
 exportqa=[]
 for v,rows in data.items():
  for r in rows:
   raw=meshio.read(rawpath(r['raw_mesh']));assert len(raw.cells_dict['tetra'])==r['mesh']['tetrahedra']
   from scipy.sparse.csgraph import connected_components
   tet=raw.cells_dict['tetra'];coordinates=raw.points[tet];det=np.linalg.det(np.stack([coordinates[:,i]-coordinates[:,0] for i in [1,2,3]],axis=-1));reimport_volume=float(np.abs(det).sum()/6);assert abs(reimport_volume/r['mesh']['mesh_volume_mm3']-1)<1e-11;assert min(abs(det))>0
   edges=np.concatenate([tet[:,[a,bb]] for a in range(4) for bb in range(a+1,4)]);adj=sp.csr_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(raw.points),len(raw.points)));active=np.unique(tet);ncomponents=connected_components(adj[active][:,active],directed=False,return_labels=False);assert ncomponents==1
   for name,c in r['cases'].items():
    vm=meshio.read(rawpath(c['result_vtu']));vt=vm.cells_dict['tetra10'];assert len(vt)==r['mesh']['tetrahedra']
    midpoint_error=max(float(np.max(abs(vm.points[vt[:,k]]-(vm.points[vt[:,a]]+vm.points[vt[:,bb]])/2))) for a,bb,k in [(0,1,4),(1,2,5),(0,2,6),(0,3,7),(1,3,8),(2,3,9)]);assert midpoint_error<1e-10
    assert np.isfinite(vm.point_data['displacement_mm']).all();assert np.min(vm.cell_data_dict['mean_von_mises_MPa']['tetra10'])>=0;exportqa.append(dict(file=c['result_vtu'],tetra10=len(vm.cells_dict['tetra10']),finite_displacement=True,connected_volume_components=int(ncomponents),raw_reimport_volume_mm3=reimport_volume,quadratic_node_midpoint_max_error_mm=midpoint_error))
 all_meshes=[r for rows in data.values() for r in rows]+list(sensitivity.values())
 assert len(all_meshes)==8 and sum(len(r['cases']) for r in all_meshes)==24
 result=dict(revision=REV,license='CC-BY-NC-4.0',required_notice=NOTICE,material_nominal=dict(E_MPa=E,nu=NU,yield_MPa=None),mesh_sizes_mm=sizes,convergence_checks=checks,comparison_finest=comparison,compact_surface_exports=surface_exports,same_post_support_sensitivity=support_comparison,sensitivity_note='One h6 mesh per variant; same four CAD annular fixed areas, not contact/bolt physics and not a separate converged study.',aggregate_scope=dict(main_meshes=6,sensitivity_meshes=2,total_meshes=8,total_load_solutions=24),minimum_mean_ratio_all_meshes=min(r['mesh']['mean_ratio_min'] for r in all_meshes),maximum_absolute_CAD_volume_error=max(abs(r['mesh']['CAD_volume_relative_error']) for r in all_meshes),maximum_force_balance_error_N=max(c['solver']['force_balance_error_N'] for r in all_meshes for c in r['cases'].values()),maximum_moment_balance_error_Nmm=max(c['solver']['moment_balance_error_Nmm'] for r in all_meshes for c in r['cases'].values()),maximum_energy_balance_relative_error=max(c['solver']['energy_balance_relative_error'] for r in all_meshes for c in r['cases'].values()),export_reimport_checks=exportqa,generator_sha256=sha(__file__),decision='Only rear-fork ideal elastic stiffness comparison; no assembly, material, payload, fatigue or manufacturing release. Foot constraint areas differ by geometry.');dump('comparison.json',result)
 # Keep bulky raw artifacts local, with a complete reproducibility inventory.
 for p in list(OUT.glob('*.msh'))+list(OUT.glob('*.vtu')):
  if 'surface-fields' not in p.name:
   dest=RAW/p.name
   if dest.exists():assert sha(dest)==sha(p);p.unlink()
   else:p.rename(dest)
 raw_inventory=[dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(RAW.iterdir()) if p.is_file()]
 dump('raw-artifact-manifest.json',dict(directory_relative_to_repo='../../work/shoulder-fea01-raw',artifacts=raw_inventory,total_bytes=sum(a['bytes'] for a in raw_inventory),regeneration='See exact commands in docs/engineering/shoulder-fea01.md',not_distributed_with_repository=True))
 print(json.dumps(result,default=native,indent=2),flush=True)

def audit():
 rows=[json.loads(p.read_text()) for p in sorted(OUT.glob('RAISE*-h*.json'))];assert len(rows)==8
 force_source=json.loads((ROOT/'engineering/generated/shoulder-raise-strength01/study.json').read_text())['gravity_bounds']['interfaces']['J2_rear'];assert abs(force_source['expanded_force_N']-CASES['Fz'][2])<1e-12
 source_hashes={};export_audit=[]
 for r in rows:
  for path,key in [(r['source']['source'],'source_sha256'),(r['source']['placement_manifest'],'placement_manifest_sha256')]:
   expected=r['source'][key];assert sha(ROOT/path)==expected;source_hashes[path]=expected
  assert abs(r['load_CAD_area_mm2']-2124.6591116228)<1e-5
  assert sha(rawpath(r['raw_mesh']))==r['raw_mesh_sha256'];raw=meshio.read(rawpath(r['raw_mesh']));tet=raw.cells_dict['tetra'];x=raw.points[tet];det=np.linalg.det(np.stack([x[:,i]-x[:,0] for i in [1,2,3]],axis=-1));volume=float(np.abs(det).sum()/6);assert min(abs(det))>0 and abs(volume/r['mesh']['mesh_volume_mm3']-1)<1e-11
  from scipy.sparse.csgraph import connected_components
  edges=np.concatenate([tet[:,[a,bb]] for a in range(4) for bb in range(a+1,4)]);adj=sp.csr_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(raw.points),len(raw.points)));active=np.unique(tet);nc=connected_components(adj[active][:,active],directed=False,return_labels=False);assert nc==1
  for c in r['cases'].values():
   assert sha(rawpath(c['result_vtu']))==c['result_sha256'];vm=meshio.read(rawpath(c['result_vtu']));vt=vm.cells_dict['tetra10'];assert len(vt)==len(tet);me=max(float(np.max(abs(vm.points[vt[:,k]]-(vm.points[vt[:,a]]+vm.points[vt[:,bb]])/2))) for a,bb,k in [(0,1,4),(1,2,5),(0,2,6),(0,3,7),(1,3,8),(2,3,9)]);assert me<2e-15;assert np.isfinite(vm.point_data['displacement_mm']).all();export_audit.append(dict(file=c['result_vtu'],volume_components=int(nc),reimport_volume_mm3=volume,midpoint_max_error_mm=me))
   q=c['solver'];assert q['free_residual_relative']<1e-7;assert q['force_balance_normalized']<1e-6 and q['moment_balance_normalized']<1e-6;assert q['energy_balance_relative_error']<1e-7
 for path in ['engineering/generated/shoulder-raise-strength01/study.json','engineering/generated/raised-arm-integration01/model.json']:source_hashes[path]=sha(ROOT/path)
 files=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='ready-manifest.json'];assert not any(p.suffix=='.msh' for p in files);assert not any(p.suffix=='.vtu' and 'surface-fields' not in p.name for p in files);total=sum(p.stat().st_size for p in files);assert total<30_000_000,total
 doc=ROOT/'docs/engineering/shoulder-fea01.md';assert '求解进行中' not in doc.read_text();assert '待本轮结果汇总' not in doc.read_text()
 result=dict(revision=REV,status='READY independent ideal-boundary elastic comparison; not manufacturing or payload acceptance',license='CC-BY-NC-4.0',required_notice=NOTICE,original_sources_unchanged=True,source_hashes=source_hashes,force_input_from_STRENGTH01=force_source,script=dict(file=str(Path(__file__).relative_to(ROOT)),sha256=sha(__file__)),document=dict(file=str(doc.relative_to(ROOT)),sha256=sha(doc)),all_eight_mesh_cases_and_24_load_solutions_verified=True,all_raw_reimport_checks=export_audit,repository_generated_bytes_excluding_manifest=total,files=[dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files],raw_repository_policy='Complete meshes/fields remain work/shoulder-fea01-raw; hashes and commands supplied; no LFS change.',source_provenance_note='Case generator_sha256 records the script file at completion; reporting/optional support instrumentation evolved between independently run cases. Original STEP/placement hashes and stored result fields are frozen. This final script reproduces the declared algorithms and all cases; file-byte identity is not promised across Gmsh/OCC runs.');dump('ready-manifest.json',result);print('READY',sha(OUT/'ready-manifest.json'),total,flush=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['benchmark','actual','report','audit'],default='benchmark');ap.add_argument('--variant',choices=['01','02'],default='01');ap.add_argument('--size',type=float,default=6.);ap.add_argument('--support',choices=['full','posts'],default='full');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 if args.stage=='benchmark':benchmarks()
 elif args.stage=='report':report()
 elif args.stage=='audit':audit()
 else:actual(args.variant,args.size,args.support)
if __name__=='__main__':main()
