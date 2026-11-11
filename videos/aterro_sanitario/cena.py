"""Vídeo: "Você construiu um aterro sanitário" (roteiro 1029_3.srt, 72,7 s).

Uso:  python cena.py   ->  aterro.blend + cortes.json
Tempos em segundos, copiados do roteiro.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "motor3d"))
import bpy, bmesh
from mathutils import Vector, Matrix
import shapely.geometry as sg
import motor as mt
from motor import (mat, lin, box, cyl, tube, ball, prism, prism_fill, add_relative_key, fill, shape, pop_in, pop_out,
                   grow, grow_z, hide_until, hide_from, move, path, jump, k, ks, flicker, loop_fall, along, empty,
                   glow, key_input, house, terrain, decor, far_ground, text, mosaic_mat, stones_mat, node_of, Sky,
                   cameras, write_cuts, save, mesh_obj, bsdf)

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 72.8
mt.setup(DUR, samples=16)
rnd = random.Random(5)

# ================================================================ materiais
M = {n: mat(n, c, **kw) for n, c, kw in [
    ("grass", "#6cc24a", {}), ("soft", "#c8945c", {}), ("mid", "#a87447", {}), ("firm", "#8a5d3b", {}),
    ("aquifer", "#86b4d8", {}), ("rock", "#6e6c75", {}), ("base", "#9b9ba0", {}),
    ("white", "#f4f1ea", {}), ("roof", "#c9483a", {}), ("wood", "#b07a45", {}), ("glass", "#5b8fd6", {"rough": 0.3}),
    ("fence", "#ffffff", {}), ("trunk", "#7a5230", {}), ("leaf", "#3f9b46", {}), ("cloud", "#ffffff", {}),
    ("cloud_dark", "#6f7987", {}), ("dark", "#2b2b2f", {}), ("steel", "#4c5560", {"rough": 0.4}),
    ("yellow", "#ffc928", {"emit": 1.2}), ("machine", "#f2b51d", {}), ("truck_cab", "#f07c1f", {}),
    ("truck_bed", "#8f9aa5", {}), ("clay", "#c98a62", {}), ("membrane", "#1d1d22", {"rough": 0.35}),
    ("pipe_leach", "#e4e4e4", {"rough": 0.5}), ("pipe_gas", "#d4d4d4", {"rough": 0.5}), ("hole", "#1a1a1a", {}),
    ("cover", "#9a6b45", {}), ("chorume", "#2b2117", {"rough": 0.12, "alpha": 0.92}),
    ("plume", "#3a2a18", {"alpha": 0.66}), ("water", "#3a8ee6", {"rough": 0.1, "alpha": 0.8}),
    ("well_water", "#3a8ee6", {"rough": 0.1}), ("lagoon1", "#3b2a1a", {"rough": 0.1}),
    ("lagoon2", "#4c9a8a", {"rough": 0.1}), ("methane", "#d8f06a", {"emit": 0.9, "alpha": 0.75}),
    ("toxic", "#8bc34a", {"emit": 1.4}), ("fire", "#ff8a1c", {"emit": 4.0}), ("fire_core", "#ffd23f", {"emit": 6.0}),
    ("smoke", "#5d5d60", {}), ("rain", "#a9cdf0", {"alpha": 0.8, "emit": 0.3}), ("drip", "#22180f", {"rough": 0.2}),
    ("rat", "#8d8d8d", {}), ("pink", "#e7a3a3", {}), ("vulture", "#26262a", {}), ("vulture_head", "#d79a8f", {}),
    ("bag_w", "#f2f2f2", {}), ("bag_b", "#4a7fd6", {}), ("bag_k", "#3a3a3a", {}), ("wind", "#ffffff", {"alpha": 0.7, "emit": 0.5}),
    ("paper", "#efe7d2", {}), ("ink", "#262626", {}), ("ink_gray", "#9a958a", {}), ("bottle", "#3f8f4f", {"rough": 0.2}),
    ("can", "#d33a2f", {"rough": 0.3}), ("plant", "#9fb3c8", {}), ("pole", "#5b4632", {}), ("wire", "#222222", {}),
    ("pawn", "#3b6fd6", {}), ("concrete", "#c9c9cc", {}), ("concrete_dark", "#a9a9ae", {}), ("stone_wall", "#a8a39b", {}),
]}
TRASH = dict(base="#5a5047", sat=1.0, mix=0.55, val=0.72)
M["trash"] = mosaic_mat("trash", scale=3.2, **TRASH)
M["trash_old"] = mosaic_mat("trash_old", scale=3.2, **TRASH)
M["trash_pile"] = mosaic_mat("trash_pile", scale=2.2, **TRASH)
M["gravel"] = stones_mat("gravel", light="#a39d92", dark="#5e5a55", scale=5.5)
M["gravel_col"] = stones_mat("gravel_col", light="#a39d92", dark="#5e5a55", scale=5.5)
M["blast"] = mat("blast", "#ff7b1c", emit=1.6)
M["blast_core"] = mat("blast_core", "#ffd23f", emit=2.2)
M["win_lit"] = mat("win_lit", "#5b8fd6", rough=0.3)
JUNK = ["bag_w", "bag_b", "bag_k", "bottle", "can", "paper", "truck_cab", "roof", "wood"]


# ================================================================ peças reutilizáveis deste vídeo
def disc(name, r, w, m, seg=16):
    """Roda/cilindro centrado, eixo em y."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=w)
    o = mesh_obj(name, bm, m)
    o.rotation_euler = (math.pi / 2, 0, 0)
    return o


def cone(name, r, h, m, seg=8):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=0.0, depth=h,
                          matrix=Matrix.Translation((0, 0, h / 2)))
    return mesh_obj(name, bm, m)


def child(o, parent, loc=None):
    o.parent = parent
    if loc is not None:
        o.location = loc
    return o


def junk(name, size=0.35, kind=None):
    kind = kind or rnd.choice(["box", "box", "bag", "can"])
    m = M[rnd.choice(JUNK)]
    if kind == "bag":
        o = ball(name, size * 0.7, (0, 0, 0), m, scale=(1.2, 1.0, 0.7))
    elif kind == "can":
        o = cyl(name, size * 0.3, 0, size * 0.9, (0, 0), m, seg=10)
    else:
        s = size * rnd.uniform(0.6, 1.1)
        o = box(name, -s / 2, s / 2, -s * 0.4, s * 0.4, 0, s * 0.6, m)
    o.rotation_euler = (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(0, 6.28))
    return o


def truck(name):
    root = empty(name)
    child(box(name + "_chassi", -2.6, 2.6, -0.9, 0.9, 0.55, 0.85, M["dark"]), root)
    child(box(name + "_cab", 1.3, 2.7, -1.0, 1.0, 0.85, 2.45, M["truck_cab"]), root)
    child(box(name + "_vidro", 2.69, 2.75, -0.8, 0.8, 1.6, 2.25, M["glass"]), root)
    for wx in (-1.7, 1.9):
        for wy in (-0.95, 0.95):
            child(disc(f"{name}_roda{wx}{wy}", 0.55, 0.35, M["dark"]), root, (wx, wy, 0.55))
    hinge = child(empty(name + "_hinge"), root, (-2.6, 0, 0.9))
    child(box(name + "_cacamba", 0.0, 3.8, -1.05, 1.05, 0.0, 1.5, M["truck_bed"]), hinge)
    return root, hinge


def roller(name):
    root = empty(name)
    child(box(name + "_corpo", -1.3, 0.9, -0.8, 0.8, 0.45, 1.45, M["machine"]), root)
    child(box(name + "_cab", -1.1, 0.1, -0.6, 0.6, 1.45, 2.3, M["glass"]), root)
    drum = child(disc(name + "_rolo", 0.75, 1.9, M["steel"], seg=18), root, (1.65, 0, 0.75))
    for wy in (-0.85, 0.85):
        child(disc(f"{name}_roda{wy}", 0.5, 0.35, M["dark"]), root, (-0.8, wy, 0.5))
    return root, drum


def dozer(name):
    root = empty(name)
    child(box(name + "_corpo", -1.2, 1.0, -0.85, 0.85, 0.35, 1.35, M["machine"]), root)
    child(box(name + "_cab", -1.0, 0.0, -0.6, 0.6, 1.35, 2.2, M["glass"]), root)
    for wy in (-1, 1):
        child(box(f"{name}_esteira{wy}", -1.45, 1.15, 0.62 * wy - 0.22, 0.62 * wy + 0.22, 0.0, 0.55, M["dark"]), root)
    child(box(name + "_lamina", 1.25, 1.45, -1.15, 1.15, 0.0, 1.05, M["steel"]), root)
    return root


def vulture(name):
    root = empty(name)
    child(ball(name + "_corpo", 1, (0, 0, 0), M["vulture"], scale=(0.4, 0.85, 0.36)), root)
    child(ball(name + "_cabeca", 0.2, (0, 0, 0), M["vulture_head"]), root, (0, 0.88, 0.16))
    hinges = []
    for s in (1, -1):
        h = child(empty(f"{name}_asa{s}"), root, (0.22 * s, 0, 0.1))
        child(box(f"{name}_asa_m{s}", 0 if s > 0 else -1.7, 1.7 if s > 0 else 0, -0.32, 0.32, -0.04, 0.04, M["vulture"], anchor="center"),
              h, (0.85 * s, 0, 0))
        hinges.append((h, s))
    return root, hinges


def flap(hinges, t0, t1, step=0.18, amp=0.5):
    t, up = t0, True
    while t <= t1:
        for h, s in hinges:
            k(h, "rotation_euler", t, (0, -s * amp if up else s * amp * 0.6, 0))
        up = not up
        t += step


def rat(name):
    root = empty(name)
    child(ball(name + "_corpo", 1, (0, 0, 0), M["rat"], scale=(0.42, 0.22, 0.2)), root, (0, 0, 0.2))
    child(ball(name + "_cabeca", 0.15, (0, 0, 0), M["rat"]), root, (0.42, 0, 0.25))
    for s in (1, -1):
        child(ball(f"{name}_orelha{s}", 0.07, (0, 0, 0), M["pink"]), root, (0.42, 0.1 * s, 0.38))
    child(tube(name + "_rabo", (0, 0, 0), (-0.55, 0, -0.12), 0.03, M["pink"], seg=6), root, (-0.4, 0, 0.18))
    return root


def flame(name, size=1.0):
    root = empty(name)
    cones = []
    for i, (dx, dy, h, r, mm) in enumerate([(0, 0, 1.0, 0.32, "fire"), (0.2, 0.05, 0.7, 0.22, "fire"),
                                            (-0.19, -0.04, 0.75, 0.22, "fire"), (0, -0.08, 0.55, 0.17, "fire_core")]):
        c = child(cone(f"{name}_{i}", r * size, h * size, M[mm]), root, (dx * size, dy * size, 0))
        cones.append(c)
    return root, cones


def burn(name, loc, t0, t1, size=1.0):
    root, cones = flame(name, size)
    root.location = loc
    pop_in(root, t0, 0.3)
    hide_from(root, t1)
    for c in cones:
        flicker(c, t0, t1, amp=0.35)
    return root


# ================================================================ céu, terreno, decoração
sky = Sky()
far_ground(M, y0=14)
CLOUDS = [(-15, 60, 26), (5, 70, 30), (25, 55, 24), (45, 75, 32), (-55, 50, 22), (-95, 62, 27), (-120, 70, 30), (-75, 66, 25)]
decor(M, fence=None, clouds=CLOUDS)

# ---------------------------------------------------------------- LIXÃO (ilha em x = LX)
LX = -100
terrain("lixao", LX - 20, LX + 20, [(0, 14, [])], M)
decor(M, fence=(LX - 20, LX + 20, 12.9),
      trees=[(LX - 17, 10), (LX - 13, 12), (LX - 8, 10.5), (LX + 2, 12.2), (LX + 6, 10.4), (LX + 16.5, 11.5), (LX - 19, 6.5), (LX + 18, 7.5)],
      seed=9)
house("lixao_casa", LX + 12.8, 2.6, M)

# ================================================================ CENA 1 — despejo do lixo (0 – 4.2)
PILE = Vector((LX - 2.5, 4.4, 0))
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=9, radius1=4.2, radius2=0.7, depth=2.6, matrix=Matrix.Translation((0, 0, 1.3)))
for v in bm.verts:
    if 0.1 < v.co.z < 2.5:
        v.co += Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), rnd.uniform(-0.2, 0.2)))
pile = mesh_obj("monte_lixo", bm, M["trash_pile"], PILE)
ks(pile, 0.95, 0.0)
ks(pile, 1.15, (0.35, 0.35, 0.25))
ks(pile, 1.9, (0.75, 0.75, 0.65))
ks(pile, 2.7, (1, 1, 1))

trk, hinge = truck("caminhao")
path(trk, [(0.1, (LX + 17, 4.4, 0)), (0.95, (LX + 4.4, 4.4, 0)), (2.35, (LX + 4.4, 4.4, 0)), (3.0, (LX + 19, 4.4, 0))])
k(hinge, "rotation_euler", 0.95, (0, 0, 0))
k(hinge, "rotation_euler", 1.4, (0, math.radians(-42), 0))
k(hinge, "rotation_euler", 2.0, (0, math.radians(-42), 0))
k(hinge, "rotation_euler", 2.3, (0, 0, 0))

for i in range(16):
    j = junk(f"queda{i}", 0.45)
    t = 1.15 + 0.06 * i
    r, a = rnd.uniform(0.6, 3.4), rnd.uniform(-0.3, 3.4)
    end = PILE + Vector((r * math.cos(a), max(-4.0, r * math.sin(a)), 2.6 * (1 - r / 4.2) + 0.05))
    end.y = max(end.y, 0.5)
    start = Vector((LX + 1.6, 4.4 + rnd.uniform(-0.6, 0.6), 2.2))
    hide_until(j, t)
    path(j, [(t, start), (t + 0.22, (start + end) / 2 + Vector((0, 0, 0.6))), (t + 0.45, end)])
for i in range(10):  # lixo espalhado em volta: "já tem um lixão"
    a = rnd.uniform(0, 6.28)
    r = rnd.uniform(4.3, 6.0)
    j = junk(f"espalhado{i}", 0.4)
    j.location = PILE + Vector((r * math.cos(a), max(-3.8, r * math.sin(a)), 0.0))
    pop_in(j, 3.1 + i * 0.05, 0.3)

flies = []
for i in range(9):
    piv = empty(f"mosca_piv{i}", PILE + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 0.5), 3.0 + rnd.uniform(0, 1.2))))
    f = child(ball(f"mosca{i}", 0.07, (0, 0, 0), M["dark"]), piv, (rnd.uniform(0.6, 1.6), 0, 0))
    pop_in(f, 3.15 + i * 0.04, 0.2)
    k(piv, "rotation_euler", 3.1, (0, 0, rnd.uniform(0, 6)))
    k(piv, "rotation_euler", 11.9, (0, 0, rnd.choice((-1, 1)) * 2 * math.pi * 14))

# ================================================================ CENA 2 — chuva e chorume (4.2 – 11.9)
sky.day(4.2)
sky.state(4.7, 1.6, 0.55, "#7d8ea3", "#c5ccd4", "#dfe6ee")
sky.state(7.0, 1.6, 0.55, "#7d8ea3", "#c5ccd4", "#dfe6ee")
sky.day(7.8)
nuvem = empty("nuvem_chuva", PILE + Vector((0.5, 0.5, 10.5)))
for i, (dx, dz, r) in enumerate([(0, 0, 2.6), (2.6, 0.3, 2.0), (-2.6, -0.1, 2.1), (1.2, 1.3, 1.8), (-1.3, 1.0, 1.7)]):
    child(ball(f"nuvem_c{i}", r, (0, 0, 0), M["cloud_dark"], scale=(1.3, 1, 0.7)), nuvem, (dx, 0, dz))
pop_in(nuvem, 4.2, 0.4)
pop_out(nuvem, 7.15, 0.35)
for i in range(42):
    x, y = PILE.x + rnd.uniform(-6.5, 6.5), rnd.uniform(0.3, 8)
    d = box(f"chuva{i}", -0.03, 0.03, -0.03, 0.03, 0, 0.55, M["rain"])
    top = (x, y, 9.0)
    r = math.hypot(x - PILE.x, y - PILE.y)
    zb = max(0.0, 2.6 * (1 - r / 4.2)) + 0.05
    d.location = top
    loop_fall(d, 4.25, 7.0, top, (x, y, zb), rnd.uniform(0.38, 0.5), rnd.uniform(0, 0.4))
# gotas pretas escorrendo pelo monte
for i in range(9):
    x = PILE.x + rnd.uniform(-2.6, 2.6)
    g = ball(f"gota_monte{i}", 0.13, (x, 2.6, 1.7), M["drip"], scale=(1, 1, 1.4))
    along(g, [(x, 2.6, 1.7), (x, 0.15, 0.06)], 5.0 + i * 0.12, 7.0 + i * 0.1, loops=2)
# pluma de chorume no corte do terreno
col_pts = [(LX - 5.6, -0.2), (LX + 0.6, -0.2), (LX + 0.9, -1.8), (LX + 0.4, -3.5), (LX + 1.1, -5.2), (LX + 0.6, -7.5),
           (LX - 4.8, -7.5), (LX - 5.4, -5.6), (LX - 6.1, -3.9), (LX - 5.3, -2.0)]
col = prism("pluma_coluna", col_pts, -0.03, -0.01, M["plume"], origin=(LX - 2.5, -0.2))
grow_z(col, 6.4, 8.4)
tongue_pts = [(LX - 5.0, -7.5), (LX + 3.0, -7.5), (LX + 6.0, -7.7), (LX + 8.7, -7.6), (LX + 8.9, -8.6), (LX + 7.0, -9.3),
              (LX + 3.5, -9.6), (LX - 1.0, -9.3), (LX - 4.6, -9.5), (LX - 5.4, -8.4)]
tongue = prism("pluma_lingua", tongue_pts, -0.03, -0.01, M["plume"], origin=(LX - 5.4, -8.5))
grow(tongue, 8.2, 9.7, "x")
for i in range(8):
    x = LX - 5.2 + i * 0.75
    g = ball(f"gota_solo{i}", 0.12, (x, -0.12, -0.3), M["drip"])
    along(g, [(x, -0.12, -0.3), (x, -0.12, -7.6)], 6.6 + i * 0.1, 8.8 + i * 0.06, loops=2)
for i in range(6):
    z = -8.0 - i * 0.22
    g = ball(f"gota_lencol{i}", 0.12, (LX + 0.5, -0.12, z), M["drip"])
    along(g, [(LX + 0.5, -0.12, z), (LX + 8.0, -0.12, z)], 8.4 + i * 0.12, 9.9, loops=2)
glow(M["plume"], 10.3, 11.7, "#6b8f22", peak=0.25)

# poço (corte) + casa
WX = LX + 8.0
box("poco_parede", WX - 0.45, WX + 0.45, -0.05, 0.9, -9.6, 0.0, M["concrete"])
box("poco_ar", WX - 0.28, WX + 0.28, -0.07, 0.8, -7.6, 0.0, M["dark"])
box("poco_agua", WX - 0.28, WX + 0.28, -0.07, 0.8, -9.5, -7.6, M["well_water"])
key_input(M["well_water"], "Base Color", 9.3, lin("#3a8ee6"))
key_input(M["well_water"], "Base Color", 10.0, lin("#2e2216"))
cyl("poco_boca", 0.95, 0.0, 0.85, (WX, 0.95), M["stone_wall"], seg=12)
cyl("poco_boca_in", 0.7, 0.05, 0.9, (WX, 0.95), M["dark"], seg=12)
for s in (-1, 1):
    box(f"poco_poste{s}", WX + s * 0.85 - 0.08, WX + s * 0.85 + 0.08, 0.87, 1.03, 0, 2.3, M["wood"])
box("poco_telhado", WX - 1.2, WX + 1.2, 0.2, 1.7, 2.3, 2.45, M["roof"])
tube("poco_eixo", (WX - 0.85, 0.95, 1.9), (WX + 0.85, 0.95, 1.9), 0.06, M["wood"])
pawn = empty("pessoa", (WX + 2.0, 1.4, 0))
child(cyl("pessoa_corpo", 0.28, 0, 0.9, (0, 0), M["pawn"]), pawn)
child(ball("pessoa_cabeca", 0.24, (0, 0, 0), M["pawn"]), pawn, (0, 0, 1.15))
pop_in(pawn, 8.9, 0.35)
key_input(M["pawn"], "Base Color", 10.0, lin("#3b6fd6"))
key_input(M["pawn"], "Base Color", 10.7, lin("#7fae3a"))

# ---------------------------------------------------------------- ATERRO (x = 0)
EXC = sg.Polygon([(-12, 5), (-6, -5), (6, -5), (12, 5)])
UP = sg.box(-60, -60, 60, 0)
CLAY_IN = EXC.buffer(-0.5, join_style=2)
MEMB_IN = EXC.buffer(-0.62, join_style=2)
ZB = -4.38                      # fundo interno (topo da manta)
XR0 = 5.65 + 0.6 * (0 - ZB)     # meia-largura interna na boca da cava
MOUND = 3.4 / 2.76              # inclinação do morro acima do chão
Y_IN = (0.0, 9.38)
L1, L2 = (-19.0, -12.5), (-27.5, -21.0)


def xr(z):
    return 5.65 + 0.6 * (z - ZB) if z <= 0 else XR0 - z * MOUND


def layer_pts(z0, z1):
    pts = [(-xr(z0), z0), (xr(z0), z0)]
    if z0 < 0 < z1:
        pts.append((xr(0), 0))
    pts += [(xr(z1), z1), (-xr(z1), z1)]
    if z0 < 0 < z1:
        pts.append((-xr(0), 0))
    return pts


def layer(name, z0, z1, m):
    return prism_fill(name, layer_pts(z0, z1), Y_IN[0], Y_IN[1], m, z0)


lag = [sg.box(L1[0], -1.2, L1[1], 5), sg.box(L2[0], -1.2, L2[1], 5)]
terrain("aterro", -36, 38, [(0, 7, [EXC] + lag), (7, 10, [EXC]), (10, 16, [])], M)
decor(M, fence=(-36, 38, 14.9),
      trees=[(-33, 12), (-30, 9.5), (-24, 12.5), (-16, 11), (-11, 13), (-7, 12.5), (10, 12.5), (14, 11), (16.5, 13.6),
             (33.5, 12.5), (35.5, 9), (-20, 22), (-5, 25), (8, 22), (20, 26), (34, 22), (-36, 28)], seed=4)
CITY = [(18.5, 2.6), (23.2, 2.2), (27.8, 3.0), (20.5, 8.8), (25.5, 9.2), (30.5, 7.8)]
for i, (hx, hy) in enumerate(CITY):
    house(f"casa{i}", hx, hy, M, win=M["win_lit"])

# liners das lagoas
for (x0, x1) in (L1, L2):
    box(f"lagoa_fundo{x0}", x0, x1, 0, 7, -1.2, -1.1, M["membrane"])
    box(f"lagoa_pe{x0}", x0, x0 + 0.1, 0, 7, -1.2, 0.0, M["membrane"])
    box(f"lagoa_pd{x0}", x1 - 0.1, x1, 0, 7, -1.2, 0.0, M["membrane"])
    box(f"lagoa_tras{x0}", x0, x1, 6.9, 7.0, -1.2, 0.0, M["membrane"])

# ================================================================ CENA 3 — argila compactada (13.9 – 15.7)
clay = prism("argila", EXC.difference(CLAY_IN).intersection(UP), 0, 10, M["clay"])
clay_back = prism("argila_fundo", EXC.intersection(UP), 9.5, 10.0, M["clay"])
for o in (clay, clay_back):
    pop_in(o, 13.95, 0.4)
key_input(M["clay"], "Base Color", 14.2, lin("#c98a62"))
key_input(M["clay"], "Base Color", 15.6, lin("#8f5a40"))
rol, drum = roller("rolo")
rol.location = (-4.4, 4.7, -4.5)
pop_in(rol, 14.0, 0.3)
move(rol, 14.2, 15.6, Vector((-4.4, 4.7, -4.5)), Vector((3.8, 4.7, -4.5)))
k(drum, "rotation_euler", 14.2, (math.pi / 2, 0, 0))
k(drum, "rotation_euler", 15.6, (math.pi / 2, 8.2 / 0.75, 0))
pop_out(rol, 15.75, 0.25)

# ================================================================ CENA 4 — geomembrana (15.8 – 19.9)
memb = CLAY_IN.difference(MEMB_IN).intersection(UP)
mL = memb.intersection(sg.box(-60, -60, -5.4, 60))
mB = memb.intersection(sg.box(-5.4, -60, 5.4, 60))
mR = memb.intersection(sg.box(5.4, -60, 60, 60))
dL, dR = (3 / 5.831, -5 / 5.831), (3 / 5.831, 5 / 5.831)
partL = prism("manta_esq", mL, 0, 9.5, M["membrane"], origin=(-8.35, 0.05), along=dL)
partB = prism("manta_fundo", mB, 0, 9.5, M["membrane"], origin=(-5.4, -4.44), along=(1, 0))
partR = prism("manta_dir", mR, 0, 9.5, M["membrane"], origin=(5.4, -4.44), along=dR)
memb_back = prism("manta_tras", CLAY_IN.intersection(UP), 9.38, 9.5, M["membrane"])
grow(partL, 15.8, 16.5, "x")
grow(partB, 16.5, 17.4, "x")
grow(partR, 17.4, 18.05, "x")
pop_in(memb_back, 16.45, 0.35)
roll = disc("rolo_manta", 0.35, 9.3, M["membrane"], seg=14)
roll.location = (-7.98, 4.7, 0.18)
hide_until(roll, 15.8)
path(roll, [(15.8, (-7.98, 4.7, 0.18)), (16.5, (-5.45, 4.7, -4.03)), (17.4, (5.45, 4.7, -4.03)), (18.05, (7.98, 4.7, 0.18))])
pop_out(roll, 18.1, 0.2)
glow(M["membrane"], 18.37, 19.9, peak=1.0)

# ================================================================ CENA 5 — chorume empoçado (19.9 – 24.7)
T0 = layer("lixo_inicial", ZB, -2.6, M["trash"])
fill(T0, 20.0, 20.9)
hide_from(T0, 24.72)
for i in range(30):
    x, y = rnd.uniform(-6, 6), rnd.uniform(0.6, 8.6)
    d = box(f"chuva_cava{i}", -0.03, 0.03, -0.03, 0.03, 0, 0.55, M["rain"])
    d.location = (x, y, 7.5)
    loop_fall(d, 19.95, 21.6, (x, y, 7.5), (x, y, -2.6), rnd.uniform(0.38, 0.5), rnd.uniform(0, 0.4))
for i in range(9):
    x = -5.0 + i * 1.25
    g = ball(f"gota_lixo{i}", 0.11, (x, -0.12, -2.75), M["drip"])
    along(g, [(x, -0.12, -2.75), (x, -0.12, -4.25)], 20.5 + i * 0.07, 22.4, loops=2)
puddle = prism_fill("chorume_poca", layer_pts(ZB, -3.15), -0.03, 9.36, M["chorume"], ZB)
hide_until(puddle, 21.0)
shape(puddle, "cheio", 21.0, 0.0)
shape(puddle, "cheio", 22.4, 0.3)
shape(puddle, "cheio", 24.3, 1.0)
hide_from(puddle, 24.72)
key_input(M["chorume"], "Emission Color", 22.6, lin("#5d8a1c"))
for t, e in [(22.6, 0.0), (23.2, 0.9), (23.7, 0.3), (24.2, 0.9), (24.7, 0.4)]:
    key_input(M["chorume"], "Emission Strength", t, e)
for i in range(11):
    x = rnd.uniform(-5.5, 5.5)
    b = ball(f"bolha_toxica{i}", rnd.uniform(0.09, 0.16), (x, -0.12, -4.3), M["toxic"])
    loop_fall(b, 22.7, 24.7, (x, -0.12, -4.3), (x, -0.12, -3.3), rnd.uniform(0.6, 0.85), rnd.uniform(0, 0.5))

# ================================================================ CENA 6 — drenagem de chorume (24.7 – 31.7)
P_Z = -4.0
pipe_h = tube("dreno_chorume", (5.5, -0.15, P_Z), (-6.2, -0.15, P_Z), 0.22, M["pipe_leach"])
grow_z(pipe_h, 24.9, 25.7)
pipe_d = tube("dreno_saida", (-6.2, -0.15, P_Z), (-12.6, -0.15, -0.75), 0.22, M["pipe_leach"])
grow_z(pipe_d, 25.7, 26.3)
x = 5.0
while x > -5.9:
    h = tube(f"furo{x:.1f}", (x, -0.33, P_Z), (x, -0.39, P_Z), 0.075, M["hole"], seg=8)
    pop_in(h, 24.9 + (5.5 - x) / 11.7 * 0.8, 0.2)
    x -= 0.85
gravel = layer("brita_fundo", ZB, -3.6, M["gravel"])
fill(gravel, 25.9, 26.8)
lag1 = box("lagoa1_liquido", L1[0] + 0.1, L1[1] - 0.1, 0.0, 6.9, -1.1, -0.35, M["lagoon1"])
grow_z(lag1, 27.9, 29.1)
pipe_l = tube("cano_lagoas", (L1[0] - 0.05, -0.15, -0.6), (L2[1] + 0.05, -0.15, -0.6), 0.15, M["pipe_leach"])
grow_z(pipe_l, 28.6, 28.9)
lag2 = box("lagoa2_liquido", L2[0] + 0.1, L2[1] - 0.1, 0.0, 6.9, -1.1, -0.35, M["lagoon2"])
grow_z(lag2, 28.9, 29.75)
route = [(5.0, -0.42, P_Z), (-6.2, -0.42, P_Z), (-12.6, -0.42, -0.75), (-15.5, -0.42, -0.75)]
for i in range(9):
    g = ball(f"fluxo_chorume{i}", 0.13, route[0], M["drip"])
    along(g, route, 27.2 + i * 0.16, 29.7, loops=2)
glow(M["pipe_leach"], 29.87, 31.67, peak=1.2)

# ================================================================ CENA 7 — lixo exposto, urubus e ratos (31.7 – 36.5)
T1 = layer("lixo_1", -3.6, -1.9, M["trash_old"])
fill(T1, 31.75, 32.2)
add_relative_key(T1, "compacto", layer_pts(-3.6, -2.24))
shape(T1, "compacto", 38.0, 0.0)
shape(T1, "compacto", 39.6, 1.0)
surface = []
for i in range(22):
    j = junk(f"superficie{i}", 0.42)
    x, y = rnd.uniform(-6.6, 6.6), rnd.uniform(0.4, 8.8)
    j.location = (x, y, -1.95)
    pop_in(j, 32.0 + i * 0.02, 0.3)
    pop_out(j, 38.0 + (x + 6.8) / 13.6 * 1.5, 0.15)
vultures = []
for i in range(3):
    orb = empty(f"urubu_orbita{i}", (rnd.uniform(-1.5, 1.5), 4.5, 4.6 + i * 0.9))
    v, hinges = vulture(f"urubu{i}")
    child(v, orb, (3.0 + i * 1.3, 0, 0))
    v.rotation_euler = (0, math.radians(18), 0)
    pop_in(v, 32.1 + i * 0.15, 0.35)
    k(orb, "rotation_euler", 32.1, (0, 0, i * 2.1))
    k(orb, "rotation_euler", 38.2, (0, 0, i * 2.1 + 2 * math.pi * 1.6))
    move(orb, 38.2, 39.6, orb.location.copy(), Vector((24, 14, 15 + i)))
    flap(hinges, 32.1, 39.6)
    hide_from(v, 40.7)
for i in range(3):
    r = rat(f"rato{i}")
    x0 = -4.0 + i * 3.4
    pts = [(32.6 + i * 0.15, (x0, 1.0 + i, -1.92)), (33.5, (x0 + 1.2, 1.4 + i, -1.92)), (34.6, (x0 + 0.4, 2.2 + i, -1.92)),
           (35.8, (x0 + 1.8, 1.6 + i, -1.92)), (37.3, (x0 + 1.0, 1.2 + i, -1.92))]
    r.location = pts[0][1]
    pop_in(r, pts[0][0], 0.3, s=1.7)
    path(r, pts)
    for (ta, pa), (tb, pb) in zip(pts, pts[1:]):
        k(r, "rotation_euler", ta + 0.05, (0, 0, math.atan2(pb[1] - pa[1], pb[0] - pa[0])))
    pop_out(r, 38.2 + i * 0.1, 0.25, s=1.7)

# vento e sacolas voando para a cidade
for i in range(12):
    w = box(f"vento{i}", -1.2, 1.2, -0.03, 0.03, -0.03, 0.03, M["wind"])
    y, z = rnd.uniform(0, 6), rnd.uniform(0.5, 5.5)
    t = 34.1 + rnd.uniform(0, 0.5)
    hide_until(w, 34.1)
    w.location = (-12, y, z)
    while t + 0.7 < 36.4:
        jump(w, "location", t, Vector((30, y, z)), Vector((-12, y, z)))
        k(w, "location", t + 0.7, (30, y, z))
        t += 0.75
    hide_from(w, 36.5)
ends = [(18.5, 3.6, 4.0), (23.2, 2.4, 3.6), (21.0, 1.0, 0.1), (27.8, 3.4, 4.0), (25.5, 1.4, 0.1), (20.5, 10.5, 4.0),
        (16.5, 13.6, 3.2), (30.2, 1.2, 0.1), (19.6, 0.6, 0.1), (26.4, 0.4, 0.1), (29.0, 9.0, 4.2), (32.5, 2.0, 0.1)]
for i, e in enumerate(ends):
    m = M[["bag_w", "bag_b", "bag_w", "bag_k"][i % 4]]
    b = box(f"sacola{i}", -0.5, 0.5, -0.38, 0.38, -0.03, 0.03, m, anchor="center")
    s = Vector((rnd.uniform(-4, 4), rnd.uniform(1, 8), -1.75))
    t0 = 34.25 + i * 0.07
    b.location = s
    pop_in(b, t0, 0.2)
    mid = (s + Vector(e)) / 2 + Vector((0, 0, rnd.uniform(4, 7)))
    path(b, [(t0, s), (t0 + 0.8, mid), (t0 + 1.6, e)])
    k(b, "rotation_euler", t0, (0, 0, 0))
    k(b, "rotation_euler", t0 + 1.6, (rnd.uniform(4, 9), rnd.uniform(2, 6), rnd.uniform(2, 8)))
    hide_from(b, 40.7)

# ================================================================ CENA 8 — fim do dia: trator e cobertura (36.5 – 40.7)
sky.sunset(36.5, 37.4)
sky.state(40.62, 2.2, 0.75, "#5b6fae", "#ffb36b", "#ffb070")
sky.day(40.7)
dz = dozer("trator")
pop_in(dz, 37.9, 0.3)
path(dz, [(37.9, (-6.8, 4.7, -1.9)), (38.0, (-6.8, 4.7, -1.9)), (39.5, (6.6, 4.7, -2.24))])
jump(dz, "rotation_euler", 39.55, (0, 0, 0), (0, 0, math.pi))
path(dz, [(39.55, (6.6, 4.7, -1.94)), (40.45, (-6.6, 4.7, -1.94))])
pop_out(dz, 40.5, 0.15)
S1 = prism("terra_1", layer_pts(-2.24, -1.94), *Y_IN, M["cover"], origin=(xr(-2.24), -2.24), along=(-1, 0))
grow(S1, 39.5, 40.45, "x")

# ================================================================ CENA 9 — bolo de camadas e célula (40.7 – 46.9)
T2 = layer("lixo_2", -1.94, -0.74, M["trash_old"]); fill(T2, 43.45, 43.9)
S2 = layer("terra_2", -0.74, -0.44, M["cover"]); fill(S2, 44.0, 44.35)
T3 = layer("lixo_3", -0.44, 0.76, M["trash"]); fill(T3, 44.7, 45.1)
S3 = layer("terra_3", 0.76, 1.06, M["cover"]); fill(S3, 45.15, 45.5)
cell = empty("celula")
cp = layer_pts(-1.94, -0.44)
for i in range(4):
    a, b = cp[i], cp[(i + 1) % 4]
    child(tube(f"celula_borda{i}", (a[0], -0.14, a[1]), (b[0], -0.14, b[1]), 0.1, M["yellow"], seg=8), cell)
pop_in(cell, 45.75, 0.3)
pop_out(cell, 46.85, 0.2)

# ================================================================ CENA 10 — metano, fogo e explosão (46.9 – 54.0)
hsv = node_of(M["trash_old"], "ShaderNodeHueSaturation")
for t, v in [(47.4, 0.72), (49.0, 0.42)]:
    hsv.inputs["Value"].default_value = v
    hsv.inputs["Value"].keyframe_insert("default_value", frame=mt.F(t))
hsv.inputs["Value"].default_value = 0.42
hsv.inputs["Value"].keyframe_insert("default_value", frame=mt.F(53.95))
hsv.inputs["Value"].default_value = 0.72
hsv.inputs["Value"].keyframe_insert("default_value", frame=mt.F(54.0))
gas = []
for i, (z0, z1) in enumerate([(-3.4, -2.33), (-1.75, -0.83), (-0.3, 0.67)] * 6):
    x = rnd.uniform(-xr(z1) + 0.8, xr(z1) - 0.8)
    b = ball(f"metano{i}", rnd.uniform(0.12, 0.2), (x, -0.2, z0), M["methane"])
    t0 = 48.0 + (i % 6) * 0.38 + rnd.uniform(0, 0.2)
    hide_until(b, t0)
    move(b, t0, t0 + 1.5, Vector((x, -0.2, z0)), Vector((x, -0.2, z1)))
    hide_from(b, 52.55)
    gas.append(b)
pockets = []
for i, (x, z) in enumerate([(-3.5, -2.36), (2.5, -2.36), (-1.5, -0.86), (3.4, -0.86), (-3.0, 0.64), (1.0, 0.64), (4.0, 0.64)]):
    p = ball(f"bolsao{i}", 1.0, (x, -0.15, z), M["methane"], scale=(1.3, 0.5, 0.16))
    grow(p, 50.5 + i * 0.08, 51.4, "x")
    hide_from(p, 52.55)
    pockets.append(p)
for i, x in enumerate((-3.0, 1.0, 4.0)):
    burn(f"fogo{i}", (x, 1.0, 1.06), 51.6 + i * 0.25, 53.95, 0.9 + 0.2 * (i == 1))
C = Vector((1.0, -0.5, 1.6))
for i in range(9):
    off = Vector((rnd.uniform(-1.4, 1.4), rnd.uniform(-0.8, 0.2), rnd.uniform(-0.4, 1.6)))
    core_ = i < 3
    b = ball(f"explosao{i}", rnd.uniform(0.7, 1.0) if core_ else rnd.uniform(1.0, 1.6), C + off * (0.5 if core_ else 1.0),
             M["blast_core"] if core_ else M["blast"], sub=1)
    t0 = 52.5 + i * 0.025
    ks(b, t0, 0.0)
    ks(b, t0 + 0.18, 1.3)
    ks(b, t0 + 0.55, 1.55)
    ks(b, t0 + 0.9, 0.0)
for i in range(7):
    s = ball(f"fumaca{i}", 1.0, C, M["smoke"], sub=1)
    off = Vector((rnd.uniform(-2.5, 2.5), rnd.uniform(-1, 1), rnd.uniform(0.5, 3.5)))
    ks(s, 52.6, 0.0)
    move(s, 52.6, 53.8, C, C + off)
    ks(s, 53.3, rnd.uniform(1.4, 2.4))
    hide_from(s, 53.95)
for i in range(14):
    d = junk(f"destrocos{i}", 0.35)
    v = Vector((rnd.uniform(-7, 7), rnd.uniform(-5, 1), rnd.uniform(6, 11)))
    d.location = C
    hide_until(d, 52.55)
    for n in range(9):
        dt = n * 0.1
        k(d, "location", 52.55 + dt, C + v * dt + Vector((0, 0, -0.5 * 18 * dt * dt)))
    hide_from(d, 53.95)

# ================================================================ CENA 11 — drenos de gás, queima e energia (54.0 – 63.5)
DRAIN_X = (-4.0, 0.0, 4.0)
D_BOT, D_TOP = -3.7, 3.5
drains = []
for i, x in enumerate(DRAIN_X):
    root = empty(f"dreno_gas{i}", (x, -0.15, D_BOT + 6.0))
    child(cyl(f"dreno_tubo{i}", 0.25, 0, D_TOP - D_BOT, (0, 0), M["pipe_gas"], seg=14), root)
    child(cyl(f"dreno_queimador{i}", 0.36, D_TOP - D_BOT, D_TOP - D_BOT + 0.25, (0, 0), M["steel"], seg=14), root)
    z = 0.35
    while z < 1.06 - D_BOT:
        child(tube(f"dreno_furo{i}_{z:.1f}", (0, -0.2, z), (0, -0.28, z), 0.06, M["hole"], seg=8), root)
        z += 0.55
    hide_until(root, 54.3 + i * 0.2)
    move(root, 54.3 + i * 0.2, 55.9 + i * 0.2, Vector((x, -0.15, D_BOT + 6.0)), Vector((x, -0.15, D_BOT)))
    gc = box(f"brita_coluna{i}", x - 0.75, x + 0.75, -0.04, 1.6, D_BOT, 1.06, M["gravel_col"])
    grow_z(gc, 56.75 + i * 0.12, 57.5 + i * 0.12)
    drains.append(root)
for i in range(14):
    lz = [(-3.3, -2.4), (-1.7, -0.9), (-0.3, 0.6)][i % 3]
    x0 = rnd.uniform(-6, 6)
    dx = min(DRAIN_X, key=lambda d: abs(d - x0))
    z = rnd.uniform(*lz)
    b = ball(f"gas_dreno{i}", 0.15, (x0, -0.35, z), M["methane"])
    t0 = 57.8 + (i % 7) * 0.22
    along(b, [(x0, -0.35, z), (dx + (0.35 if x0 > dx else -0.35), -0.35, z), (dx, -0.5, z), (dx, -0.5, D_TOP + 0.2)], t0, t0 + 1.5)
for i, x in enumerate(DRAIN_X[:2]):
    burn(f"chama_dreno{i}", (x, -0.15, D_TOP + 0.25), 59.0 + i * 0.15, DUR + 1, 0.8)

# usina de energia + rede elétrica
plant = empty("usina", (14.0, 3.0, 0))
child(box("usina_corpo", -1.6, 1.6, -1.5, 1.5, 0, 2.4, M["plant"]), plant)
child(box("usina_teto", -1.75, 1.75, -1.65, 1.65, 2.4, 2.6, M["dark"]), plant)
child(cyl("usina_chamine", 0.3, 2.6, 4.2, (0.9, 0.6), M["concrete_dark"], seg=10), plant)
child(box("usina_porta", -0.45, 0.45, -1.53, -1.5, 0, 1.5, M["dark"]), plant)
pop_in(plant, 60.25, 0.4)
zig = [(-0.25, 0.75), (0.3, 0.75), (0.05, 0.15), (0.35, 0.15), (-0.3, -0.75), (-0.05, -0.1), (-0.35, -0.1)]
bolt = prism("raio", [(14.0 + x, 3.9 + z) for x, z in zig], 1.25, 1.35, M["yellow"], origin=(14.0, 3.9))
pop_in(bolt, 60.7, 0.35)
header = tube("tubo_gas_usina", (4.25, -0.15, D_TOP - 0.3), (12.4, 2.2, 1.6), 0.18, M["pipe_gas"])
grow_z(header, 60.2, 60.6)
for i in range(6):
    g = ball(f"gas_usina{i}", 0.14, (4.25, -0.15, 3.2), M["methane"])
    along(g, [(4.25, -0.45, D_TOP - 0.3), (12.4, 1.9, 1.6)], 60.6 + i * 0.12, 61.5)
poles = [(16.6, 0.9), (21.0, 0.9), (25.6, 0.9), (30.2, 0.9)]
prev = (15.6, 3.0, 2.4)
for i, (px, py) in enumerate(poles):
    pole = empty(f"poste{i}", (px, py, 0))
    child(cyl(f"poste_m{i}", 0.1, 0, 4.2, (0, 0), M["pole"], seg=8), pole)
    child(box(f"poste_x{i}", -0.6, 0.6, -0.06, 0.06, 3.9, 4.05, M["pole"]), pole)
    pop_in(pole, 60.75 + i * 0.1, 0.3)
    w = tube(f"fio{i}", prev, (px, py, 4.05), 0.03, M["wire"], seg=6)
    grow_z(w, 60.8 + i * 0.1, 61.0 + i * 0.1)
    prev = (px, py, 4.05)
key_input(M["win_lit"], "Emission Color", 60.9, lin("#ffd76a"))
key_input(M["win_lit"], "Emission Strength", 60.9, 0.0)
key_input(M["win_lit"], "Emission Strength", 61.4, 2.5)
glow(M["pipe_gas"], 61.8, 63.17, peak=1.2)

# ================================================================ CENA 12 — jornal de 40 anos (63.5 – 70.0)
items = [tube("garrafa", (0.4, -0.08, -1.2), (1.05, -0.08, -1.05), 0.13, M["bottle"]),
         tube("lata", (3.1, -0.08, -1.65), (3.4, -0.08, -1.45), 0.11, M["can"]),
         ball("saco", 0.28, (3.5, -0.06, -0.98), M["bag_b"], scale=(1.3, 0.6, 0.8)),
         box("caixa", 0.55, 1.15, -0.1, 0.25, -1.82, -1.45, M["wood"])]
for o in items:
    hide_until(o, 63.4)
    hide_from(o, 69.95)
news = empty("jornal", (2.0, -0.08, -1.32))
child(box("jornal_papel", -0.7, 0.7, -0.015, 0.015, -0.9, 0.9, M["paper"], anchor="center"), news)
child(box("jornal_titulo", -0.6, 0.6, -0.03, -0.015, 0.45, 0.68, M["ink"], anchor="center"), news)
child(text("jornal_ano", "1986", 0.3, (0, -0.035, 0.12), M["ink"]), news)
child(box("jornal_foto", -0.6, -0.05, -0.03, -0.015, -0.55, 0.02, M["ink_gray"], anchor="center"), news)
for j in range(6):
    z = 0.0 - j * 0.11
    child(box(f"jornal_linha{j}", 0.05, 0.6, -0.03, -0.015, z - 0.025, z + 0.025, M["ink_gray"], anchor="center"), news)
for j in range(2):
    z = -0.68 - j * 0.1
    child(box(f"jornal_rodape{j}", -0.6, 0.6, -0.03, -0.015, z - 0.025, z + 0.025, M["ink_gray"], anchor="center"), news)
hide_until(news, 63.4)
k(news, "scale", 63.4, (0.42, 0.42, 0.42))
k(news, "rotation_euler", 63.4, (0, math.radians(24), 0))
k(news, "location", 66.3, (2.0, -0.08, -1.32))
k(news, "scale", 66.3, (0.42, 0.42, 0.42))
k(news, "rotation_euler", 66.3, (0, math.radians(24), 0))
k(news, "location", 67.6, (2.0, -2.4, 0.45))
k(news, "scale", 67.6, (1.35, 1.35, 1.35))
k(news, "rotation_euler", 67.6, (0, 0, 0))
hide_from(news, 69.95)

# ================================================================ CENA 13 — parabéns: aterro completo (70.0 – 72.8)
T4 = layer("lixo_4", 1.06, 2.26, M["trash"]); fill(T4, 70.05, 70.35)
S4 = layer("terra_4", 2.26, 2.56, M["cover"]); fill(S4, 70.3, 70.5)
# capa final de terra + grama cobrindo topo e encostas do morro
top_in = [(-XR0, 0), (XR0, 0), (xr(2.56), 2.56), (-xr(2.56), 2.56)]
top_out = [(-XR0 - 0.35, 0), (XR0 + 0.35, 0), (xr(2.56) + 0.35, 2.86), (-xr(2.56) - 0.35, 2.86)]
cap = prism("capa_final", sg.Polygon(top_out).difference(sg.Polygon(top_in)), 0.0, Y_IN[1] + 0.12, M["grass"])
grow_z(cap, 70.45, 70.75)

# ================================================================ câmeras
LXc = LX
SHOTS = [
    (0.0, [(0.0, (LXc + 3, -23, 6.5), (LXc + 1, 3, 1.4)), (4.2, (LXc + 2, -22.5, 6.2), (LXc + 0.5, 3, 1.4)), (7.0, (LXc + 2, -22, 6.0), (LXc, 3, 1.2))]),
    (7.0, [(7.0, (LXc + 3, -27, -1.5), (LXc + 2, 2, -4.0)), (10.2, (LXc + 3.5, -26, -2.0), (LXc + 2.5, 2, -4.5)), (11.9, (LXc + 3.5, -25, -2.0), (LXc + 2.5, 2, -4.5))]),
    (11.9, [(11.9, (1, -31, 6), (0, 4, -1.8)), (13.9, (0.5, -28, 4), (0, 4, -2.2))]),
    (13.9, [(13.9, (0, -25, 1.5), (0, 4, -2.6)), (18.3, (0, -24, 1.0), (0, 4, -2.8)), (19.9, (0.5, -23, 1.0), (0, 4, -2.8))]),
    (19.9, [(19.9, (1, -22, 0.5), (0, 4, -2.8)), (22.5, (0.5, -20, -0.5), (0, 4, -3.3)), (24.72, (0, -17, -1.5), (0, 4, -3.8))]),
    (24.72, [(24.72, (-1, -20, 0.0), (-1, 3, -3.0)), (27.3, (-2, -21, 0.5), (-2, 3, -3.0)), (29.2, (-15, -24, 2.5), (-16, 3, -0.8)), (29.8, (-15.5, -24, 2.5), (-16.5, 3, -0.8))]),
    (29.8, [(29.8, (-8, -37, 4), (-8, 3, -2.2)), (31.7, (-7.5, -36, 4), (-7.5, 3, -2.2))]),
    (31.7, [(31.7, (0, -24, 5), (0, 4, 0.8)), (34.1, (0, -24, 5.5), (0, 4, 1.0)), (36.0, (19, -26, 6), (22, 6, 2.0)), (36.5, (19.5, -26, 6), (22.5, 6, 2.0))]),
    (36.5, [(36.5, (0, -23, 4), (0, 4, -1.2)), (40.7, (0, -22, 3.5), (0, 4, -1.4))]),
    (40.7, [(40.7, (0, -27, 3), (0, 4, -1.2)), (46.9, (0, -25, 2.5), (0, 4, -1.0))]),
    (46.9, [(46.9, (0, -19, -1.5), (0, 3, -2.0)), (50.4, (0, -21, 0.0), (0, 3, -1.0)), (51.5, (0, -26, 3.0), (0, 3, 0.6)), (54.0, (0, -26, 3.0), (0, 3, 0.6))]),
    (54.0, [(54.0, (0, -24, 1.0), (0, 3, -1.0)), (57.6, (0, -24, 2.5), (0, 3, 0.8)), (60.1, (0, -24, 2.5), (0, 3, 0.8)),
            (60.9, (10, -28, 4.5), (12, 4, 1.8)), (61.6, (10, -28, 4.5), (12, 4, 1.8)), (62.3, (1, -27, 3), (0, 3, 0.2)), (63.5, (1, -26.5, 3), (0, 3, 0.2))]),
    (63.5, [(63.5, (2.4, -6.0, -0.9), (2.0, 0, -1.3)), (66.2, (2.3, -5.2, -1.0), (2.0, 0, -1.3)), (67.6, (2.0, -8.2, 0.5), (2.0, -2.4, 0.45)), (70.0, (2.0, -7.9, 0.5), (2.0, -2.4, 0.45))]),
    (70.0, [(70.0, (2, -30, 8), (0, 4, 0)), (DUR, (5, -52, 17), (1, 6, 0))]),
]
cameras(SHOTS, shakes=[(52.5, 53.4, 0.35)])
WHIPS = [11.9, 24.72, 54.0, 70.0]
write_cuts(os.path.join(HERE, "cortes.json"), WHIPS, DUR)
save(os.path.join(HERE, "aterro.blend"))
