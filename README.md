# 회의 STT 파이프라인 (시작 골격)

회의 녹음을 **전사 → (선택) 보정 → 회의록**으로 처리하고, 클로바노트 SRT로
**파인튜닝 데이터셋**을 만드는 프로젝트의 시작 골격입니다.

> 이 골격은 Claude 채팅에서 작성됐고, 무거운 부분(faster-whisper 전사, API 호출,
> 실제 오디오 분할)은 **사장님 PC / DGX Spark 의 Claude Code 에서 실행**하는 것을 전제로 합니다.
> 회의록 표준 .docx 의 '정본'은 기존 `ax-meeting-minutes` 스킬입니다.

## 검증된 파이프라인 (두 STT 테스트 보고서 기준)

```
음성  →  faster-whisper(medium/large-v3)  →  (선택) GPT 청크 보정  →  Claude 회의록 스킬  →  .docx
                  ▲ +용어집(vocab biasing)        ▲ 타임스탬프 보존              ▲ AX 표준 양식
```
- Gemini 직접 전사는 장문 한국어에서 무한 반복 루프 → STT 엔진으로 제외.
- 로컬 faster-whisper 가 안정성 최고(38분 완주, 비용 0).

## 디렉터리 구조

```
meeting-stt-pipeline/
├── README.md
├── requirements.txt
├── .env.example          # OPENAI/ANTHROPIC 키 (보정·회의록 단계용)
├── config.py             # 모든 옵션을 한곳에서 관리
├── glossary.txt          # 도메인 용어집 (vocab biasing, 테스트 오류어로 시드)
├── app.py                # Streamlit MVP (업로드→전사→보정→다운로드)
├── pipeline/
│   ├── transcribe.py     # faster-whisper + 용어집 initial_prompt + VAD
│   ├── correct.py        # GPT 청크 보정 (선택)
│   └── minutes.py        # 회의록 초안 + ax-meeting-minutes 스킬 안내
└── tools/
    └── srt_to_dataset.py # SRT + 오디오 → (클립↔텍스트) 데이터셋 (화자 라벨 보존)
```

## 설치

```bash
# 1) 가상환경
python3 -m venv .venv && source .venv/bin/activate

# 2) 의존성
pip install -r requirements.txt          # faster-whisper, openai, anthropic, streamlit

# 3) 시스템 패키지
#    macOS:  brew install ffmpeg
#    Ubuntu: sudo apt-get install ffmpeg
#    (GPU 사용 시 NVIDIA 드라이버 + CUDA — DGX Spark)

# 4) 키 (보정·회의록 단계만 필요)
cp .env.example .env   # 키 채우기
```

## 실행

### A. 회의록용 전사 (MVP 웹앱)
```bash
streamlit run app.py
```
사이드바에서 모델(medium/large-v3)·보정·회의록 초안을 토글한 뒤 음성을 올리면 됩니다.

### B. 파인튜닝 데이터셋 만들기 (클로바 SRT + 음성)
```bash
python tools/srt_to_dataset.py \
  --srt  "에스핀_1차미팅.srt" \
  --audio "에스핀_1차미팅.m4a" \
  --out  dataset \
  --split-long          # 30초 초과 구간을 무음 기준으로 분할(텍스트 근사 배분)
```
→ `dataset/clips/*.wav`(16kHz mono), `dataset/manifest.jsonl`, `dataset/summary.txt` 생성.
보유한 11시간 분량 클로바 코퍼스를 모두 돌리면 LoRA 파인튜닝 데이터가 한 번에 모입니다.

## 미해결 결정 (config.py에서 전환)

1. **보정 단계 유지 여부** — Phase 1에서 "보정 유/무" 회의록 품질을 A/B 비교 후 결정.
2. **전사 모델** — `medium`(Mac CPU 검증) vs `large-v3`(Spark GPU, 정확도↑). 실제 음성 WER로 확정.
3. **보정 LLM** — `gpt-4o-mini`(검증) vs Claude(스킬과 통일).

## 로드맵 매핑

- **Phase 1 (지금)**: `app.py` + 기존 전사/보정 스크립트 통합 + 용어집. ← 이 골격
- **Phase 2 (운영화)**: 비동기 큐(Celery+Redis), 교정 화면(교정 쌍 저장=데이터 공장), 화자 분리(pyannote).
- **Phase 3 (Spark)**: `large-v3`/`Qwen3-ASR` GPU 전환 → 용어집 고도화 → `tools/srt_to_dataset.py` 산출물로 LoRA 파인튜닝.

## 주의

- 긴 회의는 전사에 수~수십 분. MVP는 동기 처리이며 Phase 2에서 비동기로 전환.
- Claude Code는 파일 수정·명령 실행 전 권한을 묻지만 파일시스템에 직접 접근하므로,
  **삭제·이동 명령은 승인 전에 확인**하고 Spark/운영 환경에선 접근 범위를 좁혀 쓰세요.
- `srt_to_dataset.py --split-long` 의 분할 텍스트는 시간 비율 근사 배분이라 `needs_review=True`로
  표시됩니다. 30초 이하 원구간은 그대로 학습 단위로 쓸 수 있습니다.
