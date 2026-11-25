/**
 * Cooking Clip US - 24/7 Serverless Telegram Bot (Cloudflare Worker ES Module)
 * Secrets (set via Cloudflare Worker Secrets/Vars, never hardcoded):
 * - BOT_TOKEN
 * - ALLOWED_CHAT_ID
 * - GITHUB_PAT (optional: enables 1-tap /upload & Cron workflow_dispatch)
 */

const GITHUB_REPO = "Charansingaraju1/cooking-clip-us";
const WORKFLOW_FILE = "viral_pipeline.yml";

const TRACKED_VIDEOS = [
  { id: "aOQsf2H7flw", streamer: "Lacy", label: "GTA 6 Graphics" },
  { id: "89TyL4qEXpc", streamer: "Lacy", label: "First Heist" },
  { id: "YGLt0Ddk1u4", streamer: "Lacy", label: "GTA 6 Mission" },
  { id: "lxBks72Ku4s", streamer: "Kai", label: "Strip Club" },
  { id: "7D19dt_s7wc", streamer: "Kai", label: "Vault Robbery" },
  { id: "0fZocvkPLCw", streamer: "Kai", label: "Getaway" },
  { id: "wF8i4d3wLgU", streamer: "Lacy", label: "Cops Chase" },
  { id: "w4ICvZ7pwbU", streamer: "Kai", label: "Compound Shootout" },
  { id: "xMQSx45G8pY", streamer: "Kai", label: "Praying Intro" },
];

const REWARD_CAMPAIGNS = {
  KAI: "https://contentrewards.com/c/campaigns/1d2bcb00-c904-415f-aa82-f95b96baad86",
  LACY: "https://contentrewards.com/c/campaigns/a5c63fad-cd53-4b81-9305-4a2d1696872a",
};

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
    { headers: { "User-Agent": "CookedClipsCloudflareBot/1.0" } }
  );
  if (!resp.ok) return [];
  const data = await resp.json();
  return data.workflow_runs || [];
}

async function fetchLiveViewCount(videoId) {
  try {
    const resp = await fetch(`https://www.youtube.com/watch?v=${videoId}`, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });
    if (!resp.ok) return 0;
    const html = await resp.text();
    const m = html.match(/"viewCount":"(\d+)"/);
    return m ? parseInt(m[1], 10) : 0;
  } catch {
    return 0;
  }
}

async function triggerCloudWorkflow(env, channel, url = "", hook = "") {
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
        "User-Agent": "CookedClipsCloudflareBot/1.0",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ref: "main",
        inputs: { channel: channel || "lacy", url: url || "", hook: hook || "" },
      }),
    }
  );
  return { ok: resp.status === 204, status: resp.status };
}

function formatSchedule() {
  return (
    "⏰ <b>2-SLOT CLOUD SCHEDULE (ZERO LAPTOP)</b>\n" +
    "━━━━━━━━━━━━━━━━━━━━━━\n" +
    "☀️ <b>Slot 1 (19:00 UTC):</b> 02:00 PM EST / 12:30 AM IST — <b>Lacy</b>\n" +
    "🌙 <b>Slot 2 (23:00 UTC):</b> 06:00 PM EST / 04:30 AM IST — <b>Kai Cenat</b>\n\n" +
    "<i>Format: 70/30 facecam, -20dB BGM, 15s loop, US GitHub runner.</i>"
  );
}

async function handleText(text, env, chatId) {
  const clean = text.trim();
  const cmd = clean.toLowerCase();

  if (cmd === "/start" || cmd === "/help") {
    return sendTelegram(
      env.BOT_TOKEN,
      chatId,
      "🤖 <b>Cooked Clips US — 24/7 Serverless Bot</b>\n" +
        "━━━━━━━━━━━━━━━━━━━━━━\n" +
        "• <code>/status</code> or <code>/dash</code> — Live cloud runs & bot state\n" +
        "• <code>/analyze</code> — Live YouTube Shorts view count audit\n" +
        "• <code>/schedule</code> — Daily 2-slot US & IST schedule\n" +
        "• <code>/rewards</code> — Content Rewards claim portals\n" +
        "• <code>/upload</code> or paste any stream URL — Launch US cloud slot\n\n" +
        "☁️ <i>Running 100% on Cloudflare Workers (laptop can stay off).</i>"
    );
  }

  if (cmd === "/schedule" || cmd === "schedule") {
    return sendTelegram(env.BOT_TOKEN, chatId, formatSchedule());
  }

  if (cmd === "/rewards" || cmd === "/portal") {
    return sendTelegram(
      env.BOT_TOKEN,
      chatId,
      "🏆 <b>CONTENT REWARDS PORTALS</b>\n" +
        `• <a href="${REWARD_CAMPAIGNS.LACY}">Lacy Campaign ($12.5k Pool)</a>\n` +
        `• <a href="${REWARD_CAMPAIGNS.KAI}">Kai Cenat Campaign ($10k Pool)</a>`
    );
  }

  if (cmd === "/status" || cmd === "/dash" || cmd === "status") {
    const runs = await fetchGitHubRuns();
    const lines = runs.map((r) => {
      const icon = r.conclusion === "success" ? "✅" : r.conclusion ? "❌" : "⏳";
      return `${icon} <code>${r.event}</code> (${r.created_at.slice(0, 16).replace("T", " ")} UTC)`;
    });
    const dispatchState = env.GITHUB_PAT ? "🟢 Armed" : "⚠️ Needs <code>GITHUB_PAT</code> secret";
    return sendTelegram(
      env.BOT_TOKEN,
      chatId,
      "🟢 <b>24/7 CLOUD SYSTEM STATUS</b>\n" +
        "━━━━━━━━━━━━━━━━━━━━━━\n" +
        "• <b>Bot Host:</b> Cloudflare Worker (Always On)\n" +
        `• <b>Remote Trigger:</b> ${dispatchState}\n` +
        "• <b>Latest US GitHub Runs:</b>\n" +
        (lines.length ? lines.join("\n") : "No runs returned") +
        `\n\n👉 <a href="https://github.com/${GITHUB_REPO}/actions">Open GitHub Actions</a>`
    );
  }

  if (cmd === "/analyze" || cmd === "/audit" || cmd === "analyze") {
    await sendTelegram(env.BOT_TOKEN, chatId, "🔍 <i>Fetching live YouTube views across 9 Shorts...</i>");
    const counts = await Promise.all(
      TRACKED_VIDEOS.map(async (v) => ({ ...v, views: await fetchLiveViewCount(v.id) }))
    );
    const total = counts.reduce((s, v) => s + v.views, 0);
    const top = [...counts].sort((a, b) => b.views - a.views)[0];
    const lacyViews = counts.filter((c) => c.streamer === "Lacy").reduce((s, c) => s + c.views, 0);
    const kaiViews = counts.filter((c) => c.streamer === "Kai").reduce((s, c) => s + c.views, 0);

    return sendTelegram(
      env.BOT_TOKEN,
      chatId,
      "📊 <b>LIVE YOUTUBE SHORTS AUDIT (@Cooked_Clips_US)</b>\n" +
        `• <b>Total Views (${counts.length} Shorts):</b> <code>${total.toLocaleString()}</code>\n` +
        `• <b>Top Clip:</b> <a href="https://youtube.com/shorts/${top.id}">${top.label}</a> (<b>${top.views.toLocaleString()}</b>)\n` +
        `• <b>Lacy vs Kai:</b> ${lacyViews.toLocaleString()} vs ${kaiViews.toLocaleString()} views`
    );
  }

  const urlMatch = clean.match(/https?:\/\/\S+/i);
  if (cmd.startsWith("/upload") || urlMatch) {
    const streamUrl = urlMatch ? urlMatch[0] : "";
    const channel = cmd.includes("kai") ? "kaicenat" : "lacy";
    const res = await triggerCloudWorkflow(env, channel, streamUrl);
    if (res.ok) {
      return sendTelegram(
        env.BOT_TOKEN,
        chatId,
        `🚀 <b>US Cloud Upload Triggered!</b>\n• <b>Streamer:</b> ${channel}\n• <b>Source:</b> ${streamUrl || "Auto search"}\n👉 <a href="https://github.com/${GITHUB_REPO}/actions">Watch Live Run</a>`
      );
    }
    if (res.missingPat) {
      return sendTelegram(
        env.BOT_TOKEN,
        chatId,
        "⚠️ <b>Remote /upload needs one secret:</b>\n" +
          "Add <code>GITHUB_PAT</code> (GitHub token with <code>repo</code> + <code>workflow</code> scope) in Cloudflare Worker Settings ➔ Variables.\n\n" +
          `Until then, tap here to trigger from phone browser:\n👉 <a href="https://github.com/${GITHUB_REPO}/actions/workflows/${WORKFLOW_FILE}">Run US Pipeline Manually</a>`
      );
    }
    return sendTelegram(env.BOT_TOKEN, chatId, `❌ GitHub dispatch returned HTTP <code>${res.status}</code>.`);
  }

  return sendTelegram(
    env.BOT_TOKEN,
    chatId,
    `Got it, Boss! Send <code>/status</code>, <code>/analyze</code>, <code>/schedule</code>, or paste a stream link.`
  );
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "GET") {
      return new Response("Cooked Clips US Cloudflare Bot Active", { status: 200 });
    }
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }
    if (!env.BOT_TOKEN) {
      return new Response("Missing BOT_TOKEN secret", { status: 500 });
    }

    try {
      const update = await request.json();
      const msg = update.message || update.edited_message;
      if (!msg || !msg.chat) return new Response("OK", { status: 200 });

      const chatId = String(msg.chat.id);
      const allowedId = String(env.ALLOWED_CHAT_ID || "6236827164");
      if (chatId !== allowedId) {
        return new Response("OK", { status: 200 });
      }

      if (msg.voice || msg.audio) {
        ctx.waitUntil(
          sendTelegram(
            env.BOT_TOKEN,
            chatId,
            "🎙️ Cloud bot uses fast text commands (<code>/status</code>, <code>/analyze</code>, <code>/upload</code>, or paste a stream URL)."
          )
        );
      } else if (msg.text) {
        ctx.waitUntil(handleText(msg.text, env, chatId));
      }
    } catch {
      // Return 200 so Telegram never retries malformed webhook payloads.
    }
    return new Response("OK", { status: 200 });
  },

  async scheduled(event, env, ctx) {
    const hour = new Date(event.scheduledTime).getUTCHours();
    const channel = hour === 19 ? "lacy" : "kaicenat";
    ctx.waitUntil(triggerCloudWorkflow(env, channel));
  },
};
