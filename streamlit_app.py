from __future__ import annotations
from io import BytesIO
from pathlib import Path
import json, re
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

BASE=Path(__file__).parent
SHAREPOINT_URL='https://dikichi-my.sharepoint.com/:x:/p/faiz_hadiyanul/IQBhaRp7aZ9kQqxBMD8CGalqAb9P84syKxrZ2xBJn4lP-Ns?e=MO7GY1'
REF=BASE/'geprek_ui_reference_v6.html'
st.set_page_config(page_title='Kichi-Kichi · Market Insight',page_icon='🍗',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],section[data-testid="stSidebar"]{display:none!important}.block-container{padding:0!important;max-width:none!important}iframe{border:0!important}</style>''',unsafe_allow_html=True)

def norm(x): return re.sub(r'\s+',' ',str(x or '').replace('\xa0',' ').strip()).lower()
def pick(cols, variants):
    for terms in variants:
        terms=[norm(t) for t in terms]
        for c in cols:
            n=norm(c)
            if all(t in n for t in terms): return c
    return None

def parse_file(content):
    if content[:2]==b'PK': return pd.read_excel(BytesIO(content),dtype=str)
    try: return pd.read_excel(BytesIO(content),dtype=str)
    except Exception:
        for enc in ('utf-8-sig','cp1252','latin1'):
            try: return pd.read_csv(BytesIO(content),dtype=str,encoding=enc)
            except Exception: pass
    raise RuntimeError('Respons SharePoint bukan workbook Excel/CSV.')

@st.cache_data(ttl=60,show_spinner=False)
def load_sharepoint():
    # Public SharePoint share link -> force file download. No dummy/local fallback.
    urls=[SHAREPOINT_URL+'&download=1', SHAREPOINT_URL.replace('?e=MO7GY1','?download=1&e=MO7GY1'), SHAREPOINT_URL+'&web=0']
    errors=[]
    for url in urls:
        try:
            r=requests.get(url,timeout=40,allow_redirects=True,headers={'User-Agent':'Mozilla/5.0','Accept':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*'})
            r.raise_for_status(); head=r.content[:300].lstrip().lower(); ctype=r.headers.get('content-type','').lower()
            if 'text/html' in ctype or head.startswith(b'<!doctype') or head.startswith(b'<html'):
                errors.append('SharePoint mengembalikan halaman viewer, bukan file Excel'); continue
            raw=parse_file(r.content)
            if not raw.empty:
                try: kw=pd.read_excel(BytesIO(r.content),sheet_name='keyword',dtype=str)
                except Exception: kw=pd.DataFrame(columns=['Group','Keyword','Reason'])
                return raw, kw
            errors.append('workbook kosong')
        except Exception as e: errors.append(str(e))
    raise RuntimeError('File SharePoint tidak dapat diunduh. Pastikan link memiliki akses Anyone/Publik. Detail: '+' | '.join(errors[-2:]))

def prepare(raw):
    cols=list(raw.columns)
    cmap={
      'Timestamp': [('completion time',),('start time',),('timestamp',),('waktu',),('tanggal',)],
      'Outlet': [('outlet',),('store',),('cabang',),('lokasi',)],
      'Ayam':[('rasa ayam',),('ayam',)], 'Sambal':[('rasa sambel',),('rasa sambal',),('sambal',)],
      'Kol Goreng':[('rasa kol goreng',),('kol goreng',)], 'Tahu':[('rasa tahu',),('tahu',)],
      'Tempe':[('rasa tempe',),('tempe',)], 'Bayam Crispy':[('rasa bayam crispy',),('bayam crispy',)],
      'Overall Rasa':[('overall rasa',)], 'Overall Plating':[('overall plating',),('tampilan product',),('tampilan produk',),('plating',)],
      'Rasa vs Harga':[('rasa vs harga',),('rasa','harga')], 'Porsi vs Harga':[('porsi vs harga',),('porsi','harga')],
      'Review':[('kritik','saran'),('review','saran'),('review',),('saran',),('masukan',),('comment',)]}
    found={k:pick(cols,v) for k,v in cmap.items()}
    if not found['Timestamp']: raise RuntimeError('Kolom waktu/tanggal tidak ditemukan. Kolom: '+' | '.join(map(str,cols)))
    ratings=['Ayam','Sambal','Kol Goreng','Tahu','Tempe','Bayam Crispy','Overall Rasa','Overall Plating','Rasa vs Harga','Porsi vs Harga']
    missing=[k for k in ratings if not found[k]]
    if missing: raise RuntimeError('Kolom rating belum cocok: '+', '.join(missing)+'. Kolom Excel: '+' | '.join(map(str,cols)))
    d=pd.DataFrame(); d['Timestamp']=pd.to_datetime(raw[found['Timestamp']],errors='coerce',dayfirst=True)
    d['Outlet']=raw[found['Outlet']].fillna('').astype(str).str.strip() if found['Outlet'] else 'Semua Outlet'
    for k in ratings: d[k]=pd.to_numeric(raw[found[k]],errors='coerce')
    d['Review']=raw[found['Review']].fillna('').astype(str).str.strip() if found['Review'] else ''
    d=d.dropna(subset=['Timestamp']).sort_values('Timestamp').reset_index(drop=True)
    if d.empty: raise RuntimeError('Workbook terbaca, tetapi tidak ada tanggal valid.')
    return d, found

def make_html(df, kw):
    src=REF.read_text(encoding='utf-8')
    style=re.search(r'<style>(.*?)</style>',src,re.S).group(1)
    records=[]
    for _,r in df.iterrows():
        x={'Timestamp':r.Timestamp.strftime('%Y-%m-%dT%H:%M:%S'),'Outlet':r.Outlet,'Review':r.Review}
        for c in ['Ayam','Sambal','Kol Goreng','Tahu','Tempe','Bayam Crispy','Overall Rasa','Overall Plating','Rasa vs Harga','Porsi vs Harga']:
            x[c]=None if pd.isna(r[c]) else float(r[c])
        records.append(x)
    data=json.dumps(records,ensure_ascii=False).replace('</','<\\/')
    keywords=[]
    if kw is not None and not kw.empty and {'Group','Keyword','Reason'}.issubset(set(map(str,kw.columns))):
        for _,r in kw[['Group','Keyword','Reason']].dropna(how='all').iterrows():
            g=str(r.get('Group','')).strip(); k=str(r.get('Keyword','')).strip(); rs=str(r.get('Reason','')).strip()
            if g and k and rs and g.lower()!='nan' and k.lower()!='nan' and rs.lower()!='nan':
                keywords.append({'group':g,'keyword':k.lower(),'reason':rs})
    kwdata=json.dumps(keywords,ensure_ascii=False).replace('</','<\\/')
    mn=df.Timestamp.min().strftime('%Y-%m-%d'); mx=df.Timestamp.max().strftime('%Y-%m-%d')
    return f'''<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Market Insight · Ayam Geprek Kichi-Kichi</title><style>{style}
.attr{{cursor:pointer}}.attr:hover{{border-color:#79b9bd;box-shadow:0 5px 14px #153c4612}}
.modalback{{position:fixed;inset:0;background:#082d3b80;display:none;align-items:center;justify-content:center;padding:18px;z-index:999}}.modalback.show{{display:flex}}
.modal{{background:#fff;width:min(760px,100%);max-height:86vh;overflow:auto;border-radius:16px}}.modalhead{{display:flex;justify-content:space-between;padding:20px 22px 14px;border-bottom:1px solid #e6eceb}}
.modalhead h3{{margin:0;color:#123d4a}}.close{{border:0;background:#edf3f2;border-radius:9px;width:36px;height:36px;font-size:20px}}.modalbody{{padding:18px 22px 22px}}
.modalstats{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:16px}}.mstat{{background:#f5f8f7;border:1px solid #e1e8e7;border-radius:10px;padding:12px}}.mstat span{{display:block;font-size:9px;font-weight:800}}.mstat b{{font-size:21px;color:#123d4a}}
.analysisbox{{margin-top:9px;padding:10px 12px;background:#f6f9f8;border:1px solid #e2e9e7;border-radius:9px}}
.reasonline{{display:grid;grid-template-columns:minmax(120px,1fr) minmax(180px,2fr) auto;gap:8px;padding:7px 0;border-bottom:1px solid #e7eceb;align-items:center}}
.reasonline:last-child{{border-bottom:0}}.reasonline b{{color:#173f4b}}.reasonrating{{font-weight:800;color:#b8493d;white-space:nowrap}}
.originalcomment{{margin-top:10px;padding-top:10px;border-top:1px dashed #d7e0de}}.originalcomment small{{display:block;color:#78898d;font-weight:800;margin-bottom:4px;text-transform:uppercase}}
.reasonTable{{width:100%;border-collapse:collapse}}.reasonTable th,.reasonTable td{{padding:11px 9px;border-bottom:1px solid #e7eceb;font-size:11px}}.reasonname{{font-weight:750}}
</style></head><body>
<header class="hero"><div class="eyebrow">MARKET INSIGHT · CUSTOMER SURVEY</div><h1>Ayam Geprek Kichi-Kichi</h1><p>Ringkasan penilaian produk dan detail respons pelanggan.</p>
<form class="filters" id="mainFilter"><label class="field"><b>PERIODE DARI</b><input id="dateFrom" type="date" min="{mn}" max="{mx}" value="{mn}"></label><label class="field"><b>SAMPAI</b><input id="dateTo" type="date" min="{mn}" max="{mx}" value="{mx}"></label><label class="field"><b>OUTLET</b><select id="outletFilter"></select></label><button class="btn">Terapkan</button></form></header>
<main><div class="summary-title"><h2>RINGKASAN OVERALL</h2><span>Skala rating 1–5</span></div>
<div class="stats stats4"><div class="card stat stat-teal"><div class="label">TOTAL RESPONDEN</div><div class="val" id="kpiN">0</div><div class="sub">Respons pada periode terpilih</div></div><div class="card stat stat-gold"><div class="label">OVERALL RASA</div><div class="val" id="kpiRasa">-</div><div class="sub">Product Quality · rasa</div></div><div class="card stat stat-green"><div class="label">OVERALL PLATING</div><div class="val" id="kpiPlate">-</div><div class="sub">Product Quality · tampilan produk</div></div><div class="card stat stat-red"><div class="label">QUALITY VS HARGA</div><div class="val" id="kpiHarga">-</div><div class="sub">Gabungan rasa & porsi vs harga</div></div></div>
<div class="grid"><div class="card"><div class="head"><h3>Rata-rata Nilai Atribut</h3><p>Rata-rata dari masing-masing kolom penilaian produk</p></div><div class="body"><div class="attrs" id="attrs"></div></div></div><div class="card"><div class="head"><h3>Tren Respons</h3><p>Jumlah respons per tanggal</p></div><div class="body"><div class="trend" id="trend"></div></div><div class="note">Tanggal mengikuti timestamp pada formulir.</div></div></div>
<div class="grid"><div class="card"><div class="head"><h3>Rating Rendah & Review Terkait</h3><p>Cek komentar responden berdasarkan atribut dan batas rating</p></div><div class="body"><div class="reviewfilters"><label class="field"><b>ASPEK PENILAIAN</b><select id="attrFilter"></select></label><label class="field"><b>BATAS RATING</b><select id="rateFilter"><option value="3">≤ 3</option><option value="2">≤ 2</option><option value="1">≤ 1</option><option value="5">Semua Rating</option></select></label></div><div class="review" id="reviews"></div></div></div><div class="card"><div class="head"><h3>Distribusi Overall Rasa</h3><p>Jumlah respons untuk setiap nilai</p></div><div class="body"><div class="trend" id="rating"></div></div></div></div>
<div class="card"><div class="head"><h3>Semua Data Survei</h3><p>Detail respons terbaru — kolom penilaian komponen tetap ditampilkan</p></div><div class="body tablewrap"><table class="table"><thead><tr><th>Waktu</th><th>Outlet</th><th>Ayam</th><th>Sambal</th><th>Kol Goreng</th><th>Tahu</th><th>Tempe</th><th>Bayam Crispy</th><th>Overall Rasa</th><th>Plating</th><th>Rasa vs Harga</th><th>Porsi vs Harga</th><th>Review / Saran</th></tr></thead><tbody id="rows"></tbody></table></div></div></main>
<div class="modalback" id="attrModal"><section class="modal"><div class="modalhead"><div><h3 id="modalTitle">Detail Penilaian</h3><p>Breakdown berdasarkan Reason dari master Keyword</p></div><button class="close" id="modalClose" type="button">×</button></div><div class="modalbody"><div class="modalstats"><div class="mstat"><span>Rata-rata Nilai</span><b id="mAvg">-</b></div><div class="mstat"><span>Total Penilaian</span><b id="mTotal">-</b></div><div class="mstat"><span>Review Teridentifikasi</span><b id="mIssue">-</b></div></div><table class="reasonTable"><thead><tr><th>Reason</th><th>Jumlah Review</th><th>Avg Nilai</th><th>Distribusi 1–5</th></tr></thead><tbody id="reasonRows"></tbody></table></div></section></div>
<script>
const KEYWORDS={kwdata};
const ALL={data}; const ATTRS=['Ayam','Sambal','Kol Goreng','Tahu','Tempe','Bayam Crispy']; const ASPECTS=[...ATTRS,'Overall Rasa','Overall Plating','Rasa vs Harga','Porsi vs Harga']; let CURRENT=[];
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m])); const avg=(a,k)=>{{const v=a.map(x=>x[k]).filter(Number.isFinite);return v.length?v.reduce((p,c)=>p+c,0)/v.length:null}}; const fmt=v=>v==null?'-':v.toFixed(2).replace('.',','); const dmy=s=>new Date(s).toLocaleDateString('id-ID',{{day:'2-digit',month:'short',year:'numeric'}}); const dm=s=>new Date(s).toLocaleDateString('id-ID',{{day:'2-digit',month:'short'}});
const outlets=[...new Set(ALL.map(x=>x.Outlet).filter(Boolean))].sort(); document.getElementById('outletFilter').innerHTML='<option>Semua Outlet</option>'+outlets.map(x=>`<option>${{esc(x)}}</option>`).join(''); document.getElementById('attrFilter').innerHTML='<option>Semua Aspek</option>'+ASPECTS.map(x=>`<option>${{x}}</option>`).join('');
function matchedReasons(x,attr){{
 const txt=normtxt(x.Review), rules=KEYWORDS.filter(k=>k.group===attr), reasons=[];
 rules.forEach(k=>{{if(txt.includes(normtxt(k.keyword))&&!reasons.includes(k.reason))reasons.push(k.reason)}});
 return reasons;
}}
function renderReviews(){{
 const a=document.getElementById('attrFilter').value,max=+document.getElementById('rateFilter').value;let out=[];
 CURRENT.forEach(x=>{{const names=a==='Semua Aspek'?ASPECTS:[a];names.forEach(n=>{{if(Number.isFinite(x[n])&&x[n]<=max)out.push({{...x,attr:n,rating:x[n],reasons:matchedReasons(x,n)}})}})}});
 out.sort((a,b)=>new Date(b.Timestamp)-new Date(a.Timestamp));
 document.getElementById('reviews').innerHTML=out.length?out.slice(0,100).map(x=>{{
   const reasonHtml=x.reasons.length?`<div class="analysisbox">${{x.reasons.map(r=>`<div class="reasonline"><b>${{esc(x.attr)}}</b><span>${{esc(r)}}</span><span class="reasonrating">${{x.rating}}/5</span></div>`).join('')}}</div>`:`<div class="analysisbox"><i>Tidak ada keyword/reason yang cocok untuk atribut ini.</i></div>`;
   return `<div class="comment"><div class="reviewleft"><b>${{x.attr}} · <span class="ratinglow">${{x.rating}}/5</span></b>${{reasonHtml}}<div class="originalcomment"><small>Komentar Responden</small><span>${{x.Review?`“${{esc(x.Review)}}”`:'<i>Tidak ada review/saran</i>'}}</span></div></div><span class="date">${{dm(x.Timestamp)}}<br>${{esc(x.Outlet)}}</span></div>`;
 }}).join(''):'<div class="comment">Tidak ada data pada filter ini.</div>'
}}
function render(){{const f=document.getElementById('dateFrom').value,t=document.getElementById('dateTo').value,o=document.getElementById('outletFilter').value;CURRENT=ALL.filter(x=>x.Timestamp.slice(0,10)>=f&&x.Timestamp.slice(0,10)<=t&&(o==='Semua Outlet'||x.Outlet===o));document.getElementById('kpiN').textContent=CURRENT.length;document.getElementById('kpiRasa').innerHTML=fmt(avg(CURRENT,'Overall Rasa'))+' <small>/ 5</small>';document.getElementById('kpiPlate').innerHTML=fmt(avg(CURRENT,'Overall Plating'))+' <small>/ 5</small>';const q=[avg(CURRENT,'Rasa vs Harga'),avg(CURRENT,'Porsi vs Harga')].filter(x=>x!=null);document.getElementById('kpiHarga').innerHTML=fmt(q.length?q.reduce((a,b)=>a+b,0)/q.length:null)+' <small>/ 5</small>';
 document.getElementById('attrs').innerHTML=ATTRS.map(n=>{{let v=avg(CURRENT,n);return `<div class="attr" data-attr="${{esc(n)}}"><div class="attrname">${{n}}</div><div class="score">${{fmt(v)}}</div><div class="track"><div class="fill" style="width:${{v?Math.min(100,v/5*100):0}}%"></div></div></div>`}}).join('');
 document.querySelectorAll('.attr[data-attr]').forEach(el=>el.onclick=()=>openAttr(el.dataset.attr));
 const by={{}};CURRENT.forEach(x=>{{let k=x.Timestamp.slice(0,10);by[k]=(by[k]||0)+1}});const tr=Object.entries(by).sort();const mx=Math.max(1,...tr.map(x=>x[1]));document.getElementById('trend').innerHTML=tr.map(x=>`<div class="tcol"><b>${{x[1]}}</b><div class="bar" style="height:${{Math.max(3,x[1]/mx*125)}}px"></div>${{dm(x[0]+'T00:00:00')}}</div>`).join('');
 const dist=[1,2,3,4,5].map(n=>[n,CURRENT.filter(x=>Math.round(x['Overall Rasa'])===n).length]);const md=Math.max(1,...dist.map(x=>x[1]));document.getElementById('rating').innerHTML=dist.map(x=>`<div class="tcol"><b>${{x[1]}}</b><div class="bar" style="height:${{Math.max(3,x[1]/md*125)}}px"></div>${{x[0]}}</div>`).join('');
 const cs=['Ayam','Sambal','Kol Goreng','Tahu','Tempe','Bayam Crispy','Overall Rasa','Overall Plating','Rasa vs Harga','Porsi vs Harga'];document.getElementById('rows').innerHTML=[...CURRENT].sort((a,b)=>new Date(b.Timestamp)-new Date(a.Timestamp)).map(x=>`<tr><td>${{dmy(x.Timestamp)}} ${{x.Timestamp.slice(11,16)}}</td><td>${{esc(x.Outlet)}}</td>${{cs.map(c=>`<td>${{Number.isFinite(x[c])?`<span class="pill">${{x[c]}}</span>`:''}}</td>`).join('')}}<td>${{esc(x.Review)}}</td></tr>`).join('');renderReviews()}}

function normtxt(s){{return String(s||'').toLowerCase().replace(/\\s+/g,' ').trim()}}
function openAttr(name){{
 const rows=CURRENT.filter(x=>Number.isFinite(x[name])), rules=KEYWORDS.filter(k=>k.group===name), grouped={{}};
 rows.forEach(x=>{{const txt=normtxt(x.Review), matched=new Set();rules.forEach(k=>{{if(txt.includes(normtxt(k.keyword)))matched.add(k.reason)}});matched.forEach(reason=>{{if(!grouped[reason])grouped[reason]={{count:0,sum:0,ratings:[0,0,0,0,0]}};const g=grouped[reason],rt=Number(x[name]);g.count++;g.sum+=rt;if(rt>=1&&rt<=5)g.ratings[Math.round(rt)-1]++}})}});
 const items=Object.entries(grouped).sort((a,b)=>b[1].count-a[1].count), issue=items.reduce((a,x)=>a+x[1].count,0);
 document.getElementById('modalTitle').textContent='Detail Penilaian — '+name;document.getElementById('mAvg').textContent=fmt(avg(rows,name))+' / 5';document.getElementById('mTotal').textContent=rows.length;document.getElementById('mIssue').textContent=issue;
 document.getElementById('reasonRows').innerHTML=items.length?items.map(([reason,v])=>`<tr><td class="reasonname">${{esc(reason)}}</td><td>${{v.count}}</td><td>${{(v.sum/v.count).toFixed(2).replace('.',',')}}</td><td>${{v.ratings.map((n,i)=>`${{i+1}}★ ${{n}}`).join(' · ')}}</td></tr>`).join(''):`<tr><td colspan="4">Belum ada review yang cocok dengan keyword ${{esc(name)}}.</td></tr>`;
 document.getElementById('attrModal').classList.add('show')
}}
function closeAttr(){{document.getElementById('attrModal').classList.remove('show')}}
document.getElementById('modalClose').onclick=closeAttr;document.getElementById('attrModal').onclick=e=>{{if(e.target.id==='attrModal')closeAttr()}};

document.getElementById('mainFilter').onsubmit=e=>{{e.preventDefault();render()}};document.getElementById('attrFilter').onchange=renderReviews;document.getElementById('rateFilter').onchange=renderReviews;render();
</script></body></html>'''

try:
    raw,kw=load_sharepoint(); df,mapping=prepare(raw); components.html(make_html(df,kw),height=2600,scrolling=True)
except Exception as e:
    st.error('Dashboard gagal membaca data SharePoint live. Tidak ada data dummy/fallback yang digunakan.')
    st.code(str(e))
    st.caption('Cache data: 60 detik. Source: Market Insight - Ayam Geprek Kichi-Kichi.xlsx')
