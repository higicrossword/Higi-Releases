#!/usr/bin/env python3
"""Guarded Higi 0.15.205 Realtime Database rules release, via official REST API.

Used only by manually dispatched GitHub Actions with WIF credentials.
Does NOT alter production until the explicit 'publish' step.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

EXPECTED_PARENT_SHA256 = 'f172d02f4b7b17ebe4c747584908d7b7a52a1dcc7b6df38f193c5bb7ca629802'
TARGET_BRANCH = ('canonicalPuzzles', '$puzzleKey')
EXPECTED_FIELDS = frozenset({
    'sourceImageUrl', 'revision', 'updatedAt', 'lastEditedBy',
    'lastEditedByName', 'clueRegionsRevision', 'clueRegions',
    'clueRegionLines', 'clueRegionEvidence', 'clueRegionEdits', 'clueApprovals',
})
HERE = Path(__file__).resolve().parent
PATCHER = HERE / 'higi-image-child-rules-patch.py'


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def rules_url(raw):
    parsed = urllib.parse.urlsplit(raw.rstrip('/'))
    host = (parsed.hostname or '').lower()
    accepted = (
        host in ('higi-8b169.firebaseio.com', 'higi-8b169-default-rtdb.firebaseio.com')
        or (host.startswith('higi-8b169-') and host.endswith('.firebasedatabase.app'))
    )
    if (parsed.scheme != 'https' or not accepted or parsed.username or parsed.password or
        parsed.port is not None or parsed.query or parsed.fragment or parsed.path):
        raise ValueError('HIGI_RTDB_URL must be the exact higi-8b169 HTTPS database root URL')
    return raw.rstrip('/') + '/.settings/rules.json'


def parse_rules(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('rules'), dict):
        raise ValueError('Live database returned invalid rules JSON; refusing deployment')
    return raw


def get_rules(token, endpoint):
    req = urllib.request.Request(endpoint, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
        'X-Firebase-ETag': 'true',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return parse_rules(json.load(res)), (res.headers.get('ETag') or '').strip()
    except urllib.error.HTTPError as ex:
        if ex.code != 400:
            raise
        # Some RTDB rules endpoints do not advertise ETag support.
        # Retry GET without the optional header, never retry PUT.
        req.remove_header('X-firebase-etag')
        with urllib.request.urlopen(req, timeout=30) as res:
            return parse_rules(json.load(res)), (res.headers.get('ETag') or '').strip()


def put_rules(token, endpoint, document, etag):
    payload = json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
    }
    # Only use a conditional PUT when the rules endpoint returned an ETag.
    # If the endpoint rejects If-Match, do not retry the write.
    if etag:
        headers['If-Match'] = etag
    req = urllib.request.Request(endpoint, headers=headers, data=payload, method='PUT')
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.status


def patch_live(live, output_dir):
    base = live['rules']
    if base.get('.read') is not False or base.get('.write') is not False:
        raise ValueError('Root RTDB access differs from trusted baseline; abort')
    parent = base.get('canonicalPuzzles', {}).get('$puzzleKey', {})
    if not isinstance(parent, dict) or hashlib.sha256(str(parent.get('.write', '')).encode()).hexdigest() != EXPECTED_PARENT_SHA256:
        raise ValueError('canonicalPuzzles parent write rule has changed; requires explicit security review')
    if not PATCHER.is_file():
        raise FileNotFoundError('Pinned image-only patcher missing')

    baseline_path = output_dir / 'live-original.json'
    candidate_path = output_dir / 'candidate.json'
    baseline_path.write_text(json.dumps(live, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    subprocess.run([sys.executable, str(PATCHER), str(baseline_path), str(candidate_path)], check=True)
    candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
    before = copy.deepcopy(live)
    after = copy.deepcopy(candidate)
    original_parent = before['rules']['canonicalPuzzles']['$puzzleKey']
    patched_parent = after['rules']['canonicalPuzzles']['$puzzleKey']
    changed = set()
    for key in EXPECTED_FIELDS:
        if key not in patched_parent or '.write' not in patched_parent[key]:
            raise ValueError('Expected child write rule missing: ' + key)
        if key in original_parent and '.write' in original_parent[key]:
            raise ValueError('Existing write rule must not be overwritten: ' + key)
        changed.add(key)
        del patched_parent[key]['.write']
        if not patched_parent[key] and key not in original_parent:
            del patched_parent[key]
    if changed != EXPECTED_FIELDS or before != after:
        raise ValueError('Candidate changes unexpected rules: reject')
    return candidate


def prepare(token, endpoint, target_dir):
    live, etag = get_rules(token, endpoint)
    candidate = patch_live(live, target_dir)
    m = {'project': 'higi-8b169', 'live_sha256': digest(live),
         'candidate_sha256': digest(candidate),
         'changed_fields': sorted(EXPECTED_FIELDS), 'etag': etag,
         'mode': 'PREPARED_ONLY'}
    (target_dir / 'audit.json').write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')
    print('PASS: live rules fetched; precisely 11 child write rules added')
    print('Live SHA256:', m['live_sha256'])
    print('Candidate SHA256:', m['candidate_sha256'])
    print('ETag present:', bool(etag))
    return m


def publish(token, endpoint, target_dir):
    m = json.loads((target_dir / 'audit.json').read_text(encoding='utf-8'))
    original = json.loads((target_dir / 'live-original.json').read_text(encoding='utf-8'))
    candidate = json.loads((target_dir / 'candidate.json').read_text(encoding='utf-8'))
    if digest(original) != m['live_sha256'] or digest(candidate) != m['candidate_sha256']:
        raise ValueError('Prepared files changed after audit; refusing to publish')
    # Recheck before PUT. Without ETag support there remains a small race window.
    current, tag = get_rules(token, endpoint)
    if digest(current) != m['live_sha256'] or (m['etag'] and m['etag'] != tag):
        raise RuntimeError('Firebase rules changed after backup; publish aborted')
    if not tag:
        raise RuntimeError('Rules endpoint did not return a usable ETag; refusing non-conditional publish')
    result = put_rules(token, endpoint, candidate, tag)
    print('Firebase REST publish returned status:', result)
    actual, _ = get_rules(token, endpoint)
    if digest(actual) != m['candidate_sha256']:
        raise RuntimeError('POST-PUBLISH VERIFIED RULES DIFFER; investigate and restore backup')
    print('PASS: published rules confirmed via second independent server GET')


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('prepare', 'publish'):
        raise SystemExit('Usage: higi-rtdb-v205-deploy.py prepare|publish')
    token = os.environ.get('FIREBASE_ACCESS_TOKEN', '').strip()
    if len(token) < 30:
        raise ValueError('Missing short-lived Firebase OAuth access token')
    endpoint = rules_url(os.environ.get('HIGI_RTDB_URL', '').strip())
    out_arg = os.environ.get('HIGI_RULES_OUT', '').strip()
    if not out_arg or not Path(out_arg).is_absolute():
        raise ValueError('HIGI_RULES_OUT must be an absolute private temporary directory')
    target_dir = Path(out_arg).resolve()
    if target_dir == Path('/'):
        raise ValueError('HIGI_RULES_OUT must not be filesystem root')
    target_dir.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == 'prepare':
        prepare(token, endpoint, target_dir)
    else:
        if os.environ.get('HIGI_PUBLISH_CONFIRM') != 'PUBLISH-0.15.205':
            raise ValueError('Missing explicit publish confirmation')
        publish(token, endpoint, target_dir)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as ex:
        print('BLOCKED:', ex, file=sys.stderr)
        sys.exit(2)
    except urllib.error.HTTPError as ex:
        print('BLOCKED: Firebase REST HTTP', ex.code, '(no credentials printed)', file=sys.stderr)
        sys.exit(3)
