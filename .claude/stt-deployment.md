---
name: stt-deployment
description: 배포/원격접속 아키텍처(웹앱 UI + 서버 실행 + Tailscale)와 회사 진행 체크리스트
metadata: 
  node_type: memory
  type: project
  originSessionId: 0b6168f1-27c2-4dfa-94c1-c24a8feb7dda
---

배포 아키텍처 방향 (사용자와 논의, 2026-05-31): **UI는 웹앱(Streamlit), 실제 실행(전사)은 서버**(집 PC / 회사 서버 / DGX Spark). 클라이언트-서버 분리.
- `app.py`(Streamlit)가 이미 그 구조의 출발점. 서버에서 `streamlit run app.py --server.address 0.0.0.0 --server.port 8501`로 띄우면 브라우저(모바일 포함)로 접속.
- **모바일은 실행기가 아니라 단말** — faster-whisper 전사는 CPU/GPU 연산이 필요해 폰 단독 실행 불가.
- "어디서나 접속" 관건은 네트워크 노출: 사내망 직접(같은 LAN) / **Tailscale**(추천 — 사설 VPN, 기기마다 100.x.x.x, 인터넷 공개 노출 없음) / 회사 VPN. 회의록 민감정보라 공개노출 방식(ngrok/포트포워딩) 지양.
- 이상적 구성: DGX Spark/회사 서버에 두고 Tailscale 또는 사내망으로 접속(로드맵 Phase 3와 일치).
- Tailscale 사용법: 서버+접속기기 모두 설치→같은 계정 로그인→서버 `tailscale ip -4` 확인→브라우저 `http://100.x.x.x:8501`. 로그인·VPN권한 승인은 사용자 본인만 가능.

**회사 진행 시 확인 체크리스트** (사용자가 "나중에" 진행 예정 — 2026-05-31 시점 보류):
1. 회사 서버/DGX Spark 접근 권한 여부
2. 사내 Tailscale/VPN 설치 허용 여부(보안팀 확인)
3. 회의 음성·회의록의 외부 반출 정책 — GitHub·Claude/OpenAI API 모두 "외부"임. 사내 GitLab/온프레미스 LLM 대안 검토
4. API 키 발급(회의록 생성 Claude, 보정 OpenAI)
5. git은 반드시 private + 데이터/키/모델 `.gitignore` 제외(음성·전사문·회의록은 고객사명·금액 포함 민감정보). 아직 git 미초기화 상태.

[[stt-pipeline-overview]] [[stt-workflow-design]]
