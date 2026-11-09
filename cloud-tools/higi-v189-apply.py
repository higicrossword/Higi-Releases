#!/usr/bin/env python3
"""Create conservative Higi v0.15.189 DRY source patch from pinned v188."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
src=root/'app/src/main/java/com/example/hebrewcrossword/OcrInlineClueRecoveryV180.kt'
s=src.read_text(encoding='utf-8')
old='''            val narrowColumn=shared==0 && anchored.size>=7 &&
                singleAnchorRows>=7 && rightLaneStarts*5>=anchored.size*4 &&
                verticalSpan>=height/8
            if(shared==0 && !narrowColumn)continue
            foundInline=true'''
new='''            // V189 DRY: require independent real printed-number boxes in at
            // least two narrow RTL rows, not seven. Real scanned newspapers
            // may omit several digits even when source word boxes are correct.
            val compactRows=candidates.count{(row,_,observed)->
                row.rect.left>=width*58/100 &&
                    row.rect.right-row.rect.left<=width*44/100 &&
                    observed.any{it in reconciled}
            }
            val narrowColumn=shared==0 && anchored.size>=2 &&
                singleAnchorRows>=2 && compactRows>=2 &&
                rightLaneStarts*2>=anchored.size &&
                verticalSpan>=height/80
            DebugLog.i("OCR_COLUMN_V189",
                "dir="+section.direction+" rawRows="+section.rows.size+
                " expected="+expected.size+" wordAnchors="+
                candidates.sumOf{it.third.size}+" aligned="+anchored.size+
                " single="+singleAnchorRows+" compact="+compactRows+
                " right="+rightLaneStarts+" shared="+shared+
                " span="+verticalSpan+" enabled="+narrowColumn)
            if(shared==0 && !narrowColumn)continue
            foundInline=true'''
if s.count(old)!=1:raise SystemExit('v188 compact gate is not unique; aborting')
s=s.replace(old,new,1)
if s.count('V186_PREVIEW_ONLY: source-pixel word-box boundaries;')!=1:
    raise SystemExit('Expected V186 reviewer marker missing')
s=s.replace('V186_PREVIEW_ONLY: source-pixel word-box boundaries;',
            'V189_PREVIEW_ONLY: source-pixel word-box boundaries;',1)
src.write_text(s,encoding='utf-8')

engine=root/'app/src/main/java/com/example/hebrewcrossword/HigiLocalOcrCropEngine.kt'
s=engine.read_text(encoding='utf-8')
needle='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
if s.count(needle)!=1:raise SystemExit('Engine review-only insertion point missing')
block=r'''        // V189 DRY review-only safety guard. A legacy whole-row crop is NOT
        // a one-clue crop when it contains a different printed clue number.
        // Text on the RIGHT of its own RTL number is also a foreign fragment.
        // Only ADMIN preview maps are filtered; canonical/manual/AI unchanged.
        if(refineSharedRows && auditWords.isNotEmpty()){
            val printedStart=Regex("^[0-9]{1,2}[.,:]$")
            fun startNum(t:String):Int?{
                val normalized=t.trim().replace('\uFF0E','.')
                return if(printedStart.matches(normalized))
                    normalized.dropLast(1).toIntOrNull() else null
            }
            newPreviews.keys.toList().forEach{candidate->
                val origin=newPreviewReasons[candidate].orEmpty()
                if(!origin.startsWith("V178_") && !origin.startsWith("V179_"))
                    return@forEach
                val proposal=newPreviews[candidate]?:return@forEach
                if(proposal.lines.isEmpty() || proposal.lines.any{it.left<0.58f})
                    return@forEach
                val inside=auditWords.filter{word->
                    word.box.valid && word.confidence>=40 &&
                    proposal.lines.any{part->
                        val x=(word.box.left+word.box.right)/(2f*w)
                        val y=(word.box.top+word.box.bottom)/(2f*h)
                        x>=part.left && x<=part.right &&
                            y>=part.top && y<=part.bottom
                    }
                }
                val foreign=inside.firstOrNull{word->
                    word.confidence>=65 &&
                        startNum(word.text)?.let{it!=candidate.number}==true
                }
                val own=inside.firstOrNull{word->
                    word.confidence>=65 &&
                        startNum(word.text)==candidate.number
                }
                val preceding=own?.let{anchor->
                    inside.firstOrNull{word->
                        word!==anchor && word.box.left>=anchor.box.right+8 &&
                            word.box.right-word.box.left>=16 &&
                            kotlin.math.min(word.box.bottom,anchor.box.bottom)-
                                kotlin.math.max(word.box.top,anchor.box.top)>8
                    }
                }
                if(foreign!=null || preceding!=null){
                    newPreviews.remove(candidate)
                    val why=if(foreign!=null) "FOREIGN_PRINTED_NUMBER" else
                        "TEXT_BEFORE_OWN_RTL_START"
                    newPreviewReasons[candidate]="V189_UNSAFE_LEGACY_PREVIEW:"+why+
                        "; source-word evidence; withheld for manual review; "+
                        "NO AI re-decode / NO canonical write"
                    DebugLog.i("LOCAL_OCR_V189",
                        "key="+wire(candidate)+" reason="+why+
                        " legacyPreviewWithheld=true")
                }
            }
        }
'''
s=s.replace(needle,block+needle,1)
engine.write_text(s,encoding='utf-8')

test=root/'app/src/test/java/com/example/hebrewcrossword/OcrCompactColumnV188Test.kt'
t=test.read_text(encoding='utf-8')
needle='''    @Test fun sameSingleMarkerPatternInBroadLayoutDoesNotActivate() {'''
if t.count(needle)!=1:raise SystemExit('v188 test anchor missing')
new_test=r'''    @Test fun sparseNarrowColumnDoesNotRequireSevenAnchors() {
        val (allRows,allWords)=fixture(true)
        val rows=allRows.take(5) // heading plus four independently printed starts
        val words=allWords.take(12)
        val expected=(1..4).map{"H$it"}.toSet()
        val result=OcrInlineClueRecoveryV180.recover(rows,words,3000,2400,expected)
        assertTrue(result.inlineDetected)
        assertEquals(expected,result.previews.keys)
        assertTrue(result.previews.values.flatten().all{it.valid})
    }

    @Test fun missingExpectedNumberDoesNotFabricateAClue() {
        val (allRows,allWords)=fixture(true)
        val rows=allRows.take(5)
        val words=allWords.take(12)
        val expected=setOf("H1","H2","H3","H4","H8")
        val result=OcrInlineClueRecoveryV180.recover(rows,words,3000,2400,expected)
        assertFalse("H8" in result.previews)
    }

'''
t=t.replace(needle,new_test+needle,1)
test.write_text(t,encoding='utf-8')

gradle=root/'app/build.gradle.kts'
t=gradle.read_text(encoding='utf-8')
for a,b in (('versionCode = 338','versionCode = 339'),
            ('versionName = "0.15.188"','versionName = "0.15.189"')):
    if t.count(a)!=1:raise SystemExit('Version invariant failed '+a)
    t=t.replace(a,b,1)
gradle.write_text(t,encoding='utf-8')
print('Prepared v189 DRY narrow column + invalid preview filter + unit tests.')
