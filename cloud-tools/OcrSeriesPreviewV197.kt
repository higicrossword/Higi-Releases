package com.example.hebrewcrossword

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/** Strict Monday-series WORD anchor review. No change to accepted/verified/canonical geometry.
 * A printed start and the very next printed number must be physically anchored.
 */
object OcrSeriesPreviewV197 {
    data class Review(val previews:Map<String,List<CropRect>>,val reasons:Map<String,String>)
    private val printed=Regex("^(?:([0-9]{1,2})[.,:]|[.,:]([0-9]{1,2}))$")
    private fun n(text:String):Int?=printed.matchEntire(text.trim())?.let{ (it.groupValues[1].ifBlank { it.groupValues[2] }).toIntOrNull() }
    private fun overlap(a:CropRect,b:CropRect)=min(a.bottom,b.bottom)-max(a.top,b.top)
    private fun cx(a:CropRect)=(a.left+a.right)/2
    private fun cy(a:CropRect)=(a.top+a.bottom)/2

    fun inspect(profile:OcrSeriesProfilesV197.Profile,
        old:Map<String,List<CropRect>>, lines:List<OcrTextLocatorV033.Line>,
        words:List<OcrSharedRowSplitterV161.Word>,expected:Set<String>,
        width:Int,height:Int):Review {
        if(!profile.mondayBoundaryReview || width<600 || height<400 || old.isEmpty())
            return Review(emptyMap(),emptyMap())
        val proposals=linkedMapOf<String,List<CropRect>>()
        val reasons=linkedMapOf<String,String>()
        for((key,parts) in old){
            if(!key.matches(Regex("^[HV][0-9]{1,2}$")) || key !in expected ||
                parts.isEmpty() || parts.any{!it.valid})continue
            // Already narrow one-row boundaries must not be replaced.
            // A one-row legacy candidate may still be partial; review it, never auto-publish.
            val num=key.drop(1).toIntOrNull()?:continue
            val next=expected.asSequence().filter{it.startsWith(key.first())}
                .mapNotNull{it.drop(1).toIntOrNull()}.filter{it>num}.minOrNull()?:continue
            val bounds=CropRect(parts.minOf{it.left},parts.minOf{it.top},
                parts.maxOf{it.right},parts.maxOf{it.bottom})
            val laneWidth=bounds.right-bounds.left
            if(laneWidth !in width/9..width*48/100)continue
            val anchors=words.filter{it.box.valid && it.confidence>=70 &&
                it.box.left>=bounds.left-width/25 && it.box.right<=bounds.right+width/25 &&
                it.box.top>=bounds.top-height/70 && it.box.top<=bounds.bottom+height/70}
            val start=anchors.filter{n(it.text)==num}
            val stop=anchors.filter{n(it.text)==next}
            if(start.size!=1 || stop.size!=1){
                reasons[key]="V197_MISSING_PRINTED_ANCHOR:own=${start.size} next=${stop.size}; review unchanged"
                continue
            }
            val a=start.single().box;val b=stop.single().box
            val sameRow=abs(cy(b)-cy(a))<=max(6,height/125)
            if((sameRow && cx(b)>=cx(a)) || (!sameRow && cy(b)<=cy(a)) ||
                cy(b)-cy(a)>height/7 || abs(cx(a)-cx(b))>width/3)continue
            fun rowFor(rect:CropRect)=lines.filter{it.box.valid && it.confidence>=40 &&
                overlap(it.box,rect)>=max(4,(rect.bottom-rect.top)/2) &&
                cx(rect) in (it.box.left-12)..(it.box.right+12)}
                .maxByOrNull{overlap(it.box,rect)}
            val first=rowFor(a)?:continue
            val last=rowFor(b)?:continue
            if(last.box.top<first.box.top)continue
            val candidateRows=lines.filter{it.box.valid && it.confidence>=40 &&
                it.box.top>=first.box.top-8 && it.box.top<=last.box.top+8 &&
                it.box.left>=bounds.left-width/25 &&
                it.box.right<=bounds.right+width/25}
                .distinctBy{it.id}.sortedBy{it.box.top}
            if(candidateRows.size !in 1..5 || candidateRows.none{it.id==first.id} ||
                candidateRows.none{it.id==last.id})continue
            val proposed=mutableListOf<CropRect>()
            for(row in candidateRows){
                if(row.box.top>last.box.top+5)break
                val cutMargin=max(3,width/500)
                // Source is RTL: after the OWN number starts left of it;
                // before the NEXT number ends to the right of it.
                val startX=if(row.id==last.id)max(row.box.left,b.right+cutMargin) else row.box.left
                val endX=if(row.id==first.id)min(row.box.right,a.right+cutMargin) else row.box.right
                if(endX-startX<8)continue
                val top=if(proposed.isEmpty())row.box.top else max(row.box.top,proposed.last().bottom)
                if(row.box.bottom-top<8)continue
                proposed+=CropRect(startX,top,endX,row.box.bottom)
            }
            if(proposed.isEmpty() || proposed.size>5)continue
            if(proposed.none{cx(a) in it.left..it.right && cy(a) in it.top..it.bottom})continue
            if(proposed.any{cx(b) in it.left..it.right && cy(b) in it.top..it.bottom})continue
            if(anchors.any{it!==start.single() && it!==stop.single() &&
                n(it.text)!=null && proposed.any{r->cx(it.box) in r.left..r.right && cy(it.box) in r.top..r.bottom}})continue
            val areaOld=parts.sumOf{(it.right-it.left).toLong()*(it.bottom-it.top)}
            val areaNew=proposed.sumOf{(it.right-it.left).toLong()*(it.bottom-it.top)}
            if(areaNew>=areaOld)continue
            proposals[key]=proposed
            reasons[key]="YEDIOTH_WEEKLY_TWO_BOUNDARY_REVIEW_ONLY: printed $num and $next anchored; pieces=${proposed.size}; sameRow=$sameRow; not verified; NO canonical write"
        }
        return Review(proposals,reasons)
    }
}