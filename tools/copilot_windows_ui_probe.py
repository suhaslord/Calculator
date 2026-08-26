import json, subprocess, time
from pathlib import Path
from pywinauto import Desktop

OUT=Path('native_copilot_artifacts'); OUT.mkdir(exist_ok=True)
APPID='Microsoft.Copilot_8wekyb3d8bbwe!App'
subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{APPID}'])
time.sleep(15)
desktop=Desktop(backend='uia')

def copilot_window():
    for w in desktop.windows():
        try:
            if 'copilot' in w.window_text().lower(): return w
        except Exception: pass
    return None

def find_button(w, text=None, aid=None):
    for c in w.descendants():
        try:
            if c.element_info.control_type!='Button': continue
            if aid and c.element_info.automation_id==aid: return c
            if text and c.window_text().strip().lower()==text.lower(): return c
        except Exception: pass
    return None

def dump(tag,w):
    rec={'title':w.window_text(),'class':w.class_name(),'rectangle':str(w.rectangle()),'children':[]}
    print('\n===',tag,'===',rec['title'],rec['class'],rec['rectangle'])
    for c in w.descendants():
        try:
            info={'text':c.window_text(),'control_type':c.element_info.control_type,'automation_id':c.element_info.automation_id,'class_name':c.element_info.class_name,'enabled':c.is_enabled(),'visible':c.is_visible()}
            rec['children'].append(info)
            if info['text'] or info['control_type'] in ('Edit','Document','Button','Hyperlink'):
                print(' CHILD',json.dumps(info,ensure_ascii=False))
        except Exception: pass
    (OUT/f'{tag}_uia.json').write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding='utf-8')
    return rec

w=copilot_window();
if not w: raise RuntimeError('Copilot window not found')
dump('onboarding',w)
skip=find_button(w,aid='SkipToHomeButton') or find_button(w,text='Skip')
if not skip: raise RuntimeError('Skip button not found')
print('CLICK_SKIP'); skip.click_input(); time.sleep(8)
w=copilot_window(); mid=dump('post_skip',w)

go=find_button(w,aid='GoToHomeButton') or find_button(w,text='Go to Home')
if go:
    print('CLICK_GO_HOME'); go.click_input(); time.sleep(12)
else:
    print('NO_GO_HOME_BUTTON')
w=copilot_window(); final=dump('final_home',w)

interesting=[]
for x in final['children']:
    text=(x.get('text') or '').lower(); aid=(x.get('automation_id') or '').lower(); ct=x.get('control_type')
    if ct in ('Edit','Document') or any(k in text or k in aid for k in ['message','ask','prompt','chat','new','send','type','home']): interesting.append(x)
print('INTERESTING',json.dumps(interesting,indent=2,ensure_ascii=False))
(OUT/'interesting_controls.json').write_text(json.dumps(interesting,indent=2,ensure_ascii=False),encoding='utf-8')
