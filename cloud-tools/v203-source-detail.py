from pathlib import Path
import sys
root=Path(sys.argv[1]) / "app/src/main/java/com/example/hebrewcrossword"
windows={
 "AdminPuzzleMenu.kt":[(1,55)],
 "CanonicalSourceImageStorage.kt":[(1,130)],
 "RecentCrosswordsActivity.kt":[(55,115),(1200,1405),(1410,1540),(2150,2220)],
 "CanonicalPuzzleCloud.kt":[(605,710),(1318,1480)],
 "MainActivity.kt":[(3950,4075)],
}
for name,ranges in windows.items():
 p=root/name
 if not p.is_file():
  print("MISSING",name)
  continue
 lines=p.read_text().splitlines()
 print("=== FILE",name,"LINES",len(lines),"===")
 for first,last in ranges:
  print("--- LINES",first,last,"---")
  for i in range(first-1,min(last,len(lines))):
   print(f"{i+1:05d} {lines[i]}")
