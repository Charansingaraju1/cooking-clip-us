/**
 * Cooking Clip US - 24/7 Serverless Telegram Bot (Cloudflare Worker ES Module)
 * Triggers 100% Original High-Retention Shorts generation on GitHub Actions (zero laptop needed).
 */

const GITHUB_REPO = "Charansingaraju1/cooking-clip-us";
const WORKFLOW_FILE = "viral_pipeline.yml";
const CHANNEL_HANDLE = "@Cooked_Clips_US";

async function sendTelegram(botToken, chatId, text) {
  await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: "HTML",
      disable_web_page_preview: true,
    }),
  });
}

async function fetchGitHubRuns() {
  const resp = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/actions/runs?per_page=3`,
    { headers: { "User-Agent": "CookedClipsCloudflareBot/2.0" } }
  );
  if (!resp.ok) return [];
  const data = await resp.json();
  return data.workflow_runs || [];
}

async function discoverLiveChannelStats() {
  try {
    const chResp = await fetch(`https://www.youtube.com/${CHANNEL_HANDLE}/shorts`, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });
    const html = await chResp.text();
    const matches = [...html.matchAll(/"videoId":"([A-Za-z0-9_-]{11})"/g)].map((m) => m[1]);
    const uniqueIds = [...new Set(matches)].slice(0, 10);

    const rows = await Promise.all(
      uniqueIds.map(async (id) => {
        try {
          const [wRes, oRes] = await Promise.all([
            fetch(`https://www.youtube.com/watch?v=${id}`, { headers: { "User-Agent": "Mozilla/5.0" } }),
            fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${id}&format=json`),
          ]);
          const wHtml = await wRes.text();
          const m = wHtml.match(/"viewCount":"(\d+)"/);
          const views = m ? parseInt(m[1], 10) : 0;
          const oJson = oRes.ok ? await oRes.json() : {};
          return { id, views, title: oJson.title || id };
        } catch {
          return { id, views: 0, title: id };
        }
      })
    );
    return rows;
  } catch {
    return [];
  }
}

async function triggerCloudWorkflow(env, topic = "") {
  if (!env.GITHUB_PAT) {
    return { ok: false, missingPat: true };
  }
  const resp = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "CookedClipsCloudflareBot/2.0",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ref: "main",
        inputs: { topic: topic || "" },
      }),
    }
  );
  return { ok: resp.status === 204, status: resp.status };
}

function formatSchedule() {
  return (
    "⏰ <b>2-SLOT ORIGINAL SHORTS SCHEDULE</b>\n" +
    "━━━━━━━━━━━━━━━━━━━━━━\n" +
    "☀️ <b>Slot 1 (19:00 UTC):</b> 02:00 PM EST / 12:30 AM IST\n" +
    "🌙 <b>Slot 2 (23:00 UTC):</b> 06:00 PM EST / 04:30 AM IST\n\n" +
    "<i>100% Original Voiceover + HD Visuals + Sync Captions (Zero Clipping).</i>"
  );
}

async function handleText(text, env, chatId) {
  const clean = text.trim();
  const cmd = clean.toLowerCase();

  if (cmd === "/start" || cmd === "/help") {
    return sendTelegram(
      env.BOT_TOKEN,
      chatId,
      "🤖 <b>Cooked Clips US — Original Shorts Engine</b>\n" +
        "━━━━━━━━━━━━━━━━━━━━━━\n" +
        "• <code>/status</code> or <code>/dash</code> — Live cloud runs & triggers\n" +
        "• <code>/analyze</code> — Live YouTube Shorts view audit\n" +
        "• <code>/schedule</code> — Daily 2-slot US & IST schedule\n" +
        "• <code>/upload</code> — Publish next original story now\n" +
        "• <code>/upload Black Hole</code> — Generate & post custom topic\n\n" +
        "☁️ <i>Zero clipping. 100% YPP-safe original automation on Cloudflare + GitHub.</i>"
    );
  }

  if (cmd === "/schedule" || cmd === "schedule") {
    return sendTelegram(env.BOT_TOKEN, chatId, formatSchedule());
  }

  if (cmd === "/status" || cmd === "/dash" || cmd === "status") {
    const runs = await fetchGitHubRuns();
    const lines = runs.map((r) => {
      const icon = r.conclusion === "success" ? "✅" : r.conclusion ? "❌" : "⏳";
      return `${icon} <code>${r.event}</code> (${r.created_at.slice(0, 16).replace("T", " ")} UTC)`;
    });
    const dispatchState = env.GITHUB_PAT ? "🟢 Armed" : "⚠️ Needs <code>GITHUB_PAT</code>";
    return sendTelegram(
      env.BOT_TOKEN,
      chatId,
      "🟢 <b>24/7 ORIGINAL SHORTS ENGINE</b>\n" +
        "━━━━━━━━━━━━━━━━━━━━━━\n" +
        "• <b>Bot Host:</b> Cloudflare Worker (Always On)\n" +
        `• <b>Remote Upload:</b> ${dispatchState}\n` +
        "• <b>Latest US Runs:</b>\n" +
        (lines.length ? lines.join("\n") : "No runs returned") +
        `\n\n👉 <a href="https://github.com/${GITHUB_REPO}/actions">Open GitHub Actions</a>`
    );
  }

  if (cmd === "/analyze" || cmd === "/audit" || cmd === "analyze") {
    await sendTelegram(env.BOT_TOKEN, chatId, "🔍 <i>Scanning latest Shorts on @Cooked_Clips_US...</i>");
    const rows = await discoverLiveChannelStats();
    const total = rows.reduce((s, v) => s + v.views, 0);
    const top = rows.length ? [...rows].sort((a, b) => b.views - a.views)[0] : { id: "", title: "N/A", views: 0 };
    return sendTelegram(
      env.BOT_TOKEN,
      chatId,
      `📊 <b>LIVE AUDIT (${CHANNEL_HANDLE})</b>\n` +
        `• <b>Latest ${rows.length} Shorts Views:</b> <code>${total.toLocaleString()}</code>\n` +
        `• <b>Top Video:</b> <a href="https://youtube.com/shorts/${top.id}">${top.title}</a> (<b>${top.views.toLocaleString()}</b>)`
    );
  }

  if (cmd.startsWith("/upload")) {
    const customTopic = clean.replace(/^\/upload\s*/i, "").trim();
    const res = await triggerCloudWorkflow(env, customTopic);
    if (res.ok) {
      return sendTelegram(
        env.BOT_TOKEN,
        chatId,
        `🚀 <b>Original Short Triggered in US Cloud!</b>\n• <b>Topic:</b> ${customTopic || "Next Curated Story"}\n👉 <a href="https://github.com/${GITHUB_REPO}/actions">Watch Live Run</a>`
      );
    }
    return sendTelegram(env.BOT_TOKEN, chatId, `❌ Trigger failed (status <code>${res.status || "no PAT"}</code>).`);
  }

  return sendTelegram(
    env.BOT_TOKEN,
    chatId,
    "Got it! Use <code>/upload</code>, <code>/upload &lt;any topic&gt;</code>, <code>/status</code>, or <code>/analyze</code>."
  );
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "GET") {
      return new Response("Cooked Clips US Original Shorts Bot Active", { status: 200 });
    }
    if (request.method !== "POST" || !env.BOT_TOKEN) {
      return new Response("OK", { status: 200 });
    }
    try {
      const update = await request.json();
      const msg = update.message || update.edited_message;
      if (!msg || !msg.chat) return new Response("OK", { status: 200 });
      if (String(msg.chat.id) !== String(env.ALLOWED_CHAT_ID || "6236827164")) {
        return new Response("OK", { status: 200 });
      }
      if (msg.voice || msg.audio) {
        ctx.waitUntil(
          sendTelegram(
            env.BOT_TOKEN,
            msg.chat.id,
            "🎙️ Send text commands: <code>/upload</code>, <code>/upload &lt;topic&gt;</code>, <code>/status</code>, or <code>/analyze</code>."
          )
        );
      } else if (msg.text) {
        ctx.waitUntil(handleText(msg.text, env, String(msg.chat.id)));
      }
    } catch {
      // Never trigger Telegram retry storms.
    }
    return new Response("OK", { status: 200 });
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(triggerCloudWorkflow(env, ""));
  },
};
