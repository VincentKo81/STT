---
name: stt-verified-settings
description: "에스핀 음성으로 실측 검증한 STT 파이프라인 설정값과 결과(medium RTF 0.50, 용어집 효과)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0b6168f1-27c2-4dfa-94c1-c24a8feb7dda
---

에스핀 1차미팅 음성으로 실측 검증 (2026-05-30):
- **전사**: faster-whisper `medium`/int8/cpu 가 Mac CPU에서 **RTF 0.50배** (180초 오디오를 90초에 전사 → 83분 전체는 약 42분), 무한반복 루프 없음, 한국어 감지 prob 1.00. 용어집(`glossary.txt`) initial_prompt 효과 확인 — "IT"·"AX 데이터 팀"·"바로답 AI"·건설용어(시공/시운전/하자/견적) 정확 표기.
- **미세 오류**: 외래어("리스트 업"→"리스톱"), 문맥("과제화해서"→"과제와 해서") 등 3~4건/3분 → GPT 보정 단계의 근거. 단 발음 오인식("테클"→"택글")은 텍스트 보정으로 한계.
- **데이터셋**: `tools/srt_to_dataset.py --split-long` 정상 동작. 클로바 SRT 268구간(30초 초과 23%)→ 352클립(16kHz mono pcm_s16le), 빈 텍스트 0개, 분할물 148개(42%)는 `needs_review=True`(텍스트 시간비율 근사배분).

config.py 미해결 결정 3개: #2(모델)는 Mac=medium 합리적 / Spark GPU에서 large-v3 비교 예정. #1(보정 유무)·#3(보정 LLM)은 API 키 확보 후 검증 예정.

**2026-05-31 업데이트 — 회의록 LLM 확정**: **gpt-4.1-mini** (가성비 최고 ~9원/건, 6섹션·개조식 준수). 비교: gpt-4o(~55원, 구세대 비추) / gpt-4.1(~44원, 고품질) / gpt-5.4-nano(~4원, 미검증). **Ollama 로컬(gemma4:e2b·qwen3:8b)은 34000자 한국어 전사문에서 6섹션 형식 지시를 못 따라 실패**(짧은 3분은 OK) → 로컬 자동화는 Spark GPU+큰 모델(Phase 3) 전까지 보류. OpenAI 가격은 gpt-5.x 세대로 개편됨(gpt-4o 가격표에서 사라짐).

[[stt-pipeline-overview]] [[stt-code-gotchas]] [[stt-workflow-design]]
