"""SRT(클로바노트 등) + 오디오 → 파인튜닝용 (음성 클립 ↔ 텍스트) 데이터셋.

클로바노트 SRT는 각 구간에 시작→끝 타임스탬프와 화자 라벨이 들어 있어
forced alignment 없이 곧바로 클립을 잘라 학습 쌍을 만들 수 있습니다.

기본 동작:
  - SRT를 파싱하고, 각 구간을 16kHz mono WAV 클립으로 잘라 dataset/clips/ 에 저장
  - dataset/manifest.jsonl 에 (clip, start, end, dur, speaker, text, 플래그) 기록
  - 30초(--max-seconds) 초과 구간은 over_max=True / needs_review=True 로 표시

--split-long 옵션:
  - 30초 초과 구간을 ffmpeg 무음 감지(silencedetect) 기준으로 ≤max 서브클립으로 분할
  - 텍스트는 시간 비율에 맞춰 근사 배분하고 needs_review=True 표시(추후 교정 권장)

사용 예:
  python tools/srt_to_dataset.py --srt 회의.srt --audio 회의.m4a --out dataset --split-long
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TC = re.compile(
    r"(\d\d):(\d\d):(\d\d)[,.](\d+)\s*-->\s*(\d\d):(\d\d):(\d\d)[,.](\d+)"
)
SPEAKER = re.compile(r"^\s*\[(.*?)\]\s*")


def _to_sec(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: Path):
    """SRT를 [{start, end, speaker, text}] 로 파싱."""
    raw = path.read_text(encoding="utf-8-sig")
    segs = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = TC.search(lines[1])
        if not m:
            continue
        start = _to_sec(*m.group(1, 2, 3, 4))
        end = _to_sec(*m.group(5, 6, 7, 8))
        text = " ".join(lines[2:]).strip()
        sp = SPEAKER.match(text)
        speaker = sp.group(1) if sp else "(미상)"
        text = SPEAKER.sub("", text, count=1).strip()
        if end > start and text:
            segs.append({"start": start, "end": end, "speaker": speaker, "text": text})
    return segs


def detect_silences(audio: Path, start: float, end: float, noise="-30dB", dur=0.4):
    """[start,end] 구간의 무음 (sil_start, sil_end) 목록을 반환."""
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(audio),
        "-af", f"silencedetect=noise={noise}:d={dur}", "-f", "null", "-",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    sils, cur = [], None
    for line in p.stderr.splitlines():
        if "silence_start:" in line:
            cur = float(line.split("silence_start:")[1].strip()) + start
        elif "silence_end:" in line and cur is not None:
            val = line.split("silence_end:")[1].split("|")[0].strip()
            sils.append((cur, float(val) + start))
            cur = None
    return sils


def plan_cuts(start, end, silences, max_sec):
    """무음 중간점을 우선 사용해 각 구간 ≤max_sec 가 되도록 경계 리스트를 반환."""
    mids = sorted((s + e) / 2 for s, e in silences if start < (s + e) / 2 < end)
    points, cur = [start], start
    while end - cur > max_sec:
        limit = cur + max_sec
        cand = [m for m in mids if cur < m <= limit]
        cur = cand[-1] if cand else limit  # 무음 없으면 강제 등분
        points.append(cur)
    points.append(end)
    return points


def split_text_by_ratio(text, boundaries, start, end):
    """텍스트를 공백 토큰 기준으로 각 서브구간 시간 비율에 맞춰 근사 배분."""
    tokens = text.split()
    if not tokens:
        return ["" for _ in range(len(boundaries) - 1)]
    total = end - start
    out, used = [], 0
    for i in range(len(boundaries) - 1):
        frac = (boundaries[i + 1] - boundaries[i]) / total if total else 0
        take = round(len(tokens) * frac)
        if i == len(boundaries) - 2:
            take = len(tokens) - used  # 마지막 구간이 나머지 흡수
        out.append(" ".join(tokens[used : used + take]))
        used += take
    return out


def cut_clip(audio: Path, start: float, end: float, sr: int, out_path: Path):
    """ffmpeg로 [start,end]를 sr Hz mono WAV로 추출."""
    dur = end - start
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(audio), "-t", f"{dur:.3f}",
        "-ar", str(sr), "-ac", "1", "-c:a", "pcm_s16le", str(out_path),
    ]
    subprocess.run(cmd, check=True)


def build(srt_path, audio_path, out_dir, max_sec, sr, split_long):
    srt_path, audio_path, out_dir = Path(srt_path), Path(audio_path), Path(out_dir)
    clips_dir = out_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    segs = parse_srt(srt_path)
    if not segs:
        sys.exit("SRT에서 유효한 구간을 찾지 못했습니다. 파일 형식을 확인하세요.")

    manifest = out_dir / "manifest.jsonl"
    rows, n_clip, n_over, n_split = [], 0, 0, 0

    with manifest.open("w", encoding="utf-8") as mf:
        for bi, seg in enumerate(segs):
            dur = seg["end"] - seg["start"]
            over = dur > max_sec

            if over and split_long:
                n_over += 1
                sils = detect_silences(audio_path, seg["start"], seg["end"])
                bounds = plan_cuts(seg["start"], seg["end"], sils, max_sec)
                texts = split_text_by_ratio(seg["text"], bounds, seg["start"], seg["end"])
                for si in range(len(bounds) - 1):
                    s0, s1 = bounds[si], bounds[si + 1]
                    name = f"{bi:04d}_{si:02d}.wav"
                    cut_clip(audio_path, s0, s1, sr, clips_dir / name)
                    row = {
                        "clip": f"clips/{name}", "start": round(s0, 3), "end": round(s1, 3),
                        "dur": round(s1 - s0, 3), "speaker": seg["speaker"],
                        "text": texts[si], "source_block": bi,
                        "over_max": False, "needs_review": True,  # 분할물은 검수 권장
                    }
                    mf.write(json.dumps(row, ensure_ascii=False) + "\n")
                    rows.append(row)
                    n_clip += 1
                    n_split += 1
            else:
                if over:
                    n_over += 1
                name = f"{bi:04d}.wav"
                cut_clip(audio_path, seg["start"], seg["end"], sr, clips_dir / name)
                row = {
                    "clip": f"clips/{name}", "start": round(seg["start"], 3),
                    "end": round(seg["end"], 3), "dur": round(dur, 3),
                    "speaker": seg["speaker"], "text": seg["text"], "source_block": bi,
                    "over_max": over, "needs_review": over,  # 30초 초과는 검수/분할 권장
                }
                mf.write(json.dumps(row, ensure_ascii=False) + "\n")
                rows.append(row)
                n_clip += 1

    # 요약
    durs = [r["dur"] for r in rows]
    speakers = {}
    for r in rows:
        speakers[r["speaker"]] = speakers.get(r["speaker"], 0) + 1
    summary = [
        f"입력 SRT 구간 수 : {len(segs)}",
        f"생성 클립 수     : {n_clip}  (무음분할 서브클립 {n_split}개 포함)",
        f"30초 초과 원구간 : {n_over}개",
        f"클립 길이 최소/평균/최대 : {min(durs):.1f}s / {sum(durs)/len(durs):.1f}s / {max(durs):.1f}s",
        "화자별 클립 수:",
    ] + [f"  - {sp}: {c}" for sp, c in sorted(speakers.items(), key=lambda x: -x[1])]
    (out_dir / "summary.txt").write_text("\n".join(summary), encoding="utf-8")
    print("\n".join(summary))
    print(f"\n→ manifest: {manifest}")
    print(f"→ clips   : {clips_dir}")


def main():
    ap = argparse.ArgumentParser(description="SRT + 오디오 → (클립↔텍스트) 데이터셋")
    ap.add_argument("--srt", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", default="dataset")
    ap.add_argument("--max-seconds", type=float, default=30.0)
    ap.add_argument("--sample-rate", type=int, default=16000)
    ap.add_argument("--split-long", action="store_true",
                    help="30초 초과 구간을 무음 기준으로 분할(텍스트는 근사 배분, 검수 권장)")
    a = ap.parse_args()
    build(a.srt, a.audio, a.out, a.max_seconds, a.sample_rate, a.split_long)


if __name__ == "__main__":
    main()
