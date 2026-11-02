import json, re, os, sys, struct
from collections import OrderedDict, defaultdict
sys.path.insert(0,'/home/claude/Arcade-Midway-T-Unit/tools')
R=json.load(open('recs.json'))
SIM='/home/claude/simroms/'
_img={}
def img(s):
    if s not in _img:
        _img[s]=open(SIM+s+'_rom0.bin','rb').read()
    return _img[s]
def rw(s,off):
    d=img(s); return d[off]|(d[off+1]<<8)
RAM_LO,RAM_HI=0x01000000,0x013FFFFF
ROMBASE=0x0FF80000   # core word address of ROM byte 0 (bit 0xFF800000 >> 4)

GAMEOF=lambda s:'Mortal Kombat' if s=='mk' else 'Mortal Kombat II' if s=='mk2' else 'NBA Jam Tournament Edition' if s.startswith('nbajamte') else 'NBA Jam'
ORDER={'mk':0,'mk2':0,'nbajam':0,'nbajamr2':1,'nbajamte':0,'nbajamte4':1,'nbajamte3':2,'nbajamte3a':3,'nbajamte2':4,'nbajamte2a':5,'nbajamte1':6,'nbajamten':7}

def analyze(r):
    """-> dict(units, flags, ...) for one XML cheat in set r['set']"""
    s=r['set']; out=dict(flags=set(r['flags']),units=[],notes=[],lit_all=True,verified=[0,0],cond=False)
    W=[]
    seen=set()
    for w in r['writes']:
        k=(w['space'],w['size'],w['addr'],w['val'])
        if k in seen: continue
        seen.add(k); W.append(w)
    if any(f.startswith('other') for f in out['flags']) or 'pointer' in out['flags']:
        out['flags'].add('unsupported'); 
    words=OrderedDict()   # (kind,wordkey) -> dict(lanes,val,fetch)
    def add(kind,widx,lane_mask,value16,lit):
        key=(kind,widx)
        e=words.setdefault(key,dict(kind=kind,widx=widx,lanes=0,val=0,lit=True))
        e['lanes']|=lane_mask
        if lit is None: e['lit']=False
        else:
            for ln in (0,1):
                if lane_mask>>ln&1:
                    e['val']=(e['val']&~(0xFF<<(8*ln)))|(value16&(0xFF<<(8*ln)))
    for w in W:
        if w['cond']: out['cond']=True
        lit=w['lit']; a=w['addr']
        if w['space']=='m':
            if w['size']=='b':
                add('ROM',a//2,1<<(a&1),(lit or 0)<<(8*(a&1)) if lit is not None else 0,lit)
            elif w['size']=='w':
                if a&1: out['flags'].add('unsupported'); continue
                add('ROM',a//2,3,lit if lit is not None else 0,lit)
            elif w['size']=='d':
                if a&1: out['flags'].add('unsupported'); continue
                add('ROM',a//2,3,(lit&0xFFFF) if lit is not None else 0,lit)
                add('ROM',a//2+1,3,(lit>>16) if lit is not None else 0,lit)
        else:
            if not (RAM_LO<=a<=RAM_HI): out['flags'].add('notram')
            if w['size']=='b':
                if a&7: out['flags'].add('unsupported'); continue
                ln=(a>>3)&1
                add('RAM',a>>4,1<<ln,(lit or 0)<<(8*ln) if lit is not None else 0,lit)
            elif w['size']=='w':
                if a&15: out['flags'].add('unsupported'); continue
                add('RAM',a>>4,3,lit if lit is not None else 0,lit)
            elif w['size']=='d':
                if a&15: out['flags'].add('unsupported'); continue
                add('RAM',a>>4,3,(lit&0xFFFF) if lit is not None else 0,lit)
                add('RAM',(a>>4)+1,3,(lit>>16) if lit is not None else 0,lit)
    # ROM words: fill the other lane from the image, compute the final word
    for e in words.values():
        if e['kind']=='ROM':
            o=rw(s,e['widx']*2); e['orig']=o
            if e['lanes']!=3:
                keep=0xFF00 if e['lanes']==1 else 0x00FF
                e['val']=(e['val']&~keep)|(o&keep); e['lanes']=3
        else:
            e['partial']= e['lanes']!=3
    # verify ROM words against the off values
    for o in r['offs']:
        if o['space']!='m' or o['lit'] is None: continue
        a=o['addr']
        try:
            if o['size']=='w' and not a&1:
                out['verified'][1]+=1
                if rw(s,a)==o['lit']: out['verified'][0]+=1
                else: out['notes'].append('off value %04X differs from ROM image %04X at %X'%(o['lit'],rw(s,a),a))
            elif o['size']=='b':
                out['verified'][1]+=1
                if img(s)[a]==o['lit']: out['verified'][0]+=1
                else: out['notes'].append('off byte differs at %X'%a)
        except Exception as ex:
            out['notes'].append('verify error %s'%ex)
    out['units']=list(words.values())
    out['nwrites']=len(W)
    out['rom_orig']=[(e['widx'],e['orig'],e['val']) for e in words.values() if e['kind']=='ROM']
    # trigger style
    st=r['states']
    out['mode']='run' if 'run' in st else ('on' if 'on' in st else ('change' if 'change' in st else '-'))
    out['has_run']=any(w['state']=='run' for w in W)
    out['has_on']=any(w['state']=='on' for w in W)
    out['has_change']=any(w['state']=='change' for w in W)
    out['param']=r['param']
    out['uses_param']=any(w['lit'] is None for w in W)
    return out

# ---------------- families ----------------
fam=OrderedDict()
dupcount=defaultdict(int)
for r in R:
    if r.get('label'): continue
    s=r['set']; g=GAMEOF(s)
    d=r['desc'].strip()
    dupcount[(s,d)]+=1
    key=(g,d if dupcount[(s,d)]==1 else d+' #%d'%dupcount[(s,d)])
    fam.setdefault(key,[]).append((s,r))
print(len(fam),'families')
json.dump({'n':len(fam)},open('fam.json','w'))
import pickle
pickle.dump((fam,),open('fam.pkl','wb'))
# quick stats
res={}
for key,lst in fam.items():
    lst.sort(key=lambda x:ORDER[x[0]])
    s,r=lst[0]
    res[key]=[(s,analyze(r)) for s,r in lst]
pickle.dump(res,open('res.pkl','wb'))
vm=0;vt=0;bad=[]
for key,lst in res.items():
    for s,a in lst:
        vm+=a['verified'][0]; vt+=a['verified'][1]
        for n in a['notes']: bad.append((key,s,n))
print('ROM off-values verified',vm,'of',vt); 
for b in bad[:20]: print(b)
