// SPDX-License-Identifier: CC-BY-NC-4.0
// Guarded incremental operation on the placed controller, not a full replay.
const old=await eda.pcb_PrimitiveLine.getAll();
if(old.length!==275 || (await eda.pcb_PrimitiveVia.getAll()).length!==22 || (await eda.pcb_PrimitivePad.getAll()).length!==121)throw Error('Unexpected controller routing baseline');
const removed=old.filter(l=>__CLI__.args.removed_lines.includes(l.primitiveId));
if(removed.length!==4 || removed.some(l=>l.net!=='LAMP5V'))throw Error('Unexpected power branch');
const lineIds=[],viaIds=[];
try {
 if(!await eda.pcb_PrimitiveLine.delete(removed.map(l=>l.primitiveId)))throw Error('Remove branch');
 for(const v of __CLI__.args.vias) {
  const p=await eda.pcb_PrimitiveVia.create(v.net,v.point[0]/.0254,-v.point[1]/.0254,v.hole_mm/.0254,v.diameter_mm/.0254);
  if(!p)throw Error('Via');viaIds.push(p.primitiveId);
 }
 for(const r of __CLI__.args.routes)for(let i=1;i<r.points.length;i++) {
  const a=r.points[i-1],b=r.points[i];
  const p=await eda.pcb_PrimitiveLine.create(r.net,r.layer,a[0]/.0254,-a[1]/.0254,b[0]/.0254,-b[1]/.0254,r.width_mm/.0254,false);
  if(!p)throw Error('Line');lineIds.push(p.primitiveId);
 }
 const saved=await eda.pcb_Document.save();if(!saved)throw Error('Save');
 return {saved,created_lines:lineIds,created_vias:viaIds,drc:await eda.pcb_Drc.check(true,false,true)};
} catch(error) {
 if(lineIds.length)await eda.pcb_PrimitiveLine.delete(lineIds);
 if(viaIds.length)await eda.pcb_PrimitiveVia.delete(viaIds);
 for(const l of removed)await eda.pcb_PrimitiveLine.create(l.net,l.layer,l.startX,l.startY,l.endX,l.endY,l.lineWidth,false);
 await eda.pcb_Document.save();throw error;
}
