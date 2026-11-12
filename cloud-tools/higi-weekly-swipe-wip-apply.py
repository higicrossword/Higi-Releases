#!/usr/bin/env python3
"""Apply only worktree-only fixes onto exact v0.15.197 source. No version bump, APK or deploy."""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
assets=Path(sys.argv[2]).resolve()
app=root/'app/src/main/java/com/example/hebrewcrossword'
tests=root/'app/src/test/java/com/example/hebrewcrossword'


def replace_one(text,old,new,label):
    matches=text.count(old)
    if matches!=1:
        raise RuntimeError(f'{label}: expected exact source anchor once, got {matches}')
    return text.replace(old,new,1)


def update(path,replacements):
    value=path.read_text(encoding='utf-8')
    for old,new,description in replacements:
        value=replace_one(value,old,new,f'{path.name}:{description}')
    path.write_text(value,encoding='utf-8')
    print('UPDATED',path.relative_to(root))


def copy_new(src,dst):
    assert src.is_file(),f'missing {src}'
    assert not dst.exists(),f'already exists {dst}'
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(src.read_bytes())
    print('CREATED',dst.relative_to(root))

# Weekly profile source is staged in this WIP branch; Android uses the same shared rules
# for Monday and Wednesday, but both source title and original sourceKey remain unchanged.
for file in ('OcrSeriesProfilesV197.kt','OcrSeriesPreviewV197.kt'):
    src=assets/file
    assert src.exists(),file
    (app/file).write_bytes(src.read_bytes())
    print('WIP_SOURCE',file)

# Regression test shipped in 197 expected two separate profiles; update the fixture
# alongside the WIP alias rather than weakening the test suite.
weekly_test=tests/'OcrSeriesProfilesV197Test.kt'
update(weekly_test,[
 ('assertEquals("YEDIOTH_MONDAY_DEKEL",OcrSeriesProfilesV197.resolve("דקל בנו שני","YEDIOTH_MONDAY_DEKEL:20261109").id)',
  'assertEquals("YEDIOTH_DEKEL_WEEKLY",OcrSeriesProfilesV197.resolve("דקל בנו שני","YEDIOTH_MONDAY_DEKEL:20261109").id)\n        assertEquals("YEDIOTH_DEKEL_WEEKLY",OcrSeriesProfilesV197.resolve("דקל בנו רביעי","YEDIOTH_WEDNESDAY_DEKEL:20261111").id)',
  'weekly profile expected'),
 ('assertFalse(OcrSeriesProfilesV197.HAFUCH.mondayBoundaryReview)',
  'assertFalse(OcrSeriesProfilesV197.HAFUCH.mondayBoundaryReview)\n        assertTrue(OcrSeriesProfilesV197.WEDNESDAY.mondayBoundaryReview)',
  'Wednesday enable')
])

# App is dynamically routed by profile ID, not filename: both aliases now have the
# same ID. Preserve TARTEY/HAFUCH behavior and all existing canonical policies.
engine=app/'HigiLocalOcrCropEngine.kt'
engine_txt=engine.read_text(encoding='utf-8')
assert 'layoutSeriesId==OcrSeriesProfilesV197.MONDAY.id' in engine_txt, 'weekly gate absent'
assert 'if(refineSharedRows' in engine_txt

# A gesture tracker measures displacement from the ORIGINAL ACTION_DOWN and remembers
# multi-touch until the end of the gesture; it never interprets pinch as navigation.
copy_new(assets/'AdminOcrSwipeTracker.kt',app/'AdminOcrSwipeTracker.kt')
copy_new(assets/'AdminOcrSwipeTrackerTest.kt',tests/'AdminOcrSwipeTrackerTest.kt')

crop=app/'AdminOcrSelectedCropView.kt'
update(crop,[
 ('''    private var swipeStartX=0f
    private var swipeStartY=0f
    private var hadMultiTouch=false''',
 '''    private val swipeTracker=AdminOcrSwipeTracker(dp(56f),dp(52f))
    // Use actual drawn width, not raw zoom: readable mode can overflow at zoom=1.
    private var horizontalPanAvailable=false''', 'gesture fields'),
 ('''        source=bitmap
        regions=geometry?.lines.orEmpty().ifEmpty {''',
 '''        source=bitmap
        horizontalPanAvailable=false
        swipeTracker.cancel()
        regions=geometry?.lines.orEmpty().ifEmpty {''', 'reset on new clue'),
 ('''        val visibleWidth=(width-2f*pad).coerceAtLeast(1f)
        val visibleHeight=''',
 '''        val visibleWidth=(width-2f*pad).coerceAtLeast(1f)
        horizontalPanAvailable=maxDrawWidth>visibleWidth+dp(2f)
        val visibleHeight=''', 'actual pan width'),
 ('''                swipeStartX=event.x;swipeStartY=event.y;hadMultiTouch=false
                parent?.requestDisallowInterceptTouchEvent(true)''',
 '''                swipeTracker.down(event.x,event.y)
                parent?.requestDisallowInterceptTouchEvent(true)''', 'touch down'),
 ('''                pinchDistance=distance(event);pinchZoom=zoom;hadMultiTouch=true''',
 '''                pinchDistance=distance(event);pinchZoom=zoom;swipeTracker.addPointer()''', 'multitouch'),
 ('''                    lastX=event.x;lastY=event.y
                swipeStartX=event.x;swipeStartY=event.y;hadMultiTouch=false''',
 '''                    lastX=event.x;lastY=event.y''', 'bug: reset on each move'),
 ('''                if(event.actionMasked==MotionEvent.ACTION_UP && !hadMultiTouch &&
                    zoom in .99f..1.01f && kotlin.math.abs(event.x-swipeStartX)>dp(76f) &&
                    kotlin.math.abs(event.y-swipeStartY)<dp(54f)) {
                    onHorizontalSwipe?.invoke(if(event.x>swipeStartX)-1 else 1)
                }
                pinchDistance=0f
                parent?.requestDisallowInterceptTouchEvent(false)
                performClick()''',
 '''                val direction=if(event.actionMasked==MotionEvent.ACTION_UP)
                    swipeTracker.up(event.x,event.y,!horizontalPanAvailable)
                else {swipeTracker.cancel();0}
                pinchDistance=0f
                parent?.requestDisallowInterceptTouchEvent(false)
                if(direction!=0) onHorizontalSwipe?.invoke(direction) else performClick()''', 'gesture finish')
])

# The full-source inspector is pannable when zoomed. Keep panning priority; allow
# next/previous navigation when the source fits, without conflicting with pinch.
inspector=app/'AdminClueRegionsActivity.kt'
update(inspector,[
 ('''    private var swipeStartX=0f
    private var swipeStartY=0f
    private var hadMultiTouch=false''',
 '''    private val swipeTracker=AdminOcrSwipeTracker(dp(56f),dp(52f))''', 'inspector gesture fields'),
 ('''MotionEvent.ACTION_DOWN->{lastX=e.x;lastY=e.y;swipeStartX=e.x;swipeStartY=e.y;hadMultiTouch=false;parent?.requestDisallowInterceptTouchEvent(true)}''',
 '''MotionEvent.ACTION_DOWN->{lastX=e.x;lastY=e.y;swipeTracker.down(e.x,e.y);parent?.requestDisallowInterceptTouchEvent(true)}''', 'inspector down'),
 ('''MotionEvent.ACTION_POINTER_DOWN->{if(e.pointerCount>=2){pinchStart=distance(e);pinchZoom=zoom;hadMultiTouch=true}}''',
 '''MotionEvent.ACTION_POINTER_DOWN->{if(e.pointerCount>=2){pinchStart=distance(e);pinchZoom=zoom;swipeTracker.addPointer()}}''', 'inspector pinch'),
 ('''                if(e.actionMasked==MotionEvent.ACTION_UP && !hadMultiTouch && zoom<=1.02f &&
                    kotlin.math.abs(e.x-swipeStartX)>dp(76f) && kotlin.math.abs(e.y-swipeStartY)<dp(54f))
                    onHorizontalSwipe?.invoke(if(e.x>swipeStartX)-1 else 1)
                pinchStart=0f;parent?.requestDisallowInterceptTouchEvent(false)''',
 '''                val direction=if(e.actionMasked==MotionEvent.ACTION_UP)
                    swipeTracker.up(e.x,e.y,zoom<=1.02f)
                else {swipeTracker.cancel();0}
                if(direction!=0)onHorizontalSwipe?.invoke(direction)
                pinchStart=0f;parent?.requestDisallowInterceptTouchEvent(false)''', 'inspector finish')
])

# The review screen keeps the existing spinner/list semantics and has no extra
# buttons. This method must remain accessible from BOTH viewers.
activity=(app/'AdminOcrRecropActivity.kt').read_text(encoding='utf-8')
for marker in ('preview.onHorizontalSwipe={delta->moveBySwipe(delta)}',
               'selectedCrop.onHorizontalSwipe={delta->moveBySwipe(delta)}',
               'if(loading||saving||keys.isEmpty())return',
               'if(next!=index)spinner.setSelection(next)'):
    assert marker in activity,f'missing swipe navigation {marker}'
assert 'BuildConfig.HIGI_DRY_BUILD' in activity

# Release metadata must stay at 0.15.197: this is NOT a version or deploy.
gradle=(root/'app/build.gradle.kts').read_text(encoding='utf-8')
assert 'versionCode = 347' in gradle and 'versionName = "0.15.197"' in gradle
print('WIP_PATCH_OK: no version bump, no Canonical/Firebase changes')