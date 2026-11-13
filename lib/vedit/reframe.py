"""EXPERIMENTAL: face tracking + active-speaker crop_x keyframes (needs OpenCV)."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

from . import edl as edlmod
from .probe import probe
from .util import VeditError, ffmpeg_path, info, require_module

YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
    "face_detection_yunet_2023mar.onnx"
)
SAMPLE_FPS = 3.0
SCAN_W = 640
MOUTH_ROI = (32, 16)  # fixed size the mouth crop is resized to before differencing


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    d = Path(base) / "vedit" / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_yunet_model() -> str | None:
    p = cache_dir() / "face_detection_yunet_2023mar.onnx"
    if p.exists() and p.stat().st_size > 10000:
        return str(p)
    info("Baixando o modelo de rostos YuNet (opencv_zoo, ~230 KB) para o cache local ...")
    try:
        with urllib.request.urlopen(YUNET_URL, timeout=60) as r:
            data = r.read()
        p.write_bytes(data)
        return str(p)
    except Exception as exc:  # noqa: BLE001
        info(f"Não consegui baixar o YuNet ({exc}). Usando Haar cascade (menos preciso).")
        return None


class Detector:
    def __init__(self, cv2, w: int, h: int):
        self.cv2, self.w, self.h = cv2, w, h
        self.yunet = None
        model = get_yunet_model()
        if model and hasattr(cv2, "FaceDetectorYN"):
            self.yunet = cv2.FaceDetectorYN.create(model, "", (w, h), 0.6, 0.3, 5000)
        else:
            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.haar = cv2.CascadeClassifier(path)

    def detect(self, bgr) -> list[tuple[float, float, float, float]]:
        """Return faces as (x, y, w, h) in pixels."""
        if self.yunet is not None:
            self.yunet.setInputSize((self.w, self.h))
            _, faces = self.yunet.detect(bgr)
            if faces is None:
                return []
            return [(float(f[0]), float(f[1]), float(f[2]), float(f[3])) for f in faces]
        gray = self.cv2.cvtColor(bgr, self.cv2.COLOR_BGR2GRAY)
        found = self.haar.detectMultiScale(gray, 1.15, 5, minSize=(self.w // 20, self.w // 20))
        return [tuple(map(float, f)) for f in found]


def read_frames(np, source, start, dur, w, h):
    cmd = [
        ffmpeg_path(), "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{start:.4f}",
        "-t", f"{dur:.4f}", "-i", str(source), "-an",
        "-vf", f"fps={SAMPLE_FPS},scale={w}:{h}", "-pix_fmt", "bgr24", "-f", "rawvideo", "-",
    ]  # fmt: skip
    p = subprocess.run(cmd, capture_output=True)
    size = w * h * 3
    n = len(p.stdout) // size
    return [np.frombuffer(p.stdout[i * size : (i + 1) * size], np.uint8).reshape(h, w, 3) for i in range(n)]


def audio_energy(np, source, start, dur, n):
    cmd = [
        ffmpeg_path(), "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{start:.4f}",
        "-t", f"{dur:.4f}", "-i", str(source), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-",
    ]  # fmt: skip
    raw = subprocess.run(cmd, capture_output=True).stdout
    a = np.frombuffer(raw[: len(raw) // 2 * 2], np.int16).astype(np.float32) / 32768.0
    out = np.zeros(n)
    for i in range(n):
        c = int((i / SAMPLE_FPS) * 8000)
        seg = a[max(c - 1333, 0) : c + 1333]
        out[i] = float(np.sqrt((seg**2).mean())) if len(seg) else 0.0
    return out


def build_tracks(frames_faces, w, max_gap=3, dist=0.15):
    """Track faces by nearest centre. Returns list of {frame_idx: (cx_fraction, box)}."""
    tracks: list[dict] = []
    for fi, faces in enumerate(frames_faces):
        used = set()
        for box in faces:
            cx = (box[0] + box[2] / 2) / w
            best, bd = None, dist
            for ti, t in enumerate(tracks):
                if ti in used:
                    continue
                last = max(t)
                if fi - last > max_gap:
                    continue
                d = abs(t[last][0] - cx)
                if d < bd:
                    best, bd = ti, d
            if best is None:
                tracks.append({})
                best = len(tracks) - 1
            used.add(best)
            tracks[best][fi] = (cx, box)
    return tracks


def merge_tracks(tracks, close=0.08):
    """Merge fragmented tracks with close mean x and no overlapping frames."""
    tracks = [t for t in tracks if t]
    merged = True
    while merged:
        merged = False
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                a, b = tracks[i], tracks[j]
                ma = sum(v[0] for v in a.values()) / len(a)
                mb = sum(v[0] for v in b.values()) / len(b)
                if abs(ma - mb) < close and not (set(a) & set(b)):
                    a.update(b)
                    del tracks[j]
                    merged = True
                    break
            if merged:
                break
    return tracks


def mouth_activity(cv2, np, frames, track):
    """Mean abs difference of the mouth ROI between consecutive sampled frames."""
    act = np.zeros(len(frames))
    prev, prev_i = None, None
    for i in sorted(track):
        x, y, fw, fh = track[i][1]
        H, W = frames[i].shape[:2]
        x0, x1 = max(int(x + fw * 0.2), 0), min(int(x + fw * 0.8), W)
        y0, y1 = max(int(y + fh * 0.62), 0), min(int(y + fh * 0.98), H)
        if x1 - x0 < 2 or y1 - y0 < 2:
            prev = None
            continue
        roi = cv2.cvtColor(frames[i][y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        roi = cv2.resize(roi, MOUTH_ROI).astype(np.float32)
        if prev is not None and prev_i == i - 1:
            act[i] = float(np.abs(roi - prev).mean())
        prev, prev_i = roi, i
    return act


def pick_speaker(np, acts, energy, win=9, margin=0.15, hold=2):
    """Active speaker per sample by activity/energy correlation, with hysteresis."""
    n = len(energy)
    if len(acts) == 1:
        return [0] * n
    chosen, cur, pending, pend_n = [], 0, None, 0
    for i in range(n):
        lo, hi = max(0, i - win + 1), i + 1
        scores = []
        for a in acts:
            x, y = a[lo:hi], energy[lo:hi]
            if len(x) < 3 or x.std() < 1e-6 or y.std() < 1e-9:
                scores.append(0.0)
            else:
                scores.append(float(np.corrcoef(x, y)[0, 1]))
        best = int(np.argmax(scores))
        if best != cur and scores[best] > scores[cur] + margin:
            if pending == best:
                pend_n += 1
            else:
                pending, pend_n = best, 1
            if pend_n >= hold:
                cur, pending, pend_n = best, None, 0
        else:
            pending, pend_n = None, 0
        chosen.append(cur)
    return chosen


def smooth_keyframes(xs, alpha=0.35, dead=0.04, min_gap=1.5):
    """EMA smoothing restarted per clip, then sparse piecewise-constant keyframes."""
    if not xs:
        return [{"t": 0.0, "x": 0.5}]
    s = xs[0]
    kfs = [{"t": 0.0, "x": round(s, 3)}]
    last_x, last_t = s, 0.0
    for i, x in enumerate(xs):
        s = alpha * x + (1 - alpha) * s
        t = i / SAMPLE_FPS
        if abs(s - last_x) > dead and t - last_t >= min_gap:
            kfs.append({"t": round(t, 2), "x": round(s, 3)})
            last_x, last_t = s, t
    return kfs


def reframe(edl_path, write: bool = False) -> dict:
    cv2 = require_module("cv2", "opencv-python", "o reframe automático")
    np = require_module("numpy", "numpy", "o reframe automático")
    edl = edlmod.load_edl(edl_path)
    fps = edlmod.resolve_fps(edl, edl_path)
    tl = edlmod.timeline(edl, fps)
    sw = SCAN_W
    detectors: dict = {}
    metas: dict = {}
    result = []
    for c in tl:
        if edlmod.is_image(edlmod.source_key(edl, c["clip"])):
            result.append({"id": c["id"], "crop_x": 0.5, "faces": 0})
            continue
        source = edlmod.resolve_source(edl, edl_path, c["clip"])
        if source not in metas:
            metas[source] = probe(source, audio_analysis=False)
        W, H = metas[source]["width"], metas[source]["height"]
        sh = max(2, int(round(SCAN_W * H / W)))
        if (sw, sh) not in detectors:
            detectors[(sw, sh)] = Detector(cv2, sw, sh)
        det = detectors[(sw, sh)]
        # Scan the source window (before speed); keyframe times are converted to output time below.
        frames = read_frames(np, source, c["in"], c["src_duration"], sw, sh)
        n = len(frames)
        if n == 0:
            result.append({"id": c["id"], "crop_x": 0.5, "faces": 0})
            continue
        faces = [det.detect(f) for f in frames]
        tracks = merge_tracks(build_tracks(faces, sw))
        if not tracks:
            result.append({"id": c["id"], "crop_x": 0.5, "faces": 0})
            continue
        energy = audio_energy(np, source, c["in"], c["src_duration"], n)
        acts = [mouth_activity(cv2, np, frames, t) for t in tracks]
        who = pick_speaker(np, acts, energy)
        xs = []
        for i in range(n):
            t = tracks[who[i]]
            near = i if i in t else min(t, key=lambda k, i=i: abs(k - i))
            xs.append(t[near][0])
        kfs = smooth_keyframes(xs)
        if c["speed"] != 1.0:
            kfs = [{"t": round(k["t"] / c["speed"], 3), "x": k["x"]} for k in kfs]
        result.append({"id": c["id"], "crop_x": kfs if len(kfs) > 1 else kfs[0]["x"], "faces": len(tracks)})
    if write:
        for c, r in zip(edl["clips"], result, strict=True):
            c["crop_x"] = r["crop_x"]
        Path(edl_path).write_text(json.dumps(edl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not any(r["faces"] for r in result):
        info("Nenhum rosto detectado; crop_x ficou em 0.5.")
    if not result:
        raise VeditError("Nada para reenquadrar.")
    return {"written": write, "clips": result}
