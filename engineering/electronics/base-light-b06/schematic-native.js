// SPDX-License-Identifier: CC-BY-NC-4.0
// Recreate only this new schematic's circuit; preserve title block. Full library items
// retain required footprint association; never copy PCB Footprint display titles.
const nets=__CLI__.args.nets;
const specs=[
['LED1','LTST-C170KFKT',400,700],['LED2','LTST-C170KFKT',700,700],['LED3','LTST-C170KFKT',1000,700],
['R1','RC0603FR-07470RL',400,600],['R2','RC0603FR-07470RL',700,600],['R3','RC0603FR-07470RL',1000,600],
['R4','RC0603FR-071KL',600,250],['R5','RC0603FR-0747KL',850,250],
['Q1','DMG2302UK-7',850,450],['D1','NSVBAT54HT1G',400,250],
['J1','BM03B-GHS-TBT',180,450],['C1','CC0603KRX7R8BB104',600,450]
];
const all=await eda.sch_PrimitiveComponent.getAll();
if(all.filter(x=>x.designator).some(x=>!nets[x.designator]))throw Error('Unexpected component; stop');
await eda.sch_PrimitiveWire.delete((await eda.sch_PrimitiveWire.getAll()).map(x=>x.primitiveId));
await eda.sch_PrimitiveComponent.delete(all.filter(x=>x.componentType!=='sheet').map(x=>x.primitiveId));
const items={};
for(const [d,key,x,y] of specs){
 if(!items[key]){const found=await eda.lib_Device.search(key);items[key]=found.find(p=>p.name===key || p.name===key+'(LF)(SN)');}
 if(!items[key])throw Error('Library exact name '+key);
 const p=await eda.sch_PrimitiveComponent.create(items[key],x,y,undefined,0,false,true,true);
 // Preserve the native Footprint UUID/reference. Only populate properties which
 // already exist on the schematic instance; the PCB title is not that reference.
 const safe={};
 for(const prop of Object.keys(p.otherProperty||{})){
  if(prop!=='Footprint' && items[key].otherProperty?.[prop]!==undefined)
   safe[prop]=items[key].otherProperty[prop];
 }
 await eda.sch_PrimitiveComponent.modify(p.primitiveId,{designator:d,uniqueId:'B06LIGHT-'+d,otherProperty:{...p.otherProperty,...safe}});
 for(const pin of await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(p.primitiveId)){
  const net=nets[d][pin.pinNumber];let px=pin.x,py=pin.y;const line=[px,py];
  if(d==='J1'&&pin.pinNumber==='1'){px-=30;py+=65;line.push(px,pin.y,px,py);}
  else if(d==='J1'&&pin.pinNumber==='3'){px-=50;py-=65;line.push(px,pin.y,px,py);}
  else{const a=pin.rotation*Math.PI/180;px+=40*Math.cos(a);py+=40*Math.sin(a);line.push(px,py);}
  if(!await eda.sch_PrimitiveWire.create(line,net))throw Error('Wire '+d);
  if(!await eda.sch_PrimitiveComponent.createNetPort('BI',net,px,py,pin.rotation))throw Error('Net '+net);
 }
}
return {saved:await eda.sch_Document.save(),drc:await eda.sch_Drc.check(true,false,true),components:(await eda.sch_PrimitiveComponent.getAll()).filter(x=>x.designator)};
