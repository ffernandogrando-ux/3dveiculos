"""Vídeo: "Pintar por cima do mofo" (roteiro 1030_8.srt, 76,1 s) — 1º vídeo do canal "dentro da sua casa".

Uso:  python cena.py   ->  mofo_pintura.blend + cortes.json
Cenário único: quarto em corte (casa de bonecas). Parede externa à esquerda (x de -0,5 a 0) com as camadas
visíveis no corte (y = 0): reboco externo, tijolo, reboco interno, tinta. Mancha de mofo na face interna (x = 0).
Tempos em segundos, copiados do roteiro.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "motor3d"))
import bpy, bmesh
from mathutils import Vector, Matrix
import motor as mt
import pecas as pc
from motor import (mat, lin, box, box_bm, cyl, tube, ball, arrow, mesh_obj, empty, pop_in, pop_out, grow, hide_until,
                   hide_from, move, path, jump, k, ks, glow, key_input, terrain, decor, far_ground, Sky, cameras,
                   write_cuts, save, node_of, bsdf, sock)

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 76.25
mt.setup(DUR)
rnd = random.Random(8)

# ================================================================ materiais
M = {n: mat(n, c, **kw) for n, c, kw in [
    ("grass", "#6cc24a", {}), ("soft", "#c8945c", {}), ("mid", "#a87447", {}), ("firm", "#8a5d3b", {}),
    ("aquifer", "#86b4d8", {}), ("rock", "#6e6c75", {}), ("base", "#9b9ba0", {}),
    ("fence", "#ffffff", {}), ("trunk", "#7a5230", {}), ("leaf", "#3f9b46", {}), ("cloud", "#ffffff", {}),
    ("rext", "#e9d8ad", {}), ("rint", "#d9cbb0", {}), ("paint_old", "#e6e0d0", {}), ("floor", "#c08a55", {}),
    ("wall_blue", "#a9c4dd", {}), ("ceiling", "#ece8de", {}), ("rug", "#f1c45a", {}), ("frame", "#8a5a35", {}),
    ("rain", "#a9cdf0", {"alpha": 0.8, "emit": 0.3}), ("crack", "#2b2b2f", {}), ("filler", "#9e9e9e", {}),
    ("coat", "#5d6b7a", {"rough": 0.4}), ("blotch", "#6f7556", {"alpha": 0.55}), ("wet_ring", "#b8b29c", {"alpha": 0.35}),
    ("haze", "#b9c3a0", {"alpha": 0.6, "emit": 0.2}), ("yellow", "#ffc928", {"emit": 1.2}), ("lamp", "#fff2c8", {"emit": 3.0}),
]}
pc.materiais_casa(M)
M["patch"] = mat("patch", "#f7f7f4")          # tinta nova (brilha ao terminar de pintar)
M["mold_sec"] = mat("mold_sec", "#3d4a26")     # colônias no corte (pulsam em verde)
M["wet_sec"] = mat("wet_sec", "#1f6f9a", alpha=0.5)


def tijolo_mat(name):
    m = mat(name, "#b5653f")
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 3.2
    br.inputs["Mortar Size"].default_value = 0.025
    br.inputs["Color1"].default_value = lin("#b5653f")
    br.inputs["Color2"].default_value = lin("#a65a37")
    br.inputs["Mortar"].default_value = lin("#d8c7a8")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["X"], add.inputs[0])
    nt.links.new(sep.outputs["Y"], add.inputs[1])
    nt.links.new(add.outputs[0], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], bsdf(m).inputs["Base Color"])
    return m


M["brick"] = tijolo_mat("brick")


# ================================================================ auxiliares
def caixa(name, x0, x1, y0, y1, z0, z1, m, org):
    """Caixa com origem em `org` (para crescer a partir de um canto/lado)."""
    bm = bmesh.new()
    box_bm(bm, x0 - org[0], x1 - org[0], y0 - org[1], y1 - org[1], z0 - org[2], z1 - org[2])
    return mesh_obj(name, bm, m, org)


def fcurves(o):
    ad = o.animation_data
    if not ad or not ad.action:
        return []
    a = ad.action
    if hasattr(a, "fcurves") and len(getattr(a, "fcurves", [])):
        return list(a.fcurves)
    out = []
    for layer in getattr(a, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def linear(o):
    for fc in fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def show_at(o, t):
    jump(o, "scale", t, (0, 0, 0), (1, 1, 1))


def hide_at(o, t):
    jump(o, "scale", t, (1, 1, 1), (0, 0, 0))


def pulse_scale(o, t0, t1, amp=0.18, step=0.33):
    t = t0
    while t < t1:
        ks(o, t, 1.0)
        ks(o, t + step / 2, 1.0 + amp)
        t += step
    ks(o, t1, 1.0)


# ================================================================ cenário
terrain("solo", -16, 16, [(0, 16, [])], M)
far_ground(M, y0=16)
decor(M, fence=(-16, 16, 12.5), trees=[(-5.5, 4), (-8.5, 9), (-3.6, 10), (8.2, 4.5), (10.5, 9), (6.8, 10.5)],
      clouds=[(-14, 60, 22), (6, 70, 26), (24, 65, 20)])

WX0, WX1 = -0.5, 0.0                  # parede externa (esquerda)
LAYERS_W = [("rext", -0.5, -0.44), ("brick", -0.44, -0.08), ("rint", -0.08, -0.012), ("paint_old", -0.012, 0.0)]
WIN = (2.3, 3.3, 1.45, 2.35)          # janela na parede externa: y0, y1, z0, z1
H = 2.9                               # pé-direito (do chão z = 0 ao forro)


def parede_com_janela(name, x0, x1, m, y0=0.0, y1=4.2, z0=0.0, z1=H, win=WIN):
    wy0, wy1, wz0, wz1 = win
    bm = bmesh.new()
    box_bm(bm, x0, x1, y0, y1, z0, wz0)
    box_bm(bm, x0, x1, y0, y1, wz1, z1)
    box_bm(bm, x0, x1, y0, wy0, wz0, wz1)
    box_bm(bm, x0, x1, wy1, y1, wz0, wz1)
    return mesh_obj(name, bm, m)


for ln, a, b in LAYERS_W:
    parede_com_janela("parede_" + ln, a, b, M[ln])
box("piso", 0, 5.0, 0, 4.0, 0, 0.15, M["floor"])
box("parede_fundo", -0.5, 5.2, 4.0, 4.2, 0, H, M["wall_blue"])
box("parede_dir", 5.0, 5.2, 0, 4.0, 0, H, M["wall_blue"])
box("forro", -0.62, 5.32, 0, 4.32, H, H + 0.22, M["ceiling"])
box("rodape", 0.0, 0.03, 0.0, 4.0, 0.15, 0.25, M["frame"])
# janela: batentes de madeira e peitoril
wy0, wy1, wz0, wz1 = WIN
for nm, a in [("jan_inf", (wy0 - 0.06, wy1 + 0.06, wz0 - 0.07, wz0)), ("jan_sup", (wy0 - 0.06, wy1 + 0.06, wz1, wz1 + 0.07)),
              ("jan_e", (wy0 - 0.06, wy0, wz0, wz1)), ("jan_d", (wy1, wy1 + 0.06, wz0, wz1))]:
    box(nm, -0.52, 0.04, a[0], a[1], a[2], a[3], M["frame"])
M["reveal"] = mat("reveal", "#ece7dc", emit=0.35)   # revestimento do vão (parede de 50 cm fica escura sem ele)
for nm, a in [("vao_inf", (wy0, wy1, wz0, wz0 + 0.01)), ("vao_sup", (wy0, wy1, wz1 - 0.01, wz1)),
              ("vao_e", (wy0, wy0 + 0.01, wz0, wz1)), ("vao_d", (wy1 - 0.01, wy1, wz0, wz1))]:
    box(nm, -0.5, 0.0, a[0], a[1], a[2], a[3], M["reveal"])
box("jan_meio", -0.27, -0.23, (wy0 + wy1) / 2 - 0.025, (wy0 + wy1) / 2 + 0.025, wz0, wz1, M["frame"])
ball("tapete", 1, (2.7, 1.6, 0.152), M["rug"], sub=2, scale=(1.0, 0.7, 0.004))
cyl("luminaria", 0.22, H - 0.12, H, (2.5, 1.9), M["lamp"], seg=16)
bed = pc.cama("cama", M, comprimento=2.1, largura=1.5)
bed.location = (0.1, 2.9, 0.15)

# tampa que esconde o corte da parede até o "lá dentro"
tampa = box("tampa", -0.5, 0.0, -0.45, 0.0, 0.0, H, M["rint"])

# ---------------------------------------------------------------- céu e luz
sky = Sky()
lamp_d = bpy.data.lights.new("lamp", "POINT")
lamp_d.energy = 110
lamp_d.shadow_soft_size = 0.6
lamp = mt.link(bpy.data.objects.new("lamp", lamp_d))
lamp.location = (2.5, 1.9, 2.55)
fill_d = bpy.data.lights.new("fill", "AREA")
fill_d.energy = 140
fill_d.size = 4
fill = mt.link(bpy.data.objects.new("fill", fill_d))
fill.location = (2.0, -3.5, 2.4)
fill.rotation_euler = (math.radians(70), 0, 0)
STATES = {"day": (3.6, 1.0, "#5fa3e0", "#dcecf7", 110), "cloudy": (1.3, 0.62, "#7d8ea3", "#b8c2cc", 110),
          "night": (0.12, 0.16, "#1b2747", "#41507a", 45)}


def sk(t, name):
    e, s, top, hor, le = STATES[name]
    sky.state(t, e, s, top, hor)
    lamp_d.energy = le
    lamp_d.keyframe_insert("energy", frame=mt.F(t))


def sk_hold(t0, t1, name):
    sk(t0, name)
    sk(t1, name)


def passar_tempo(t, noites=2, step=0.12):
    """Dia/noite piscando rápido (passagem de tempo)."""
    sk(t, "day")
    for i in range(noites):
        sk(t + step * (2 * i + 1), "night")
        sk(t + step * (2 * i + 2), "day")


sk_hold(0, 10.9, "day")
sk(11.6, "cloudy"); sk(28.85, "cloudy")
passar_tempo(28.97, 2); sk(32.3, "day")
passar_tempo(32.45, 2); sk(36.2, "day")
passar_tempo(36.3, 2); sk_hold(36.8, 60.35, "day")
sk(60.4, "cloudy"); sk(65.85, "cloudy")
sk(66.4, "day"); sk(DUR, "day")

# ================================================================ mofo na face interna (x = 0)
SC = (0.0, 0.95, 0.95)            # centro da mancha
S0 = pc.manchas("s0_", M, (0.004, SC[1], SC[2]), 0.62, 70, seed=1)                 # mancha original (visível no início)
patch1 = caixa("patch1", 0.012, 0.02, 0.25, 1.7, 0.18, 1.8, M["patch"], (0.016, 0.25, 0.99))
S1 = pc.manchas("s1_", M, (0.024, SC[1], SC[2]), 0.55, 26, seed=2, tam=(0.015, 0.035), cores=("mold_dark", "mold_dark"))
BUB = [(0.62, 1.25, 0.11), (0.95, 0.7, 0.14), (1.3, 1.1, 0.1), (0.75, 0.42, 0.09), (1.2, 0.55, 0.12), (1.0, 1.45, 0.08),
       (0.5, 0.85, 0.1)]
blotch = pc.esfera("blotch", 1, (0.023, SC[1], SC[2] - 0.05), M["blotch"], scale=(0.004, 0.85, 0.75))
S4 = pc.manchas("s4_", M, (0.027, SC[1], SC[2] - 0.05), 0.82, 110, seed=4)
patch2 = caixa("patch2", 0.032, 0.04, 0.18, 1.78, 0.17, 1.82, M["patch"], (0.036, 0.98, 0.17))
wet_ring = pc.esfera("wet_ring", 1, (0.042, SC[1], SC[2]), M["wet_ring"], scale=(0.004, 0.42, 0.38))
S5 = pc.manchas("s5_", M, (0.046, SC[1], SC[2]), 0.5, 34, seed=5, tam=(0.02, 0.05))
patch3 = caixa("patch3", 0.012, 0.022, 0.25, 1.7, 0.18, 1.8, M["patch"], (0.017, 0.25, 0.99))

# --- gancho: pintando por cima (0,3–2,9) — o rolo vai e volta em y, a tinta nova cresce atrás dele
grow(patch1, 0.3, 2.9, "y")
linear(patch1)
glow(M["patch"], 3.2, 4.1, hexcol="#ffffff", peak=0.6, pulses=1)

# --- linha do tempo: 1 mês (29,9–32,3) / 3 meses: bolhas e descascado (33,3–36,2) / 1 ano (36,4–38,4)
pc.aparecer_manchas(S1, 29.9, 32.2, de_dentro=False)
bubbles, S3 = [], []
for i, (y, z, r) in enumerate(BUB):
    b = ball(f"bolha{i}", r, (0.02, y, z), M["patch"], sub=2, scale=(0.35, 1, 1))
    tb = 33.35 + i * 0.13
    grow(b, tb, tb + 0.6, "x")
    ks(b, tb + 0.6, (1, 1, 1))
    tp = 34.6 + i * 0.22
    pop_out(b, tp, 0.18)
    bubbles.append(b)
    for j in range(2):                       # lascas caindo
        l = box(f"lasca{i}_{j}", -0.005, 0.005, -r * 0.5, r * 0.5, -r * 0.35, r * 0.35, M["patch"], anchor="center")
        hide_until(l, tp)
        path(l, [(tp, (0.04, y + (j - 0.5) * r * 0.6, z)), (tp + 0.25, (0.18 + 0.1 * j, y + (j - 0.5) * r, z - 0.25)),
                 (tp + 0.75, (0.3 + 0.15 * j, y + (j - 0.5) * r * 1.4, 0.16))])
        k(l, "rotation_euler", tp, (0, 0, 0))
        k(l, "rotation_euler", tp + 0.75, (rnd.uniform(1, 2), rnd.uniform(1.2, 1.6), rnd.uniform(-1, 1)))
        hide_from(l, 60.4)
    S3 += [(o, d) for o, d in pc.manchas(f"s3_{i}_", M, (0.024, y, z), r * 0.9, 9, seed=10 + i, tam=(0.015, 0.04))]
    for o, _ in S3[-9:]:
        pop_in(o, tp + 0.05, 0.25)
ks(blotch, 36.45, 0.0)
ks(blotch, 38.4, 1.0)
pc.aparecer_manchas(S4, 36.5, 38.3)

# --- desculpa 1: tinta antimofo (48,9–54,0)
lata = pc.lata_tinta("lata", M)
lata.location = (0.4, 0.42, 0.15)
lata.rotation_euler = (0, 0, 0.4)
pop_in(lata, 49.05, 0.35)
pop_out(lata, 53.95, 0.2)
grow(patch2, 49.5, 50.5, "z")
glow(M["patch"], 50.5, 51.0, hexcol="#ffffff", peak=0.5, pulses=1)
ks(wet_ring, 51.9, 0.0)
ks(wet_ring, 53.1, 1.0)
pc.aparecer_manchas(S5, 53.3, 53.95)
xis = pc.xis("xis", M, 0.55)
xis.location = (0.35, 0.95, 1.0)
xis.rotation_euler = (0, 0, math.radians(90))
pop_in(xis, 53.45, 0.3)
pop_out(xis, 54.05, 0.2)

# --- desculpa 2: água sanitária "e sumiu" (54,1–56,4)
balde1 = pc.balde("balde1", M, agua="water_dot")
balde1.location = (0.4, 0.42, 0.15)
pop_in(balde1, 54.15, 0.35)
hide_from(balde1, 58.0)
pc.sumir_manchas(S5, 55.0, 56.3)

# --- "o certo": volta ao estado original depois do rebobinar (60,4)
for o in [patch1, patch2, blotch, wet_ring] + [o for o, _ in S1 + S3 + S4]:
    hide_at(o, 60.4)

# --- limpeza (67,2–70,2) e pintura certa (70,95–71,85)
pc.sumir_manchas(S0, 67.3, 70.2, ordem=lambda o: (o.location.y - 0.3) / 1.35)
grow(patch3, 70.95, 71.85, "y")
linear(patch3)
glow(M["patch"], 71.9, 72.5, hexcol="#ffc928", peak=0.7, pulses=1)
hide_at(patch3, 74.53)
for o, _ in S0:                                  # loop: a mancha original volta para o 1º quadro
    show_at(o, 74.53)

# ================================================================ corte da parede (y = 0): camadas, fungo, água
SEC_Y = -0.03
sec_new = box("sec_tinta_nova", 0.0, 0.02, -0.035, 0.0, 0.18, 1.8, M["patch"])
hide_until(sec_new, 2.9)
hide_at(sec_new, 60.4)
show_at(sec_new, 71.85)
hide_at(sec_new, 74.53)

colonias, hifas1, hifas2 = [], [], []
for i in range(9):
    z = 0.42 + i * 0.13 + rnd.uniform(-0.03, 0.03)
    c = ball(f"colonia{i}", rnd.uniform(0.022, 0.034), (-0.006, SEC_Y, z), M["mold_sec"], sub=1, scale=(1, 0.35, 1.2))
    pop_in(c, 7.45 + i * 0.05, 0.3)
    colonias.append(c)
    for j in range(2):
        a = Vector((-0.01, SEC_Y - 0.004, z + rnd.uniform(-0.02, 0.02)))
        b1 = a + Vector((-rnd.uniform(0.04, 0.065), 0, rnd.uniform(-0.04, 0.04)))
        h1 = tube(f"hifa1_{i}_{j}", a, b1, 0.0045, M["mold_sec"], seg=5)
        grow(h1, 7.7 + 0.04 * i, 8.3, "z")
        hifas1.append(h1)
        b2 = b1 + Vector((-rnd.uniform(0.08, 0.17), 0, rnd.uniform(-0.07, 0.07)))
        h2 = tube(f"hifa2_{i}_{j}", b1, b2, 0.0035, M["mold_sec"], seg=5)
        grow(h2, 26.95 + 0.05 * i, 28.6, "z")
        hifas2.append(h2)
for i, c in enumerate(colonias):
    pulse_scale(c, 25.3 + 0.03 * i, 26.65)
glow(M["mold_sec"], 25.3, 26.7, hexcol="#7fbf3f", peak=1.0, pulses=2)
for o in colonias + hifas1 + hifas2:
    hide_at(o, 68.0)

gotas_sec = []
for i in range(14):
    g = ball(f"gota_sec{i}", rnd.uniform(0.012, 0.02), (rnd.uniform(-0.4, -0.1), SEC_Y - 0.01, rnd.uniform(0.45, 1.5)),
             M["water_dot"], sub=1)
    pop_in(g, 9.2 + i * 0.04, 0.25)
    hide_at(g, 66.4)
    gotas_sec.append(g)

wetA = caixa("umidade_tijolo", -0.44, -0.08, -0.027, -0.006, 0.12, 1.9, M["wet_sec"], (-0.44, -0.016, 0.12))
wetB = caixa("umidade_reboco", -0.08, -0.012, -0.027, -0.006, 0.12, 1.9, M["wet_sec"], (-0.08, -0.016, 0.12))
grow(wetA, 16.9, 19.2, "x")
grow(wetB, 19.5, 20.6, "x")
grow(wetA, 66.0, 66.7, "x", frm=1.0, to=0.0)
grow(wetB, 65.95, 66.5, "x", frm=1.0, to=0.0)
glow(M["patch"], 21.2, 22.4, hexcol="#ffc928", peak=0.8, pulses=2)
glow(M["wet_sec"], 22.9, 24.9, hexcol="#4fc3f7", peak=0.9, pulses=3)
glow(M["wet_sec"], 57.8, 58.9, hexcol="#4fc3f7", peak=0.9, pulses=2)

# tampa: cai e revela o corte (6,35–6,8); volta para o loop final
move(tampa, 6.35, 6.8, (0, 0, 0), (0, 0, -3.2))
hide_at(tampa, 6.85)
jump(tampa, "location", 74.53, (0, 0, -3.2), (0, 0, 0))
show_at(tampa, 74.53)

# ================================================================ lado de fora: chuva, trinca, impermeabilização
CRACK = [(0.12, 1.62), (0.22, 1.47), (0.17, 1.32), (0.3, 1.17), (0.25, 1.02), (0.38, 0.86)]
M["crack"] = mat("crack_m", "#2b2b2f")
crack = []
for j in range(len(CRACK) - 1):
    a = (-0.505, CRACK[j][0], CRACK[j][1])
    b = (-0.505, CRACK[j + 1][0], CRACK[j + 1][1])
    s = tube(f"trinca{j}", a, b, 0.016, M["crack"], seg=5)
    grow(s, 14.35 + j * 0.08, 14.5 + j * 0.08, "z")
    hide_at(s, 63.0 + j * 0.08)
    crack.append(s)
glow(M["crack"], 14.6, 16.4, hexcol="#e53935", peak=1.4, pulses=2)
glow(M["crack"], 61.4, 62.7, hexcol="#e53935", peak=1.4, pulses=2)
for j in range(len(CRACK) - 1):
    a = (-0.51, CRACK[j][0], CRACK[j][1])
    b = (-0.51, CRACK[j + 1][0], CRACK[j + 1][1])
    s = tube(f"massa{j}", a, b, 0.03, M["filler"], seg=6)
    grow(s, 63.0 + j * 0.08, 63.15 + j * 0.08, "z")
glow(M["filler"], 63.3, 64.2, peak=1.0, pulses=2)

coat = []
for nm, (y0, y1, z0, z1), t0, t1 in [("baixo", (0, 4.2, 0, WIN[2]), 64.3, 64.9), ("esq", (0, WIN[0], WIN[2], WIN[3]), 64.9, 65.3),
                                     ("dir", (WIN[1], 4.2, WIN[2], WIN[3]), 64.9, 65.3), ("cima", (0, 4.2, WIN[3], H), 65.3, 65.6)]:
    c = caixa(f"impermeab_{nm}", -0.53, -0.5, y0, y1, z0, z1, M["coat"], (-0.515, (y0 + y1) / 2, z0))
    grow(c, t0, t1, "z")
    hide_at(c, 74.53)
    coat.append(c)
glow(M["coat"], 65.6, 66.3, peak=0.8, pulses=1)

seta = arrow("seta_trinca", 0.45, M["yellow"], (-0.56, 0.28, 1.28), direction=(1, 0.35, -0.15), r=0.018, head=0.05)
pop_in(seta, 61.6, 0.3)
pop_out(seta, 62.85, 0.2)

# chuva: no chão de fora e batendo na parede (dois períodos)
for tag, t0, t1 in [("a", 10.9, 28.9), ("b", 60.4, 65.9)]:
    pc.chuva(f"chuva{tag}_", M, -4.5, -0.75, -1.5, 4.5, 5.0, 0.0, t0, t1, n=70, vento=(-0.45, 0), seed=3 if tag == "a" else 4)
    pc.chuva(f"chuvap{tag}_", M, -0.52, -0.52, -0.3, 4.2, 4.0, lambda x, y: rnd.uniform(0.3, 2.7), t0, t1, n=24,
             vento=(-1.1, 0), seed=5 if tag == "a" else 6)

# gotas entrando pela trinca e atravessando o tijolo (15,2–20,6)
for i in range(10):
    g = ball(f"gota_trinca{i}", 0.016, (0, 0, 0), M["water_dot"], sub=1)
    z = rnd.uniform(1.05, 1.5)
    t0 = 15.2 + i * 0.35
    zz = z - rnd.uniform(0.05, 0.35)
    mt.along(g, [(-0.55, 0.25, z), (-0.505, 0.22, z), (-0.47, SEC_Y - 0.012, z - 0.02),
                 (-0.3, SEC_Y - 0.012, (z + zz) / 2 + rnd.uniform(-0.05, 0.05)), (-0.1, SEC_Y - 0.012, zz)], t0, t0 + 2.2)

# ================================================================ pessoas (boneco de brinquedo: pc.personagem)
VIRA_PAREDE = (0, 0, math.radians(-90))       # olhando para a parede (-x)


def pintar(rolo_obj, t0, t1, P, y0=0.3, y1=1.65, n=5, z_lo=0.5, z_hi=1.65, x_raiz=1.2, solta_em=None):
    """Boneco pintando com o rolo NA MÃO: anda junto (raiz em y), o braço direito sobe/desce e o cabo do rolo vai da
    parede até a mão. solta_em: tempo em que ele larga o rolo encostado na parede."""
    SH = 0.15 + 0.9                                   # altura do ombro
    CABO = 1.03                                       # haste + cabo do rolo
    for i in range(n * 2 + 1):
        f = i / (n * 2)
        t = t0 + (t1 - t0) * f
        y, z = y0 + (y1 - y0) * f, (z_hi if i % 2 == 0 else z_lo)
        best = None
        for a in range(5, 171):                       # ângulo do braço que deixa a mão a um cabo de distância do rolo
            ar = math.radians(a)
            hx, hz = x_raiz - 0.4 * math.sin(ar), SH - 0.4 * math.cos(ar)
            err = abs(math.hypot(hx - 0.09, hz - z) - CABO)
            if best is None or err < best[0]:
                best = (err, ar, hx, hz)
        _, ar, hx, hz = best
        k(rolo_obj, "location", t, (0.09, y, z))
        k(rolo_obj, "rotation_euler", t, (0, math.atan2(-(hx - 0.09), -(hz - z)), 0))
        k(P["braco_d"], "rotation_euler", t, (-ar, 0, 0))
        k(P["braco_e"], "rotation_euler", t, (math.radians(-15), 0, 0))
        k(P["raiz"], "location", t, (x_raiz, y + 0.25, 0.15))
    for o in (rolo_obj, P["braco_d"], P["raiz"]):
        linear(o)
    if solta_em:
        k(rolo_obj, "location", solta_em, (0.09, y1 + 0.2, 0.95))
        k(rolo_obj, "rotation_euler", solta_em, (0, math.radians(-38), 0))
        k(P["braco_d"], "rotation_euler", solta_em, (math.radians(-10), 0, 0))
        k(P["raiz"], "location", solta_em, (x_raiz + 0.15, y1 + 0.4, 0.15))


def pintor_com_rolo(nome, **kw):
    P = pc.personagem(nome, M, camisa="shirt", **kw)
    P["raiz"].rotation_euler = VIRA_PAREDE
    r = pc.rolo_pintura(nome + "_rolo", M, cabo=0.85)
    return P, r


pint, rolo = pintor_com_rolo("pintor")
pintar(rolo, 0.3, 2.9, pint, solta_em=3.4)
k(pint["cabeca"], "rotation_euler", 3.3, (0, 0, 0))
k(pint["cabeca"], "rotation_euler", 3.7, (math.radians(-12), 0, math.radians(-25)))   # olha satisfeito
hide_from(pint["raiz"], 7.0)
hide_from(rolo, 7.0)

# família dormindo (cabeça no travesseiro junto da parede, rosto para cima, coberta por cima)
DEITADO = (math.radians(-90), 0, math.radians(90))
dormindo = []
for i, (y, cam_) in enumerate(((2.55, "shirt"), (3.25, "sheet"))):
    P = pc.personagem(f"dorme{i}", M, camisa=cam_, cabelo="hair")
    P["raiz"].location = (1.68, y, 0.9)
    P["raiz"].rotation_euler = DEITADO
    hide_until(P["raiz"], 38.93)
    hide_from(P["raiz"], 48.9)
    pc.rosto_expr(P, 38.93, olhos="fechados", boca="neutra")
    dormindo.append(P)
edredom = pc.esfera("edredom", 1, (1.5, 2.9, 0.98), M["blanket"], scale=(0.78, 0.8, 0.16))
hide_until(edredom, 38.93)
hide_from(edredom, 48.9)
P = dormindo[0]
pc.rosto_expr(P, 46.4, olhos="abertos", boca="o")
pc.rosto_expr(P, 47.6, boca="triste")
for tc in (46.45, 46.95, 47.7, 48.05):                      # tosse: cabeça dá um tranco
    k(P["cabeca"], "rotation_euler", tc - 0.02, (0, 0, 0))
    k(P["cabeca"], "rotation_euler", tc + 0.08, (math.radians(-22), 0, 0))
    k(P["cabeca"], "rotation_euler", tc + 0.22, (0, 0, 0))

# limpeza com luva e máscara (esponja presa na luva), depois a pintura certa
limp = pc.personagem("limpador", M, camisa="shirt", mascara=True, luvas="glove")
limp["raiz"].rotation_euler = VIRA_PAREDE
hide_until(limp["raiz"], 66.77)
hide_at(limp["raiz"], 74.53)
sponge = box("esponja", -0.09, 0.09, -0.06, 0.06, -0.035, 0.035, M["sponge"], anchor="center")
sponge.parent = limp["mao_d"]
sponge.location = (0, 0, -0.1)
hide_until(sponge, 66.77)
hide_from(sponge, 70.45)
k(limp["raiz"], "location", 66.77, (0.5, 0.55, 0.15))
k(limp["braco_d"], "rotation_euler", 66.77, (math.radians(-90), 0, 0))
for i in range(11):                                          # esfrega em zigue-zague, andando ao longo da mancha
    t = 67.2 + i * 0.3
    k(limp["braco_d"], "rotation_euler", t, (math.radians(-135 if i % 2 == 0 else -55), 0, 0))
    k(limp["raiz"], "location", t, (0.5, 0.6 + 1.25 * i / 10, 0.15))
k(limp["raiz"], "location", 70.45, (0.5, 1.85, 0.15))
k(limp["cabeca"], "rotation_euler", 68.6, (0, 0, 0))
k(limp["cabeca"], "rotation_euler", 69.0, (0, 0, math.radians(40)))      # olha para a câmera (luva + máscara)
k(limp["cabeca"], "rotation_euler", 70.1, (0, 0, math.radians(40)))
k(limp["cabeca"], "rotation_euler", 70.5, (0, 0, 0))
balde2 = pc.balde("balde2", M, agua="water_dot")
balde2.location = (0.45, 0.25, 0.15)
hide_until(balde2, 66.77)
hide_from(balde2, 70.9)
rolo2 = pc.rolo_pintura("rolo2", M, cabo=0.85)
hide_until(rolo2, 70.9)
pintar(rolo2, 70.95, 71.85, limp, n=3, solta_em=72.25)
for lado in ("braco_d", "braco_e"):
    k(limp[lado], "rotation_euler", 72.5, (0, math.radians(-35 if lado == "braco_d" else 35), 0))
k(limp["raiz"], "rotation_euler", 72.25, VIRA_PAREDE)
k(limp["raiz"], "rotation_euler", 72.6, (0, 0, math.radians(37)))        # vira para a câmera, comemorando
hide_at(limp["mascara"], 72.3)
pc.rosto_expr(limp, 72.3, boca="sorriso")
show_at(limp["nariz"], 72.3)
hide_at(rolo2, 74.53)

# loop final: pintor e rolo repetem o começo (74,53 = 0,0)
L0 = 74.53
pint2, rolo3 = pintor_com_rolo("pintor_loop")
hide_until(pint2["raiz"], L0)
hide_until(rolo3, L0)
k(rolo3, "location", L0, (0.09, 0.3, 1.65))
pintar(rolo3, L0 + 0.3, L0 + 2.9, pint2)
patch_loop = caixa("patch_loop", 0.012, 0.02, 0.25, 1.7, 0.18, 1.8, M["patch"], (0.016, 0.25, 0.99))
grow(patch_loop, L0 + 0.3, L0 + 2.9, "y")
linear(patch_loop)

# ================================================================ esporos e ar parado
pc.particulas("ar_", M, "haze", 26, (0.1, SC[1], SC[2]), (2.6, 2.2, 1.7), 38.95, 41.7, espalha=1.1, r=0.03, seed=21)
NARIZ = (0.35, 2.55, 1.2)
pc.particulas("esporo_", M, "spore", 46, (0.06, SC[1], SC[2]), NARIZ, 41.75, 46.2, espalha=0.45, r=0.022, seed=22)
pc.particulas("esporob_", M, "spore", 18, (0.06, SC[1], SC[2]), (0.35, 3.25, 1.2), 43.4, 46.3, espalha=0.4, r=0.022, seed=23)
pc.particulas("tosse_", M, "spore", 10, NARIZ, (1.4, 2.0, 1.7), 46.45, 48.3, espalha=0.5, r=0.02, seed=24)

# ================================================================ câmeras
P0, T0 = (2.5, -1.7, 1.75), (0.1, 1.0, 1.0)
SEC_W = ((-0.26, -1.95, 1.0), (-0.26, 0.0, 1.0))     # corte da parede, plano aberto (fora + parede + dentro)
OUT_W = ((-3.9, -3.3, 1.9), (-0.6, 0.7, 1.3))        # lado de fora
CRK = ((-1.5, -1.05, 1.35), (-0.5, 0.35, 1.25))      # trinca de perto
WALL = ((2.4, 0.95, 1.05), (0.0, 0.95, 0.95))        # parede de frente (linha do tempo)
shots = [
    (0.0, [(0.0, P0, T0), (3.1, (2.05, -0.95, 1.6), T0), (5.75, (1.85, -0.7, 1.55), (0.05, 0.95, 1.0)),
           (6.35, (-0.2, -1.55, 1.05), (-0.22, 0.0, 1.0)), (7.2, (-0.2, -1.4, 1.02), (-0.22, 0.0, 1.0)),
           (7.65, (-0.05, -0.72, 1.0), (-0.05, 0.0, 0.98)), (8.65, (-0.06, -0.68, 1.0), (-0.06, 0.0, 0.98)),
           (9.15, (-0.16, -0.98, 1.0), (-0.16, 0.0, 1.0)), (10.85, (-0.17, -1.05, 1.0), (-0.17, 0.0, 1.0)),
           (11.55, *OUT_W), (14.15, (-3.3, -2.6, 1.75), OUT_W[1]), (14.7, *CRK), (16.6, (-1.4, -0.95, 1.33), CRK[1]),
           (17.15, *SEC_W), (20.85, (-0.24, -1.8, 1.0), (-0.24, 0.0, 1.0)),
           (21.4, (-0.02, -0.85, 1.05), (-0.03, 0.0, 1.0)), (25.2, (-0.03, -0.75, 1.02), (-0.03, 0.0, 1.0)),
           (26.9, (-0.05, -0.6, 1.0), (-0.05, 0.0, 0.95)), (28.9, (-0.07, -0.5, 0.98), (-0.07, 0.0, 0.95))]),
    (28.97, [(28.97, *WALL), (38.85, (2.2, 0.95, 1.02), WALL[1])]),
    (38.93, [(38.93, (3.4, -3.4, 2.3), (0.8, 1.9, 1.0)), (41.6, (3.1, -3.0, 2.2), (0.8, 1.9, 1.0)),
             (43.4, (2.8, -2.6, 2.1), (0.5, 2.0, 1.0)), (44.1, (2.3, 0.5, 1.85), (0.5, 2.9, 0.9)),
             (48.85, (2.15, 0.65, 1.8), (0.5, 2.9, 0.9))]),
    (48.9, [(48.9, *WALL), (57.65, (2.25, 0.9, 1.03), WALL[1])]),
    (57.73, [(57.73, (-0.24, -1.8, 1.0), (-0.24, 0.0, 1.0)), (60.35, (-0.24, -1.7, 1.0), (-0.24, 0.0, 1.0))]),
    (60.4, [(60.4, *OUT_W), (60.9, *OUT_W), (61.5, (-1.6, -1.1, 1.4), CRK[1]), (62.9, (-1.5, -1.0, 1.38), CRK[1]),
            (64.3, (-1.6, -1.1, 1.4), CRK[1]), (65.6, (-3.6, -2.9, 1.8), (-0.55, 1.2, 1.35)),
            (65.85, (-3.6, -2.9, 1.8), (-0.55, 1.2, 1.35)), (66.35, *SEC_W), (66.72, *SEC_W)]),
    (66.77, [(66.77, (0.95, -1.15, 1.3), (0.0, 1.0, 1.0)), (68.65, (0.9, -1.05, 1.3), (0.0, 1.0, 1.0)),
             (69.2, (0.05, 0.55, 1.45), (0.45, 1.43, 1.35)), (69.95, (0.07, 0.6, 1.45), (0.45, 1.43, 1.35)),
             (70.5, (1.9, -2.2, 1.5), (0.6, 1.1, 1.05)), (72.0, (1.95, -2.3, 1.5), (0.6, 1.1, 1.05)),
             (72.6, (4.0, -5.0, 2.6), (1.4, 1.9, 1.2)), (74.45, (4.6, -6.0, 2.9), (1.4, 1.9, 1.2))]),
    (L0, [(L0, P0, T0), (L0 + 3.1, (2.05, -0.95, 1.6), T0)]),
]
cameras(shots, shakes=[(28.97, 29.2, 0.02), (32.45, 32.65, 0.02), (36.3, 36.5, 0.025), (46.4, 46.9, 0.025),
                       (47.6, 48.3, 0.035), (53.45, 53.6, 0.015)])

write_cuts(os.path.join(HERE, "cortes.json"), [6.05, 11.2, 72.3], DUR)
import json
info = json.load(open(os.path.join(HERE, "cortes.json")))
info["rebobinar"] = [{"ini": 59.1, "fim": 60.4, "de": 29.0, "ate": 58.8}]
json.dump(info, open(os.path.join(HERE, "cortes.json"), "w"), indent=1)
save(os.path.join(HERE, "mofo_pintura.blend"))
