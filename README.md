# Cooked Clips US — Automated Original Shorts Engine

100% serverless YouTube Shorts engine designed for YPP compliance (original voiceover, kinetic captions, smooth motion visuals, zero third-party stream clipping).

## Architecture (Zero Laptop Power, $0.00/mo)
- **Cloudflare Worker ([worker.js](worker.js))**: 24/7 Telegram command center (`@Cookedclip_bot`) + exact daily crons (`19:00` & `23:00 UTC`).
- **GitHub Actions ([viral_pipeline.yml](.github/workflows/viral_pipeline.yml))**: US Azure cloud renderer & publisher.
- **Shorts Renderer ([editor.py](editor.py))**: Wikipedia HD art + Ken Burns crop motion + top hook banner + animated countdown progress bar + `Edge-TTS` WordBoundary synced captions + `-20 dB` BGM.
- **Publisher ([youtube_publisher.py](youtube_publisher.py))**: Headless YouTube Data API v3 upload with OAuth auto-refresh.
- **Analytics ([analytics_engine.py](analytics_engine.py))**: Live public Short discovery & view counter.
