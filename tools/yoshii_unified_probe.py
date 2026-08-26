import json, subprocess, time
from pathlib import Path
from pywinauto import Desktop, keyboard

OUT = Path('yoshii_unified_probe')
OUT.mkdir(exist_ok=True)
APPID = 'Microsoft.MicrosoftOfficeHub_8wekyb3d8bbwe!Microsoft.MicrosoftOfficeHub'
PROMPT = 'You are tutoring a student. The student says: 1/3 + 1/4 = 2/7'

subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{APPID}'])
time.sleep(20)
desktop = Desktop(backend='uia')

def get_windows():
    rows=[]
    for w in desktop.windows():
        try:
            rows.append({'title':w.window_text(),'class_name':w.class_name(),'rect':str(w.rectangle())})
        except Exception:
            pass
    return rows

(OUT/'windows.json').write_text(json.dumps(get_windows(), indent=2), encoding='utf-8')

def candidate_windows():
    out=[]
    for w in desktop.windows():
        try:
            title=w.window_text().lower()
            cls=w.class_name()
            if 'copilot' in title or 'microsoft 365' in title or cls=='WinUIDesktopWin32WindowClass':
                out.append(w)
        except Exception:
            pass
    return out

def snapshot(tag):
    allrows=[]
    for idx,w in enumerate(candidate_windows()):
        els=[]
        try:
            for c in w.descendants():
                try:
                    els.append({
                        'text':c.window_text(),
                        'control_type':c.element_info.control_type,
                        'automation_id':c.element_info.automation_id,
                        'class_name':c.element_info.class_name,
                        'visible':c.is_visible(),
                        'enabled':c.is_enabled(),
                    })
                except Exception:
                    pass
            allrows.append({'index':idx,'title':w.window_text(),'class_name':w.class_name(),'elements':els})
        except Exception as e:
            allrows.append({'index':idx,'error':repr(e)})
    (OUT/f'{tag}.json').write_text(json.dumps(allrows,indent=2,ensure_ascii=False),encoding='utf-8')
    print('SNAPSHOT',tag,'windows',len(allrows))
    for row in allrows:
        print('WINDOW',row.get('title'),row.get('class_name'))
        for e in row.get('elements',[]):
            if e.get('visible') and e.get('text'):
                print(json.dumps(e,ensure_ascii=False))
    return allrows

before=snapshot('before')
edit=None
for w in candidate_windows():
    try:
        for c in w.descendants():
            if c.element_info.control_type=='Edit' and c.is_visible() and c.is_enabled():
                edit=c; break
        if edit: break
    except Exception:
        pass

record={'prompt':PROMPT,'input_found':bool(edit)}
if edit:
    edit.click_input(); time.sleep(1)
    try:
        edit.set_edit_text(PROMPT)
    except Exception:
        keyboard.send_keys('^a'); keyboard.send_keys(PROMPT,with_spaces=True)
    keyboard.send_keys('{ENTER}')
    time.sleep(25)
    record['after']=snapshot('after_prompt')
else:
    record['before']=before

(OUT/'record.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
print('DONE',json.dumps({'input_found':bool(edit)}))
