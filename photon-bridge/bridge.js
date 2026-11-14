// SafeLine <-> Photon Spectrum iMessage bridge.
// Run with:  node --env-file=.env bridge.js
// .env needs SPECTRUM_PROJECT_ID and SPECTRUM_PROJECT_SECRET (never commit it).
import http from "http";
import { Spectrum } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";

const BACKEND = process.env.SAFELINE_BACKEND_URL || "http://localhost:8000";
const PORT = Number(process.env.PHOTON_BRIDGE_PORT || 8001);

if (!process.env.SPECTRUM_PROJECT_ID || !process.env.SPECTRUM_PROJECT_SECRET) {
  console.error("Missing SPECTRUM_PROJECT_ID / SPECTRUM_PROJECT_SECRET. Start with: node --env-file=.env bridge.js");
  process.exit(1);
}

console.log("Starting SafeLine Photon iMessage Bridge...");
const app = await Spectrum({ providers: [imessage.config()] });
const im = imessage(app);
console.log("Photon Spectrum connected to project:", process.env.SPECTRUM_PROJECT_ID);

// 1. Inbound iMessages -> SafeLine triage -> reply in the same thread
(async () => {
  try {
    for await (const [space, message] of app.messages) {
      if (message.direction !== "inbound") continue;
      const text = message.content?.text || "";
      if (!text) continue;
      console.log(`[iMessage in] ${text.length} chars`);
      try {
        const res = await fetch(`${BACKEND}/api/photon/webhook`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, sender_id: message.sender?.id || "anonymous", region: "US" }),
        });
        if (!res.ok) {
          console.error("Backend returned", res.status);
          continue;
        }
        const data = await res.json();
        const reply = data.assistant_reply || data.spoken_reply;
        if (reply) {
          await app.responding(space, async () => {
            await message.reply(reply);
          });
        }
      } catch (err) {
        console.error("Error talking to SafeLine backend:", err.message);
      }
    }
  } catch (err) {
    console.error("Photon messages loop error:", err);
  }
})();

// 2. Outbound: POST /send {recipient: "+1555...", text} from the Python backend
async function sendTo(recipient, text) {
  const space = await im.space.create(recipient);
  return space.send(text);
}

const server = http.createServer((req, res) => {
  const reply = (code, obj) => {
    res.writeHead(code, { "Content-Type": "application/json" });
    res.end(JSON.stringify(obj));
  };
  if (req.method === "POST" && req.url === "/send") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", async () => {
      let recipient, text;
      try {
        ({ recipient, text } = JSON.parse(body));
      } catch {
        return reply(400, { ok: false, error: "bad_json" });
      }
      if (!recipient || !text) return reply(400, { ok: false, error: "recipient_and_text_required" });
      try {
        await sendTo(recipient, text);
        console.log(`[iMessage out] sent to ...${String(recipient).slice(-4)}`);
        reply(200, { ok: true });
      } catch (err) {
        // Report failure honestly so the backend can fall back to SMS.
        console.warn(`[iMessage out] failed to ...${String(recipient).slice(-4)}: ${err.message}`);
        reply(502, { ok: false, error: err.message });
      }
    });
  } else if (req.url === "/health") {
    reply(200, { status: "healthy", service: "photon-bridge" });
  } else {
    res.writeHead(404);
    res.end();
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`SafeLine Photon Bridge listening on 127.0.0.1:${PORT}`);
});
