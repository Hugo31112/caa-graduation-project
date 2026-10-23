"""Generate the English page and SVGs from reviewed translations. No network calls."""
from pathlib import Path
from html.parser import HTMLParser
import html
import json
import re
import xml.etree.ElementTree as ET

DOCS = Path(__file__).resolve().parent.parent / 'docs'
translations = json.loads((DOCS/'locales/en.json').read_text(encoding='utf-8'))
svg_translations = json.loads((DOCS/'locales/en-diagrams.json').read_text(encoding='utf-8'))
HAN = re.compile(r'[\u4e00-\u9fff]')

def translate(s):
    if not HAN.search(s): return s
    if s not in translations:
        raise ValueError('English translation missing: '+s)
    return translations[s]

class English(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out=[]
        self.control_depth=0
    def handle_starttag(self,tag,attrs):
        raw=self.get_starttag_text()
        if tag=='div' and dict(attrs).get('class')=='language-bar':self.control_depth=1
        elif self.control_depth and tag=='div':self.control_depth+=1
        def attr(m):return m[1]+'="'+html.escape(translate(html.unescape(m[2])),quote=True)+'"'
        raw=re.sub(r'(alt|aria-label|title)="([^"]*)"',attr,raw)
        raw=raw.replace('lang="zh-CN"','lang="en"') if tag=='html' else raw
        raw=raw.replace('assets/diagrams/','assets/diagrams/en/') if tag in ['img','source'] else raw
        if self.control_depth and tag=='a':
            if dict(attrs).get('hreflang')=='en':raw=raw.replace('data-language-link','data-language-link aria-current="page"')
            else:raw=raw.replace(' aria-current="page"','')
        self.out.append(raw)
    def handle_endtag(self,tag):
        self.out.append('</'+tag+'>')
        if self.control_depth and tag=='div':self.control_depth-=1
    def handle_data(self,data):
        stripped=data.strip()
        if self.control_depth or not stripped:self.out.append(data);return
        value=translate(stripped)
        self.out.append(data[:len(data)-len(data.lstrip())]+html.escape(value,quote=False)+data[len(data.rstrip()):])
    def handle_entityref(self,name):self.out.append('&'+name+';')
    def handle_charref(self,name):self.out.append('&#'+name+';')
    def handle_decl(self,decl):self.out.append('<!'+decl+'>')
    def handle_comment(self,data):self.out.append('<!--'+data+'-->')

source=(DOCS/'index.html').read_text(encoding='utf-8')
p=English();p.feed(source)
english=''.join(p.out)
(DOCS/'index-en.html').write_text(english,encoding='utf-8',newline='\n')

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
dest=DOCS/'assets/diagrams/en';dest.mkdir(exist_ok=True)
for f in (DOCS/'assets/diagrams').glob('*.svg'):
    tree=ET.parse(f);root=tree.getroot()
    root.set('lang','en')
    root.set('font-family','Arial, Helvetica, sans-serif')
    if 'style' in root.attrib:root.set('style','font-family:Arial,Helvetica,sans-serif')
    width=float(root.get('viewBox').split()[2])
    for el in root.iter():
        if el.text and HAN.search(el.text):
            if el.text not in svg_translations:raise ValueError('Missing SVG translation: '+el.text)
            el.text=svg_translations[el.text]
    if f.name.startswith('cultural_reach'):
        # The Chinese diagram already has English subtitles; avoid repeated labels.
        for parent in root.iter():
            for el in list(parent):
                if el.tag=='{'+NS+'}text' and el.get('font-size') in ['13','15'] and el.text in ['Reach','Understanding','Circulation','Connection']:
                    parent.remove(el)
    rects=list(root.iter('{'+NS+'}rect'));texts=list(root.iter('{'+NS+'}text'))
    for el in texts:
        x=float(el.get('x','0'));y=float(el.get('y','0'));size=float(el.get('font-size','18'));anchor=el.get('text-anchor','start')
        limit=width-x-8 if anchor=='start' else (x-8 if anchor=='end' else 2*min(x,width-x)-8)
        for rect in rects:
            rx=float(rect.get('x','0'));ry=float(rect.get('y','0'));rw=float(rect.get('width','0'));rh=float(rect.get('height','0'))
            if rx<=x<rx+rw and ry<y<=ry+rh:
                limit=min(limit,rx+rw-x-12 if anchor=='start' else rw-24)
        if anchor=='start':
            for other in texts:
                ox=float(other.get('x','0'));oy=float(other.get('y','0'))
                if ox>x and abs(oy-y)<10:limit=min(limit,ox-x-24)
        # Constrain labels inside their existing diagram cells without moving geometry.
        estimate=len(el.text or '')*size*.53
        if estimate>limit and limit>0:
            newsize=max(12,min(size,limit/max(1,len(el.text or ''))/.53))
            el.set('font-size',f'{newsize:.1f}')
            if len(el.text or '')*newsize*.53>limit:
                el.set('textLength',f'{limit:.0f}');el.set('lengthAdjust','spacingAndGlyphs')
    tree.write(dest/f.name,encoding='utf-8',xml_declaration=False)
print('Generated index-en.html and 10 English SVGs; all required translations present.')
