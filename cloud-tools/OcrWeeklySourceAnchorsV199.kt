package com.example.hebrewcrossword

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Yedioth Dekel Monday+Wednesday administrator DRY review only.
 * Reconstruct clue ownership DIRECTLY from boxed OCR word numbers.  Unlike V197,
 * this class never requires a pre-existing crop and never changes Canonical.
 * Weak/missing anchors produce diagnostics, not guessed or published crops.
 */
object OcrWeeklySourceAnchorsV199 {
    data class Result(val previews: Map<String,List<CropRect>>,
                      val reasons: Map<String,String>)
    private data class Anchor(val number:Int,val box:CropRect,val inferred:Boolean)
    private data class OcrRow(val words:List<OcrSharedRowSplitterV161.Word>) {
        val top:Int get()=words.minOf{it.box.top}
        val bottom:Int get()=words.maxOf{it.box.bottom}
        val center:Int get()=(top+bottom)/2
    }
    private val marker=Regex("^(?:([0-9]{1,2})[.:]|[.:]([0-9]{1,2}))$")
    private val bare=Regex("^[0-9]{1,2}$")
    private val keyPattern=Regex("^[HV][0-9]{1,2}$")
    private fun clean(text:String)=text.replace(Regex("[\\u200e\\u200f\\u202a-\\u202e\\u2066-\\u2069\\s]"),"")
        .replace('\uFF0E','.')
    private fun printed(t:String):Int?=marker.matchEntire(clean(t))?.let{
        (it.groupValues[1].ifEmpty{it.groupValues[2]}).toIntOrNull()
    }
    private fun inRect(x:Int,y:Int,r:CropRect)=x>=r.left&&x<r.right&&y>=r.top&&y<r.bottom
    private fun area(r:CropRect)=max(0,r.right-r.left).toLong()*max(0,r.bottom-r.top)
    private fun common(a:CropRect,b:CropRect)=max(0,min(a.right,b.right)-max(a.left,b.left)).toLong() *
        max(0,min(a.bottom,b.bottom)-max(a.top,b.top))
    private fun inLane(r:CropRect,dir:Char,w:Int):Boolean {
        // Broad relative layout boundaries, used ONLY after the verified series
        // selector chose YEDIOTH_DEKEL_WEEKLY (two clues columns LEFT of grid).
        val c=(r.left+r.right)/2f/w
        return if(dir=='H')c in 0.315f..0.675f else c in 0.003f..0.315f
    }
    private fun laneRange(dir:Char,w:Int):IntRange = if(dir=='H')
        ((.315*w).toInt())..((.675*w).toInt()) else 0..((.315*w).toInt())

    /** Independently extract strictly anchored numeric starts in ONE text column. */
    private fun anchors(dir:Char, words:List<OcrSharedRowSplitterV161.Word>,
                        nums:List<Int>,w:Int,h:Int):Map<Int,Anchor> {
        val all=words.filter{it.box.valid && it.confidence>=40 &&
            it.box.top>h/4 && it.box.bottom<h*96/100 && inLane(it.box,dir,w)}
        val matches=linkedMapOf<Int,Anchor>()
        for(num in nums){
            val strong=all.filter{printed(it.text)==num && it.confidence>=60}
            if(strong.size==1)matches[num]=Anchor(num,strong.single().box,false)
        }
        // Missing dots and truncated leading digits are REVIEW-ONLY evidence.
        // Limit suffix inference to unique tokens near the right of each text lane.
        // Never infer when there is any ambiguity or a competing exact anchor.
        for(num in nums){
            if(num in matches)continue
            val last=(num%10).toString()
            val plausible=all.filter{word->
                val raw=clean(word.text)
                val bareNumber=bare.matches(raw) && raw==num.toString()
                val truncation=num>=10 &&
                    (raw==last || printed(raw)==(num%10)) &&
                    word.box.right.toFloat()/w >= if(dir=='H')0.55f else 0.245f
                (bareNumber || truncation) && word.confidence>=52
            }
            if(plausible.size!=1)continue
            val candidate=plausible.single().box
            val prior=nums.filter{it<num}.lastOrNull()?.let{matches[it]}
            val after=nums.firstOrNull{it>num}?.let{matches[it]}
            val middle=(candidate.top+candidate.bottom)/2
            // For inline starts the next number can share a printed row.
            if(prior!=null && middle<prior.box.top-4)continue
            if(after!=null && middle>after.box.bottom+4)continue
            if(matches.values.any{it.box==candidate})continue
            matches[num]=Anchor(num,candidate,true)
        }
        return matches
    }
    private fun rows(words:List<OcrSharedRowSplitterV161.Word>,w:Int,h:Int,dir:Char):List<OcrRow> {
        val eligible=words.filter{it.box.valid && it.confidence>=20 &&
            it.box.top>h/4 && it.box.bottom<h*96/100 && inLane(it.box,dir,w) &&
            it.box.bottom-it.box.top in 5..max(12,h/14)}.sortedBy{(it.box.top+it.box.bottom)/2}
        if(eligible.isEmpty())return emptyList()
        val heights=eligible.map{it.box.bottom-it.box.top}.sorted()
        val tolerance=(heights[heights.size/2]*.46f).toInt().coerceIn(5,15)
        val out=mutableListOf<MutableList<OcrSharedRowSplitterV161.Word>>()
        for(word in eligible){
            val center=(word.box.top+word.box.bottom)/2
            val nearest=out.lastOrNull()
            val central=nearest?.let{item->item.map{(it.box.top+it.box.bottom)/2}.average()}
            if(central!=null&&abs(center-central)<=tolerance)nearest.add(word)
            else out.add(mutableListOf(word))
        }
        return out.map{OcrRow(it)}
    }
    private fun rectFor(selected:List<OcrSharedRowSplitterV161.Word>,w:Int,h:Int):CropRect? {
        if(selected.isEmpty())return null
        val left=(selected.minOf{it.box.left}-2).coerceAtLeast(0)
        val right=(selected.maxOf{it.box.right}+2).coerceAtMost(w)
        val top=(selected.minOf{it.box.top}-2).coerceAtLeast(0)
        val bottom=(selected.maxOf{it.box.bottom}+2).coerceAtMost(h)
        return CropRect(left,top,right,bottom).takeIf{it.valid && right-left>=9 && bottom-top>=7}
    }
    private fun closestRow(rows:List<OcrRow>,box:CropRect):Int? {
        val center=(box.top+box.bottom)/2
        return rows.indices.minByOrNull{abs(rows[it].center-center)}?.takeIf{
            abs(rows[it].center-center)<=max(7,box.bottom-box.top)
        }
    }
    fun inspect(words:List<OcrSharedRowSplitterV161.Word>,expected:Set<String>,
                width:Int,height:Int):Result {
        if(width<600||height<350||words.isEmpty())return Result(emptyMap(),emptyMap())
        val proposals=linkedMapOf<String,List<CropRect>>()
        val reasons=linkedMapOf<String,String>()
        for(dir in listOf('H','V')){
            val nums=expected.filter{it.matches(keyPattern)&&it[0]==dir}
                .map{it.substring(1).toInt()}.sorted()
            if(nums.isEmpty())continue
            val numbered=anchors(dir,words,nums,width,height)
            val rowList=rows(words,width,height,dir)
            val lane=laneRange(dir,width)
            for((i,num) in nums.withIndex()){
                val label="$dir$num"
                val first=numbered[num]
                if(first==null){reasons[label]="V199_NO_INDEPENDENT_PRINTED_START; legacy retained; DRY only";continue}
                val nextNum=nums.getOrNull(i+1)
                val last=nextNum?.let{numbered[it]}
                if(nextNum!=null&&last==null){
                    reasons[label]="V199_NEXT_NUMBER_MISSING:$nextNum; legacy retained; DRY only"
                    continue
                }
                val ownRow=closestRow(rowList,first.box)
                val nextRow=last?.let{closestRow(rowList,it.box)}
                if(ownRow==null || (last!=null&&nextRow==null)){
                    reasons[label]="V199_ANCHOR_ROW_UNRESOLVED; legacy retained; DRY only"
                    continue
                }
                if(nextRow!=null && nextRow<ownRow){
                    reasons[label]="V199_NON_MONOTONIC_START_SEQUENCE; legacy retained; DRY only"
                    continue
                }
                if(nextRow==ownRow && (last?.box?.right ?: -1)>=first.box.left){
                    reasons[label]="V199_INLINE_RTL_ORDER_CONFLICT; legacy retained; DRY only"
                    continue
                }
                val end=nextRow ?: min(rowList.lastIndex,ownRow+4)
                val owned=mutableListOf<CropRect>()
                val gapLimit=max(20,height/24)
                var previousBottom=-1
                for(j in ownRow..end){
                    val row=rowList[j]
                    if(j>ownRow && previousBottom>=0 && row.top-previousBottom>gapLimit)break
                    previousBottom=row.bottom
                    if(nextRow==null && j>ownRow+3)break
                    val minX=if(last!=null && j==nextRow)last.box.right+2 else lane.first
                    val maxX=if(j==ownRow)first.box.right+3 else lane.last
                    if(maxX-minX<8)continue
                    val chosen=row.words.filter{word->
                        val center=(word.box.left+word.box.right)/2
                        center>=minX && center<=maxX
                    }
                    val rect=rectFor(chosen,width,height)
                    if(rect!=null)owned+=rect
                }
                // A complete candidate must visibly include its own printed start.
                val ownX=(first.box.left+first.box.right)/2
                val ownY=(first.box.top+first.box.bottom)/2
                if(owned.isEmpty()||owned.size>5||owned.none{inRect(ownX,ownY,it)}){
                    reasons[label]="V199_INCOMPLETE_OWN_START; legacy retained; DRY only"
                    continue
                }
                proposals[label]=owned
                reasons[label]="V199_SOURCE_ANCHORED_REVIEW_ONLY: independent start=$num, " +
                    "next=${nextNum?:"END_OF_COLUMN"}, inferred=${first.inferred||last?.inferred==true}, " +
                    "pieces=${owned.size}; no Canonical write"
            }
        }
        return Result(proposals,reasons)
    }

    /** Prefer a candidate that actually includes its OWN independent printed start. */
    fun ownsPrintedNumber(label:String,parts:List<CropRect>,
                          words:List<OcrSharedRowSplitterV161.Word>):Boolean {
        if(!label.matches(keyPattern)||parts.isEmpty())return false
        val number=label.drop(1).toInt()
        val first=parts.first()
        return words.any { word ->
            word.box.valid && word.confidence>=60 && printed(word.text)==number &&
                inRect((word.box.left+word.box.right)/2,
                    (word.box.top+word.box.bottom)/2,first)
        }
    }

    /** Check cross-clue ownership AFTER all legacy stages generated their previews. */
    fun conflictingKeys(previews:Map<String,List<CropRect>>,
                        words:List<OcrSharedRowSplitterV161.Word>):Map<String,Set<String>> {
        val map=linkedMapOf<String,MutableSet<String>>()
        val entries=previews.filterKeys{it.matches(keyPattern)}.toList()
        for(i in entries.indices)for(j in i+1 until entries.size){
            val (a,ap)=entries[i]; val (b,bp)=entries[j]
            if(a[0]!=b[0])continue
            val conflicting=ap.any{p->bp.any{q->
                val intersection=common(p,q)
                val small=min(area(p),area(q))
                small>0&&intersection*100>=small*14 &&
                    (intersection*100>=small*55 || words.any{word->
                        word.box.valid && word.confidence>=30 &&
                        inRect((word.box.left+word.box.right)/2,(word.box.top+word.box.bottom)/2,p) &&
                        inRect((word.box.left+word.box.right)/2,(word.box.top+word.box.bottom)/2,q)
                    })
            }}
            if(conflicting){map.getOrPut(a){linkedSetOf()}.add(b)
                map.getOrPut(b){linkedSetOf()}.add(a)}
        }
        return map
    }
}