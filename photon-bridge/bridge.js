import http from "http";
import { Spectrum } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";

process.env.SPECTRUM_PROJECT_ID = process.env.SPECTRUM_PROJECT_ID || "3df6ba38-c287-462e-b579-b993c388de66";
process.env.SPECTRUM_PROJECT_SECRET = process.env.SPECTRUM_PROJECT_SECRET || "BvKH7VlisfCzd5um2EtCs4KsC7Y4DQaa6XxlKTyIVhk";

console.log("Starting SafeLine Photon iMessage Bridge...");
const app = await Spectrum({
  providers: [imessage.config()],
});

console.log("✅ Photon Spectrum connected to project:", process.env.SPECTRUM_PROJECT_ID);

// 1. Process inbound iMessages
(async () => {
  try {
    for await (const [space, message] of app.messages) {
      if (message.direction !== "inbound") continue;
      const text = message.content?.text || "";
      const senderId = message.sender?.id || "anonymous";

      console.log(`📩 [iMessage from ${senderId}]: "${text}"`);

      try {
        const res = await fetch("http://localhost:8000/api/photon/webhook", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: text,
            sender_id: senderId,
            region: "US",
          }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.spoken_reply) {
            console.log(`💬 Replying via iMessage: "${data.spoken_reply}"`);
            await space.responding(async () => {
              await message.reply(data.spoken_reply);
            });
          }
        }
      } catch (err) {
        console.error("Error communicating with SafeLine backend:", err);
      }
    }
  } catch (err) {
    console.error("Photon messages loop error:", err);
  }
})();

// 2. HTTP Server to receive outbound dispatch alerts from Python backend
const server = http.createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/send") {
    let body = "";
    req.on("data", chunk => body += chunk);
    req.on("end", async () => {
      try {
        const { recipient, text } = JSON.parse(body);
        console.log(`🚀 Dispatching outbound alert to ${recipient}: "${text}"`);
        
        // Attempt to send message
        try {
          if (app.send) {
            await app.send(recipient, text);
          }
        } catch (sendErr) {
          console.warn("Outbound direct send note:", sendErr.message);
        }

        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, recipient }));
      } catch (err) {
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: err.message }));
      }
    });
  } else if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "healthy", service: "photon-bridge" }));
  } else {
    res.writeHead(404);
    res.end();
  }
});

server.listen(8001, () => {
  console.log("SafeLine Photon Bridge listening for dispatch calls on port 8001");
});

