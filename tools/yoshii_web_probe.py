from playwright.sync_api import sync_playwright
from pathlib import Path
import json

OUT=Path('yoshii_web_probe'); OUT.mkdir(exist_ok=True)
PROMPT='You are tutoring a student. The student says: 1/3 + 1/4 = 2/7'


def summarize(page, tag):
    page.wait_for_timeout(5000)
    body=page.locator('body').inner_text(timeout=30000)
    html=page.content()
    (OUT/f'{tag}.txt').write_text(body,encoding='utf-8')
    (OUT/f'{tag}.html').write_text(html,encoding='utf-8')
    page.screenshot(path=str(OUT/f'{tag}.png'),full_page=True)
    controls=[]
    for selector in ['a','textarea','input','button','[contenteditable="true"]','[role="textbox"]']:
        try:
            for i in range(page.locator(selector).count()):
                el=page.locator(selector).nth(i)
                text=''
                try: text=el.inner_text(timeout=500)
                except Exception: pass
                controls.append({
                    'selector':selector,
                    'text':text,
                    'href':el.get_attribute('href'),
                    'placeholder':el.get_attribute('placeholder'),
                    'aria':el.get_attribute('aria-label'),
                    'role':el.get_attribute('role'),
                    'visible':el.is_visible(),
                    'enabled':el.is_enabled(),
                })
        except Exception as e:
            controls.append({'selector':selector,'error':repr(e)})
    return {'url':page.url,'title':page.title(),'body':body,'controls':controls}


def composer(page):
    for sel in ['textarea','[contenteditable="true"]','[role="textbox"]']:
        loc=page.locator(sel)
        for i in range(loc.count()):
            el=loc.nth(i)
            try:
                if el.is_visible() and el.is_enabled(): return el
            except Exception: pass
    return None

with sync_playwright() as p:
    rec=[]
    for browser_name,browser_type in [('chromium',p.chromium),('firefox',p.firefox)]:
        browser=browser_type.launch(headless=True)
        context=browser.new_context(
            viewport={'width':1440,'height':1200},locale='en-US',timezone_id='America/Los_Angeles',
            geolocation={'latitude':37.7749,'longitude':-122.4194},permissions=['geolocation'],
            extra_http_headers={'Accept-Language':'en-US,en;q=0.9'},
        )
        page=context.new_page()
        entry={'browser':browser_name}
        try:
            page.goto('https://copilot.com/',wait_until='domcontentloaded',timeout=120000)
            entry['landing']=summarize(page,f'{browser_name}_landing')
            clicked=None
            for label in ['Go to Chat','Try Copilot online','Get started with chat','Sign in']:
                loc=page.get_by_text(label,exact=True)
                try:
                    if loc.count() and loc.first.is_visible():
                        if label=='Sign in': continue
                        clicked=label
                        loc.first.click()
                        break
                except Exception: pass
            entry['clicked']=clicked
            page.wait_for_timeout(12000)
            entry['chat_route']=summarize(page,f'{browser_name}_chat_route')
            target=composer(page)
            if target is not None:
                target.click(); target.fill(PROMPT); target.press('Enter')
                entry['submitted']=True
                page.wait_for_timeout(30000)
                entry['after']=summarize(page,f'{browser_name}_after')
            else:
                entry['submitted']=False
                entry['submit_error']='no visible composer after official Go to Chat route'
        except Exception as e:
            entry['error']=repr(e)
        rec.append(entry)
        context.close(); browser.close()
    (OUT/'record.json').write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding='utf-8')
    for r in rec:
        route=r.get('chat_route',{})
        print('RESULT',r.get('browser'),'clicked',r.get('clicked'),'route',route.get('url'),'title',route.get('title'),'submitted',r.get('submitted'),'error',r.get('error') or r.get('submit_error'))
