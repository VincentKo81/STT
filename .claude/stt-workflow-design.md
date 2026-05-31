---
name: stt-workflow-design
description: 회의록 자동화 워크플로우 설계 결정(faster-whisper 단독 기본 + GPT보정 옵션 + 파인튜닝 오픈)
metadata: 
  node_type: memory
  type: project
  originSessionId: 0b6168f1-27c2-4dfa-94c1-c24a8feb7dda
---

회의록 자동화 워크플로우 설계 (사용자와 합의, 2026-05-31):
- **기본 경로(자동)**: 음성 + 회의정보 입력 → faster-whisper(medium+용어집) 전사 → 회의록 LLM(Claude) → .docx. GPT 후보정 없음.
- **옵션 경로**: 단독 회의록 품질이 불만족스러울 때만 GPT 후보정(`correct.py`)으로 재작성하거나 회의록 직접 수정. → config 결정 #1(보정)은 **"기본 無, 옵션 有"**로 결론.
- **파인튜닝**: 기능적으로 오픈. `srt_to_dataset.py` 산출물 + 교정쌍(보정 전/후)으로 LoRA.
- **회의 메타정보(일시·장소·참석자·제목)는 사용자 입력칸으로** 받음 → 클로바노트 의존 제거. AX 회의록 양식은 주제별 통합이라 발언자 귀속이 불필요 → **화자분리(pyannote)는 Phase 2 필수 → 선택적 고도화로 강등**.

핵심 통찰: 회의록 생성 LLM(Claude)이 작성하면서 이미 오인식을 보정함(425→429, PTO→PTU, S-PIN→에스핀테크놀로지 등). 그래서 회의록만 뽑을 거면 별도 보정 단계가 중복일 수 있음. 보정이 꼭 필요한 경우는 전사문/자막 자체를 그대로 쓸 때(파인튜닝 데이터, 타임코드 자막).

키 구성: STT=faster-whisper(키 불필요) / 회의록 생성=Claude(키 필요, 기본 경로에도) / 보정=OpenAI(옵션 켤 때만).
구현 갭: `app.py`가 현재 마크다운 초안만 생성 → `minutes.py`(6섹션 구조화) + `generate.js`(docx 렌더) 연결 필요.

[[stt-pipeline-overview]] [[stt-verified-settings]] [[stt-deployment]]
