#!/usr/bin/env python3
"""v0.15.204: source-image-only canonical swap and authoritative original viewer."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
pkg=root/'app/src/main/java/com/example/hebrewcrossword'
def edit(name, old, new):
    path=pkg/name
    source=path.read_text()
    if source.count(old)!=1:
        raise RuntimeError(f"{name}: expected exactly one anchor, found {source.count(old)}: {old[:100]}")
    path.write_text(source.replace(old,new,1))

# Keep every existing caller of SourceImageDialog compatible.
edit('SourceImageDialog.kt',
    'class SourceImageDialog(context: Context, bitmap: Bitmap,\n                         verifiedFocus: BoxF? = null) : Dialog(context, R.style.Theme_HebrewCrossword) {',
    'class SourceImageDialog(context: Context, bitmap: Bitmap,\n                         verifiedFocus: BoxF? = null,\n                         sourceStatus:String = "") : Dialog(context, R.style.Theme_HebrewCrossword) {')
edit('SourceImageDialog.kt',
    '    init {\n        requestWindowFeature(Window.FEATURE_NO_TITLE)',
    '''    private val bar = LinearLayout(context).apply { gravity=Gravity.CENTER }
    private var replacementActionAdded=false
    fun enableCanonicalReplacement(onReplace:()->Unit) {
        if(replacementActionAdded)return
        replacementActionAdded=true
        bar.addView(Button(context).apply {
            text="החלף תמונה קנונית"
            isAllCaps=false
            setOnClickListener { dismiss();onReplace() }
        },LinearLayout.LayoutParams(0,dp(50),1f))
    }
    init {
        requestWindowFeature(Window.FEATURE_NO_TITLE)''')
edit('SourceImageDialog.kt',
    '        root.addView(image, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1f))\n        val bar=LinearLayout(context).apply { gravity=Gravity.CENTER }',
    '''        if(sourceStatus.isNotBlank()){
            root.addView(TextView(context).apply {
                text=sourceStatus;textSize=12.5f;gravity=Gravity.CENTER
                setPadding(8,0,8,8)
            })
        }
        root.addView(image, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1f))''')

# A single-purpose transaction must never call updateDecodedForAdminAtNode:
# that method merges clue text, answers and source geometry as well.
p=pkg/'CanonicalPuzzleCloud.kt'
s=p.read_text()
anchor='    /**\n     * User clue corrections are canonical.'
assert s.count(anchor)==1
newMethod='''    /**
     * Replace ONLY the canonical original image, never grid, clues, answers or progress.
     * Per-image regions and approvals are made invalid rather than carrying old
     * pixel coordinates over to a different scan. This is an explicit admin action.
     */
    fun replaceCanonicalSourceImageOnly(
        issueKey:String,
        physicalNodeKey:String,
        expectedGridSignature:String,
        expectedSourceImageUrl:String,
        replacementUrl:String,
        editorName:String,
        callback:(Result<Long>)->Unit
    ) {
        if(issueKey.isBlank() || physicalNodeKey.isBlank() ||
            expectedGridSignature.isBlank() || expectedSourceImageUrl.isBlank() ||
            !CanonicalSourceImageStorage.isManagedUrl(replacementUrl)){
            callback(Result.failure(IllegalArgumentException("זהות קנונית או תמונת מקור אינה מאומתת")))
            return
        }
        AdminAccess(context).loadRole { role ->
            if(role==AdminAccess.Role.NONE){
                callback(Result.failure(SecurityException("החלפת תמונה קנונית למנהל בלבד")))
                return@loadRole
            }
            authenticated({uid,d ->
                val ref=d.getReference("canonicalPuzzles/"+CanonicalNodeRoute.resolve(issueKey,physicalNodeKey))
                ref.get().addOnSuccessListener { preflight ->
                    if(!preflight.exists() || preflight.child("issueKey").value!=issueKey ||
                        (preflight.child("schema").value as? Number)?.toInt()!=SCHEMA ||
                        (preflight.child("parserSchema").value as? Number)?.toInt()!=PARSER_SCHEMA ||
                        preflight.child("gridSignature").value!=expectedGridSignature ||
                        LocalOcrGeometryAuthority.sourceIdentity(preflight.child("sourceImageUrl").value as? String ?: "")!=
                            LocalOcrGeometryAuthority.sourceIdentity(expectedSourceImageUrl)) {
                        callback(Result.failure(IllegalStateException("התשבץ או תמונתו השתנו; יש לפתוח מחדש")))
                        return@addOnSuccessListener
                    }
                    val snapshot=preflight.value
                    if(snapshot==null){
                        callback(Result.failure(IllegalStateException("לא ניתן לגבות מצב רשומה לצורך העדכון")))
                        return@addOnSuccessListener
                    }
                    var invocation=0
                    var reason="התשבץ השתנה בזמן החלפת התמונה"
                    ref.runTransaction(object:Transaction.Handler {
                        override fun doTransaction(data:MutableData):Transaction.Result {
                            invocation++
                            if(data.value==null){
                                when(CanonicalTransactionCachePolicy.action(invocation,true)){
                                    CanonicalTransactionCachePolicy.NullAction.BOOTSTRAP_PREFETCH->data.value=snapshot
                                    CanonicalTransactionCachePolicy.NullAction.ABORT_AS_DELETED->{
                                        reason="התשבץ נמחק במהלך ההחלפה"
                                        return Transaction.abort()
                                    }
                                }
                            }
                            if(data.child("issueKey").value!=issueKey ||
                                (data.child("schema").value as? Number)?.toInt()!=SCHEMA ||
                                (data.child("parserSchema").value as? Number)?.toInt()!=PARSER_SCHEMA ||
                                data.child("gridSignature").value!=expectedGridSignature ||
                                LocalOcrGeometryAuthority.sourceIdentity(data.child("sourceImageUrl").value as? String ?: "")!=
                                    LocalOcrGeometryAuthority.sourceIdentity(expectedSourceImageUrl)){
                                reason="זהות התשבץ, הרשת או התמונה השתנו"
                                return Transaction.abort()
                            }
                            if(LocalOcrGeometryAuthority.sourceIdentity(replacementUrl)==
                                LocalOcrGeometryAuthority.sourceIdentity(expectedSourceImageUrl)){
                                reason="התמונה החדשה זהה לתמונה הקנונית"
                                return Transaction.abort()
                            }
                            val next=((data.child("revision").value as? Number)?.toLong()?:0L)+1L
                            // These fields belong to pixels of the previous image.
                            // Never silently keep old source rectangles or old approvals.
                            data.child("clueRegions").value=null
                            data.child("clueRegionLines").value=null
                            data.child("clueRegionEvidence").value=null
                            data.child("clueRegionEdits").value=null
                            data.child("clueApprovals").value=null
                            data.child("clueRegionsRevision").value=next
                            data.child("sourceImageUrl").value=replacementUrl
                            data.child("revision").value=next
                            data.child("updatedAt").value=System.currentTimeMillis()
                            data.child("lastEditedBy").value=uid
                            data.child("lastEditedByName").value=editorName.trim().take(40)
                            return Transaction.success(data)
                        }
                        override fun onComplete(error:DatabaseError?,committed:Boolean,snapshot:DataSnapshot?){
                            if(error!=null)callback(Result.failure(error.toException()))
                            else if(!committed)callback(Result.failure(IllegalStateException(reason)))
                            else if(snapshot?.child("sourceImageUrl")?.value!=replacementUrl)
                                callback(Result.failure(IllegalStateException("השרת לא אישר את התמונה החדשה")))
                            else {
                                val revision=(snapshot.child("revision").value as? Number)?.toLong()?:0L
                                DebugLog.i("CANONICAL_IMAGE_REPLACE","committed issue="+DebugLog.compactId(issueKey)+" revision="+revision+" image-only=true")
                                callback(Result.success(revision))
                            }
                        }
                    })
                }.addOnFailureListener { callback(Result.failure(it)) }
            },{callback(Result.failure(it))})
        }
    }

'''
p.write_text(s.replace(anchor,newMethod+anchor))

# The ordinary source and editor paths must remain unchanged. A separate
# viewer loads the remote Canonical image, and only administrator DRY
# displays an action to replace it from the device.
edit('MainActivity.kt',
    '    private val sourcePicker = registerForActivityResult(ActivityResultContracts.GetContent())',
    '''    private data class PendingCanonicalImage(
        val puzzleId:String,val issue:String,val physicalNode:String,
        val expectedGrid:String,val oldUrl:String,val threadUrl:String
    )
    private var pendingCanonicalImage:PendingCanonicalImage?=null
    private var canonicalImageUploadInFlight=false
    private val canonicalImagePicker=registerForActivityResult(ActivityResultContracts.GetContent()){uri->
        val target=pendingCanonicalImage
        pendingCanonicalImage=null
        if(uri!=null && target!=null && board.crossword?.puzzleId==target.puzzleId)
            previewCanonicalImageReplacement(uri,target)
    }
    private val sourcePicker = registerForActivityResult(ActivityResultContracts.GetContent())''')

old='''    private fun showSourceImage() {
        val cw=board.crossword?:return
        ScreenUi.hideKeyboard(board)
        withSource(displayOnly=true) { bitmap ->
            if(board.crossword!==cw)return@withSource
            if(bitmap==null) {
                toast(if(isLocalStructuredSource(cw.puzzleId))
                    PrintedStructuredSource.userFacingStatus(cw.puzzleId) else
                    "תמונת המקור אינה שמורה לתשבץ הזה.")
                return@withSource
            }
            show(SourceImageDialog(this,bitmap))
        }
    }
'''
new='''    private fun showSourceImage() {
        val cw=board.crossword?:return
        ScreenUi.hideKeyboard(board)
        // Structured publisher images are local-only; their existing separate
        // display policy is not changed by Canonical administration.
        val issue=canonicalIndex.issueKey(cw.puzzleId)
        if(isLocalStructuredSource(cw.puzzleId) || issue.isNullOrBlank()){
            showLocalSourceImage(cw)
            return
        }
        val id=++generation
        busy(true,"בודק תמונה קנונית...")
        executor.execute {
            val thread=canonicalIndex.sourceThreadUrl(cw.puzzleId)
            val image=canonicalIndex.sourceImageUrl(cw.puzzleId)
            val lookup=canonicalCloud.fetchCompatibleBlockingResult(
                issue,CrosswordCatalog.issueKeyFromSourceKey(issue),thread,image,8000L)
            val snapshot=lookup?.getOrNull()?.takeIf {
                it.issueKey==issue && it.gridSignature==AnswerChecking.signature(cw)
            }
            val remoteUrl=snapshot?.sourceImageUrl.orEmpty().takeIf{it.startsWith("https://")}
            val bitmap=remoteUrl?.let{ url ->runCatching {
                val file=ImageDownload.fetch(url,WeeklyCrosswordsFetcher.USER_AGENT,cacheDir)
                try{ImageLoader.load(file)}finally{file.delete()}
            }.getOrNull() }
            runOnUiThread {
                busy(false)
                if(board.crossword!==cw || isFinishing || isDestroyed){
                    bitmap?.recycle()
                    return@runOnUiThread
                }
                if(bitmap==null || snapshot==null){
                    DebugLog.w("CANONICAL_IMAGE_VIEW","remote not verified; showing local fallback")
                    showLocalSourceImage(cw,"עותק מקומי — לא אומת כעת מול Canonical")
                }else{
                    val dialog=SourceImageDialog(this,bitmap,
                        sourceStatus="תמונה קנונית מאומתת • Revision "+snapshot.revision)
                    show(dialog)
                    // Permissions are verified again by Storage and the database
                    // transaction when the administrator actually publishes.
                    if(BuildConfig.HIGI_DRY_BUILD){
                        AdminAccess(applicationContext).loadRole{role->runOnUiThread{
                            if(role!=AdminAccess.Role.NONE && dialog.isShowing &&
                                board.crossword===cw && !isFinishing && !isDestroyed){
                                dialog.enableCanonicalReplacement {
                                    pendingCanonicalImage=PendingCanonicalImage(
                                        cw.puzzleId,issue,snapshot.storageNodeKey,
                                        snapshot.gridSignature,snapshot.sourceImageUrl,
                                        snapshot.sourceThreadUrl)
                                    canonicalImagePicker.launch("image/*")
                                }
                            }
                        }}
                    }
                }
            }
        }
    }

    private fun showLocalSourceImage(cw:Crossword,notice:String="תמונה מקומית — לא אומתה מול Canonical"){
        withSource(displayOnly=true){bitmap->
            if(board.crossword!==cw)return@withSource
            if(bitmap==null){
                toast("תמונת מקור לא זמינה")
                return@withSource
            }
            show(SourceImageDialog(this,bitmap,sourceStatus=notice))
        }
    }

    private fun previewCanonicalImageReplacement(uri:Uri,target:PendingCanonicalImage){
        val cw=board.crossword?:return
        if(cw.puzzleId!=target.puzzleId || canonicalImageUploadInFlight)return
        val id=++generation
        busy(true,"טוען תמונה לאישור...")
        executor.execute{
            val candidate=runCatching{ImageLoader.load(this,uri)}.getOrNull()
            runOnUiThread{
                busy(false)
                if(board.crossword!==cw || isFinishing || isDestroyed){
                    candidate?.recycle();return@runOnUiThread
                }
                if(candidate==null || candidate.width<100 || candidate.height<100){
                    candidate?.recycle()
                    toast("תמונת המקור אינה תקינה")
                    return@runOnUiThread
                }
                val preview=ImageView(this).apply{
                    setImageBitmap(candidate)
                    adjustViewBounds=true
                    scaleType=ImageView.ScaleType.FIT_CENTER
                    layoutParams=LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,dp(250))
                }
                val content=LinearLayout(this).apply{
                    orientation=LinearLayout.VERTICAL
                    addView(TextView(this@MainActivity).apply{
                        text="תמונת המקור הקנונית תוחלף לכל המשתמשים. הרשת, טקסט ההגדרות והפתרונות יישמרו ללא פענוח מחדש. חיתוכים השייכים לתמונה הישנה יאבדו את תוקפם."
                        setPadding(dp(12),dp(9),dp(12),dp(9))
                    })
                    addView(preview)
                }
                AlertDialog.Builder(this).setTitle("אשר החלפת תמונה קנונית")
                    .setView(content)
                    .setNegativeButton("ביטול"){_,_->candidate.recycle()}
                    .setPositiveButton("אישור ופרסום"){_,_->
                        if(board.crossword?.puzzleId!=target.puzzleId ||
                            canonicalImageUploadInFlight){
                            candidate.recycle()
                        }else publishCanonicalImageReplacement(target,candidate)
                    }.setOnCancelListener{candidate.recycle()}.show()
            }
        }
    }

    private fun publishCanonicalImageReplacement(target:PendingCanonicalImage,bitmap:Bitmap){
        if(canonicalImageUploadInFlight || !BuildConfig.HIGI_DRY_BUILD ||
            board.crossword?.puzzleId!=target.puzzleId){
            bitmap.recycle();return
        }
        canonicalImageUploadInFlight=true
        busy(true,"מעלה תמונה קנונית...")
        executor.execute{
            CanonicalSourceImageStorage.upload(applicationContext,target.issue,bitmap,
                explicitDryAdminPublish=true){ uploaded ->
                uploaded.fold(onFailure={error->
                    bitmap.recycle()
                    runOnUiThread{
                        canonicalImageUploadInFlight=false
                        if(!isDestroyed){
                            busy(false)
                            toast("ההעלאה נכשלה: "+error.message.orEmpty().take(100))
                        }
                    }
                },onSuccess={image->
                    canonicalCloud.replaceCanonicalSourceImageOnly(
                        target.issue,target.physicalNode,target.expectedGrid,
                        target.oldUrl,image.url,settings.displayName){result->
                        result.fold(onFailure={error->
                            bitmap.recycle()
                            runOnUiThread{
                                canonicalImageUploadInFlight=false
                                if(!isDestroyed){
                                    busy(false)
                                    toast("הקנוני לא שונה: "+error.message.orEmpty().take(110))
                                }
                            }
                        },onSuccess={revision->
                            // Only after Firebase commit update local cache. The
                            // authoritative viewer independently refetches the
                            // server URL, rather than claiming local==canonical.
                            executor.execute{
                                val saved=runCatching{
                                    library.writeSource(target.puzzleId){out->
                                        check(bitmap.compress(Bitmap.CompressFormat.PNG,100,out))
                                    }
                                    true
                                }.getOrDefault(false)
                                bitmap.recycle()
                                runOnUiThread {
                                    canonicalImageUploadInFlight=false
                                    if(!isDestroyed){
                                        canonicalIndex.bind(target.puzzleId,target.issue,revision,
                                            image.url,target.threadUrl)
                                        source=null
                                        sourceViewportStore.clear(target.puzzleId)
                                        sourceClueCropStore.clear(target.puzzleId)
                                        clueRegionStore.deletePuzzle(target.puzzleId)
                                        busy(false)
                                        DebugLog.i("CANONICAL_IMAGE_REPLACE","local cache updated="+saved+" revision="+revision)
                                        toast(if(saved)"התמונה הקנונית עודכנה בהצלחה"
                                            else "התמונה הקנונית עודכנה, אך העותק המקומי לא נשמר")
                                        if(board.crossword?.puzzleId==target.puzzleId)showSourceImage()
                                    }
                                }
                            }
                        })
                    }
                })
            }
        }
    }
'''
edit('MainActivity.kt',old,new)

gradle=root/'app/build.gradle.kts'
s=gradle.read_text()
assert s.count('versionCode = 353')==1 and s.count('versionName = "0.15.203"')==1
gradle.write_text(s.replace('versionCode = 353','versionCode = 354').replace('versionName = "0.15.203"','versionName = "0.15.204"'))
# Invariant checks. These are supplemental; the cloud workflow also runs Gradle tests.
a=(pkg/'MainActivity.kt').read_text()
b=(pkg/'CanonicalPuzzleCloud.kt').read_text()
assert 'fun replaceCanonicalSourceImageOnly(' in b
assert 'data.child("clues").value' not in b[b.index('fun replaceCanonicalSourceImageOnly('):b.index('fun replaceCanonicalSourceImageOnly(')+6000]
assert 'data.child("answers").value' not in b[b.index('fun replaceCanonicalSourceImageOnly('):b.index('fun replaceCanonicalSourceImageOnly(')+6000]
assert 'sourceStatus="תמונה קנונית מאומתת' in a
assert 'showLocalSourceImage(cw,"עותק מקומי — לא אומת כעת מול Canonical")' in a
assert 'fun updateClueAndRegion' in b
assert 'DRY local-only; upload and canonical publication blocked' in a
print("Higi v204 canonical-only image replacement and viewer changes staged.")
