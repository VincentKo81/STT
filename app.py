"""회의 STT MVP 웹앱 (Streamlit).

흐름: 음성 업로드 → faster-whisper 전사 → (선택) GPT 보정 → 결과 다운로드(txt/srt)
      → (선택) 회의록 초안. 표준 .docx 는 ax-meeting-minutes 스킬로 생성하세요.

실행: streamlit run app.py
주의: 긴 회의는 전사에 수~수십 분 걸립니다. 이 MVP는 동기 처리이며,
      Phase 2에서 비동기 큐(Celery+Redis)로 전환하는 것을 전제로 합니다.
"""
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

st.set_page_config(page_title="회의 STT 파이프라인", layout="wide")
st.title("회의 STT 파이프라인 (MVP)")

with st.sidebar:
    st.header("설정")
    model_size = st.selectbox(
        "전사 모델", ["medium", "large-v3"],
        index=0 if config.WHISPER_MODEL == "medium" else 1,
        help="medium=Mac CPU 검증 / large-v3=GPU(DGX Spark) 권장",
    )
    compute_type = st.selectbox("compute_type", ["int8", "float16", "int8_float16"], index=0)
    device = st.selectbox("device", ["auto", "cpu", "cuda"], index=0)
    language = st.selectbox("언어", ["ko", "(자동감지)"], index=0)
    enable_correction = st.checkbox("GPT 보정 사용", value=config.ENABLE_CORRECTION)
    enable_minutes = st.checkbox("회의록 초안 생성", value=False,
                                 help="표준 .docx 는 ax-meeting-minutes 스킬 사용 권장")
    if enable_minutes:
        minutes_backend = st.selectbox(
            "회의록 LLM 백엔드",
            ["openai", "claude", "ollama"],
            index=["openai", "claude", "ollama"].index(config.MINUTES_BACKEND),
            help="openai: gpt-4o-mini(기본, 저렴) / claude: Claude API / ollama: 로컬 무료",
        )
        minutes_model_default = {
            "openai": "gpt-4o-mini", "claude": "claude-sonnet-4-6", "ollama": "qwen3:8b"
        }.get(minutes_backend, config.MINUTES_MODEL)
        minutes_model = st.text_input("회의록 모델명", value=minutes_model_default)
    else:
        minutes_backend = config.MINUTES_BACKEND
        minutes_model = config.MINUTES_MODEL

uploaded = st.file_uploader(
    "회의 음성 파일", type=["m4a", "mp3", "wav", "aac", "flac", "ogg"]
)

if uploaded and st.button("실행", type="primary"):
    lang = None if language == "(자동감지)" else language

    # 업로드 파일을 임시 경로에 저장(한글 파일명 인코딩 이슈 회피 위해 ASCII 이름)
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        audio_path = tmp.name

    # 1) 전사
    with st.status("전사 중... (faster-whisper)", expanded=True) as status:
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
        status.update(label=f"전사 완료 — {len(segments)}개 구간", state="complete")

    # 2) (선택) 보정
    corrected = None
    if enable_correction:
        with st.status("GPT 보정 중...", expanded=True) as status:
            cbar = st.progress(0.0)
            corrected = C.correct_text(
                srt,  # 타임스탬프 포함 텍스트를 보정(라인 보존)
                model=config.CORRECTION_MODEL,
                chunk_lines=config.CORRECTION_CHUNK_LINES,
                glossary_path=config.GLOSSARY_PATH,
                on_progress=lambda i, n: cbar.progress(min(i / n, 1.0)),
            )
            status.update(label="보정 완료", state="complete")

    # 결과 표시 + 다운로드
    final_text = corrected or txt
    st.subheader("결과")
    col1, col2 = st.columns(2)
    col1.download_button("원본 전사 (.txt)", txt, file_name="transcript.txt")
    col1.download_button("원본 전사 (.srt)", srt, file_name="transcript.srt")
    if corrected:
        col2.download_button("보정본 (.txt)", corrected, file_name="transcript_corrected.txt")
    st.text_area("미리보기", final_text, height=320)

    # 3) (선택) 회의록 초안
    if enable_minutes:
        with st.status("회의록 초안 생성 중...", expanded=True) as status:
            md = M.generate_minutes_draft(
                final_text, backend=minutes_backend, model=minutes_model
            )
            status.update(label="초안 완료", state="complete")
        st.subheader("회의록 초안 (마크다운)")
        st.info("표준 양식 .docx 는 ax-meeting-minutes 스킬로 생성하세요. 아래는 빠른 확인용 초안입니다.")
        st.download_button("회의록 초안 (.md)", md, file_name="minutes_draft.md")
        st.markdown(md)
