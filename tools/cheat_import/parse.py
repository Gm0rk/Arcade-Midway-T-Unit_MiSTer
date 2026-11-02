import re, glob, os, json, struct
import xml.etree.ElementTree as ET
D='/mnt/user-data/attachments/f76bcb13-0f26-5379-8463-e76bbbc69357/'
SIM='/home/claude/simroms/'
SETS={}  # filename -> set name
for f in glob.glob(D+'*.xml'):
    SETS[f]=os.path.basename(f).split('-',1)[1][:-4]
GAME={'mk':'Mortal Kombat','mk2':'Mortal Kombat II'}
def game(s):
    return GAME.get(s,'NBA Jam Tournament Edition' if s.startswith('nbajamte') else 'NBA Jam')

def split_top(s):
    out=[];d=0;cur=''
    for ch in s:
        if ch=='(':d+=1
        if ch==')':d-=1
        if ch==',' and d==0: out.append(cur);cur=''
        else: cur+=ch
    if cur.strip(): out.append(cur)
    return [x.strip() for x in out]

WR=re.compile(r'^maincpu\.([pm])([bwdq])@(\(?[0-9A-Fa-f]+\)?|\([^=]*\))\s*=\s*(.+)$', re.S)
HEX=re.compile(r'^(0x)?[0-9A-Fa-f]+$')

_img={}
def img(s):
    if s not in _img:
        p=SIM+s+'_rom0.bin'
        _img[s]=open(p,'rb').read() if os.path.exists(p) else None
    return _img[s]

def rom_word(s,off):
    d=img(s)
    if d is None or off+2>len(d): return None
    return d[off]|(d[off+1]<<8)

def parse_cheat(el,s):
    r={'set':s,'desc':(el.get('desc') or '').strip(),'comment':'','param':None,'writes':[],'offs':[],'flags':set(),'states':set()}
    c=el.find('comment')
    if c is not None and c.text: r['comment']=' '.join(c.text.split())
    p=el.find('parameter')
    if p is not None:
        items=[(i.get('value'),(i.text or '').strip()) for i in p.findall('item')]
        if items: r['param']={'items':items}
        else: r['param']={'min':p.get('min'),'max':p.get('max'),'step':p.get('step')}
    for sc in el.findall('script'):
        st=sc.get('state'); r['states'].add(st)
        for a in sc.findall('action'):
            cond=a.get('condition')
            if cond: r['flags'].add('conditional')
            for stmt in split_top((a.text or '').strip()):
                if st=='on' and re.match(r'^temp\d\s*=',stmt) : continue
                m=WR.match(stmt)
                if not m:
                    if re.match(r'^temp\d\s*=',stmt): continue
                    r['flags'].add('other:'+stmt[:40]); continue
                sp,sz,addr,val=m.groups()
                if addr.startswith('('): r['flags'].add('pointer'); continue
                a_=int(addr,16); v=val.strip()
                lit=int(v,16) if HEX.match(v) else None
                w=dict(space=sp,size=sz,addr=a_,val=v,lit=lit,cond=bool(cond),state=st)
                if st=='off': r['offs'].append(w)
                else: r['writes'].append(w)
    return r

recs=[]
for f in sorted(SETS):
    s=SETS[f]
    root=ET.parse(f).getroot()
    for el in root.iter('cheat'):
        if not list(el) and el.get('desc'):   # label-only line
            recs.append(dict(set=s,desc=el.get('desc').strip(),label=True)); continue
        recs.append(parse_cheat(el,s))
json.dump(recs,open('recs.json','w'),default=lambda o:sorted(o) if isinstance(o,set) else str(o),indent=0)
print(len(recs), sum(1 for r in recs if r.get('label')))
from collections import Counter
print(Counter(r['set'] for r in recs if not r.get('label')))
