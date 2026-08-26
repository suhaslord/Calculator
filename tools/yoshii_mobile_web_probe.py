from playwright.sync_api import sync_playwright
from pathlib import Path
import json, time

OUT = Path('yoshii_mobile_web_result')
OUT.mkdir(exist_ok=True)
PROMPT1 = 'You are tutoring a student. The student says: 1/3 + 1/4 = 2/7'
PROMPT2 = 'I added the tops because they are parts, and I added the bottoms because they are the number of pieces.'
SIGNIN = ['sign in to copilot', 'email, phone, or skype', 'choose a microsoft account', 'sign in with microsoft', 'sign in with apple', 'sign in with google']

PROFILES = [
    {
        'name': 'android_chrome',
        'user_agent': 'Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Mobile Safari/537.36',
        'viewport': {'width': 412, 'height': 915},
        'is_mobile': True,
        'has_touch': True,
    },
    {
        'name': 'iphone_safari',
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1',
        'viewport': {'width': 393, 'height': 852},
        'is_mobile': True,
        'has_touch': True,
    },
]

URLS = ['https://copilot.com/', 'https://copilot.microsoft.com/']

def body(page):
    return page.locator('body').inner_text(timeout=30000)

def save(page, tag):
    page.wait_for_timeout(1500)
    text = body(page)
    (OUT / f'{tag}.txt').write_text(text, encoding='utf-8')
    (OUT / f'{tag}.html').write_text(page.content(), encoding='utf-8')
    page.screenshot(path=str(OUT / f'{tag}.png'), full_page=True)
    return text

def find_composer(page):
    selectors = [
        'textarea', '[contenteditable="true"]', '[role="textbox"]',
        'input[placeholder*="message" i]', 'input[placeholder*="ask" i]',
    ]
    found = []
    for sel in selectors:
        try:
            loc = page.locator(sel)
            for i in range(loc.count()):
                el = loc.nth(i)
                if el.is_visible() and el.is_enabled():
                    found.append(el)
        except Exception:
            pass
    return found[-1] if found else None

def click_public_continue(page):
    # Only click public consent/continue controls; never any sign-in button.
    names = ['Continue', 'Accept', 'Accept all', 'Maybe later', 'Not now', 'Go to chat', 'Go to Chat']
    for name in names:
        try:
            btn = page.get_by_role('button', name=name, exact=True)
            if btn.count() and btn.first.is_visible() and btn.first.is_enabled():
                btn.first.click(); page.wait_for_timeout(4000); return name
        except Exception:
            pass
        try:
            link = page.get_by_role('link', name=name, exact=True)
            if link.count() and link.first.is_visible() and link.first.is_enabled():
                link.first.click(); page.wait_for_timeout(4000); return name
        except Exception:
            pass
    return None

def submit(page, text):
    c = find_composer(page)
    if c is None:
        raise RuntimeError('no visible composer')
    c.click()
    try:
        c.fill(text)
    except Exception:
        page.keyboard.type(text)
    for label in ['Send', 'Submit', 'Send message']:
        try:
            b = page.get_by_role('button', name=label)
            if b.count() and b.first.is_visible() and b.first.is_enabled():
                b.first.click(); return
        except Exception:
            pass
    c.press('Enter')

def wait_response(page, prior, timeout=75):
    end = time.time() + timeout
    last = ''
    stable = 0
    latest = prior
    while time.time() < end:
        page.wait_for_timeout(2500)
        latest = body(page)
        changed = latest != prior and len(latest) > len(prior) + 40
        if changed and latest == last:
            stable += 1
        else:
            stable = 0
        last = latest
        if changed and stable >= 2:
            return latest
    return latest

records = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=['--no-first-run', '--no-default-browser-check'])
    for profile in PROFILES:
        for ui, url in enumerate(URLS):
            context = browser.new_context(
                user_agent=profile['user_agent'], viewport=profile['viewport'],
                is_mobile=profile['is_mobile'], has_touch=profile['has_touch'],
                locale='en-US', timezone_id='America/Los_Angeles'
            )
            page = context.new_page()
            tag = f"{profile['name']}_{ui}"
            rec = {'profile': profile['name'], 'url_requested': url}
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=120000)
                page.wait_for_timeout(10000)
                first = save(page, tag + '_before')
                rec['url_landed'] = page.url
                rec['public_continue_clicked'] = click_public_continue(page)
                if rec['public_continue_clicked']:
                    first = save(page, tag + '_after_continue')
                    rec['url_after_continue'] = page.url
                lower = first.lower()
                if any(s in lower for s in SIGNIN) and find_composer(page) is None:
                    rec['status'] = 'sign_in_required'
                elif find_composer(page) is None:
                    rec['status'] = 'no_public_composer'
                else:
                    submit(page, PROMPT1)
                    turn1 = wait_response(page, first)
                    (OUT / f'{tag}_turn1.txt').write_text(turn1, encoding='utf-8')
                    rec['turn1_body'] = turn1
                    if any(s in turn1.lower() for s in SIGNIN) or len(turn1) <= len(first) + len(PROMPT1) + 30:
                        rec['status'] = 'invalid_turn1'
                    else:
                        submit(page, PROMPT2)
                        turn2 = wait_response(page, turn1)
                        (OUT / f'{tag}_turn2.txt').write_text(turn2, encoding='utf-8')
                        rec['turn2_body'] = turn2
                        rec['status'] = 'completed' if len(turn2) > len(turn1) + len(PROMPT2) + 20 else 'invalid_turn2'
            except Exception as e:
                rec['status'] = 'error'
                rec['error'] = repr(e)
            records.append(rec)
            print('MOBILE_COPILOT', rec.get('profile'), rec.get('url_requested'), rec.get('url_landed'), rec.get('public_continue_clicked'), rec.get('status'), rec.get('error'))
            context.close()
    browser.close()

(OUT / 'record.json').write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding='utf-8')
