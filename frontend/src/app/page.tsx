"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Shield,
  PhoneCall,
  MessageSquare,
  Sparkles,
  HeartHandshake,
  Ear,
  Brain,
  Lock,
  ArrowRight,
  Activity,
  Globe2,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Zap,
  Users,
  Compass,
  FileCheck2,
  Volume2,
  Send,
} from "lucide-react";

// Interactive Demo Scenarios
const DEMO_SCENARIOS = [
  {
    id: "abuse_disclosure",
    title: "1. Spontaneous Abuse Disclosure",
    tag: "Anti-Retaliation Protocol",
    caller: "My uncle is abusing me... he does bad things and he tells me not to tell anyone or else.",
    acousticCue: "Acoustic Tremor: Moderate distress, hesitations, low fundamental frequency",
    mode: "Voice Telephony (8kHz GSM)",
    ayoReply:
      "Thank you for telling me. What he is doing is completely wrong, and it is not your fault at all. Your secret is safe with me—I will never go and tell your uncle, and we will only report to someone safe who protects you and will never tell him. Are you in a safe room away from him right now?",
    clinicalPillars: ["Believed & De-Blamed", "Safe-Protector Guarantee", "NICHD Open Invitation", "Micro-Agency"],
    riskLevel: 3,
    dispatchAction: "Instant Emergency Caseworker Alert Dispatched via Twilio SMS & Photon",
  },
  {
    id: "panic_hyperventilation",
    title: "2. Acute Panic & Hyperventilation",
    tag: "Neurosequential Model (Regulate)",
    caller: "I can't breathe... my chest is beating so hard... I don't know what's happening...",
    acousticCue: "Respiratory Rate: Rapid short inhalations (32 bpm), vocal hyper-arousal",
    mode: "Voice Telephony (8kHz GSM)",
    ayoReply:
      "I am right here with you. You are safe on this phone with me. Put one hand on your chest, and feel your feet flat on the floor. Let's take one slow breath in together... and let it out softly like a sigh.",
    clinicalPillars: ["Bruce Perry NMT Level 1", "Somatic DBT Grounding", "Paced Physiological Sigh", "Zero Questions"],
    riskLevel: 2,
    dispatchAction: "Somatic De-escalation Active · Background Supervisor Monitored",
  },
  {
    id: "everyday_companion",
    title: "3. Everyday Non-Crisis Check-in",
    tag: "Dual-Mode Companion",
    caller: "Hi Ayo, I'm just sitting here in the courtyard. School was kind of annoying today.",
    acousticCue: "Acoustic Tone: Conversational, casual baseline volume (62 dB)",
    mode: "Voice Telephony (8kHz GSM)",
    ayoReply:
      "Hello my dear! I'm so glad you called. Ah, school can really be annoying sometimes. What happened today that made you feel that way?",
    clinicalPillars: ["Unconditional Positive Regard", "Auntie/Sisterly Attunement", "No Unsolicited Crisis Triggers"],
    riskLevel: 0,
    dispatchAction: "Routine Support Recorded · Zero Alert Required",
  },
  {
    id: "silent_photon",
    title: "4. Silent Whisper / Text Intake",
    tag: "Photon 2.0 Silent Reporting",
    caller: "he is outside my bedroom door right now i cannot talk he is banging",
    acousticCue: "Modality: Silent Photon iMessage/SMS · Zero Acoustic Leakage",
    mode: "Silent Text (Photon 2.0)",
    ayoReply:
      "I hear you silently. Do not make a sound. Keep your door locked. I am alerting an emergency caseworker right now and sending help to your location. Stay low and quiet.",
    clinicalPillars: ["Zero-Audio Stealth", "Immediate Physical Peril Floor", "Instant Caseworker Dispatch"],
    riskLevel: 3,
    dispatchAction: "CRITICAL: Urgent Caseworker Dispatch + Emergency Services Geo-Routed",
  },
];

export default function AyoHomePage() {
  const [activeScenario, setActiveScenario] = useState(DEMO_SCENARIOS[0]);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const simulatePlayAudio = () => {
    setIsPlayingAudio(true);
    setTimeout(() => setIsPlayingAudio(false), 3200);
  };

  return (
    <div className="min-h-screen bg-[#07090E] text-zinc-100 selection:bg-[#CBA868]/30 selection:text-[#E6CA85] font-sans antialiased">
      {/* Background Subtle Ambient Glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-[20%] left-1/2 -translate-x-1/2 w-[900px] h-[500px] bg-gradient-to-b from-[#CBA868]/10 via-[#38BDF8]/5 to-transparent blur-[140px] rounded-full" />
        <div className="absolute top-[45%] -left-[10%] w-[600px] h-[500px] bg-emerald-500/5 blur-[160px] rounded-full" />
        <div className="absolute top-[70%] -right-[10%] w-[600px] h-[500px] bg-[#CBA868]/5 blur-[160px] rounded-full" />
      </div>

      {/* STICKY TOP NAVIGATION */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#07090E]/80 border-b border-white/[0.08]">
        <div className="max-w-7xl mx-auto px-5 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-[#CBA868] to-[#997938] flex items-center justify-center shadow-lg shadow-[#CBA868]/20">
              <Sparkles className="h-5 w-5 text-black" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight text-white">Ayo</span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-[#CBA868]/15 text-[#E6CA85] border border-[#CBA868]/30">
                  Child Safety Line
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 hidden sm:block">Full-duplex voice & silent triage that actually listens</p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-xs text-zinc-300">
            <a href="#blind-spot" className="hover:text-white transition">The Blind Spot</a>
            <a href="#how-it-listens" className="hover:text-white transition">How It Listens</a>
            <a href="#clinical-pillars" className="hover:text-white transition">5 Clinical Pillars</a>
            <a href="#acoustic-ear" className="hover:text-white transition">2026 Acoustic AI</a>
            <a href="#live-demo" className="hover:text-white transition">Live Sandbox</a>
            <a href="#evidence" className="hover:text-white transition">Validation</a>
          </nav>

          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/10 text-xs font-mono text-zinc-300">
              <PhoneCall className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
              <span>+234 201 700 1459</span>
            </div>

            <Link
              href="/console"
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#CBA868] to-[#B89650] text-black text-xs font-semibold hover:brightness-110 transition shadow-lg shadow-[#CBA868]/25 flex items-center gap-1.5"
            >
              <span>Caseworker Console</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* HERO SECTION */}
      <section className="relative z-10 pt-16 pb-20 md:pt-24 md:pb-28 max-w-7xl mx-auto px-5">
        <div className="text-center max-w-4xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>24/7 Full-Duplex Telephony & Silent Messaging Live</span>
          </div>

          <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white leading-[1.08]">
            The 24/7 child-safety line that <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#E6CA85] via-[#CBA868] to-[#997938]">actually listens.</span>
          </h1>

          <p className="text-base sm:text-lg md:text-xl text-zinc-300 max-w-2xl mx-auto font-normal leading-relaxed">
            Full-duplex telephony voice and silent-text triage engineered with clinical trauma psychology, 
            2026 acoustic distress intelligence, and zero family cost. Born from Sabi&apos;s proven Nigerian telephony infrastructure.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3.5">
            <a
              href="#live-demo"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-gradient-to-r from-[#CBA868] to-[#B89650] text-black font-semibold text-sm hover:brightness-110 transition shadow-xl shadow-[#CBA868]/20 flex items-center justify-center gap-2"
            >
              <Sparkles className="h-4 w-4" />
              <span>Simulate Ayo Voice & Silent Text</span>
            </a>

            <Link
              href="/console"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-white border border-white/10 font-semibold text-sm transition flex items-center justify-center gap-2"
            >
              <Shield className="h-4 w-4 text-[#CBA868]" />
              <span>Explore Caseworker Command Center</span>
            </Link>
          </div>

          {/* Institutional Trust Banner */}
          <div className="pt-8 border-t border-white/[0.06] mt-10 grid grid-cols-2 sm:grid-cols-4 gap-4 text-left">
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="text-xs font-mono text-[#CBA868]">&lt; 300 ms</div>
              <div className="text-xs text-zinc-300 font-medium">Barge-in latency</div>
              <div className="text-[11px] text-zinc-500">Asterisk AudioSocket + Gemini Live</div>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="text-xs font-mono text-emerald-400">100.0% Recall</div>
              <div className="text-xs text-zinc-300 font-medium">Acute triage safety floor</div>
              <div className="text-[11px] text-zinc-500">40-case synthetic validation</div>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="text-xs font-mono text-[#38BDF8]">0 PII Stored</div>
              <div className="text-xs text-zinc-300 font-medium">Deterministic Scrubber</div>
              <div className="text-[11px] text-zinc-500">Cryptographic audit preservation</div>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="text-xs font-mono text-amber-300">88% Known Figures</div>
              <div className="text-xs text-zinc-300 font-medium">Anti-retaliation shield</div>
              <div className="text-[11px] text-zinc-500">Confidential from the abuser</div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 1: THE UNSPOKEN BLIND SPOT */}
      <section id="blind-spot" className="relative z-10 py-16 border-t border-white/[0.08] bg-[#090C14]">
        <div className="max-w-7xl mx-auto px-5 space-y-10">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-1.5 text-[#CBA868] text-xs font-semibold uppercase tracking-wider mb-2">
              <Globe2 className="h-4 w-4" /> The Unspoken Blind Spot
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white tracking-tight">
              Half a million child helpline calls go unanswered every year. And when 88% know their abuser, speaking aloud is dangerous.
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <div className="text-3xl font-extrabold text-[#CBA868]">1B+</div>
              <h3 className="text-sm font-semibold text-white">Children face violence every year</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                WHO and UNICEF report staggering violence against youth worldwide. In Nigeria, 6 in 10 children face violence before age 18, yet less than 5% ever receive help.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <div className="text-3xl font-extrabold text-rose-400">88%</div>
              <h3 className="text-sm font-semibold text-white">Know their abuser personally</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Most abuse occurs within homes, schools, and neighborhoods. A child in the next room cannot call 911 or shout for help without immediate physical retaliation.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <div className="text-3xl font-extrabold text-amber-400">71%</div>
              <h3 className="text-sm font-semibold text-white">Helplines report severe understaffing</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Published in JAMA Network Open, 71% of crisis centers report chronic shortages. Half a million child contacts/year are dropped entirely by Child Helpline International.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <div className="text-3xl font-extrabold text-emerald-400">₦0 / $0</div>
              <h3 className="text-sm font-semibold text-white">Zero hardware or data barrier</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                No app install, no internet connectivity, and no smartphone needed. Ayo reaches children over basic 2G feature phones on standard telephony or silent SMS.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2: DUAL-MODALITY INTAKE */}
      <section id="how-it-listens" className="relative z-10 py-16 border-t border-white/[0.08]">
        <div className="max-w-7xl mx-auto px-5 space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-[#CBA868] text-xs font-semibold uppercase tracking-wider">Dual-Modality Architecture</span>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white tracking-tight">
              Designed for every scenario a child faces.
            </h2>
            <p className="text-sm text-zinc-400">
              Whether calling aloud from a schoolyard or texting silently under a blanket with an abuser outside the door.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Channel A: Voice Telephony */}
            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#101422] to-[#0A0D15] p-6 space-y-5">
              <div className="flex items-center justify-between">
                <div className="p-3 rounded-xl bg-[#CBA868]/10 text-[#CBA868] border border-[#CBA868]/20">
                  <PhoneCall className="h-6 w-6" />
                </div>
                <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  8kHz Full-Duplex GSM
                </span>
              </div>

              <div>
                <h3 className="text-xl font-bold text-white">Toll-Free Telephony Voice Line</h3>
                <p className="text-xs text-zinc-400 mt-1">Direct call via Africa&apos;s Talking (+234 201 700 1459) & Twilio Voice</p>
              </div>

              <ul className="space-y-3 text-xs text-zinc-300">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Zero-latency barge-in:</strong> Model drops its playback queue instantly when the child speaks or cries.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Auntie/sisterly cadence:</strong> Warm Nigerian English or US tone; slow pacing to down-regulate sympathetic panic.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Turn length capped:</strong> Strictly 1 to 3 short sentences per turn to avoid overwhelming the child.</span>
                </li>
              </ul>
            </div>

            {/* Channel B: Photon Silent Messaging */}
            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#101422] to-[#0A0D15] p-6 space-y-5">
              <div className="flex items-center justify-between">
                <div className="p-3 rounded-xl bg-[#38BDF8]/10 text-[#38BDF8] border border-[#38BDF8]/20">
                  <MessageSquare className="h-6 w-6" />
                </div>
                <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-[#38BDF8]/10 text-[#38BDF8] border border-[#38BDF8]/20">
                  Photon 2.0 Silent SMS/iMessage
                </span>
              </div>

              <div>
                <h3 className="text-xl font-bold text-white">Silent Text Reporting (Photon 2.0)</h3>
                <p className="text-xs text-zinc-400 mt-1">Built for children who cannot speak aloud without risking physical harm</p>
              </div>

              <ul className="space-y-3 text-xs text-zinc-300">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-[#38BDF8] shrink-0 mt-0.5" />
                  <span><strong>Stealth interaction:</strong> 1-tap quick safe prompts and whisper prompts for minimal finger movement.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-[#38BDF8] shrink-0 mt-0.5" />
                  <span><strong>Caseworker auto-dispatch:</strong> High-risk disclosures immediately route to trained caseworkers via SMS.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-[#38BDF8] shrink-0 mt-0.5" />
                  <span><strong>Zero PII exposure:</strong> Scrubbed before database persistence to preserve forensic admissibility without leaking identity.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3: THE 5 CLINICAL PILLARS */}
      <section id="clinical-pillars" className="relative z-10 py-16 border-t border-white/[0.08] bg-[#090C14]">
        <div className="max-w-7xl mx-auto px-5 space-y-12">
          <div className="max-w-2xl">
            <span className="text-[#CBA868] text-xs font-semibold uppercase tracking-wider">Engineered Clinical Care</span>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white tracking-tight mt-1">
              Why Ayo never causes iatrogenic harm.
            </h2>
            <p className="text-sm text-zinc-400 mt-2">
              Untrained AI asks interrogative questions, imposes toxic positivity, or promises dangerous secrets. Ayo synthesizes five validated clinical methodologies.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <div className="h-8 w-8 rounded-lg bg-[#CBA868]/15 text-[#CBA868] flex items-center justify-center font-bold text-xs">
                1
              </div>
              <h3 className="text-base font-semibold text-white">Carl Rogers&apos; Person-Centered Core</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Unconditional Positive Regard (UPR) without judgment. Transparent AI congruence (openly disclaiming medical license while providing boundless human warmth).
              </p>
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 text-[11px] text-zinc-300 italic">
                &ldquo;I am an AI voice friend here to help you feel safe and calm. Let&apos;s help your body feel settled.&rdquo;
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/15 text-emerald-400 flex items-center justify-center font-bold text-xs">
                2
              </div>
              <h3 className="text-base font-semibold text-white">Bruce Perry&apos;s NMT (Regulate First)</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                In trauma, the amygdala hijacks the brain. You cannot reason with a panicked child. Ayo down-regulates autonomic arousal before ever exploring facts or safety choices.
              </p>
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 text-[11px] text-zinc-300 italic">
                &ldquo;Put one hand on your chest and feel your feet on the floor. Let&apos;s take one breath together.&rdquo;
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <div className="h-8 w-8 rounded-lg bg-[#38BDF8]/15 text-[#38BDF8] flex items-center justify-center font-bold text-xs">
                3
              </div>
              <h3 className="text-base font-semibold text-white">Psychological First Aid (WHO/SAMHSA)</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Practical felt safety first. Non-intrusive presence without demanding stories. Identifying existing human anchors (teachers, aunties, neighbors) in the child&apos;s world.
              </p>
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 text-[11px] text-zinc-300 italic">
                &ldquo;Are you in a safe room away from him right now? You are very brave for reaching out.&rdquo;
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <div className="h-8 w-8 rounded-lg bg-rose-400/15 text-rose-400 flex items-center justify-center font-bold text-xs">
                4
              </div>
              <h3 className="text-base font-semibold text-white">NICHD Child Forensic Protocol</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Strict elimination of &ldquo;Why&rdquo; questions (which imply self-blame). Micro-agency restoration on every turn. Zero leading questions to protect forensic integrity.
              </p>
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 text-[11px] text-zinc-300 italic">
                &ldquo;You can tell me as much or as little as you want. There is no rush, and you can stop anytime.&rdquo;
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3 md:col-span-2 lg:col-span-2">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-amber-400/15 text-amber-400 flex items-center justify-center font-bold text-xs">
                  5
                </div>
                <h3 className="text-base font-semibold text-white">The Safe-Protector Guarantee (Anti-Retaliation)</h3>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Children stay silent because they fear abuser retaliation. If an AI bluntly says &ldquo;I can&apos;t keep secrets,&rdquo; the child hears &ldquo;You will tell my uncle and he will beat me.&rdquo; Ayo guarantees safe confidentiality against the abuser while establishing a protected bridge to trained caseworkers.
              </p>
              <div className="p-3 rounded-xl bg-[#CBA868]/10 border border-[#CBA868]/20 text-xs text-[#E6CA85] font-medium">
                &ldquo;Your secret is completely safe with me. I will never go and tell your uncle, and I will never get you into trouble. When we get help, we will only report to someone safe whose job is to protect you, someone who will never tell your uncle.&rdquo;
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 4: 2026 ACOUSTIC AI INNOVATION */}
      <section id="acoustic-ear" className="relative z-10 py-16 border-t border-white/[0.08]">
        <div className="max-w-7xl mx-auto px-5 space-y-10">
          <div className="grid lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-6 space-y-5">
              <span className="text-[#38BDF8] text-xs font-semibold uppercase tracking-wider font-mono">
                2026 Voice Research Breakthrough
              </span>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white tracking-tight">
                &ldquo;Voice AI Hears but Does Not Listen.&rdquo; Here is how Ayo fixes it.
              </h2>
              <p className="text-xs sm:text-sm text-zinc-300 leading-relaxed">
                In June 2026, leading speech AI researchers (Bartelds et al., arXiv 2606.26083) tested top voice models. 
                They discovered that when words and acoustic distress contradict—such as a crying child saying &ldquo;I&apos;m fine&rdquo;—<strong>the models act solely on the words in 119 out of 120 trials.</strong>
              </p>
              <div className="space-y-3 text-xs text-zinc-300">
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/10 flex items-start gap-3">
                  <Ear className="h-5 w-5 text-[#38BDF8] shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-white">Acoustic Listener Sidecar:</strong> Ayo runs an acoustic sidecar alongside the call that analyzes loudness, crying, silence duration, and tremor in real time.
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/10 flex items-start gap-3">
                  <Volume2 className="h-5 w-5 text-[#CBA868] shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-white">Whisper Mode Shift:</strong> If volume drops precipitously, Ayo infers the perpetrator entered the room and automatically pivots to low-volume whisper questions and keypad &ldquo;Press 1&rdquo; choices.
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-6">
              <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-white/5 pb-3">
                  <span className="text-xs font-mono text-zinc-400">Live Acoustic Signal Pipeline</span>
                  <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">Active Sidecar</span>
                </div>

                <div className="space-y-2.5">
                  <div className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-black/40 border border-white/5">
                    <span className="text-zinc-400">Input Sample Rate</span>
                    <span className="font-mono text-zinc-200">8,000 Hz Narrowband GSM</span>
                  </div>
                  <div className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-black/40 border border-white/5">
                    <span className="text-zinc-400">Decimator Engine</span>
                    <span className="font-mono text-zinc-200">Stateful 3:1 Boxcar Filter (24k→8k)</span>
                  </div>
                  <div className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-black/40 border border-white/5">
                    <span className="text-zinc-400">Whisper Threshold</span>
                    <span className="font-mono text-amber-300">-28 dBFS Delta Trigger</span>
                  </div>
                  <div className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-black/40 border border-white/5">
                    <span className="text-zinc-400">PII De-identification</span>
                    <span className="font-mono text-emerald-400">Pre-LLM Deterministic Scrubber</span>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#CBA868]/10 border border-[#CBA868]/20 text-[11px] text-[#E6CA85]">
                  💡 <em>&ldquo;We don&apos;t just transcribe words. We translate raw telephony acoustics into steering guidance for the brain.&rdquo;</em>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 5: INTERACTIVE LIVE SANDBOX */}
      <section id="live-demo" className="relative z-10 py-16 border-t border-white/[0.08] bg-[#090C14]">
        <div className="max-w-7xl mx-auto px-5 space-y-10">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-[#CBA868] text-xs font-semibold uppercase tracking-wider">Interactive Live Simulator</span>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white tracking-tight">
              Test Ayo&apos;s trauma-informed response engine.
            </h2>
            <p className="text-xs sm:text-sm text-zinc-400">
              Select a scenario to inspect the acoustic detection, spoken response, clinical guarantees, and caseworker dispatch.
            </p>
          </div>

          {/* Scenario Selector Pills */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            {DEMO_SCENARIOS.map((sc) => (
              <button
                key={sc.id}
                onClick={() => setActiveScenario(sc)}
                className={`px-3.5 py-2 rounded-xl text-xs font-medium transition flex items-center gap-2 ${
                  activeScenario.id === sc.id
                    ? "bg-[#CBA868] text-black shadow-lg shadow-[#CBA868]/20 font-semibold"
                    : "bg-white/[0.04] text-zinc-300 hover:bg-white/[0.08] border border-white/10"
                }`}
              >
                <span>{sc.title}</span>
              </button>
            ))}
          </div>

          {/* Active Scenario Card */}
          <div className="max-w-4xl mx-auto rounded-3xl border border-white/10 bg-[#0E121E] p-6 sm:p-8 space-y-6 shadow-2xl">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-mono uppercase px-2.5 py-1 rounded-md bg-[#CBA868]/15 text-[#E6CA85] border border-[#CBA868]/30 font-semibold">
                  {activeScenario.tag}
                </span>
                <span className="text-xs text-zinc-400">{activeScenario.mode}</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="text-zinc-400">Risk Assessment:</span>
                <span
                  className={`px-2 py-0.5 rounded font-bold ${
                    activeScenario.riskLevel === 3
                      ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                      : activeScenario.riskLevel === 2
                      ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  }`}
                >
                  Level {activeScenario.riskLevel}
                </span>
              </div>
            </div>

            {/* Caller Utterance */}
            <div className="space-y-1.5">
              <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Caller Audio / Text</div>
              <div className="p-4 rounded-2xl bg-black/50 border border-white/10 text-sm text-zinc-200 font-mono">
                &ldquo;{activeScenario.caller}&rdquo;
              </div>
            </div>

            {/* Acoustic Sidecar Signal */}
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-zinc-400">
                <Ear className="h-4 w-4 text-[#38BDF8]" />
                <span className="text-zinc-300 font-medium">{activeScenario.acousticCue}</span>
              </div>
              <span className="text-[10px] font-mono text-emerald-400">Sidecar Latency: 22ms</span>
            </div>

            {/* Ayo Spoken Response */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-[11px] font-semibold text-[#CBA868] uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" /> Ayo Spoken Voice Response
                </div>
                <button
                  onClick={simulatePlayAudio}
                  disabled={isPlayingAudio}
                  className="px-3 py-1 rounded-lg bg-[#CBA868]/15 hover:bg-[#CBA868]/25 text-[#E6CA85] text-xs font-medium border border-[#CBA868]/30 flex items-center gap-1.5 transition"
                >
                  {isPlayingAudio ? (
                    <>
                      <Volume2 className="h-3 w-3 animate-pulse text-emerald-400" />
                      <span>Synthesizing Voice...</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-3 w-3" />
                      <span>Simulate Audio Playback</span>
                    </>
                  )}
                </button>
              </div>

              <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-br from-[#151A29] to-[#0D111A] border border-[#CBA868]/20 text-zinc-100 text-sm sm:text-base leading-relaxed">
                &ldquo;{activeScenario.ayoReply}&rdquo;
              </div>
            </div>

            {/* Safeguard Pillars & Dispatch Result */}
            <div className="pt-2 grid sm:grid-cols-2 gap-4 border-t border-white/10">
              <div className="space-y-1.5">
                <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Clinical Guarantees Active</span>
                <div className="flex flex-wrap gap-1.5">
                  {activeScenario.clinicalPillars.map((pil) => (
                    <span key={pil} className="px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/10 text-[11px] text-zinc-300">
                      ✓ {pil}
                    </span>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Caseworker Dispatch Action</span>
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 text-xs text-emerald-400 font-mono">
                  {activeScenario.dispatchAction}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 6: FORENSICS & PRIVACY */}
      <section id="evidence" className="relative z-10 py-16 border-t border-white/[0.08]">
        <div className="max-w-7xl mx-auto px-5 space-y-10">
          <div className="max-w-2xl">
            <span className="text-[#CBA868] text-xs font-semibold uppercase tracking-wider">Forensic Accountability</span>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white tracking-tight mt-1">
              Protecting the child today. Exposing serial abusers tomorrow.
            </h2>
            <p className="text-sm text-zinc-400 mt-2">
              Every incident is deterministically scrubbed of raw PII to protect victim privacy, while preserving forensic location and recurring entity links for authorized child-protection caseworkers.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-5">
            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <Lock className="h-6 w-6 text-emerald-400" />
              <h3 className="text-base font-semibold text-white">Deterministic PII Scrubber</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Names, phone numbers, exact street numbers, and emails are redacted before model ingestion or SQLite persistence. Zero raw PII leaks across 40 evaluation test suites.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <Zap className="h-6 w-6 text-[#CBA868]" />
              <h3 className="text-base font-semibold text-white">Cross-Case Entity Forensics</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Connects recurring locations (e.g. &ldquo;Surulere Primary Annex&rdquo;) and roles (&ldquo;coach&rdquo;, &ldquo;store room&rdquo;) across separate anonymized reports to surface predator patterns to caseworkers.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#0E121E] p-5 space-y-3">
              <HeartHandshake className="h-6 w-6 text-[#38BDF8]" />
              <h3 className="text-base font-semibold text-white">Verified Human Lifeline Handoff</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                AI stabilizes and triages; human professionals intervene. Direct routing to Nigeria&apos;s Cece Yara Free Child Helpline (0800 800 8001), 112 Emergency, and US 988 Lifeline.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 7: VENTURE ROOTS & FOUNDER MISSION */}
      <section className="relative z-10 py-16 border-t border-white/[0.08] bg-[#090C14]">
        <div className="max-w-7xl mx-auto px-5">
          <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-[#121624] to-[#0A0D15] p-8 md:p-12 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#CBA868]/15 border border-[#CBA868]/30 text-[#E6CA85] text-xs font-semibold">
              <Sparkles className="h-3.5 w-3.5" /> Born from Education for Equality & Sabi
            </div>

            <h2 className="text-2xl sm:text-3xl md:text-4xl font-extrabold text-white tracking-tight max-w-3xl leading-snug">
              Every child has the right to grow up safe, heard, and protected.
            </h2>

            <p className="text-sm md:text-base text-zinc-300 max-w-3xl leading-relaxed">
              Founded by <strong>Naomi Ivie</strong> (Wesleyan University, Patricelli Fellow, MIT Sloan Africa Business Challenge Runner-up), 
              Ayo represents the expansion of Education for Equality&apos;s low-latency telephony infrastructure—scaling from foundational learning into 
              lifesaving child protection across Nigeria and globally.
            </p>

            <div className="pt-4 flex flex-wrap items-center gap-4">
              <Link
                href="/console"
                className="px-6 py-3 rounded-xl bg-[#CBA868] text-black font-semibold text-sm hover:brightness-110 transition shadow-lg shadow-[#CBA868]/20 flex items-center gap-2"
              >
                <span>Launch Caseworker Command Center</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="relative z-10 py-12 border-t border-white/[0.08] text-xs text-zinc-400">
        <div className="max-w-7xl mx-auto px-5 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 rounded-lg bg-[#CBA868] flex items-center justify-center text-black font-bold text-xs">
              A
            </div>
            <div>
              <span className="font-semibold text-white">Ayo</span> · An Education for Equality 501(c)(3) Initiative
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 text-zinc-400">
            <span>Nigeria: <strong>112</strong> / Cece Yara <strong>0800 800 8001</strong></span>
            <span>US: <strong>988 Lifeline</strong> / Childhelp <strong>1-800-422-4453</strong></span>
            <Link href="/console" className="hover:text-white transition underline">Caseworker Console</Link>
          </div>

          <div className="text-zinc-400">
            © {new Date().getFullYear()} Ayo. Built with care for every child.
          </div>
        </div>
      </footer>
    </div>
  );
}
