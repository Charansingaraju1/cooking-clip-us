#!/usr/bin/env python3
"""
Cooking Clip US - Headless Linux / Docker Clipping Engine
Pure POSIX, no Windows dependencies, runs headless in Docker on Hugging Face Spaces.
"""

import collections
import datetime
import os
import pathlib
import random
import re
import shutil
import socket
import statistics
import subprocess
import sys
import threading
import time

# Storage path: use /data if persistent storage is attached, otherwise local ./data
DATA_ROOT = pathlib.Path(os.environ.get("STREAMCLIPS_HOME", "/data" if os.path.exists("/data") else "./data"))
REC_DIR = DATA_ROOT / "rec"
CLIPS_DIR = DATA_ROOT / "clips"
READY_DIR = DATA_ROOT / "clips" / "ready"

for p in (REC_DIR, CLIPS_DIR, READY_DIR):
    p.mkdir(parents=True, exist_ok=True)


class SpikeDetector:
    def __init__(self, min_messages=5, multiplier=2.5, window_buckets=18, cooldown_seconds=30):
        self.min_messages = min_messages
        self.multiplier = multiplier
        self.window_buckets = window_buckets
        self.cooldown_seconds = cooldown_seconds
        self.history = collections.deque(maxlen=window_buckets)
        self.last_spike_time = -9999.0

    def record_bucket(self, count, current_time):
        med = statistics.median(self.history) if self.history else 0.0
        threshold = max(float(self.min_messages), self.multiplier * med if med > 0 else float(self.min_messages))
        is_spike = False
        time_since_last = current_time - self.last_spike_time
        if count >= self.min_messages and (med == 0 or count >= self.multiplier * med):
            if time_since_last >= self.cooldown_seconds:
                is_spike = True
                self.last_spike_time = current_time
        self.history.append(count)
        return is_spike, count, med, threshold


class TwitchIRC(threading.Thread):
    def __init__(self, channel, on_message, host="irc.chat.twitch.tv", port=6667):
        super().__init__(daemon=True)
        self.channel = channel.lower().lstrip("#")
        self.on_message = on_message
        self.host = host
        self.port = port
        self.running = True
        self.sock = None

    def run(self):
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(10.0)
                self.sock.connect((self.host, self.port))
                nick = f"justinfan{random.randint(10000, 99999)}"
                self.sock.sendall(f"NICK {nick}\r\n".encode("utf-8"))
                self.sock.sendall(f"JOIN #{self.channel}\r\n".encode("utf-8"))

                buffer = ""
                while self.running:
                    try:
                        data = self.sock.recv(4096).decode("utf-8", errors="ignore")
                        if not data:
                            break
                        buffer += data
                        while "\r\n" in buffer:
                            line, buffer = buffer.split("\r\n", 1)
                            if line.startswith("PING"):
                                self.sock.sendall(b"PONG :tmi.twitch.tv\r\n")
                            elif f"PRIVMSG #{self.channel}" in line:
                                self.on_message()
                    except socket.timeout:
                        continue
            except Exception:
                if self.running:
                    time.sleep(2)
            finally:
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception:
                        pass

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


def build_filters(speed=1.0, layout="crop", channel=""):
    if layout == "stack":
        ch = channel.lower()
        if ch in ("speed", "ishowspeed"):
            cam = "[0:v]crop=388:220:0:460,scale=1080:720:flags=lanczos[cam]"
            game = "[0:v]crop=1080:1080:420:0,scale=1080:1200:flags=lanczos[game]"
        elif ch in ("kai", "kaicenat"):
            cam = "[0:v]crop=480:360:1440:720,scale=1080:720:flags=lanczos[cam]"
            game = "[0:v]crop=1080:1080:0:0,scale=1080:1200:flags=lanczos[game]"
        else:
            cam = "[0:v]crop=494:278:0:0,scale=1080:720:flags=lanczos[cam]"
            game = "[0:v]crop=1080:1080:550:0,scale=1080:1200:flags=lanczos[game]"
        stack = f"{cam};{game};[cam][game]vstack=inputs=2"
        if speed != 1.0:
            stack += f"[stk];[stk]setpts=PTS/{speed}[outv]"
        else:
            stack += "[outv]"
        filter_args = ["-filter_complex", stack, "-map", "[outv]", "-map", "0:a?"]
    else:
        vf = "crop=trunc(ih*9/16/2)*2:ih:(iw-ow)/2:0"
        if speed != 1.0:
            vf += f",setpts=PTS/{speed}"
        filter_args = ["-vf", vf]

    af = ["-af", f"atempo={speed}"] if speed != 1.0 else []
    return filter_args, af


def check_excitement(clip_path):
    cmd = ["ffmpeg", "-i", str(clip_path), "-af", "volumedetect", "-f", "null", "-"]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
    max_v = -99.0
    mean_v = -99.0
    m_max = re.search(r"max_volume:\s*([-0-9.]+)\s*dB", res.stderr)
    m_mean = re.search(r"mean_volume:\s*([-0-9.]+)\s*dB", res.stderr)
    if m_max:
        max_v = float(m_max.group(1))
    if m_mean:
        mean_v = float(m_mean.group(1))
    is_excited = (max_v >= -3.5) and (mean_v >= -25.0)
    return is_excited, max_v, mean_v


def generate_subtitles(clip_path, output_dir, model_name="base"):
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(clip_path), beam_size=5)
        srt_file = pathlib.Path(output_dir) / f"{pathlib.Path(clip_path).stem}.srt"
        with open(srt_file, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                start_hms = str(datetime.timedelta(seconds=seg.start))[:11].replace(".", ",")
                end_hms = str(datetime.timedelta(seconds=seg.end))[:11].replace(".", ",")
                f.write(f"{i}\n{start_hms} --> {end_hms}\n{seg.text.strip()}\n\n")
        return srt_file
    except Exception as e:
        print(f"[!] Whisper subtitle generation warning: {e}")
        return None


def cut_clip_worker(rec_file, clip_start, duration, clip_out, speed=1.0, layout="crop", require_excited=True, channel=""):
    filter_args, af = build_filters(speed, layout, channel=channel)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{clip_start:.2f}",
        "-t", f"{duration:.2f}",
        "-i", str(rec_file),
    ] + filter_args + af + [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        str(clip_out)
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        print(f"[!] ffmpeg failed: {res.stderr.decode('utf-8', errors='ignore')[-300:]}")
        return None

    if require_excited:
        is_excited, max_v, mean_v = check_excitement(clip_out)
        if not is_excited:
            print(f"[-] Discarded low-energy clip (peak: {max_v:.1f} dB)")
            try:
                os.remove(clip_out)
            except Exception:
                pass
            return None
        print(f"[🔥 VIRAL SPIKE CONFIRMED] Peak: {max_v:.1f} dB, Mean: {mean_v:.1f} dB")

    # Generate subtitles
    generate_subtitles(clip_out, READY_DIR)

    # Save numbered copy to ready directory
    existing = [f for f in os.listdir(READY_DIR) if f.endswith(".mp4") and f[:-4].isdigit()]
    next_num = len(existing) + 1
    ready_file = READY_DIR / f"{next_num}.mp4"
    shutil.copy2(clip_out, ready_file)
    print(f"[✅ VIRAL CLIP READY] Saved as {ready_file}")
    return ready_file


class StreamWatcher(threading.Thread):
    def __init__(self, channel, min_msgs=5, multiplier=2.5, layout="auto"):
        super().__init__(daemon=True)
        self.channel = channel.lower()
        if self.channel == "speed":
            self.channel = "ishowspeed"
        elif self.channel == "kai":
            self.channel = "kaicenat"

        self.min_msgs = min_msgs
        self.multiplier = multiplier
        self.layout = ("stack" if self.channel in ("lacy", "kaicenat", "ishowspeed") else "crop") if layout == "auto" else layout
        self.running = True
        self.stream_proc = None
        self.irc = None
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.rec_file = REC_DIR / f"{self.channel}_{self.session_id}.ts"

    def run(self):
        print(f"[*] Starting headless watcher for #{self.channel} (Layout: {self.layout})...")
        cmd = [
            sys.executable, "-m", "yt_dlp",
            f"https://twitch.tv/{self.channel}",
            "-o", str(self.rec_file),
            "--no-part", "-q"
        ]
        self.stream_proc = subprocess.Popen(cmd)
        t_start = time.time()

        msg_counter = 0
        lock = threading.Lock()

        def on_msg():
            nonlocal msg_counter
            with lock:
                msg_counter += 1

        self.irc = TwitchIRC(self.channel, on_msg)
        self.irc.start()
        detector = SpikeDetector(min_messages=self.min_msgs, multiplier=self.multiplier)

        try:
            while self.running:
                time.sleep(10)
                if self.stream_proc.poll() is not None:
                    print(f"[*] Stream process ended for #{self.channel}")
                    break
                with lock:
                    cnt = msg_counter
                    msg_counter = 0
                elapsed = time.time() - t_start
                is_spike, cnt, med, thresh = detector.record_bucket(cnt, elapsed)
                if is_spike:
                    print(f"[🔥 SPIKE in #{self.channel}] {cnt} msgs (thresh: {thresh:.1f})")
                    clip_start = max(0.0, elapsed - 20.0)
                    clip_out = CLIPS_DIR / f"{self.channel}_{self.session_id}_{int(elapsed)}s.mp4"

                    def do_cut(s_start, c_out):
                        time.sleep(25)  # buffer broadcast latency
                        cut_clip_worker(self.rec_file, s_start, 30.0, c_out, layout=self.layout, channel=self.channel)

                    threading.Thread(target=do_cut, args=(clip_start, clip_out), daemon=True).start()
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.irc:
            self.irc.stop()
        if self.stream_proc and self.stream_proc.poll() is None:
            self.stream_proc.terminate()
            try:
                self.stream_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.stream_proc.kill()
