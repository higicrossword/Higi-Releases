#!/usr/bin/env python3
"""Apply Higi 0.15.188 administrator-only narrow-column OCR review improvement."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
src=root/'app/src/main/java/com/example/hebrewcrossword/OcrInlineClueRecoveryV180.kt'
text=src.read_text(encoding='utf-8')
old='''            val shared=candidates.count{row->row.third.count{it in reconciled}>=2}
            if(shared==0)continue
            foundInline=true'''
new='''            val shared=candidates.count{row->row.third.count{it in reconciled}>=2}
            // V188 DRY: one printed number per physical OCR row is normal in
            // narrow right-hand clue columns. The old "shared>=1" test made
            // that layout entirely bypass word-based segmentation and display
            // multi-row V178 rectangles containing foreign clue numbers.
            //
            // Do not activate this alternative for sparse/noisy OCR or the
            // full-width newspaper rows supported by the old shared-row path.
            // Every start used here is an actual source-pixel number WORD box
            // already aligned unambiguously to an expected clue.
            val anchored=candidates.flatMap{it.third}.filter{it in reconciled}
            val singleAnchorRows=candidates.count{r->
                r.third.count{it in reconciled}==1
            }
            val rightLaneStarts=anchored.count{it.box.left>=width*62/100 &&
                it.box.right>=width*70/100}
            val verticalSpan=if(anchored.isEmpty())0 else
                anchored.maxOf{it.box.bottom}-anchored.minOf{it.box.top}
            val narrowColumn=shared==0 && anchored.size>=7 &&
                singleAnchorRows>=7 && rightLaneStarts*5>=anchored.size*4 &&
                verticalSpan>=height/8
            if(shared==0 && !narrowColumn)continue
            foundInline=true'''
if text.count(old)!=1:
    raise SystemExit('Unexpected v187 narrow-column gate; refusing unsafe patch')
text=text.replace(old,new,1)
src.write_text(text,encoding='utf-8')

gradle=root/'app/build.gradle.kts'
t=gradle.read_text(encoding='utf-8')
for a,b in (('versionCode = 337','versionCode = 338'),
            ('versionName = "0.15.187"','versionName = "0.15.188"')):
    if t.count(a)!=1:raise SystemExit('Version invariant failed: '+a)
    t=t.replace(a,b,1)
gradle.write_text(t,encoding='utf-8')

test=root/'app/src/test/java/com/example/hebrewcrossword/OcrCompactColumnV188Test.kt'
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text(r'''package com.example.hebrewcrossword

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * DRY-only regression for one-number-per-line narrow newspaper columns.
 * Every image rectangle is from synthetic source word boxes. No AI or cloud.
 */
class OcrCompactColumnV188Test {
    private fun fixture(narrow:Boolean):Pair<
        List<OcrRawLineV166>,List<OcrSharedRowSplitterV161.Word>> {
        val rows=mutableListOf<OcrRawLineV166>()
        val words=mutableListOf<OcrSharedRowSplitterV161.Word>()
        val x0=if(narrow)1980 else 900
        val xr=if(narrow)2820 else 1640
        rows+=OcrRawLineV166(1,"מאוזן:",CropRect(x0,160,xr,187),90)
        for(n in 1..7){
            val y=210+n*85
            rows+=OcrRawLineV166(n+1,"$n. נוסח הגדרה (5)",
                CropRect(x0,y,xr,y+32),93)
            words+=OcrSharedRowSplitterV161.Word("$n.",
                CropRect(xr-55,y+5,xr-22,y+26),93)
            words+=OcrSharedRowSplitterV161.Word("הגדרה",
                CropRect(xr-340,y+4,xr-65,y+28),91)
            words+=OcrSharedRowSplitterV161.Word("(5)",
                CropRect(xr-405,y+4,xr-351,y+29),92)
        }
        return rows to words
    }

    @Test fun compactRightColumnIsSegmentedByRealWordBoxes() {
        val (rows,words)=fixture(true)
        val expected=(1..7).map{"H$it"}.toSet()
        val result=OcrInlineClueRecoveryV180.recover(rows,words,3000,2400,expected)
        assertTrue(result.inlineDetected)
        assertEquals(expected,result.previews.keys)
        assertTrue(result.previews.values.all{it.size==1})
        assertTrue(result.previews.values.all{r->r.all{
            it.left>1800 && it.right<2950 && it.right>it.left
        }})
        assertTrue(result.diagnostics.values.all{it.contains("NO canonical write") ||
            it.contains("NO AI re-decode / NO canonical write")})
    }

    @Test fun sameSingleMarkerPatternInBroadLayoutDoesNotActivate() {
        val (rows,words)=fixture(false)
        val result=OcrInlineClueRecoveryV180.recover(
            rows,words,3000,2400,(1..7).map{"H$it"}.toSet())
        assertFalse(result.inlineDetected)
        assertTrue(result.previews.isEmpty())
    }
}
''',encoding='utf-8')
print('Applied v188 DRY compact-column gate + JUnit regressions')
