---
title: Cooking Clip US
emoji: 🎬
colorFrom: red
colorTo: black
sdk: docker
app_port: 7860
pinned: false
---

# Cooking Clip US - Autonomous Cloud Clipping Studio

Autonomous 24/7 clipping engine deployed on Hugging Face Spaces.
- **Streams**: Monitors Kai Cenat, Lacy, IShowSpeed on Twitch & YouTube.
- **Format**: Auto-detects facecams and stacks 9:16 vertical shorts (TikTok, Reels, Shorts).
- **Subtitles**: Auto-transcribes speech and generates `.srt` files.
- **Port**: Serves web dashboard on port `7860`.

### Deploying to Hugging Face:
1. Create a new Space on [huggingface.co/new-space](https://huggingface.co/new-space)
2. Select **Docker** as Space SDK.
3. In this folder, run:
```bash
git init
git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
git add .
git commit -m "Deploy autonomous clipping engine"
git push -u origin main --force
```
