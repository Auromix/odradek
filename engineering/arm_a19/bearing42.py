# SPDX-License-Identifier: CC-BY-NC-4.0
"""Ideal separate J7 two-bearing radial load path, static gravity only."""
from pathlib import Path
import sys,json
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c

def main():
 path=OUT/'manifest.json';d=json.loads(path.read_text());rows=[p for p in d['budget']if p['frame']=='J7.rotor']+[dict(id='payload-at-flange',mass_kg=3,com_mm=[110,0,0])]
 A=np.array([39.7,0,0]);B=np.array([50.7,0,0]);spacing=B[0]-A[0];maps=[]
 for direction in np.eye(3):
  F=sum((p['mass_kg']*9.81*direction for p in rows),np.zeros(3));M=sum((np.cross(np.array(p['com_mm'])-A,p['mass_kg']*9.81*direction) for p in rows),np.zeros(3));RB=np.array([0,-M[2]/spacing,M[1]/spacing]);RA=np.array([0,-F[1]-RB[1],-F[2]-RB[2]])
  assert np.linalg.norm((RA+RB+F)[1:])<1e-10 and np.linalg.norm((M+np.cross(B-A,RB))[1:])<1e-8
  maps.append(dict(gravity_unit=direction.tolist(),external_force_N=F.tolist(),moment_about_A_Nmm=M.tolist(),reaction_A_radial_N=RA.tolist(),reaction_B_radial_N=RB.tolist(),unallocated_axial_N=F[0],motor_roll_torque_Nm=-M[0]/1000))
 results=[]
 for key in ['reaction_A_radial_N','reaction_B_radial_N']:
  mat=np.array([m[key]for m in maps]).T;u,s,vt=np.linalg.svd(mat);direction=vt[0];reaction=mat@direction
  results.append(dict(bearing='rear-A'if 'A_'in key else'front-B',max_over_any_gravity_orientation_N=float(s[0]),gravity_unit=direction.tolist(),reaction_N=reaction.tolist(),reaction_map_N=mat.tolist(),catalogue_C0r_N=4100,radial_only_C0r_to_force_ratio=float(4100/s[0]),combined_static_equivalent_calculated=False))
 report=dict(revision='A19-J7-IDEAL-BEARING-SCREEN42',source_assembly_sha256=c.sha(path),source_checker_sha256=c.sha(Path(__file__)),bearing_centres_J7_mm=[A.tolist(),B.tolist()],spacing_mm=spacing,payload_kg=3,payload_point_J7_mm=[110,0,0],included_rotor_own_and_allowance_kg=sum(p['mass_kg']for p in rows)-3,basis=maps,results=results,maximum_unallocated_axial_N=9.81*sum(p['mass_kg']for p in rows),motor_roll_torque_max_Nm=float(np.linalg.norm([m['motor_roll_torque_Nm']for m in maps])),catalogue=dict(manufacturer='NSK',model='6807',ID_OD_width_mm=[35,47,7],Cr_N=5400,C0r_N=4100,url='https://www.nsk.com/my-en/engineering/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6807-apn.html'),actual_steel_bearing_selected=False,production_release=False,scope='Ideal rigid two-support static radial load path, all external radial forces assigned to added pair and axial force left unallocated. No actual load sharing with RS00, clearance/preload, combined equivalent load, life, plastic seat stiffness/creep, metal fit, dynamics or off-centre workpiece. Radial catalogue ratio is not safety factor or capacity approval.')
 (OUT/'bearing42.json').write_text(json.dumps(report,indent=2)+'\n');print('BEARING42',results,flush=True)
if __name__=='__main__':main()
