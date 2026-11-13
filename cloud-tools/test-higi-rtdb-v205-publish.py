#!/usr/bin/env python3
"""Pure offline contract tests for the no-ETag RTDB publish path.
No network, Google credentials, GitHub secrets or Firebase production access.
"""
import importlib.util
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

S=Path(__file__).with_name('higi-rtdb-v205-deploy.py')
spec=importlib.util.spec_from_file_location('higi_rtdb_v205_deploy',S)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ORIGINAL={'rules':{'.read':False,'.write':False,'canonicalPuzzles':{'$puzzleKey':{'.write':'old'}}}}
CANDIDATE={'rules':{'.read':False,'.write':False,'canonicalPuzzles':{'$puzzleKey':{'.write':'old','revision':{'.write':'added'}}}}}
ENDPOINT='https://higi-8b169-default-rtdb.europe-west1.firebasedatabase.app/.settings/rules.json'

def files(target,etag=''):
  (target/'live-original.json').write_text(json.dumps(ORIGINAL),encoding='utf8')
  (target/'candidate.json').write_text(json.dumps(CANDIDATE),encoding='utf8')
  (target/'audit.json').write_text(json.dumps({
    'live_sha256':m.digest(ORIGINAL),'candidate_sha256':m.digest(CANDIDATE),'etag':etag
  }),encoding='utf8')

def case(name, confirmation, responses, calls_expected, succeed, tag=''):
  with TemporaryDirectory() as d:
    target=Path(d)
    files(target,tag)
    requests=[]
    def fake_get(token,endpoint):
      assert endpoint==ENDPOINT
      x=responses[len(requests)]
      requests.append(('GET',x))
      return x
    puts=[]
    def fake_put(token,endpoint,doc,etag):
      puts.append((doc,etag))
      return 200
    with patch.object(m,'get_rules',side_effect=fake_get),patch.object(m,'put_rules',side_effect=fake_put),patch.dict(os.environ,{'HIGI_PUBLISH_CONFIRM':confirmation}):
      try:
        m.publish('fake','%s'%ENDPOINT,target)
        assert succeed,name+': unexpectedly succeeded'
      except RuntimeError:
        assert not succeed,name+': unexpectedly failed'
    assert len(requests)==calls_expected,(name,'get calls',len(requests))
    assert len(puts)==int(succeed),(name,'put calls',len(puts))
    if puts:
      assert puts[0][0]==CANDIDATE
      assert puts[0][1]==tag
    print('PASS',name)

case('no-ETag guarded PUT succeeds with double-check',
     'PUBLISH-NONATOMIC-0.15.205',[(ORIGINAL,''),(ORIGINAL,''),(CANDIDATE,'')],3,True)
case('old confirmation fails without ETag',
     'PUBLISH-0.15.205',[(ORIGINAL,'')],1,False)
case('changed rules fail before PUT',
     'PUBLISH-NONATOMIC-0.15.205',[(CANDIDATE,'')],1,False)
case('last-second changed rules fail',
     'PUBLISH-NONATOMIC-0.15.205',[(ORIGINAL,''),(CANDIDATE,'')],2,False)
case('ETag appears on last check -> abort',
     'PUBLISH-NONATOMIC-0.15.205',[(ORIGINAL,''),(ORIGINAL,'newtag')],2,False)
case('previously-present ETag disappears -> abort',
     'PUBLISH-NONATOMIC-0.15.205',[(ORIGINAL,'')],1,False,'oldtag')
case('ETag normal conditional PUT success',
     'PUBLISH-0.15.205',[(ORIGINAL,'oldtag'),(CANDIDATE,'newtag')],2,True,'oldtag')
print('PASSED 7 no-network publish regression scenarios')
