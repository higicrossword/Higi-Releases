package com.example.hebrewcrossword

import android.graphics.Bitmap

/**
 * HAFUCH_DEKEL-only experimental source-pixel guard (androidTest only).
 * Selects a taller single OCR region *before* any OCR call, with no text inference.
 * Source-image horizontal ink bands matching regular clue text can cross the
 * original 97.5% bottom cutoff. Short decorative dotted lines are ignored.
 * Never apply to other series; this is NOT production or an app release.
 */
internal object HafuchBottomInkV1 {
    fun needsSourceBottom(image:Bitmap,measuredGridRight:Float):Boolean {
        val width=image.width;val height=image.height
        val x0=(measuredGridRight+width*.012f).toInt().coerceIn(0,width-2)
        val x1=(width-width*.018f).toInt().coerceIn(x0+1,width)
        val y0=(height*.10f).toInt()
        val sliceWidth=x1-x0
        val sliceHeight=height-y0
        val pixels=IntArray(sliceWidth*sliceHeight)
        image.getPixels(pixels,0,sliceWidth,x0,y0,sliceWidth,sliceHeight)
        val rowInk=IntArray(sliceHeight)
        for(y in 0 until sliceHeight){
            var count=0
            val offset=y*sliceWidth
            for(x in 0 until sliceWidth){
                val pixel=pixels[offset+x]
                val red=(pixel ushr 16) and 255
                val green=(pixel ushr 8) and 255
                val blue=pixel and 255
                val grayscale=(red*299+green*587+blue*114)/1000
                if(grayscale<125)count++
            }
            rowInk[y]=count
        }
        val threshold=maxOf(9.0,sliceWidth*.016)
        val spans=mutableListOf<Pair<Int,Int>>()
        var start=-1
        for(i in rowInk.indices){
            val dark=rowInk[i]>threshold
            if(dark && start<0)start=i
            if(start>=0 && (!dark || i==rowInk.lastIndex)){
                val end=if(dark && i==rowInk.lastIndex)i+1 else i
                if(end-start>=2)spans.add((start+y0) to (end+y0))
                start=-1
            }
        }
        val body=spans.filter{(a,b)->
            a>=(height*.15f).toInt() &&
            b<=(height*.90f).toInt() && b-a>=5
        }.map{it.second-it.first}.sorted()
        if(body.isEmpty())return false
        val bodyHeight=body[body.size/2]
        val cutoff=(height*.975f).toInt()
        return spans.any{(a,b)->b>cutoff &&
            (b-a).toDouble()>=maxOf(8.0,bodyHeight*.6)}
    }
}
