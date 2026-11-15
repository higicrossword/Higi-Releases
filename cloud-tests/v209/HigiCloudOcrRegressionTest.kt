package com.example.hebrewcrossword

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.PointF
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.charset.StandardCharsets
import java.util.UUID

/** Runs the EXACT application OCR pipeline on real verified source JPEGs.
 * Offline: no login, Firebase, Canonical, network, AI or approval.
 * Fixture bytes are injected into androidTest assets by the CI workflow.
 */
@RunWith(AndroidJUnit4::class)
class HigiCloudOcrRegressionTest {
    @Test fun replayVerifiedNewspaperFixtures() {
        check(BuildConfig.HIGI_DRY_BUILD) { "Never run OCR QA under a normal build" }
        val instrument=InstrumentationRegistry.getInstrumentation()
        val context=instrument.targetContext
        val assets=instrument.context.assets
        val entries=assets.open("higi-fixtures/manifest.tsv").bufferedReader().use { it.readLines() }
            .filter { it.isNotBlank() }.map { it.split('\t') }
        require(entries.size in 13..20 && entries.all { it.size==3 }) { "Fixture coverage invalid" }
        val folder=File(context.getExternalFilesDir(null),"ocr-cloud-v209")
        if(folder.exists())folder.deleteRecursively()
        check(folder.mkdirs()) { "Cannot create cloud-only output folder" }
        var ocrRan=0
        var proposedTotal=0
        val manifest=StringBuilder("date,source_sha256,grid,expected,proposed,ocr_lines,verified,review,repair_before,status,reason,zip\n")
        for (entry in entries) {
            val date=entry[0]
            val file=entry[1]
            val sourceSha=entry[2]
            var bitmap:Bitmap?=null
            var zipName=""
            var gridLabel=""
            var expected=0
            var proposed=0
            var lines=0
            var verified=0
            var review=0
            var repaired=0
            var state="FAILED"
            var reason=""
            try {
                require(file.matches(Regex("[0-9]{6}\\.jpg")))
                val image=assets.open("higi-fixtures/$file").use { BitmapFactory.decodeStream(it) }
                    ?:error("Bitmap decode failed")
                bitmap=image
                check(image.width>500 && image.height>350) { "Unexpected source dimensions" }
                val found=GridDetector.locate(image)
                if(found==null) {
                    state="GRID_NOT_FOUND"
                } else {
                    val crossword=found.result.crossword
                    val across=crossword.startNumbers(Direction.HORIZONTAL).size
                    val down=crossword.startNumbers(Direction.VERTICAL).size
                    gridLabel="${crossword.rows}x${crossword.cols}"
                    expected=across+down
                    if(crossword.rows!=9 || crossword.cols!=9 || across!=8 || down!=8) {
                        state="GRID_WRONG_EXPECTED_16"
                        reason="across=$across down=$down"
                    } else {
                        val b=found.bounds
                        val corners=listOf(PointF(b.left,b.top),PointF(b.right,b.top),
                            PointF(b.right,b.bottom),PointF(b.left,b.bottom))
                        val result=LocalOcrCropPass.run(context,image,crossword,corners,
                            refineSharedRows=true,layoutSeriesId=OcrSeriesProfilesV197.WEEKLY.id)
                        lines=result.ocrLineCount
                        val candidates=linkedMapOf<ClueEditorModel.Key,ClueGeometry>()
                        candidates.putAll(result.trusted)
                        result.previewOnly.forEach { (k,g)->candidates.putIfAbsent(k,g) }
                        proposed=candidates.size
                        verified=result.trusted.size
                        review=result.previewOnly.size
                        repaired=result.repairBefore.size
                        proposedTotal+=proposed
                        if(result.attempted && lines>0)ocrRan++
                        val previewSet=result.previewOnly.keys
                        val crops=candidates.map{(k,g)->AdminOcrBatchExportV206.Crop(
                            k,g.lines,k in previewSet)}
                        val candidateGrids=AdminOcrGridCandidatesV208.collect(image)
                        val diagnostics=buildString {
                            append("cloud_ocr=true\n")
                            append("read_only=true\n")
                            append("date=$date\n")
                            append("grid_variant=${found.variant}\n")
                            append("ocr_lines=$lines\n")
                            result.previewReasons.toSortedMap(compareBy<ClueEditorModel.Key>({it.direction.name},{it.number}))
                                .forEach{(k,v)-> append("${k.direction}:${k.number}=$v\n")}
                        }
                        val z=AdminOcrBatchExportV206.saveBatchToCache(context,image,crops,
                            "Dekel $date",UUID.randomUUID().toString(),
                            AdminOcrBatchExportV206.BatchDetails(
                                candidateGrids,result.repairBefore.mapValues{(_,g)->g.lines},diagnostics)
                        ).getOrThrow()
                        zipName="${date.replace('-','')}.zip"
                        z.copyTo(File(folder,zipName),overwrite=true)
                        state=if(proposed==16)"PROPOSED_16_REVIEW_ONLY" else "PARTIAL_REVIEW_ONLY"
                    }
                }
            }catch(t:Throwable){
                state="ERROR"
                reason=t.javaClass.simpleName+":"+t.message.orEmpty().take(110)
            }finally { bitmap?.recycle() }
            val safe=reason.replace(',',';').replace('\n',' ').replace('\r',' ')
            manifest.append("$date,$sourceSha,$gridLabel,$expected,$proposed,$lines,$verified,$review,$repaired,$state,$safe,$zipName\n")
            android.util.Log.i("HIGI_CLOUD_OCR", "$date $state expected=$expected proposed=$proposed lines=$lines")
        }
        File(folder,"manifest.csv").writeText(manifest.toString(),StandardCharsets.UTF_8)
        File(folder,"readme.txt").writeText(
            "Higi cloud OCR replay on Android emulator. Identical in-app OCR engine, DRY only.\n"+
            "Visual correctness NOT automatically assessed. No Canonical or Firebase writes.\n"+
            "Expected 16 clue definitions per scanned 9x9 puzzle.\n",StandardCharsets.UTF_8)
        assertTrue("OCR engine did not produce recognized lines",ocrRan>=1)
        assertTrue("No crop proposals emitted",proposedTotal>=1)
    }
}
