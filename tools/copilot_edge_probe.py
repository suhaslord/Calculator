from playwright.sync_api import sync_playwright
from pathlib import Path
import json

OUT=Path('edge_artifacts'); OUT.mkdir(exist_ok=True)
ENDPOINTS=['edge://copilot','edge://sidebar','https://copilot.microsoft.com/','https://www.bing.com/chat']
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True,args=['--disable-blink-features=AutomationControlled'])
    context=browser.new_context(viewport={'width':1440,'height':1200},locale='en-US',timezone_id='America/Los_Angeles',extra_http_headers={'Accept-Language':'en-US,en;q=0.9'})
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    records=[]
    for i,url in enumerate(ENDPOINTS):
        page=context.new_page()
        try:
            page.goto(url,wait_until='domcontentloaded',timeout=120000)
            page.wait_for_timeout(8000)
            body=page.locator('body').inner_text(timeout=30000)
            inputs=[]
            for sel in ['textarea','[contenteditable="true"]','[role="textbox"]','input[type="text"]','input[type="search"]']:
                loc=page.locator(sel)
                for j in range(min(loc.count(),20)):
                    el=loc.nth(j)
                    try:
                        inputs.append({'selector':sel,'i':j,'visible':el.is_visible(),'editable':el.is_editable(),'placeholder':el.get_attribute('placeholder'),'aria':el.get_attribute('aria-label')})
                    except Exception: pass
            print('\n===',i,url,'==='); print('FINAL_URL',page.url); print('TITLE',page.title()); print(body[:12000]); print('INPUTS',json.dumps(inputs,indent=2))
            records.append({'url':url,'final_url':page.url,'title':page.title(),'body':body,'inputs':inputs})
            (OUT/f'edge_{i}.txt').write_text(body,encoding='utf-8'); (OUT/f'edge_{i}.html').write_text(page.content(),encoding='utf-8'); (OUT/f'edge_{i}_inputs.json').write_text(json.dumps(inputs,indent=2),encoding='utf-8')
            page.screenshot(path=str(OUT/f'edge_{i}.png'),full_page=True)
        except Exception as e:
            print('PROBE_ERROR',i,url,repr(e)); records.append({'url':url,'error':repr(e)})
        finally:
            page.close()
    (OUT/'edge_probe.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    browser.close()
