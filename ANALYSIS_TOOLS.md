# 🎬 Top Open-Source GitHub Repositories for Shorts Analytics & Clipping

This document details the leading open-source repositories and AI architectures used across the developer community for YouTube Shorts clipping, virality analytics, and retention optimization, alongside our integrated `analytics_engine.py`.

---

## 1. Leading Open-Source Clipping & Analytics Repositories

### A. **OpenShorts** (`mutonby/openshorts`)
- **Repository:** [github.com/mutonby/openshorts](https://github.com/mutonby/openshorts)
- **Architecture:** Local-first & Dockerized AI video clipper alternative to Opus Clip and Klap.
- **Key Capabilities:**
  - LLM-powered highlight and hook detection from stream audio transcripts.
  - Active speaker face-tracking and dynamic 9:16 re-framing.
  - Karaoke-style word-level animated subtitles with custom ASS/SRT formatting.
  - Native Model Context Protocol (MCP) support for AI agent integrations.

### B. **Clipper** (`Achbi/Clipper`)
- **Repository:** [github.com/Achbi/Clipper](https://github.com/Achbi/Clipper)
- **Architecture:** Production-ready full-stack automation platform (FastAPI + Next.js + Serverless GPU via Modal).
- **Key Capabilities:**
  - Audio transcription via `whisperX` with word-level timestamps.
  - Light-Rotation Active Speaker Detection (`LR-ASD`) for smart face centering.
  - Viral potential scoring algorithm based on energy shifts and emotional peaks.

### C. **AI-Youtube-Shorts-Generator** (`SamurAIGPT/AI-Youtube-Shorts-Generator`)
- **Repository:** [github.com/SamurAIGPT/AI-Youtube-Shorts-Generator](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator)
- **Architecture:** Python + FFmpeg pipeline that parses full YouTube streams via `yt-dlp` and auto-chops top moments.
- **Key Capabilities:**
  - Automatic download and segmentation of high-viewership segments.
  - Sentiment analysis on video transcripts to find funny or intense moments.
  - Vertical stacking filter graphs in FFmpeg (similar to our 70/30 layout).

### D. **yt-dlp** (`yt-dlp/yt-dlp`)
- **Repository:** [github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Architecture:** The industry-standard media and metadata extraction engine.
- **Key Capabilities:**
  - Bypasses regional and client player restrictions (e.g. Android client emulation).
  - Pulls live chapter marks, heatmaps (most-replayed segments), and full stream metadata.

---

## 2. Our Integrated Solution: `analytics_engine.py` & `channel_growth_agent.py`

In this project, we have integrated these concepts into a zero-dependency, cloud-native architecture:

1. **Live Analytics Tracking (`analytics_engine.py`)**:
   - Queries public YouTube metadata and view counts without requiring paid API keys.
   - Computes catalog view velocity, streamer distribution (Lacy vs. Kai), and average views per clip.
   - Connected directly to Telegram: type `/analyze` to run an on-demand audit.

2. **70/30 Reaction Hook Editor (`editor.py`)**:
   - 1100px streamer reaction / 820px gameplay stack.
   - Ducked Phonk background audio (-15dB) with high-energy sub-bass.
   - Sub-22-second clip duration ceiling to force 100%+ Average Percentage Viewed (APV).

3. **US Cloud Publisher (`.github/workflows/viral_pipeline.yml`)**:
   - Executes strictly on US Azure runners via GitHub Actions.
   - Prevents regional throttling and Indian IP cold-start issues.
