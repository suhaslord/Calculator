from playwright.sync_api import sync_playwright
from pathlib import Path
import json, os, time

OUT = Path('yoshii_edge_probe')
OUT.mkdir(exist_ok=True)
URLS = ['https://copilot.microsoft.com/', 'https://copilot.ai/']
PROMPT1 = 'You are tutoring a student. The student says: 1/3 + 1/4 = 2/7'
PROMPT2 = 'I added the tops because they are parts, and I added the bottoms because they are the number of pieces.'
SIGNIN = ['email, phone, or skype', 'choose a microsoft account']
EDGE_PATH = os.environ.get('EDGE_PATH')

def save(page, tag):
    page.wait_for_timeout(2500)
    body = page.locator('body').inner_text(timeout=30000)
    (OUT/f'{tag}.txt').write_text(body, encoding='utf-8')
    (OUT/f'{tag}.html').write_text(page.content(), encoding='utf-8')
    page.screenshot(path=str(OUT/f'{tag}.png'), full_page=True)
    return body

def composer(page):
    selectors = [
        'textarea',
        '[contenteditable="true"]',
        '[role="textbox"]',
        'input[placeholder*="ask" i]',
        'input[placeholder*="message" i]',
    ]
    found=[]
    for sel in selectors:
        try:
            loc=page.locator(sel)
            for i in range(loc.count()):
                el=loc.nth(i)
                if el.is_visible() and el.is_enabled(): found.append(el)
        except Exception:
            pass
    return found[-1] if found else None

def submit(page, text):
    c=composer(page)
    if c is None: raise RuntimeError('no visible composer')
    c.click()
    try: c.fill(text)
    except Exception: page.keyboard.type(text)
    clicked=False
    for pat in ['Send', 'Submit', 'Send message']:
        try:
            b=page.get_by_role('button', name=pat)
            if b.count() and b.first.is_visible() and b.first.is_enabled():
                b.first.click(); clicked=True; break
        except Exception:
            pass
    if not clicked: c.press('Enter')
    page.wait_for_timeout(1500)

def wait_change(page, prior, timeout=90):
    end=time.time()+timeout; last=''; stable=0; latest=prior
    while time.time()<end:
        page.wait_for_timeout(2500)
        latest=page.locator('body').inner_text(timeout=30000)
        changed=latest!=prior and len(latest)>len(prior)+30
        if changed and latest==last: stable+=1
        else: stable=0
        last=latest
        if changed and stable>=2: break
    return latest

with sync_playwright() as p:
    if EDGE_PATH and Path(EDGE_PATH).exists():
        browser=p.chromium.launch(executable_path=EDGE_PATH, headless=False, args=['--no-first-run','--no-default-browser-check'])
        browser_source='resolved_edge'
    else:
        browser=p.chromium.launch(headless=False, args=['--no-first-run','--no-default-browser-check'])
        browser_source='playwright_chromium'
    context=browser.new_context(viewport={'width':1440,'height':1000}, locale='en-US', timezone_id='America/Los_Angeles')
    results=[]
    for ui,url in enumerate(URLS):
        page=context.new_page()
        rec={'url_requested':url,'edge_path':EDGE_PATH,'browser_source':browser_source}
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=120000)
            page.wait_for_timeout(10000)
            before=save(page,f'{ui}_before')
            rec['url_landed']=page.url; rec['before_body']=before
            if any(x in before.lower() for x in SIGNIN) and composer(page) is None:
                rec['status']='sign_in_required'
            elif composer(page) is None:
                rec['status']='no_public_composer'
            else:
                submit(page,PROMPT1)
                turn1=wait_change(page,before)
                (OUT/f'{ui}_turn1.txt').write_text(turn1,encoding='utf-8')
                page.screenshot(path=str(OUT/f'{ui}_turn1.png'),full_page=True)
                rec['turn1_body']=turn1
                if len(turn1)<=len(before)+len(PROMPT1)+30 or any(x in turn1.lower() for x in SIGNIN):
                    rec['status']='invalid_turn1'
                else:
                    submit(page,PROMPT2)
                    turn2=wait_change(page,turn1)
                    (OUT/f'{ui}_turn2.txt').write_text(turn2,encoding='utf-8')
                    page.screenshot(path=str(OUT/f'{ui}_turn2.png'),full_page=True)
                    rec['turn2_body']=turn2
                    rec['status']='completed' if len(turn2)>len(turn1)+len(PROMPT2)+20 else 'invalid_turn2'
        except Exception as e:
            rec['status']='error'; rec['error']=repr(e)
        results.append(rec); page.close()
    (OUT/'record.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    for r in results: print('EDGE_COPILOT',r.get('browser_source'),r.get('url_requested'),r.get('url_landed'),r.get('status'),r.get('error'))
    context.close(); browser.close()
