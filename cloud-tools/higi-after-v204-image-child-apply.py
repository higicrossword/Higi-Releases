#!/usr/bin/env python3
"""Unreleased post-0.15.204 proof: replace whole-record transaction with child multipath update.
No versionCode change. This prepares an integration candidate only.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1])/"app/src/main/java/com/example/hebrewcrossword"
p=root/"CanonicalPuzzleCloud.kt"
s=p.read_text(encoding='utf-8')
start=s.find("    fun replaceCanonicalSourceImageOnly(")
end=s.find("    /**\n     * User clue corrections are canonical.",start)
if start<0 or end<0:raise RuntimeError("Expected v204 method markers missing; fail closed")
old=s[start:end]
assert old.count("ref.runTransaction(")==1
assert old.count('data.child("clues")')==0
new='''    /**
     * Canonical image-only update (unreleased candidate).
     * A multi-path update is checked per child by RTDB Security Rules.
     * Revision is checked against current server value inside child .write rules:
     * this prevents stale preflight snapshots from replacing a newer image.
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
                ref.get().addOnSuccessListener { snapshot ->
                    val prevUrl=snapshot.child("sourceImageUrl").value as? String ?: ""
                    if(!snapshot.exists() || snapshot.child("issueKey").value!=issueKey ||
                        (snapshot.child("schema").value as? Number)?.toInt()!=SCHEMA ||
                        (snapshot.child("parserSchema").value as? Number)?.toInt()!=PARSER_SCHEMA ||
                        snapshot.child("gridSignature").value!=expectedGridSignature ||
                        LocalOcrGeometryAuthority.sourceIdentity(prevUrl)!=
                            LocalOcrGeometryAuthority.sourceIdentity(expectedSourceImageUrl) ||
                        LocalOcrGeometryAuthority.sourceIdentity(replacementUrl)==
                            LocalOcrGeometryAuthority.sourceIdentity(prevUrl)){
                        callback(Result.failure(IllegalStateException("התשבץ או תמונתו השתנו; יש לפתוח מחדש")))
                        return@addOnSuccessListener
                    }
                    val oldRevision=(snapshot.child("revision").value as? Number)?.toLong()
                    if(oldRevision==null || oldRevision<1 || oldRevision==Long.MAX_VALUE){
                        callback(Result.failure(IllegalStateException("גרסת התשבץ אינה תקינה")))
                        return@addOnSuccessListener
                    }
                    val newRevision=oldRevision+1L
                    val updates=hashMapOf<String,Any?>(
                        "sourceImageUrl" to replacementUrl,
                        "revision" to newRevision,
                        "updatedAt" to System.currentTimeMillis(),
                        "lastEditedBy" to uid,
                        "lastEditedByName" to editorName.trim().take(40),
                        "clueRegionsRevision" to newRevision,
                        "clueRegions" to null,
                        "clueRegionLines" to null,
                        "clueRegionEvidence" to null,
                        "clueRegionEdits" to null,
                        "clueApprovals" to null
                    )
                    // This is NOT a parent transaction. Each changed child requires
                    // authorization, and no grid/clue/answer path is ever included.
                    ref.updateChildren(updates).addOnCompleteListener { task ->
                        if(!task.isSuccessful){
                            callback(Result.failure(task.exception ?:
                                IllegalStateException("עדכון התמונה נדחה; ייתכן שהתשבץ השתנה")))
                        }else{
                            // Do not mark success based solely on local cache.
                            ref.get().addOnSuccessListener { confirmed ->
                                if(confirmed.child("sourceImageUrl").value!=replacementUrl ||
                                    ((confirmed.child("revision").value as? Number)?.toLong() ?: 0L) < newRevision){
                                    callback(Result.failure(IllegalStateException("האימות מול שרת Firebase נכשל")))
                                }else{
                                    DebugLog.i("CANONICAL_IMAGE_REPLACE",
                                        "image-only-server-confirmed issue="+DebugLog.compactId(issueKey)+
                                        " revision="+newRevision)
                                    callback(Result.success(newRevision))
                                }
                            }.addOnFailureListener {callback(Result.failure(it))}
                        }
                    }
                }.addOnFailureListener { callback(Result.failure(it)) }
            },{callback(Result.failure(it))})
        }
    }

'''
assert "ref.runTransaction(" not in new
p.write_text(s[:start]+new+s[end:],encoding='utf-8')
print("POST-204 CHILD-SCOPED IMAGE WRITE STAGED (NO RELEASE)")
