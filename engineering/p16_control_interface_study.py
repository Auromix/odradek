# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""P16-CTRL01: conditional electrical/feedback budgets, no hardware-control code."""
from pathlib import Path
import csv,hashlib,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/p16-control-interface'
SOURCES=ROOT/'docs/engineering/sources/p16-control-interface-sources.json'
D=123.;A=26.;PHASE=68.;CAD_L0=97.4;STROKE=50.
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def length(q):return np.sqrt(D*D+A*A+2*D*A*np.sin(np.radians(q-PHASE)))
def inverse(L):
    x=(np.asarray(L)**2-D*D-A*A)/(2*D*A)
    if not np.all(np.isfinite(x)) or np.any(np.abs(x)>1):raise ValueError('Length outside geometric inverse branch')
    return PHASE+np.degrees(np.arcsin(x))
def jac(q):return D*A*np.cos(np.radians(q-PHASE))/length(q) # mm/rad

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    src=json.loads(SOURCES.read_text())
    q=np.linspace(0,122,10001);L=length(q);j=jac(q)
    inv_err=float(np.max(np.abs(inverse(L)-q)))
    h=1e-4;fd=(length(q+math.degrees(h))-length(q-math.degrees(h)))/(2*h)
    fd_err=float(np.max(np.abs(j-fd)));assert inv_err<1e-10 and fd_err<1e-6 and j.min()>0
    # Deliberately accept a full assembled reference +/-1% budget; this is not
    # simply the REF3125 initial accuracy, and remains a test acceptance target.
    ref=2.5;R=6190.;gain=450e-6;vr=.01;rr=.001;gg=.075
    itrip=ref/(R*gain);imin=ref*(1-vr)/(R*(1+rr)*gain*(1+gg));imax=ref*(1+vr)/(R*(1-rr)*gain*(1-gg))
    assert .4<imin<imax<1 # self-consistent with chosen datasheet error interval
    current={'driver_candidate':'DRV8874PWPR','quantity':4,'VREF_nominal_V':ref,'VREF_total_planning_envelope_fraction':vr,
      'VREF_candidate':'REF3125AIDBZR','R_IPROPI_ohm':R,'R_tolerance_fraction':rr,'gain_A_per_A':gain,'gain_error_fraction':gg,
      'trip_nominal_A':itrip,'trip_static_corner_A':[imin,imax],'full_reference_and_resistor_selected':False,
      'scope':'DC comparison threshold with nominal gain and specified error interval; not a guaranteed peak clamp. Switching blanking, deglitch, current-sense dynamics and VREF transient faults are excluded.'}
    rows=[]
    for angle in [0,15,30,45,60,90,109,122]:
        ell=float(length(angle));jj=float(jac(angle));adc=(ell-CAD_L0)/STROKE*4095
        rows.append({'q_deg':angle,'pin_distance_mm':ell,'stroke_from_nominal_CAD_closed_mm':ell-CAD_L0,
          'nominal_pot_fraction':(ell-CAD_L0)/STROKE,'ideal_12bit_ADC_code':adc,'jacobian_mm_per_rad':jj,
          'local_angle_step_deg_per_ADC_LSB':math.degrees(STROKE/4095/jj),
          'geometric_inverse_at_length_minus_plus_1mm_deg':[float(inverse(ell-1)),float(inverse(ell+1))]})
    with (OUT/'feedback-angle-table.csv').open('w',newline='') as f:
        fields=[k for k in rows[0] if not k.startswith('geometric_')];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows)
    duty=[]
    for name,q0,q1 in [('upper_full',0,109),('lower_full',0,122),('small_attention_45_plus_minus_2',43,47)]:
        travel=2*abs(float(length(q1)-length(q0)));minimum_on=travel/4.8
        duty.append({'gesture':name,'angle_span_deg':[q0,q1],'round_trip_travel_mm':travel,'no_load_minimum_motor_on_s':minimum_on,
          'minimum_cycle_time_if_20percent_window_s':minimum_on/.2,'minimum_rest_s':minimum_on/.2-minimum_on,
          'scope':'Minimum times assuming full no-load4.8mm/s, ignoring acceleration/reversal. Loaded times grow.20% catalog does not specify a thermal averaging window; this arithmetic does not qualify a duty schedule.'})
    supply={'candidate':'MEAN WELL LRS-75-12','external':True,'catalog_nominal_V':12,'catalog_current_A':6,'catalog_power_W':72,
      'four_catalog_stall_A':4,'four_driver_quiescent_budget_A':4*.007,'worst_simultaneous_input_scenario_A':4+4*.007,
      'planning_margin_factor':1.25,'planned_input_A':(4+4*.007)*1.25,
      'typical_four_Hbridge_conduction_W_at1A':4*.2,'thermal_note':'0.2ohm is typical specified-condition bridge resistance, not a guaranteed hot12V value. Bridge loss is part of VM*I, do not add it again to 48W motor-branch input.',
      'regen_test_case_J':[.05,.5,2,10],'C_required_12_to_15V_uF':[2*x/(15**2-12**2)*1e6 for x in [.05,.5,2,10]],
      'energy_1000uF_12_to_15V_J':.5*.001*(15**2-12**2),
      'not_selected':['mains/branch fuse and wire size','12V regen/clamp hardware','actual hot PCB thermal path','head power connector and cable length'],
      'scope':'Fault/start-current planning, not sustained stall operation. No sink capability is assumed for the AC/DC source.15V is P16 stated maximum input, not a proposed normal clamp setpoint; actual clamp must leave margin below it.'}
    # Five-wire factory connector directions are referenced to its documented
    # mating face. OUT2/black is not permanently ground on a bidirectional bridge.
    pins=[(1,'orange','feedback negative','AGND sense return'),(2,'purple','potentiometer wiper','protected ADC position input'),(3,'red','motor positive designation','Hbridge OUT1'),(4,'black','motor negative designation','Hbridge OUT2; not fixed GND'),(5,'yellow','feedback positive','3V3_A excitation')]
    with (OUT/'actuator-interface.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['factory_pin','wire_color','factory_function','proposed_board_net']);w.writerows(pins)
    result={'revision':'P16-CTRL01','status':'conditional P16 electronics branch; no completed schematic/PCB or powered validation',
      'generator_sha256':sha(Path(__file__)),'sources_sha256':sha(SOURCES),
      'mechanical_sources_sha256':{p:sha(ROOT/p) for p in ['engineering/p16_packaging_study.py','engineering/linear_finger_drive_study.py','engineering/generated/contact02-study/study.json']},
      'kinematics':{'D_mm':D,'crank_mm':A,'phase_deg':PHASE,'CAD_closed_mm':CAD_L0,'catalog_closed_mm':97,'stroke_mm':STROKE,
        'valid_angle_deg':[0,122],'inverse_branch':'68deg+asin((L²-D²-a²)/(2Da)); monotonic in0..122deg',
        'minimum_jacobian_mm_per_rad':float(j.min()),'roundtrip_max_deg':inv_err,'finite_difference_jacobian_max_mm_per_rad':fd_err,'samples':len(q),'feedback_table':rows,
        'ADC_scope':'12-bit ideal ADC across the full physical stroke using common excitation/reference. Actual end codes require per-axis calibration; this is not an accuracy or connector acceptance specification.'},
      'current_regulation':current,'duty_examples':duty,'motor_supply':supply,
      'proposed_modes':{'PMODE':'GND: PH/EN','IMODE':'Hi-Z: fixed off-time and latched OCP; no external pull-up/down unless revised','nSLEEP':'individual or shared supervised enable, external default low; hard fault latches in supervisor',
         'normal_STOP':'EN=0 means both outputs low (electrical brake), not Hi-Z. After current settles nSLEEP low gives Hi-Z; exact timing and mechanical hold require bench proof.',
         'factory_pin3_pin4':'OUT1=H/OUT2=L extends; reverse retracts according to factory color/connector diagram; verify on unloaded axis before calibration.',
         'current_is_not_force':'IPROPI cannot substitute calibrated contact force due to friction, screw efficiency and linkage changes.'},
      'conditional_topology':{'EtherCAT_nodes':8,'path':['master','J1','J2','J3','J4','J5','J6','J7','HEAD-DC'],'head_channels':4,
       'comparison':'Old4xindependent EtherCAT BLDC servo route remains12nodes; do not add both architectures. HEAD-DC requires its own process-data/ESI and MCU4brushed-loop implementation.'},
      'manufacturing_release':False}
    (OUT/'study.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'trip':current,'duty':duty,'feedback_QA':{k:v for k,v in result['kinematics'].items() if k in ['minimum_jacobian_mm_per_rad','roundtrip_max_deg','finite_difference_jacobian_max_mm_per_rad']},'supply_A':supply['planned_input_A']},indent=2))

if __name__=='__main__':main()
