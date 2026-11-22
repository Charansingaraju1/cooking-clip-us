#!/usr/bin/env python3
import json
import os
import pathlib
import re
import subprocess
import sys

BASE_DIR = pathlib.Path(r"C:\Users\chara\OneDrive\Desktop\Stream Clippers\hf_space")
OUT_DIR = BASE_DIR / "output"
READY_DIR = BASE_DIR / "clips" / "ready"
READY_DIR.mkdir(parents=True, exist_ok=True)

def parse_time(ts_str):
    # '00:32:18,630' -> float seconds
    h, m, s_ms = ts_str.strip().split(':')
    s, ms = s_ms.replace('.', ',').split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

def format_ass_time(sec):
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass(srt_path, base_sec, max_dur, hook_text, output_ass_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = content.strip().split('\n\n')
    header = """[Script Info]
Title: Cooking Clip US
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookStyle,Arial,64,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,4,8,40,40,120,1
Style: ViralYellow,Impact,76,&H0000FFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,4,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    # Hook line on top for first 4 seconds
    events.append(f"Dialogue: 0,0:00:00.00,0:00:04.00,HookStyle,,0,0,0,,{hook_text}")

    seen = set()
    for b in blocks:
        lines = [l.strip() for l in b.split('\n') if l.strip()]
        if len(lines) >= 3:
            tm = re.match(r'(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)', lines[1])
            if tm:
                s_sec = parse_time(tm.group(1))
                e_sec = parse_time(tm.group(2))
                if s_sec >= base_sec - 1.0 and s_sec <= base_sec + max_dur:
                    rel_s = max(0.0, s_sec - base_sec)
                    rel_e = min(max_dur, e_sec - base_sec)
                    if rel_e <= rel_s:
                        continue
                    text_line = ' '.join(lines[2:]).strip()
                    # Clean text
                    clean = re.sub(r'<[^>]+>', '', text_line)
                    clean = re.sub(r'\[.*?\]', '', clean)
                    clean = clean.replace('>>', '').strip()
                    clean = clean.upper().replace('{', '').replace('}', '')
                    if not clean or clean in seen:
                        continue
                    seen.add(clean)
                    events.append(f"Dialogue: 0,{format_ass_time(rel_s)},{format_ass_time(rel_e)},ViralYellow,,0,0,0,,{clean}")

    with open(output_ass_path, 'w', encoding='utf-8') as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"[+] Wrote ASS to {output_ass_path} ({len(events)} events)")

def render_clip(input_mp4, ass_file, filter_complex, output_mp4):
    print(f"\n[*] Rendering {output_mp4.name}...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_mp4),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "0:a?",
        "-af", "loudnorm=I=-14:LRA=7:tp=-1.5",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_mp4)
    ]
    # Run in OUT_DIR so relative ass works
    res = subprocess.run(cmd, cwd=str(OUT_DIR), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[!] FFmpeg error on {output_mp4.name}: {res.stderr[-400:]}")
        return False
    print(f"[✓] Rendered: {output_mp4} ({output_mp4.stat().st_size / (1024*1024):.2f} MB)")
    return True

def verify_file(p):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(p)]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        return False, "ffprobe failed"
    data = json.loads(res.stdout)
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v or not a:
        return False, "Missing audio or video stream"
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    dur = float(data.get("format", {}).get("duration", 0.0))
    return (w == 1080 and h == 1920 and dur >= 15.0), f"{w}x{h}, {dur:.1f}s, v={v.get('codec_name')}, a={a.get('codec_name')}"

def main():
    # 1. Clip 1: Kai Cenat GTA 6 Shootout
    ass_kai_1 = OUT_DIR / "subs_kai_1.ass"
    generate_ass(
        srt_path=r"C:\Users\chara\AppData\Local\Programs\antigravity\output\7mjhCbFi9Wk.en.srt",
        base_sec=1938.0,
        max_dur=37.0,
        hook_text="KAI CENAT FIRST GTA 6 SHOOTOUT 😱🔫",
        output_ass_path=ass_kai_1
    )
    filter_kai_1 = "[0:v]crop=392:204:0:324,scale=1080:672:flags=lanczos[cam];[0:v]crop=1080:1080:700:0,scale=1080:1248:flags=lanczos[game];[cam][game]vstack=inputs=2[vstacked];[vstacked]ass=subs_kai_1.ass[vout]"
    out_kai_1 = READY_DIR / "NEW_1_KAI_GTA6_SHOOTOUT.mp4"
    render_clip(OUT_DIR / "test_kai_mission.mp4", "subs_kai_1.ass", filter_kai_1, out_kai_1)

    # 2. Clip 2: Kai Cenat IRL GTA 6 Getaway
    ass_kai_2 = OUT_DIR / "subs_kai_2.ass"
    generate_ass(
        srt_path=str(OUT_DIR / "ETWvry6twFA.en.srt"),
        base_sec=508.0,
        max_dur=37.0,
        hook_text="KAI CENAT REAL LIFE GTA 6 GETAWAY 🚗💨",
        output_ass_path=ass_kai_2
    )
    filter_kai_2 = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];[0:v]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[vstacked];[vstacked]ass=subs_kai_2.ass[vout]"
    out_kai_2 = READY_DIR / "NEW_2_KAI_GTA6_IRL_GETAWAY.mp4"
    render_clip(OUT_DIR / "test_kai_sec.mp4", "subs_kai_2.ass", filter_kai_2, out_kai_2)

    # 3. Clip 3: Lacy GTA 6 Cops Foot Chase
    ass_lacy = OUT_DIR / "subs_lacy.ass"
    generate_ass(
        srt_path=str(OUT_DIR / "NxgYtzq_n70.en.srt"),
        base_sec=315.0,
        max_dur=37.0,
        hook_text="LACY GETS CHASED BY COPS ON FOOT 😭🏃",
        output_ass_path=ass_lacy
    )
    filter_lacy = "[0:v]crop=494:278:0:0,scale=1080:672:flags=lanczos[cam];[0:v]crop=1080:1080:550:0,scale=1080:1248:flags=lanczos[game];[cam][game]vstack=inputs=2[vstacked];[vstacked]ass=subs_lacy.ass[vout]"
    out_lacy = READY_DIR / "NEW_3_LACY_GTA6_COPS_CHASE.mp4"
    render_clip(OUT_DIR / "test_lacy_sec.mp4", "subs_lacy.ass", filter_lacy, out_lacy)

    # Verify all
    print("\n" + "="*50)
    print("VERIFYING OUTPUT INTEGRITY")
    print("="*50)
    for p in [out_kai_1, out_kai_2, out_lacy]:
        ok, msg = verify_file(p)
        status = "PASSED" if ok else "FAILED"
        print(f"[{status}] {p.name}: {msg}")

if __name__ == "__main__":
    main()
