import os
import re
import json
import shutil
import hashlib
import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DAILY_ROOT = os.path.join(BASE_DIR, 'DailyPlan', 'daily-plans')

TASK_STATUS_MAP = {
    '[ ]': 'todo',
    '[x]': 'done',
    '[~]': 'partial',
    '[!]': 'cancelled',
    '[>]': 'in_progress',
    '[?]': 'need_help',
}

STATUS_TO_MARK = {v: k for k, v in TASK_STATUS_MAP.items()}

TASK_MARK_RE = re.compile(r"^\s*-\s*(\[(?: |x|~|!|>|\?)\])\s*(.*)$", re.IGNORECASE)
H1_RE = re.compile(r"^#\s+")
H2_RE = re.compile(r"^##\s+")
H3_RE = re.compile(r"^###\s+")

@dataclass
class TaskItem:
    line_index: int
    raw: str
    status_mark: str
    status: str
    text: str
    section: str
    subsection: Optional[str] = None

@dataclass
class Section:
    title: str
    start: int
    end: int


def _today_ymd() -> Tuple[str, str, str]:
    now = datetime.datetime.now()
    return now.strftime('%Y'), now.strftime('%m'), now.strftime('%d')


def get_today_path() -> Dict[str, Any]:
    y, m, d = _today_ymd()
    path = os.path.join(DAILY_ROOT, y, m, f'{d}.md')
    return {
        'date': f'{y}-{m}-{d}',
        'path': path,
        'exists': os.path.exists(path)
    }


def _ensure_parents(file_path: str) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)


def _load_file_lines(path: str) -> List[str]:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().splitlines()


def _save_file_lines(path: str, lines: List[str]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


FALLBACK_TEMPLATE = """# 📅 今日计划

**☀️ 天气：晴朗，温度 25~32°C，中国·上海**

## 🎯 今日重点任务

### 学习与成长
- [ ] 示例任务：阅读30分钟

## 🌞 生活安排

### 用餐时间
- [ ] 早餐 (8:00 - 8:30)
- [ ] 午餐 (12:00 - 12:30)
- [ ] 晚餐 (18:00 - 18:30)

## 🌙 晚间总结

### 📝 今日总结 (21:00 - 21:30)
- [ ] 回顾今日完成情况

### 📋 明日计划 (21:30 - 22:00)
- [ ] 制定明日计划

## 📊 今日目标

### 🎯 主要目标
- 保持良好作息

## 💡 学习笔记

"""


def _guess_template_source() -> Optional[str]:
    # 尝试优先复制最近一份已有的同月文件作为模板
    info = get_today_path()
    y, m, _ = info['date'].split('-')
    month_dir = os.path.join(DAILY_ROOT, y, m)
    if os.path.isdir(month_dir):
        md_files = [f for f in os.listdir(month_dir) if f.endswith('.md')]
        if md_files:
            md_files.sort()
            return os.path.join(month_dir, md_files[-1])
    # 退化到上层 README.md 中的格式不可控，改用内置模板
    return None


def create_today_from_template(force: bool = False) -> Dict[str, Any]:
    info = get_today_path()
    path = info['path']
    if os.path.exists(path) and not force:
        return {'created': False, 'path': path, 'reason': 'exists'}
    _ensure_parents(path)
    src = _guess_template_source()
    if src and os.path.exists(src):
        content = '\n'.join(_load_file_lines(src)) + '\n'
        # 简单规范化：替换首行标题为“今日计划”
        lines = content.splitlines()
        if lines and H1_RE.match(lines[0]):
            lines[0] = '# 📅 今日计划'
        _save_file_lines(path, lines)
        return {'created': True, 'path': path, 'source': src}
    else:
        _save_file_lines(path, FALLBACK_TEMPLATE.splitlines())
        return {'created': True, 'path': path, 'source': 'fallback'}


def _parse_sections(lines: List[str]) -> List[Section]:
    sections: List[Section] = []
    current: Optional[Section] = None
    for i, line in enumerate(lines):
        if H2_RE.match(line):
            if current:
                current.end = i - 1
                sections.append(current)
            current = Section(title=line.strip().lstrip('#').strip(), start=i, end=len(lines)-1)
    if current:
        sections.append(current)
    return sections


def _section_range(lines: List[str], title_prefix: str) -> Optional[Tuple[int, int]]:
    sec_list = _parse_sections(lines)
    for sec in sec_list:
        if sec.title.startswith(title_prefix):
            return sec.start, sec.end
    return None


def _iter_tasks(lines: List[str], start: int, end: int, parent_title: str) -> List[TaskItem]:
    results: List[TaskItem] = []
    current_sub: Optional[str] = None
    for idx in range(start, end + 1):
        line = lines[idx]
        if H3_RE.match(line):
            current_sub = line.strip().lstrip('#').strip()
            continue
        m = TASK_MARK_RE.match(line)
        if m:
            mark, text = m.group(1), m.group(2).strip()
            status = TASK_STATUS_MAP.get(mark.lower(), 'todo')
            results.append(TaskItem(
                line_index=idx,
                raw=line,
                status_mark=mark,
                status=status,
                text=text,
                section=parent_title,
                subsection=current_sub,
            ))
    return results


def read_structured(path: Optional[str] = None) -> Dict[str, Any]:
    info = get_today_path() if path is None else {'path': path, 'exists': os.path.exists(path)}
    if not info['exists']:
        return {'exists': False, 'path': info['path'] if 'path' in info else path}
    lines = _load_file_lines(info['path'])
    sections = _parse_sections(lines)
    payload: List[Dict[str, Any]] = []
    for sec in sections:
        tasks = _iter_tasks(lines, sec.start, sec.end, sec.title)
        payload.append({
            'title': sec.title,
            'range': [sec.start, sec.end],
            'tasks': [task.__dict__ for task in tasks]
        })
    return {
        'exists': True,
        'path': info['path'],
        'sections': payload
    }


def _find_task_line(lines: List[str], task_text: str) -> Optional[int]:
    for i, line in enumerate(lines):
        m = TASK_MARK_RE.match(line)
        if not m:
            continue
        text = m.group(2).strip()
        if text == task_text:
            return i
    return None


def set_task_status(task_text: str, status: str, path: Optional[str] = None) -> Dict[str, Any]:
    info = get_today_path() if path is None else {'path': path, 'exists': os.path.exists(path)}
    if not info['exists']:
        return {'updated': False, 'error': 'not_found', 'path': info['path']}
    lines = _load_file_lines(info['path'])
    idx = _find_task_line(lines, task_text)
    if idx is None:
        return {'updated': False, 'error': 'task_not_found'}
    m = TASK_MARK_RE.match(lines[idx])
    mark, text = m.group(1), m.group(2)
    new_mark = STATUS_TO_MARK.get(status, '[ ]')
    lines[idx] = f"- {new_mark} {text}"
    _save_file_lines(info['path'], lines)
    return {'updated': True, 'line': idx, 'new_status': status}


def add_task(section_title_prefix: str, task_text: str, status: str = 'todo', path: Optional[str] = None) -> Dict[str, Any]:
    info = get_today_path() if path is None else {'path': path, 'exists': os.path.exists(path)}
    if not info['exists']:
        return {'inserted': False, 'error': 'not_found', 'path': info['path']}
    lines = _load_file_lines(info['path'])
    rng = _section_range(lines, section_title_prefix)
    if not rng:
        return {'inserted': False, 'error': 'section_not_found'}
    start, end = rng
    insert_at = end
    # 向上回溯找到最后一个任务行后插入
    for i in range(end, start, -1):
        if lines[i].strip():
            insert_at = i + 1
            break
    mark = STATUS_TO_MARK.get(status, '[ ]')
    lines.insert(insert_at, f"- {mark} {task_text}")
    _save_file_lines(info['path'], lines)
    return {'inserted': True, 'line': insert_at}


def append_note(section_title_prefix: str, note_line: str, path: Optional[str] = None) -> Dict[str, Any]:
    info = get_today_path() if path is None else {'path': path, 'exists': os.path.exists(path)}
    if not info['exists']:
        return {'appended': False, 'error': 'not_found', 'path': info['path']}
    lines = _load_file_lines(info['path'])
    rng = _section_range(lines, section_title_prefix)
    if not rng:
        return {'appended': False, 'error': 'section_not_found'}
    start, end = rng
    insert_at = end
    for i in range(end, start, -1):
        if lines[i].strip():
            insert_at = i + 1
            break
    # 追加为普通子弹
    lines.insert(insert_at, f"- {note_line}")
    _save_file_lines(info['path'], lines)
    return {'appended': True, 'line': insert_at}


def rollover_incomplete(path: Optional[str] = None) -> Dict[str, Any]:
    info = get_today_path() if path is None else {'path': path, 'exists': os.path.exists(path)}
    if not info['exists']:
        return {'moved': 0, 'error': 'not_found', 'path': info['path']}
    lines = _load_file_lines(info['path'])
    tasks_to_move: List[str] = []
    for line in lines:
        m = TASK_MARK_RE.match(line)
        if not m:
            continue
        mark, text = m.group(1), m.group(2).strip()
        status = TASK_STATUS_MAP.get(mark.lower(), 'todo')
        if status in ('todo', 'partial', 'in_progress'):
            tasks_to_move.append(text)
    # 创建明天文件
    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)
    y, m, d = tomorrow.strftime('%Y'), tomorrow.strftime('%m'), tomorrow.strftime('%d')
    new_path = os.path.join(DAILY_ROOT, y, m, f'{d}.md')
    if not os.path.exists(new_path):
        _ensure_parents(new_path)
        _save_file_lines(new_path, FALLBACK_TEMPLATE.splitlines())
    # 将任务追加到“## 🎯 今日重点任务”末尾
    new_lines = _load_file_lines(new_path)
    rng = _section_range(new_lines, '🎯') or _section_range(new_lines, '今日重点任务')
    if not rng:
        # 若无该分节，追加到文件末尾
        insert_at = len(new_lines)
    else:
        start, end = rng
        insert_at = end + 1
    for t in tasks_to_move:
        new_lines.insert(insert_at, f"- [ ] {t}")
        insert_at += 1
    _save_file_lines(new_path, new_lines)
    return {'moved': len(tasks_to_move), 'new_file_path': new_path}


# 简易自检入口
if __name__ == '__main__':
    print(json.dumps(get_today_path(), ensure_ascii=False, indent=2))
