from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import quote
import json

OUT=Path('copilot_artifacts'); OUT.mkdir(exist_ok=True)
prompt='I am testing tutoring behavior. A student says: 1/3 + 1/4 = 2/7. Respond as a tutor.'
urls=[
  'https://www.bing.com/copilotsearch?q='+quote(prompt),
  'https://www.bing.com/search?q='+quote(prompt)+'&showconv=1',
  'https://aka.ms/CopilotSearchinBing',
]
with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
  context=browser.new_context(viewport={'width':1440,'height':1400},locale='en-US',timezone_id='America/Los_Angeles',extra_http_headers={'Accept-Language':'en-US,en;q=0.9'})
  results=[]
  for i,url in enumerate(urls):
    page=context.new_page()
    try:
      page.goto(url,wait_until='domcontentloaded',timeout=120000)
      page.wait_for_timeout(12000)
      body=page.locator('body').inner_text(timeout=30000)
      rec={'requested':url,'final_url':page.url,'title':page.title(),'body':body[:20000]}
      results.append(rec)
      print('\n===',i,'===\nREQUEST',url,'\nFINAL',page.url,'\nTITLE',page.title(),'\n',body[:20000])
      OUT.joinpath(f'probe_{i}.txt').write_text(body,encoding='utf-8')
      OUT.joinpath(f'probe_{i}.html').write_text(page.content(),encoding='utf-8')
      page.screenshot(path=str(OUT/f'probe_{i}.png'),full_page=True)
    except Exception as e:
      print('ERROR',i,repr(e)); results.append({'requested':url,'error':repr(e)})
  OUT.joinpath('probe_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
  browser.close()
