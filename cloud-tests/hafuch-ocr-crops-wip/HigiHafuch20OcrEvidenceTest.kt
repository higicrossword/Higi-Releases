package com.example.hebrewcrossword

import android.graphics.BitmapFactory
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/**
 * READ ONLY: same on-device Tesseract and GridDetector as real Higi.
 * Exactly 20 verified publisher originals. Never exports clue text or source pixels.
 * Writes only 2D OCR box geometry, obscured Hebrew strings and confidence.
 * Never calls Firebase, AI, canonical storage or Higi release packaging.
 */
@RunWith(AndroidJUnit4::class)
class HigiHafuch20OcrEvidenceTest {
    private fun sha(data:ByteArray)=MessageDigest.getInstance("SHA-256")
        .digest(data).joinToString(""){"%02x".format(it.toInt() and 255)}
    @Test fun auditAllTwentyOriginals() {
        check(BuildConfig.HIGI_DRY_BUILD){"Use DRY test only"}
        val ins=InstrumentationRegistry.getInstrumentation()
        val assets=ins.context.assets
        val context=ins.targetContext
        val input=assets.open("hafuch-20/manifest.tsv")
            .bufferedReader().use{it.readLines()}.filter{it.isNotBlank()}
        check(input.size==20){"Expected exactly 20 SHA-pinned historical issues"}
        val dates=linkedSetOf<String>()
        val root=File(context.filesDir,"hafuch-ocr-20")
        check(root.isDirectory || root.mkdirs())
        val overview=File(root,"manifest.tsv")
        overview.writeText("date\tsha256\twidth\theight\tgrid\tgrid_left\tgrid_right\tgrid_top\tgrid_bottom\tocr_lines\tocr_words\tocr_millis\n")
        for(entry in input){
            val args=entry.split('\t')
            check(args.size==3)
            val date=args[0];val originalSha=args[1];val name=args[2]
            check(date.matches(Regex("^2026-[0-9]{2}-[0-9]{2}$")))
            check(name==date+".jpg" && dates.add(date))
            val bytes=assets.open("hafuch-20/"+name).use{it.readBytes()}
            check(sha(bytes)==originalSha){"SHA mismatch for source $date"}
            val image=BitmapFactory.decodeByteArray(bytes,0,bytes.size)
                ?:error("Bitmap decoding error: $date")
            try {
                val bounds=GridDetector.locate(image)?.let{loc->
                    check(loc.result.crossword.rows==13 && loc.result.crossword.cols==13){
                        "Not Hafuch 13x13: $date"
                    }
                    val cross=loc.result.crossword
                    check(cross.startNumbers(Direction.HORIZONTAL).size==14 &&
                          cross.startNumbers(Direction.VERTICAL).size==14){
                        "Not 14+14 starts: $date"
                    }
                    loc.bounds
                }?:error("No source grid found: $date")
                val words=mutableListOf<OcrSharedRowSplitterV161.Word>()
                val before=android.os.SystemClock.elapsedRealtime()
                val lines=LocalHebrewOcrV031(context).use{ it.readFullPageLines(image,
                    wordBoxes=words)}
                val ms=android.os.SystemClock.elapsedRealtime()-before
                check(lines.isNotEmpty() && words.isNotEmpty()){"No local OCR evidence $date"}
                val dir=File(root,date)
                check(dir.isDirectory || dir.mkdirs())
                val wordFile=File(dir,"words.tsv")
                wordFile.writeText("id\tmasked\tconfidence\tleft\ttop\tright\tbottom\n")
                val hebrew=Regex("[\u0590-\u05ff]")
                words.forEachIndexed{i,word->
                    // Remove all Hebrew wording; retain only physical OCR punctuation/numerals.
                    val masked=word.text.replace(hebrew,"H")
                        .replace('\t',' ').replace('\n',' ')
                    val b=word.box
                    wordFile.appendText(listOf(i,masked,word.confidence,
                        b.left,b.top,b.right,b.bottom).joinToString("\t")+"\n")
                }
                val linesFile=File(dir,"lines.tsv")
                linesFile.writeText("id\tconfidence\tleft\ttop\tright\tbottom\theading\n")
                lines.forEach{line->
                    val t=line.text.trim()
                    val heading=when{
                        t.startsWith("מאוזן")||t.startsWith("אופקי")->"H"
                        t.startsWith("מאונך")||t.startsWith("אנכי")->"V"
                        else->""
                    }
                    val b=line.box
                    linesFile.appendText(listOf(line.id,line.confidence,
                        b.left,b.top,b.right,b.bottom,heading).joinToString("\t")+"\n")
                }
                overview.appendText(listOf(date,originalSha,image.width,image.height,
                    "13x13",bounds.left,bounds.right,bounds.top,bounds.bottom,
                    lines.size,words.size,ms).joinToString("\t")+"\n")
                android.util.Log.i("HAFUCH20","SOURCE_SHA_VERIFIED "+date+" OCR_WORDS "+
                    words.size+" OCR_LINES "+lines.size+" GRID "+bounds.left+","+
                    bounds.top+","+bounds.right+","+bounds.bottom+" OCR_MS "+ms)
            } finally { image.recycle() }
        }
        check(dates.size==20)
    }
}
