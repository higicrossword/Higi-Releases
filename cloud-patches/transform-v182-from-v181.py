#!/usr/bin/env python3
"""DRY-only Higi 0.15.182 OCR inline recovery hardening.
Requires exact 0.15.181 source, refuses inconsistent input.
No clue text decoding, AI call, canonical write or backend change.
"""
from pathlib import Path
import subprocess
import sys

root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()
target=root/"app/src/main/java/com/example/hebrewcrossword/OcrInlineClueRecoveryV180.kt"
s=target.read_text(encoding="utf-8")

def replace_once(before,after):
    global s
    if s.count(before)!=1:
        raise RuntimeError("Unexpected V181 source: "+repr(before[:100]))
    s=s.replace(before,after,1)

for old,new in [
    (r'Regex("^(?:מאוזן|אופקי)\\s*[:.]$")',
     r'Regex("^(?:ב?מאוזן|אופקי)\\s*[:.]$")'),
    (r'Regex("^(?:מאונך|אנכי)\\s*[:.]$")',
     r'Regex("^(?:ב?מאונך|אנכי)\\s*[:.]$")'),
    (r'Regex("^(?:מאוזן|אופקי)\\s*[:.]")',
     r'Regex("^(?:ב?מאוזן|אופקי)\\s*[:.]")'),
    (r'Regex("^(?:מאונך|אנכי)\\s*[:.]")',
     r'Regex("^(?:ב?מאונך|אנכי)\\s*[:.]")'),
]:
    replace_once(old,new)

replace_once("""            val allAnchors=candidates.flatMap{it.third}
            val counts=allAnchors.groupingBy{it.number}.eachCount()
            val duplicates=counts.filterValues{it>1}.keys
""","")
replace_once("""                val invalid=numbered.any{it.number in duplicates} ||
                    numbered.zipWithNext().any{(a,b)->a.number>=b.number} ||
                    numbered.any{it.number<=previousNumber}
                if(invalid){
                    active=null
                    numbered.forEach{errors.putIfAbsent("${section.direction}${it.number}",
                        "V180_DUPLICATE_OR_OUT_OF_ORDER_PRINTED_NUMBER")}
                    continue
                }
""","""                // A later OCR marker may repeat a previously used number when a
                // leading digit is missed (e.g. printed 17 read as 7). Quarantine
                // that marker, but do not retroactively reject an earlier valid
                // clue or lose later, independently anchored numbers on this row.
                val stale=numbered.filter{it.number<=previousNumber}
                if(stale.isNotEmpty()){
                    active=null
                    stale.forEach{a->
                        val label="${section.direction}${a.number}"
                        // The first valid occurrence was already recovered;
                        // a later OCR misread must not mark it as unresolved.
                        if(label !in byKey) errors.putIfAbsent(label,
                            "V182_STALE_OR_MISREAD_PRINTED_NUMBER")
                    }
                }
                val forward=numbered.filter{it.number>previousNumber}
                // A stale marker is safe to ignore ONLY when it is to the
                // right of every currently forward anchor; otherwise the
                // current printed line is ambiguous and must not be split.
                if(stale.isNotEmpty() && forward.isNotEmpty() &&
                    stale.any{it.box.right<=forward.first().box.right}){
                    active=null
                    forward.forEach{errors.putIfAbsent("${section.direction}${it.number}",
                        "V182_INTERLEAVED_STALE_PRINTED_NUMBER")}
                    continue
                }
                if(forward.zipWithNext().any{(a,b)->a.number>=b.number}){
                    active=null
                    forward.forEach{errors.putIfAbsent("${section.direction}${it.number}",
                        "V180_DUPLICATE_OR_OUT_OF_ORDER_PRINTED_NUMBER")}
                    continue
                }
""")
start=s.index("                val cuts=mutableListOf<Int>()")
end=s.index("            }\n            for((key,entry) in byKey)",start)
segment=s[start:end]
if segment.count("numbered")!=9:
    raise RuntimeError("Unexpected number-loop references: "+str(segment.count("numbered")))
s=s[:start]+segment.replace("numbered","forward")+s[end:]
target.write_text(s,encoding="utf-8")

gradle=root/"app/build.gradle.kts"
g=gradle.read_text()
for before,after in [
    ("versionCode = 331","versionCode = 332"),
    ('versionName = "0.15.181"','versionName = "0.15.182"'),
]:
    if g.count(before)!=1: raise RuntimeError("Unexpected build version")
    g=g.replace(before,after,1)
gradle.write_text(g)
subprocess.run([sys.executable,str(root/"tools/sync-release-version.py"),"--write","--root",str(root)],check=True)
subprocess.run([sys.executable,str(root/"tools/sync-release-version.py"),"--check","--root",str(root)],check=True)
print("Higi 0.15.182 DRY migration complete; canonical state unchanged.")
