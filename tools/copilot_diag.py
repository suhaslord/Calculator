from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import quote
import json

OUT=Path('copilot_artifacts'); OUT.mkdir(exist_ok=True)
queries=[
 'why is one third plus one fourth not equal to two sevenths',
 'student says one third plus one fourth equals two sevenths common misconception'
]
with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
  context=browser.new_context(viewport={'width':1440,'height':1600},locale='en-US',timezone_id='America/Los_Angeles',extra_http_headers={'Accept-Language':'en-US,en;q=0.9'})
  rec=[]
  for i,q in enumerate(queries):
    page=context.new_page(); url='https://www.bing.com/search?q='+quote(q)
    page.goto(url,wait_until='domcontentloaded',timeout=120000); page.wait_for_timeout(12000)
    body=page.locator('body').inner_text(timeout=30000)
    print('\n===',i,q,'===\n',body[:25000])
    rec.append({'query':q,'url':page.url,'title':page.title(),'body':body})
    OUT.joinpath(f'bing_{i}.txt').write_text(body,encoding='utf-8'); OUT.joinpath(f'bing_{i}.html').write_text(page.content(),encoding='utf-8'); page.screenshot(path=str(OUT/f'bing_{i}.png'),full_page=True); page.close()
  OUT.joinpath('bing_probe.json').write_text(json.dumps(rec,indent=2),encoding='utf-8'); browser.close()
