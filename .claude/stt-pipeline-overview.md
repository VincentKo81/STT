---
name: stt-pipeline-overview
description: "STT 회의록 파이프라인 프로젝트 개요와 실행 환경(Python 3.11 venv, 테스트 데이터 위치)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0b6168f1-27c2-4dfa-94c1-c24a8feb7dda
---

`meeting-stt-pipeline/` — 회의 녹음을 전사(faster-whisper) → 보정(GPT, 선택) → 회의록(.docx, `ax-meeting-minutes` 스킬)으로 처리하고, 클로바노트 SRT로 LoRA 파인튜닝 데이터셋을 만드는 파이프라인. 현재 Phase 1(MVP) 진행 중.

실행 환경:
- venv는 `meeting-stt-pipeline/.venv` (Python 3.11.15). **시스템 기본 python3는 3.9.6인데 `pipeline/transcribe.py`가 `str | None`(PEP 604, 3.10+ 문법)을 써서 3.9로는 import 실패** → 반드시 `.venv/bin/python`(3.11) 사용.
- ffmpeg는 Homebrew(`/opt/homebrew/bin`)에 설치됨. Homebrew python3.11/3.13도 있음.
- 테스트 데이터: `~/Downloads/에스핀 1차미팅.{m4a,srt,txt}` (83분 회의, 화자 5명: 고재영·이유녕·송윤희 + 참석자 2).

[[stt-verified-settings]] [[stt-code-gotchas]]
