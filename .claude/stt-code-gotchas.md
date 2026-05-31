---
name: stt-code-gotchas
description: "meeting-stt-pipeline 코드의 함정(.env 자동로드 안 됨, app.py 임시파일 누수)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0b6168f1-27c2-4dfa-94c1-c24a8feb7dda
---

`meeting-stt-pipeline` 코드에서 주의할 점 (수정 후보):
- **`.env` 자동 로드 안 됨**: `pipeline/correct.py`·`pipeline/minutes.py`가 python-dotenv를 안 써서 `.env` 파일이 있어도 무시됨. OPENAI/ANTHROPIC 키는 **환경변수로 주입**해야 동작함 (`OPENAI_API_KEY=... .venv/bin/python ...` 또는 export). README의 `cp .env.example .env` 안내만으로는 키가 읽히지 않음.
- **임시파일 누수**: `app.py`가 업로드 오디오를 `tempfile.NamedTemporaryFile(delete=False)`로 저장한 뒤 삭제하지 않음 → 반복 처리 시 임시 디렉토리에 누적.
- `config.OUTPUT_DIR`/`DATASET_DIR`는 정의돼 있으나 `app.py`에서 미사용(다운로드 버튼으로만 처리).

**Why:** 사용자가 안내대로 진행하다 보정/회의록 단계에서 키가 안 읽혀 막힐 수 있는 함정.
**How to apply:** 보정·회의록 테스트 시 키를 환경변수로 주입. 코드 정리 단계에서 dotenv 로드·임시파일 cleanup 추가 검토.

[[stt-pipeline-overview]] [[stt-verified-settings]]
