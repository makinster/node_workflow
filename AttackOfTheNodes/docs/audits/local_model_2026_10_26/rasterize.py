"""Offline PNG companions; font substitution only, no UI styling changes."""
from pathlib import Path
import sys

sys.path.insert(0, '/tmp/aotn-ui-review-rendering')
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import cairosvg
from PIL import Image, ImageDraw
from frontend import colors

out=Path(__file__).resolve().parent
images=[]
for source in sorted(out.glob('*.svg')):
    data=source.read_text().replace('font-family: Fira Code, monospace;',
                                   'font-family: "DejaVu Sans Mono";')
    target=source.with_suffix('.png')
    cairosvg.svg2png(bytestring=data.encode(),write_to=str(target))
    image=Image.open(target).convert('RGB');image.thumbnail((520,410))
    tile=Image.new('RGB',(540,440),colors.PANEL_BACKGROUND)
    tile.paste(image,((540-image.width)//2,25))
    ImageDraw.Draw(tile).text((8,5),source.name,fill=colors.NAME)
    images.append(tile)
sheet=Image.new('RGB',(2160,440*((len(images)+3)//4)),colors.PANEL_BACKGROUND)
for i,tile in enumerate(images):sheet.paste(tile,((i%4)*540,(i//4)*440))
sheet.save(out/'contact-sheet.png')
print(f'{len(images)} PNG companions and contact sheet written.')
