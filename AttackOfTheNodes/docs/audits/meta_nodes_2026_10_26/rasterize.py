"""Offline PNG companions for real Textual SVGs; local font substitution only."""
from pathlib import Path
import sys
sys.path.insert(0,'/tmp/aotn-ui-review-rendering')
import cairosvg
from PIL import Image, ImageDraw
OUT=Path(__file__).resolve().parent
images=[]
for source in sorted(OUT.glob('*.svg')):
 data=source.read_text().replace('font-family: Fira Code, monospace;','font-family: "DejaVu Sans Mono";')
 target=source.with_suffix('.png')
 cairosvg.svg2png(bytestring=data.encode(),write_to=str(target))
 image=Image.open(target).convert('RGB');image.thumbnail((520,400))
 tile=Image.new('RGB',(540,440),'#111111');tile.paste(image,((540-image.width)//2,28))
 ImageDraw.Draw(tile).text((8,6),source.stem,fill='#ffffff');images.append(tile)
sheet=Image.new('RGB',(2160,440*((len(images)+3)//4)),'#111111')
for i,tile in enumerate(images):sheet.paste(tile,((i%4)*540,(i//4)*440))
sheet.save(OUT/'contact-sheet.png')
print(len(images),'PNG companions and contact sheet written')
