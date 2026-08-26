from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import quote
import json

OUT=Path('copilot_artifacts'); OUT.mkdir(exist_ok=True)
queries=[
 'common student misconception 1/3 + 1/4 = 2/7',
 'why might a student think 1/3 + 1/4 = 2/7',
 'possible misconceptions behind 1/3 + 1/4 = 2/7 and diagnostic questions',
 'how should a tutor diagnose a student who says 1/3 + 1/4 = 2/7 before correcting them',
]
with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
  context=browser.new_context(viewport={'width':1440,'height':1400},locale='en-US',timezone_id='America/Los_Angeles',extra_http_headers={'Accept-Language':'en-US,en;q=0.9'})
  records=[]
  for i,q in enumerate(queries):
    page=context.new_page()
    url='https://www.bing.com/copilotsearch?q='+quote(q)
    page.goto(url,wait_until='domcontentloaded',timeout=120000)
    page.wait_for_timeout(12000)
    body=page.locator('body').inner_text(timeout=30000)
    no_results='There are no results for this question' in body
    print('\n=== QUERY',i,'===\n',q,'\nNO_RESULTS=',no_results,'\n',body[:20000])
    records.append({'query':q,'url':page.url,'title':page.title(),'no_results':no_results,'body':body})
    OUT.joinpath(f'q{i}.txt').write_text(body,encoding='utf-8')
    page.screenshot(path=str(OUT/f'q{i}.png'),full_page=True)
    page.close()
  OUT.joinpath('calibration.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
  browser.close()
