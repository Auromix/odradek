/* SPDX-License-Identifier: CC-BY-NC-4.0 */
(() => {
  'use strict';
  const root=document.getElementById('odradek-a05-viewer'),M=window.ArmA05;
  const layout=JSON.parse(root.querySelector('#a05-layout-data').textContent),parts=M.bodies(layout);
  const canvas=root.querySelector('canvas'),stage=root.querySelector('.av-stage'),layer=root.querySelector('.av-label-layer');
  const d=Math.PI/180,v=a=>new THREE.Vector3(...a),vm=a=>v(a).multiplyScalar(.001);
  let q=[...layout.poses.idle],pose='idle',selected=1,showHead=true,showBrackets=true,showWires=false,showAxes=true;
  let orbit={az:-55*d,el:23*d,distance:1.6},target=new THREE.Vector3(.24,.07,.3),mode='perspective',animation=0;
  let renderer;try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,preserveDrawingBuffer:true});}
  catch(e){stage.textContent='此视图需要WebGL。';return;}
  renderer.setPixelRatio(Math.min(2,devicePixelRatio||1));renderer.setClearColor(0,0);
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,.01,8);camera.up.set(0,0,1);
  scene.add(new THREE.AmbientLight(0xffffff,2));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(.5,-.7,1.4);scene.add(light);
  const fill=new THREE.DirectionalLight(0xffffff,.8);fill.position.set(-.4,.8,.4);scene.add(fill);
  const materials={motor:new THREE.MeshStandardMaterial({metalness:.5,roughness:.45}),structure:new THREE.MeshStandardMaterial({metalness:.45,roughness:.5}),bracket:new THREE.MeshStandardMaterial({metalness:.55,roughness:.55}),head:new THREE.MeshStandardMaterial({metalness:.3,roughness:.6}),display:new THREE.MeshBasicMaterial(),base:new THREE.MeshStandardMaterial({roughness:.7}),wire:new THREE.MeshBasicMaterial(),volume:new THREE.MeshBasicMaterial({transparent:true,opacity:.08,depthWrite:false,side:THREE.DoubleSide})};
  materials.lens=new THREE.MeshStandardMaterial({metalness:.15,roughness:.18});
  const lineMaterial=new THREE.LineBasicMaterial({transparent:true,opacity:.3});
  const groups={},meshes=new Map(),jointLabels=[],arrows=[],motorMaterials=[],inputs=[],outputs=[];
  const state0=M.fk(layout,q);for(const name of Object.keys(state0.frames)){const g=new THREE.Group();g.matrixAutoUpdate=false;groups[name]=g;scene.add(g);}
  function meshPart(b) {
    let g;
    if(b.kind==='box')g=new THREE.BoxGeometry(...b.size.map(x=>x*.001));
    else if(b.kind==='petal'){
      const s=new THREE.Shape(b.polygon.map(p=>new THREE.Vector2(...p.map(x=>x*.001))));
      g=new THREE.ExtrudeGeometry(s,{depth:b.depth*.001,bevelEnabled:false});
      g.translate(0,0,-b.depth*.0005);g.applyMatrix4(new THREE.Matrix4().makeBasis(v([0,1,0]),v([0,0,1]),v([1,0,0])));
    }else g=new THREE.CylinderGeometry(b.r*.001,b.r*.001,b.length*.001,40);
    const material=b.role==='motor'?materials.motor.clone():materials[b.role];
    const m=new THREE.Mesh(g,material);m.position.copy(vm(b.center||[0,0,0]));
    if(b.id.startsWith('camera-'))m.material=[materials.head,materials.lens,materials.head];
    if(b.kind==='cylinder')m.quaternion.setFromUnitVectors(v([0,1,0]),v(b.axis));
    groups[b.frame].add(m);meshes.set(b.id,m);if(b.role==='motor')motorMaterials[b.joint]=material;
    if(b.kind==='petal'){
      const cy=b.polygon.reduce((s,p)=>s+p[0],0)/b.polygon.length,cz=b.polygon.reduce((s,p)=>s+p[1],0)/b.polygon.length;
      const shape=new THREE.Shape(b.polygon.map(([y,z])=>new THREE.Vector2((cy+(y-cy)*.87)*.001,(cz+(z-cz)*.83)*.001)));
      const pg=new THREE.ShapeGeometry(shape);pg.applyMatrix4(new THREE.Matrix4().makeBasis(v([0,1,0]),v([0,0,1]),v([1,0,0])));
      const panel=new THREE.Mesh(pg,materials.display);panel.position.x=b.depth*.0005+.0002;m.add(panel);
    }
  }
  parts.forEach(meshPart);
  // Output-face markers distinguish a fixed motor casing from its rotating carrier.
  layout.joints.forEach((j,i)=>{
    const ring=new THREE.Mesh(new THREE.TorusGeometry(j.diameter_mm*.00030,.0015,7,36),materials.bracket);
    ring.quaternion.setFromUnitVectors(v([0,0,1]),v(j.axis));
    const face=i===0?[0,0,1]:i===1?[0,54,0]:i===4?[0,49,0]:i===5?[0,0,49]:M.mul(j.axis,j.length_mm/2+1);
    ring.position.copy(vm(face));groups[j.id+'.rotor'].add(ring);
    const a=new THREE.ArrowHelper(v(j.axis),vm(M.mul(j.axis,-18)),.105,0xffffff,.012,.008);groups[j.id+'.fixed'].add(a);arrows.push(a);
    const el=document.createElement('span');el.className='av-label text-small';el.textContent=`${j.id} · ${j.model}`;layer.appendChild(el);jointLabels.push(el);
  });
  const tcpLabel=document.createElement('span');tcpLabel.className='av-label text-small';tcpLabel.textContent='TCP';layer.appendChild(tcpLabel);
  const tcpDot=new THREE.Mesh(new THREE.SphereGeometry(.004,12,8),materials.display);groups.tcp.add(tcpDot);
  // Non-bore routing reservations: rigid trunks and local movement chambers are intentionally separate.
  const wireGroups=[],wireSegments=[];
  function wire(frame,points){const curve=new THREE.CatmullRomCurve3(points.map(vm));const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,40,.0025,6,false),materials.wire);groups[frame].add(mesh);wireGroups.push(mesh);wireSegments.push({frame,points});}
  const reservations=M.cableReservations();
  reservations.segments.forEach(s=>wire(s.frame,s.points));
  const chambers=reservations.chambers;
  chambers.forEach(([f,axis,c,r,t])=>{const g=new THREE.TorusGeometry(r*.001,t*.001,8,40),m=new THREE.Mesh(g,materials.volume);m.quaternion.setFromUnitVectors(v([0,0,1]),v(axis));m.position.copy(vm(c));groups[f].add(m);wireGroups.push(m);});
  const grid=[];for(let k=-4;k<=9;k++)grid.push(vm([k*100,-400,0]),vm([k*100,500,0]));for(let k=-4;k<=5;k++)grid.push(vm([-400,k*100,0]),vm([900,k*100,0]));
  scene.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(grid),lineMaterial));
  const detailText=[
    '转向关节固定在底座上；走线绕过电机外缘。',
    '电机移至肩轴一侧，对侧预留辅助支承与线腔。',
    '转子带动上臂；没有假定轴心可穿双GMSL。',
    '前臂错层90 mm，输出转接与对侧支承仍需细化。',
    '开口叉架；J6轴心前移55 mm，避免三台电机挤在一起。',
    '上下布置的驱动与输出载架；横摆探索范围±60°。',
    '整头roll保留；±90°为布局目标，线腔尚待恒长滚弯校核。'
  ];
  layout.joints.forEach((j,i)=>{
    const row=document.createElement('div');row.className='av-control';
    row.innerHTML=`<div class="av-control-top"><label for="a05-q${i}">${j.id} ${j.name}</label><output class="tabular-nums"></output></div><input id="a05-q${i}" class="form-range" type="range" min="${j.limits_deg[0]}" max="${j.limits_deg[1]}" step="1" value="${q[i]}" aria-label="${j.id} ${j.name}，角度">`;
    root.querySelector('.av-controls').appendChild(row);const input=row.querySelector('input'),output=row.querySelector('output');inputs.push(input);outputs.push(output);
    input.addEventListener('input',()=>{stopAnimation();selected=i;q[i]=+input.value;pose='';apply();});input.addEventListener('change',save);input.addEventListener('focus',()=>{selected=i;highlight();detail();render();});
  });
  let palette,lastCheck,lastState,themeKey='';
  const partLabel=id=>id==='camera--1'?'下鱼眼':id==='camera-1'?'上鱼眼':id.replace(/^(J\d)-motor$/,'$1 电机');
  function color(name){const p=document.createElement('span');p.style.color=`var(${name})`;p.hidden=true;root.appendChild(p);const css=getComputedStyle(p).color;p.remove();const rgba=css.match(/^rgba\(([^)]+)\)$/);if(rgba){const channels=rgba[1].split(',').map(Number),c=new THREE.Color(`rgb(${channels.slice(0,3).join(',')})`);return name==='--background'?c:c.lerp(color('--background'),1-channels[3]);}return new THREE.Color(css);}
  function theme(){const p={fg:color('--foreground'),bg:color('--background'),mid:color('--muted-foreground'),active:color('--viz-series-1'),wire:color('--viz-series-2'),amber:color('--orange'),bad:color('--destructive')};const key=Object.values(p).map(x=>x.getHexString()).join();if(key===themeKey)return;themeKey=key;palette=p;
    materials.motor.color.copy(p.mid).lerp(p.bg,.12);materials.structure.color.copy(p.mid).lerp(p.bg,.18);materials.bracket.color.copy(p.mid).lerp(p.bg,.37);materials.head.color.copy(p.fg).lerp(p.bg,.24);materials.lens.color.copy(p.bg).lerp(p.fg,.08);materials.base.color.copy(p.mid).lerp(p.bg,.35);materials.display.color.copy(p.amber);materials.wire.color.copy(p.wire);materials.volume.color.copy(p.wire);lineMaterial.color.copy(p.mid);highlight();}
  function detail(){const j=layout.joints[selected];root.querySelector('.av-detail').textContent=`${j.id} · ${j.model} · Ø${j.diameter_mm} × ${j.length_mm} mm 包络 — ${detailText[selected]}`;}
  function highlight(){if(!palette)return;const bad=new Set((lastCheck?.conflicts||[]).flatMap(c=>[c.a,c.b]));parts.forEach(b=>{const mesh=meshes.get(b.id);if(b.role==='motor'){mesh.material.color.copy(bad.has(b.id)?palette.bad:materials.motor.color);mesh.material.emissive.copy(b.joint===selected?palette.active:new THREE.Color(0));mesh.material.emissiveIntensity=b.joint===selected?.2:0;}mesh.visible=(showHead||!['head','display'].includes(b.role))&&(showBrackets||b.role!=='bracket');});wireGroups.forEach(m=>m.visible=showWires);arrows.forEach((a,i)=>{a.visible=showAxes;a.setColor(i===selected?palette.active:palette.mid);jointLabels[i].classList.toggle('is-active',i===selected);});}
  function apply(){lastCheck=M.checks(layout,q,parts);lastState=lastCheck.state;for(const [name,t]of Object.entries(lastState.frames)){groups[name].matrix.set(t.r[0],t.r[1],t.r[2],t.p[0]*.001,t.r[3],t.r[4],t.r[5],t.p[1]*.001,t.r[6],t.r[7],t.r[8],t.p[2]*.001,0,0,0,1);}
    q.forEach((a,i)=>{inputs[i].value=String(a);outputs[i].value=`${Math.round(a)}°`;});root.querySelectorAll('[data-pose]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.pose===pose)));
    const status=root.querySelector('.av-status');status.classList.toggle('text-destructive',lastCheck.conflicts.length>0);status.textContent=lastCheck.conflicts.length?`粗包络干涉：${lastCheck.conflicts.slice(0,3).map(c=>`${partLabel(c.a)} ↔ ${partLabel(c.b)}`).join('；')}`:`粗包络未检出干涉 · 电机／主杆／头部／活动支架／桌面${showWires?' · 线束占位，未解恒长滚弯':''}`;
    root.querySelector('.av-tcp').value=`TCP X ${lastState.tcp[0].toFixed(0)} · Y ${lastState.tcp[1].toFixed(0)} · Z ${lastState.tcp[2].toFixed(0)} mm`;
    root.dataset.angles=JSON.stringify(q);highlight();detail();render();}
  function render(){const ce=Math.cos(orbit.el);camera.position.set(target.x+orbit.distance*ce*Math.cos(orbit.az),target.y+orbit.distance*ce*Math.sin(orbit.az),target.z+orbit.distance*Math.sin(orbit.el));camera.lookAt(target);scene.updateMatrixWorld(true);renderer.render(scene,camera);labels();}
  function labels(){if(!lastState)return;const r=stage.getBoundingClientRect(),occupied=[];function place(el,p){const w=vm(p).project(camera);el.hidden=w.z>1||w.z< -1;if(el.hidden)return;let x=Math.max(3,Math.min(r.width-el.offsetWidth-3,(w.x+1)*r.width/2+5)),y=Math.max(3,Math.min(r.height-el.offsetHeight-3,(1-w.y)*r.height/2-18));for(let k=0;k<12;k++){const hit=occupied.find(a=>x<a.x+a.w+3&&x+el.offsetWidth+3>a.x&&y<a.y+a.h+2&&y+el.offsetHeight+2>a.y);if(!hit)break;y=hit.y+hit.h+3;if(y>r.height-el.offsetHeight){y=Math.max(3,hit.y-el.offsetHeight-3);x=Math.max(3,x-el.offsetWidth-4);}}el.style.left=x+'px';el.style.top=y+'px';occupied.push({x,y,w:el.offsetWidth,h:el.offsetHeight});}jointLabels.forEach((el,i)=>place(el,lastState.joints[i].p));place(tcpLabel,lastState.tcp);}
  function fit(extraPoses=[]){const bounds=new THREE.Box3();parts.forEach(b=>{if(meshes.get(b.id).visible)bounds.expandByObject(meshes.get(b.id));});extraPoses.forEach(angles=>{const frames=M.fk(layout,angles).frames;parts.forEach(b=>{if(meshes.get(b.id).visible)M.worldPoly(b,frames).vertices.forEach(p=>bounds.expandByPoint(vm(p)));});});bounds.expandByPoint(v([0,0,0]));bounds.getCenter(target);const s=bounds.getBoundingSphere(new THREE.Sphere()),halfV=38*d/2,halfH=Math.atan(Math.tan(halfV)*camera.aspect);orbit.distance=Math.min(4,Math.max(.7,s.radius/Math.sin(Math.min(halfV,halfH))*1.1));render();}
  function resize(){const r=stage.getBoundingClientRect();if(!r.width)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();theme();render();}
  function save(){window.openai?.setWidgetState?.({modelContent:{viewer:'odradek-arm-a05',jointAnglesDeg:q,pose:pose||'custom',selectedJoint:layout.joints[selected].id},privateContent:{orbit,target:target.toArray(),showHead,showBrackets,showWires,showAxes,mode}}).catch(()=>{});}
  function restore(s){if(s?.modelContent?.viewer!=='odradek-arm-a05')return;const a=s.modelContent.jointAnglesDeg;if(Array.isArray(a)&&a.length===7&&a.every(Number.isFinite))q=a.map((x,i)=>Math.max(layout.joints[i].limits_deg[0],Math.min(layout.joints[i].limits_deg[1],x)));selected=Math.max(0,Math.min(6,Number(String(s.modelContent.selectedJoint||'J2').slice(1))-1));pose=Object.keys(layout.poses).find(k=>layout.poses[k].every((a,i)=>a===q[i]))||'';const p=s.privateContent||{};if(p.orbit&&[p.orbit.az,p.orbit.el,p.orbit.distance].every(Number.isFinite))orbit={az:p.orbit.az,el:Math.max(-.05,Math.min(1.5,p.orbit.el)),distance:Math.max(.4,Math.min(4,p.orbit.distance))};if(Array.isArray(p.target)&&p.target.length===3&&p.target.every(Number.isFinite))target.fromArray(p.target);for(const key of ['showHead','showBrackets','showWires','showAxes'])if(typeof p[key]==='boolean'){if(key==='showHead')showHead=p[key];if(key==='showBrackets')showBrackets=p[key];if(key==='showWires')showWires=p[key];if(key==='showAxes')showAxes=p[key];}syncChecks();apply();}
  function syncChecks(){root.querySelector('#a05-head').checked=showHead;root.querySelector('#a05-brackets').checked=showBrackets;root.querySelector('#a05-wires').checked=showWires;root.querySelector('#a05-axes').checked=showAxes;}
  function stopAnimation(){if(animation)cancelAnimationFrame(animation);animation=0;root.querySelector('#a05-transition').textContent='收拢 → 互动';}
  root.querySelectorAll('[data-pose]').forEach(b=>b.addEventListener('click',()=>{stopAnimation();pose=b.dataset.pose;q=[...layout.poses[pose]];apply();fit();save();}));
  root.querySelector('#a05-transition').addEventListener('click',()=>{if(animation){stopAnimation();save();return;}if(matchMedia('(prefers-reduced-motion: reduce)').matches){pose='attention';q=[...layout.poses.attention];apply();fit();save();return;}q=[...layout.poses.idle];pose='';apply();fit(Array.from({length:17},(_,k)=>layout.poses.idle.map((a,i)=>a+(layout.poses.attention[i]-a)*k/16)));const start=performance.now();root.querySelector('#a05-transition').textContent='停止演示';function step(t){const u=Math.min(1,(t-start)/2200),s=u*u*(3-2*u);q=layout.poses.idle.map((x,i)=>x+(layout.poses.attention[i]-x)*s);apply();if(u<1)animation=requestAnimationFrame(step);else{stopAnimation();pose='attention';apply();save();}}animation=requestAnimationFrame(step);});
  for(const key of ['head','brackets','wires','axes'])root.querySelector('#a05-'+key).addEventListener('change',e=>{if(key==='head')showHead=e.target.checked;if(key==='brackets')showBrackets=e.target.checked;if(key==='wires')showWires=e.target.checked;if(key==='axes')showAxes=e.target.checked;apply();save();});
  root.querySelector('#a05-fit').addEventListener('click',()=>{fit();save();});
  root.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.view;const views={perspective:[-55*d,23*d],side:[-Math.PI/2,.05],front:[0,.05],wrist:[-45*d,28*d]};[orbit.az,orbit.el]=views[mode];root.querySelectorAll('[data-view]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));if(mode==='wrist'){target.copy(vm(lastState.joints[5].p));orbit.distance=camera.aspect<.9?.95:.8;render();}else fit();save();}));
  const pointers=new Map();canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});});canvas.addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId))return;const old=pointers.get(e.pointerId),next={x:e.clientX,y:e.clientY};if(pointers.size===1){orbit.az-=(next.x-old.x)*.008;orbit.el=Math.max(-.05,Math.min(1.5,orbit.el+(next.y-old.y)*.006));}else{const other=[...pointers.entries()].find(([id])=>id!==e.pointerId)?.[1];if(other){const a=Math.hypot(old.x-other.x,old.y-other.y),b=Math.hypot(next.x-other.x,next.y-other.y);if(a>5&&b>5)orbit.distance=Math.max(.4,Math.min(4,orbit.distance*a/b));}}pointers.set(e.pointerId,next);render();});for(const name of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(name,e=>{if(pointers.delete(e.pointerId))save();});canvas.addEventListener('wheel',e=>{e.preventDefault();orbit.distance=Math.max(.4,Math.min(4,orbit.distance*Math.exp(e.deltaY*.001)));render();clearTimeout(canvas.timer);canvas.timer=setTimeout(save,150);},{passive:false});
  window.addEventListener('openai:set_globals',e=>{restore(e.detail?.globals?.widgetState);theme();render();});new MutationObserver(()=>{theme();render();}).observe(document.documentElement,{attributes:true,attributeFilter:['class','style','data-theme','data-appearance']});matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{theme();render();});new ResizeObserver(resize).observe(stage);
  root.getKinematicState=()=>({anglesDeg:[...q],jointPositionsMm:lastState.joints.map(x=>x.p),headPositionMm:lastState.head,tcpPositionMm:lastState.tcp,collisions:lastCheck.conflicts,checkedScope:lastCheck.checkedScope,showWires,showHead,selectedJoint:selected+1});
  theme();apply();restore(window.openai?.widgetState);resize();if(window.openai?.widgetState?.modelContent?.viewer!=='odradek-arm-a05')fit();root.dataset.ready='true';
})();
