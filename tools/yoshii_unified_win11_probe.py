import json, subprocess, time
from pathlib import Path
from pywinauto import Desktop, keyboard

OUT = Path('yoshii_unified_result')
OUT.mkdir(exist_ok=True)
APPIDS = [
    'Microsoft.MicrosoftOfficeHub_8wekyb3d8bbwe!Microsoft.MicrosoftOfficeHub',
    'Microsoft.MicrosoftOfficeHub_8wekyb3d8bbwe!App',
]
PROMPT = 'You are tutoring a student. The student says: 1/3 + 1/4 = 2/7'

def launch():
    for appid in APPIDS:
        try:
            subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{appid}'])
            time.sleep(15)
            return appid
        except Exception:
            pass
    raise RuntimeError('No unified Copilot app id launched')

appid = launch()
desktop = Desktop(backend='uia')

def candidate_windows():
    out = []
    for w in desktop.windows():
        try:
            t = w.window_text().lower()
            c = w.class_name()
            if 'copilot' in t or 'microsoft 365' in t or 'office' in t or c in ('Microsoft 365 Copilot Host','WinUIDesktopWin32WindowClass'):
                out.append(w)
        except Exception:
            pass
    return out

def snapshot(tag):
    rows = []
    for wi, w in enumerate(candidate_windows()):
        els = []
        try:
            for c in w.descendants():
                try:
                    els.append({
                        'text': c.window_text(),
                        'control_type': c.element_info.control_type,
                        'automation_id': c.element_info.automation_id,
                        'class_name': c.element_info.class_name,
                        'visible': c.is_visible(),
                        'enabled': c.is_enabled(),
                        'rect': str(c.rectangle()),
                    })
                except Exception:
                    pass
            rows.append({'index': wi, 'title': w.window_text(), 'class_name': w.class_name(), 'elements': els})
        except Exception as e:
            rows.append({'index': wi, 'error': repr(e)})
    (OUT / f'{tag}.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
    return rows

def visible_text(rows):
    vals=[]
    for r in rows:
        for e in r.get('elements', []):
            if e.get('visible') and e.get('text'):
                vals.append(e.get('text'))
    return '\n'.join(vals)

def find_composer():
    for w in candidate_windows():
        try:
            for c in w.descendants():
                if not c.is_visible() or not c.is_enabled():
                    continue
                aid = c.element_info.automation_id or ''
                ct = c.element_info.control_type
                txt = (c.window_text() or '').lower()
                if ct == 'Edit' and ('input' in aid.lower() or 'chat' in aid.lower() or 'message' in aid.lower() or not aid):
                    return c
                if ct == 'Document' and ('message' in txt or 'ask' in txt):
                    return c
        except Exception:
            pass
    return None

before = snapshot('before')
text_before = visible_text(before)
record = {'app_id': appid, 'prompt': PROMPT, 'before_visible_text': text_before}

composer = find_composer()
record['composer_found'] = bool(composer)
if composer is not None:
    try:
        composer.click_input()
        time.sleep(1)
        try:
            composer.set_edit_text(PROMPT)
        except Exception:
            keyboard.send_keys(PROMPT, with_spaces=True)
        keyboard.send_keys('{ENTER}')
        time.sleep(30)
        after = snapshot('after_prompt')
        record['after_visible_text'] = visible_text(after)
    except Exception as e:
        record['submit_error'] = repr(e)
else:
    lower = text_before.lower()
    if 'choose a microsoft account' in lower or 'sign in' in lower or 'email, phone, or skype' in lower:
        record['status'] = 'account_required'
    else:
        record['status'] = 'no_composer'

(OUT / 'record.json').write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
print('UNIFIED_RECORD', json.dumps({k: record.get(k) for k in ['app_id','composer_found','status','submit_error']}, ensure_ascii=False))
