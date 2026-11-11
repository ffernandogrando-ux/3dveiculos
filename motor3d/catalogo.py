"""Renderiza o catálogo visual das peças (catalogo.jpg). Rode de novo sempre que adicionar peças.

Uso:  python catalogo.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import motor as mt
import pecas as pc
from motor import mat, house, terrain, far_ground, Sky, empty, ball, mosaic_mat, stones_mat, box
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "catalogo")
os.makedirs(OUT, exist_ok=True)
mt.setup(1.0, samples=8)
M = {n: mat(n, c) for n, c in [("grass", "#6cc24a"), ("soft", "#c8945c"), ("mid", "#a87447"), ("firm", "#8a5d3b"),
                                 ("aquifer", "#86b4d8"), ("rock", "#6e6c75"), ("base", "#9b9ba0"), ("fence", "#ffffff")]}
pc.materiais(M)
M["trash"] = mosaic_mat("trash", base="#5a5047", sat=1.0, mix=0.55, val=0.72, scale=3.2)
M["gravel"] = stones_mat("gravel", light="#a39d92", dark="#5e5a55", scale=5.5)
Sky()
far_ground(M, y0=14)

ITEMS = []      # (rótulo, x, câmera, alvo)
SP = 16.0
terrain("cat", -10, SP * 18, [(0, 14, [])], M)


def slot(label, near=True, tall=False):
    x = len(ITEMS) * SP
    if tall:
        cam, tgt = (x + 5, -24, 8), (x, 2.5, 4.5)
    elif near:
        cam, tgt = (x + 3.5, -11, 4.0), (x, 2.0, 0.9)
    else:
        cam, tgt = (x + 4, -16, 5), (x, 2.0, 1.2)
    ITEMS.append((label, x, cam, tgt))
    return x


x = slot("caminhao() basculante", near=False); r, h = pc.caminhao("cam", M); r.location = (x, 2.5, 0); h.rotation_euler = (0, math.radians(-35), 0)
x = slot("rolo_compactador()"); r, _ = pc.rolo_compactador("rolo", M); r.location = (x, 2.5, 0)
x = slot("trator_esteira()"); pc.trator_esteira("trat", M).location = (x, 2.5, 0)
x = slot("carro()"); pc.carro("carro", M).location = (x, 2.5, 0)
x = slot("bate_estaca()", tall=True); r, ham = pc.bate_estaca("bate", M); r.location = (x, 1.0, 0); ham.location = (0, 0, 3.0)
x = slot("helice() estaca hélice", tall=True); pc.helice("hel", M).location = (x, 1.5, 0.2)
x = slot("predio() 20 andares", tall=True); pc.predio("pred", M).location = (x, 3.0, 0)
x = slot("usina() + raio_icone() + poste()", near=False); pc.usina("usi", M).location = (x, 3.0, 0); pc.raio_icone("raio", M, x, 3.9, 1.25, 1.35)
p1 = pc.poste("pos1", M, x + 3.5, 1.2); pc.fio("fio1", M, (x + 1.6, 3.0, 2.4), (x + 3.5, 1.2, 4.05))
x = slot("poco() em corte + pessoa()", near=False); pc.poco("poco", M, x); pc.pessoa("pes", M).location = (x + 2.0, 1.4, 0)
x = slot("house() + rachaduras()", near=False); house("casa", x, 1.0, M)
for s in pc.rachaduras("rach", M, [(x - 1.2, 2.5), (x - 0.95, 2.1), (x - 1.15, 1.7), (x - 0.85, 1.3), (x - 1.05, 0.9)], 0.96):
    pass
x = slot("urubu()"); u, asas = pc.urubu("uru", M); u.location = (x, 2.5, 2.0); u.rotation_euler = (0, math.radians(15), math.radians(-60))
x = slot("rato() + junk()"); pc.rato("rato", M).location = (x - 0.6, 2.0, 0)
for i in range(7):
    pc.junk(f"lixo{i}", M, 0.45).location = (x + 0.6 + (i % 4) * 0.55, 1.6 + (i // 4) * 0.7, 0)
x = slot("fogo() / chama()"); r, _ = pc.chama("chama", M, 1.3); r.location = (x, 2.0, 0)
x = slot("jornal()"); j = pc.jornal("jor", M); j.location = (x, 1.0, 1.2); j.scale = (1.3, 1.3, 1.3)
x = slot("mosaic_mat() lixo / stones_mat() brita"); box("mos", x - 2.6, x - 0.2, 0.5, 3.0, 0, 2.2, M["trash"]); box("bri", x + 0.2, x + 2.6, 0.5, 3.0, 0, 2.2, M["gravel"])

scene = mt.scene
names = []
for i, (label, x, cam, tgt) in enumerate(ITEMS):
    cd = bpy.data.cameras.new(f"ccam{i}"); cd.lens = 35
    c = mt.link(bpy.data.objects.new(f"ccam{i}", cd)); c.location = cam
    t = empty(f"ctgt{i}", tgt)
    con = c.constraints.new("TRACK_TO"); con.target = t; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    scene.camera = c
    scene.render.resolution_x, scene.render.resolution_y = 432, 540
    p = os.path.join(OUT, f"{i:02d}.png")
    scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    names.append((p, label))

# folha do catálogo
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
cols = 5
rows = math.ceil(len(names) / cols)
W, H, L = 432, 540, 34
sheet = Image.new("RGB", (cols * W, rows * (H + L)), "white")
d = ImageDraw.Draw(sheet)
for i, (p, label) in enumerate(names):
    cx, cy = (i % cols) * W, (i // cols) * (H + L)
    sheet.paste(Image.open(p).convert("RGB"), (cx, cy + L))
    d.text((cx + 10, cy + 8), label, font=font, fill=(25, 25, 25))
sheet.save(os.path.join(HERE, "catalogo.jpg"), quality=88)
print("catálogo:", os.path.join(HERE, "catalogo.jpg"))
