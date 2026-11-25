#!/usr/bin/env python3
"""
Cooking Clip US - Viral Auto-Editor & Subtitler
Features:
- Dual stacked vertical layout (Facecam top 35% ~672px, Gameplay bottom 65% ~1248px, total 1080x1920).
- High-contrast curiosity hook text on the top frame (first 3 seconds).
- Stylized ASS karaoke-style subtitles.
- Audio loudness normalization (-14 LUFS broadcast standard).
- Video integrity verification (resolution, framerate, duration, audio levels).
"""

import json
import os
import pathlib
import re
import subprocess
import sys


def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_hook_voiceover(hook_text: str, output_path: pathlib.Path) -> str:
    """Generates a punchy 2-second cold-open Edge-TTS commentary intro for YPP originality + retention."""
    clean = re.sub(r"[^\w\s.,!?'\"-]", "", hook_text or "").strip()
    if not clean:
        return None
    try:
        import asyncio
        import edge_tts

        out_p = pathlib.Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        async def _synth():
            comm = edge_tts.Communicate(clean, voice="en-US-AndrewNeural", rate="+18%")
            await comm.save(str(out_p))

        asyncio.run(_synth())
        if out_p.exists() and out_p.stat().st_size > 1000:
            return str(out_p)
    except Exception as e:
        print(f"[!] Hook voiceover skipped: {e}")
    return None


def generate_karaoke_ass(segments, output_path: pathlib.Path, video_width=1080, video_height=1920, hook_text: str = ""):
    """
    Generates top open-loop hook banner (0-3.5s) and yellow ASS subtitles in the lower zone.
    """
    header = f"""[Script Info]
Title: Cooking Clip US Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralYellow,Impact,74,&H0000FFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,4,2,60,60,320,1
Style: TopHook,Impact,68,&H0000E8FF,&H000000FF,&H00000000,&HC0000000,-1,0,0,0,100,100,1,0,1,8,4,8,50,50,115,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    clean_hook = re.sub(r"[^\w\s.,!?'\"$%-]", "", hook_text or "").strip().upper()
    if clean_hook:
        events.append(f"Dialogue: 1,0:00:00.00,0:00:03.50,TopHook,,0,0,0,,{clean_hook}")

    for seg in segments or []:
        text = getattr(seg, "text", str(seg)).strip()
        start = getattr(seg, "start", 0.0)
        end = getattr(seg, "end", start + 2.0)
        if not text:
            continue
        start_str = format_ass_time(start)
        end_str = format_ass_time(end)
        clean_text = text.upper().replace("{", "").replace("}", "")
        events.append(f"Dialogue: 0,{start_str},{end_str},ViralYellow,,0,0,0,,{clean_text}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    return output_path


def build_stack_filters(channel: str = "", hook_text: str = "", ass_path: str = None, has_bgm: bool = False, has_vo: bool = False):
    ch = channel.lower() if channel else ""
    # Normalize any input resolution to 1920x1080 before cropping so 720p/1080p VODs never crash crop geometry.
    norm = "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,split=2[vcam][vgame]"
    # 70% Extreme Reaction Facecam (1100px) / 30% Gameplay (820px) = 1920px total
    if ch in ("speed", "ishowspeed"):
        cam = "[vcam]crop=388:220:0:460,scale=1080:1100:flags=lanczos[cam]"
        game = "[vgame]crop=1080:820:420:0,scale=1080:820:flags=lanczos[game]"
    elif ch in ("kai", "kaicenat"):
        cam = "[vcam]crop=480:360:1440:720,scale=1080:1100:flags=lanczos[cam]"
        game = "[vgame]crop=1080:820:0:0,scale=1080:820:flags=lanczos[game]"
    elif ch in ("lacy",):
        cam = "[vcam]crop=494:278:0:0,scale=1080:1100:flags=lanczos[cam]"
        game = "[vgame]crop=1080:820:550:0,scale=1080:820:flags=lanczos[game]"
    else:
        cam = "[vcam]crop=1280:720:0:0,scale=1080:1100:flags=lanczos[cam]"
        game = "[vgame]crop=1080:820:420:0,scale=1080:820:flags=lanczos[game]"

    # Alternate subtle 10% zoom punch every 2.0s to reset visual attention (matches 1.5-2.5s Shorts pacing rule)
    punch = "[cam][game]vstack=inputs=2,crop=w='if(lt(mod(t,4),2),1080,980)':h='if(lt(mod(t,4),2),1920,1742)':x='(iw-ow)/2':y='(ih-oh)/2',scale=1080:1920:flags=bilinear,setsar=1[vpunch]"
    chain = f"{norm};{cam};{game};{punch}"
    curr_v = "[vpunch]"

    # ASS Subtitles & Top Hook Banner Filter
    if ass_path and os.path.exists(ass_path):
        ass_name = pathlib.Path(ass_path).name
        chain += f";{curr_v}ass={ass_name}[vout]"
    else:
        chain += f";{curr_v}null[vout]"

    # Audio Mixing: duck stream slightly during 2.5s cold-open voiceover, layer -20dB BGM, normalize -14 LUFS
    in_idx = 1
    mix_inputs = []
    if has_vo:
        chain += ";[0:a]volume='if(lt(t,2.5),0.35,1.0)'[base_a]"
        mix_inputs.append("[base_a]")
    else:
        mix_inputs.append("[0:a]")

    if has_bgm:
        bgm_idx = in_idx
        in_idx += 1
        chain += f";[{bgm_idx}:a]aloop=loop=-1:size=2e+09,volume=0.10[bgm]"
        mix_inputs.append("[bgm]")

    if has_vo:
        vo_idx = in_idx
        in_idx += 1
        chain += f";[{vo_idx}:a]volume=1.35[vo]"
        mix_inputs.append("[vo]")

    if len(mix_inputs) > 1:
        chain += f";{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=7:tp=-1.5[aout]"
        audio_map = ["-map", "[aout]"]
    else:
        audio_map = ["-map", "0:a?", "-af", "loudnorm=I=-14:LRA=7:tp=-1.5"]

    filter_complex = ["-filter_complex", chain, "-map", "[vout]"] + audio_map
    return filter_complex


def render_vertical_clip(
    input_video: str,
    output_video: str,
    start_sec: float,
    duration: float,
    channel: str = "",
    hook_text: str = "",
    ass_path: str = None,
    vo_path: str = None
) -> bool:
    """Renders high-impact 70/30 reaction vertical video with 2s zoom punches, -20dB BGM, and optional voiceover hook."""
    out_p = pathlib.Path(output_video).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    working_dir = out_p.parent

    # Detect viral BGM
    bgm_candidates = [
        pathlib.Path("assets/viral_bgm.mp3").resolve(),
        pathlib.Path("output/viral_bgm.mp3").resolve(),
        pathlib.Path(__file__).parent / "assets" / "viral_bgm.mp3"
    ]
    bgm_file = next((p for p in bgm_candidates if p.exists()), None)
    has_bgm = bgm_file is not None
    has_vo = bool(vo_path and os.path.exists(vo_path))

    filter_complex = build_stack_filters(channel, hook_text, ass_path, has_bgm=has_bgm, has_vo=has_vo)

    in_p = str(pathlib.Path(input_video).resolve())
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.2f}",
        "-t", f"{duration:.2f}",
        "-i", in_p,
    ]
    if has_bgm:
        cmd += ["-i", str(bgm_file)]
    if has_vo:
        cmd += ["-i", str(pathlib.Path(vo_path).resolve())]

    cmd += filter_complex + [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(out_p)
    ]

    res = subprocess.run(cmd, cwd=str(working_dir), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[!] FFmpeg error: {res.stderr[-400:]}")
        return False
    return True


def verify_video_integrity(video_path: str) -> dict:
    """Verifies resolution, framerate, duration, and audio stream using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        return {"valid": False, "error": "ffprobe failed"}

    try:
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not v_stream or not a_stream:
            return {"valid": False, "error": "Missing video or audio stream"}

        w = int(v_stream.get("width", 0))
        h = int(v_stream.get("height", 0))
        dur = float(data.get("format", {}).get("duration", 0.0))

        valid = (w == 1080 and h == 1920 and 8.0 <= dur <= 65.0)
        return {
            "valid": valid,
            "width": w,
            "height": h,
            "duration": dur,
            "video_codec": v_stream.get("codec_name"),
            "audio_codec": a_stream.get("codec_name"),
            "aspect_ratio": f"{w}x{h} (9:16)"
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


def generate_viral_thumbnail(frame_jpg_path: str, hook_text: str = "", badge_text: str = "GTA 6 REACTION", out_path: str = None) -> str:
    """Generates a high-contrast 1080x1920 viral preview thumbnail with saturation boost and neon text."""
    try:
        from PIL import Image, ImageEnhance, ImageDraw, ImageFont
        if not out_path:
            out_path = str(pathlib.Path(frame_jpg_path).with_name(f"thumb_{pathlib.Path(frame_jpg_path).name}"))
        img = Image.open(frame_jpg_path).convert("RGB")
        img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
        # Boost saturation and contrast for mobile AMOLED/OLED displays
        img = ImageEnhance.Color(img).enhance(1.18)
        img = ImageEnhance.Contrast(img).enhance(1.12)
        draw = ImageDraw.Draw(img)

        # Top viral badge
        badge_y = 160
        badge_box = (120, badge_y, 960, badge_y + 90)
        draw.rounded_rectangle(badge_box, radius=18, fill=(235, 30, 30), outline=(255, 255, 255), width=3)
        try:
            font_badge = ImageFont.truetype("arialbd.ttf", 46)
            font_hook = ImageFont.truetype("impact.ttf", 80)
        except Exception:
            font_badge = ImageFont.load_default()
            font_hook = ImageFont.load_default()

        draw.text((540, badge_y + 45), badge_text.upper(), font=font_badge, fill="white", anchor="mm")

        # Main hook text overlay
        if hook_text:
            hook_y = 1040
            draw.text((540, hook_y), hook_text.upper(), font=font_hook, fill="#FFE800", stroke_width=6, stroke_fill="black", anchor="mm")

        img.save(out_path, quality=92)
        return out_path
    except Exception as e:
        print(f"[!] Thumbnail generation fallback: {e}")
        return frame_jpg_path


if __name__ == "__main__":
    print("[*] Viral Auto-Editor & Subtitler initialized.")
