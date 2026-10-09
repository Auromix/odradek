// SPDX-License-Identifier: CC-BY-NC-4.0
// Execute inside the activated JLCEDA editor via the project's MCP adapter.
// Units: API mil; route specification below in mm. Guarded first application only.
await eda.dmt_EditorControl.openDocument('52caa9452ee66dee');
const old = await eda.pcb_PrimitiveLine.getAll();
if (old.some(x=>[1,2,15,16].includes(x.layer))) throw Error('Copper lines exist; do not duplicate routes');
const pads = await eda.pcb_PrimitivePad.getAll();
const p = id => { const q=pads.find(x=>x.primitiveId===id); if(!q)throw Error('Missing '+id);return [q.x*.0254,-q.y*.0254]; };
const a=p('ie0ie4'), b=p('ie0ie7');
if(Math.abs(a[0]-100.30968)>.001||Math.abs(b[0]-92.68968)>.001)throw Error('Header datum changed');
for(const [id,net] of [['ie0ie4','VIN48'],['ie0ie5','VIN48'],['ie0ie6','VIN48'],['ie64ie4','VIN48'],['ie64ie5','VIN48'],['ie64ie6','VIN48'],['ie64ie7','VIN48'],['ie0ie7','RETURN48'],['ie0ie8','RETURN48'],['ie0ie9','RETURN48'],['ie56ie4','RETURN48'],['ie56ie5','RETURN48'],['ie56ie6','RETURN48'],['ie56ie7','RETURN48']]) if(pads.find(x=>x.primitiveId===id)?.net!==net)throw Error('Net mismatch '+id);
const vinL=p('ie64ie4'),vinLB=p('ie64ie5'),vinR=p('ie64ie6'),vinRB=p('ie64ie7');
const retL=p('ie56ie4'),retLB=p('ie56ie5'),retR=p('ie56ie6'),retRB=p('ie56ie7');
const routes=[
{net:'VIN48',points:[a,[a[0],vinLB[1]],vinLB,vinL,vinR,vinRB,[a[0],vinRB[1]]]},
{net:'RETURN48',points:[b,[b[0],20],[retRB[0],20-(b[0]-retRB[0])],retRB,retLB,retL,retR,retRB]}
];
const created=[];
try {
 for(const layer of [1,2]) for(const r of routes) for(let i=1;i<r.points.length;i++){
 const s=r.points[i-1],t=r.points[i];
 const obj=await eda.pcb_PrimitiveLine.create(r.net,layer,s[0]/.0254,-s[1]/.0254,t[0]/.0254,-t[1]/.0254,2.4/.0254,false);
 if(!obj)throw Error('Failed line creation');created.push(obj.primitiveId);
 }
 await eda.pcb_PrimitiveString.modify('ie98',{text:'B06 IO / POWER ROUTED'});
 const saved=await eda.pcb_Document.save();
 if(!saved)throw Error('Save failed');
 return {saved,created,routes,width_mm:2.4,layers:[1,2],pads:await eda.pcb_PrimitivePad.getAll(),lines:await eda.pcb_PrimitiveLine.getAll(),rules:await eda.pcb_Drc.getCurrentRuleConfiguration(),drc:await eda.pcb_Drc.check(true,false,true)};
} catch(err){
 // The editor splits long lines at pads and replaces their primitive IDs.
 const beforeIds=new Set(old.map(x=>x.primitiveId));
 const rollback=(await eda.pcb_PrimitiveLine.getAll()).filter(x=>!beforeIds.has(x.primitiveId)).map(x=>x.primitiveId);
 await eda.pcb_PrimitiveLine.delete(rollback);
 await eda.pcb_PrimitiveString.modify('ie98',{text:'B06 IO FIT / UNROUTED'});
 await eda.pcb_Document.save();
 throw err;
}
