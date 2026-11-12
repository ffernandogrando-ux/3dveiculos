"""Mascote ADULTO do canal: o mecânico Zé, ~40 anos (direção A "estilizado adulto", briefing do diretor de arte).

O dono achou o Zé de 3 cabeças infantil. Aqui: 6,3 cabeças (1,79 m), ombros largos, maxilar quadrado, olhos amendoados
com íris e pálpebra pintados no shader, nariz em cunha de geometria, barba por fazer (ruído), cabelo curto, macacão
grafite com faixas laranja refletivas, mãos com dedos. Mesma técnica do boneco.py: Skin+Subsurf com esqueleto
(Armature antes do Skin), rosto por nós Value (animáveis), objetos rígidos presos aos ossos.

    Z = ze_adulto("ze", M, pose="explica", expressao="fala")
    girar(Z["arm"], "ombro_e", x=-60)          # eixos do mundo em repouso; olha para -y
"""
import math
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion, noise
import motor as mt
from motor import lin, empty
from boneco import skin, esfera, _deforma, _no_osso, _bevel, _liso, _sub

COR = {"pele": "#C98463", "pele_sombra": "#C07E5C", "barba": "#3A2A22", "cabelo": "#2B1D16", "sobr": "#2B1D16",
       "iris": "#5A3A24", "labio": "#B5655A", "macacao": "#1F4E79", "macacao_esc": "#173B5C", "faixa": "#E8590C",
       "refletivo": "#D9DDE2", "camiseta": "#E8E2D6", "bota": "#1E1F23", "sola": "#111214", "pano": "#D62828",
       "luva": "#1B1C20"}

ALT = 1.79                           # altura total
HC = 0.27                            # altura da cabeça (≈ 1/6,6)


def _pbr(name, hexcol, rough=0.6, coat=0.0, sss=0.0, metal=0.0):
    m = mt.mat(name, hexcol, rough=rough)
    b = mt.bsdf(m)
    for k, v in (("Specular IOR Level", 0.5), ("Coat Weight", coat), ("Coat Roughness", 0.2), ("Metallic", metal),
                 ("Subsurface Weight", sss)):
        if k in b.inputs:
            b.inputs[k].default_value = v
    if sss and "Subsurface Radius" in b.inputs:
        b.inputs["Subsurface Radius"].default_value = (0.01, 0.004, 0.002)
        if "Subsurface Scale" in b.inputs:
            b.inputs["Subsurface Scale"].default_value = 0.02
    return m


def _tecido(name, hexcol, rough=0.85):
    """Tecido: Principled fosco com bump de ruído fino (trama/ruga leve)."""
    m = _pbr(name, hexcol, rough=rough)
    nt = m.node_tree
    b = mt.bsdf(m)
    tx = nt.nodes.new("ShaderNodeTexNoise")
    tx.inputs["Scale"].default_value = 140.0
    tx.inputs["Detail"].default_value = 4.0
    bu = nt.nodes.new("ShaderNodeBump")
    bu.inputs["Strength"].default_value = 0.12
    bu.inputs["Distance"].default_value = 0.002
    nt.links.new(tx.outputs["Fac"], bu.inputs["Height"])
    tx2 = nt.nodes.new("ShaderNodeTexNoise")
    tx2.inputs["Scale"].default_value = 9.0
    bu2 = nt.nodes.new("ShaderNodeBump")
    bu2.inputs["Strength"].default_value = 0.18
    bu2.inputs["Distance"].default_value = 0.01
    nt.links.new(tx2.outputs["Fac"], bu2.inputs["Height"])
    nt.links.new(bu2.outputs["Normal"], bu.inputs["Normal"])
    nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])
    return m


def materiais(M):
    if "ad_pele" in M:
        return M
    M["ad_pele"] = _pbr("ad_pele", COR["pele"], rough=0.5, sss=0.08)
    M["ad_cabelo"] = _tecido("ad_cabelo", COR["cabelo"], rough=0.7)
    M["ad_macacao"] = _tecido("ad_macacao", COR["macacao"])
    M["ad_macacao_esc"] = _tecido("ad_macacao_esc", COR["macacao_esc"])
    M["ad_faixa"] = _tecido("ad_faixa", COR["faixa"], rough=0.7)
    M["ad_refletivo"] = _pbr("ad_refletivo", COR["refletivo"], rough=0.3, metal=0.6)
    M["ad_camiseta"] = _tecido("ad_camiseta", COR["camiseta"])
    M["ad_bota"] = _pbr("ad_bota", COR["bota"], rough=0.45, coat=0.3)
    M["ad_sola"] = _pbr("ad_sola", COR["sola"], rough=0.8)
    M["ad_pano"] = _tecido("ad_pano", COR["pano"])
    M["ad_metal"] = _pbr("ad_metal", "#B9C0C8", rough=0.25, metal=1.0)
    return M


# ================================================================ rosto adulto pintado
def _rosto(name, P):
    """Material da cabeça (origem no centro, frente -y): pele, olhos amendoados com íris/pupila/pálpebra, sobrancelhas
    grossas, lábios, barba por fazer. P: valores iniciais dos nós animáveis."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    X, Y, Zs = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
    V = {}

    def val(n, v):
        no = nt.nodes.new("ShaderNodeValue")
        no.name = no.label = n
        no.outputs[0].default_value = v
        V[n] = no
        return no.outputs[0]

    def op(o, a, b=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = o
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                nt.links.new(x, n.inputs[i])
        return n.outputs[0]

    def el(xs, cx, cz, a, b):
        dx = op("DIVIDE", op("SUBTRACT", xs, cx), a)
        dz = op("DIVIDE", op("SUBTRACT", Zs, cz), b)
        return op("ADD", op("MULTIPLY", dx, dx), op("MULTIPLY", dz, dz))

    def dentro(e, borda=0.1):
        return op("SUBTRACT", 1.0, op("MINIMUM", op("MAXIMUM", op("DIVIDE", op("SUBTRACT", e, 1.0 - borda), borda),
                                                    0.0), 1.0))

    frente = op("LESS_THAN", Y, -0.04)
    abre = val("abre_olho", P.get("abre_olho", 1.0))
    ox = val("olhar_x", P.get("olhar_x", 0.0))
    oz = val("olhar_z", P.get("olhar_z", 0.0))
    s_alt = val("sobr_alt", P.get("sobr_alt", 0.0))
    s_inc = val("sobr_inc", P.get("sobr_inc", 0.0))
    sorr = val("sorriso", P.get("sorriso", 0.4))
    abert = val("boca_aberta", P.get("boca_aberta", 0.0))

    ex, ez, ea, eb = 0.036, 0.016, 0.019, 0.0098
    olho = luz = iris = palp = olheira = 0.0
    for lado in (-1, 1):
        cx = lado * ex
        ebs = op("MAXIMUM", op("MULTIPLY", abre, eb), 0.0006)
        mo = dentro(el(X, cx, ez, ea * 0.92, ebs), 0.15)
        mo = op("MULTIPLY", mo, op("LESS_THAN", Zs, op("ADD", ez, op("MULTIPLY", ebs, 0.62))))   # pálpebra cobre o topo
        # íris + pupila (presas ao branco do olho)
        ix = op("ADD", cx, op("MULTIPLY", ox, ea * 0.4))
        iz = op("ADD", ez, op("MULTIPLY", oz, eb * 0.3))
        ir = op("MULTIPLY", dentro(el(X, ix, iz, 0.0085, 0.0085), 0.12), mo)
        pu = op("MULTIPLY", dentro(el(X, ix, iz, 0.0036, 0.0036), 0.2), mo)
        li = op("MULTIPLY", dentro(el(X, op("ADD", ix, -0.0025), op("ADD", iz, 0.0025), 0.0015, 0.0015), 0.3), mo)
        # pálpebra superior: faixa escura logo acima do olho (linha dos cílios)
        pl = op("MULTIPLY", dentro(el(X, cx, op("ADD", ez, 0.0008), ea * 1.0, op("ADD", ebs, 0.0022)), 0.15),
                op("SUBTRACT", 1.0, mo))
        pl = op("MULTIPLY", pl, op("GREATER_THAN", Zs, op("ADD", ez, op("MULTIPLY", ebs, 0.45))))
        olh = op("MULTIPLY", op("MAXIMUM", op("SUBTRACT", 1.0, el(X, cx, ez - 0.012, ea * 0.9, 0.006)), 0.0), 0.2)
        olheira = olh if lado == -1 else op("MAXIMUM", olheira, olh)
        olho = mo if olho == 0.0 else op("MAXIMUM", olho, mo)
        iris = op("ADD", ir, op("MULTIPLY", pu, 2.0)) if iris == 0.0 else op("ADD", iris, op("ADD", ir, op(
            "MULTIPLY", pu, 2.0)))
        luz = li if luz == 0.0 else op("MAXIMUM", luz, li)
        palp = pl if palp == 0.0 else op("MAXIMUM", palp, pl)
    # sobrancelhas grossas, anguladas (ponta de dentro um pouco mais baixa = sério/simpático)
    AX = op("ABSOLUTE", X)
    bz = op("ADD", ez + 0.021, op("MULTIPLY", s_alt, 0.006))
    zl = op("SUBTRACT", Zs, op("ADD", bz, op("MULTIPLY", op("ADD", 0.12, s_inc), op("SUBTRACT", AX, ex))))
    dx = op("DIVIDE", op("SUBTRACT", AX, ex - 0.002), 0.02)
    sob = dentro(op("ADD", op("POWER", op("ABSOLUTE", dx), 3.0), op("POWER", op("DIVIDE", zl, 0.0055), 2.0)), 0.25)
    # boca: lábios com curva de sorriso (z sobe nas pontas)
    mz = -0.056
    curva = op("MULTIPLY", op("MULTIPLY", X, X), op("MULTIPLY", sorr, 18.0))
    zb = op("SUBTRACT", Zs, op("ADD", mz, curva))
    larg = 0.024
    bx = op("DIVIDE", X, larg)
    labio = dentro(op("ADD", op("POWER", op("ABSOLUTE", bx), 4.0), op("POWER", op("DIVIDE", zb, 0.0055), 2.0)), 0.3)
    fenda = dentro(op("ADD", op("POWER", op("ABSOLUTE", op("DIVIDE", X, larg * 0.95)), 4.0),
                       op("POWER", op("DIVIDE", zb, op("ADD", 0.0011, op("MULTIPLY", abert, 0.009))), 2.0)), 0.3)
    # barba por fazer: ruído fino só no queixo/maxilar/buço
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 900.0
    tex.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], tex.inputs["Vector"])
    # região em degradê (sem linha dura): cresce de z=-0,03 a -0,06 e some perto do nariz/olhos
    reg = op("MINIMUM", op("MAXIMUM", op("DIVIDE", op("SUBTRACT", -0.03, Zs), 0.03), 0.0), 1.0)
    reg = op("MULTIPLY", reg, op("SUBTRACT", 1.0, labio))
    barba = op("MULTIPLY", op("MULTIPLY", reg, op("GREATER_THAN", tex.outputs["Fac"], 0.48)), 0.26)

    def mix(base, f, hexcol, sock=None):
        n = nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"
        nt.links.new(op("MULTIPLY", f, frente), n.inputs["Factor"])
        if isinstance(base, str):
            n.inputs["A"].default_value = lin(base)
        else:
            nt.links.new(base, n.inputs["A"])
        n.inputs["B"].default_value = lin(hexcol)
        return n.outputs[2]

    c = COR["pele"]
    c = mix(c, op("MULTIPLY", olheira, op("SUBTRACT", 1.0, olho)), "#B5735A")
    c = mix(c, barba, COR["barba"])
    c = mix(c, op("MULTIPLY", labio, 0.85), COR["labio"])
    c = mix(c, fenda, "#4A1E1E")
    c = mix(c, olho, "#F2EEE6")
    c = mix(c, op("MINIMUM", iris, 1.0), COR["iris"])
    c = mix(c, op("MINIMUM", op("MAXIMUM", op("SUBTRACT", iris, 1.0), 0.0), 1.0), "#0E0A08")
    c = mix(c, luz, "#FFFFFF")
    c = mix(c, palp, "#1E1410")
    c = mix(c, sob, COR["sobr"])
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(c, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5
    for k, v in (("Specular IOR Level", 0.5), ("Subsurface Weight", 0.08)):
        if k in b.inputs:
            b.inputs[k].default_value = v
    if "Subsurface Radius" in b.inputs:
        b.inputs["Subsurface Radius"].default_value = (0.01, 0.004, 0.002)
        if "Subsurface Scale" in b.inputs:
            b.inputs["Subsurface Scale"].default_value = 0.02
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m, V


def _forma(x, y, z):
    """Leva um ponto da esfera unitária para a forma da cabeça adulta: crânio mais baixo, maxilar largo e quadrado,
    queixo projetado. Largura ~0,19, altura ~0,25, profundidade ~0,22."""
    sx, sy = 0.094, 0.108
    sz = 0.118 if z > 0 else 0.132
    if z < 0:
        t = -z
        sx *= 1.0 + 0.12 * math.sin(math.pi * min(t, 1.0) * 0.8) - 0.12 * t ** 4      # maxilar largo, queixo largo
        sy *= 1.0 - 0.1 * t ** 2
        if t < 0.3 and abs(x) > 0.55:               # maçãs do rosto
            sx *= 1.04
    if z > 0.3:
        sy *= 1.0 + 0.05 * (z - 0.3)
    p = Vector((x * sx, y * sy, z * sz))
    if z < -0.5 and y < -0.1:                       # queixo à frente
        p.y -= 0.02 * (-z - 0.5) * 2
    if 0.25 < z < 0.4 and y < -0.7:                 # arco da sobrancelha
        p.y -= 0.006 * math.sin(math.pi * (z - 0.25) / 0.15)
    return p


def _cabeca_malha(name, m):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=40, radius=1.0)
    for v in bm.verts:
        v.co = _forma(*v.co)
    o = _liso(mt.mesh_obj(name, bm, m))
    _sub(o, 1)
    return o


def _cabelo_malha(name, m):
    """Cabelo curto colado na cabeça (mesma forma, inflada 5 mm), da linha da testa para cima e para trás."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=40, radius=1.0)
    apagar = []
    for v in bm.verts:
        x, y, z = v.co
        limite = 0.5 if y < -0.5 else (0.12 if y < 0.25 else -0.5)       # testa / têmporas / nuca
        if z < limite:
            apagar.append(v)
            continue
        n = Vector((x, y, z)).normalized()
        topo = min(max((z - 0.2) / 0.6, 0.0), 1.0)
        topete = 1.0 if (y < -0.45 and z > 0.5) else 0.0
        infla = 0.006 + 0.016 * topo + 0.014 * topete * topo
        v.co = _forma(x, y, z) + n * infla
    bmesh.ops.delete(bm, geom=apagar, context="VERTS")
    o = _liso(mt.mesh_obj(name, bm, m))
    so = o.modifiers.new("esp", "SOLIDIFY")
    so.thickness = 0.006
    so.offset = 1.0
    _sub(o, 2)
    return o


# ================================================================ esqueleto adulto
def _ossos():
    O = [("quadril", (0, 0, 0.95), (0, 0, 1.1), None),
         ("tronco", (0, 0, 1.1), (0, 0, 1.42), "quadril"),
         ("pescoco", (0, 0, 1.42), (0, 0, 1.53), "tronco"),
         ("cabeca", (0, 0, 1.53), (0, 0, 1.79), "pescoco")]
    for l, s in (("e", 1), ("d", -1)):
        O += [(f"coxa_{l}", (s * 0.105, 0, 0.92), (s * 0.11, -0.005, 0.5), "quadril"),
              (f"canela_{l}", (s * 0.11, -0.005, 0.5), (s * 0.115, 0, 0.1), f"coxa_{l}")]
        O += [(f"ombro_{l}", (s * 0.2, 0.01, 1.4), (s * 0.245, 0.01, 1.12), "tronco"),
              (f"cotovelo_{l}", (s * 0.245, 0.01, 1.12), (s * 0.265, -0.005, 0.87), f"ombro_{l}"),
              (f"mao_{l}", (s * 0.265, -0.005, 0.87), (s * 0.27, -0.01, 0.76), f"cotovelo_{l}")]
    return O


def _armature(name, root):
    ad = bpy.data.armatures.new(name)
    arm = mt.link(bpy.data.objects.new(name, ad))
    arm.parent = root
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for n, h, t, pai in _ossos():
        b = ad.edit_bones.new(n)
        b.head, b.tail = h, t
        if pai:
            b.parent = eb[pai]
        eb[n] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return arm


def girar(arm, osso, x=0.0, y=0.0, z=0.0):
    """Gira o osso em graus nos eixos do mundo em repouso (olhando -y): x<0 leva o braço à frente; y<0 abre o braço
    esquerdo (+x), y>0 o direito."""
    g = math.radians
    qw = Quaternion((0, 0, 1), g(z)) @ Quaternion((0, 1, 0), g(y)) @ Quaternion((1, 0, 0), g(x))
    br = arm.data.bones[osso].matrix_local.to_quaternion()
    arm.pose.bones[osso].rotation_quaternion = br.inverted() @ qw @ br


# ================================================================ mãos
def _mao(name, M, tipo, s, pulso):
    """Mão adulta (pele) no pulso apontando para -z: palma + 4 dedos + polegar. tipo: relaxada | aponta | aberta |
    punho. s = +1 mão esquerda (+x), -1 direita."""
    px, py, pz = pulso
    pele = M["ad_pele"]
    obs = [skin(f"{name}_palma", [(px, py, pz + 0.01), (px + s * 0.004, py - 0.006, pz - 0.075)], [(0, 1)],
                [(0.04, 0.022), (0.046, 0.021)], pele)]
    # dedos: (offset lateral na palma, comprimento)
    dedos = [(-0.024, 0.07), (-0.008, 0.08), (0.008, 0.076), (0.022, 0.062)]   # do indicador ao mindinho (de -s)
    for k, (dx, L) in enumerate(dedos):
        x0 = px - s * dx
        base = (x0, py - 0.008, pz - 0.075)
        estendido = (tipo == "aberta") or (tipo == "aponta" and k == 0) or (tipo == "relaxada")
        if estendido:
            curva = 0.022 if tipo == "relaxada" else 0.0
            pts = [base, (x0, py - 0.012 - curva, pz - 0.075 - L * 0.55),
                   (x0, py - 0.016 - curva * 2.2, pz - 0.075 - L)]
        else:                              # dobrado para dentro da palma (punho)
            pts = [base, (x0, py - 0.03, pz - 0.095), (x0, py - 0.022, pz - 0.075)]
        obs.append(skin(f"{name}_dedo{k}", pts, [(0, 1), (1, 2)],
                        [(0.0115, 0.0115), (0.0105, 0.0105), (0.0092, 0.0092)], pele))
    pol = [(px + s * 0.03, py - 0.01, pz - 0.015), (px + s * 0.043, py - 0.03, pz - 0.045),
           (px + s * 0.044, py - 0.042, pz - 0.07)]
    obs.append(skin(f"{name}_polegar", pol, [(0, 1), (1, 2)], [(0.0145, 0.0145), (0.013, 0.013), (0.011, 0.011)],
                    pele))
    return obs


POSES = {
    "parado": ({"ombro_e": (0, -6, 0), "ombro_d": (0, 6, 0), "cotovelo_e": (-10, 0, 0), "cotovelo_d": (-10, 0, 0)},
               "relaxada", "relaxada"),
    "aponta": ({"ombro_e": (-70, -30, 0), "cotovelo_e": (-10, 0, 0), "ombro_d": (0, 6, 0), "cotovelo_d": (-12, 0, 0)},
               "aponta", "relaxada"),
    "explica": ({"ombro_e": (-25, -18, 0), "cotovelo_e": (-60, 0, 10), "ombro_d": (-25, 18, 0),
                 "cotovelo_d": (-60, 0, -10)}, "aberta", "aberta"),
    "bracos_cruzados": ({"ombro_e": (-30, -10, 0), "cotovelo_e": (-80, 0, 70), "ombro_d": (-30, 10, 0),
                         "cotovelo_d": (-80, 0, -70)}, "punho", "punho"),
    "conta": ({"ombro_e": (-35, -15, 0), "cotovelo_e": (-75, 0, 15), "ombro_d": (0, 6, 0), "cotovelo_d": (-12, 0, 0)},
              "aponta", "relaxada"),
}


# ================================================================ o Zé adulto
def ze_adulto(name, M, pose="parado", expressao="neutro", olhar=(0.0, 0.0)):
    """Mecânico Zé, ~40 anos, 1,79 m. pose: parado | aponta | explica | bracos_cruzados | conta.
    expressao: neutro | sorriso | fala | preocupado | surpreso."""
    materiais(M)
    root = empty(name)
    Z = {"raiz": root}
    arm = _armature(name + "_esqueleto", root)
    Z["arm"] = arm
    # ---- macacão: tronco + pernas + mangas até o cotovelo (manga arregaçada)
    P = [(0, 0, 0.95), (0, -0.02, 1.06), (0, 0, 1.24), (0, 0, 1.38), (0, 0, 1.47),           # 0-4 quadril..pescoço
         (0.105, 0, 0.9), (0.11, 0, 0.72), (0.11, -0.005, 0.5), (0.11, 0.005, 0.36), (0.115, 0, 0.16),   # 5-9
         (-0.105, 0, 0.9), (-0.11, 0, 0.72), (-0.11, -0.005, 0.5), (-0.11, 0.005, 0.36), (-0.115, 0, 0.16),
         (0.2, 0.0, 1.37), (0.228, 0.01, 1.25), (0.245, 0.01, 1.13),                       # 15-17 manga esq.
         (-0.2, 0.0, 1.37), (-0.228, 0.01, 1.25), (-0.245, 0.01, 1.13)]                    # 18-20
    A = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (8, 9), (0, 10), (10, 11), (11, 12),
         (12, 13), (13, 14), (3, 15), (15, 16), (16, 17), (3, 18), (18, 19), (19, 20)]
    Rr = [(0.175, 0.135), (0.18, 0.155), (0.205, 0.15), (0.2, 0.13), (0.07, 0.065),
          (0.1, 0.098), (0.095, 0.093), (0.068, 0.068), (0.074, 0.074), (0.085, 0.085),
          (0.1, 0.098), (0.095, 0.093), (0.068, 0.068), (0.074, 0.074), (0.085, 0.085),
          (0.078, 0.07), (0.06, 0.058), (0.057, 0.057), (0.078, 0.07), (0.06, 0.058), (0.057, 0.057)]
    G = ["quadril", "quadril", "tronco", "tronco", "pescoco",
         "quadril", "coxa_e", "canela_e", "canela_e", "canela_e",
         "quadril", "coxa_d", "canela_d", "canela_d", "canela_d",
         "tronco", "ombro_e", "cotovelo_e", "tronco", "ombro_d", "cotovelo_d"]
    corpo = skin(name + "_macacao", P, A, Rr, M["ad_macacao"], parent=root)
    _deforma(corpo, arm, G)
    tx = bpy.data.textures.new(name + "_dobras", "CLOUDS")
    tx.noise_scale = 0.08
    dp = corpo.modifiers.new("dobras", "DISPLACE")
    dp.texture = tx
    dp.strength = 0.006
    dp.mid_level = 0.5
    dp.texture_coords = "LOCAL"
    Z["corpo"] = corpo
    # trapézios e cós (cintura) do macacão
    for s_ in (1, -1):
        tp = skin(f"{name}_trapezio{s_}", [(0, 0.02, 1.47), (s_ * 0.13, 0.012, 1.41)], [(0, 1)],
                  [(0.055, 0.05), (0.06, 0.05)], M["ad_macacao"], parent=root)
        _deforma(tp, arm, ["pescoco", "tronco"])
    cos = skin(name + "_cos", [(0, -0.008, 0.955), (0, -0.008, 0.99)], [(0, 1)], [(0.186, 0.148), (0.186, 0.15)],
               M["ad_macacao_esc"], parent=root)
    _deforma(cos, arm, ["quadril", "quadril"])
    # antebraços (pele) saindo da manga arregaçada + dobra da manga
    for l, s in (("e", 1), ("d", -1)):
        ab = skin(f"{name}_antebraco_{l}", [(s * 0.243, 0.01, 1.16), (s * 0.255, 0.0, 1.0), (s * 0.265, -0.005, 0.86)],
                  [(0, 1), (1, 2)], [(0.048, 0.046), (0.046, 0.042), (0.037, 0.031)], M["ad_pele"], parent=root)
        _deforma(ab, arm, [f"cotovelo_{l}", f"cotovelo_{l}", f"mao_{l}"])
        dobra = skin(f"{name}_dobra_{l}", [(s * 0.243, 0.01, 1.15), (s * 0.247, 0.01, 1.11)], [(0, 1)],
                     [(0.062, 0.06), (0.062, 0.06)], M["ad_macacao_esc"], parent=root)
        _deforma(dobra, arm, [f"cotovelo_{l}", f"cotovelo_{l}"])
    # pescoço
    pc = skin(name + "_pescoco", [(0, 0.008, 1.43), (0, 0.008, 1.535)], [(0, 1)], [(0.074, 0.07), (0.07, 0.066)],
              M["ad_pele"], parent=root)
    _deforma(pc, arm, ["tronco", "pescoco"])
    # gola com camiseta, faixas refletivas laranja (canelas e braços), bolso, pano, botas
    tronco = []
    tronco.append(skin(name + "_gola", [(-0.06, -0.03, 1.455), (0, -0.065, 1.42), (0.06, -0.03, 1.455)],
                       [(0, 1), (1, 2)], [(0.018, 0.01), (0.022, 0.012), (0.018, 0.01)], M["ad_camiseta"]))
    for s in (1, -1):
        tronco.append(skin(f"{name}_lapela{s}", [(s * 0.03, -0.085, 1.43), (s * 0.08, -0.07, 1.47)], [(0, 1)],
                           [(0.03, 0.006), (0.024, 0.006)], M["ad_macacao_esc"]))
    bo = mt.box(name + "_bolso", -0.045, 0.045, -0.006, 0.006, -0.05, 0.035, M["ad_macacao_esc"], anchor="center")
    bo.location = (0.08, -0.112, 1.3)
    _bevel(bo, 0.006)
    tronco.append(bo)
    tag = mt.box(name + "_tag", -0.035, 0.035, -0.003, 0.003, -0.012, 0.012, M["ad_faixa"], anchor="center")
    tag.location = (-0.085, -0.114, 1.33)
    _bevel(tag, 0.003)
    tronco.append(tag)
    quadril = [skin(name + "_pano", [(-0.08, 0.1, 0.94), (-0.09, 0.122, 0.85), (-0.095, 0.12, 0.76)],
                    [(0, 1), (1, 2)], [(0.035, 0.008), (0.032, 0.008), (0.028, 0.008)], M["ad_pano"])]
    canelas = {"e": [], "d": []}
    for l, x in (("e", 0.115), ("d", -0.115)):
        c = canelas[l]
        c.append(skin(f"{name}_faixa_perna_{l}", [(x, 0, 0.3), (x, 0, 0.34)], [(0, 1)],
                      [(0.078, 0.078), (0.078, 0.078)], M["ad_faixa"]))
        c.append(skin(f"{name}_refl_perna_{l}", [(x, 0, 0.312), (x, 0, 0.328)], [(0, 1)],
                      [(0.0792, 0.0792), (0.0792, 0.0792)], M["ad_refletivo"]))
        c.append(skin(f"{name}_barra_{l}", [(x, 0, 0.13), (x, 0, 0.165)], [(0, 1)], [(0.088, 0.088), (0.087, 0.087)],
                      M["ad_macacao_esc"]))
        c.append(skin(f"{name}_bota_{l}", [(x, 0.02, 0.14), (x, -0.005, 0.06), (x, -0.13, 0.05)],
                      [(0, 1), (1, 2)], [(0.07, 0.07), (0.074, 0.054), (0.06, 0.042)], M["ad_bota"]))
        c.append(skin(f"{name}_sola_{l}", [(x, 0.035, 0.014), (x, -0.15, 0.014)], [(0, 1)],
                      [(0.07, 0.014), (0.064, 0.014)], M["ad_sola"]))
        # bolso de chapa na lateral da coxa
        bc = mt.box(f"{name}_bolso_coxa_{l}", -0.006, 0.006, -0.05, 0.05, -0.06, 0.06, M["ad_macacao_esc"],
                    anchor="center")
        bc.location = (x + (0.098 if x > 0 else -0.098), 0, 0.7)
        _bevel(bc, 0.005)
        c_coxa = bc
        c_coxa.parent = root
        _no_osso(c_coxa, arm, f"coxa_{l}")
    for l in ("e", "d"):
        for o in canelas[l]:
            o.parent = root
            _no_osso(o, arm, f"canela_{l}")
    for o in tronco:
        o.parent = root
        _no_osso(o, arm, "tronco")
    for o in quadril:
        o.parent = root
        _no_osso(o, arm, "quadril")
    # ---- cabeça
    P0 = {"neutro": dict(sorriso=0.15), "sorriso": dict(sorriso=0.9), "fala": dict(sorriso=0.35, boca_aberta=0.8,
                                                                                    sobr_alt=0.5),
          "preocupado": dict(sorriso=-0.4, sobr_inc=-0.35, sobr_alt=0.6),
          "surpreso": dict(sorriso=0.0, boca_aberta=1.0, sobr_alt=1.4, abre_olho=1.25)}[expressao]
    P0 = dict(P0, olhar_x=olhar[0], olhar_z=olhar[1])
    mr, V = _rosto(f"{name}_rosto", P0)
    Z["rosto"] = V
    cab = empty(name + "_cabeca")
    cab.parent = root
    cab.location = (0, 0, 1.5 + 0.135)
    cab.scale = (1.07, 1.07, 1.07)          # cabeça um pouco maior: lê no celular sem virar "boneca"
    _cabeca_malha(name + "_cabeca_m", mr).parent = cab
    # nariz em cunha (geometria) + orelhas + cabelo curto
    nz = skin(name + "_nariz", [(0, -0.1, 0.012), (0, -0.112, -0.012), (0, -0.122, -0.03)], [(0, 1), (1, 2)],
              [(0.008, 0.006), (0.011, 0.009), (0.016, 0.012)], M["ad_pele"])
    nz.parent = cab
    for s in (1, -1):
        esfera(f"{name}_orelha{s}", 0.026, (s * 0.094, 0.01, 0.0), M["ad_pele"], scale=(0.4, 0.75, 1.15), seg=24,
               parent=cab)
    _cabelo_malha(name + "_cabelo", M["ad_cabelo"]).parent = cab
    _no_osso(cab, arm, "cabeca")
    Z["cabeca"] = cab
    # ---- mãos por pose
    rot, me, md = POSES[pose]
    for l, s, tipo in (("e", 1, me), ("d", -1, md)):
        pulso = (s * 0.265, -0.005, 0.87)
        for o in _mao(f"{name}_mao_{l}", M, tipo, s, pulso):
            o.parent = root
            _no_osso(o, arm, f"mao_{l}")
    base = {"tronco": (0, -3, 0), "cabeca": (0, 3, 6), "coxa_e": (-8, -4, -6), "canela_e": (14, 0, 0),
            "coxa_d": (0, 2, 0)}                     # contrapposto: peso na perna direita, joelho esquerdo solto
    for osso, rv in base.items():
        if osso not in rot:
            girar(arm, osso, *rv)
    for osso, (x, y, z) in rot.items():
        girar(arm, osso, x, y, z)
    bpy.context.view_layer.update()
    return Z


# ================================================================ oficina de verdade (limpa)
def oficina(M, largura=9.0, fundo_y=2.2):
    """Piso de concreto polido, parede de bloco pintada, faixa amarela de segurança no piso, carrinho de ferramentas
    vermelho, painel de ferramentas e barras de luz no teto (emissivas)."""
    def pbr(n, c, rough=0.6, coat=0.0, metal=0.0, emit=0.0):
        k = "of_" + n
        if k not in M:
            M[k] = _pbr(k, c, rough=rough, coat=coat, metal=metal)
            if emit:
                b = mt.bsdf(M[k])
                b.inputs["Emission Color"].default_value = lin(c)
                b.inputs["Emission Strength"].default_value = emit
        return M[k]

    root = empty("oficina")
    # piso concreto polido (cor com ruído suave)
    piso = pbr("piso", "#6E737A", rough=0.32)
    nt = piso.node_tree
    tx = nt.nodes.new("ShaderNodeTexNoise"); tx.inputs["Scale"].default_value = 3.0
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = lin("#5E636A"); rp.color_ramp.elements[1].color = lin("#7A7F86")
    nt.links.new(tx.outputs["Fac"], rp.inputs["Fac"])
    nt.links.new(rp.outputs["Color"], mt.bsdf(piso).inputs["Base Color"])
    mt.box("piso", -largura / 2, largura / 2, -6, fundo_y, -0.02, 0, piso).parent = root
    # parede de bloco: tijolo procedural em tons de grafite
    par = pbr("parede", "#4A5059", rough=0.85)
    nt = par.node_tree
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = lin("#4A5059"); br.inputs["Color2"].default_value = lin("#474D55")
    br.inputs["Mortar"].default_value = lin("#3A3F46")
    br.inputs["Scale"].default_value = 1.4
    br.inputs["Mortar Size"].default_value = 0.012
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], mt.bsdf(par).inputs["Base Color"])
    mt.box("parede", -largura / 2, largura / 2, fundo_y, fundo_y + 0.1, 0, 4.0, par).parent = root
    # faixa laranja na parede (meia-parede pintada) + faixa amarela de segurança no piso
    mt.box("meia_parede", -largura / 2, largura / 2, fundo_y - 0.005, fundo_y, 0, 1.1, pbr("meia", "#3A4A5C", 0.7)).parent = root
    mt.box("filete", -largura / 2, largura / 2, fundo_y - 0.008, fundo_y, 1.1, 1.16, pbr("filete", "#E8590C", 0.6)).parent = root
    mt.box("seg", -largura / 2, largura / 2, fundo_y - 0.6, fundo_y - 0.5, 0, 0.002, pbr("seg", "#F2B705", 0.5)).parent = root
    # carrinho de ferramentas vermelho
    cr = pbr("carrinho", "#C81E24", rough=0.3, coat=0.6)
    c = mt.box("carrinho", -0.32, 0.32, -0.24, 0.24, 0.1, 0.95, cr)
    c.location = (1.7, fundo_y - 0.45, 0.1)
    _bevel(c, 0.015)
    c.parent = root
    for k in range(4):
        g = mt.box(f"gaveta{k}", -0.29, 0.29, -0.006, 0.006, -0.08, 0.08, pbr("puxador", "#B9C0C8", 0.25, metal=1.0))
        g.location = (1.7, fundo_y - 0.695, 0.32 + k * 0.19)
        g.scale = (1, 1, 0.08)
        g.parent = root
    # painel perfurado com ferramentas (silhuetas simples)
    pn = mt.box("painel", -0.9, 0.9, -0.01, 0.01, 1.35, 2.25, pbr("painel", "#2B3038", 0.7))
    pn.location = (-1.6, fundo_y - 0.02, 1.35)
    pn.parent = root
    for k in range(5):        # chaves combinadas penduradas (cabo + duas cabeças), em degraus de tamanho
        L = 0.14 + 0.03 * k
        x = -2.15 + k * 0.28
        cabo = skin(f"chave_cabo{k}", [(x, fundo_y - 0.035, 1.95), (x, fundo_y - 0.035, 1.95 - L)], [(0, 1)],
                    [(0.012, 0.004), (0.012, 0.004)], pbr("ferr", "#B9C0C8", 0.25, metal=1.0))
        cabo.parent = root
        for z in (1.95, 1.95 - L):
            esfera(f"chave_cab{k}{z:.2f}", 0.022, (x, fundo_y - 0.035, z), pbr("ferr", "#B9C0C8", 0.25, metal=1.0),
                   scale=(1, 0.3, 1), seg=20, parent=root)
    # barras de luz no teto (emissivas, aparecem nos reflexos)
    for k in range(3):
        b = mt.box(f"luz_teto{k}", -1.0, 1.0, -0.04, 0.04, -0.02, 0.02, pbr("tubo", "#FFFFFF", 0.3, emit=6.0))
        b.location = (0, -1.5 + k * 1.5, 5.0)
        b.parent = root
    return root
