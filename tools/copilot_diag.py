from playwright.sync_api import sync_playwright
from pathlib import Path
import json

OUT = Path('copilot_artifacts'); OUT.mkdir(exist_ok=True)
URLS = ['https://copilot.com/chats','https://copilot.com/','https://copilot.microsoft.com/']
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0')

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    except Exception as e:
        print('HEADED_LAUNCH_FAILED', repr(e))
        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
    context = browser.new_context(
        viewport={'width': 1440, 'height': 1200}, locale='en-US',
        timezone_id='America/Los_Angeles', user_agent=UA,
        geolocation={'latitude': 37.7749, 'longitude': -122.4194},
        permissions=['geolocation'], extra_http_headers={'Accept-Language':'en-US,en;q=0.9'})
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    for idx,url in enumerate(URLS):
        page=context.new_page()
        try:
            page.goto(url,wait_until='domcontentloaded',timeout=120000)
            page.wait_for_timeout(10000)
            for label in ['Go to Chat','Chat','Try Copilot','Continue']:
                try:
                    loc=page.get_by_role('link',name=label,exact=True)
                    if loc.count() and loc.first.is_visible():
                        print('CLICK_LINK',label)
                        loc.first.click(); page.wait_for_timeout(8000); break
                except Exception: pass
            body=page.locator('body').inner_text(timeout=30000)
            candidates=[]
            for sel in ['textarea','[contenteditable="true"]','[role="textbox"]','input[type="text"]']:
                loc=page.locator(sel)
                for i in range(min(loc.count(),10)):
                    el=loc.nth(i)
                    try:
                        candidates.append({'selector':sel,'i':i,'visible':el.is_visible(),'editable':el.is_editable(),'placeholder':el.get_attribute('placeholder'),'aria':el.get_attribute('aria-label')})
                    except Exception: pass
            print(f'=== {idx} {url} ==='); print('FINAL_URL',page.url); print('TITLE',page.title()); print(body[:12000]); print('CANDIDATES',json.dumps(candidates,indent=2))
            (OUT/f'probe_{idx}.txt').write_text(body,encoding='utf-8')
            (OUT/f'probe_{idx}.html').write_text(page.content(),encoding='utf-8')
            (OUT/f'probe_{idx}_candidates.json').write_text(json.dumps(candidates,indent=2),encoding='utf-8')
            page.screenshot(path=str(OUT/f'probe_{idx}.png'),full_page=True)
        except Exception as e:
            print('PROBE_ERROR',idx,repr(e))
        finally:
            page.close()
    browser.close()
