#!/usr/bin/env python3
"""Read-only verification for six exact administrator-approved HAFUCH_DEKEL crops."""
import hashlib,io,json,sys,zipfile
from PIL import Image
from pathlib import Path

def verify(original_zip,fixture_json):
    data=json.loads(Path(fixture_json).read_text(encoding='utf8'))
    assert data['series_id']=='HAFUCH_DEKEL'
    assert data['state']=='ADMIN_VISUAL_CONFIRMATION_FIXTURES'
    assert data['confirmed_date']=='2026-11-19'
    assert data['regression_policy']['may_auto_write_canonical'] is False
    assert data['regression_policy']['may_auto_write_firebase'] is False
    assert len(data['crops'])==6
    assert len({(c['date'],c['direction'],c['number']) for c in data['crops']})==6
    with zipfile.ZipFile(original_zip) as z:
        for date,source in data['sources'].items():
            raw=z.read('hafuch-20-source-results/images/'+date+'.jpg')
            assert hashlib.sha256(raw).hexdigest()==source['sha256'],date
            with Image.open(io.BytesIO(raw)) as im:
                assert im.size==(source['width'],source['height'])
                rgb=im.convert('RGB')
                for crop in (c for c in data['crops'] if c['date']==date):
                    assert crop['status']=='VISUAL_CROP_CONFIRMED'
                    assert len(crop['row_rectangles'])==len(crop['rgb_row_sha256'])
                    for rect,digest in zip(crop['row_rectangles'],crop['rgb_row_sha256']):
                        x0,y0,x1,y1=rect
                        assert 0<=x0<x1<=im.width and 0<=y0<y1<=im.height
                        assert hashlib.sha256(rgb.crop((x0,y0,x1,y1)).tobytes()).hexdigest()==digest,(date,crop['direction'],crop['number'],rect)
    print('PASS: 6 approved crop geometries, exact publisher SHA and source pixel hashes, no external writes')
if __name__=='__main__':
    if len(sys.argv)==3:verify(*sys.argv[1:])
    else:raise SystemExit('Usage: verify_six_admin_confirmed_crops.py original-images.zip fixtures.json')
