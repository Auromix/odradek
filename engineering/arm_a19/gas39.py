# SPDX-License-Identifier: CC-BY-NC-4.0
"""Catalogue-size tension gas spring screening; not a selected component."""
from pathlib import Path
import json,sys
import numpy as np
from scipy.optimize import differential_evolution
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import shoulder15 as s
c=s.f.c

def main():
 path=OUT/'J2-ideal-passive-limit27.csv';a=np.genfromtxt(path,delimiter=',',names=True);theta=a['J2_deg'];lo=a['raw_min_Nm'];hi=a['raw_max_Nm'];results=[]
 # HAHN main catalogue PDF page9 (printed16-17), shortest ordinary steel
 # hinged eyes from PDF page19 (printed36-37). Standard length is assumed
 # extended bare length, consistent with the catalogue ordering convention.
 # This dimensional interpretation and actual datasheet must be confirmed.
 families=[('Z04-15',15,20,200,63,50,300,.22,22,'AU11'),('Z06-19',19,30,400,100,40,350,.29,32,'AU16'),('Z10-28',28,60,600,100,150,1200,.20,38,'AU19'),('Z10-40',40,10,590,150,400,2000,.78,84,'AU42'),('Z28-40',40,50,700,125,500,5000,.40,84,'AU42')]
 for model,diam,Smin,Smax,constant,Fmin,Fmax,progression,fittings,fitting_model in families:
  def data(x):
   rad,phase,b,fx,stroke,links,F1=x;ax=rad*np.cos(np.radians(phase));az=rad*np.sin(np.radians(phase));length,lever,mn,mx=s.geometry(theta,ax,az,b,fx)
   factor=2.5 if model=='Z28-40' else 2
   extended=factor*stroke+constant+fittings+links;compressed=extended-stroke;travel=length*1000-compressed
   # Ideal-gas interpolation constrained only by catalogue progression.
   # Manufacturer does not publish this force curve; it is an optimistic
   # screening hypothesis, NOT a guaranteed characteristic.
   alpha=progression/(1+progression)
   force=F1*(1-alpha*5/stroke)/(1-alpha*travel/stroke)
   assist=-2*force*lever
   violation=max(0,compressed+5-mn)+max(0,mx-(extended-5))
   return dict(ax=ax,az=az,length=length,lever=lever,mn=mn,mx=mx,force=force,assist=assist,extended=extended,compressed=compressed,violation=violation)
  def objective(x):
   d=data(x)
   if d['violation']>0:return 1000+20*d['violation']
   return float(np.max(abs(np.array([lo+.9*d['assist'],hi+.9*d['assist'],lo+1.1*d['assist'],hi+1.1*d['assist']]))))
  bounds=[(25,95),(145,235),(110,194),(-65,65),(Smin,min(Smax,160)),(0,60),(Fmin,Fmax)]
  trials=[differential_evolution(objective,bounds,seed=1939+k,maxiter=280,popsize=14,tol=1e-7,polish=True)for k in range(2)];best=min(trials,key=lambda p:p.fun);x=best.x;d=data(x);feasible=bool(d['violation']<1e-5)
  rec=dict(model_family=model,quantity=2,diameter_mm=diam,catalogue_force_N=[Fmin,Fmax],catalogue_progression=progression,proposed_F1_N=float(x[6]),stroke_mm=float(x[4]),eye_fitting=fitting_model,two_eye_length_mm=fittings,extra_links_mm=float(x[5]),moving_pin_J2_xz_mm=[float(d['ax']),float(d['az'])],fixed_pin_J1_xz_mm=[float(x[3]),float(114-x[2])],pin_span_range_mm=[d['mn'],d['mx']],assumed_spring_pin_span_mm=[d['compressed'],d['extended']],dimensional_feasible=feasible,residual_Nm=float(best.fun)if feasible else None,search_penalty=float(best.fun),below_22_8_screen=bool(feasible and best.fun<=22.8),actual_force_curve_verified=False,actual_CAD_verified=False,actual_mass_verified=False,purchase_selected=False)
  results.append(rec);print('GAS39',model,rec['dimensional_feasible'],rec['residual_Nm'],rec['pin_span_range_mm'],rec['assumed_spring_pin_span_mm'],flush=True)
 report=dict(revision='A19-TENSION-GAS-SCREEN39',source_interval_csv_sha256=c.sha(path),source_assembly_sha256=c.sha(OUT/'manifest.json'),source_checker_sha256=c.sha(Path(__file__)),source_pdf_sha256=c.sha(HERE.parents[1]/'work/arm-a19/HAHN-catalogue-EN.pdf'),source_url='https://www.hahn-gasfedern.de/media/default/Hahn/Download-Center/HAHN_Katalog_EN-web.pdf',source_pdf_pages=[4,8,9,19,23],candidates=results,force_tolerance=[.9,1.1],force_curve_is_manufacturer_guarantee=False,friction_and_temperature_included=False,production_release=False,scope='Five catalogue tension-gas families; ordinary two-pivot straight geometry, two identical parallel springs. Optimistic ideal-gas curve hypothesis, cold force tolerance only. Missing actual force/stroke data, temperature, friction, ageing, grease-chamber usable stroke, orientation, real mass, transverse CAD, brackets and life. No supplier contacted or procurement issued.')
 (OUT/'gas39.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
