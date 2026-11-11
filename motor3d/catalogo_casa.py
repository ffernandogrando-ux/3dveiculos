"""Catálogo visual das peças de CASA (canal "dentro da sua casa"): catalogo_casa.jpg. Rode de novo ao criar peças.

Uso:  python catalogo_casa.py
Cada peça num cantinho (piso + parede) com a função que a cria. As peças de obra/terreno estão no catalogo.py.
"""
import os, sys, math, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import motor as mt
import pecas as pc
from motor import mat, Sky, empty, box, lin
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = tempfile.mkdtemp(prefix="catalogo_casa_")
mt.setup(4.0, samples=8)
M = {"leaf": mat("leaf", "#3f9b46"), "rug": mat("rug", "#f2b5a0"), "frame": mat("frame", "#b98a5e")}
pc.materiais_banheiro(M)
M["piso_cat"] = pc.ladrilho_mat("piso_cat", "#e9dfcf", "#e1d5c2", "#c9b79c", tam=(0.4, 0.4), piso=True)
M["parede_cat"] = mat("parede_cat", "#eef0ea")
M["azulejo_cat"] = pc.ladrilho_mat("azulejo_cat", "#9fd8cf", "#96d1c7", "#ffffff", tam=(0.2, 0.2))
M["teto_cat"] = mat("teto_cat", "#f6f5ef")
Sky()
d = bpy.data.lights.new("frente", "AREA"); d.energy = 900; d.size = 30
o = mt.link(bpy.data.objects.new("frente", d)); o.location = (40, -12, 6); o.rotation_euler = (math.radians(70), 0, 0)
o.visible_camera = False
SP = 4.0
ITEMS = []                                        # (rótulo, câmera, alvo)


def slot(label, vista, _=None, parede="parede_cat", teto=False):
    """vista = (câmera, alvo) relativos ao centro do cantinho."""
    cam, tgt = vista
    x = len(ITEMS) * SP
    box(f"piso{len(ITEMS)}", x - 1.6, x + 1.6, -1.0, 1.4, -0.02, 0.0, M["piso_cat"])
    box(f"parede{len(ITEMS)}", x - 1.6, x + 1.6, 1.4, 1.5, 0.0, 2.6, M[parede])
    if teto:
        box(f"teto{len(ITEMS)}", x - 1.6, x + 1.6, -1.0, 1.5, 2.6, 2.7, M["teto_cat"])
    ITEMS.append((label, (x + cam[0], cam[1], cam[2]), (x + tgt[0], tgt[1], tgt[2])))
    return x


PERTO = ((0.9, -1.9, 1.2), (0.0, 0.6, 0.75))
x = slot("personagem() + toalha_ombro()", PERTO, ((0.0, 0.6, 0.7)))
P = pc.personagem("p1", M); P["raiz"].location = (x - 0.35, 0.6, 0); pc.toalha_ombro(P, M)
P2 = pc.personagem("p2", M, camisa="robe", calca="robe"); P2["raiz"].location = (x + 0.45, 0.6, 0); pc.turbante(P2, M)
x = slot("personagem(mascara, luvas) / touca()", PERTO, ((0.0, 0.6, 0.7)))
P = pc.personagem("p3", M, mascara=True, luvas="glove"); P["raiz"].location = (x - 0.35, 0.6, 0)
P["braco_d"].rotation_euler = (math.radians(-80), 0, 0)
P4 = pc.personagem("p4", M, camisa="orange"); P4["raiz"].location = (x + 0.45, 0.6, 0); pc.touca(P4, M)
pc.rosto_expr(P4, 0.0, boca="o")
x = slot("cama() + vaso_planta()", ((1.4, -2.4, 1.6), (0.1, 0.5, 0.4)), (0, 0, 0))
c = pc.cama("cama", M); c.location = (x - 0.6, 1.35, 0); c.rotation_euler = (0, 0, -math.pi / 2)
pc.vaso_planta("vp", M, altura=0.6).location = (x + 0.9, 1.0, 0)
x = slot("rolo_pintura() lata_tinta() balde() xis()", ((0.6, -1.3, 0.9), (0.0, 0.6, 0.45)), (0, 0, 0))
r = pc.rolo_pintura("rolo", M, cabo=0.7); r.location = (x - 0.45, 0.7, 0.75); r.rotation_euler = (0, math.radians(15), 0)
pc.lata_tinta("lata", M).location = (x - 0.05, 0.5, 0)
pc.balde("balde", M, agua="water_dot").location = (x + 0.35, 0.6, 0)
xx = pc.xis("xis", M, 0.35); xx.location = (x + 0.15, 1.35, 1.0)
x = slot("manchas() + aparecer/sumir_manchas", ((0.0, -0.6, 1.2), (0.0, 1.4, 1.2)), (0, 0, 0))
pc.manchas("mc", M, (x, 1.398, 1.2), 0.5, 90, normal="y", seed=1)
pc.manchas("gt", M, (x + 0.7, 1.395, 1.6), 0.25, 30, normal="y", seed=2, tam=(0.01, 0.02), cores=("drop", "drop"),
           achatado=0.7)
x = slot("tomada() benjamim() plugue()", ((0.1, 1.05, 0.62), (0.0, 1.4, 0.6)), (0, 0, 0))
pc.tomada("tom", M).location = (x, 1.4, 0.6)
b = pc.benjamim("benj", M); b.location = (x, 1.4 - 0.047, 0.602)
pl = pc.plugue("plug", M); pl.location = (x, 1.4 - 0.047 - 0.033, 0.602)
x = slot("bancada() air_fryer() micro_ondas() cafeteira()", ((0.3, -1.5, 1.45), (0.0, 1.0, 0.95)), (0, 0, 0))
pc.bancada("banc", M, comprimento=2.2).location = (x - 1.1, 0.78, 0)
pc.cafeteira("caf", M).location = (x - 0.75, 1.15, 0.9)
pc.micro_ondas("mic", M).location = (x - 0.15, 1.1, 0.9)
pc.air_fryer("air", M).location = (x + 0.6, 1.12, 0.9)
x = slot("mesa() cadeira() fruteira() pendente()", ((1.0, -2.0, 1.5), (0.0, 0.6, 0.8)), (0, 0, 0))
pc.mesa("mesa", M).location = (x, 0.6, 0)
for i, (dx, rz) in enumerate(((-0.75, -math.pi / 2), (0.75, math.pi / 2))):
    cd = pc.cadeira(f"cad{i}", M); cd.location = (x + dx, 0.6, 0); cd.rotation_euler = (0, 0, rz)
pc.fruteira("fru", M).location = (x, 0.6, 0.75)
pc.pendente("pend", M, altura_fio=0.5).location = (x, 0.6, 2.4)
x = slot("relogio_parede() quadro_disjuntores()", ((0.0, -0.4, 1.4), (0.0, 1.4, 1.4)), (0, 0, 0))
rl, _, _ = pc.relogio_parede("rel", M); rl.location = (x - 0.35, 1.38, 1.6)
qd, _ = pc.quadro_disjuntores("qd", M); qd.location = (x + 0.3, 1.39, 1.2)
x = slot("vaso_sanitario() pia_banheiro() espelho()", ((0.4, -1.4, 1.2), (0.1, 1.0, 0.85)), (0, 0, 0), parede="azulejo_cat")
pc.vaso_sanitario("vaso", M).location = (x - 0.4, 1.4, 0)
pc.pia_banheiro("pia", M).location = (x + 0.35, 1.4, 0)
e, emb = pc.espelho("esp", M); e.location = (x + 0.35, 1.4, 1.45)
x = slot("exaustor() interruptor() temporizador()", ((0.0, 0.55, 1.35), (0.0, 1.4, 1.35)), (0, 0, 0))
ex, hel = pc.exaustor("exa", M); ex.location = (x, 1.4, 1.6); hel.rotation_euler = (0, 0.4, 0)
it, _ = pc.interruptor("int", M); it.location = (x - 0.15, 1.4, 1.15)
tp, _ = pc.temporizador("tmp", M); tp.location = (x + 0.15, 1.4, 1.15)
x = slot("vitro() (aberto) + porta()", ((0.2, -1.6, 1.3), (0.0, 1.4, 1.2)), (0, 0, 0))
v, lam = pc.vitro("vit", M); v.location = (x - 0.6, 1.36, 1.7)
for p_ in lam:
    p_.rotation_euler = (math.radians(55), 0, 0)
pt, fl = pc.porta("porta", M); pt.location = (x + 0.05, 1.42, 0); fl.rotation_euler = (0, 0, math.radians(-35))
x = slot("chuveiro() cortina_box()", ((0.5, -1.3, 1.3), (0.0, 1.0, 1.2)), (0, 0, 0), parede="azulejo_cat")
ch, _ = pc.chuveiro("chu", M); ch.location = (x - 0.1, 1.4, 2.0)
ct = pc.cortina_box("cort", M, largura=0.9, altura=1.7); ct.location = (x - 0.55, 0.4, 1.95); ct.scale = (0.7, 1, 1)
x = slot("esfregao() frasco_sanitaria() frascos_shampoo()", ((0.4, -1.3, 1.0), (0.0, 0.8, 0.6)), (0, 0, 0))
es = pc.esfregao("esf", M, cabo=1.2); es.location = (x - 0.4, 1.0, 1.3); es.rotation_euler = (math.radians(-15), 0, 0)
pc.frasco_sanitaria("fr", M).location = (x + 0.05, 0.8, 0)
pc.frascos_shampoo("sh", M).location = (x + 0.35, 0.9, 0)
x = slot("vapor() + mancha_agua() no teto", ((0.3, -1.4, 1.1), (0.0, 0.6, 2.2)), (0, 0, 0), teto=True)
pc.vapor("vp_", M, 26, (x - 0.3, 0.5, 0.9), (x - 1.0, x + 1.0, -0.2, 1.2), 2.6, 0.0, 1.0, nascer=0.4)
pc.mancha_agua("inf", M, (x + 0.6, 0.6, 2.597), 0.3)
pc.manchas("mt", M, (x - 0.5, 0.9, 2.597), 0.35, 50, normal="z", seed=3, tam=(0.018, 0.05))

scene = mt.scene
scene.frame_set(mt.F(3.0))
names = []
for i, (label, cam, tgt) in enumerate(ITEMS):
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

font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
cols = 4
rows = math.ceil(len(names) / cols)
W, H, L = 432, 540, 34
sheet = Image.new("RGB", (cols * W, rows * (H + L)), "white")
dr = ImageDraw.Draw(sheet)
for i, (p, label) in enumerate(names):
    cx, cy = (i % cols) * W, (i // cols) * (H + L)
    sheet.paste(Image.open(p).convert("RGB"), (cx, cy + L))
    dr.text((cx + 10, cy + 9), label, font=font, fill=(25, 25, 25))
sheet.save(os.path.join(HERE, "catalogo_casa.jpg"), quality=88)
print("catálogo:", os.path.join(HERE, "catalogo_casa.jpg"))
