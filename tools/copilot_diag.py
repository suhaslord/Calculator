from playwright.sync_api import sync_playwright
from pathlib import Path
import json

OUT=Path('copilot_artifacts'); OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-blink-features=AutomationControlled'])
    context=browser.new_context(viewport={'width':1440,'height':1200},locale='en-US',timezone_id='America/Los_Angeles',extra_http_headers={'Accept-Language':'en-US,en;q=0.9'})
    page=context.new_page(); page.goto('https://copilot.microsoft.com/',wait_until='domcontentloaded',timeout=120000); page.wait_for_timeout(10000)
    def snapshot(tag):
        body=page.locator('body').inner_text(timeout=30000)
        buttons=[]
        for sel in ['button','[role="button"]']:
            loc=page.locator(sel)
            for i in range(min(loc.count(),80)):
                el=loc.nth(i)
                try:
                    if el.is_visible():
                        buttons.append({'selector':sel,'i':i,'text':el.inner_text()[:200],'aria':el.get_attribute('aria-label'),'title':el.get_attribute('title')})
                except Exception: pass
        tas=[]; loc=page.locator('textarea')
        for i in range(loc.count()):
            el=loc.nth(i)
            try: tas.append({'i':i,'visible':el.is_visible(),'editable':el.is_editable(),'placeholder':el.get_attribute('placeholder'),'aria':el.get_attribute('aria-label')})
            except Exception: pass
        print('\nSNAP',tag,'URL',page.url,'TITLE',page.title()); print(body[:10000]); print('BUTTONS',json.dumps(buttons,indent=2)); print('TEXTAREAS',json.dumps(tas,indent=2))
        (OUT/f'{tag}.txt').write_text(body,encoding='utf-8'); (OUT/f'{tag}_buttons.json').write_text(json.dumps(buttons,indent=2),encoding='utf-8'); (OUT/f'{tag}_textareas.json').write_text(json.dumps(tas,indent=2),encoding='utf-8'); page.screenshot(path=str(OUT/f'{tag}.png'),full_page=True)
    snapshot('before')
    # Only use ordinary UI dismissal paths. Do not bypass authentication.
    dismissed=False
    for name in ['Close','Not now','Maybe later','Skip','Continue without signing in','No thanks']:
        for role in ['button','link']:
            try:
                loc=page.get_by_role(role,name=name,exact=False)
                if loc.count() and loc.first.is_visible():
                    print('CLICK',role,name); loc.first.click(); page.wait_for_timeout(4000); dismissed=True; break
            except Exception: pass
        if dismissed: break
    if not dismissed:
        print('TRY_ESCAPE'); page.keyboard.press('Escape'); page.wait_for_timeout(3000)
    snapshot('after')
    browser.close()
