from pathlib import Path
import sys
root=Path(sys.argv[1])
pkg=root/'app/src/main/java/com/example/hebrewcrossword'
def edit(name,old,new):
 p=pkg/name
 s=p.read_text()
 if s.count(old)!=1: raise RuntimeError(name+' missing/duplicated anchor: '+old[:100])
 p.write_text(s.replace(old,new,1))
edit('AdminPuzzleMenu.kt','Action(9,"יצירת חיתוכי OCR מחדש (בדיקת מנהל)")\n    )','Action(9,"יצירת חיתוכי OCR מחדש (בדיקת מנהל)")\n    ) + (if(BuildConfig.HIGI_DRY_BUILD) listOf(Action(10,"פרסם לקנוני (מנהל DRY)")) else emptyList())')
edit('CanonicalSourceImageStorage.kt','        bitmap:Bitmap,\n        callback:(Result<Uploaded>)->Unit\n    ) {\n        if(BuildConfig.HIGI_DRY_BUILD) {','        bitmap:Bitmap,\n        explicitDryAdminPublish:Boolean=false,\n        callback:(Result<Uploaded>)->Unit\n    ) {\n        if(BuildConfig.HIGI_DRY_BUILD && !explicitDryAdminPublish) {')
edit('CanonicalPuzzleCloud.kt','        previousSourceImageUrl:String = ""\n    ){','        previousSourceImageUrl:String = "",\n        explicitDryAdminPublish:Boolean = false\n    ){')
edit('CanonicalPuzzleCloud.kt','        if(BuildConfig.HIGI_DRY_BUILD){\n            callback(Result.failure(IllegalStateException("גרסת DRY אינה מפרסמת פענוחים למאגר הקנוני")))','        if(BuildConfig.HIGI_DRY_BUILD && (!explicitDryAdminPublish || !allowSourceReplacement ||\n            !CanonicalSourceImageStorage.isManagedUrl(sourceImageUrl))){\n            callback(Result.failure(IllegalStateException("גרסת DRY אינה מפרסמת פענוחים למאגר הקנוני")))')
edit('CanonicalPuzzleCloud.kt','                if(allowSourceReplacement){\n                    callback(Result.failure(IllegalStateException("לא נמצאה רשומת קנוני קיימת להחלפת התמונה. לא נוצר תשבץ נוסף")))','                if(allowSourceReplacement && !explicitDryAdminPublish){\n                    callback(Result.failure(IllegalStateException("לא נמצאה רשומת קנוני קיימת להחלפת התמונה. לא נוצר תשבץ נוסף")))')
edit('RecentCrosswordsActivity.kt','AdminPuzzleMenu.actions.forEachIndexed{index,action->menu.add(0,action.id,index,action.title)}','AdminPuzzleMenu.actions.filter{it.id!=10}.forEachIndexed{index,action->menu.add(0,action.id,index,action.title)}')
edit('RecentCrosswordsActivity.kt','    private var adminAiTestRunning=false','    private var adminAiTestRunning=false\n    private var canonicalPublishRunning=false')
edit('RecentCrosswordsActivity.kt','            9->openAdminOcrRecrop(target.raw,target.effective)\n            7,8->{','            9->openAdminOcrRecrop(target.raw,target.effective)\n            10->confirmSavedDryCanonicalPublication(target)\n            7,8->{')
marker='    /** Existing saved-puzzle runner redetects the grid, preserves progress, and\n'
method="""
    /** Administrator's explicit DRY exception; never reached from automatic import. */
    private fun confirmSavedDryCanonicalPublication(target:SavedAdminTarget){
        if(!BuildConfig.HIGI_DRY_BUILD || !moderationState.admin || !adminMode ||
            canonicalPublishRunning || !target.remoteVerified || target.storedKey.isNullOrBlank()){
            toastAdmin("לא ניתן לפרסם ללא הרשאת מנהל ומקור מאומת");return
        }
        val id=target.entry.id
        val record=library.load(id)
        val issue=canonicalIndex.issueKey(id)
        val oldImage=canonicalIndex.sourceImageUrl(id)
        val thread=canonicalIndex.sourceThreadUrl(id)
        val source=library.sourceFiles(id).firstOrNull{it.isFile && it.length()>0L}
        if(record==null || record.id!=id || issue!=target.storedKey ||
            oldImage.isBlank() || !oldImage.startsWith("https://") ||
            thread.isBlank() || !thread.startsWith("https://") ||
            source==null || !CanonicalPuzzleCloud.isAdminPublishableRecord(record)){
            toastAdmin("התשבץ אינו קשור למקור מאומת או שחסרה תמונה שמורה");return
        }
        val cw=record.crossword
        val expected=cw.startNumbers(Direction.HORIZONTAL).size+
            cw.startNumbers(Direction.VERTICAL).size
        val found=cw.clues.map{it.number to it.direction}.toSet().size
        if(expected<=0 || found!=expected ||
            cw.clues.any{it.text.isBlank() || GalleryRecoveryPolicy.isPlaceholder(it.text)}){
            toastAdmin("יש לאמת את כל ההגדרות לפני הפרסום");return
        }
        AlertDialog.Builder(this).setTitle("פרסם לקנוני — מנהל DRY")
            .setMessage("תשבץ: "+record.title+"\\nהגדרות: "+found+"/"+expected+
                "\\n\\nאשר שכל האותיות בתמונה ובהגדרות תואמות למקור. " +
                "תמונות שעובדו ב-AI עלולות לשנות אותיות. " +
                "הפרסום יעדכן את הרשומה המשותפת, ללא קריאת AI נוספת. " +
                "חיתוכי OCR לא יפורסמו אוטומטית.")
            .setNegativeButton("ביטול",null)
            .setPositiveButton("בדקתי — פרסם"){_,_->
                if(canonicalPublishRunning)return@setPositiveButton
                canonicalPublishRunning=true
                progress.visibility=View.VISIBLE
                message.text="מעלה תמונת מקור..."
                executor.execute{
                    val bitmap=runCatching{
                        android.graphics.BitmapFactory.decodeFile(source.absolutePath)
                    }.getOrNull()
                    if(bitmap==null){
                        runOnUiThread{
                            canonicalPublishRunning=false
                            if(!isDestroyed){
                                progress.visibility=View.INVISIBLE
                                toastAdmin("תמונת המקור אינה ניתנת לקריאה")
                            }
                        }
                        return@execute
                    }
                    CanonicalSourceImageStorage.upload(applicationContext,issue,bitmap,
                        explicitDryAdminPublish=true){ upload->
                        bitmap.recycle()
                        upload.onFailure{ error->
                            runOnUiThread{
                                canonicalPublishRunning=false
                                if(!isDestroyed){
                                    progress.visibility=View.INVISIBLE
                                    toastAdmin("העלאת התמונה נכשלה: "+error.message.orEmpty().take(100))
                                }
                            }
                        }.onSuccess{ stored->
                            val fresh=library.load(id)
                            val unchanged=fresh!=null && fresh.id==record.id &&
                                AnswerChecking.signature(fresh.crossword)==AnswerChecking.signature(cw) &&
                                fresh.crossword.clues.map{it.text}==cw.clues.map{it.text} &&
                                canonicalIndex.issueKey(id)==issue
                            if(!unchanged){
                                runOnUiThread{
                                    canonicalPublishRunning=false
                                    if(!isDestroyed){
                                        progress.visibility=View.INVISIBLE
                                        toastAdmin("התשבץ השתנה בזמן ההעלאה — לא פורסם")
                                    }
                                }
                            }else{
                                runOnUiThread{if(!isDestroyed)message.text="מעדכן Canonical..."}
                                canonicalCloud.refreshDecodedForAdmin(
                                    issue,CrosswordCatalog.issueKeyFromSourceKey(issue),
                                    thread,stored.url,record,
                                    emptyMap(),emptyMap(),"",
                                    callback={ published->runOnUiThread{
                                        canonicalPublishRunning=false
                                        if(!isDestroyed){
                                            progress.visibility=View.INVISIBLE
                                            published.onSuccess{ cached->
                                                canonicalIndex.bind(id,cached.issueKey,cached.revision,
                                                    cached.sourceImageUrl.ifBlank{stored.url},
                                                    cached.sourceThreadUrl.ifBlank{thread})
                                                getSharedPreferences("higi_local_review",MODE_PRIVATE).edit()
                                                    .remove(id).remove("source-upload-pending:"+id).apply()
                                                DebugLog.i("ADMIN_DRY_CANONICAL","committed revision="+cached.revision)
                                                AlertDialog.Builder(this).setTitle("פורסם לקנוני")
                                                    .setMessage("תמונת המקור וההגדרות פורסמו. עדכון: "+cached.revision)
                                                    .setPositiveButton("סגור"){_,_->finish()}.show()
                                            }.onFailure{ error->
                                                DebugLog.w("ADMIN_DRY_CANONICAL",
                                                    "publish failed: "+DebugLog.sanitize(error.message.orEmpty()))
                                                toastAdmin("התמונה עלתה, אך הקנוני לא שונה: "+
                                                    error.message.orEmpty().take(90))
                                            }
                                        }
                                    }},
                                    allowSourceReplacement=true,
                                    previousSourceImageUrl=oldImage,
                                    explicitDryAdminPublish=true)
                            }
                        }
                    }
                }
            }.show()
    }

"""
p=pkg/'RecentCrosswordsActivity.kt'
s=p.read_text()
assert s.count(marker)==1
p.write_text(s.replace(marker,method+marker))
p=root/'app/build.gradle.kts'
s=p.read_text()
assert s.count('versionCode = 352')==1 and s.count('versionName = "0.15.202"')==1
p.write_text(s.replace('versionCode = 352','versionCode = 353').replace('versionName = "0.15.202"','versionName = "0.15.203"'))
assert 'DRY local-only; upload and canonical publication blocked' in (pkg/'MainActivity.kt').read_text()
assert 'בגרסת DRY השמירה הקנונית חסומה' in (pkg/'CanonicalPuzzleCloud.kt').read_text()
assert 'confirmSavedDryCanonicalPublication(target)' in (pkg/'RecentCrosswordsActivity.kt').read_text()
print('v203 manual dry publish path staged, legacy DRY gates retained')
