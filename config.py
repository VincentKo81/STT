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
# [결정 #2] 'auto' = 디바이스 기반 자동 선택 (GPU→large-v3 / CPU→medium)
#   검증(5.2분 회의, 정답 대비 CER): medium 27.5% vs large-v3 13.1% — large-v3가 오류율 절반.
#   large-v3는 CPU에서 ~2배 느리지만 GPU(DGX Spark)에선 속도 페널티 없음 → device로 자동 분기.
#   고정하려면 "medium" 또는 "large-v3"로 변경.
WHISPER_MODEL = "auto"
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
# 모델 가성비 순위 (2026-05-31 가격 기준):
#   gpt-4.1-mini  →  ~9원/건,  품질 ★★★★  ← 기본값 (가성비 최고)
#   gpt-4.1       →  ~44원/건, 품질 ★★★★★
#   gpt-4.1-nano  →  ~2원/건,  품질 미검증
#   gpt-5-mini    →  ~7원/건,  품질 미검증
#   gpt-4o        →  ~55원/건, 구세대 (비추)
MINUTES_MODEL = "gpt-4.1-mini"

# --- 데이터셋 (SRT → 파인튜닝용 음성-텍스트 쌍) ---
DATASET_MAX_SECONDS = 30               # Whisper 학습 단위 상한
DATASET_SAMPLE_RATE = 16000            # 16kHz mono (전처리 표준)
