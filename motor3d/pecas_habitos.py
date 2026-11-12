"""Peças do canal de hábitos — Direção B "Laboratório de bolso" (referencias/habitos/05_estilo_visual_e_propostas.md).

- argila(): material fosco tipo massinha (sem o brilho de vinil do concorrente).
- contorno(): contorno fino escuro por "inverted hull" (Solidify com normais invertidas + material que só aparece
  pelo lado de dentro). Funciona no Cycles sem Freestyle; custo = dobra a geometria do objeto.
- gota(): mascote fixo "Gota" (gotinha-cientista de óculos, jaleco curto e lupa amarela).
- lupa(): lupa (aro amarelo-gema, vidro, cabo coral). Retorna o centro e o raio interno (para a máscara da transição).
- palco_micro(): fundo verde-petróleo com grade milimetrada clara (papel de laboratório), cor plana (emissão).
- terreno_pele(): pele em close (plano subdividido com ondulação por ruído e poros afundados, poros mais escuros).
- bolha(), espinha(): bolhas de condicionador e espinha inflada.
Use materiais_habitos(M) uma vez antes das peças.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import motor as mt
from motor import mat, lin, mesh_obj, empty, bsdf
from pecas import child, _liso, esfera, capsula, _arco

PALETA = {"petroleo": "#0E3B3A", "menta": "#7FD6B5", "coral": "#FF6B5A", "gema": "#FFC928", "creme": "#FFF4E0",
          "pele": "#F1B98F", "tinta": "#1B2B2A"}

HAB = {  # nome: (cor, rugosidade)
    "gota": ("#45B3AA", 0.9), "gota_escura": ("#2F958E", 0.9), "jaleco": ("#F8F6EF", 0.95), "oculos": ("#1B2B2A", 0.6),
    "lupa_aro": ("#FFC928", 0.75), "lupa_cabo": ("#FF6B5A", 0.85), "pupila_g": ("#14201F", 0.4),
    "olho_g": ("#FFFFFF", 0.5), "boca_g": ("#7A2E2E", 0.7), "lingua_g": ("#FF8C7A", 0.8), "bochecha_g": ("#FF8F80", 0.9),
    "bolha": ("#F4F5F0", 0.4), "espinha": ("#FF6B5A", 0.6), "espinha_topo": ("#FFF1DA", 0.5),
    "espinha_base": ("#E9735F", 0.85), "frasco_cond": ("#FFC928", 0.8), "tampa_cond": ("#FF6B5A", 0.8),
    "rotulo_cond": ("#FFF4E0", 0.9),
}


def argila(name, hexcol, rough=0.9, alpha=1.0, emit=0.0):
    """Material fosco tipo argila/massinha: rugosidade alta, reflexo especular baixo e um leve 'sheen' de veludo."""
    m = mat(name, hexcol, rough=rough, alpha=alpha, emit=emit)
    b = bsdf(m)
    for inp, v in (("Specular IOR Level", 0.25), ("Sheen Weight", 0.25), ("Sheen Roughness", 0.6)):
        if inp in b.inputs:
            b.inputs[inp].default_value = v
    return m


def mat_contorno(name="contorno", hexcol="#1B2B2A"):
    """Material do contorno: cor chapada (emissão) só nas faces vistas por dentro; transparente no resto."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(hexcol)
    em.inputs["Strength"].default_value = 1.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    # só raios da câmera veem o contorno (senão a casca faz sombra no próprio objeto)
    lp = nt.nodes.new("ShaderNodeLightPath")
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(lp.outputs["Is Camera Ray"], inv.inputs[1])
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    nt.links.new(geo.outputs["Backfacing"], mx.inputs[0])
    nt.links.new(inv.outputs[0], mx.inputs[1])
    nt.links.new(mx.outputs[0], mix.inputs[0])
    nt.links.new(em.outputs[0], mix.inputs[1])        # casca vista por dentro (silhueta): cor do contorno
    nt.links.new(tr.outputs[0], mix.inputs[2])        # casca vista por fora, ou raio que não é da câmera: transparente
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def materiais_habitos(M):
    for n, (c, r) in HAB.items():
        if n not in M:
            M[n] = argila(n, c, rough=r)
    if "lupa_vidro" not in M:
        M["lupa_vidro"] = mat("lupa_vidro", "#D9FFF4", rough=0.05, alpha=0.18)
    if "brilho_g" not in M:
        M["brilho_g"] = mat("brilho_g", "#FFFFFF", rough=0.3, emit=1.2)
    if "contorno" not in M:
        M["contorno"] = mat_contorno()
    return M


SEM_CONTORNO = ("_sobr", "_luz", "_brilho", "_reflexo", "_boch", "_feixe")


def contorno(objs, M, esp=0.006):
    """Contorno fino (inverted hull) em todos os objetos de malha da lista (e nos filhos deles).
    `esp` em metros do mundo (corrigido pela escala do objeto)."""
    vistos = set()

    def faz(o):
        if o.name in vistos:
            return
        vistos.add(o.name)
        for c in o.children:
            faz(c)
        if o.type not in ("MESH", "CURVE", "FONT") or o.data is None or not hasattr(o.data, "materials"):
            return
        if any(md.name == "contorno" for md in o.modifiers):
            return
        if any(t in o.name for t in SEM_CONTORNO):
            return
        esc = max(o.matrix_world.to_scale()) or 1.0
        if esc < 1e-6:
            esc = 1.0
        o.data.materials.append(M["contorno"])
        md = o.modifiers.new("contorno", "SOLIDIFY")
        md.thickness = esp / esc
        md.offset = 1.0
        md.use_flip_normals = True
        md.use_rim = False
        md.material_offset = len(o.data.materials) - 1
        md.use_even_offset = False

    bpy.context.view_layer.update()
    for o in objs:
        faz(o)


# ================================================================ geometria auxiliar
def toro(name, R, r, m, eixo="y", seg=40, seg2=12, loc=(0, 0, 0)):
    """Anel (toro) de raio R e espessura r, com o furo ao longo de `eixo`."""
    bm = bmesh.new()
    vs = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        anel = []
        for j in range(seg2):
            b = 2 * math.pi * j / seg2
            rr = R + r * math.cos(b)
            p = Vector((rr * math.cos(a), rr * math.sin(a), r * math.sin(b)))   # furo em z
            if eixo == "y":
                p = Vector((p.x, p.z, p.y))
            elif eixo == "x":
                p = Vector((p.z, p.y, p.x))
            anel.append(bm.verts.new(p))
        vs.append(anel)
    for i in range(seg):
        for j in range(seg2):
            bm.faces.new([vs[i][j], vs[(i + 1) % seg][j], vs[(i + 1) % seg][(j + 1) % seg2], vs[i][(j + 1) % seg2]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _liso(mesh_obj(name, bm, m, loc))


def disco(name, r, esp, m, eixo="y", seg=40, loc=(0, 0, 0)):
    bm = bmesh.new()
    rot = Matrix.Rotation(math.pi / 2, 4, "X") if eixo == "y" else Matrix()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=esp, matrix=rot)
    return mesh_obj(name, bm, m, loc)


# ================================================================ lupa
def lupa(name, M, raio=0.06, cabo=0.07):
    """Lupa com o vidro no plano x-z (olhando para -y), cabo para baixo a partir da origem (a pegada).
    Retorna dict: raiz, centro (empty no meio do vidro), raio_interno."""
    root = empty(name)
    esp = raio * 0.16
    cz = cabo + raio + esp * 0.6
    child(toro(name + "_aro", raio, esp, M["lupa_aro"]), root, (0, 0, cz))
    child(disco(name + "_vidro", raio, esp * 0.4, M["lupa_vidro"]), root, (0, 0, cz))
    child(capsula(name + "_cabo", esp * 1.15, cabo, M["lupa_cabo"]), root, (0, 0, cabo + esp * 0.6))
    child(mt.cyl(name + "_virola", esp * 1.45, -esp * 0.5, esp * 0.9, (0, 0), M["lupa_aro"], seg=16), root,
          (0, 0, cabo + esp * 0.4))
    # reflexo no vidro (arco branco)
    rf = child(_arco(name + "_reflexo", raio * 0.68, esp * 0.22, M["brilho_g"], ang=math.pi * 0.35, para_cima=False),
               root, (0, -esp * 0.3, cz))
    rf.rotation_euler = (0, math.radians(-40), 0)
    c = child(empty(name + "_centro"), root, (0, 0, cz))
    return {"raiz": root, "centro": c, "raio_interno": raio - esp}


# ================================================================ mascote Gota
def _perfil_gota(R, bico=1.45, m=1.1):
    """Perfil (rho, z) da gota: base redonda de raio R, ponta para cima com altura bico*R acima do equador.
    Origem na base (z = 0)."""
    def f(th):
        if th >= math.pi / 2:
            rho, z = R * math.sin(th), R * math.cos(th)
        else:
            g = (math.sin(th / 2) / math.sin(math.pi / 4)) ** m
            rho, z = R * math.sin(th) * g, bico * R * math.cos(th)
        return rho, z + R
    return f


def _raio_em(f, z, n=400):
    """Raio do corpo da gota na altura z (busca no perfil)."""
    best = None
    for i in range(n + 1):
        th = math.pi * i / n
        rho, zz = f(th)
        if best is None or abs(zz - z) < best[0]:
            best = (abs(zz - z), rho)
    return best[1]


def gota(name, M, R=0.1, pose="lupa", olhar=(0.0, 0.0), sobrancelha=12.0, boca="aberta", jaleco=True,
         lupa_raio=None, inclina=0.0, cabo=None):
    """Mascote "Gota" (gotinha-cientista). Olha para -y; origem na base. R = raio da barriga (altura total ≈ 2,5 R).
    pose: 'lupa' (lupa erguida ao lado, na mão direita), 'aponta' (braço esquerdo apontando, lupa na direita).
    olhar: desvio das pupilas (x, z) em fração do olho. sobrancelha: graus de 'curiosidade' (uma sobe, a outra desce).
    boca: 'sorriso' | 'aberta'. Retorna dict com raiz, corpo, lupa (dict de lupa()), braco_e, braco_d."""
    materiais_habitos(M)
    root = empty(name)
    G = {"raiz": root}
    f = _perfil_gota(R)
    # ---- corpo (gota torneada)
    bm = bmesh.new()
    nu, nv = 40, 28
    rows = []
    for j in range(nv + 1):
        th = math.pi * j / nv
        rho, z = f(th)
        if j in (0, nv):
            rows.append([bm.verts.new((0, 0, z))])
            continue
        rows.append([bm.verts.new((rho * math.cos(2 * math.pi * i / nu), rho * math.sin(2 * math.pi * i / nu), z))
                     for i in range(nu)])
    for i in range(nu):
        bm.faces.new([rows[0][0], rows[1][(i + 1) % nu], rows[1][i]])
        bm.faces.new([rows[nv][0], rows[nv - 1][i], rows[nv - 1][(i + 1) % nu]])
    for j in range(1, nv - 1):
        for i in range(nu):
            bm.faces.new([rows[j][i], rows[j + 1][i], rows[j + 1][(i + 1) % nu], rows[j][(i + 1) % nu]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    corpo = child(_liso(mesh_obj(name + "_corpo", bm, M["gota"])), root, (0, 0, 0))
    G["corpo"] = corpo
    sub = corpo.modifiers.new("liso", "SUBSURF")
    sub.levels = sub.render_levels = 1

    def frente(x, z, d=0.0):
        """Ponto na superfície da frente (-y) na altura z, deslocado x para o lado (+ d para fora)."""
        rho = _raio_em(f, z)
        x = max(-rho * 0.98, min(rho * 0.98, x))
        y = -math.sqrt(max(rho * rho - x * x, 0.0))
        n = Vector((x, y, 0)).normalized()
        return Vector((x, y, z)) + n * d

    # brilho de "água" no alto da cabeça
    child(esfera(name + "_brilho", R * 0.13, tuple(frente(-R * 0.38, R * 1.85, R * 0.0)), M["brilho_g"],
                 scale=(0.6, 0.35, 1.25)), root).rotation_euler = (0, math.radians(-25), 0)
    child(esfera(name + "_brilho2", R * 0.06, tuple(frente(-R * 0.48, R * 1.55, R * 0.0)), M["brilho_g"],
                 scale=(0.7, 0.35, 0.7)), root)
    # ---- olhos grandes + óculos redondos
    zo = R * 1.12
    ro = R * 0.27
    for lado in (-1, 1):
        c = frente(lado * R * 0.36, zo, -ro * 0.35)
        olho = child(esfera(f"{name}_olho{lado}", ro, tuple(c), M["olho_g"], scale=(1, 0.55, 1.12)), root)
        pp = Vector((olhar[0] * ro * 0.4 - lado * ro * 0.08, -ro * 0.42, olhar[1] * ro * 0.4 - ro * 0.06))
        pup = child(esfera(f"{name}_pupila{lado}", ro * 0.62, tuple(pp), M["pupila_g"], scale=(1, 0.5, 1.12)), olho)
        child(esfera(f"{name}_luz{lado}", ro * 0.2, (ro * 0.22, -ro * 0.27, ro * 0.3), M["brilho_g"],
                     scale=(1, 0.5, 1)), pup)
        aro = child(toro(f"{name}_oculos{lado}", ro * 1.22, ro * 0.13, M["oculos"]), root,
                    tuple(c + Vector((0, -ro * 0.62, 0))))
        G["oculos" + str(lado)] = aro
        # haste do óculos indo para trás
        h0 = c + Vector((lado * ro * 1.22, -ro * 0.55, 0))
        h1 = frente(lado * R * 0.92, zo, R * 0.02)
        child(mt.tube(f"{name}_haste{lado}", tuple(h0), tuple(h1 + Vector((0, R * 0.25, 0))), ro * 0.1, M["oculos"], seg=8),
              root)
        # sobrancelha (uma levantada e inclinada: cara de curiosa)
        sobe = math.radians(sobrancelha) if lado > 0 else -math.radians(sobrancelha) * 0.3
        zb_ = zo + ro * 1.42 + (ro * 0.18 if (lado > 0) == (sobrancelha > 0) else 0)
        xi, xo = lado * R * 0.17, lado * R * 0.5
        pi_ = frente(xi, zb_ + math.tan(abs(sobe)) * ro * 0.3 + ro * 0.04, ro * 0.12)     # ponta de dentro mais alta:
        po_ = frente(xo, zb_ - math.tan(abs(sobe)) * ro * 0.3 - ro * 0.06, ro * 0.12)     # cara curiosa, não brava
        child(mt.tube(f"{name}_sobr{lado}", tuple(pi_), tuple(po_), ro * 0.14, M["oculos"], seg=8), root)
        for q in (pi_, po_):
            child(esfera(f"{name}_sobrp{lado}", ro * 0.14, tuple(q), M["oculos"], seg=10), root)
    pnt = frente(0, zo, -ro * 0.1) + Vector((0, -ro * 0.5, 0))
    child(mt.tube(name + "_ponte", tuple(pnt + Vector((-ro * 0.22, 0, 0))), tuple(pnt + Vector((ro * 0.22, 0, 0))),
                  ro * 0.11, M["oculos"], seg=8), root)
    # bochechas
    for lado in (-1, 1):
        child(esfera(f"{name}_boch{lado}", R * 0.11, tuple(frente(lado * R * 0.6, R * 0.8, -R * 0.02)), M["bochecha_g"],
                     scale=(1.1, 0.35, 0.7)), root)
    # boca
    bc = frente(0, R * 0.76, -R * 0.01)
    if boca == "aberta":
        child(esfera(name + "_boca", R * 0.19, tuple(bc), M["boca_g"], scale=(1.0, 0.4, 0.75)), root)
        child(esfera(name + "_lingua", R * 0.08, tuple(bc + Vector((0, -R * 0.03, -R * 0.05))), M["lingua_g"],
                     scale=(1.2, 0.4, 0.6)), root)
    else:
        child(_arco(name + "_sorriso", R * 0.15, R * 0.028, M["boca_g"], ang=math.pi * 0.85), root, tuple(bc))
    # ---- jaleco curto (casca aberta na frente em V, com gola)
    if jaleco:
        bm = bmesh.new()
        th0, th1 = math.radians(96), math.radians(158)
        nu2, nv2 = 48, 10
        grid = []
        for j in range(nv2 + 1):
            th = th0 + (th1 - th0) * j / nv2
            rho, z = f(th)
            rho *= 1.045
            gap = math.radians(30 - 20 * j / nv2)        # abertura em V, mais larga em cima
            a0, a1 = -math.pi / 2 + gap, -math.pi / 2 + 2 * math.pi - gap
            grid.append([bm.verts.new((rho * math.cos(a0 + (a1 - a0) * i / nu2), rho * math.sin(a0 + (a1 - a0) * i / nu2), z))
                         for i in range(nu2 + 1)])
        for j in range(nv2):
            for i in range(nu2):
                bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        jl = child(_liso(mesh_obj(name + "_jaleco", bm, M["jaleco"])), root)
        sd = jl.modifiers.new("esp", "SOLIDIFY")
        sd.thickness = R * 0.04
        sd.offset = 1.0
        # gola: duas abas triangulares
        for lado in (-1, 1):
            rho, z = f(th0)
            a = -math.pi / 2 + lado * math.radians(30)
            p = Vector((rho * 1.06 * math.cos(a), rho * 1.06 * math.sin(a), z))
            bm = bmesh.new()
            v1 = bm.verts.new(p + Vector((0, 0, R * 0.02)))
            v2 = bm.verts.new(p + Vector((lado * R * 0.3, R * 0.08, R * 0.04)))
            v3 = bm.verts.new(p + Vector((lado * R * 0.06, -R * 0.03, -R * 0.24)))
            bm.faces.new([v1, v2, v3])
            go = child(mesh_obj(f"{name}_gola{lado}", bm, M["jaleco"]), root)
            go.modifiers.new("esp", "SOLIDIFY").thickness = R * 0.035
        # bolso com caneta
        pb = frente(R * 0.5, R * 0.42, R * 0.07)
        child(mt.box(name + "_bolso", -R * 0.13, R * 0.13, -R * 0.02, R * 0.02, -R * 0.12, R * 0.1, M["jaleco"],
                     anchor="center"), root, tuple(pb)).rotation_euler = (0, 0, math.radians(-25))
        child(capsula(name + "_caneta", R * 0.025, R * 0.18, M["lupa_cabo"]), root,
              tuple(pb + Vector((R * 0.05, -R * 0.01, R * 0.2)))).rotation_euler = (0, 0, math.radians(-25))
    # ---- pezinhos
    for lado in (-1, 1):
        child(esfera(f"{name}_pe{lado}", R * 0.2, (lado * R * 0.38, -R * 0.42, R * 0.07), M["gota_escura"],
                     scale=(1.0, 1.35, 0.55)), root)
    # ---- braços (articulação no "ombro")
    zb = R * 0.78
    for lado, nome in ((-1, "e"), (1, "d")):
        rho = _raio_em(f, zb)
        ombro = child(empty(f"{name}_ombro_{nome}"), root, (lado * rho * 0.92, -R * 0.05, zb))
        child(capsula(f"{name}_braco_{nome}", R * 0.085, R * 0.42, M["gota"]), ombro)
        mao = child(esfera(f"{name}_mao_{nome}", R * 0.13, (0, 0, -R * 0.5), M["gota"]), ombro)
        G["braco_" + nome], G["mao_" + nome] = ombro, mao
        ombro.rotation_euler = (0, lado * math.radians(-35), 0)
    # lupa na mão direita
    L = lupa(name + "_lupa", M, raio=lupa_raio or R * 0.62, cabo=cabo or R * 0.55)
    child(L["raiz"], G["mao_d"], (0, 0, 0))
    G["lupa"] = L
    if pose in ("lupa", "aponta"):
        # braço direito erguido para o lado, lupa em pé ao lado do rosto
        G["braco_d"].rotation_euler = (0, math.radians(-135), 0)
        L["raiz"].rotation_euler = (0, math.radians(135), 0)
    if pose == "aponta":
        G["braco_e"].rotation_euler = (math.radians(-20), math.radians(110), 0)
    root.rotation_euler = (0, 0, inclina)
    return G


# ================================================================ mundo micro
def grade_mat(name="grade", fundo="#0E3B3A", linha="#3F7C77", linha_forte="#7FB8B0", passo=0.1, maior=5,
              fina=0.035, forte=0.06, eixos="xz"):
    """Papel milimetrado em cor chapada (emissão): linhas finas a cada `passo` e fortes a cada `maior` passos."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def linhas(eixo, p, w):
        a = nt.nodes.new("ShaderNodeMath"); a.operation = "DIVIDE"; a.inputs[1].default_value = p
        nt.links.new(sep.outputs[eixo], a.inputs[0])
        b = nt.nodes.new("ShaderNodeMath"); b.operation = "PINGPONG"; b.inputs[1].default_value = 0.5
        nt.links.new(a.outputs[0], b.inputs[0])            # distância até a linha mais próxima (0..0,5)
        c = nt.nodes.new("ShaderNodeMath"); c.operation = "LESS_THAN"; c.inputs[1].default_value = w / 2
        nt.links.new(b.outputs[0], c.inputs[0])
        return c

    def uniao(x, y):
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
        nt.links.new(x.outputs[0], mx.inputs[0]); nt.links.new(y.outputs[0], mx.inputs[1])
        return mx

    e1, e2 = eixos[0].upper(), eixos[1].upper()
    finas = uniao(linhas(e1, passo, fina), linhas(e2, passo, fina))
    fortes = uniao(linhas(e1, passo * maior, forte / maior), linhas(e2, passo * maior, forte / maior))
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = lin(fundo); mix1.inputs["B"].default_value = lin(linha)
    nt.links.new(finas.outputs[0], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    mix2.inputs["B"].default_value = lin(linha_forte)
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    nt.links.new(fortes.outputs[0], mix2.inputs["Factor"])
    nt.links.new(mix2.outputs["Result"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    return m


def palco_micro(name, M, largura=12.0, altura=8.0, y=4.0, z0=-1.0, passo=0.25):
    """Fundo vertical (plano x-z em y) verde-petróleo com grade clara. Chão pode ficar a cargo do terreno_pele."""
    if "grade" not in M:
        M["grade"] = grade_mat("grade", passo=passo)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-largura / 2, 0, z0), (largura / 2, 0, z0), (largura / 2, 0, z0 + altura),
                                    (-largura / 2, 0, z0 + altura))]
    bm.faces.new(vs)
    return mesh_obj(name, bm, M["grade"], (0, y, 0))


def terreno_pele(name, M, tam=(4.0, 3.0), n=(140, 110), poros=(), amp=0.05, escala=1.3, seed=2,
                 cor="#F1B98F", cor_poro="#C9876A", cor_vale="#E5A47E"):
    """Pele vista de muito perto: plano (x, y) subdividido com ondulação suave por ruído, rugas leves e poros
    afundados (cor mais escura dentro). poros = [(x, y, raio, profundidade)]. Origem no centro, z = 0 na média.
    Retorna (objeto, altura(x, y)) para encaixar bolhas/espinhas na superfície."""
    off = Vector((seed * 13.1, seed * 7.7, 0))

    def h(x, y):
        p = Vector((x * escala, y * escala, 0)) + off
        z = amp * noise.noise(p) + amp * 0.35 * noise.noise(p * 2.7)
        z += amp * 0.18 * math.sin((x * 0.6 + y) * 7.0 + noise.noise(p * 0.5) * 3)     # rugas finas
        for (px, py, pr, pd) in poros:
            d2 = ((x - px) ** 2 + (y - py) ** 2) / (pr * pr)
            if d2 < 4:
                z -= pd * math.exp(-d2 * 1.6)
                z += pd * 0.25 * math.exp(-(math.sqrt(d2) - 1.15) ** 2 * 6)        # borda levemente elevada
        return z

    def escuro(x, y):
        v = 0.0
        for (px, py, pr, pd) in poros:
            d2 = ((x - px) ** 2 + (y - py) ** 2) / (pr * pr)
            v = max(v, math.exp(-d2 * 1.2))
        return v

    bm = bmesh.new()
    nx, ny = n
    W, D = tam
    vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x, y = -W / 2 + W * i / nx, -D / 2 + D * j / ny
            row.append(bm.verts.new((x, y, h(x, y))))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new([vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]])
    lay = bm.loops.layers.float_color.new("cor")
    c0, c1, c2 = Vector(lin(cor)[:3]), Vector(lin(cor_poro)[:3]), Vector(lin(cor_vale)[:3])
    for fc in bm.faces:
        for lp in fc.loops:
            x, y, z = lp.vert.co
            e = escuro(x, y)
            vale = max(0.0, min(1.0, -z / (amp * 1.2)))
            c = c0.lerp(c2, vale * 0.6).lerp(c1, e)
            lp[lay] = (*c, 1.0)
    m = argila(name + "_mat", cor, rough=0.75)
    nt = m.node_tree
    at = nt.nodes.new("ShaderNodeVertexColor")
    at.layer_name = "cor"
    nt.links.new(at.outputs["Color"], bsdf(m).inputs["Base Color"])
    if "Subsurface Weight" in bsdf(m).inputs:
        bsdf(m).inputs["Subsurface Weight"].default_value = 0.0
    o = _liso(mesh_obj(name, bm, m))
    return o, h


def bolha(name, M, r, loc, achata=0.85):
    """Bolha/gotinha de condicionador (branca, brilho suave), com um pontinho de luz."""
    o = esfera(name, r, loc, M["bolha"], scale=(1, 1, achata), seg=20)
    child(esfera(name + "_luz", r * 0.22, (-r * 0.35, -r * 0.45, r * 0.5 * achata), M["brilho_g"], scale=(1, 0.6, 0.6),
                 seg=10), o)
    return o


def espinha(name, M, r, loc):
    """Espinha inflada: base avermelhada larga, domo coral e ponta clara. Origem na base."""
    root = empty(name, loc)
    child(esfera(name + "_base", r * 1.3, (0, 0, -r * 0.05), M["espinha_base"], scale=(1, 1, 0.25)), root)
    child(esfera(name + "_domo", r, (0, 0, r * 0.45), M["espinha"], scale=(1, 1, 1.05)), root)
    child(esfera(name + "_topo", r * 0.4, (0, 0, r * 1.38), M["espinha_topo"], scale=(1, 1, 0.55)), root)
    child(esfera(name + "_luz", r * 0.15, (-r * 0.45, -r * 0.62, r * 1.0), M["brilho_g"], scale=(1, 0.6, 0.8)), root)
    return root


def frasco_condicionador(name, M, altura=0.2, raio=0.045):
    """Frasco amarelo de condicionador (tampa coral, rótulo creme). Origem na base."""
    root = empty(name)
    child(esfera(name + "_corpo", raio, (0, 0, altura * 0.5), M["frasco_cond"], scale=(1.0, 0.7, altura / (2 * raio))),
          root)
    child(mt.cyl(name + "_tampa", raio * 0.55, altura * 0.95, altura * 1.12, (0, 0), M["tampa_cond"], seg=16), root)
    child(esfera(name + "_rotulo", raio * 0.7, (0, -raio * 0.62, altura * 0.48), M["rotulo_cond"],
                 scale=(1.0, 0.15, 1.1)), root)
    return root
