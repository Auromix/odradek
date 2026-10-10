# SPDX-License-Identifier: CC-BY-NC-4.0
"""Ordinary spring screening on current torque intervals; not a purchase release."""
from pathlib import Path
import json,sys,csv
import numpy as np
from scipy.optimize import linprog,differential_evolution
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import shoulder15 as s
c=s.f.c

def fit(X,lo,hi):
 n=X.shape[1];r=linprog(np.r_[np.zeros(n),1],A_ub=np.vstack([np.c_[X,-np.ones(len(lo))],np.c_[-X,-np.ones(len(lo))]]),b_ub=np.r_[-hi,lo],bounds=[(None,None)]*n+[(0,None)],method='highs');assert r.success
 return dict(coefficients=r.x[:-1].tolist(),best_sampled_residual_Nm=float(r.x[-1]))

def main():
 path=OUT/'J2-ideal-passive-limit27.csv';a=np.genfromtxt(path,delimiter=',',names=True);theta=a['J2_deg'];rad=np.radians(theta);lo=a['raw_min_Nm'];hi=a['raw_max_Nm']
 fits=dict(ordinary_linear_torsion=fit(np.c_[np.ones(len(a)),rad],lo,hi),ideal_sinusoidal_assist=fit(np.c_[np.cos(rad),np.sin(rad)],lo,hi))
 # Values are directly transcribed from manufacturer US2023 PDF pages270-271;
 # music wire table, force converted lbf->N, rate lbf/in->N/mm.
 stock=[('LE095J06M',25.4,2.41,30,2.7,127,4.8,271.53,270),('LE105J06M',25.4,2.67,40,4,127,7.73,245.36,270),('LE115J08M',25.4,2.92,50,5,152.4,9.5,272.80,271),('LE125J08M',25.4,3.18,70,7,152.4,14.97,259.33,271),('LE135J07M',25.4,3.43,85,9,139.7,25.5,215.39,271),('LE135J08M',25.4,3.43,85,9,152.4,22.61,237.74,271)]
 results=[]
 for model,OD,wire,Fmax,Fi,Lfree,k,Lmax,page in stock:
  Fmax*=4.4482216152605;Fi*=4.4482216152605;k*=4.4482216152605/25.4
  # Two equal ordinary extension springs in parallel; +6 nominal hook
  # bearing-to-pin-centre correction for6mm pin. This needs real hook geometry.
  def data(x):
   radius,phase,b,fx,extension=x;ax=radius*np.cos(np.radians(phase));az=radius*np.sin(np.radians(phase));length,lever,mn,mx=s.geometry(theta,ax,az,b,fx)
   spring_length=length*1000-extension-6
   force=Fi+k*(spring_length-Lfree);assist=-2*force*lever
   return dict(ax=ax,az=az,Lmin=mn,Lmax=mx,spring_length=spring_length,force=force,assist=assist,lever=lever)
  def objective(x):
   d=data(x);minimum=d['Lmin']-x[4]-6;maximum=d['Lmax']-x[4]-6
   violation=max(0,Lfree+3-minimum)+max(0,maximum-(Lmax-5))
   if violation:return 1000+10*violation
   # +/-5% is an explicit sensitivity, NOT a manufacturer tolerance guarantee.
   return float(np.max(abs(np.array([lo+.95*d['assist'],hi+.95*d['assist'],lo+1.05*d['assist'],hi+1.05*d['assist']]))))
  best=None
  for seed in [1933,1934]:
   r=differential_evolution(objective,[(25,95),(145,235),(110,194),(-65,65),(0,60)],seed=seed,maxiter=300,popsize=14,tol=1e-7,polish=True)
   if best is None or r.fun<best.fun:best=r
  x=best.x;d=data(x)
  # Required motor holding contribution is +dU/dtheta; actual spring torque is its negative.
  U=[];checks=[]
  for angle in [-60,0,35,90,110]:
   def energy(t):
    L=s.geometry(np.array([t]),d['ax'],d['az'],x[2],x[3])[0][0]*1000-x[4]-6;delta=L-Lfree;return 2*(Fi*delta+.5*k*delta**2)/1000
   h=1e-4;virtual=(energy(angle+h)-energy(angle-h))/(2*np.radians(h));L,lever,*_=s.geometry(np.array([angle]),d['ax'],d['az'],x[2],x[3]);anal=-2*(Fi+k*(L[0]*1000-x[4]-6-Lfree))*lever[0];err=abs(virtual-anal);assert err<1e-6
   checks.append(dict(q2_deg=angle,spring_potential_error_Nm=err))
  rec=dict(model=model,quantity=2,diameter_mm=OD,wire_mm=wire,catalogue_Fmax_N=Fmax,catalogue_initial_tension_N=Fi,catalogue_rate_N_mm=k,catalogue_free_length_mm=Lfree,catalogue_max_length_mm=Lmax,catalogue_pdf_page=page,moving_pin_J2_xz_mm=[float(d['ax']),float(d['az'])],fixed_pin_J1_xz_mm=[float(x[3]),float(114-x[2])],additional_end_links_mm=float(x[4]),pin_diameter_assumption_mm=6,analytic_pin_span_mm=[d['Lmin'],d['Lmax']],sampled_per_spring_force_N=[float(min(d['force'])),float(max(d['force']))],sampled_residual_Nm=float(best.fun),below_22_8_screen=bool(best.fun<=22.8),checks=checks,geometry_checked=False,hook_life_checked=False,purchase_selected=False)
  results.append(rec);print('ASSIST33',model,rec['sampled_residual_Nm'],rec['moving_pin_J2_xz_mm'],rec['fixed_pin_J1_xz_mm'],flush=True)
 report=dict(revision='A19-ORDINARY-SPRING-SCREEN33',source_interval_csv_sha256=c.sha(path),source_assembly_sha256=c.sha(OUT/'manifest.json'),fits=fits,candidates=results,force_sensitivity=[.95,1.05],force_sensitivity_is_supplier_guarantee=False,payload_cases_kg=[0,3],same_extra_full_moving_mass_allowance_kg=.30,source_pdf_sha256=c.sha(HERE.parents[1]/'work/arm-a19/Lee-Spring-US-2023.pdf'),source_url='https://www.leespring.com/sites/default/files/2023-03/lee-spring-catalog-us.pdf',production_release=False,scope='Finite current torque intervals. Ordinary linear torsion minimax and two ordinary steel extension springs. No physical hook/pin bracket/CAD routing/thermal/fatigue approval; catalogue maximum extension is not continuous robot life rating.')
 (OUT/'assist33.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
