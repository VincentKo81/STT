"""마크다운 회의록 → generate.js 용 데이터 변환.

LLM이 생성한 마크다운을 파싱해서 tools/generate.js 가 받는 JSON 구조로 만든다.

설계:
- 섹션을 **등장 순서대로 blocks 배열에 보존** → 섹션 순서·제목 자유 (사용자가 5↔6 순서·3·4 제목 변경 가능)
- '합의' 포함 섹션은 번호매김(numbered), 그 외는 불릿(bullets)
- '## 회의 정보' 블록에서 회의명·일시·장소·참석자·주제를 추론
- 사이드바 입력값이 있으면 그것을 우선, 없으면 LLM 추론값 사용
"""
import re

BULLETS = {'○': 0, '◦': 0, '•': 0, '-': 1, '·': 2}
_INFO_KEYS = {
    '회의명': 'subtitle', '일시': 'date', '장소': 'location',
    '참석자': 'attendees', '주제': 'topic',
}


def _safe_filename(text, max_len=24):
    s = re.sub(r'[^\w가-힣]', '_', text or '회의록')
    s = re.sub(r'_+', '_', s).strip('_')
    return s[:max_len] or '회의록'


def parse_markdown_to_data(markdown: str, meeting_info: dict, today: str = None) -> dict:
    """마크다운 → generate.js 데이터.

    Args:
        markdown    : LLM이 생성한 회의록 마크다운 (## 회의 정보 + 6섹션 + Appendix)
        meeting_info: 사이드바 입력 { subtitle, date, location, attendees, topic }
                      값이 비어있으면 LLM 추론값으로 대체됨
    """
    inferred: dict = {}      # LLM이 추론한 회의정보
    blocks: list = []        # 본문 섹션 (등장 순서 보존)
    appendix: list = []
    cur = None               # 현재 블록 dict / 'appendix' / None
    cur_sub = None           # 현재 소제목 dict
    in_info = False          # '## 회의 정보' 블록 안인지

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue

        # ── 대섹션 헤더 (## ...) ──
        if line.startswith('## '):
            title = line[3:].strip()
            in_info = False
            cur_sub = None

            if re.search(r'회의\s*정보', title):
                in_info = True
                cur = None
            elif re.search(r'appendix|첨부', title, re.I):
                cur = 'appendix'
            else:
                # 제목을 번호 접두사 포함 그대로 보존 (순서·제목 자유)
                is_numbered = bool(re.search(r'합의', title))
                cur = {
                    'title': title,
                    'type': 'numbered' if is_numbered else 'bullets',
                    'subsections': [],
                    'items': [],
                }
                blocks.append(cur)
            continue

        # ── 소제목 (### ...) ──
        if line.startswith('### '):
            if isinstance(cur, dict) and cur['type'] == 'bullets':
                cur_sub = {'subtitle': line[4:].strip(), 'items': []}
                cur['subsections'].append(cur_sub)
            continue

        # ── 회의 정보: "- 키: 값" ──
        if in_info:
            m = re.match(r'^[-○•·]\s*([^:：]+)\s*[:：]\s*(.+)$', line)
            if m:
                key, val = m.group(1).strip(), m.group(2).strip()
                if key in _INFO_KEYS and val and '확인 필요' not in val:
                    inferred[_INFO_KEYS[key]] = val
            continue

        # ── 번호 항목 (1. 2. ...) ──
        nm = re.match(r'^(\d+)\.\s+(.+)$', line)
        if nm:
            text = nm.group(2).strip()
            if cur == 'appendix':
                appendix.append(text)
            elif isinstance(cur, dict):
                if cur['type'] == 'numbered':
                    cur['items'].append(text)
                else:
                    if cur_sub is None:
                        cur_sub = {'subtitle': None, 'items': []}
                        cur['subsections'].append(cur_sub)
                    cur_sub['items'].append([text, 0])
            continue

        # ── 불릿 항목 (○ - ·) ──
        fc = line[0]
        if fc in BULLETS and len(line) > 1 and line[1] in (' ', '\t'):
            level = BULLETS[fc]
            text = line[2:].strip()
            if cur == 'appendix':
                appendix.append(text)
            elif isinstance(cur, dict):
                if cur['type'] == 'numbered':
                    cur['items'].append(text)
                else:
                    if cur_sub is None:
                        cur_sub = {'subtitle': None, 'items': []}
                        cur['subsections'].append(cur_sub)
                    cur_sub['items'].append([text, level])
            continue

    # ── 회의정보 병합: 사이드바 입력 우선, 없으면 LLM 추론 ──
    def pick(key):
        v = (meeting_info.get(key) or '').strip()
        return v if v else inferred.get(key, '')

    subtitle  = pick('subtitle')  or '(회의명 미상)'
    date      = pick('date')      or today or '(일시 확인 필요)'
    location  = pick('location')  or '(장소 확인 필요)'
    attendees = pick('attendees') or '(참석자 확인 필요)'
    topic     = pick('topic')     or subtitle

    # ── 빈 bullets 블록 보호 ──
    for blk in blocks:
        if blk['type'] == 'bullets' and not blk['subsections']:
            blk['subsections'] = [{'subtitle': None, 'items': [['(내용 확인 필요)', 0]]}]

    # ── 파일명 ──
    date_part = re.sub(r'[^\d.]', '', date)[:10].replace('.', '_').strip('_')
    name_part = _safe_filename(subtitle)
    filename = (f"{date_part}_{name_part}_회의록.docx"
                if date_part else f"{name_part}_회의록.docx")

    return {
        'subtitle': subtitle, 'date': date, 'location': location,
        'attendees': attendees, 'topic': topic, 'filename': filename,
        'blocks': blocks,
        'appendix': appendix or meeting_info.get('appendix', []),
        # 앱에서 "AI가 자동으로 채운 항목" 표시용
        'ai_filled': sorted(inferred.keys()),
    }
