#!/usr/bin/env python3
"""Staged v212 -> v213 series-only OCR read/preview activation; no release or Canonical writes."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
base=root/"app/src/main/java/com/example/hebrewcrossword"
main=base/"MainActivity.kt"
source=main.read_text()
old="        val local=LocalOcrCropPass.run(this,original,prepared.crossword,prepared.points,stage)"
new="""        // Explicit stable series identity only: do not select OCR geometry rules by appearance.
        val ocrSeriesId=OcrSeriesActivationV213.forCatalogId(
            CrosswordCatalog.fromCanonicalTitle(prepared.title)?.id)
        val local=LocalOcrCropPass.run(this,original,prepared.crossword,prepared.points,stage,
            refineSharedRows=ocrSeriesId!=null,layoutSeriesId=ocrSeriesId)"""
assert source.count(old)==1,("main auto import locator",source.count(old))
main.write_text(source.replace(old,new))
runner=base/"AdminLibraryRedecodeRunner.kt"
source=runner.read_text()
old="            val localCrop=LocalOcrCropPass.run(context,bitmap,cw,grid,stage)"
new="""            val cropSeriesId=OcrSeriesActivationV213.forCatalogId(
                CrosswordCatalog.fromCanonicalTitle(original.title)?.id)
            val localCrop=LocalOcrCropPass.run(context,bitmap,cw,grid,stage,
                refineSharedRows=cropSeriesId!=null,layoutSeriesId=cropSeriesId)"""
assert source.count(old)==1,("runner",source.count(old))
runner.write_text(source.replace(old,new))
policy=base/"OcrSeriesActivationV213.kt"
assert not policy.exists(),str(policy)
policy.write_text("""package com.example.hebrewcrossword

/**
 * Opts the three already tested series into their existing source-word OCR review
 * engine. NEVER promotes review-only crops into trusted/canonical automatically.
 * Unknown and ambiguous series fail closed. No change to series' frozen OCR rules.
 */
object OcrSeriesActivationV213 {
    fun forCatalogId(id:String?):String? = when(id) {
        "YEDIOTH_DEKEL_WEEKLY", "YEDIOTH_MONDAY_DEKEL", "YEDIOTH_WEDNESDAY_DEKEL" ->
            OcrSeriesProfilesV197.WEEKLY.id
        "HAFUCH_DEKEL" -> OcrSeriesProfilesV197.HAFUCH.id
        else -> null
    }
}
""")
test=root/"app/src/test/java/com/example/hebrewcrossword/OcrSeriesActivationV213Test.kt"
assert not test.exists()
test.write_text("""package com.example.hebrewcrossword

import org.junit.Assert.*
import org.junit.Test

class OcrSeriesActivationV213Test {
    @Test fun selectedSeriesHaveExactProfiles() {
        assertEquals("YEDIOTH_DEKEL_WEEKLY", OcrSeriesActivationV213.forCatalogId("YEDIOTH_MONDAY_DEKEL"))
        assertEquals("YEDIOTH_DEKEL_WEEKLY", OcrSeriesActivationV213.forCatalogId("YEDIOTH_WEDNESDAY_DEKEL"))
        assertEquals("YEDIOTH_DEKEL_WEEKLY", OcrSeriesActivationV213.forCatalogId("YEDIOTH_DEKEL_WEEKLY"))
        assertEquals("HAFUCH_DEKEL", OcrSeriesActivationV213.forCatalogId("HAFUCH_DEKEL"))
    }
    @Test fun noOtherSeriesActivate() {
        for(id in listOf<String?>(null, "", "TARTEY_DEKEL", "MAARIV_ODED_ROZEN", "YEDIOTH", "HAFUCH", "OTHER"))
            assertNull(OcrSeriesActivationV213.forCatalogId(id))
    }
}
""")
print("STAGED 4 Kotlin files",main,runner,policy,test)
