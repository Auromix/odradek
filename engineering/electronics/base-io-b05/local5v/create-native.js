// SPDX-License-Identifier: CC-BY-NC-4.0
// Adds the local lamp supply to the authoritative IO board. One-shot; never
// recreates legacy connectors or changes the EtherCAT route.
const PCB='52caa9452ee66dee', SCH='30968987fbc1647d';
const LIB='0819f05c4eef4c71ace90d822a990e87';
const specs=[
 ['U1','7435655a6b43434e9a8cb29b7399d473',62,18,0,400,100],
 ['F1','af094a2c26454541b57a03036fed447c',94,25,0,100,100],
 ['D1','669c793c5f594243bbca92340a194036',81,25,0,250,100],
 ['C1','56ead569f8974eb08e18d051c05f9d10',73,24,90,250,300],
 ['C2','bf579cce8b8c4c2abcab285bf1ff247a',60,27,90,550,100],
 ['R1','69006d078db14035b49e0276377f90ea',60,32,90,700,100],
 ['J7','fa20194ac1624d79b3182946f68bae4b',73,32,0,900,100]
];
const items={};
for(const [d,id] of specs){items[d]=await eda.lib_Device.get(id,LIB);if(!items[d]||items[d].uuid!==id)throw Error('Library '+d);}
await eda.dmt_EditorControl.openDocument(PCB);
const old=await eda.pcb_PrimitiveComponent.getAll();
if(old.length!==12 || !old.some(c=>c.designator==='J1'&&c.primitiveId==='ie48'))throw Error('Wrong or modified IO PCB');
const out={pcb:[],sch:[]};
for(const [d,id,u,v,r] of specs){
 const c=await eda.pcb_PrimitiveComponent.create(items[d],1,u/.0254,-v/.0254,r,false);
 if(!c)throw Error('PCB create '+d);
 await eda.pcb_PrimitiveComponent.modify(c.primitiveId,{designator:d,uniqueId:'B06LOCAL5V-'+d,addIntoBom:true,manufacturer:items[d].manufacturer,manufacturerId:items[d].manufacturerId,supplier:items[d].supplier,supplierId:items[d].supplierId});
 out.pcb.push({d,component:await eda.pcb_PrimitiveComponent.get(c.primitiveId),pins:await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)});
}
out.pcbSave=await eda.pcb_Document.save();
await eda.dmt_EditorControl.openDocument(SCH);
if((await eda.sch_PrimitiveComponent.getAll()).some(c=>specs.some(s=>s[0]===c.designator)))throw Error('Supply SCH already exists');
for(const [d,id,u,v,r,x,y] of specs){
 const c=await eda.sch_PrimitiveComponent.create(items[d],x,y,undefined,0,false,true,true);
 if(!c)throw Error('SCH create '+d);
 const safe={};for(const prop of Object.keys(c.otherProperty||{})){if(prop!=='Footprint'&&items[d].otherProperty?.[prop]!==undefined)safe[prop]=items[d].otherProperty[prop];}
 await eda.sch_PrimitiveComponent.modify(c.primitiveId,{designator:d,uniqueId:'B06LOCAL5V-'+d,manufacturer:items[d].manufacturer,manufacturerId:items[d].manufacturerId,supplier:items[d].supplier,supplierId:items[d].supplierId,otherProperty:{...c.otherProperty,...safe}});
 out.sch.push({d,component:await eda.sch_PrimitiveComponent.get(c.primitiveId),pins:await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)});
}
out.schSave=await eda.sch_Document.save();
return out;
