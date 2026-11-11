"""Vídeo: "Mofo no teto do banheiro limpo todo mês" — canal "dentro da sua casa".

Uso:  python cena.py   ->  mofo_banheiro.blend + cortes.json + carimbos.json
Prédio de apartamentos em corte (casa de bonecas, frente aberta em y = 0). O banheiro do morador fica no meio, com o
apartamento de cima e o de baixo visíveis; o teto do banheiro (laje) é a estrela: mancha, vapor, gotas, corte em
camadas. Os tempos vêm das FRASES do roteiro.srt (motor3d/roteiro.py): com a gravação nova, troque o .srt e rode de
novo — a cena, os cortes e os carimbos se reajustam.
"""
import sys, os, math, random, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "motor3d"))
import bpy, bmesh
from mathutils import Vector
import motor as mt
import pecas as pc
from roteiro import Roteiro
from motor import (mat, lin, box, box_bm, cyl, tube, ball, arrow, mesh_obj, empty, pop_in, pop_out, grow, hide_until,
                   hide_from, move, path, jump, k, ks, glow, key_input, Sky, cameras, write_cuts, save, bsdf)

HERE = os.path.dirname(os.path.abspath(__file__))
R = Roteiro(os.path.join(HERE, "roteiro.srt"))
DUR = round(R.duracao + 0.2, 2)
mt.setup(DUR)
mt.scene.cycles.transparent_max_bounces = 8        # vapor translúcido em camadas
rnd = random.Random(12)
T, FIM = R.t, R.fim

# ================================================================ materiais
M = {n: mat(n, c, **kw) for n, c, kw in [
    ("paint_w", "#eee8da", {}), ("teto", "#f6f5ef", {}), ("massa", "#efe3c8", {}), ("reboco", "#d9c7a5", {}),
    ("laje", "#9e9e9e", {}), ("contrapiso", "#b4a891", {}), ("slab_w", "#f1efe8", {}), ("core", "#cfc6b4", {}),
    ("reveal", "#f3ede0", {"emit": 0.3}), ("frame", "#b98a5e", {}), ("yellow", "#ffc928", {"emit": 1.2}),
    ("mold_sec", "#3d4a26", {}), ("wet_sec", "#4fc3f7", {"alpha": 0.3, "emit": 0.15}),
    ("water_sh", "#a9dcf5", {"alpha": 0.75, "emit": 0.5}), ("rain", "#a9dcf5", {"alpha": 0.75, "emit": 0.5}),
    ("patch", "#ffffff", {}), ("flake", "#f3f1ea", {}), ("rebar", "#5b5f66", {}), ("tampa_m", "#f1efe8", {}),
    ("far_bld", "#c9d3dc", {}), ("far_bld2", "#d9d2c6", {}), ("far_win", "#9fc3e6", {}), ("leaf", "#3f9b46", {}),
    ("rug", "#f2b5a0", {}),
]}
pc.materiais_banheiro(M)
M["tile_b"] = pc.ladrilho_mat("tile_b", "#9fd8cf", "#96d1c7", "#ffffff", tam=(0.2, 0.2))
M["floor_b"] = pc.ladrilho_mat("floor_b", "#e8edf1", "#dce4ea", "#b5c0ca", tam=(0.4, 0.4), piso=True)
M["tile_up"] = pc.ladrilho_mat("tile_up", "#f6c9d3", "#f1bfcb", "#ffffff", tam=(0.2, 0.2))
M["floor_up"] = pc.ladrilho_mat("floor_up", "#efe2cf", "#e6d6bf", "#c9b79c", tam=(0.4, 0.4), piso=True)
M["tile_dn"] = pc.ladrilho_mat("tile_dn", "#f5e3a1", "#efdb93", "#ffffff", tam=(0.2, 0.2))
M["wood_f"] = pc.ladrilho_mat("wood_f", "#c99a66", "#bd8e5b", "#a87a4a", tam=(0.9, 0.15), junta_tam=0.01, piso=True)
for nome, cor in (("wall_y", "#f3e3b3"), ("wall_b", "#cfe1f2"), ("wall_p", "#f5d3c6"), ("wall_g", "#d6ead0"),
                  ("wall_l", "#e3d9f0")):
    M[nome] = mat(nome, cor)

# ================================================================ medidas (m)
W, D, H = 2.4, 2.0, 2.5           # banheiro: largura (x), fundo (y), pé-direito (z)
SLAB = 0.265                       # laje entre andares (acabamento do teto + laje + contrapiso + piso)
ANDAR = H + SLAB
XL, XR = -2.7, 5.2                 # cômodos vizinhos (esquerda e direita do banheiro)
WT = 0.12                          # parede interna
FT = 0.22                          # fachada (parede do fundo)
BOX_X = 0.95                       # box do chuveiro: x de 0 a BOX_X
CORT_Y = 0.32                      # varão da cortina
WIN_B = (1.1, 1.6, 1.78, 2.22)     # vitrô do banheiro: x0, x1, z0, z1
VASO_X, PIA_X = 1.35, 2.0
EXA = (2.0, 2.2)                   # exaustor na parede do fundo (x, z)
LUZ = (1.2, 1.0)                   # plafon (x, y)
PORTA_Y = (0.22, 0.92)             # porta na parede da direita
INT = (1.12, 1.18)                 # interruptor (y, z) na parede da direita
PISO_E = 0.016                     # espessura do piso acabado (fica por cima da laje)
CAMADAS = [("teto", 0.0, 0.012), ("massa", 0.012, 0.035), ("reboco", 0.035, 0.07), ("laje", 0.07, 0.2),
           ("contrapiso", 0.2, SLAB - PISO_E)]


def caixa(name, x0, x1, y0, y1, z0, z1, m, org):
    """Caixa com origem em `org` (para crescer a partir de um canto)."""
    bm = bmesh.new()
    box_bm(bm, x0 - org[0], x1 - org[0], y0 - org[1], y1 - org[1], z0 - org[2], z1 - org[2])
    return mesh_obj(name, bm, m, org)


# ================================================================ prédio em corte
def paredes_comodo(pref, z0, x0, x1, parede, jan):
    """Acabamento colorido das 3 paredes de um cômodo (fundo com o vão da janela)."""
    pc.parede_furada(pref + "_parede_fundo", "x", (D - 0.02, D), x0, x1, z0, z0 + H, [(jan[0], jan[1], z0 + 1.0, z0 + 2.1)],
                  M[parede])
    box(pref + "_parede_e", x0, x0 + 0.02, 0, D - 0.02, z0, z0 + H, M[parede])
    box(pref + "_parede_d", x1 - 0.02, x1, 0, D - 0.02, z0, z0 + H, M[parede])


def comodo_quarto(pref, z0, x0, x1, parede, var):
    """Quarto do vizinho (cama, criado, planta, tapete)."""
    box(pref + "_piso", x0, x1, 0, D, z0 - PISO_E, z0, M["wood_f"])
    paredes_comodo(pref, z0, x0, x1, parede, (XL + 0.6, XL + 1.9))
    cm = pc.cama(pref + "_cama", M, comprimento=1.9, largura=1.4)
    cm.location = ((x0 + x1) / 2 + 0.35 * var, D - 0.05, z0)
    cm.rotation_euler = (0, 0, -math.pi / 2)
    pl = pc.vaso_planta(pref + "_planta", M, altura=0.7, folhas=8, seed=3 + var)
    pl.location = (x0 + 0.35, 0.55, z0)
    pc.caixa_arred(pref + "_criado", x1 - 0.55, x1 - 0.15, D - 0.45, D - 0.05, z0, z0 + 0.5, M["table_wood"], r=0.02)
    ball(pref + "_tapete", 1, ((x0 + x1) / 2, 0.8, z0 + 0.003), M["rug"] if "rug" in M else M["blanket"], sub=2,
         scale=(0.9, 0.55, 0.003))


def comodo_sala(pref, z0, x0, x1, parede, var):
    """Sala do vizinho (mesa, cadeiras, pendente, frutas, planta)."""
    box(pref + "_piso", x0, x1, 0, D, z0 - PISO_E, z0, M["wood_f"])
    paredes_comodo(pref, z0, x0, x1, parede, (W + WT + 0.55, W + WT + 1.85))
    ms = pc.mesa(pref + "_mesa", M)
    ms.location = ((x0 + x1) / 2, 1.05, z0)
    for i, (dx, r) in enumerate(((-0.75, -math.pi / 2), (0.75, math.pi / 2))):
        c = pc.cadeira(f"{pref}_cad{i}", M)
        c.location = ((x0 + x1) / 2 + dx, 1.05, z0)
        c.rotation_euler = (0, 0, r)
    pc.fruteira(pref + "_frutas", M, seed=var).location = ((x0 + x1) / 2, 1.05, z0 + 0.75)
    pc.pendente(pref + "_pend", M, altura_fio=0.6).location = ((x0 + x1) / 2, 1.05, z0 + H)
    pl = pc.vaso_planta(pref + "_planta", M, altura=0.85, folhas=9, seed=7 + var)
    pl.location = (x1 - 0.4, D - 0.45, z0)


def janela_grande(pref, z0, x0, x1):
    """Janela de correr da fachada (moldura + 2 vidros)."""
    for nm, (a, b, c, d) in (("i", (x0 - 0.05, x1 + 0.05, 0.95, 1.0)), ("s", (x0 - 0.05, x1 + 0.05, 2.1, 2.15)),
                             ("e", (x0 - 0.05, x0, 1.0, 2.1)), ("d", (x1, x1 + 0.05, 1.0, 2.1))):
        box(f"{pref}_jan_{nm}", a, b, D - 0.04, D + 0.04, z0 + c, z0 + d, M["frame"])
    xm = (x0 + x1) / 2
    box(f"{pref}_jan_m", xm - 0.025, xm + 0.025, D - 0.02, D + 0.02, z0 + 1.0, z0 + 2.1, M["frame"])
    box(f"{pref}_jan_v", x0, x1, D + 0.05, D + 0.06, z0 + 1.0, z0 + 2.1, M["glass_w"])


def andar(pref, z0, var, banheiro_detalhado=False):
    """Um andar: quarto à esquerda, banheiro no meio, sala à direita, fachada com janelas e laje de cima."""
    paredes = ["wall_y", "wall_b", "wall_p", "wall_g", "wall_l"]
    pq, ps = paredes[var % 5], paredes[(var + 2) % 5]
    comodo_quarto(pref + "_q", z0, XL, -WT, pq, var)
    comodo_sala(pref + "_s", z0, W + WT, XR, ps, var)
    # paredes internas (miolo + acabamento) e laterais do prédio
    for nm, x0, x1 in (("pe", -WT, 0.0), ("le", XL - WT, XL), ("ld", XR, XR + WT)):
        box(f"{pref}_{nm}", x0, x1, 0, D, z0 - PISO_E, z0 + H, M["core"])
    pc.parede_furada(f"{pref}_pd", "y", (W, W + WT), 0, D, z0 - PISO_E, z0 + H, [(PORTA_Y[0], PORTA_Y[1], z0 - PISO_E, z0 + 2.1)],
                  M["core"])
    # fachada com os vãos (vitrô do banheiro + janelas dos quartos)
    furos = [(WIN_B[0], WIN_B[1], z0 + WIN_B[2], z0 + WIN_B[3]), (XL + 0.6, XL + 1.9, z0 + 1.0, z0 + 2.1),
             (W + WT + 0.55, W + WT + 1.85, z0 + 1.0, z0 + 2.1)]
    pc.parede_furada(f"{pref}_fachada", "x", (D, D + FT), XL - WT, XR + WT, z0 - PISO_E, z0 + H, furos, M["core"])
    for nm, (x0, x1, za, zb) in (("vi", (WIN_B[0], WIN_B[1], WIN_B[2], WIN_B[2] + 0.01)),
                                 ("vs", (WIN_B[0], WIN_B[1], WIN_B[3] - 0.01, WIN_B[3])),
                                 ("ve", (WIN_B[0], WIN_B[0] + 0.01, WIN_B[2], WIN_B[3])),
                                 ("vd", (WIN_B[1] - 0.01, WIN_B[1], WIN_B[2], WIN_B[3]))):
        box(f"{pref}_vao_{nm}", x0, x1, D, D + FT, z0 + za, z0 + zb, M["reveal"])
    for x0, x1, nm in ((XL + 0.6, XL + 1.9, "q"), (W + WT + 0.55, W + WT + 1.85, "s")):
        janela_grande(f"{pref}_{nm}", z0, x0, x1)
        for a in (("vi", (x0, x1, 1.0, 1.01)), ("vs", (x0, x1, 2.09, 2.1)), ("ve", (x0, x0 + 0.01, 1.0, 2.1)),
                  ("vd", (x1 - 0.01, x1, 1.0, 2.1))):
            box(f"{pref}_{nm}_vao_{a[0]}", a[1][0], a[1][1], D, D + FT, z0 + a[1][2], z0 + a[1][3], M["reveal"])
    # laje de cima (corte em 3 faixas: acabamento do teto, laje, contrapiso+piso)
    zc = z0 + H
    for nm, a, b, m in (("forro", 0.0, 0.07, "slab_w"), ("laje", 0.07, 0.2, "laje"), ("piso", 0.2, SLAB - PISO_E, "contrapiso")):
        if banheiro_detalhado:
            for sx0, sx1, tag in ((XL - WT, -WT, "e"), (W + WT, XR + WT, "d")):
                box(f"{pref}_teto_{nm}_{tag}", sx0, sx1, 0, D + FT, zc + a, zc + b, M[m])
        else:
            box(f"{pref}_teto_{nm}", XL - WT, XR + WT, 0, D + FT, zc + a, zc + b, M[m])
    if banheiro_detalhado:                   # sobre as paredes do banheiro, a faixa lisa continua
        for sx0, sx1, tag in ((-WT, 0.0, "e"), (W, W + WT, "d")):
            for nm, a, b, m in (("forro", 0.0, 0.07, "slab_w"), ("laje", 0.07, 0.2, "laje"),
                                ("piso", 0.2, SLAB - PISO_E, "contrapiso")):
                box(f"{pref}_teto_{nm}_p{tag}", sx0, sx1, 0, D + FT, zc + a, zc + b, M[m])


def banheiro(pref, z0, tile, floor, var):
    """Banheiro (azulejo, louças, box com cortina, vitrô, exaustor, espelho, porta). Retorna dict das peças."""
    B = {}
    box(pref + "_piso", 0, W, 0, D, z0 - PISO_E, z0, M[floor])
    # azulejo até 1,6 m (no box, até o teto) e pintura acima
    furos_f = [(WIN_B[0], WIN_B[1], z0 + WIN_B[2], z0 + WIN_B[3])]
    pc.parede_furada(pref + "_az_fundo_box", "x", (D - 0.02, D), 0, BOX_X, z0, z0 + H, [], M[tile])
    pc.parede_furada(pref + "_az_fundo", "x", (D - 0.02, D), BOX_X, W, z0, z0 + 1.6, [], M[tile])
    pc.parede_furada(pref + "_pint_fundo", "x", (D - 0.02, D), BOX_X, W, z0 + 1.6, z0 + H, furos_f, M["paint_w"])
    box(pref + "_az_esq", 0.0, 0.02, 0, D, z0, z0 + H, M[tile])
    furo_porta = [(PORTA_Y[0], PORTA_Y[1], z0, z0 + 2.1)]
    pc.parede_furada(pref + "_az_dir", "y", (W - 0.02, W), 0, D, z0, z0 + 1.6, furo_porta, M[tile])
    pc.parede_furada(pref + "_pint_dir", "y", (W - 0.02, W), 0, D, z0 + 1.6, z0 + H, [(PORTA_Y[0], PORTA_Y[1], z0, z0 + 2.1)],
                  M["paint_w"])
    box(pref + "_rodameio", BOX_X, W, D - 0.035, D - 0.02, z0 + 1.6, z0 + 1.63, M["white"])
    # vitrô
    vit, lam = pc.vitro(pref + "_vitro", M, largura=WIN_B[1] - WIN_B[0], altura=WIN_B[3] - WIN_B[2])
    vit.location = ((WIN_B[0] + WIN_B[1]) / 2, D + 0.1, z0 + (WIN_B[2] + WIN_B[3]) / 2)
    B["vitro"], B["laminas"] = vit, lam
    # louças
    vs = pc.vaso_sanitario(pref + "_vaso", M); vs.location = (VASO_X, D - 0.02, z0)
    pia = pc.pia_banheiro(pref + "_pia", M, largura=0.56, cor="cabinet"); pia.location = (PIA_X, D - 0.02, z0)
    esp, emb = pc.espelho(pref + "_espelho", M, largura=0.44, altura=0.58)
    esp.location = (PIA_X, D - 0.02, z0 + 1.45)
    B["espelho"], B["embaco"] = esp, emb
    ex, hel = pc.exaustor(pref + "_exaustor", M)
    ex.location = (EXA[0], D - 0.02, z0 + EXA[1])
    B["exaustor"], B["helice"] = ex, hel
    # box: chuveiro, cortina, varão, ralo, prateleira com frascos
    ch, saida = pc.chuveiro(pref + "_chuveiro", M)
    ch.location = (0.45, D - 0.02, z0 + 2.08)
    B["ducha"] = Vector(ch.location) + saida
    tube(pref + "_varao", (0.02, CORT_Y, z0 + 2.02), (BOX_X, CORT_Y, z0 + 2.02), 0.012, M["chrome"])
    cort = pc.cortina_box(pref + "_cortina", M, largura=BOX_X - 0.04, altura=1.85)
    cort.location = (0.03, CORT_Y, z0 + 2.0)                 # presa junto da parede: recolhe no canto
    B["cortina"] = cort
    pc.caixa_arred(pref + "_ralo", 0.38, 0.52, 1.25, 1.39, z0, z0 + 0.004, M["drain"], r=0.01)
    pc.caixa_arred(pref + "_prat", 0.03, 0.27, D - 0.17, D - 0.02, z0 + 1.2, z0 + 1.22, M["glass_w"], r=0.005)
    fr = pc.frascos_shampoo(pref + "_frascos", M, n=3, seed=6 + var); fr.location = (0.08, D - 0.09, z0 + 1.22)
    # luz, porta, interruptor, toalha, tapete, lixeira
    B["plafon"] = pc.plafon(pref + "_plafon", M); B["plafon"].location = (LUZ[0], LUZ[1], z0 + H)
    pt, folha = pc.porta(pref + "_porta", M, largura=PORTA_Y[1] - PORTA_Y[0])
    pt.location = (W + (WT - 0.02) / 2, PORTA_Y[1], z0)
    pt.rotation_euler = (0, 0, -math.pi / 2)
    B["porta"], B["folha"] = pt, folha
    it, tec = pc.interruptor(pref + "_interruptor", M)
    it.location = (W - 0.02, INT[0], z0 + INT[1]); it.rotation_euler = (0, 0, -math.pi / 2)
    B["interruptor"], B["tecla"] = it, tec
    tl = pc.toalha(pref + "_toalha", M, cor="towel"); tl.location = (W - 0.03, 1.55, z0 + 1.35); tl.rotation_euler = (0, 0, -math.pi / 2)
    pc.caixa_arred(pref + "_tapete", 1.0, 1.55, 0.12, 0.55, z0, z0 + 0.012, M["mat_b"], r=0.03)
    pc.caixa_arred(pref + "_lixeira", 1.75, 1.92, D - 0.3, D - 0.13, z0, z0 + 0.28, M["steel"], r=0.02)
    pl = pc.vaso_planta(pref + "_planta_pia", M, altura=0.22, folhas=6, seed=11 + var)
    pl.location = (PIA_X + 0.2, D - 0.14, z0 + 0.82)
    pc.caixa_arred(pref + "_copo", PIA_X - 0.25, PIA_X - 0.19, D - 0.14, D - 0.08, z0 + 0.82, z0 + 0.93, M["bottle_b"], r=0.01)
    return B


# andares: -2, -1, 0 (o nosso), +1 (vizinho de cima), +2
AND = {}
for n, var in ((-2, 3), (-1, 1), (0, 0), (1, 2), (2, 4)):
    z0 = n * ANDAR
    andar(f"a{n}", z0, var, banheiro_detalhado=(n == 0))
    tile, floor = {0: ("tile_b", "floor_b"), 1: ("tile_up", "floor_up"), -1: ("tile_dn", "floor_b")}.get(n, ("tile_b", "floor_up"))
    AND[n] = banheiro(f"b{n}", z0, tile, floor, var)
B0, B1 = AND[0], AND[1]

# ---------------------------------------------------------------- teto do banheiro em corte (camadas exageradas)
CAM = {}
for nm, a, b in CAMADAS:
    CAM[nm] = box("teto_" + nm, 0.0, W, 0, D + FT, H + a, H + b, M[nm])
for i in range(9):                         # ferragem da laje (pontinhos escuros no corte)
    x = 0.12 + i * 0.27
    cyl(f"ferro{i}", 0.012, -0.004, 0.0, (x, -0.004), M["rebar"], seg=8).location = (x, -0.002, H + 0.115)
    bpy.data.objects[f"ferro{i}"].rotation_euler = (math.pi / 2, 0, 0)
# tampa: esconde as camadas até o raio-x (imita as 3 faixas lisas do resto do prédio)
tampa = empty("tampa", (W / 2, -0.02, H))
for nm, a, b, m in (("forro", 0.0, 0.07, "slab_w"), ("laje", 0.07, 0.2, "laje"), ("piso", 0.2, SLAB - PISO_E, "contrapiso")):
    pc.child(box("tampa_" + nm, -W / 2 - 0.005, W / 2 + 0.005, -0.012, 0.0, a, b, M[m]), tampa)

# fundo da cidade (prédios distantes vistos pelas janelas)
for i, (x, y, w, h, m) in enumerate([(-6, 22, 7, 30, "far_bld"), (4, 26, 8, 38, "far_bld2"), (13, 20, 6, 26, "far_bld"),
                                     (-16, 28, 9, 34, "far_bld2"), (22, 30, 9, 40, "far_bld")]):
    box(f"cidade{i}", x - w / 2, x + w / 2, y, y + 6, -30, h - 12, M[m])

# ================================================================ luz
sky = Sky(top="#8fc3ef", horizon="#fde6c8", sun_energy=2.0)
sky.sun_d.angle = math.radians(15)
sky.sun.rotation_euler = (math.radians(55), 0, math.radians(160))


def luz_area(nome, loc, rot, e, s, cor, cam=False):
    d = bpy.data.lights.new(nome, "AREA"); d.energy = e; d.size = s; d.color = lin(cor)[:3]
    o = mt.link(bpy.data.objects.new(nome, d)); o.location = loc
    o.rotation_euler = tuple(math.radians(a) for a in rot)
    o.visible_camera = cam
    return d


L_FRENTE = luz_area("luz_frente", (1.2, -4.5, 2.4), (72, 0, 0), 90, 7.0, "#fff3e2")
L_PREDIO = luz_area("luz_predio", (1.2, -16, 1.5), (88, 0, 0), 0, 18.0, "#fff3e2")
L_TETO = luz_area("luz_teto_fill", (1.2, 1.0, 0.9), (180, 0, 0), 12, 2.0, "#fbf7f0")
L_PLAF = luz_area("luz_plafon", (LUZ[0], LUZ[1], H - 0.07), (0, 0, 0), 60, 0.35, "#ffe9c4")   # só ilumina para baixo
for n in (-2, -1, 1, 2):
    d = bpy.data.lights.new(f"luz_and{n}", "POINT"); d.energy = 40; d.shadow_soft_size = 0.4; d.color = lin("#ffe2b8")[:3]
    mt.link(bpy.data.objects.new(f"luz_and{n}", d)).location = (1.2, 1.0, n * ANDAR + H - 0.3)

bsdf(M["curtain_b"]).inputs["Alpha"].default_value = 0.72     # cortina translúcida (vê a água e a silhueta)

# ================================================================ tempos (frases do roteiro)
t_agua_s = T("passa água sanitária")
t_branco = T("fica branquinho")
t_olha = T("mas olha")
t_dentro = T("lá dentro")
t_clareou = T("a mancha clareou")
t_umido = T("continua úmido")
t_fungo = T("e o fungo só precisa")
t_agua = T("água", depois=t_fungo)
t_onde = T("e de onde vem")
t_banho = T("do seu próprio banho")
t_vapor = T("o banho quente")
t_sobe = T("o vapor sobe")
t_frio = T("mais frio")
t_gota = T("e vira gotinha")
t_esp = T("igual no espelho")
t_fech = T("com tudo fechado")
t_horas = T("o teto fica molhado")
t_santo = T("todo santo dia")
t_sem = T("uma semana depois")
t_pont = T("voltam os pontinhos")
t_mes = T("um mês", depois=t_sem)
t_inteira = T("a mancha volta inteira")
t_molhar = T("e de tanto molhar")
t_estufa = T("a tinta estufa")
t_desc = T("descasca", depois=t_estufa)
t_exa = T("ah mas meu banheiro")
t_luz = T("que desliga junto")
t_sai = T("você sai")
t_viz = T("ah mas é infiltração")
t_amar = T("infiltração faz mancha")
t_semb = T("e molha até sem banho")
t_preto = T("pontinho preto")
t_evap = T("vapor", depois=t_preto)
t_certo = T("o certo é simples")
t_tira = T("tira o vapor")
t_liga = T("liga o exaustor")
t_exa2 = T("exaustor", depois=t_liga)
t_jan = T("abre a janela")
t_20 = T("e deixa ventilar")
t_q = T("exaustor que desliga", depois=t_20)
t_tmp = T("pede pra instalar")
t_limpa = T("só depois limpa")
t_luva = T("de luva e máscara")
t_pinta = T("depois de seco")
t_manda = T("manda esse vídeo")
t_perg = T("e aí seu banheiro")
t_pjan = T("janela", depois=t_perg)
t_pexa = T("exaustor", depois=t_perg)
X_RX = round(t_dentro - 0.25, 3)              # chicote: corte do teto (raio-x)
X_BANHO = round(t_onde + 0.3, 3)              # chicote: de volta ao banheiro
REW0, REW1 = round(t_certo - 0.05, 3), round(t_tira - 0.02, 3)   # rebobinar (quadros não renderizados)


# ================================================================ auxiliares de animação
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


def linear(o, f0=None, f1=None):
    for fc in fcurves(o):
        for kp in fc.keyframe_points:
            if (f0 is None or kp.co.x >= f0) and (f1 is None or kp.co.x <= f1):
                kp.interpolation = "LINEAR"


def show_at(o, t, s=(1, 1, 1)):
    jump(o, "scale", t, (0, 0, 0), s)


def hide_at(o, t, s=(1, 1, 1)):
    jump(o, "scale", t, s, (0, 0, 0))


def oculto(o, janelas, s=(1, 1, 1)):
    """Visível só nas janelas [(t0, t1), ...] (troca seca)."""
    o.scale = (0, 0, 0)
    o.keyframe_insert("scale", frame=1)
    for a, b in janelas:
        show_at(o, a, s)
        if b < DUR:
            hide_at(o, b, s)


class Estado:
    """Valores que mudam em degrau (luzes, céu): guarda o valor atual para chavear antes/depois."""
    def __init__(self, alvo, caminho, v0, idx=None):
        self.alvo, self.caminho, self.v, self.idx = alvo, caminho, v0, idx
        self._set(v0, 1)

    def _set(self, v, f):
        if self.idx is None:
            setattr(self.alvo, self.caminho, v)
            self.alvo.keyframe_insert(self.caminho, frame=f)
        else:
            getattr(self.alvo, self.caminho)[self.idx] = v
            self.alvo.keyframe_insert(self.caminho, index=self.idx, frame=f)

    def degrau(self, t, v):
        self._set(self.v, mt.F(t) - 1)
        self._set(v, mt.F(t))
        self.v = v

    def rampa(self, t0, t1, v):
        self._set(self.v, mt.F(t0))
        self._set(v, mt.F(t1))
        self.v = v


# ---------------------------------------------------------------- luz da casa e céu
plaf_m = B0["plafon"].data.materials[0]
LZ = {"plaf": Estado(L_PLAF, "energy", 60.0), "frente": Estado(L_FRENTE, "energy", 90.0),
      "teto": Estado(L_TETO, "energy", 12.0), "predio": Estado(L_PREDIO, "energy", 0.0),
      "emis": Estado(bsdf(plaf_m).inputs["Emission Strength"], "default_value", 2.5)}
ACESA, APAGADA = (60.0, 90.0, 12.0, 2.5), (0.0, 26.0, 2.5, 0.0)
tecla = B0["tecla"]
TEC = Estado(tecla, "rotation_euler", 0.22, idx=0)


def luz(t, acesa):
    for nome, v in zip(("plaf", "frente", "teto", "emis"), ACESA if acesa else APAGADA):
        LZ[nome].degrau(t, v)
    TEC.degrau(t, 0.22 if acesa else -0.22)


CEU = {"dia": (2.0, 1.0, "#8fc3ef", "#fde6c8"), "tarde": (1.2, 0.7, "#6f86c4", "#ffb98a"),
       "noite": (0.1, 0.16, "#1b2747", "#41507a")}


def ceu(t, nome):
    e, st, top, hor = CEU[nome]
    sky.state(t, e, st, top, hor)


def ceu_degrau(t, de, para):
    ceu(t - 1 / mt.FPS, de)
    ceu(t, para)


def passar_tempo(t, n=2, passo=0.12, final="dia"):
    ceu(t, "dia")
    for i in range(n):
        ceu(t + passo * (2 * i + 1), "noite")
        ceu(t + passo * (2 * i + 2), "dia")
    ceu(t + passo * (2 * n), final)


ceu(0, "dia")
ceu(t_horas + 0.1, "dia"); ceu(t_horas + 1.0, "noite")
for i in range(3):                                            # "todo santo dia"
    ceu(t_santo + 0.13 * (2 * i), "noite"); ceu(t_santo + 0.13 * (2 * i + 1), "dia")
ceu(t_santo + 0.8, "dia")
passar_tempo(t_sem); passar_tempo(t_mes)
ceu(t_exa - 0.05, "dia"); ceu_degrau(t_exa, "dia", "tarde"); ceu(t_viz - 0.05, "tarde"); ceu_degrau(t_viz, "tarde", "dia")
ceu(DUR, "dia")

luz(t_horas + 0.1, False)                                    # sai e apaga a luz
for i in range(3):                                            # "todo santo dia": luz acende e apaga
    luz(t_santo + 0.13 * (2 * i), True); luz(t_santo + 0.13 * (2 * i + 1), False)
luz(t_sem, True)                                              # linha do tempo: banheiro claro
luz(t_luz + 0.3, False)                                       # desculpa 1: apaga a luz
luz(REW1, True)                                               # o certo
luz(t_q + 0.35, False)                                        # exaustor que desliga com a luz
luz(t_limpa, True)
LZ["predio"].rampa(t_manda + 0.6, t_perg + 0.6, 1300.0)      # prédio inteiro no plano final

# ================================================================ mofo no teto do box
MC = (0.46, 1.3)                                             # centro da mancha
S0 = pc.manchas("s0_", M, (MC[0], MC[1], H - 0.004), 0.48, 130, normal="z", seed=1, alongado=1.35, tam=(0.018, 0.05))
S0 += pc.manchas("s0c_", M, (0.16, D - 0.17, H - 0.004), 0.26, 50, normal="z", seed=2, alongado=1.0, tam=(0.016, 0.045))
S0 += pc.manchas("s0e_", M, (0.023, 1.55, H - 0.12), 0.32, 22, normal="x", seed=3, tam=(0.02, 0.06), alongado=0.4)
S0 += pc.manchas("s0f_", M, (0.35, D - 0.023, H - 0.12), 0.3, 20, normal="y", seed=4, tam=(0.02, 0.06), alongado=0.4)


def ordem_esfrega(o):
    """Ordem em que o esfregão passa: do fundo do box para a frente."""
    return max(0.0, min(1.0, (1.85 - o.location.y) / 1.0 + 0.05 * o.location.x))


# gancho: limpa (some) — volta inteira no "um mês" — some de novo na limpeza certa
pc.sumir_manchas(S0, 0.45, t_branco - 0.1, ordem=ordem_esfrega)
for o, dd in S0:                                              # "a mancha volta inteira": do canto para fora
    f = min(1.0, math.hypot(o.location.x - 0.1, o.location.y - (D - 0.1)) / 1.6)
    pop_in(o, t_inteira + (FIM("a mancha volta inteira") - t_inteira + 0.3) * f, 0.28)
pc.sumir_manchas(S0, t_limpa + 0.35, t_luva - 0.15, ordem=ordem_esfrega)
# 1 semana: pontinhos pequenos no canto
S1 = pc.manchas("s1_", M, (0.2, D - 0.25, H - 0.005), 0.3, 34, normal="z", seed=5, tam=(0.012, 0.03),
                cores=("mold_dark", "mold_dark"))
pc.aparecer_manchas(S1, t_pont, FIM("voltam os pontinhos pretos") + 0.2, de_dentro=False)
for o, _ in S1:
    hide_at(o, REW1)
# marcas cinza que ficam depois de limpar (a tinta nova cobre)
M["ghost_mark"] = mat("ghost_mark", "#d6d2c6", alpha=0.32)
marca = pc.esfera("marca_limpeza", 1, (MC[0], MC[1] + 0.05, H - 0.0025), M["ghost_mark"], scale=(0.42, 0.62, 0.004))
oculto(marca, [(t_luva - 0.2, t_pinta + 1.9)])

# ---------------------------------------------------------------- gotas de condensação no teto e no espelho
G1 = pc.manchas("gota_", M, (1.05, 1.0, H - 0.01), 1.25, 120, normal="z", seed=31, tam=(0.012, 0.024),
                cores=("drop", "drop"), achatado=0.75, alongado=0.85)
for o, dd in G1:
    f = min(1.0, math.hypot(o.location.x - MC[0], o.location.y - MC[1]) / 1.9)
    pop_in(o, t_gota + 0.75 * f, 0.22)
    hide_at(o, t_sem)
    show_at(o, t_molhar)
    hide_at(o, t_viz)
glow(M["drop"], t_molhar + 0.1, t_molhar + 0.9, hexcol="#4fc3f7", peak=2.0, pulses=2)
pingos = []
for i, (x, y) in enumerate([(0.62, 1.05), (1.3, 0.75), (0.9, 1.55), (1.75, 1.2)]):
    g = box(f"pingo{i}", -0.008, 0.008, -0.008, 0.008, -0.025, 0.025, M["drop"], anchor="center")
    mt.loop_fall(g, t_horas + 0.3 + 0.2 * i, t_sem - 0.02, (x, y, H - 0.03), (x, y, 0.02), 0.9 + 0.15 * i, phase=0.3 * i)
emb = B0["embaco"]
pc.embacar(emb, t_vapor + 0.6, t_esp + 0.35, ate=0.82)
mt.key_input(emb.data.materials[0], "Alpha", t_sem - 1 / mt.FPS, 0.82)
mt.key_input(emb.data.materials[0], "Alpha", t_sem, 0.0)
GE = pc.manchas("gota_esp_", M, (PIA_X, D - 0.02 - 0.037, 1.45), 0.2, 26, normal="y", seed=33, tam=(0.008, 0.016),
                cores=("drop", "drop"), achatado=0.6, alongado=1.3)
pc.aparecer_manchas(GE, t_esp + 0.1, t_esp + 0.9, de_dentro=False)
for o, _ in GE:
    hide_at(o, t_sem)

# ---------------------------------------------------------------- tinta estufando e descascando (linha do tempo)
bolhas = []
for i in range(9):
    x, y = MC[0] + rnd.uniform(-0.33, 0.33), MC[1] + rnd.uniform(-0.45, 0.45)
    r = rnd.uniform(0.05, 0.085)
    b = ball(f"bolha{i}", r, (x, y, H - 0.002), M["teto"], sub=2, scale=(1, 1, 0.42))
    for f in b.data.polygons:
        f.use_smooth = True
    tb = t_estufa + 0.07 * i
    grow(b, tb, tb + 0.45, "z", 0.0, 1.0)
    ks(b, tb, (0.2, 0.2, 0.0)); ks(b, tb + 0.45, (1, 1, 1))
    tp = t_desc + 0.06 * i
    pop_out(b, tp, 0.16)
    exp = pc.esfera(f"massa_exp{i}", 1, (x, y, H - 0.0015), M["massa"], scale=(r * 0.9, r * 0.8, 0.002), seg=12)
    oculto(exp, [(tp + 0.05, REW1)])
    for j in range(2):                                       # lascas caindo até o chão
        l = box(f"lasca{i}_{j}", -r * 0.45, r * 0.45, -r * 0.35, r * 0.35, -0.003, 0.003, M["flake"], anchor="center")
        hide_until(l, tp)
        x1, y1 = x + rnd.uniform(-0.25, 0.25), y + rnd.uniform(-0.25, 0.15)
        path(l, [(tp, (x, y, H - 0.01)), (tp + 0.35, ((x + x1) / 2, (y + y1) / 2, H - 0.9)), (tp + 0.8, (x1, y1, 0.006))])
        k(l, "rotation_euler", tp, (0, 0, 0))
        k(l, "rotation_euler", tp + 0.8, (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), rnd.uniform(-2, 2)))
        hide_at(l, REW1)
    bolhas.append(b)

# ================================================================ corte do teto: tampa, fungo e umidade
SEC_Y = -0.006
k(tampa, "location", t_dentro + 0.02, (W / 2, -0.001, H))
k(tampa, "location", t_dentro + 0.42, (W / 2, -0.45, H - 0.75))
k(tampa, "rotation_euler", t_dentro + 0.02, (0, 0, 0))
k(tampa, "rotation_euler", t_dentro + 0.42, (math.radians(-85), 0, math.radians(6)))
hide_at(tampa, t_dentro + 0.45)
tampa.location = (W / 2, -0.001, H)

fios, colonias = [], []
for i in range(16):
    x = 0.07 + i * 0.06 + rnd.uniform(-0.015, 0.015)
    c = ball(f"colonia{i}", rnd.uniform(0.006, 0.009), (x, SEC_Y, H + 0.004), M["mold_sec"], sub=2, scale=(1.3, 0.4, 0.8))
    colonias.append(c)
    a = Vector((x, SEC_Y - 0.001, H + 0.006))
    for j in range(2):
        b1 = a + Vector((rnd.uniform(-0.012, 0.012), 0, rnd.uniform(0.018, 0.03)))
        b2 = b1 + Vector((rnd.uniform(-0.015, 0.015), 0, rnd.uniform(0.012, 0.03)))
        h1 = tube(f"fio{i}_{j}a", a, b1, 0.0022, M["mold_sec"], seg=5)
        h2 = tube(f"fio{i}_{j}b", b1, b2, 0.0017, M["mold_sec"], seg=5)
        fios += [h1, h2]
        grow(h1, t_dentro + 0.5 + 0.03 * i, t_dentro + 0.9 + 0.03 * i, "z")
        grow(h2, t_agua - 0.05 + 0.02 * i, t_agua + 0.5 + 0.02 * i, "z")
for i, c in enumerate(colonias):
    pop_in(c, t_dentro + 0.45 + 0.03 * i, 0.25)
glow(M["mold_sec"], t_fungo + 0.2, FIM("pra voltar") + 0.1, hexcol="#7fbf3f", peak=1.1, pulses=3)
glow(M["teto"], t_clareou, t_clareou + 0.9, hexcol="#ffffff", peak=0.5, pulses=1)
umid = []
for i in range(26):
    g = ball(f"umid{i}", rnd.uniform(0.004, 0.007), (rnd.uniform(0.06, 1.05), SEC_Y - 0.001, H + rnd.uniform(0.008, 0.066)),
             M["water_dot"], sub=2, scale=(1, 0.5, 1))
    pop_in(g, t_umido + 0.03 * i, 0.22)
    umid.append(g)
faixa = caixa("faixa_umida", 0.0, 1.12, -0.004, -0.002, H + 0.012, H + 0.07, M["wet_sec"], (0.56, -0.003, H + 0.012))
grow(faixa, t_umido + 0.15, t_umido + 1.3, "z")
glow(M["water_dot"], t_agua, t_agua + 0.7, hexcol="#4fc3f7", peak=2.2, pulses=2)
glow(M["wet_sec"], t_agua, t_agua + 0.7, hexcol="#4fc3f7", peak=0.9, pulses=2)
# o certo: o teto seca (umidade some) e o fungo morre na limpeza
for i, g in enumerate(umid):
    pop_out(g, t_20 + 0.6 + 0.04 * i, 0.2)
grow(faixa, t_20 + 0.5, t_20 + 1.6, "z", 1.0, 0.0)
for o in colonias + fios:
    hide_at(o, t_luva - 0.1)

# ================================================================ banho: cortina, água, vapor
cort = B0["cortina"]
ABERTA, FECHADA = 0.17, 1.0
CORT = Estado(cort, "scale", ABERTA, idx=0)
CORT.rampa(t_banho + 0.25, t_banho + 0.75, FECHADA)
CORT.rampa(t_fech + 0.05, t_fech + 0.45, ABERTA)
CORT.degrau(REW1, FECHADA)
CORT.rampa(t_20 + 0.2, t_20 + 0.6, ABERTA)
DUCHA = B0["ducha"]
for tag, a, b in (("1", t_banho + 0.55, t_fech - 0.15), ("2", REW1, t_20 + 0.15)):
    pc.chuva(f"agua{tag}_", M, DUCHA.x - 0.07, DUCHA.x + 0.07, DUCHA.y - 0.07, DUCHA.y + 0.07, DUCHA.z, 0.02, a, b, n=16,
             mat_nome="water_sh", seed=40 + int(tag), periodo=0.42)
FONTE = (0.48, 1.2, 1.55)
AREA = (0.05, 2.3, 0.15, 1.9)
V1 = pc.vapor("vapor1_", M, 38, FONTE, AREA, H, t_vapor - 0.35, t_gota + 0.3, seed=51, nascer=0.6,
              fim=t_horas + 1.2)
V3 = pc.vapor("vapor3_", M, 30, (1.0, 1.0, H - 0.35), AREA, H, t_exa - 0.15, t_exa + 0.5, seed=53, subida=(0.15, 0.3),
              espalha=0.9, nascer=0.4, fim=t_viz)
V3s = pc.vapor("vapor3s_", M, 8, (1.6, 1.2, H - 0.3), (1.4, 2.2, 1.0, 1.8), H, t_exa - 0.1, t_exa + 0.4, seed=54,
               subida=(0.15, 0.3), espalha=0.4, nascer=0.4, saida=((EXA[0], D - 0.1, EXA[1]), t_exa + 0.5), fim=t_viz)
SAI_EXA = ((EXA[0], D - 0.08, EXA[1]), t_exa2 + 0.3)
SAI_JAN = (((WIN_B[0] + WIN_B[1]) / 2, D + 0.35, (WIN_B[2] + WIN_B[3]) / 2), t_jan + 0.45)
V4a = pc.vapor("vapor4a_", M, 18, FONTE, AREA, H, REW1 - 0.6, t_20, seed=55, nascer=0.75, saida=SAI_EXA, fim=t_20 + 1.6)
V4b = pc.vapor("vapor4b_", M, 18, FONTE, AREA, H, REW1 - 0.4, t_20, seed=56, nascer=0.75, saida=SAI_JAN, fim=t_20 + 1.6)
V5 = pc.vapor("vapor5_", M, 9, (MC[0], MC[1] - 0.2, H - 0.45), (0.15, 0.85, 0.9, 1.75), H, t_evap - 0.15, t_evap + 0.35,
              seed=57, subida=(0.25, 0.45), espalha=0.25, nascer=0.4, fim=REW0)
for o, rad in V4a + V4b:                                      # nada de vapor antes do rebobinar
    ks(o, REW1 - 1 / mt.FPS, 0.0)
glow(M["teto"], t_frio, t_frio + 0.8, hexcol="#8fd0ff", peak=0.55, pulses=1)

# ================================================================ exaustor, vitrô, temporizador, porta
hel = B0["helice"]
a = pc.girar(hel, t_exa - 0.1, t_luz + 1.1, rps=1.5, partida=0.3, parada=0.75)
a = pc.girar(hel, t_exa2 - 0.05, t_q + 0.9, rps=1.5, partida=0.4, parada=0.5, ang0=a)
a = pc.girar(hel, t_tmp + 0.45, DUR, rps=1.3, partida=0.4, parada=0.01, ang0=a)
glow(M["vent_mark"], t_luz + 0.35, t_luz + 1.2, hexcol="#e53935", peak=2.0, pulses=2)
glow(M["vent"], t_exa2, t_exa2 + 0.8, peak=0.9, pulses=2)
glow(M["vent"], t_tmp + 0.5, t_tmp + 1.3, peak=0.9, pulses=2)
glow(M["vent"], t_pexa, t_pexa + 0.6, peak=0.9, pulses=1)
for piv in B0["laminas"]:
    k(piv, "rotation_euler", t_jan + 0.05, (0, 0, 0))
    k(piv, "rotation_euler", t_jan + 0.45, (math.radians(58), 0, 0))
glow(M["glass_w"], t_jan + 0.1, t_jan + 0.9, peak=1.0, pulses=2)
glow(M["glass_w"], t_pjan, t_pjan + 0.5, peak=1.0, pulses=1)
glow(M["frame"], t_fech + 0.35, t_fech + 1.0, hexcol="#e53935", peak=0.8, pulses=2)   # tudo fechado
tmp, pont = pc.temporizador("temporizador", M)
tmp.location = (W - 0.02, INT[0] + 0.14, INT[1]); tmp.rotation_euler = (0, 0, -math.pi / 2)
hide_until(tmp, t_tmp + 0.1)
pop_in(tmp, t_tmp + 0.1, 0.35)
k(pont, "rotation_euler", t_tmp + 0.5, (0, 0, 0))
k(pont, "rotation_euler", t_tmp + 1.9, (0, math.radians(-270), 0))
glow(M["timer"], t_tmp + 0.2, t_tmp + 1.2, peak=0.9, pulses=2)
folha = B0["folha"]
PORT = Estado(folha, "rotation_euler", 0.0, idx=2)
for ta, tb in ((t_fech + 0.5, t_horas + 0.05), (t_sai + 0.05, t_sai + 0.75), (t_20 + 0.9, t_20 + 1.75)):
    PORT.rampa(ta, ta + 0.3, math.radians(-95))
    PORT.rampa(tb, tb + 0.3, 0.0)

# ================================================================ pessoas
SH, ARM = 0.9, 0.4


def mao_local(a, lado=1):
    return Vector((0.25 * lado, -ARM * math.sin(a), SH - ARM * math.cos(a)))


def esfregar(P, ferr, cabo, pontos, t0, t1, raiz_de, rotz, zt=H - 0.003):
    """O personagem passa a ferramenta (esfregão/rolo, origem na ponta) pelos `pontos` (x, y) do teto entre t0 e t1.
    raiz_de(t) -> (x, y) da raiz; o braço direito acha o ângulo para a mão ficar a `cabo` da ponta."""
    ferr.rotation_mode = "QUATERNION"
    n = len(pontos)
    rot = mt.Matrix.Rotation(rotz, 4, "Z")
    for i, (x, y) in enumerate(pontos):
        t = t0 + (t1 - t0) * i / (n - 1)
        rx, ry = raiz_de(t)
        S = Vector((x, y, zt))
        best = None
        for ad in range(70, 178):
            a = math.radians(ad)
            hand = Vector((rx, ry, 0)) + rot @ mao_local(a)
            err = abs((S - hand).length - cabo)
            if best is None or err < best[0]:
                best = (err, a, hand)
        _, a, hand = best
        k(P["raiz"], "location", t, (rx, ry, 0))
        k(P["raiz"], "rotation_euler", t, (0, 0, rotz))
        k(P["braco_d"], "rotation_euler", t, (-a, 0, 0))
        k(ferr, "location", t, S)
        k(ferr, "rotation_quaternion", t, Vector((0, 0, -1)).rotation_difference((hand - S).normalized()))
    for o in (P["raiz"], P["braco_d"], ferr):
        linear(o, mt.F(t0), mt.F(t1))


def zigue(y0, y1, xs, passadas=2):
    """Passadas de ida e volta em y, avançando pelas colunas x."""
    pts = []
    for j, x in enumerate(xs):
        for p in range(passadas):
            ida = (j * passadas + p) % 2 == 0
            pts.append((x, y1 if ida else y0))
    return [(xs[0], y0)] + pts


ROT_CAM = math.radians(18)                                   # de frente para a câmera (à frente, à direita)
CABO, CABO_R = 1.45, 1.38                                    # mão até a esponja / até o centro do rolo


def zigue_x(x0, x1, ys, passadas=2):
    """Passadas de ida e volta em x, avançando pelas linhas y (do fundo para a frente)."""
    pts = [(x0, ys[0])]
    for j, y in enumerate(ys):
        for p in range(passadas):
            pts.append((x1 if (j * passadas + p) % 2 == 0 else x0, y))
    return pts


def raiz_segue(pts, t0, t1, y_raiz=1.66):
    """Raiz acompanhando metade do vaivém da esponja em x (sem encostar na parede) e parada em y."""
    n = len(pts)

    def f(t):
        u = (t - t0) / (t1 - t0) * (n - 1)
        i = max(0, min(n - 2, int(u)))
        fr = u - i
        x = pts[i][0] * (1 - fr) + pts[i + 1][0] * fr
        return (0.3 + 0.45 * (x - 0.22), y_raiz)
    return f


LINHAS = [1.72, 1.52, 1.32, 1.12, 0.92]

# --- gancho: morador sem luva e sem máscara limpando o teto com água sanitária
P0 = pc.personagem("morador", M, camisa="shirt")
esf0 = pc.esfregao("esfregao0", M, cabo=CABO)
PTS0 = zigue_x(0.22, 0.86, LINHAS, passadas=2)
T0a, T0b = 0.3, t_branco - 0.15
esfregar(P0, esf0, CABO, PTS0, T0a, T0b, raiz_segue(PTS0, T0a, T0b), ROT_CAM)
k(P0["braco_e"], "rotation_euler", 0.3, (math.radians(-20), 0, 0))
pc.rosto_expr(P0, 0.0, olhos="abertos", boca="neutra")
pc.rosto_expr(P0, t_branco, boca="sorriso")
k(P0["cabeca"], "rotation_euler", 0.0, (math.radians(25), 0, 0))                 # olhando para o teto
k(P0["cabeca"], "rotation_euler", t_branco - 0.05, (math.radians(25), 0, 0))
k(P0["cabeca"], "rotation_euler", t_branco + 0.3, (math.radians(-8), 0, math.radians(15)))
oculto(P0["raiz"], [(0.0, X_RX)])
oculto(esf0, [(0.0, X_RX)])
balde0 = pc.balde("balde0", M, agua="water_dot"); balde0.location = (1.25, 0.42, 0)
frasco0 = pc.frasco_sanitaria("frasco0", M); frasco0.location = (1.45, 0.5, 0); frasco0.rotation_euler = (0, 0, 0.5)
for o in (balde0, frasco0):
    oculto(o, [(0.0, X_RX)])
glow(M["bleach_lab"], t_agua_s, t_agua_s + 0.8, hexcol="#ffffff", peak=1.0, pulses=2)

# --- banho: entra com a toalha no ombro, fecha a cortina (o vapor sobe por cima)
P1 = pc.personagem("banhista", M, camisa="shirt")
pc.toalha_ombro(P1, M)
pc.rosto_expr(P1, X_BANHO, olhos="abertos", boca="sorriso")
path(P1["raiz"], [(X_BANHO, (1.75, 0.7, 0)), (t_banho - 0.1, (1.25, 0.72, 0)), (t_banho + 0.35, (0.75, 1.05, 0)),
                  (t_banho + 0.7, (0.5, 1.15, 0))])
k(P1["raiz"], "rotation_euler", t_banho - 0.1, (0, 0, 0))
k(P1["raiz"], "rotation_euler", t_banho + 0.5, (0, 0, math.radians(-60)))
k(P1["raiz"], "rotation_euler", t_banho + 0.9, (0, 0, 0))
pc.rosto_expr(P1, t_vapor, olhos="fechados")
for i in range(6):                                            # balança cantando no chuveiro
    k(P1["raiz"], "rotation_euler", t_vapor + 0.6 * i, (0, 0, math.radians(14 if i % 2 else -14)))
k(P1["raiz"], "location", REW1, (0.5, 1.15, 0))
oculto(P1["raiz"], [(X_BANHO, t_fech + 0.05), (REW1, t_20 + 0.25)])

# --- roupão e toalha na cabeça: sai do banho, apaga a luz (e o exaustor junto)
P2 = pc.personagem("roupao", M, camisa="robe", calca="robe")
pc.turbante(P2, M)
pc.rosto_expr(P2, 0.0, olhos="abertos", boca="sorriso")
R2 = P2["raiz"]
NO_INT = (1.73, INT[0])                                      # ao lado do interruptor, de frente para a câmera
path(R2, [(t_fech + 0.05, (0.55, 1.1, 0)), (t_fech + 0.45, (1.0, 0.85, 0)), (t_fech + 0.85, (1.95, 0.6, 0)),
          (t_horas + 0.1, (2.75, 0.57, 0))])
k(R2, "rotation_euler", t_fech + 0.05, (0, 0, 0)); k(R2, "rotation_euler", t_fech + 0.5, (0, 0, math.radians(75)))
# desculpa 1: acabou o banho, exaustor girando; estica o braço e apaga a luz
jump(R2, "location", t_exa, (2.75, 0.57, 0), (*NO_INT, 0))
jump(R2, "rotation_euler", t_exa, (0, 0, math.radians(75)), (0, 0, 0))
k(P2["braco_d"], "rotation_euler", t_luz - 0.05, (0, math.radians(-8), 0))
k(P2["braco_d"], "rotation_euler", t_luz + 0.28, (0, math.radians(-128), 0))
k(P2["braco_d"], "rotation_euler", t_luz + 0.6, (0, math.radians(-128), 0))
k(P2["braco_d"], "rotation_euler", t_luz + 0.9, (0, math.radians(-8), 0))
pc.rosto_expr(P2, t_luz + 0.3, boca="neutra")
path(R2, [(t_sai, (*NO_INT, 0)), (t_sai + 0.3, (2.0, 0.62, 0)), (t_sai + 0.75, (2.85, 0.57, 0))])
k(R2, "rotation_euler", t_sai, (0, 0, 0)); k(R2, "rotation_euler", t_sai + 0.25, (0, 0, math.radians(90)))
# o certo: sai do banho e deixa o exaustor ligado
jump(R2, "location", t_20 + 0.25, (2.85, 0.57, 0), (0.55, 1.1, 0))
jump(R2, "rotation_euler", t_20 + 0.25, (0, 0, math.radians(90)), (0, 0, 0))
pc.rosto_expr(P2, t_20 + 0.25, boca="sorriso")
path(R2, [(t_20 + 0.6, (0.55, 1.1, 0)), (t_20 + 1.0, (1.1, 0.85, 0)), (t_20 + 1.45, (1.95, 0.6, 0)),
          (t_20 + 1.75, (2.8, 0.57, 0))])
k(R2, "rotation_euler", t_20 + 0.6, (0, 0, 0)); k(R2, "rotation_euler", t_20 + 0.9, (0, 0, math.radians(75)))
oculto(R2, [(t_fech + 0.05, t_horas + 0.15), (t_exa, t_sai + 0.8), (t_20 + 0.25, t_20 + 1.8)])

# --- vizinho de cima
P4 = pc.personagem("vizinho", M, camisa="orange")
P4["raiz"].location = (1.6, 1.15, ANDAR)
pc.rosto_expr(P4, t_viz, olhos="abertos", boca="sorriso")
pc.rosto_expr(P4, t_amar, boca="o")
for lado, sgn in (("braco_e", 1), ("braco_d", -1)):         # dá de ombros: "eu?"
    k(P4[lado], "rotation_euler", t_viz + 0.3, (0, 0, 0))
    k(P4[lado], "rotation_euler", t_viz + 0.7, (math.radians(-25), sgn * math.radians(50), 0))
    k(P4[lado], "rotation_euler", t_viz + 1.8, (math.radians(-25), sgn * math.radians(50), 0))
    k(P4[lado], "rotation_euler", t_viz + 2.1, (0, 0, 0))
oculto(P4["raiz"], [(t_viz, REW0)])

# --- o certo: limpa de luva e máscara, depois pinta; no fim acena
P3 = pc.personagem("limpador", M, camisa="shirt", mascara=True, luvas="glove")
esf3 = pc.esfregao("esfregao3", M, cabo=CABO)
PTS3 = zigue_x(0.22, 0.86, LINHAS[:4], passadas=2)
T3a, T3b = t_limpa + 0.3, t_luva - 0.2
esfregar(P3, esf3, CABO, PTS3, T3a, T3b, raiz_segue(PTS3, T3a, T3b), ROT_CAM)
k(P3["cabeca"], "rotation_euler", t_limpa, (math.radians(25), 0, 0))
k(P3["cabeca"], "rotation_euler", t_luva - 0.1, (math.radians(25), 0, 0))
k(P3["cabeca"], "rotation_euler", t_luva + 0.2, (0, 0, 0))
oculto(esf3, [(t_limpa, t_luva - 0.05)])
balde3 = pc.balde("balde3", M, agua="water_dot"); balde3.location = (1.25, 0.42, 0)
frasco3 = pc.frasco_sanitaria("frasco3", M); frasco3.location = (1.45, 0.5, 0); frasco3.rotation_euler = (0, 0, 0.5)
for o in (balde3, frasco3):
    oculto(o, [(t_limpa, t_pinta)])
# "de luva e máscara": vem para a frente e mostra as luvas
LUVA_POS = (0.78, 1.2, 0)
k(P3["raiz"], "location", t_luva - 0.05, P3["raiz"].location.copy())
k(P3["raiz"], "location", t_luva + 0.25, LUVA_POS)
for lado in ("braco_d", "braco_e"):
    k(P3[lado], "rotation_euler", t_luva - 0.05, P3[lado].rotation_euler.copy())
    k(P3[lado], "rotation_euler", t_luva + 0.3, (math.radians(-80), 0, 0))
    k(P3[lado], "rotation_euler", t_pinta - 0.15, (math.radians(-80), 0, 0))
glow(M["glove"], t_luva + 0.2, FIM("de luva e máscara") + 0.2, peak=1.0, pulses=2)
glow(M["mask"], t_luva + 0.2, FIM("de luva e máscara") + 0.2, peak=1.0, pulses=2)
rolo3 = pc.rolo_pintura("rolo3", M, cabo=CABO_R)
PTS3r = zigue_x(0.22, 0.86, [1.72, 1.45, 1.18, 0.92], passadas=1)
T3c, T3d = t_pinta + 0.15, FIM("tinta antimofo") - 0.1
esfregar(P3, rolo3, CABO_R, PTS3r, T3c, T3d, raiz_segue(PTS3r, T3c, T3d), ROT_CAM, zt=H - 0.075)
k(P3["cabeca"], "rotation_euler", t_pinta + 0.1, (math.radians(25), 0, 0))
oculto(rolo3, [(t_pinta, t_manda)])
lata3 = pc.lata_tinta("lata3", M); lata3.location = (1.3, 0.45, 0)
hide_until(lata3, t_pinta); pop_in(lata3, t_pinta, 0.3); hide_at(lata3, t_manda)
tinta_nova = caixa("tinta_nova", 0.03, 0.93, 0.6, 1.95, H - 0.006, H - 0.0015, M["patch"], (0.48, 1.95, H - 0.004))
grow(tinta_nova, T3c, T3d, "y")
linear(tinta_nova)
glow(M["patch"], T3d + 0.05, T3d + 0.65, hexcol="#ffc928", peak=0.9, pulses=1)
# final: tira a máscara, sorri e acena
jump(P3["raiz"], "location", t_manda, (0.5, 1.66, 0), (1.2, 0.75, 0))
jump(P3["raiz"], "rotation_euler", t_manda, (0, 0, ROT_CAM), (0, 0, math.radians(-8)))
k(P3["cabeca"], "rotation_euler", t_manda, (0, 0, 0))
hide_at(P3["mascara"], t_manda)
show_at(P3["nariz"], t_manda)
pc.rosto_expr(P3, t_manda, olhos="abertos", boca="sorriso")
k(P3["braco_e"], "rotation_euler", t_manda - 0.02, (0, 0, 0))
for i in range(6):
    k(P3["braco_d"], "rotation_euler", t_manda + 0.1 + 0.35 * i, (0, math.radians(-150 if i % 2 else -120), 0))
oculto(P3["raiz"], [(t_limpa, DUR + 1)])

# ================================================================ desculpas: X, infiltração, seta
xis1 = pc.xis("xis1", M, 0.42)
xis1.location = (1.62, D - 0.3, 1.95)
hide_until(xis1, t_sai + 0.75); pop_in(xis1, t_sai + 0.75, 0.3); pop_out(xis1, t_viz - 0.25, 0.2)
INF = (1.75, 0.42)
poca = pc.esfera("poca", 1, (INF[0], 0.25, ANDAR + 0.002), M["drop"], scale=(0.22, 0.14, 0.004))
hide_until(poca, t_viz + 0.6); pop_in(poca, t_viz + 0.6, 0.4); hide_at(poca, REW0)
for i in range(7):                                            # a água desce pela laje (no corte)
    g = ball(f"infiltra{i}", 0.009, (INF[0], SEC_Y - 0.003, ANDAR), M["drop"], sub=1)
    t0 = t_amar - 0.4 + 0.18 * i
    mt.along(g, [(INF[0] + rnd.uniform(-0.03, 0.03), SEC_Y - 0.003, ANDAR - PISO_E),
                 (INF[0] + rnd.uniform(-0.04, 0.04), SEC_Y - 0.003, H + 0.13),
                 (INF[0] + rnd.uniform(-0.02, 0.02), SEC_Y - 0.003, H + 0.01)], t0, t0 + 3.6, loops=3)
manch = pc.mancha_agua("infiltracao", M, (INF[0], INF[1], H - 0.003), 0.3)
hide_until(manch, t_amar + 0.4)
ks(manch, t_amar + 0.4, 0.05); ks(manch, FIM("mancha amarelada") + 0.3, 1.0)
hide_at(manch, REW0)
glow(M["stain_y"], FIM("infiltração faz mancha amarelada") - 0.5, FIM("infiltração faz mancha amarelada") + 0.4,
     hexcol="#ffd23f", peak=1.0, pulses=1)
for i in range(3):
    g = box(f"pinga_inf{i}", -0.009, 0.009, -0.009, 0.009, -0.03, 0.03, M["drop"], anchor="center")
    p0 = (INF[0] + 0.06 * (i - 1), INF[1] + 0.03 * i, H - 0.03)
    mt.loop_fall(g, t_semb + 0.1 * i, REW0 - 0.05, p0, (p0[0], p0[1], 0.02), 0.85, phase=0.25 * i)
seta = arrow("seta_preto", 0.5, M["yellow"], (MC[0] + 0.05, MC[1] - 0.15, H - 0.12), direction=(-0.05, 0.25, 1.0), r=0.022,
             head=0.06)
hide_until(seta, t_preto + 0.25); pop_in(seta, t_preto + 0.25, 0.3); hide_at(seta, REW0)

# ================================================================ câmeras
GER = ((1.2, -3.25, 1.3), (1.2, 1.0, 1.35))
GANCHO_A = ((1.75, -1.6, 0.95), (0.5, 1.2, 1.75))
GANCHO_B = ((1.5, -1.2, 1.0), (0.5, 1.2, 1.85))


def SEC(x, d, z=H + 0.075):
    return ((x, -d, z), (x, 0.0, z))


TETO_BOX = ((1.3, 0.05, 1.35), (0.45, 1.3, 2.5))
ESP = ((1.82, 0.9, 1.42), (2.0, 2.0, 1.45))
TL = ((1.25, -0.35, 1.2), (0.38, 1.5, 2.45))
EX1 = ((1.1, -2.05, 1.35), (1.85, 1.2, 1.6))
VIZ = ((1.6, -2.55, 1.85), (1.6, 0.6, 2.95))
BOXP = ((1.2, -0.9, 1.4), (0.45, 1.3, 2.45))
LIMPA = ((1.7, -1.5, 0.98), (0.5, 1.2, 1.8))
LUVA = ((1.12, -0.42, 1.12), (0.8, 1.2, 1.15))
shots = [
    (0.0, [(0.0, *GANCHO_A), (t_agua_s, (1.6, -1.35, 0.98), GANCHO_A[1]), (t_branco, *GANCHO_B),
           (t_olha, (1.35, -1.05, 1.1), (0.55, 1.1, 2.0)), (X_RX - 0.05, (0.55, -0.85, 2.3), (0.5, 0.0, 2.55))]),
    (X_RX, [(X_RX, *SEC(0.5, 0.42)), (t_clareou, *SEC(0.5, 0.36)), (t_fungo, *SEC(0.48, 0.33)),
            (t_agua, *SEC(0.46, 0.3)), (X_BANHO - 0.05, *SEC(0.46, 0.29))]),
    (X_BANHO, [(X_BANHO, (1.25, -3.0, 1.35), (1.15, 1.0, 1.3)), (t_banho, (1.15, -2.75, 1.4), (1.0, 1.0, 1.4)),
               (t_vapor, (1.05, -2.5, 1.45), (0.75, 1.0, 1.75)), (t_sobe, (1.0, -1.8, 1.4), (0.8, 1.2, 2.35)),
               (t_gota - 0.05, (0.95, -1.35, 1.45), (0.75, 1.2, 2.45))]),
    (t_gota, [(t_gota, *TETO_BOX), (t_esp - 0.05, (1.25, 0.15, 1.35), TETO_BOX[1])]),
    (t_esp, [(t_esp, *ESP), (t_fech - 0.05, (1.86, 1.0, 1.43), ESP[1])]),
    (t_fech, [(t_fech, *GER), (t_horas + 0.1, (1.2, -3.0, 1.32), GER[1]), (t_horas + 0.8, (1.1, -1.9, 1.3), (0.85, 1.2, 2.25)),
              (t_sem - 0.05, (1.05, -1.6, 1.3), (0.8, 1.2, 2.3))]),
    (t_sem, [(t_sem, *TL), (t_mes - 0.05, (1.22, -0.3, 1.2), TL[1])]),
    (t_mes, [(t_mes, *TL), (t_molhar - 0.05, (1.22, -0.3, 1.2), TL[1])]),
    (t_molhar, [(t_molhar, *TL), (t_exa - 0.05, (1.2, -0.22, 1.2), TL[1])]),
    (t_exa, [(t_exa, *EX1), (t_luz, (1.15, -1.8, 1.35), EX1[1]), (t_viz - 0.05, (1.18, -1.65, 1.35), EX1[1])]),
    (t_viz, [(t_viz, *VIZ), (t_amar, (1.65, -2.2, 1.85), (1.65, 0.6, 2.9)), (t_preto - 0.15, (1.7, -2.05, 1.85), (1.7, 0.6, 2.85)),
             (t_preto + 0.35, *BOXP), (REW0, (1.15, -0.8, 1.4), BOXP[1])]),
    (REW1, [(REW1, *GER), (t_liga, (1.2, -3.05, 1.35), (1.2, 1.0, 1.45)), (t_exa2 + 0.15, (1.55, -1.7, 1.55), (1.6, 1.4, 1.95)),
            (t_20 - 0.1, (1.5, -1.6, 1.55), (1.55, 1.4, 1.95)), (t_20 + 0.35, (1.2, -2.9, 1.35), (1.2, 1.0, 1.45)),
            (t_q - 0.05, (1.2, -2.75, 1.35), (1.2, 1.0, 1.45))]),
    (t_q, [(t_q, (1.3, -1.15, 1.3), (1.95, 1.3, 1.6)), (t_tmp, (1.32, -0.95, 1.32), (2.05, 1.3, 1.55)),
           (t_limpa - 0.05, (1.35, -0.85, 1.32), (2.05, 1.3, 1.55))]),
    (t_limpa, [(t_limpa, *LIMPA), (t_luva - 0.05, (1.6, -1.3, 1.0), LIMPA[1])]),
    (t_luva, [(t_luva, *LUVA), (t_pinta - 0.05, (1.1, -0.35, 1.12), LUVA[1])]),
    (t_pinta, [(t_pinta, *LIMPA), (t_manda - 0.05, (1.6, -1.3, 1.0), LIMPA[1])]),
    (t_manda, [(t_manda, (1.2, -3.1, 1.3), (1.2, 1.0, 1.3)), (t_perg, (1.2, -6.5, 1.35), (1.2, 1.0, 1.3)),
               (DUR, (1.2, -11.5, 1.4), (1.2, 1.0, 1.35))]),
]
SHK = [(t_sem, t_sem + 0.2, 0.012), (t_mes, t_mes + 0.2, 0.012), (t_molhar, t_molhar + 0.2, 0.01),
       (t_sai + 0.75, t_sai + 0.9, 0.01), (t_dentro + 0.05, t_dentro + 0.3, 0.004)]
cams = cameras(shots, shakes=SHK)
FOCO = {1: 2.0, 3: 2.8, 4: 2.2, 6: 3.2, 7: 3.2, 8: 3.2, 14: 2.4}
for i, cam in enumerate(cams):
    if i in FOCO:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_object = bpy.data.objects[f"tgt{i}"]
        cam.data.dof.aperture_fstop = FOCO[i]

# ================================================================ desempenho do render (teste de 31/10: 6,8 -> ~4 s/quadro)
# O céu muda de cor (dia/noite): com amostragem de importância o mapa do céu era refeito a cada quadro (+2 s).
# Emissão dos materiais só para ser vista (gotas, vapor, destaques): não precisa virar luz.
mt.scene.world.cycles.sampling_method = "NONE"
for m_ in bpy.data.materials:
    m_.cycles.emission_sampling = "NONE"
for o_ in bpy.data.objects:
    if o_.type == "MESH" and o_.name.startswith(("vapor", "gota", "s0", "s1_", "infiltra", "agua", "umid", "colonia", "fio",
                                                  "pingo", "pinga")):
        o_.visible_shadow = False

# ================================================================ cortes, carimbos e blend
write_cuts(os.path.join(HERE, "cortes.json"), [X_RX, X_BANHO], DUR)
info = json.load(open(os.path.join(HERE, "cortes.json")))
info["rebobinar"] = [{"ini": REW0, "fim": REW1, "de": round(t_sem + 0.1, 3), "ate": round(REW0 - 0.3, 3)}]
json.dump(info, open(os.path.join(HERE, "cortes.json"), "w"), indent=1)


def carimbo(t, fim, texto, tipo):
    return {"t": round(t, 2), "fim": round(fim, 2), "texto": texto, "tipo": tipo}


CARIMBOS = [
    carimbo(T("todo mês") + 0.05, t_agua_s + 0.6, "TODO MÊS", "tempo"),
    carimbo(t_umido + 0.15, FIM("continua úmido") + 0.5, "ÚMIDO", "problema"),
    carimbo(t_banho, FIM("do seu próprio banho") + 0.6, "SEU BANHO", "problema"),
    carimbo(t_frio, FIM("mais frio") + 0.8, "TETO FRIO", "problema"),
    carimbo(T("por horas"), FIM("por horas") + 0.9, "POR HORAS", "tempo"),
    carimbo(t_sem, t_mes - 0.15, "1 SEMANA DEPOIS", "tempo"),
    carimbo(t_mes, FIM("a mancha volta inteira") + 0.2, "1 MÊS", "tempo"),
    carimbo(t_exa, FIM("tem exaustor") + 0.5, "EXAUSTOR?", "problema"),
    carimbo(t_viz, FIM("vizinho de cima") + 0.4, "VIZINHO DE CIMA?", "problema"),
    carimbo(t_preto, min(FIM("vapor", depois=t_preto) + 0.3, t_certo - 0.08), "PRETO = VAPOR", "problema"),
    carimbo(t_certo, t_tira + 0.6, "O CERTO", "solucao"),
    carimbo(T("20 minutos") - 0.2, FIM("minutos depois") + 0.3, "+20 MIN", "solucao"),
    carimbo(T("temporizador") - 0.1, FIM("temporizador") + 0.5, "TEMPORIZADOR", "solucao"),
    carimbo(t_luva, FIM("de luva e máscara") + 0.2, "LUVA + MÁSCARA", "solucao"),
    carimbo(T("tinta antimofo") - 0.1, FIM("tinta antimofo") + 0.35, "TINTA ANTIMOFO", "solucao"),
]
json.dump(CARIMBOS, open(os.path.join(HERE, "carimbos.json"), "w"), ensure_ascii=False, indent=1)
TEMPOS = {k_: v for k_, v in globals().items() if k_.startswith("t_") and isinstance(v, float)}
TEMPOS.update({"T0a": T0a, "T0b": T0b, "n0": len(PTS0), "T3a": T3a, "T3b": T3b, "n3": len(PTS3), "T3c": T3c, "T3d": T3d,
               "n3r": len(PTS3r), "X_RX": X_RX, "X_BANHO": X_BANHO, "REW0": REW0, "REW1": REW1, "DUR": DUR})
json.dump(TEMPOS, open(os.path.join(HERE, "tempos.json"), "w"), indent=1)   # usado pelo efeitos.py
save(os.path.join(HERE, "mofo_banheiro.blend"))
