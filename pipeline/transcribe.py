"""faster-whisper 로컬 전사 (+ 용어집 기반 vocabulary biasing).

두 테스트 보고서에서 검증된 안정 경로. 무한 반복 루프 없이 38분 회의를 완주.
medium은 Mac CPU에서, large-v3는 GPU(DGX Spark)에서 권장.
"""
from datetime import timedelta
from pathlib import Path


def load_glossary_prompt(glossary_path) -> str | None:
    """용어집을 initial_prompt 문장으로 변환. 없으면 None."""
    p = Path(glossary_path)
    if not p.exists():
        return None
    terms = [
        ln.strip()
        for ln in p.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    if not terms:
        return None
    # 모델에게 등장 가능 용어를 미리 노출 → 고유명사 표기 확률↑
    return "다음 용어가 등장할 수 있음: " + ", ".join(terms) + "."


def _fmt_ts(seconds: float) -> str:
    td = timedelta(seconds=max(0.0, seconds))
    total = int(td.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    ms = int((seconds - total) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe(
    audio_path,
    *,
    model_size: str,
    compute_type: str,
    device: str,
    language: str | None,
    glossary_path=None,
    on_progress=None,
):
    """오디오를 전사하여 segment 리스트와 info를 반환.

    on_progress(current_seconds, total_seconds) 콜백으로 진행률 표시 가능.
    """
    from faster_whisper import WhisperModel  # 무거운 의존성 → 지연 import

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    initial_prompt = load_glossary_prompt(glossary_path) if glossary_path else None

    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        initial_prompt=initial_prompt,
        vad_filter=True,      # 침묵 제거 → 환각/반복 완화
        beam_size=5,
    )

    segments = []
    for seg in segments_iter:
        segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
        if on_progress:
            on_progress(seg.end, getattr(info, "duration", 0) or 0)
    return segments, info


def to_srt(segments) -> str:
    blocks = []
    for i, s in enumerate(segments, 1):
        blocks.append(f"{i}\n{_fmt_ts(s['start'])} --> {_fmt_ts(s['end'])}\n{s['text']}\n")
    return "\n".join(blocks)


def to_txt(segments) -> str:
    return "\n".join(s["text"] for s in segments)
