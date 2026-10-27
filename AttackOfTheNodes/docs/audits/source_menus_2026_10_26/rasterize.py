"""Rasterize native Textual SVG exports; no invented UI styling."""
from pathlib import Path
import sys
sys.path.insert(0, '/tmp/aotn-ui-review-rendering')
import cairosvg
from PIL import Image, ImageDraw
out=Path(__file__).resolve().parent
for svg in out.glob('*.svg'):
    source=svg.read_text().replace('Fira Code','DejaVu Sans Mono')
    cairosvg.svg2png(bytestring=source.encode(),write_to=str(svg.with_suffix('.png')))
files=sorted(out.glob('*.png'))
files=[f for f in files if f.name!='contact-sheet.png']
thumbs=[]
for path in files:
    img=Image.open(path).convert('RGB');img.thumbnail((550,400))
    tile=Image.new('RGB',(570,430),'#20242b');tile.paste(img,(10,25))
    ImageDraw.Draw(tile).text((10,6),path.stem,fill='white');thumbs.append(tile)
sheet=Image.new('RGB',(1140,430*((len(thumbs)+1)//2)),'#20242b')
for i,tile in enumerate(thumbs):sheet.paste(tile,((i%2)*570,(i//2)*430))
sheet.save(out/'contact-sheet.png')
