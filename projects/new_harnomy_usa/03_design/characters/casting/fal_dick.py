import os, sys, urllib.request
from dotenv import load_dotenv
load_dotenv(r'C:/Users/bradu/Documents/ilyrium-autostudio/.env', override=False)
load_dotenv(r'C:/Users/bradu/Documents/slm-foundry/.env', override=False)
import fal_client

SRC = r'C:\Users\bradu\Documents\ilyrium-autostudio\projects\new_harnomy_usa\03_design\characters\casting\caste\DIC-K02.png'
OUT = r'C:\Users\bradu\Documents\ilyrium-autostudio\projects\new_harnomy_usa\03_design\characters\casting\dick_v2'
os.makedirs(OUT, exist_ok=True)

url = fal_client.upload_file(SRC)
print('uploaded:', url[:70], flush=True)

HOLD = ('Keep this exact man: same face, same bone structure, same tan and skin, same '
        'gym-built shoulders, same heritage workwear jacket over a plain fitted tee, '
        'same plain grey backdrop, same even neutral lighting. Photographic realism, '
        '85mm, sharp focus on the eyes, mouth closed with the lips together, jaw '
        'relaxed, eyes steady on the lens, unbothered and certain.')

JOBS = [
 ('DIC-K02-hair',
  'Change ONLY the hair: make it dirty blond and slightly longer, worn loose and '
  'falling to the collarbone, thick enough to be gathered into a man-bun at a '
  "minute's notice - the carefully maintained 'I do not care' cut that takes an "
  'expensive barber to look effortless. ' + HOLD),
 ('DIC-K02-bun',
  'Change ONLY the hair: dirty blond, gathered up into a neat man-bun at the crown '
  'with a few loose strands at the temples, the sides swept back cleanly. ' + HOLD),
]

for name, prompt in JOBS:
    print('--', name, flush=True)
    r = fal_client.subscribe('fal-ai/nano-banana-pro/edit', arguments={
        'prompt': prompt,
        'image_urls': [url],
        'aspect_ratio': '3:2',
        'resolution': '2K',
        'output_format': 'png',
        'num_images': 1,
    })
    imgs = r.get('images') or []
    if not imgs:
        print('   NO IMAGE', r); continue
    dst = os.path.join(OUT, name + '.png')
    urllib.request.urlretrieve(imgs[0]['url'], dst)
    print('   saved', dst, os.path.getsize(dst)//1024, 'KB', flush=True)
print('DONE')
