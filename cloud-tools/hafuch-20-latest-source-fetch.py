#!/usr/bin/env python3
"""Read-only public source image inventory for latest 20 Hafuch al Hafuch crosswords.
Does not change app, algorithms, profiles, Firebase, Canonical, or releases.
"""
import concurrent.futures, datetime as dt, hashlib, html, io, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image

GROUP="https://groups.google.com/g/tartey_mashma"
USER_AGENT={"User-Agent":"Mozilla/5.0 Chrome/131.0.0.0"}
OUT=Path("hafuch-20-source-results")
IMAGES=OUT/"images"
IMAGES.mkdir(parents=True,exist_ok=True)
TODAY=dt.date(2026,11,16)
FRIDAY=dt.date(2026,11,13)
WEEKS=34
dates=[FRIDAY-dt.timedelta(days=7*i) for i in range(WEEKS)]
DATE_SET=set(dates)
PREFERRED=[dt.date(2026,11,6)]
KNOWN_URLS={
 "2026-11-06":"https://groups.google.com/group/tartey_mashma/attach/637b8b58672e4/%D7%94%D7%A4%D7%95%D7%9A%20%D7%A2%D7%9C%20%D7%94%D7%A4%D7%95%D7%9A%20%D7%93%D7%A7%D7%9C%20%D7%91%D7%A0%D7%95%206-11-26.jpg?part=0.2"
}
def fetch(url,limit=14_000_000,timeout=18):
    req=urllib.request.Request(url,headers=USER_AGENT)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        data=response.read(limit+1)
        if len(data)>limit:raise ValueError("response byte limit exceeded")
        return data,response.headers.get("Content-Type","")
def search_threads(text):
    # Google Groups search HTML exposes thread ids even if JS is required for full UI.
    ids=re.findall(r'(?:\.?/)?g/tartey_mashma/c/([A-Za-z0-9_-]{8,24})',text)
    ids+=re.findall(r'groups\.google\.com/g/tartey_mashma/c/([A-Za-z0-9_-]{8,24})',text)
    return list(dict.fromkeys(ids))
def title_from(text):
    t=re.search(r"<title>(.*?)</title>",text,re.S|re.I)
    return html.unescape(re.sub(r"<[^>]+>","",t.group(1))).strip() if t else ""
def is_series_title(s):
    s=s.replace("_"," ").replace("-"," ")
    return ("הפוך על הפוך" in s and "דקל בנו" in s and
            "פתרונות" not in s and "פתרון" not in s)
def dated(s):
    s=html.unescape(urllib.parse.unquote(s)).replace("_"," ")
    # Common title/source filename dates, including DD/MM/YYYY or DD.MM.YY
    matches=re.findall(r'(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](2026|26)(?!\d)',s)
    out=[]
    for a,b,y in matches:
        try:out.append(dt.date(2026,int(b),int(a)))
        except ValueError:pass
    return out
def attachment_urls(text):
    decoded=html.unescape(text)
    urls=re.findall(r'href="(https://groups\.google\.com/group/tartey_mashma/attach/[^"<>]+)"',decoded)
    urls+=re.findall(r'(https://groups\.google\.com/group/tartey_mashma/attach/[^\s"<>]+)',decoded)
    out=[]
    for u in urls:
        u=u.replace("&amp;","&")
        if re.search(r'\.(?:jpg|jpeg|png)(?:\?|$)',u,re.I) and u not in out:out.append(u)
    return out
def search_one(entry):
    key,query=entry
    url=GROUP+"/search?q="+urllib.parse.quote(query)
    try:
        raw,ctype=fetch(url,limit=5_000_000,timeout=20)
        text=html.unescape(raw.decode("utf-8","replace"))
        ids=search_threads(text)
        return {"key":key,"query":query,"ids":ids,"title_count":text.count('t17a0d'),
                "bytes":len(raw)}
    except Exception as exc:
        return {"key":key,"query":query,"ids":[],"error":type(exc).__name__+":"+str(exc)[:160]}
searches=[
 ("generic", "הפוך על הפוך דקל בנו"),
 ("recent", "הפוך על הפוך דקל בנו after:2026-07-01 before:2026-11-17"),
]
for month in (11,10,9,8,7,6,5,4):
    start=dt.date(2026,month,1)
    finish=dt.date(2026,month+1,1) if month<12 else dt.date(2027,1,1)
    searches.append(("month-%02d"%month, "הפוך על הפוך דקל בנו after:%s before:%s"%(start,finish)))
for d in dates:
    searches.append((d.isoformat(), "הפוך על הפוך דקל בנו %s"%d.strftime("%d/%m/%y")))
    # Reverse names in some posts.
    if d>=dt.date(2026,7,1):
        searches.append(("alt-"+d.isoformat(), "דקל בנו הפוך על הפוך %s"%d.strftime("%d.%m.%y")))
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
    for r in pool.map(search_one,searches):
        results.append(r)
        print("SEARCH",r["key"],"ids",len(r["ids"]),r.get("error",""),flush=True)
seen={}
for result in results:
    for thread_id in result["ids"]:
        seen.setdefault(thread_id,[]).append(result["key"])
print("THREAD_IDS",len(seen),flush=True)
def get_thread(tid):
    url=GROUP+"/c/"+tid
    try:
        raw,_=fetch(url,limit=7_000_000,timeout=20)
        text=html.unescape(raw.decode("utf-8","replace"))
        title=title_from(text)
        urls=attachment_urls(text)
        dates_title=dated(title)
        matched=is_series_title(title)
        return {"thread":tid,"url":url,"title":title,"candidate_dates":[d.isoformat() for d in dates_title],
                "matched_series":matched,"attachments":urls[:12],"searches":seen[tid]}
    except Exception as exc:
        return {"thread":tid,"url":url,"error":type(exc).__name__+":"+str(exc)[:150]}
threads=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
    for r in pool.map(get_thread,seen):
        threads.append(r)
        if r.get("matched_series"):
            print("THREAD",r.get("candidate_dates"),r.get("title","")[:85],"attachments",len(r.get("attachments",[])),flush=True)
sources=[]
candidates=[]
for t in threads:
    if not t.get("matched_series"):continue
    tdates=[dt.date.fromisoformat(x) for x in t["candidate_dates"] if dt.date.fromisoformat(x) in DATE_SET]
    if not tdates:continue
    for d in tdates:
        for url in t["attachments"]:
            fname=urllib.parse.unquote(urllib.parse.urlparse(url).path.split("/")[-1])
            fdates=dated(fname)
            # 11 Sep thread has a filename marked 11-8-26; retain it explicitly
            # for visual verification rather than silently treating it as Aug 11.
            if fdates and d not in fdates and not (
                d==dt.date(2026,9,11) and t.get("thread")=="tpducUFCeCo"
            ):continue
            candidates.append((d,t,url))
# Always include one explicitly user-supplied link as an independent fallback.
for ds,url in KNOWN_URLS.items():
    d=dt.date.fromisoformat(ds)
    candidates.append((d,{"title":"הפוך על הפוך דקל בנו 6-11-26 (user-provided source)","url":"https://groups.google.com/g/tartey_mashma","thread":"original-user-link"},url))
# Deduplicate URLs; request most recent first.
candidates.sort(key=lambda v:v[0],reverse=True)
uniq=[];seen_urls=set()
for c in candidates:
    if c[2] not in seen_urls:uniq.append(c);seen_urls.add(c[2])
candidates=uniq
print("CANDIDATE_ATTACHMENTS",len(candidates),flush=True)
def download_one(v):
    date,thread,url=v
    try:
        raw,ctype=fetch(url,limit=14_000_000,timeout=24)
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            fmt=im.format
            w,h=im.size
            if fmt not in ("JPEG","PNG") or w<500 or h<340:raise ValueError("not valid full page image")
        return {"date":date.isoformat(),"title":thread["title"],"thread":thread["url"],
                "url":url,"sha256":hashlib.sha256(raw).hexdigest(),
                "width":w,"height":h,"format":fmt,"bytes":len(raw),
                "filename_dates":[x.isoformat() for x in dated(urllib.parse.unquote(urllib.parse.urlparse(url).path))],
                "source_date_filename_mismatch":bool(dated(urllib.parse.unquote(urllib.parse.urlparse(url).path)) and date not in dated(urllib.parse.unquote(urllib.parse.urlparse(url).path))),
                "_data":raw}
    except Exception as exc:
        return {"date":date.isoformat(),"url":url,"error":type(exc).__name__+":"+str(exc)[:150]}
downloaded=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for r in pool.map(download_one,candidates):
        downloaded.append(r)
        if "_data" in r:print("IMAGE",r["date"],r["width"],r["height"],r["sha256"][:12],flush=True)
perdate={}
for r in downloaded:
    if "_data" not in r:continue
    d=r["date"]
    if d not in perdate or r["width"]*r["height"]>perdate[d]["width"]*perdate[d]["height"]:
        perdate[d]=r
selected=sorted(perdate.values(),key=lambda r:r["date"],reverse=True)[:20]
for r in selected:
    extension="jpg" if r["format"]=="JPEG" else "png"
    filename=r["date"]+"."+extension
    (IMAGES/filename).write_bytes(r.pop("_data"))
    r["local_image_file"]="images/"+filename
    print("SELECTED",r["date"],r["width"],r["height"],r["sha256"][:12],flush=True)
# Do not include binary bytes in the diagnostic JSON.
download_status=[{k:v for k,v in row.items() if k!="_data"} for row in downloaded]
report={"as_of":TODAY.isoformat(),"series":"הפוך על הפוך — דקל בנו",
        "requested_latest":20,"verified_distinct_dates":len(selected),
        "selected":selected,"expected_weekly_fridays":[d.isoformat() for d in dates[:20]],
        "searched_queries":results,"candidate_threads":threads,
        "download_status":download_status,"missing_from_recent_20":[d.isoformat() for d in dates[:20]
                  if d.isoformat() not in set(perdate)],
        "crossword_grid_assessment":"NOT_TESTED_HERE; analyze selected original images downstream",
        "no_app_algorithm_changes":True,"firebase_writes":0,"canonical_writes":0,"new_apk_or_release":False}
(OUT/"sources.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("SUMMARY",len(selected),"/20 verified; MISSING RECENT",report["missing_from_recent_20"],flush=True)
if len(selected)<20:
    print("::warning::Fewer than 20 distinct verified originals; report exact coverage, don't invent",flush=True)
