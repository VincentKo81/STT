"""📜 전사·회의록 생성 이력 — 과거 결과 조회 및 다운로드."""
from pathlib import Path

import streamlit as st

from pipeline import history as H

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

st.set_page_config(page_title="이력 — 회의 STT", layout="wide")
st.title("📜 전사·회의록 생성 이력")

runs = H.list_runs()

if not runs:
    st.info("아직 생성 이력이 없습니다. **회의 STT 파이프라인** 페이지에서 회의록을 생성하면 여기에 자동 기록됩니다.")
    st.stop()

st.caption(f"총 **{len(runs)}건**의 이력 · 결과물은 `outputs/history/`에 저장됩니다.")

# ── 요약 테이블 ────────────────────────────────────────────────
table = [
    {
        "일시": m.get("created_at", ""),
        "회의명": m.get("subtitle") or "(자동 생성)",
        "오디오": m.get("audio_name", ""),
        "오디오 길이": H.fmt_duration(m.get("duration_sec")),
        "소요시간": H.fmt_duration(m.get("elapsed_total")),
        "모델": f'{m.get("model", "?")} / {m.get("device", "?")}',
        "구간": m.get("n_segments", "-"),
    }
    for m in runs
]
st.dataframe(table, use_container_width=True, hide_index=True)

st.divider()

# ── 개별 항목 상세/다운로드 ────────────────────────────────────
st.subheader("📂 항목 선택 → 미리보기 / 다운로드")

labels = [
    f'{m.get("created_at", "")} · {m.get("subtitle") or m.get("audio_name", "")}'
    for m in runs
]
idx = st.selectbox(
    "이력 항목", range(len(runs)), format_func=lambda i: labels[i],
    label_visibility="collapsed",
)
m = runs[idx]
d = H.run_dir(m["run_id"])
rid = m["run_id"]

# 소요시간 지표
c1, c2, c3, c4 = st.columns(4)
c1.metric("⏱️ 총 소요시간", H.fmt_duration(m.get("elapsed_total")))
c2.metric("🎙️ 전사", H.fmt_duration(m.get("elapsed_transcribe")))
c3.metric("📝 회의록", H.fmt_duration(m.get("elapsed_minutes")))
c4.metric("🔊 오디오 길이", H.fmt_duration(m.get("duration_sec")))

# 부가 정보
info_bits = [
    f'🤖 회의록 LLM: {m.get("backend")}/{m.get("minutes_model")}',
    f'✏️ GPT 보정: {"사용" if m.get("correction") else "미사용"}',
]
if m.get("audio_size_mb"):
    info_bits.append(f'💾 파일: {m["audio_size_mb"]}MB')
st.caption(" · ".join(info_bits))

# ── 다운로드 버튼 ──────────────────────────────────────────────
st.markdown("##### 📥 다운로드")
cols = st.columns(4)

docx_name = m.get("docx_name")
docx_path = d / docx_name if docx_name else None
if docx_path and docx_path.exists():
    cols[0].download_button(
        "📥 회의록 (.docx)", data=docx_path.read_bytes(),
        file_name=docx_name, mime=_DOCX_MIME, type="primary",
        key=f"docx_{rid}", use_container_width=True,
    )
else:
    cols[0].button("회의록 없음", disabled=True, use_container_width=True, key=f"nodocx_{rid}")

_txt = d / "transcript.txt"
if _txt.exists():
    cols[1].download_button(
        "📄 전사문 (.txt)", data=_txt.read_bytes(),
        file_name=f"{rid}_transcript.txt", mime="text/plain",
        key=f"txt_{rid}", use_container_width=True,
    )

_srt = d / "transcript.srt"
if _srt.exists():
    cols[2].download_button(
        "🕐 자막 (.srt)", data=_srt.read_bytes(),
        file_name=f"{rid}_transcript.srt", mime="text/plain",
        key=f"srt_{rid}", use_container_width=True,
    )

_md = d / "minutes.md"
if _md.exists():
    cols[3].download_button(
        "📝 회의록 (.md)", data=_md.read_bytes(),
        file_name=f"{rid}_minutes.md", mime="text/markdown",
        key=f"md_{rid}", use_container_width=True,
    )

_corr = d / "transcript_corrected.txt"
if _corr.exists():
    st.download_button(
        "✏️ 보정 전사문 (.txt)", data=_corr.read_bytes(),
        file_name=f"{rid}_transcript_corrected.txt", mime="text/plain",
        key=f"corr_{rid}",
    )

# ── 미리보기 ───────────────────────────────────────────────────
if _md.exists():
    with st.expander("📋 회의록 미리보기 (마크다운)", expanded=True):
        st.markdown(_md.read_text(encoding="utf-8"))

if _txt.exists():
    with st.expander("📝 전사문 미리보기"):
        st.text_area(
            "전사문", _txt.read_text(encoding="utf-8"), height=300,
            label_visibility="collapsed", key=f"prev_{rid}",
        )

# ── 삭제 ───────────────────────────────────────────────────────
with st.expander("🗑️ 이 이력 삭제"):
    st.warning(f"`{rid}` 이력을 영구 삭제합니다. 되돌릴 수 없습니다.")
    confirm = st.checkbox("삭제를 확인합니다", key=f"confirm_{rid}")
    if st.button("삭제", type="primary", disabled=not confirm, key=f"del_{rid}"):
        if H.delete_run(rid):
            st.success("삭제했습니다.")
            st.rerun()
        else:
            st.error("삭제에 실패했습니다.")
