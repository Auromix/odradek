/* SPDX-License-Identifier: CC-BY-NC-4.0
 * Conditional gravity bookkeeping. No dynamic or continuous-holding rating.
 */
'use strict';
const fs=require('fs'),path=require('path'),M=require('../arm_a05/model.js');
const root=path.resolve(__dirname,'../..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const layout=read('engineering/parameters/arm-a05-layout.json');
const budget=read('engineering/parameters/arm-a06-load-budget.json');
const qdd=read('docs/engineering/sources/arm-a04-qdd.json');
const rating=layout.joints.map(j=>qdd.actuators.find(a=>a.model==='RobStride'+j.model.slice(2)).rated_torque_Nm);

function ledger(scenario) {
 const s={...budget.reference_scenario,...scenario};
 return [
  ...layout.joints.map((j,i)=>({id:j.id+'_motor',category:'actuator',frame:j.id+'.fixed',owner:i,mass_kg:j.mass_kg,com_mm:j.motor_center})),
  ...budget.structure_groups.map(b=>({...b,category:'structure_budget',owner:M.rigidOwner(b.frame),mass_kg:b.mass_kg*s.structure_scale})),
  {id:'detachable_head',category:'head',frame:'head',owner:7,mass_kg:s.head_kg,com_mm:s.head_com_in_head_mm},
  {id:'net_workpiece',category:'workpiece',frame:'tcp',owner:7,mass_kg:s.payload_kg,com_mm:s.payload_com_in_tcp_mm}
 ];
}
function evaluate(q,scenario={},includeCategory=null) {
 const state=M.fk(layout,q),entries=ledger(scenario).filter(b=>!includeCategory||includeCategory.includes(b.category)).map(b=>({...b,world_com_m:M.mul(M.point(state.frames[b.frame],b.com_mm),.001),force_N:M.mul(budget.gravity_m_s2,b.mass_kg)}));
 let downstreamForce=[0,0,0],downstreamMoment=[0,0,0],nextOrigin=null;
 const axes=Array(7);
 for(let i=6;i>=0;i--) {
  const joint=state.joints[i],origin=M.mul(joint.p,.001),own=entries.filter(b=>b.owner===i+1);
  let force=[...downstreamForce],moment=nextOrigin?M.add(downstreamMoment,M.cross(M.sub(nextOrigin,origin),downstreamForce)):[0,0,0];
  for(const b of own){force=M.add(force,b.force_N);moment=M.add(moment,M.cross(M.sub(b.world_com_m,origin),b.force_N));}
  const drive=-M.dot(joint.axis,moment),axialForce=M.dot(joint.axis,force),axialMoment=M.dot(joint.axis,moment);
  // Independent direct summation of every downstream point mass.
  let directF=[0,0,0],directM=[0,0,0];
  for(const b of entries.filter(b=>b.owner>=i+1)){directF=M.add(directF,b.force_N);directM=M.add(directM,M.cross(M.sub(b.world_com_m,origin),b.force_N));}
  if(M.norm(M.sub(force,directF))>1e-9||M.norm(M.sub(moment,directM))>1e-9)throw Error('Recursive/direct mismatch '+joint.id);
  axes[i]={joint:joint.id,holding_torque_Nm:drive,abs_holding_torque_Nm:Math.abs(drive),force_world_N:force,moment_world_Nm:moment,axial_force_abs_N:Math.abs(axialForce),radial_force_N:M.norm(M.sub(force,M.mul(joint.axis,axialForce))),bending_moment_Nm:M.norm(M.sub(moment,M.mul(joint.axis,axialMoment))),catalog_rated_torque_Nm:rating[i],catalog_ratio:Math.abs(drive)/rating[i]};
  downstreamForce=force;downstreamMoment=moment;nextOrigin=origin;
 }
 return {angles_deg:q,head_mm:state.head,tcp_mm:state.tcp,total_model_mass_kg:entries.reduce((s,b)=>s+b.mass_kg,0),axes,entries};
}
function potential(q,scenario) {
 const state=M.fk(layout,q);
 return ledger(scenario).reduce((s,b)=>s-M.dot(budget.gravity_m_s2,M.mul(M.point(state.frames[b.frame],b.com_mm),.001))*b.mass_kg,0);
}
function verifyVirtualWork(q,scenario) {
 const r=evaluate(q,scenario),h=1e-5,degree=h*180/Math.PI;
 return r.axes.map((a,i)=>{const plus=q.slice(),minus=q.slice();plus[i]+=degree;minus[i]-=degree;const derivative=(potential(plus,scenario)-potential(minus,scenario))/(2*h),err=Math.abs(derivative-a.holding_torque_Nm);if(err>1e-6)throw Error('Virtual-work mismatch '+a.joint+': '+err);return err;});
}
function halton(n,b){let v=0,f=1;while(n>0){f/=b;v+=f*(n%b);n=Math.floor(n/b);}return v;}
const summary=r=>({angles_deg:r.angles_deg,head_mm:r.head_mm,tcp_mm:r.tcp_mm,total_model_mass_kg:r.total_model_mass_kg,axes:r.axes});
function main() {
 const nominal=budget.reference_scenario,parts=M.bodies(layout);
 const poses=Object.fromEntries(Object.entries(layout.poses).map(([name,q])=>[name,summary(evaluate(q,nominal))]));
 const virtualWorkErrors=Object.values(layout.poses).flatMap(q=>verifyVirtualWork(q,nominal));
 // A tilted, eccentric case exercises all gravity-sensitive axes.
 virtualWorkErrors.push(...verifyVirtualWork([23,55,35,-85,68,24,42],{...nominal,payload_com_in_tcp_mm:[20,50,10],head_com_in_head_mm:[0,0,20]}));
 const scenarios=[];
 for(const payload_kg of budget.sensitivity.payload_kg)for(const head_kg of budget.sensitivity.head_kg)for(const structure_scale of budget.sensitivity.structure_scale){const s={...nominal,payload_kg,head_kg,structure_scale};scenarios.push({scenario:s,reference:summary(evaluate(layout.poses.reference,s))});}
 const candidates=Object.entries(layout.poses).map(([name,q])=>({name,q}));
 for(let k=0;k<budget.sampling.preset_transition_samples;k++){const t=k/(budget.sampling.preset_transition_samples-1);candidates.push({name:'idle_attention_'+k,q:layout.poses.idle.map((a,i)=>a+(layout.poses.attention[i]-a)*t)});}
 for(let k=1;k<=budget.sampling.halton_count;k++)candidates.push({name:'halton_'+k,q:layout.joints.map((j,i)=>j.limits_deg[0]+halton(k,budget.sampling.basis[i])*(j.limits_deg[1]-j.limits_deg[0]))});
 const maxes=()=>Array.from({length:7},()=>({abs_holding_torque_Nm:-1}));
 const rawMax=maxes(),acceptedMax=maxes();let accepted=0;
 const exampleFailures=[];
 for(const c of candidates){
  const r=evaluate(c.q,nominal),check=M.checks(layout,c.q,parts),valid=check.conflicts.length===0;
  if(valid)accepted++;
  for(let i=0;i<7;i++)for(const [arr,enabled]of [[rawMax,true],[acceptedMax,valid]])if(enabled&&r.axes[i].abs_holding_torque_Nm>arr[i].abs_holding_torque_Nm)arr[i]={...r.axes[i],pose_name:c.name,angles_deg:c.q,proxy_conflicts:check.conflicts,tcp_mm:r.tcp_mm};
  if(valid&&exampleFailures.length<8&&r.axes.some(a=>a.catalog_ratio>1))exampleFailures.push({name:c.name,...summary(r)});
 }
 const j7=[];
 for(const payload_kg of [0.5,1,2])for(const eccentricity_mm of [0,50,100]){const r=evaluate(layout.poses.reference,{...nominal,payload_kg,payload_com_in_tcp_mm:[0,eccentricity_mm,0]});j7.push({payload_kg,eccentricity_mm,head_kg:nominal.head_kg,axis:r.axes[6]});}
 const comScenarios=[];
 for(const x of [0,50,100])for(const y of [0,50])comScenarios.push({payload_com_in_tcp_mm:[x,y,0],reference:summary(evaluate(layout.poses.reference,{...nominal,payload_com_in_tcp_mm:[x,y,0]}))});
 const headEccentricity={assumed_radial_offset_mm:20,head_mass_kg:nominal.head_kg,additional_roll_gravity_torque_upper_bound_Nm:nominal.head_kg*9.81*.020,note:'Triangle-inequality bound over gravity orientation. Not a measured head COM. Nominal whole-arm scan assumes centred COM.'};
 const categories=['head','workpiece'];
 const subtotal={head_and_workpiece:summary(evaluate(layout.poses.reference,nominal,categories)),plus_actuators:summary(evaluate(layout.poses.reference,nominal,[...categories,'actuator'])),plus_structure_budget:poses.reference};
 const report={id:'ARM-A06-GRAVITY',date:budget.date,geometry_source:budget.geometry,reference_scenario:nominal,method:'World-frame static wrench recursion J7 to J1, independently checked by direct summation and finite-difference potential-energy derivative. SI internally.',limits:budget.limitations,ledger:ledger(nominal),presets:poses,reference_subtotals:subtotal,sensitivity:scenarios,sensitivity_scope:'Mass sensitivity and payload COM cases are at reference pose only; sample maxima apply only to reference_scenario.',payload_com_scenarios:comScenarios,j7_offset_scenarios:j7,head_eccentricity_bound:headEccentricity,sampled_gravity:{candidate_count:candidates.length,halton_count:budget.sampling.halton_count,proxy_collision_clear_count:accepted,note:'Finite sample maxima, not global maxima or certified safe workspace; separate joints reach maxima at different poses.',unfiltered_maxima:rawMax,proxy_clear_maxima:acceptedMax,examples_above_catalog_torque:exampleFailures},verification:{recursive_matches_direct:true,max_virtual_work_error_Nm:Math.max(...virtualWorkErrors),current_model_J1_gravity_torque_zero:acceptedMax[0].abs_holding_torque_Nm<1e-9}};
 const output=path.join(root,'docs/engineering/analysis/arm-a06-gravity.json');fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
 const csv=['scenario,payload_kg,head_kg,structure_scale,joint,holding_torque_Nm,bending_moment_Nm,axial_force_N,radial_force_N'];
 for(const [name,r]of Object.entries(poses))for(const a of r.axes)csv.push([name,nominal.payload_kg,nominal.head_kg,nominal.structure_scale,a.joint,a.holding_torque_Nm,a.bending_moment_Nm,a.axial_force_abs_N,a.radial_force_N].join(','));
 fs.writeFileSync(path.join(root,'docs/engineering/analysis/arm-a06-preset-loads.csv'),csv.join('\n')+'\n');
 console.log(JSON.stringify({reference:poses.reference.axes.map(a=>({joint:a.joint,torque:a.holding_torque_Nm,bending:a.bending_moment_Nm,ratio:a.catalog_ratio})),model_mass:poses.reference.total_model_mass_kg,sample_count:candidates.length,proxy_clear:accepted,maxima:acceptedMax.map(a=>({joint:a.joint,torque:a.abs_holding_torque_Nm,pose:a.pose_name,ratio:a.catalog_ratio})),verification:report.verification},null,2));
}
if(require.main===module)main();
module.exports={evaluate,ledger,potential,verifyVirtualWork,layout,budget};
