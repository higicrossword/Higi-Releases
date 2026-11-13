from pathlib import Path
import re,sys
root=Path(sys.argv[1])/'app/src/main/java/com/example/hebrewcrossword'
keys=['CLUE_APPROVAL','single-clue-save','updateClues(', 'updateClueRegion', 'updateClueRegions', 'saveClue','saveRegion','SOURCE_CROP', 'CLUE_REGION','HIGI_DRY_BUILD','MANUAL','manualCrop','saveManual','commitClue','canonicalCloud.','sourceClueCropStore']
priority={'MainActivity.kt':90,'ClueEditorDialog.kt':85,'CanonicalPuzzleCloud.kt':55,'ClueRegionStore.kt':30,'AdminOcrRecropActivity.kt':40,'ClueGeometryDebugStore.kt':20}
for name,cap in priority.items():
 p=root/name
 if not p.exists():continue
 a=p.read_text().splitlines()
 hits=[i for i,line in enumerate(a) if any(k.lower() in line.lower() for k in keys)]
 print(f'=== {name}: {len(a)} lines, {len(hits)} matches ===')
 for i in hits[:cap]:
  print(f'{i+1:05d} {a[i]}')
 windows={
 'MainActivity.kt':['single-clue-save','CLUE_APPROVAL','updateClues(', 'updateClueRegion','saveClueGeometry','saveClueRegion'],
 'ClueEditorDialog.kt':['saveClue','updateClue','saveRegion','clueRegion','onSave'],
 'CanonicalPuzzleCloud.kt':['fun updateClues(', 'fun updateClueRegion','fun setClueApproved','HIGI_DRY_BUILD'],
 'ClueRegionStore.kt':['fun setManual','fun getManualVerified'],
 }
 for term in windows.get(name,[]):
  indices=[i for i,line in enumerate(a) if term in line]
  for h in indices[:3]:
   print(f'--- {term} lines {max(1,h-8)}..{min(len(a),h+40)} ---')
   for i in range(max(0,h-9),min(len(a),h+40)):
    print(f'{i+1:05d} {a[i]}')
