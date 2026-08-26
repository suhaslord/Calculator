import json, os, subprocess, time
from pathlib import Path
from pywinauto import Desktop, keyboard

OUT = Path('yoshii_result')
OUT.mkdir(exist_ok=True)
APPID = 'Microsoft.Copilot_8wekyb3d8bbwe!App'
CASE_ID = os.environ['CASE_ID']
CONDITION = os.environ['CONDITION']

CASES = {
    'C1': ('234 x 501 = 1404', 'I multiplied 234 by 5, but I did not shift it two places because I thought the 5 just meant five.'),
    'C2': ('1/3 + 1/4 = 2/7', 'I added the tops because they are parts, and I added the bottoms because they are the number of pieces.'),
    'C3': ('-3^2 = 9', 'I thought the base was negative three even without parentheses.'),
    'C4': ('The heavier object accelerates faster in a vacuum', 'Gravity pulls harder on the heavier object, so I thought its acceleration had to be larger.'),
    'C5': ('if x = 5:', "I know = changes a variable in some code, but here I thought it meant 'is x equal to 5?' like in algebra."),
    'C6': ('20% off then 20% up returns to original', 'I was thinking +20 and -20 cancel, so I never checked what number the second 20% was taken from.'),
    'C7': ('After five heads, tails is now more likely', 'I know the coin itself has not changed. I just thought the results need to even out soon.'),
    'C8': ('range(1,10) runs the loop 10 times', "I expected it to include 10 because I read range(1,10) as 'from 1 to 10.'"),
}

DIAG_POLICY = (
    "You are tutoring a student. When a student's answer could reflect more than one misconception, "
    "do not assume the first explanation is correct. Consider multiple plausible misconceptions, ask one "
    "follow-up question that would distinguish them before correcting, and after the student's reply update "
    "your diagnosis and adapt the teaching. "
)

initial, followup = CASES[CASE_ID]
if CONDITION == 'generic':
    prompt1 = f'You are tutoring a student. The student says: {initial}'
elif CONDITION == 'diagnosis-first':
    prompt1 = DIAG_POLICY + f'The student says: {initial}'
else:
    raise ValueError(CONDITION)

subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{APPID}'])
time.sleep(15)
desktop = Desktop(backend='uia')

def looks_like_copilot(w):
    try:
        if 'copilot' in w.window_text().lower():
            return True
        if w.class_name() != 'WinUIDesktopWin32WindowClass':
            return False
        for c in w.descendants():
            try:
                if c.element_info.automation_id in (
                    'InputTextBox','HomeButton','SkipToHomeButton','GoToHomeButton','ComposerChatModeButton'
                ):
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False

def win(retries=15):
    for _ in range(retries):
        for w in desktop.windows():
            if looks_like_copilot(w):
                return w
        time.sleep(1)
    return None

def find(w, aid, ctype=None):
    if w is None:
        return None
    for c in w.descendants():
        try:
            if c.element_info.automation_id == aid and (ctype is None or c.element_info.control_type == ctype):
                return c
        except Exception:
            pass
    return None

def snapshot(tag):
    w = win()
    if w is None:
        raise RuntimeError(f'Copilot window missing at {tag}')
    vals = []
    for c in w.descendants():
        try:
            vals.append({
                'text': c.window_text(),
                'control_type': c.element_info.control_type,
                'automation_id': c.element_info.automation_id,
                'class_name': c.element_info.class_name,
                'enabled': c.is_enabled(),
                'visible': c.is_visible(),
                'rect': str(c.rectangle()),
            })
        except Exception:
            pass
    payload = {'window_title': w.window_text(), 'window_class': w.class_name(), 'elements': vals}
    (OUT / f'{tag}.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return payload

def visible_signature():
    w = win(retries=4)
    if w is None:
        return None, []
    vals = []
    for c in w.descendants():
        try:
            if not c.is_visible():
                continue
            text = c.window_text().strip()
            if text:
                vals.append({
                    'text': text,
                    'control_type': c.element_info.control_type,
                    'automation_id': c.element_info.automation_id,
                    'class_name': c.element_info.class_name,
                })
        except Exception:
            pass
    sig = '\n'.join(f"{v['control_type']}|{v['automation_id']}|{v['text']}" for v in vals)
    return sig, vals

def wait_stable(tag, min_wait=10, max_wait=105):
    start = time.time()
    last = None
    stable = 0
    latest = []
    while time.time() - start < max_wait:
        time.sleep(3)
        sig, vals = visible_signature()
        elapsed = int(time.time() - start)
        if sig is None:
            print('POLL', tag, elapsed, 'WINDOW_MISSING')
            continue
        print('POLL', tag, elapsed, 'chars', len(sig))
        if sig == last and elapsed >= min_wait:
            stable += 1
        else:
            stable = 0
        last, latest = sig, vals
        if stable >= 2:
            print('STABLE', tag, elapsed)
            break
    (OUT / f'{tag}_visible.json').write_text(json.dumps(latest, indent=2, ensure_ascii=False), encoding='utf-8')
    return latest

def onboard():
    w = win()
    if w is None:
        raise RuntimeError('Copilot did not launch')
    skip = find(w, 'SkipToHomeButton', 'Button')
    if skip is not None:
        print('CLICK_SKIP')
        skip.click_input()
        time.sleep(7)
    w = win()
    go = find(w, 'GoToHomeButton', 'Button')
    if go is not None:
        print('CLICK_GO_HOME')
        go.click_input()
        time.sleep(10)
    if find(win(), 'InputTextBox', 'Edit') is None:
        raise RuntimeError('Signed-out InputTextBox not found after onboarding')

def send(text):
    w = win()
    edit = find(w, 'InputTextBox', 'Edit')
    if edit is None:
        raise RuntimeError('InputTextBox missing')
    edit.click_input()
    time.sleep(1)
    try:
        edit.set_edit_text(text)
    except Exception:
        edit.click_input()
        keyboard.send_keys('^a')
        keyboard.send_keys(text, with_spaces=True)
    print('SUBMIT', CASE_ID, CONDITION, repr(edit.window_text()))
    keyboard.send_keys('{ENTER}')
    time.sleep(3)

record = {
    'case_id': CASE_ID,
    'condition': CONDITION,
    'initial_error': initial,
    'prompt1': prompt1,
    'scripted_reply': followup,
}
try:
    onboard()
    record['home'] = snapshot('home')
    send(prompt1)
    record['turn1_visible'] = wait_stable('turn1')
    record['turn1_raw'] = snapshot('turn1_raw')
    send(followup)
    record['turn2_visible'] = wait_stable('turn2')
    record['turn2_raw'] = snapshot('turn2_raw')
    record['status'] = 'completed'
except Exception as e:
    record['status'] = 'error'
    record['error'] = repr(e)
    try:
        record['error_snapshot'] = snapshot('error_snapshot')
    except Exception as e2:
        record['snapshot_error'] = repr(e2)
    raise
finally:
    (OUT / 'record.json').write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    print('RESULT_RECORD', json.dumps({'case_id': CASE_ID, 'condition': CONDITION, 'status': record.get('status'), 'error': record.get('error')}, ensure_ascii=False))
