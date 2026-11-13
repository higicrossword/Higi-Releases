#!/usr/bin/env python3
"""Higi 0.15.205-DRY: integrate tested child-scoped image swap on v0.15.204.
Only the known Canonical image-write method and release version are changed.
"""
from pathlib import Path
import subprocess
import sys

if len(sys.argv)!=2:
    raise SystemExit("Usage: python higi-v205-apply.py <source-root>")
root=Path(sys.argv[1]).resolve()
pkg=root/"app/src/main/java/com/example/hebrewcrossword"
cloud=pkg/"CanonicalPuzzleCloud.kt"
gradle=root/"app/build.gradle.kts"
assert cloud.is_file() and gradle.is_file()
before=cloud.read_text(encoding="utf-8")
assert before.count("    fun replaceCanonicalSourceImageOnly(")==1
assert "ref.runTransaction(" in before[before.index("    fun replaceCanonicalSourceImageOnly("):before.index("    /**\n     * User clue corrections are canonical.")]
subprocess.run([sys.executable,str(Path(__file__).with_name("higi-after-v204-image-child-apply.py")),str(root)],check=True)
after=cloud.read_text(encoding="utf-8")
a=after.index("    fun replaceCanonicalSourceImageOnly(")
b=after.index("    /**\n     * User clue corrections are canonical.",a)
method=after[a:b]
assert "ref.updateChildren(updates)" in method
assert "ref.runTransaction(" not in method
assert '"sourceImageUrl" to replacementUrl' in method
assert '"revision" to newRevision' in method
assert '"clueRegions" to null' in method
assert "AdminAccess(context).loadRole" in method
assert '"clues" to' not in method and '"answers" to' not in method
assert "LocalOcrGeometryAuthority.sourceIdentity" in method
g=gradle.read_text(encoding="utf-8")
assert g.count("versionCode = 354")==1 and g.count('versionName = "0.15.204"')==1
gradle.write_text(g.replace("versionCode = 354","versionCode = 355").replace('versionName = "0.15.204"','versionName = "0.15.205"'),encoding="utf-8")
print("PASS Higi 0.15.205-DRY: child-only source image swap, DRY state retained; source ready for sync and tests")
