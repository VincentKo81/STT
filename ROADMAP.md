# 🗺️ 회의 STT 파이프라인 — 전체 로드맵

> 회의 녹음 → **전사 → 보정 → 회의록(.docx)** + 클로바 SRT로 **파인튜닝 데이터셋**.
> 각 단계 제목을 클릭하면 상세 내용이 펼쳐집니다.

```
현재 위치 👉  Phase 0 · 7단계 "config 결정 확정"  (0-5·0-6 완료 / API 키 확보 후 진행)

Phase 0 준비·검증   ▓▓▓▓▓▓▓  ▶ 거의 완료  (6/7 완료, 0-7만 대기)
Phase 1 MVP 통합    ░░░░░░░  ⬜ 예정
Phase 2 운영화      ░░░░░░░  ⬜ 예정
Phase 3 Spark·튜닝  ░░░░░░░  ⬜ 예정
```

---

<details open>
<summary>🔵 <b>Phase 0 — 준비 · 검증</b> &nbsp;|&nbsp; ▶ <b>진행 중 (현재 단계)</b></summary>

<br>

골격 코드가 실제 음성·데이터로 동작하는지 검증하고, `config.py`의 미해결 결정 3개를 실측으로 확정하는 단계. **에스핀 1차미팅**(83분, 화자 5명)을 표본으로 사용.

| # | 단계 | 상태 | 핵심 결과 |
|---|------|------|-----------|
| 0-1 | 프로젝트 구조 분석 | ✅ | 8개 파일 역할·잠재 이슈 파악 |
| 0-2 | 환경 구축 | ✅ | Python 3.11 venv + 의존성 + ffmpeg |
| 0-3 | 데이터셋 검증 | ✅ | 268구간 → 352클립(16kHz mono) |
| 0-4 | 전사 엔진 검증(샘플) | ✅ | medium RTF 0.50, 용어집 효과 |
| 0-5 | 전체 회의 전사 | ✅ | 1894구간 34,561자, 36.5분(RTF 0.44) |
| 0-6 | 회의록 .docx 생성 | ✅ | AX 표준 6섹션 .docx 생성 완료 |
| **0-7** | **config 결정 3개 확정** | **⬜ 대기** | **👉 다음 — 보정 A/B (API 키 필요)** |

<details>
<summary>📂 0-1 ~ 0-4 완료 상세</summary>

<br>

**0-1 프로젝트 구조 분석** ✅
- `app.py`(Streamlit) · `pipeline/{transcribe,correct,minutes}.py` · `tools/srt_to_dataset.py` · `config.py` · `glossary.txt` 구조 파악.
- 검증된 파이프라인: `음성 → faster-whisper(+용어집) → (선택)GPT보정 → Claude 회의록 스킬 → .docx`.
- 발견 이슈: `.env` 자동 로드 안 됨, `app.py` 임시파일 누수 → [코드 정리는 Phase 1].

**0-2 환경 구축** ✅
- 시스템 python3가 3.9.6 → `transcribe.py`의 `str | None`(PEP 604) 때문에 import 실패 → **Homebrew Python 3.11로 venv**(`meeting-stt-pipeline/.venv`).
- 설치: faster-whisper 1.2.1, ctranslate2 4.7.2, av 17.0.1, onnxruntime 1.26.0, openai 2.38.0, anthropic 0.105.2, streamlit 1.58.0.
- ffmpeg 8.1.1(Homebrew) 확인.

**0-3 데이터셋 검증** ✅ — `tools/srt_to_dataset.py --split-long`
- 입력: 클로바노트 SRT 268구간(30초 초과 64개=23%), 음성 83분.
- 출력: **352클립**(16kHz·mono·pcm_s16le), manifest.jsonl, summary.txt.
- 품질: 빈 텍스트 0개, 30초 초과 잔존 0개, 화자 라벨 5명 보존. 분할물 148개(42%)는 `needs_review`(텍스트 시간비율 근사배분).

**0-4 전사 엔진 검증(샘플 3분)** ✅ — medium/int8/cpu
- **RTF 0.50배**(180초 → 90초), 무한반복 없음, 한국어 prob 1.00.
- 용어집 효과: "IT"·"AX 데이터 팀"·"바로답 AI"·건설용어 정확 표기.
- 미세 오류 3~4건/3분("리스트 업"→"리스톱" 등) → 보정 단계의 근거.

</details>

<details>
<summary>⏳ 0-5 전체 회의 전사 (현재 진행 중)</summary>

<br>

- 입력: `~/Downloads/에스핀 1차미팅.m4a`(83분) → medium/int8/cpu, 용어집 주입.
- 출력 예정: `outputs/espin_full_transcript.txt` / `.srt`.
- 예상 소요: RTF 0.50 기준 **약 42분**(백그라운드 실행).
- 목적: 실전 전사문 확보 → 0-6 회의록·0-7 보정 검증의 재료.

</details>

<details>
<summary>⬜ 0-6 회의록 .docx 생성 (다음)</summary>

<br>

- 전사문을 **`ax-meeting-minutes` 스킬**에 넘겨 AX 표준 양식 .docx 생성. **API 키 불필요**(Claude Code 내 스킬).
- 6개 표준 섹션(개조식): 개요 / 주요 논의 / 시스템·기술 / 데이터·자료 / 향후 일정 / 합의 사항.
- 산출물이 "실제 쓰는 회의록"이 되는 핵심 단계.

</details>

<details>
<summary>⬜ 0-7 config 결정 3개 확정 (API 키 필요)</summary>

<br>

| 결정 | 후보 | 현재 데이터 | 확정 방법 |
|------|------|-------------|-----------|
| #1 보정 유무 | 유 ↔ 무 | 미세오류 3~4건/3분 존재 | 보정 유/무 회의록 A/B 비교 |
| #2 전사 모델 | medium ↔ large-v3 | medium=Mac RTF 0.50, 품질 충분 | Spark GPU에서 large-v3 WER 비교 |
| #3 보정 LLM | gpt-4o-mini ↔ Claude | 미검증 | 같은 청크 보정 품질 비교 |

- 선행 조건: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`를 **환경변수로 주입**(`.env` 자동 로드 안 됨).

</details>

</details>

---

<details>
<summary>⚪ <b>Phase 1 — MVP 통합 (app.py 웹앱)</b> &nbsp;|&nbsp; ⬜ 예정</summary>

<br>

검증된 단계들을 Streamlit 웹앱 하나로 묶어, 비기술자도 음성만 올리면 전사·보정·회의록 초안을 받게 하는 단계.

- **웹앱 실전화**: 업로드 → 전사 → (선택)보정 → 회의록 초안 → txt/srt/md 다운로드. (`app.py` 골격 존재)
- **코드 정리**(검증 중 발견한 이슈):
  - `.env` 자동 로드 추가(python-dotenv) — 현재 키가 환경변수로만 읽힘.
  - `app.py` 임시파일 cleanup — `delete=False` 후 미삭제.
  - `config.OUTPUT_DIR`/`DATASET_DIR` 실제 활용.
- **산출물 표준화**: 회의록 초안 → `ax-meeting-minutes` 연결 동선 정리.

</details>

<details>
<summary>⚪ <b>Phase 2 — 운영화</b> &nbsp;|&nbsp; ⬜ 예정</summary>

<br>

여러 회의를 안정적으로 처리하고, 사람의 교정을 데이터로 축적하는 단계.

- **비동기 큐 (Celery + Redis)**: 긴 전사를 백그라운드 작업화 → 동기 처리의 대기 문제 해소.
- **교정 화면 = 데이터 공장**: 사람이 고친 before/after(교정 쌍)를 저장 → Phase 3 파인튜닝 데이터로 직결.
- **화자 분리 (pyannote)**: "누가 말했는지" 자동 라벨링 → 회의록 발언 주체 명확화.

</details>

<details>
<summary>⚪ <b>Phase 3 — DGX Spark · 파인튜닝</b> &nbsp;|&nbsp; ⬜ 예정</summary>

<br>

GPU 인프라로 정확도를 끌어올리고, 한국어 도메인 특화 ASR로 자립하는 단계.

- **GPU 전환**: `large-v3` 또는 `Qwen3-ASR`로 전환(compute_type float16) → WER 개선.
- **용어집 고도화**: 운영 중 누적된 오인식어로 `glossary.txt` 지속 보강.
- **LoRA 파인튜닝**: `tools/srt_to_dataset.py` 산출물(클립↔텍스트) + Phase 2 교정 쌍으로 도메인 특화 모델 학습.
  - 보유 자산: 클로바 코퍼스 약 11시간 분량 → 일괄 데이터셋화 가능.

</details>

---

### 범례
✅ 완료 · ⏳ 진행 중(현재) · ⬜ 예정 &nbsp;|&nbsp; 🔵 현재 Phase · ⚪ 향후 Phase

_최종 업데이트: 2026-05-31 · Phase 0-6 완료(회의록 생성), 0-7 대기_
