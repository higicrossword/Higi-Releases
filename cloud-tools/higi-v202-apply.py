#!/usr/bin/env python3
"""Higi 0.15.202 DRY-only admin library filter, return, Downloads, contextual OCR.

A fail-closed change set: only explicit paths and exact anchors. No backend,
Firebase, normal solver, app initialization, OCR engine invocation or networking.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
assets=Path(__file__).resolve().parent
app=root/'app/src/main/java/com/example/hebrewcrossword'
tests=root/'app/src/test/java/com/example/hebrewcrossword'

def once(s,old,new,name):
    n=s.count(old)
    assert n==1, f'{name}: expected exactly one anchor, got {n}: {old[:90]!r}'
    return s.replace(old,new,1)

def add_file(name,folder):
    dest=folder/name
    assert not dest.exists(), f'New file already present: {dest}'
    data=(assets/name).read_bytes()
    assert len(data)>500
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
    print('CREATE',dest.relative_to(root))

for n,folder in [
    ('AdminLibrarySeriesFilterV202.kt',app),
    ('AdminLibrarySeriesFilterV202Test.kt',tests),
    ('OcrWeeklyAnchorsV202Test.kt',tests)]: add_file(n,folder)

# A: The saved crossword dialog: list remains virtualized, no bitmap loads.
p=app/'PuzzleLibraryDialog.kt'
s=p.read_text()
s=once(s,
'''    private val onAdminAction: ((PuzzleLibrary.Entry, Int) -> Unit)? = null
) : Dialog(context, R.style.Theme_HebrewCrossword) {''',
'''    private val onAdminAction: ((PuzzleLibrary.Entry, Int) -> Unit)? = null,
    private val initialAdminSeriesFilterId:String=AdminLibrarySeriesFilterV202.ALL,
    private val onAdminSeriesFilterChanged:((String)->Unit)?=null
) : Dialog(context, R.style.Theme_HebrewCrossword) {''', 'Library dialog constructor')
s=once(s,
'''    private val entries = listing.entries
    // Default deny until Firebase confirms this session has administrator privileges.
    private var adminEnabled=false
    fun setAdminEnabled(allowed:Boolean){
        if(adminEnabled!=allowed){adminEnabled=allowed; if(::list.isInitialized)list.invalidateViews()}
    }
''',
'''    private val entries = listing.entries
    // Never resolve series on every visible row or for a regular user's library.
    private var visibleEntries:List<PuzzleLibrary.Entry> = entries
    private var seriesIds:Map<String,String?>?=null
    private var selectedSeriesId=AdminLibrarySeriesFilterV202.normalized(initialAdminSeriesFilterId)
    private lateinit var adminFilterRow:LinearLayout
    // Default deny until Firebase confirms this session has administrator privileges.
    private var adminEnabled=false
    fun setAdminEnabled(allowed:Boolean){
        val filterPermitted=BuildConfig.HIGI_DRY_BUILD && allowed
        if(adminEnabled==allowed)return
        adminEnabled=allowed
        if(::adminFilterRow.isInitialized){
            adminFilterRow.visibility=if(filterPermitted)View.VISIBLE else View.GONE
        }
        if(filterPermitted && seriesIds==null){
            // One bounded local classification, only after the role check.
            seriesIds=entries.associate{e->e.id to e.puzzle?.title?.let{
                title->CrosswordCatalog.fromCanonicalTitle(title)?.id
            }}
        }
        applyAdminSeriesFilter()
    }
    private fun applyAdminSeriesFilter(){
        val selected=if(BuildConfig.HIGI_DRY_BUILD && adminEnabled)
            selectedSeriesId else AdminLibrarySeriesFilterV202.ALL
        val lookup=seriesIds.orEmpty()
        visibleEntries=if(selected==AdminLibrarySeriesFilterV202.ALL)entries else
            entries.filter{e->AdminLibrarySeriesFilterV202.matches(selected,lookup[e.id])}
        if(::list.isInitialized){
            (list.adapter as? BaseAdapter)?.notifyDataSetChanged()
            list.setSelection(0)
        }
    }
''', 'Library filter state + cache')
needle='''        list = ListView(context).apply { adapter = Adapter(); setOnItemClickListener { _, _, position, _ ->
            val e = entries[position]
'''
replace='''        if(BuildConfig.HIGI_DRY_BUILD){
            adminFilterRow=LinearLayout(context).apply {
                orientation=LinearLayout.HORIZONTAL
                layoutDirection=View.LAYOUT_DIRECTION_RTL
                gravity=Gravity.CENTER_VERTICAL
                visibility=View.GONE  // Firebase role still unconfirmed.
                setPadding(dp(12),0,dp(12),dp(6))
            }
            adminFilterRow.addView(TextView(context).apply {
                text="\\u05e1\\u05d3\\u05e8\\u05d4:"
                setTextColor(UiKit.primaryText());textSize=14f
            },LinearLayout.LayoutParams(-2,-2))
            val available=AdminLibrarySeriesFilterV202.options
            val chooser=Spinner(context).apply {
                adapter=ArrayAdapter(context,android.R.layout.simple_spinner_dropdown_item,
                    available.map{it.title})
                setSelection(available.indexOfFirst{it.id==selectedSeriesId}.coerceAtLeast(0))
                onItemSelectedListener=object:AdapterView.OnItemSelectedListener {
                    override fun onItemSelected(parent:AdapterView<*>?,view:View?,position:Int,id:Long){
                        val next=available.getOrNull(position)?.id ?: return
                        if(next==selectedSeriesId)return
                        selectedSeriesId=next
                        onAdminSeriesFilterChanged?.invoke(next)
                        applyAdminSeriesFilter()
                    }
                    override fun onNothingSelected(parent:AdapterView<*>?)=Unit
                }
            }
            adminFilterRow.addView(chooser,LinearLayout.LayoutParams(0,dp(44),1f))
            root.addView(adminFilterRow)
        }
        list = ListView(context).apply { adapter = Adapter(); setOnItemClickListener { _, _, position, _ ->
            val e = visibleEntries[position]
'''
s=once(s,needle,replace,'Library filter controls')
s=once(s,'override fun getCount() = entries.size','override fun getCount() = visibleEntries.size','ListView size')
s=once(s,'override fun getItem(position: Int) = entries[position]',
       'override fun getItem(position: Int) = visibleEntries[position]','ListView item')
s=once(s,'val entry = entries[position]; val puzzle = entry.puzzle',
       'val entry = visibleEntries[position]; val puzzle = entry.puzzle','Virtualized row selection')
assert s.count('visibleEntries[position]')==3
p.write_text(s)
print('MODIFY',p.relative_to(root),'admin-only virtualized series selector')

# B: MainActivity persists the filter in activity state and receives an explicit
# completion from the saved-puzzle OCR reviewer, not from normal opening/import.
p=app/'MainActivity.kt';s=p.read_text()
s=once(s,
'''    private var activeDialog:android.app.Dialog?=null
''',
'''    private var activeDialog:android.app.Dialog?=null
    // DRY administrator-only UI selection. No disk writes, network or hot-path work.
    private var adminLibrarySeriesFilterId=AdminLibrarySeriesFilterV202.ALL
''','Main filter memory')
s=once(s,
'''    private val recentPicker=registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        explicitImportFlowPending=false
        if(result.resultCode==RESULT_OK) {
            val data=result.data
            if(handleSourceReplacementOnly(data))return@registerForActivityResult''',
'''    private val recentPicker=registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        explicitImportFlowPending=false
        if(BuildConfig.HIGI_DRY_BUILD && result.resultCode==RESULT_OK &&
            result.data?.getBooleanExtra(RecentCrosswordsActivity.EXTRA_ADMIN_OCR_RETURN_TO_LIBRARY,false)==true){
            // The saved-review launcher has finished; restore only this library
            // context, never the normal weekly/import activity flow.
            whenReady{if(!isFinishing && !isDestroyed && atHome)
                refreshLibrary{displayLibrary()}}
            return@registerForActivityResult
        }
        if(result.resultCode==RESULT_OK) {
            val data=result.data
            if(handleSourceReplacementOnly(data))return@registerForActivityResult''',
'Main saved review result routing')
s=once(s,
'''            onAdminAction=::openSavedPuzzleAdminAction
''',
'''            onAdminAction=::openSavedPuzzleAdminAction,
            initialAdminSeriesFilterId=adminLibrarySeriesFilterId,
            onAdminSeriesFilterChanged={id->
                if(BuildConfig.HIGI_DRY_BUILD)
                    adminLibrarySeriesFilterId=AdminLibrarySeriesFilterV202.normalized(id)
            }
''', 'Pass filter state to virtualized dialog')
s=once(s,
'''        DebugLog.i("MAIN","onCreate savedState=${savedInstanceState!=null}")
''',
'''        DebugLog.i("MAIN","onCreate savedState=${savedInstanceState!=null}")
        if(BuildConfig.HIGI_DRY_BUILD)adminLibrarySeriesFilterId=
            AdminLibrarySeriesFilterV202.normalized(savedInstanceState?.getString("adminLibrarySeriesFilterId"))
''', 'Restore after Activity recreation')
s=once(s,
'''    override fun onSaveInstanceState(outState: Bundle) {
        save()
''',
'''    override fun onSaveInstanceState(outState: Bundle) {
        if(BuildConfig.HIGI_DRY_BUILD)
            outState.putString("adminLibrarySeriesFilterId",adminLibrarySeriesFilterId)
        save()
''', 'Save admin filter state')
p.write_text(s)
print('MODIFY',p.relative_to(root),'explicit saved OCR return and filter state')

# C: Saved puzzle admin path needs a real Activity Result. Keep other paths as
# they are. On cancel or Back the callback runs identically.
p=app/'RecentCrosswordsActivity.kt';s=p.read_text()
s=once(s,
'''        const val EXTRA_SAVED_ADMIN_ACTION="savedAdminAction"
''',
'''        const val EXTRA_SAVED_ADMIN_ACTION="savedAdminAction"
        const val EXTRA_ADMIN_OCR_RETURN_TO_LIBRARY="adminOcrReturnToLibrary"
''', 'Review return result token')
s=once(s,
'''    private val adminPhoneImagePicker=registerForActivityResult(ActivityResultContracts.GetContent()){uri->''',
'''    private val savedAdminOcrReviewer=registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()) { _ ->
        if(BuildConfig.HIGI_DRY_BUILD && savedAdminId.isNotBlank() && savedAdminAction==9){
            setResult(Activity.RESULT_OK,Intent().putExtra(EXTRA_ADMIN_OCR_RETURN_TO_LIBRARY,true))
            finish()
        }
    }
    private val adminPhoneImagePicker=registerForActivityResult(ActivityResultContracts.GetContent()){uri->''',
'Admin OCR result registration')
start='''        startActivity(Intent(this,AdminOcrRecropActivity::class.java).apply {
            record?.let{putExtra(AdminOcrRecropActivity.EXTRA_PUZZLE_ID,it.id)}'''
s=once(s,start,
'''        val reviewIntent=Intent(this,AdminOcrRecropActivity::class.java).apply {
            record?.let{putExtra(AdminOcrRecropActivity.EXTRA_PUZZLE_ID,it.id)}''','Construct review intent')
s=once(s,
'''            putExtra(AdminOcrRecropActivity.EXTRA_TITLE,WeeklyCrosswordsFetcher.displayTitle(raw))
        })
        // The saved-puzzle admin launcher hides its list and is one-shot. If
        // left on the back stack it becomes a permanently empty loading page.
        if(savedAdminId.isNotBlank())finish()
''',
'''            putExtra(AdminOcrRecropActivity.EXTRA_TITLE,WeeklyCrosswordsFetcher.displayTitle(raw))
        }
        if(BuildConfig.HIGI_DRY_BUILD && savedAdminId.isNotBlank() && savedAdminAction==9){
            // Keep this one-shot trampoline until the OCR Activity actually closes.
            // Its result restores the saved library and the current filter.
            savedAdminOcrReviewer.launch(reviewIntent)
        }else{
            startActivity(reviewIntent)
            // Retain historic navigation for weekly and non-DRY builds.
            if(savedAdminId.isNotBlank())finish()
        }
''', 'Review deferred completion')
p.write_text(s)
print('MODIFY',p.relative_to(root),'review return on Back/cancel after activity closure')

# D: Keep exactly the SAME report body, including all v201 diagnostics.
# Only swap its button and destination to MediaStore.Downloads (Android Q+).
p=app/'AdminOcrRecropActivity.kt';s=p.read_text()
copy_title='\u05d4\u05e2\u05ea\u05e7 \u05d3\u05d5\u05d7'
save_title='\u05e9\u05de\u05d5\u05e8 \u05d3\u05d5\u05d7'
s=once(s,'button("'+copy_title+'"){copyReport()}',
    'button(if(BuildConfig.HIGI_DRY_BUILD) "'+save_title+'" else "'+copy_title+'"){saveReport()}',
    'Save report button in DRY, clipboard unchanged outside DRY')
s=once(s,'private fun copyReport(){','private fun saveReport(){','Report handler name')
start=s.index('    private fun saveReport(){')
end=s.index('    private fun confirmCommit()',start)
body=s[start:end]
idx=body.find('        val clipboard=getSystemService(CLIPBOARD_SERVICE) as? ClipboardManager')
assert idx>=0,'Clipboard end of report no longer matches expected source'
body=body[:idx]+'''        if(!BuildConfig.HIGI_DRY_BUILD){
            val clipboard=getSystemService(CLIPBOARD_SERVICE) as? ClipboardManager
            if(clipboard==null){toast("\u05d4\u05dc\u05d5\u05d7 \u05d0\u05d9\u05e0\u05d5 \u05d6\u05de\u05d9\u05df");return}
            clipboard.setPrimaryClip(ClipData.newPlainText("Higi OCR ${BuildConfig.VERSION_NAME}",result))
            toast("\u05d4\u05d3\u05d5\u05d7 \u05d4\u05d5\u05e2\u05ea\u05e7 \u05dc\u05dc\u05d5\u05d7")
            return
        }
        if(android.os.Build.VERSION.SDK_INT<android.os.Build.VERSION_CODES.Q){
            toast("\\u05e9\\u05de\\u05d9\\u05e8\\u05d4 \\u05d9\\u05e9\\u05d9\\u05e8\\u05d4 \\u05dc-Downloads \\u05d3\\u05d5\\u05e8\\u05e9\\u05ea Android 10+")
            return
        }
        // Filesystem work is on-demand and off the UI thread. Scoped Storage,
        // no broad storage permission, no OCR/bitmap/network reprocessing.
        executor.execute {
            val filename="Higi_OCR_${BuildConfig.VERSION_NAME}_"+
                java.text.SimpleDateFormat("yyyyMMdd_HHmmss_SSS",java.util.Locale.US)
                    .format(java.util.Date())+".txt"
            val values=android.content.ContentValues().apply {
                put(android.provider.MediaStore.MediaColumns.DISPLAY_NAME,filename)
                put(android.provider.MediaStore.MediaColumns.MIME_TYPE,"text/plain; charset=utf-8")
                put(android.provider.MediaStore.MediaColumns.RELATIVE_PATH,
                    android.os.Environment.DIRECTORY_DOWNLOADS+"/")
                put(android.provider.MediaStore.MediaColumns.IS_PENDING,1)
            }
            var uri:android.net.Uri?=null
            val saved=runCatching {
                uri=contentResolver.insert(android.provider.MediaStore.Downloads.EXTERNAL_CONTENT_URI,values)
                    ?: error("MediaStore insert failed")
                contentResolver.openOutputStream(uri!!,"w")?.use { stream ->
                    stream.write(result.toByteArray(Charsets.UTF_8))
                    stream.flush()
                } ?: error("Downloads output stream unavailable")
                val ready=android.content.ContentValues().apply {
                    put(android.provider.MediaStore.MediaColumns.IS_PENDING,0)
                }
                check(contentResolver.update(uri!!,ready,null,null)>0)
            }
            if(saved.isFailure){
                uri?.let{runCatching{contentResolver.delete(it,null,null)}}
            }
            runOnUiThread {
                if(!isDestroyed && !isFinishing){
                    if(saved.isSuccess)toast("\\u05d4\\u05d3\\u05d5\\u05d7 \\u05e0\\u05e9\\u05de\\u05e8 \\u05d1-Downloads: $filename")
                    else toast("\\u05e9\\u05de\\u05d9\\u05e8\\u05ea \\u05d4\\u05d3\\u05d5\\u05d7 \\u05e0\\u05db\\u05e9\\u05dc\\u05d4: ${saved.exceptionOrNull()?.message.orEmpty().take(100)}")
                }
            }
        }
    }

'''
s=s[:start]+body+s[end:]
assert 'ClipboardManager' in s[s.index('    private fun saveReport(){'):s.index('    private fun confirmCommit()')]
p.write_text(s)
print('MODIFY',p.relative_to(root),'MediaStore.Downloads UTF-8 txt, existing report body unchanged')

# E: Recover truncated printed anchors exclusively inside the Yedioth weekly
# review helper. Require unique candidates BETWEEN other printed starts.
p=app/'OcrWeeklySourceAnchorsV199.kt';s=p.read_text()
s=once(s,
'''        val all=words.filter{it.box.valid && it.confidence>=40 &&
''',
'''        val all=words.filter{it.box.valid && it.confidence>=20 &&
''','Allow low-confidence candidates for context-only evaluation')
start='''        for(num in nums){
            if(num in matches)continue
            val last=(num%10).toString()
            val plausible=all.filter{word->
                val raw=clean(word.text)
                val bareNumber=bare.matches(raw) && raw==num.toString()
                val truncation=num>=10 &&
                    (raw==last || printed(raw)==(num%10)) &&
                    word.box.right.toFloat()/w >= if(dir=='H')0.55f else 0.245f
                (bareNumber || truncation) && word.confidence>=52
            }
            if(plausible.size!=1)continue
            val candidate=plausible.single().box
            val prior=nums.filter{it<num}.lastOrNull()?.let{matches[it]}
            val after=nums.firstOrNull{it>num}?.let{matches[it]}
            val middle=(candidate.top+candidate.bottom)/2
            // For inline starts the next number can share a printed row.
            if(prior!=null && middle<prior.box.top-4)continue
            if(after!=null && middle>after.box.bottom+4)continue
            if(matches.values.any{it.box==candidate})continue
            matches[num]=Anchor(num,candidate,true)
        }
'''
new='''        for(num in nums){
            if(num in matches)continue
            val last=(num%10).toString()
            val prior=nums.filter{it<num}.lastOrNull()?.let{matches[it]}
            val after=nums.firstOrNull{it>num}?.let{matches[it]}
            val plausible=all.filter{word->
                val raw=clean(word.text)
                val bareNumber=bare.matches(raw) && raw==num.toString()
                val truncation=num>=10 &&
                    (raw==last || printed(raw)==(num%10)) &&
                    word.box.right.toFloat()/w >= if(dir=='H')0.55f else 0.245f
                val middle=(word.box.top+word.box.bottom)/2
                // FIRST constrain to neighboring reliable printed anchors;
                // otherwise 1. at the top of the column masks 11. further down.
                val ordered=(prior==null || middle>=prior.box.top-4) &&
                    (after==null || middle<=after.box.bottom+4)
                // Confidence 20..51 is evidence ONLY when bounded on BOTH
                // sides, has the right suffix/column and is the sole candidate.
                val weakContext=word.confidence in 20..51 && truncation &&
                    prior!=null && after!=null &&
                    middle>prior.box.bottom && middle<after.box.top
                (bareNumber || truncation) && ordered &&
                    (word.confidence>=52 || weakContext)
            }
            if(plausible.size!=1)continue
            val candidate=plausible.single().box
            if(matches.values.any{it.box==candidate})continue
            matches[num]=Anchor(num,candidate,true)
        }
'''
s=once(s,start,new,'Bounded truncated-number recovery only')
p.write_text(s)
print('MODIFY',p.relative_to(root),'contextual weak printed numbers; no global confidence change')

# Prevent accidental changes to regular builds. Only version metadata is shared;
# all UI features are BuildConfig.HIGI_DRY_BUILD and role guarded.
p=root/'app/build.gradle.kts';s=p.read_text()
s=once(s,'versionCode = 351','versionCode = 352','versionCode')
s=once(s,'versionName = "0.15.201"','versionName = "0.15.202"','versionName')
p.write_text(s)
print('V202_SOURCE_MODIFICATIONS_APPLIED')