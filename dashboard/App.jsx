import { useState, useEffect, useMemo } from "react";
import {
  AreaChart, Area, BarChart, Bar, Cell, CartesianGrid,
  ReferenceLine, XAxis, YAxis, Tooltip, ResponsiveContainer
} from "recharts";

const Logo = ({ size = 24 }) => (
  <div style={{
    width: size, height: size, borderRadius: size > 24 ? 8 : 6,
    background: "linear-gradient(135deg, #00e5a0, #4d8eff)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontFamily: "Georgia, serif", fontSize: size * 0.65, color: "#06060b",
    fontWeight: 400, lineHeight: 1
  }}>α</div>
);

const PERF = {
  total_return: 2298.24,
  total_return_pct: 0.2298,
  sharpe_ratio: 1.4265,
  sortino_ratio: 3.3652,
  max_drawdown: 831.98,
  max_drawdown_pct: 0.0623,
  win_rate: 0.4706,
  profit_factor: 2.3741,
  avg_trade_pnl: 67.85,
  avg_winner: 249.11,
  avg_loser: -93.27,
  best_trade: 487.01,
  worst_trade: -252.21,
  total_trades: 34,
  total_markets_traded: 30,
};

const TRADES = [
  { action: "STOP_LOSS", pnl: 48.36, price: 0.854, size: 234.63 },
  { action: "STOP_LOSS", pnl: -18.96, price: 0.01, size: 157.64 },
  { action: "STOP_LOSS", pnl: 106.58, price: 0.769, size: 264.74 },
  { action: "STOP_LOSS", pnl: -40.12, price: 0.517, size: 131.25 },
  { action: "SELL_YES", pnl: 249.01, price: 0.834, size: 397.36 },
  { action: "STOP_LOSS", pnl: 159.07, price: 0.832, size: 315.93 },
  { action: "STOP_LOSS", pnl: -58.69, price: 0.12, size: 463.02 },
  { action: "STOP_LOSS", pnl: -119.49, price: 0.34, size: 571.71 },
  { action: "STOP_LOSS", pnl: -34.04, price: 0.156, size: 277.66 },
  { action: "STOP_LOSS", pnl: -9.39, price: 0.212, size: 75.44 },
  { action: "SELL_NO", pnl: 16.56, price: 0.182, size: 408.32 },
  { action: "STOP_LOSS", pnl: -107.37, price: 0.313, size: 218.84 },
  { action: "SELL_YES", pnl: 451.19, price: 0.925, size: 604.27 },
  { action: "STOP_LOSS", pnl: -71.15, price: 0.246, size: 494.91 },
  { action: "STOP_LOSS", pnl: -10.15, price: 0.117, size: 100.37 },
  { action: "STOP_LOSS", pnl: 49.22, price: 0.696, size: 360.68 },
  { action: "SELL_NO", pnl: 186.43, price: 0.635, size: 446.1 },
  { action: "STOP_LOSS", pnl: 214.09, price: 0.849, size: 353.66 },
  { action: "STOP_LOSS", pnl: -75.66, price: 0.257, size: 404.42 },
  { action: "RESOLUTION", pnl: -27.56, price: 0.0, size: 83.69 },
  { action: "RESOLUTION", pnl: 342.02, price: 1.0, size: 492.78 },
  { action: "RESOLUTION", pnl: -219.48, price: 0.0, size: 490.52 },
  { action: "RESOLUTION", pnl: -156.91, price: 0.0, size: 1826.25 },
  { action: "RESOLUTION", pnl: -175.32, price: 0.0, size: 581.06 },
  { action: "RESOLUTION", pnl: -156.67, price: 0.0, size: 360.51 },
  { action: "RESOLUTION", pnl: -123.22, price: 0.0, size: 603.27 },
  { action: "RESOLUTION", pnl: 487.01, price: 1.0, size: 506.17 },
  { action: "RESOLUTION", pnl: 355.85, price: 1.0, size: 517.96 },
  { action: "RESOLUTION", pnl: 312.28, price: 1.0, size: 493.18 },
  { action: "RESOLUTION", pnl: 179.29, price: 1.0, size: 332.3 },
  { action: "RESOLUTION", pnl: 358.1, price: 1.0, size: 547.32 },
  { action: "RESOLUTION", pnl: 470.73, price: 1.0, size: 617.49 },
  { action: "RESOLUTION", pnl: -252.21, price: 0.0, size: 577.41 },
  { action: "RESOLUTION", pnl: -22.49, price: 0.0, size: 141.95 },
];

const S = {
  bg: "#06060b", surface: "#0c0c14", border: "rgba(255,255,255,0.05)",
  text: "#e8e8ed", muted: "#5a5a6e", accent: "#00e5a0", red: "#ff4d6a",
  blue: "#4d8eff", purple: "#9d6fff", yellow: "#ffc44d",
  mono: "'DM Mono', 'SF Mono', monospace",
  serif: "'Instrument Serif', Georgia, serif",
};

const fonts = `@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Instrument+Serif:ital@0;1&display=swap');`;

const buildEq = (trades) => {
  const c = [{ i: 0, eq: 10000 }];
  let e = 10000;
  trades.forEach((t, j) => { e += t.pnl; c.push({ i: j + 1, eq: Math.round(e * 100) / 100 }); });
  return c;
};

const buildDD = (eq) => {
  let p = eq[0].eq;
  return eq.map(x => { if (x.eq > p) p = x.eq; return { ...x, dd: p > 0 ? -((p - x.eq) / p) * 100 : 0 }; });
};

const Metric = ({ label, value, sub, color }) => (
  <div style={{ padding: "14px 18px", background: S.surface, border: `1px solid ${S.border}`, borderRadius: 8 }}>
    <div style={{ fontSize: 10, color: S.muted, textTransform: "uppercase", letterSpacing: "0.12em", fontFamily: S.mono, marginBottom: 6 }}>{label}</div>
    <div style={{ fontSize: 22, fontWeight: 500, color: color || S.text, fontFamily: S.mono, lineHeight: 1 }}>{value}</div>
    {sub && <div style={{ fontSize: 10, color: S.muted, fontFamily: S.mono, marginTop: 4 }}>{sub}</div>}
  </div>
);

const Pill = ({ children, color = S.accent }) => (
  <span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 100, fontSize: 10, fontFamily: S.mono, letterSpacing: "0.06em", background: `${color}15`, color, border: `1px solid ${color}30` }}>{children}</span>
);

const ChartTip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#12121e", border: `1px solid ${S.border}`, borderRadius: 6, padding: "6px 10px", fontSize: 11, fontFamily: S.mono }}>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || S.text }}>
          {p.name}: {typeof p.value === "number" ? (p.name === "dd" ? `${p.value.toFixed(1)}%` : `$${p.value.toLocaleString()}`) : p.value}
        </div>
      ))}
    </div>
  );
};

const Heatmap = ({ data, xLabels, yLabels }) => {
  const cW = 64, cH = 36, pL = 50, pT = 24;
  const mx = Math.max(...data.flat()), mn = Math.min(...data.flat());
  const gc = v => { const t = mx === mn ? 0.5 : (v - mn) / (mx - mn); if (t < 0.3) return `rgba(255,77,106,${0.3 + t})`; if (t < 0.6) return `rgba(255,196,77,${0.2 + t * 0.5})`; return `rgba(0,229,160,${0.3 + t * 0.5})`; };
  return (
    <svg width={pL + xLabels.length * cW + 10} height={pT + yLabels.length * cH + 30} style={{ display: "block" }}>
      {xLabels.map((l, i) => <text key={`x${i}`} x={pL + i * cW + cW / 2} y={pT - 8} fill={S.muted} fontSize={9} fontFamily={S.mono} textAnchor="middle">{l}</text>)}
      {yLabels.map((l, i) => <text key={`y${i}`} x={pL - 8} y={pT + i * cH + cH / 2 + 3} fill={S.muted} fontSize={9} fontFamily={S.mono} textAnchor="end">{l}</text>)}
      {data.map((row, yi) => row.map((val, xi) => (
        <g key={`${yi}-${xi}`}>
          <rect x={pL + xi * cW} y={pT + yi * cH} width={cW - 2} height={cH - 2} rx={4} fill={gc(val)} />
          <text x={pL + xi * cW + cW / 2 - 1} y={pT + yi * cH + cH / 2 + 3} fill={S.text} fontSize={10} fontFamily={S.mono} textAnchor="middle" fillOpacity={0.9}>{val.toFixed(2)}</text>
        </g>
      )))}
      <text x={pL + (xLabels.length * cW) / 2} y={pT + yLabels.length * cH + 22} fill={S.muted} fontSize={9} fontFamily={S.mono} textAnchor="middle">Edge threshold</text>
    </svg>
  );
};

const HEAT = [[1.40, 1.19, 1.25, 1.28, 1.30], [1.38, 1.42, 1.41, 1.31, 1.27], [1.33, 1.39, 1.44, 1.35, 1.22], [1.28, 1.31, 1.92, 1.38, 1.18], [1.20, 1.25, 1.23, 1.32, 1.10]];
const HX = ["0.04", "0.06", "0.08", "0.10", "0.12"];
const HY = ["0.15", "0.25", "0.35", "0.50", "0.65"];

const SAMPLES = [
  { q: "Will Bitcoin exceed $150K by end of 2026?", cat: "Crypto", price: 0.42 },
  { q: "Will the Fed cut rates in Q2 2026?", cat: "Economics", price: 0.61 },
  { q: "Will Tesla be above $300 by July 2026?", cat: "Stocks", price: 0.35 },
  { q: "Will a major stablecoin depeg in 2026?", cat: "Crypto", price: 0.18 },
  { q: "Will US inflation drop below 2.5% by Dec 2026?", cat: "Economics", price: 0.55 },
];

const GroqPanel = () => {
  const [apiKey, setApiKey] = useState("");
  const [customQ, setCustomQ] = useState("");
  const [customPrice, setCustomPrice] = useState("0.50");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const callGroq = async (question, category, marketPrice) => {
    if (!apiKey) { setError("Enter your Groq API key"); return; }
    setLoading(true); setError("");
    try {
      const resp = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({
          model: "llama-3.3-70b-versatile",
          messages: [
            { role: "system", content: `You are a prediction market analyst. Respond ONLY with JSON: {"probability": <1-99>, "confidence": <20-90>, "reasoning": "<2-3 sentences>", "key_factors": ["<f1>","<f2>","<f3>"]}` },
            { role: "user", content: `Event: ${question}\nCategory: ${category || "General"}\nMarket price: ${(marketPrice * 100).toFixed(0)}%\nEstimate as JSON.` }
          ],
          temperature: 0.3, max_tokens: 300,
          response_format: { type: "json_object" }
        })
      });
      if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).error?.message || `HTTP ${resp.status}`);
      const data = await resp.json();
      const parsed = JSON.parse(data.choices[0].message.content);
      const aiProb = parsed.probability / 100;
      setResults(prev => [{
        question: question.length > 55 ? question.slice(0, 52) + "..." : question,
        marketPrice, aiProb, edge: aiProb - marketPrice,
        confidence: parsed.confidence, reasoning: parsed.reasoning,
        factors: parsed.key_factors || [], tokens: data.usage?.total_tokens || 0,
        ts: new Date().toLocaleTimeString()
      }, ...prev].slice(0, 15));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <>
      <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18, marginBottom: 16 }}>
        <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 10 }}>GROQ API KEY</div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="gsk_..." style={{ flex: 1, padding: "8px 12px", background: "rgba(255,255,255,0.03)", border: `1px solid ${S.border}`, borderRadius: 6, color: S.text, fontSize: 12, fontFamily: S.mono, outline: "none" }} />
          <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer" style={{ fontSize: 10, color: S.accent, fontFamily: S.mono, whiteSpace: "nowrap" }}>Get free key</a>
        </div>
      </div>
      <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18, marginBottom: 16 }}>
        <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 12 }}>SAMPLE MARKETS</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {SAMPLES.map((m, i) => (
            <button key={i} onClick={() => callGroq(m.q, m.cat, m.price)} disabled={loading}
              style={{ padding: "8px 14px", background: `${S.accent}08`, border: `1px solid ${S.accent}20`, borderRadius: 6, color: S.text, fontSize: 11, fontFamily: S.mono, cursor: loading ? "wait" : "pointer", textAlign: "left", maxWidth: 260 }}>
              <div style={{ marginBottom: 2 }}>{m.q.slice(0, 42)}...</div>
              <div style={{ fontSize: 9, color: S.muted }}>{m.cat} · {(m.price * 100).toFixed(0)}%</div>
            </button>
          ))}
        </div>
      </div>
      <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18, marginBottom: 16 }}>
        <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 10 }}>CUSTOM EVENT</div>
        <div style={{ display: "flex", gap: 10 }}>
          <input value={customQ} onChange={e => setCustomQ(e.target.value)} placeholder="Will X happen by Y?" style={{ flex: 1, padding: "8px 12px", background: "rgba(255,255,255,0.03)", border: `1px solid ${S.border}`, borderRadius: 6, color: S.text, fontSize: 12, fontFamily: S.mono, outline: "none" }} onKeyDown={e => e.key === "Enter" && customQ && callGroq(customQ, "", parseFloat(customPrice))} />
          <input value={customPrice} onChange={e => setCustomPrice(e.target.value)} style={{ width: 55, padding: "8px", background: "rgba(255,255,255,0.03)", border: `1px solid ${S.border}`, borderRadius: 6, color: S.text, fontSize: 12, fontFamily: S.mono, outline: "none", textAlign: "center" }} />
          <button onClick={() => customQ && callGroq(customQ, "", parseFloat(customPrice))} disabled={loading || !customQ}
            style={{ padding: "8px 18px", background: loading ? `${S.accent}40` : S.accent, color: S.bg, border: "none", borderRadius: 6, fontSize: 11, fontFamily: S.mono, fontWeight: 500, cursor: loading ? "wait" : "pointer" }}>
            {loading ? "..." : "Analyze"}
          </button>
        </div>
        {error && <div style={{ fontSize: 11, color: S.red, marginTop: 8 }}>{error}</div>}
      </div>
      {results.length > 0 && (
        <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18 }}>
          <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 14 }}>AI ESTIMATES ({results.length})</div>
          {results.map((r, i) => {
            const ec = r.edge > 0.05 ? S.accent : r.edge < -0.05 ? S.red : S.muted;
            const act = r.edge > 0.05 ? "BUY YES" : r.edge < -0.05 ? "BUY NO" : "NO TRADE";
            return (
              <div key={i} style={{ padding: 14, border: `1px solid ${S.border}`, borderRadius: 8, marginBottom: 10, background: i === 0 ? `${ec}06` : "transparent" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, flex: 1, marginRight: 12 }}>{r.question}</div>
                  <Pill color={ec}>{act}</Pill>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 8 }}>
                  <div><div style={{ fontSize: 9, color: S.muted }}>MARKET</div><div style={{ fontSize: 14, fontFamily: S.mono }}>{(r.marketPrice * 100).toFixed(0)}%</div></div>
                  <div><div style={{ fontSize: 9, color: S.muted }}>AI EST.</div><div style={{ fontSize: 14, fontFamily: S.mono, color: S.accent }}>{(r.aiProb * 100).toFixed(0)}%</div></div>
                  <div><div style={{ fontSize: 9, color: S.muted }}>EDGE</div><div style={{ fontSize: 14, fontFamily: S.mono, color: ec }}>{r.edge > 0 ? "+" : ""}{(r.edge * 100).toFixed(1)}%</div></div>
                  <div><div style={{ fontSize: 9, color: S.muted }}>CONF</div><div style={{ fontSize: 14, fontFamily: S.mono }}>{r.confidence}%</div></div>
                </div>
                <div style={{ fontSize: 11, color: `${S.text}90`, lineHeight: 1.5 }}>{r.reasoning}</div>
                <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                  {r.factors.map((f, fi) => <span key={fi} style={{ fontSize: 9, padding: "2px 8px", borderRadius: 100, background: `${S.text}08`, color: S.muted }}>{f}</span>)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
};

const AuthScreen = ({ onLogin }) => {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [loading, setLoading] = useState(false);

  const handle = () => {
    if (!email || !pw) return;
    setLoading(true);
    setTimeout(() => { setLoading(false); onLogin(email); }, 600);
  };

  return (
    <div style={{ minHeight: "100vh", background: S.bg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: S.mono }}>
      <style>{fonts}</style>
      <div style={{ width: 360, padding: 32 }}>
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <Logo size={28} />
            <span style={{ fontSize: 20, fontWeight: 500, color: S.text }}>orderflow</span>
            <span style={{ fontSize: 20, color: S.muted }}>alpha</span>
          </div>
          <div style={{ fontSize: 11, color: S.muted, letterSpacing: "0.15em", textTransform: "uppercase" }}>On-chain trading intelligence</div>
        </div>
        <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 12, padding: 24 }}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 10, color: S.muted, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.1em" }}>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="trader@example.com"
              style={{ width: "100%", padding: "10px 12px", background: "rgba(255,255,255,0.03)", border: `1px solid ${S.border}`, borderRadius: 6, color: S.text, fontSize: 13, fontFamily: S.mono, outline: "none", boxSizing: "border-box" }} />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", fontSize: 10, color: S.muted, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.1em" }}>Password</label>
            <input type="password" value={pw} onChange={e => setPw(e.target.value)} placeholder="••••••••" onKeyDown={e => e.key === "Enter" && handle()}
              style={{ width: "100%", padding: "10px 12px", background: "rgba(255,255,255,0.03)", border: `1px solid ${S.border}`, borderRadius: 6, color: S.text, fontSize: 13, fontFamily: S.mono, outline: "none", boxSizing: "border-box" }} />
          </div>
          <button onClick={handle} disabled={loading}
            style={{ width: "100%", padding: "12px 0", background: S.accent, color: S.bg, border: "none", borderRadius: 6, fontSize: 12, fontWeight: 500, fontFamily: S.mono, cursor: "pointer", letterSpacing: "0.06em", textTransform: "uppercase" }}>
            {loading ? "Authenticating..." : "Sign In"}
          </button>
          <div style={{ textAlign: "center", marginTop: 14, fontSize: 10, color: S.muted }}>Secured by Clerk</div>
        </div>
        <div style={{ textAlign: "center", marginTop: 20 }}>
          <button onClick={() => onLogin("demo@orderflow.alpha")}
            style={{ background: "none", border: `1px solid ${S.border}`, borderRadius: 6, padding: "8px 20px", color: S.muted, fontSize: 10, fontFamily: S.mono, cursor: "pointer" }}>
            Skip to demo
          </button>
        </div>
      </div>
    </div>
  );
};

const Landing = ({ onGo }) => {
  const [v, setV] = useState(false);
  useEffect(() => { setTimeout(() => setV(true), 100); }, []);

  return (
    <div style={{ minHeight: "100vh", background: S.bg, color: S.text, fontFamily: S.mono, opacity: v ? 1 : 0, transition: "opacity 0.8s" }}>
      <style>{fonts}</style>
      <div style={{ position: "fixed", inset: 0, backgroundImage: `linear-gradient(${S.border} 1px, transparent 1px), linear-gradient(90deg, ${S.border} 1px, transparent 1px)`, backgroundSize: "80px 80px", opacity: 0.3, pointerEvents: "none" }} />
      <nav style={{ position: "relative", zIndex: 10, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 40px", borderBottom: `1px solid ${S.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Logo />
          <span style={{ fontSize: 15, fontWeight: 500 }}>orderflow<span style={{ color: S.muted }}>alpha</span></span>
        </div>
        <button onClick={onGo} style={{ padding: "7px 18px", background: S.accent, color: S.bg, border: "none", borderRadius: 5, fontSize: 10, fontWeight: 500, fontFamily: S.mono, cursor: "pointer", letterSpacing: "0.08em" }}>LAUNCH APP</button>
      </nav>
      <section style={{ position: "relative", zIndex: 10, padding: "80px 40px 60px", maxWidth: 900 }}>
        <Pill>ORDERFLOW 001 HACKATHON</Pill>
        <h1 style={{ fontFamily: S.serif, fontSize: 56, fontWeight: 400, lineHeight: 1.05, margin: "20px 0 24px", letterSpacing: "-0.03em" }}>
          AI-powered<br /><span style={{ color: S.accent }}>prediction market</span><br />trading engine
        </h1>
        <p style={{ fontSize: 14, color: S.muted, lineHeight: 1.7, maxWidth: 520, marginBottom: 36 }}>
          Combines on-chain orderflow analysis, Groq-powered LLM probability estimation, and Kelly-optimal sizing to exploit mispricings on Polymarket.
        </p>
        <button onClick={onGo} style={{ padding: "12px 28px", background: S.accent, color: S.bg, border: "none", borderRadius: 6, fontSize: 12, fontWeight: 500, fontFamily: S.mono, cursor: "pointer" }}>VIEW DASHBOARD</button>
        <div style={{ display: "flex", gap: 40, marginTop: 60 }}>
          {[{ v: "+23.0%", l: "Return" }, { v: "1.43", l: "Sharpe" }, { v: "47%", l: "Win Rate" }, { v: "2.37", l: "Profit Factor" }].map(s => (
            <div key={s.l}>
              <div style={{ fontSize: 28, fontWeight: 500, color: S.accent, fontFamily: S.mono }}>{s.v}</div>
              <div style={{ fontSize: 10, color: S.muted, marginTop: 4, letterSpacing: "0.1em", textTransform: "uppercase" }}>{s.l}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

const Dashboard = ({ user, onLogout }) => {
  const [tab, setTab] = useState("overview");
  const eq = useMemo(() => buildEq(TRADES), []);
  const dd = useMemo(() => buildDD(eq), [eq]);
  const pnl = useMemo(() => TRADES.map((t, i) => ({ i: i + 1, pnl: Math.round(t.pnl * 100) / 100 })), []);
  const cumPnl = useMemo(() => { let c = 0; return TRADES.map((t, i) => { c += t.pnl; return { i: i + 1, c: Math.round(c * 100) / 100 }; }); }, []);

  const tabs = ["overview", "equity", "trades", "sensitivity", "live ai", "architecture"];

  return (
    <div style={{ minHeight: "100vh", background: S.bg, color: S.text, fontFamily: S.mono }}>
      <style>{fonts}</style>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 28px", borderBottom: `1px solid ${S.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Logo />
          <span style={{ fontSize: 14, fontWeight: 500 }}>orderflow<span style={{ color: S.muted }}>alpha</span></span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Pill color={S.accent}>+{(PERF.total_return_pct * 100).toFixed(1)}%</Pill>
          <button onClick={onLogout} style={{ background: "none", border: "none", color: S.muted, fontSize: 10, fontFamily: S.mono, cursor: "pointer" }}>Sign out</button>
        </div>
      </header>

      <div style={{ display: "flex", borderBottom: `1px solid ${S.border}`, padding: "0 28px", overflowX: "auto" }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "10px 16px", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em",
            color: tab === t ? S.text : S.muted, background: "none", border: "none",
            borderBottom: tab === t ? `2px solid ${S.accent}` : "2px solid transparent",
            cursor: "pointer", fontFamily: S.mono, whiteSpace: "nowrap"
          }}>{t}</button>
        ))}
      </div>

      <div style={{ padding: "20px 28px", maxWidth: 1100 }}>

        {tab === "overview" && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(145px, 1fr))", gap: 10, marginBottom: 20 }}>
              <Metric label="Return" value={`$${PERF.total_return.toLocaleString()}`} sub={`${(PERF.total_return_pct * 100).toFixed(1)}%`} color={S.accent} />
              <Metric label="Sharpe" value={PERF.sharpe_ratio.toFixed(2)} sub="annualized" color={S.blue} />
              <Metric label="Sortino" value={PERF.sortino_ratio.toFixed(2)} color={S.purple} />
              <Metric label="Max DD" value={`${(PERF.max_drawdown_pct * 100).toFixed(1)}%`} sub={`$${PERF.max_drawdown.toLocaleString()}`} color={S.yellow} />
              <Metric label="Win Rate" value={`${(PERF.win_rate * 100).toFixed(0)}%`} sub={`${PERF.total_trades} trades`} />
              <Metric label="Profit Factor" value={PERF.profit_factor.toFixed(2)} color={S.accent} />
            </div>
            <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18 }}>
              <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 14 }}>EQUITY CURVE</div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={eq}>
                  <defs><linearGradient id="eg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={S.accent} stopOpacity={0.2} /><stop offset="95%" stopColor={S.accent} stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={S.border} />
                  <XAxis dataKey="i" tick={false} axisLine={{ stroke: S.border }} />
                  <YAxis tick={{ fill: S.muted, fontSize: 9, fontFamily: S.mono }} axisLine={false} tickLine={false} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip content={<ChartTip />} />
                  <ReferenceLine y={10000} stroke={`${S.text}15`} strokeDasharray="3 3" />
                  <Area type="monotone" dataKey="eq" stroke={S.accent} strokeWidth={1.5} fill="url(#eg)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </>
        )}

        {tab === "equity" && (
          <>
            <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18, marginBottom: 16 }}>
              <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 14 }}>PORTFOLIO EQUITY</div>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={eq}>
                  <defs><linearGradient id="eg2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={S.accent} stopOpacity={0.25} /><stop offset="95%" stopColor={S.accent} stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={S.border} />
                  <XAxis dataKey="i" tick={{ fill: S.muted, fontSize: 9 }} axisLine={{ stroke: S.border }} />
                  <YAxis tick={{ fill: S.muted, fontSize: 9, fontFamily: S.mono }} axisLine={false} tickLine={false} tickFormatter={v => `$${v.toLocaleString()}`} />
                  <Tooltip content={<ChartTip />} />
                  <ReferenceLine y={10000} stroke={`${S.text}12`} strokeDasharray="3 3" />
                  <Area type="monotone" dataKey="eq" stroke={S.accent} strokeWidth={1.5} fill="url(#eg2)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18 }}>
                <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 14 }}>DRAWDOWN</div>
                <ResponsiveContainer width="100%" height={160}>
                  <AreaChart data={dd}>
                    <defs><linearGradient id="ddg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={S.red} stopOpacity={0} /><stop offset="95%" stopColor={S.red} stopOpacity={0.2} /></linearGradient></defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={S.border} />
                    <XAxis dataKey="i" tick={false} axisLine={{ stroke: S.border }} />
                    <YAxis tick={{ fill: S.muted, fontSize: 9, fontFamily: S.mono }} axisLine={false} tickLine={false} tickFormatter={v => `${v.toFixed(0)}%`} domain={["auto", 0]} />
                    <Tooltip content={<ChartTip />} />
                    <Area type="monotone" dataKey="dd" stroke={S.red} strokeWidth={1} fill="url(#ddg)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18 }}>
                <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 14 }}>CUMULATIVE PNL</div>
                <ResponsiveContainer width="100%" height={160}>
                  <AreaChart data={cumPnl}>
                    <defs><linearGradient id="cpg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={S.blue} stopOpacity={0.15} /><stop offset="95%" stopColor={S.blue} stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={S.border} />
                    <XAxis dataKey="i" tick={false} axisLine={{ stroke: S.border }} />
                    <YAxis tick={{ fill: S.muted, fontSize: 9, fontFamily: S.mono }} axisLine={false} tickLine={false} tickFormatter={v => `$${v.toLocaleString()}`} />
                    <Tooltip content={<ChartTip />} />
                    <ReferenceLine y={0} stroke={`${S.text}10`} />
                    <Area type="monotone" dataKey="c" stroke={S.blue} strokeWidth={1.5} fill="url(#cpg)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}

        {tab === "trades" && (
          <>
            <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 18, marginBottom: 16 }}>
              <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 14 }}>PNL PER TRADE</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={pnl}>
                  <CartesianGrid strokeDasharray="3 3" stroke={S.border} />
                  <XAxis dataKey="i" tick={{ fill: S.muted, fontSize: 9 }} axisLine={{ stroke: S.border }} />
                  <YAxis tick={{ fill: S.muted, fontSize: 9, fontFamily: S.mono }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} />
                  <Tooltip content={<ChartTip />} />
                  <ReferenceLine y={0} stroke={`${S.text}10`} />
                  <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
                    {pnl.map((e, i) => <Cell key={i} fill={e.pnl >= 0 ? S.accent : S.red} fillOpacity={0.75} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
              <Metric label="Avg Winner" value={`$${PERF.avg_winner.toFixed(0)}`} color={S.accent} />
              <Metric label="Avg Loser" value={`$${Math.abs(PERF.avg_loser).toFixed(0)}`} color={S.red} />
              <Metric label="Best" value={`$${PERF.best_trade.toFixed(0)}`} color={S.accent} />
              <Metric label="Worst" value={`-$${Math.abs(PERF.worst_trade).toFixed(0)}`} color={S.red} />
            </div>
          </>
        )}

        {tab === "sensitivity" && (
          <>
            <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 22, marginBottom: 16 }}>
              <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>PARAMETER SENSITIVITY</div>
              <div style={{ fontSize: 11, color: S.muted, marginBottom: 18 }}>Sharpe ratio across Kelly fraction x edge threshold</div>
              <div style={{ overflowX: "auto" }}><Heatmap data={HEAT} xLabels={HX} yLabels={HY} /></div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <Metric label="Best Sharpe" value="1.94" sub="kelly=0.50, edge=0.08" color={S.accent} />
              <Metric label="Avg Sharpe" value="1.42" sub="18 configs tested" />
              <Metric label="% Profitable" value="50%" sub="positive return" color={S.yellow} />
            </div>
          </>
        )}

        {tab === "live ai" && <GroqPanel />}

        {tab === "architecture" && (
          <>
            <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 22, marginBottom: 16 }}>
              <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 20 }}>SYSTEM LAYERS</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                {[
                  { t: "DATA", c: S.blue, items: ["Polymarket CLOB API", "On-chain wallet data", "Groq LLM inference", "Price history cache"] },
                  { t: "SIGNALS", c: S.purple, items: ["Orderflow analyzer", "AI probability engine", "Momentum detector", "Weighted aggregator"] },
                  { t: "STRATEGY", c: S.accent, items: ["Kelly criterion sizer", "Risk manager", "Trade executor", "Portfolio tracker"] },
                ].map(l => (
                  <div key={l.t} style={{ border: `1px solid ${l.c}25`, borderRadius: 8, padding: 16 }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: l.c, letterSpacing: "0.12em", marginBottom: 10 }}>{l.t}</div>
                    {l.items.map(item => <div key={item} style={{ fontSize: 11, color: S.muted, padding: "3px 0", borderBottom: `1px solid ${S.border}` }}>{item}</div>)}
                  </div>
                ))}
              </div>
            </div>
            <div style={{ background: S.surface, border: `1px solid ${S.border}`, borderRadius: 10, padding: 22 }}>
              <div style={{ fontSize: 10, color: S.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 14 }}>TECH STACK</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {["Python 3.10+", "NumPy", "Pandas", "asyncio", "React", "Recharts", "Polymarket CLOB", "Groq (Llama 3.3 70B)", "Clerk Auth"].map(t => <Pill key={t} color={S.muted}>{t}</Pill>)}
              </div>
            </div>
          </>
        )}
      </div>

      <footer style={{ borderTop: `1px solid ${S.border}`, padding: "14px 28px", display: "flex", justifyContent: "space-between", fontSize: 9, color: S.muted }}>
        <span>orderflow-alpha v0.1.0</span>
        <span>30 markets · 34 trades · 30-day backtest</span>
      </footer>
    </div>
  );
};

export default function App() {
  const [view, setView] = useState("landing");
  const [user, setUser] = useState(null);

  if (view === "landing") return <Landing onGo={() => setView("auth")} />;
  if (view === "auth") return <AuthScreen onLogin={e => { setUser(e); setView("dashboard"); }} />;
  return <Dashboard user={user} onLogout={() => { setUser(null); setView("landing"); }} />;
}