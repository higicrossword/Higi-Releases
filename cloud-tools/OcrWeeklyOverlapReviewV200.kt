package com.example.hebrewcrossword

import kotlin.math.max
import kotlin.math.min

/**
 * Yedioth Dekel WEEKLY, administrator DRY diagnostics ONLY.
 * Pixel boxes from earlier OCR pipelines are not authoritative ownership claims.
 * This helper reports possible conflicts without deleting, replacing, accepting,
 * publishing or resolving any candidate. The Android review screen must display
 * and explicitly warn on every such candidate, with approval disabled.
 */
object OcrWeeklyOverlapReviewV200 {
    enum class Origin { ACCEPTED, SOURCE_ANCHORED, LEGACY_PREVIEW }
    data class Candidate(val parts:List<CropRect>, val origin:Origin)
    data class Warning(
        val peer:String,
        val peerOrigin:Origin,
        val sharedOcrWords:Int,
        val overlapPercentOfSmaller:Int,
        val classification:String
    )
    data class Result(
        val candidates:Map<String,Candidate>,
        val warnings:Map<String,List<Warning>>
    )
    private val clueKey=Regex("^[HV][0-9]{1,2}$")
    private fun area(r:CropRect):Long =
        max(0,r.right-r.left).toLong()*max(0,r.bottom-r.top)
    private fun common(a:CropRect,b:CropRect):Long =
        max(0,min(a.right,b.right)-max(a.left,b.left)).toLong()*
            max(0,min(a.bottom,b.bottom)-max(a.top,b.top))
    private fun containsCenter(rect:CropRect,word:OcrSharedRowSplitterV161.Word):Boolean {
        val x=(word.box.left+word.box.right)/2
        val y=(word.box.top+word.box.bottom)/2
        return x>=rect.left && x<rect.right && y>=rect.top && y<rect.bottom
    }

    fun assess(candidates:Map<String,Candidate>,
               words:List<OcrSharedRowSplitterV161.Word>):Result {
        val warnings=linkedMapOf<String,MutableList<Warning>>()
        val sorted=candidates.entries.filter{it.key.matches(clueKey)}.sortedBy{it.key}
        for(i in sorted.indices) for(j in i+1 until sorted.size){
            val (a,ca)=sorted[i]
            val (b,cb)=sorted[j]
            // Printed Across/Down columns are different physical text lanes.
            if(a[0]!=b[0])continue
            var highestPct=0
            var overlapping=false
            for(p in ca.parts)for(q in cb.parts){
                val smaller=min(area(p),area(q))
                if(smaller<=0L)continue
                val shared=common(p,q)
                if(shared<=0L)continue
                overlapping=true
                // Long arithmetic prevents overflow on high-resolution sources.
                val percent=(shared*100L/smaller).toInt()
                highestPct=max(highestPct,percent)
            }
            if(!overlapping)continue
            val sharedWords=words.count{word->
                word.box.valid && word.confidence>=35 &&
                ca.parts.any{containsCenter(it,word)} &&
                cb.parts.any{containsCenter(it,word)}
            }
            // A shared OCR word is a stronger signal than large geometric boxes;
            // large intersections without a recognized word are *uncertain* only.
            if(sharedWords==0 && highestPct<55)continue
            val evidence=if(sharedWords>0)"SHARED_OCR_WORD_CENTERS"
                         else "GEOMETRIC_ONLY_UNVERIFIED"
            warnings.getOrPut(a){mutableListOf()}.add(
                Warning(b,cb.origin,sharedWords,highestPct,evidence))
            warnings.getOrPut(b){mutableListOf()}.add(
                Warning(a,ca.origin,sharedWords,highestPct,evidence))
        }
        // No candidate is removed here, even when multiple edges form a chain.
        return Result(candidates,warnings.mapValues{it.value.toList()})
    }

    fun detail(warnings:List<Warning>):String =
        warnings.sortedBy{it.peer}.joinToString(" | ") { warning ->
            "${warning.peer}[${warning.peerOrigin},${warning.classification},"+
                "sharedWords=${warning.sharedOcrWords},geom=${warning.overlapPercentOfSmaller}%]"
        }

    /**
     * Allow ONLY an unpublishable multi-piece preview where the single narrow
     * segment is the clue's printed start number. No global threshold change.
     * The caller must also have validation reason 'too-narrow-px' and MUST keep
     * the candidate in DRY review rather than the trusted/canonical map.
     */
    fun narrowNumberOnlyPreview(label:String,parts:List<CropRect>,
                                words:List<OcrSharedRowSplitterV161.Word>,
                                invalidReason:String):Boolean {
        if(!label.matches(clueKey) || parts.size !in 2..5 ||
            !Regex("^physical-row-[0-9]+:too-narrow-px:[0-9]+$").matches(invalidReason))return false
        val target=label.drop(1).toInt()
        val narrow=parts.filter{(it.right-it.left) in 9..23}
        if(narrow.size!=1 || parts.any{!it.valid || it.bottom-it.top<12})return false
        val rect=narrow.single()
        val numberWords=words.filter{word->
            word.box.valid && word.confidence>=50 && containsCenter(rect,word) &&
                word.text.trim().matches(Regex("^[0-9]{1,2}[.:]?$"))
        }
        val own=numberWords.any{it.text.trim().trimEnd('.',':').toIntOrNull()==target}
        val other=numberWords.any{it.text.trim().trimEnd('.',':').toIntOrNull()!=target}
        if(!own||other)return false
        return parts.filter{it!==rect}.all{it.right-it.left>=24}
    }
}