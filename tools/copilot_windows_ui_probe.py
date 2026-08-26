import json, os, subprocess, time, traceback
from pathlib import Path
from pywinauto import Desktop

OUT=Path('native_copilot_artifacts'); OUT.mkdir(exist_ok=True)
APPID='Microsoft.Copilot_8wekyb3d8bbwe!App'

# Launch the installed Store app through the normal AppsFolder shell route.
subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{APPID}'])
time.sleep(15)

records=[]
desktop=Desktop(backend='uia')
for w in desktop.windows():
    try:
        title=w.window_text()
        cls=w.class_name()
        if 'copilot' not in title.lower() and 'copilot' not in cls.lower():
            continue
        rec={'title':title,'class':cls,'rectangle':str(w.rectangle()),'children':[]}
        print('WINDOW',title,cls,w.rectangle())
        try:
            for c in w.descendants():
                try:
                    info={
                        'text':c.window_text(),
                        'control_type':c.element_info.control_type,
                        'automation_id':c.element_info.automation_id,
                        'class_name':c.element_info.class_name,
                        'enabled':c.is_enabled(),
                        'visible':c.is_visible(),
                    }
                    rec['children'].append(info)
                    if info['text'] or info['control_type'] in ('Edit','Document','Button'):
                        print(' CHILD',json.dumps(info,ensure_ascii=False))
                except Exception as e:
                    pass
        except Exception as e:
            rec['descendants_error']=repr(e)
        records.append(rec)
    except Exception:
        pass

(OUT/'uia_tree.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
print('MATCHED_WINDOWS',len(records))

# Also inventory top-level titles so failures are diagnosable.
top=[]
for w in desktop.windows():
    try: top.append({'title':w.window_text(),'class':w.class_name(),'rect':str(w.rectangle())})
    except Exception: pass
(OUT/'top_windows.json').write_text(json.dumps(top,indent=2,ensure_ascii=False),encoding='utf-8')
print('TOP_WINDOWS',json.dumps(top,ensure_ascii=False)[:12000])
