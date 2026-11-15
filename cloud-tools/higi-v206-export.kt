package com.example.hebrewcrossword

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.BufferedOutputStream
import java.nio.charset.StandardCharsets
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max

/** Read-only export for administrator DRY OCR preview. No OCR rerun and no cloud writes. */
internal object AdminOcrBatchExportV206 {
    data class Crop(val key:ClueEditorModel.Key,val pieces:List<BoxF>,val reviewOnly:Boolean)

    private fun tag(key:ClueEditorModel.Key):String =
        "${if(key.direction==Direction.HORIZONTAL)"H" else "V"}${key.number.toString().padStart(2,'0')}"

    private fun pixels(rect:BoxF,w:Int,h:Int):Rect? {
        if(!rect.left.isFinite() || !rect.top.isFinite() ||
            !rect.right.isFinite() || !rect.bottom.isFinite())return null
        if(rect.left < 0f || rect.top < 0f || rect.right > 1f || rect.bottom > 1f ||
            rect.right <= rect.left || rect.bottom <= rect.top)return null
        val l=floor(rect.left*w).toInt().coerceIn(0,w-1)
        val t=floor(rect.top*h).toInt().coerceIn(0,h-1)
        val r=ceil(rect.right*w).toInt().coerceIn(l+1,w)
        val b=ceil(rect.bottom*h).toInt().coerceIn(t+1,h)
        return Rect(l,t,r,b)
    }

    private fun ZipOutputStream.textEntry(name:String,value:String){
        putNextEntry(ZipEntry(name))
        write(value.toByteArray(StandardCharsets.UTF_8))
        closeEntry()
    }

    private fun ZipOutputStream.pngEntry(name:String,bitmap:Bitmap){
        putNextEntry(ZipEntry(name))
        check(bitmap.compress(Bitmap.CompressFormat.PNG,100,this)) {"PNG encoding failed for $name"}
        closeEntry()
    }

    private fun overview(source:Bitmap,crops:List<Crop>):Bitmap {
        val target=Bitmap.createBitmap(source.width,source.height,Bitmap.Config.ARGB_8888)
        val canvas=Canvas(target)
        canvas.drawBitmap(source,0f,0f,Paint(Paint.FILTER_BITMAP_FLAG))
        val line=Paint(Paint.ANTI_ALIAS_FLAG).apply{style=Paint.Style.STROKE;strokeWidth=max(2f,source.width/580f)}
        val label=Paint(Paint.ANTI_ALIAS_FLAG).apply{color=Color.WHITE;textSize=max(14f,source.width/85f);isFakeBoldText=true}
        val plate=Paint(Paint.ANTI_ALIAS_FLAG).apply{style=Paint.Style.FILL}
        for(crop in crops){
            val tint=if(crop.reviewOnly)Color.rgb(215,105,20) else Color.rgb(30,130,55)
            line.color=tint;plate.color=tint
            crop.pieces.forEachIndexed { index, piece ->
                val px=pixels(piece,source.width,source.height)?:return@forEachIndexed
                val box=RectF(px)
                canvas.drawRect(box,line)
                val caption="${tag(crop.key)}.${index+1}"
                val tw=label.measureText(caption)
                val top=(box.top-label.textSize-4f).coerceAtLeast(0f)
                val x=box.right.coerceAtMost(source.width-tw-10f).coerceAtLeast(0f)
                canvas.drawRect(x,top,x+tw+8f,top+label.textSize+6f,plate)
                canvas.drawText(caption,x+4f,top+label.textSize,label)
            }
        }
        return target
    }

    /** Full source-pixel segments stitched vertically without changing their content. */
    private fun combined(source:Bitmap,rects:List<Rect>):Bitmap {
        val margin=8
        val maxWidth=rects.maxOf{it.width()}
        val height=rects.sumOf{it.height()}+margin*(rects.size+1)
        require(maxWidth>0 && height>0 && maxWidth<=source.width && height<=source.height*8)
        val result=Bitmap.createBitmap(maxWidth+margin*2,height,Bitmap.Config.ARGB_8888)
        val canvas=Canvas(result)
        canvas.drawColor(Color.WHITE)
        val draw=Paint(Paint.FILTER_BITMAP_FLAG)
        var y=margin
        for(rect in rects){
            val dest=Rect(margin,y,margin+rect.width(),y+rect.height())
            canvas.drawBitmap(source,rect,dest,draw)
            y+=rect.height()+margin
        }
        return result
    }

    fun saveToDownloads(context:Context,source:Bitmap,crops:List<Crop>,title:String):Result<String> = runCatching {
        require(BuildConfig.HIGI_DRY_BUILD) {"DRY build required"}
        require(!source.isRecycled && crops.isNotEmpty() && crops.size<=150) {"Invalid crop export"}
        require(Build.VERSION.SDK_INT>=Build.VERSION_CODES.Q) {"Android 10 or later required for Downloads"}
        val stamp=SimpleDateFormat("yyyyMMdd_HHmmss",Locale.US).format(Date())
        val name="Higi_OCR_Crops_${BuildConfig.VERSION_NAME}_$stamp.zip"
        val resolver=context.contentResolver
        val values=ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME,name)
            put(MediaStore.MediaColumns.MIME_TYPE,"application/zip")
            put(MediaStore.MediaColumns.RELATIVE_PATH,Environment.DIRECTORY_DOWNLOADS)
            put(MediaStore.MediaColumns.IS_PENDING,1)
        }
        val uri=resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,values)
            ?:error("Cannot create ZIP in Downloads")
        try {
            resolver.openOutputStream(uri)?.use { stream ->
                ZipOutputStream(BufferedOutputStream(stream)).use{ zip ->
                    val markup=overview(source,crops)
                    try{zip.pngEntry("overview_all_crops.png",markup)}finally{markup.recycle()}
                    val report=StringBuilder()
                    report.append("Higi ").append(BuildConfig.VERSION_NAME).append(" DRY local crop export\n")
                    report.append("Source: ").append(title.replace('\n',' ')).append("\n")
                    report.append("Crops: ").append(crops.size).append(". Green = geometry candidate, Orange = review-only.\n")
                    report.append("Coordinates normalized to original image. No automatic approval.\n")
                    val csv=StringBuilder("key,status,piece,left,top,right,bottom,file\n")
                    for(crop in crops.sortedWith(compareBy({it.key.direction.name},{it.key.number}))){
                        val base=tag(crop.key)
                        val rectangles=crop.pieces.mapNotNull{pixels(it,source.width,source.height)}
                        if(rectangles.isEmpty()){
                            report.append(base).append(": no valid crop rectangles\n")
                            continue
                        }
                        val status=if(crop.reviewOnly)"REVIEW_ONLY" else "GEOMETRY_CANDIDATE"
                        report.append(base).append(" ").append(status).append(" segments=").append(rectangles.size).append('\n')
                        crop.pieces.forEachIndexed{index,box->
                            val rect=pixels(box,source.width,source.height)?:return@forEachIndexed
                            val pieceName="pieces/${base}_part${(index+1).toString().padStart(2,'0')}.png"
                            val piece=Bitmap.createBitmap(source,rect.left,rect.top,rect.width(),rect.height())
                            try{zip.pngEntry(pieceName,piece)}finally{piece.recycle()}
                            csv.append(base).append(',').append(status).append(',').append(index+1).append(',')
                            csv.append(box.left).append(',').append(box.top).append(',')
                                .append(box.right).append(',').append(box.bottom).append(',')
                                .append(pieceName).append('\n')
                        }
                        val stitched=combined(source,rectangles)
                        try{zip.pngEntry("clues/$base.png",stitched)}finally{stitched.recycle()}
                    }
                    zip.textEntry("crop_coordinates.csv",csv.toString())
                    zip.textEntry("review_notes.txt",report.toString())
                }
            }?:error("Could not open ZIP output")
            val finished=ContentValues().apply{put(MediaStore.MediaColumns.IS_PENDING,0)}
            check(resolver.update(uri,finished,null,null)>0) {"ZIP finalization failed"}
        }catch(e:Exception){resolver.delete(uri,null,null);throw e}
        name
    }
}
