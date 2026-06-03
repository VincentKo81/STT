"""faster-whisper 로컬 전사 (+ 용어집 기반 vocabulary biasing).

두 테스트 보고서에서 검증된 안정 경로. 무한 반복 루프 없이 38분 회의를 완주.
medium은 Mac CPU에서, large-v3는 GPU(DGX Spark)에서 권장.
"""
import os
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


def resolve_model(model_size: str, device: str):
    """('auto' 모델 + 디바이스) → 실제 사용할 (model_size, effective_device) 결정.

    검증 결과(5.2분 회의, 정답 대비 CER):
      medium   CER 27.5% / RTF 0.12
      large-v3 CER 13.1% / RTF 0.24   ← 오류율 절반, GPU에선 속도 페널티 없음
    따라서 GPU 사용 가능 시 large-v3, CPU면 medium을 자동 선택한다.
    """
    eff_device = device
    if device == "auto":
        try:
            import ctranslate2
            eff_device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            eff_device = "cpu"
    if model_size == "auto":
        model_size = "large-v3" if eff_device == "cuda" else "medium"
    return model_size, eff_device


def _get_model(model_size: str, device: str, compute_type: str):
    """WhisperModel을 캐싱하여 반환. 동일 설정이면 재로딩 없이 재사용.

    Streamlit 환경에서는 st.cache_resource를 사용하고,
    그 외 환경(CLI, 테스트 등)에서는 모듈 레벨 딕셔너리로 캐싱.
    """
    from faster_whisper import WhisperModel  # 무거운 의존성 → 지연 import

    try:
        import streamlit as st

        @st.cache_resource
        def _cached(ms, dev, ct, threads):
            return WhisperModel(ms, device=dev, compute_type=ct, cpu_threads=threads)

        cpu_threads = int(os.cpu_count() or 4)
        return _cached(model_size, device, compute_type, cpu_threads)
    except Exception:
        # Streamlit 없는 환경 — 프로세스 내 딕셔너리 캐시
        key = (model_size, device, compute_type)
        if key not in _MODEL_CACHE:
            cpu_threads = int(os.cpu_count() or 4)
            _MODEL_CACHE[key] = WhisperModel(
                model_size, device=device, compute_type=compute_type,
                cpu_threads=cpu_threads,
            )
        return _MODEL_CACHE[key]


def _get_batched_pipeline(model_size: str, device: str, compute_type: str):
    """BatchedInferencePipeline을 캐싱하여 반환."""
    from faster_whisper import BatchedInferencePipeline

    try:
        import streamlit as st

        @st.cache_resource
        def _cached_batched(ms, dev, ct, threads):
            base = WhisperModel(ms, device=dev, compute_type=ct, cpu_threads=threads)
            return BatchedInferencePipeline(model=base)

        cpu_threads = int(os.cpu_count() or 4)
        return _cached_batched(model_size, device, compute_type, cpu_threads)
    except Exception:
        key = ("batched", model_size, device, compute_type)
        if key not in _MODEL_CACHE:
            cpu_threads = int(os.cpu_count() or 4)
            base = WhisperModel(
                model_size, device=device, compute_type=compute_type,
                cpu_threads=cpu_threads,
            )
            _MODEL_CACHE[key] = BatchedInferencePipeline(model=base)
        return _MODEL_CACHE[key]


_MODEL_CACHE: dict = {}


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
    model_size, _ = resolve_model(model_size, device)  # 'auto' → 디바이스 기반 선택
    pipeline = _get_batched_pipeline(model_size, device, compute_type)
    initial_prompt = load_glossary_prompt(glossary_path) if glossary_path else None

    segments_iter, info = pipeline.transcribe(
        str(audio_path),
        language=language,
        initial_prompt=initial_prompt,
        vad_filter=True,      # 침묵 제거 → 환각/반복 완화
        beam_size=1,          # greedy decoding
        batch_size=16,        # BatchedInferencePipeline — 병렬 배치 처리로 61% 추가 단축
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
