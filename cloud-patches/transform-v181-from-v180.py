#!/usr/bin/env python3
"""Upgrade verified Higi 0.15.180 DRY source to 0.15.181.
Administrator OCR review only; no AI, canonical writes, or app backend changes.
"""
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
source = root / "app/src/main/java/com/example/hebrewcrossword"

def swap(path, old, new):
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"Unexpected source in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")

view = source / "AdminOcrSelectedCropView.kt"
swap(view,
    "    // Fit the entire printed line by default. Readable/enlarged mode is opt-in.\n    private var fitToWidth=true",
    "    // Prefer a readable source-pixel crop at open; width-fit remains available.\n    // Large original lines scroll horizontally from their RTL start.\n    private var fitToWidth=false")
swap(view,
    "        fitImage()\n    }\n    fun fitImage()=fitWidth()",
    "        fitImage()\n    }\n    fun fitImage()=fitReadable()")
swap(view,
    "        val readable=(dp(34f)/medianHeight).coerceAtMost(8f)",
    "        val readable=(dp(38f)/medianHeight).coerceAtMost(8f)")
swap(view,
    "        val originY=if(totalHeight>visibleHeight)pad+panY else (height-totalHeight.toFloat())/2f",
    "        // Keep the first segment near the upper edge instead of losing it\n"
    "        // in a large empty white center on tall phone displays.\n"
    "        val originY=pad+panY")

inline = source / "OcrInlineClueRecoveryV180.kt"
swap(inline,
    "    private fun union(words:List<OcrSharedRowSplitterV161.Word>,w:Int,h:Int):CropRect? {",
    "    private fun union(words:List<OcrSharedRowSplitterV161.Word>,w:Int,h:Int,\n"
    "                      rowWords:List<OcrSharedRowSplitterV161.Word>):CropRect? {")
swap(inline,
    "        val rect=CropRect(max(0,words.minOf{it.box.left}-1),max(0,words.minOf{it.box.top}),\n"
    "            min(w,words.maxOf{it.box.right}+1),min(h,words.maxOf{it.box.bottom}))",
    "        // Preserve visible Hebrew strokes without consuming adjacent clues.\n"
    "        // Limit margins by the nearest foreign word in this physical row.\n"
    "        val left=words.minOf{it.box.left}\n"
    "        val right=words.maxOf{it.box.right}\n"
    "        val foreign=rowWords.filter{it !in words && it.box.valid}\n"
    "        val previous=foreign.filter{it.box.right<=left}.maxOfOrNull{it.box.right}\n"
    "        val following=foreign.filter{it.box.left>=right}.minOfOrNull{it.box.left}\n"
    "        val leftPad=previous?.let{((left-it-1)/2).coerceIn(0,3)}?:3\n"
    "        val rightPad=following?.let{((it-right-1)/2).coerceIn(0,3)}?:3\n"
    "        val rect=CropRect(max(0,left-leftPad),max(0,words.minOf{it.box.top}),\n"
    "            min(w,right+rightPad),min(h,words.maxOf{it.box.bottom}))")
swap(inline,
    "                    if(selected.none{w-> w.box.left<=a.box.left && w.box.right>=a.box.right} ||\n"
    "                        selected.any{it.box.left<xLeft-3 || it.box.right>xRight+3}){",
    "                    // A number and its dot may be separate OCR word boxes.\n"
    "                    // Require all constituent tokens, never an invented union word.\n"
    "                    if(a.words.any{index->items.getOrNull(index) !in selected} ||\n"
    "                        selected.any{it.box.left<xLeft-3 || it.box.right>xRight+3}){")
swap(inline, "union(prefix,width,height)?.let{rect->", "union(prefix,width,height,items)?.let{rect->")
swap(inline, "val rect=union(selected,width,height)", "val rect=union(selected,width,height,items)")

build = root / "app/build.gradle.kts"
swap(build, "versionCode = 330", "versionCode = 331")
swap(build, 'versionName = "0.15.180"', 'versionName = "0.15.181"')

subprocess.run([sys.executable,"tools/sync-release-version.py","--write"],
               cwd=root,check=True)
subprocess.run([sys.executable,"tools/sync-release-version.py","--check"],
               cwd=root,check=True)
print("Verified Higi 0.15.181 DRY source migration complete.")
