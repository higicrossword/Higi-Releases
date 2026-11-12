package com.example.hebrewcrossword

import kotlin.math.max
import kotlin.math.min

/**
 * Final on-screen geometry audit for YEDIOTH_DEKEL_WEEKLY administrator DRY mode.
 * This receives ONLY the objects that survived LocalOcrCropPass filtering, not
 * HigiLocalOcrCropEngine's intermediate `accepted` map. It never writes Canonical.
 */
object OcrWeeklyFinalGeometryV201 {
    enum class Origin { VERIFIED_FINAL, SOURCE_ANCHORED_REVIEW, OTHER_REVIEW, REJECTED_LEGACY_REVIEW }
    data class Candidate(val parts: List<CropRect>, val origin: Origin)
    data class Audit(val reasons: Map<String,List<String>>, val demoteVerified: Set<String>)
    private val clue = Regex("^[HV][0-9]{1,2}$")

    private fun area(r: CropRect): Long =
        max(0,r.right-r.left).toLong()*max(0,r.bottom-r.top)
    private fun overlap(a: CropRect,b: CropRect): Long =
        max(0,min(a.right,b.right)-max(a.left,b.left)).toLong() *
        max(0,min(a.bottom,b.bottom)-max(a.top,b.top))
    private fun centerWithin(r:CropRect,w:OcrSharedRowSplitterV161.Word):Boolean {
        val x=(w.box.left+w.box.right)/2
        val y=(w.box.top+w.box.bottom)/2
        return x>=r.left && x<r.right && y>=r.top && y<r.bottom
    }
    private fun validGridLeft(value:Int?, imageWidth:Int):Int? =
        value?.takeIf { imageWidth>=600 && it in (imageWidth*0.58f).toInt()..(imageWidth*0.83f).toInt() }

    /**
     * Trim ONLY newly source-anchored Across previews to the measured grid edge.
     * A bad/uncertain grid does NOT become a guessed crop.  Returning null
     * withholds the unsafe candidate and leaves legacy/manual review available.
     */
    fun clipFreshAcross(label:String,parts:List<CropRect>,gridLeftPx:Int?,imageWidth:Int):List<CropRect>? {
        if(!label.matches(clue) || label[0]!='H')return parts
        val limit=validGridLeft(gridLeftPx,imageWidth)?.minus(2) ?: return parts
        val output=parts.map{p->
            if(p.left>=limit)return null
            CropRect(p.left,p.top,min(p.right,limit),p.bottom)
        }
        if(output.any{!it.valid || it.right-it.left<9})return null
        return output
    }

    fun inspect(candidates:Map<String,Candidate>,words:List<OcrSharedRowSplitterV161.Word>,
                imageWidth:Int,gridLeftPx:Int?):Audit {
        val reasons=linkedMapOf<String,MutableList<String>>()
        val blocking=linkedSetOf<String>()
        fun warn(label:String, message:String,block:Boolean) {
            reasons.getOrPut(label){mutableListOf()}.add(
                (if(block)"V201_FINAL_GEOMETRY_BLOCK: " else "V201_FINAL_GEOMETRY_REVIEW_ONLY: ")+message)
            if(block && candidates[label]?.origin==Origin.VERIFIED_FINAL)blocking+=label
        }
        val valid=candidates.filterKeys{it.matches(clue)}.toSortedMap()
        val grid=validGridLeft(gridLeftPx,imageWidth)
        for((label,candidate) in valid) {
            // A source text row may be split horizontally into different boxes.
            // Adjacent/non-intersecting strips are fine; substantial repeated
            // source pixels are not. This check was absent from V199/V200.
            for(i in candidate.parts.indices) for(j in i+1 until candidate.parts.size) {
                val a=candidate.parts[i]; val b=candidate.parts[j]
                val small=min(area(a),area(b))
                if(small<=0L)continue
                val shared=overlap(a,b)
                val pct=(shared*100L/small).toInt()
                val commonWidth=max(0,min(a.right,b.right)-max(a.left,b.left))
                val commonHeight=max(0,min(a.bottom,b.bottom)-max(a.top,b.top))
                if(pct>=14 && commonWidth>=6 && commonHeight>=3)
                    warn(label,"SELF_OVERLAP: parts=${i+1},${j+1},geom=${pct}%; review-only",true)
            }
            // Check actual measured grid, not a hard-coded profile column width.
            if(label[0]=='H' && grid!=null) {
                for((i,part) in candidate.parts.withIndex()) {
                    val spill=part.right-grid
                    if(spill>2)
                        warn(label,"GRID_INTRUSION: part=${i+1},gridLeft=$grid,right=${part.right},spill=${spill}px",true)
                }
            }
        }
        val entries=valid.entries.toList()
        for(i in entries.indices) for(j in i+1 until entries.size) {
            val (ak,a)=entries[i]; val (bk,b)=entries[j]
            if(ak[0]!=bk[0])continue
            var pct=0
            var touching=false
            for(ap in a.parts) for(bp in b.parts){
                val small=min(area(ap),area(bp));if(small<=0L)continue
                val shared=overlap(ap,bp)
                if(shared>0L){touching=true;pct=max(pct,(100L*shared/small).toInt())}
            }
            if(!touching)continue
            val commonWords=words.count{w->w.box.valid && w.confidence>=35 &&
                a.parts.any{centerWithin(it,w)} && b.parts.any{centerWithin(it,w)}}
            if(pct<55 && commonWords==0)continue
            val aLegacy=a.origin==Origin.REJECTED_LEGACY_REVIEW
            val bLegacy=b.origin==Origin.REJECTED_LEGACY_REVIEW
            // Invalid old bounds must NEVER veto a final valid OCR candidate.
            // They can be displayed with a low-priority warning for the owner.
            if(aLegacy||bLegacy){
                if(aLegacy)warn(ak,"OLD_REJECTED_BOUND_OVERLAPS: $bk,geom=${pct}%,words=$commonWords; cannot claim ownership",false)
                if(bLegacy)warn(bk,"OLD_REJECTED_BOUND_OVERLAPS: $ak,geom=${pct}%,words=$commonWords; cannot claim ownership",false)
                continue
            }
            val strong=commonWords>0
            val bothTrusted=a.origin==Origin.VERIFIED_FINAL && b.origin==Origin.VERIFIED_FINAL
            val realConflict=strong || (bothTrusted && pct>=55)
            // A provisional preview with geometric-only overlap does not veto a
            // verified final candidate. A genuinely shared OCR word does.
            val aBlock=realConflict && a.origin==Origin.VERIFIED_FINAL
            val bBlock=realConflict && b.origin==Origin.VERIFIED_FINAL
            warn(ak,"CROSS_CLUE: $bk,geom=${pct}%,sharedWords=$commonWords,peer=${b.origin}",aBlock)
            warn(bk,"CROSS_CLUE: $ak,geom=${pct}%,sharedWords=$commonWords,peer=${a.origin}",bBlock)
        }
        return Audit(reasons.mapValues{it.value.toList()},blocking)
    }
}