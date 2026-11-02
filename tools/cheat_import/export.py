import pickle, sys, collections
res=pickle.load(open('res.pkl','rb'))
names=pickle.load(open('names.pkl','rb'))
picked=pickle.load(open('picked.pkl','rb'))
rows=pickle.load(open('rows.pkl','rb'))
NAME={(g,d):n for g,d,n in names}

# picks whose menu entry is made from the finders in tools/tunit_secrets.py / tunit_cheats.py (every version),
# or already in the core's Cheats menu: not exported from the MAME files
FINDER=set()
for p in (1,2,3,4):
    FINDER.add(('NBA Jam','P%d Big Head'%p if p>1 else 'P1 Big Head #2'))
    FINDER.add(('NBA Jam','P%d Powerup Intercept'%p)); FINDER.add(('NBA Jam','P%d Powerup Defense'%p))
    for k in ('Big/Huge Head','Max Power','Powerup Goal Tending','Quick Hands'):
        FINDER.add(('NBA Jam Tournament Edition','P%d %s'%(p,k)))
FINDER |= {('NBA Jam','Play Hidden 3D Tank Game'),('NBA Jam','Shot % Display (Learning Mode 2)'),('NBA Jam','Computer Assistance Turned Off'),
  ('NBA Jam Tournament Edition','Tournament Mode (Stops other Power Up cheats working)'),('NBA Jam Tournament Edition','Baby Size Players'),
  ('NBA Jam Tournament Edition','Shot % Display'),('NBA Jam Tournament Edition','Huge Heads in preference to Big Heads'),
  ('Mortal Kombat II','Enable Hidden Debug Tool: Show Hitboxes'),('Mortal Kombat II','Go to Jade Fight Without Low Kick Requirement'),
  ('Mortal Kombat II','Always Play Pong After First Round'),('Mortal Kombat II','Winner Battles Noob Saibot'),('Mortal Kombat II','Press Start To Fight Smoke'),
  ('Mortal Kombat','Always have Reptile Clues'),
  ('Mortal Kombat II','P1 Drain all Energy Now!'),('Mortal Kombat II','P2 Drain all Energy Now!'),
  # in the Cheats menu already
  ('Mortal Kombat II','Infinite Time'),('Mortal Kombat II','Infinite Fatality Time'),('Mortal Kombat II','P1 Infinite Energy'),('Mortal Kombat II','P2 Infinite Energy')}
missing=[k for k in FINDER if k not in picked]
print('finder keys not picked:',missing)

out=collections.OrderedDict()
problems=[]
cnt=collections.Counter()
for (g,d) in sorted(picked):
    if (g,d) in FINDER: continue
    key=(g,d)
    if key not in res: problems.append(('no res',key)); continue
    for s,a in res[key]:
        if a['cond'] or 'unsupported' in a['flags'] or 'notram' in a['flags']:
            problems.append(('unsupported',key,s)); continue
        units=[]
        oneshot=(a['mode']=='on') or (a['has_on'] and not a['has_run'])
        for u in a['units']:
            if not u['lit'] and u['kind']=='RAM':
                problems.append(('not literal',key,s,u)); continue
            if u['kind']=='ROM':
                units.append((0xFF800000+(u['widx']<<4), u['val'], 0xFFFF, 'F'))
            else:
                ln=u['lanes']
                mask=0xFFFF if ln==3 else (0x00FF if ln==1 else 0xFF00)
                val=u['val']&mask
                if oneshot: units.append((u['widx']<<4, u['val'] if ln==3 else val, 0xFFFF, 'P'))
                else: units.append((u['widx']<<4, val, mask, ''))
        out.setdefault(s,[]).append((NAME[key],units,key))
        cnt[s]+=1
print(cnt)
print('problems',problems[:10],len(problems))
# duplicate names per set
for s,l in out.items():
    c=collections.Counter(n for n,_,_ in l)
    for n,k in c.items():
        if k>1: print('DUP',s,n)
pickle.dump(out,open('export.pkl','wb'))
