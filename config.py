"""중앙 설정. Claude Code에서 이 값들만 바꿔 쓰면 됩니다.

미해결 결정 항목(README 참고)을 주석으로 표시해 두었습니다.
"""
from pathlib import Path

# --- 경로 ---
ROOT = Path(__file__).resolve().parent
GLOSSARY_PATH = ROOT / "glossary.txt"
OUTPUT_DIR = ROOT / "outputs"          # 전사/회의록 결과
DATASET_DIR = ROOT / "dataset"         # 파인튜닝 데이터셋

# --- STT (faster-whisper) ---
# [결정 #2] 'medium'(Mac CPU에서 38분 완주 검증) ↔ 'large-v3'(DGX Spark GPU 권장, 정확도↑)
WHISPER_MODEL = "medium"
WHISPER_COMPUTE_TYPE = "int8"          # CPU: "int8" / GPU: "float16" 권장
WHISPER_DEVICE = "auto"                # "cpu" | "cuda" | "auto"
WHISPER_LANGUAGE = "ko"                # 한·영 혼용이면 None(자동감지)도 실험해볼 것

# --- 보정 (선택) ---
# [결정 #1] 보정 단계 유지 여부 — Phase 1에서 "보정 유/무" 회의록 품질 A/B 비교 후 결정
ENABLE_CORRECTION = True
CORRECTION_MODEL = "gpt-4o-mini"       # 두 테스트 보고서에서 검증된 모델
CORRECTION_CHUNK_LINES = 120           # 16k 출력 한도 회피 (보고서 기준값)

# --- 회의록 ---
# 백엔드: "openai"(기본, OPENAI_API_KEY) | "claude"(ANTHROPIC_API_KEY) | "ollama"(로컬, 무료)
MINUTES_BACKEND = "openai"
# 모델: openai="gpt-4o"(기본, 고품질) or "gpt-4o-mini"(저렴·빠름) / claude="claude-sonnet-4-6" / ollama="qwen3:8b"
MINUTES_MODEL = "gpt-4o"

# --- 데이터셋 (SRT → 파인튜닝용 음성-텍스트 쌍) ---
DATASET_MAX_SECONDS = 30               # Whisper 학습 단위 상한
DATASET_SAMPLE_RATE = 16000            # 16kHz mono (전처리 표준)
