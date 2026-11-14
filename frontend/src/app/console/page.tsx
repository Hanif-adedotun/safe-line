"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Globe2,
  Lock,
  MessageSquare,
  Mic,
  MicOff,
  Network,
  PhoneCall,
  Search,
  Send,
  ShieldAlert,
  Sparkles,
  ZoomIn,
  ZoomOut,
  MapPin,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type ViewMode = "zoom_out_macro" | "zoom_in_intake" | "zoom_out_forensics";

interface TraceStep {
  node: string;
  status: string;
  latency_ms: number;
  detail: string;
}

interface Turn {
  role: "reporter" | "safeline";
  text_redacted: string;
  timestamp: string;
}

interface GpsFix {
  latitude: number;
  longitude: number;
  accuracy_m: number | null;
  captured_at: string;
}

interface LocationEvidence {
  network: string | null;
  network_source: string | null;
  country: string | null;
  spoken_address: string | null;
  spoken_at: string | null;
  gps: GpsFix | null;
  link_sent_via: string[];
  link_sent_at: string | null;
  best: "gps" | "spoken" | "network" | "none";
}

const mapsUrl = (q: string) => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;

interface CaseRecord {
  id: string;
  created_at: string;
  updated_at: string;
  channel: string;
  region: "NG" | "US";
  status: string;
  risk_level: number;
  harm_category: string;
  general_location: string | null;
  latitude: number | null;
  longitude: number | null;
  who_at_risk: string | null;
  immediate_danger: boolean;
  redacted_summary: string;
  entities: string[];
  linked_case_ids: string[];
  alert_dispatched: boolean;
  alert_channels: string[];
  turns: Turn[];
  trace: TraceStep[];
  location?: LocationEvidence | null;
  live_call?: boolean;
}

interface Citation {
  case_id: string;
  location: string | null;
  risk_level: number;
  excerpt: string;
}

interface EvalReport {
  total_cases: number;
  escalation_recall_pct: number;
  false_positive_rate_pct: number;
  pii_leaks: number;
  avg_guard_latency_ms: number;
}

const PRESETS = [
  {
    label: "NG Pidgin (Silent Photon)",
    channel: "photon_sms" as const,
    region: "NG" as const,
    text: "My name is Tunde, call 08031234567. One teacher for Surulere Primary Annex dey lock my small sister for store room beat am after school.",
  },
  {
    label: "US Silent Text (Unsafe to Speak)",
    channel: "photon_sms" as const,
    region: "US" as const,
    text: "Cant talk out loud my stepdad is outside the bedroom door he just threw me into the wall in Trenton",
  },
  {
    label: "NG Voice Call (PII Scrub Check)",
    channel: "voice_call" as const,
    region: "NG" as const,
    text: "Please help my neighbor's child in Yaba, her uncle burns her hand with hot iron and told her not to tell anyone. My email is witness@example.com.",
  },
];

const RISK_STYLE: Record<number, string> = {
  3: "bg-red-500/20 text-red-300 border-red-500/40",
  2: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  1: "bg-sky-500/20 text-sky-300 border-sky-500/40",
  0: "bg-zinc-500/20 text-zinc-300 border-zinc-500/40",
};

export default function SafeLineApp() {
  const [mode, setMode] = useState<ViewMode>("zoom_out_macro");
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [message, setMessage] = useState("");
  const [channel, setChannel] = useState<"photon_sms" | "voice_call" | "web_mic">("photon_sms");
  const [region, setRegion] = useState<"NG" | "US">("NG");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [forensicQ, setForensicQ] = useState("Which cases mention Surulere Primary Annex?");
  const [forensicRes, setForensicRes] = useState<{ answer: string; citations: Citation[]; matched_entities: string[] } | null>(null);
  const [evalRes, setEvalRes] = useState<EvalReport | null>(null);
  const [lastLatency, setLastLatency] = useState<number | null>(null);
  const [lastPiiCount, setLastPiiCount] = useState<number>(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  async function refreshCases() {
    try {
      const r = await fetch(`${API_BASE}/api/cases`);
      if (r.ok) {
        const data: CaseRecord[] = await r.json();
        setCases(data);
        // Keep the open case in sync so live location updates appear without a reload.
        setSelectedCase((prev) => (prev ? data.find((c) => c.id === prev.id) ?? prev : data[0] ?? null));
      }
    } catch {
      // Backend offline fallback handled silently
    }
  }

  useEffect(() => {
    refreshCases();
    // Live calls create and update cases server-side; poll so they appear on screen.
    const t = setInterval(refreshCases, 3000);
    return () => clearInterval(t);
  }, []);

  async function submitIntake(customText?: string, customChannel?: "photon_sms" | "voice_call" | "web_mic", customRegion?: "NG" | "US") {
    const text = (customText ?? message).trim();
    if (!text) return;
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          channel: customChannel ?? channel,
          region: customRegion ?? region,
        }),
      });
      if (r.ok) {
        const data = await r.json();
        setSelectedCase(data.case);
        setLastLatency(data.total_latency_ms);
        setLastPiiCount(data.pii_redacted_count);
        if (!customText) setMessage("");
        setMode("zoom_in_intake");
        await refreshCases();
      }
    } finally {
      setLoading(false);
    }
  }

  async function toggleMic() {
    if (recording && mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => chunksRef.current.push(e.data);
      rec.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        const fd = new FormData();
        fd.append("file", blob, "mic.webm");
        fd.append("region", region);
        setLoading(true);
        try {
          const r = await fetch(`${API_BASE}/api/intake/audio`, { method: "POST", body: fd });
          if (r.ok) {
            const data = await r.json();
            setSelectedCase(data.case);
            setLastLatency(data.total_latency_ms);
            setLastPiiCount(data.pii_redacted_count);
            await refreshCases();
          }
        } finally {
          setLoading(false);
        }
      };
      mediaRecorderRef.current = rec;
      rec.start();
      setRecording(true);
    } catch {
      alert("Microphone permission unavailable — use silent text or a preset.");
    }
  }

  async function runForensics() {
    const r = await fetch(`${API_BASE}/api/forensics/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: forensicQ }),
    });
    if (r.ok) setForensicRes(await r.json());
  }

  async function runEval() {
    const r = await fetch(`${API_BASE}/api/eval/run`, { method: "POST" });
    if (r.ok) setEvalRes(await r.json());
  }

  return (
    <div className="min-h-screen bg-[#0B0D12] text-[#F7F1E4]">
      {/* Header */}
      <header className="border-b border-white/10 bg-[#0E1118]/90 backdrop-blur sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-5 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-[#CBA868]/15 border border-[#CBA868]/40 flex items-center justify-center">
              <ShieldAlert className="h-5 w-5 text-[#CBA868]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold tracking-tight text-lg">SafeLine</span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  Toll-Free Voice + Photon 2.0 Silent Text
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                Trauma-informed child safety triage · Zero graphic probing · &lt;60s caseworker dispatch
              </p>
            </div>
          </div>

          {/* Zoom-Out -> Zoom-In -> Zoom-Out Controls */}
          <nav className="flex items-center gap-1.5 bg-black/40 p-1 rounded-xl border border-white/10">
            <a
              href="/"
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-300 hover:bg-white/5 flex items-center gap-1.5 transition"
            >
              ← Ayo Website
            </a>
            <button
              onClick={() => setMode("zoom_out_macro")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                mode === "zoom_out_macro" ? "bg-[#CBA868] text-black" : "text-zinc-300 hover:bg-white/5"
              }`}
            >
              <ZoomOut className="h-3.5 w-3.5" /> 1. Zoom Out: Blind Spot
            </button>
            <button
              onClick={() => setMode("zoom_in_intake")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                mode === "zoom_in_intake" ? "bg-[#CBA868] text-black" : "text-zinc-300 hover:bg-white/5"
              }`}
            >
              <ZoomIn className="h-3.5 w-3.5" /> 2. Zoom In: Live Triage
            </button>
            <button
              onClick={() => {
                setMode("zoom_out_forensics");
                runForensics();
                runEval();
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                mode === "zoom_out_forensics" ? "bg-[#CBA868] text-black" : "text-zinc-300 hover:bg-white/5"
              }`}
            >
              <Network className="h-3.5 w-3.5" /> 3. Zoom Out: Forensics & Eval
            </button>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-5 py-6">
        {/* VIEW 1: ZOOM OUT - MACRO BLIND SPOT */}
        {mode === "zoom_out_macro" && (
          <section key="macro" className="animate-zoom space-y-6">
            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#131722] to-[#0B0D12] p-6">
              <div className="flex items-center gap-2 text-[#CBA868] text-xs font-semibold uppercase tracking-wider mb-2">
                <Globe2 className="h-4 w-4" /> Global & Nigerian Child-Protection Blind Spot
              </div>
              <h1 className="text-2xl md:text-3xl font-semibold leading-tight max-w-3xl">
                Half a million children&apos;s helpline calls go unanswered every year—and when 88% know their abuser, speaking aloud isn&apos;t safe.
              </h1>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                {[
                  { stat: "1B+", label: "Children face violence/yr (WHO/UNICEF)" },
                  { stat: "500,000+", label: "Unanswered child helpline contacts/yr" },
                  { stat: "6 in 10", label: "Nigerian children abused; <5% get help" },
                  { stat: "71%", label: "US 988 crisis centers understaffed (JAMA)" },
                ].map((item) => (
                  <div key={item.stat} className="rounded-xl bg-white/[0.03] border border-white/10 p-4">
                    <div className="text-2xl font-bold text-[#CBA868]">{item.stat}</div>
                    <div className="text-xs text-zinc-400 mt-1">{item.label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
                Live Geographic Hotspot Map — Click Any Pin to Zoom In
              </h2>
              <button
                onClick={() => setMode("zoom_in_intake")}
                className="px-4 py-2 rounded-lg bg-[#CBA868] text-black text-xs font-semibold hover:opacity-90 flex items-center gap-1.5"
              >
                <ZoomIn className="h-4 w-4" /> Simulate New Call / Silent Text
              </button>
            </div>

            {/* Dual-Region Live Location Plot (Nigeria + US) */}
            <div className="grid md:grid-cols-2 gap-4">
              {(["NG", "US"] as const).map((reg) => {
                const regCases = cases.filter((c) => c.region === reg);
                return (
                  <div key={reg} className="rounded-2xl border border-white/10 bg-[#111520] p-4 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-[#CBA868]">
                        {reg === "NG" ? "Nigeria Live Node (Lagos / Rivers / Abuja)" : "US Live Node (NJ / Northeast)"}
                      </span>
                      <span className="text-zinc-400">{regCases.length} active report(s)</span>
                    </div>
                    <div className="relative h-44 rounded-xl bg-black/50 border border-white/10 overflow-hidden">
                      {/* Subtle grid */}
                      <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#CBA868_1px,transparent_1px)] [background-size:16px_16px]" />
                      {regCases.map((c, idx) => {
                        const lat = c.latitude ?? (reg === "NG" ? 6.52 : 40.35);
                        const lng = c.longitude ?? (reg === "NG" ? 3.37 : -74.66);
                        const xPct =
                          reg === "NG"
                            ? Math.min(88, Math.max(12, ((lng - 3.2) / 4.5) * 70 + 15 + (idx % 3) * 6))
                            : Math.min(88, Math.max(12, ((lng + 75.3) / 1.5) * 70 + 15 + (idx % 3) * 6));
                        const yPct =
                          reg === "NG"
                            ? Math.min(82, Math.max(18, 80 - ((lat - 4.7) / 4.6) * 60 + (idx % 2) * 8))
                            : Math.min(82, Math.max(18, 80 - ((lat - 39.8) / 1.1) * 60 + (idx % 2) * 8));
                        return (
                          <button
                            key={c.id}
                            onClick={() => {
                              setSelectedCase(c);
                              setMode("zoom_in_intake");
                            }}
                            style={{ left: `${xPct}%`, top: `${yPct}%` }}
                            className="absolute -translate-x-1/2 -translate-y-1/2 group flex flex-col items-center"
                          >
                            <span
                              className={`h-3.5 w-3.5 rounded-full border-2 border-white shadow ${
                                c.risk_level >= 3 ? "bg-red-500 animate-pulse" : "bg-amber-400"
                              }`}
                            />
                            <span className="mt-1 px-2 py-0.5 rounded bg-black/85 border border-white/15 text-[10px] text-zinc-200 whitespace-nowrap group-hover:border-[#CBA868]">
                              {c.general_location?.split(",")[0] || c.id} · R{c.risk_level}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              {cases.map((c) => (
                <button
                  key={c.id}
                  onClick={() => {
                    setSelectedCase(c);
                    setMode("zoom_in_intake");
                  }}
                  className="text-left rounded-xl border border-white/10 bg-[#111520] hover:border-[#CBA868]/60 p-4 transition space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-zinc-400 flex items-center gap-1.5">
                      {c.id}
                      {c.live_call && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/40 animate-pulse">
                          LIVE
                        </span>
                      )}
                    </span>
                    <span className={`text-[11px] px-2 py-0.5 rounded-full border ${RISK_STYLE[c.risk_level]}`}>
                      Risk {c.risk_level} · {c.harm_category.replace("_", " ")}
                    </span>
                  </div>
                  <div className="font-medium text-sm">{c.general_location || "Location pending"}</div>
                  <p className="text-xs text-zinc-400 line-clamp-2">{c.redacted_summary}</p>
                  <div className="flex items-center justify-between pt-1 text-[11px] text-zinc-500">
                    <span>Channel: {c.channel}</span>
                    <span>{c.linked_case_ids.length} linked case(s)</span>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* VIEW 2: ZOOM IN - LIVE INTAKE & LANGGRAPH TRIAGE */}
        {mode === "zoom_in_intake" && (
          <section key="intake" className="animate-zoom grid lg:grid-cols-12 gap-6">
            {/* Left: Caller / Silent Text Simulator */}
            <div className="lg:col-span-5 space-y-4">
              <div className="rounded-2xl border border-white/10 bg-[#111520] p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-sm flex items-center gap-2">
                    <PhoneCall className="h-4 w-4 text-[#CBA868]" /> Live Intake Channel
                  </h2>
                  <div className="flex gap-1.5">
                    {(["NG", "US"] as const).map((r) => (
                      <button
                        key={r}
                        onClick={() => setRegion(r)}
                        className={`px-2.5 py-1 rounded text-xs font-medium ${
                          region === r ? "bg-[#CBA868] text-black" : "bg-white/5 text-zinc-400"
                        }`}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setChannel("photon_sms")}
                    className={`p-2.5 rounded-xl border text-xs font-medium flex items-center justify-center gap-1.5 ${
                      channel === "photon_sms"
                        ? "border-[#CBA868] bg-[#CBA868]/10 text-[#CBA868]"
                        : "border-white/10 text-zinc-400"
                    }`}
                  >
                    <MessageSquare className="h-3.5 w-3.5" /> Photon 2.0 Silent Text
                  </button>
                  <button
                    onClick={() => setChannel("voice_call")}
                    className={`p-2.5 rounded-xl border text-xs font-medium flex items-center justify-center gap-1.5 ${
                      channel === "voice_call"
                        ? "border-[#CBA868] bg-[#CBA868]/10 text-[#CBA868]"
                        : "border-white/10 text-zinc-400"
                    }`}
                  >
                    <PhoneCall className="h-3.5 w-3.5" /> Toll-Free Voice Line
                  </button>
                </div>

                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={4}
                  placeholder="Type a synthetic disclosure (English or Nigerian Pidgin) or use a preset / mic below..."
                  className="w-full rounded-xl bg-black/50 border border-white/10 p-3 text-sm text-[#F7F1E4] placeholder:text-zinc-500 focus:outline-none focus:border-[#CBA868]"
                />

                <div className="flex items-center gap-2">
                  <button
                    disabled={loading}
                    onClick={() => submitIntake()}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-[#CBA868] text-black font-semibold text-xs flex items-center justify-center gap-1.5 hover:opacity-90 disabled:opacity-50"
                  >
                    <Send className="h-3.5 w-3.5" /> {loading ? "Triaging..." : "Send to SafeLine Agent"}
                  </button>
                  <button
                    onClick={toggleMic}
                    className={`py-2.5 px-3.5 rounded-xl border text-xs font-medium flex items-center gap-1.5 ${
                      recording
                        ? "bg-red-500/20 border-red-500 text-red-300"
                        : "border-white/15 text-zinc-300 hover:bg-white/5"
                    }`}
                  >
                    {recording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    {recording ? "Stop" : "Mic"}
                  </button>
                </div>

                <div className="pt-2 border-t border-white/10 space-y-2">
                  <div className="text-[11px] text-zinc-400 font-medium">1-Click Synthetic Demo Scenarios:</div>
                  <div className="flex flex-wrap gap-1.5">
                    {PRESETS.map((p) => (
                      <button
                        key={p.label}
                        onClick={() => {
                          setChannel(p.channel);
                          setRegion(p.region);
                          submitIntake(p.text, p.channel, p.region);
                        }}
                        className="text-[11px] px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300"
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Live Case Packet + LangGraph Agent Trace */}
            <div className="lg:col-span-7 space-y-4">
              {selectedCase ? (
                <div className="rounded-2xl border border-white/10 bg-[#111520] p-5 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-[#CBA868]">{selectedCase.id}</span>
                        {selectedCase.live_call && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 border border-red-500/40 animate-pulse">
                            ● LIVE CALL
                          </span>
                        )}
                        <span className={`text-xs px-2.5 py-0.5 rounded-full border ${RISK_STYLE[selectedCase.risk_level]}`}>
                          Risk Level {selectedCase.risk_level} · {selectedCase.harm_category}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-400 mt-1">
                        Location: <span className="text-zinc-200">{selectedCase.general_location || "Pending"}</span>
                        {selectedCase.latitude && selectedCase.longitude && (
                          <span className="font-mono text-[11px] text-zinc-500 ml-1.5">
                            ({selectedCase.latitude.toFixed(4)}, {selectedCase.longitude.toFixed(4)})
                          </span>
                        )}
                        {" · "}At risk: <span className="text-zinc-200">{selectedCase.who_at_risk || "Child"}</span>
                      </div>
                    </div>
                    <div className="text-right text-xs">
                      {selectedCase.alert_dispatched && (
                        <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Alert Sent ({selectedCase.alert_channels.join(", ")})
                        </div>
                      )}
                      {lastLatency !== null && (
                        <div className="text-[11px] text-zinc-400 mt-1">
                          {lastLatency} ms · {lastPiiCount} PII token(s) scrubbed
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Caller location: every signal, strongest first */}
                  {selectedCase.location && (
                    <div className="rounded-xl border border-white/10 bg-black/30 p-3 space-y-2">
                      <div className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                        <MapPin className="h-3.5 w-3.5 text-[#CBA868]" /> Caller Location
                        <span className="ml-auto text-[10px] uppercase tracking-wider text-zinc-500">
                          best signal: {selectedCase.location.best}
                        </span>
                      </div>
                      <div className="grid sm:grid-cols-3 gap-2 text-[11px]">
                        <div className={`rounded-lg p-2 border ${selectedCase.location.gps ? "border-emerald-500/50 bg-emerald-500/10" : "border-white/10"}`}>
                          <div className="text-zinc-400 mb-0.5">GPS (one-tap link)</div>
                          {selectedCase.location.gps ? (
                            <a
                              className="text-emerald-300 hover:underline font-mono"
                              href={mapsUrl(`${selectedCase.location.gps.latitude},${selectedCase.location.gps.longitude}`)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {selectedCase.location.gps.latitude.toFixed(5)}, {selectedCase.location.gps.longitude.toFixed(5)}
                              {selectedCase.location.gps.accuracy_m ? ` ±${Math.round(selectedCase.location.gps.accuracy_m)}m` : ""}
                            </a>
                          ) : selectedCase.location.link_sent_via.length > 0 ? (
                            <span className="text-amber-300">Link sent via {selectedCase.location.link_sent_via.join(", ")}, waiting for tap</span>
                          ) : selectedCase.live_call ? (
                            <button
                              onClick={async () => {
                                const r = await fetch(`${API_BASE}/api/cases/${selectedCase.id}/location-link`, { method: "POST" });
                                const d = await r.json().catch(() => ({}));
                                if (!r.ok || !d.sent) alert(`Link not sent: ${d.reason || d.detail || r.status}`);
                                refreshCases();
                              }}
                              className="px-2 py-1 rounded bg-[#CBA868] text-black font-semibold"
                            >
                              Send location link
                            </button>
                          ) : (
                            <span className="text-zinc-500">Not shared</span>
                          )}
                        </div>
                        <div className={`rounded-lg p-2 border ${selectedCase.location.spoken_address ? "border-sky-500/50 bg-sky-500/10" : "border-white/10"}`}>
                          <div className="text-zinc-400 mb-0.5">Caller said</div>
                          {selectedCase.location.spoken_address ? (
                            <a className="text-sky-300 hover:underline" href={mapsUrl(selectedCase.location.spoken_address)} target="_blank" rel="noreferrer">
                              {selectedCase.location.spoken_address}
                            </a>
                          ) : (
                            <span className="text-zinc-500">Not yet</span>
                          )}
                        </div>
                        <div className="rounded-lg p-2 border border-white/10">
                          <div className="text-zinc-400 mb-0.5">Phone network (registered area)</div>
                          <span className="text-zinc-300">{selectedCase.location.network || "Unknown"}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* PII-Redacted Conversation */}
                  <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                    {selectedCase.turns.map((t, i) => (
                      <div
                        key={i}
                        className={`p-3 rounded-xl text-xs leading-relaxed ${
                          t.role === "reporter"
                            ? "bg-white/[0.04] border border-white/10"
                            : "bg-[#CBA868]/10 border border-[#CBA868]/30 text-[#F7F1E4]"
                        }`}
                      >
                        <div className="text-[10px] uppercase tracking-wider text-zinc-400 mb-1 flex items-center gap-1">
                          {t.role === "reporter" ? (
                            <>
                              <Lock className="h-3 w-3 text-emerald-400" /> Reporter (PII-Redacted)
                            </>
                          ) : (
                            <>
                              <Sparkles className="h-3 w-3 text-[#CBA868]" /> SafeLine Trauma-Informed Response
                            </>
                          )}
                        </div>
                        {t.text_redacted}
                      </div>
                    ))}
                  </div>

                  {/* LangGraph DeepAgent Trace */}
                  <div className="border-t border-white/10 pt-3">
                    <div className="text-xs font-semibold text-zinc-300 mb-2 flex items-center gap-1.5">
                      <Activity className="h-3.5 w-3.5 text-[#CBA868]" /> LangGraph Agent Execution Trace
                    </div>
                    <div className="grid sm:grid-cols-2 gap-2">
                      {selectedCase.trace.map((step, i) => (
                        <div key={i} className="rounded-lg bg-black/40 border border-white/10 p-2.5 text-xs">
                          <div className="flex items-center justify-between font-mono text-[11px]">
                            <span className="text-[#CBA868]">{step.node}</span>
                            <span className="text-zinc-500">{step.latency_ms} ms</span>
                          </div>
                          <div className="text-zinc-300 text-[11px] mt-1">{step.detail}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {selectedCase.linked_case_ids.length > 0 && (
                    <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-3 flex items-center justify-between">
                      <div className="text-xs text-amber-200 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        Cross-case pattern: linked to {selectedCase.linked_case_ids.join(", ")}
                      </div>
                      <button
                        onClick={() => {
                          setMode("zoom_out_forensics");
                          runForensics();
                        }}
                        className="text-xs font-semibold text-[#CBA868] hover:underline"
                      >
                        Inspect Timeline →
                      </button>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </section>
        )}

        {/* VIEW 3: ZOOM BACK OUT - ARLEQUIN FORENSICS & EVAL HARNESS */}
        {mode === "zoom_out_forensics" && (
          <section key="forensics" className="animate-zoom grid lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7 rounded-2xl border border-white/10 bg-[#111520] p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-sm flex items-center gap-2">
                  <Network className="h-4 w-4 text-[#CBA868]" /> Evidence-Cited Investigator Q&A (Arlequin Forensics)
                </h2>
              </div>
              <div className="flex gap-2">
                <input
                  value={forensicQ}
                  onChange={(e) => setForensicQ(e.target.value)}
                  className="flex-1 rounded-xl bg-black/50 border border-white/10 px-3 py-2 text-sm focus:outline-none focus:border-[#CBA868]"
                  placeholder="Ask across anonymized reports (e.g. Surulere Primary Annex)..."
                />
                <button
                  onClick={runForensics}
                  className="px-4 py-2 rounded-xl bg-[#CBA868] text-black text-xs font-semibold flex items-center gap-1.5"
                >
                  <Search className="h-3.5 w-3.5" /> Query
                </button>
              </div>
              {forensicRes && (
                <div className="space-y-3">
                  <div className="rounded-xl bg-black/40 border border-white/10 p-3 text-xs text-zinc-200">
                    {forensicRes.answer}
                  </div>
                  <div className="space-y-2">
                    {forensicRes.citations.map((cit) => (
                      <div key={cit.case_id} className="rounded-xl border border-white/10 bg-white/[0.02] p-3 text-xs">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-[#CBA868]">{cit.case_id}</span>
                          <span className="text-zinc-400">
                            {cit.location || "Unspecified"} · Risk {cit.risk_level}
                          </span>
                        </div>
                        <p className="text-zinc-300 italic">&ldquo;{cit.excerpt}&rdquo;</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="lg:col-span-5 rounded-2xl border border-white/10 bg-[#111520] p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-sm flex items-center gap-2">
                  <Activity className="h-4 w-4 text-[#CBA868]" /> Synthetic Safeguarding Eval Harness
                </h2>
                <button
                  onClick={runEval}
                  className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-xs font-medium"
                >
                  Re-run 40 Cases
                </button>
              </div>
              {evalRes && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-black/40 border border-white/10 p-3">
                    <div className="text-2xl font-bold text-emerald-400">{evalRes.escalation_recall_pct}%</div>
                    <div className="text-[11px] text-zinc-400">Escalation Recall ({evalRes.total_cases} cases)</div>
                  </div>
                  <div className="rounded-xl bg-black/40 border border-white/10 p-3">
                    <div className="text-2xl font-bold text-emerald-400">{evalRes.pii_leaks}</div>
                    <div className="text-[11px] text-zinc-400">Raw PII Leaks</div>
                  </div>
                  <div className="rounded-xl bg-black/40 border border-white/10 p-3">
                    <div className="text-2xl font-bold text-[#CBA868]">{evalRes.false_positive_rate_pct}%</div>
                    <div className="text-[11px] text-zinc-400">False-Positive Rate</div>
                  </div>
                  <div className="rounded-xl bg-black/40 border border-white/10 p-3">
                    <div className="text-2xl font-bold text-[#CBA868]">{evalRes.avg_guard_latency_ms} ms</div>
                    <div className="text-[11px] text-zinc-400">Avg Guard Latency</div>
                  </div>
                </div>
              )}
              <p className="text-xs text-zinc-400 leading-relaxed">
                Tested across Nigerian Pidgin, Nigerian English, US silent-text emergencies, and non-crisis control utterances.
              </p>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

