/* QuadCOM ❖ GLIMMER VISION (V45)
 *
 * The high-end render path: GLIMMER's insight drawn through the AURUM texture
 * pack. One full-screen fragment pass renders four instruments from a single
 * data buffer:
 *   RISK CONE    bootstrap density fan in √time space (volatility spreads
 *                linearly), P5/P25/P50/P75/P95 lines, live TP/SL levels
 *   TRADE ODDS   TP-first / SL-first / open ring for the best singular trade
 *   HOLDOUT MAP  out-of-sample Sharpe for every momentum/reversion setting
 *   INDEPENDENCE spectrum of per-PICO mean |ρ| and the effective-count bar
 *
 * Backends, in fixed order: WebGPU (shared GLIMMER device) → WebGL2 → Canvas 2D.
 * Quality tiers (ULTRA/HIGH/MED/LOW) follow GLIMMER's health, envelope and
 * inferred pressure. It renders only while the VISION view is on screen and
 * only when data, size or tier change. ULTRA/HIGH add a short reveal on new
 * data, then hold still: no constant glow (V43 D03).
 */
(() => {
'use strict';

const root = document.documentElement;
const TEXTURE_KEY = 'quadcom-v45-texture';
const TEX = { B: './textures/aurum-brushed.png', O: './textures/obsidian-grain.png', C: './textures/carbon-weave.png', G: './textures/glass-sheen.png', L: './textures/quad-lattice.png' };
const TAU = [12 * 60, 60 * 60, 4 * 60 * 60];
const O = { H: 192, TAU: 195, Q: 198, ODDS: 213, LV: 217, SWM: 221, CORR: 225, SPEC: 229, SW: 325 };
const DATA_LEN = 2048;
const TIERS = { ULTRA: { scale: 3, reveal: true, id: 3 }, HIGH: { scale: 2, reveal: true, id: 2 }, MED: { scale: 1, reveal: false, id: 1 }, LOW: { scale: 0.75, reveal: false, id: 0 } };
const REVEAL_MS = 1200;

/* ───────────────────────── texture pack (CSS) ───────────────────────── */
function applyTexture(name) {
  root.dataset.qcTexture = name;
  try { localStorage.setItem(TEXTURE_KEY, name); } catch (_) {}
}
let texName = 'aurum';
try { texName = localStorage.getItem(TEXTURE_KEY) || 'aurum'; } catch (_) {}
applyTexture(texName === 'off' ? 'off' : 'aurum');
window.__quadcomTexture = toggle => { if (toggle) applyTexture(root.dataset.qcTexture === 'aurum' ? 'off' : 'aurum'); return root.dataset.qcTexture; };

/* ───────────────────────── shaders ───────────────────────── */
const WGSL = `
const O_H:u32=${O.H}u;const O_TAU:u32=${O.TAU}u;const O_Q:u32=${O.Q}u;const O_ODDS:u32=${O.ODDS}u;const O_LV:u32=${O.LV}u;
const O_SWM:u32=${O.SWM}u;const O_CORR:u32=${O.CORR}u;const O_SPEC:u32=${O.SPEC}u;const O_SW:u32=${O.SW}u;
const GOLD=vec3<f32>(0.851,0.678,0.271);const HI=vec3<f32>(0.953,0.831,0.467);const MINT=vec3<f32>(0.573,0.843,0.718);
const RED=vec3<f32>(0.894,0.498,0.439);const PAPER=vec3<f32>(0.941,0.929,0.894);
struct U{v:array<vec4<f32>,8>};
@group(0) @binding(0) var<uniform> u:U;
@group(0) @binding(1) var<storage,read> d:array<f32>;
@group(0) @binding(2) var smp:sampler;
@group(0) @binding(3) var tB:texture_2d<f32>;
@group(0) @binding(4) var tO:texture_2d<f32>;
@group(0) @binding(5) var tC:texture_2d<f32>;
@group(0) @binding(6) var tG:texture_2d<f32>;
@group(0) @binding(7) var tL:texture_2d<f32>;
@vertex fn vs(@builtin(vertex_index) i:u32)->@builtin(position) vec4<f32>{
  var q=array<vec2<f32>,3>(vec2<f32>(-1.0,-1.0),vec2<f32>(3.0,-1.0),vec2<f32>(-1.0,3.0));return vec4<f32>(q[i],0.0,1.0);}
fn tex(t:texture_2d<f32>,uv:vec2<f32>)->vec4<f32>{return textureSampleLevel(t,smp,uv,0.0);}
fn dpr()->f32{return u.v[5].z;}
fn inR(p:vec2<f32>,r:vec4<f32>)->bool{return p.x>=r.x&&p.y>=r.y&&p.x<r.x+r.z&&p.y<r.y+r.w;}
fn edgeD(p:vec2<f32>,r:vec4<f32>)->f32{return min(min(p.x-r.x,r.x+r.z-p.x),min(p.y-r.y,r.y+r.w-p.y));}
fn ln1(dist:f32,w:f32)->f32{return 1.0-smoothstep(w*0.5,w*1.5,abs(dist));}
fn dens(k:u32,z:f32)->f32{let x=(z+1.0)*32.0-0.5;if(x<(-1.0)||x>64.0){return 0.0;}
  let i0=clamp(floor(x),0.0,63.0);let i1=min(i0+1.0,63.0);return mix(d[k*64u+u32(i0)],d[k*64u+u32(i1)],clamp(x-i0,0.0,1.0));}
fn backdrop(p:vec2<f32>)->vec3<f32>{let s=dpr();let o=tex(tO,p/(128.0*s)).rgb;let l=tex(tL,p/(32.0*s));return o*1.6+l.rgb*l.a*0.55;}
fn regionBase(p:vec2<f32>,r:vec4<f32>)->vec3<f32>{let s=dpr();let c=tex(tC,p/(16.0*s)).rgb;let g=tex(tG,(p-r.xy)/(256.0*s));return c*0.9+g.rgb*g.a*0.35;}
fn frame(col:vec3<f32>,p:vec2<f32>,r:vec4<f32>)->vec3<f32>{return mix(col,GOLD,ln1(edgeD(p,r),dpr())*0.55);}
fn tauA(k:u32)->f32{return d[O_TAU+k];}
fn at(k:u32,y:f32,st:f32)->f32{return dens(k,y*(sqrt(tauA(k))/st)/d[O_H+k]);}
fn qv(k:u32,i:u32,st:f32)->f32{return d[O_Q+k*5u+i]*st/sqrt(tauA(k));}
fn cone(p:vec2<f32>)->vec3<f32>{
  let r=u.v[1];let l=(p-r.xy)/r.zw;let s2=sqrt(tauA(2u));let st=max(l.x*s2,0.5);let yM=u.v[5].x;let y=yM*(1.0-2.0*l.y);let px=2.0*yM/r.w;
  var col=regionBase(p,r);
  let s0=sqrt(tauA(0u));let s1=sqrt(tauA(1u));var k0=0u;var k1=0u;var w=0.0;
  if(st>s0&&st<=s1){k1=1u;w=(st-s0)/(s1-s0);}else if(st>s1){k0=1u;k1=2u;w=clamp((st-s1)/(s2-s1),0.0,1.0);}
  if(d[O_H]>0.0){
    let den=mix(at(k0,y,st),at(k1,y,st),w);
    let gold=tex(tB,vec2<f32>(p.x/(512.0*dpr()),p.y/(64.0*dpr()))).rgb;
    var fan=gold*pow(den,0.7)*1.05;fan=mix(fan,fan*select(RED,MINT,y>0.0)*1.5,0.22*den);
    col=col*(1.0-0.55*smoothstep(0.0,0.08,den))+fan;
    let a=u.v[5].y;if(u.v[0].w>=2.0&&a<1.0){col=col+HI*exp(-pow((l.x-(a*1.4-0.2))*7.0,2.0))*0.45*den;}
    for(var i=0u;i<5u;i++){let q=mix(qv(k0,i,st),qv(k1,i,st),w);var qc=HI;var al=0.55;
      if(i==2u){qc=PAPER;al=0.9;}if(i==0u){qc=RED;al=0.7;}if(i==4u){qc=MINT;al=0.7;}col=mix(col,qc,ln1(y-q,px*dpr()*0.9)*al);}
  }
  col=mix(col,GOLD,ln1(y,px*dpr()*0.7)*0.35*step(0.5,fract(p.x/(6.0*dpr()))));
  for(var k=0u;k<3u;k++){col=mix(col,GOLD,ln1((l.x-sqrt(tauA(k))/s2)*r.z,dpr())*0.28);}
  if(d[O_ODDS+3u]>0.0){let hs=sqrt(max(d[O_LV+2u],1.0))/s2;if(l.x<=hs){let dash=step(0.35,fract(p.x/(9.0*dpr())));
    col=mix(col,MINT,ln1(y-d[O_LV],px*dpr()*1.2)*0.95*dash);col=mix(col,RED,ln1(y-d[O_LV+1u],px*dpr()*1.2)*0.95*dash);}}
  col=mix(col,GOLD,ln1(l.x*r.z,dpr()*1.5)*0.6);
  return frame(col,p,r);}
fn odds(p:vec2<f32>)->vec3<f32>{
  let r=u.v[2];var col=regionBase(p,r);
  let sz=min(r.z,r.w);let c=r.xy+vec2<f32>(sz*0.5,r.w*0.5);let v=p-c;let dist=length(v);let R1=sz*0.45;let R0=sz*0.32;
  if(d[O_ODDS+3u]>0.0){
    let a=fract(atan2(v.x,-v.y)/6.2831853+1.0);let reveal=select(1.0,u.v[5].y,u.v[0].w>=2.0);
    let pT=d[O_ODDS];let pS=d[O_ODDS+1u];var seg=GOLD*0.35;if(a<pT){seg=MINT;}else if(a<pT+pS){seg=RED;}
    let gap=min(min(abs(a-pT),abs(a-pT-pS)),min(a,1.0-a))*6.2831853*dist;
    let m=dot(tex(tB,vec2<f32>(a*3.0,dist/(64.0*dpr()))).rgb,vec3<f32>(0.333))/0.55;
    let ring=smoothstep(R0-dpr(),R0,dist)*(1.0-smoothstep(R1,R1+dpr(),dist))*smoothstep(0.0,1.5*dpr(),gap)*step(a,reveal);
    col=mix(col,seg*(0.45+0.6*m),ring);
    let inner=1.0-smoothstep(R0-3.0*dpr(),R0-2.0*dpr(),dist);let g=tex(tG,v/(128.0*dpr()));
    col=mix(col,col*0.5+g.rgb*g.a*0.8,inner*0.8);col=mix(col,GOLD,ln1(dist-R1-2.5*dpr(),dpr())*0.7);
  }
  return frame(col,p,r);}
fn heat(p:vec2<f32>)->vec3<f32>{
  let r=u.v[3];var col=regionBase(p,r);let nL=d[O_SWM];let nT=d[O_SWM+1u];let mx=max(d[O_SWM+2u],1e-6);
  if(nL>0.0){
    let gap=4.0*dpr();let bh=(r.w-gap)*0.5;let ly=p.y-r.y;let mode=select(0.0,1.0,ly>bh+gap*0.5);let by=select(ly,ly-bh-gap,mode>0.5);
    if(by>=0.0&&by<bh){
      let fx=(p.x-r.x)/r.z*nL;let fy=by/bh*nT;let li=min(floor(fx),nL-1.0);let ti=nT-1.0-min(floor(fy),nT-1.0);
      let idx=u32(mode*nL*nT+li*nT+ti);let s=clamp(d[O_SW+idx]/mx,-1.0,1.0);
      col=select(mix(col,RED,pow(max(-s,0.0),0.7)*0.95),mix(col,MINT,pow(max(s,0.0),0.7)*0.95),s>=0.0);
      let cx=fract(fx);let cy=fract(fy);let ce=min(min(cx,1.0-cx)*r.z/nL,min(cy,1.0-cy)*bh/nT);
      col=col*(0.55+0.45*smoothstep(0.0,dpr(),ce));
      if(f32(idx)==d[O_SWM+3u]){col=mix(col,HI,1.0-smoothstep(0.8*dpr(),1.8*dpr(),ce));}
    }
  }
  return frame(col,p,r);}
fn spec(p:vec2<f32>)->vec3<f32>{
  let r=u.v[4];var col=regionBase(p,r);
  if(d[O_CORR+2u]>0.0){
    let l=(p-r.xy)/r.zw;
    if(l.y<0.74){let b=u32(min(floor(l.x*32.0),31.0));let yy=1.0-l.y/0.74;
      let bar=step(yy,d[O_SPEC+b])*step(0.14,fract(l.x*32.0));let gold=tex(tB,vec2<f32>(p.x/(512.0*dpr()),p.y/(32.0*dpr()))).rgb;
      col=mix(col,gold*(0.45+0.7*yy),bar);col=mix(col,PAPER,ln1((l.x-d[O_CORR+1u])*r.z,dpr())*0.8);}
    else if(l.y>0.84){col=mix(col,MINT*0.9,select(0.0,0.9,l.x<d[O_CORR]));}
  }
  return frame(col,p,r);}
@fragment fn fs(@builtin(position) q:vec4<f32>)->@location(0) vec4<f32>{
  let p=q.xy;var col=backdrop(p);
  if(inR(p,u.v[1])){col=cone(p);}else if(inR(p,u.v[2])){col=odds(p);}else if(inR(p,u.v[3])){col=heat(p);}else if(inR(p,u.v[4])){col=spec(p);}
  let vg=1.0-0.35*pow(length(p/u.v[0].xy-0.5)*1.25,2.0);return vec4<f32>(col*vg,1.0);}`;

// GLSL ES 3.0 mirror of the WGSL above (WebGL2 fallback).
const GLSL_VS = `#version 300 es
void main(){vec2 q[3]=vec2[3](vec2(-1.,-1.),vec2(3.,-1.),vec2(-1.,3.));gl_Position=vec4(q[gl_VertexID],0.,1.);}`;
const GLSL_FS = `#version 300 es
precision highp float;precision highp int;precision highp sampler2D;
uniform vec4 uV[8];uniform sampler2D uD,tB,tO,tC,tG,tL;out vec4 outC;
const vec3 GOLD=vec3(.851,.678,.271),HI=vec3(.953,.831,.467),MINT=vec3(.573,.843,.718),RED=vec3(.894,.498,.439),PAPER=vec3(.941,.929,.894);
float D(int i){return texelFetch(uD,ivec2(i,0),0).r;}
vec4 tex(sampler2D t,vec2 uv){return textureLod(t,uv,0.);}
float dpr(){return uV[5].z;}
bool inR(vec2 p,vec4 r){return p.x>=r.x&&p.y>=r.y&&p.x<r.x+r.z&&p.y<r.y+r.w;}
float edgeD(vec2 p,vec4 r){return min(min(p.x-r.x,r.x+r.z-p.x),min(p.y-r.y,r.y+r.w-p.y));}
float ln1(float dist,float w){return 1.-smoothstep(w*.5,w*1.5,abs(dist));}
float dens(int k,float z){float x=(z+1.)*32.-.5;if(x<-1.||x>64.)return 0.;float i0=clamp(floor(x),0.,63.),i1=min(i0+1.,63.);return mix(D(k*64+int(i0)),D(k*64+int(i1)),clamp(x-i0,0.,1.));}
vec3 backdrop(vec2 p){float s=dpr();vec3 o=tex(tO,p/(128.*s)).rgb;vec4 l=tex(tL,p/(32.*s));return o*1.6+l.rgb*l.a*.55;}
vec3 regionBase(vec2 p,vec4 r){float s=dpr();vec3 c=tex(tC,p/(16.*s)).rgb;vec4 g=tex(tG,(p-r.xy)/(256.*s));return c*.9+g.rgb*g.a*.35;}
vec3 frame(vec3 col,vec2 p,vec4 r){return mix(col,GOLD,ln1(edgeD(p,r),dpr())*.55);}
float tauA(int k){return D(${O.TAU}+k);}
float at(int k,float y,float st){return dens(k,y*(sqrt(tauA(k))/st)/D(${O.H}+k));}
float qv(int k,int i,float st){return D(${O.Q}+k*5+i)*st/sqrt(tauA(k));}
vec3 cone(vec2 p){vec4 r=uV[1];vec2 l=(p-r.xy)/r.zw;float s2=sqrt(tauA(2)),st=max(l.x*s2,.5),yM=uV[5].x,y=yM*(1.-2.*l.y),px=2.*yM/r.w;
  vec3 col=regionBase(p,r);float s0=sqrt(tauA(0)),s1=sqrt(tauA(1));int k0=0,k1=0;float w=0.;
  if(st>s0&&st<=s1){k1=1;w=(st-s0)/(s1-s0);}else if(st>s1){k0=1;k1=2;w=clamp((st-s1)/(s2-s1),0.,1.);}
  if(D(${O.H})>0.){float den=mix(at(k0,y,st),at(k1,y,st),w);vec3 gold=tex(tB,vec2(p.x/(512.*dpr()),p.y/(64.*dpr()))).rgb;
    vec3 fan=gold*pow(den,.7)*1.05;fan=mix(fan,fan*(y>0.?MINT:RED)*1.5,.22*den);col=col*(1.-.55*smoothstep(0.,.08,den))+fan;
    float a=uV[5].y;if(uV[0].w>=2.&&a<1.)col+=HI*exp(-pow((l.x-(a*1.4-.2))*7.,2.))*.45*den;
    for(int i=0;i<5;i++){float q=mix(qv(k0,i,st),qv(k1,i,st),w);vec3 qc=HI;float al=.55;if(i==2){qc=PAPER;al=.9;}if(i==0){qc=RED;al=.7;}if(i==4){qc=MINT;al=.7;}col=mix(col,qc,ln1(y-q,px*dpr()*.9)*al);}}
  col=mix(col,GOLD,ln1(y,px*dpr()*.7)*.35*step(.5,fract(p.x/(6.*dpr()))));
  for(int k=0;k<3;k++)col=mix(col,GOLD,ln1((l.x-sqrt(tauA(k))/s2)*r.z,dpr())*.28);
  if(D(${O.ODDS}+3)>0.){float hs=sqrt(max(D(${O.LV}+2),1.))/s2;if(l.x<=hs){float dash=step(.35,fract(p.x/(9.*dpr())));
    col=mix(col,MINT,ln1(y-D(${O.LV}),px*dpr()*1.2)*.95*dash);col=mix(col,RED,ln1(y-D(${O.LV}+1),px*dpr()*1.2)*.95*dash);}}
  col=mix(col,GOLD,ln1(l.x*r.z,dpr()*1.5)*.6);return frame(col,p,r);}
vec3 odds(vec2 p){vec4 r=uV[2];vec3 col=regionBase(p,r);float sz=min(r.z,r.w);vec2 c=r.xy+vec2(sz*.5,r.w*.5),v=p-c;float dist=length(v),R1=sz*.45,R0=sz*.32;
  if(D(${O.ODDS}+3)>0.){float a=fract(atan(v.x,-v.y)/6.2831853+1.),reveal=uV[0].w>=2.?uV[5].y:1.,pT=D(${O.ODDS}),pS=D(${O.ODDS}+1);
    vec3 seg=GOLD*.35;if(a<pT)seg=MINT;else if(a<pT+pS)seg=RED;
    float gap=min(min(abs(a-pT),abs(a-pT-pS)),min(a,1.-a))*6.2831853*dist,m=dot(tex(tB,vec2(a*3.,dist/(64.*dpr()))).rgb,vec3(.333))/.55;
    float ring=smoothstep(R0-dpr(),R0,dist)*(1.-smoothstep(R1,R1+dpr(),dist))*smoothstep(0.,1.5*dpr(),gap)*step(a,reveal);
    col=mix(col,seg*(.45+.6*m),ring);float inner=1.-smoothstep(R0-3.*dpr(),R0-2.*dpr(),dist);vec4 g=tex(tG,v/(128.*dpr()));
    col=mix(col,col*.5+g.rgb*g.a*.8,inner*.8);col=mix(col,GOLD,ln1(dist-R1-2.5*dpr(),dpr())*.7);}
  return frame(col,p,r);}
vec3 heat(vec2 p){vec4 r=uV[3];vec3 col=regionBase(p,r);float nL=D(${O.SWM}),nT=D(${O.SWM}+1),mx=max(D(${O.SWM}+2),1e-6);
  if(nL>0.){float gap=4.*dpr(),bh=(r.w-gap)*.5,ly=p.y-r.y,mode=ly>bh+gap*.5?1.:0.,by=mode>.5?ly-bh-gap:ly;
    if(by>=0.&&by<bh){float fx=(p.x-r.x)/r.z*nL,fy=by/bh*nT,li=min(floor(fx),nL-1.),ti=nT-1.-min(floor(fy),nT-1.);
      int idx=int(mode*nL*nT+li*nT+ti);float s=clamp(D(${O.SW}+idx)/mx,-1.,1.);
      col=s>=0.?mix(col,MINT,pow(max(s,0.),.7)*.95):mix(col,RED,pow(max(-s,0.),.7)*.95);
      float cx=fract(fx),cy=fract(fy),ce=min(min(cx,1.-cx)*r.z/nL,min(cy,1.-cy)*bh/nT);col*=.55+.45*smoothstep(0.,dpr(),ce);
      if(float(idx)==D(${O.SWM}+3))col=mix(col,HI,1.-smoothstep(.8*dpr(),1.8*dpr(),ce));}}
  return frame(col,p,r);}
vec3 spec(vec2 p){vec4 r=uV[4];vec3 col=regionBase(p,r);
  if(D(${O.CORR}+2)>0.){vec2 l=(p-r.xy)/r.zw;
    if(l.y<.74){int b=int(min(floor(l.x*32.),31.));float yy=1.-l.y/.74,bar=step(yy,D(${O.SPEC}+b))*step(.14,fract(l.x*32.));
      vec3 gold=tex(tB,vec2(p.x/(512.*dpr()),p.y/(32.*dpr()))).rgb;col=mix(col,gold*(.45+.7*yy),bar);col=mix(col,PAPER,ln1((l.x-D(${O.CORR}+1))*r.z,dpr())*.8);}
    else if(l.y>.84)col=mix(col,MINT*.9,l.x<D(${O.CORR})?.9:0.);}
  return frame(col,p,r);}
void main(){vec2 p=vec2(gl_FragCoord.x,uV[0].y-gl_FragCoord.y);vec3 col=backdrop(p);
  if(inR(p,uV[1]))col=cone(p);else if(inR(p,uV[2]))col=odds(p);else if(inR(p,uV[3]))col=heat(p);else if(inR(p,uV[4]))col=spec(p);
  float vg=1.-.35*pow(length(p/uV[0].xy-.5)*1.25,2.);outC=vec4(col*vg,1.);}`;

/* ───────────────────────── state ───────────────────────── */
const V = {
  backend: 'NONE', tier: 'MED', pendingTier: null, tierSince: 0, dirty: true, raf: 0, revealStart: -1e9,
  lastMs: null, gpuMs: null, frames: 0, renders: 0, error: null, data: new Float32Array(DATA_LEN), yMax: 0.01,
  rects: null, css: { w: 0, h: 0 }, scale: 1, images: null, gpu: null, gl: null, ctx2d: null, sig: '',
};
const $ = id => document.getElementById(id);
const active = () => root.dataset.qcView === 'vision' && !document.hidden && !!$('visionGPU');

/* ───────────────────────── data ───────────────────────── */
function packData() {
  const R = window.GLIMMER?.results?.() || {}, D = V.data.fill(0);
  D.set(TAU, O.TAU);
  let yMax = 0;
  const c = R.cone;
  if (c?.dens && c.H) {
    for (let k = 0; k < 3; k++) { D.set(c.dens[k].slice(0, 64), k * 64); D[O.H + k] = c.H[k]; D[O.TAU + k] = c.cones[k].horizon; for (let i = 0; i < 5; i++) D[O.Q + k * 5 + i] = Math.log1p(c.cones[k].q[i]) || 0; }
    yMax = Math.max(Math.abs(D[O.Q + 10]), Math.abs(D[O.Q + 14])) * 1.3;
  }
  const o = R.odds;
  if (o && Number.isFinite(o.pTP) && Number.isFinite(o.tpLog)) {
    D[O.ODDS] = o.pTP; D[O.ODDS + 1] = o.pSL; D[O.ODDS + 2] = o.pOpen; D[O.ODDS + 3] = 1;
    D[O.LV] = o.tpLog; D[O.LV + 1] = o.slLog; D[O.LV + 2] = Math.min(o.horizon, D[O.TAU + 2]); D[O.LV + 3] = o.H || 0;
    yMax = Math.max(yMax, Math.abs(o.tpLog) * 1.25, Math.abs(o.slLog) * 1.25);
  }
  const s = R.sweep;
  if (s?.grid && s.Ls && s.Ths) {
    let mx = 0; for (const g of s.grid) mx = Math.max(mx, Math.abs(g));
    D[O.SWM] = s.Ls.length; D[O.SWM + 1] = s.Ths.length; D[O.SWM + 2] = mx; D[O.SWM + 3] = s.best ?? -1;
    D.set(s.grid.slice(0, DATA_LEN - O.SW), O.SW);
  }
  const f = R.corr;
  if (f?.spectrum) {
    const m = Math.max(1, ...f.spectrum);
    D[O.CORR] = f.effective / f.n; D[O.CORR + 1] = f.meanAbs; D[O.CORR + 2] = 1; D[O.CORR + 3] = f.n;
    for (let i = 0; i < 32; i++) D[O.SPEC + i] = f.spectrum[i] / m;
  }
  V.yMax = Math.max(yMax, 0.002);
  V.results = R;
  return R;
}

/* ───────────────────────── layout ───────────────────────── */
function layout(w, h) {
  const pad = 6, lab = 12, gap = 8, R = {};
  if (w > h * 1.15) {
    const cw = Math.floor(w * 0.56);
    R.cone = [pad, pad + lab, cw - pad, h - pad * 2 - lab - 12];
    const x = cw + gap, rw = w - x - pad, cap = 11, avail = h - pad * 2 - lab * 3 - gap * 2 - cap;
    R.odds = [x, pad + lab, rw, Math.floor(avail * 0.36)];
    R.map = [x, R.odds[1] + R.odds[3] + gap + lab, rw, Math.floor(avail * 0.40)];
    const y3 = R.map[1] + R.map[3] + cap + gap + lab;       // room for the map caption
    R.spec = [x, y3, rw, h - pad - y3];
  } else {
    const avail = h - pad * 2 - lab * 4 - gap * 3 - 11;
    R.cone = [pad, pad + lab, w - pad * 2, Math.floor(avail * 0.46) - 10];
    const y2 = R.cone[1] + R.cone[3] + 12 + gap + lab, h2 = Math.floor(avail * 0.32);
    const ow = Math.floor((w - pad * 2 - gap) * 0.42);
    R.odds = [pad, y2, ow, h2];
    R.map = [pad + ow + gap, y2, w - pad * 2 - ow - gap, h2];
    const y3 = y2 + h2 + 11 + gap + lab;
    R.spec = [pad, y3, w - pad * 2, h - pad - y3];
  }
  for (const k in R) R[k] = R[k].map(v => Math.max(1, v));
  return R;
}
function uniforms() {
  const s = V.scale, u = new Float32Array(32), r = V.rects, dev = a => a.map(v => v * s);
  const now = performance.now(), a = TIERS[V.tier].reveal ? Math.min(1, (now - V.revealStart) / REVEAL_MS) : 1;
  u.set([V.css.w * s, V.css.h * s, now / 1000, TIERS[V.tier].id]);
  u.set(dev(r.cone), 4); u.set(dev(r.odds), 8); u.set(dev(r.map), 12); u.set(dev(r.spec), 16);
  u.set([V.yMax, a, s, 0], 20);
  return { u, reveal: a };
}

/* ───────────────────────── textures ───────────────────────── */
async function loadImages() {
  const entries = await Promise.all(Object.entries(TEX).map(async ([k, url]) => {
    try {
      const img = new Image(); img.decoding = 'async'; img.src = url; await img.decode();
      const bmp = typeof createImageBitmap === 'function' ? await createImageBitmap(img) : img;
      return [k, bmp];
    } catch (_) {
      // Missing texture: a neutral 1x1 keeps every backend rendering.
      const c = document.createElement('canvas'); c.width = c.height = 1;
      const x = c.getContext('2d'); x.fillStyle = k === 'B' ? '#a07c2a' : k === 'G' || k === 'L' ? 'rgba(0,0,0,0)' : '#0a0c0b'; x.fillRect(0, 0, 1, 1);
      return [k, c];
    }
  }));
  return Object.fromEntries(entries);
}

/* ───────────────────────── canvas plumbing ───────────────────────── */
function freshCanvas() {
  const old = $('visionGPU'); if (!old) return null;
  const c = document.createElement('canvas'); c.id = 'visionGPU'; c.className = old.className; c.setAttribute('aria-hidden', 'true');
  old.replaceWith(c); return c;
}
function sizeCanvas(c) {
  const body = c.parentElement, w = Math.max(1, body.clientWidth), h = Math.max(1, body.clientHeight);
  const s = Math.min(devicePixelRatio || 1, TIERS[V.tier].scale);
  if (w !== V.css.w || h !== V.css.h || s !== V.scale) { V.css = { w, h }; V.scale = s; V.rects = layout(w, h); }
  const W = Math.round(w * s), H = Math.round(h * s);
  if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
  return [W, H];
}

/* ───────────────────────── WebGPU backend ───────────────────────── */
async function initWebGPU() {
  const shared = await window.GLIMMER?.gpuDevice?.();
  if (!shared?.device) return false;
  const device = shared.device, canvas = freshCanvas(), ctx = canvas?.getContext('webgpu');
  if (!ctx) return false;
  const format = navigator.gpu.getPreferredCanvasFormat();
  ctx.configure({ device, format, alphaMode: 'opaque' });
  device.pushErrorScope('validation');
  const module = device.createShaderModule({ code: WGSL });
  const pipeline = device.createRenderPipeline({ layout: 'auto', vertex: { module, entryPoint: 'vs' }, fragment: { module, entryPoint: 'fs', targets: [{ format }] }, primitive: { topology: 'triangle-list' } });
  const err = await device.popErrorScope();
  if (err) throw Error(`vision pipeline: ${err.message}`);
  const uni = device.createBuffer({ size: 128, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const data = device.createBuffer({ size: DATA_LEN * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
  const sampler = device.createSampler({ addressModeU: 'repeat', addressModeV: 'repeat', magFilter: 'linear', minFilter: 'linear' });
  const texs = {};
  for (const k of ['B', 'O', 'C', 'G', 'L']) {
    const img = V.images[k], w = img.width, h = img.height;
    const t = device.createTexture({ size: [w, h], format: 'rgba8unorm', usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST | GPUTextureUsage.RENDER_ATTACHMENT });
    device.queue.copyExternalImageToTexture({ source: img }, { texture: t }, [w, h]);
    texs[k] = t;
  }
  const bind = device.createBindGroup({ layout: pipeline.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: uni } }, { binding: 1, resource: { buffer: data } }, { binding: 2, resource: sampler },
    ...['B', 'O', 'C', 'G', 'L'].map((k, i) => ({ binding: 3 + i, resource: texs[k].createView() })),
  ] });
  V.gpu = { device, ctx, pipeline, uni, data, bind, canvas };
  const born = performance.now();
  device.lost.then(info => {
    if (V.gpu?.device !== device) return;
    V.gpu = null;
    // A loss right after we started presenting points at canvas presentation itself. Retrying would
    // crash-loop and take GLIMMER's compute device down with it, so stop presenting via WebGPU this session.
    if (performance.now() - born < 10_000) { V.webgpuBanned = true; note(`webgpu presentation unstable (${String(info?.message || '').slice(0, 40)}) → WebGL2 for this session`); }
    else note('webgpu device lost → WebGL2');
    switchBackend(['webgl2', '2d']);
  });
  return true;
}
function drawWebGPU() {
  const g = V.gpu; sizeCanvas(g.canvas);
  const { u, reveal } = uniforms();
  g.device.queue.writeBuffer(g.uni, 0, u);
  if (V.dataDirty) { g.device.queue.writeBuffer(g.data, 0, V.data); V.dataDirty = false; }
  const enc = g.device.createCommandEncoder();
  const pass = enc.beginRenderPass({ colorAttachments: [{ view: g.ctx.getCurrentTexture().createView(), loadOp: 'clear', storeOp: 'store', clearValue: { r: 0, g: 0, b: 0, a: 1 } }] });
  pass.setPipeline(g.pipeline); pass.setBindGroup(0, g.bind); pass.draw(3); pass.end();
  g.device.queue.submit([enc.finish()]);
  const t0 = performance.now();
  g.device.queue.onSubmittedWorkDone?.().then(() => { V.gpuMs = performance.now() - t0; }).catch(() => {});
  return reveal;
}

/* ───────────────────────── WebGL2 backend ───────────────────────── */
function initWebGL2() {
  const canvas = freshCanvas(); if (!canvas) return false;
  const gl = canvas.getContext('webgl2', { antialias: false, depth: false, stencil: false, alpha: false, powerPreference: 'high-performance' });
  if (!gl) return false;
  canvas.addEventListener('webglcontextlost', e => {
    e.preventDefault(); if (V.gl?.canvas !== canvas) return;
    V.gl = null; note('webgl2 context lost → 2D'); switchBackend(['2d']);
    // Context loss is often transient (GPU process restart): try WebGL2 again, a bounded number of times.
    if ((V.glRetries = (V.glRetries || 0) + 1) <= 2) setTimeout(() => { if (V.backend === 'CANVAS2D') switchBackend(['webgl2', '2d']); }, 5000 * V.glRetries);
  });
  const sh = (t, src) => { const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s)); return s; };
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, GLSL_VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, GLSL_FS)); gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(prog));
  gl.useProgram(prog); gl.bindVertexArray(gl.createVertexArray());
  const unit = (name, i, tex) => { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, tex); gl.uniform1i(gl.getUniformLocation(prog, name), i); };
  const dataTex = gl.createTexture();
  unit('uD', 0, dataTex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.R32F, DATA_LEN, 1, 0, gl.RED, gl.FLOAT, V.data);
  ['B', 'O', 'C', 'G', 'L'].forEach((k, i) => {
    const t = gl.createTexture(); unit(`t${k}`, i + 1, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, V.images[k]);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  });
  V.gl = { gl, prog, dataTex, uV: gl.getUniformLocation(prog, 'uV'), canvas };
  return true;
}
function drawWebGL2() {
  const g = V.gl, gl = g.gl; const [W, H] = sizeCanvas(g.canvas);
  const { u, reveal } = uniforms();
  gl.viewport(0, 0, W, H); gl.useProgram(g.prog);
  if (V.dataDirty) { gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, g.dataTex); gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, DATA_LEN, 1, gl.RED, gl.FLOAT, V.data); V.dataDirty = false; }
  gl.uniform4fv(g.uV, u); gl.drawArrays(gl.TRIANGLES, 0, 3);
  return reveal;
}

/* ───────────────────────── Canvas 2D backend ───────────────────────── */
function init2D() {
  const canvas = freshCanvas(), ctx = canvas?.getContext('2d', { alpha: false });
  if (!ctx) return false;
  const pat = k => { const p = ctx.createPattern(V.images[k], 'repeat'); return p; };
  V.ctx2d = { ctx, canvas, pat: { B: pat('B'), O: pat('O'), C: pat('C'), G: pat('G'), L: pat('L') } };
  return true;
}
function draw2D() {
  const g = V.ctx2d, x = g.ctx, [W, H] = sizeCanvas(g.canvas), s = V.scale, D = V.data, r = V.rects;
  x.setTransform(1, 0, 0, 1, 0, 0);
  const fillPat = (p, sc, rx, ry, rw, rh) => { p.setTransform?.(new DOMMatrix().scale(sc)); x.fillStyle = p; x.fillRect(rx, ry, rw, rh); };
  fillPat(g.pat.O, s / 2, 0, 0, W, H); fillPat(g.pat.L, s / 2, 0, 0, W, H);
  x.scale(s, s);
  const region = rr => { const [rx, ry, rw, rh] = rr; fillPat(g.pat.C, 0.25, rx, ry, rw, rh); x.globalAlpha = 0.35; fillPat(g.pat.G, 1, rx, ry, rw, rh); x.globalAlpha = 1; };
  const frame = rr => { x.strokeStyle = 'rgba(217,173,69,.55)'; x.lineWidth = 1; x.strokeRect(rr[0] + .5, rr[1] + .5, rr[2] - 1, rr[3] - 1); };
  // cone
  region(r.cone);
  if (D[O.H] > 0) {
    const [cx, cy, cw, ch] = r.cone, s2 = Math.sqrt(D[O.TAU + 2]), yM = V.yMax;
    const densAt = (k, z) => { const xx = (z + 1) * 32 - 0.5; if (xx < -1 || xx > 64) return 0; const i0 = Math.max(0, Math.min(63, Math.floor(xx))), i1 = Math.min(63, i0 + 1); return D[k * 64 + i0] + (D[k * 64 + i1] - D[k * 64 + i0]) * Math.max(0, Math.min(1, xx - i0)); };
    const blend = st => { const s0 = Math.sqrt(D[O.TAU]), s1 = Math.sqrt(D[O.TAU + 1]); if (st <= s0) return [0, 0, 0]; if (st <= s1) return [0, 1, (st - s0) / (s1 - s0)]; return [1, 2, Math.min(1, (st - s1) / (s2 - s1))]; };
    const step = 3;
    for (let px = 0; px < cw; px += step) {
      const st = Math.max(px / cw * s2, 0.5), [k0, k1, w] = blend(st);
      for (let py = 0; py < ch; py += step) {
        const y = yM * (1 - 2 * py / ch), at = k => densAt(k, y * (Math.sqrt(D[O.TAU + k]) / st) / D[O.H + k]);
        const den = at(k0) * (1 - w) + at(k1) * w;
        if (den > 0.02) { x.fillStyle = `rgba(${y > 0 ? '226,190,100' : '222,160,95'},${Math.min(1, Math.pow(den, 0.7))})`; x.fillRect(cx + px, cy + py, step, step); }
      }
    }
    const qcol = ['#e47f70', '#f3d477', '#f0ede4', '#f3d477', '#92d7b7'];
    for (let i = 0; i < 5; i++) {
      x.beginPath();
      for (let px = 0; px <= cw; px += 2) { const st = Math.max(px / cw * s2, 0.5), [k0, k1, w] = blend(st), qv = k => D[O.Q + k * 5 + i] * st / Math.sqrt(D[O.TAU + k]); const q = qv(k0) * (1 - w) + qv(k1) * w; const py = cy + (1 - q / yM) * ch / 2; px ? x.lineTo(cx + px, py) : x.moveTo(cx + px, py); }
      x.strokeStyle = qcol[i]; x.globalAlpha = i === 2 ? 0.9 : 0.6; x.stroke(); x.globalAlpha = 1;
    }
    if (D[O.ODDS + 3] > 0) {
      const hs = Math.sqrt(Math.max(D[O.LV + 2], 1)) / s2;
      x.setLineDash([5, 4]);
      for (const [v, c] of [[D[O.LV], '#92d7b7'], [D[O.LV + 1], '#e47f70']]) { const py = cy + (1 - v / yM) * ch / 2; x.strokeStyle = c; x.beginPath(); x.moveTo(cx, py); x.lineTo(cx + hs * cw, py); x.stroke(); }
      x.setLineDash([]);
    }
  }
  frame(r.cone);
  // odds
  region(r.odds);
  if (D[O.ODDS + 3] > 0) {
    const [ox, oy, ow, oh] = r.odds, sz = Math.min(ow, oh), c = [ox + sz / 2, oy + oh / 2], R1 = sz * 0.45, R0 = sz * 0.32, mid = (R0 + R1) / 2;
    let a0 = -Math.PI / 2;
    x.lineWidth = R1 - R0;
    for (const [p, col] of [[D[O.ODDS], '#92d7b7'], [D[O.ODDS + 1], '#e47f70'], [D[O.ODDS + 2], 'rgba(217,173,69,.35)']]) { const a1 = a0 + p * Math.PI * 2; x.strokeStyle = col; x.beginPath(); x.arc(c[0], c[1], mid, a0 + 0.02, Math.max(a0 + 0.02, a1 - 0.02)); x.stroke(); a0 = a1; }
    x.lineWidth = 1;
  }
  frame(r.odds);
  // heatmap
  region(r.map);
  if (D[O.SWM] > 0) {
    const [mx, my, mw, mh] = r.map, nL = D[O.SWM], nT = D[O.SWM + 1], m = Math.max(D[O.SWM + 2], 1e-6), bh = (mh - 4) / 2, cw = mw / nL, chh = bh / nT;
    for (let mode = 0; mode < 2; mode++) for (let li = 0; li < nL; li++) for (let ti = 0; ti < nT; ti++) {
      const idx = mode * nL * nT + li * nT + ti, v = Math.max(-1, Math.min(1, D[O.SW + idx] / m)), a = Math.pow(Math.abs(v), 0.7) * 0.95;
      x.fillStyle = v >= 0 ? `rgba(146,215,183,${a})` : `rgba(228,127,112,${a})`;
      const px = mx + li * cw, py = my + mode * (bh + 4) + (nT - 1 - ti) * chh;
      x.fillRect(px + 0.5, py + 0.5, Math.max(0.5, cw - 1), Math.max(0.5, chh - 1));
      if (idx === D[O.SWM + 3]) { x.strokeStyle = '#f3d477'; x.strokeRect(px + 0.5, py + 0.5, cw - 1, chh - 1); }
    }
  }
  frame(r.map);
  // spectrum
  region(r.spec);
  if (D[O.CORR + 2] > 0) {
    const [sx, sy, sw, sh] = r.spec, bw = sw / 32;
    fillPat(g.pat.B, 0.5, 0, 0, 0, 0);
    for (let i = 0; i < 32; i++) { const hh = D[O.SPEC + i] * sh * 0.74; x.fillStyle = g.pat.B; x.fillRect(sx + i * bw + bw * 0.14, sy + sh * 0.74 - hh, bw * 0.86, hh); }
    x.fillStyle = 'rgba(146,215,183,.85)'; x.fillRect(sx, sy + sh * 0.84, sw * D[O.CORR], sh * 0.16);
    x.strokeStyle = '#f0ede4'; x.beginPath(); x.moveTo(sx + sw * D[O.CORR + 1], sy); x.lineTo(sx + sw * D[O.CORR + 1], sy + sh * 0.74); x.stroke();
  }
  frame(r.spec);
  return 1;
}

/* ───────────────────────── text overlay ───────────────────────── */
const pctS = v => Number.isFinite(v) ? `${v >= 0 ? '+' : '−'}${Math.abs(v * 100).toFixed(2)}%` : '—';
const hm = s => s >= 3600 ? `${s / 3600}h` : `${Math.round(s / 60)}m`;
function drawText() {
  const c = $('visionText'); if (!c) return;
  const w = V.css.w, h = V.css.h, s = Math.min(devicePixelRatio || 1, 3);
  if (c.width !== Math.round(w * s) || c.height !== Math.round(h * s)) { c.width = Math.round(w * s); c.height = Math.round(h * s); }
  const x = c.getContext('2d'); x.setTransform(s, 0, 0, s, 0, 0); x.clearRect(0, 0, w, h);
  const R = V.results || {}, r = V.rects, fs = Math.max(6.5, Math.min(9, w / 52));
  const font = (sz, wgt = 600) => { x.font = `${wgt} ${sz}px ui-monospace,SFMono-Regular,Menlo,monospace`; };
  const title = (rr, left, right) => {
    font(fs, 700); x.fillStyle = '#f3d477'; x.textBaseline = 'bottom'; x.textAlign = 'left'; x.fillText(left, rr[0] + 1, rr[1] - 2);
    if (right) { font(fs * 0.86, 500); x.fillStyle = '#9b9687'; x.textAlign = 'right'; x.fillText(right, rr[0] + rr[2] - 1, rr[1] - 2); }
  };
  const shadowText = (t, px, py) => { x.fillStyle = 'rgba(0,0,0,.72)'; x.fillText(t, px + 0.6, py + 0.6); x.fillStyle = x._c; x.fillText(t, px, py); };
  const col = c2 => { x._c = c2; };
  const eng = e => (e || []).join('/').toUpperCase();
  // cone
  const cone = R.cone;
  title(r.cone, 'RISK CONE · BOOTSTRAP MC', cone ? `${cone.paths.toLocaleString()} paths · ${eng(cone.engines)}${cone.stale ? ' · STALE' : ''}` : 'warming');
  if (cone && V.data[O.H] > 0) {
    const [cx, cy, cw, ch] = r.cone, yM = V.yMax;
    font(fs * 0.86, 500); x.textBaseline = 'middle'; x.textAlign = 'left';
    for (const f of [1, 0.5, -0.5, -1]) { col('#9b9687'); shadowText(pctS(Math.expm1(yM * f * 0.92)), cx + 4, cy + (1 - f * 0.92) * ch / 2); }
    x.textAlign = 'center'; x.textBaseline = 'bottom';
    const s2 = Math.sqrt(TAU[2]);
    TAU.forEach(t => { col('#bdb49b'); shadowText(hm(t), Math.min(cx + cw - 10, cx + Math.sqrt(t) / s2 * cw), cy + ch - 2); });
    x.textAlign = 'right'; x.textBaseline = 'middle';
    const q = cone.cones[2].q, lab = [['P95', q[4], '#92d7b7'], ['P50', q[2], '#f0ede4'], ['P5', q[0], '#e47f70']];
    for (const [n, v, cc] of lab) { col(cc); shadowText(`${n} ${pctS(v)}`, cx + cw - 4, cy + (1 - Math.log1p(v) / yM) * ch / 2 + (n === 'P95' ? -7 : n === 'P5' ? 7 : -7)); }
    x.textAlign = 'left'; x.textBaseline = 'top'; font(fs * 0.8, 500); col('#9b9687');
    shadowText(`max DD 4h P50 ${pctS(-cone.mdd50).replace('+', '')} · P95 ${pctS(-cone.mdd95).replace('+', '')}`, cx + 2, cy + ch + 2);
  }
  // odds
  const o = R.odds;
  title(r.odds, `TRADE ODDS${o ? ` · ${o.mode} · ${hm(o.horizon)}` : ''}`, o ? `${o.n.toLocaleString()} paths` : 'warming');
  if (o && V.data[O.ODDS + 3] > 0) {
    const [ox, oy, ow, oh] = r.odds, sz = Math.min(ow, oh), cxx = ox + sz / 2, cyy = oy + oh / 2;
    x.textAlign = 'center'; x.textBaseline = 'middle'; font(Math.max(9, sz * 0.15), 700); col('#92d7b7'); shadowText(`${Math.round(o.pTP * 100)}%`, cxx, cyy - sz * 0.03);
    font(Math.max(5.5, sz * 0.065), 500); col('#9b9687'); shadowText('TP FIRST', cxx, cyy + sz * 0.1);
    if (ow - sz > 50) {
      const tx = ox + sz + 4; x.textAlign = 'left'; font(fs * 0.9, 600);
      const lines = [[`TP ${(o.pTP * 100).toFixed(1)}%`, '#92d7b7'], [`SL ${(o.pSL * 100).toFixed(1)}%`, '#e47f70'], [`OPEN ${(o.pOpen * 100).toFixed(1)}%`, '#d9ad45'], [`E[R] ${o.expR.toFixed(2)}`, '#f0ede4'], [`R:R ${o.rr.toFixed(2)}`, '#9b9687'], [`±${(o.se * 100).toFixed(1)}%`, '#9b9687']];
      const lh = Math.min(fs * 1.35, oh / lines.length);
      lines.forEach(([t, cc], i) => { col(cc); shadowText(t, tx, oy + oh / 2 + (i - (lines.length - 1) / 2) * lh); });
    }
  }
  // heatmap
  const sw = R.sweep;
  title(r.map, 'HOLDOUT SHARPE · MOM ▲ REV ▼', sw ? `${sw.combos} combos · ${eng(sw.engines)}` : 'warming');
  if (sw && V.data[O.SWM] > 0) {
    const [mx, my, mw, mh] = r.map; font(fs * 0.8, 500); x.textBaseline = 'top'; x.textAlign = 'left'; col('#9b9687');
    shadowText(`best-in-train ${sw.mode === 'REVERT' ? 'REV' : 'MOM'} ${sw.lookbackMin.toFixed(1)}m th ${sw.th.toFixed(2)}σ → hold ${sw.hold.toFixed(2)} · ${Math.round(sw.positiveHold * 100)}% +`, mx + 1, my + mh + 2);
    x.textAlign = 'right'; x.textBaseline = 'bottom'; col('#bdb49b'); shadowText('lookback →', mx + mw - 3, my + mh - 2);
  }
  // spectrum
  const f = R.corr;
  title(r.spec, 'FLEET INDEPENDENCE · MEAN |ρ| SPECTRUM', f ? `≈${f.effective.toFixed(0)} of ${f.n} effective` : 'warming');
  if (f && V.data[O.CORR + 2] > 0) {
    const [sx, sy, sww, sh] = r.spec; font(fs * 0.8, 500); x.textBaseline = 'top'; x.textAlign = 'left'; col('#f0ede4');
    shadowText(`mean |ρ| ${f.meanAbs.toFixed(3)}`, Math.min(sx + sww * f.meanAbs + 3, sx + sww - 70), sy + 2);
  }
  if (!cone && !o && !sw && !f) {
    x.textAlign = 'center'; x.textBaseline = 'middle'; font(fs * 1.1, 700); col('#f3d477');
    const [cx, cy, cw, ch] = r.cone, mx = cx + cw / 2, my = cy + ch / 2;
    shadowText('VISION WARMING', mx, my - fs); font(fs * 0.9, 500); col('#9b9687'); shadowText('waiting for GLIMMER output (≈5 min of price history)', mx, my + fs * 0.6);
  }
}

/* ───────────────────────── orchestration ───────────────────────── */
const log = [];
function note(m) { log.push(`${new Date().toISOString().slice(11, 19)} ${m}`); if (log.length > 20) log.shift(); }
function pickTier() {
  const g = window.GLIMMER?.governor?.();
  if (!g) return 'MED';
  if (g.health === 'RED' || g.pressure === 'THROTTLED-LIKE') return 'LOW';
  if (g.health === 'GREEN' && g.envelope >= 0.6 && (g.pressure === 'HEADROOM' || g.pressure === 'NORMAL')) return 'ULTRA';
  if (g.envelope >= 0.25) return 'HIGH';
  return 'MED';
}
function updateTier() {
  const want = pickTier(), now = performance.now();
  if (want === V.tier) { V.pendingTier = null; return; }
  // Hysteresis: a lower tier applies at once, a higher one only after holding for 3 s.
  if (TIERS[want].id < TIERS[V.tier].id) { V.tier = want; V.dirty = true; return; }
  if (V.pendingTier !== want) { V.pendingTier = want; V.tierSince = now; return; }
  if (now - V.tierSince > 3000) { V.tier = want; V.pendingTier = null; V.dirty = true; }
}
async function switchBackend(order) {
  for (const b of order) {
    try {
      if (b === 'webgpu' && navigator.gpu && !V.webgpuBanned && await initWebGPU()) { V.backend = 'WEBGPU'; break; }
      if (b === 'webgl2' && initWebGL2()) { V.backend = 'WEBGL2'; break; }
      if (b === '2d' && init2D()) { V.backend = 'CANVAS2D'; break; }
    } catch (e) { note(`${b} init failed: ${String(e.message || e).slice(0, 60)}`); }
  }
  V.dataDirty = true; V.dirty = true; schedule();
}
function schedule() { if (!V.raf && active()) V.raf = requestAnimationFrame(frame); }
function frame() {
  V.raf = 0;
  if (!active()) return;
  const t0 = performance.now();
  try {
    let reveal = 1;
    if (V.backend === 'WEBGPU' && V.gpu) reveal = drawWebGPU();
    else if (V.backend === 'WEBGL2' && V.gl) reveal = drawWebGL2();
    else if (V.backend === 'CANVAS2D' && V.ctx2d) reveal = draw2D();
    else return;
    if (V.dirty) drawText();
    V.dirty = false; V.renders++;
    V.lastMs = performance.now() - t0;
    window.GLIMMER?.account?.(V.backend === 'CANVAS2D' ? 'main' : 'gpu', V.lastMs, 'P1');
    const meta = $('visionMeta'); if (meta) meta.textContent = `${V.backend} · ${V.tier} · ${root.dataset.qcTexture === 'aurum' ? 'AURUM' : 'NO TEX'}`;
    if (reveal < 1) V.raf = requestAnimationFrame(frame);    // brief reveal only, then still
  } catch (e) {
    V.error = String(e.message || e); note(`render error: ${V.error.slice(0, 60)}`);
    const next = V.backend === 'WEBGPU' ? ['webgl2', '2d'] : ['2d'];
    V.gpu = null; V.gl = null; switchBackend(next);
  }
}
function refreshData(reveal) {
  const R = packData();
  const sig = ['cone', 'odds', 'sweep', 'corr'].map(k => R[k]?.at ?? '').join('|');
  if (sig === V.sig && !reveal) return;
  V.sig = sig; V.dataDirty = true; V.dirty = true;
  if (TIERS[V.tier].reveal) V.revealStart = performance.now();
  schedule();
}
async function boot() {
  if (!$('visionGPU')) return;
  V.images = await loadImages();
  await window.GLIMMER?.ready;
  refreshData(true);
  await switchBackend(['webgpu', 'webgl2', '2d']);
  note(`vision backend ${V.backend}`);
  addEventListener('glimmer:result', () => refreshData(false));
  window.GLIMMER?.onGpuDevice?.(() => { if (V.backend !== 'WEBGPU' && !V.webgpuBanned) switchBackend(['webgpu', 'webgl2', '2d']); });
  const body = $('visionGPU').parentElement;
  if (typeof ResizeObserver === 'function') new ResizeObserver(() => { V.dirty = true; schedule(); }).observe(body);
  new MutationObserver(() => { if (active()) { refreshData(true); V.dirty = true; schedule(); } }).observe(root, { attributes: true, attributeFilter: ['data-qc-view', 'data-qc-texture'] });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { V.dirty = true; schedule(); } });
  setInterval(() => { if (!active()) return; const before = V.tier; updateTier(); if (V.tier !== before) { note(`tier ${before}→${V.tier}`); schedule(); } }, 1000);
}
window.__quadcomVisionShaders = { WGSL, GLSL_VS, GLSL_FS, frameInputs: () => V.rects ? { data: V.data.slice(), uniforms: uniforms().u, css: { ...V.css }, scale: V.scale } : null };
window.__quadcomVision = () => ({ backend: V.backend, tier: V.tier, scale: V.scale, lastMs: V.lastMs, gpuMs: V.gpuMs, renders: V.renders, texture: root.dataset.qcTexture, active: active(), error: V.error, log: log.slice(-8) });
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
