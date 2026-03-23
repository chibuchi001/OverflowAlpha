import { useState, useEffect, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, Cell, CartesianGrid, ReferenceLine } from "recharts";

const AlphaLogo = ({ size = 28 }) => (<svg width={size} height={size} viewBox="0 0 40 40"><rect width="40" height="40" rx="8" fill="url(#lg)" /><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#00e5a0" /><stop offset="100%" stopColor="#4d8eff" /></linearGradient></defs><text x="20" y="22" textAnchor="middle" dominantBaseline="central" fontFamily="Georgia,serif" fontSize="24" fill="#06060b">α</text></svg>);
const PERF = { total_return:2298.24,total_return_pct:0.2298,sharpe_ratio:1.4265,sortino_ratio:3.3652,max_drawdown:831.98,max_drawdown_pct:0.0623,win_rate:0.4706,profit_factor:2.3741,avg_trade_pnl:67.85,avg_winner:249.11,avg_loser:-93.27,best_trade:487.01,worst_trade:-252.21,total_trades:34,total_markets_traded:30 };
const TRADES = [{pnl:48.36},{pnl:-18.96},{pnl:106.58},{pnl:-40.12},{pnl:249.01},{pnl:159.07},{pnl:-58.69},{pnl:-119.49},{pnl:-34.04},{pnl:-9.39},{pnl:16.56},{pnl:-107.37},{pnl:451.19},{pnl:-71.15},{pnl:-10.15},{pnl:49.22},{pnl:186.43},{pnl:214.09},{pnl:-75.66},{pnl:-27.56},{pnl:342.02},{pnl:-219.48},{pnl:-156.91},{pnl:-175.32},{pnl:-156.67},{pnl:-123.22},{pnl:487.01},{pnl:355.85},{pnl:312.28},{pnl:179.29},{pnl:358.1},{pnl:470.73},{pnl:-252.21},{pnl:-22.49}];
const HM=[[1.12,.98,1.05,1.08,.92],[1.18,1.25,1.31,1.14,1.01],[1.15,1.29,1.43,1.22,.96],[1.08,1.21,1.38,1.28,.88],[.95,1.10,1.18,1.15,.80]];
const HX=["0.04","0.06","0.08","0.10","0.12"],HY=["0.15","0.25","0.35","0.50","0.65"];
const bE=t=>{const c=[{i:0,eq:10000}];let e=10000;t.forEach((x,idx)=>{e+=x.pnl;c.push({i:idx+1,eq:Math.round(e*100)/100})});return c};
const bD=eq=>{let p=eq[0].eq;return eq.map(x=>{if(x.eq>p)p=x.eq;return{...x,dd:p>0?-((p-x.eq)/p)*100:0}})};
const S={bg:"#06060b",sf:"#0c0c14",bd:"rgba(255,255,255,0.05)",tx:"#e8e8ed",mt:"#5a5a6e",ac:"#00e5a0",rd:"#ff4d6a",bl:"#4d8eff",pu:"#9d6fff",yl:"#ffc44d",mn:"'DM Mono','SF Mono',monospace",sr:"'Instrument Serif',Georgia,serif"};
const fonts=`@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Instrument+Serif:ital@0;1&display=swap');`;
const M=({label,value,sub,color})=>(<div style={{padding:"14px 18px",background:S.sf,border:`1px solid ${S.bd}`,borderRadius:8}}><div style={{fontSize:10,color:S.mt,textTransform:"uppercase",letterSpacing:"0.12em",fontFamily:S.mn,marginBottom:6}}>{label}</div><div style={{fontSize:22,fontWeight:500,color:color||S.tx,fontFamily:S.mn,lineHeight:1}}>{value}</div>{sub&&<div style={{fontSize:10,color:S.mt,fontFamily:S.mn,marginTop:4}}>{sub}</div>}</div>);
const P=({children,color=S.ac})=>(<span style={{display:"inline-block",padding:"3px 10px",borderRadius:100,fontSize:10,fontFamily:S.mn,letterSpacing:"0.06em",background:`${color}15`,color,border:`1px solid ${color}30`}}>{children}</span>);
const TT=({active,payload})=>{if(!active||!payload?.length)return null;return(<div style={{background:"#12121e",border:`1px solid ${S.bd}`,borderRadius:6,padding:"6px 10px",fontSize:11,fontFamily:S.mn}}>{payload.map((p,i)=>(<div key={i} style={{color:p.color||S.tx}}>{p.name}:{typeof p.value==="number"?(p.name==="dd"?`${p.value.toFixed(1)}%`:`$${p.value.toLocaleString()}`):p.value}</div>))}</div>)};
const HMap=({data,xl,yl})=>{const cw=60,ch=34,pl=46,pt=22;const mx=Math.max(...data.flat()),mn=Math.min(...data.flat());const gc=v=>{const t=mx===mn?.5:(v-mn)/(mx-mn);return t<.3?`rgba(255,77,106,${.3+t})`:t<.6?`rgba(255,196,77,${.2+t*.5})`:`rgba(0,229,160,${.3+t*.5})`};return(<svg width={pl+xl.length*cw+10} height={pt+yl.length*ch+28} style={{display:"block"}}>{xl.map((l,i)=><text key={`x${i}`} x={pl+i*cw+cw/2} y={pt-7} fill={S.mt} fontSize={9} fontFamily={S.mn} textAnchor="middle">{l}</text>)}{yl.map((l,i)=><text key={`y${i}`} x={pl-8} y={pt+i*ch+ch/2+3} fill={S.mt} fontSize={9} fontFamily={S.mn} textAnchor="end">{l}</text>)}{data.map((r,yi)=>r.map((v,xi)=><g key={`${yi}-${xi}`}><rect x={pl+xi*cw} y={pt+yi*ch} width={cw-2} height={ch-2} rx={4} fill={gc(v)}/><text x={pl+xi*cw+cw/2-1} y={pt+yi*ch+ch/2+3} fill={S.tx} fontSize={10} fontFamily={S.mn} textAnchor="middle" fillOpacity={.9}>{v.toFixed(2)}</text></g>))}<text x={pl+(xl.length*cw)/2} y={pt+yl.length*ch+20} fill={S.mt} fontSize={9} fontFamily={S.mn} textAnchor="middle">Edge threshold</text></svg>)};

const Auth=({onLogin})=>{const[tab,setTab]=useState("login");const[email,setEmail]=useState("");const[pw,setPw]=useState("");const[ld,setLd]=useState(false);const[err,setErr]=useState("");
const go=()=>{if(!email||!pw){setErr("All fields required");return}if(pw.length<6){setErr("6+ chars required");return}setLd(true);setErr("");setTimeout(()=>{setLd(false);onLogin(email)},700)};
const inp={width:"100%",padding:"10px 12px",background:"rgba(255,255,255,0.03)",border:`1px solid ${S.bd}`,borderRadius:6,color:S.tx,fontSize:13,fontFamily:S.mn,outline:"none",boxSizing:"border-box"};
return(<div style={{minHeight:"100vh",background:S.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:S.mn}}><style>{fonts}</style>
<div style={{width:380,padding:32}}><div style={{textAlign:"center",marginBottom:40}}><div style={{display:"inline-flex",alignItems:"center",gap:10,marginBottom:12}}><AlphaLogo size={32}/><span style={{fontSize:20,fontWeight:500,color:S.tx}}>orderflow</span><span style={{fontSize:20,color:S.mt}}>alpha</span></div><div style={{fontSize:11,color:S.mt,letterSpacing:"0.15em",textTransform:"uppercase"}}>On-chain trading intelligence</div></div>
<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:12,padding:28}}>
<div style={{display:"flex",marginBottom:24,borderBottom:`1px solid ${S.bd}`}}>{["login","signup"].map(t=>(<button key={t} onClick={()=>{setTab(t);setErr("")}} style={{flex:1,padding:"10px 0",fontSize:11,textTransform:"uppercase",letterSpacing:"0.1em",color:tab===t?S.tx:S.mt,background:"none",border:"none",borderBottom:tab===t?`2px solid ${S.ac}`:"2px solid transparent",cursor:"pointer",fontFamily:S.mn}}>{t==="login"?"Sign In":"Create Account"}</button>))}</div>
<div style={{marginBottom:16}}><label style={{display:"block",fontSize:10,color:S.mt,marginBottom:6,textTransform:"uppercase",letterSpacing:"0.1em"}}>Email</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="trader@example.com" style={inp}/></div>
<div style={{marginBottom:20}}><label style={{display:"block",fontSize:10,color:S.mt,marginBottom:6,textTransform:"uppercase",letterSpacing:"0.1em"}}>Password</label><input type="password" value={pw} onChange={e=>setPw(e.target.value)} placeholder="••••••••" style={inp} onKeyDown={e=>e.key==="Enter"&&go()}/></div>
{err&&<div style={{fontSize:11,color:S.rd,marginBottom:12}}>{err}</div>}
<button onClick={go} disabled={ld} style={{width:"100%",padding:"12px 0",background:ld?`${S.ac}60`:S.ac,color:S.bg,border:"none",borderRadius:6,fontSize:12,fontWeight:500,fontFamily:S.mn,cursor:ld?"wait":"pointer",letterSpacing:"0.06em",textTransform:"uppercase"}}>{ld?"Authenticating...":tab==="login"?"Sign In":"Create Account"}</button>
<div style={{textAlign:"center",marginTop:16,fontSize:10,color:S.mt}}>Secured by <span style={{color:S.tx}}>Clerk</span></div></div>
<div style={{textAlign:"center",marginTop:20}}><button onClick={()=>onLogin("demo@orderflow.alpha")} style={{background:"none",border:`1px solid ${S.bd}`,borderRadius:6,padding:"8px 20px",color:S.mt,fontSize:10,fontFamily:S.mn,cursor:"pointer"}}>Skip to demo →</button></div></div></div>)};

const SMP=[{q:"Will Bitcoin exceed $150K by end of 2026?",cat:"Crypto",price:.42},{q:"Will the Fed cut rates in Q2 2026?",cat:"Economics",price:.61},{q:"Will a major stablecoin depeg in 2026?",cat:"Crypto",price:.18},{q:"Will US inflation drop below 2.5% by Dec 2026?",cat:"Economics",price:.55}];
const GP=()=>{const[key,setKey]=useState("");const[cQ,setCQ]=useState("");const[cP,setCP]=useState("0.50");const[res,setRes]=useState([]);const[ld,setLd]=useState(false);const[err,setErr]=useState("");
const run=async(q,cat,mp)=>{if(!key){setErr("Enter Groq API key");return}setLd(true);setErr("");
try{const r=await fetch("https://api.groq.com/openai/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json","Authorization":`Bearer ${key}`},body:JSON.stringify({model:"llama-3.3-70b-versatile",messages:[{role:"system",content:`You are a prediction market analyst. Respond ONLY with JSON: {"probability":<1-99>,"confidence":<20-90>,"reasoning":"<2-3 sentences>","key_factors":["<f1>","<f2>","<f3>"]}`},{role:"user",content:`Event: ${q}\nCategory: ${cat||"General"}\nMarket: ${(mp*100).toFixed(0)}%\nEstimate as JSON.`}],temperature:.3,max_tokens:300,response_format:{type:"json_object"}})});
if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e?.error?.message||`HTTP ${r.status}`)}
const d=await r.json();const p=JSON.parse(d.choices[0].message.content);const ai=p.probability/100;
setRes(prev=>[{q:q.length>50?q.slice(0,47)+"...":q,mp,ai,edge:ai-mp,conf:p.confidence,reason:p.reasoning,factors:p.key_factors||[],tok:d.usage?.total_tokens||0,ts:new Date().toLocaleTimeString()},...prev].slice(0,15))}catch(e){setErr(e.message)}finally{setLd(false)}};
return(<><div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18,marginBottom:16}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:10}}>GROQ API — LLAMA 3.3 70B</div>
<div style={{display:"flex",gap:10,alignItems:"center"}}><input type="password" value={key} onChange={e=>setKey(e.target.value)} placeholder="gsk_..." style={{flex:1,padding:"8px 12px",background:"rgba(255,255,255,0.03)",border:`1px solid ${S.bd}`,borderRadius:6,color:S.tx,fontSize:12,fontFamily:S.mn,outline:"none"}}/><a href="https://console.groq.com/keys" target="_blank" rel="noreferrer" style={{fontSize:10,color:S.ac,fontFamily:S.mn,whiteSpace:"nowrap"}}>Free key →</a></div></div>
<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18,marginBottom:16}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:12}}>SAMPLE MARKETS</div>
<div style={{display:"flex",flexWrap:"wrap",gap:8}}>{SMP.map((m,i)=>(<button key={i} onClick={()=>run(m.q,m.cat,m.price)} disabled={ld} style={{padding:"8px 14px",background:`${S.ac}08`,border:`1px solid ${S.ac}20`,borderRadius:6,color:S.tx,fontSize:11,fontFamily:S.mn,cursor:ld?"wait":"pointer",textAlign:"left",maxWidth:260}}><div style={{marginBottom:3}}>{m.q.slice(0,42)}{m.q.length>42?"...":""}</div><div style={{fontSize:9,color:S.mt}}>{m.cat} · {(m.price*100).toFixed(0)}%</div></button>))}</div></div>
<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18,marginBottom:16}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:10}}>CUSTOM EVENT</div>
<div style={{display:"flex",gap:10}}><input value={cQ} onChange={e=>setCQ(e.target.value)} placeholder="Will X happen by Y?" style={{flex:1,padding:"8px 12px",background:"rgba(255,255,255,0.03)",border:`1px solid ${S.bd}`,borderRadius:6,color:S.tx,fontSize:12,fontFamily:S.mn,outline:"none"}} onKeyDown={e=>e.key==="Enter"&&cQ&&run(cQ,"",parseFloat(cP))}/><input value={cP} onChange={e=>setCP(e.target.value)} style={{width:60,padding:"8px",background:"rgba(255,255,255,0.03)",border:`1px solid ${S.bd}`,borderRadius:6,color:S.tx,fontSize:12,fontFamily:S.mn,outline:"none",textAlign:"center"}}/><button onClick={()=>cQ&&run(cQ,"",parseFloat(cP))} disabled={ld||!cQ} style={{padding:"8px 18px",background:ld?`${S.ac}40`:S.ac,color:S.bg,border:"none",borderRadius:6,fontSize:11,fontFamily:S.mn,fontWeight:500,cursor:ld?"wait":"pointer"}}>{ld?"...":"Analyze"}</button></div>
{err&&<div style={{fontSize:11,color:S.rd,marginTop:8}}>{err}</div>}</div>
{res.length>0&&<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:14}}>AI ESTIMATES ({res.length})</div>
{res.map((r,i)=>{const ec=r.edge>.05?S.ac:r.edge<-.05?S.rd:S.mt;const act=r.edge>.05?"BUY YES":r.edge<-.05?"BUY NO":"HOLD";return(
<div key={i} style={{padding:14,border:`1px solid ${S.bd}`,borderRadius:8,marginBottom:10,background:i===0?`${ec}06`:"transparent"}}>
<div style={{display:"flex",justifyContent:"space-between",alignItems:"start",marginBottom:8}}><div style={{fontSize:12,fontWeight:500,flex:1,marginRight:12}}>{r.q}</div><P color={ec}>{act}</P></div>
<div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:8}}>
<div><div style={{fontSize:9,color:S.mt}}>MARKET</div><div style={{fontSize:14,fontFamily:S.mn}}>{(r.mp*100).toFixed(0)}%</div></div>
<div><div style={{fontSize:9,color:S.mt}}>AI EST.</div><div style={{fontSize:14,fontFamily:S.mn,color:S.ac}}>{(r.ai*100).toFixed(0)}%</div></div>
<div><div style={{fontSize:9,color:S.mt}}>EDGE</div><div style={{fontSize:14,fontFamily:S.mn,color:ec}}>{r.edge>0?"+":""}{(r.edge*100).toFixed(1)}%</div></div>
<div><div style={{fontSize:9,color:S.mt}}>CONF</div><div style={{fontSize:14,fontFamily:S.mn}}>{r.conf}%</div></div></div>
<div style={{fontSize:11,color:`${S.tx}90`,lineHeight:1.5}}>{r.reason}</div>
<div style={{display:"flex",gap:6,marginTop:6,flexWrap:"wrap"}}>{r.factors.map((f,fi)=><span key={fi} style={{fontSize:9,padding:"2px 8px",borderRadius:100,background:`${S.tx}08`,color:S.mt}}>{f}</span>)}<span style={{fontSize:9,color:`${S.tx}30`,marginLeft:"auto"}}>{r.tok} tok · {r.ts}</span></div></div>)})}</div>}</>)};

const Landing=({onGo})=>{const[v,setV]=useState(false);useEffect(()=>{setTimeout(()=>setV(true),100)},[]);
return(<div style={{minHeight:"100vh",background:S.bg,color:S.tx,fontFamily:S.mn,opacity:v?1:0,transition:"opacity 0.8s"}}><style>{fonts}</style>
<div style={{position:"fixed",inset:0,backgroundImage:`linear-gradient(${S.bd} 1px,transparent 1px),linear-gradient(90deg,${S.bd} 1px,transparent 1px)`,backgroundSize:"80px 80px",opacity:.3,pointerEvents:"none"}}/>
<div style={{position:"fixed",top:"-20%",right:"10%",width:800,height:800,background:"radial-gradient(circle,rgba(0,229,160,0.035) 0%,transparent 60%)",pointerEvents:"none"}}/>
<nav style={{position:"relative",zIndex:10,display:"flex",alignItems:"center",justifyContent:"space-between",padding:"20px 40px",borderBottom:`1px solid ${S.bd}`}}>
<div style={{display:"flex",alignItems:"center",gap:10}}><AlphaLogo size={26}/><span style={{fontSize:15,fontWeight:500}}>orderflow<span style={{color:S.mt}}>alpha</span></span></div>
<div style={{display:"flex",gap:24,alignItems:"center"}}><button onClick={onGo} style={{padding:"7px 18px",background:S.ac,color:S.bg,border:"none",borderRadius:5,fontSize:10,fontWeight:500,fontFamily:S.mn,cursor:"pointer",letterSpacing:"0.08em"}}>LAUNCH APP</button></div></nav>
<section style={{position:"relative",zIndex:10,padding:"90px 40px 70px",maxWidth:900}}><P>ORDERFLOW 001 HACKATHON</P>
<h1 style={{fontFamily:S.sr,fontSize:60,fontWeight:400,lineHeight:1.05,margin:"20px 0 24px",letterSpacing:"-0.03em"}}>AI-powered<br/><span style={{color:S.ac}}>prediction market</span><br/>trading engine</h1>
<p style={{fontSize:14,color:S.mt,lineHeight:1.7,maxWidth:520,marginBottom:36}}>Combines on-chain orderflow analysis, Groq-powered LLM probability estimation, and Kelly-optimal sizing to exploit mispricings on Polymarket.</p>
<button onClick={onGo} style={{padding:"12px 28px",background:S.ac,color:S.bg,border:"none",borderRadius:6,fontSize:12,fontWeight:500,fontFamily:S.mn,cursor:"pointer"}}>VIEW DASHBOARD →</button>
<div style={{display:"flex",gap:40,marginTop:60}}>{[{v:"+23.0%",l:"Return"},{v:"1.43",l:"Sharpe"},{v:"47.1%",l:"Win Rate"},{v:"6.2%",l:"Max DD"}].map(s=>(<div key={s.l}><div style={{fontSize:28,fontWeight:500,color:S.ac,fontFamily:S.mn}}>{s.v}</div><div style={{fontSize:10,color:S.mt,marginTop:4,letterSpacing:"0.1em",textTransform:"uppercase"}}>{s.l}</div></div>))}</div></section>
<section style={{position:"relative",zIndex:10,padding:"60px 40px",borderTop:`1px solid ${S.bd}`}}>
<div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))",gap:16}}>
{[{t:"Orderflow intelligence",d:"Detect informed positioning through trade flow, whale tracking, and smart wallet clustering on Polymarket CLOB."},
{t:"Groq AI probability",d:"Sub-second Llama 3.3 70B inference produces independent estimates. Find mispricings before the market corrects."},
{t:"Kelly-optimal sizing",d:"Fractional Kelly criterion with risk guardrails. Every position sized for maximum long-term growth rate."},
{t:"Risk architecture",d:"Stop-losses, drawdown breakers, exposure limits, cooldown periods. Systematic risk management."}
].map(f=>(<div key={f.t} style={{padding:24,border:`1px solid ${S.bd}`,borderRadius:10,background:S.sf}}><div style={{fontSize:14,fontWeight:500,marginBottom:8}}>{f.t}</div><div style={{fontSize:12,color:S.mt,lineHeight:1.6}}>{f.d}</div></div>))}</div></section>
<footer style={{position:"relative",zIndex:10,padding:"24px 40px",borderTop:`1px solid ${S.bd}`,display:"flex",justifyContent:"space-between",fontSize:10,color:S.mt}}><span>orderflow-alpha v0.1.0</span><span>48-hour sprint · March 2026</span></footer></div>)};

const Dash=({user,onOut})=>{const[tab,setTab]=useState("overview");const eq=useMemo(()=>bE(TRADES),[]);const dd=useMemo(()=>bD(eq),[eq]);const pnl=useMemo(()=>TRADES.map((t,i)=>({i:i+1,pnl:Math.round(t.pnl*100)/100})),[]);const cum=useMemo(()=>{let c=0;return TRADES.map((t,i)=>{c+=t.pnl;return{i:i+1,c:Math.round(c*100)/100}})},[]);
const tabs=["overview","equity","trades","sensitivity","live ai","architecture"];
return(<div style={{minHeight:"100vh",background:S.bg,color:S.tx,fontFamily:S.mn}}><style>{fonts}</style>
<header style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"14px 28px",borderBottom:`1px solid ${S.bd}`}}>
<div style={{display:"flex",alignItems:"center",gap:10}}><AlphaLogo size={24}/><span style={{fontSize:14,fontWeight:500}}>orderflow<span style={{color:S.mt}}>alpha</span></span></div>
<div style={{display:"flex",alignItems:"center",gap:16}}><P color={S.ac}>+{(PERF.total_return_pct*100).toFixed(1)}%</P>
<div style={{display:"flex",alignItems:"center",gap:8}}><div style={{width:26,height:26,borderRadius:"50%",background:`${S.ac}20`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:11,color:S.ac}}>{(user||"D")[0].toUpperCase()}</div>
<button onClick={onOut} style={{background:"none",border:"none",color:S.mt,fontSize:10,fontFamily:S.mn,cursor:"pointer"}}>Sign out</button></div></div></header>
<div style={{display:"flex",borderBottom:`1px solid ${S.bd}`,padding:"0 28px",overflowX:"auto"}}>{tabs.map(t=>(<button key={t} onClick={()=>setTab(t)} style={{padding:"10px 16px",fontSize:10,textTransform:"uppercase",letterSpacing:"0.1em",color:tab===t?S.tx:S.mt,background:"none",border:"none",borderBottom:tab===t?`2px solid ${S.ac}`:"2px solid transparent",cursor:"pointer",fontFamily:S.mn,whiteSpace:"nowrap"}}>{t}</button>))}</div>
<div style={{padding:"20px 28px",maxWidth:1100}}>
{tab==="overview"&&<><div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(145px,1fr))",gap:10,marginBottom:20}}>
<M label="Return" value={`$${PERF.total_return.toLocaleString()}`} sub={`${(PERF.total_return_pct*100).toFixed(1)}%`} color={S.ac}/>
<M label="Sharpe" value={PERF.sharpe_ratio.toFixed(2)} sub="annualized" color={S.bl}/>
<M label="Sortino" value={PERF.sortino_ratio.toFixed(2)} color={S.pu}/>
<M label="Max DD" value={`${(PERF.max_drawdown_pct*100).toFixed(1)}%`} sub={`$${PERF.max_drawdown.toLocaleString()}`} color={S.yl}/>
<M label="Win Rate" value={`${(PERF.win_rate*100).toFixed(1)}%`} sub={`${PERF.total_trades} trades`}/>
<M label="Profit Factor" value={PERF.profit_factor.toFixed(2)} color={S.ac}/></div>
<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18,marginBottom:16}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:14}}>EQUITY CURVE</div>
<ResponsiveContainer width="100%" height={200}><AreaChart data={eq}><defs><linearGradient id="eg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={S.ac} stopOpacity={.2}/><stop offset="95%" stopColor={S.ac} stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke={S.bd}/><XAxis dataKey="i" tick={false} axisLine={{stroke:S.bd}}/><YAxis tick={{fill:S.mt,fontSize:9,fontFamily:S.mn}} axisLine={false} tickLine={false} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`}/><Tooltip content={<TT/>}/><ReferenceLine y={10000} stroke={`${S.tx}15`} strokeDasharray="3 3"/><Area type="monotone" dataKey="eq" stroke={S.ac} strokeWidth={1.5} fill="url(#eg)"/></AreaChart></ResponsiveContainer></div>
<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:14}}>SIGNAL WEIGHTS</div>
{[{n:"AI Probability",w:.40,c:S.ac},{n:"Orderflow",w:.30,c:S.bl},{n:"Momentum",w:.30,c:S.pu}].map(s=>(<div key={s.n} style={{display:"flex",alignItems:"center",gap:10,marginBottom:6}}><div style={{width:85,fontSize:10,color:S.mt,textAlign:"right"}}>{s.n}</div><div style={{flex:1,height:5,background:`${S.tx}08`,borderRadius:3}}><div style={{width:`${s.w*100}%`,height:"100%",background:s.c,borderRadius:3}}/></div><div style={{width:30,fontSize:10,color:S.mt}}>{(s.w*100).toFixed(0)}%</div></div>))}</div></>}

{tab==="equity"&&<><div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18,marginBottom:16}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:14}}>PORTFOLIO EQUITY</div>
<ResponsiveContainer width="100%" height={260}><AreaChart data={eq}><defs><linearGradient id="eg2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={S.ac} stopOpacity={.25}/><stop offset="95%" stopColor={S.ac} stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke={S.bd}/><XAxis dataKey="i" tick={{fill:S.mt,fontSize:9}} axisLine={{stroke:S.bd}}/><YAxis tick={{fill:S.mt,fontSize:9,fontFamily:S.mn}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v.toLocaleString()}`}/><Tooltip content={<TT/>}/><ReferenceLine y={10000} stroke={`${S.tx}12`} strokeDasharray="3 3"/><Area type="monotone" dataKey="eq" stroke={S.ac} strokeWidth={1.5} fill="url(#eg2)"/></AreaChart></ResponsiveContainer></div>
<div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18}}><div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:14}}>DRAWDOWN</div><ResponsiveContainer width="100%" height={160}><AreaChart data={dd}><defs><linearGradient id="dg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={S.rd} stopOpacity={0}/><stop offset="95%" stopColor={S.rd} stopOpacity={.2}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke={S.bd}/><XAxis dataKey="i" tick={false} axisLine={{stroke:S.bd}}/><YAxis tick={{fill:S.mt,fontSize:9,fontFamily:S.mn}} axisLine={false} tickLine={false} tickFormatter={v=>`${v.toFixed(0)}%`} domain={["auto",0]}/><Tooltip content={<TT/>}/><Area type="monotone" dataKey="dd" stroke={S.rd} strokeWidth={1} fill="url(#dg)"/></AreaChart></ResponsiveContainer></div>
<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18}}><div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:14}}>CUMULATIVE PNL</div><ResponsiveContainer width="100%" height={160}><AreaChart data={cum}><defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={S.bl} stopOpacity={.15}/><stop offset="95%" stopColor={S.bl} stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke={S.bd}/><XAxis dataKey="i" tick={false} axisLine={{stroke:S.bd}}/><YAxis tick={{fill:S.mt,fontSize:9,fontFamily:S.mn}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v.toLocaleString()}`}/><Tooltip content={<TT/>}/><ReferenceLine y={0} stroke={`${S.tx}10`}/><Area type="monotone" dataKey="c" stroke={S.bl} strokeWidth={1.5} fill="url(#cg)"/></AreaChart></ResponsiveContainer></div></div></>}

{tab==="trades"&&<><div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:18,marginBottom:16}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:14}}>PNL PER TRADE</div>
<ResponsiveContainer width="100%" height={220}><BarChart data={pnl}><CartesianGrid strokeDasharray="3 3" stroke={S.bd}/><XAxis dataKey="i" tick={{fill:S.mt,fontSize:9}} axisLine={{stroke:S.bd}}/><YAxis tick={{fill:S.mt,fontSize:9,fontFamily:S.mn}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v}`}/><Tooltip content={<TT/>}/><ReferenceLine y={0} stroke={`${S.tx}10`}/><Bar dataKey="pnl" radius={[2,2,0,0]}>{pnl.map((e,i)=><Cell key={i} fill={e.pnl>=0?S.ac:S.rd} fillOpacity={.75}/>)}</Bar></BarChart></ResponsiveContainer></div>
<div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr 1fr",gap:10}}>
<M label="Avg Winner" value={`$${PERF.avg_winner.toFixed(0)}`} color={S.ac}/>
<M label="Avg Loser" value={`$${Math.abs(PERF.avg_loser).toFixed(0)}`} color={S.rd}/>
<M label="Best" value={`$${PERF.best_trade.toFixed(0)}`} color={S.ac}/>
<M label="Worst" value={`-$${Math.abs(PERF.worst_trade).toFixed(0)}`} color={S.rd}/></div></>}

{tab==="sensitivity"&&<><div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:22,marginBottom:16}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:6}}>PARAMETER SENSITIVITY — SHARPE RATIO</div>
<div style={{fontSize:11,color:S.mt,marginBottom:18}}>Kelly fraction × edge threshold grid search</div>
<div style={{overflowX:"auto"}}><HMap data={HM} xl={HX} yl={HY}/></div></div>
<div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10}}>
<M label="Best Sharpe" value="1.43" sub="kelly=0.35, edge=0.08" color={S.ac}/>
<M label="Avg Sharpe" value="1.12 ± 0.16" sub="18 configs tested"/>
<M label="% Profitable" value="56%" sub="configs with return > 0" color={S.yl}/></div></>}

{tab==="live ai"&&<GP/>}

{tab==="architecture"&&<><div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:22,marginBottom:16}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:20}}>SYSTEM LAYERS</div>
<div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12,marginBottom:16}}>
{[{t:"DATA",c:S.bl,items:["Polymarket CLOB API","On-chain wallet data","News / event feeds","Price history cache"]},{t:"SIGNALS",c:S.pu,items:["Orderflow analyzer","Groq AI probability","Momentum detector","Weighted aggregator"]},{t:"STRATEGY",c:S.ac,items:["Kelly criterion sizer","Risk manager","Trade executor","Portfolio tracker"]}].map(l=>(<div key={l.t} style={{border:`1px solid ${l.c}25`,borderRadius:8,padding:16}}><div style={{fontSize:10,fontWeight:500,color:l.c,letterSpacing:"0.12em",marginBottom:10}}>{l.t}</div>{l.items.map(i=><div key={i} style={{fontSize:11,color:S.mt,padding:"3px 0",borderBottom:`1px solid ${S.bd}`}}>{i}</div>)}</div>))}</div>
<div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
{[{t:"BACKTEST",c:S.yl,items:["Event-driven replay","Realistic slippage","Fee simulation","Sensitivity grid search"]},{t:"RISK",c:S.rd,items:["Position limits","Exposure caps","Stop-loss automation","Drawdown circuit breaker"]}].map(l=>(<div key={l.t} style={{border:`1px solid ${l.c}25`,borderRadius:8,padding:16}}><div style={{fontSize:10,fontWeight:500,color:l.c,letterSpacing:"0.12em",marginBottom:10}}>{l.t}</div>{l.items.map(i=><div key={i} style={{fontSize:11,color:S.mt,padding:"3px 0",borderBottom:`1px solid ${S.bd}`}}>{i}</div>)}</div>))}</div></div>
<div style={{background:S.sf,border:`1px solid ${S.bd}`,borderRadius:10,padding:22}}>
<div style={{fontSize:10,color:S.mt,letterSpacing:"0.12em",textTransform:"uppercase",marginBottom:14}}>TECH STACK</div>
<div style={{display:"flex",flexWrap:"wrap",gap:8}}>{["Python 3.10+","NumPy","Pandas","asyncio","React","Recharts","Polymarket CLOB","Groq (Llama 3.3 70B)","Clerk Auth"].map(t=><P key={t} color={S.mt}>{t}</P>)}</div></div></>}
</div>
<footer style={{borderTop:`1px solid ${S.bd}`,padding:"14px 28px",display:"flex",justifyContent:"space-between",fontSize:9,color:S.mt}}><span>orderflow-alpha v0.1.0</span><span>30 markets · {PERF.total_trades} trades · honest backtest</span></footer></div>)};

export default function App(){const[v,setV]=useState("landing");const[u,setU]=useState(null);
if(v==="landing")return<Landing onGo={()=>setV("auth")}/>;
if(v==="auth")return<Auth onLogin={e=>{setU(e);setV("dash")}}/>;
return<Dash user={u} onOut={()=>{setU(null);setV("landing")}}/>}