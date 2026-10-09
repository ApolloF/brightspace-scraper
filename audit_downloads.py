"""Audit downloaded TOC files and embedded Brightspace links; write an inventory."""
from pathlib import Path
import json,re,urllib.parse,hashlib,zipfile
from brightspace_sync.downloader import sanitize_name,generate_materials_index
root=Path('downloads');missing=[];topics=0
for f in root.rglob('course-content.json'):
 d=json.loads(f.read_text(encoding='utf-8'))
 def walk(m,p):
  global topics
  for t in m.get('Topics',[]):
   if t.get('TypeIdentifier')=='File' or t.get('ActivityType')==1:
    topics+=1
    name=Path(urllib.parse.unquote(urllib.parse.urlparse(t.get('Url','')).path)).name
    if not name or not (p/sanitize_name(name)).exists():missing.append(str(p/name))
  for child in m.get('Modules',[]):walk(child,p/sanitize_name(child['Title']))
 walk(d['toc'],f.parent)
for p in root.rglob('*.html'):
 for u in re.findall(r'(?:href|src)=["\x27]([^"\x27]+)',p.read_text(encoding='utf-8'),re.I):
  if '/content/enforced/' in u:
   name=sanitize_name(Path(urllib.parse.unquote(urllib.parse.urlparse(u).path)).name)
   if not (p.parent/name).exists():missing.append(str(p.parent/name))
files=[]
for folder in root.iterdir():
 if not folder.is_dir():continue
 for p in folder.rglob('*'):
  if not p.is_file():continue
  if p.suffix=='.part':missing.append('Unfinished '+str(p));continue
  with p.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
  if p.suffix=='.pdf':
   with p.open('rb') as f:assert f.read(4)==b'%PDF',p
  if p.suffix in ['.docx','.pptx','.xlsx']:assert zipfile.is_zipfile(p),p
  files.append({'path':p.as_posix(),'bytes':p.stat().st_size,'sha256':digest})
report={'published_file_topics':topics,'local_files':len(files),'bytes':sum(p['bytes'] for p in files),'missing':sorted(set(missing)),'files':files}
(root/'download-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
generate_materials_index()
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
if missing:raise SystemExit(1)
