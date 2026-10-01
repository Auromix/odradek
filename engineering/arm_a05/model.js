/* SPDX-License-Identifier: CC-BY-NC-4.0
 * A05 shared kinematics and conservative convex-envelope checks. Units: mm.
 * No physics, thermal, fatigue, connector-contact or cable-life claims.
 */
(function (scope) {
  'use strict';
  const add=(a,b)=>a.map((x,i)=>x+b[i]), sub=(a,b)=>a.map((x,i)=>x-b[i]);
  const mul=(a,s)=>a.map(x=>x*s), dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const norm=a=>Math.hypot(...a), unit=a=>mul(a,1/(norm(a)||1));
  const I=[1,0,0,0,1,0,0,0,1];
  const mv=(r,v)=>[dot(r.slice(0,3),v),dot(r.slice(3,6),v),dot(r.slice(6,9),v)];
  const mm=(a,b)=>Array.from({length:9},(_,k)=>{const row=Math.floor(k/3),col=k%3;return a[row*3]*b[col]+a[row*3+1]*b[col+3]+a[row*3+2]*b[col+6];});
  function rotation(axis,deg) {
    const [x,y,z]=unit(axis),a=deg*Math.PI/180,c=Math.cos(a),s=Math.sin(a),t=1-c;
    return [t*x*x+c,t*x*y-s*z,t*x*z+s*y,t*x*y+s*z,t*y*y+c,t*y*z-s*x,t*x*z-s*y,t*y*z+s*x,t*z*z+c];
  }
  const point=(t,p)=>add(t.p,mv(t.r,p));
  const frame=(base,p,r=I)=>({p:point(base,p),r:mm(base.r,r)});
  function fk(layout,angles) {
    const f={world:{p:[0,0,0],r:I}}, joints=[]; let parent=f.world;
    layout.joints.forEach((j,i)=>{
      const fixed=frame(parent,j.offset),rotor=frame(fixed,[0,0,0],rotation(j.axis,angles[i]+j.zero_deg));
      f[j.id+'.fixed']=fixed;f[j.id+'.rotor']=rotor;parent=rotor;
      joints.push({id:j.id,p:fixed.p,axis:mv(fixed.r,j.axis)});
    });
    f.head=frame(parent,layout.head_offset_mm);f.tcp=frame(f.head,layout.tcp_offset_mm);
    return {frames:f,joints,head:f.head.p,tcp:f.tcp.p};
  }
  function bodies(layout) {
    const result=[];
    const cyl=(id,frame,c,axis,r,l,role,extra={})=>result.push({id,frame,center:c,axis,r,length:l,kind:'cylinder',role,...extra});
    const box=(id,frame,c,size,role,extra={})=>result.push({id,frame,center:c,size,kind:'box',role,...extra});
    const beam=(id,frame,a,b,r,role='structure',extra={})=>cyl(id,frame,mul(add(a,b),.5),unit(sub(b,a)),r,norm(sub(b,a)),role,extra);
    layout.joints.forEach((j,i)=>cyl(j.id+'-motor',j.id+'.fixed',j.motor_center,j.axis,j.diameter_mm/2,j.length_mm,'motor',{joint:i}));
    cyl('fixed-datum','world',[0,0,16],[0,0,1],78,32,'base');
    // Structure is an explicit packaging proposal, not manufacturer flange CAD.
    beam('shoulder-pedestal','J1.rotor',[0,0,8],[0,0,20],27,'structure',{ignoreMotors:[0,1]});
    beam('shoulder-pedestal-brace','J1.rotor',[0,0,20],[-74,25,55],12,'bracket');
    box('shoulder-crossbar','J1.rotor',[-74,26,55],[14,196,34],'bracket');
    beam('shoulder-drive-cheek','J1.rotor',[-74,124,55],[0,124,85],7,'bracket');
    // Keep fixed idler cheeks axially outside the rotating output cheeks.
    // Bearings, trunnions and mating faces remain unresolved interface volumes.
    beam('shoulder-idler-cheek','J1.rotor',[-74,-64,55],[0,-64,85],8,'bracket');
    [-1,1].forEach(s=>beam('shoulder-output-'+s,'J2.rotor',[0,s*46,0],[64,s*46,0],7,'bracket'));
    box('shoulder-output-bridge','J2.rotor',[64,0,0],[12,104,20],'bracket');
    beam('upper-link','J3.rotor',[35,0,0],[89,0,0],20,'structure',{ignoreMotors:[2,3]});
    // Elbow output is offset from the upper-arm plane; a separate idler carrier is required.
    cyl('elbow-output-adapter','J4.rotor',[0,59,0],[0,1,0],18,57,'bracket');
    beam('forearm-link','J4.rotor',[12,90,0],[142,90,0],19,'structure',{ignoreMotors:[3,4]});
    beam('elbow-idler-backbone','J4.fixed',[-66,0,-26],[-66,120,-26],7,'bracket');
    beam('elbow-idler-cheek','J4.fixed',[-66,120,-26],[0,120,0],7,'bracket');
    beam('wrist-pitch-carrier-root','J5.fixed',[-62,0,0],[-35,0,0],14,'bracket');
    beam('wrist-pitch-drive-carrier','J5.fixed',[-55,0,0],[-55,114,0],7,'bracket');
    beam('wrist-pitch-drive-ear','J5.fixed',[-55,114,0],[0,114,0],7,'bracket');
    beam('wrist-pitch-idler','J5.fixed',[-40,-60,0],[0,-60,0],7,'bracket');
    [-1,1].forEach(s=>{
      beam('wrist-open-cheek-'+s,'J5.rotor',[0,s*41.5,0],[55,s*41.5,0],6,'bracket');
      beam('yaw-stator-cheek-'+s,'J5.rotor',[55,s*51,0],[55,s*51,106],6,'bracket');
    });
    box('yaw-stator-back-bridge','J6.fixed',[0,0,106],[25,114,10],'bracket');
    box('yaw-output-saddle','J6.rotor',[17,0,23],[34,48,8],'bracket');
    cyl('yaw-output-hub','J6.rotor',[0,0,35],[0,0,1],16,28,'bracket');
    cyl('roll-rear-adapter','J7.fixed',[-31,0,0],[1,0,0],25,8,'bracket');
    cyl('head-quick-interface','J7.rotor',[29,0,0],[1,0,0],25,6,'bracket');
    cyl('head-back','head',[-12,0,0],[1,0,0],56,35,'head');
    cyl('head-display','head',[13,0,0],[1,0,0],46,10,'display',{check:false});
    const upper=[[63,27],[96,31],[106,64],[193,112],[201,133],[190,145],[98,110],[70,75]];
    const lower=[[58,-30],[86,-42],[164,-105],[169,-122],[156,-125],[78,-78],[56,-60]];
    [1,-1].forEach(s=>[upper,lower].forEach((p,k)=>result.push({id:`petal-${s}-${k}`,frame:'head',kind:'petal',center:[0,0,0],polygon:p.map(([y,z])=>[s*y,z]),depth:14,role:'head'})));
    [1,-1].forEach(s=>{const axis=mv(rotation([0,1,0],-s*12),[1,0,0]);cyl('camera-'+s,'head',add([8,0,s*73],mul(axis,8)),axis,23,51,'head');});
    return result;
  }
  function cableReservations() {
    return {
      segments:[
        {frame:'J1.rotor',points:[[-62,0,0],[-72,0,30],[-70,-40,60],[0,-54,85]]},
        {frame:'J2.rotor',points:[[0,-54,0],[40,-64,0],[100,-64,0],[143,-45,0],[150,0,0]]},
        {frame:'J3.rotor',points:[[34,-64,0],[62,-55,0],[110,-38,0],[150,-38,0]]},
        {frame:'J4.rotor',points:[[0,100,0],[40,104,0],[100,90,0],[140,52,0],[180,-54,0]]},
        {frame:'J5.rotor',points:[[0,-54,0],[24,-59,0],[55,-58,-35],[55,0,-54]]},
        {frame:'J6.rotor',points:[[0,0,-54],[32,-40,-48],[65,-43,-18],[95,-41,0]]},
        {frame:'J7.rotor',points:[[29,-43,0],[48,-58,0],[67,-53,0],[75,-40,0]]}
      ],
      chambers:[
        ['J1.fixed',[0,0,1],[0,0,13],65,18],['J2.fixed',[0,1,0],[0,-56,0],38,14],
        ['J3.fixed',[1,0,0],[0,0,0],65,17],['J4.fixed',[0,1,0],[0,105,0],38,14],
        ['J5.fixed',[0,1,0],[0,-58,0],38,14],['J6.fixed',[0,0,1],[0,0,-58],38,14],
        ['J7.fixed',[1,0,0],[12,0,0],45,17]
      ],
      status:'Conceptual discontinuous ducts and movement chambers; no constant-length harness solution.'
    };
  }
  function hull2(points) {
    const p=points.map(x=>[...x]).sort((a,b)=>a[0]-b[0]||a[1]-b[1]),cw=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
    const lo=[],hi=[];for(const v of p){while(lo.length>1&&cw(lo.at(-2),lo.at(-1),v)<=0)lo.pop();lo.push(v);}
    for(const v of [...p].reverse()){while(hi.length>1&&cw(hi.at(-2),hi.at(-1),v)<=0)hi.pop();hi.push(v);}return lo.slice(0,-1).concat(hi.slice(0,-1));
  }
  function poly(body) {
    let vertices=[],normals=[],edges=[];
    if(body.kind==='box') {
      for(const x of [-1,1])for(const y of [-1,1])for(const z of [-1,1])vertices.push([x*body.size[0]/2,y*body.size[1]/2,z*body.size[2]/2]);
      normals=edges=[[1,0,0],[0,1,0],[0,0,1]];
    } else if(body.kind==='petal') {
      const h=hull2(body.polygon); normals=[[1,0,0]];edges=[[1,0,0]];
      for(const x of [-body.depth/2,body.depth/2])for(const [y,z]of h)vertices.push([x,y,z]);
      h.forEach((p,i)=>{const d=sub([0,...h[(i+1)%h.length]],[0,...p]);edges.push(unit(d));normals.push(unit(cross(d,[1,0,0])));});
    } else {
      const a=unit(body.axis),u=unit(cross(a,Math.abs(a[0])<.8?[1,0,0]:[0,1,0])),v=cross(a,u),n=16,r=body.r/Math.cos(Math.PI/n);
      normals=[a];edges=[a];
      for(let k=0;k<n;k++) {
        const t=2*Math.PI*k/n,rad=add(mul(u,Math.cos(t)),mul(v,Math.sin(t)));
        vertices.push(add(mul(a,-body.length/2),mul(rad,r)),add(mul(a,body.length/2),mul(rad,r)));
        const half=t+Math.PI/n;normals.push(add(mul(u,Math.cos(half)),mul(v,Math.sin(half))));edges.push(add(mul(u,-Math.sin(half)),mul(v,Math.cos(half))));
      }
    }
    vertices=vertices.map(v=>add(v,body.center||[0,0,0]));
    return {vertices,normals,edges};
  }
  const localCache=new WeakMap();
  function worldPoly(b,frames) {
    let p=localCache.get(b);if(!p){p=poly(b);localCache.set(b,p);}const t=frames[b.frame];
    const vertices=p.vertices.map(v=>point(t,v));return {vertices,normals:p.normals.map(v=>mv(t.r,v)),edges:p.edges.map(v=>mv(t.r,v)),center:point(t,b.center||[0,0,0]),radius:Math.max(...p.vertices.map(v=>norm(sub(v,b.center||[0,0,0]))))};
  }
  function separation(a,b) {
    // SAT for convex polyhedra. Cylinders use a circumscribed 16-gon (conservative).
    let best=-Infinity;
    const axes=a.normals.concat(b.normals);
    for(const u of a.edges)for(const v of b.edges){const w=cross(u,v);if(norm(w)>1e-7)axes.push(unit(w));}
    for(const axis of axes) {
      let amin=Infinity,amax=-Infinity,bmin=Infinity,bmax=-Infinity;
      for(const p of a.vertices){const s=dot(p,axis);amin=Math.min(amin,s);amax=Math.max(amax,s);}
      for(const p of b.vertices){const s=dot(p,axis);bmin=Math.min(bmin,s);bmax=Math.max(bmax,s);}
      const gap=Math.max(bmin-amax,amin-bmax);best=Math.max(best,gap);if(gap>2)return gap;
    }return best;
  }
  function rigidOwner(frame) {
    if(frame==='world')return 0;
    if(frame==='head'||frame==='tcp')return 7;
    const m=/^J([1-7])\.(fixed|rotor)$/.exec(frame);
    if(!m)throw Error('Unknown frame ownership: '+frame);
    return Number(m[1])-(m[2]==='fixed'?1:0);
  }
  function checks(layout,q,parts) {
    const state=fk(layout,q),solids=parts.filter(b=>b.check!==false&&['motor','structure','head','bracket','base'].includes(b.role));
    const wp=new Map(solids.map(b=>[b,worldPoly(b,state.frames)]));let tableMin=Infinity,bracketTableMin=Infinity;const conflicts=[],bracketConflicts=[];
    for(const b of solids)if(b.role!=='base')for(const p of wp.get(b).vertices){tableMin=Math.min(tableMin,p[2]);if(b.role==='bracket')bracketTableMin=Math.min(bracketTableMin,p[2]);}
    for(let i=0;i<solids.length;i++)for(let j=i+1;j<solids.length;j++){
      const a=solids[i],b=solids[j];
      const bracketPair=a.role==='bracket'||b.role==='bracket';
      if(bracketPair){
        // Same-carrier joins are intentional. Across a joint there is no blanket
        // bearing-interface exemption: a fixed cheek must clear a rotating one.
        if(rigidOwner(a.frame)===rigidOwner(b.frame))continue;
      }else{
        if(a.role==='base'||b.role==='base')continue;
        if(a.role==='head'&&b.role==='head')continue;
        if(a.role==='structure'&&b.role==='structure')continue;
        if(a.role==='motor'&&b.ignoreMotors?.includes(a.joint)||b.role==='motor'&&a.ignoreMotors?.includes(b.joint))continue;
      }
      const pa=wp.get(a),pb=wp.get(b);if(norm(sub(pa.center,pb.center))>pa.radius+pb.radius+2)continue;
      const gap=separation(pa,pb);if(gap<-.25){const c={a:a.id,b:b.id,overlap_mm:-gap};conflicts.push(c);if(bracketPair)bracketConflicts.push(c);}
    }
    if(tableMin<0)conflicts.push({a:'桌面',b:'检测包络',overlap_mm:-tableMin});
    if(bracketTableMin<0)bracketConflicts.push({a:'桌面',b:'支架检测包络',overlap_mm:-bracketTableMin});
    return {state,conflicts,tableMinMm:tableMin,bracketConflicts,bracketTableMinMm:bracketTableMin,checkedScope:'motor-motor, motor-mainlink, head-motor, head-mainlink, cross-rigid-carrier bracket pairs, table; same-carrier bracket joins, declared adjacent motor-mainlink joins and cables excluded'};
  }
  const api={add,sub,mul,dot,cross,norm,unit,mv,mm,rotation,point,frame,fk,bodies,cableReservations,poly,worldPoly,separation,rigidOwner,checks};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else scope.ArmA05=api;
})(typeof window!=='undefined'?window:globalThis);
