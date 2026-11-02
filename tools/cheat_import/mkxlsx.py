import pickle, re
from collections import Counter, OrderedDict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter as L

rows=pickle.load(open('rows.pkl','rb'))
GORDER=['Mortal Kombat','Mortal Kombat II','NBA Jam','NBA Jam Tournament Edition']
FORDER=['Fits now','Needs byte merge','Needs one-shot write','Needs bit mask','Needs OSD option','Not practical']
CORD=['Gameplay assist','Boss / hidden content','Fatality','Selector / debug','Cosmetic / audio','Other']
rows.sort(key=lambda r:(GORDER.index(r['game']),FORDER.index(r['fit']),CORD.index(r['cat']),r['desc'].lower()))

def osdname(d):
    if len(d)<=27: return d
    cut=d[:27]
    if d[27]!=' ' and ' ' in cut: cut=cut[:cut.rfind(' ')]
    return cut.rstrip(' -:(')

F='Arial'
f_norm=Font(name=F,size=10); f_b=Font(name=F,size=10,bold=True); f_h=Font(name=F,size=10,bold=True,color='FFFFFF')
f_title=Font(name=F,size=14,bold=True); f_note=Font(name=F,size=9,italic=True,color='555555')
f_in=Font(name=F,size=10,color='0000FF')            # hardcoded inputs (blue)
f_link=Font(name=F,size=10,color='008000')          # cross-sheet links (green)
hdr=PatternFill('solid',fgColor='1F3864'); pickfill=PatternFill('solid',fgColor='FFFF00')
fitfill={'Fits now':'D9EAD3','Needs byte merge':'FFF2CC','Needs one-shot write':'FFF2CC','Needs bit mask':'FFF2CC','Needs OSD option':'FCE5CD','Not practical':'E7E6E6'}
thin=Side(style='thin',color='BBBBBB'); box=Border(left=thin,right=thin,top=thin,bottom=thin)
wrap=Alignment(wrap_text=True,vertical='top'); top=Alignment(vertical='top'); ctr=Alignment(horizontal='center',vertical='top')

wb=Workbook()
wsH=wb.active; wsH.title='Headroom'
wsC=wb.create_sheet('Cheats'); wsS=wb.create_sheet('Sets'); wsG=wb.create_sheet('Legend')

# ---------------- Cheats ----------------
cols=[('Pick',7),('Game',17),('Cheat (MAME name)',34),('OSD name (27 max)',28),('Name length',8),('Category',22),('Fit',19),('Units',7),
      ('What it needs',44),('What it does (MAME note)',40),('In the core already',34),('MAME sets with it',20),('Versions with an address',12),
      ('Same RAM address in every set',14),('Changes (reference set)',52),('MRA units (hex, reference set)',46),('Patch type',28),
      ('ROM words checked',12),('Parameter choices',34),('New to the core',9)]
for i,(h,w) in enumerate(cols,1):
    c=wsC.cell(row=1,column=i,value=h); c.font=f_h; c.fill=hdr; c.alignment=Alignment(wrap_text=True,vertical='center'); c.border=box
    wsC.column_dimensions[L(i)].width=w
wsC['A1'].font=Font(name=F,size=10,bold=True,color='000000'); wsC['A1'].fill=pickfill
wsC.row_dimensions[1].height=42
N=len(rows); last=N+1
for i,r in enumerate(rows,2):
    ver='%d of %d'%(len(r['sets']),r['core_versions'])
    same=r['same'] if len(r['sets'])>1 else 'one set'
    vv=r['verified']+((' ('+r['vnotes']+')') if r['vnotes'] else '')
    vals=[None,r['game'],r['desc'],osdname(r['desc']),'=LEN(D%d)'%i,r['cat'],r['fit'],(r['units'] if r['units'] else None),r['why'],r['comment'] or None,
          r['incore'] or None,', '.join(r['sets']),ver,same,r['detail'],r['hex'] or None,r['code'],vv or None,r['choices'] or None,'=IF(K%d="","Yes","No")'%i]
    for j,v in enumerate(vals,1):
        c=wsC.cell(row=i,column=j,value=v); c.font=f_norm; c.alignment=wrap if j in (3,4,9,10,11,15,16,17,19) else top; c.border=box
    wsC.cell(row=i,column=1).fill=PatternFill('solid',fgColor='FFFFCC'); wsC.cell(row=i,column=1).alignment=ctr
    wsC.cell(row=i,column=7).fill=PatternFill('solid',fgColor=fitfill[r['fit']])
    wsC.cell(row=i,column=4).font=f_in
    for j in (5,8,13): wsC.cell(row=i,column=j).alignment=ctr
dv=DataValidation(type='list',formula1='"Yes"',allow_blank=True,showErrorMessage=True,errorTitle='Pick',error='Type Yes, or leave blank')
wsC.add_data_validation(dv); dv.add('A2:A%d'%last)
wsC.conditional_formatting.add('B2:T%d'%last,FormulaRule(formula=['$A2="Yes"'],fill=PatternFill('solid',bgColor='FFE699',fgColor='FFE699')))
wsC.conditional_formatting.add('E2:E%d'%last,FormulaRule(formula=['$E2>27'],font=Font(name=F,size=10,bold=True,color='C00000')))
wsC.freeze_panes='D2'; wsC.auto_filter.ref='A1:T%d'%last

# ---------------- Sets ----------------
SETS=[('Mortal Kombat','mk','Mortal Kombat (rev 5.0 T-Unit 03-19-93)','mk',46),
('Mortal Kombat','mkr4','Mortal Kombat (rev 4.0 T-Unit 02-11-93)',None,0),
('Mortal Kombat','mktturbo','Mortal Kombat (Turbo Ninja T-Unit 03-19-93, hack)',None,0),
('Mortal Kombat II','mk2','Mortal Kombat II (rev L3.1)','mk2',95),
('Mortal Kombat II','mk2r32e','Mortal Kombat II (rev L3.2, European)',None,0),
('Mortal Kombat II','mk2r31e','Mortal Kombat II (rev L3.1, European)',None,0),
('Mortal Kombat II','mk2r30','Mortal Kombat II (rev L3.0)',None,0),
('Mortal Kombat II','mk2r21','Mortal Kombat II (rev L2.1)',None,0),
('Mortal Kombat II','mk2r20','Mortal Kombat II (rev L2.0)',None,0),
('Mortal Kombat II','mk2r14','Mortal Kombat II (rev L1.4)',None,0),
('Mortal Kombat II','mk2r11','Mortal Kombat II (rev L1.1)',None,0),
('Mortal Kombat II','mk2r42','Mortal Kombat II (rev L4.2, hack)',None,0),
('Mortal Kombat II','mk2r91','Mortal Kombat II (rev L9.1, hack)',None,0),
('Mortal Kombat II','mk2chal','Mortal Kombat II Challenger (hack)',None,0),
('Mortal Kombat II','(not in MAME)','Mortal Kombat II Plus (Beta 2, hack)',None,0),
('Judge Dredd','jdreddp','Judge Dredd (rev TA1 7-12-92, location test)',None,0),
('NBA Jam','nbajam','NBA Jam (rev 3.01 4-07-93)','nbajam',40),
('NBA Jam','nbajamr2','NBA Jam (rev 2.00 2-10-93)','nbajamr2',17),
('NBA Jam','nbajamr1','NBA Jam (rev 1.00 2-1-93)','nbajamr1',0),
('NBA Jam','nbajamp2','NBA Jam (proto v 2.00 1-24-93)','nbajamp2',0),
('NBA Jam','nbajamp1','NBA Jam (proto v 1.01 1-23-93)','nbajamp1',0),
('NBA Jam Tournament Edition','nbajamte','NBA Jam Tournament Edition (rev 4.0 3-23-94)','nbajamte',45),
('NBA Jam Tournament Edition','nbajamte4','NBA Jam Tournament Edition (rev 4.0 3-03-94)','nbajamte4',36),
('NBA Jam Tournament Edition','nbajamte3','NBA Jam Tournament Edition (rev 3.0 3-04-94)','nbajamte3',24),
('NBA Jam Tournament Edition','nbajamte3a','NBA Jam Tournament Edition (rev 3.0 2-26-94)','nbajamte3a',36),
('NBA Jam Tournament Edition','nbajamte2','NBA Jam Tournament Edition (rev 2.1 2-06-94)','nbajamte2',36),
('NBA Jam Tournament Edition','nbajamte2a','NBA Jam Tournament Edition (rev 2.0 1-28-94)','nbajamte2a',25),
('NBA Jam Tournament Edition','nbajamte1','NBA Jam Tournament Edition (rev 1.00 1-17-94)','nbajamte1',25),
('NBA Jam Tournament Edition','nbajamten','NBA Jam Tournament Edition (Nani Edition, rev 5.2 8-11-95, prototype)','nbajamten',1),
('NBA Jam Tournament Edition','nbajamtep2','NBA Jam Tournament Edition (proto 2.00 12-17-93)','nbajamtep2',0),
('(not in the core)','nbajamex','NBA Jam Extra (hack)','nbajamex',0),('(not in the core)','nbajamexa','NBA Jam Extra (alternate hack)','nbajamexa',0)]
given={'mk','mk2','nbajam','nbajamr2','nbajamr1','nbajamp2','nbajamp1','nbajamte','nbajamte4','nbajamte3','nbajamte3a','nbajamte2','nbajamte2a','nbajamte1','nbajamten','nbajamtep2','nbajamex','nbajamexa'}
sh=['Game','MAME set','Core version (MRA name)','Cheat file attached?','Cheats in the file','Note']
for j,h in enumerate(sh,1):
    c=wsS.cell(row=1,column=j,value=h); c.font=f_h; c.fill=hdr; c.border=box; c.alignment=Alignment(wrap_text=True,vertical='center')
for j,w in enumerate([26,16,62,16,14,70],1): wsS.column_dimensions[L(j)].width=w
for i,(g,s,n,x,cnt) in enumerate(SETS,2):
    if s in given:
        if cnt: note='Real cheat file'
        elif s in('nbajamr1','nbajamp2','nbajamp1','nbajamtep2'): note='File only says a related game has cheats; none for this set'
        else: note='File says the game was never looked at; no cheats'
    elif s=='(not in MAME)': note='Not a MAME game: no cheat file exists'
    else: note='No cheat file attached: addresses would be found from this version\'s program, as for the four Mortal Kombat II cheats'
    vals=[g,s,n,'Yes' if s in given else 'No',cnt if s in given else None,note]
    for j,v in enumerate(vals,1):
        c=wsS.cell(row=i,column=j,value=v); c.font=f_norm; c.border=box; c.alignment=wrap if j in(3,6) else top
wsS.freeze_panes='A2'
sr=len(SETS)+3
wsS.cell(row=sr,column=1,value='Each cheat file holds addresses for its own set only. ROM addresses change with the version; RAM addresses may or may not. The "Versions with an address" column on the Cheats sheet counts the sets whose file has the cheat.').font=f_note

# ---------------- Legend ----------------
wsG.column_dimensions['A'].width=24; wsG.column_dimensions['B'].width=110
wsG['A1']='Fit classes'; wsG['A1'].font=f_title
L_=[('Fits now','Only MRA lines (8-byte units) and a Cheats menu for that game. No FPGA change. Each version still needs its address found from its own program (tools/tunit_cheats.py style), unless its file already has it (see "Versions with an address").'),
('Needs byte merge','The cheat changes one byte of a 16-bit word. The board replaces the whole word on a read, so it would have to keep the game\'s other byte: two lane bits in the unit flags and a byte mux on the CPU read data. Small change, on a path I have no slack figure for.'),
('Needs bit mask','The cheat sets some bits of a word and keeps the rest (MAME: value OR (word AND NOT mask)). The unit has no room for a mask, so the unit becomes longer (size 10 or 12) and every existing cheat is re-encoded. Same read-path merge as the byte case.'),
('Needs one-shot write','The cheat writes a value once when switched on (Finish this Quarter Now, Select Level) and must not hold it. A poke-only flag on the existing poke path would do it. A byte write also needs a lane mask there.'),
('Needs OSD option','The value comes from a list too long to make one cheat per choice (character, team, level, score). It needs an OSD item and status bits that fill the unit, like Fixed AI Difficulty does now.'),
('Not practical','Conditional script (depends on other memory), pointer-relative address, more than 8 words (the unit limit), an address that is not RAM or ROM, or code injection (Free Fly Camera).'),
('Units','Words the cheat changes. Every unit patches one 16-bit word. Only 8 units can be on at once; the menu refuses a switch-on that would pass 8.'),
('Parameter cheats','A cheat with a short list of choices (Team Scores All Points: Team 1 or 2) is listed once here; the MRA would carry one cheat per choice. Units are for one choice.'),
('ROM words checked','For ROM patches, the MAME file lists the original word; "n of m" counts how many equal the word in the core\'s ROM image of that set. 295 of 297 matched over all files; the two that did not are in Mortal Kombat II (Always Get Finisher Announcement, Enable Finishers During Round).'),
('Patch type','ROM patches work only when the word is fetched as code. Branch opcodes (C0xx-CFxx) are safe; other words need a check that they are code, not table data.')]
for i,(a,b) in enumerate(L_,3):
    wsG.cell(row=i,column=1,value=a).font=f_b; c=wsG.cell(row=i,column=2,value=b); c.font=f_norm; c.alignment=wrap
    wsG.cell(row=i,column=1).alignment=top
    if a in fitfill: wsG.cell(row=i,column=1).fill=PatternFill('solid',fgColor=fitfill[a])

# ---------------- Headroom ----------------
wsH.column_dimensions['A'].width=44
for col,w in zip('BCDEFGH',[18,18,18,20,18,18,4]): wsH.column_dimensions[col].width=w
wsH['A1']='Cheat headroom: Arcade-Midway-T-Unit (Build 53)'; wsH['A1'].font=f_title
wsH['A2']='Facts come from the core source, the Main_MiSTer source and the Build 53 fit and timing reports. Estimates are marked.'; wsH['A2'].font=f_note
wsH['A4']='1. How much room there is'; wsH['A4'].font=Font(name=F,size=11,bold=True)
hh=['Item','Today','Limit / free','Note','','','']
for j,h in enumerate(hh,1):
    c=wsH.cell(row=5,column=j,value=h); c.font=f_h; c.fill=hdr
rowsH=[
('Cheats switched on at the same time (units)',4,8,'Hard limit. 8 cheat entries in the board\'s patch table (it has 16: 8 for the OSD secrets, 8 for cheats), MRA max="8", and the loader accepts 64 bytes. Today = Mortal Kombat II with all four cheats on (1 unit each).'),
('Free units with all four Mortal Kombat II cheats on',None,None,'The menu refuses a switch-on that would pass 8.'),
('Cheats listed in the menu',4,'no limit found','Main_MiSTer keeps the list in a vector; only switched-on units count. Names show 27 characters.'),
('Games with a Cheats menu',1,5,'Hidden by menu mask bit 0, set for Mortal Kombat II only. Showing it for Mortal Kombat, NBA Jam, NBA Jam TE and Judge Dredd is one change in the OSD mask.'),
('Logic used (ALMs)',32648,41910,'Build 53 fit: 78%. 9,262 ALMs free. Estimate, not measured: one more cheat entry is about 20-30 ALMs (a 28-bit compare, 16 bits of data, flags).'),
('Memory blocks used (M10K)',405,553,'Build 53 fit: 73%. Cheats use none.'),
('Worst setup slack, clk_sys (ns)',0.036,None,'SDRAM controller path, not the cheats. Any RTL change needs a fresh timing report.'),
('Board patch compare slack (ns)',0.55,None,'Path b_baddr to pt_q in the Build 53 paths report: +0.55 ns with a 9.25 ns data path. More entries lengthen this path, so adding entries is the timing risk, not area.'),
]
r0=6
for i,(a,b,c_,n) in enumerate(rowsH):
    rr=r0+i
    wsH.cell(row=rr,column=1,value=a).font=f_norm
    cb=wsH.cell(row=rr,column=2,value=b); cb.font=f_in
    cc=wsH.cell(row=rr,column=3,value=c_); cc.font=f_in
    cn=wsH.cell(row=rr,column=4,value=n); cn.font=f_norm; cn.alignment=wrap; wsH.merge_cells(start_row=rr,start_column=4,end_row=rr,end_column=7)
    for j in (1,2,3): wsH.cell(row=rr,column=j).alignment=top; wsH.cell(row=rr,column=j).border=box
    if rr in(10,11): cb.number_format='#,##0'; cc.number_format='#,##0'
wsH.cell(row=7,column=3,value='=C6-B6').font=f_norm
wsH.cell(row=7,column=2).value=None
wsH.cell(row=12,column=2).number_format='0.000'; wsH.cell(row=13,column=2).number_format='0.00'
for rr in range(r0,r0+len(rowsH)): wsH.row_dimensions[rr].height=64
wsH.merge_cells(start_row=5,start_column=4,end_row=5,end_column=7)

# section 2: candidate counts
s2=r0+len(rowsH)+2
wsH.cell(row=s2,column=1,value='2. What the 227 candidate cheats need').font=Font(name=F,size=11,bold=True)
heads=['Fit']+GORDER+['All games']
for j,h in enumerate(heads,1):
    c=wsH.cell(row=s2+1,column=j,value=h); c.font=f_h; c.fill=hdr; c.alignment=Alignment(wrap_text=True,vertical='center')
wsH.row_dimensions[s2+1].height=30
rng=lambda col:"Cheats!$%s$2:$%s$%d"%(col,col,last)
for i,fit in enumerate(FORDER):
    rr=s2+2+i
    c=wsH.cell(row=rr,column=1,value=fit); c.font=f_norm; c.fill=PatternFill('solid',fgColor=fitfill[fit]); c.border=box
    for j,g in enumerate(GORDER,2):
        cc=wsH.cell(row=rr,column=j,value='=COUNTIFS(%s,"%s",%s,$A%d)'%(rng('B'),g,rng('G'),rr)); cc.font=f_link; cc.border=box
    cc=wsH.cell(row=rr,column=6,value='=SUM(B%d:E%d)'%(rr,rr)); cc.font=f_b; cc.border=box
rr=s2+2+len(FORDER)
wsH.cell(row=rr,column=1,value='All candidates').font=f_b
for j in range(2,7):
    cc=wsH.cell(row=rr,column=j,value='=SUM(%s%d:%s%d)'%(L(j),s2+2,L(j),rr-1)); cc.font=f_b; cc.border=box
rr+=1
wsH.cell(row=rr,column=1,value='Fits now and new to the core').font=f_norm
for j,g in enumerate(GORDER,2):
    cc=wsH.cell(row=rr,column=j,value='=COUNTIFS(%s,"%s",%s,"Fits now",%s,"Yes")'%(rng('B'),g,rng('G'),rng('T'))); cc.font=f_link; cc.border=box
cc=wsH.cell(row=rr,column=6,value='=SUM(B%d:E%d)'%(rr,rr)); cc.font=f_b; cc.border=box
rr+=1
wsH.cell(row=rr,column=1,value='Fits now, new, and 1 unit').font=f_norm
for j,g in enumerate(GORDER,2):
    cc=wsH.cell(row=rr,column=j,value='=COUNTIFS(%s,"%s",%s,"Fits now",%s,"Yes",%s,1)'%(rng('B'),g,rng('G'),rng('T'),rng('H'))); cc.font=f_link; cc.border=box
cc=wsH.cell(row=rr,column=6,value='=SUM(B%d:E%d)'%(rr,rr)); cc.font=f_b; cc.border=box
s2end=rr
wsH.cell(row=s2end+1,column=1,value='Counts are one per cheat name per game. Judge Dredd has no cheat file. Mortal Kombat II and Mortal Kombat have a file for one version each, so a cheat that fits needs its address found in the other versions.').font=f_note

# section 3: picks
s3=s2end+3
wsH.cell(row=s3,column=1,value='3. Your picks (type Yes in column A of the Cheats sheet)').font=Font(name=F,size=11,bold=True)
h3=['Game','Cheats picked','Units, all on at once','Largest cheat (units)','Existing cheats (units)','Total with existing','Needs an FPGA change']
for j,h in enumerate(h3,1):
    c=wsH.cell(row=s3+1,column=j,value=h); c.font=f_h; c.fill=hdr; c.alignment=Alignment(wrap_text=True,vertical='center')
wsH.row_dimensions[s3+1].height=42
existing={'Mortal Kombat':0,'Mortal Kombat II':4,'NBA Jam':0,'NBA Jam Tournament Edition':0}
for i,g in enumerate(GORDER):
    rr=s3+2+i
    wsH.cell(row=rr,column=1,value=g).font=f_norm
    wsH.cell(row=rr,column=2,value='=COUNTIFS(%s,"Yes",%s,$A%d)'%(rng('A'),rng('B'),rr)).font=f_link
    wsH.cell(row=rr,column=3,value='=SUMIFS(%s,%s,"Yes",%s,$A%d)'%(rng('H'),rng('A'),rng('B'),rr)).font=f_link
    wsH.cell(row=rr,column=4,value='=_xlfn.MAXIFS(%s,%s,"Yes",%s,$A%d)'%(rng('H'),rng('A'),rng('B'),rr)).font=f_link
    wsH.cell(row=rr,column=5,value=existing[g]).font=f_in
    wsH.cell(row=rr,column=6,value='=C%d+E%d'%(rr,rr)).font=f_norm
    wsH.cell(row=rr,column=7,value='=COUNTIFS(%s,"Yes",%s,$A%d,%s,"Needs*")'%(rng('A'),rng('B'),rr,rng('G'))).font=f_link
    for j in range(1,8): wsH.cell(row=rr,column=j).border=box
rr=s3+2+len(GORDER)
wsH.cell(row=rr,column=1,value='All games').font=f_b
for j in (2,3,7):
    wsH.cell(row=rr,column=j,value='=SUM(%s%d:%s%d)'%(L(j),s3+2,L(j),rr-1)).font=f_b
wsH.cell(row=rr,column=4,value='=MAX(D%d:D%d)'%(s3+2,rr-1)).font=f_b
for j in range(1,8): wsH.cell(row=rr,column=j).border=box
wsH.cell(row=rr+1,column=1,value='Units, all on at once is the worst case. Only 8 units can be on at the same time, so a total above 8 is fine for the menu but the picks cannot all be on together. "Existing cheats" is the four Mortal Kombat II cheats (1 unit each); edit it if that changes.').font=f_note
wsH.cell(row=rr+2,column=1,value='Needs an FPGA change counts picks whose Fit starts with "Needs": each class is a separate change, described on the Legend sheet.').font=f_note
wsH.cell(row=rr+3,column=1,value='Example: type Yes next to "Dunks Always Break Backboard" (NBA Jam, 1 unit) and the NBA Jam row above shows 1 cheat and 1 unit.').font=f_note

for ws in (wsH,wsC,wsS,wsG):
    ws.sheet_view.showGridLines=False if ws in (wsH,wsG) else True
wsH.sheet_view.zoomScale=100
for ws in (wsH,wsC,wsS,wsG):
    ws.page_setup.orientation='landscape'; ws.page_setup.fitToWidth=1; ws.page_setup.fitToHeight=0
    ws.sheet_properties.pageSetUpPr.fitToPage=True
wb.save('/tmp/claude-0/cheatcat/Midway-T-Unit-cheat-picker.xlsx')
print('saved',N,'rows; last row',last,'; picks section row',s3)
