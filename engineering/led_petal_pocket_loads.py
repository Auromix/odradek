# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Actual net-section sensitivity after pocketing; not whole-finger strength."""
import hashlib,json
from pathlib import Path
import numpy as np
import cadquery as cq
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from led_petal_pocket_study import ROOT,OUT,box,sha

def main():
    path=ROOT/'engineering/generated/pad-retention-study/verification.json';source=json.loads(path.read_text())
    study=json.loads((OUT/'study.json').read_text());rows=[];fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for ix,(ref,geometry) in enumerate(zip(source['variants'],study['variants'])):
        name=ref['variant'];L=ref['length_mm'];forces=[np.array(f['force_on_pad_blade_N']) for f in ref['force_witness']]
        points=[np.array(f['force_application_point_toe_mm'])+np.array([L,0,0]) for f in ref['force_witness']]
        inputs={'full_retained_blade':ROOT/f'engineering/generated/pad-retention-study/ODR-RET-{name}-BLADE.step',
                'pocketed_blade':OUT/f'{name}-metal.step'};result={}
        # Samples immediately adjacent to hole, cavity and aperture edges are
        # added to the regular grid. They do not certify unsampled extrema.
        features=[26.75,38.5,47.5,L-21.75,L-28-2.75,L-28+2.75,L-16.25,L-11.75,L-6.25,L-1.75,30.25,35.75]
        xx=np.unique(np.r_[np.linspace(25.01,L-.01,121),[x+dx for x in features for dx in [-.003,.003] if 25<x+dx<L]])
        for label,p in inputs.items():
            shape=cq.importers.importStep(str(p)).val()
            if label=='full_retained_blade':shape=shape.translate((L,0,0))
            sections=[];t=.002
            for x in xx:
                sec=shape.intersect(box(t,100,20,[float(x),0,5]));props=GProp_GProps();BRepGProp.VolumeProperties_s(sec.wrapped,props)
                A=props.Mass()/t;I=props.MatrixOfInertia();Iy=I.Value(2,2)/t-A*t*t/12;Iz=I.Value(3,3)/t-A*t*t/12
                yz=-I.Value(2,3)/t;c=np.array(sec.Center().toTuple());c[0]=x
                assert A>0 and Iy>0 and Iz>0 and abs(yz)<1e-4
                moment=sum((np.cross(point-c,F) for point,F in zip(points,forces)),start=np.zeros(3));F=sum(forces,start=np.zeros(3))
                stress=[F[0]/A+moment[1]*(v.Center().z-c[2])/Iy-moment[2]*(v.Center().y-c[1])/Iz for v in sec.Vertices()]
                sections.append({'x_mm':float(x),'area_mm2':A,'Iy_mm4':Iy,'Iz_mm4':Iz,'Iyz_mm4':yz,
                    'centroid_yz_mm':c[1:].tolist(),'moment_Nmm':moment.tolist(),
                    'max_abs_normal_stress_MPa':float(max(abs(v) for v in stress)),
                    'slice_thickness_mm':t,'slice_solids':len(sec.Solids())})
            worst=max(sections,key=lambda r:r['max_abs_normal_stress_MPa'])
            zdef=float(np.trapezoid([v['moment_Nmm'][1]*(L-v['x_mm'])/(70000*v['Iy_mm4']) for v in sections],xx))
            ydef=float(np.trapezoid([v['moment_Nmm'][2]*(L-v['x_mm'])/(70000*v['Iz_mm4']) for v in sections],xx))
            result[label]={'source_sha256':sha(p),'sample_count':len(sections),'max_sampled_normal_stress_MPa':worst['max_abs_normal_stress_MPa'],
                'max_stress_x_mm':worst['x_mm'],'tip_bending_deflection_indicator_mm':[ydef,zdef],
                'max_torsion_moment_not_in_stress_Nmm':max(abs(v['moment_Nmm'][0]) for v in sections),'sections':sections}
            axes[ix].plot(xx,[r['max_abs_normal_stress_MPa'] for r in sections],label=label.replace('_',' '))
        axes[ix].set(title=name+' / same conditional contact witness',xlabel='Root x / mm',ylabel='Sampled normal stress / MPa');axes[ix].legend();axes[ix].grid(alpha=.2)
        rows.append({'variant':name,'force_witness':ref['force_witness'],'assumed_clamp_x_mm':25.,'comparison':result})
    fig.suptitle('Distal blade section screening / no torsion, local notch or root-interface qualification')
    fig.savefig(OUT/'net-section-loads.png',dpi=165);plt.close(fig)
    d={'revision':'R4-LED-POCKET-LOADS-01','generator_sha256':sha(Path(__file__)),
       'geometry_study_sha256':sha(OUT/'study.json'),'force_source_sha256':sha(path),'manufacturing_release':False,
       'E_MPa':70000,'variants':rows,
       'method':'Thin BREP slices, actual net centroid/inertia; sigma=Fx/A+My*z/Iy-Mz*y/Iz; ideal clamp at x25; Euler-Bernoulli variable-section deflection indicator.',
       'limits':['Only one documented 80x40 cylinder force witness at mu .4 and 2 kg x2; not worst-case loads.',
                 'No root flexure, torsional/shear stress, local notch, fastener preload, contact stress, buckling or fatigue.',
                 'Section sampling does not certify extrema between samples or exact sharp-edge stresses.',
                 'Ideal beam clamp and stepped centroid approximation do not constitute 3D FEA or conservative compliance bound.',
                 'No component/self-weight, trajectory inertia, manufacturing imperfections or thermal properties.']}
    (OUT/'net-section-loads.json').write_text(json.dumps(d,indent=2)+'\n')
    print([(r['variant'],{k:(v['max_sampled_normal_stress_MPa'],v['tip_bending_deflection_indicator_mm']) for k,v in r['comparison'].items()}) for r in rows])

if __name__=='__main__':main()
