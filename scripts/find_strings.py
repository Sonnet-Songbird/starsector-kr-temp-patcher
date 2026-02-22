#!/usr/bin/env python3
"""
04_find_strings.py - 미번역 화면 스트링 추출

api_src/의 모든 Java 파일을 스캔하여:
1. 화면에 표시될 가능성 있는 문자열 후보 추출
2. final_translations.json에 없는 것만 선별
3. 안전하지 않은 사용 패턴(ID/키로 사용되는 경우) 제외

Output: intermediate/untranslated.json
"""

from pathlib import Path
import re, json, os, sys

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

GAME_CORE    = _resolve(_p['game_core'])
GAME_MODS    = _resolve(_p['game_mods'])
PATCHES      = _resolve(_p['patches'])
TRANSLATIONS = _resolve(_p['translations'])
OUTPUT_MODS  = _resolve(_p['output_mods'])
INTERMEDIATE = str(SCRIPT_DIR / 'intermediate')

def _load_all_translations():
    merged = {}
    for key in ['translations', 'api_trans', 'obf_trans']:
        p = _resolve(_p.get(key, ''))
        if p and os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                merged.update(json.load(f))
    return merged

NEW_SRC  = str(SCRIPT_DIR / 'api_src')
OUT_FILE = os.path.join(INTERMEDIATE, 'untranslated.json')

# Load existing translations
translation_map = _load_all_translations()

# UI-friendly method calls (safe to translate)
UI_CALL_PATTERNS = re.compile(
    r'(?:addOption|addParagraph|addPara|addTitle|addTooltip|setText|setTitle|'
    r'addButton|addMessage|addDescription|setDescription|addSection|addNote|'
    r'showMenu|addIntro|setButtonText|addBullet|addBlockquote|addSectionHeading|'
    r'addCustom|setStatusMessage|addError|addWarning|addInfo|addDetail|'
    r'addSubTitles|addSubtitle|setName|setTooltip|showDialog|getTooltip|'
    r'setLabel|addLabel|addRow|addCell|addHeader|getString)\s*\('
)

# Unsafe patterns: string used as ID/key/comparison
UNSAFE_PATTERNS = [
    re.compile(r'\.equals\s*\(\s*"([^"]+)"\s*\)'),
    re.compile(r'\.equalsIgnoreCase\s*\(\s*"([^"]+)"\s*\)'),
    re.compile(r'switch\s*\(\s*"([^"]+)"\s*\)'),
    re.compile(r'\.get\s*\(\s*"([^"]+)"\s*\)'),
    re.compile(r'\.put\s*\(\s*"([^"]+)"\s*,'),
    re.compile(r'\.containsKey\s*\(\s*"([^"]+)"\s*\)'),
    re.compile(r'\.remove\s*\(\s*"([^"]+)"\s*\)'),
    re.compile(r'return\s+"([^"]+)"\s*;'),
    re.compile(r'=\s*"([^"]+)"\s*;'),  # variable assignment (might be ID)
    re.compile(r'new\s+\w+\s*\(\s*"([^"]+)"\s*\)'),  # constructor with string
    re.compile(r'@\w+\s*\(\s*"([^"]+)"\s*\)'),  # annotations
    re.compile(r'(?:getId|getKey|getType|getSpec|getTag|getCommand|getSuffix|getPrefix)\s*\(\s*\)\s*\{[^}]*return\s+"([^"]+)"'),
]

# Patterns that are definitely NOT UI strings
EXCLUDE_PREFIXES = [
    'com.', 'java.', 'org.', 'fs.', 'net.', 'sun.',
    'com/', 'java/', 'org/', 'fs/',
]
EXCLUDE_CONTAINS = [
    'http', '://', '\\n', '\\t', '.class', '.jar', '.csv', '.json',
    'graphics/', 'data/', 'sounds/', 'music/',
]
PURE_ID_PATTERN = re.compile(r'^[A-Z_][A-Z0-9_]*$')  # PURE_CONSTANT
CAMELCASE_NOSPACE = re.compile(r'^[a-z][a-zA-Z0-9_]*$')  # camelCase identifier


def is_ui_string_candidate(s):
    """Returns True if the string looks like a UI display string"""
    if len(s) < 4:
        return False

    # Exclude patterns
    for prefix in EXCLUDE_PREFIXES:
        if s.startswith(prefix):
            return False
    for cont in EXCLUDE_CONTAINS:
        if cont in s:
            return False

    # Pure constant (e.g. ALL_CAPS_WITH_UNDERSCORES)
    if PURE_ID_PATTERN.match(s):
        return False

    # Pure camelCase identifier without spaces (short ones)
    if len(s) < 8 and CAMELCASE_NOSPACE.match(s) and ' ' not in s:
        return False

    # Single word without spaces and without punctuation - skip if < 8 chars
    has_space = ' ' in s
    has_punct = any(c in s for c in '.,!?:;-()[]{}')
    if not has_space and not has_punct and len(s) < 8:
        return False

    # Must start with letter or space
    if not (s[0].isalpha() or s[0] == ' '):
        return False

    # Must contain at least one English letter
    if not re.search(r'[A-Za-z]', s):
        return False

    return True


def extract_strings_from_java(filepath):
    """Extract string literals from a Java source file with context"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Find all string literals with their context (surrounding line)
    results = []
    lines = content.split('\n')

    for line_no, line in enumerate(lines):
        # Skip comment lines
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('*'):
            continue

        # Find all string literals on this line
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        for lit in literals:
            # Unescape basic escape sequences
            try:
                s = lit.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
            except:
                s = lit

            if not is_ui_string_candidate(s):
                continue

            # Check if it's used in a UI context
            ui_context = bool(UI_CALL_PATTERNS.search(line))

            # Check if it's in an unsafe context
            unsafe = False
            for pat in UNSAFE_PATTERNS:
                if pat.search(line):
                    unsafe = True
                    break

            # Additional unsafe check: look at surrounding context (3 lines)
            ctx_start = max(0, line_no - 2)
            ctx_end = min(len(lines), line_no + 3)
            context = '\n'.join(lines[ctx_start:ctx_end])

            # If in return statement
            if re.search(r'\breturn\s+"' + re.escape(lit) + r'"', context):
                unsafe = True

            # Skip unsafe non-UI strings
            if unsafe and not ui_context:
                continue

            results.append({
                'string': s,
                'line': line_no + 1,
                'ui_context': ui_context,
                'unsafe': unsafe,
                'line_text': line.strip()[:120],
            })

    return results


def main():
    os.makedirs(INTERMEDIATE, exist_ok=True)

    # Build set of already-translated strings (normalized)
    already_translated = set(translation_map.keys())

    # Track results
    all_untranslated = {}  # string → {files: [...], count: N, ui_context: bool}
    total_files = 0
    total_strings = 0

    for root, dirs, files in os.walk(NEW_SRC):
        for fname in files:
            if not fname.endswith('.java'):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, NEW_SRC).replace('\\', '/')

            candidates = extract_strings_from_java(fpath)
            total_files += 1

            for c in candidates:
                s = c['string']
                total_strings += 1

                if s in already_translated:
                    continue
                if re.search(r'[\uAC00-\uD7A3]', s):
                    continue  # Already has Korean

                if s not in all_untranslated:
                    all_untranslated[s] = {
                        'files': [],
                        'count': 0,
                        'ui_context': False,
                        'sample_line': c['line_text'],
                    }
                entry = all_untranslated[s]
                if rel not in entry['files']:
                    entry['files'].append(rel)
                entry['count'] += 1
                entry['ui_context'] = entry['ui_context'] or c['ui_context']

    print(f"Scanned {total_files} Java files, found {total_strings} string candidates")
    print(f"After filtering: {len(all_untranslated)} unique untranslated strings")

    # Prioritize UI context strings
    ui_strings = {k: v for k, v in all_untranslated.items() if v['ui_context']}
    other_strings = {k: v for k, v in all_untranslated.items() if not v['ui_context']}
    print(f"  UI context: {len(ui_strings)}")
    print(f"  Other context: {len(other_strings)}")

    # Sort by frequency (most used first)
    sorted_ui = dict(sorted(ui_strings.items(), key=lambda x: -x[1]['count']))
    sorted_other = dict(sorted(other_strings.items(), key=lambda x: -x[1]['count']))

    output = {
        'ui_strings': sorted_ui,
        'other_strings': sorted_other,
        'stats': {
            'total_java_files': total_files,
            'total_candidates': total_strings,
            'unique_untranslated': len(all_untranslated),
            'ui_context_count': len(ui_strings),
            'other_count': len(other_strings),
        }
    }

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nWritten to: {OUT_FILE}")

    # Show sample UI strings
    print("\nSample UI strings (need translation):")
    for s, info in list(sorted_ui.items())[:20]:
        print(f"  [{info['count']}x] {repr(s[:70])}")
        print(f"       {info['sample_line'][:80]}")


if __name__ == '__main__':
    main()
