from playwright.sync_api import sync_playwright
from pathlib import Path
import json, re

OUT = Path('copilot_artifacts')
OUT.mkdir(exist_ok=True)

ENDPOINTS = [
    'https://copilot.com/',
    'https://www.copilot.com/',
    'https://copilot.microsoft.com/?cc=US&setlang=en-US',
    'https://www.bing.com/chat',
    'https://www.bing.com/copilot',
]
SELECTORS = [
    'textarea',
    '[contenteditable="true"]',
    '[role="textbox"]',
    'input[placeholder*="Copilot" i]',
    'input[placeholder*="message" i]',
    'textarea[placeholder*="message" i]',
    'input[type="search"]',
]

def find_editor(page):
    for sel in SELECTORS:
        try:
            loc = page.locator(sel)
            for i in range(min(loc.count(), 20)):
                el = loc.nth(i)
                if el.is_visible() and el.is_editable():
                    return sel, i
        except Exception:
            pass
    return None

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(
        viewport={"width": 1440, "height": 1200},
        locale='en-US',
        timezone_id='America/Los_Angeles',
        geolocation={"latitude": 37.7749, "longitude": -122.4194},
        permissions=['geolocation'],
        extra_http_headers={'Accept-Language': 'en-US,en;q=0.9'},
    )
    results=[]
    selected=None
    for idx, url in enumerate(ENDPOINTS):
        page=context.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=120000)
            page.wait_for_timeout(7000)
            body=page.locator('body').inner_text(timeout=30000)
            chosen=find_editor(page)
            rec={'requested':url,'url':page.url,'title':page.title(),'chosen':chosen,'body':body[:8000]}
            results.append(rec)
            print('\n=== ENDPOINT', idx, url, '===')
            print('FINAL URL:', page.url)
            print('TITLE:', page.title())
            print('CHOSEN:', chosen)
            print(body[:8000])
            OUT.joinpath(f'endpoint_{idx}_body.txt').write_text(body,encoding='utf-8')
            OUT.joinpath(f'endpoint_{idx}.html').write_text(page.content(),encoding='utf-8')
            page.screenshot(path=str(OUT/f'endpoint_{idx}.png'), full_page=True)
            if chosen and 'not available in your region' not in body.lower():
                selected=(page,chosen,url,body)
                break
        except Exception as e:
            results.append({'requested':url,'error':repr(e)})
            print('ERROR',url,repr(e))
            page.close()
    OUT.joinpath('probe_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    if not selected:
        raise RuntimeError('No usable Copilot/Bing Copilot composer found on any current entry point')

    page,chosen,url,body=selected
    for label in ['Accept', 'Accept all', 'I agree', 'Got it', 'Continue']:
        try:
            loc=page.get_by_role('button',name=re.compile(f'^{re.escape(label)}$',re.I))
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=3000)
                page.wait_for_timeout(800)
                break
        except Exception:
            pass
    chosen=find_editor(page)
    print('USING:',url,'EDITOR:',chosen)
    el=page.locator(chosen[0]).nth(chosen[1])
    prompt='I am testing tutoring behavior. A student says: 1/3 + 1/4 = 2/7. Respond as a tutor.'
    try:
        el.fill(prompt)
    except Exception:
        el.click(); page.keyboard.insert_text(prompt)
    el.press('Enter')
    page.wait_for_timeout(5000)
    prev=''; stable=0
    for _ in range(70):
        txt=page.locator('body').inner_text()
        if txt==prev and len(txt)>len(body)+20:
            stable+=1
        else:
            stable=0
        prev=txt
        if stable>=4:
            break
        page.wait_for_timeout(2000)
    final=page.locator('body').inner_text()
    print('FINAL BODY TAIL:\n',final[-16000:])
    OUT.joinpath('final_body.txt').write_text(final,encoding='utf-8')
    OUT.joinpath('final.html').write_text(page.content(),encoding='utf-8')
    page.screenshot(path=str(OUT/'final.png'),full_page=True)
    browser.close()
