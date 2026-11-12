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


# ================================================================ o mecânico
def mecanico(name, M, estilo="vinil", pose="parado", expressao="sorriso", olhar=(0.0, 0.0), chave=True):
    """Mecânico "Zé". pose: 'parado' | 'aponta' | 'joinha' | 'explica' | 'espanto'.
    expressao: 'sorriso' | 'fala' | 'espanto' | 'preocupado' | 'pisca'."""
    mat = lambda n, **k: material(M, n, estilo, **k)
    root = empty(name)
    Z = {"raiz": root}
    R = 0.21                          # raio da cabeça (cabeça = 0,42 = 1/3 da altura)
    # ---- pernas + quadril + tronco (macacão) numa malha só
    P = [(0, 0, 0.45), (0, 0, 0.58), (0, 0, 0.7), (0, 0, 0.8),               # 0 quadril, 1 barriga, 2 peito, 3 pescoço
         (-0.09, 0, 0.36), (-0.095, 0, 0.2), (-0.095, 0, 0.1),              # 4-6 perna esquerda (dele: +x é a esq.)
         (0.09, 0, 0.36), (0.095, 0, 0.2), (0.095, 0, 0.1)]                 # 7-9
    A = [(0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6), (0, 7), (7, 8), (8, 9)]
    Rr = [(0.155, 0.12), (0.17, 0.13), (0.165, 0.125), (0.075, 0.07),
          (0.085, 0.08), (0.075, 0.072), (0.072, 0.07), (0.085, 0.08), (0.075, 0.072), (0.072, 0.07)]
    corpo = skin(name + "_macacao", P, A, Rr, mat("macacao", rough=0.6), parent=root)
    Z["corpo"] = corpo
    # gola em V da camiseta + zíper + bolso + cinto de ferramentas
    esfera(name + "_gola", 0.08, (0, -0.045, 0.79), mat("camiseta"), scale=(1, 0.7, 0.55), parent=root)
    zp = mt.box(name + "_ziper", -0.006, 0.006, -0.004, 0.004, 0.5, 0.74, mat("ziper", rough=0.35), anchor="bottom")
    zp.parent = root
    zp.location = (0, -0.127, 0.47)
    bo = mt.box(name + "_bolso", -0.045, 0.045, -0.006, 0.006, -0.035, 0.035, mat("macacao_escuro", rough=0.6),
                anchor="center")
    bo.parent = root
    bo.location = (-0.075, -0.118, 0.69)
    bo.rotation_euler = (math.radians(-12), 0, 0)
    _bevel(bo, 0.012)
    skin(name + "_cinto", [(0, 0, 0.455), (0, 0, 0.485)], [(0, 1)], [(0.176, 0.138), (0.178, 0.14)],
         mat("cinto", rough=0.5), sub=2, parent=root)
    # pano vermelho saindo do bolso de trás
    pano = skin(name + "_pano", [(0.06, 0.12, 0.47), (0.07, 0.15, 0.4), (0.075, 0.15, 0.33)], [(0, 1), (1, 2)],
                [(0.035, 0.012), (0.03, 0.01), (0.026, 0.01)], mat("pano", rough=0.7), parent=root)
    # ---- botas (bico redondo, maiores que o pé)
    for lado, x in (("e", 0.095), ("d", -0.095)):
        skin(f"{name}_bota_{lado}", [(x, 0.015, 0.11), (x, -0.005, 0.065), (x, -0.075, 0.055)], [(0, 1), (1, 2)],
             [(0.072, 0.072), (0.08, 0.065), (0.07, 0.05)], mat("bota", rough=0.35), parent=root)
        skin(f"{name}_sola_{lado}", [(x, 0.03, 0.018), (x, -0.09, 0.018)], [(0, 1)],
             [(0.068, 0.018), (0.07, 0.018)], mat("sola", rough=0.5), parent=root)
    # ---- braços (articulação no ombro; pose = girar o empty): manga do macacão até o cotovelo, depois antebraço
    # e mão de pele numa malha só (sem vão), polegar separado para o joinha
    for lado, sx in (("e", 1), ("d", -1)):
        ombro = empty(f"{name}_ombro_{lado}")
        ombro.parent = root
        ombro.location = (sx * 0.13, 0, 0.72)
        Z["braco_" + lado] = ombro
        skin(f"{name}_manga_{lado}", [(0, 0, 0.0), (sx * 0.012, 0, -0.08), (sx * 0.02, 0, -0.155)], [(0, 1), (1, 2)],
             [(0.058, 0.058), (0.058, 0.058), (0.063, 0.063)], mat("macacao", rough=0.6), parent=ombro)
        skin(f"{name}_braco_pele_{lado}", [(sx * 0.018, 0, -0.11), (sx * 0.024, -0.004, -0.25),
                                           (sx * 0.026, -0.008, -0.3), (sx * 0.026, -0.012, -0.35)],
             [(0, 1), (1, 2), (2, 3)], [(0.045, 0.045), (0.042, 0.042), (0.054, 0.04), (0.048, 0.036)],
             mat("pele", rough=0.42, coat=0.15), parent=ombro)
        mao = empty(f"{name}_mao_{lado}")
        mao.parent = ombro
        mao.location = (sx * 0.026, -0.01, -0.32)
        Z["mao_" + lado] = mao
        pol = skin(f"{name}_polegar_{lado}", [(-sx * 0.028, -0.02, 0.0), (-sx * 0.04, -0.04, 0.035)],
                   [(0, 1)], [(0.024, 0.024), (0.021, 0.021)], mat("pele", rough=0.42, coat=0.15), parent=mao)
        Z["polegar_" + lado] = pol
    # ---- cabeça
    cab = empty(name + "_cabeca")
    cab.parent = root
    cab.location = (0, 0, 0.8 + R * 0.92)
    Z["cabeca"] = cab
    P0 = {"sorriso": dict(), "fala": dict(boca_sorriso=0, boca_aberta=1, sobr_alt=0.4),
          "espanto": dict(boca_sorriso=0, boca_o=1, sobr_alt=1.0, abre_olho=1.15),
          "preocupado": dict(boca_sorriso=0, boca_o=0.0, sobr_inc=0.35, sobr_alt=0.3),
          "pisca": dict(abre_olho=0.08)}[expressao]
    P0 = dict(P0, olhar_x=olhar[0], olhar_z=olhar[1])
    mr, V = _rosto_mat(f"{name}_rosto_{estilo}", estilo, R, P0)
    Z["rosto"] = V
    esfera(name + "_cabeca_m", R, (0, 0, 0), mr, scale=(1.05, 0.98, 1.0), seg=64, parent=cab)
    # nariz (bolinha) e orelhas
    esfera(name + "_nariz", 0.019, (0, -R * 0.99, -R + 0.36 * 2 * R), mat("pele_quente", rough=0.42), seg=24,
           scale=(1.15, 1, 0.9), parent=cab)
    for sx in (-1, 1):
        esfera(f"{name}_orelha{sx}", 0.04, (sx * R * 1.02, 0.01, -R + 0.42 * 2 * R), mat("pele", rough=0.42),
               scale=(0.45, 0.8, 1.0), seg=24, parent=cab)
    # cabelo (casca lisa por baixo do boné: costeletas e nuca)
    esfera(name + "_cabelo", R * 1.02, (0, R * 0.1, -R * 0.04), mat("cabelo", rough=0.5), scale=(1.05, 0.95, 0.9),
           parent=cab)
    # boné: copa + faixa + aba + botão + emblema creme (chave inglesa estilizada = círculo + barra)
    copa = esfera(name + "_bone", R * 1.07, (0, R * 0.03, R * 0.2), mat("bone", rough=0.45, coat=0.15),
                  scale=(1.04, 1.02, 0.8), parent=cab)
    _corta_baixo(copa, 0.0)
    aba = esfera(name + "_aba", R * 0.64, (0, -R * 1.08, R * 0.24), mat("aba", rough=0.45), scale=(1.12, 1.0, 0.08),
                 parent=cab)
    aba.rotation_euler = (math.radians(-14), 0, 0)
    esfera(name + "_botao", R * 0.08, (0, R * 0.03, R * 1.12), mat("aba", rough=0.45), seg=24, parent=cab)
    em = esfera(name + "_emblema", R * 0.17, (0, -R * 0.9, R * 0.72), mat("emblema", rough=0.5), scale=(1, 0.22, 1),
                seg=32, parent=cab)
    em.rotation_euler = (math.radians(-40), 0, 0)
    # ---- chave inglesa amarela na mão direita
    if chave:
        ch = empty(name + "_chave")
        ch.parent = Z["mao_d"]
        ch.location = (0, -0.012, 0.04)
        skin(name + "_chave_cabo", [(0, 0, 0.0), (0, 0, -0.2)], [(0, 1)], [(0.016, 0.009), (0.016, 0.009)],
             mat("chave", rough=0.4), parent=ch)
        bocal = toro(name + "_chave_boca", 0.028, 0.012, mat("chave", rough=0.4), loc=(0, 0, -0.23), eixo="y", parent=ch)
        Z["chave"] = ch
    _posa(Z, pose)
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


def _posa(Z, pose):
    """Eixo y do ombro: negativo abre o braço esquerdo (+x) para fora; x negativo leva o braço para a frente."""
    e, d = Z["braco_e"], Z["braco_d"]
    g = math.radians
    e.rotation_euler = (0, g(-10), 0)
    d.rotation_euler = (0, g(10), 0)
    if pose == "aponta":        # braço esquerdo apontando para a frente/lado
        e.rotation_euler = (g(-70), g(-40), 0)
    elif pose == "joinha":      # mão esquerda na frente com polegar para cima
        e.rotation_euler = (g(-80), g(-15), 0)
        Z["polegar_e"].rotation_euler = (g(-60), 0, 0)
    elif pose == "explica":     # as duas mãos abertas na frente
        e.rotation_euler = (g(-50), g(-30), 0)
        d.rotation_euler = (g(-50), g(30), 0)
    elif pose == "espanto":     # braços abertos para cima
        e.rotation_euler = (g(-15), g(-135), 0)
        d.rotation_euler = (g(-15), g(135), 0)


# ================================================================ cena: oficina clara
def oficina_clara(M, estilo="vinil", largura=8.0, fundo_y=1.6):
    """Parede azul-acinzentada clara, rodapé com faixa amarela, chão epóxi liso, prateleira com pneus e galões."""
    cor = {"parede": "#DCE6F2", "chao": "#C9D0DA", "faixa": "#FFC928", "prat": "#AEB8C6", "pneu": "#3A4256",
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
        p = mt.box(f"prat{z}", 0.5, 1.9, fundo_y - 0.32, fundo_y, z - 0.03, z, m_("prat", 0.5))
        p.parent = root
        _bevel(p, 0.01)
    for i in range(3):        # pneus em pé
        pn = toro(f"pneu{i}", 0.13, 0.055, m_("pneu", 0.7), loc=(0.68 + i * 0.22, fundo_y - 0.16, 0.62 + 0.185),
                  eixo="x", parent=root)
    for i, c in enumerate(("galao_a", "galao_b", "galao_c", "galao_a")):
        g = mt.box(f"galao{i}", -0.09, 0.09, -0.07, 0.07, 0, 0.24, m_(c, 0.5))
        g.parent = root
        g.location = (0.7 + i * 0.32, fundo_y - 0.15, 1.08)
        _bevel(g, 0.03)
    return root
