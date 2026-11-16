package com.example.hebrewcrossword

import android.graphics.BitmapFactory
import android.graphics.PointF
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/** Offline, read-only Android image/OCR smoke for explicitly pinned NON-Yedioth series.
 * No assumptions about grid size, number of clues or Yedioth text columns.
 * No source images or clue text exported; only counters/diagnostics.
 */
@RunWith(AndroidJUnit4::class)
class HigiOtherSeriesOcrSmokeTest {
    @Test fun inspectVerifiedOtherSeries() {
        check(BuildConfig.HIGI_DRY_BUILD){"Must not run under regular build"}
        val instrument=InstrumentationRegistry.getInstrumentation()
        val assets=instrument.context.assets
        val context=instrument.targetContext
        val series=InstrumentationRegistry.getArguments().getString("higi.series.id")
            ?:error("Missing explicit series")
        val lines=assets.open("cross-series/manifest.tsv")
            .bufferedReader().use{it.readLines()}.filter{it.isNotBlank()}
        val fields=lines.singleOrNull{it.substringBefore('\t')==series}?.split('\t')
            ?:error("No pinned asset for "+series)
        check(fields.size==6)
        val id=fields[0];val name=fields[1];val sha=fields[2]
        val date=fields[3];val title=fields[4];val reported=fields[5]
        val expectedId=when(series){
            "HAFUCH_DEKEL"->OcrSeriesProfilesV197.HAFUCH.id
            "MAARIV_ODED_ROZEN"->OcrSeriesProfilesV197.MAARIV.id
            else->error("Unsupported series "+series)
        }
        val profile=OcrSeriesProfilesV197.resolve(title,id+":"+date)
        check(profile.id==expectedId && profile.id!=OcrSeriesProfilesV197.WEEKLY.id){
            "Series routing failed: "+profile.id
        }
        val folder=File(context.filesDir,"ocr-cross-series-wip")
        check(folder.isDirectory||folder.mkdirs())
        val report=File(folder,"summary.tsv")
        if(!report.exists())report.writeText(
            "series\tsha256\timage_w\timage_h\tgrid\tgrid_start_numbers\t"+
            "reported_expected\tocr_lines\ttrusted\treview_only\tunique_proposals\t"+
            "invalid_normalized\tocr_millis\tstatus\terror\n")
        var imageW=0;var imageH=0;var grid="";var count=0;var ocrLines=0
        var trusted=0;var previews=0;var proposals=0;var invalid=0;var ms=0L
        var status="NOT_RUN";var reason=""
        var bitmap:android.graphics.Bitmap?=null
        try {
            val bytes=assets.open("cross-series/"+name).use{it.readBytes()}
            val actual=MessageDigest.getInstance("SHA-256").digest(bytes)
                .joinToString(""){"%02x".format(it.toInt() and 255)}
            check(actual==sha){"Original image SHA mismatch "+series}
            val image=BitmapFactory.decodeByteArray(bytes,0,bytes.size)
                ?:error("IMAGE_DECODE_FAILED")
            bitmap=image
            imageW=image.width;imageH=image.height
            val located=GridDetector.locate(image)?:error("GRID_NOT_FOUND")
            val crossword=located.result.crossword
            grid=crossword.rows.toString()+"x"+crossword.cols.toString()
            count=crossword.startNumbers(Direction.HORIZONTAL).size+
                  crossword.startNumbers(Direction.VERTICAL).size
            check(count>0){"EMPTY_GRID"}
            val b=located.bounds
            val corners=listOf(PointF(b.left,b.top),PointF(b.right,b.top),
                PointF(b.right,b.bottom),PointF(b.left,b.bottom))
            val start=System.nanoTime()
            val outcome=LocalOcrCropPass.run(context,image,crossword,corners,
                refineSharedRows=true,layoutSeriesId=profile.id)
            ms=(System.nanoTime()-start)/1000000
            ocrLines=outcome.ocrLineCount
            check(outcome.attempted&&ocrLines>0){"OCR_NOT_EXECUTED"}
            trusted=outcome.trusted.size;previews=outcome.previewOnly.size
            val candidates=linkedMapOf<ClueEditorModel.Key,ClueGeometry>()
            candidates.putAll(outcome.trusted)
            outcome.previewOnly.forEach{(k,g)->candidates.putIfAbsent(k,g)}
            proposals=candidates.size
            invalid=candidates.count{(_,g)->g.lines.isEmpty() || g.lines.any{r->
                r.left<0f || r.top<0f || r.right>1f || r.bottom>1f ||
                r.left>=r.right || r.top>=r.bottom
            }}
            status="DIAGNOSTIC_ONLY"
        }catch(t:Throwable){
            status="FAILED_DIAGNOSTIC"
            reason=t.javaClass.simpleName+":"+t.message.orEmpty().take(120)
        }finally{
            bitmap?.recycle()
            report.appendText(listOf(series,sha,imageW,imageH,grid,count,reported,
                ocrLines,trusted,previews,proposals,invalid,ms,status,
                reason.replace('\t',' ').replace('\n',' ')).joinToString("\t")+"\n")
        }
        assertTrue(series+" Android OCR diagnostic failed: "+reason,status=="DIAGNOSTIC_ONLY")
    }
}
