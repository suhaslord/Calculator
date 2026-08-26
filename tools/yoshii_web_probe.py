from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import quote
import json, re

OUT=Path('yoshii_web_probe'); OUT.mkdir(exist_ok=True)
PROMPT='You are tutoring a student. The student says: 1/3 + 1/4 = 2/7'
URLS=[
    'https://copilot.com/?q='+quote(PROMPT),
    'https://copilot.microsoft.com/?q='+quote(PROMPT),
]

def summarize(page, tag):
    page.wait_for_timeout(8000)
    body=page.locator('body').inner_text(timeout=30000)
    html=page.content()
    (OUT/f'{tag}.txt').write_text(body,encoding='utf-8')
    (OUT/f'{tag}.html').write_text(html,encoding='utf-8')
    page.screenshot(path=str(OUT/f'{tag}.png'),full_page=True)
    controls=[]
    for selector in ['textarea','input','button','[contenteditable="true"]','[role="textbox"]']:
        try:
            for i in range(page.locator(selector).count()):
                el=page.locator(selector).nth(i)
                controls.append({
                    'selector':selector,
                    'text':(el.inner_text(timeout=1000) if selector not in ('textarea','input') else ''),
                    'placeholder':el.get_attribute('placeholder'),
                    'aria':el.get_attribute('aria-label'),
                    'role':el.get_attribute('role'),
                    'visible':el.is_visible(),
                    'enabled':el.is_enabled(),
                })
        except Exception as e:
            controls.append({'selector':selector,'error':repr(e)})
    return {'url':page.url,'title':page.title(),'body':body,'controls':controls}

with sync_playwright() as p:
    rec=[]
    for browser_name,browser_type in [('chromium',p.chromium),('firefox',p.firefox)]:
        browser=browser_type.launch(headless=True)
        context=browser.new_context(
            viewport={'width':1440,'height':1200},
            locale='en-US',
            timezone_id='America/Los_Angeles',
            geolocation={'latitude':37.7749,'longitude':-122.4194},
            permissions=['geolocation'],
            extra_http_headers={'Accept-Language':'en-US,en;q=0.9'},
        )
        for idx,url in enumerate(URLS):
            page=context.new_page()
            tag=f'{browser_name}_{idx}'
            try:
                page.goto(url,wait_until='domcontentloaded',timeout=120000)
                info=summarize(page,tag+'_before')
                # If a real visible composer is available, submit the prompt directly.
                target=None
                for sel in ['textarea','[contenteditable="true"]','[role="textbox"]']:
                    loc=page.locator(sel)
                    for i in range(loc.count()):
                        el=loc.nth(i)
                        if el.is_visible() and el.is_enabled():
                            target=el; break
                    if target is not None: break
                submitted=False
                if target is not None:
                    try:
                        target.click()
                        if target.get_attribute('contenteditable')=='true':
                            target.fill(PROMPT)
                        else:
                            target.fill(PROMPT)
                        target.press('Enter')
                        submitted=True
                        page.wait_for_timeout(25000)
                        after=summarize(page,tag+'_after')
                    except Exception as e:
                        after={'submit_error':repr(e)}
                else:
                    after={'submit_error':'no visible composer'}
                rec.append({'browser':browser_name,'requested_url':url,'before':info,'submitted':submitted,'after':after})
            except Exception as e:
                rec.append({'browser':browser_name,'requested_url':url,'error':repr(e)})
            finally:
                page.close()
        context.close(); browser.close()
    (OUT/'record.json').write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding='utf-8')
    for r in rec:
        b=r.get('before',{})
        print('RESULT',r.get('browser'),r.get('requested_url'),'landed',b.get('url'),'title',b.get('title'),'submitted',r.get('submitted'),'error',r.get('error') or r.get('after',{}).get('submit_error'))
