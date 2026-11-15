#!/usr/bin/env python3
"""Minimal DRY-only administrator UI addition for full source overlay and offline ZIP.
Applies to a fully reconstructed v0.15.205 source tree. No OCR or Canonical edits.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
pkg=root/'app/src/main/java/com/example/hebrewcrossword'
p=pkg/'AdminOcrRecropActivity.kt'
s=p.read_text(encoding='utf-8')
assert 'class AdminOcrRecropActivity' in s
assert s.count('        lowerPanel.addView(editRow)')==1, 'UI edit-row anchor changed'
assert s.count('    private fun confirmCommit() {')==1, 'Commit method anchor changed'
assert s.count('    private fun button(title:String, action:()->Unit):Button=')==1, 'Button method anchor changed'
assert 'previewOnly' in s and 'candidates' in s, 'v205 review-only proposals missing'
assert 'HIGI_DRY_BUILD' in s
assert 'AdminOcrBatchExportV206' not in s, 'already patched'

# Keep controls inside existing lowerScroll, leaving bitmap/viewer dimensions unchanged.
addition='''        if(BuildConfig.HIGI_DRY_BUILD){
            val batchReviewRow=LinearLayout(this).apply { layoutDirection=View.LAYOUT_DIRECTION_RTL }
            batchReviewRow.addView(button("כל החיתוכים על התמונה"){showAllCropsV206()},
                LinearLayout.LayoutParams(0,dp(46),1f))
            batchReviewRow.addView(button("שמור ZIP חיתוכים"){saveCropsZipV206()},
                LinearLayout.LayoutParams(0,dp(46),1f))
            lowerPanel.addView(batchReviewRow)
        }
'''
s=s.replace('        lowerPanel.addView(editRow)', '        lowerPanel.addView(editRow)\n'+addition,1)

methods='''    /** Full-page read-only overlay of ALL current proposed crops, not the selected one.
     * Uses existing inspector and the same in-memory OCR coordinates as single review.
     */
    private fun showAllCropsV206(){
        if(!BuildConfig.HIGI_DRY_BUILD)return
        val b=original
        if(loading || b==null || b.isRecycled){toast("יש להמתין לסיום חיתוכי OCR");return}
        val list=candidates.map{(key,geometry)->asItem(key,geometry)}
        if(list.isEmpty()){toast("אין חיתוכים להצגה");return}
        val sheet=LinearLayout(this).apply{
            orientation=LinearLayout.VERTICAL
            layoutDirection=View.LAYOUT_DIRECTION_RTL
            setPadding(dp(5),dp(5),dp(5),dp(5))
        }
        sheet.addView(TextView(this).apply{
            text="${list.size}/${keys.size} חיתוכים מוצגים (כולל ${previewOnly.size} הצעות לא מאומתות). " +
                "המלבנים ממוספרים H=מאוזן, V=מאונך. גרור או הגדל בשתי אצבעות."
            textSize=13f
            gravity=Gravity.CENTER
        },LinearLayout.LayoutParams(-1,ViewGroup.LayoutParams.WRAP_CONTENT))
        val all=ClueRegionInspectorView(this)
        all.setData(b,list,null)
        sheet.addView(all,LinearLayout.LayoutParams(-1,0,1f))
        val controls=LinearLayout(this).apply{layoutDirection=View.LAYOUT_DIRECTION_LTR}
        controls.addView(button("−"){all.zoomBy(.80f)},LinearLayout.LayoutParams(0,dp(45),1f))
        controls.addView(button("התאם למסך"){all.fitImage()},LinearLayout.LayoutParams(0,dp(45),2f))
        controls.addView(button("+"){all.zoomBy(1.25f)},LinearLayout.LayoutParams(0,dp(45),1f))
        sheet.addView(controls)
        val dialog=android.app.Dialog(this)
        dialog.setContentView(sheet)
        dialog.show()
        dialog.window?.setLayout(ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT)
        dialog.setOnDismissListener{all.setData(null,emptyList(),null)}
    }

    /** Exports EXACT proposed bitmap rectangles, including unverified DRY previews.
     * ZIP generation is offline; it does not modify the source or Canonical.
     */
    private fun saveCropsZipV206(){
        if(!BuildConfig.HIGI_DRY_BUILD)return
        val b=original
        if(loading || saving || b==null || b.isRecycled){toast("יש להמתין לסיום בדיקת OCR");return}
        if(candidates.isEmpty()){toast("אין חיתוכים לייצוא");return}
        val snapshot=runCatching{b.copy(android.graphics.Bitmap.Config.ARGB_8888,false)}.getOrNull()
        if(snapshot==null){toast("לא ניתן להכין עותק בטוח של תמונת המקור");return}
        val crops=candidates.map{(key,geometry)->
            AdminOcrBatchExportV206.Crop(key,geometry.lines.ifEmpty{listOf(geometry.union)},
                key in previewOnly)
        }
        val title=intent.getStringExtra(EXTRA_TITLE).orEmpty()
        toast("מכין ZIP בתיקיית Downloads…")
        executor.execute{
            val outcome=try{
                AdminOcrBatchExportV206.saveToDownloads(applicationContext,snapshot,crops,title)
            }catch(error:Exception){Result.failure(error)}finally{snapshot.recycle()}
            runOnUiThread{
                if(!isDestroyed){
                    outcome.onSuccess{toast("ZIP נשמר בתיקיית Downloads: $it")}
                        .onFailure{toast("שמירת ZIP נכשלה: ${it.message.orEmpty().take(110)}")}
                }
            }
        }
    }

'''
s=s.replace('    private fun confirmCommit() {',methods+'    private fun confirmCommit() {',1)
p.write_text(s,encoding='utf-8')
helper=Path(__file__).with_name('higi-v206-export.kt')
assert helper.is_file()
output=pkg/'AdminOcrBatchExportV206.kt'
assert not output.exists(), 'existing export class'
output.write_text(helper.read_text(encoding='utf-8'),encoding='utf-8')

gradle=root/'app/build.gradle.kts'
g=gradle.read_text(encoding='utf-8')
assert g.count('versionCode = 355')==1 and g.count('versionName = "0.15.205"')==1, 'not v205 base'
gradle.write_text(g.replace('versionCode = 355','versionCode = 356').replace('versionName = "0.15.205"','versionName = "0.15.206"'),encoding='utf-8')
print('PASS v206 UI: two DRY-only controls, existing geometry, offline export; v0.15.206 / 356')
