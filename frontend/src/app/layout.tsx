import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SafeLine — 24/7 Voice & Silent-Text Child Safety Triage",
  description: "Trauma-informed voice and Photon silent-text reporting line with real-time LangGraph triage and evidence-cited forensics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0B0D12] text-[#F7F1E4] antialiased selection:bg-[#CBA868]/30">
        {children}
      </body>
    </html>
  );
}
