#!/usr/bin/env python3
from pathlib import Path
import sys,re
p=Path(sys.argv[1])/"app/src/main/java/com/example/hebrewcrossword"
tasks={
"MainActivity.kt":[("HEAD",r"\A",85),("withSource",r"fun withSource\b|private fun withSource\b",95),("showSourceImage",r"private fun showSourceImage\b",38),("admin picker",r"private val picker=|registerForActivityResult\(ActivityResultContracts.GetContent",32),("canonical watch image",r"val previousSourceUrl=canonicalIndex.sourceImageUrl",65),("image change",r"handleSourceReplacementOnly",26)],
"SourceImageDialog.kt":[("ALL",r".",200)],
"CanonicalPuzzleCloud.kt":[("auth internals",r"fun authenticated\(",80),("admin update",r"private fun updateDecodedForAdminAtNode|fun updateDecodedForAdminAtNode",200),("CachedPuzzle",r"data class CachedPuzzle",110),("update clue region",r"fun updateClueAndRegion\(",105),("refresh admin",r"fun refreshDecodedForAdmin\(",82)],
"CanonicalSourceImageStorage.kt":[("ALL",r".",150)],
"RecentCrosswordsActivity.kt":[("source select",r"fun chooseAdminSource|fun replaceSource|source.*Replacement|source.*Picker|ADMIN_SOURCE",125),("image action",r"private fun runAdminMenuAction",100),("public",r"private fun confirmSavedDryCanonicalPublication",112)],
"PuzzleLibrary.kt":[("source files",r"fun sourceFiles|fun writeSource|fun clearSource",65)],
"CanonicalPuzzleIndex.kt":[("bind",r"fun bind\(|fun sourceImageUrl",38)],
"ImageDownload.kt":[("ALL",r".",100)],
"SourceClueCropStore.kt":[("source cache",r"fun clear|fun .*Bound",55)],
}
for name,queries in tasks.items():
 f=p/name
 if not f.exists():
  print("== MISSING",name)
  continue
 lines=f.read_text().splitlines()
 print("========",name,"lines",len(lines),"========")
 printed=set()
 for label,pattern,after in queries:
  indexes=[i for i,t in enumerate(lines) if re.search(pattern,t,re.I)]
  if label=="ALL":indexes=[0]
  for i in indexes[:4]:
   start=max(0,i-6);end=min(len(lines),i+after)
   print("====",label,"range",start+1,end)
   for j in range(start,end):
    if j in printed:continue
    print(f"{j+1:05d} {lines[j]}")
    printed.add(j)
