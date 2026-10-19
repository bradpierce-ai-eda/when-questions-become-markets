#!/usr/bin/env python3
"""Offline, lossless bibliography serialization from frozen public bibliographic facts."""
import argparse,base64,hashlib,json,re
from pathlib import Path
MARKER='SOURCE-RECORD-JSON-UTF8-BASE64: '

def jdump(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def esc(x):
 d={'\\':r'\textbackslash{}','{':r'\{','}':r'\}','%':r'\%','&':r'\&','#':r'\#','_':r'\_'}
 return ''.join(d.get(c,c) for c in str(x))
def people(aa):
 return ' and '.join('{'+esc(a['literal'])+'}' if a.get('literal') else esc(a['family'])+(', '+esc(a['given']) if a.get('given') else '') for a in aa)
def name(a):return a.get('literal') or ' '.join(x for x in [a.get('given'),a.get('non-dropping-particle'),a.get('family')] if x)
def dates(w):
 v=w.get('issued') or {}
 dd=v.get('date_parts') or v.get('date-parts') or []
 return dd[0] if dd and isinstance(dd[0],list) else dd
def iso(dd):return '-'.join(str(n).zfill(4 if i==0 else 2) for i,n in enumerate(dd))
def source_record(w):
 # Public bibliographic facts only. Wrong before-citation text, QA, fetch histories,
 # reviewer counts and production timestamps remain solely in the private dataset.
 keys=['citekey','type','authors','editors','title','title_translated','issued','url','locators','doi','isbn','language','container_title','collection_title','volume','issue','pages','publisher','publisher_place','institution','edition','article_number','number','patent_number','publication_records','assignee_credit','application_filed_verbatim','source_credit','source_publication_date','versions','editions','identifiers','edition_date_roles','case_number','genre','statement_contributor','statement_date']
 z={k:w[k] for k in keys if k in w}
 if w.get('date_roles'):
  allowed={'published','published-print','published-online','issued','publication_date','webpage_updated','evaluation_report_publication'}
  z['date_roles']={k:v for k,v in w['date_roles'].items() if k in allowed}
 return z

def source_note(w):
 z=source_record(w);parts=[]
 if z.get('authors'):parts.append('Credited authors: '+'; '.join(name(a) for a in z['authors']))
 if z.get('title_translated'):parts.append('English title: '+z['title_translated'])
 for k in ['publication_records','locators','versions','editions','date_roles','source_publication_date','edition_date_roles','assignee_credit','application_filed_verbatim','source_credit','article_number','collection_title','number','identifiers','case_number','genre','statement_contributor','statement_date']:
  if z.get(k):parts.append(k.replace('_',' ').capitalize()+': '+jdump(z[k]))
 blob=base64.b64encode(jdump(z).encode()).decode();parts.append(MARKER+blob)
 return ' | '.join(parts)
BIB={'article-journal':'article','paper-conference':'inproceedings','book':'book','chapter':'incollection','report':'techreport','manuscript':'unpublished','patent':'patent','dataset':'misc','webpage':'misc','standard':'misc','software':'misc','thesis':'phdthesis'}
RIS={'article-journal':'JOUR','paper-conference':'CPAPER','book':'BOOK','chapter':'CHAP','report':'RPRT','manuscript':'UNPB','patent':'PAT','dataset':'DATA','webpage':'ELEC','standard':'STAND','software':'COMP','thesis':'THES'}
def primary_patent_number(w):
 return w.get('patent_number') or (next((r.get('number') for r in w.get('publication_records',[]) if r.get('number')),None) if w.get('type')=='patent' else None)

def bib_work(w):
 typ=BIB.get(w.get('type'),'misc');ff=[]
 if w.get('authors'):ff.append(('author',people(w['authors']),True))
 if w.get('editors'):ff.append(('editor',people(w['editors']),True))
 ff.append(('title','{'+esc(w['title'])+'}',True))
 for a,b in [('container_title','journal' if w.get('type')=='article-journal' else 'booktitle'),('volume','volume'),('issue','number'),('pages','pages'),('publisher','publisher'),('institution','institution'),('edition','edition'),('language','language'),('doi','doi'),('isbn','isbn'),('url','url'),('patent_number','patentnumber')]:
  if w.get(a):ff.append((b,str(w[a]),a in ['doi','url']))
 if w.get('article_number') and not w.get('pages'):ff.append(('pages',str(w['article_number']),False))
 if w.get('number') and w.get('type')=='article' and re.fullmatch(r'\d{4}\.\d{4,5}(?:v\d+)?',str(w['number'])):
  ff += [('eprint',str(w['number']),True),('eprinttype','arxiv',True)]
 if primary_patent_number(w) or (w.get('number') and not w.get('issue')):ff.append(('number',primary_patent_number(w) or str(w['number']),True))
 dd=dates(w)
 if dd:
  ff += [('year',str(dd[0]),True),('date',iso(dd),True)]
  if len(dd)>1:ff.append(('month',str(dd[1]),True))
 ff.append(('note',source_note(w),False))
 return '@'+typ+'{'+w['citekey']+',\n'+',\n'.join('  '+k+' = {'+(v if raw else esc(v))+'}' for k,v,raw in ff)+'\n}'
def csl_work(w):
 r={'id':w['citekey'],'type':w.get('type','document'),'title':w['title']}
 for a,b in [('container_title','container-title'),('volume','volume'),('issue','issue'),('pages','page'),('publisher','publisher'),('edition','edition'),('language','language'),('doi','DOI'),('isbn','ISBN'),('url','URL'),('patent_number','number')]:
  if w.get(a):r[b]=w[a]
 for a,b in [('authors','author'),('editors','editor')]:
  if w.get(a):r[b]=[{k:v for k,v in q.items() if k in ('literal','given','family','non-dropping-particle','dropping-particle','suffix')} for q in w[a]]
 if w.get('article_number') and not w.get('pages'):r['page']=w['article_number']
 if primary_patent_number(w) or w.get('number'):r['number']=primary_patent_number(w) or w['number']
 dd=dates(w)
 if dd:r['issued']={'date-parts':[dd]}
 r['note']=source_note(w);r['custom']={'source-record':source_record(w)}
 return r

def ris_work(w):
 ss=['TY  - '+RIS.get(w.get('type'),'GEN'),'ID  - '+w['citekey'],'TI  - '+w['title']]
 for a,b in [('authors','AU'),('editors','ED')]:
  for q in w.get(a,[]):ss.append(b+'  - '+(q['literal']+',' if q.get('literal') else q['family']+(', '+q['given'] if q.get('given') else '')))
 for a,b in [('container_title','T2'),('volume','VL'),('issue','IS'),('pages','SP'),('publisher','PB'),('language','LA'),('doi','DO'),('url','UR'),('isbn','SN'),('patent_number','M1')]:
  if w.get(a):ss.append(b+'  - '+str(w[a]))
 if w.get('article_number') and not w.get('pages'):ss.append('SP  - '+str(w['article_number']))
 if primary_patent_number(w) or w.get('number'):
  identifier=primary_patent_number(w) or str(w['number']);ss+=['M1  - '+identifier,'AN  - '+identifier]
 dd=dates(w)
 if dd:ss+=['PY  - '+str(dd[0]),'DA  - '+iso(dd).replace('-','/')]
 for u in list(dict.fromkeys(w.get('alternate_urls',[])+w.get('locators',[]))):
  if u!=w.get('url'):ss.append('L2  - '+str(u))
 ss+=['N1  - '+source_note(w),'ER  -'];return '\n'.join(ss)


def classic_bib_work(w):
 """Classic BibTeX types require actual fields; typed facts stay in the lossless note."""
 raw=bib_work(w)
 typ=re.match(r'@(\w+)',raw)[1]
 allowed={'article','book','booklet','conference','inbook','incollection','inproceedings','manual','mastersthesis','misc','phdthesis','proceedings','techreport','unpublished'}
 required={'article':['authors','title','container_title'],'techreport':['authors','title','institution'],'book':['title','publisher'],'incollection':['authors','title','container_title','publisher'],'inproceedings':['authors','title','container_title'],'phdthesis':['authors','title','institution']}
 if typ not in allowed or any(not w.get(k)for k in required.get(typ,[]))or(typ in required and not dates(w)):
  raw=re.sub(r'^@\w+','@misc',raw);typ='misc'
 if typ=='article'and not w.get('volume'):
  raw=re.sub(r'\n  number = \{[^\n]*\},','',raw)
 return raw
