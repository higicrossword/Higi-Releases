package com.example.hebrewcrossword

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/** Strict Monday-series WORD anchor review. No change to accepted/verified/canonical geometry.
 * A printed start and the very next printed number must be physically anchored.
 */
object OcrSeriesPreviewV197 {
    data class Review(val previews:Map<String,List<CropRect>>,val reasons:Map<String,String>)
    private val printed=Regex("^([0-9]{1,2})[.,:]$")
    private fun n(text:String):Int?=printed.matchEntire(text.trim())?.groupValues?.get(1)?.toIntOrNull()
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
            if(parts.size==1 && parts.single().bottom-parts.single().top<height/25)continue
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
            if(b.top<=a.top+4 || b.top-a.top>height/9 ||
                abs(cx(a)-cx(b))>width/4)continue
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
            if(candidateRows.size !in 2..4 || candidateRows.none{it.id==first.id} ||
                candidateRows.none{it.id==last.id})continue
            val proposed=mutableListOf<CropRect>()
            for(row in candidateRows){
                if(row.box.top>last.box.top+5)break
                val startX=if(row.id==last.id)max(row.box.left,b.right+max(3,width/900))
                    else row.box.left
                if(row.box.right-startX<14)continue
                val top=if(proposed.isEmpty())row.box.top else max(row.box.top,proposed.last().bottom)
                if(row.box.bottom-top<8)continue
                proposed+=CropRect(startX,top,row.box.right,row.box.bottom)
            }
            if(proposed.isEmpty() || proposed.size>3)continue
            if(proposed.none{cx(a) in it.left..it.right && cy(a) in it.top..it.bottom})continue
            if(proposed.any{cx(b) in it.left..it.right && cy(b) in it.top..it.bottom})continue
            if(anchors.any{it!==start.single() && it!==stop.single() &&
                n(it.text)!=null && proposed.any{r->cx(it.box) in r.left..r.right && cy(it.box) in r.top..r.bottom}})continue
            val areaOld=parts.sumOf{(it.right-it.left).toLong()*(it.bottom-it.top)}
            val areaNew=proposed.sumOf{(it.right-it.left).toLong()*(it.bottom-it.top)}
            if(areaNew>=areaOld)continue
            proposals[key]=proposed
            reasons[key]="V197_MONDAY_REVIEW_ONLY: printed $num and $next anchored; pieces=${proposed.size}; not verified; NO canonical write"
        }
        return Review(proposals,reasons)
    }
}