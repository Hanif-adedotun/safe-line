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
      console.log(`[iMessage in] from ${maskHandle(message.sender?.id)} (${text.length} chars)`);
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

// Shows whether Apple reports a phone number or an email for a sender, without
// logging the full handle: "+1•••7048" or "n•••@gmail.com".
function maskHandle(h) {
  if (!h) return "unknown";
  h = String(h).replace(/^.*;-;/, "");
  if (h.includes("@")) return `${h[0]}•••@${h.split("@")[1]}`;
  return `${h.slice(0, 2)}•••${h.slice(-4)}`;
}

// Free/Pro Photon projects only message registered users. Register the
// recipient first (idempotent: re-creating an existing phone returns it).
// Set PHOTON_AUTO_REGISTER=0 to turn this off.
async function ensureRegistered(phone) {
  if (process.env.PHOTON_AUTO_REGISTER === "0" || !/^\+[1-9]\d{6,14}$/.test(phone)) return;
  const id = process.env.SPECTRUM_PROJECT_ID;
  const auth = Buffer.from(`${id}:${process.env.SPECTRUM_PROJECT_SECRET}`).toString("base64");
  const res = await fetch(`https://spectrum.photon.codes/projects/${id}/users/`, {
    method: "POST",
    headers: { Authorization: `Basic ${auth}`, "Content-Type": "application/json" },
    body: JSON.stringify({ type: "shared", phoneNumber: phone }),
  });
  if (!res.ok) {
    console.warn(`[photon users] register ${maskHandle(phone)} failed: HTTP ${res.status} ${(await res.text()).slice(0, 200)}`);
  }
}

// 2. Outbound: POST /send {recipient: "+1555...", text} from the Python backend
async function sendTo(recipient, text) {
  await ensureRegistered(recipient);
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
        console.log(`[iMessage out] sent to ${maskHandle(recipient)}`);
        reply(200, { ok: true });
      } catch (err) {
        // Report failure honestly so the backend can fall back to SMS.
        console.warn(`[iMessage out] failed to ${maskHandle(recipient)}: ${err.message}`);
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
