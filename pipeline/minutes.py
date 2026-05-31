"""회의록 생성.

LLM 백엔드를 선택할 수 있습니다:
  - "openai"  : OpenAI API (OPENAI_API_KEY 필요) ← 기본값
  - "ollama"  : 로컬 Ollama (비용 0, 데이터 외부 유출 없음)
  - "claude"  : Anthropic Claude API (ANTHROPIC_API_KEY 필요)

[표준 .docx 출력] 두 백엔드 모두 6섹션 마크다운을 만들고,
  이후 generate_minutes_docx()가 generate.js를 호출해 .docx로 변환합니다.
"""
import json
import subprocess
import tempfile
import os
from pathlib import Path
from textwrap import dedent

MINUTES_SYSTEM = dedent(
    """
    당신은 AX 데이터팀 표준 회의록 작성기입니다. 회의 전사본을 분석해 표준 양식의 본문을 마크다운으로 작성하세요.

    [① 회의 기본정보 — 맨 앞에 출력]
    전사 내용으로 파악되는 항목은 채우고, 도저히 알 수 없으면 "(확인 필요)"로 표기.

    ## 회의 정보
    - 회의명: (회의 주제를 함축한 제목)
    - 일시: (전사에 단서가 있으면 추정, 없으면 (확인 필요))
    - 장소: (전사에 단서가 있으면, 없으면 (확인 필요))
    - 참석자: (언급된 이름·소속·직급. 형식: 홍길동 책임 (소속팀), 공백 3칸 구분)
    - 주제: (한 문장 요약)

    [② 작성 톤·문체]
    - 개조식(서술형 절대 금지). 종결어미는 명사형 또는 "~함", "~임"
      · 올바름: ○ Azure 허브앤스포크 아키텍처 도입 방향 확인함
      · 금지:   ○ Azure 허브앤스포크 아키텍처를 도입하기로 하였습니다
    - 발언자별로 나누지 말고 발언 내용을 '주제별'로 통합 정리

    [③ 불릿 3단 계층 — 기호로 단계 구분]
    ○ 1단계: 주요 항목
      - 2단계: ○의 세부 내용
        · 3단계: -의 세부 내용
    ※ 세부 내용이 여러 개일 때만 하위 단계로 내려가고, 단순 항목은 ○ 1단계로 평탄하게 둘 것

    [④ 본문 — 아래 6개 섹션, 각 섹션 사이에 빈 줄을 둘 것]

    ## 1. 회의 개요
    (회의 목적·배경과 진행된 주요 활동을 ○ 5개 내외로 정리)

    ## 2. 주요 논의 사항
    ### 2.1 (논의 주제 소제목)
    ### 2.2 (논의 주제 소제목)
    (논의 흐름별로 소제목을 나눠 정리, 토론·쟁점이 오간 부분 중심)

    ## 3. (회의 성격에 맞는 제목)
    (기술회의면 "시스템/기술 검토", 그 외 회의면 적절한 제목으로 변경 가능.
     3.1, 3.2 소제목으로 정량 데이터·세부 내역 정리)

    ## 4. (회의 성격에 맞는 제목)
    (예: "데이터/자료 현황" 또는 회의에 맞는 제목으로 변경 가능.
     4.1, 4.2 소제목. 자료 출처·보유 현황·요구사항 등)

    ## 5. 주요 합의 사항
    1. (결정사항을 한 문장으로 명문화)
    (5~10개 내외. "...추진", "...전달", "...검토" 등 행동 동사로 종결)

    ## 6. 향후 일정 및 추진 방향
    (가까운 미래 → 먼 미래 순. 마일스톤마다 책임 주체·기한 명시)

    ## Appendix
    (회의 중 언급된 외부 자료·참고 사례·후속 제출 자료를 ○로 정리. 없으면 이 섹션 생략)

    [⑤ 필수 준수 규칙]
    - ( ) 안의 지침과 자리표시자는 실제 내용으로 채우고, 지침 문구 자체는 출력하지 말 것
    - 1·2·5·6번 섹션 제목은 그대로 사용. 3·4번만 회의 성격에 맞게 제목 변경 가능
    - 고유명사·약어는 원문 그대로 유지(Azure, M365, PoC, MSP, API, EA, CSP 등). 영어 약어는 처음 등장 시 풀네임 병기 검토
    - 코드명·제품명은 원문 표기 유지(예: Bedrock AgentCore)
    - 사내 민감정보(고객사명·금액·인명)는 전사본에 있으면 그대로 유지하되, 추측·창작 금지
    - 전사본에 없는 내용은 절대 추가하지 말 것
    """
).strip()

# generate.js 경로 (pipeline/ 기준으로 상위 tools/)
_SCRIPT_DIR = Path(__file__).resolve().parent
_GENERATE_JS = _SCRIPT_DIR.parent / "tools" / "generate.js"


# ─────────────────────────────────────────
# Ollama 백엔드
# ─────────────────────────────────────────
def _generate_ollama(transcript_text: str, model: str) -> str:
    """Ollama 로컬 LLM으로 회의록 마크다운 생성."""
    import urllib.request

    # qwen3 계열은 /no_think 접미사로 thinking 토큰 비활성화 → 속도↑ 형식 준수↑
    user_msg = f"/no_think\n\n다음 회의 전사본으로 위 형식에 맞춰 회의록을 작성하세요. 맨 앞에 ## 회의 정보, 이어서 ## 1 부터 ## 6 까지 본문 섹션과 (있으면) ## Appendix 를 모두 출력할 것.\n\n{transcript_text}"

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": MINUTES_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 12000},
    }).encode()

    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read())
    return result["message"]["content"].strip()


# ─────────────────────────────────────────
# OpenAI API 백엔드
# ─────────────────────────────────────────
def _generate_openai(transcript_text: str, model: str) -> str:
    """OpenAI API로 회의록 마크다운 생성. correct.py와 동일한 패턴."""
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": MINUTES_SYSTEM},
            {"role": "user",   "content": f"다음 회의 전사본으로 위 형식에 맞춰 회의록을 작성하세요. 맨 앞에 ## 회의 정보, 이어서 ## 1 부터 ## 6 까지 본문 섹션과 (있으면) ## Appendix 를 모두 출력할 것.\n\n{transcript_text}"},
        ],
        temperature=0.3,
    )
    return (resp.choices[0].message.content or "").strip()


# ─────────────────────────────────────────
# Claude API 백엔드
# ─────────────────────────────────────────
def _generate_claude(transcript_text: str, model: str, max_tokens: int = 4000) -> str:
    """Claude API로 회의록 마크다운 생성."""
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=MINUTES_SYSTEM,
        messages=[{"role": "user",
                   "content": f"다음 회의 전사본으로 회의록 초안을 작성하세요.\n\n{transcript_text}"}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


# ─────────────────────────────────────────
# 공통 진입점
# ─────────────────────────────────────────
def generate_minutes_draft(
    transcript_text: str,
    *,
    backend: str = "openai",          # "openai" | "claude" | "ollama"
    model: str = "gpt-4o-mini",       # 기본값: OpenAI gpt-4o-mini
    max_tokens: int = 4000,
) -> str:
    """전사본 → 회의록 마크다운 (백엔드 선택 가능).

    Args:
        backend: "openai" / "claude" / "ollama"
        model  : 각 백엔드 모델명
                 openai  → "gpt-4o-mini"(기본, 저렴) | "gpt-4o"(고품질)
                 claude  → "claude-sonnet-4-6"
                 ollama  → "qwen3:8b" | "gemma4:e2b"
    """
    if backend == "openai":
        return _generate_openai(transcript_text, model)
    elif backend == "claude":
        return _generate_claude(transcript_text, model, max_tokens)
    else:
        return _generate_ollama(transcript_text, model)


# ─────────────────────────────────────────
# 마크다운 → .docx 변환
# ─────────────────────────────────────────
def generate_minutes_docx(
    markdown_text: str,
    meeting_info: dict,
    out_dir: Path,
    today: str = None,
) -> Path:
    """회의록 마크다운 + 회의 정보 → AX 표준 .docx.

    meeting_info 키:
        subtitle   회의명
        date       회의일시
        location   회의장소
        attendees  참석자 (공백 3칸 구분)
        topic      회의주제 한 문장
    Returns:
        생성된 .docx 경로
    """
    from pipeline.md_to_meeting_data import parse_markdown_to_data

    meeting_data = parse_markdown_to_data(markdown_text, meeting_info, today=today)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / meeting_data["filename"]

    # JSON 임시파일 → generate.js → .docx
    data_file = Path(tempfile.mktemp(suffix=".json"))
    data_file.write_text(
        json.dumps({**meeting_data, "out_path": str(out_path)}, ensure_ascii=False),
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            ["node", str(_GENERATE_JS), "--data", str(data_file)],
            check=True, capture_output=True, text=True,
        )
        # generate.js 가 "OK:<path>" 를 stdout 에 씀
        for line in result.stdout.splitlines():
            if line.startswith("OK:"):
                out_path = Path(line[3:])
    finally:
        data_file.unlink(missing_ok=True)

    return out_path
