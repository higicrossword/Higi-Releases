from pathlib import Path
import sys,re
root=Path(sys.argv[1])/'app/src/main/java/com/example/hebrewcrossword'
patterns=[
 r'תמונת התשבץ המקורית',r'כל התמונה',r'OriginalImage',
 r'original.image',r'showSource',r'showOriginal',r'sourceFiles',
 r'writeSource',r'viewSource',r'loadSource',r'canonicalImage',r'sourceImageUrl',
]
count=0
for p in sorted(root.glob('*.kt')):
 lines=p.read_text().splitlines()
 hits=[i for i,line in enumerate(lines) if any(re.search(x,line,re.I) for x in patterns)]
 if not hits:continue
 print('===',p.name,'matches=',len(hits),'===')
 for i in hits:
  if p.name not in ('MainActivity.kt','RecentCrosswordsActivity.kt','SourceImageViewerActivity.kt','PuzzleLibrary.kt','CanonicalPuzzleIndex.kt') and not any(k in p.name for k in ['Viewer','Source','Image']):continue
  a=max(0,i-11);b=min(len(lines),i+15)
  print('--',a+1,b,'hit',i+1,'--')
  for n in range(a,b):
   print(f'{n+1:05d} {lines[n]}')
  count+=1
  if count>=50:quit()
