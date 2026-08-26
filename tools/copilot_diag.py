from playwright.sync_api import sync_playwright
from pathlib import Path
import json, re

OUT=Path('copilot_artifacts'); OUT.mkdir(exist_ok=True)
prompt='A student says 1/3 + 1/4 = 2/7. Respond as a tutor: first diagnose what misunderstanding may have caused the error, then ask one useful follow-up question before giving a correction.'

with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
  context=browser.new_context(viewport={'width':1440,'height':1400},locale='en-US',timezone_id='America/Los_Angeles',extra_http_headers={'Accept-Language':'en-US,en;q=0.9'})
  page=context.new_page()
  page.goto('https://aka.ms/CopilotSearchinBing',wait_until='domcontentloaded',timeout=120000)
  page.wait_for_timeout(7000)
  body0=page.locator('body').inner_text(timeout=30000)
  print('HOME URL',page.url,'TITLE',page.title())
  print(body0[:12000])
  OUT.joinpath('home.txt').write_text(body0,encoding='utf-8')
  OUT.joinpath('home.html').write_text(page.content(),encoding='utf-8')
  page.screenshot(path=str(OUT/'home.png'),full_page=True)

  candidates=[]
  for sel in ['textarea','input[type="search"]','input[name="q"]','input[type="text"]','[contenteditable="true"]','[role="textbox"]']:
    try:
      loc=page.locator(sel)
      for i in range(min(loc.count(),20)):
        el=loc.nth(i)
        info={'selector':sel,'i':i,'visible':el.is_visible(),'editable':el.is_editable(),'placeholder':el.get_attribute('placeholder'),'aria':el.get_attribute('aria-label')}
        candidates.append(info)
    except Exception as e:
      candidates.append({'selector':sel,'error':repr(e)})
  print('CANDIDATES',json.dumps(candidates,indent=2))
  OUT.joinpath('candidates.json').write_text(json.dumps(candidates,indent=2),encoding='utf-8')

  editor=None
  for c in candidates:
    if c.get('visible') and c.get('editable'):
      editor=page.locator(c['selector']).nth(c['i']); break
  if editor is None:
    raise RuntimeError('No editable Copilot Search input found')

  try:
    editor.fill(prompt)
  except Exception:
    editor.click(); page.keyboard.press('Meta+A'); page.keyboard.insert_text(prompt)
  page.screenshot(path=str(OUT/'filled.png'),full_page=True)
  editor.press('Enter')
  page.wait_for_timeout(6000)

  prev=''; stable=0
  for _ in range(60):
    txt=page.locator('body').inner_text()
    if txt==prev and len(txt)>len(body0)+50: stable+=1
    else: stable=0
    prev=txt
    if stable>=4: break
    page.wait_for_timeout(2000)
  final=page.locator('body').inner_text()
  print('FINAL URL',page.url,'TITLE',page.title())
  print('FINAL BODY\n',final[:25000])
  OUT.joinpath('final.txt').write_text(final,encoding='utf-8')
  OUT.joinpath('final.html').write_text(page.content(),encoding='utf-8')
  page.screenshot(path=str(OUT/'final.png'),full_page=True)
  browser.close()
