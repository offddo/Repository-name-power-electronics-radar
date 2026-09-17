import os, json, re, html, requests, feedparser
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from source_fetcher import fetch_source, crossref_papers
try:
    from googlenewsdecoder import gnewsdecoder
except Exception:
    gnewsdecoder = None

RSS = [
("国际资讯 - Power Electronics","https://news.google.com/rss/search?q=power+electronics&hl=en-US&gl=US&ceid=US:en","国际资讯"),
("国际资讯 - SST","https://news.google.com/rss/search?q=%22solid-state+transformer%22&hl=en-US&gl=US&ceid=US:en","国际资讯"),
("国际资讯 - SiC","https://news.google.com/rss/search?q=SiC+power+electronics&hl=en-US&gl=US&ceid=US:en","国际资讯"),
("国际资讯 - GaN","https://news.google.com/rss/search?q=GaN+power+electronics&hl=en-US&gl=US&ceid=US:en","国际资讯"),
("国际资讯 - GFM PCS","https://news.google.com/rss/search?q=%22grid-forming%22+PCS+power&hl=en-US&gl=US&ceid=US:en","国际资讯"),
("国际资讯 - 800V AI DC","https://news.google.com/rss/search?q=800V+AI+data+center+power&hl=en-US&gl=US&ceid=US:en","国际资讯"),
("国际资讯 - DAB CLLC LLC","https://news.google.com/rss/search?q=DAB+CLLC+LLC+power+electronics&hl=en-US&gl=US&ceid=US:en","国际资讯"),
("国内资讯 - 中国电力电子","https://news.google.com/rss/search?q=%E4%B8%AD%E5%9B%BD+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+SiC+GaN+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans","国内资讯"),
("国内资讯 - 构网型变流器","https://news.google.com/rss/search?q=%E6%9E%84%E7%BD%91%E5%9E%8B+%E5%8F%98%E6%B5%81%E5%99%A8+GFM+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans","国内资讯"),
("国内资讯 - SiC GaN","https://news.google.com/rss/search?q=SiC+GaN+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+%E5%8A%9F%E7%8E%87%E5%8D%8A%E5%AF%BC%E4%BD%93&hl=zh-CN&gl=CN&ceid=CN:zh-Hans","国内资讯"),
("国内资讯 - 800V 数据中心","https://news.google.com/rss/search?q=800V+%E6%95%B0%E6%8D%AE%E4%B8%AD%E5%BF%83+%E7%94%B5%E6%BA%90+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans","国内资讯")]
KW=["sst","solid-state transformer","solid state transformer","sic","silicon carbide","gan","gallium nitride","grid-forming","grid forming","gfm","pcs","800v","ai data center","ai datacenter","power electronics","power semiconductor","wide-bandgap","dual active bridge","dab","cllc","llc","magnetics","构网型","变流器","电力电子","碳化硅","氮化镓"]
TOP={"sst":["sst","solid-state transformer","solid state transformer"],"sic":["sic","silicon carbide","碳化硅"],"gan":["gan","gallium nitride","氮化镓"],"gfm":["grid-forming","grid forming","gfm","构网型"],"pcs":["pcs","power conversion system","变流器","储能变流器"],"ai_dc":["ai data center","ai datacenter","data center","datacenter","数据中心"],"dab":["dab","dual active bridge"],"cllc":["cllc"],"llc":["llc"],"800v":["800v","800 v","800-volt","800伏"],"magnetics":["magnetics","magnetic integration","high-frequency magnetics","磁性元件"]}
PRIO={"ieee":98,"nature.com":98,"infineon":96,"ti.com":96,"texas instruments":96,"renesas":95,"sungrow":95,"tmeic":95,"电力电子技术":96,"电力自动化设备":96,"电力系统自动化":96,"电工技术学报":96,"中国电机工程学报":96,"pv magazine":90}

def clean(x):
 x=html.unescape(str(x or "")); x=re.sub(r"<script.*?</script>|<style.*?</style>"," ",x,flags=re.I|re.S); return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",x)).strip()
def topics(x):
 x=clean(x).lower(); return sorted(k for k,v in TOP.items() if any(a in x for a in v))
def score(s):
 s=s.lower(); return max((v for k,v in PRIO.items() if k in s),default=40)
def published(i):
 for k in ("published","updated","created"):
  v=i.get(k)
  if v:
   try:
    d=parsedate_to_datetime(v); d=d if d.tzinfo else d.replace(tzinfo=timezone.utc); return d.astimezone(timezone.utc).isoformat()
   except Exception: pass
 return ""
def resolve(u):
 if not u or "news.google.com" not in u:return u
 if gnewsdecoder:
  try:
   r=gnewsdecoder(u,interval=1)
   if isinstance(r,dict) and r.get("status") and r.get("decoded_url"):u=r["decoded_url"]
  except Exception:pass
 try:
  r=requests.get(u,timeout=5,allow_redirects=True,headers={"User-Agent":"Mozilla/5.0 PowerElectronicsRadar"}); u=r.url if r.url and "news.google.com" not in r.url else u
 except Exception:pass
 return u
def similar(a,b):
 a=re.sub(r"[^\w\u4e00-\u9fff ]","",a["title"].lower()); b=re.sub(r"[^\w\u4e00-\u9fff ]","",b["title"].lower())
 return a==b or SequenceMatcher(None,a,b).ratio()>=.86

def collect():
 cand=[]; seen=set()
 for name,url,stype in RSS:
  try:f=feedparser.parse(url)
  except Exception:continue
  for i in f.entries[:8]:
   title=clean(i.get("title")); summary=clean(i.get("summary"));
   if not title or not any(k in (title+" "+summary).lower() for k in KW):continue
   link=resolve(i.get("link","") or ""); key=link.split("#",1)[0].rstrip("/") or title.lower()
   if key in seen:continue
   seen.add(key); src=i.get("source"); src=clean(src.get("title") or src.get("name") or name) if isinstance(src,dict) else clean(src or name)
   cand.append({"source":src,"source_type":stype,"title":title,"summary":summary[:4000],"link":link,"published_at":published(i),"score":score(src),"paper":False})

 papers=crossref_papers(["电力电子技术","电力自动化设备","电力系统自动化","电工技术学报","中国电机工程学报"],["构网型","SiC","GaN","电力电子","变流器","储能变流器","DAB","CLLC","LLC","固态变压器"],since="2026-01-01",rows=8)
 for p in papers[:24]:
  k=(p.get("link") or p["title"]).lower()
  if k not in seen:seen.add(k);cand.append(p)
 # Fetch original pages concurrently. If the original page cannot be fetched, the item is discarded.
 grounded=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  jobs={ex.submit(fetch_source,c["link"],9000):c for c in cand[:90]}
  for fut in as_completed(jobs):
   c=jobs[fut]
   try:t=fut.result()
   except Exception:t=""
   if len(t)>=500:c["source_text"]=t; grounded.append(c)
   else: print("Skipped without original source content:",c["title"])
 clusters=[]
 for a in sorted(grounded,key=lambda x:(x["score"],x["published_at"]),reverse=True):
  cl=next((x for x in clusters if similar(a,x["primary"])),None)
  if cl:
   cl["sources"].append({k:a[k] for k in ["source","source_type","title","link","published_at"]})
   if len(a["source_text"])>len(cl["primary"]["source_text"]):cl["primary"]=a
  else:clusters.append({"primary":dict(a),"sources":[]})
 out=[]
 for n,cl in enumerate(clusters[:50],1):
  p=cl["primary"]; out.append({"id":datetime.now(timezone.utc).strftime("%y%m%d")+f"-{n:02d}","title":p["title"],"category":topics(p["title"]+" "+p["summary"]+" "+p["source_text"]),"source_type":p["source_type"],"primary_source":p["source"],"published_at":p["published_at"],"link":p["link"],"summary_raw":p["summary"],"source_text":p["source_text"],"sources":cl["sources"][:10]})
 return out

def ai(events,date):
 rules="""SOURCE_TEXT是唯一事实依据。禁止使用预训练知识、常识、标题推断或外部知识补充事实、参数、拓扑、应用、性能、成本或产业化状态。只能重组SOURCE_TEXT明确内容。企业/机构判断必须标为来源声称。plain_summary 3-5句，通俗解释发生了什么；technical_summary 5-8句，工程师视角，优先器件、拓扑、控制、参数、实验和产品信息；若原文不足，少写，绝不凑句。二者不能同义改写。没有写到的内容直接省略，不输出“原文未提供/未知参数/无法判断”。evidence.inferences和unknowns永远为空数组。confirmed_facts必须能在SOURCE_TEXT逐项找到，source_claims只写来源明确声称。只输出JSON。"""
 schema={"events":[{"id":"","title":"","source_type":"","primary_source":"","published_at":"","link":"","category":[],"importance":"重点|一般","plain_summary":"","technical_summary":"","technical":{"voltage":"","power":"","topology":"","device":"","switching_frequency":"","efficiency":"","power_density":"","isolation":"","control":"","application":""},"industrialization":{"stage":"研究论文|实验室样机|工程样机|产品发布|试点/示范|试产|量产|商业部署|未知","status":"","target":""},"evidence":{"confirmed_facts":[],"source_claims":[],"inferences":[],"unknowns":[]},"sources":[]}],"directions":{},"observations":[],"quality_notes":""}
 inp=[]
 for e in events:
  x=dict(e);x["SOURCE_TEXT"]=x.pop("source_text","");inp.append(x)
 p=rules+"\n报告日期："+date+"\n结构："+json.dumps(schema,ensure_ascii=False)+"\n事件："+json.dumps(inp,ensure_ascii=False)
 r=requests.post("https://api.deepseek.com/chat/completions",headers={"Authorization":"Bearer "+os.environ["DEEPSEEK_API_KEY"],"Content-Type":"application/json"},json={"model":"deepseek-chat","messages":[{"role":"system","content":"只输出合法JSON，任何事实必须来自对应SOURCE_TEXT。"},{"role":"user","content":p}],"temperature":.02,"max_tokens":28000,"response_format":{"type":"json_object"}},timeout=180);r.raise_for_status();return json.loads(re.sub(r"^```(?:json)?\s*|\s*```$","",r.json()["choices"][0]["message"]["content"].strip(),flags=re.I).strip())

def normalize(x,b):
 e=dict(x or {})
 for k in ["id","title","source_type","primary_source","published_at","link","summary_raw"]:e[k]=b.get(k,e.get(k,""))
 e["category"]=e.get("category") or b.get("category",[]);e["sources"]=e.get("sources") or b.get("sources",[]);e["plain_summary"]=clean(e.get("plain_summary"));e["technical_summary"]=clean(e.get("technical_summary"))
 t=dict(e.get("technical") or {}); 
 for k in ["voltage","power","topology","device","switching_frequency","efficiency","power_density","isolation","control","application"]:t[k]=t.get(k,"")
 e["technical"]=t;i=dict(e.get("industrialization") or {});i["stage"]=i.get("stage") or "未知";e["industrialization"]={"stage":i["stage"],"status":i.get("status",""),"target":i.get("target","")}
 ev=dict(e.get("evidence") or {});ev["confirmed_facts"]=ev.get("confirmed_facts") or [];ev["source_claims"]=ev.get("source_claims") or [];ev["inferences"]=[];ev["unknowns"]=[];e["evidence"]=ev
 return e

def main():
 tz=timezone(timedelta(hours=8));now=datetime.now(timezone.utc).astimezone(tz);date=now.strftime("%Y-%m-%d");raw=collect()
 try:
  if not raw:raise ValueError("no grounded events")
  result=ai(raw,date);by={e["id"]:e for e in raw};events=[normalize(x,by[x["id"]]) for x in result.get("events",[]) if x.get("id") in by]
  if not events:raise ValueError("AI returned no matching events")
 except Exception as exc:
  print("AI structured output failed:",repr(exc));result={"events":[],"directions":{},"observations":[],"quality_notes":"AI分析失败；未补充原文之外的事实。"};events=[normalize({},e) for e in raw]
 for e in events:e.pop("source_text",None)
 with open("data.json","w",encoding="utf-8") as f:json.dump({"schema_version":"3.2","updated":now.isoformat(),"report_date":date,"event_count":len(events),"events":events,"directions":result.get("directions",{}),"observations":result.get("observations",[]),"quality_notes":result.get("quality_notes","")},f,ensure_ascii=False,indent=2)
 print("Validated",len(events),"strictly grounded events")
if __name__=="__main__":main()
