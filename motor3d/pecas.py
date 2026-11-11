"""Catálogo de peças 3D reutilizáveis (estilo low-poly dos vídeos).

Cada função recebe o dicionário de materiais M do vídeo; use `materiais(M)` uma vez para
garantir os materiais que as peças usam (cria só os que faltarem). As peças são paramétricas:
troque cores, tamanhos e composição a cada vídeo para não ficar repetitivo.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import motor as mt
import shapely.geometry as sg
from shapely.ops import unary_union
from motor import mat, box, cyl, tube, ball, empty, mesh_obj, prism, text, k, ks, flicker, pop_in, hide_from, building_mat

rnd = random.Random(5)

PADRAO = {
    "dark": "#2b2b2f", "glass": "#5b8fd6", "steel": "#4c5560", "machine": "#f2b51d", "truck_cab": "#f07c1f",
    "truck_bed": "#8f9aa5", "concrete": "#c9c9cc", "concrete_dark": "#a9a9ae", "wood": "#b07a45", "roof": "#c9483a",
    "white": "#f4f1ea", "vulture": "#26262a", "vulture_head": "#d79a8f", "rat": "#8d8d8d", "pink": "#e7a3a3",
    "fire": "#ff8a1c", "fire_core": "#ffd23f", "pawn": "#3b6fd6", "stone_wall": "#a8a39b", "plant": "#9fb3c8",
    "pole": "#5b4632", "wire": "#222222", "paper": "#efe7d2", "ink": "#262626", "ink_gray": "#9a958a",
    "car": "#d93636", "orange": "#f07c1f", "yellow": "#ffc928", "bag_w": "#f2f2f2", "bag_b": "#4a7fd6",
    "bag_k": "#3a3a3a", "bottle": "#3f8f4f", "can": "#d33a2f",
}
EMIT = {"fire": 4.0, "fire_core": 6.0, "yellow": 1.2}
ROUGH = {"glass": 0.3, "steel": 0.4, "car": 0.4, "bottle": 0.2, "can": 0.3}
JUNK = ["bag_w", "bag_b", "bag_k", "bottle", "can", "paper", "truck_cab", "roof", "wood"]


def materiais(M):
    for n, c in PADRAO.items():
        if n not in M:
            M[n] = mat(n, c, rough=ROUGH.get(n, 0.85), emit=EMIT.get(n, 0.0))
    if "tower" not in M:
        M["tower"] = building_mat("tower")
    return M


# ================================================================ primitivas auxiliares
def disc(name, r, w, m, seg=16):
    """Roda/cilindro centrado com eixo em y."""
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


def junk(name, M, size=0.35, kind=None):
    """Item de lixo/entulho aleatório (caixa, saco, lata)."""
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


# ================================================================ veículos e máquinas (frente para +x)
def caminhao(name, M, cab="truck_cab"):
    """Caminhão basculante. Retorna (raiz, dobradiça_da_caçamba): gire a dobradiça em y negativo para basculhar."""
    root = empty(name)
    child(box(name + "_chassi", -2.6, 2.6, -0.9, 0.9, 0.55, 0.85, M["dark"]), root)
    child(box(name + "_cab", 1.3, 2.7, -1.0, 1.0, 0.85, 2.45, M[cab]), root)
    child(box(name + "_vidro", 2.69, 2.75, -0.8, 0.8, 1.6, 2.25, M["glass"]), root)
    for wx in (-1.7, 1.9):
        for wy in (-0.95, 0.95):
            child(disc(f"{name}_roda{wx}{wy}", 0.55, 0.35, M["dark"]), root, (wx, wy, 0.55))
    hinge = child(empty(name + "_hinge"), root, (-2.6, 0, 0.9))
    child(box(name + "_cacamba", 0.0, 3.8, -1.05, 1.05, 0.0, 1.5, M["truck_bed"]), hinge)
    return root, hinge


def rolo_compactador(name, M):
    """Retorna (raiz, rolo). Gire o rolo com rotation_euler = (pi/2, ângulo, 0)."""
    root = empty(name)
    child(box(name + "_corpo", -1.3, 0.9, -0.8, 0.8, 0.45, 1.45, M["machine"]), root)
    child(box(name + "_cab", -1.1, 0.1, -0.6, 0.6, 1.45, 2.3, M["glass"]), root)
    drum = child(disc(name + "_rolo", 0.75, 1.9, M["steel"], seg=18), root, (1.65, 0, 0.75))
    for wy in (-0.85, 0.85):
        child(disc(f"{name}_roda{wy}", 0.5, 0.35, M["dark"]), root, (-0.8, wy, 0.5))
    return root, drum


def trator_esteira(name, M):
    root = empty(name)
    child(box(name + "_corpo", -1.2, 1.0, -0.85, 0.85, 0.35, 1.35, M["machine"]), root)
    child(box(name + "_cab", -1.0, 0.0, -0.6, 0.6, 1.35, 2.2, M["glass"]), root)
    for wy in (-1, 1):
        child(box(f"{name}_esteira{wy}", -1.45, 1.15, 0.62 * wy - 0.22, 0.62 * wy + 0.22, 0.0, 0.55, M["dark"]), root)
    child(box(name + "_lamina", 1.25, 1.45, -1.15, 1.15, 0.0, 1.05, M["steel"]), root)
    return root


def carro(name, M, cor="car"):
    root = empty(name)
    child(box(name + "_corpo", -1.7, 1.7, -0.8, 0.8, 0.25, 0.95, M[cor]), root)
    child(box(name + "_cabine", -0.9, 0.9, -0.75, 0.75, 0.95, 1.55, M["glass"]), root)
    for wx in (-1.05, 1.05):
        for wy in (-0.8, 0.8):
            child(disc(f"{name}_roda{wx}{wy}", 0.32, 0.24, M["dark"]), root, (wx, wy, 0.32))
    return root


def bate_estaca(name, M):
    """Retorna (raiz, martelo). Anime martelo.location.z subindo/descendo sobre a estaca (x=0 da raiz)."""
    root = empty(name)
    child(box(name + "_torre", -0.15, 0.15, 0.45, 0.75, 0, 9.5, M["machine"]), root, (0, 0.6, 0))
    child(box(name + "_base", -1.2, 1.2, 0.3, 2.6, 0, 0.8, M["machine"]), root, (0, 1.45, 0))
    child(box(name + "_cab", -0.6, 0.6, 1.4, 2.4, 0, 0.9, M["glass"]), root, (0, 1.9, 0.8))
    hammer = child(box(name + "_martelo", -0.45, 0.45, -0.45, 0.45, 0, 1.1, M["dark"]), root)
    return root, hammer


def helice(name, M, comprimento=9.1, raio=0.55, passo=0.7):
    """Trado/hélice contínua. Retorna a raiz (origem na ponta). Gire em z e mova em z."""
    root = empty(name)
    prof = bpy.data.meshes.new(name + "_perfil")
    prof.from_pydata([(0.12, 0, 0), (raio, 0, 0)], [(0, 1)], [])
    hx = mt.link(bpy.data.objects.new(name + "_espiral", prof))
    hx.data.materials.append(M["steel"])
    sc = hx.modifiers.new("screw", "SCREW")
    sc.axis = "Z"; sc.screw_offset = passo; sc.iterations = max(1, int(comprimento / passo)); sc.steps = 20; sc.render_steps = 20
    hx.modifiers.new("solid", "SOLIDIFY").thickness = 0.08
    child(hx, root)
    child(cyl(name + "_eixo", 0.13, 0.0, comprimento + 3.4, (0, 0), M["steel"]), root)
    child(box(name + "_motor", -0.5, 0.5, -0.5, 0.5, comprimento + 3.4, comprimento + 4.5, M["orange"]), root)
    return root


# ================================================================ construções
def predio(name, M, largura=4.0, profundidade=4.0, andares=20, pe_direito=0.6, m="tower"):
    """Prédio com janelas (material com Brick Texture). Origem no centro da base."""
    h = andares * pe_direito
    o = box(name, -largura / 2, largura / 2, -profundidade / 2, profundidade / 2, 0, h, M[m])
    child(box(name + "_teto", -largura / 2 - 0.1, largura / 2 + 0.1, -profundidade / 2 - 0.1, profundidade / 2 + 0.1, 0, 0.3,
              M["concrete_dark"]), o, (0, 0, h))
    return o


def usina(name, M):
    root = empty(name)
    child(box(name + "_corpo", -1.6, 1.6, -1.5, 1.5, 0, 2.4, M["plant"]), root)
    child(box(name + "_teto", -1.75, 1.75, -1.65, 1.65, 2.4, 2.6, M["dark"]), root)
    child(cyl(name + "_chamine", 0.3, 2.6, 4.2, (0.9, 0.6), M["concrete_dark"], seg=10), root)
    child(box(name + "_porta", -0.45, 0.45, -1.53, -1.5, 0, 1.5, M["dark"]), root)
    return root


def raio_icone(name, M, x, z, y0=-0.05, y1=0.05, escala=1.0):
    """Ícone de raio (energia) na vertical, de frente para a câmera."""
    zig = [(-0.25, 0.75), (0.3, 0.75), (0.05, 0.15), (0.35, 0.15), (-0.3, -0.75), (-0.05, -0.1), (-0.35, -0.1)]
    return prism(name, [(x + a * escala, z + b * escala) for a, b in zig], y0, y1, M["yellow"], origin=(x, z))


def poste(name, M, x, y, altura=4.2):
    root = empty(name, (x, y, 0))
    child(cyl(name + "_m", 0.1, 0, altura, (0, 0), M["pole"], seg=8), root)
    child(box(name + "_x", -0.6, 0.6, -0.06, 0.06, altura - 0.3, altura - 0.15, M["pole"]), root)
    return root


def fio(name, M, a, b):
    return tube(name, a, b, 0.03, M["wire"], seg=6)


def poco(name, M, x, y_corte=0.0, fundo=-9.6, agua_topo=-7.6, m_agua=None):
    """Poço em corte (paredes, ar, água) + boca com telhadinho. Retorna o objeto da água (troque a cor dele)."""
    box(name + "_parede", x - 0.45, x + 0.45, y_corte - 0.05, y_corte + 0.9, fundo, 0.0, M["concrete"])
    box(name + "_ar", x - 0.28, x + 0.28, y_corte - 0.07, y_corte + 0.8, agua_topo, 0.0, M["dark"])
    agua = box(name + "_agua", x - 0.28, x + 0.28, y_corte - 0.07, y_corte + 0.8, fundo + 0.1, agua_topo, m_agua or M["glass"])
    cyl(name + "_boca", 0.95, 0.0, 0.85, (x, y_corte + 0.95), M["stone_wall"], seg=12)
    cyl(name + "_boca_in", 0.7, 0.05, 0.9, (x, y_corte + 0.95), M["dark"], seg=12)
    for s in (-1, 1):
        box(f"{name}_poste{s}", x + s * 0.85 - 0.08, x + s * 0.85 + 0.08, y_corte + 0.87, y_corte + 1.03, 0, 2.3, M["wood"])
    box(name + "_telhado", x - 1.2, x + 1.2, y_corte + 0.2, y_corte + 1.7, 2.3, 2.45, M["roof"])
    tube(name + "_eixo", (x - 0.85, y_corte + 0.95, 1.9), (x + 0.85, y_corte + 0.95, 1.9), 0.06, M["wood"])
    return agua


def rachaduras(name, M, pontos, y):
    """Rachadura em zigue-zague numa parede (lista de (x, z)). Retorna os segmentos (anime com pop_in)."""
    segs = []
    for j in range(len(pontos) - 1):
        a, b = Vector((pontos[j][0], y, pontos[j][1])), Vector((pontos[j + 1][0], y, pontos[j + 1][1]))
        segs.append(tube(f"{name}{j}", a, b, 0.04, M["dark"], seg=4))
    return segs


# ================================================================ seres
def pessoa(name, M, cor="pawn"):
    """Boneco 'peão' (estilo dos vídeos de referência). Origem nos pés."""
    root = empty(name)
    child(cyl(name + "_corpo", 0.28, 0, 0.9, (0, 0), M[cor]), root)
    child(ball(name + "_cabeca", 0.24, (0, 0, 0), M[cor]), root, (0, 0, 1.15))
    return root


def urubu(name, M):
    """Corpo ao longo de +y. Retorna (raiz, asas) — use bater_asas(asas, t0, t1)."""
    root = empty(name)
    child(ball(name + "_corpo", 1, (0, 0, 0), M["vulture"], scale=(0.4, 0.85, 0.36)), root)
    child(ball(name + "_cabeca", 0.2, (0, 0, 0), M["vulture_head"]), root, (0, 0.88, 0.16))
    asas = []
    for s in (1, -1):
        h = child(empty(f"{name}_asa{s}"), root, (0.22 * s, 0, 0.1))
        child(box(f"{name}_asa_m{s}", 0 if s > 0 else -1.7, 1.7 if s > 0 else 0, -0.32, 0.32, -0.04, 0.04, M["vulture"], anchor="center"),
              h, (0.85 * s, 0, 0))
        asas.append((h, s))
    return root, asas


def bater_asas(asas, t0, t1, passo=0.18, amp=0.5):
    t, up = t0, True
    while t <= t1:
        for h, s in asas:
            k(h, "rotation_euler", t, (0, -s * amp if up else s * amp * 0.6, 0))
        up = not up
        t += passo


def rato(name, M):
    """Corpo ao longo de +x. Origem nas patas."""
    root = empty(name)
    child(ball(name + "_corpo", 1, (0, 0, 0), M["rat"], scale=(0.42, 0.22, 0.2)), root, (0, 0, 0.2))
    child(ball(name + "_cabeca", 0.15, (0, 0, 0), M["rat"]), root, (0.42, 0, 0.25))
    for s in (1, -1):
        child(ball(f"{name}_orelha{s}", 0.07, (0, 0, 0), M["pink"]), root, (0.42, 0.1 * s, 0.38))
    child(tube(name + "_rabo", (0, 0, 0), (-0.55, 0, -0.12), 0.03, M["pink"], seg=6), root, (-0.4, 0, 0.18))
    return root


# ================================================================ efeitos
def chama(name, M, tamanho=1.0):
    """Chama low-poly (4 cones). Retorna (raiz, cones)."""
    root = empty(name)
    cones = []
    for i, (dx, dy, h, r, mm) in enumerate([(0, 0, 1.0, 0.32, "fire"), (0.2, 0.05, 0.7, 0.22, "fire"),
                                            (-0.19, -0.04, 0.75, 0.22, "fire"), (0, -0.08, 0.55, 0.17, "fire_core")]):
        cones.append(child(cone(f"{name}_{i}", r * tamanho, h * tamanho, M[mm]), root, (dx * tamanho, dy * tamanho, 0)))
    return root, cones


def fogo(name, M, loc, t0, t1, tamanho=1.0):
    """Chama que aparece em t0, tremula e some em t1."""
    root, cones = chama(name, M, tamanho)
    root.location = loc
    pop_in(root, t0, 0.3)
    hide_from(root, t1)
    for c in cones:
        flicker(c, t0, t1, amp=0.35)
    return root


def jornal(name, M, ano="1986"):
    """Jornal de frente para -y (texto legível pela câmera). Origem no centro."""
    root = empty(name)
    child(box(name + "_papel", -0.7, 0.7, -0.015, 0.015, -0.9, 0.9, M["paper"], anchor="center"), root)
    child(box(name + "_titulo", -0.6, 0.6, -0.03, -0.015, 0.45, 0.68, M["ink"], anchor="center"), root)
    child(text(name + "_ano", ano, 0.3, (0, -0.035, 0.12), M["ink"]), root)
    child(box(name + "_foto", -0.6, -0.05, -0.03, -0.015, -0.55, 0.02, M["ink_gray"], anchor="center"), root)
    for j in range(6):
        z = -j * 0.11
        child(box(f"{name}_linha{j}", 0.05, 0.6, -0.03, -0.015, z - 0.025, z + 0.025, M["ink_gray"], anchor="center"), root)
    for j in range(2):
        z = -0.68 - j * 0.1
        child(box(f"{name}_rodape{j}", -0.6, 0.6, -0.03, -0.015, z - 0.025, z + 0.025, M["ink_gray"], anchor="center"), root)
    return root


# ================================================================ casa por dentro (canal "dentro da sua casa")
CASA = {"paint_white": "#f7f7f4", "mold": "#4e5b31", "mold_dark": "#2b2b2b", "wet": "#1f6f9a", "water_dot": "#4fc3f7",
        "spore": "#9fae7c", "red": "#e53935", "bucket": "#3f7fd0", "can_label": "#3f9b5a", "sheet": "#e98c7a",
        "pillow": "#fbfbf8", "blanket": "#5a86c9", "mask": "#f2f2f2", "glove": "#ffc928", "sponge": "#f4d03f"}
EMIT_CASA = {"water_dot": 1.0, "red": 0.8, "spore": 0.35}
ALPHA_CASA = {"wet": 0.5, "spore": 0.85}


def materiais_casa(M):
    """Materiais das peças de casa (cria só os que faltarem)."""
    materiais(M)
    for n, c in CASA.items():
        if n not in M:
            M[n] = mat(n, c, emit=EMIT_CASA.get(n, 0.0), alpha=ALPHA_CASA.get(n, 1.0))
    return M


def rolo_pintura(name, M, cabo=1.1):
    """Rolo de pintura. Origem no rolo; o cabo desce em -z (segure pela ponta)."""
    root = empty(name)
    child(disc(name + "_rolo", 0.07, 0.28, M["paint_white"], seg=12), root)
    child(tube(name + "_haste", (0, 0, 0), (0.0, 0, -0.18), 0.012, M["steel"], seg=6), root, (0, 0, 0))
    child(tube(name + "_cabo", (0, 0, 0), (0, 0, -cabo), 0.022, M["wood"], seg=8), root, (0, 0, -0.18))
    return root


def lata_tinta(name, M, rotulo="can_label"):
    """Lata de tinta (galão) com faixa colorida. Origem na base."""
    root = empty(name)
    child(cyl(name + "_corpo", 0.17, 0, 0.36, (0, 0), M["white"], seg=16), root)
    child(cyl(name + "_faixa", 0.172, 0.1, 0.26, (0, 0), M[rotulo], seg=16), root)
    child(cyl(name + "_tampa", 0.175, 0.36, 0.38, (0, 0), M["steel"], seg=16), root)
    return root


def balde(name, M, cor="bucket", agua=None):
    """Balde levemente cônico, aberto. Origem na base. `agua`: material da superfície (opcional)."""
    root = empty(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.15, radius2=0.2, depth=0.34,
                          matrix=Matrix.Translation((0, 0, 0.17)))
    o = child(mesh_obj(name + "_corpo", bm, M[cor]), root)
    o.modifiers.new("esp", "SOLIDIFY").thickness = 0.015
    child(cyl(name + "_fundo", 0.15, 0, 0.02, (0, 0), M[cor], seg=16), root)
    if agua:
        child(cyl(name + "_agua", 0.185, 0.24, 0.25, (0, 0), M[agua], seg=16), root)
    return root


def xis(name, M, tamanho=0.5, cor="red"):
    """X de 'errado' de frente para -y (gire o objeto para outra direção). Origem no centro."""
    root = empty(name)
    for a in (45, -45):
        b = child(box(f"{name}_{a}", -tamanho / 2, tamanho / 2, -0.03, 0.03, -tamanho * 0.09, tamanho * 0.09, M[cor],
                      anchor="center"), root)
        b.rotation_euler = (0, math.radians(a), 0)
    return root


def cama(name, M, comprimento=2.0, largura=1.5):
    """Cama de casal ao longo de +x (cabeceira em x = 0). Origem no chão, no meio da cabeceira."""
    root = empty(name)
    w = largura / 2
    child(box(name + "_base", 0, comprimento, -w, w, 0, 0.35, M["wood"]), root)
    child(box(name + "_cabeceira", -0.08, 0.0, -w, w, 0, 1.05, M["wood"]), root)
    child(box(name + "_colchao", 0.02, comprimento - 0.02, -w + 0.02, w - 0.02, 0.35, 0.55, M["sheet"]), root)
    child(box(name + "_coberta", 0.7, comprimento + 0.02, -w - 0.02, w + 0.02, 0.5, 0.62, M["blanket"]), root)
    for s in (-1, 1):
        child(ball(f"{name}_trav{s}", 1, (0, 0, 0), M["pillow"], scale=(0.22, 0.32, 0.1)), root, (0.3, s * w * 0.5, 0.64))
    return root


def rosto(pessoa_root, M, frente=(1, 0, 0), mascara=False):
    """Olhos (abertos e fechados) e máscara opcional na cabeça do pessoa(). `frente`: para onde ele olha
    (no espaço do boneco). Retorna dict {'abertos': [...], 'fechados': [...], 'mascara': obj|None};
    troque a expressão com expressao()."""
    f = Vector(frente).normalized()
    lado = Vector((-f.y, f.x, 0))
    head = Vector((0, 0, 1.15))
    out = {"abertos": [], "fechados": [], "mascara": None}
    for s in (-1, 1):
        p = head + f * 0.21 + lado * 0.09 * s + Vector((0, 0, 0.05))
        out["abertos"].append(child(ball(f"{pessoa_root.name}_olho{s}", 0.04, (0, 0, 0), M["dark"]), pessoa_root, p))
        fe = child(box(f"{pessoa_root.name}_olhof{s}", -0.045, 0.045, -0.012, 0.012, -0.008, 0.008, M["dark"], anchor="center"),
                   pessoa_root, p)
        fe.rotation_euler = (0, 0, math.atan2(lado.y, lado.x))
        fe.scale = (0, 0, 0)
        out["fechados"].append(fe)
    if mascara:
        mk = child(ball(pessoa_root.name + "_mascara", 1, (0, 0, 0), M["mask"], scale=(0.09, 0.14, 0.08)), pessoa_root,
                   head + f * 0.2 - Vector((0, 0, 0.06)))
        mk.rotation_euler = (0, 0, math.atan2(f.y, f.x))
        out["mascara"] = mk
    return out


def expressao(r, t, nome):
    """Troca para 'abertos' ou 'fechados' no tempo t."""
    for o in r["abertos"]:
        mt.jump(o, "scale", t, o.scale.copy() if t > 0 else (1, 1, 1), (1, 1, 1) if nome == "abertos" else (0, 0, 0))
    for o in r["fechados"]:
        mt.jump(o, "scale", t, o.scale.copy() if t > 0 else (0, 0, 0), (1, 1, 1) if nome == "fechados" else (0, 0, 0))


def manchas(name, M, centro, raio, n, normal="x", seed=1, tam=(0.03, 0.09), cores=("mold", "mold_dark"),
            achatado=0.12, alongado=1.15):
    """Pontos de mofo/sujeira espalhados num disco sobre uma parede ou teto.
    centro=(x,y,z) na superfície; normal 'x' (parede de frente para +x), 'y' ou 'z' (teto/piso). Mais denso no meio.
    `achatado`: espessura relativa (0,12 = mancha chapada; ~0,7 = gotinha). `alongado`: estica o 2º eixo do disco.
    Retorna lista [(objeto, distância_ao_centro)] — anime com aparecer_manchas / sumir_manchas."""
    r = random.Random(seed)
    out = []
    for i in range(n):
        d = raio * math.sqrt(r.random()) * (0.55 + 0.45 * r.random())
        a = r.uniform(0, 2 * math.pi)
        u, v = d * math.cos(a), d * math.sin(a) * alongado
        s = r.uniform(*tam) * (1.25 - 0.6 * d / raio)
        m = M[cores[0] if r.random() < 0.45 else cores[1]]
        if normal == "x":
            loc, sc = (centro[0], centro[1] + u, centro[2] + v), (achatado, 1, 1)
        elif normal == "z":
            loc, sc = (centro[0] + u, centro[1] + v, centro[2]), (1, 1, achatado)
        else:
            loc, sc = (centro[0] + u, centro[1], centro[2] + v), (1, achatado, 1)
        o = ball(f"{name}{i}", s, loc, m, sub=2, scale=sc)
        for p in o.data.polygons:
            p.use_smooth = True
        out.append((o, d))
    return out


def aparecer_manchas(pts, t0, t1, de_dentro=True, d=0.25):
    """Cada ponto surge (pop) entre t0 e t1, do centro para fora (ou aleatório se de_dentro=False)."""
    dmax = max(dd for _, dd in pts) or 1
    r = random.Random(len(pts))
    for o, dd in pts:
        f = dd / dmax if de_dentro else r.random()
        pop_in(o, t0 + (t1 - t0 - d) * f, d)


def sumir_manchas(pts, t0, t1, ordem=None, d=0.2):
    """Cada ponto encolhe até sumir entre t0 e t1. `ordem(obj)` → 0..1 define a sequência (padrão: aleatória)."""
    r = random.Random(len(pts) + 1)
    for o, _ in pts:
        f = ordem(o) if ordem else r.random()
        mt.pop_out(o, t0 + (t1 - t0 - d) * f, d)


def particulas(name, M, mat_nome, n, origem, alvo, t0, t1, espalha=0.6, r=0.025, seed=3, ondas=3):
    """Nuvem de partículas (esporos, poeira, vapor) indo de `origem` até `alvo` em trajetos ondulados.
    Cada partícula sai num momento diferente entre t0 e o meio do intervalo. Retorna os objetos."""
    rr = random.Random(seed)
    o0, o1 = Vector(origem), Vector(alvo)
    objs = []
    for i in range(n):
        p = ball(f"{name}{i}", r * rr.uniform(0.6, 1.3), o0, M[mat_nome], sub=2 if r >= 0.015 else 1)
        if r >= 0.015:                       # fumaça/vapor: bolinha lisa
            for f in p.data.polygons:
                f.use_smooth = True
        start = t0 + (t1 - t0) * 0.5 * rr.random()
        dur = (t1 - start) * rr.uniform(0.7, 1.0)
        pts = []
        jit = Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-1, 1))) * espalha
        for j in range(ondas * 2 + 1):
            f = j / (ondas * 2)
            w = math.sin(f * math.pi)
            q = o0.lerp(o1 + jit * 0.4, f) + jit * w + Vector((0, 0, 0.15 * math.sin(f * 6.28 * ondas / 2 + i)))
            pts.append(tuple(q))
        mt.along(p, pts, start, start + dur)
        objs.append(p)
    return objs


def chuva(name, M, x0, x1, y0, y1, topo, chao, t0, t1, n=40, vento=(0.0, 0.0), mat_nome="rain", seed=9, periodo=0.55):
    """Gotas alongadas caindo de `topo` a `chao` dentro do retângulo (x0..x1, y0..y1); `vento`=(dx, dy) desloca a
    queda. `chao` pode ser uma função (x, y) -> z (ex.: bater numa parede). Retorna as gotas."""
    rr = random.Random(seed)
    gotas = []
    for i in range(n):
        x, y = rr.uniform(x0, x1), rr.uniform(y0, y1)
        zb = chao(x, y) if callable(chao) else chao
        g = box(f"{name}{i}", -0.012, 0.012, -0.012, 0.012, -0.14, 0.14, M[mat_nome], anchor="center")
        top = Vector((x - vento[0], y - vento[1], topo))
        bot = Vector((x, y, zb))
        mt.orient(g, top - bot)
        mt.loop_fall(g, t0, t1, top, bot, periodo * rr.uniform(0.85, 1.15), phase=rr.random() * periodo)
        gotas.append(g)
    return gotas


# ================================================================ personagem "de brinquedo" (liso, com rosto e membros)
PELE = {"skin": "#f2c4a0", "skin_dark": "#e3a985", "hair": "#3b2a20", "eye_white": "#ffffff", "pupil": "#1e1e24",
        "blush": "#f29a9a", "mouth": "#7a2e2e", "shirt": "#3f7fd0", "pants": "#2f3f5c", "shoe": "#2b2b2f"}


def materiais_personagem(M, camisa=None, cabelo=None, calca=None):
    for n, c in PELE.items():
        if n not in M:
            M[n] = mat(n, c, rough=0.6, emit=0.15 if n == "blush" else 0.0)
    if camisa:
        M["shirt_" + camisa.strip("#")] = M.get("shirt_" + camisa.strip("#")) or mat("shirt_" + camisa.strip("#"), camisa, rough=0.7)
    return M


def _liso(o):
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def esfera(name, r, loc, m, scale=(1, 1, 1), seg=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r, matrix=Matrix.Diagonal((*scale, 1)))
    return _liso(mesh_obj(name, bm, m, loc))


def capsula(name, r, comprimento, m, seg=20):
    """Cápsula ao longo de -z a partir da origem (bom para braço/perna pendurados de uma articulação)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=seg, radius1=r, radius2=r, depth=comprimento,
                          matrix=Matrix.Translation((0, 0, -comprimento / 2)))
    for z in (0.0, -comprimento):
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r, matrix=Matrix.Translation((0, 0, z)))
    return _liso(mesh_obj(name, bm, m))


def _arco(name, r, espessura, m, ang=math.pi, para_cima=True):
    """Arco (sorriso / olho fechado / boca triste) no plano x-z, de frente para -y."""
    bm = bmesh.new()
    n = 10
    a0 = math.pi + (math.pi - ang) / 2 if para_cima else (math.pi - ang) / 2
    pts = [(r * math.cos(a0 + ang * i / n), 0, r * math.sin(a0 + ang * i / n)) for i in range(n + 1)]
    for i in range(n):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        d = b - a
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=espessura, radius2=espessura, depth=d.length,
                              matrix=Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4())
    return _liso(mesh_obj(name, bm, m))


def personagem(name, M, camisa="shirt", calca="pants", cabelo="hair", altura=1.0, mascara=False, luvas=None):
    """Boneco de brinquedo (cabeça grande, rosto, braços, mãos, pernas). Olha para -y; origem nos pés.
    `altura` escala tudo (1,0 ≈ 1,45 m). Retorna dict com 'raiz', 'cabeca', 'braco_e', 'braco_d' (gire em x para
    levantar), 'mao_e', 'mao_d', 'olhos', 'boca'. Use rosto_expr(p, t, olhos=..., boca=...)."""
    materiais_personagem(M)
    root = empty(name)
    s = altura
    P = {"raiz": root}
    # pernas
    for lado, x in (("e", -0.11), ("d", 0.11)):
        perna = child(empty(f"{name}_perna_{lado}"), root, (x * s, 0, 0.5 * s))
        child(capsula(f"{name}_coxa_{lado}", 0.085 * s, 0.38 * s, M[calca]), perna)
        child(esfera(f"{name}_sapato_{lado}", 0.1 * s, (0, -0.04 * s, -0.44 * s), M["shoe"], scale=(0.9, 1.35, 0.6)), perna)
        P["perna_" + lado] = perna
    # tronco
    child(esfera(f"{name}_tronco", 0.24 * s, (0, 0, 0.74 * s), M[camisa], scale=(1, 0.8, 1.15)), root)
    child(esfera(f"{name}_quadril", 0.2 * s, (0, 0, 0.55 * s), M[calca], scale=(1.05, 0.85, 0.6)), root)
    # braços (articulação no ombro)
    for lado, x in (("e", -1), ("d", 1)):
        ombro = child(empty(f"{name}_ombro_{lado}"), root, (x * 0.25 * s, 0, 0.9 * s))
        child(capsula(f"{name}_braco_{lado}", 0.065 * s, 0.32 * s, M[camisa]), ombro)
        mao = child(esfera(f"{name}_mao_{lado}", 0.075 * s, (0, 0, -0.4 * s), M[luvas or "skin"]), ombro)
        P["braco_" + lado], P["mao_" + lado] = ombro, mao
        ombro.rotation_euler = (0, x * math.radians(-8), 0)
    # cabeça (articulação no pescoço)
    cab = child(empty(f"{name}_cabeca"), root, (0, 0, 1.0 * s))
    P["cabeca"] = cab
    R = 0.27 * s
    child(esfera(f"{name}_cranio", R, (0, 0, R * 0.95), M["skin"]), cab)
    cab_c = Vector((0, 0, R * 0.95))
    hair = child(esfera(f"{name}_cabelo", R * 1.05, tuple(cab_c + Vector((0, 0.04 * s, 0.05 * s))), M[cabelo],
                        scale=(1.0, 1.0, 0.9)), cab)
    # corta o cabelo na frente (franja) deslocando para trás/cima
    hair.location = tuple(cab_c + Vector((0, 0.07 * s, 0.07 * s)))
    for lado in (-1, 1):
        child(esfera(f"{name}_orelha{lado}", 0.05 * s, tuple(cab_c + Vector((lado * R * 0.98, 0, 0))), M["skin"],
                     scale=(0.5, 1, 1)), cab)
        child(esfera(f"{name}_bochecha{lado}", 0.045 * s, tuple(cab_c + Vector((lado * 0.13 * s, -R * 0.86, -0.07 * s))),
                     M["blush"], scale=(1, 0.3, 0.7)), cab)
    nariz = child(esfera(f"{name}_nariz", 0.035 * s, tuple(cab_c + Vector((0, -R * 0.99, -0.02 * s))), M["skin_dark"]), cab)
    olhos = {"abertos": [], "fechados": []}
    for lado in (-1, 1):
        c = cab_c + Vector((lado * 0.095 * s, -R * 0.9, 0.045 * s))
        o = child(esfera(f"{name}_olho{lado}", 0.042 * s, tuple(c), M["eye_white"], scale=(1, 0.5, 1.15)), cab)
        child(esfera(f"{name}_pupila{lado}", 0.026 * s, (0, -0.016 * s, -0.004 * s), M["pupil"], scale=(1, 0.5, 1.1)), o)
        olhos["abertos"].append(o)
        f = child(_arco(f"{name}_olhof{lado}", 0.035 * s, 0.009 * s, M["pupil"], ang=math.pi * 0.8, para_cima=True), cab,
                  tuple(c + Vector((0, -0.01 * s, 0.01 * s))))
        f.scale = (0, 0, 0)
        olhos["fechados"].append(f)
        child(box(f"{name}_sobr{lado}", -0.035 * s, 0.035 * s, -0.008 * s, 0.008 * s, -0.008 * s, 0.008 * s, M[cabelo],
                  anchor="center"), cab, tuple(c + Vector((0, -0.01 * s, 0.075 * s))))
    boca = {}
    bc = cab_c + Vector((0, -R * 0.93, -0.11 * s))
    boca["sorriso"] = child(_arco(f"{name}_sorriso", 0.05 * s, 0.011 * s, M["mouth"], ang=math.pi * 0.8), cab, tuple(bc))
    boca["triste"] = child(_arco(f"{name}_triste", 0.04 * s, 0.011 * s, M["mouth"], ang=math.pi * 0.7, para_cima=False),
                           cab, tuple(bc + Vector((0, 0, -0.035 * s))))
    boca["o"] = child(esfera(f"{name}_bocao", 0.032 * s, tuple(bc + Vector((0, 0, -0.01 * s))), M["mouth"],
                             scale=(0.8, 0.4, 1.0)), cab)
    boca["neutra"] = child(box(f"{name}_bocan", -0.03 * s, 0.03 * s, -0.008 * s, 0.008 * s, -0.007 * s, 0.007 * s,
                               M["mouth"], anchor="center"), cab, tuple(bc + Vector((0, 0, -0.02 * s))))
    for kname, o in boca.items():
        if kname != "sorriso":
            o.scale = (0, 0, 0)
    if mascara:
        P["mascara"] = child(esfera(f"{name}_mascara", 0.12 * s, tuple(bc + Vector((0, 0.03 * s, 0.05 * s))), M["mask"],
                                    scale=(1.4, 0.55, 1.1)), cab)
        nariz.scale = (0, 0, 0)            # o nariz fica dentro da máscara
        P["nariz"] = nariz
        for o in boca.values():            # boca escondida sob a máscara (rosto_expr mostra de novo)
            o.scale = (0, 0, 0)
    P["olhos"], P["boca"] = olhos, boca
    return P


def rosto_expr(P, t, olhos=None, boca=None):
    """Troca a expressão no tempo t. olhos: 'abertos'/'fechados'; boca: 'sorriso'/'triste'/'o'/'neutra'."""
    if olhos:
        for nome, objs in P["olhos"].items():
            for o in objs:
                v = (1, 1, 1) if nome == olhos else (0, 0, 0)
                mt.jump(o, "scale", t, tuple(o.scale), v)
    if boca:
        for nome, o in P["boca"].items():
            v = (1, 1, 1) if nome == boca else (0, 0, 0)
            mt.jump(o, "scale", t, tuple(o.scale), v)


# ================================================================ cozinha e elétrica (canal "dentro da sua casa")
ELETRICA = {"plastic_w": "#f4f2ec", "plastic_dark": "#2a2a2e", "socket_hole": "#151517", "brass": "#d8a93a",
            "conduit": "#f2c230", "box44": "#f08a24", "wire_ph": "#d23a2f", "wire_n": "#2f6fd2", "wire_t": "#3fa34d",
            "counter": "#9aa0a6", "cabinet": "#f1ede4", "handle": "#7d838a", "fryer": "#25262b", "fryer_win": "#3c4d5c",
            "micro": "#e9e9ea", "micro_door": "#202833", "coffee": "#c0392b", "coffee_jar": "#b9d6e8",
            "phone": "#1d1f24", "panel": "#c4c7cc", "breaker": "#f7f7f5", "lever": "#1f1f22", "spark": "#fff3b0",
            "heat": "#ff7a1c", "smoke": "#6d6d72", "burnt": "#3b2b1f"}
EMIT_EL = {"spark": 8.0, "heat": 2.0}
ALPHA_EL = {"coffee_jar": 0.55, "smoke": 0.6, "heat": 0.75}


def materiais_cozinha(M):
    materiais_casa(M)
    for n, c in ELETRICA.items():
        if n not in M:
            M[n] = mat(n, c, rough=0.35 if n in ("plastic_w", "micro", "fryer", "coffee", "brass") else 0.7,
                       emit=EMIT_EL.get(n, 0.0), alpha=ALPHA_EL.get(n, 1.0))
    return M


def caixa_arred(name, x0, x1, y0, y1, z0, z1, m, r=0.02, anchor="bottom"):
    """Caixa com quinas arredondadas (chanfro + sombreamento liso): visual de brinquedo/eletrodoméstico."""
    o = box(name, x0, x1, y0, y1, z0, z1, m, anchor=anchor)
    b = o.modifiers.new("arred", "BEVEL")
    b.width = r
    b.segments = 3
    b.limit_method = "ANGLE"
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def tomada(name, M, cor="plastic_w"):
    """Tomada 2P+T (placa + 3 furos) de frente para -y, origem no centro da placa, encostada em y = 0."""
    root = empty(name)
    child(caixa_arred(name + "_placa", -0.04, 0.04, -0.012, 0.0, -0.06, 0.06, M[cor], r=0.006, anchor="center"), root)
    child(disc(name + "_rebaixo", 0.024, 0.006, M[cor], seg=20), root, (0, -0.013, 0))
    for i, (x, z) in enumerate([(-0.011, 0.006), (0.011, 0.006), (0, -0.009)]):
        child(disc(f"{name}_furo{i}", 0.0035, 0.004, M["socket_hole"], seg=8), root, (x, -0.017, z))
    return root


def benjamim(name, M, cor="plastic_w"):
    """Adaptador T (benjamim) de frente para -y; os pinos saem em +y (encaixe na tomada). Origem no centro."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.032, 0.032, -0.03, 0.03, -0.032, 0.032, M[cor], r=0.008, anchor="center"), root)
    for i, (pos, rot) in enumerate([((0, -0.031, 0), (math.pi / 2, 0, 0)), ((-0.033, 0, 0), (0, math.pi / 2, 0)),
                                    ((0.033, 0, 0), (0, math.pi / 2, 0))]):
        d = child(disc(f"{name}_tom{i}", 0.017, 0.004, M[cor], seg=16), root, pos)
        d.rotation_euler = rot
    for i, x in enumerate((-0.011, 0.011)):
        p = child(cyl(f"{name}_pino{i}", 0.0025, 0, 0.02, (0, 0), M["brass"], seg=8), root, (x, 0.03, 0.004))
        p.rotation_euler = (-math.pi / 2, 0, 0)
    return root


def plugue(name, M, cor="plastic_dark"):
    """Plugue com pinos saindo em +y. Origem na face dos pinos (encoste na tomada/benjamim)."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.016, 0.016, -0.045, -0.004, -0.018, 0.018, M[cor], r=0.006, anchor="center"), root)
    for i, x in enumerate((-0.011, 0.011)):
        p = child(cyl(f"{name}_pino{i}", 0.0025, 0, 0.018, (0, 0), M["brass"], seg=8), root, (x, -0.004, 0.003))
        p.rotation_euler = (-math.pi / 2, 0, 0)
    return root


def cabo(name, M, pts, r=0.006, cor="plastic_dark"):
    """Cabo flexível por uma polilinha (lista de pontos). Retorna os segmentos."""
    segs = []
    for j in range(len(pts) - 1):
        segs.append(tube(f"{name}{j}", pts[j], pts[j + 1], r, M[cor], seg=6))
        if j:
            ball(f"{name}_n{j}", r, pts[j], M[cor], sub=1)
    return segs


def bancada(name, M, comprimento=2.4, profundidade=0.6, altura=0.9):
    """Bancada de cozinha (armários + tampo) ao longo de x, fundo em y = profundidade. Origem no chão, canto esquerdo
    da frente."""
    root = empty(name)
    child(box(name + "_corpo", 0, comprimento, 0.04, profundidade, 0.1, altura - 0.04, M["cabinet"]), root)
    child(box(name + "_rodape", 0.03, comprimento - 0.03, 0.08, profundidade, 0, 0.1, M["plastic_dark"]), root)
    child(caixa_arred(name + "_tampo", -0.02, comprimento + 0.02, 0.0, profundidade + 0.01, altura - 0.04, altura,
                      M["counter"], r=0.01), root)
    n = max(2, int(comprimento / 0.6))
    w = comprimento / n
    for i in range(n):
        child(box(f"{name}_porta{i}", i * w + 0.015, (i + 1) * w - 0.015, 0.02, 0.04, 0.13, altura - 0.08, M["cabinet"]), root)
        child(caixa_arred(f"{name}_puxador{i}", i * w + w * 0.42, i * w + w * 0.58, 0.0, 0.02, altura - 0.2,
                          altura - 0.17, M["handle"], r=0.005), root)
    return root


def air_fryer(name, M):
    """Air fryer (frente para -y). Origem na base."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.15, 0.15, -0.16, 0.16, 0, 0.32, M["fryer"], r=0.06), root)
    child(caixa_arred(name + "_cesto", -0.12, 0.12, -0.175, -0.13, 0.03, 0.17, M["fryer"], r=0.02), root)
    child(caixa_arred(name + "_alca", -0.035, 0.035, -0.23, -0.17, 0.08, 0.12, M["plastic_dark"], r=0.012), root)
    child(caixa_arred(name + "_painel", -0.09, 0.09, -0.17, -0.15, 0.2, 0.29, M["fryer_win"], r=0.015), root)
    return root


def micro_ondas(name, M):
    """Micro-ondas (frente para -y). Origem na base."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.25, 0.25, -0.18, 0.18, 0, 0.29, M["micro"], r=0.02), root)
    child(caixa_arred(name + "_porta", -0.23, 0.1, -0.19, -0.17, 0.03, 0.26, M["micro_door"], r=0.01), root)
    child(box(name + "_painel", 0.13, 0.23, -0.19, -0.18, 0.05, 0.25, M["panel"]), root)
    for j in range(3):
        child(disc(f"{name}_botao{j}", 0.015, 0.012, M["plastic_dark"], seg=12), root, (0.18, -0.195, 0.2 - j * 0.05))
    return root


def cafeteira(name, M):
    root = empty(name)
    child(caixa_arred(name + "_base", -0.09, 0.09, -0.1, 0.1, 0, 0.04, M["coffee"], r=0.015), root)
    child(caixa_arred(name + "_torre", -0.09, 0.09, 0.03, 0.1, 0.04, 0.3, M["coffee"], r=0.02), root)
    child(caixa_arred(name + "_topo", -0.09, 0.09, -0.08, 0.1, 0.26, 0.31, M["coffee"], r=0.02), root)
    child(cyl(name + "_jarra", 0.06, 0.04, 0.2, (0, -0.03), M["coffee_jar"], seg=16), root)
    return root


def celular_carregando(name, M):
    """Celular deitado com carregador (o carregador fica na origem; o cabo sai em -y)."""
    root = empty(name)
    child(caixa_arred(name + "_fonte", -0.02, 0.02, -0.02, 0.02, -0.02, 0.02, M["plastic_w"], r=0.006, anchor="center"), root)
    return root


def caixinha_4x2(name, M):
    """Caixa de embutir 4x2 (laranja), aberta para -y, origem no centro da boca."""
    root = empty(name)
    bm = bmesh.new()
    mt.box_bm(bm, -0.03, 0.03, 0.0, 0.05, -0.055, 0.055)
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.y < -0.9], context="FACES")
    o = child(mesh_obj(name + "_c", bm, M["box44"]), root)
    o.modifiers.new("esp", "SOLIDIFY").thickness = 0.004
    return root


def fios_eletricos(name, M, pts, sep=0.012, r=0.0035, conduite=True):
    """Fase (vermelho), neutro (azul) e terra (verde) seguindo a polilinha pts, dentro de um conduíte amarelo opcional.
    Retorna (lista de segmentos de fio por cor, segmentos do conduíte)."""
    fios = {"wire_ph": [], "wire_n": [], "wire_t": []}
    for c, off in (("wire_ph", -sep), ("wire_n", 0.0), ("wire_t", sep)):
        p2 = [Vector(p) + Vector((off, 0, 0)) for p in pts]
        for j in range(len(p2) - 1):
            fios[c].append(tube(f"{name}_{c}{j}", p2[j], p2[j + 1], r, M[c], seg=6))
    cond = []
    if conduite:
        for j in range(len(pts) - 1):
            cond.append(tube(f"{name}_cond{j}", pts[j], pts[j + 1], sep * 2.4, M["conduit"], seg=10))
    return fios, cond


def quadro_disjuntores(name, M, n=6):
    """Quadro de luz com a tampa aberta, de frente para -y. Retorna (raiz, lista de alavancas)."""
    root = empty(name)
    child(caixa_arred(name + "_caixa", -0.22, 0.22, 0.0, 0.1, -0.2, 0.2, M["panel"], r=0.015, anchor="center"), root)
    child(box(name + "_fundo", -0.2, 0.2, -0.005, 0.0, -0.18, 0.18, M["plastic_dark"], anchor="center"), root)
    alav = []
    for i in range(n):
        x = -0.17 + i * (0.34 / (n - 1))
        child(caixa_arred(f"{name}_dj{i}", x - 0.024, x + 0.024, -0.05, 0.0, -0.06, 0.06, M["breaker"], r=0.004,
                          anchor="center"), root)
        lv = child(empty(f"{name}_lv{i}"), root, (x, -0.05, 0))
        child(box(f"{name}_alav{i}", -0.008, 0.008, -0.03, 0.0, 0.0, 0.035, M["lever"]), lv)
        alav.append(lv)
    return root, alav


def faisca(name, M, loc, t, d=0.35, raios=9, tamanho=0.08, seed=4):
    """Faísca: raios emissivos que estouram em t e somem em t + d."""
    rr = random.Random(seed)
    root = empty(name, loc)
    for i in range(raios):
        a = rr.uniform(0, 2 * math.pi)
        b = rr.uniform(-0.8, 0.8)
        dirv = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b)))
        s = child(tube(f"{name}_{i}", (0, 0, 0), tuple(dirv * tamanho * rr.uniform(0.6, 1.2)), 0.003, M["spark"], seg=4), root)
    pop_in(root, t, d * 0.4)
    mt.pop_out(root, t + d * 0.5, d * 0.5)
    return root


# ================================================================ decoração "aconchegante" (cozinha/sala)
DECOR = {"leaf2": "#4caf50", "leaf3": "#7cc96b", "pot": "#d9825b", "orange_f": "#f39c12", "apple": "#e74c3c",
         "bowl": "#f5e6c8", "table_wood": "#c9935f", "clock_face": "#fbfaf5", "clock_rim": "#2f6f8f",
         "iron": "#4fa3c7", "heater": "#e8e3d8", "heater_grill": "#ff9a3c", "strip": "#f6f6f2", "seal": "#2e9e5b",
         "curtain": "#f7c6c7", "pendant": "#f6d36b", "bulb": "#fff4d0"}


def materiais_decor(M):
    materiais_cozinha(M)
    for n, c in DECOR.items():
        if n not in M:
            M[n] = mat(n, c, rough=0.5, emit=4.0 if n == "bulb" else 0.0)
    return M


def vaso_planta(name, M, altura=0.35, folhas=7, seed=2):
    """Vaso com folhas arredondadas. Origem na base."""
    rr = random.Random(seed)
    root = empty(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.08 * altura / 0.35, radius2=0.11 * altura / 0.35,
                          depth=0.14 * altura / 0.35, matrix=Matrix.Translation((0, 0, 0.07 * altura / 0.35)))
    child(_liso(mesh_obj(name + "_vaso", bm, M["pot"])), root)
    for i in range(folhas):
        a = i / folhas * 2 * math.pi + rr.uniform(-0.3, 0.3)
        r = rr.uniform(0.04, 0.1) * altura / 0.35
        z = rr.uniform(0.2, 0.34) * altura / 0.35
        f = child(esfera(f"{name}_f{i}", 0.07 * altura / 0.35, (math.cos(a) * r, math.sin(a) * r, z),
                         M[rr.choice(["leaf2", "leaf3", "leaf"])], scale=(1.0, 0.55, 1.4), seg=12), root)
        f.rotation_euler = (rr.uniform(-0.5, 0.5), rr.uniform(-0.6, 0.6), a)
    return root


def fruteira(name, M, seed=3):
    rr = random.Random(seed)
    root = empty(name)
    child(esfera(name + "_tigela", 0.13, (0, 0, 0.05), M["bowl"], scale=(1, 1, 0.45)), root)
    for i, (x, y) in enumerate([(-0.05, -0.02), (0.05, 0.0), (0.0, 0.05), (0.0, -0.05)]):
        child(esfera(f"{name}_fr{i}", 0.045, (x, y, 0.1 + 0.01 * i), M[rr.choice(["orange_f", "apple", "orange_f"])]), root)
    return root


def mesa(name, M, comprimento=1.1, largura=0.75, altura=0.75):
    root = empty(name)
    child(caixa_arred(name + "_tampo", -comprimento / 2, comprimento / 2, -largura / 2, largura / 2, altura - 0.05, altura,
                      M["table_wood"], r=0.015), root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            child(cyl(f"{name}_pe{sx}{sy}", 0.03, 0, altura - 0.05, (sx * (comprimento / 2 - 0.08), sy * (largura / 2 - 0.08)),
                      M["table_wood"], seg=10), root)
    return root


def cadeira(name, M, cor="table_wood"):
    """Cadeira com o encosto em +y. Origem no chão."""
    root = empty(name)
    child(caixa_arred(name + "_assento", -0.2, 0.2, -0.2, 0.2, 0.42, 0.47, M[cor], r=0.015), root)
    child(caixa_arred(name + "_encosto", -0.2, 0.2, 0.17, 0.21, 0.47, 0.85, M[cor], r=0.015), root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            child(cyl(f"{name}_pe{sx}{sy}", 0.02, 0, 0.42, (sx * 0.17, sy * 0.17), M[cor], seg=8), root)
    return root


def relogio_parede(name, M, raio=0.16):
    """Relógio de parede de frente para -y. Retorna (raiz, ponteiro_hora, ponteiro_minuto): gire os ponteiros em y."""
    root = empty(name)
    a = child(disc(name + "_aro", raio, 0.04, M["clock_rim"], seg=32), root)
    child(disc(name + "_mostrador", raio * 0.86, 0.045, M["clock_face"], seg=32), root, (0, -0.003, 0))
    for i in range(12):
        ang = i / 12 * 2 * math.pi
        child(box(f"{name}_m{i}", -0.006, 0.006, -0.03, -0.024, raio * 0.66, raio * 0.76, M["dark"], anchor="bottom"),
              root).rotation_euler = (0, ang, 0)
    hora = child(empty(name + "_ph"), root, (0, -0.03, 0))
    child(box(name + "_h", -0.008, 0.008, -0.006, 0.0, 0, raio * 0.45, M["dark"]), hora)
    minuto = child(empty(name + "_pm"), root, (0, -0.036, 0))
    child(box(name + "_mi", -0.005, 0.005, -0.006, 0.0, 0, raio * 0.68, M["red"]), minuto)
    child(esfera(name + "_eixo", 0.012, (0, -0.04, 0), M["dark"]), root)
    return root, hora, minuto


def ferro_passar(name, M):
    root = empty(name)
    bm = bmesh.new()
    pts = [(-0.13, 0.0), (0.13, 0.0), (0.07, 0.07), (-0.13, 0.07)]
    o = child(prism(name + "_corpo", pts, -0.06, 0.06, M["iron"]), root)
    o.rotation_euler = (0, 0, 0)
    child(caixa_arred(name + "_base", -0.135, 0.135, -0.065, 0.065, -0.012, 0.0, M["steel"], r=0.005), root)
    child(caixa_arred(name + "_alca", -0.1, 0.05, -0.02, 0.02, 0.07, 0.12, M["iron"], r=0.012), root)
    return root


def aquecedor(name, M):
    """Aquecedor elétrico portátil (frente para -y)."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.14, 0.14, -0.08, 0.08, 0.02, 0.36, M["heater"], r=0.03), root)
    for j in range(5):
        child(box(f"{name}_grade{j}", -0.1, 0.1, -0.085, -0.075, 0.08 + j * 0.05, 0.1 + j * 0.05, M["heater_grill"]), root)
    child(caixa_arred(name + "_pe", -0.12, 0.12, -0.1, 0.1, 0, 0.025, M["plastic_dark"], r=0.01), root)
    return root


def filtro_linha(name, M, tomadas=4):
    """Filtro de linha (régua) ao longo de x, tomadas viradas para +z, com selo verde e botão. Origem na base."""
    root = empty(name)
    L = 0.07 * tomadas + 0.08
    child(caixa_arred(name + "_corpo", -L / 2, L / 2, -0.035, 0.035, 0, 0.045, M["strip"], r=0.012), root)
    for i in range(tomadas):
        x = -L / 2 + 0.11 + i * 0.07
        d = child(disc(f"{name}_t{i}", 0.02, 0.004, M["socket_hole"], seg=16), root, (x, 0, 0.046))
        d.rotation_euler = (0, 0, 0)
    child(caixa_arred(name + "_botao", L / 2 - 0.05, L / 2 - 0.02, -0.015, 0.015, 0.04, 0.055, M["red"], r=0.005), root)
    selo = child(disc(name + "_selo", 0.014, 0.004, M["seal"], seg=16), root, (-L / 2 + 0.04, 0, 0.047))
    return root, selo


def pendente(name, M, altura_fio=0.6):
    """Luminária pendente (cúpula + lâmpada). Origem no teto."""
    root = empty(name)
    child(tube(name + "_fio", (0, 0, 0), (0, 0, -altura_fio), 0.006, M["dark"], seg=6), root)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.2, radius2=0.05, depth=0.18,
                          matrix=Matrix.Translation((0, 0, -altura_fio - 0.09)))
    c = child(_liso(mesh_obj(name + "_cupula", bm, M["pendant"])), root)
    c.modifiers.new("esp", "SOLIDIFY").thickness = 0.01
    child(esfera(name + "_lampada", 0.05, (0, 0, -altura_fio - 0.17), M["bulb"]), root)
    return root


# ================================================================ banheiro (canal "dentro da sua casa")
BANHO = {"porcelain": "#fbfbf8", "chrome": "#c3ccd4", "mirror": "#d3e8f2", "shine": "#ffffff", "fog": "#eef4f6",
         "curtain_b": "#7fcfc4", "sponge_b": "#9ad04f", "pole": "#3f7fd0", "bleach": "#f7f7f2", "bleach_cap": "#2f6fd2",
         "bleach_lab": "#4fc3f7", "timer": "#f6f6f2", "steam": "#eef7fb", "towel": "#f4d468", "robe": "#f06aa0",
         "cap_pink": "#f59ac0", "door": "#f1e6d4", "vent": "#f2f2ee", "vent_blade": "#9aa3ab", "vent_mark": "#e53935",
         "glass_w": "#bfe3f2", "drop": "#4fc3f7", "drain": "#5f6670", "bottle_a": "#ff8fab", "bottle_b": "#7ec8e3",
         "bottle_c": "#ffd166", "mat_b": "#5aa6d6", "stain_y": "#e3c766", "stain_b": "#a87a3c", "light_off": "#e8e4da"}
EMIT_B = {"steam": 0.06, "drop": 0.9, "shine": 0.8}
ALPHA_B = {"fog": 0.0, "steam": 0.3, "glass_w": 0.35, "stain_y": 0.85, "stain_b": 0.75}
ROUGH_B = {"porcelain": 0.25, "chrome": 0.2, "mirror": 0.1, "glass_w": 0.1, "drop": 0.2, "steam": 0.9}


def materiais_banheiro(M):
    """Materiais das peças de banheiro (inclui os de casa, cozinha, decoração e personagem)."""
    materiais_decor(M)
    materiais_personagem(M)
    for n, c in BANHO.items():
        if n not in M:
            M[n] = mat(n, c, rough=ROUGH_B.get(n, 0.6), emit=EMIT_B.get(n, 0.0), alpha=ALPHA_B.get(n, 1.0))
            if n in ("mirror", "chrome"):
                mt.bsdf(M[n]).inputs["Metallic"].default_value = 0.85 if n == "mirror" else 0.6
    return M


def ladrilho_mat(name, c1, c2, junta, tam=(0.25, 0.25), junta_tam=0.04, piso=False, rough=0.35):
    """Azulejo/piso em grade (sem desencontro), em metros: `tam` = largura x altura de cada peça.
    Parede: usa (x + y, z) do objeto; piso (piso=True): usa (x, y)."""
    m = mat(name, c1, rough=rough)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.squash = 1.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = tam[0]
    br.inputs["Row Height"].default_value = tam[1]
    br.inputs["Mortar Size"].default_value = tam[0] * junta_tam
    br.inputs["Color1"].default_value = mt.lin(c1)
    br.inputs["Color2"].default_value = mt.lin(c2)
    br.inputs["Mortar"].default_value = mt.lin(junta)
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    if piso:
        nt.links.new(sep.outputs["X"], comb.inputs["X"])
        nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
    else:
        nt.links.new(sep.outputs["X"], add.inputs[0])
        nt.links.new(sep.outputs["Y"], add.inputs[1])
        nt.links.new(add.outputs[0], comb.inputs["X"])
        nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], mt.bsdf(m).inputs["Base Color"])
    return m


def parede_furada(name, eixo, plano, a0, a1, z0, z1, buracos, m):
    """Placa vertical (parede) com recortes retangulares (janelas, portas), sem perder os furos internos.
    eixo 'x': placa no plano x-z, com espessura em y = plano (c0, c1); eixo 'y': placa no plano y-z (espessura em x).
    a0..a1 ao longo do eixo, z0..z1 na altura; buracos = [(a0, a1, z0, z1)]."""
    g = sg.box(a0, z0, a1, z1)
    xs = {a0, a1}
    if buracos:
        g = g.difference(unary_union([sg.box(b[0], b[2], b[1], b[3]) for b in buracos]))
        xs |= {b[0] for b in buracos} | {b[1] for b in buracos}
    xs = sorted(x for x in xs if a0 <= x <= a1)
    bm = bmesh.new()
    for xa, xb in zip(xs, xs[1:]):               # faixas verticais: nenhum pedaço fica com furo interno
        for p in mt.polys(g.intersection(sg.box(xa, z0 - 1, xb, z1 + 1))):
            mt.prism_bm(bm, mt.ring(p), plano[0], plano[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_obj(name, bm, m)
    if eixo == "y":                       # placa no plano y-z: troca x <-> y
        for v in o.data.vertices:
            v.co.x, v.co.y = v.co.y, v.co.x
        o.data.flip_normals()
    return o


def vaso_sanitario(name, M):
    """Vaso com caixa acoplada encostado na parede (fundo em y = 0), frente para -y. Origem no chão, meio do fundo."""
    root = empty(name)
    child(caixa_arred(name + "_caixa", -0.19, 0.19, -0.19, -0.01, 0.42, 0.78, M["porcelain"], r=0.03), root)
    child(caixa_arred(name + "_tampa_cx", -0.2, 0.2, -0.2, 0.0, 0.78, 0.81, M["porcelain"], r=0.012), root)
    child(cyl(name + "_botao", 0.03, 0.81, 0.825, (0, -0.1), M["chrome"], seg=16), root)
    child(esfera(name + "_pe", 0.13, (0, -0.33, 0.17), M["porcelain"], scale=(1.0, 1.25, 1.35)), root)
    child(esfera(name + "_bacia", 0.2, (0, -0.42, 0.36), M["porcelain"], scale=(1.0, 1.3, 0.42)), root)
    child(esfera(name + "_assento", 0.205, (0, -0.43, 0.45), M["white"], scale=(1.0, 1.28, 0.1)), root)
    return root


def pia_banheiro(name, M, largura=0.56, cor="cabinet"):
    """Gabinete com tampo, cuba de apoio e torneira, encostado na parede (y = 0), frente para -y.
    Origem no chão, meio do fundo."""
    w = largura / 2
    root = empty(name)
    child(caixa_arred(name + "_gab", -w, w, -0.42, 0.0, 0.12, 0.78, M[cor], r=0.015), root)
    child(box(name + "_rodape", -w + 0.03, w - 0.03, -0.38, 0.0, 0.0, 0.12, M["plastic_dark"]), root)
    child(box(name + "_divisao", -0.004, 0.004, -0.426, -0.42, 0.16, 0.74, M["handle"]), root)
    for s in (-1, 1):
        child(caixa_arred(f"{name}_pux{s}", s * 0.035 - 0.01, s * 0.035 + 0.01, -0.44, -0.42, 0.6, 0.7, M["handle"], r=0.004), root)
    child(caixa_arred(name + "_tampo", -w - 0.01, w + 0.01, -0.45, 0.0, 0.78, 0.82, M["counter"], r=0.008), root)
    child(esfera(name + "_cuba", 0.17, (0, -0.24, 0.86), M["porcelain"], scale=(1.0, 0.8, 0.42)), root)
    child(esfera(name + "_cuba_in", 0.15, (0, -0.24, 0.925), M["mirror"], scale=(1.0, 0.78, 0.08)), root)
    child(tube(name + "_bica_v", (0, -0.04, 0.82), (0, -0.04, 1.03), 0.016, M["chrome"]), root)
    child(tube(name + "_bica_h", (0, -0.04, 1.03), (0, -0.17, 1.0), 0.013, M["chrome"]), root)
    child(caixa_arred(name + "_registro", -0.012, 0.012, -0.08, -0.03, 1.04, 1.06, M["chrome"], r=0.005), root)
    return root


def espelho(name, M, largura=0.45, altura=0.6, moldura="frame"):
    """Espelho de frente para -y, encostado em y = 0. Origem no centro.
    Retorna (raiz, embaçado): o embaçado tem material próprio — use embacar(embaçado, t0, t1)."""
    root = empty(name)
    w, h = largura / 2, altura / 2
    child(caixa_arred(name + "_moldura", -w - 0.025, w + 0.025, -0.02, 0.0, -h - 0.025, h + 0.025, M[moldura], r=0.01,
                      anchor="center"), root)
    child(box(name + "_vidro", -w, w, -0.026, -0.02, -h, h, M["mirror"], anchor="center"), root)
    for i, (dx, ww) in enumerate(((-0.06, 0.035), (0.05, 0.016))):
        b = child(box(f"{name}_brilho{i}", -ww / 2, ww / 2, -0.029, -0.026, -h * 0.55, h * 0.55, M["shine"], anchor="center"),
                  root, (dx * largura / 0.45, 0, 0))
        b.rotation_euler = (0, math.radians(35), 0)
    fog = M["fog"].copy()
    fog.name = name + "_fog"
    emb = child(box(name + "_embaco", -w, w, -0.034, -0.03, -h, h, fog, anchor="center"), root)
    return root, emb


def embacar(obj, t0, t1, ate=0.88, de=0.0):
    """Anima a opacidade (Alpha) do material do objeto de `de` até `ate` entre t0 e t1."""
    m = obj.data.materials[0]
    mt.key_input(m, "Alpha", t0, de)
    mt.key_input(m, "Alpha", t1, ate)


def exaustor(name, M, lado=0.26):
    """Exaustor de parede (caixa quadrada, grade e hélice), de frente para -y, encostado em y = 0. Origem no centro.
    Retorna (raiz, hélice): gire a hélice com girar(hélice, t0, t1)."""
    root = empty(name)
    a = lado / 2
    child(caixa_arred(name + "_caixa", -a, a, -0.04, 0.0, -a, a, M["vent"], r=0.015, anchor="center"), root)
    d = child(disc(name + "_furo", a * 0.8, 0.008, M["dark"], seg=24), root, (0, -0.041, 0))
    hel = child(empty(name + "_helice"), root, (0, -0.05, 0))
    for i in range(4):
        pa = child(box(f"{name}_pa{i}", -0.026, 0.026, -0.004, 0.004, 0.012, a * 0.74,
                       M["vent_mark" if i == 0 else "vent_blade"]), hel)
        pa.rotation_euler = (0, i * math.pi / 2, 0)
    child(esfera(name + "_cubo", 0.026, (0, -0.006, 0), M["vent_blade"], seg=12), hel)
    for j in range(-3, 4):
        child(box(f"{name}_grade{j}", -a * 0.82, a * 0.82, -0.066, -0.058, j * 0.03 - 0.0045, j * 0.03 + 0.0045, M["vent"],
                  anchor="center"), root)
    return root, hel


def girar(o, t0, t1, rps=1.4, eixo=1, partida=0.5, parada=0.8, ang0=None):
    """Gira o objeto no eixo local (0 = x, 1 = y, 2 = z) entre t0 e t1, acelerando por `partida` s e
    desacelerando por `parada` s. Chaves lineares a cada quadro. Retorna o ângulo final (para continuar depois)."""
    fps = mt.FPS
    a = o.rotation_euler[eixo] if ang0 is None else ang0
    f0, f1 = mt.F(t0), mt.F(t1)
    w = 2 * math.pi * rps / fps
    for f in range(f0, f1 + 1):
        t = (f - 1) / fps
        v = w * min(1.0, (t - t0) / partida if partida else 1.0, (t1 - t) / parada if parada else 1.0)
        rot = list(o.rotation_euler)
        rot[eixo] = a
        o.rotation_euler = rot
        o.keyframe_insert("rotation_euler", index=eixo, frame=f)
        a += max(0.0, v)
    ad = o.animation_data
    fcs = []
    if ad and ad.action:
        act = ad.action
        if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
            fcs = list(act.fcurves)
        else:
            for layer in getattr(act, "layers", []):
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        fcs.extend(cb.fcurves)
    for fc in fcs:
        if fc.data_path == "rotation_euler" and fc.array_index == eixo:
            for kp in fc.keyframe_points:
                if f0 <= kp.co.x <= f1:
                    kp.interpolation = "LINEAR"
    return a


def vitro(name, M, largura=0.55, altura=0.5, laminas=3, moldura="frame"):
    """Vitrô basculante de frente para -y, no plano y = 0 (moldura + lâminas de vidro que giram no eixo x).
    Origem no centro. Retorna (raiz, pivôs das lâminas): abra com rotation_euler.x (≈ 55°)."""
    root = empty(name)
    w, h = largura / 2, altura / 2
    e = 0.035
    for nm, (x0, x1, z0, z1) in (("i", (-w - e, w + e, -h - e, -h)), ("s", (-w - e, w + e, h, h + e)),
                                 ("e", (-w - e, -w, -h, h)), ("d", (w, w + e, -h, h))):
        child(box(f"{name}_mold_{nm}", x0, x1, -0.03, 0.03, z0, z1, M[moldura]), root)
    piv = []
    hl = altura / laminas
    for i in range(laminas):
        p = child(empty(f"{name}_piv{i}"), root, (0, 0, -h + hl * (i + 0.5)))
        child(box(f"{name}_lam{i}", -w + 0.005, w - 0.005, -0.006, 0.006, -hl / 2 + 0.006, hl / 2 - 0.006, M["glass_w"],
                  anchor="center"), p)
        child(box(f"{name}_lamb{i}", -w + 0.005, w - 0.005, -0.008, 0.008, hl / 2 - 0.016, hl / 2 - 0.004, M[moldura],
                  anchor="center"), p)
        piv.append(p)
    return root, piv


def chuveiro(name, M):
    """Chuveiro de parede: cano saindo da parede (y = 0) para -y, cotovelo e ducha redonda virada para baixo.
    Origem no ponto da parede. Retorna (raiz, posição local do centro da ducha)."""
    root = empty(name)
    child(cyl(name + "_canopla", 0.04, 0, 0.02, (0, 0), M["chrome"], seg=16), root).rotation_euler = (math.pi / 2, 0, 0)
    child(tube(name + "_cano", (0, 0, 0), (0, -0.3, 0.0), 0.016, M["chrome"]), root)
    child(tube(name + "_cano2", (0, -0.3, 0.0), (0, -0.33, -0.05), 0.016, M["chrome"]), root)
    child(cyl(name + "_ducha", 0.09, 0.0, 0.035, (0, 0), M["chrome"], seg=24), root, (0, -0.35, -0.06))
    child(cyl(name + "_crivo", 0.075, 0.0, 0.01, (0, 0), M["drain"], seg=24), root, (0, -0.35, -0.066))
    return root, Vector((0, -0.35, -0.07))


def cortina_box(name, M, largura=0.95, altura=1.8, cor="curtain_b", ondas=6, amp=0.035):
    """Cortina de box pregueada ao longo de +x a partir da origem (presa no alto, em z = 0, caindo até -altura).
    Feche/abra com scale.x (1 = fechada; ~0,18 = recolhida junto da origem)."""
    bm = bmesh.new()
    n = ondas * 8
    top, bot = [], []
    for i in range(n + 1):
        x = largura * i / n
        y = amp * math.sin(2 * math.pi * ondas * i / n)
        top.append(bm.verts.new((x, y, 0)))
        bot.append(bm.verts.new((x, y, -altura)))
    for i in range(n):
        bm.faces.new([top[i], top[i + 1], bot[i + 1], bot[i]])
    o = _liso(mesh_obj(name, bm, M[cor]))
    o.modifiers.new("esp", "SOLIDIFY").thickness = 0.01
    return o


def esfregao(name, M, cabo=1.0, cor="sponge_b"):
    """Esfregão de cabo comprido (limpar teto): esponja na origem com a face de esfregar para +z e o cabo descendo
    em -z (a mão segura a `cabo` m da origem)."""
    root = empty(name)
    child(caixa_arred(name + "_esponja", -0.12, 0.12, -0.05, 0.05, -0.05, 0.0, M[cor], r=0.015), root)
    child(box(name + "_base", -0.13, 0.13, -0.055, 0.055, -0.075, -0.05, M["plastic_dark"]), root)
    child(tube(name + "_cabo", (0, 0, -0.075), (0, 0, -cabo), 0.014, M["pole"]), root)
    return root


def frasco_sanitaria(name, M):
    """Frasco de água sanitária (branco, rótulo azul-claro, tampa azul). Origem na base."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.07, 0.07, -0.05, 0.05, 0, 0.24, M["bleach"], r=0.03), root)
    child(caixa_arred(name + "_rotulo", -0.073, 0.073, -0.053, 0.053, 0.07, 0.16, M["bleach_lab"], r=0.01), root)
    child(cyl(name + "_gargalo", 0.022, 0.235, 0.285, (0.03, 0), M["bleach"], seg=12), root)
    child(cyl(name + "_tampa", 0.027, 0.285, 0.315, (0.03, 0), M["bleach_cap"], seg=12), root)
    child(caixa_arred(name + "_alca", -0.065, -0.035, -0.014, 0.014, 0.12, 0.27, M["bleach"], r=0.01), root)
    return root


def interruptor(name, M):
    """Interruptor (placa + tecla) de frente para -y, encostado em y = 0. Origem no centro.
    Retorna (raiz, tecla): incline a tecla em x (+0,25 rad = ligado, -0,25 = desligado)."""
    root = empty(name)
    child(caixa_arred(name + "_placa", -0.045, 0.045, -0.012, 0.0, -0.065, 0.065, M["plastic_w"], r=0.006, anchor="center"), root)
    tec = child(empty(name + "_tecla"), root, (0, -0.012, 0))
    child(caixa_arred(name + "_tecla_m", -0.024, 0.024, -0.012, 0.0, -0.038, 0.038, M["plastic_w"], r=0.006, anchor="center"), tec)
    child(box(name + "_marca", -0.007, 0.007, -0.0135, -0.011, 0.02, 0.028, M["dark"], anchor="center"), tec)
    return root, tec


def temporizador(name, M):
    """Temporizador de parede (caixa, mostrador e ponteiro), de frente para -y, encostado em y = 0. Origem no centro.
    Retorna (raiz, ponteiro): gire o ponteiro em y."""
    root = empty(name)
    child(caixa_arred(name + "_caixa", -0.05, 0.05, -0.03, 0.0, -0.07, 0.07, M["timer"], r=0.012, anchor="center"), root)
    child(disc(name + "_mostrador", 0.036, 0.006, M["clock_face"], seg=24), root, (0, -0.033, 0.005))
    for i in range(8):
        tk = child(box(f"{name}_m{i}", -0.002, 0.002, -0.004, 0.0, 0.026, 0.033, M["dark"]), root, (0, -0.036, 0.005))
        tk.rotation_euler = (0, i * math.pi / 4, 0)
    pont = child(empty(name + "_ponteiro"), root, (0, -0.04, 0.005))
    child(box(name + "_pont", -0.004, 0.004, -0.003, 0.0, -0.004, 0.03, M["red"]), pont)
    child(cyl(name + "_led", 0.006, 0, 0.004, (0, 0), M["yellow"], seg=8), root, (0.03, -0.03, -0.05)).rotation_euler = (math.pi / 2, 0, 0)
    return root, pont


def porta(name, M, largura=0.7, altura=2.1, cor="door", esp=0.14):
    """Porta para o vão de uma parede (largura x altura), no plano x-z: o batente reveste o vão por dentro
    (espessura `esp` em y) e a folha gira em z pela dobradiça em x = 0,05. Origem no chão, no canto do vão.
    Retorna (raiz, folha): folha.rotation_euler.z < 0 abre para -y."""
    root = empty(name)
    b = 0.05
    child(box(name + "_bat_e", 0.0, b, -esp / 2, esp / 2, 0, altura, M["frame"]), root)
    child(box(name + "_bat_d", largura - b, largura, -esp / 2, esp / 2, 0, altura, M["frame"]), root)
    child(box(name + "_bat_s", 0.0, largura, -esp / 2, esp / 2, altura - b, altura, M["frame"]), root)
    folha = child(empty(name + "_folha"), root, (b, 0, 0))
    lf = largura - 2 * b
    child(caixa_arred(name + "_placa", 0.003, lf - 0.003, -0.02, 0.02, 0.005, altura - b - 0.003, M[cor], r=0.01), folha)
    for s in (-1, 1):
        child(esfera(f"{name}_mac{s}", 0.028, (lf - 0.08, s * 0.06, 1.0), M["chrome"], seg=12), folha)
        child(tube(f"{name}_mac_h{s}", (lf - 0.08, s * 0.02, 1.0), (lf - 0.08, s * 0.06, 1.0), 0.009, M["chrome"]), folha)
    return root, folha


def plafon(name, M, raio=0.17):
    """Luminária de teto redonda, origem no teto (corpo para -z). Material próprio (anime a emissão para
    ligar/desligar: mt.key_input(o.data.materials[0], 'Emission Strength', t, v))."""
    m = mat(name + "_luz", "#fff6dc", rough=0.4, emit=2.5)
    o = esfera(name, raio, (0, 0, 0), m, scale=(1, 1, 0.22))
    return o


def toalha(name, M, cor="towel", largura=0.32, altura=0.5):
    """Toalha pendurada num suporte (dobrada sobre a barra), de frente para -y. Origem na barra."""
    root = empty(name)
    child(tube(name + "_barra", (-largura / 2 - 0.05, 0, 0), (largura / 2 + 0.05, 0, 0), 0.01, M["chrome"]), root)
    child(caixa_arred(name + "_frente", -largura / 2, largura / 2, -0.03, -0.01, -altura, 0.02, M[cor], r=0.012), root)
    child(caixa_arred(name + "_tras", -largura / 2, largura / 2, 0.005, 0.025, -altura * 0.7, 0.02, M[cor], r=0.012), root)
    return root


def frascos_shampoo(name, M, n=3, seed=6):
    """Frascos coloridos de xampu/sabonete lado a lado ao longo de x. Origem na base do primeiro."""
    rr = random.Random(seed)
    root = empty(name)
    x = 0.0
    for i in range(n):
        h = rr.uniform(0.14, 0.22)
        r = rr.uniform(0.028, 0.04)
        cor = ("bottle_a", "bottle_b", "bottle_c")[i % 3]
        child(caixa_arred(f"{name}_{i}", x - r, x + r, -r * 0.8, r * 0.8, 0, h, M[cor], r=0.012), root)
        child(cyl(f"{name}_t{i}", r * 0.45, h, h + 0.03, (x, 0), M["white"], seg=10), root)
        x += r * 2 + 0.015
    return root


def touca(P, M, cor="cap_pink"):
    """Touca de banho na cabeça do personagem() (cobre o cabelo)."""
    s = P["cabeca"].location.z
    R = 0.27 * s
    o = esfera(P["raiz"].name + "_touca", R * 1.12, (0, 0.075 * s, R * 0.95 + 0.09 * s), M[cor], scale=(1.02, 1.0, 0.88))
    return child(o, P["cabeca"])


def toalha_ombro(P, M, cor="towel"):
    """Toalha dobrada no ombro esquerdo do personagem() (pendurada na frente e atrás)."""
    s = P["cabeca"].location.z
    nome = P["raiz"].name + "_toalha"
    root = child(empty(nome), P["raiz"], (-0.17 * s, 0, 0.98 * s))
    child(caixa_arred(nome + "_cima", -0.06 * s, 0.06 * s, -0.13 * s, 0.13 * s, -0.015 * s, 0.02 * s, M[cor], r=0.012), root)
    for sy in (-1, 1):
        child(caixa_arred(f"{nome}_{sy}", -0.06 * s, 0.06 * s, -0.02 * s, 0.02 * s, -0.3 * s, 0.0, M[cor], r=0.012), root,
              (0, sy * 0.13 * s, 0.005 * s))
    return root


def turbante(P, M, cor="towel"):
    """Toalha enrolada na cabeça (turbante) do personagem()."""
    s = P["cabeca"].location.z
    R = 0.27 * s
    o = esfera(P["raiz"].name + "_turbante", R * 1.0, (0, 0.06 * s, R * 0.95 + 0.17 * s), M[cor], scale=(1.0, 1.0, 1.05))
    child(o, P["cabeca"])
    child(esfera(P["raiz"].name + "_turb_no", R * 0.35, (0, -0.1 * s, R * 0.95 + 0.38 * s), M[cor]), P["cabeca"])
    return o


def mancha_agua(name, M, centro, raio, cores=("stain_b", "stain_y"), achatado=0.04):
    """Mancha de infiltração no teto (normal -z): disco amarelado com borda marrom. Origem no centro.
    Retorna a raiz (anime com grow/pop_in)."""
    root = empty(name, centro)
    child(esfera(name + "_borda", raio, (0, 0, 0), M[cores[0]], scale=(1.0, 0.85, achatado), seg=24), root)
    child(esfera(name + "_meio", raio * 0.86, (0, 0, -0.002), M[cores[1]], scale=(1.0, 0.85, achatado), seg=24), root)
    return root


def vapor(name, M, n, fonte, area, teto, t0, t1, mat_nome="steam", r=(0.07, 0.15), subida=(1.0, 1.7), seed=4,
          espalha=0.18, nascer=0.6, saida=None, fim=None):
    """Vapor que sobe da `fonte` (x, y, z), bate no `teto` (altura z) e se espalha em `area` = (x0, x1, y0, y1),
    ficando ali rodando devagar. As nuvens nascem entre t0 e t0 + nascer·(t1 − t0); até t1 elas sobem e espalham.
    fim: tempo em que somem (padrão: t1 + 0,6). saida = ((x, y, z), t): a partir de t cada nuvem vai até o ponto
    (exaustor/janela) e some. Retorna as nuvens [(objeto, raio)]."""
    rr = random.Random(seed)
    fim = t1 + 0.6 if fim is None else fim
    out = []
    fx, fy, fz = fonte
    for i in range(n):
        rad = rr.uniform(*r)
        o = esfera(f"{name}{i}", 1.0, (fx, fy, fz), M[mat_nome], seg=12)
        ts = t0 + (t1 - t0) * nascer * (i / max(1, n - 1)) * rr.uniform(0.85, 1.0)
        tu = ts + rr.uniform(*subida)
        tsp = tu + rr.uniform(0.8, 1.5)
        zt = teto - rad * 0.55
        tx, ty = rr.uniform(area[0], area[1]), rr.uniform(area[2], area[3])
        p0 = Vector((fx + rr.uniform(-espalha, espalha), fy + rr.uniform(-espalha, espalha), fz))
        p1 = Vector((p0.x * 0.65 + tx * 0.35, p0.y * 0.65 + ty * 0.35, zt))
        p2 = Vector((tx, ty, zt))
        o.scale = (0, 0, 0)
        o.keyframe_insert("scale", frame=max(1, mt.F(ts) - 1))
        ks(o, ts + 0.2, rad * 0.4)
        ks(o, tu, rad)
        ks(o, tsp, rad * 1.25)
        k(o, "location", ts, p0)
        k(o, "location", tu, p1)
        k(o, "location", tsp, p2)
        t_out = fim
        if saida:
            t_out = min(fim, saida[1] + rr.uniform(0.0, 1.6))
        t = tsp
        p = p2
        while t + 1.4 < t_out:                          # deriva lenta embaixo do teto
            t += rr.uniform(1.1, 1.6)
            p = Vector((p.x + rr.uniform(-0.12, 0.12), p.y + rr.uniform(-0.1, 0.1), zt + rr.uniform(-0.04, 0.0)))
            k(o, "location", t, p)
        if saida and t_out < fim:
            dest = Vector(saida[0]) + Vector((rr.uniform(-0.05, 0.05), rr.uniform(-0.05, 0.05), rr.uniform(-0.05, 0.05)))
            k(o, "location", max(t_out, t + 0.05), p)
            dur = rr.uniform(0.7, 1.2)
            k(o, "location", max(t_out, t + 0.05) + dur, dest)
            ks(o, max(t_out, t + 0.05), rad * 1.25)
            ks(o, max(t_out, t + 0.05) + dur, 0.0)
        else:
            ks(o, max(t_out, tsp + 0.05), rad * 1.25)
            ks(o, max(t_out, tsp + 0.05) + 0.5, 0.0)
        out.append((o, rad))
    return out

# ================================================================ reparo de parede (trinca) e sala
OBRA = {"blade": "#c9ced4", "grip": "#e8742a", "putty": "#dedad0", "putty_pot": "#f4f1ea", "putty_label": "#2f6fd2",
        "cement_bag": "#d9c9a0", "cement_label": "#c0392b", "cement": "#a7a7a2", "sealant": "#fbfbf6",
        "cartridge": "#eceae4", "cartridge_label": "#3f9b5a", "mesh_w": "#ffffff", "helmet": "#f5b700",
        "vest": "#ff7a1c", "sofa": "#4f7f8f", "sofa_cushion": "#6aa0b0", "door_wood": "#c58a52",
        "door_frame": "#8a5a35", "knob": "#d8a93a", "board": "#c9935f", "dust": "#cfc6b4"}
ROUGH_OBRA = {"blade": 0.3, "sealant": 0.35, "helmet": 0.4, "knob": 0.3}
ALPHA_OBRA = {"dust": 0.85}


def materiais_obra(M):
    materiais_decor(M)
    for n, c in OBRA.items():
        if n not in M:
            M[n] = mat(n, c, rough=ROUGH_OBRA.get(n, 0.7), alpha=ALPHA_OBRA.get(n, 1.0))
    return M


def espatula(name, M):
    """Espátula de massa. Origem na ponta da lâmina; lâmina larga em y, cabo descendo em -z (como rolo_pintura)."""
    root = empty(name)
    child(box(name + "_lamina", -0.003, 0.003, -0.06, 0.06, -0.1, 0.0, M["blade"]), root)
    child(caixa_arred(name + "_cabo", -0.016, 0.016, -0.022, 0.022, -0.3, -0.1, M["grip"], r=0.012), root)
    return root


def bisnaga(name, M):
    """Bisnaga de selante (cartucho) com bico. Origem na ponta do bico; corpo descendo em -z."""
    root = empty(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.016, radius2=0.004, depth=0.08,
                          matrix=Matrix.Translation((0, 0, -0.04)))
    child(_liso(mesh_obj(name + "_bico", bm, M["cartridge"])), root)
    child(cyl(name + "_corpo", 0.03, -0.33, -0.08, (0, 0), M["cartridge"], seg=16), root)
    child(cyl(name + "_rotulo", 0.031, -0.27, -0.14, (0, 0), M["cartridge_label"], seg=16), root)
    child(tube(name + "_haste", (0, 0, -0.33), (0, 0, -0.42), 0.006, M["steel"], seg=6), root)
    return root


def pote_massa(name, M):
    """Pote de massa corrida (balde baixo com tampa e rótulo). Origem na base."""
    root = empty(name)
    child(cyl(name + "_corpo", 0.15, 0, 0.2, (0, 0), M["putty_pot"], seg=18), root)
    child(cyl(name + "_rotulo", 0.152, 0.05, 0.15, (0, 0), M["putty_label"], seg=18), root)
    child(cyl(name + "_tampa", 0.158, 0.2, 0.225, (0, 0), M["putty_label"], seg=18), root)
    return root


def saco_cimento(name, M):
    """Saco de cimento deitado-em-pé (caixa arredondada com faixa). Origem na base."""
    root = empty(name)
    child(caixa_arred(name + "_saco", -0.2, 0.2, -0.09, 0.09, 0, 0.5, M["cement_bag"], r=0.05), root)
    child(box(name + "_faixa", -0.17, 0.17, -0.095, 0.095, 0.24, 0.34, M["cement_label"]), root)
    return root


def tela_poliester(name, M, comprimento=1.2, largura=0.18, passo=0.03, r=0.0035):
    """Tela de reforço (malha) no plano y-z, de frente para +x. Origem na base, no meio da largura;
    cresce para cima (grow em z)."""
    bm = bmesh.new()

    def fio(a, b):
        a, b = Vector(a), Vector(b)
        d = b - a
        bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=r, radius2=r, depth=d.length,
                              matrix=Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4())
    ny = max(2, int(round(largura / passo)) + 1)
    for i in range(ny):
        y = -largura / 2 + largura * i / (ny - 1)
        fio((0, y, 0), (0, y, comprimento))
    nz = max(2, int(round(comprimento / passo)) + 1)
    for j in range(nz):
        z = comprimento * j / (nz - 1)
        fio((0, -largura / 2, z), (0, largura / 2, z))
    return mesh_obj(name, bm, M["mesh_w"])


def capacete(P, M, cor="helmet"):
    """Capacete de obra na cabeça de um personagem() (filho da cabeça). Retorna o objeto."""
    R = 0.27
    c = Vector((0, 0, R * 0.95))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=R * 1.12)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.001], context="VERTS")
    cap = _liso(mesh_obj(P["raiz"].name + "_capacete", bm, M[cor]))
    child(cap, P["cabeca"], tuple(c + Vector((0, 0.01, 0.06))))
    aba = child(cyl(P["raiz"].name + "_aba", R * 1.25, 0.0, 0.025, (0, 0), M[cor], seg=24), P["cabeca"],
                tuple(c + Vector((0, -0.04, 0.05))))
    aba.scale = (1.0, 1.12, 1.0)
    return cap


def porta_sala(name, M, largura=0.9, altura=2.1, espessura=0.04):
    """Porta no plano x-z (parede ao longo de x), batente incluído. Origem no chão, no lado da dobradiça (x = 0).
    Retorna (raiz, folha): gire folha.rotation_euler.z para abrir."""
    root = empty(name)
    for nm, a in [("_bat_e", (-0.07, 0.0, 0.0, altura)), ("_bat_d", (largura, largura + 0.07, 0.0, altura)),
                  ("_bat_s", (-0.07, largura + 0.07, altura, altura + 0.07))]:
        child(box(name + nm, a[0], a[1], -0.12, 0.12, a[2], a[3], M["door_frame"]), root)
    folha = child(empty(name + "_folha"), root)
    child(box(name + "_painel", 0.0, largura, -espessura / 2, espessura / 2, 0.0, altura, M["door_wood"]), folha)
    for j, (z0, z1) in enumerate(((0.25, 0.95), (1.15, 1.85))):
        child(box(f"{name}_alm{j}", 0.12, largura - 0.12, -espessura / 2 - 0.008, -espessura / 2, z0, z1,
                  M["door_frame"]), folha)
    child(esfera(name + "_macaneta", 0.035, (largura - 0.1, -espessura / 2 - 0.035, 1.0), M["knob"]), folha)
    return root, folha


def sofa(name, M, comprimento=1.9, profundidade=0.85):
    """Sofá de 3 lugares ao longo de x, encosto em +y, de frente para -y. Origem no chão, no meio da frente."""
    root = empty(name)
    L = comprimento / 2
    child(caixa_arred(name + "_base", -L, L, 0.0, profundidade, 0.08, 0.42, M["sofa"], r=0.05), root)
    child(caixa_arred(name + "_encosto", -L, L, profundidade - 0.22, profundidade, 0.42, 0.9, M["sofa"], r=0.07), root)
    for lado in (-1, 1):
        x0 = L - 0.16 if lado > 0 else -L
        child(caixa_arred(f"{name}_braco{lado}", x0, x0 + 0.16, 0.0, profundidade, 0.42, 0.66, M["sofa"], r=0.06), root)
    n = 3
    w = (comprimento - 0.32) / n
    for i in range(n):
        x0 = -L + 0.16 + i * w
        child(caixa_arred(f"{name}_ass{i}", x0 + 0.01, x0 + w - 0.01, 0.04, profundidade - 0.2, 0.42, 0.55,
                          M["sofa_cushion"], r=0.05), root)
    for i, x in enumerate((-0.45, 0.45)):
        a = child(caixa_arred(f"{name}_alm{i}", x - 0.2, x + 0.2, profundidade - 0.36, profundidade - 0.2, 0.55, 0.92,
                              M["sofa_cushion"], r=0.06), root)
        a.rotation_euler = (math.radians(-12), 0, 0)
    for sx in (-L + 0.08, L - 0.08):
        for sy in (0.08, profundidade - 0.08):
            child(cyl(f"{name}_pe{sx:.1f}{sy:.1f}", 0.03, 0.0, 0.08, (sx, sy), M["dark"], seg=8), root)
    return root


# ================================================================ cozinha 2 e encanamento (vídeo do óleo na pia)
COZINHA2 = {"pvc": "#f1efe9", "pan": "#2e3036", "pan_handle": "#1b1b1e", "oil": "#f5b21c", "grease": "#c9a55a",
            "pet": "#bfe3f2", "pet_cap": "#2f7fd8", "funnel": "#f07c1f", "kettle": "#d94f3d", "trash": "#5c6670",
            "steam": "#ffffff", "stink": "#8fb04a", "dirty": "#7b6a3e", "towel": "#fbfaf4", "soap": "#8fd18a",
            "jerry": "#3f9b46", "fish": "#ff8a3d", "cooktop": "#1c1d21", "burner": "#4a4c52", "bin_green": "#2f8f4e"}
EMIT_C2 = {"oil": 0.35, "steam": 0.4, "stink": 0.3}
ALPHA_C2 = {"pet": 0.45, "steam": 0.55, "stink": 0.7}
ROUGH_C2 = {"oil": 0.15, "pan": 0.45, "pet": 0.1, "kettle": 0.35, "pvc": 0.55}


def materiais_cozinha2(M):
    materiais_cozinha(M)
    for n, c in COZINHA2.items():
        if n not in M:
            M[n] = mat(n, c, rough=ROUGH_C2.get(n, 0.7), emit=EMIT_C2.get(n, 0.0), alpha=ALPHA_C2.get(n, 1.0))
    return M


def _percurso(pts):
    """Polilinha no plano x-z -> (pontos, tangentes, normais de esquadro, escala de esquadro, comprimentos)."""
    P = [Vector((x, z)) for x, z in pts]
    n = len(P)
    T, N, S, L = [], [], [], [0.0]
    for i in range(n):
        a = (P[i] - P[i - 1]).normalized() if i > 0 else None
        b = (P[i + 1] - P[i]).normalized() if i < n - 1 else None
        t = (a + b).normalized() if a is not None and b is not None else (a if b is None else b)
        nn = Vector((-t.y, t.x))
        ref = Vector((-(a or b).y, (a or b).x))
        T.append(t); N.append(nn); S.append(1.0 / max(0.3, nn.dot(ref)))
        if i:
            L.append(L[-1] + (P[i] - P[i - 1]).length)
    return P, T, N, S, L


def _cano_coords(pts, r_out, r_in, y=0.0, frente=False, seg=12):
    """Vértices (em ordem fixa) de um cano em corte longitudinal varrido pela polilinha (x, z).
    Metade de trás (y >= 0) ou da frente. Ordem: para cada ponto, anel externo (seg+1) e interno (seg+1)."""
    P, T, N, S, _ = _percurso(pts)
    th = [(math.pi * j / seg) + (math.pi if frente else 0.0) for j in range(seg + 1)]
    out = []
    for p, nn, s in zip(P, N, S):
        for r in (r_out, r_in):
            for a in th:
                c, sn = r * math.cos(a) * s, r * math.sin(a)
                out.append((p.x + nn.x * c, y + sn, p.y + nn.y * c))
    return out


def cano_corte(name, m, pts, r_out, r_in, y=0.0, frente=False, seg=12):
    """Cano em corte longitudinal ao longo da polilinha `pts` (x, z) no plano y: só a metade de trás (frente=False)
    — vê-se o lado de dentro — ou a da frente (tampa o cano até o raio-x). Use a mesma função com r_out/r_in
    diferentes para camadas internas (gordura, crosta) e anime com camada_shape()."""
    co = _cano_coords(pts, r_out, r_in, y, frente, seg)
    k1 = seg + 1
    faces = []
    for i in range(len(pts) - 1):
        a, b = i * 2 * k1, (i + 1) * 2 * k1
        for j in range(seg):
            faces.append((a + j, a + j + 1, b + j + 1, b + j))                       # externo
            faces.append((a + k1 + j, b + k1 + j, b + k1 + j + 1, a + k1 + j + 1))  # interno
        for j in (0, seg):                                                          # faces do corte
            faces.append((a + j, b + j, b + k1 + j, a + k1 + j))
    for i in (0, len(pts) - 1):                                                     # bordas das pontas
        a = i * 2 * k1
        for j in range(seg):
            faces.append((a + j, a + k1 + j, a + k1 + j + 1, a + j + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(co, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    me.materials.append(m)
    mt.link(o)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return o


def camada_cano(name, m, pts, r_out, r_fino, r_grosso, y=0.0, seg=12):
    """Camada dentro do cano (gordura): chave de forma 'grossa' fecha o cano de r_fino até r_grosso.
    Anime com mt.shape(o, 'grossa', t, valor)."""
    o = cano_corte(name, m, pts, r_out, r_fino, y, False, seg)
    o.shape_key_add(name="Basis")
    kg = o.shape_key_add(name="grossa", from_mix=False)
    for i, c in enumerate(_cano_coords(pts, r_out, r_grosso, y, False, seg)):
        kg.data[i].co = c
    return o


def ponto_no_cano(pts, f):
    """Ponto (x, z), tangente e normal a uma fração f (0..1) do comprimento da polilinha."""
    P, T, N, S, L = _percurso(pts)
    s = f * L[-1]
    for i in range(len(P) - 1):
        if L[i + 1] >= s:
            u = (s - L[i]) / max(1e-9, L[i + 1] - L[i])
            t = (P[i + 1] - P[i]).normalized()
            return P[i].lerp(P[i + 1], u), t, Vector((-t.y, t.x))
    t = (P[-1] - P[-2]).normalized()
    return P[-1], t, Vector((-t.y, t.x))


def frigideira(name, M, raio=0.12, cabo_len=0.2, oleo="oil"):
    """Frigideira com o pivô na ponta do cabo; o cabo sai em +x até a panela (centro em x = cabo_len + raio).
    Gire com rotation_euler = (0, inclinação, direção). Retorna (raiz, disco_de_óleo)."""
    root = empty(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=raio * 0.82, radius2=raio, depth=0.05,
                          matrix=Matrix.Translation((cabo_len + raio, 0, 0.025)))
    o = child(mesh_obj(name + "_corpo", bm, M["pan"]), root)
    o.modifiers.new("esp", "SOLIDIFY").thickness = 0.008
    _liso(o)
    child(cyl(name + "_fundo", raio * 0.82, 0, 0.008, (cabo_len + raio, 0), M["pan"], seg=24), root)
    cb = child(tube(name + "_cabo", (0, 0, 0), (cabo_len + 0.02, 0, 0), 0.013, M["pan_handle"], seg=8), root)
    cb.location = (0, 0, 0.035)
    disco = child(cyl(name + "_oleo", raio * 0.84, 0.0, 0.01, (0, 0), M[oleo], seg=24), root, (cabo_len + raio, 0, 0.008))
    return root, disco


def cooktop(name, M, largura=0.55, prof=0.45):
    """Cooktop de 2 bocas (vidro preto). Origem no centro, em cima da bancada."""
    root = empty(name)
    child(caixa_arred(name + "_vidro", -largura / 2, largura / 2, -prof / 2, prof / 2, 0, 0.012, M["cooktop"], r=0.004), root)
    for i, x in enumerate((-largura / 4, largura / 4)):
        child(cyl(f"{name}_boca{i}", 0.09, 0.012, 0.016, (x, 0), M["burner"], seg=20), root)
    return root


def garrafa_pet(name, M, altura=0.24, raio=0.045, liquido=None):
    """Garrafa PET transparente com tampinha. Origem na base. Retorna (raiz, tampa, líquido|None):
    o líquido (cilindro com origem na base) enche com grow(..., 'z')."""
    root = empty(name)
    corpo = child(capsula(name + "_corpo", raio, altura * 0.62, M["pet"]), root, (0, 0, altura * 0.7))
    corpo.scale = (1, 1, 1)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=raio, radius2=raio * 0.35, depth=altura * 0.18,
                          matrix=Matrix.Translation((0, 0, altura * 0.79)))
    child(_liso(mesh_obj(name + "_ombro", bm, M["pet"])), root)
    tampa = child(cyl(name + "_tampa", raio * 0.38, altura * 0.88, altura * 0.94, (0, 0), M["pet_cap"], seg=12), root)
    liq = None
    if liquido:
        liq = child(cyl(name + "_liq", raio * 0.9, 0, altura * 0.68, (0, 0), M[liquido], seg=16), root, (0, 0, 0.012))
    return root, tampa, liq


def funil(name, M, raio=0.06, altura=0.09):
    """Funil (boca para cima). Origem na ponta de baixo."""
    root = empty(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=raio * 0.2, radius2=raio, depth=altura * 0.6,
                          matrix=Matrix.Translation((0, 0, altura * 0.4 + altura * 0.3)))
    o = child(_liso(mesh_obj(name + "_cone", bm, M["funnel"])), root)
    o.modifiers.new("esp", "SOLIDIFY").thickness = 0.004
    child(cyl(name + "_bico", raio * 0.18, 0, altura * 0.42, (0, 0), M["funnel"], seg=10), root)
    return root


def chaleira(name, M):
    """Chaleira com o pivô na alça (em cima); o bico aponta para +x. Retorna (raiz, ponta_do_bico_local)."""
    root = empty(name)
    child(esfera(name + "_corpo", 0.11, (0, 0, -0.16), M["kettle"], scale=(1, 1, 0.85)), root)
    child(cyl(name + "_tampa", 0.04, -0.08, -0.06, (0, 0), M["steel"], seg=12), root)
    for a, b in (((-0.08, 0, -0.1), (-0.05, 0, 0)), ((-0.05, 0, 0), (0.05, 0, 0)), ((0.05, 0, 0), (0.08, 0, -0.1))):
        child(tube(name + "_alca", a, b, 0.012, M["pan_handle"], seg=6), root)
    child(tube(name + "_bico", (0.08, 0, -0.2), (0.2, 0, -0.1), 0.016, M["kettle"], seg=8), root)
    return root, Vector((0.2, 0, -0.1))


def lixeira(name, M, cor="trash"):
    """Lixeira com tampa articulada (gire a dobradiça em x negativo para abrir). Retorna (raiz, dobradiça)."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.14, 0.14, -0.12, 0.12, 0, 0.4, M[cor], r=0.02), root)
    dob = child(empty(name + "_dob"), root, (0, 0.12, 0.4))
    child(caixa_arred(name + "_tampa", -0.145, 0.145, -0.245, 0.005, 0, 0.025, M[cor], r=0.01), dob)
    child(box(name + "_pedal", -0.05, 0.05, -0.16, -0.12, 0.0, 0.02, M["steel"]), root)
    return root, dob


def peixe(name, M, cor="fish", tamanho=0.3):
    """Peixe ao longo de +x (nariz em +x). Origem no centro."""
    root = empty(name)
    child(esfera(name + "_corpo", tamanho / 2, (0, 0, 0), M[cor], scale=(1, 0.38, 0.6)), root)
    c = child(cone(name + "_rabo", tamanho * 0.22, tamanho * 0.3, M[cor], seg=4), root, (-tamanho * 0.42, 0, 0))
    c.rotation_euler = (0, -math.pi / 2, 0)
    c.scale = (1, 0.3, 1)
    for s in (-1, 1):
        child(ball(f"{name}_olho{s}", tamanho * 0.05, (0, 0, 0), M["dark"]), root,
              (tamanho * 0.3, s * tamanho * 0.17, tamanho * 0.07))
    return root


def barra_sabao(name, M, cor="soap"):
    root = empty(name)
    child(caixa_arred(name + "_b", -0.09, 0.09, -0.05, 0.05, 0, 0.05, M[cor], r=0.018), root)
    return root


def galao(name, M, cor="jerry"):
    """Galão (biodiesel). Origem na base."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.12, 0.12, -0.07, 0.07, 0, 0.3, M[cor], r=0.03), root)
    child(cyl(name + "_bocal", 0.03, 0.3, 0.35, (0.07, 0), M["dark"], seg=10), root)
    child(caixa_arred(name + "_alca", -0.08, 0.02, -0.02, 0.02, 0.3, 0.35, M[cor], r=0.01), root)
    return root


def coletor_oleo(name, M, rotulo="ÓLEO", cor="bin_green"):
    """Coletor de óleo usado (caixa com boca e rótulo) de frente para -y. Origem na base."""
    root = empty(name)
    child(caixa_arred(name + "_corpo", -0.35, 0.35, -0.3, 0.3, 0, 1.0, M[cor], r=0.04), root)
    child(caixa_arred(name + "_tampa", -0.37, 0.37, -0.32, 0.32, 1.0, 1.08, M["yellow"], r=0.03), root)
    child(box(name + "_boca", -0.16, 0.16, -0.322, -0.3, 0.78, 0.86, M["dark"]), root)
    child(text(name + "_txt", rotulo, 0.17, (0, -0.31, 0.45), M["white"], extrude=0.008), root)
    child(esfera(name + "_gota", 0.07, (0, -0.31, 0.68), M["oil"], scale=(1, 0.3, 1)), root)
    child(cone(name + "_gpt", 0.062, 0.1, M["oil"], seg=12), root, (0, -0.31, 0.71)).scale = (1, 0.3, 1)
    return root
