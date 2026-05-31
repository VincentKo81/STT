"""회의 STT MVP 웹앱 (Streamlit).

흐름:
  [회의정보 입력] + [음성 업로드]
        ↓
  faster-whisper 전사 → (선택) GPT 보정
        ↓
  gpt-4o 회의록 생성 → AX 표준 .docx 자동 생성
        ↓
  📥 전사문(.txt/.srt) + 회의록(.docx) 다운로드

실행: streamlit run app.py --server.address 0.0.0.0 --server.port 8501
"""
import json
import tempfile
from pathlib import Path

# .env 자동 로드 (OPENAI_API_KEY, ANTHROPIC_API_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import streamlit as st

import config
from pipeline import transcribe as T
from pipeline import correct as C
from pipeline import minutes as M

# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="회의 STT 파이프라인", layout="wide")
st.title("🎙️ 회의 STT 파이프라인")

# ── 사이드바 ──────────────────────────────────────────────────
with st.sidebar:

    # 📝 회의 정보
    st.header("📝 회의 정보")
    meeting_subtitle = st.text_input(
        "회의명 *",
        placeholder="에스핀테크 Azure 도입 1차 협의",
    )
    meeting_date = st.text_input(
        "회의일시",
        placeholder="2026.05.31 (일) 14:00 ~ 15:30",
    )
    meeting_location = st.text_input(
        "회의장소",
        placeholder="본사 3층 회의실",
    )
    meeting_attendees = st.text_area(
        "참석자",
        placeholder="홍길동 책임 (AX 데이터팀)   김철수 매니저 (에스핀테크)",
        height=80,
        help="이름 직급 (소속팀) 형식, 공백 3칸으로 구분",
    )
    meeting_topic = st.text_input(
        "회의주제",
        placeholder="Azure 클라우드 도입 방향 및 MSP 선정 논의",
    )

    st.divider()

    # ⚙️ 전사 설정
    st.header("⚙️ 전사 설정")
    model_size = st.selectbox(
        "전사 모델", ["medium", "large-v3"],
        index=0 if config.WHISPER_MODEL == "medium" else 1,
        help="medium=Mac CPU 검증 / large-v3=GPU(DGX Spark) 권장",
    )
    compute_type = st.selectbox(
        "compute_type", ["int8", "float16", "int8_float16"], index=0,
    )
    device   = st.selectbox("device", ["auto", "cpu", "cuda"], index=0)
    language = st.selectbox("언어", ["ko", "(자동감지)"], index=0)

    st.divider()

    # 🤖 회의록 설정
    st.header("🤖 회의록 설정")
    enable_correction = st.checkbox(
        "GPT 보정 사용", value=config.ENABLE_CORRECTION,
        help="전사 후 GPT로 오인식 교정 (OpenAI 키 필요)",
    )
    minutes_backend = st.selectbox(
        "회의록 LLM",
        ["openai", "claude", "ollama"],
        index=["openai", "claude", "ollama"].index(config.MINUTES_BACKEND),
        help="openai=gpt-4o(기본) / claude=Claude API / ollama=로컬 무료",
    )
    _model_defaults = {
        "openai": config.MINUTES_MODEL,
        "claude": "claude-sonnet-4-6",
        "ollama": "qwen3:8b",
    }
    minutes_model = st.text_input(
        "모델명",
        value=_model_defaults.get(minutes_backend, config.MINUTES_MODEL),
    )

# ── 메인 영역 ─────────────────────────────────────────────────
uploaded = st.file_uploader(
    "회의 음성 파일을 올려주세요",
    type=["m4a", "mp3", "wav", "aac", "flac", "ogg"],
)

if not meeting_subtitle:
    st.info("👈 왼쪽 사이드바에서 **회의명**을 입력한 뒤 음성 파일을 올려주세요.")

run_btn = st.button(
    "🚀 전사 + 회의록 생성",
    type="primary",
    disabled=(not uploaded or not meeting_subtitle),
)

if run_btn and uploaded and meeting_subtitle:
    lang = None if language == "(자동감지)" else language

    # 임시 오디오 파일 저장 (한글 파일명 인코딩 이슈 회피)
    suffix = Path(uploaded.name).suffix
    tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp_audio.write(uploaded.getbuffer())
        tmp_audio.flush()
        audio_path = tmp_audio.name
    finally:
        tmp_audio.close()

    try:
        # ── 1) 전사 ───────────────────────────────────────────
        with st.status("🎙️ 전사 중... (faster-whisper)", expanded=True) as status:
            bar = st.progress(0.0)

            def on_prog(cur, total):
                if total:
                    bar.progress(min(cur / total, 1.0))

            segments, info = T.transcribe(
                audio_path,
                model_size=model_size,
                compute_type=compute_type,
                device=device,
                language=lang,
                glossary_path=config.GLOSSARY_PATH,
                on_progress=on_prog,
            )
            bar.progress(1.0)
            txt = T.to_txt(segments)
            srt = T.to_srt(segments)
            status.update(
                label=f"✅ 전사 완료 — {len(segments)}개 구간", state="complete"
            )

        # ── 2) (선택) 보정 ────────────────────────────────────
        corrected = None
        if enable_correction:
            with st.status("✏️ GPT 보정 중...", expanded=True) as status:
                cbar = st.progress(0.0)
                corrected = C.correct_text(
                    srt,
                    model=config.CORRECTION_MODEL,
                    chunk_lines=config.CORRECTION_CHUNK_LINES,
                    glossary_path=config.GLOSSARY_PATH,
                    on_progress=lambda i, n: cbar.progress(min(i / n, 1.0)),
                )
                status.update(label="✅ 보정 완료", state="complete")

        final_text = corrected or txt

        # ── 3) 회의록 생성 → .docx ───────────────────────────
        with st.status(f"📝 회의록 생성 중... ({minutes_backend}/{minutes_model})",
                       expanded=True) as status:
            # 마크다운 생성
            md = M.generate_minutes_draft(
                final_text, backend=minutes_backend, model=minutes_model
            )
            status.update(label="📄 .docx 변환 중...", state="running")

            # .docx 생성
            meeting_info = {
                "subtitle"  : meeting_subtitle,
                "date"      : meeting_date,
                "location"  : meeting_location,
                "attendees" : meeting_attendees,
                "topic"     : meeting_topic,
            }
            out_dir  = Path(__file__).parent / "outputs"
            docx_path = M.generate_minutes_docx(md, meeting_info, out_dir)
            docx_bytes = docx_path.read_bytes()

            status.update(label="✅ 회의록 완료", state="complete")

        # ── 결과 표시 ─────────────────────────────────────────
        st.success(f"✅ **{meeting_subtitle}** 회의록이 완성됐습니다!")

        # 다운로드 버튼
        col1, col2, col3 = st.columns(3)
        col1.download_button(
            "📥 회의록 다운로드 (.docx)",
            data=docx_bytes,
            file_name=docx_path.name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
        )
        col2.download_button(
            "📄 전사문 (.txt)",
            data=txt,
            file_name="transcript.txt",
            mime="text/plain",
        )
        col3.download_button(
            "🕐 자막 (.srt)",
            data=srt,
            file_name="transcript.srt",
            mime="text/plain",
        )
        if corrected:
            st.download_button(
                "✏️ 보정 전사문 (.txt)",
                data=corrected,
                file_name="transcript_corrected.txt",
                mime="text/plain",
            )

        # 미리보기
        with st.expander("📋 회의록 미리보기 (마크다운)", expanded=True):
            st.markdown(md)

        with st.expander("📝 전사문 미리보기"):
            st.text_area("전사 원본", final_text, height=300, label_visibility="collapsed")

    finally:
        # 임시 오디오 파일 정리 (누수 방지)
        Path(audio_path).unlink(missing_ok=True)
