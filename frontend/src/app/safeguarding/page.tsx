"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  BellRing,
  Brain,
  CheckCircle2,
  ClipboardList,
  FlaskConical,
  Gavel,
  MapPin,
  MessageSquare,
  RotateCcw,
  Send,
  ShieldCheck,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8010";

// ---------- types (mirror backend/app/safeguarding) ----------
interface Concern {
  category: string;
  status: "potential" | "stated" | "unclear";
  evidence_quotes: string[];
  interpretation: string;
  evidence_verified: boolean;
}
interface Assessment {
  concerns: Concern[];
  urgency: string;
  immediate_danger: string;
  model_uncertainty: string[];
  missing_information: string[];
  human_review_recommended: boolean;
  follow_up_appropriate: boolean;
  suggested_follow_up: string | null;
  limitations: string[];
  engine: string;
  fallback: boolean;
  fallback_reason: string | null;
  assessed_at: string | null;
  turns_assessed: number;
}
interface Decision {
  policy_version: string;
  rule_id: string;
  rule_text: string;
  action: string;
  priority: string;
  create_review_item: boolean;
  notify: boolean;
  notification_preview: string | null;
  in_call_instruction: string | null;
  explanation: string;
  held_from_previous: boolean;
}
interface Turn {
  role: "reporter" | "safeline";
  text_redacted: string;
  timestamp: string;
}
interface Session {
  id: string;
  created_at: string;
  updated_at: string;
  channel: string;
  region: "NG" | "US";
  turns: Turn[];
  live_call?: boolean;
  assessment?: Assessment | null;
  decision?: Decision | null;
  review_item_id?: string | null;
  location?: { best: string; network: string | null; spoken_address: string | null; gps: { latitude: number; longitude: number; accuracy_m: number | null } | null } | null;
}
interface ReviewItem {
  id: string;
  session_id: string;
  created_at: string;
  priority: string;
  categories: string[];
  urgency: string;
  immediate_danger: string;
  rule_id: string;
  status: "open" | "reviewed";
  notification_preview: string | null;
  disposition: string | null;
  reviewer_note: string | null;
}
interface AuditEvent {
  at: string;
  kind: string;
  detail: Record<string, unknown>;
}

const LABEL: Record<string, string> = {
  physical_abuse: "Physical abuse",
  emotional_abuse: "Emotional abuse",
  sexual_abuse_or_exploitation: "Sexual abuse / exploitation",
  neglect: "Neglect",
  domestic_violence_exposure: "Domestic violence exposure",
  bullying: "Bullying",
  threats_intimidation: "Threats / intimidation",
  coercion_control: "Coercion / control",
  unsafe_living_environment: "Unsafe living environment",
  online_exploitation: "Online exploitation",
  fear_unclear_cause: "Fear, cause unclear",
  self_harm_or_suicide: "Self-harm / suicide",
  other_or_unknown: "Other / unknown",
};

const PRIORITY_STYLE: Record<string, string> = {
  critical: "bg-red-500/20 text-red-200 border-red-500/50",
  high: "bg-amber-500/20 text-amber-200 border-amber-500/50",
  standard: "bg-sky-500/15 text-sky-200 border-sky-500/40",
  routine: "bg-zinc-500/20 text-zinc-200 border-zinc-500/40",
  none: "bg-zinc-800 text-zinc-400 border-zinc-700",
};

const DISPOSITIONS = [
  "escalated_per_protocol",
  "support_referral_offered",
  "no_safeguarding_concern_after_review",
  "needs_more_information",
  "duplicate_or_test",
];

// Synthetic demo scenarios (fictional). Each message is sent in order as the child.
const SCENARIOS: { label: string; region: "NG" | "US"; messages: string[] }[] = [
  { label: "Indirect, builds over turns", region: "US", messages: ["I don't like going home.", "My dad gets angry when I eat.", "Sometimes I don't get dinner."] },
  { label: "Emotional abuse", region: "US", messages: ["My mum tells me every day that I'm worthless and she wishes I was never born."] },
  { label: "Ambiguous", region: "US", messages: ["I don't like my uncle."] },
  { label: "Pidgin", region: "NG", messages: ["My aunty dey flog me with wire every day, e dey pain me well well."] },
  { label: "Immediate danger", region: "NG", messages: ["He's banging on my door right now and shouting he's going to kill me. I locked myself in the bathroom."] },
  { label: "Ordinary (no concern)", region: "US", messages: ["Can you help me with my maths homework? It's fractions."] },
];

function Chip({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <span className={`text-[11px] px-2 py-0.5 rounded-full border ${className}`}>{children}</span>;
}

function Panel({ title, icon, tag, children }: { title: string; icon: React.ReactNode; tag: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-[#111520] p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold">
        {icon}
        {title}
        <span className="ml-auto text-[10px] uppercase tracking-wider text-zinc-500">{tag}</span>
      </div>
      {children}
    </section>
  );
}

export default function SafeguardingConsole() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [draft, setDraft] = useState("");
  const [region, setRegion] = useState<"NG" | "US">("US");
  const [busy, setBusy] = useState(false);
  const [disposition, setDisposition] = useState(DISPOSITIONS[0]);
  const [note, setNote] = useState("");
  const [evalSummary, setEvalSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selected = sessions.find((s) => s.id === selectedId) || null;
  const selectedItem = selected?.review_item_id ? items.find((i) => i.id === selected.review_item_id) : undefined;

  const refresh = useCallback(async () => {
    try {
      const [c, r] = await Promise.all([fetch(`${API}/api/cases`), fetch(`${API}/api/review-items`)]);
      if (c.ok) {
        const all: Session[] = await c.json();
        // Lane sessions only: legacy seeded records have no assessment and no turns from this lane.
        setSessions(all.filter((s) => s.assessment || s.live_call));
      }
      if (r.ok) setItems(await r.json());
      setError(null);
    } catch {
      setError(`Backend not reachable at ${API}`);
    }
  }, []);

  useEffect(() => {
    // Deep link: /safeguarding?session=SL-2026-XXXX opens that session.
    const s = new URLSearchParams(window.location.search).get("session");
    if (s) setSelectedId(s);
    refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    if (!selectedId) return setAudit([]);
    fetch(`${API}/api/audit?session_id=${selectedId}`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setAudit)
      .catch(() => {});
  }, [selectedId, sessions]);

  async function sendAsChild(text: string, caseId: string | null, reg: "NG" | "US") {
    const r = await fetch(`${API}/api/intake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, channel: "web_text", region: reg, case_id: caseId }),
    });
    if (!r.ok) throw new Error(`intake ${r.status}`);
    return (await r.json()).case.id as string;
  }

  async function send() {
    if (!draft.trim()) return;
    setBusy(true);
    try {
      const id = await sendAsChild(draft.trim(), selectedId, region);
      setSelectedId(id);
      setDraft("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function runScenario(s: (typeof SCENARIOS)[number]) {
    setBusy(true);
    try {
      let id: string | null = null;
      for (const m of s.messages) {
        id = await sendAsChild(m, id, s.region);
        setSelectedId(id);
        await refresh();
      }
    } finally {
      setBusy(false);
    }
  }

  async function markReviewed() {
    if (!selectedItem) return;
    await fetch(`${API}/api/review-items/${selectedItem.id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ disposition, note }),
    });
    setNote("");
    refresh();
  }

  async function runEval() {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/eval/run`, { method: "POST" });
      if (r.ok) setEvalSummary((await r.json()).summary);
    } finally {
      setBusy(false);
    }
  }

  async function resetDemo() {
    if (!confirm("Delete all demo sessions, review items and audit events?")) return;
    await fetch(`${API}/api/demo/reset`, { method: "POST" });
    setSelectedId(null);
    setEvalSummary(null);
    refresh();
  }

  const a = selected?.assessment || null;
  const d = selected?.decision || null;

  return (
    <div className="min-h-screen bg-[#0B0D12] text-[#F7F1E4]">
      <header className="border-b border-white/10 bg-[#0E1118] px-4 py-3 flex flex-wrap items-center gap-3">
        <ShieldCheck className="h-5 w-5 text-[#CBA868]" />
        <div className="font-semibold">Ayo · Safeguarding Console</div>
        <Chip className="border-amber-500/40 text-amber-200 bg-amber-500/10">DEMO · synthetic data · nothing is sent</Chip>
        <div className="ml-auto flex gap-2">
          <button onClick={runEval} disabled={busy} className="text-xs px-3 py-1.5 rounded-lg border border-white/15 hover:bg-white/5 flex items-center gap-1.5">
            <FlaskConical className="h-3.5 w-3.5" /> Run synthetic eval
          </button>
          <button onClick={resetDemo} className="text-xs px-3 py-1.5 rounded-lg border border-white/15 hover:bg-white/5 flex items-center gap-1.5">
            <RotateCcw className="h-3.5 w-3.5" /> Reset demo data
          </button>
        </div>
      </header>
      {error && <div className="bg-red-500/15 text-red-200 text-xs px-4 py-2">{error}</div>}
      <p className="px-4 pt-3 text-[11px] text-zinc-400">
        System 1 output is a preliminary AI interpretation, not a verified finding. System 2 applies a demo policy that has not been
        approved by safeguarding professionals. Every consequential decision belongs to a trained human reviewer.
      </p>

      {evalSummary && (
        <div className="mx-4 mt-3 rounded-xl border border-white/10 bg-black/40 p-3 text-xs grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            ["Concern recall", `${evalSummary.concern_detection_recall_pct}%`],
            ["Category recall", `${evalSummary.category_recall_pct}%`],
            ["Urgency agreement", `${evalSummary.urgency_agreement_pct}%`],
            ["Evidence verbatim", `${evalSummary.evidence_verbatim_pct}%`],
            ["Human review rate", `${evalSummary.human_review_rate_pct}%`],
            ["False positives", String((evalSummary.false_positives_on_no_concern as string[]).length)],
          ].map(([k, v]) => (
            <div key={k}>
              <div className="text-lg font-semibold text-[#CBA868]">{v}</div>
              <div className="text-zinc-400">{k}</div>
            </div>
          ))}
          <div className="col-span-full text-zinc-500">
            {evalSummary.total_cases as number} synthetic cases, developer-written labels, not expert-reviewed. Missed:{" "}
            {(evalSummary.missed_concern_cases as string[]).join(", ") || "none"} · Under-escalated:{" "}
            {(evalSummary.under_escalated as string[]).join(", ") || "none"}
          </div>
        </div>
      )}

      <main className="p-4 grid lg:grid-cols-12 gap-4">
        {/* Panel D: review queue + sessions */}
        <div className="lg:col-span-3 space-y-4">
          <Panel title="Review queue" icon={<ClipboardList className="h-4 w-4 text-[#CBA868]" />} tag="Panel D">
            {items.length === 0 && <div className="text-xs text-zinc-500">No review items. A session only becomes one when the policy says so.</div>}
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {items.map((i) => (
                <button
                  key={i.id}
                  onClick={() => setSelectedId(i.session_id)}
                  className={`w-full text-left rounded-lg border p-2 text-xs space-y-1 ${selectedId === i.session_id ? "border-[#CBA868]" : "border-white/10"} ${i.status === "reviewed" ? "opacity-60" : ""}`}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono">{i.id}</span>
                    <Chip className={PRIORITY_STYLE[i.priority]}>{i.priority}</Chip>
                    <span className="ml-auto text-zinc-500">{i.status}</span>
                  </div>
                  <div className="text-zinc-300">{i.categories.map((c) => LABEL[c] || c).join(", ") || "Unclassified"}</div>
                  <div className="text-zinc-500">{new Date(i.created_at).toLocaleTimeString()} · {i.rule_id}</div>
                </button>
              ))}
            </div>
          </Panel>
          <Panel title="Sessions" icon={<MessageSquare className="h-4 w-4 text-[#CBA868]" />} tag="calls & texts">
            <div className="space-y-1.5 max-h-72 overflow-y-auto">
              <button onClick={() => setSelectedId(null)} className="w-full text-left text-xs px-2 py-1.5 rounded border border-dashed border-white/20 text-zinc-400">
                + New synthetic session
              </button>
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  className={`w-full text-left text-xs px-2 py-1.5 rounded border flex items-center gap-1.5 ${selectedId === s.id ? "border-[#CBA868]" : "border-white/10"}`}
                >
                  <span className="font-mono">{s.id}</span>
                  {s.live_call && <Chip className="border-red-500/50 text-red-200 animate-pulse">LIVE</Chip>}
                  <span className="ml-auto text-zinc-500">{s.decision?.priority || "…"}</span>
                </button>
              ))}
            </div>
          </Panel>
        </div>

        {/* Panel A: conversation */}
        <div className="lg:col-span-4 space-y-4">
          <Panel title={selected ? `Conversation · ${selected.id}` : "New synthetic conversation"} icon={<MessageSquare className="h-4 w-4 text-[#CBA868]" />} tag="Panel A">
            <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
              {selected?.turns.map((t, i) => (
                <div key={i} className={`p-2.5 rounded-xl text-xs leading-relaxed ${t.role === "reporter" ? "bg-white/[0.05] border border-white/10" : "bg-[#CBA868]/10 border border-[#CBA868]/30"}`}>
                  <div className="text-[10px] uppercase tracking-wider text-zinc-400 mb-1">{t.role === "reporter" ? "Child (PII-redacted)" : "Ayo"}</div>
                  {t.text_redacted}
                </div>
              ))}
              {!selected && <div className="text-xs text-zinc-500">Type as a fictional child, or pick a scenario. Synthetic only.</div>}
            </div>
            <div className="flex gap-1.5">
              {(["US", "NG"] as const).map((r) => (
                <button key={r} onClick={() => setRegion(r)} className={`px-2 py-1 rounded text-xs ${region === r ? "bg-[#CBA868] text-black" : "bg-white/5 text-zinc-400"}`}>
                  {r}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Synthetic child message…"
                className="flex-1 rounded-lg bg-black/50 border border-white/10 px-3 py-2 text-xs focus:outline-none focus:border-[#CBA868]"
              />
              <button onClick={send} disabled={busy} className="px-3 rounded-lg bg-[#CBA868] text-black text-xs font-semibold disabled:opacity-50 flex items-center gap-1">
                <Send className="h-3.5 w-3.5" /> {busy ? "…" : "Send"}
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {SCENARIOS.map((s) => (
                <button key={s.label} disabled={busy} onClick={() => runScenario(s)} className="text-[11px] px-2 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10">
                  {s.label}
                </button>
              ))}
            </div>
          </Panel>
          {selected?.location && selected.location.best !== "none" && (
            <Panel title="Caller location" icon={<MapPin className="h-4 w-4 text-[#CBA868]" />} tag={`best: ${selected.location.best}`}>
              <div className="text-xs text-zinc-300 space-y-1">
                {selected.location.gps && <div>GPS: {selected.location.gps.latitude.toFixed(5)}, {selected.location.gps.longitude.toFixed(5)}</div>}
                {selected.location.spoken_address && <div>Caller said: {selected.location.spoken_address}</div>}
                {selected.location.network && <div className="text-zinc-500">Network area: {selected.location.network}</div>}
              </div>
            </Panel>
          )}
        </div>

        {/* Panels B + C */}
        <div className="lg:col-span-5 space-y-4">
          <Panel title="Safeguarding Intelligence Engine" icon={<Brain className="h-4 w-4 text-[#CBA868]" />} tag="Panel B · System 1">
            {!a && <div className="text-xs text-zinc-500">No assessment yet.</div>}
            {a && (
              <div className="space-y-3 text-xs">
                <div className="flex flex-wrap gap-1.5 items-center">
                  <Chip className="border-white/20">urgency: {a.urgency}</Chip>
                  <Chip className={a.immediate_danger === "yes" ? "border-red-500/60 text-red-200" : "border-white/20"}>immediate danger: {a.immediate_danger}</Chip>
                  <Chip className="border-white/20 text-zinc-400">engine: {a.engine}</Chip>
                  {a.fallback && <Chip className="border-red-500/60 text-red-200">FALLBACK: {a.fallback_reason}</Chip>}
                </div>
                {a.concerns.length === 0 && !a.fallback && <div className="text-zinc-400">No safeguarding concern identified.</div>}
                {a.concerns.map((c, i) => (
                  <div key={i} className="rounded-lg border border-white/10 p-2.5 space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      <span className="font-semibold">{LABEL[c.category] || c.category}</span>
                      <Chip className="border-white/20 text-zinc-300">{c.status}</Chip>
                      {c.evidence_verified ? (
                        <span className="ml-auto text-emerald-300 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> child&apos;s words</span>
                      ) : (
                        <span className="ml-auto text-amber-300 flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> quote not verified</span>
                      )}
                    </div>
                    {c.evidence_quotes.map((q, j) => (
                      <div key={j} className="border-l-2 border-[#CBA868]/60 pl-2 text-zinc-200">&ldquo;{q}&rdquo;</div>
                    ))}
                    <div className="text-zinc-400">{c.interpretation}</div>
                  </div>
                ))}
                {a.model_uncertainty.length > 0 && (
                  <div><div className="text-zinc-400 mb-0.5">Uncertainty</div><ul className="list-disc pl-4 text-zinc-300">{a.model_uncertainty.map((u, i) => <li key={i}>{u}</li>)}</ul></div>
                )}
                {a.missing_information.length > 0 && (
                  <div><div className="text-zinc-400 mb-0.5">Missing information</div><ul className="list-disc pl-4 text-zinc-300">{a.missing_information.map((u, i) => <li key={i}>{u}</li>)}</ul></div>
                )}
                {a.follow_up_appropriate && a.suggested_follow_up && (
                  <div className="text-zinc-400">
                    Model&apos;s suggested follow-up <span className="text-zinc-500">(reviewer only; the child only hears approved prompts)</span>:{" "}
                    <span className="text-zinc-200">{a.suggested_follow_up}</span>
                  </div>
                )}
                <div className="text-[10px] text-zinc-500">{a.limitations.join(" ")} · {a.turns_assessed} turns assessed</div>
              </div>
            )}
          </Panel>

          <Panel title="Intervention & Escalation Engine" icon={<Gavel className="h-4 w-4 text-[#CBA868]" />} tag="Panel C · System 2">
            {!d && <div className="text-xs text-zinc-500">No decision yet.</div>}
            {d && (
              <div className="space-y-3 text-xs">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Chip className={PRIORITY_STYLE[d.priority]}>priority: {d.priority}</Chip>
                  <Chip className="border-white/20">action: {d.action.replace(/_/g, " ")}</Chip>
                  <Chip className="border-white/20 text-zinc-400">policy {d.policy_version}</Chip>
                </div>
                <div className="rounded-lg bg-black/40 border border-white/10 p-2.5">
                  <div className="font-mono text-[#CBA868]">{d.rule_id}</div>
                  <div className="text-zinc-300 mt-0.5">Why: {d.explanation}</div>
                </div>
                <div className="text-zinc-300">Review item: {d.create_review_item ? <span className="font-mono">{selected?.review_item_id}</span> : "not created (no concern)"}</div>
                {d.notification_preview && (
                  <div>
                    <div className="flex items-center gap-1.5 text-zinc-400 mb-1"><BellRing className="h-3.5 w-3.5" /> Mock notification preview <Chip className="border-emerald-500/40 text-emerald-300">not sent</Chip></div>
                    <pre className="whitespace-pre-wrap rounded-lg bg-black/60 border border-amber-500/30 p-2.5 text-[11px] text-amber-100">{d.notification_preview}</pre>
                  </div>
                )}
                {d.in_call_instruction && (
                  <div className="text-red-200">
                    Emergency protocol (demo):{" "}
                    {selected?.channel === "twilio_voice"
                      ? "the live voice agent was cued to check safety and give the local emergency number."
                      : "the reply checked safety and gave the local emergency number."}
                  </div>
                )}
              </div>
            )}
            {selectedItem && (
              <div className="border-t border-white/10 pt-3 space-y-2 text-xs">
                <div className="font-semibold">Human review · {selectedItem.id} · {selectedItem.status}</div>
                {selectedItem.status === "reviewed" ? (
                  <div className="text-zinc-300">Disposition: {selectedItem.disposition?.replace(/_/g, " ")}{selectedItem.reviewer_note ? ` — ${selectedItem.reviewer_note}` : ""}</div>
                ) : (
                  <>
                    <select value={disposition} onChange={(e) => setDisposition(e.target.value)} className="w-full rounded bg-black/50 border border-white/10 px-2 py-1.5">
                      {DISPOSITIONS.map((x) => <option key={x} value={x}>{x.replace(/_/g, " ")}</option>)}
                    </select>
                    <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Reviewer note (demo)" className="w-full rounded bg-black/50 border border-white/10 px-2 py-1.5" />
                    <button onClick={markReviewed} className="px-3 py-1.5 rounded bg-[#CBA868] text-black font-semibold">Mark reviewed</button>
                  </>
                )}
              </div>
            )}
          </Panel>

          {audit.length > 0 && (
            <Panel title="Audit trail" icon={<ClipboardList className="h-4 w-4 text-[#CBA868]" />} tag="this session">
              <div className="space-y-1 max-h-48 overflow-y-auto font-mono text-[10px] text-zinc-400">
                {audit.map((e, i) => (
                  <div key={i}>{new Date(e.at).toLocaleTimeString()} · <span className="text-zinc-200">{e.kind}</span> · {JSON.stringify(e.detail)}</div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      </main>
    </div>
  );
}
