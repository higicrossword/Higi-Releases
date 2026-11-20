#!/usr/bin/env python3
"""DRY-only source patch; no commits, publishing or Firebase access."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
pkg=root/"app/src/main/java/com/example/hebrewcrossword"
template=pkg/"HafuchAdminSourceGridV1.kt"
main=pkg/"MainActivity.kt"

s=template.read_text()
old='''    /** Pixel-proven template candidate, never a blind assignment based on the series name. */
    fun verifiedBounds(source:Bitmap):BoxF? {
        val expected=template()
        val found=GridDetector.locate(source,expected) ?: return null'''
new='''    /** Pixel-proven topology only; do not infer grid from a series title alone. */
    fun matchesKnownMask(grid:Crossword):Boolean {
        val expected=template()
        return grid.rows==13 && grid.cols==13 &&
            (0 until 13).all { y -> (0 until 13).all { x ->
                grid.cell(y,x).blocked==expected.cell(y,x).blocked
            } }
    }

    /** Use only after ordinary detection is missing/mismatched. */
    fun verifiedLocated(source:Bitmap):GridDetector.LocatedResult? {
        val expected=template()
        val found=GridDetector.locate(source,expected) ?: return null'''
assert s.count(old)==1, "template anchor"
s=s.replace(old,new)
old='''        return found.bounds
    }
}'''
new='''        return found
    }

    fun verifiedBounds(source:Bitmap):BoxF? = verifiedLocated(source)?.bounds
}'''
assert s.count(old)==1,"template return anchor"
print('TEMPLATE_BEFORE_ASSERT',repr(s[-550:]))
assert 'fun verifiedBounds(source:Bitmap):BoxF? = verifiedLocated(source)?.bounds' in s
assert 'return found.bounds' not in s
template.write_text(s)
print('TEMPLATE_FINAL',repr(s[-600:]))

s=main.read_text()
old='''        val located=GridDetector.locate(original, knownLayout) ?: error("לא זוהתה רשת באופן אוטומטי")
        val b=located.bounds'''
new='''        val ordinarilyLocated=GridDetector.locate(original, knownLayout)
        // HAFUCH_DEKEL only: the generic detector can report an 11x11 interior
        // with high confidence. Recover 13x13 only on source-pixel proof.
        val isHafuch=CrosswordCatalog.fromCanonicalTitle(cleanSuggested.orEmpty())?.id=="HAFUCH_DEKEL"
        val requiresHafuchRescue=isHafuch &&
            (ordinarilyLocated==null ||
                !HafuchAdminSourceGridV1.matchesKnownMask(ordinarilyLocated.result.crossword))
        val hafuchVerified=if(requiresHafuchRescue)
            HafuchAdminSourceGridV1.verifiedLocated(original) else null
        if(requiresHafuchRescue)DebugLog.i("HAFUCH_GRID_RESCUE",
            "series=HAFUCH_DEKEL verified=${hafuchVerified!=null} " +
            "initial=${ordinarilyLocated?.result?.crossword?.rows}x${ordinarilyLocated?.result?.crossword?.cols}")
        val located=hafuchVerified ?: ordinarilyLocated ?: error("לא זוהתה רשת באופן אוטומטי")
        val b=located.bounds'''
assert s.count(old)==1,"single-image import anchor"
s=s.replace(old,new)
# Pixel-proven rescue must not be overturned by second-pass refinement.
old='''        val refined=if(located.variant.startsWith("template-")) null else {'''
new='''        val refined=if(hafuchVerified!=null || located.variant.startsWith("template-")) null else {'''
assert s.count(old)==1,"refinement anchor"
s=s.replace(old,new)
old='''        val refinement=if(located.variant.startsWith("template-"))
            GridRefinement.Choice(located.result.crossword,"full-page","verified-template-topology-preserved")'''
new='''        val refinement=if(hafuchVerified!=null || located.variant.startsWith("template-"))
            GridRefinement.Choice(located.result.crossword,"full-page","verified-template-topology-preserved")'''
assert s.count(old)==1,"choice anchor"
s=s.replace(old,new)
main.write_text(s)
print("DRY_PATCH_APPLIED",template.name,main.name)
