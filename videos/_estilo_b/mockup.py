"""Prova de estilo da Direção B "Laboratório de bolso" (canal de hábitos) — 3 quadros + comparação com o concorrente.

Uso:  ~/.venv-video/bin/python videos/_estilo_b/mockup.py [1] [2] [3] [comp]   (sem argumentos = tudo)
Saídas nesta pasta: quadro1.png (gancho), quadro2.png (a lupa), quadro3.png (mundo micro), comparacao.jpg.
Tema de exemplo: condicionador deixado no cabelo durante o banho escorre pelas costas e entope os poros → espinhas.
"""
import sys, os, math, random, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "motor3d"))
import bpy, bmesh
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import motor as mt
import pecas as pc
import pecas_habitos as ph
from motor import mat, lin, empty, mesh_obj, box
from pecas import child, esfera, capsula

AMOSTRAS = 16
W, H = 576, 1024
TMP = os.path.join(HERE, "_tmp")
os.makedirs(TMP, exist_ok=True)
VIDEO_CONC = ("/tmp/claude-0/-home-user/75c06454-59ed-500a-b8e2-1fbbee500889/scratchpad/habitos/videos/"
              "7704458691008875797.mp4")
TEMPOS = {}


# ================================================================ utilidades de cena
def camera(pos, alvo, lens=35):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start = 0.01
    cam = mt.link(bpy.data.objects.new("cam", cd))
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    mt.scene.camera = cam
    return cam


def mundo(cor="#FFF4E0", forca=0.7):
    w = bpy.data.worlds.new("mundo")
    mt.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = lin(cor)
    bg.inputs["Strength"].default_value = forca
    if hasattr(w.cycles, "sampling_method"):
        w.cycles.sampling_method = "NONE"


def luz_sol(rot, energia=3.0, cor="#FFF6E8", angulo=8):
    d = bpy.data.lights.new("sol", "SUN")
    d.energy = energia
    d.color = lin(cor)[:3]
    d.angle = math.radians(angulo)
    o = mt.link(bpy.data.objects.new("sol", d))
    o.rotation_euler = [math.radians(a) for a in rot]
    return o


def luz_area(pos, alvo, energia=80, tam=1.5, cor="#FFFFFF"):
    d = bpy.data.lights.new("area", "AREA")
    d.energy = energia
    d.size = tam
    d.color = lin(cor)[:3]
    o = mt.link(bpy.data.objects.new("area", d))
    o.location = pos
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    return o


def render(nome, amostras=AMOSTRAS, res=(W, H)):
    sc = mt.scene
    sc.cycles.samples = amostras
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.filepath = os.path.join(TMP, nome)
    sc.frame_set(1)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    TEMPOS[nome] = dt
    print(f"render {nome}: {dt:.1f} s")
    return sc.render.filepath


def tela(cam, p):
    """Posição de um ponto do mundo na imagem (pixels, origem no canto de cima)."""
    v = world_to_camera_view(mt.scene, cam, Vector(p))
    rx, ry = mt.scene.render.resolution_x, mt.scene.render.resolution_y
    return v.x * rx, (1 - v.y) * ry


# ================================================================ personagem no banho
def materiais_cena(M):
    pc.materiais_banheiro(M)
    ph.materiais_habitos(M)
    for n, c, r in (("skin", "#F1B98F", 0.8), ("skin_dark", "#E3A07A", 0.8), ("hair_h", "#5B3A2A", 0.85),
                    ("toalha_h", "#F3E3C3", 0.95), ("blush", "#F59A8A", 0.9), ("chao_h", "#E9E1D2", 0.9),
                    ("prateleira", "#FFF4E0", 0.9), ("cond_trilha", "#FFFDF7", 0.5)):
        M[n] = ph.argila(n, c, rough=r)
    M["azulejo_h"] = pc.ladrilho_mat("azulejo_h", "#BFE9DA", "#B5E3D2", "#FFFFFF", tam=(0.2, 0.2), rough=0.8)
    M["piso_h"] = pc.ladrilho_mat("piso_h", "#F3E9D6", "#EADFCA", "#D2C4AC", tam=(0.3, 0.3), piso=True, rough=0.8)
    M["azulejo_lado"] = pc.ladrilho_mat("azulejo_lado", "#A9DFCB", "#A0D9C4", "#F4FFF9", tam=(0.2, 0.2), rough=0.8)
    return M


def costas_y(x, z, s=1.0, folga=0.004):
    """y da superfície das costas do tronco do personagem() (elipsoide), no espaço da raiz (costas = +y)."""
    cx, cz = 0.0, 0.74 * s
    a, b, c = 0.24 * s, 0.24 * 0.8 * s, 0.24 * 1.15 * s
    q = 1 - ((x - cx) / a) ** 2 - ((z - cz) / c) ** 2
    return b * math.sqrt(max(q, 0.0)) + folga


def personagem_banho(M, rnd):
    """Personagem de toalha (menta), cabelo comprido cheio de condicionador, trilhas brancas escorrendo nas costas."""
    P = pc.personagem("moca", M, camisa="skin", calca="skin", cabelo="hair_h", altura=1.0)
    raiz = P["raiz"]
    # toalha enrolada na cintura/quadril (deixa as costas à mostra)
    child(esfera("toalha_corpo", 0.25, (0, 0, 0.5), M["toalha_h"], scale=(1.02, 0.84, 1.05)), raiz)
    child(ph.toro("toalha_borda", 0.245, 0.02, M["toalha_h"], eixo="z"), raiz, (0, 0, 0.72)).scale = (1.0, 0.84, 1)
    # cabelo comprido caindo nas costas (preso ao corpo, não à cabeça)
    longo = child(esfera("cabelo_longo", 1.0, (0, 0.2, 1.12), M["hair_h"], scale=(0.16, 0.085, 0.19)), raiz)
    longo.rotation_euler = (math.radians(-8), 0, 0)
    # espuma de condicionador: coroa no alto da cabeça + bolhas pelo cabelo comprido
    cab = P["cabeca"]
    R = 0.27
    cc = Vector((0, 0.07, R * 0.95 + 0.07))
    for i in range(40):
        az = rnd.uniform(0, 2 * math.pi)
        el = rnd.uniform(0.15, 1.35)
        p = cc + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el) * 1.0 + 0.0, math.sin(el) * 0.9)) * R * 1.0
        if p.y < -0.05:          # não cobre o rosto
            p.y = -0.05 + (p.y + 0.05) * 0.2
        child(ph.bolha(f"espuma{i}", M, rnd.uniform(0.03, 0.055), tuple(p)), cab)
    for i in range(26):
        x = rnd.uniform(-0.14, 0.14)
        z = rnd.uniform(0.96, 1.25)
        q = 1 - (x / 0.16) ** 2 - ((z - 1.12) / 0.19) ** 2
        y = 0.2 + 0.085 * math.sqrt(max(q, 0.05))
        child(ph.bolha(f"espuma_l{i}", M, rnd.uniform(0.022, 0.04), (x, y, z)), raiz)
    # trilhas de condicionador escorrendo pelas costas (saem da ponta do cabelo)
    for i, (x0, comp) in enumerate(((-0.12, 0.2), (-0.06, 0.24), (0.0, 0.17), (0.06, 0.22), (0.12, 0.15),
                                     (-0.17, 0.12), (0.17, 0.13))):
        z0 = 0.96 + 1.2 * x0 * x0 / 0.17
        pts = []
        n = 10
        for j in range(n + 1):
            z = z0 - comp * j / n
            x = x0 + 0.01 * math.sin(j * 1.3 + i)
            pts.append(Vector((x, costas_y(x, z, folga=0.006), z)))
        for j in range(n):
            rr = 0.011 + 0.003 * math.sin(j + i)
            child(mt.tube(f"trilha{i}_{j}", tuple(pts[j]), tuple(pts[j + 1]), rr, M["cond_trilha"], seg=10), raiz)
            child(esfera(f"trilha{i}_n{j}", rr, tuple(pts[j]), M["cond_trilha"], seg=10), raiz)
        child(ph.bolha(f"gotinha{i}", M, 0.02, tuple(pts[-1] + Vector((0, 0.008, -0.01))), achata=1.2), raiz)
    return P


def banheiro(M):
    """Canto do box: parede do fundo (+y), parede da esquerda, piso, prateleira de canto e chuveiro."""
    objs = []
    box("parede_fundo", -1.6, 1.6, 0.9, 1.0, 0, 3.0, M["azulejo_h"])
    box("parede_esq", -1.7, -1.6, -2.0, 1.0, 0, 3.0, M["azulejo_lado"])
    box("piso", -1.7, 1.6, -3, 1.0, -0.05, 0, M["piso_h"])
    # prateleira de canto (à direita, na parede do fundo) com frasco amarelo e frascos
    prat = box("prateleira", 0.25, 0.95, 0.68, 0.9, 1.38, 1.42, M["prateleira"])
    objs.append(prat)
    fr = ph.frasco_condicionador("frasco", M, altura=0.22, raio=0.05)
    fr.location = (0.82, 0.8, 1.42)
    fr.rotation_euler = (0, 0, math.radians(-15))
    objs.append(fr)
    ch, _ = pc.chuveiro("chuveiro", M)
    ch.location = (-0.15, 0.9, 2.05)
    ch.scale = (1.2, 1.2, 1.2)
    # água caindo do chuveiro (traços curtos)
    rr = random.Random(3)
    for i in range(16):
        x, y = -0.15 + rr.uniform(-0.09, 0.09), 0.46 + rr.uniform(-0.08, 0.06)
        z = rr.uniform(1.6, 1.92)
        mt.tube(f"agua{i}", (x, y, z), (x - 0.004, y - 0.006, z - rr.uniform(0.05, 0.09)), 0.006, M["drop"], seg=6)
    return objs


# ================================================================ quadro 1: gancho
def quadro1():
    mt.setup(1, samples=AMOSTRAS)
    rnd = random.Random(4)
    M = materiais_cena({})
    mundo("#FFF8EE", 0.45)
    objs = banheiro(M)
    P = personagem_banho(M, rnd)
    P["raiz"].rotation_euler = (0, 0, math.radians(180 - 12))
    P["raiz"].location = (-0.18, 0.2, 0)
    P["cabeca"].rotation_euler = (math.radians(-6), 0, math.radians(-72))
    P["braco_e"].rotation_euler = (math.radians(-10), math.radians(18), 0)
    P["braco_d"].rotation_euler = (math.radians(-10), math.radians(-18), 0)
    pc.rosto_expr(P, 0, olhos="fechados", boca="sorriso")
    # Gota na prateleira, espiando com a lupa
    G = ph.gota("gota", M, R=0.11, pose="lupa", olhar=(-0.8, 0.0), sobrancelha=18)
    G["raiz"].location = (0.48, 0.76, 1.42)
    G["raiz"].rotation_euler = (0, 0, math.radians(-12))
    ph.contorno([P["raiz"], G["raiz"]] + objs, M, esp=0.006)
    luz_sol((52, 8, -30), energia=1.6)
    luz_area((-1.2, -1.8, 2.4), (0, 0.4, 1.1), energia=45, tam=2.0, cor="#FFF4E6")
    cam = camera((0.35, -2.5, 1.45), (0.1, 0.4, 1.02), lens=35)
    return render("q1_base.png")


# ================================================================ quadro 2: a lupa (cena macro + cena micro)
def quadro2_macro():
    mt.setup(1, samples=AMOSTRAS)
    rnd = random.Random(4)
    M = materiais_cena({})
    mundo("#FFF8EE", 0.45)
    objs = banheiro(M)
    P = personagem_banho(M, rnd)
    P["raiz"].rotation_euler = (0, 0, math.radians(180 - 6))
    P["raiz"].location = (-0.04, 0.25, 0)
    P["cabeca"].rotation_euler = (math.radians(-6), 0, math.radians(-30))
    G = ph.gota("gota", M, R=0.12, pose="lupa", olhar=(0.6, 0.45), sobrancelha=18, boca="aberta", lupa_raio=0.15,
                cabo=0.2)
    G["raiz"].rotation_euler = (0, 0, math.radians(-8))
    bpy.context.view_layer.update()
    alvo = Vector((0.125, -0.3, 1.0))          # onde o centro da lupa deve ficar (na frente das costas)
    G["raiz"].location = alvo - G["lupa"]["centro"].matrix_world.translation
    ph.contorno([P["raiz"], G["raiz"]] + objs, M, esp=0.003)
    luz_sol((52, 8, -30), energia=1.6)
    luz_area((-1.0, -1.6, 2.0), (0, 0.3, 0.9), energia=40, tam=2.0, cor="#FFF4E6")
    cam = camera((0.05, -1.5, 1.08), (0.04, 0.3, 0.86), lens=45)
    bpy.context.view_layer.update()
    L = G["lupa"]
    c = L["centro"].matrix_world.translation
    dirx = cam.matrix_world.to_quaternion() @ Vector((1, 0, 0))
    sc = L["centro"].matrix_world.to_scale()[0]
    p0 = tela(cam, c)
    p1 = tela(cam, c + dirx * L["raio_interno"] * sc)
    raio_px = math.dist(p0, p1)
    return render("q2_macro.png"), p0, raio_px


def mundo_micro(M, rnd, poros_n=22, area=(3.6, 2.6), seed=3, espinha_em=None, bolhas_frac=0.75, extra=()):
    """Terreno de pele com poros e bolhas de condicionador encaixadas. Retorna (terreno, altura, poros)."""
    poros = list(extra)
    tent = 0
    while len(poros) < poros_n and tent < 2000:
        tent += 1
        p = (rnd.uniform(-area[0] / 2 + 0.2, area[0] / 2 - 0.2), rnd.uniform(-area[1] / 2 + 0.2, area[1] / 2 - 0.1))
        if espinha_em and math.dist(p, espinha_em) < 0.55:
            continue
        if all(math.dist(p, q[:2]) > 0.42 for q in poros):
            poros.append((p[0], p[1], rnd.uniform(0.09, 0.12), 0.08))
    terr, h = ph.terreno_pele("pele", M, tam=(area[0] + 1.8, 5.4), n=(170, 190), poros=poros, amp=0.06,
                              seed=seed, cor="#F4C9A6", cor_poro="#C27A5E", cor_vale="#EAB590")
    bol = []
    for i, (x, y, r, d) in enumerate(poros):
        if i < len(extra) or rnd.random() < bolhas_frac:
            rb = r * rnd.uniform(1.05, 1.5)
            bol.append(ph.bolha(f"bolha{i}", M, rb, (x, y, h(x, y) - d * 0.3 + rb * 0.95), achata=0.95))
    return terr, h, poros, bol


# ---------------------------------------------------------------- vista micro dentro da lupa
def quadro2_micro():
    mt.setup(1, samples=AMOSTRAS)
    rnd = random.Random(21)
    M = {}
    ph.materiais_habitos(M)
    mundo("#F4F7F6", 0.5)
    terr, h, poros, bol = mundo_micro(M, rnd, poros_n=26, area=(3.2, 2.4), seed=5, bolhas_frac=0.85)
    ph.palco_micro("palco", M, largura=14, altura=8, y=1.4, z0=-1.0, passo=0.22)
    ph.contorno(bol, M, esp=0.008)
    luz_sol((40, 10, -25), energia=2.6)
    camera((0.05, -0.62, 0.5), (0.05, 0.3, 0.02), lens=30)
    return render("q2_micro.png", res=(W, W))


# ================================================================ quadro 3: mundo micro
def quadro3():
    mt.setup(1, samples=AMOSTRAS)
    rnd = random.Random(8)
    M = {}
    ph.materiais_habitos(M)
    mundo("#F4F7F6", 0.5)
    ESP = (-0.3, 0.15)
    terr, h, poros, bol = mundo_micro(M, rnd, poros_n=24, area=(3.6, 2.6), seed=3, espinha_em=ESP, bolhas_frac=0.8,
                                      extra=[(-0.45, -0.95, 0.12, 0.08), (0.85, -1.05, 0.11, 0.08)])
    ph.palco_micro("palco", M, largura=14, altura=8, y=1.55, z0=-1.0, passo=0.2)
    esp = ph.espinha("espinha", M, 0.3, (ESP[0], ESP[1], h(*ESP) - 0.02))
    G = ph.gota("gota", M, R=0.19, pose="aponta", olhar=(-0.75, 0.2), sobrancelha=16, boca="aberta")
    gx, gy = 0.16, -0.5
    G["raiz"].location = (gx, gy, h(gx, gy) + 0.015)
    G["raiz"].rotation_euler = (0, 0, math.radians(-28))
    # tira bolhas que atravessam a Gota
    fora = [o for o in bol if math.dist(o.location[:2], (gx, gy)) < 0.45]
    bol = [o for o in bol if o not in fora]
    for o in fora:
        for c in list(o.children):
            bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.objects.remove(o, do_unlink=True)
    ph.contorno([G["raiz"], esp] + bol, M, esp=0.009)
    luz_sol((50, 12, -28), energia=2.2)
    luz_area((-1.5, -2.0, 1.6), (0, 0, 0.3), energia=50, tam=2.0, cor="#FFF4E6")
    camera((0.05, -2.05, 1.12), (0.0, 0.1, 0.02), lens=33)
    return render("q3_base.png")


# ================================================================ gráficos 2D (pós em PIL)
FONTE = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FONTE_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
TINTA, CREME = "#1B2B2A", "#FFF4E0"
FAIXA = {"problema": "#FF6B5A", "solucao": "#FFC928", "tempo": "#0E3B3A", "objecao": "#9AA3A2"}


def fonte(px, f=FONTE):
    return ImageFont.truetype(f, px)


def icone_alerta(tam):
    im = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = tam * 0.06
    tri = [(tam / 2, m), (tam - m, tam - m * 1.4), (m, tam - m * 1.4)]
    d.polygon([(x + 3, y + 4) for x, y in tri], fill=(0, 0, 0, 80))
    d.polygon(tri, fill="#FFC928", outline=TINTA)
    d.line(tri + [tri[0]], fill=TINTA, width=max(3, tam // 16), joint="curve")
    f = fonte(int(tam * 0.55))
    d.text((tam / 2, tam * 0.62), "!", font=f, fill=TINTA, anchor="mm")
    return im


def etiqueta(texto, tipo, Wimg, icone=False):
    """Etiqueta de frasco: retângulo creme com canto cortado, faixa colorida à esquerda, texto escuro bold."""
    f = fonte(int(Wimg * 0.064))
    x0, y0, x1, y1 = f.getbbox(texto)
    tw, th = x1 - x0, y1 - y0
    faixa = int(Wimg * 0.04)
    pw, ph_ = int(Wimg * 0.035), int(Wimg * 0.028)
    ic = int(th * 1.5) if icone else 0
    w = faixa + pw + (ic + pw // 2 if icone else 0) + tw + pw
    h = th + 2 * ph_
    corte = int(h * 0.32)
    lw = max(3, Wimg // 160)
    im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    poly = [(0, 0), (w - corte, 0), (w, corte), (w, h), (corte * 0.6, h), (0, h - corte * 0.6)]
    ox, oy = 6, 6
    d.polygon([(x + ox + 5, y + oy + 6) for x, y in poly], fill=(0, 0, 0, 70))
    d.polygon([(x + ox, y + oy) for x, y in poly], fill=CREME)
    # faixa colorida
    d.polygon([(ox, oy), (ox + faixa, oy), (ox + faixa, oy + h), (ox + corte * 0.6, oy + h), (ox, oy + h - corte * 0.6)],
              fill=FAIXA[tipo])
    # pontilhado de 'lote' na faixa
    for k in range(3):
        cy = oy + h * (0.3 + 0.2 * k)
        d.ellipse([ox + faixa / 2 - 3, cy - 3, ox + faixa / 2 + 3, cy + 3], fill=CREME)
    d.line([(x + ox, y + oy) for x, y in poly + [poly[0]]], fill=TINTA, width=lw, joint="curve")
    tx = ox + faixa + pw
    if icone:
        a = icone_alerta(ic)
        im.alpha_composite(a, (int(tx), int(oy + h / 2 - ic / 2)))
        tx += ic + pw // 2
    d.text((tx - x0, oy + ph_ - y0), texto, font=f, fill=TINTA)
    return im


def cartao_gancho(texto, Wimg, cabec="TESTE Nº 01  ·  HÁBITOS"):
    """Placa de laboratório: cartão creme inclinado, cabeçalho petróleo com 'TESTE Nº', clipe amarelo."""
    f = fonte(int(Wimg * 0.097))
    fc = fonte(int(Wimg * 0.034), FONTE_B)
    x0, y0, x1, y1 = f.getbbox(texto)
    tw, th = x1 - x0, y1 - y0
    pad = int(Wimg * 0.05)
    w = tw + 2 * pad
    hc = int(Wimg * 0.07)
    h = hc + th + 2 * pad
    lw = max(4, Wimg // 130)
    im = Image.new("RGBA", (w + 40, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = 14, 34
    r = int(Wimg * 0.025)
    d.rounded_rectangle([ox + 7, oy + 9, ox + w + 7, oy + h + 9], radius=r, fill=(0, 0, 0, 80))
    d.rounded_rectangle([ox, oy, ox + w, oy + h], radius=r, fill=CREME, outline=TINTA, width=lw)
    d.rounded_rectangle([ox, oy, ox + w, oy + hc], radius=r, fill="#0E3B3A", outline=TINTA, width=lw)
    d.rectangle([ox + lw, oy + hc - r, ox + w - lw, oy + hc - lw // 2], fill="#0E3B3A")
    d.line([(ox, oy + hc), (ox + w, oy + hc)], fill=TINTA, width=lw)
    d.text((ox + pad * 0.6, oy + hc / 2), cabec, font=fc, fill="#7FD6B5", anchor="lm")
    # linhas de caderno de laboratório
    for k in range(1, 4):
        yy = oy + hc + (h - hc) * k / 4
        d.line([(ox + lw * 2, yy), (ox + w - lw * 2, yy)], fill="#EADCC2", width=2)
    d.text((ox + pad - x0, oy + hc + pad - y0), texto, font=f, fill=TINTA)
    # clipe amarelo no topo
    cw = int(w * 0.22)
    cx = ox + int(w * 0.8)
    d.rounded_rectangle([cx - cw // 2, oy - 26, cx + cw // 2, oy + 16], radius=10, fill="#FFC928", outline=TINTA, width=lw)
    d.ellipse([cx - 9, oy - 16, cx + 9, oy + 2], fill=TINTA)
    return im.rotate(4, resample=Image.BICUBIC, expand=True)


def colar(base, im, cx, cy):
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def pos_quadro1(src):
    img = Image.open(src).convert("RGBA")
    colar(img, cartao_gancho("VOCÊ FAZ ISSO?", W), W / 2, H * 0.13)
    img.convert("RGB").save(os.path.join(HERE, "quadro1.png"))


def pos_quadro2(src_macro, src_micro, centro, raio):
    img = Image.open(src_macro).convert("RGBA")
    micro = Image.open(src_micro).convert("RGBA")
    r = int(raio + 2)
    d = 2 * r
    mw, mh = micro.size
    z = 0.8                                   # recorte central (efeito de aumento)
    micro = micro.crop((int(mw * (1 - z) / 2), int(mh * (1 - z) / 2 - mh * 0.05), int(mw * (1 + z) / 2),
                        int(mh * (1 + z) / 2 - mh * 0.05)))
    micro = micro.resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d * 4 - 1, d * 4 - 1], fill=255)
    mask = mask.resize((d, d), Image.LANCZOS)
    # sombra interna (borda do vidro) + reflexo
    som = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    sd = ImageDraw.Draw(som)
    sd.ellipse([0, 0, d - 1, d - 1], outline=(14, 59, 58, 150), width=max(6, d // 18))
    som = som.filter(ImageFilter.GaussianBlur(d / 40))
    micro.alpha_composite(som)
    br = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    ImageDraw.Draw(br).arc([d * 0.14, d * 0.14, d * 0.86, d * 0.86], 200, 250, fill=(255, 255, 255, 170), width=max(5, d // 30))
    micro.alpha_composite(br)
    img.paste(micro, (int(centro[0] - r), int(centro[1] - r)), mask)
    # o aro 3D da lupa fica por cima: recolocamos os pixels do aro (fora do raio interno) a partir do render original
    orig = Image.open(src_macro).convert("RGBA")
    anel = Image.new("L", img.size, 0)
    ad = ImageDraw.Draw(anel)
    ad.ellipse([centro[0] - r - 40, centro[1] - r - 40, centro[0] + r + 40, centro[1] + r + 40], fill=255)
    ad.ellipse([centro[0] - raio + 1, centro[1] - raio + 1, centro[0] + raio - 1, centro[1] + raio - 1], fill=0)
    img.paste(orig, (0, 0), anel)
    # selo de aumento no aro da lupa
    sf = fonte(int(W * 0.04))
    selo = Image.new("RGBA", (int(W * 0.2), int(W * 0.08)), (0, 0, 0, 0))
    sd2 = ImageDraw.Draw(selo)
    sd2.rounded_rectangle([2, 2, selo.width - 3, selo.height - 3], radius=selo.height // 2, fill="#0E3B3A",
                          outline=TINTA, width=3)
    sd2.text((selo.width / 2, selo.height / 2), "x 1000", font=sf, fill="#7FD6B5", anchor="mm")
    selo = selo.rotate(-12, resample=Image.BICUBIC, expand=True)
    colar(img, selo, centro[0] + raio * 0.75, centro[1] - raio * 1.02)
    colar(img, etiqueta("TAMPA OS POROS", "problema", W), W / 2, H * 0.17)
    img.convert("RGB").save(os.path.join(HERE, "quadro2.png"))


def pos_quadro3(src):
    img = Image.open(src).convert("RGBA")
    colar(img, etiqueta("ESPINHA", "problema", W, icone=True), W / 2, H * 0.17)
    img.convert("RGB").save(os.path.join(HERE, "quadro3.png"))


# ================================================================ comparação
def comparacao():
    tempos = [3.5, 30.5, 35.6]
    conc = []
    for t in tempos:
        p = os.path.join(TMP, f"conc_{t}.png")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", VIDEO_CONC, "-frames:v", "1", p],
                       check=True)
        conc.append(Image.open(p).convert("RGB"))
    nossos = [Image.open(os.path.join(HERE, f"quadro{i}.png")).convert("RGB") for i in (1, 2, 3)]
    cw, ch = 576, 1024
    gap, mx = 24, 30
    top_lbl, col_lbl, row_lbl = 110, 64, 70
    Wt = mx * 2 + cw * 3 + gap * 2
    Ht = top_lbl + col_lbl + (row_lbl + ch) * 2 + gap + mx
    out = Image.new("RGB", (Wt, Ht), "#0E3B3A")
    d = ImageDraw.Draw(out)
    d.text((Wt / 2, top_lbl / 2 + 6), "Mesmo tema, dois estilos", font=fonte(64), fill=CREME, anchor="mm")
    nomes = ["1. Gancho", "2. Entrando no corpo", "3. Lá dentro"]
    y = top_lbl
    for i, n in enumerate(nomes):
        d.text((mx + i * (cw + gap) + cw / 2, y + col_lbl / 2), n, font=fonte(44), fill="#FFC928", anchor="mm")
    y += col_lbl
    for rot, ims, cor in (("CONCORRENTE", conc, "#C9D1D0"), ("NOSSO (proposta B)", nossos, "#7FD6B5")):
        d.text((mx, y + row_lbl / 2), rot, font=fonte(48), fill=cor, anchor="lm")
        y += row_lbl
        for i, im in enumerate(ims):
            im = im.resize((cw, int(im.height * cw / im.width)), Image.LANCZOS).crop((0, 0, cw, ch))
            x = mx + i * (cw + gap)
            out.paste(im, (x, y))
            d.rectangle([x - 3, y - 3, x + cw + 2, y + ch + 2], outline=cor, width=4)
        y += ch + gap
    out.save(os.path.join(HERE, "comparacao.jpg"), quality=88)
    print("comparacao:", out.size)


if __name__ == "__main__":
    alvo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    alvo = alvo or ["1", "2", "3", "comp"]
    if "1" in alvo:
        pos_quadro1(quadro1())
    if "2" in alvo:
        src_macro, centro, raio = quadro2_macro()
        src_micro = quadro2_micro()
        pos_quadro2(src_macro, src_micro, centro, raio)
    if "3" in alvo:
        pos_quadro3(quadro3())
    if "comp" in alvo:
        comparacao()
    print("tempos:", {k: round(v, 1) for k, v in TEMPOS.items()})
