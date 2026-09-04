#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, html, io, json, os, re, statistics, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT/'config/settings.json').read_text(encoding='utf-8'))
UA='TechTicker/0.1 (+https://github.com/cheneddie/TechTicker)'


def get_bytes(url, ua=UA, timeout=30, retries=3):
    last=None
    for i in range(retries):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':ua,'Accept':'*/*','Accept-Encoding':'identity'})
            with urllib.request.urlopen(req,timeout=timeout) as r: return r.read()
        except Exception as e: last=e
    raise RuntimeError(f'GET failed: {url}: {last}')

def get_text(url, **kw): return get_bytes(url, **kw).decode('utf-8','replace')
def get_json(url, **kw): return json.loads(get_text(url, **kw))


def fred_series(series_id):
    url=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series_id)}'
    rows=[]
    for row in csv.DictReader(io.StringIO(get_text(url))):
        raw=row.get(series_id)
        if not raw or raw=='.': continue
        try: rows.append((row['DATE'],float(raw)))
        except: pass
    return rows

def pct(points,n):
    if len(points)<=n or points[-1-n][1]==0:return None
    return (points[-1][1]/points[-1-n][1]-1)*100

def fred_summary(points):
    if not points:return {'available':False}
    return {'available':True,'latest_date':points[-1][0],'latest':points[-1][1],'mom_pct':pct(points,1),'chg_3m_pct':pct(points,3),'yoy_pct':pct(points,12),'n':len(points)}

CAPEX_CONCEPTS=['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsForProceedsFromProductiveAssets','PaymentsToAcquireProductiveAssets']
def sec_companyfacts(cik):
    ua=os.environ.get('SEC_USER_AGENT','TechTicker/0.1 contact=https://github.com/cheneddie/TechTicker/issues')
    return get_json(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',ua=ua)

def sec_capex_summary(cf):
    us=((cf.get('facts') or {}).get('us-gaap') or {})
    units=None; concept=None
    for c in CAPEX_CONCEPTS:
        o=us.get(c)
        if o and (o.get('units') or {}).get('USD'):concept=c;units=o['units']['USD'];break
    if not units:return {'available':False,'reason':'capex concept not found'}
    frames={}
    for e in units:
        f=e.get('frame') or ''
        if not re.fullmatch(r'CY\d{4}Q[1-4]',f) or e.get('form') not in {'10-Q','10-K'} or 'val' not in e:continue
        if f not in frames or (e.get('filed') or '')>(frames[f].get('filed') or ''):frames[f]=e
    if not frames:return {'available':False,'reason':'no quarterly frames'}
    lf=sorted(frames)[-1]; latest=frames[lf]; year=int(lf[2:6]); q=lf[-2:]; pf=f'CY{year-1}{q}'; prior=frames.get(pf)
    yoy=None
    if prior and prior.get('val') not in (None,0):yoy=(latest['val']/prior['val']-1)*100
    return {'available':True,'concept':concept,'latest_frame':lf,'latest_value_usd':latest['val'],'prior_frame':pf if prior else None,'prior_value_usd':prior['val'] if prior else None,'yoy_pct':yoy,'filed':latest.get('filed'),'form':latest.get('form')}

def capex_confirmation(capex):
    vals=[v.get('yoy_pct') for v in capex.values() if v.get('available') and v.get('yoy_pct') is not None]
    if not vals:return {'available':False,'score':None}
    med=statistics.median(vals)
    score=100 if med<=0 else 75 if med<=10 else 40 if med<=25 else 15 if med<=50 else 0
    return {'available':True,'median_yoy_pct':med,'score':score}


def google_news(query,max_items=30):
    url='https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=en-US&gl=US&ceid=US:en'
    root=ET.fromstring(get_bytes(url)); out=[]
    for item in root.findall('./channel/item')[:max_items]:
        title=html.unescape((item.findtext('title') or '').strip()); link=(item.findtext('link') or '').strip(); desc=html.unescape(item.findtext('description') or ''); desc=re.sub(r'<[^>]+>',' ',desc); desc=re.sub(r'\s+',' ',desc).strip(); raw=item.findtext('pubDate') or ''
        try: pub=parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
        except: pub=raw
        out.append({'title':title,'link':link,'description':desc,'published':pub})
    return out

def classify_event(cfg,items,lookback_days=120):
    cutoff=datetime.now(timezone.utc)-timedelta(days=lookback_days); evidence=[]; counter=[]; total=0.0
    for item in items:
        try: pub=datetime.fromisoformat(item['published'])
        except: pub=None
        if pub and pub<cutoff:continue
        text=(item.get('title','')+' '+item.get('description','')).lower()
        trig=[p for p in cfg.get('trigger_terms',[]) if p.lower() in text]; watch=[p for p in cfg.get('watch_terms',[]) if p.lower() in text]; neg=[p for p in cfg.get('counter_terms',[]) if p.lower() in text]
        score=2*len(trig)+0.8*len(watch)-1*len(neg)
        row={**item,'matched_trigger':trig,'matched_watch':watch,'matched_counter':neg,'signal_score':score}
        if score>0:evidence.append(row);total+=score
        elif neg:counter.append(row)
    evidence.sort(key=lambda x:(x.get('signal_score',0),x.get('published','')),reverse=True); counter.sort(key=lambda x:x.get('published',''),reverse=True)
    strongest=evidence[0]['signal_score'] if evidence else 0
    if strongest>=3.5 or total>=6:state='TRIGGERED';mult=1.0
    elif total>=1:state='WATCH';mult=.5
    elif counter:state='CLEAR';mult=0.0
    else:state='UNKNOWN';mult=0.0
    return {'id':cfg['id'],'label_zh':cfg['label_zh'],'weight':cfg['weight'],'state':state,'multiplier':mult,'signal_score':round(total,2),'evidence':evidence[:5],'counter_evidence':counter[:3],'items_scanned':len(items)}

def ppi_score(v):
    if v is None:return None
    return 100 if v<=-5 else 75 if v<=-2 else 60 if v<0 else 40 if v<2 else 20 if v<5 else 0

def compute_scores(events,fred,capex_conf):
    tw=sum(e['weight'] for e in events) or 1; es=sum(e['weight']*e['multiplier'] for e in events)/tw*100
    ps=[ppi_score((fred.get(k) or {}).get('chg_3m_pct')) for k in ('semiconductor_ppi','storage_device_ppi')];ps=[x for x in ps if x is not None]; price=sum(ps)/len(ps) if ps else None; cap=capex_conf.get('score') if capex_conf.get('available') else None
    comps=[(es,.75)]+([] if price is None else [(price,.15)])+([] if cap is None else [(cap,.10)]); den=sum(w for _,w in comps); r=sum(v*w for v,w in comps)/den
    phase='主升／供給吃緊' if r<20 else '過熱但尚未反轉' if r<40 else '築頂監控' if r<55 else '下跌週期形成' if r<70 else '明確下跌' if r<85 else '深度去庫存／崩價'
    return {'downturn_readiness':round(r,1),'phase':phase,'event_score':round(es,1),'price_confirmation_score':None if price is None else round(price,1),'capex_confirmation_score':None if cap is None else round(cap,1)}

def write_json(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def append_history(path,s):
    row={'as_of':s['as_of'],**s['scores']}; existing=[]
    if path.exists():
        with path.open('r',encoding='utf-8',newline='') as f:existing=[r for r in csv.DictReader(f) if r.get('as_of')!=row['as_of']]
    fields=['as_of','downturn_readiness','phase','event_score','price_confirmation_score','capex_confirmation_score']; path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(existing+[row])
def append_events(path,events,as_of):
    old=[];seen=set();path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:o=json.loads(line);old.append(o);seen.add(o['dedupe_id'])
            except:pass
    new=[]
    for e in events:
        for i in e.get('evidence',[]):
            did=hashlib.sha256(f"{e['id']}|{i.get('title','')}|{i.get('link','')}".encode()).hexdigest()[:20]
            if did in seen:continue
            seen.add(did);new.append({'dedupe_id':did,'observed_on':as_of,'event_id':e['id'],'event_state':e['state'],'title':i.get('title'),'published':i.get('published'),'link':i.get('link'),'signal_score':i.get('signal_score'),'matched_trigger':i.get('matched_trigger'),'matched_watch':i.get('matched_watch')})
    path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in old+new),encoding='utf-8')
def fmt(v,s=''):
    if v is None:return 'N/A'
    return f'{v:.1f}{s}' if isinstance(v,float) else f'{v}{s}'
def dashboard(s):
    st={'TRIGGERED':'🔴 TRIGGERED','WATCH':'🟠 WATCH','CLEAR':'🟢 CLEAR','UNKNOWN':'⚪ UNKNOWN'}
    L=['# TechTicker｜硬體價格週期監控','',f'> 最後更新：**{s["as_of"]}**','',f'## Downturn Readiness：**{s["scores"]["downturn_readiness"]}/100**','',f'目前階段：**{s["scores"]["phase"]}**','', '分數越高，代表越接近 2022～2023 式的「需求降溫＋庫存累積＋供給追上」下跌環境。這是規則式早期警報，不是投資建議。','','### 六大反轉事件','','| 事件 | 狀態 | 權重 | 最近證據 |','|---|---:|---:|---|']
    for e in s['events']:
        ev=(e.get('evidence') or e.get('counter_evidence') or [])
        x=f'[{ev[0].get("title","來源")}]({ev[0].get("link","")})' if ev else '—';L.append(f'| {e["label_zh"]} | {st.get(e["state"],e["state"])} | {e["weight"]}% | {x} |')
    L+=['','### 公開價格代理','','| 指標 | 最新值 | MoM | 3M | YoY |','|---|---:|---:|---:|---:|']
    for k,o in s['fred'].items():L.append(f'| {o.get("label_zh",k)} | {fmt(o.get("latest"))} | {fmt(o.get("mom_pct"),"%")} | {fmt(o.get("chg_3m_pct"),"%")} | {fmt(o.get("yoy_pct"),"%")} |')
    L+=['','### CSP 實際 CapEx（SEC XBRL）','','| 公司 | 最新季度 | YoY |','|---|---:|---:|']
    for t,o in s['capex'].items():L.append(f'| {o.get("name",t)} | {o.get("latest_frame","N/A")} | {fmt(o.get("yoy_pct"),"%")} |')
    return '\n'.join(L)+'\n'

def main():
    as_of=datetime.now(timezone.utc).date().isoformat();fred={}
    for k,m in CFG['fred_series'].items():
        try:o=fred_summary(fred_series(m['series_id']))
        except Exception as e:o={'available':False,'error':str(e)}
        o.update(m);fred[k]=o
    capex={}
    for t,m in CFG['sec_companies'].items():
        try:o=sec_capex_summary(sec_companyfacts(m['cik']))
        except Exception as e:o={'available':False,'error':str(e)}
        o.update({'name':m['name'],'cik':m['cik']});capex[t]=o
    cc=capex_confirmation(capex);events=[]
    for ecfg in CFG['events']:
        all=[]
        for q in ecfg['queries']:
            try:all+=google_news(q,CFG['max_news_items_per_query'])
            except Exception as e:all.append({'title':f'QUERY_ERROR: {e}','link':'','description':'','published':''})
        uniq={};[uniq.__setitem__(i.get('link') or i.get('title'),i) for i in all if (i.get('link') or i.get('title'))]
        events.append(classify_event(ecfg,list(uniq.values()),CFG['lookback_days']))
    scores=compute_scores(events,fred,cc);snap={'schema_version':1,'as_of':as_of,'scores':scores,'events':events,'fred':fred,'capex':capex,'capex_confirmation':cc}
    write_json(ROOT/'data/latest.json',snap);append_history(ROOT/'data/history/daily.csv',snap);append_events(ROOT/'data/events/events.jsonl',events,as_of);(ROOT/'docs').mkdir(exist_ok=True);(ROOT/'docs/DASHBOARD.md').write_text(dashboard(snap),encoding='utf-8')
    print(json.dumps({'as_of':as_of,**scores},ensure_ascii=False))
if __name__=='__main__':main()
