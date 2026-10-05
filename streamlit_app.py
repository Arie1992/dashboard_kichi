from __future__ import annotations
from io import BytesIO
from pathlib import Path
import html as htmlmod, json, re
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

BASE=Path(__file__).parent
OLD_TEMPLATE=BASE/'dashboard_template.html'
SHEET_ID='1K08X5qX9fY4dLBCn7lsOET1pMe8d25wz9iGF0ssYrE0'; GID='771277575'
OLD_URL=f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'
SHAREPOINT_URL='https://dikichi-my.sharepoint.com/:x:/p/faiz_hadiyanul/IQBhaRp7aZ9kQqxBMD8CGalqAb9P84syKxrZ2xBJn4lP-Ns?e=MO7GY1'

st.set_page_config(page_title='Kichi-Kichi · Market Insight',page_icon='🍗',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],section[data-testid="stSidebar"]{display:none!important}.block-container{padding:0!important;max-width:none!important}iframe{border:0!important}</style>''',unsafe_allow_html=True)

def nh(x): return re.sub(r'\s+',' ',str(x or '').replace('\xa0',' ').strip()).lower()
def fc(cols,*terms):
    terms=[nh(t) for t in terms]
    return next((c for c in cols if all(t in nh(c) for t in terms)),None)
def first_col(cols, variants):
    for terms in variants:
        c=fc(cols,*terms)
        if c:return c
    return None

@st.cache_data(ttl=60)
def old_data():
    r=requests.get(OLD_URL,timeout=25); r.raise_for_status(); raw=pd.read_csv(BytesIO(r.content),dtype=str)
    cols=list(raw.columns); ts=fc(cols,'timestamp'); menu=fc(cols,'menu yang dipesan')
    sats=[c for c in cols if nh(c).split('.')[0]==nh('Apakah Anda puas dengan menu tersebut?')]
    if not ts or not menu or not sats: raise RuntimeError('Kolom dashboard ALL tidak lengkap.')
    out=pd.DataFrame({'Timestamp':pd.to_datetime(raw[ts],errors='coerce',dayfirst=True),'Menu':raw[menu]})
    aliases={'ayam geprek kichi-kichi':'Ayam Geprek Kichi-Kichi','ayam geprek kichi kichi':'Ayam Geprek Kichi-Kichi','crispy ori':'Crispy Ori','crispy original':'Crispy Ori'}
    out['Menu']=out['Menu'].map(lambda x:aliases.get(str(x).strip().casefold(),str(x).strip()))
    out['Overall']=raw[sats].apply(lambda x:pd.to_numeric(x,errors='coerce')).bfill(axis=1).iloc[:,0]
    for a in ['Rasa','Crispy','Juicy','Ukuran']:
        c=next((c for c in cols if nh(c).split('.')[0]==nh(a)),None); out[a]=pd.to_numeric(raw[c],errors='coerce') if c else float('nan')
    return out.dropna(subset=['Timestamp','Menu']).query("Menu in ['Ayam Geprek Kichi-Kichi','Crispy Ori']").sort_values('Timestamp').reset_index(drop=True)

def sidebar_css(): return '''<style>
:root{--side:260px;--navy:#0d3d4d;--teal:#2f98a5;--paper:#f1f0ea;--line:#d8e0df;--ink:#253941;--muted:#77888c}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px Inter,system-ui,"Segoe UI",sans-serif}.shell{display:grid;grid-template-columns:var(--side) minmax(0,1fr);min-height:100vh;transition:grid-template-columns .2s}.shell.sidebar-collapsed{grid-template-columns:0 minmax(0,1fr)}
.sidebar{position:sticky;top:0;height:100vh;background:#fff;border-right:1px solid var(--line);padding:28px 14px 18px;overflow:hidden;transition:padding .2s,border .2s}.sidebar.hide{padding:0;border:0}.side-title{font-size:12px;font-weight:900;letter-spacing:1.2px;color:#95a3a6;margin:8px 12px 14px}.side-link{display:block;text-decoration:none;color:#42565e;padding:14px 16px;border-radius:10px;margin:5px 0;font-size:16px}.side-link.active{background:#e8f2f1;color:#073a4b;font-weight:800}.hidebtn{position:absolute;bottom:18px;left:14px;right:14px;border:1px solid var(--line);background:#fff;border-radius:9px;padding:10px;cursor:pointer;color:#52666d}.menutoggle{position:fixed;left:14px;top:14px;z-index:99;width:44px;height:44px;border:1px solid var(--line);border-radius:9px;background:#fff;color:var(--navy);font-size:24px;box-shadow:0 4px 14px #0d3d4d22;cursor:pointer}.content{min-width:0}.sidebar:not(.hide)~.content .menutoggle{display:none}@media(max-width:760px){.shell{grid-template-columns:0 minmax(0,1fr)}.sidebar{position:fixed;z-index:100;width:260px;transform:translateX(-100%)}.sidebar:not(.hide){transform:translateX(0);padding:28px 14px 18px}.sidebar:not(.hide)~.content .menutoggle{display:block}}
</style>'''
def sidebar(active):
    return f'''<aside id="sidebar" class="sidebar"><div class="side-title">MARKET INSIGHT</div><a class="side-link {'active' if active=='all' else ''}" target="_top" href="?view=all">▣ ALL</a><a class="side-link {'active' if active=='geprek' else ''}" target="_top" href="?view=geprek">▣ Ayam Geprek</a><button id="hidebtn" class="hidebtn">‹ Hide Menu</button></aside>'''
def side_js(): return '''<script>const sb=document.getElementById('sidebar'),sh=document.querySelector('.shell');function setSide(h){sb.classList.toggle('hide',h);sh.classList.toggle('sidebar-collapsed',h);try{localStorage.setItem('kk_hide',h?'1':'0')}catch(e){}}document.getElementById('hidebtn').onclick=()=>setSide(true);document.getElementById('menutoggle').onclick=()=>setSide(!sb.classList.contains('hide'));try{if(localStorage.getItem('kk_hide')==='1')setSide(true)}catch(e){}</script>'''

def old_html(data):
    t=OLD_TEMPLATE.read_text(encoding='utf-8'); menus=['Ayam Geprek Kichi-Kichi','Crispy Ori']; origin=data.Timestamp.iloc[0].strftime('%Y-%m-%dT%H:%M:%S'); prev=data.Timestamp.iloc[0]; enc=[]
    for _,r in data.iterrows():
        cur=r.Timestamp; d=max(0,round((cur-prev).total_seconds())); prev=cur; vals=[r.Overall,r.Rasa,r.Crispy,r.Juicy,r.Ukuran]; payload=str(menus.index(r.Menu))+''.join(str(int(v)) if pd.notna(v) else '0' for v in vals); enc.append(f'{d}:{payload}')
    mn=data.Timestamp.min().strftime('%Y-%m-%d'); mx=data.Timestamp.max().strftime('%Y-%m-%d')
    t=t.replace("const MENU_NAMES=['Ayam Geprek Kichi-Kichi','Crispy Ori'];",f'const MENU_NAMES={json.dumps(menus)};',1).replace("const ORIGIN=new Date('2026-10-02T14:48:20');",f"const ORIGIN=new Date('{origin}');",1)
    t=re.sub(r"const ENCODED='[^']*';",f"const ENCODED='{';'.join(enc)}';",t,count=1)
    t=re.sub(r'min="2026-10-02" max="2026-10-03" value="2026-10-02"',f'min="{mn}" max="{mx}" value="{mn}"',t,count=1); t=re.sub(r'min="2026-10-02" max="2026-10-03" value="2026-10-03"',f'min="{mn}" max="{mx}" value="{mx}"',t,count=1)
    t=t.replace('__MIN_DATE__',mn).replace('__MAX_DATE__',mx).replace('Menampilkan ${n} dari 132 respons','Menampilkan ${n} dari '+str(len(data))+' respons')
    body=re.search(r'<body>(.*)</body>',t,re.S).group(1); head=re.search(r'<head>(.*)</head>',t,re.S).group(1)
    return '<!doctype html><html><head>'+head+sidebar_css()+'</head><body><div class="shell">'+sidebar('all')+'<div class="content"><button id="menutoggle" class="menutoggle">☰</button>'+body+'</div></div>'+side_js()+'</body></html>'

def read_blob(b):
    if b[:2]==b'PK': return pd.read_excel(BytesIO(b),dtype=str)
    try:return pd.read_excel(BytesIO(b),dtype=str)
    except Exception:
        for e in ['utf-8-sig','cp1252','latin1']:
            try:return pd.read_csv(BytesIO(b),dtype=str,encoding=e)
            except Exception: pass
    raise ValueError('Respons bukan file Excel/CSV yang valid.')

@st.cache_data(ttl=60)
def geprek_raw():
    # Exact public share link supplied by user. No dummy/local fallback.
    base=SHAREPOINT_URL
    candidates=[base+'&download=1',base.replace('?e=MO7GY1','?download=1&e=MO7GY1'),base+'&web=0']
    errs=[]
    for u in candidates:
        try:
            r=requests.get(u,timeout=35,allow_redirects=True,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36','Accept':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*'})
            r.raise_for_status(); ctype=r.headers.get('content-type','').lower(); head=r.content[:500].lstrip().lower()
            if 'text/html' in ctype or head.startswith(b'<!doctype') or head.startswith(b'<html'):
                errs.append('SharePoint mengembalikan halaman viewer HTML, bukan workbook'); continue
            df=read_blob(r.content)
            if df.empty: errs.append('Workbook terbaca tetapi kosong'); continue
            return df,'SharePoint live'
        except Exception as e: errs.append(f'{type(e).__name__}: {e}')
    raise RuntimeError('Direct SharePoint belum menghasilkan workbook yang bisa dibaca. '+ ' | '.join(errs[-3:]))

def geprek_data():
    raw,src=geprek_raw(); cols=list(raw.columns)
    tm=first_col(cols,[("completion time",),("start time",),("timestamp",),("waktu",)])
    mapping={
      'Ayam':[("rasa ayam",),("ayam",)],'Sambal':[("rasa sambel",),("rasa sambal",),("sambal",)],'Kol Goreng':[("rasa kol goreng",),("kol goreng",)],'Tahu':[("rasa tahu",),("tahu",)],'Tempe':[("rasa tempe",),("tempe",)],'Bayam Crispy':[("rasa bayam crispy",),("bayam crispy",)],
      'Overall Rasa':[("overall rasa",)],'Overall Plating':[("overall plating",),("tampilan product",),("tampilan produk",)],'Rasa vs Harga':[("rasa vs harga",)],'Porsi vs Harga':[("porsi vs harga",)]}
    found={k:first_col(cols,v) for k,v in mapping.items()}; comment=first_col(cols,[("kritik","saran"),("review",),("saran",),("comment",)])
    if not tm: raise RuntimeError('Kolom tanggal/waktu tidak ditemukan. Kolom tersedia: '+', '.join(map(str,cols[:12])))
    essential=['Overall Rasa','Overall Plating','Rasa vs Harga','Porsi vs Harga']
    missing=[k for k in essential if not found[k]]
    if missing: raise RuntimeError('Mapping kolom belum cocok untuk: '+', '.join(missing)+'. Kolom workbook: '+ ' | '.join(map(str,cols)))
    df=pd.DataFrame({'Timestamp':pd.to_datetime(raw[tm],errors='coerce',dayfirst=True)})
    for k,c in found.items(): df[k]=pd.to_numeric(raw[c],errors='coerce') if c else float('nan')
    df['Review']=raw[comment].fillna('').astype(str).str.strip() if comment else ''
    df=df.dropna(subset=['Timestamp']).sort_values('Timestamp').reset_index(drop=True)
    if df.empty: raise RuntimeError('Tidak ada timestamp valid setelah workbook dibaca.')
    return df,src

def geprek_html(df,src):
    # IMPORTANT: use the exact HTML supplied by the user as the visual source of truth.
    # This prevents Streamlit/custom CSS from rebuilding or shifting the reference layout.
    return (BASE / "geprek_ui_reference_v6.html").read_text(encoding="utf-8")

view=st.query_params.get('view','geprek')
if view=='all':
    try: components.html(old_html(old_data()),height=2300,scrolling=True)
    except Exception as e: st.error(f'Dashboard ALL gagal dimuat: {e}')
else:
    try:
        df,src=geprek_data(); components.html(geprek_html(df,src),height=2800,scrolling=True)
    except Exception as e:
        st.error('Dashboard Ayam Geprek gagal membaca SharePoint live. Tidak ada dummy/fallback yang ditampilkan.')
        st.code(str(e))
        st.caption('Source dikunci ke link SharePoint yang diberikan. Cache 60 detik.')
