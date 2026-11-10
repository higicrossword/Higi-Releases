#!/usr/bin/env python3
"""Fail-closed v197 source integration on top of exactly v196."""
from pathlib import Path
import sys
root=Path(sys.argv[1]); assets=Path(__file__).parent
app=root/'app/src/main/java/com/example/hebrewcrossword'
source=assets/'v197-ui.patch'
import subprocess
subprocess.run(['git','-C',str(root),'apply','--3way','--check',str(source)],check=True)
subprocess.run(['git','-C',str(root),'apply','--3way',str(source)],check=True)
# New preview logic is specifically scoped to the administrator-only OCR review lane.
p=app/'HigiLocalOcrCropEngine.kt'
s=p.read_text(encoding='utf-8')
needle='''               refineSharedRows:Boolean=false):Outcome {'''
assert s.count(needle)==1, 'engine locate signature unexpectedly changed'
s=s.replace(needle,'''               refineSharedRows:Boolean=false,layoutSeriesId:String?=null):Outcome {''',1)
needle='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
assert s.count(needle)==1, 'v196 review stage boundary unexpectedly changed'
block='''        // V197 profile-aware review (never accepted/canonical): no modifications
        // to TARTEY/HAFUCH/MAARIV or any unknown layout profile.
        if(refineSharedRows && layoutSeriesId==OcrSeriesProfilesV197.MONDAY.id &&
            auditWords.isNotEmpty()) {
            val previous=newPreviews.map{(candidate,g)->
                wire(candidate) to g.lines.map{b->
                    CropRect((b.left*w).roundToInt(),(b.top*h).roundToInt(),
                        (b.right*w).roundToInt(),(b.bottom*h).roundToInt())
                }
            }.toMap()
            val eligible=acceptedPixels().filter{(label,_)->label !in previous}
            val suggestions=OcrSeriesPreviewV197.inspect(OcrSeriesProfilesV197.MONDAY,
                previous+eligible,lines,auditWords,expectedWires,w,h)
            suggestions.previews.forEach{(label,pieces)->
                val k=key(label)
                val g=geometry(pieces,w,h)
                val v=ClueRegionValidation.validateGeometryNormalized(g,w,h,gridPoints)
                if(v.usable){
                    newPreviews[k]=g
                    newPreviewReasons[k]=suggestions.reasons[label].orEmpty()
                    DebugLog.i("LOCAL_OCR_V197","key=$label source=MONDAY adminPreview=true canonicalWrite=false")
                }else{
                    newPreviewReasons[k]="V197_REVIEW_REJECTED:${v.reason}; old geometry retained"
                }
            }
        }
'''
s=s.replace(needle,block+needle,1)
p.write_text(s,encoding='utf-8')
for item in ['OcrSeriesProfilesV197.kt','OcrSeriesPreviewV197.kt']:
    path=app/item
    assert not path.exists(), item+' already exists'
    path.write_text((assets/item).read_text(encoding='utf-8'),encoding='utf-8')
test=root/'app/src/test/java/com/example/hebrewcrossword/OcrSeriesProfilesV197Test.kt'
assert not test.exists()
test.write_text((assets/'OcrSeriesProfilesV197Test.kt').read_text(encoding='utf-8'),encoding='utf-8')
gradle=root/'app/build.gradle.kts'
s=gradle.read_text(encoding='utf-8')
for old,new in [('versionCode = 346','versionCode = 347'),
                ('versionName = "0.15.196"','versionName = "0.15.197"')]:
    assert s.count(old)==1, old+' not unique'
    s=s.replace(old,new,1)
gradle.write_text(s,encoding='utf-8')
print('Integrated v197 DRY UI navigation and series profiles; v196 accepted/canonical unchanged')