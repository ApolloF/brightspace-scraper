"""Download same-origin embedded course media with bounded concurrency and streaming."""
import concurrent.futures, http.cookiejar, json, re, urllib.request, urllib.parse
from pathlib import Path
from brightspace_sync.auth import AUTH_STATE_PATH, BRIGHTSPACE_BASE_URL
from brightspace_sync.downloader import generate_materials_index

def download(item):
 url,dest=item
 jar=http.cookiejar.CookieJar()
 for c in json.loads(Path(AUTH_STATE_PATH).read_text())['cookies']:
  jar.set_cookie(http.cookiejar.Cookie(0,c['name'],c['value'],None,False,c['domain'],True,c['domain'].startswith('.'),c['path'],True,c['secure'],int(c['expires']) if c.get('expires',-1)>0 else None,False,None,None,{},False))
 opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
 with opener.open(urllib.request.Request(url,method='HEAD'),timeout=60) as r:
  expected=int(r.headers.get('Content-Length',0))
 if dest.exists() and expected and dest.stat().st_size==expected:
  return f'Verified existing: {dest.name}'
 part=dest.with_suffix(dest.suffix+'.part')
 with opener.open(url,timeout=120) as r, part.open('wb') as f:
  if 'video/' not in r.headers.get('Content-Type',''):raise ValueError('Expected video content: '+dest.name)
  expected=int(r.headers.get('Content-Length',0));count=0
  while chunk:=r.read(1024*1024):f.write(chunk);count+=len(chunk)
 if expected and count!=expected:raise ValueError('Incomplete media: '+dest.name)
 part.replace(dest)
 return f'Downloaded: {dest.name} ({count/1048576:.1f} MB)'

def main():
 items={}
 for p in Path('downloads').rglob('*.html'):
  for url in re.findall(r'<source[^>]+src=["\x27]([^"\x27]+)',p.read_text(encoding='utf-8'),re.I):
   url=urllib.parse.urljoin(BRIGHTSPACE_BASE_URL,url)
   if urllib.parse.urlparse(url).netloc!=urllib.parse.urlparse(BRIGHTSPACE_BASE_URL).netloc:continue
   items[url]=p.parent/Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
 print(f'Checking {len(items)} embedded videos',flush=True)
 errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for task in concurrent.futures.as_completed([pool.submit(download,i) for i in items.items()]):
   try: print(task.result(),flush=True)
   except Exception as e: errors.append(str(e));print('FAILED:',e,flush=True)
 generate_materials_index()
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
