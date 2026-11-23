import pathlib
import re
import subprocess
import json

BASE_DIR = pathlib.Path(r"C:\Users\chara\OneDrive\Desktop\Stream Clippers\hf_space")
OUT_DIR = BASE_DIR / "output"
READY_DIR = BASE_DIR / "clips" / "ready"
READY_DIR.mkdir(parents=True, exist_ok=True)

ass_file = OUT_DIR / "subs_kai_stripclub.ass"

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
events.append("Dialogue: 0,0:00:00.00,0:00:04.00,HookStyle,,0,0,0,,KAI FOUND THE GTA 6 STRIP CLUB! 😭🔥")

base_sec = 310.0
end_sec = 355.0

def parse_time(ts):
    h, m, s_ms = ts.strip().split(':')
    s, ms = s_ms.replace('.', ',').split(',')
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0

def fts(t):
    return f"{int(t//3600)}:{int((t%3600)//60):02d}:{int(t%60):02d}.{int(round((t-int(t))*100)):02d}"

with open(OUT_DIR / "kai_stripclub_sub.en.srt", encoding="utf-8") as f:
    text = f.read()

blocks = text.strip().split("\n\n")
prev = ""
for b in blocks:
    lines = [l.strip() for l in b.split("\n") if l.strip()]
    if len(lines) >= 3:
        m = re.match(r"(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)", lines[1])
        if m:
            s_s = parse_time(m.group(1))
            e_s = parse_time(m.group(2))
            if base_sec <= s_s < end_sec:
                content = " ".join(lines[2:])
                clean = re.sub(r"<[^>]+>", "", content)
                clean = clean.replace("&gt;", "").replace("&lt;", "").replace(">>", "").strip().upper()
                if clean and clean != prev and not clean.startswith("YOU PAY ME"):
                    rs = max(0.0, s_s - base_sec)
                    re_t = min(44.0, e_s - base_sec)
                    if re_t > rs + 0.3:
                        events.append(f"Dialogue: 0,{fts(rs)},{fts(re_t)},ViralYellow,,0,0,0,,{clean}")
                        prev = clean

with open(ass_file, "w", encoding="utf-8") as f:
    f.write(header + "\n".join(events) + "\n")
print(f"[+] Wrote {len(events)} events to {ass_file.name}")

# Crop filter: Kai facecam on bottom right: crop=480:360:1440:720 -> scale 1080:672
# Gameplay: crop 1080x1080:0:0 -> scale 1080:1248
filter_kai = (
    "[0:v]crop=480:360:1440:720,scale=1080:672:flags=lanczos[cam];"
    "[0:v]crop=1080:1080:0:0,scale=1080:1248:flags=lanczos[game];"
    "[cam][game]vstack=inputs=2[vstacked];"
    f"[vstacked]ass={ass_file.name}[vout]"
)

out_mp4 = READY_DIR / "NEW_5_KAI_GTA6_STRIPCLUB.mp4"

cmd = [
    "ffmpeg", "-y",
    "-i", str(OUT_DIR / "raw_kai_stripclub.mp4"),
    "-filter_complex", filter_kai,
    "-map", "[vout]",
    "-map", "0:a?",
    "-af", "loudnorm=I=-14:LRA=7:tp=-1.5",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "20",
    "-c:a", "aac",
    "-b:a", "192k",
    str(out_mp4)
]

print(f"[*] Rendering {out_mp4.name}...")
res = subprocess.run(cmd, cwd=str(OUT_DIR), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if res.returncode != 0:
    print("[!] FFmpeg error:", res.stderr[-500:])
    exit(1)

print(f"[SUCCESS] Rendered {out_mp4.name}: {out_mp4.stat().st_size / (1024*1024):.2f} MB")
