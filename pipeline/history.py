"""전사·회의록 생성 이력 저장/조회.

각 실행을 outputs/history/<run_id>/ 에 저장한다:
  meta.json                 실행 메타데이터(시간, 소요시간, 모델 등)
  transcript.txt            전사문
  transcript.srt            자막
  transcript_corrected.txt  (보정 사용 시) 보정 전사문
  minutes.md                회의록 마크다운
  <회의록>.docx              최종 회의록 문서
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

HISTORY_DIR = Path(__file__).resolve().parent.parent / "outputs" / "history"


def fmt_duration(sec) -> str:
    """초 → '1시간 2분 3초' 형식. None이면 '-'."""
    if sec is None:
        return "-"
    sec = int(round(float(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}시간 {m}분 {s}초"
    if m:
        return f"{m}분 {s}초"
    return f"{s}초"


def save_run(
    *,
    audio_name: str,
    audio_size_mb: float,
    duration_sec,
    elapsed_total: float,
    elapsed_transcribe: float,
    elapsed_minutes: float,
    model: str,
    device: str,
    backend: str,
    minutes_model: str,
    correction: bool,
    n_segments: int,
    txt: str,
    srt: str,
    md: str,
    docx_path,
    corrected: str = None,
    meeting_info: dict = None,
    created_at: datetime = None,
) -> str:
    """한 번의 실행 결과를 이력 폴더에 저장하고 run_id를 반환."""
    created = created_at or datetime.now()
    run_id = created.strftime("%Y%m%d_%H%M%S")
    d = HISTORY_DIR / run_id
    n = 2
    while d.exists():                       # 같은 초 내 중복 방지
        d = HISTORY_DIR / f"{run_id}_{n}"
        n += 1
    run_id = d.name
    d.mkdir(parents=True, exist_ok=True)

    (d / "transcript.txt").write_text(txt or "", encoding="utf-8")
    (d / "transcript.srt").write_text(srt or "", encoding="utf-8")
    (d / "minutes.md").write_text(md or "", encoding="utf-8")
    if corrected:
        (d / "transcript_corrected.txt").write_text(corrected, encoding="utf-8")

    docx_name = None
    if docx_path and Path(docx_path).exists():
        docx_name = Path(docx_path).name
        shutil.copy2(docx_path, d / docx_name)

    meta = {
        "run_id": run_id,
        "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
        "audio_name": audio_name,
        "audio_size_mb": round(audio_size_mb, 1) if audio_size_mb else None,
        "duration_sec": round(float(duration_sec), 1) if duration_sec else None,
        "elapsed_total": round(elapsed_total, 1),
        "elapsed_transcribe": round(elapsed_transcribe, 1),
        "elapsed_minutes": round(elapsed_minutes, 1),
        "model": model,
        "device": device,
        "backend": backend,
        "minutes_model": minutes_model,
        "correction": bool(correction),
        "n_segments": n_segments,
        "docx_name": docx_name,
        "subtitle": (meeting_info or {}).get("subtitle", "") or "",
    }
    (d / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return run_id


def list_runs() -> list:
    """저장된 모든 실행 메타데이터를 최신순으로 반환."""
    if not HISTORY_DIR.exists():
        return []
    runs = []
    for d in HISTORY_DIR.iterdir():
        meta_f = d / "meta.json"
        if d.is_dir() and meta_f.exists():
            try:
                runs.append(json.loads(meta_f.read_text(encoding="utf-8")))
            except Exception:
                pass
    runs.sort(key=lambda m: m.get("run_id", ""), reverse=True)
    return runs


def run_dir(run_id: str) -> Path:
    return HISTORY_DIR / run_id


def delete_run(run_id: str) -> bool:
    """이력 한 건 삭제. 성공 시 True."""
    d = HISTORY_DIR / run_id
    # 경로 탈출 방지: HISTORY_DIR 하위인지 확인
    try:
        d.resolve().relative_to(HISTORY_DIR.resolve())
    except ValueError:
        return False
    if d.exists() and d.is_dir():
        shutil.rmtree(d)
        return True
    return False
