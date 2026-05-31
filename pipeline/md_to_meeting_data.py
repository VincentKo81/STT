"""마크다운 회의록 → generate.js 용 MEETING_DATA 딕셔너리 변환.

gpt-4o / Claude 가 생성한 6섹션 마크다운을 파싱해서
tools/generate.js 가 받는 JSON 구조로 만든다.

지원 형식:
    ## 1. 회의 개요
    ○ 항목

    ## 2. 주요 논의 사항
    ### 2.1 소제목
    ○ 1단계 항목
    - 2단계 항목
    · 3단계 항목

    ## 6. 주요 합의 사항
    1. 합의 내용
"""
import re
from pathlib import Path


def _safe_filename(text: str, max_len: int = 20) -> str:
    """텍스트를 파일명에 쓸 수 있는 문자열로 변환."""
    s = re.sub(r'[^\w가-힣]', '_', text)
    s = re.sub(r'_+', '_', s).strip('_')
    return s[:max_len]


def parse_markdown_to_data(markdown: str, meeting_info: dict) -> dict:
    """마크다운 → generate.js MEETING_DATA dict.

    Args:
        markdown   : 6섹션 마크다운 문자열
        meeting_info: { subtitle, date, location, attendees, topic }
    Returns:
        generate.js 가 받을 수 있는 완전한 dict
    """
    # ── 상태 변수 ──────────────────────────────────────────────
    section      = None   # 'overview' | 'body' | 'agreements' | 'appendix'
    body_sec     = None   # sections 마지막 항목 참조
    body_sub     = None   # subsections 마지막 항목 참조

    overview   : list[str]  = []
    sections   : list[dict] = []
    agreements : list[str]  = []
    appendix   : list[str]  = []

    BULLETS = {
        '○': 0,   # U+25CB
        '◦': 0,   # U+25E6  (일부 모델이 쓰는 변형)
        '-': 1,
        '·': 2,   # U+00B7
        '•': 0,   # U+2022  (일부 모델)
    }

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue

        # ── 대섹션 헤더 (## N. ...) ──────────────────────────
        if line.startswith('## '):
            title = line[3:].strip()
            num_m = re.match(r'^(\d+)\.', title)
            num   = int(num_m.group(1)) if num_m else 0

            if num == 1:
                section = 'overview'
            elif num == 6:
                section = 'agreements'
            elif re.search(r'appendix|첨부', title, re.I):
                section = 'appendix'
            elif 2 <= num <= 5:
                section   = 'body'
                body_sec  = {'title': title, 'subsections': []}
                body_sub  = None
                sections.append(body_sec)
            continue

        # ── 소제목 (### N.M ...) ──────────────────────────────
        if line.startswith('### '):
            subtitle = line[4:].strip()
            if section == 'body' and body_sec is not None:
                body_sub = {'subtitle': subtitle, 'items': []}
                body_sec['subsections'].append(body_sub)
            continue

        # ── 번호 매김 (1. 2. ...) — 합의사항 ─────────────────
        num_match = re.match(r'^(\d+)\.\s+(.+)$', line)
        if num_match:
            text = num_match.group(2).strip()
            if section == 'agreements':
                agreements.append(text)
            continue

        # ── 불릿 항목 ─────────────────────────────────────────
        first_char = line[0] if line else ''
        if first_char in BULLETS and len(line) > 1 and line[1] in (' ', '\t'):
            level = BULLETS[first_char]
            text  = line[2:].strip()

            if section == 'overview':
                overview.append(text)

            elif section == 'agreements':
                agreements.append(text)

            elif section == 'appendix':
                appendix.append(text)

            elif section == 'body' and body_sec is not None:
                # 소제목 없이 바로 항목이 오면 None 소제목으로 감싸기
                if body_sub is None:
                    body_sub = {'subtitle': None, 'items': []}
                    body_sec['subsections'].append(body_sub)
                body_sub['items'].append([text, level])
            continue

    # ── 빈 섹션 보호 ──────────────────────────────────────────
    for sec in sections:
        if not sec['subsections']:
            sec['subsections'] = [{'subtitle': None, 'items': ['회의 내용 참조']}]

    # ── 파일명 자동 생성 ──────────────────────────────────────
    date_raw  = meeting_info.get('date', '')
    date_part = re.sub(r'[^\d.]', '', date_raw)[:10].replace('.', '_').rstrip('_')
    name_part = _safe_filename(meeting_info.get('subtitle', '회의록'))
    filename  = f"{date_part}_{name_part}_회의록.docx" if date_part else f"{name_part}_회의록.docx"

    return {
        # 기본정보 (사용자 입력)
        'subtitle'  : meeting_info.get('subtitle',  ''),
        'date'      : meeting_info.get('date',       ''),
        'location'  : meeting_info.get('location',   ''),
        'attendees' : meeting_info.get('attendees',  ''),
        'topic'     : meeting_info.get('topic',      ''),
        'filename'  : filename,
        # 파싱 결과
        'overview'  : overview   or ['(회의 개요 확인 필요)'],
        'sections'  : sections,
        'agreements': agreements or ['(합의 사항 확인 필요)'],
        'appendix'  : appendix   or meeting_info.get('appendix', []),
    }
