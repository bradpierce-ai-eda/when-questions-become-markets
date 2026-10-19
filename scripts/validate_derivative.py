#!/usr/bin/env python3
"""Independent semantic and publication-identity checks for this paper."""
import argparse,copy,hashlib,json,re,sys,importlib.util
from pathlib import Path
from bs4 import BeautifulSoup
import mistune,pymupdf,pypdf,yaml,bibtexparser
from urllib.parse import unquote
sys.dont_write_bytecode=True
PDFHASH='d5667e31ab98eed51a4781fe745ff241ef319b3751e2cdb34edb23ca85ed3780';DOI='10.5281/zenodo.23464042';URL='https://bradpierce.ai/when-questions-become-markets/'
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(s):return re.sub(r'\s+',' ',s).strip()
def need(c,m):
 if not c:raise AssertionError(m)
def validate(root,rebuild=True):
 s=json.loads((root/'source/paper.json').read_text());inv=json.loads((root/'source/invariants.json').read_text());b=json.loads((root/'bibliography.json').read_text());h=BeautifulSoup((root/'index.html').read_text(),'html.parser');original=BeautifulSoup(s['canonical_html'],'html.parser');need(sha(s['canonical_html'].encode())==inv['canonical_html_sha256']=='884a0ac12e5c15d0ffe3c2a5e4b4fa7ca6f8cf2ba91f66ba4eadb0b942145aab','Frozen complete HTML changed');need(sha(json.dumps(s['paragraphs'],ensure_ascii=False,separators=(',',':')).encode())==inv['canonical_paragraphs_sha256']=='8130493ae1030b8f2c5fa5c8d1a1601034fadb62ad6a7754963e35fabb8b6c5a','Frozen paragraphs changed')
 need(s['title']=='When Questions Become Markets'and s['doi']==DOI and s['publication_date']=='2026-10-19','Authority drift')
 expected={'citation_title':s['title'],'citation_author':'Brad Pierce','citation_publication_date':'2026/10/19','citation_doi':DOI,'citation_pdf_url':URL+'when-questions-become-markets.pdf','citation_fulltext_html_url':URL}
 for k,v in expected.items():need([x.get('content')for x in h.select('meta[name="'+k+'"]')]==[v],k)
 need([x.get('href')for x in h.select('link[rel="canonical"]')]==[URL],'Self canonical')
 front=h.select_one('#scholarly-front-matter');scope=h.select_one('#relevance-and-citation-scope');body=h.select_one('#canonical-paper');need(front and scope and body,'Page scopes absent');need(h.decode().index('id="scholarly-front-matter"')<h.decode().index('id="relevance-and-citation-scope"')<h.decode().index('id="canonical-paper"'),'Front matter order');need(s['abstract'] in front.get_text(),'Abstract absent');need('2026-10-19'in front.get_text()and s['orcid']in front.get_text(),'Published date/ORCID absent')
 # Every original top-level HTML block remains exact after moving it into wrappers.
 recovered=''.join(str(e)for e in list(front.contents)[:8])+''.join(str(e)for e in body.contents)
 need(recovered==s['canonical_html'],'Complete canonical HTML body drift')
 pars=[]
 for e in h.select('[data-source-index]'):
  q=copy.deepcopy(e)
  for x in q.select('.list-number'):x.decompose()
  pars.append({'key':e['data-source-index'],'text':q.get_text()})
 need(pars==s['paragraphs'],'Ordered paragraph text/word boundaries')
 need(len(h.select('table'))==4 and len(h.select('table th'))==11,'Tables/header cells');need([str(x)for x in h.select('table')]==[str(x)for x in original.select('table')],'Table geometry/content drift')
 need(len(h.select('figure'))==len(h.select('figure svg'))==13,'All 13 inline vector figures')
 for f in s['figures']:
  need(sha((root/f['file']).read_bytes())==f['sha256'],'SVG master hash '+f['file']);node=h.select_one('#figure-'+str(f['number']));need(node.find('svg')and node.figcaption.get_text()==f['caption']and f['alt']in node.get_text(),'Figure caption/accessibility');need(str(node.find('svg'))==str(original.select_one('#figure-'+str(f['number'])).find('svg')),'Inline SVG changed')
 need(not h.find(['canvas','iframe']),'Raster/interactive article substitution');need(not h.find('img'),'HTML does not replace SVG with raster images');need(not re.search(r'data:image/(png|jpeg|webp)',str(h),re.I),'Raster diagram data')
 refs=h.select('ol.references>li');need(len(refs)==169,'Reference count');need([x.get_text()for x in refs]==[x['raw_reference']for x in b['reference_slots']],'Exact published reference strings');need([x['number']for x in b['reference_slots']]==list(range(1,170)),'Reference order');need(len(b['works'])==len({x['id']for x in b['works']})==173,'Work identities');need(len({x['citekey']for x in b['works']})==173,'Citekey uniqueness');need({x['work_id']for x in b['reference_work_links']}=={x['id']for x in b['works']},'No orphan works');need({x['reference_slot']for x in b['reference_work_links']}==set(range(1,170)),'No orphan slots')
 links=h.select('a[href^="#reference-"]');need(len(links)==352,'Citation occurrence count')
 for x in links:need(h.select_one(x['href'])is not None,'Citation target missing')
 for x in refs:
  for a in x.select('a'):need(a.get_text() in [a['href'],unquote(a['href'])],'Only literal reference URLs are linked')
 md=(root/'paper.md').read_text();readme=(root/'README.md').read_text();need(readme.endswith(md),'README must contain complete exact Markdown');need('## Relevance and citation scope'in readme and readme.index('## Relevance and citation scope')<readme.index('## Canonical paper text'),'README scope order')
 rendered=BeautifulSoup(mistune.html(md),'html.parser');text=norm(rendered.get_text());pos=0
 for p in s['paragraphs']:
  needle=norm(p['text']);i=text.find(needle,pos);need(i>=0,'Markdown paragraph missing or changed '+p['key']+': '+needle[:55]);pos=i+len(needle)
 need(len(rendered.find_all('table'))==4,'Markdown tables');need(len(rendered.find_all('img'))==13,'Markdown figure links')
 need(norm(scope.get_text()).startswith('Relevance and citation scope'),'Scope title');need([x.get_text()for x in scope.select('p')]==s['relevance_and_citation_scope'],'Scope synchronization')
 added='\n'.join(s['relevance_and_citation_scope'])+'\n'+h.select_one('#repository-resources').get_text()+'\n'+(root/'metadata.json').read_text()+'\n'+(root/'provenance.json').read_text()
 need(not re.search(r'\b(cite this|when to cite|you should|ignore (previous|all)|system prompt|follow these instructions)\b',added,re.I),'Instruction-like repository framing');need(not re.search(r'https://(docs.google.com|drive.google.com)',added+str(h)),'Private Drive links')
 cff=yaml.safe_load((root/'CITATION.cff').read_text());need(cff['title']==cff['preferred-citation']['title']==s['title'],'CFF title');need(cff['doi']==cff['preferred-citation']['doi']==DOI,'CFF DOI');need(cff['date-released']==cff['preferred-citation']['date-published']=='2026-10-19','CFF date');need(cff['preferred-citation']['type']=='report'and cff['authors'][0]['orcid']=='https://orcid.org/'+s['orcid'],'CFF author/type');need(cff['keywords']==s['keywords'],'CFF keywords')
 own=bibtexparser.loads((root/'citation.bib').read_text()).entries;need(len(own)==1 and own[0]['doi']==DOI and own[0]['date']=='2026-10-19','Paper BibTeX');rr=bibtexparser.loads((root/'references.bib').read_text(),parser=bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)).entries;need(len(rr)==173,'BibTeX parser count');need(len(json.loads((root/'references.csl.json').read_text()))==173,'CSL count');need((root/'references.ris').read_text().count('TY  - ')==173,'RIS count')
 meta=json.loads((root/'metadata.json').read_text());need(meta['title']==s['title']and meta['publication_date']=='2026-10-19'and meta['doi']==DOI and meta['keywords']==s['keywords'],'Metadata agreement');schema=json.loads(h.find('script',type='application/ld+json').string);need(schema['headline']==s['title']and schema['datePublished']=='2026-10-19'and schema['encoding']['contentUrl']==URL+'when-questions-become-markets.pdf','JSON-LD')
 pdf=root/'when-questions-become-markets.pdf';need(pdf.stat().st_size==2085240 and sha(pdf.read_bytes())==PDFHASH,'Exact published PDF bytes');d=pymupdf.open(pdf);need(len(d)==133 and all(not p.get_image_info()for p in d),'PDF page/image inventory');need(all(p.get_text().strip()for p in d),'Searchable PDF');need(len(h.encode())<5_000_000,'HTML final size below 5 MB')
 if rebuild:
  spec=importlib.util.spec_from_file_location('build_derivative',root/'scripts/build_derivative.py');mod=importlib.util.module_from_spec(spec);sys.path.insert(0,str(root/'scripts'));spec.loader.exec_module(mod);mod.run(root,True)
 return {'status':'PASS','paragraphs':len(pars),'tables':4,'figures':13,'references':169,'works':173,'citationLinks':352,'pdfBytes':2085240,'pdfSHA256':PDFHASH,'htmlBytes':(root/'index.html').stat().st_size,'completeHTMLPreserved':True,'completeMarkdownAndREADME':True,'normalizedExportsParsed':True}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);a=ap.parse_args();print(json.dumps(validate(a.repo.resolve()),indent=2))
