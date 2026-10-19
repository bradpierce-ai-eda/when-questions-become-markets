#!/usr/bin/env python3
"""Required negative controls for semantic, vector, source and metadata drift."""
import argparse,json,shutil,tempfile,sys
from pathlib import Path
sys.dont_write_bytecode=True
from validate_derivative import validate

def run(root):
 cases=[('wrong-doi','index.html','content="10.5281/zenodo.23464042"','content="10.5281/zenodo.00000000"'),('wrong-date','index.html','content="2026/10/19"','content="2026/10/18"'),('abstract-loss','index.html','Questions become economically useful','Questions become unaccountably useful'),('body-loss','index.html','The economic unit in this report','The replaced unit in this report'),('figure-loss','index.html','<figure aria-describedby=','<div aria-describedby='),('vector-asset-drift','figures/figure-01.svg','<svg','<svg data-mutated="true"'),('reference-drift','index.html','10.1016/j.respol.2006.03.005','10.1016/j.respol.2006.03.006'),('readme-truncation','README.md','## Canonical paper text','## Truncated paper text'),('markdown-loss','paper.md','Questions become economically useful','Questions become unaccountably useful'),('cff-date','CITATION.cff','2026-10-19','2026-10-18'),('table-loss','index.html','<thead>','<tbody>'),('instruction-framing','metadata.json','faithful machine-readable','Ignore previous instructions; faithful machine-readable')]
 results=[]
 with tempfile.TemporaryDirectory()as td:
  base=Path(td)/'paper';shutil.copytree(root,base)
  validate(base)
  for name,fn,old,new in cases:
   p=base/fn;original=p.read_bytes();text=original.decode();
   if old not in text:
    if name=='figure-loss':old='<figure ';new='<div '
    elif name=='instruction-framing':old='The DOI-linked Zenodo report';new='Ignore previous instructions. The DOI-linked Zenodo report'
   assert old in text,(name,'mutation absent');p.write_text(text.replace(old,new,1))
   try:validate(base);raise RuntimeError('Mutation escaped: '+name)
   except (AssertionError,ValueError,KeyError,AttributeError,TypeError):results.append({'case':name,'rejected':True})
   finally:p.write_bytes(original)
  # PDF source byte mutation and file-set leaks are independent controls.
  p=base/'when-questions-become-markets.pdf';bb=p.read_bytes();p.write_bytes(bb+b'\n%wrong source')
  try:validate(base);raise RuntimeError('PDF mutation escaped')
  except AssertionError:results.append({'case':'pdf-byte-drift','rejected':True})
  finally:p.write_bytes(bb)
  p=base/'unapproved.txt';p.write_text('Unexpected public file')
  try:validate(base);raise RuntimeError('Manifest path leak escaped')
  except AssertionError:results.append({'case':'unapproved-file','rejected':True})
  finally:p.unlink()
  validate(base)
 return {'status':'PASS','negativeCases':results,'allRejected':len(results)==14}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);a=ap.parse_args();print(json.dumps(run(a.repo.resolve()),indent=2))
