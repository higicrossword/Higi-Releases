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
        val allEntries=assets.open("higi-fixtures/manifest.tsv").bufferedReader().use { it.readLines() }
            .filter { it.isNotBlank() }.map { it.split('\t') }
        require(allEntries.size in 13..20 && allEntries.all { it.size==3 }) { "Fixture coverage invalid" }
        val requestedDate=InstrumentationRegistry.getArguments().getString("higi.fixture.date").orEmpty().trim()
        val entries=if(requestedDate.isEmpty()) allEntries else listOf(
            allEntries.single { it[0]==requestedDate }
        )
        // Always use internal app storage. External app storage can be unmounted on CI emulators.
        // Export results with adb exec-out run-as (debug-only); no public storage permissions needed.
        val folder=File(context.filesDir,"ocr-cloud-v209")
        // Individual instrumentations share app-private data; do not erase prior fixture results.
        if (requestedDate.isEmpty() && folder.exists()) {
            check(folder.deleteRecursively()) { "Cannot reset cloud output folder: ${folder.absolutePath}" }
        }
        check(folder.isDirectory || folder.mkdirs()) { "Cannot create cloud-only output folder: ${folder.absolutePath}" }
        var ocrRan=0
        var proposedTotal=0
        val manifestFile=File(folder,"manifest.csv")
        if(!manifestFile.exists()) {
            manifestFile.writeText("date,source_sha256,grid,expected,proposed,ocr_lines,verified,review,repair_before,status,reason,zip\n",StandardCharsets.UTF_8)
        }
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
            val recordStage:(String)->Unit = { stage ->
                val line="date=$date stage=$stage epoch_ms=${System.currentTimeMillis()}"
                File(folder,"progress.log").appendText(line+"\n",StandardCharsets.UTF_8)
                android.util.Log.i("HIGI_CLOUD_OCR",line)
            }
            recordStage("START")
            try {
                require(file.matches(Regex("[0-9]{6}\\.jpg")))
                val image=assets.open("higi-fixtures/$file").use { BitmapFactory.decodeStream(it) }
                    ?:error("Bitmap decode failed")
                bitmap=image
                check(image.width>500 && image.height>350) { "Unexpected source dimensions" }
                recordStage("IMAGE_DECODED")
                val found=GridDetector.locate(image)
                recordStage("GRID_DETECTION_DONE")
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
                        recordStage("OCR_START")
                        val result=LocalOcrCropPass.run(context,image,crossword,corners,
                            refineSharedRows=true,layoutSeriesId=OcrSeriesProfilesV197.WEEKLY.id)
                        recordStage("OCR_DONE")
                        // WIP diagnostics. Observe the SAME local Android OCR words already generated;
                        // no second OCR engine call, no new proposals, and no persisted clue changes.
                        val expectedWires=(
                            crossword.startNumbers(Direction.HORIZONTAL).map{"H"+it}+
                            crossword.startNumbers(Direction.VERTICAL).map{"V"+it}
                        ).toSet()
                        val measuredGridLeft=found.bounds.left.toInt()
                        val sourceAnchors=OcrWeeklySourceAnchorsV199.inspect(
                            result.geometryWords,expectedWires,image.width,image.height,measuredGridLeft)
                        // Two exact compiled implementations, same process and OCR words.
                        val benchmark=OcrSourceAnchorPairedBenchmark.run(
                            date,result.geometryWords,expectedWires,
                            image.width,image.height,measuredGridLeft)
                        val benchFile=File(folder,"source-anchor-paired-benchmark.csv")
                        if(!benchFile.exists())benchFile.writeText(
                            "date,samples,warmups,baseline_median_ns,patched_median_ns,"+
                            "baseline_p95_ns,patched_p95_ns,ratio_median,changed_source_keys\n")
                        benchFile.appendText(
                            "$date,${benchmark.samples},${benchmark.warmups},"+
                            "${benchmark.oldMedian},${benchmark.newMedian},"+
                            "${benchmark.oldP95},${benchmark.newP95},"+
                            "${benchmark.ratio},${benchmark.changedKeys}\n")
                        // Physical grid is a hard upper boundary for source word ownership.
                        // Independent V201 clipping remains in place and is NOT weakened.
                        val gridSafe=sourceAnchors.previews.all { (label,parts) ->
                            OcrWeeklyFinalGeometryV201.clipFreshAcross(
                                label,parts,measuredGridLeft,image.width)!=null
                        }
                        check(gridSafe) { "Source OCR included a grid word for $date" }
                        if(date=="11-11-26") {
                            val h11=sourceAnchors.previews["H11"]
                                ?:error("H11 source proposal missing after grid filtering")
                            check(h11.size==1) { "H11 must contain clue-only source row, found ${h11.size}" }
                        }
                        val geometryDump=buildString {
                            append("DATE\t"+date+"\n")
                            append("IMAGE\t"+image.width+"x"+image.height+
                                "\tgridLeft="+measuredGridLeft+"\n")
                            append("WORD_COUNT\t"+result.geometryWords.size+"\n")
                            result.geometryWords.sortedWith(compareBy(
                                {it.box.top},{it.box.left})).forEach { word ->
                                val value=word.text.replace('\t',' ').replace('\n',' ').replace('\r',' ')
                                append("WORD\t"+value+"\t"+word.confidence+"\t"+
                                    word.box.left+","+word.box.top+","+
                                    word.box.right+","+word.box.bottom+"\n")
                            }
                            for(label in expectedWires.sorted()){
                                val original=sourceAnchors.previews[label].orEmpty()
                                val limited=OcrWeeklyFinalGeometryV201.clipFreshAcross(
                                    label,original,measuredGridLeft,image.width)
                                append("SOURCE\t"+label+"\tparts="+original.size+
                                    "\tclipped="+(limited?.size ?: -1)+
                                    "\tstrongOwn="+OcrWeeklySourceAnchorsV199.ownsPrintedNumber(
                                        label,original,result.geometryWords)+
                                    "\treason="+sourceAnchors.reasons[label].orEmpty()+"\n")
                                original.forEachIndexed { index,part ->
                                    append("PART\t"+label+"\t"+(index+1)+"\t"+
                                        part.left+","+part.top+","+part.right+","+part.bottom+"\n")
                                }
                            }
                            result.previewReasons.forEach{(key,why)->
                                val label=(if(key.direction==Direction.HORIZONTAL)"H" else "V")+key.number
                                append("FINAL\t"+label+"\t"+
                                    why.replace('\t',' ').replace('\n',' ')+"\n")
                            }
                        }
                        File(folder,"geometry-"+date+".tsv").writeText(
                            geometryDump,StandardCharsets.UTF_8)
                        lines=result.ocrLineCount
                        val candidates=linkedMapOf<ClueEditorModel.Key,ClueGeometry>()
                        candidates.putAll(result.trusted)
                        result.previewOnly.forEach { (k,g)->candidates.putIfAbsent(k,g) }
                        proposed=candidates.size
                        // Read-only WIP: a weak terminal number (3) is not a start anchor,
                        // but its bounded source pixels belong to the prior clue.
                        val weakTerminal=Regex("""^\([1-9][0-9]?(?:,[1-9][0-9]?){0,2}\)[;:,.]?$""")
                        val weakLengthWords=result.geometryWords.filter{
                            it.confidence in 15..19 && weakTerminal.matches(it.text)
                        }
                        val terminalTargets=mapOf("11-11-26" to "H5",
                            "02-11-26" to "V1", "21-10-26" to "V1")
                        val target=terminalTargets[date]
                        check(weakLengthWords.size==(if(target==null) 0 else 1)){
                            "Unexpected low-confidence length words on $date: $weakLengthWords"
                        }
                        if(target!=null){
                            val marker=weakLengthWords.single()
                            val x=(marker.box.left+marker.box.right)/2
                            val y=(marker.box.top+marker.box.bottom)/2
                            val anchored=sourceAnchors.previews[target]
                                ?:error("Missing independent anchor for $date $target")
                            check(anchored.any{x>=it.left && x<it.right && y>=it.top && y<it.bottom}){
                                "SOURCE crop omits terminal for $date $target: "+marker.text
                            }
                            val final=candidates.entries.singleOrNull{(k,_)->
                                (if(k.direction==Direction.HORIZONTAL)"H" else "V")+k.number==target
                            }?.value ?:error("Missing final candidate for $date $target")
                            val fx=x.toFloat()/image.width
                            val fy=y.toFloat()/image.height
                            check(final.lines.any{fx>=it.left && fx<it.right &&
                                fy>=it.top && fy<it.bottom}){
                                "FINAL crop omits terminal for $date $target: "+marker.text
                            }
                        }
                        // Compare against the last SHA-verified WIP emulator fixture run.
                        // These are review-only candidate counts, NOT approved crops.
                        val baseline=mapOf(
                            "11-11-26" to 16, "09-11-26" to 16, "04-11-26" to 16,
                            "02-11-26" to 16, "28-10-26" to 16, "26-10-26" to 16,
                            "21-10-26" to 16, "19-10-26" to 16, "14-10-26" to 14,
                            "12-10-26" to 16, "07-10-26" to 15, "05-10-26" to 16,
                            "30-09-26" to 16, "23-09-26" to 16, "16-09-26" to 16,
                            "14-09-26" to 15, "09-09-26" to 14, "07-09-26" to 16,
                            "02-09-26" to 16
                        )
                        check(proposed>=baseline.getValue(date)) {
                            "Candidate regression on $date: $proposed before=${baseline.getValue(date)}"
                        }
                        val missingRecovery=when(date){
                            "14-10-26" -> setOf("H1","V1")
                            "07-10-26" -> setOf("V3")
                            "14-09-26" -> setOf("V2")
                            "09-09-26" -> setOf("V10","V12")
                            else -> emptySet<String>()
                        }
                        check(missingRecovery.all { sourceAnchors.previews.containsKey(it) }) {
                            "Still missing independently anchored OCR clues on $date: " +
                                missingRecovery.filterNot{sourceAnchors.previews.containsKey(it)}
                        }
                        if(missingRecovery.isNotEmpty())
                            check(proposed==16) { "Incomplete 16/16 recovery on $date: $proposed" }
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
                        recordStage("EXPORT_START")
                        val z=AdminOcrBatchExportV206.saveBatchToCache(context,image,crops,
                            "Dekel $date",UUID.randomUUID().toString(),
                            AdminOcrBatchExportV206.BatchDetails(
                                candidateGrids,result.repairBefore.mapValues{(_,g)->g.lines},diagnostics)
                        ).getOrThrow()
                        zipName="${date.replace("-", "")}.zip"
                        z.copyTo(File(folder,zipName),overwrite=true)
                        recordStage("EXPORT_DONE")
                        state=if(proposed==16)"PROPOSED_16_REVIEW_ONLY" else "PARTIAL_REVIEW_ONLY"
                    }
                }
            }catch(t:Throwable){
                state="ERROR"
                reason=t.javaClass.simpleName+":"+t.message.orEmpty().take(110)
            }finally { bitmap?.recycle() }
            val safe=reason.replace(',',';').replace('\n',' ').replace('\r',' ')
            manifestFile.appendText("$date,$sourceSha,$gridLabel,$expected,$proposed,$lines,$verified,$review,$repaired,$state,$safe,$zipName\n",StandardCharsets.UTF_8)
            recordStage("END_$state")
            if(requestedDate.isNotEmpty()) assertTrue("Fixture $date threw: $reason",state!="ERROR")
        }
        File(folder,"readme.txt").writeText(
            "Higi cloud OCR replay on Android emulator. Identical in-app OCR engine, DRY only.\n"+
            "Visual correctness NOT automatically assessed. No Canonical or Firebase writes.\n"+
            "Expected 16 clue definitions per scanned 9x9 puzzle.\n",StandardCharsets.UTF_8)
        if(requestedDate.isEmpty()) {
            assertTrue("OCR engine did not produce recognized lines",ocrRan>=1)
            assertTrue("No crop proposals emitted",proposedTotal>=1)
        }
    }
}


// WIP source-anchor benchmark only. Baseline is frozen BEFORE terminal-confidence fix,
// with every earlier grid/number correction shared between both exact code copies.
// Same Android process, identical recognized words, AB/BA alternation after warmup.
// Timing excludes grid detection, OCR, clue export, Firebase, AI and all file writes.
private object OcrSourceAnchorPairedBenchmark {
    data class Timings(
        val samples:Int,val warmups:Int,val oldMedian:Long,val newMedian:Long,
        val oldP95:Long,val newP95:Long,val ratio:Double,val changedKeys:String)
    private fun pct(a:List<Long>,p:Int):Long {
        check(a.isNotEmpty())
        val sorted=a.sorted()
        return sorted[((sorted.size-1)*p/100).coerceIn(0,sorted.lastIndex)]
    }
    fun run(date:String,words:List<OcrSharedRowSplitterV161.Word>,
            expected:Set<String>,w:Int,h:Int,gridLeft:Int):Timings {
        val before=OcrWeeklySourceAnchorsV199Baseline.inspect(words,expected,w,h,gridLeft)
        val after=OcrWeeklySourceAnchorsV199.inspect(words,expected,w,h,gridLeft)
        val differences=(before.previews.keys+after.previews.keys)
            .filter{before.previews[it]!=after.previews[it]}.toSortedSet()
        val allowed=when(date){
            "11-11-26" -> setOf("H5")
            "02-11-26", "21-10-26" -> setOf("V1")
            else -> emptySet()
        }
        check(differences==allowed){
            "Source-anchor A/B changed unexpected clues on $date: $differences (expected $allowed)"
        }
        var consume=0L
        fun oldCall():Long {
            val start=System.nanoTime()
            val actual=OcrWeeklySourceAnchorsV199Baseline.inspect(words,expected,w,h,gridLeft)
            val elapsed=System.nanoTime()-start
            consume+=actual.previews.size
            return elapsed
        }
        fun newCall():Long {
            val start=System.nanoTime()
            val actual=OcrWeeklySourceAnchorsV199.inspect(words,expected,w,h,gridLeft)
            val elapsed=System.nanoTime()-start
            consume+=actual.previews.size
            return elapsed
        }
        val warmups=10
        repeat(warmups){i->
            if(i%2==0){oldCall();newCall()}else{newCall();oldCall()}
        }
        val oldTimes=mutableListOf<Long>()
        val newTimes=mutableListOf<Long>()
        val samples=30
        repeat(samples){i->
            if(i%2==0){
                oldTimes+=oldCall();newTimes+=newCall()
            }else{
                newTimes+=newCall();oldTimes+=oldCall()
            }
        }
        check(consume>0 && oldTimes.all{it>0} && newTimes.all{it>0})
        val oldMedian=pct(oldTimes,50)
        val newMedian=pct(newTimes,50)
        return Timings(samples,warmups,oldMedian,newMedian,
            pct(oldTimes,95),pct(newTimes,95),
            newMedian.toDouble()/oldMedian,differences.joinToString("|"))
    }
}

