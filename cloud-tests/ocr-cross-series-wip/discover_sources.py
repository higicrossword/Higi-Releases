#!/usr/bin/env python3
"""Read-only WIP discovery of three public, non-Yedioth source JPEGs. No app or cloud writes."""
import hashlib,html,io,json,re,sys,urllib.parse,urllib.request
from pathlib import Path
from PIL import Image

BASE="https://groups.google.com"
GROUP="/g/tartey_mashma"
UA={"User-Agent":"Mozilla/5.0 (compatible; Higi offline OCR research; read-only)"}
DIRECT_HAFUCH=(
 "https://groups.google.com/group/tartey_mashma/attach/637b8b58672e4/"
 "%D7%94%D7%A4%D7%95%D7%9A%20%D7%A2%D7%9C%20%D7%94%D7%A4%D7%95%D7%9A"
 "%20%D7%93%D7%A7%D7%9C%20%D7%91%D7%A0%D7%95%206-11-26.jpg?part=0.2")
TARGETS=[
 ("TARTEY_DEKEL",["תרתי משמע","2236"],["תרתי משמע 2236","תרתי משמע דקל בנו 6/11/26"]),
 ("HAFUCH_DEKEL",["הפוך על הפוך","דקל בנו"],["הפוך על הפוך דקל בנו 6/11/26"]),
 ("MAARIV_ODED_ROZEN",["מעריב","עודד רוזן"],["מעריב עודד רוזן 6/11/26"]),
]
def get(url,limit=9500000):
    request=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(request,timeout=15) as r:
        payload=r.read(limit+1)
        if len(payload)>limit:raise ValueError("Response over byte limit")
        return payload,r.headers.get("Content-Type","")
def validate_image(data):
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        if im.format not in ("JPEG","PNG") or im.width<500 or im.height<300:
            raise ValueError("Not a full crossword scan")
        return {"sha256":hashlib.sha256(data).hexdigest(),
                "width":im.width,"height":im.height,"format":im.format,
                "bytes":len(data)}
def title_from_page(page):
    found=re.search(r"<title>(.*?)</title>",page,re.S|re.I)
    return html.unescape(re.sub(r"<[^>]+>","",found.group(1))).strip() if found else ""
def threads_from_search(page):
    ids=re.findall(r'(?:\.?/)?g/tartey_mashma/c/([A-Za-z0-9_-]{8,24})',page)
    return list(dict.fromkeys(ids))
def attachments_from_thread(page):
    urls=re.findall(r'href="(https://groups.google.com/group/tartey_mashma/attach/[^"<>]+)"',page)
    return [u.replace("&amp;","&") for u in dict.fromkeys(urls)
            if re.search(r"\.(?:jpe?g|png)(?:\?|$)",u,re.I)]
def discover(target,required,queries,results):
    entry={"series":target,"query_attempts":[],"status":"NO_VERIFIED_IMAGE",
           "source_date_requested":"06-11-2026","writes":0}
    if target=="HAFUCH_DEKEL":
        try:
            raw,ctype=get(DIRECT_HAFUCH)
            meta=validate_image(raw)
            entry.update(status="IMAGE_BYTES_VERIFIED",provenance="explicit_prior_user_source_url",
                         image_url=DIRECT_HAFUCH,**meta)
        except Exception as exc:
            entry["direct_error"]=type(exc).__name__+":"+str(exc)[:140]
    if entry["status"]=="IMAGE_BYTES_VERIFIED":
        results.append(entry);return
    for query in queries:
        qurl=BASE+GROUP+"/search?q="+urllib.parse.quote(query)
        item={"query":query}
        try:
            data,_=get(qurl,4500000)
            page=html.unescape(data.decode("utf8","replace"))
            ids=threads_from_search(page)
            item["thread_count"]=len(ids)
            for tid in ids[:6]:
                turl=BASE+GROUP+"/c/"+tid
                try:
                    body,_=get(turl,5500000)
                    thread=html.unescape(body.decode("utf8","replace"))
                    title=title_from_page(thread)
                    item.setdefault("sample_thread_titles",[]).append({"thread":tid,"title":title[:160]})
                    if not all(term in title for term in required):continue
                    if not re.search(r"(?:^|[^0-9])0?6[./-]11[./-]26(?:[^0-9]|$)",title):
                        item.setdefault("date_ambiguous",[]).append(title[:130])
                        continue
                    urls=attachments_from_thread(thread)
                    for imgurl in urls[:4]:
                        try:
                            raw,ctype=get(imgurl)
                            meta=validate_image(raw)
                            entry.update(status="IMAGE_BYTES_VERIFIED",provenance="Google_Groups_matched_title",
                                         thread=turl,title=title,image_url=imgurl,**meta)
                            break
                        except Exception as ex:
                            item.setdefault("image_errors",[]).append(str(ex)[:100])
                    if entry["status"]=="IMAGE_BYTES_VERIFIED":break
                except Exception as ex:
                    item.setdefault("thread_errors",[]).append(str(ex)[:100])
            entry["query_attempts"].append(item)
            if entry["status"]=="IMAGE_BYTES_VERIFIED":break
        except Exception as exc:
            item["error"]=type(exc).__name__+":"+str(exc)[:150]
            entry["query_attempts"].append(item)
    results.append(entry)
def self_test():
    assert threads_from_search('<a href="./g/tartey_mashma/c/Abcde12345">')==["Abcde12345"]
    assert title_from_page('<title>דוגמה - Google Groups</title>')=="דוגמה - Google Groups"
    assert attachments_from_thread('<a href="https://groups.google.com/group/tartey_mashma/attach/abcd/photo.jpg?part=0.1">')
    print("PASS public source parsing self-tests")
def main(out):
    result=[]
    for name,required,queries in TARGETS:
        discover(name,required,queries,result)
        print("SERIES",name,result[-1]["status"],result[-1].get("sha256",""),flush=True)
    summary={"goal":"Source-byte discovery only; not Android OCR nor validated clue geometry",
      "requested_series":3,"verified_image_bytes":sum(v["status"]=="IMAGE_BYTES_VERIFIED" for v in result),
      "series":result,"downloaded_images_persisted":False,
      "canonical_writes":0,"firebase_writes":0,"apk_release":False}
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("SUMMARY",summary["verified_image_bytes"],"/3")
if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    elif len(sys.argv)==2:main(sys.argv[1])
    else:raise SystemExit("Usage: discover_sources.py --self-test OR output.json")
