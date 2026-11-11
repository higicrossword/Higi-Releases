import numpy as np
from PIL import Image
from pathlib import Path

def grid_signature(path):
 im=Image.open(path).convert('L'); w,h=im.size; a=np.asarray(im)
 xx=int(.63*w); yy=int(.21*h); X=int(.998*w); Y=int(.96*h)
 roi=(a[yy:Y,xx:X]<105)
 yp=roi.mean(axis=1);xp=roi.mean(axis=0)
 def clusters(q,th):
  ids=np.where(q>=th)[0];out=[]
  for i in ids:
   if not out or i>out[-1][-1]+1:out.append([i])
   else:out[-1].append(i)
  return [float(np.mean(z)) for z in out]
 def select(coords):
  if len(coords)<10:return None
  best=None
  for i in range(len(coords)-9):
   cur=coords[i:i+10];dif=np.diff(cur);med=np.median(dif)
   dev=float(np.max(np.abs(dif-med))/max(1,med))
   if best is None or dev<best[0]:best=(dev,cur,med)
  return best
 sx=select(clusters(xp,.68));sy=select(clusters(yp,.69))
 if sx is None or sy is None:return {'error':'missing 10 grid lines'}
 if sx[0]>.2 or sy[0]>.2:return {'error':'irregular grid spacing','xerror':sx[0],'yerror':sy[0]}
 rows=[]
 for j in range(9):
  row=''
  for k in range(9):
   u=int(xx+(sx[1][k]+sx[1][k+1])/2)
   v=int(yy+(sy[1][j]+sy[1][j+1])/2)
   row+='X' if a[v,u]<120 else '.'
  rows.append(row)
 return {'grid':'/'.join(rows),'xspacing':round(float(sx[2]),2),'yspacing':round(float(sy[2]),2),'xmaxerror':round(float(sx[0]),3),'ymaxerror':round(float(sy[0]),3)}
