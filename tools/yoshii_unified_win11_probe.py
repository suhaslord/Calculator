import json, subprocess, time
from pathlib import Path
from pywinauto import Desktop, keyboard

OUT = Path('yoshii_unified_result')
OUT.mkdir(exist_ok=True)
PROMPT1 = 'You are tutoring a student. The student says: 1/3 + 1/4 = 2/7'
PROMPT2 = 'I added the tops because they are parts, and I added the bottoms because they are the number of pieces.'
SIGNIN_MARKERS = [
    'sign in',
    'choose a microsoft account',
    'email, phone, or skype',
    'pick an account',
    'use another account',
]

def run_ps(script):
    return subprocess.run(
        ['powershell.exe', '-NoProfile', '-Command', script],
        capture_output=True, text=True, timeout=30
    )

def discover_apps():
    ps = "Get-StartApps | Where-Object { $_.Name -match 'Copilot|Microsoft 365|Office' } | Select-Object Name,AppID | ConvertTo-Json -Compress"
    p = run_ps(ps)
    raw = p.stdout.strip()
    (OUT / 'start_apps_raw.txt').write_text(raw + '\nSTDERR:\n' + p.stderr, encoding='utf-8')
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    preferred = []
    for item in data:
        name = (item.get('Name') or '').lower()
        appid = item.get('AppID') or ''
        score = 0
        if 'copilot' in name:
            score += 10
        if 'microsoft 365' in name:
            score += 5
        if 'office' in name:
            score += 1
        if 'copilot' in appid.lower():
            score += 4
        preferred.append((score, item))
    preferred.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in preferred]

def launch_discovered():
    apps = discover_apps()
    (OUT / 'discovered_apps.json').write_text(json.dumps(apps, indent=2, ensure_ascii=False), encoding='utf-8')
    if not apps:
        raise RuntimeError('No Copilot/Microsoft 365/Office Start app discovered')
    errors = []
    for item in apps:
        appid = item.get('AppID')
        if not appid:
            continue
        try:
            print('LAUNCH_APP', item.get('Name'), appid)
            subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{appid}'])
            time.sleep(18)
            return item
        except Exception as e:
            errors.append({'item': item, 'error': repr(e)})
    raise RuntimeError(f'Could not launch discovered apps: {errors!r}')

app = launch_discovered()
desktop = Desktop(backend='uia')

def candidate_windows():
    out = []
    for w in desktop.windows():
        try:
            title = (w.window_text() or '').lower()
            cls = w.class_name()
            descendants = []
            try:
                descendants = w.descendants()
            except Exception:
                pass
            has_relevant_aid = False
            for c in descendants[:500]:
                try:
                    aid = (c.element_info.automation_id or '').lower()
                    if any(x in aid for x in ('composer', 'inputtextbox', 'chat', 'copilot')):
                        has_relevant_aid = True
                        break
                except Exception:
                    pass
            if any(x in title for x in ('copilot', 'microsoft 365', 'office')) or has_relevant_aid or cls in ('Microsoft 365 Copilot Host','WinUIDesktopWin32WindowClass'):
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
    vals = []
    for r in rows:
        for e in r.get('elements', []):
            if e.get('visible') and e.get('text'):
                vals.append(e.get('text'))
    return '\n'.join(vals)

def find_composer():
    candidates = []
    for w in candidate_windows():
        try:
            for c in w.descendants():
                try:
                    if not c.is_visible() or not c.is_enabled():
                        continue
                    aid = (c.element_info.automation_id or '').lower()
                    ct = c.element_info.control_type
                    txt = (c.window_text() or '').lower()
                    score = 0
                    if ct == 'Edit': score += 3
                    if any(x in aid for x in ('inputtextbox','composer','chat','message','prompt')): score += 6
                    if any(x in txt for x in ('ask', 'message', 'copilot')): score += 2
                    if ct in ('Edit','Document') and score >= 3:
                        candidates.append((score, c))
                except Exception:
                    pass
        except Exception:
            pass
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] if candidates else None

def find_submit():
    for w in candidate_windows():
        try:
            controls = w.descendants()
        except Exception:
            continue
        best = []
        for c in controls:
            try:
                if not c.is_visible() or not c.is_enabled() or c.element_info.control_type != 'Button':
                    continue
                aid = (c.element_info.automation_id or '').lower()
                text = (c.window_text() or '').lower()
                score = 0
                if 'submit' in aid or 'send' in aid: score += 6
                if text in ('send','submit','send message'): score += 4
                if score:
                    best.append((score,c))
            except Exception:
                pass
        if best:
            best.sort(key=lambda x: x[0], reverse=True)
            return best[0][1]
    return None

def sign_in_wall(text):
    low = text.lower()
    return any(marker in low for marker in SIGNIN_MARKERS)

def set_text(control, text):
    try:
        control.click_input()
    except Exception:
        try: control.set_focus()
        except Exception: pass
    time.sleep(0.5)
    try:
        control.set_edit_text(text)
    except Exception:
        keyboard.send_keys('^a')
        keyboard.send_keys(text, with_spaces=True)

def submit_turn(text, tag):
    composer = find_composer()
    if composer is None:
        raise RuntimeError(f'No composer before {tag}')
    set_text(composer, text)
    print('SUBMIT_TEXT', tag, repr(text))
    btn = find_submit()
    if btn is not None:
        try:
            btn.invoke()
        except Exception:
            btn.click_input()
    else:
        composer.set_focus()
        keyboard.send_keys('{ENTER}')
    time.sleep(2)

def wait_for_change(prior, tag, max_wait=100):
    start = time.time()
    last = ''
    stable = 0
    latest = prior
    while time.time() - start < max_wait:
        time.sleep(3)
        rows = snapshot(f'{tag}_poll')
        latest = visible_text(rows)
        changed = latest != prior and len(latest) > len(prior) + 30
        if changed and latest == last:
            stable += 1
        else:
            stable = 0
        last = latest
        print('POLL', tag, int(time.time()-start), 'chars', len(latest), 'stable', stable)
        if changed and stable >= 2:
            break
    return latest

record = {'discovered_app': app, 'prompt1': PROMPT1, 'prompt2': PROMPT2}
try:
    before = snapshot('before')
    before_text = visible_text(before)
    record['before_visible_text'] = before_text
    if sign_in_wall(before_text) and find_composer() is None:
        record['status'] = 'sign_in_required'
    elif find_composer() is None:
        record['status'] = 'no_composer'
    else:
        submit_turn(PROMPT1, 'turn1')
        turn1 = wait_for_change(before_text, 'turn1')
        record['turn1_visible_text'] = turn1
        if sign_in_wall(turn1):
            record['status'] = 'sign_in_required_after_turn1'
        elif len(turn1) <= len(before_text) + len(PROMPT1) + 30:
            record['status'] = 'invalid_turn1'
        else:
            submit_turn(PROMPT2, 'turn2')
            turn2 = wait_for_change(turn1, 'turn2')
            record['turn2_visible_text'] = turn2
            if sign_in_wall(turn2):
                record['status'] = 'sign_in_required_after_turn2'
            elif len(turn2) <= len(turn1) + len(PROMPT2) + 20:
                record['status'] = 'invalid_turn2'
            else:
                record['status'] = 'completed'
except Exception as e:
    record['status'] = 'error'
    record['error'] = repr(e)
    try:
        record['error_snapshot'] = snapshot('error')
    except Exception as e2:
        record['snapshot_error'] = repr(e2)
finally:
    (OUT / 'record.json').write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    print('UNIFIED_RECORD', json.dumps({k: record.get(k) for k in ['discovered_app','status','error']}, ensure_ascii=False))
