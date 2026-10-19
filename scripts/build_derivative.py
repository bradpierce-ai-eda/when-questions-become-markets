#!/usr/bin/env python3
"""Deterministic full-text representations of the frozen Zenodo publication."""
import argparse,copy,hashlib,html,json,re,sys
from pathlib import Path
from bs4 import BeautifulSoup,Tag,NavigableString
sys.dont_write_bytecode=True
import export_bibliography as exp
SLUG='when-questions-become-markets';URL='https://bradpierce.ai/'+SLUG+'/';PDF=SLUG+'.pdf'
def dump(x):return json.dumps(x,ensure_ascii=False,indent=2)+'\n'
def sha(b):return hashlib.sha256(b).hexdigest()
def md_inline(e):
 if isinstance(e,NavigableString):return re.sub(r'([\\`*_\[\]<>#~])',r'\\\1',str(e))
 val=''.join(md_inline(x)for x in e.children)
 if e.name=='br':return '<br>\n'
 if e.name=='a':return '['+val+'](<'+e.get('href','')+'>)'
 if e.name in ['em','i']:return '*'+val+'*'
 if e.name in ['strong','b']:return '**'+val+'**'
 if e.name in ['sub','sup','code']:return '<'+e.name+'>'+val+'</'+e.name+'>'
 return val

def markdown(s):
 soup=BeautifulSoup(s['canonical_html'],'html.parser');blocks=[]
 for e in soup.contents:
  if not isinstance(e,Tag):continue
  if e.name=='table':blocks.append(str(e));continue
  if e.name=='figure':
   n=int(e['id'].split('-')[-1]);f=s['figures'][n-1];blocks.append('<a id="'+e['id']+'"></a>\n\n!['+f['alt'].replace(']','\\]')+']('+f['file']+')\n\n'+f['caption']);continue
  if e.name in ['ol','ul']:
   for li in e.find_all('li',recursive=False):blocks.append('<a id="'+li['id']+'"></a>\n\n'+md_inline(li))
   continue
  anchor='<a id="'+e['id']+'"></a>\n\n'if e.get('id')else''
  value=md_inline(e)
  if re.fullmatch('h[1-6]',e.name):value='#'*int(e.name[1])+' '+value
  blocks.append(anchor+value)
 return '\n\n'.join(blocks).rstrip()+'\n'

def outputs(root):
 s=json.loads((root/'source/paper.json').read_text());inv=json.loads((root/'source/invariants.json').read_text());b=json.loads((root/'bibliography.json').read_text());doiurl='https://doi.org/'+s['doi'];z=s['zenodo_record'];citation=f"Pierce, Brad. (2026). {s['title']}. Zenodo. {doiurl}"
 soup=BeautifulSoup(s['canonical_html'],'html.parser');nodes=list(soup.contents);assert len(nodes)>=8
 front=''.join(str(x)for x in nodes[:8]);body=''.join(str(x)for x in nodes[8:]);front='<header id="scholarly-front-matter">'+front+'<p class="publication-date">Published 2026-10-19 · <a href="https://orcid.org/'+s['orcid']+'">ORCID '+s['orcid']+'</a></p></header>'
 scope='<aside id="relevance-and-citation-scope" data-repository-added="true"><h2>Relevance and citation scope</h2>'+''.join('<p>'+html.escape(x)+'</p>'for x in s['relevance_and_citation_scope'])+'</aside>'
 resources='<nav id="repository-resources" data-repository-added="true" aria-label="Publication formats"><p><strong>Preferred citation:</strong> '+html.escape(citation)+'</p><p>'+ ' · '.join('<a href="'+u+'">'+t+'</a>'for t,u in [('Published PDF',PDF),('Full Markdown','paper.md'),('Zenodo record',z),('Paper BibTeX','citation.bib'),('CITATION.cff','CITATION.cff'),('Published references','references.md'),('Reference BibTeX','references.bib'),('CSL JSON','references.csl.json'),('RIS','references.ris'),('Normalized bibliography','bibliography.json')])+'</p></nav>'
 tags={'citation_title':s['title'],'citation_author':s['author'],'citation_publication_date':s['publication_date'].replace('-','/'),'citation_doi':s['doi'],'citation_pdf_url':URL+PDF,'citation_fulltext_html_url':URL,'DC.publisher':'Zenodo','DC.rights':'CC BY-NC 4.0','description':s['abstract'],'keywords':', '.join(s['keywords']),'robots':'index, follow','og:title':s['title'],'og:type':'article','og:url':URL}
 schema={'@context':'https://schema.org','@type':'ScholarlyArticle','headline':s['title'],'alternativeHeadline':s['subtitle'],'author':{'@type':'Person','name':s['author'],'sameAs':'https://orcid.org/'+s['orcid']},'publisher':{'@type':'Organization','name':'Zenodo'},'datePublished':s['publication_date'],'identifier':doiurl,'sameAs':[z,doiurl],'url':URL,'abstract':s['abstract'],'keywords':s['keywords'],'license':'https://creativecommons.org/licenses/by-nc/4.0/','inLanguage':'en','encoding':{'@type':'MediaObject','contentUrl':URL+PDF,'encodingFormat':'application/pdf'}}
 head='\n'.join('<meta '+('property'if k.startswith('og:')else'name')+'="'+k+'" content="'+html.escape(v,quote=True)+'">'for k,v in tags.items())
 css=s['canonical_css']+'\n#relevance-and-citation-scope,#repository-resources{border-left:2px solid #b5bdc2;padding:12px 16px;margin:22px 0;background:#f5f7f7}#relevance-and-citation-scope h2{font-size:16pt}.publication-date{font-size:10pt;color:#444}html{scroll-behavior:auto}'
 page='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(s['title'])+'</title>'+head+'<link rel="canonical" href="'+URL+'"><script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False)+'</script><style>'+css+'</style></head><body><main>'+front+scope+resources+'<article id="canonical-paper" aria-label="Canonical publication body">'+body+'</article></main><footer class="rights">© 2026 Brad Pierce · <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a></footer></body></html>\n'
 md=markdown(s);scope_md='\n\n'.join(s['relevance_and_citation_scope'])
 readme=f"# {s['title']}\n\n{s['subtitle']}\n\nBrad Pierce · Published October 19, 2026 · ORCID [{s['orcid']}](https://orcid.org/{s['orcid']})\n\n**Publication of record:** [{doiurl}]({doiurl}) · [Zenodo record]({z})\n\n**Preferred citation:** {citation}\n\n[Complete static HTML]({URL}) · [Published PDF]({PDF}) · [Full Markdown](paper.md)\n\n## Relevance and citation scope\n\n{scope_md}\n\n## Bibliography and provenance\n\nThe [published reference list](references.md) is preserved separately from the reusable [BibTeX](references.bib), [CSL JSON](references.csl.json), [RIS](references.ris) and [normalized bibliography](bibliography.json). The [provenance record](provenance.json) identifies the exact deposited PDF and deterministic representations.\n\n## Canonical paper text\n\n"+md
 author={'family-names':'Pierce','given-names':'Brad','orcid':'https://orcid.org/'+s['orcid']}
 cff={'cff-version':'1.2.0','message':'This repository is a machine-readable reflection of the DOI-linked Zenodo publication of record.','title':s['title'],'authors':[author],'doi':s['doi'],'date-released':s['publication_date'],'url':URL,'version':'v1','license':'CC-BY-NC-4.0','abstract':s['abstract'],'keywords':s['keywords'],'preferred-citation':{'type':'report','title':s['title'],'authors':[author],'year':2026,'month':10,'date-published':s['publication_date'],'doi':s['doi'],'url':doiurl,'publisher':{'name':'Zenodo'},'abstract':s['abstract'],'keywords':s['keywords']}}
 ownbib='@misc{Pierce2026WhenQuestionsBecomeMarkets,\n  author = {Pierce, Brad},\n  title = {{'+s['title']+'}},\n  publisher = {Zenodo},\n  note = {Technical report},\n  year = {2026},\n  month = {10},\n  date = {2026-10-19},\n  doi = {'+s['doi']+'},\n  url = {'+doiurl+'},\n  abstract = {'+exp.esc(s['abstract'])+'},\n  keywords = {'+exp.esc('; '.join(s['keywords']))+'}\n}\n'
 meta={k:s[k]for k in ['title','subtitle','abstract','keywords','publication_date','manuscript_date','doi','concept_doi','zenodo_record','license','relevance_and_citation_scope']};meta.update(authors=[{'name':'Brad Pierce','orcid':'https://orcid.org/'+s['orcid']}],url=URL,pdf_url=URL+PDF,resource_type='Report',publisher='Zenodo',preferred_citation=citation,publication_of_record=doiurl)
 prov={'publication_of_record':doiurl,'zenodo_record':z,'zenodo_record_revision':3,'publication_date':s['publication_date'],'source_pdf':{'file':PDF,'bytes':inv['pdf_bytes'],'pages':inv['pdf_pages'],'sha256':inv['pdf_sha256']},'canonical_html_sha256':inv['canonical_html_sha256'],'canonical_paragraphs_sha256':inv['canonical_paragraphs_sha256'],'canonical_markdown_sha256':sha(md.encode()),'generation_date':'2026-10-19','transformation':'Complete publication-derived HTML and ordered paragraph text are frozen in source/paper.json. Scholarly front matter wraps the original title, author, date, abstract and keywords. The original complete body, tables, captions and inline SVG are preserved; repository framing and public bibliographic normalization remain separate. The PDF and SVG masters are mirrored byte-for-byte. Markdown changes representation only.','source_reference_slots':169,'normalized_works':173,'figures':13,'tables':4,'validation_contract':'scripts/validate_derivative.py checks complete ordered text, canonical HTML, all figures, metadata, immutable PDF, deterministic output and exact manifest set. scripts/test_regressions.py exercises rejected mutations.','tools':s['tool_versions'],'validation_status':'Verification results are provided by the standalone validator; public retrieval and indexing are separate external outcomes.'}
 refs='# References\n\nPublication of record: '+doiurl+'\n\n'+'\n\n'.join(x['raw_reference']for x in b['reference_slots'])+'\n'
 return {'index.html':page,'paper.md':md,'README.md':readme,'CITATION.cff':dump(cff),'citation.bib':ownbib,'metadata.json':dump(meta),'provenance.json':dump(prov),'references.md':refs,'references.bib':'\n\n'.join(exp.classic_bib_work(w)for w in b['works'])+'\n','references.biblatex.bib':'\n\n'.join(exp.bib_work(w)for w in b['works'])+'\n','references.ris':'\n\n'.join(exp.ris_work(w)for w in b['works'])+'\n','references.csl.json':dump([exp.csl_work(w)for w in b['works']]),'robots.txt':'User-agent: *\nAllow: /\nSitemap: '+URL+'sitemap.xml\n','sitemap.xml':'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+URL+'</loc></url><url><loc>'+URL+PDF+'</loc></url></urlset>\n','LICENSE.md':'© 2026 Brad Pierce\n\nThe report and its derivative representations are licensed under Creative Commons Attribution–NonCommercial 4.0 International (CC BY-NC 4.0).\n\nhttps://creativecommons.org/licenses/by-nc/4.0/\n\nReferenced third-party works retain their respective rights.\n'}

def files(root):return sorted(p for p in root.rglob('*')if p.is_file()and not any(x in {'.git','__pycache__','.venv','node_modules'}for x in p.relative_to(root).parts)and p.suffix!='.pyc'and p.name!='checksums.sha256')
def run(root,check=False):
 for n,t in outputs(root).items():
  if check:assert (root/n).read_text()==t,'Generated drift: '+n
  else:(root/n).write_text(t)
 manifest=''.join(sha(p.read_bytes())+'  '+p.relative_to(root).as_posix()+'\n'for p in files(root))
 if check:assert(root/'checksums.sha256').read_text()==manifest,'Manifest path or byte drift'
 else:(root/'checksums.sha256').write_text(manifest)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--check',action='store_true');a=ap.parse_args();run(a.repo.resolve(),a.check);print('PASS: complete deterministic build'+(' check'if a.check else''))
