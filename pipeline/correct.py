"""GPT 기반 청크 보정 (선택 단계).

주의: GPT는 음성을 직접 듣지 않고 텍스트 문맥만으로 교정합니다.
심하게 뭉개진 고유명사는 완전 복원되지 않을 수 있으므로,
가능하면 전사 단계의 vocabulary biasing(transcribe.py)으로 원천에서 잡는 것이 우선입니다.
"""
from pathlib import Path

CORRECTION_SYSTEM = (
    "당신은 한국어/영어 혼용 회의 전사문 교정기입니다. 규칙: "
    "(1) 내용을 요약하거나 삭제하지 말 것 — 전사문의 길이와 의미를 유지. "
    "(2) 어색한 띄어쓰기, 빠진 문장부호, 명백한 STT 오인식 단어만 교정. "
    "(3) 아래 [도메인 용어]가 잘못 표기됐다면 올바른 표기로 교정. "
    "(4) 입력 줄 수와 순서를 그대로 유지(타임스탬프 라인이 있으면 보존). "
    "(5) 새로운 내용을 추측·창작하지 말 것."
)


def _chunks(lines, n):
    for i in range(0, len(lines), n):
        yield lines[i : i + n]


def correct_text(text, *, model, chunk_lines, glossary_path=None, on_progress=None):
    """전사 텍스트를 chunk_lines 단위로 나눠 순차 보정 후 합쳐 반환."""
    from openai import OpenAI  # 지연 import

    client = OpenAI()
    glossary = ""
    if glossary_path and Path(glossary_path).exists():
        glossary = Path(glossary_path).read_text(encoding="utf-8")

    lines = text.splitlines()
    total = (len(lines) + chunk_lines - 1) // chunk_lines
    out = []
    for idx, chunk in enumerate(_chunks(lines, chunk_lines), 1):
        user = f"[도메인 용어]\n{glossary}\n\n[교정 대상]\n" + "\n".join(chunk)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": CORRECTION_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        out.append((resp.choices[0].message.content or "").strip())
        if on_progress:
            on_progress(idx, total)
    return "\n".join(out)
