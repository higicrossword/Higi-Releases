from pathlib import Path
import sys
p=Path(sys.argv[1])/'app/src/main/java/com/example/hebrewcrossword/MainActivity.kt'
a=p.read_text().splitlines()
for first,last in [(4660,4900),(5460,5730)]:
 print('=== MainActivity',first,last,'===')
 for i in range(first-1,min(last,len(a))):
  print(f'{i+1:05d} {a[i]}')
