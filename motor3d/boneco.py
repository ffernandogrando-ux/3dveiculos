"""Mascote humano do canal de veículos: o mecânico "Zé" (briefing do diretor de arte, 12/11/2026).

Dois acabamentos com a MESMA geometria e o mesmo rosto:
- estilo="vinil": 3D liso tipo brinquedo de vinil (Principled acetinado, AgX, luz clara de 3 pontos).
- estilo="toon": "2D" chapado (cor por emissão em 2 tons pela normal x direção de luz fixa) + linhas Freestyle.

Regras do acabamento (o que deixou a proposta anterior "torta"):
- corpo e membros são malhas inteiriças (modificador Skin + Subdivision), nada de bolinhas encostadas;
- rosto PINTADO no shader da cabeça (olhos, brilhos, sobrancelhas, boca, bochechas), simétrico por construção;
- nenhuma escala não uniforme herdada por filhos de rosto.

Uso:
    M = {}
    Z = mecanico("ze", M, estilo="vinil", pose="aponta", expressao="fala")
    Z["raiz"], Z["cabeca"], Z["braco_e"], Z["braco_d"] (empties nos ombros: gire para posar), Z["rosto"] (dict de
    nós Value do shader do rosto: abre_olho, olhar_x, olhar_z, sobr_alt, sobr_inc, boca_sorriso, boca_aberta, boca_o
    — dá para keyframar: Z["rosto"]["abre_olho"].outputs[0].default_value).
Olha para -y; origem entre os pés. Altura ≈ 1,26 m (3 cabeças).
"""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
import motor as mt
from motor import lin, empty

COR = {"pele": "#F2B98F", "pele_quente": "#E39A74", "pele_borda": "#F7C9A3", "cabelo": "#4A2E22",
       "macacao": "#2F67D8", "macacao_escuro": "#2552AE", "camiseta": "#FFF4E0", "bone": "#FF7A1A",
       "aba": "#2F67D8", "bota": "#2B2F3A", "sola": "#1E2329", "cinto": "#3A4256", "pano": "#E5484D",
       "chave": "#FFC928", "boca": "#7A2E2E", "lingua": "#E5484D", "bochecha": "#F08A7A", "olho": "#1B1B22",
       "ziper": "#C9D0DA", "emblema": "#FFF4E0"}

LUZ_TOON = Vector((-0.35, -0.8, 0.5)).normalized()     # direção fixa da "luz" do 2D (de frente-esquerda-cima)


# ================================================================ materiais
def _vinil(name, hexcol, rough=0.42, coat=0.0):
    m = mt.mat(name, hexcol, rough=rough)
    b = mt.bsdf(m)
    for k, v in (("Specular IOR Level", 0.5), ("Coat Weight", coat), ("Coat Roughness", 0.15)):
        if k in b.inputs:
            b.inputs[k].default_value = v
    return m


def _toon_nos(nt, cor_socket_ou_hex, sombra=0.74, tom="#5A4E8C", brilho=0.0):
    """Monta no node tree a cor 'toon' (2 tons + brilho opcional) e devolve o socket de cor final (emissão)."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = LUZ_TOON
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.interpolation = "CONSTANT"
    e = rampa.color_ramp.elements
    e[0].position, e[0].color = 0.0, (sombra, sombra, sombra, 1)
    e[1].position, e[1].color = 0.3, (1, 1, 1, 1)
    if brilho:
        el = e.new(0.93)
        el.color = (1 + brilho, 1 + brilho, 1 + brilho, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    nt.links.new(dot.outputs["Value"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], rampa.inputs["Fac"])
    # sombra puxada para o roxo/azul: mistura multiplicativa com um tom frio
    tint = nt.nodes.new("ShaderNodeMix"); tint.data_type = "RGBA"; tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    nt.links.new(rampa.outputs["Color"], tint.inputs["B"])
    if isinstance(cor_socket_ou_hex, str):
        tint.inputs["A"].default_value = lin(cor_socket_ou_hex)
    else:
        nt.links.new(cor_socket_ou_hex, tint.inputs["A"])
    fria = nt.nodes.new("ShaderNodeMix"); fria.data_type = "RGBA"; fria.blend_type = "MULTIPLY"
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "LESS_THAN"; inv.inputs[1].default_value = 0.3
    nt.links.new(mr.outputs["Result"], inv.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 0.35
    nt.links.new(inv.outputs[0], mul.inputs[0])
    nt.links.new(mul.outputs[0], fria.inputs["Factor"])
    nt.links.new(tint.outputs[2], fria.inputs["A"])
    fria.inputs["B"].default_value = lin(tom)
    return fria.outputs[2]


def _toon(name, hexcol, sombra=0.74, brilho=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(_toon_nos(nt, hexcol, sombra, brilho=brilho), em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def material(M, nome, estilo, rough=0.42, coat=0.0, brilho=0.0):
    k = f"{nome}_{estilo}"
    if k not in M:
        M[k] = _vinil(k, COR[nome], rough, coat) if estilo == "vinil" else _toon(k, COR[nome], brilho=brilho)
    return M[k]


# ================================================================ rosto pintado
def _rosto_mat(name, estilo, R, P):
    """Material da cabeça com o rosto pintado em coordenadas do objeto (cabeça centrada na origem, raio R,
    frente = -y). P: parâmetros iniciais. Devolve (material, dict de nós Value animáveis)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    X, Y, Z = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
    V = {}

    def val(nome, v):
        n = nt.nodes.new("ShaderNodeValue")
        n.name = n.label = nome
        n.outputs[0].default_value = v
        V[nome] = n
        return n.outputs[0]

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

    def elipse(cx, cz, a, b, xs=X):
        """< 1 dentro da elipse (cx, cz podem ser sockets)."""
        dx = op("DIVIDE", op("SUBTRACT", xs, cx), a)
        dz = op("DIVIDE", op("SUBTRACT", Z, cz), b)
        return op("ADD", op("MULTIPLY", dx, dx), op("MULTIPLY", dz, dz))

    def dentro(e, borda=0.08):
        """máscara suave 0..1 (1 dentro) com borda antisserrilhada."""
        return op("SUBTRACT", 1.0, op("MINIMUM", op("MAXIMUM", op("DIVIDE", op("SUBTRACT", e, 1.0 - borda), borda), 0.0),
                                       1.0))

    frente = op("LESS_THAN", Y, -R * 0.2)
    abre = val("abre_olho", P.get("abre_olho", 1.0))
    ox = val("olhar_x", P.get("olhar_x", 0.0))
    oz = val("olhar_z", P.get("olhar_z", 0.0))
    s_alt = val("sobr_alt", P.get("sobr_alt", 0.0))
    s_inc = val("sobr_inc", P.get("sobr_inc", 0.0))
    b_sor = val("boca_sorriso", P.get("boca_sorriso", 1.0))
    b_abe = val("boca_aberta", P.get("boca_aberta", 0.0))
    b_o = val("boca_o", P.get("boca_o", 0.0))

    # medidas do briefing em "cabeças" (H = 2R)
    H = 2 * R
    ex, ez, ea, eb = 0.2 * H, -R + 0.42 * H, 0.065 * H, 0.1 * H
    eb_s = op("MULTIPLY", abre, eb)
    olho = 0.0
    luz = 0.0
    for lado in (-1, 1):
        cx = op("ADD", lado * ex, op("MULTIPLY", ox, ea * 0.35))
        cz = op("ADD", ez, op("MULTIPLY", oz, eb * 0.3))
        e = elipse(cx, cz, ea, op("MAXIMUM", eb_s, 0.004))
        mo = dentro(e, 0.12)
        olho = mo if olho == 0.0 else op("MAXIMUM", olho, mo)
        # brilhos (sempre do mesmo lado: em cima à esquerda da imagem = +x do personagem visto de frente é -x)
        l1 = dentro(elipse(op("ADD", cx, -ea * 0.32), op("ADD", cz, eb * 0.38), ea * 0.34, ea * 0.34), 0.2)
        l2 = dentro(elipse(op("ADD", cx, ea * 0.3), op("ADD", cz, -eb * 0.42), ea * 0.16, ea * 0.16), 0.25)
        lm = op("MULTIPLY", op("MAXIMUM", l1, l2), op("GREATER_THAN", abre, 0.35))
        luz = lm if luz == 0.0 else op("MAXIMUM", luz, lm)
    # sobrancelhas: barra arredondada inclinável (s_inc > 0: ponta de dentro sobe = preocupado)
    AX = op("ABSOLUTE", X)
    bz = op("ADD", ez + eb + 0.08 * H * 0.75, op("MULTIPLY", s_alt, 0.05 * H))
    zt = op("SUBTRACT", Z, op("ADD", bz, op("MULTIPLY", s_inc, op("SUBTRACT", ex, AX))))
    dxs = op("DIVIDE", op("SUBTRACT", AX, ex), 0.075 * H)
    dzs = op("DIVIDE", zt, 0.0175 * H)
    sob = dentro(op("ADD", op("POWER", op("ABSOLUTE", dxs), 4.0), op("MULTIPLY", dzs, dzs)), 0.15)
    # bochechas (degradê 40 %)
    ec = elipse(ex * 1.25, ez - eb * 1.25, 0.075 * H, 0.05 * H, xs=AX)
    boch = op("MULTIPLY", op("MAXIMUM", op("SUBTRACT", 1.0, ec), 0.0), 0.4)
    # boca
    mz = -R + 0.24 * H
    ma, mb = 0.07 * H, 0.05 * H
    em_ = elipse(0.0, mz, ma, mb)
    abaixo = op("LESS_THAN", Z, mz + 0.002)
    anel = op("MULTIPLY", dentro(em_, 0.12), op("SUBTRACT", 1.0, dentro(elipse(0.0, mz + mb * 0.08, ma * 0.78, mb * 0.62),
                                                                       0.12)))
    sorriso = op("MULTIPLY", op("MULTIPLY", anel, abaixo), b_sor)
    d_ab = op("MULTIPLY", op("MULTIPLY", dentro(elipse(0.0, mz, ma * 1.05, mb * 1.6), 0.08), abaixo), b_abe)
    lingua = op("MULTIPLY", d_ab, dentro(elipse(0.0, mz - mb * 1.25, ma * 0.6, mb * 0.6), 0.15))
    bo = op("MULTIPLY", dentro(elipse(0.0, mz - mb * 0.4, ma * 0.42, mb * 0.85), 0.12), b_o)
    boca = op("MAXIMUM", op("MAXIMUM", sorriso, d_ab), bo)

    def mix(base, fator, hexcol):
        n = nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"
        nt.links.new(op("MULTIPLY", fator, frente), n.inputs["Factor"])
        if isinstance(base, str):
            n.inputs["A"].default_value = lin(base)
        else:
            nt.links.new(base, n.inputs["A"])
        n.inputs["B"].default_value = lin(hexcol)
        return n.outputs[2]

    # pele com borda mais clara (vida no vinil)
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    pele = nt.nodes.new("ShaderNodeMix"); pele.data_type = "RGBA"
    pele.inputs["A"].default_value = lin(COR["pele"]); pele.inputs["B"].default_value = lin(COR["pele_borda"])
    nt.links.new(op("MULTIPLY", lw.outputs["Facing"], 0.6 if estilo == "vinil" else 0.0), pele.inputs["Factor"])
    c = pele.outputs[2]
    c = mix(c, boch, COR["bochecha"])
    c = mix(c, boca, COR["boca"])
    c = mix(c, lingua, COR["lingua"])
    c = mix(c, olho, COR["olho"])
    c = mix(c, luz, "#FFFFFF")
    c = mix(c, sob, COR["cabelo"])
    if estilo == "vinil":
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(c, b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.42
        for k, v in (("Specular IOR Level", 0.5), ("Coat Weight", 0.15), ("Coat Roughness", 0.15)):
            if k in b.inputs:
                b.inputs[k].default_value = v
        nt.links.new(b.outputs[0], out.inputs["Surface"])
    else:
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(_toon_nos(nt, c, brilho=0.08), em.inputs["Color"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m, V


# ================================================================ geometria
def _liso(o):
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def _sub(o, n=2):
    s = o.modifiers.new("sub", "SUBSURF")
    s.levels, s.render_levels = min(n, 2), n
    return o


def skin(name, pts, arestas, raios, m, sub=2, parent=None):
    """Malha inteiriça lisa: esqueleto de pontos + raios (rx, ry) → Skin + Subdivision."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], arestas, [])
    me.update()
    o = mt.link(bpy.data.objects.new(name, me))
    sk = o.modifiers.new("skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.6
    for i, r in enumerate(raios):
        o.data.skin_vertices[0].data[i].radius = r if isinstance(r, (tuple, list)) else (r, r)
    o.data.skin_vertices[0].data[0].use_root = True
    _sub(o, sub)
    o.data.materials.append(m)
    if parent:
        o.parent = parent
    return o


def esfera(name, r, loc, m, scale=(1, 1, 1), seg=48, parent=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r,
                              matrix=Matrix.Diagonal((*scale, 1)))
    o = _liso(mt.mesh_obj(name, bm, m, loc))
    if parent:
        o.parent = parent
    return o


def toro(name, R, r, m, loc=(0, 0, 0), eixo="z", parent=None, seg=48):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, segments=seg, radius=R)
    o = mt.mesh_obj(name, bm, m, loc)
    # tubo por Skin seria pesado; usa curva → malha simples via Screw não; aqui: círculo + Skin com raio r
    sk = o.modifiers.new("skin", "SKIN")
    sk.use_smooth_shade = True
    for v in o.data.skin_vertices[0].data:
        v.radius = (r, r)
    _sub(o, 2)
    if eixo == "y":
        o.rotation_euler = (math.radians(90), 0, 0)
    elif eixo == "x":
        o.rotation_euler = (0, math.radians(90), 0)
    if parent:
        o.parent = parent
    return o


# ================================================================ esqueleto (armature)
OSSOS = [  # nome, cabeça, cauda, pai
    ("quadril", (0, 0, 0.47), (0, 0, 0.6), None),
    ("tronco", (0, 0, 0.6), (0, 0, 0.78), "quadril"),
    ("pescoco", (0, 0, 0.78), (0, 0, 0.87), "tronco"),
    ("cabeca", (0, 0, 0.87), (0, 0, 1.12), "pescoco"),
]
for _l, _sx in (("e", 1), ("d", -1)):
    OSSOS += [(f"ombro_{_l}", (_sx * 0.15, 0, 0.74), (_sx * 0.175, 0, 0.6), "tronco"),
              (f"cotovelo_{_l}", (_sx * 0.175, 0, 0.6), (_sx * 0.185, -0.008, 0.47), f"ombro_{_l}"),
              (f"mao_{_l}", (_sx * 0.185, -0.008, 0.47), (_sx * 0.185, -0.012, 0.4), f"cotovelo_{_l}")]


def _armature(name, root):
    ad = bpy.data.armatures.new(name)
    arm = mt.link(bpy.data.objects.new(name, ad))
    arm.parent = root
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for n, h, t, pai in OSSOS:
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
    """Gira um osso em graus nos eixos do MUNDO em repouso (personagem olhando -y): x<0 leva o braço para a frente,
    y<0 abre o braço esquerdo (+x) para fora (y>0 o direito)."""
    from mathutils import Quaternion
    g = math.radians
    qw = Quaternion((0, 0, 1), g(z)) @ Quaternion((0, 1, 0), g(y)) @ Quaternion((1, 0, 0), g(x))
    br = arm.data.bones[osso].matrix_local.to_quaternion()
    arm.pose.bones[osso].rotation_quaternion = br.inverted() @ qw @ br


def _deforma(o, arm, grupos):
    """Liga a malha-esqueleto (Skin) ao armature: grupos = lista com o nome do osso de cada vértice."""
    for i, n in enumerate(grupos):
        vg = o.vertex_groups.get(n) or o.vertex_groups.new(name=n)
        vg.add([i], 1.0, "REPLACE")
    md = o.modifiers.new("arm", "ARMATURE")
    md.object = arm
    o.modifiers.move(len(o.modifiers) - 1, 0)       # o armature deforma o esqueleto ANTES do Skin
    return o


def _no_osso(o, arm, osso):
    """Prende o objeto ao osso mantendo a posição atual no mundo."""
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    o.parent = arm
    o.parent_type = "BONE"
    o.parent_bone = osso
    bpy.context.view_layer.update()
    o.matrix_world = mw
    return o


# ================================================================ o mecânico
def _mao(name, M, mat, tipo, sx, pulso):
    """Mão de luva gordinha (pele) no pulso, apontando para -z. tipo: 'aberta' | 'aponta' | 'joinha' | 'segura'."""
    px, py, pz = pulso
    pele = mat("pele", rough=0.42, coat=0.15)
    obs = []
    palma = [(px, py, pz + 0.03), (px, py - 0.004, pz - 0.035)]
    obs.append(skin(f"{name}_palma", palma, [(0, 1)], [(0.046, 0.032), (0.05, 0.034)], pele))
    if tipo in ("aberta", "aponta"):
        nd = 3 if tipo == "aberta" else 1
        xs = (-0.022, 0.0, 0.022) if nd == 3 else (sx * -0.012,)
        L = 0.05 if tipo == "aberta" else 0.075
        for k, dx in enumerate(xs):
            obs.append(skin(f"{name}_dedo{k}", [(px + dx, py - 0.006, pz - 0.05), (px + dx * 1.15, py - 0.01, pz - 0.05 - L)],
                            [(0, 1)], [(0.017, 0.017), (0.016, 0.016)], pele))
        if tipo == "aponta":      # outros dedos dobrados = punho
            obs.append(skin(f"{name}_punho", [(px + sx * 0.012, py - 0.012, pz - 0.05), (px + sx * 0.012, py - 0.02,
                                                                                        pz - 0.06)],
                            [(0, 1)], [(0.03, 0.026), (0.028, 0.024)], pele))
    else:                          # punho fechado (joinha / segurando)
        obs.append(skin(f"{name}_punho", [(px, py - 0.008, pz - 0.05), (px, py - 0.016, pz - 0.065)], [(0, 1)],
                        [(0.046, 0.034), (0.044, 0.03)], pele))
    # polegar: no joinha aponta para -y local (fica "para cima" com o antebraço erguido)
    if tipo == "joinha":
        pol = [(px - sx * 0.02, py - 0.03, pz - 0.035), (px - sx * 0.02, py - 0.075, pz - 0.03)]
    else:
        pol = [(px - sx * 0.035, py - 0.012, pz - 0.01), (px - sx * 0.05, py - 0.022, pz - 0.04)]
    obs.append(skin(f"{name}_polegar", pol, [(0, 1)], [(0.02, 0.02), (0.018, 0.018)], pele))
    return obs


POSES = {   # osso: (x, y, z) em graus no mundo, + mão esquerda / direita
    "parado": ({"ombro_e": (0, -8, 0), "ombro_d": (0, 8, 0), "cotovelo_e": (-12, 0, 0), "cotovelo_d": (-12, 0, 0)},
               "aberta", "segura"),
    "aponta": ({"ombro_e": (-75, -35, 0), "cotovelo_e": (-8, 0, 0), "ombro_d": (0, 8, 0), "cotovelo_d": (-15, 0, 0)},
               "aponta", "segura"),
    "joinha": ({"ombro_e": (-40, -18, 0), "cotovelo_e": (-75, 0, 0), "ombro_d": (0, 8, 0), "cotovelo_d": (-15, 0, 0)},
               "joinha", "segura"),
    "explica": ({"ombro_e": (-35, -28, 0), "cotovelo_e": (-55, 0, 0), "ombro_d": (-35, 28, 0),
                 "cotovelo_d": (-55, 0, 0)}, "aberta", "aberta"),
    "espanto": ({"ombro_e": (-15, -125, 0), "cotovelo_e": (-35, 0, 0), "ombro_d": (-15, 125, 0),
                 "cotovelo_d": (-35, 0, 0)}, "aberta", "aberta"),
}


def mecanico(name, M, estilo="vinil", pose="parado", expressao="sorriso", olhar=(0.0, 0.0), chave=True):
    """Mecânico "Zé" com esqueleto (Z["arm"]; gire os ossos com girar(Z["arm"], osso, x, y, z)).
    pose: 'parado' | 'aponta' | 'joinha' | 'explica' | 'espanto'.
    expressao: 'sorriso' | 'fala' | 'espanto' | 'preocupado' | 'pisca'."""
    mat = lambda n, **k: material(M, n, estilo, **k)
    root = empty(name)
    Z = {"raiz": root}
    R = 0.21                          # raio da cabeça (cabeça = 0,42 ≈ 1/3 da altura)
    arm = _armature(name + "_esqueleto", root)
    Z["arm"] = arm
    # ---- macacão: pernas + tronco + mangas até o cotovelo, numa malha só (ombro sem emenda)
    P = [(0, 0, 0.47), (0, 0, 0.58), (0, 0, 0.7), (0, 0, 0.775),                 # 0-3
         (0.105, 0, 0.37), (0.105, 0, 0.2), (0.105, -0.004, 0.095),             # 4-6 perna esq. (+x)
         (-0.105, 0, 0.37), (-0.105, 0, 0.2), (-0.105, -0.004, 0.095),          # 7-9
         (0.15, 0, 0.735), (0.165, 0, 0.66), (0.175, 0, 0.6),                    # 10-12 manga esq.
         (-0.15, 0, 0.735), (-0.165, 0, 0.66), (-0.175, 0, 0.6)]                 # 13-15
    A = [(0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6), (0, 7), (7, 8), (8, 9), (2, 10), (10, 11), (11, 12),
         (2, 13), (13, 14), (14, 15)]
    Rr = [(0.145, 0.118), (0.168, 0.13), (0.162, 0.125), (0.08, 0.072),
          (0.085, 0.08), (0.074, 0.072), (0.08, 0.078), (0.085, 0.08), (0.074, 0.072), (0.08, 0.078),
          (0.06, 0.058), (0.053, 0.053), (0.057, 0.057), (0.06, 0.058), (0.053, 0.053), (0.057, 0.057)]
    G = ["quadril", "tronco", "tronco", "tronco", "quadril", "quadril", "quadril", "quadril", "quadril", "quadril",
         "tronco", "ombro_e", "cotovelo_e", "tronco", "ombro_d", "cotovelo_d"]
    corpo = skin(name + "_macacao", P, A, Rr, mat("macacao", rough=0.45), parent=root)
    _deforma(corpo, arm, G)
    Z["corpo"] = corpo
    # antebraços (pele) saindo de dentro da manga
    for l, sx in (("e", 1), ("d", -1)):
        ab = skin(f"{name}_antebraco_{l}", [(sx * 0.172, 0, 0.63), (sx * 0.18, -0.004, 0.54), (sx * 0.185, -0.008, 0.455)],
                  [(0, 1), (1, 2)], [(0.046, 0.046), (0.047, 0.047), (0.043, 0.043)],
                  mat("pele", rough=0.42, coat=0.15), parent=root)
        _deforma(ab, arm, [f"cotovelo_{l}", f"cotovelo_{l}", f"mao_{l}"])
    # pescoço de pele
    pc = skin(name + "_pescoco", [(0, 0.005, 0.76), (0, 0.005, 0.89)], [(0, 1)], [(0.055, 0.052), (0.055, 0.052)],
              mat("pele", rough=0.42, coat=0.15), parent=root)
    _deforma(pc, arm, ["tronco", "pescoco"])
    # gola em V da camiseta, zíper, bolso, cinto, pano no bolso de trás (presos ao tronco)
    pecas_tronco = [esfera(name + "_gola", 0.075, (0, -0.035, 0.775), mat("camiseta"), scale=(1.1, 0.8, 0.35))]
    zp = mt.box(name + "_ziper", -0.005, 0.005, -0.004, 0.004, 0.0, 0.25, mat("ziper", rough=0.35), anchor="bottom")
    zp.location = (0, -0.128, 0.49)
    zp.rotation_euler = (math.radians(4), 0, 0)
    bo = mt.box(name + "_bolso", -0.042, 0.042, -0.005, 0.005, -0.032, 0.032, mat("macacao_escuro", rough=0.5),
                anchor="center")
    bo.location = (-0.07, -0.112, 0.69)
    bo.rotation_euler = (math.radians(-14), 0, 0)
    _bevel(bo, 0.012)
    pecas_tronco += [zp, bo]
    pecas_quadril = [skin(name + "_cinto", [(0, 0, 0.465), (0, 0, 0.495)], [(0, 1)],
                          [(0.163, 0.13), (0.166, 0.132)], mat("cinto", rough=0.5)),
                     skin(name + "_pano", [(0.06, 0.12, 0.47), (0.07, 0.145, 0.4), (0.075, 0.145, 0.33)],
                          [(0, 1), (1, 2)], [(0.035, 0.012), (0.03, 0.01), (0.026, 0.01)], mat("pano", rough=0.7))]
    # botas (peça única, bico redondo)
    for x in (0.105, -0.105):
        pecas_quadril.append(skin(f"{name}_bota{x:+.2f}", [(x, 0.02, 0.1), (x, -0.01, 0.055), (x, -0.09, 0.045)],
                                  [(0, 1), (1, 2)], [(0.07, 0.06), (0.078, 0.05), (0.066, 0.045)],
                                  mat("bota", rough=0.35)))
    for o in pecas_tronco:
        o.parent = root
        _no_osso(o, arm, "tronco")
    for o in pecas_quadril:
        o.parent = root
        _no_osso(o, arm, "quadril")
    # ---- cabeça (presa ao osso da cabeça)
    zc = 0.8 + R * 0.92
    cab = empty(name + "_cabeca")
    cab.parent = root
    cab.location = (0, 0, zc)
    Z["cabeca"] = cab
    P0 = {"sorriso": dict(), "fala": dict(boca_sorriso=0, boca_aberta=1, sobr_alt=0.4),
          "espanto": dict(boca_sorriso=0, boca_o=1, sobr_alt=1.0, abre_olho=1.15),
          "preocupado": dict(boca_sorriso=0, boca_o=0.0, sobr_inc=0.35, sobr_alt=0.3),
          "pisca": dict(abre_olho=0.08)}[expressao]
    P0 = dict(P0, olhar_x=olhar[0], olhar_z=olhar[1])
    mr, V = _rosto_mat(f"{name}_rosto_{estilo}", estilo, R, P0)
    Z["rosto"] = V
    esfera(name + "_cabeca_m", R, (0, 0, 0), mr, scale=(1.05, 0.98, 1.0), seg=64, parent=cab)
    esfera(name + "_nariz", 0.019, (0, -R * 0.99, -R + 0.36 * 2 * R), mat("pele_quente", rough=0.42), seg=24,
           scale=(1.15, 1, 0.9), parent=cab)
    for sx in (-1, 1):
        esfera(f"{name}_orelha{sx}", 0.04, (sx * R * 1.02, 0.01, -R + 0.42 * 2 * R), mat("pele", rough=0.42),
               scale=(0.45, 0.8, 1.0), seg=24, parent=cab)
    # cabelo: nuca/costeletas + franja aparecendo sob a aba
    esfera(name + "_cabelo", R * 1.02, (0, R * 0.1, -R * 0.04), mat("cabelo", rough=0.5), scale=(1.05, 0.95, 0.9),
           parent=cab)
    fr = esfera(name + "_franja", R * 0.5, (0, -R * 0.86, R * 0.2), mat("cabelo", rough=0.5), scale=(1.3, 0.35, 0.22),
                seg=32, parent=cab)
    fr.rotation_euler = (math.radians(-20), 0, 0)
    # boné (copa baixa + aba encostada; sem bolinha no topo) + emblema creme de frente
    copa = esfera(name + "_bone", R * 1.07, (0, R * 0.03, R * 0.16), mat("bone", rough=0.45, coat=0.15),
                  scale=(1.04, 1.02, 0.84), parent=cab)
    _corta_baixo(copa, 0.0)
    aba = esfera(name + "_aba", R * 0.8, (0, -R * 1.0, R * 0.27), mat("aba", rough=0.45), scale=(1.0, 0.85, 0.05),
                 parent=cab)
    aba.rotation_euler = (math.radians(-6), 0, 0)
    esfera(name + "_emblema", R * 0.14, (0, -R * 1.0, R * 0.56), mat("emblema", rough=0.5), scale=(1, 0.2, 1),
           seg=32, parent=cab).rotation_euler = (math.radians(-25), 0, 0)
    _no_osso(cab, arm, "cabeca")
    # ---- mãos por pose (presas aos ossos das mãos)
    rot, me, md = POSES[pose]
    for l, sx, tipo in (("e", 1, me), ("d", -1, md)):
        pulso = (sx * 0.185, -0.008, 0.47)
        for o in _mao(f"{name}_mao_{l}", M, mat, tipo, sx, pulso):
            o.parent = root
            _no_osso(o, arm, f"mao_{l}")
    # chave inglesa (boca aberta em "C") na mão direita
    if chave and md == "segura":
        px, py, pz = -0.185, -0.03, 0.43
        cm = mat("chave", rough=0.4)
        obs = [skin(name + "_chave_cabo", [(px, py, pz + 0.03), (px, py, pz - 0.15)], [(0, 1)],
                    [(0.022, 0.011), (0.022, 0.011)], cm)]
        arco = [(px + 0.034 * math.cos(math.radians(a)), py, pz - 0.185 + 0.034 * math.sin(math.radians(a)))
                for a in range(-235, 60, 30)]
        obs.append(skin(name + "_chave_boca", arco, [(i, i + 1) for i in range(len(arco) - 1)],
                        [(0.014, 0.011)] * len(arco), cm))
        for o in obs:
            o.parent = root
            _no_osso(o, arm, "mao_d")
    # ---- pose
    for osso, (x, y, z) in rot.items():
        girar(arm, osso, x, y, z)
    bpy.context.view_layer.update()
    return Z


def _bevel(o, w):
    b = o.modifiers.new("bev", "BEVEL")
    b.width, b.segments, b.limit_method = w, 3, "NONE"
    _liso(o)
    return o


def _corta_baixo(o, z0):
    """Apaga os vértices da metade de baixo de uma esfera (copa do boné)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < z0], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    so = o.modifiers.new("esp", "SOLIDIFY")
    so.thickness = 0.008
    _sub(o, 1)


# ================================================================ cena: oficina clara
def oficina_clara(M, estilo="vinil", largura=8.0, fundo_y=1.6):
    """Parede azul-acinzentada clara, rodapé com faixa amarela, chão epóxi liso, prateleira com pneus e galões."""
    cor = {"parede": "#C9DAF0", "chao": "#C9D0DA", "faixa": "#FFC928", "prat": "#AEB8C6", "pneu": "#3A4256",
           "galao_a": "#E5484D", "galao_b": "#2F67D8", "galao_c": "#FFC928"}

    def m_(n, rough=0.6):
        k = f"of_{n}_{estilo}"
        if k not in M:
            M[k] = _vinil(k, cor[n], rough) if estilo == "vinil" else _toon(k, cor[n], sombra=0.86)
        return M[k]

    root = empty("oficina")
    chao = mt.box("chao", -largura / 2, largura / 2, -4, fundo_y, -0.02, 0, m_("chao", 0.35))
    chao.parent = root
    par = mt.box("parede", -largura / 2, largura / 2, fundo_y, fundo_y + 0.05, 0, 4, m_("parede", 0.8))
    par.parent = root
    fx = mt.box("rodape", -largura / 2, largura / 2, fundo_y - 0.012, fundo_y, 0, 0.16, m_("faixa", 0.6))
    fx.parent = root
    # prateleira
    for z in (0.62, 1.08):
        p = mt.box(f"prat{z}", 1.3, 2.7, fundo_y - 0.32, fundo_y, z - 0.03, z, m_("prat", 0.5))
        p.parent = root
        _bevel(p, 0.01)
    for i in range(3):        # pneus em pé
        pn = toro(f"pneu{i}", 0.13, 0.055, m_("pneu", 0.7), loc=(1.48 + i * 0.22, fundo_y - 0.16, 0.62 + 0.185),
                  eixo="x", parent=root)
    for i, c in enumerate(("galao_a", "galao_b", "galao_c", "galao_a")):
        g = mt.box(f"galao{i}", -0.09, 0.09, -0.07, 0.07, 0, 0.24, m_(c, 0.5))
        g.parent = root
        g.location = (1.5 + i * 0.32, fundo_y - 0.15, 1.08)
        _bevel(g, 0.03)
    return root
