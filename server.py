#!/usr/bin/env python3
"""
FastAPI Server for Hugging Face Spaces (Port 7860)
Provides a clean dashboard and REST API to monitor streams, clip URLs, and download 9:16 vertical MP4s.
"""

import os
import pathlib
import subprocess
import threading
from fastapi import FastAPI, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import engine

app = FastAPI(title="Cooking Clip US Engine")

ACTIVE_WATCHERS = {}

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cooking Clip US - Cloud Studio</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f1117; color: #e6edf3; margin: 0; padding: 20px; }
    .container { max-width: 900px; margin: auto; }
    h1 { color: #f85149; margin-bottom: 5px; }
    p.sub { color: #8b949e; margin-top: 0; font-size: 14px; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 18px; margin-bottom: 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-top: 12px; }
    button { background: #238636; color: white; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; width: 100%; transition: 0.2s; }
    button:hover { background: #2ea043; }
    button.danger { background: #da3633; }
    button.danger:hover { background: #f85149; }
    input[type="text"] { width: 100%; box-sizing: border-box; padding: 10px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: white; margin-bottom: 10px; }
    .badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
    .badge-live { background: #f85149; color: white; }
    .badge-off { background: #30363d; color: #8b949e; }
    .clip-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-top: 15px; }
    .clip-card { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; padding: 10px; text-align: center; }
    video { width: 100%; max-height: 400px; border-radius: 6px; background: black; }
    a.btn { display: block; margin-top: 8px; padding: 8px; background: #1f6feb; color: white; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: bold; }
  </style>
</head>
<body>
<div class="container">
  <h1>🎬 Cooking Clip US</h1>
  <p class="sub">Headless 24/7 Cloud Clipping Engine for Hugging Face Spaces (Port 7860)</p>

  <div class="card">
    <h3>📡 Live Stream Watchers</h3>
    <p style="font-size: 13px; color: #8b949e;">Click to start 24/7 chat-spike AI monitoring. Facecam and gameplay auto-stack into 9:16 vertical shorts.</p>
    <div class="grid">
      <div>
        <form action="/watch" method="post">
          <input type="hidden" name="channel" value="kaicenat">
          <button type="submit">Watch Kai Cenat</button>
        </form>
      </div>
      <div>
        <form action="/watch" method="post">
          <input type="hidden" name="channel" value="lacy">
          <button type="submit">Watch Lacy</button>
        </form>
      </div>
      <div>
        <form action="/watch" method="post">
          <input type="hidden" name="channel" value="speed">
          <button type="submit">Watch IShowSpeed</button>
        </form>
      </div>
      <div>
        <form action="/stop_all" method="post">
          <button type="submit" class="danger">Stop All</button>
        </form>
      </div>
    </div>
  </div>

  <div class="card">
    <h3>🔗 On-Demand URL Clipper</h3>
    <form action="/clip_url" method="post">
      <input type="text" name="url" placeholder="Paste YouTube VOD or Twitch Clip URL..." required>
      <button type="submit">Cut Viral Vertical Clip</button>
    </form>
  </div>

  <div class="card">
    <h3>📦 Generated 9:16 Clips Ready For Upload</h3>
    <div class="clip-grid">
      <!-- CLIPS_PLACEHOLDER -->
    </div>
  </div>
</div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    ready_files = sorted([f for f in engine.READY_DIR.glob("*.mp4")], key=lambda x: os.path.getmtime(x), reverse=True)
    cards = []
    for f in ready_files:
        srt = f.with_suffix(".srt")
        srt_link = f'<a href="/download/{srt.name}" style="color:#58a6ff; font-size:12px; margin-top:4px; display:inline-block;">Download Subtitles (.srt)</a>' if srt.exists() else ''
        cards.append(f"""
        <div class="clip-card">
          <video controls preload="metadata">
            <source src="/download/{f.name}" type="video/mp4">
          </video>
          <div style="font-size:12px; color:#8b949e; margin-top:6px;">{f.name}</div>
          <a class="btn" href="/download/{f.name}" download>Download MP4</a>
          {srt_link}
        </div>
        """)
    clips_html = "\n".join(cards) if cards else "<p style='color:#8b949e; font-size:13px;'>No clips generated yet. Start a watcher or clip a URL!</p>"
    return HTMLResponse(content=HTML_DASHBOARD.replace("<!-- CLIPS_PLACEHOLDER -->", clips_html))

@app.post("/watch")
def start_watcher(channel: str = Form(...)):
    channel = channel.lower().strip()
    if channel in ACTIVE_WATCHERS and ACTIVE_WATCHERS[channel].is_alive():
        return HTMLResponse(f"<h3>Watcher for #{channel} is already running!</h3><a href='/'>Back to Dashboard</a>")
    
    watcher = engine.StreamWatcher(channel=channel)
    watcher.start()
    ACTIVE_WATCHERS[channel] = watcher
    return HTMLResponse(f"<h3>Started 24/7 Watcher for #{channel}!</h3><a href='/'>Back to Dashboard</a>")

@app.post("/stop_all")
def stop_all():
    for ch, w in list(ACTIVE_WATCHERS.items()):
        w.stop()
    ACTIVE_WATCHERS.clear()
    return HTMLResponse("<h3>Stopped all active watchers!</h3><a href='/'>Back to Dashboard</a>")

@app.post("/clip_url")
def clip_direct_url(url: str = Form(...), background_tasks: BackgroundTasks = None):
    def run_url_cut(target_url):
        out_raw = engine.REC_DIR / "temp_url.mp4"
        cmd_dl = [
            "yt-dlp",
            target_url,
            "-o", str(out_raw),
            "-f", "best[ext=mp4]/best",
            "--max-filesize", "150M"
        ]
        subprocess.run(cmd_dl)
        if out_raw.exists():
            out_clip = engine.CLIPS_DIR / f"url_clip_{int(os.path.getmtime(out_raw))}.mp4"
            engine.cut_clip_worker(out_raw, 0.0, 35.0, out_clip, layout="crop", require_excited=False)
            try:
                os.remove(out_raw)
            except Exception:
                pass

    threading.Thread(target=run_url_cut, args=(url,), daemon=True).start()
    return HTMLResponse("<h3>Processing URL in background! Refresh in 1-2 minutes.</h3><a href='/'>Back to Dashboard</a>")

@app.get("/download/{filename}")
def download_file(filename: str):
    target = engine.READY_DIR / filename
    if not target.exists():
        target = engine.CLIPS_DIR / filename
    if target.exists():
        media_type = "video/mp4" if filename.endswith(".mp4") else "text/plain"
        return FileResponse(path=str(target), filename=filename, media_type=media_type)
    return JSONResponse(status_code=404, content={"error": "File not found"})

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "active_watchers": list(ACTIVE_WATCHERS.keys()),
        "ready_clips_count": len(list(engine.READY_DIR.glob("*.mp4")))
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
