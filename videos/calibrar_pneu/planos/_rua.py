"""Peças comuns dos planos de ENCENAÇÃO do vídeo 02 (rua, posto, luz de dia, câmera, o cara, moedas, pneu velho).

Estilo "adulto": luz de dia quente (sol 5000 K baixo + céu azul de preenchimento), cores de tinta de muro reais,
asfalto escuro com faixa. Tudo em escala 1:1 (o Zé tem 1,79 m; o carro antigo entra com escala=1.0).
"""
import os, sys, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import comum as C
import bpy, bmesh
from mathutils import Vector, Euler
import motor as mt
from motor import lin
import boneco_adulto as ba
import veiculos3 as v3
import veiculos_antigos as va

CARA = dict(roupa="civil", camisa="#B5452F", calca="#3A5A86", pele="#B87A5A", cabelo="#16110E", corte="alto",
            barba=0.12)


# ================================================================ render / luz
def dia(sc, sol=(38, 0, -32), forca=3.2, ceu=0.9, exposicao=-0.6):
    """Sol quente + céu. A câmera vê um degradê de céu (azul em cima, claro no horizonte); a luz do céu é uniforme."""
    c = sc.cycles
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 4, 2, 1
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = exposicao
    w = bpy.data.worlds.new("ceu")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].position = 0.35
    rp.color_ramp.elements[0].color = lin("#D9E6EE")
    rp.color_ramp.elements[1].color = lin("#6E9FD0")
    nt.links.new(sep.outputs["Y"], rp.inputs["Fac"])
    b_cam = nt.nodes.new("ShaderNodeBackground")
    b_cam.inputs["Strength"].default_value = 1.0 / (2 ** exposicao) * 0.95
    nt.links.new(rp.outputs["Color"], b_cam.inputs["Color"])
    b_luz = nt.nodes.new("ShaderNodeBackground")
    b_luz.inputs["Color"].default_value = lin("#A9C6E6")
    b_luz.inputs["Strength"].default_value = ceu
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0])
    nt.links.new(b_luz.outputs[0], mx.inputs[1])
    nt.links.new(b_cam.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    d = bpy.data.lights.new("sol", "SUN")
    d.energy = forca
    d.angle = math.radians(2.5)
    d.color = lin("#FFE3BF")[:3]
    o = mt.link(bpy.data.objects.new("sol", d))
    o.rotation_euler = tuple(math.radians(a) for a in sol)
    return o


def camera(pos, alvo, lens=35, dof=None):
    """Câmera com Track To num vazio-alvo (anime cam.location e alvo.location)."""
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.sensor_width = 36
    cam = mt.link(bpy.data.objects.new("cam", cd))
    cam.location = pos
    al = mt.empty("alvo_cam", alvo)
    ct = cam.constraints.new("TRACK_TO")
    ct.target = al
    ct.track_axis, ct.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_object = al
        cd.dof.aperture_fstop = dof
    mt.scene.camera = cam
    return cam, al


def kloc(o, t, v):
    o.location = v
    o.keyframe_insert("location", frame=C.F(t))


def krot(o, t, v):
    """Rotação euler em graus."""
    o.rotation_euler = tuple(math.radians(a) for a in v)
    o.keyframe_insert("rotation_euler", frame=C.F(t))


def kesc(o, t, v):
    o.scale = v if isinstance(v, (tuple, list)) else (v, v, v)
    o.keyframe_insert("scale", frame=C.F(t))


def pose(Z, t, ossos):
    ba.pose(Z["arm"], C.F(t), ossos)


def fala(R, t0, t1, forte=0.7, seed=1):
    """Boca abre/fecha em sílabas irregulares entre t0 e t1 (e fecha no fim)."""
    rnd = random.Random(seed)
    t, k = t0, 0
    C.key_val(R["boca_aberta"], t0, 0.05)
    while t < t1 - 0.12:
        t += 0.1 + rnd.random() * 0.08
        C.key_val(R["boca_aberta"], t, forte * (0.5 + 0.5 * rnd.random()) if k % 2 == 0 else 0.08)
        k += 1
    C.key_val(R["boca_aberta"], t1, 0.05)


def piscar(R, t):
    for dt, v in ((-0.05, 1.0), (0.0, 0.05), (0.08, 1.0)):
        C.key_val(R["abre_olho"], t + dt, v)


# ================================================================ materiais
def _m(M, k, cor, rough=0.7, metal=0.0, coat=0.0, emit=0.0):
    if k not in M:
        m = ba._pbr("rua_" + k, cor, rough=rough, coat=coat, metal=metal)
        if emit:
            b = mt.bsdf(m)
            b.inputs["Emission Color"].default_value = lin(cor)
            b.inputs["Emission Strength"].default_value = emit
        M[k] = m
    return M[k]


def _ruido_cor(m, c0, c1, escala=4.0, bump=0.0, detalhe=6.0):
    nt = m.node_tree
    tx = nt.nodes.new("ShaderNodeTexNoise")
    tx.inputs["Scale"].default_value = escala
    tx.inputs["Detail"].default_value = detalhe
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = lin(c0)
    rp.color_ramp.elements[1].color = lin(c1)
    nt.links.new(tx.outputs["Fac"], rp.inputs["Fac"])
    nt.links.new(rp.outputs["Color"], mt.bsdf(m).inputs["Base Color"])
    if bump:
        t2 = nt.nodes.new("ShaderNodeTexNoise")
        t2.inputs["Scale"].default_value = 260.0
        bu = nt.nodes.new("ShaderNodeBump")
        bu.inputs["Strength"].default_value = bump
        bu.inputs["Distance"].default_value = 0.004
        nt.links.new(t2.outputs["Fac"], bu.inputs["Height"])
        nt.links.new(bu.outputs["Normal"], mt.bsdf(m).inputs["Normal"])
    return m


def asfalto(M):
    if "asfalto" not in M:
        _ruido_cor(_m(M, "asfalto", "#34363A", rough=0.9), "#2C2E31", "#45474B", escala=3.0, bump=0.35)
    return M["asfalto"]


def concreto(M, k="concreto", c0="#9E9B93", c1="#B6B2A9"):
    if k not in M:
        _ruido_cor(_m(M, k, c0, rough=0.85), c0, c1, escala=2.5, bump=0.2)
    return M[k]


# ================================================================ cenários
def arvore(name, M, x, y, h=4.5, r=1.6, seed=0):
    rnd = random.Random(seed)
    tr = _m(M, "tronco_arv", "#5A4636", rough=0.9)
    fo = M.get("folha") or _ruido_cor(_m(M, "folha", "#4C7A3A", rough=0.8), "#3E6A30", "#6A9548", escala=1.5)
    mt.cyl(name + "_tr", 0.13, 0, h * 0.55, (x, y), tr, seg=12)
    for k in range(5):
        a = rnd.uniform(0, 6.28)
        d = rnd.uniform(0.2, 0.7) * r
        mt.ball(name + f"_c{k}", r * rnd.uniform(0.55, 0.8),
                (x + math.cos(a) * d, y + math.sin(a) * d * 0.6, h * 0.62 + rnd.uniform(-0.2, 0.6) * r), fo, sub=3)
        for p in bpy.data.objects[name + f"_c{k}"].data.polygons:
            p.use_smooth = True


def rua(M, x0=-14, x1=14, meio_fio=3.9, muro=True, arvores=True, postes=True, outro_lado=None):
    """Rua de bairro: asfalto escuro (y < meio_fio) com faixa branca tracejada e borda amarela, meio-fio, calçada,
    muro pintado (creme com barrado verde-acinzentado) e copas de árvore atrás. O carro estaciona em y≈2,9.
    outro_lado = y do meio-fio da calçada oposta (ex. -7,3): calçada + muro azul-acinzentado + árvores do outro lado
    (para câmeras que olham para -y)."""
    asf = asfalto(M)
    mt.box("asfalto", x0, x1, outro_lado if outro_lado is not None else -30, meio_fio, -0.05, 0.0, asf)
    if outro_lado is not None:
        yb = outro_lado
        mt.box("meio_fio2", x0, x1, yb - 0.16, yb, -0.05, 0.15, concreto(M, "meiofio", "#A7A49C", "#C2BEB4"))
        mt.box("calcada2", x0, x1, yb - 2.2, yb - 0.16, -0.05, 0.13, concreto(M, "calcada", "#B4ADA0", "#C9C2B4"))
        az = _ruido_cor(_m(M, "muro2", "#A9BFC9", rough=0.92), "#9DB3BE", "#B5CAD3", escala=1.2, bump=0.25)
        mt.box("muro2", x0, x1, yb - 2.4, yb - 2.2, 0.0, 2.6, az)
        mt.box("barrado2", x0, x1, yb - 2.2, yb - 2.19, 0.0, 0.5, _m(M, "barrado2", "#6F7C86", rough=0.9))
        for xp in range(int(x0) + 3, int(x1), 4):
            mt.box(f"pilar2_{xp}", xp - 0.16, xp + 0.16, yb - 2.46, yb - 2.16, 0.0, 2.7, az)
        for i, xa in enumerate(range(int(x0) + 4, int(x1), 6)):
            arvore(f"arv2_{i}", M, xa + (i % 2) * 1.5, yb - 4.2, h=5.0 + (i % 3) * 0.5, seed=10 + i)
    tinta = _ruido_cor(_m(M, "faixa_branca", "#E6E2D6", rough=0.6), "#BDB9AE", "#ECE8DC", escala=9.0) \
        if "faixa_branca" not in M else M["faixa_branca"]
    k = x0
    while k < x1:
        mt.box(f"faixa{k:.0f}", k, k + 2.0, -1.6, -1.48, 0.0, 0.003, tinta)
        k += 4.0
    am = _m(M, "faixa_amarela", "#D9A21B", rough=0.6)
    mt.box("borda_am", x0, x1, meio_fio - 0.32, meio_fio - 0.22, 0.0, 0.003, am)
    # vagas demarcadas junto ao meio-fio (traços perpendiculares)
    for xv in (-6.2, -1.6, 3.0, 7.6):
        mt.box(f"vaga{xv}", xv - 0.06, xv + 0.06, meio_fio - 2.2, meio_fio - 0.32, 0.0, 0.003, tinta)
    mf = concreto(M, "meiofio", "#A7A49C", "#C2BEB4")
    o = mt.box("meio_fio", x0, x1, meio_fio, meio_fio + 0.16, -0.05, 0.15, mf)
    ca = concreto(M, "calcada", "#B4ADA0", "#C9C2B4")
    mt.box("calcada", x0, x1, meio_fio + 0.16, meio_fio + 2.2, -0.05, 0.13, ca)
    # juntas da calçada
    jn = _m(M, "junta", "#8E887D", rough=0.9)
    xx = x0
    while xx < x1:
        mt.box(f"junta{xx:.1f}", xx, xx + 0.02, meio_fio + 0.16, meio_fio + 2.2, 0.13, 0.132, jn)
        xx += 1.5
    if muro:
        y = meio_fio + 2.2
        cr = _ruido_cor(_m(M, "muro", "#E2D2AE", rough=0.92), "#D6C49E", "#EADBB9", escala=1.2, bump=0.25)
        mt.box("muro", x0, x1, y, y + 0.2, 0.0, 2.4, cr)
        bar = _ruido_cor(_m(M, "barrado", "#5E7D7A", rough=0.9), "#557370", "#678784", escala=1.5)
        mt.box("barrado", x0, x1, y - 0.01, y, 0.0, 0.6, bar)
        mt.box("chapim", x0, x1, y - 0.04, y + 0.24, 2.4, 2.47, _m(M, "chapim", "#C9BDA2", rough=0.8))
        for xp in range(int(x0) + 1, int(x1), 4):     # pilares do muro
            mt.box(f"pilar{xp}", xp - 0.16, xp + 0.16, y - 0.06, y + 0.22, 0.0, 2.5, cr)
        if arvores:
            for i, xa in enumerate(range(int(x0) + 2, int(x1), 5)):
                arvore(f"arv{i}", M, xa + (i % 2) * 1.3, y + 1.8, h=4.6 + (i % 3) * 0.6, seed=i)
    if postes:
        po = _m(M, "poste", "#8F9499", rough=0.5, metal=0.6)
        for xp in range(int(x0) + 4, int(x1), 9):
            mt.cyl(f"poste{xp}", 0.07, 0, 6.5, (xp, meio_fio + 0.5), po, seg=12)
            b = mt.box(f"braco{xp}", -0.04, 0.04, -1.2, 0.0, -0.04, 0.04, po, anchor="center")
            b.location = (xp, meio_fio + 0.5, 6.4)
            lu = mt.box(f"lum{xp}", -0.12, 0.12, -0.3, 0.0, -0.06, 0.04, _m(M, "lum", "#3B3F45", rough=0.5),
                        anchor="center")
            lu.location = (xp, meio_fio - 0.6, 6.4)


def posto(M, x_cal=3.2):
    """Posto genérico SEM marca: piso de concreto com juntas, cobertura branca com faixa verde-acinzentada e luzes
    embutidas, ilha com bomba (tela, bicos e mangueiras), loja de vidro ao fundo e calibrador de parede (caixa com
    mostrador e mangueira em espiral) num pilar de alvenaria em x_cal. Carro entra pela esquerda em y≈0."""
    pi_ = concreto(M, "piso_posto", "#ADA9A0", "#C3BFB5")
    mt.box("piso_posto", -16, 16, -30, 9, -0.05, 0.0, pi_)
    jn = _m(M, "junta", "#8E887D", rough=0.9)
    for k in range(-16, 16, 3):
        mt.box(f"jx{k}", k, k + 0.025, -30, 9, 0.0, 0.002, jn)
    for k in range(-30, 9, 3):
        mt.box(f"jy{k}", -16, 16, k, k + 0.025, 0.0, 0.002, jn)
    # cobertura
    br = _m(M, "cob", "#EEEDE8", rough=0.6)
    vd = _m(M, "cob_faixa", "#2E5E5A", rough=0.45, coat=0.3)
    mt.box("cobertura", -9, 9, -2.5, 6.5, 4.8, 5.4, br)
    mt.box("cob_faixa", -9.02, 9.02, -2.53, 6.53, 5.0, 5.3, vd)
    mt.box("cob_filete", -9.03, 9.03, -2.54, 6.54, 5.12, 5.17, br)
    lz = _m(M, "luz_cob", "#FFFFFF", rough=0.3, emit=3.0)
    for x in (-6, -2, 2, 6):
        for y in (-0.5, 4.0):
            mt.box(f"lp{x}{y}", x - 0.6, x + 0.6, y - 0.3, y + 0.3, 4.79, 4.8, lz)
    col = _m(M, "coluna", "#D9D7D0", rough=0.5)
    for x in (-5.5, 5.5):
        mt.box(f"col{x}", x - 0.22, x + 0.22, 3.6, 4.04, 0.0, 4.8, col)
    # ilha com bomba (fundo, y≈3.8)
    il = _m(M, "ilha", "#D8D4CB", rough=0.7)
    mt.box("ilha", -2.4, 2.4, 3.3, 4.3, 0.0, 0.18, il)
    for x in (-2.4, 2.25):
        mt.box(f"ilha_am{x}", x, x + 0.15, 3.3, 4.3, 0.0, 0.19, _m(M, "faixa_amarela", "#D9A21B", rough=0.6))
    bb = _m(M, "bomba", "#E9E8E3", rough=0.4, coat=0.3)
    b = mt.box("bomba", -0.55, 0.55, 3.55, 4.05, 0.18, 2.1, bb)
    v3._no(b) if hasattr(v3, "_no") and False else None
    mt.box("bomba_topo", -0.6, 0.6, 3.5, 4.1, 2.1, 2.35, vd)
    tela = _m(M, "tela", "#10161A", rough=0.15)
    mt.box("tela", -0.38, 0.38, 3.53, 3.55, 1.35, 1.75, tela)
    dig = _m(M, "digito", "#7FE0A0", rough=0.3, emit=1.5)
    for k in range(3):
        mt.box(f"dig{k}", -0.3, 0.3, 3.525, 3.53, 1.42 + k * 0.1, 1.47 + k * 0.1, dig)
    preto = _m(M, "borracha_p", "#141516", rough=0.7)
    for s in (-1, 1):
        mt.box(f"bico{s}", s * 0.42 - 0.06, s * 0.42 + 0.06, 3.47, 3.55, 0.95, 1.2, preto)
        v3.tubo(f"mang{s}", [(s * 0.42, 3.5, 0.95), (s * 0.55, 3.35, 0.55), (s * 0.5, 3.4, 0.3),
                             (s * 0.5, 3.55, 1.8)], 0.022, preto, seg=10)
    # loja ao fundo (vidro escuro + faixa)
    loja = _m(M, "loja", "#D7D3C9", rough=0.8)
    mt.box("loja", -12, 12, 8.0, 9.0, 0.0, 3.6, loja)
    vid = _m(M, "vidro_loja", "#1C2A30", rough=0.08)
    for x in range(-11, 11, 3):
        mt.box(f"vit{x}", x + 0.1, x + 2.8, 7.98, 8.0, 0.4, 2.8, vid)
    mt.box("loja_faixa", -12, 12, 7.96, 8.0, 2.95, 3.35, vd)
    # pilar com calibrador de parede (frente direita, perto do carro)
    al = _ruido_cor(_m(M, "alvenaria", "#CFC6B4", rough=0.9), "#C4BAA6", "#D9D1C0", escala=2.0, bump=0.2)
    xc, yc = x_cal, 1.75
    mt.box("pilar_cal", xc - 0.3, xc + 0.3, yc, yc + 0.6, 0.0, 2.2, al)
    mt.box("pilar_cal_b", xc - 0.31, xc + 0.31, yc - 0.01, yc + 0.61, 0.0, 0.35, M.get("barrado") or _m(
        M, "barrado", "#5E7D7A", rough=0.9))
    cx = _m(M, "cal_caixa", "#C9CDD1", rough=0.35, metal=0.3)
    mt.box("cal_caixa", xc - 0.18, xc + 0.18, yc - 0.12, yc, 1.25, 1.75, cx)
    mt.box("cal_tampa", xc - 0.19, xc + 0.19, yc - 0.13, yc, 1.73, 1.78, vd)
    mostr = _m(M, "mostrador", "#F2F1EC", rough=0.3)
    d = mt.cyl("cal_mostrador", 0.1, 0, 0.012, (0, 0), mostr, seg=32)
    d.rotation_euler = (math.radians(90), 0, 0)
    d.location = (xc, yc - 0.12, 1.55)
    an = mt.cyl("cal_aro", 0.112, 0, 0.008, (0, 0), preto, seg=32)
    an.rotation_euler = (math.radians(90), 0, 0)
    an.location = (xc, yc - 0.121, 1.55)
    pt = mt.box("cal_ponteiro", -0.006, 0.006, -0.002, 0.002, 0.0, 0.075, _m(M, "ponteiro", "#C8221B", rough=0.4))
    pt.location = (xc, yc - 0.137, 1.55)
    pt.rotation_euler = (0, math.radians(35), 0)
    M["_ponteiro"] = pt
    for k, cbt in enumerate(("#2F8F4E", "#C8221B")):
        bt = mt.cyl(f"cal_bt{k}", 0.025, 0, 0.02, (0, 0), _m(M, f"bt{k}", cbt, rough=0.4), seg=16)
        bt.rotation_euler = (math.radians(90), 0, 0)
        bt.location = (xc - 0.07 + k * 0.14, yc - 0.12, 1.34)
    # mangueira em espiral pendurada + bico
    pts = []
    for i in range(60):
        a = i / 60 * 2 * math.pi * 6
        pts.append((xc + 0.09 * math.cos(a), yc - 0.2 + 0.07 * math.sin(a), 1.2 - i * 0.012))
    v3.tubo("cal_espiral", [(xc, yc - 0.1, 1.27)] + pts, 0.011, _m(M, "mang_cal", "#E7B21C", rough=0.5), seg=8)
    mt.box("cal_bico", xc - 0.02, xc + 0.02, yc - 0.24, yc - 0.16, 0.34, 0.46, M["cal_caixa"])
    return {"ponteiro": pt}


# ================================================================ peças
def carro(M, cor="vermelho", tipo="bolinha", conservacao="gasto", nome="carro"):
    """Carro do cara em 1:1. Devolve o dict de carro_antigo; c['spec'] tem xf, xr, R."""
    return va.carro_antigo(nome, M, tipo=tipo, cor=cor, conservacao=conservacao, escala=1.0)


def roda_dd(c):
    """Roda dianteira do lado da câmera (-y): a que perdeu a calota no "gasto"."""
    return [r for r in c["rodas"] if r.name.endswith("_roda_dd")][0]


def girar_rodas(c, t0, t1, x0, x1, passo=0.25):
    """Rodas giram sem escorregar com o deslocamento do carro: x(t) já animado em c['raiz'] — gira pela distância.
    Lado +y gira +y, lado -y (roda virada 180° em z) gira -y."""
    R = c["spec"]["R"] * c["raiz"].scale[0]
    sc = mt.scene
    t = t0
    while True:
        sc.frame_set(C.F(t))
        x = c["raiz"].location.x
        for rd in c["rodas"]:
            sinal = 1 if rd.location.y > 0 else -1
            rd.rotation_euler = (0, sinal * (x - x0) / R, 0 if sinal > 0 else math.pi)
            rd.keyframe_insert("rotation_euler", frame=C.F(t))
        if t >= t1:
            break
        t = min(t1, t + passo)
    for rd in c["rodas"]:
        ba.suavizar(rd, "LINEAR")


def moeda(name, M, r=0.0135):
    """Moeda de 1 real (bimetálica: miolo prateado, anel dourado), com eixo em y (rola no plano xz)."""
    ou = _m(M, "ouro", "#C99A3B", rough=0.3, metal=1.0)
    pr = _m(M, "prata_m", "#C8CBCE", rough=0.3, metal=1.0)
    root = mt.empty(name)
    a = v3.torno(name + "_anel", [(r * 0.6, -0.0011, 0), (r, -0.0011, 0), (r * 1.02, 0.0, 0), (r, 0.0011, 0),
                                   (r * 0.6, 0.0011, 0)], [ou], seg=32)
    a.parent = root
    m = v3.torno(name + "_miolo", [(0.0, -0.0012, 0), (r * 0.6, -0.0012, 0), (r * 0.6, 0.0012, 0), (0.0, 0.0012, 0)],
                 [pr], seg=32)
    m.parent = root
    return root


def pneu_velho(name, M, R=0.29, larg=0.175, aro=0.165, gasto=1.0):
    """Pneu solto (sem roda), eixo y: miolo da banda com sulcos fundos e BEIRADAS gastas (ombros lisos, claros e
    arredondados — o sinal do pneu rodado vazio). gasto 0..1."""
    borr = _m(M, "pv_borr", "#1B1C1E", rough=0.85)
    sulco = _m(M, "pv_sulco", "#0A0A0B", rough=0.95)
    liso = _m(M, "pv_liso", "#4A4A4C", rough=0.35)          # ombro gasto: liso e brilhante
    w = larg / 2
    g = 0.012
    q = 0.02 + 0.035 * gasto                                 # quanto o ombro foi comido
    perfil = [(aro + 0.01, -w * 0.8, 0), (aro + 0.04, -w * 1.02, 0), (R - 0.07, -w * 1.06, 0),
              (R - q - 0.01, -w * 1.0, 2), (R - q * 0.3, -w * 0.8, 2), (R, -w * 0.55, 0),
              (R - g, -w * 0.52, 1), (R - g, -w * 0.38, 0), (R, -w * 0.35, 0),
              (R, -w * 0.08, 1), (R - g, -w * 0.06, 1), (R - g, w * 0.06, 0), (R, w * 0.08, 0),
              (R, w * 0.35, 1), (R - g, w * 0.38, 1), (R - g, w * 0.52, 0), (R, w * 0.55, 2),
              (R - q * 0.3, w * 0.8, 2), (R - q - 0.01, w * 1.0, 0), (R - 0.07, w * 1.06, 0),
              (aro + 0.04, w * 1.02, 0), (aro + 0.01, w * 0.8, 0)]
    # o índice vale para o trecho seguinte: recalcula para pintar os sulcos e os ombros
    o = v3.torno(name, perfil + [perfil[0][:2] + (0,)], [borr, sulco, liso], seg=72)
    return o


def etiqueta(name, M, texto="BARATO"):
    """Etiqueta de preço de papelão amarelo com furo, barbante e texto grande em relevo. Frente = -y."""
    root = mt.empty(name)
    am = _m(M, "etq", "#F2C230", rough=0.75)
    pr = _m(M, "etq_txt", "#1A1A1A", rough=0.6)
    bm = bmesh.new()
    L, A = 0.34, 0.16
    pts = [(-L / 2, -A / 2), (L / 2 - 0.05, -A / 2), (L / 2, 0), (L / 2 - 0.05, A / 2), (-L / 2, A / 2)]
    vs_f = [bm.verts.new((x, -0.003, z)) for x, z in pts]
    vs_b = [bm.verts.new((x, 0.003, z)) for x, z in pts]
    bm.faces.new(vs_f[::-1])
    bm.faces.new(vs_b)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new([vs_f[i], vs_f[j], vs_b[j], vs_b[i]])
    e = mt.mesh_obj(name + "_papel", bm, am)
    e.parent = root
    f = mt.cyl(name + "_furo", 0.012, 0, 0.01, (0, 0), pr, seg=16)
    f.rotation_euler = (math.radians(90), 0, 0)
    f.location = (L / 2 - 0.05, 0.005, 0)
    f.parent = root
    t = mt.text(name + "_txt", texto, 0.065, (-0.03, -0.004, -0.024), pr, rot=(math.radians(90), 0, 0),
                extrude=0.002)
    t.data.body = texto
    t.data.offset_x = 0
    t.parent = root
    v3.tubo(name + "_barb", [(L / 2 - 0.05, 0, 0), (L / 2 + 0.03, 0.0, 0.05), (L / 2 + 0.06, 0.0, 0.13)], 0.003,
            _m(M, "barbante", "#D8CCB0", rough=0.9), seg=6).parent = root
    return root


def fumaca(name, M, loc, t0, t1, n=6, seed=3):
    """Fumacinha leve (bafo de pneu quente): bolinhas translúcidas que sobem, crescem e somem."""
    if "fumaca" not in M:
        m = bpy.data.materials.new("fumaca")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        df = nt.nodes.new("ShaderNodeBsdfDiffuse")
        df.inputs["Color"].default_value = (0.95, 0.95, 0.95, 1)
        mx = nt.nodes.new("ShaderNodeMixShader")
        # opacidade cai do centro para a borda (Layer Weight) e com o atributo do objeto (alpha animado em color)
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.6
        ob = nt.nodes.new("ShaderNodeObjectInfo")
        sp = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(ob.outputs["Color"], sp.inputs[0])
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        nt.links.new(lw.outputs["Facing"], inv.inputs[1])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        nt.links.new(inv.outputs[0], mul.inputs[0])
        nt.links.new(sp.outputs[0], mul.inputs[1])
        nt.links.new(mul.outputs[0], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(df.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
        m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
        M["fumaca"] = m
    rnd = random.Random(seed)
    obs = []
    for k in range(n):
        o = mt.ball(f"{name}{k}", 0.1, loc, M["fumaca"], sub=2)
        ts = t0 + (t1 - t0) * k / n
        te = min(t1, ts + 1.6)
        x, y, z = loc
        dx, dy = rnd.uniform(-0.15, 0.15), rnd.uniform(-0.1, 0.05)
        o.color = (0, 0, 0, 1)
        o.keyframe_insert("color", frame=C.F(max(0, ts - 0.01)))
        kloc(o, ts, (x, y, z)); kesc(o, ts, 0.4)
        o.color = (0.5, 0, 0, 1); o.keyframe_insert("color", frame=C.F(ts + 0.35))
        kloc(o, te, (x + dx, y + dy, z + 0.75)); kesc(o, te, 2.2)
        o.color = (0, 0, 0, 1); o.keyframe_insert("color", frame=C.F(te))
        obs.append(o)
    return obs


# ================================================================ tempos das palavras (palavras.json)
def _norm(s):
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if c.isalnum() and not unicodedata.combining(c))


def palavras():
    import json
    p = os.path.join(C.HERE, "palavras.json")
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return json.load(f)


def palavra(P, *alternativas, k=0, reserva=None, fim=False):
    """Tempo LOCAL (s) da k-ésima ocorrência, dentro do plano, da palavra (ou de uma das alternativas: a transcrição
    erra, ex. "murcho" → "muxo"). Uma alternativa com espaço ("segue a vida") casa a sequência e devolve o início
    da primeira. fim=True devolve o fim da palavra. reserva = fração da duração usada se não achar."""
    W = palavras()
    ini, fim_p = P["ini"] - 0.3, P["fim"] + 0.05
    for alt in alternativas:
        seq = [_norm(x) for x in alt.split()]
        achou = []
        for i in range(len(W) - len(seq) + 1):
            if all(_norm(W[i + j][0]) == seq[j] for j in range(len(seq))) and ini <= W[i][1] <= fim_p:
                achou.append(W[i + len(seq) - 1][2] if fim else W[i][1])
        if len(achou) > k:
            return max(0.0, achou[k] - P["ini"])
    if reserva is None:
        raise KeyError(f"palavra {alternativas} não achada em {P['nome']}")
    print(f"aviso: {alternativas} não achada em {P['nome']}; usando {reserva:.2f} da duração", flush=True)
    return reserva * P["dur"]
