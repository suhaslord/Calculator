from playwright.sync_api import sync_playwright
from pathlib import Path
import json, time, re

OUT = Path('copilot_artifacts')
OUT.mkdir(exist_ok=True)

SELECTORS = [
    'textarea',
    '[contenteditable="true"]',
    '[role="textbox"]',
    'input[placeholder*="Copilot" i]',
    'input[placeholder*="message" i]',
    'textarea[placeholder*="message" i]',
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={"width": 1440, "height": 1200}, locale='en-US')
    page = context.new_page()
    page.goto('https://copilot.microsoft.com/', wait_until='domcontentloaded', timeout=120000)
    page.wait_for_timeout(8000)
    print('TITLE:', page.title())
    print('URL:', page.url)
    body = page.locator('body').inner_text(timeout=30000)
    print('BODY_START\n', body[:12000], '\nBODY_END')
    OUT.joinpath('initial_body.txt').write_text(body, encoding='utf-8')
    OUT.joinpath('initial.html').write_text(page.content(), encoding='utf-8')
    page.screenshot(path=str(OUT/'initial.png'), full_page=True)

    # dismiss common cookie/consent UI if present
    for label in ['Accept', 'Accept all', 'I agree', 'Got it', 'Continue']:
        try:
            loc = page.get_by_role('button', name=re.compile(f'^{re.escape(label)}$', re.I))
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=3000)
                page.wait_for_timeout(1000)
                break
        except Exception:
            pass

    chosen = None
    for sel in SELECTORS:
        try:
            loc = page.locator(sel)
            for i in range(min(loc.count(), 10)):
                el = loc.nth(i)
                if el.is_visible() and el.is_editable():
                    chosen = (sel, i)
                    break
            if chosen:
                break
        except Exception:
            pass
    print('CHOSEN:', chosen)
    OUT.joinpath('diagnostic.json').write_text(json.dumps({'title': page.title(), 'url': page.url, 'chosen': chosen}, indent=2), encoding='utf-8')
    if not chosen:
        raise RuntimeError('No editable Copilot composer found')

    el = page.locator(chosen[0]).nth(chosen[1])
    prompt = 'I am testing tutoring behavior. A student says: 1/3 + 1/4 = 2/7. Respond as a tutor.'
    el.fill(prompt)
    el.press('Enter')
    page.wait_for_timeout(3000)
    previous = ''
    stable = 0
    for _ in range(60):
        txt = page.locator('body').inner_text()
        if txt == previous and len(txt) > len(body) + 20:
            stable += 1
        else:
            stable = 0
        previous = txt
        if stable >= 4:
            break
        page.wait_for_timeout(2000)
    final = page.locator('body').inner_text()
    print('FINAL_BODY_START\n', final[-16000:], '\nFINAL_BODY_END')
    OUT.joinpath('final_body.txt').write_text(final, encoding='utf-8')
    OUT.joinpath('final.html').write_text(page.content(), encoding='utf-8')
    page.screenshot(path=str(OUT/'final.png'), full_page=True)
    browser.close()
