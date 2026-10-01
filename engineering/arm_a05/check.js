/* SPDX-License-Identifier: CC-BY-NC-4.0 */
'use strict';
const fs=require('fs'),path=require('path'),M=require('./model.js');
const root=path.resolve(__dirname,'../..'),layout=JSON.parse(fs.readFileSync(path.join(root,'engineering/parameters/arm-a05-layout.json'),'utf8'));
const parts=M.bodies(layout),samples=[],presetChecks=[];
for(const [name,q]of Object.entries(layout.poses)){const c=M.checks(layout,q,parts);presetChecks.push({name,c});samples.push({name,angles_deg:q,head_mm:c.state.head,tcp_mm:c.state.tcp,conflicts:c.conflicts,table_min_mm:c.tableMinMm});}
const transition=[],transitionChecks=[];for(let k=0;k<=100;k++){const t=k/100,q=layout.poses.idle.map((a,i)=>a+(layout.poses.attention[i]-a)*t),c=M.checks(layout,q,parts);transitionChecks.push({t,q,c});if(c.conflicts.length)transition.push({t,q,conflicts:c.conflicts});}
const negative=layout.poses.idle.slice();negative[5]=-60;const bad=M.checks(layout,negative,parts);
const shoulderZero=M.fk(layout,[0,0,0,0,0,0,0]);
if(shoulderZero.joints[2].p[2]<=shoulderZero.joints[1].p[2])throw Error('J2 displayed zero must put upper arm upright');
const roll=layout.poses.reference.slice();roll[6]=45;const a=M.fk(layout,layout.poses.reference),b=M.fk(layout,roll);
if(M.norm(M.sub(a.tcp,b.tcp))>1e-8)throw Error('On-axis TCP must be invariant under J7 roll');
const tableWitness=M.checks(layout,roll,parts);
if(!(tableWitness.tableMinMm<0&&tableWitness.conflicts.some(x=>x.a==='桌面')))throw Error('J7 roll must detect the known petal-table sweep despite invariant TCP');
if(!bad.conflicts.length)throw Error('Known negative-yaw collision was not detected');
// Reuse the same checks as the live viewer; do not recompute pair sets offline.
const roles=new Map(parts.map(p=>[p.id,p.role]));
const bracketMotor=presetChecks.flatMap(({name,c})=>c.bracketConflicts.filter(x=>roles.get(x.a)==='motor'||roles.get(x.b)==='motor').map(x=>({pose:name,...x})));
const bracketPresets=presetChecks.map(({name,c})=>({name,conflicts:c.bracketConflicts,table_min_mm:c.bracketTableMinMm}));
const bracketTransition=transitionChecks.filter(x=>x.c.bracketConflicts.length).map(({t,q,c})=>({t,q,conflicts:c.bracketConflicts}));
const bracketTransitionTableMin=Math.min(...transitionChecks.map(x=>x.c.bracketTableMinMm));
// Regression witnesses: restore each old fixed cheek independently. Each must
// be detected against its rotating carrier; no blanket support exemption.
const bracketRegression=[];
for(const [id,oldY,other]of [['shoulder-idler-cheek',-42,'shoulder-output--1'],['elbow-idler-cheek',107,'forearm-link'],['wrist-pitch-idler',-54,'wrist-open-cheek--1']]){
 const oldParts=M.bodies(layout),b=oldParts.find(p=>p.id===id);b.center[1]=oldY;
 const c=M.checks(layout,layout.poses.idle,oldParts),hit=c.bracketConflicts.find(x=>(x.a===id&&x.b===other)||(x.a===other&&x.b===id));
 if(!hit)throw Error('Known fixed/rotating bracket interference was not detected: '+id);
 bracketRegression.push({restored_id:id,old_y_mm:oldY,conflict:hit});
}
const report={id:'ARM-A05-PROXY-CHECK',units:'mm',method:'Conservative convex SAT; cylinders circumscribed by 16-sided prisms. Only sampled poses and declared pair sets. overlap_mm is a proxy SAT overlap, not an exact CAD penetration depth.',scope:presetChecks[0].c.checkedScope,poses:samples,transition:{samples:101,conflicting_samples:transition},bracket_motor_at_presets:bracketMotor,cross_carrier_brackets:{scope:'Every checked pair involving a bracket on different rigid carriers, plus bracket-table; same-carrier joins excluded. Included in live viewer checks; offline report reuses those results.',presets:bracketPresets,transition:{samples:101,conflicting_samples:bracketTransition,table_min_mm:bracketTransitionTableMin},regression_witnesses:bracketRegression},negative_yaw_witness:{angles:negative,conflicts:bad.conflicts},table_witness:{angles_deg:roll,tcp_mm:tableWitness.state.tcp,tcp_delta_from_reference_mm:M.norm(M.sub(a.tcp,b.tcp)),table_min_mm:tableWitness.tableMinMm,conflicts:tableWitness.conflicts},limitations:['Not an exact vendor CAD collision test.','No complete bolt, bearing, flange, connector, assembly-tool or flex-harness collision model.','Positive samples do not prove unsampled motions safe.','No load, thermal or physical validation.']};
const out=path.join(root,'docs/engineering/analysis/arm-a05-packaging-check.json');fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
fs.mkdirSync(path.join(root,'work/arm-a05'),{recursive:true});fs.writeFileSync(path.join(root,'work/arm-a05/scene.json'),JSON.stringify({layout,parts,cables:M.cableReservations()},null,2));
console.log(JSON.stringify({presets:samples.map(x=>({name:x.name,conflicts:x.conflicts.length})),transition_failures:transition.length,bracket_motor_overlaps:bracketMotor.length,cross_carrier_bracket_presets:bracketPresets.map(x=>({name:x.name,conflicts:x.conflicts.length})),cross_carrier_bracket_transition_failures:bracketTransition.length,negative_test:bad.conflicts.map(x=>[x.a,x.b]),table_witness_min_mm:tableWitness.tableMinMm},null,2));
if(samples.some(x=>x.conflicts.length)||transition.length||bracketMotor.length||bracketPresets.some(x=>x.conflicts.length)||bracketTransition.length)process.exitCode=1;
