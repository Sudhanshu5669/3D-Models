/* Dependency-free WebGL preview; works directly from file://. */
'use strict';
const canvas = document.getElementById('scene');
const gl = canvas.getContext('webgl', {antialias:true, alpha:false});
if (!gl) {
  document.body.insertAdjacentHTML('beforeend','<p id="error">WebGL is unavailable. Open the GLB files in your preferred 3D application.</p>');
  throw new Error('WebGL unavailable');
}
const vertexSource = `
attribute vec3 position, normal, color, surface;
uniform mat4 vp;
varying vec3 world, N, base, finish;
void main() {world=position;N=normal;base=color;finish=surface;gl_Position=vp*vec4(position,1.0);}`;
const fragmentSource = `
precision highp float;
uniform vec3 eye;
varying vec3 world, N, base, finish;
vec3 linearize(vec3 c) {return mix(c/12.92,pow((c+.055)/1.055,vec3(2.4)),step(vec3(.04045),c));}
vec3 encode(vec3 c) {return mix(c*12.92,1.055*pow(max(c,vec3(0.0)),vec3(1.0/2.4))-.055,step(vec3(.0031308),c));}
void main() {
  if(finish.z<0.0){gl_FragColor=vec4(base,1.0);return;}
  vec3 n=normalize(N),v=normalize(eye-world);
  vec3 key=normalize(vec3(-.7,2.,-1.6)),fill=normalize(vec3(2.,1.,.6));
  float diffuse=.56+.58*max(0.,dot(n,key))+.24*max(0.,dot(n,fill));
  float power=12.+(1.-finish.x)*70.;
  float spec=(pow(max(0.,dot(n,normalize(key+v))),power)*.36
    +pow(max(0.,dot(n,normalize(normalize(vec3(1.8,2.,.6))+v))),power*.45)*.16)*(1.-finish.x*.8);
  vec3 reflected=mix(vec3(.83,.91,1.),base,step(.4,finish.y));
  vec3 color=linearize(base)*diffuse+spec*reflected;
  if(finish.z>0.)color=linearize(base)*1.4;
  gl_FragColor=vec4(encode(color),1.);
}`;
function shader(type, source) { const s=gl.createShader(type); gl.shaderSource(s,source); gl.compileShader(s); if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s)); return s; }
const program=gl.createProgram();
gl.attachShader(program,shader(gl.VERTEX_SHADER,vertexSource));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragmentSource));gl.linkProgram(program);
if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
gl.useProgram(program);
const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
for (const [i,key] of ['position','normal','color','surface'].entries()) {const loc=gl.getAttribLocation(program,key);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,48,i*12);}
const vpUniform=gl.getUniformLocation(program,'vp');
const eyeUniform=gl.getUniformLocation(program,'eye');
gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);gl.clearColor(.937,.949,.957,1);
const sub=(a,b)=>a.map((v,i)=>v-b[i]);
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const unit=a=>{const l=Math.hypot(...a);return a.map(v=>v/l)};
function multiply(a,b) {const out=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)out[c*4+r]+=a[k*4+r]*b[c*4+k];return out;}
function perspective(aspect) {const f=1/Math.tan(Math.PI/8),n=.01,far=80;return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+n)/(n-far),-1,0,0,2*far*n/(n-far),0]);}
function view(eye,target){const z=unit(sub(eye,target)),x=unit(cross([0,1,0],z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);}
let selected=-1,yaw=.25,pitch=.44,distance=8.5,count=0,auto=false,dirty=true;
let placements=[],labelElements=[];
const models=window.CONSOLES.models;
function build(){
  const data=[];
  placements=selected<0?models.map((m,i)=>({m,x:(i-2)*1.48})): [{m:models[selected],x:0}];
  function triangle(points,color,surface=[.8,0,-1]){const n=unit(cross(sub(points[1],points[0]),sub(points[2],points[0])));for(const p of points)data.push(...p,...n,...color,...surface);}
  for(const {m,x} of placements){
    // Concentric contact-shadow discs keep the models grounded without textures.
    const radius=Math.max(m.bounds[1][0]-m.bounds[0][0],m.bounds[1][2]-m.bounds[0][2])*.63;
    for(let ring=0;ring<30;ring++){
      const r=radius*(1-ring*.025),shade=.937-ring*.0025;
      for(let k=0;k<40;k++){
        const a=k*Math.PI/20,b=(k+1)*Math.PI/20;
        triangle([[x,-.008+ring*.0003,0],[x+Math.cos(b)*r,-.008+ring*.0003,Math.sin(b)*r*.72],[x+Math.cos(a)*r,-.008+ring*.0003,Math.sin(a)*r*.72]],[shade,shade+.012,shade+.020]);
      }
    }
    for(const part of m.parts){
      const hex=CONSOLES.materials[part.material];
      const color=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);
      const surface=[...CONSOLES.surfaces[part.material],part.material==='led_blue'?1:0];
      for(const tri of part.triangles)triangle(tri.map(i=>{const v=part.vertices[i];return [v[0]+x,v[1],v[2]]}),color,surface);
    }
  }
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);count=data.length/12;
  document.getElementById('title').textContent=selected<0?'The complete collection':models[selected].title;
  document.getElementById('stats').textContent=placements.reduce((n,{m})=>n+m.triangles,0).toLocaleString()+' triangles';
  document.getElementById('downloads').innerHTML=selected<0?'<a href="../models/manifest.json">Model specifications ↗</a>':`<a download href="../models/${models[selected].name}/${models[selected].name}.glb">Download GLB ↓</a><a download href="../models/${models[selected].name}/${models[selected].name}.obj">OBJ ↓</a><a download href="../models/${models[selected].name}/${models[selected].name}.mtl">MTL ↓</a>`;
  document.getElementById('labels').replaceChildren();
  labelElements=placements.map(({m})=>{const el=document.createElement('div');el.className='tag';el.textContent=m.name.toUpperCase();document.getElementById('labels').append(el);return el;});dirty=true;
}
function reset(){yaw=selected<0?.25:.44;pitch=selected<0?.44:([1,4].includes(selected)?.28:.52);distance=selected<0?8.5:2.7;dirty=true;}
for(const b of document.querySelectorAll('[data-index]'))b.addEventListener('click',()=>{selected=Number(b.dataset.index);for(const e of document.querySelectorAll('[data-index]'))e.setAttribute('aria-pressed',String(e===b));reset();build();});
document.getElementById('reset').onclick=reset;
document.getElementById('rotate').onclick=()=>{auto=!auto;document.getElementById('rotate').setAttribute('aria-pressed',String(auto));};
const pointers=new Map();let lastPinch=0;
canvas.addEventListener('pointerdown',e=>{pointers.set(e.pointerId,[e.clientX,e.clientY]);canvas.setPointerCapture(e.pointerId);lastPinch=0;});
canvas.addEventListener('pointermove',e=>{
  if(!pointers.has(e.pointerId))return;
  const old=pointers.get(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);
  if(pointers.size===1){yaw-=(e.clientX-old[0])*.008;pitch=Math.max(-.15,Math.min(1.4,pitch+(e.clientY-old[1])*.006));}
  else {const [a,b]=[...pointers.values()];const span=Math.hypot(a[0]-b[0],a[1]-b[1]);if(lastPinch)distance=Math.max(1.3,Math.min(20,distance*lastPinch/span));lastPinch=span;}
  dirty=true;
});
for(const event of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(event,e=>{pointers.delete(e.pointerId);lastPinch=0;});
canvas.addEventListener('wheel',e=>{e.preventDefault();distance=Math.max(1.3,Math.min(20,distance*Math.exp(e.deltaY*.001)));dirty=true;},{passive:false});
canvas.tabIndex=0;
canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-'].includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')yaw-=.1;if(e.key==='ArrowRight')yaw+=.1;if(e.key==='ArrowUp')pitch=Math.min(1.4,pitch+.1);if(e.key==='ArrowDown')pitch=Math.max(-.15,pitch-.1);if(e.key==='+'||e.key==='=')distance=Math.max(1.3,distance*.9);if(e.key==='-')distance=Math.min(20,distance*1.1);dirty=true;});
new ResizeObserver(()=>{dirty=true}).observe(canvas);
let last=0;
function frame(now){
  if(auto){yaw+=Math.min((now-last)/1000,.05)*.22;dirty=true;}last=now;
  if(dirty){
    dirty=false;const dpr=Math.min(devicePixelRatio,2),w=canvas.clientWidth,h=canvas.clientHeight;
    if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
    gl.viewport(0,0,canvas.width,canvas.height);
    const center=selected<0?.53:(models[selected].bounds[1][1]/2);
    const target=[0,center,0],adapt=selected<0?Math.max(1,1.5/(w/h)):Math.max(1,.85/(w/h));
    const r=distance*adapt,eye=[Math.sin(yaw)*Math.cos(pitch)*r,center+Math.sin(pitch)*r,-Math.cos(yaw)*Math.cos(pitch)*r];
    const vp=multiply(perspective(w/h),view(eye,target));
    gl.uniform3fv(eyeUniform,eye);gl.uniformMatrix4fv(vpUniform,false,vp);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.drawArrays(gl.TRIANGLES,0,count);
    placements.forEach(({x},i)=>{const p=[x,-.14,0,1],q=[0,0,0,0];for(let row=0;row<4;row++)for(let col=0;col<4;col++)q[row]+=vp[col*4+row]*p[col];const el=labelElements[i];el.style.left=((q[0]/q[3]*.5+.5)*w)+'px';el.style.top=((-q[1]/q[3]*.5+.5)*h)+'px';el.hidden=selected>=0||q[3]<0;});
  }
  requestAnimationFrame(frame);
}
build();requestAnimationFrame(frame);
