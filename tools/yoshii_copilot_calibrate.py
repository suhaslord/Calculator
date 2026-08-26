import json, subprocess, time
from pathlib import Path
from pywinauto import Desktop, keyboard

OUT=Path('yoshii_calibration'); OUT.mkdir(exist_ok=True)
APPID='Microsoft.Copilot_8wekyb3d8bbwe!App'
PROMPT1='You are tutoring a student. The student says: 234 x 501 = 1404'
PROMPT2='I multiplied 234 by 5, but I did not shift it two places because I thought the 5 just meant five.'

subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{APPID}'])
time.sleep(15)
desktop=Desktop(backend='uia')

def looks_like_copilot(w):
    try:
        if 'copilot' in w.window_text().lower(): return True
        if w.class_name()!='WinUIDesktopWin32WindowClass': return False
        for c in w.descendants():
            try:
                if c.element_info.automation_id in ('InputTextBox','HomeButton','SkipToHomeButton','GoToHomeButton','ComposerChatModeButton'):
                    return True
            except Exception: pass
    except Exception: pass
    return False

def win(retries=12):
    for _ in range(retries):
        for w in desktop.windows():
            if looks_like_copilot(w): return w
        time.sleep(1)
    return None

def find(w, aid, ctype=None):
    if w is None: return None
    for c in w.descendants():
        try:
            if c.element_info.automation_id==aid and (ctype is None or c.element_info.control_type==ctype): return c
        except Exception: pass
    return None

def visible_texts(w):
    vals=[]
    if w is None: return vals
    for c in w.descendants():
        try:
            if not c.is_visible(): continue
            ct=c.element_info.control_type
            text=c.window_text().strip()
            if text and ct in ('Text','Document','Button','Group','Edit'):
                vals.append({'text':text,'control_type':ct,'automation_id':c.element_info.automation_id,'class_name':c.element_info.class_name})
        except Exception: pass
    return vals

def dump(tag):
    w=win(); vals=visible_texts(w)
    print('\n===',tag,'=== WINDOW',None if w is None else repr(w.window_text()))
    for v in vals: print(json.dumps(v,ensure_ascii=False))
    (OUT/f'{tag}.json').write_text(json.dumps(vals,indent=2,ensure_ascii=False),encoding='utf-8')
    return vals

def click_onboarding():
    w=win(); s=find(w,'SkipToHomeButton','Button')
    if s is not None:
        print('CLICK_SKIP'); s.click_input(); time.sleep(7)
    w=win(); g=find(w,'GoToHomeButton','Button')
    if g is not None:
        print('CLICK_GO_HOME'); g.click_input(); time.sleep(10)

def send_text(text):
    w=win(); edit=find(w,'InputTextBox','Edit')
    if edit is None: raise RuntimeError('InputTextBox not found')
    edit.click_input(); time.sleep(1)
    try:
        edit.set_edit_text(text)
    except Exception as e:
        print('SET_EDIT_TEXT_FAILED',repr(e))
        edit.click_input(); keyboard.send_keys('^a'); keyboard.send_keys(text,with_spaces=True)
    time.sleep(2)
    print('INPUT_VALUE',repr(edit.window_text()))
    keyboard.send_keys('{ENTER}')
    time.sleep(3)

def wait_for_stable(tag, min_wait=8, max_wait=90):
    start=time.time(); last=None; stable=0; latest=[]
    while time.time()-start < max_wait:
        time.sleep(3)
        w=win(retries=3)
        if w is None:
            print('POLL',tag,'WINDOW_MISSING'); continue
        vals=visible_texts(w)
        sig='\n'.join(v['text'] for v in vals)
        elapsed=int(time.time()-start)
        print('POLL',tag,elapsed,'title',repr(w.window_text()),'chars',len(sig))
        if sig==last and elapsed>=min_wait:
            stable+=1
        else:
            stable=0
        last=sig; latest=vals
        if stable>=2:
            print('STABLE',tag,elapsed); break
    (OUT/f'{tag}.json').write_text(json.dumps(latest,indent=2,ensure_ascii=False),encoding='utf-8')
    print('\n=== FINAL',tag,'===')
    for v in latest: print(json.dumps(v,ensure_ascii=False))
    return latest

click_onboarding(); dump('home_before')
send_text(PROMPT1)
first=wait_for_stable('after_turn1')
send_text(PROMPT2)
second=wait_for_stable('after_turn2')
record={'condition':'generic','case_id':'C1','prompt1':PROMPT1,'prompt2':PROMPT2,'turn1_ui':first,'turn2_ui':second}
(OUT/'calibration_record.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
print('CALIBRATION_DONE')
