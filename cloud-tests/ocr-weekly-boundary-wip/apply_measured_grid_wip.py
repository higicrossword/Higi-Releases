"""WIP emulator-only overlay: restrict OCR source words to the measured pre-grid lane."""
from pathlib import Path
import sys

root=Path(sys.argv[1])/'app/src/main/java/com/example/hebrewcrossword'

def edit(name,operations):
    p=root/name
    s=p.read_text()
    for old,new in operations:
        assert s.count(old)==1,(name,old[:70],s.count(old))
        s=s.replace(old,new)
    p.write_text(s)

edit('OcrWeeklySourceAnchorsV199.kt',[
('    private fun inLane(r:CropRect,dir:Char,w:Int):Boolean {',
 '''    // A verified physical grid boundary must constrain source OCR words BEFORE row grouping.
    // Invalid/missing grid measurements retain V199 behavior and V201's independent veto.
    private fun measuredSourceRight(x:Int?,w:Int):Int? = x
        ?.takeIf{w>=600 && it in (w*.58f).toInt()..(w*.83f).toInt()}?.minus(2)
    private fun inLane(r:CropRect,dir:Char,w:Int,sourceRight:Int?):Boolean {'''),
("        return if(dir=='H')c in 0.315f..0.675f else c in 0.003f..0.315f",
 "        val relative=if(dir=='H')c in 0.315f..0.675f else c in 0.003f..0.315f\n        return relative && (dir!='H'||sourceRight==null||r.right<=sourceRight)"),
('private fun laneRange(dir:Char,w:Int):IntRange = if(dir==\'H\')',
 "private fun laneRange(dir:Char,w:Int,sourceRight:Int?):IntRange = if(dir=='H')"),
('((.315*w).toInt())..((.675*w).toInt()) else 0..((.315*w).toInt())',
 '((.315*w).toInt())..min((.675*w).toInt(),sourceRight?:w) else 0..((.315*w).toInt())'),
('nums:List<Int>,w:Int,h:Int):Map<Int,Anchor>',
 'nums:List<Int>,w:Int,h:Int,sourceRight:Int?):Map<Int,Anchor>'),
('inLane(it.box,dir,w)}','inLane(it.box,dir,w,sourceRight)}'),
('private fun rows(words:List<OcrSharedRowSplitterV161.Word>,w:Int,h:Int,dir:Char):List<OcrRow>',
 'private fun rows(words:List<OcrSharedRowSplitterV161.Word>,w:Int,h:Int,dir:Char,sourceRight:Int?):List<OcrRow>'),
('inLane(it.box,dir,w) &&','inLane(it.box,dir,w,sourceRight) &&'),
('width:Int,height:Int):Result {','width:Int,height:Int,gridLeftPx:Int?=null):Result {'),
('val proposals=linkedMapOf<String,List<CropRect>>()',
 'val sourceRight=measuredSourceRight(gridLeftPx,width)\n        val proposals=linkedMapOf<String,List<CropRect>>()'),
('anchors(dir,words,nums,width,height)','anchors(dir,words,nums,width,height,sourceRight)'),
('rows(words,width,height,dir)','rows(words,width,height,dir,sourceRight)'),
('laneRange(dir,width)','laneRange(dir,width,sourceRight)'),
('"pieces=${owned.size}; no Canonical write"',
 '"pieces=${owned.size}; sourceGridRight=${if(dir==\'H\')sourceRight else null}; no Canonical write"')
])
edit('HigiLocalOcrCropEngine.kt',[
('''            val independent=OcrWeeklySourceAnchorsV199.inspect(auditWords,expectedWires,w,h)
            val freshKeys=linkedSetOf<String>()''',
 '''            // Source-word ownership must be checked against the measured grid BEFORE row grouping.
            val gridLeftPx=gridPoints.takeIf{it.size==4}?.minOf{it.x}?.roundToInt()
            val independent=OcrWeeklySourceAnchorsV199.inspect(auditWords,expectedWires,w,h,gridLeftPx)
            val freshKeys=linkedSetOf<String>()'''),
('''                // A printed Across word must never pull the proposal into the
                // grid. Use measured source grid points only, never a hardcoded
                // grid position or a similarly numbered clue's old rectangle.
                val gridLeftPx=gridPoints.takeIf{it.size==4}?.minOf{it.x}?.roundToInt()''',
 '''                // Keep V201's original independent grid-boundary veto unchanged.''')
])

# Second WIP-only experiment: OCR numbering ambiguities, no fabricated text.
edit('OcrWeeklySourceAnchorsV199.kt',[
("        for(num in nums){\n            val strong=all.filter{printed(it.text)==num && it.confidence>=60}\n            if(strong.size==1)matches[num]=Anchor(num,strong.single().box,false)\n        }", "        for(num in nums){\n            val strong=all.filter{printed(it.text)==num && it.confidence>=60}\n            if(strong.size==1)matches[num]=Anchor(num,strong.single().box,false)\n        }\n        // OCR may read the final printed 12. as 2.; resolve duplicate strong starts\n        // only when exactly one occurrence fits between neighboring reliable starts.\n        for(num in nums){\n            if(num in matches)continue\n            val duplicates=all.filter{printed(it.text)==num && it.confidence>=60}\n            if(duplicates.size<=1)continue\n            val prior=nums.lastOrNull{it<num && matches.containsKey(it)}?.let{matches[it]}\n            val after=nums.firstOrNull{it>num && matches.containsKey(it)}?.let{matches[it]}\n            if(prior==null && after==null)continue\n            val ordered=duplicates.filter { candidate ->\n                val middle=(candidate.box.top+candidate.box.bottom)/2\n                (prior==null || middle>=prior.box.top-4) &&\n                    (after==null || middle<=after.box.bottom+4)\n            }\n            if(ordered.size==1)matches[num]=Anchor(num,ordered.single().box,true)\n        }"),
("                val weakContext=word.confidence in 20..51 && truncation &&\n                    prior!=null && after!=null &&\n                    middle>prior.box.bottom && middle<after.box.top\n                (bareNumber || truncation) && ordered &&\n                    (word.confidence>=52 || weakContext)", "                val weakContext=word.confidence in 20..51 && truncation &&\n                    prior!=null && after!=null &&\n                    middle>prior.box.bottom && middle<after.box.top\n                // A low-confidence *printed number* can still be unique evidence\n                // when reliable neighboring starts constrain the same text column.\n                val weakPrinted=printed(raw)==num && word.confidence>=20 &&\n                    ((word.confidence>=52 && (prior!=null || after!=null)) ||\n                    (prior!=null && after!=null &&\n                        middle>prior.box.bottom && middle<after.box.top))\n                // OCR sometimes reads printed '1.' as '1,'; never treat commas\n                // as strong automatic anchors, and require a right-edge position.\n                val edge=word.box.right.toFloat()/w >= (if(dir=='H')0.54f else 0.24f)\n                val comma=raw==\"$num,\" && word.confidence>=52 && edge &&\n                    (prior!=null || after!=null)\n                // For a LAST clue (such as V12), there is no following anchor.\n                // A 2 read from 12 is allowed only as unique, low-confidence,\n                // near-margin, short-distance REVIEW-ONLY evidence.\n                val weakLast=word.confidence in 35..51 && truncation &&\n                    prior!=null && after==null &&\n                    middle>prior.box.bottom && middle-prior.box.bottom<=max(60,h/8)\n                (bareNumber || truncation || weakPrinted || comma) && ordered &&\n                    (word.confidence>=52 || weakContext || weakPrinted || comma || weakLast)")
])

print('WIP_OVERLAY_OK two Kotlin production source files, in ephemeral emulator workspace only')
