from playwright.sync_api import sync_playwright
from pathlib import Path
import json, time

OUT = Path('yoshii_web_macos')
OUT.mkdir(exist_ok=True)
PROMPT1 = 'You are tutoring a student. The student says: 1/3 + 1/4 = 2/7'
PROMPT2 = 'I added the tops because they are parts, and I added the bottoms because they are the number of pieces.'
URL = 'https://copilot.microsoft.com/'

SIGNIN_WORDS = ['sign in', 'email, phone, or skype', 'choose a microsoft account']

def snap(page, tag):
    page.wait_for_timeout(3000)
    body = page.locator('body').inner_text(timeout=30000)
    (OUT / f'{tag}.txt').write_text(body, encoding='utf-8')
    (OUT / f'{tag}.html').write_text(page.content(), encoding='utf-8')
    page.screenshot(path=str(OUT / f'{tag}.png'), full_page=True)
    controls=[]
    for sel in ['textarea','[contenteditable="true"]','[role="textbox"]','input','button']:
        loc=page.locator(sel)
        for i in range(loc.count()):
            el=loc.nth(i)
            try:
                controls.append({
                    'selector':sel,
                    'text':el.inner_text(timeout=300) if sel not in ('textarea','input') else '',
                    'placeholder':el.get_attribute('placeholder'),
                    'aria':el.get_attribute('aria-label'),
                    'visible':el.is_visible(),
                    'enabled':el.is_enabled(),
                })
            except Exception:
                pass
    return {'url':page.url,'title':page.title(),'body':body,'controls':controls}

def find_composer(page):
    candidates=[]
    for sel in ['textarea','[contenteditable="true"]','[role="textbox"]']:
        loc=page.locator(sel)
        for i in range(loc.count()):
            el=loc.nth(i)
            try:
                if el.is_visible() and el.is_enabled():
                    candidates.append(el)
            except Exception:
                pass
    return candidates[-1] if candidates else None

def has_signin_wall(info):
    text=(info.get('body') or '').lower()
    return any(x in text for x in SIGNIN_WORDS) and find_text_hint(text)

def find_text_hint(text):
    return 'chat' not in text or 'sign in' in text

def submit(page, text):
    comp=find_composer(page)
    if comp is None:
        raise RuntimeError('no visible signed-out composer')
    comp.click()
    try:
        comp.fill(text)
    except Exception:
        page.keyboard.type(text)
    before=(comp.input_value() if comp.evaluate("el => 'value' in el") else comp.inner_text()).strip()
    # Prefer a visible submit/send button, then Enter.
    clicked=False
    for pattern in ['Send','Submit','Send message']:
        btn=page.get_by_role('button', name=pattern)
        try:
            if btn.count() and btn.first.is_visible() and btn.first.is_enabled():
                btn.first.click(); clicked=True; break
        except Exception:
            pass
    if not clicked:
        comp.press('Enter')
    page.wait_for_timeout(2000)
    return before

def wait_response(page, tag, prior_body, timeout_s=90):
    end=time.time()+timeout_s
    last=''
    stable=0
    latest=''
    while time.time()<end:
        page.wait_for_timeout(3000)
        latest=page.locator('body').inner_text(timeout=30000)
        changed=(latest != prior_body and len(latest) > len(prior_body)+20)
        if changed and latest==last:
            stable+=1
        else:
            stable=0
        last=latest
        if changed and stable>=2:
            break
    (OUT/f'{tag}.txt').write_text(latest,encoding='utf-8')
    page.screenshot(path=str(OUT/f'{tag}.png'),full_page=True)
    return latest

with sync_playwright() as p:
    results=[]
    for browser_name,browser_type in [('chromium',p.chromium),('webkit',p.webkit)]:
        browser=browser_type.launch(headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='en-US',timezone_id='America/Los_Angeles')
        page=context.new_page()
        rec={'browser':browser_name,'requested_url':URL}
        try:
            page.goto(URL,wait_until='domcontentloaded',timeout=120000)
            page.wait_for_timeout(10000)
            before=snap(page,f'{browser_name}_before')
            rec['before']=before
            if has_signin_wall(before) and find_composer(page) is None:
                rec['status']='sign_in_required'
            elif find_composer(page) is None:
                rec['status']='no_public_composer'
            else:
                p1=submit(page,PROMPT1)
                body1=wait_response(page,f'{browser_name}_turn1',before['body'])
                rec['prompt1_value']=p1
                rec['turn1_body']=body1
                # A valid turn must add content beyond the submitted prompt and must not turn into a sign-in page.
                if len(body1) <= len(before['body'])+len(PROMPT1)+30 or ('email, phone, or skype' in body1.lower()):
                    rec['status']='invalid_turn1'
                else:
                    before2=body1
                    p2=submit(page,PROMPT2)
                    body2=wait_response(page,f'{browser_name}_turn2',before2)
                    rec['prompt2_value']=p2
                    rec['turn2_body']=body2
                    rec['status']='completed' if len(body2)>len(before2)+len(PROMPT2)+20 else 'invalid_turn2'
        except Exception as e:
            rec['status']='error'
            rec['error']=repr(e)
        results.append(rec)
        context.close(); browser.close()
    (OUT/'record.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    for r in results:
        print('MACOS_COPILOT',r['browser'],r.get('status'),r.get('before',{}).get('url'),r.get('error'))
