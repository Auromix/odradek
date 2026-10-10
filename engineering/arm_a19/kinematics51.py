# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent flange Jacobian and whole-mass virtual-work check."""
from pathlib import Path
import sys,json,math
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c;f=w.f

def frames(L,q):
 T=np.array(L['root_transform_mm'],float);out={'world':T.copy()}
 for j,v in zip(L['joints'],q):
  S=np.eye(4);S[:3,3]=j['offset'];T=T@S;out[j['id']+'.fixed']=T.copy();a=np.array(j['axis'],float);a/=np.linalg.norm(a);angle=math.radians(v+j['zero_deg']);K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]]);R=np.eye(4);R[:3,:3]=np.eye(3)+math.sin(angle)*K+(1-math.cos(angle))*(K@K);T=T@R;out[j['id']+'.rotor']=T.copy()
 S=np.eye(4);S[:3,3]=L['flange_from_J7_mm'];out['flange']=T@S;return out

def main():
 path=OUT/'manifest.json';d=json.loads(path.read_text());L=d['layout'];records=[];cases=list(L['poses'].items())+[(f'halton-{k}',[j['limits_deg'][0]+f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0])for j,b in zip(L['joints'],[2,3,5,7,11,13,17])])for k in range(1,65)]
 bodies=d['budget']+[dict(id=j['id'],frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center'])for j in L['joints']]+[dict(id='payload',frame='flange',mass_kg=3,com_mm=[0,0,0])]
 def potential(q):
  F=frames(L,q);return sum(p['mass_kg']*9.81*(F[p['frame']]@np.r_[p['com_mm'],1])[2]/1000 for p in bodies)
 delta=1e-5
 for name,q in cases:
  q=np.array(q,float);F=frames(L,q);old=f.frames(L,q);error=max(float(np.max(abs(F[k]-old[k])))for k in F);assert error<1e-9
  p=F['flange'][:3,3];J=np.zeros((6,7));deriv=[];grad=[]
  for i,j in enumerate(L['joints']):
   A=F[j['id']+'.fixed'];a=A[:3,:3]@j['axis'];J[:3,i]=np.cross(a,p-A[:3,3])/1000;J[3:,i]=a;hi=q.copy();lo=q.copy();hi[i]+=math.degrees(delta);lo[i]-=math.degrees(delta);deriv.append((frames(L,hi)['flange'][:3,3]-frames(L,lo)['flange'][:3,3])/(2*delta)/1000);grad.append((potential(hi)-potential(lo))/(2*delta))
  je=float(np.max(abs(J[:3]-np.array(deriv).T)));tau=f.torque(L,np.array([q]),3,d['budget'])[0];te=float(np.max(abs(tau-grad)));assert je<1e-7 and te<1e-6,(name,je,te)
  records.append(dict(pose=name,q_deg=q.tolist(),flange_position_world_mm=p.tolist(),Jv_m_per_rad=J[:3].tolist(),Jw_rad_per_rad=J[3:].tolist(),FK_matrix_error=error,Jacobian_central_difference_error_m_per_rad=je,whole_gravity_virtual_work_error_Nm=te,holding_gravity_Nm=tau.tolist()))
 report=dict(source_assembly_sha256=c.sha(path),source_checker_sha256=c.sha(Path(__file__)),payload_kg=3,checks=records,all_67_FK_Jacobian_and_gravity_checks_passed=True,production_release=False,scope='Independent Rodrigues FK plus analytic flange Jacobian vs central finite differences, whole nominal COM gravity vs potential derivative.67finite poses, unfiltered collision; no dynamics/friction/elasticity/wires/controller execution qualification.')
 (OUT/'kinematics51.json').write_text(json.dumps(report,indent=2)+'\n');print('KINEMATICS51',len(records),max(r['whole_gravity_virtual_work_error_Nm']for r in records),flush=True)
if __name__=='__main__':main()
