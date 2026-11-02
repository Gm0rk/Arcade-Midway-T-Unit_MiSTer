import pickle, json, re, sys, struct
from collections import OrderedDict, defaultdict, Counter
sys.path.insert(0,'/home/claude/Arcade-Midway-T-Unit/tools')
import importlib.util
spec=importlib.util.spec_from_file_location('tc','/home/claude/Arcade-Midway-T-Unit/tools/tunit_cheats.py'); tc=importlib.util.module_from_spec(spec); spec.loader.exec_module(tc)
res=pickle.load(open('res.pkl','rb'))
fam=pickle.load(open('fam.pkl','rb'))[0]
CORE_VERS={'Mortal Kombat':3,'Mortal Kombat II':12,'NBA Jam':5,'NBA Jam Tournament Edition':9}
def pcount(p):
    if not p: return 0
    if 'items' in p: return len(p['items'])
    try:
        mn=int(p['min'],0); mx=int(p['max'],0); st=int(p.get('step') or 1,0)
        return (mx-mn)//st+1
    except Exception: return 0

CAT=[('Fatality',r'fatalit|babalit|friendship|finish|finisher'),
     ('Selector / debug',r'^select|free fly|hitbox|debug|ejb|watch current|attract mode screen|starting zone|kombat zone|battle plan|^p\d select|character|body/move|alternate outfit|morph|controlled by|team \d|score team|quarter$'),
     ('Boss / hidden content',r'reptile|jade|smoke|noob|goro|kintaro|pong|tank|unlock|all-star|secret|pit|shao|kahn|mountain|ending|test your might|endurance|clue|sitting in arena|kombat tomb|vs mode'),
     ('Cosmetic / audio',r'night|bloody|head|baby|sound|music|vocal|laugh|announce|taunt|volume|cheer|outfit'),
     ('Gameplay assist',r'infinite|never miss|hit anywhere|takes all damage|turbo|shot time|quarter|power|intercept|defense|quick hands|goal ?tending|scores all|easy|easily|dunk|drain|drain|accuracy|invincib|time left|computer assist|cpu|damage|energy|health|blocking|throw|immun|restriction|fighting before|single round|pong'),
    ]
def category(d):
    dl=d.lower()
    for name,rx in CAT:
        if re.search(rx,dl): return name
    return 'Other'

INCORE=[ # (game, regex, text)
 ('Mortal Kombat II',r'^infinite time$','In core: Infinite Round Time (Cheats)'),
 ('Mortal Kombat II',r'^infinite fatality time$','In core: Stop Finishing Move Timer (Cheats)'),
 ('Mortal Kombat II',r'^p1 infinite energy$','In core: Infinite Health P1 (Cheats)'),
 ('Mortal Kombat II',r'^p2 infinite energy$','In core: Infinite Health P2 (Cheats)'),
 ('Mortal Kombat II',r'show hitboxes','In core: Hitboxes (Hidden Items)'),
 ('Mortal Kombat II',r'winner battles noob','Similar in core: Noob Saibot Fight (Hidden Items)'),
 ('Mortal Kombat II',r'hidden ejb menu','In core: EJB Menu (Hidden Items)'),
 ('Mortal Kombat II',r'jade fight','Similar in core: Jade Fight (Hidden Items)'),
 ('Mortal Kombat II',r'smoke easily|press start to fight smoke','Similar in core: Smoke Fight (Hidden Items)'),
 ('Mortal Kombat II',r'pong','Similar in core: Pong at Battle 250 (Hidden Items)'),
 ('Mortal Kombat II',r'perm fatality|one button fatalit|one button friend','Similar in core: Finishing Moves page (picks any fighter\'s move)'),
 ('Mortal Kombat',r'reptile clues','Similar in core: Reptile Hints Always (Hidden Items)'),
 ('Mortal Kombat',r'access reptile','Similar in core: Reptile Fight Next (Hidden Items)'),
 ('Mortal Kombat',r'hidden ejb menu','In core: EJB Menu (Hidden Items)'),
 ('NBA Jam',r'big head','In core: Big Heads (Cheat Codes), all players at once'),
 ('NBA Jam',r'powerup intercept','In core: Power-Up Interceptions, all players at once'),
 ('NBA Jam',r'powerup defense','In core: Power-Up Defense, all players at once'),
 ('NBA Jam',r'shot % display','In core: Shot Percentage'),
 ('NBA Jam',r'computer assistance','In core: No CPU Assistance'),
 ('NBA Jam',r'hidden 3d tank game','In core: Tank Game'),
 ('NBA Jam Tournament Edition',r'baby size','In core: Baby Size Players'),
 ('NBA Jam Tournament Edition',r'tournament mode','In core: Tournament Mode'),
 ('NBA Jam Tournament Edition',r'shot % display','In core: Shot Percentage'),
 ('NBA Jam Tournament Edition',r'huge heads|big/huge head','In core: Head Size / Big Heads, all players at once'),
 ('NBA Jam Tournament Edition',r'max power','In core: Max Power, all players at once'),
 ('NBA Jam Tournament Edition',r'goal tending','In core: Power-Up Goaltending, all players at once'),
 ('NBA Jam Tournament Edition',r'quick hands','In core: Quick Hands, all players at once'),
]
def incore(g,d):
    for gg,rx,t in INCORE:
        if gg==g and re.search(rx,d.lower()): return t
    return ''

def hexs(b): return ' '.join(b[i:i+2].hex().upper() for i in range(0,len(b),2))

def describe(a):
    parts=[]
    for u in a['units']:
        if u['kind']=='ROM':
            parts.append('ROM %08X: %04X -> %04X'%(0xFF800000+u['widx']*16,u['orig'],u['val']))
        else:
            wa=u['widx']<<4
            if u['lanes']==3: parts.append('RAM %08X: word %s'%(wa,'%04X'%u['val'] if u['lit'] else 'param'))
            elif u['lanes']==1: parts.append('RAM %08X: byte %s'%(wa,'%02X'%(u['val']&0xFF) if u['lit'] else 'param'))
            else: parts.append('RAM %08X: byte %s'%(wa+8,'%02X'%(u['val']>>8) if u['lit'] else 'param'))
    return '; '.join(parts)

def classify(a,pc,g):
    n=len(a['units']); fl=a['flags']
    if 'unsupported' in fl: return 'Not practical','pointer-relative address or script logic',n
    if a['cond']: return 'Not practical','conditional script: depends on other memory',n
    if n==0: return 'Not practical','script writes no memory',n
    if n>8: return 'Not practical','%d words to change; the cheat limit is 8 units'%n,n
    if 'notram' in fl: return 'Not practical','address is not RAM or ROM (input port): check the original cheat',n
    kinds={u['kind'] for u in a['units']}
    rmw=any(w for w in [a])  # placeholder
    return None,None,n

rows=[]
for key,lst in res.items():
    g,d=key
    sets=[s for s,a in lst]
    sa=lst[0][1]
    ref=lst[0][0]
    rec=[r for (s,r) in fam[key] if s==ref][0]
    pc=pcount(rec['param'])
    fit,why,n=classify(sa,pc,g)
    kinds={u['kind'] for u in sa['units']}
    # read-modify-write expressions
    rmw=any(('maincpu' in w['val']) for w in rec['writes'])
    if fit is None:
        ram=[u for u in sa['units'] if u['kind']=='RAM']
        partial=any(u['lanes']!=3 for u in ram)
        oneshot=bool(ram) and not sa['has_run']
        uses_param=sa['uses_param'] and not rmw
        if uses_param and pc>6:
            fit,why='Needs OSD option','value chosen from %d choices: needs an OSD item (status bits) that fills the unit'%pc
        elif oneshot:
            fit,why='Needs one-shot write','writes the value once when switched on: needs a poke-only entry'+('; byte lanes need a mask' if partial else '')
        elif rmw:
            fit,why='Needs bit mask','sets some bits of a word and keeps the rest: the unit would need a bit mask (longer unit) and a merge on the read'
        elif partial:
            fit,why='Needs byte merge','changes one byte of a word: the read patch must keep the other byte of the game\'s word'
        else:
            fit='Fits now'
            if uses_param: why='%d choices: list one cheat per choice, %d unit%s each'%(pc,n,'' if n==1 else 's')
            else: why='MRA entry only'
    # units across sets
    nmax=max(len(a['units']) for s,a in lst)
    nmin=min(len(a['units']) for s,a in lst)
    # same address across sets (RAM only)
    sig=[tuple(sorted((u['kind'],u['widx']) for u in a['units'])) for s,a in lst]
    same='Yes' if len(set(sig))==1 else 'No'
    if all(u['kind']=='ROM' for u in sa['units']) and len(lst)>1: same='No (ROM differs by version)' if same=='No' else 'Yes'
    # mra hex
    hexv=''
    if fit=='Fits now' and not sa['uses_param']:
        b=b''
        for u in sa['units']:
            b+=tc.unit((0xFF800000 if u['kind']=='ROM' else 0)+(u['widx']<<4), u['val'], fetch=(u['kind']=='ROM'), store=False)
        hexv=hexs(b)
    if kinds=={'ROM'}:
        code='Branch opcodes only (C0xx-CFxx)' if all((u['orig']&0xF000)==0xC000 for u in sa['units']) else ('Mixed: some words are not branch opcodes' if any((u['orig']&0xF000)==0xC000 for u in sa['units']) else 'Other words: check they are code, not table data')
    elif kinds=={'RAM'}: code='RAM variable'
    else: code='ROM and RAM'
    vm,vt=0,0
    for s,a in lst: vm+=a['verified'][0]; vt+=a['verified'][1]
    nn=[]; 
    for s,a in lst:
        for x in a['notes']: nn.append('%s: %s'%(s,x))
    comment=rec['comment']
    choices=''
    if rec['param']:
        p=rec['param']
        if 'items' in p: choices='; '.join('%s = %s'%(t,v) for v,t in p['items'][:12])+('; ...' if len(p['items'])>12 else '')
        else: choices='%s to %s'%(p['min'],p['max'])
    rows.append(dict(game=g,desc=d,cat=category(d),comment=comment,fit=fit,why=why,units=n if nmax==nmin else nmax,
        unit_range=('%d'%nmax if nmax==nmin else '%d-%d'%(nmin,nmax)),sets=sets,ref=ref,same=same,detail=describe(sa),
        hex=hexv,code=code,choices=choices,incore=incore(g,d),verified='%d of %d'%(vm,vt) if vt else '',vnotes=' | '.join(nn),
        core_versions=CORE_VERS[g],mode=sa['mode'],pc=pc))
pickle.dump(rows,open('rows.pkl','wb'))
c=Counter((r['game'],r['fit']) for r in rows)
for k in sorted(c): print(k,c[k])
print(Counter(r['fit'] for r in rows))
