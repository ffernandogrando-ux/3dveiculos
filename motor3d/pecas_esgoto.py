"""Peças de banheiro e esgoto do vídeo do ralo (videos/ralo_esgoto): vaso em corte, canos em corte com água, ralo,
frascos, barata, rede da rua, cortar_y…

Ficam num módulo à parte porque o vídeo do mofo no teto do banheiro criou, em paralelo, peças de banheiro com os
mesmos nomes (materiais_banheiro, vaso_sanitario, pia_banheiro, espelho, ladrilho_mat) e outros parâmetros.
Aqui valem as versões do ralo; todo o resto vem de pecas.py. Uso: `import pecas_esgoto as pc`.
"""
import pecas as _base

globals().update({_k: _v for _k, _v in vars(_base).items() if not _k.startswith("__")})
from mathutils import Quaternion  # noqa: E402

# ================================================================ banheiro e esgoto (canal "dentro da sua casa")
BANHEIRO = {"porcelain": "#f7f8f6", "porcelain_in": "#b9cad3", "pvc": "#eef0ec", "pvc_in": "#a3adb3",
            "water_c": "#4fc3f7", "sewage": "#6b5236", "gas": "#8cc63f", "perfume": "#c99bf0",
            "disinfectant": "#9b59d0", "label_lilac": "#f3e8ff", "bleach": "#f4f6f8", "bleach_label": "#2f6fd2",
            "cap_w": "#f4f2ec", "grate": "#c3c8ce", "grate_slot": "#3b3f44", "roach": "#8a4424", "roach_dark": "#3b1a0e",
            "egg": "#efe6cf", "egg_rot": "#7d8f4e", "brush": "#2e9e5b", "bristle": "#f4d03f", "pitcher": "#bfe6ff",
            "concrete_p": "#a9a9ae", "concrete_in": "#6f6f74", "flapper": "#c0392b", "haze": "#a6c46a",
            "toxic": "#e6e36b", "vent_cap": "#7d838a", "chrome": "#d9dde2", "glass_box": "#cfe9f2",
            "towel": "#f29a9a", "mirror": "#bcd9ea", "bact": "#5bd16a", "sink_cab": "#e9e2d3"}
EMIT_BAN = {"water_c": 0.35, "gas": 0.4, "perfume": 0.4, "haze": 0.15, "toxic": 0.35, "mirror": 0.15, "bact": 0.6}
ALPHA_BAN = {"gas": 0.85, "perfume": 0.42, "pitcher": 0.35, "haze": 0.35, "toxic": 0.6, "glass_box": 0.22}
ROUGH_BAN = {"porcelain": 0.18, "pvc": 0.45, "water_c": 0.12, "grate": 0.3, "disinfectant": 0.3, "bleach": 0.35,
             "chrome": 0.15, "glass_box": 0.05, "mirror": 0.1, "pitcher": 0.1, "roach": 0.35, "roach_dark": 0.4}


def materiais_banheiro(M):
    """Materiais das peças de banheiro e esgoto (cria só os que faltarem; inclui os de casa/cozinha/decoração)."""
    materiais_decor(M)
    for n, c in BANHEIRO.items():
        if n not in M:
            M[n] = mat(n, c, rough=ROUGH_BAN.get(n, 0.7), emit=EMIT_BAN.get(n, 0.0), alpha=ALPHA_BAN.get(n, 1.0))
    return M


def ladrilho_mat(name, c1, c2, junta, escala=6.0, piso=False, alt=0.25, larg=0.5, rough=0.35):
    """Azulejo/piso com rejunte (Brick Texture). piso=True usa x-y (chão); senão (x+y)-z (paredes)."""
    m = mat(name, c1, rough=rough)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Scale"].default_value = escala
    br.inputs["Brick Width"].default_value = larg
    br.inputs["Row Height"].default_value = alt
    br.inputs["Mortar Size"].default_value = 0.012
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


# ---------------------------------------------------------------- corte (raio-x) de peças e de blocos
def cortar_y(root, y0=0.0, manter=1, m_corte=None, passo=0.0007):
    """Corta a peça (e todos os filhos) no plano y = y0 do mundo e fecha o corte com uma face lisa.
    manter=1 fica com o lado y > y0 (o de trás, longe da câmera); manter=-1 com o da frente.
    m_corte: material da face cortada (padrão: o do próprio objeto). Modificadores (chanfro, espessura) são
    aplicados. Cada parte é cortada `passo` atrás da anterior: faces de corte sobrepostas no MESMO plano saem pretas
    no Cycles. Chame com a peça já posicionada e ANTES de animar (escala normal)."""
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    partes = [o for o in [root] + list(root.children_recursive) if o.type == "MESH"]
    for i, o in enumerate(partes):
        yc = y0 + (1 if manter > 0 else -1) * i * passo
        mats = list(o.data.materials)
        me = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
        bm = bmesh.new()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        mw = o.matrix_world.copy()
        bm.transform(mw)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                               plane_co=(0, yc, 0), plane_no=(0, 1, 0),
                               clear_inner=manter > 0, clear_outer=manter < 0)
        # borda aberta no plano (inclui arestas que já estavam no plano, ex.: vértices de um cilindro em y = yc)
        borda = [e for e in bm.edges if e.is_boundary and all(abs(v.co.y - yc) < 1e-5 for v in e.verts)]
        novas = bmesh.ops.holes_fill(bm, edges=borda, sides=0)["faces"] if borda else []
        if m_corte is not None:
            if m_corte not in mats:
                mats.append(m_corte)
            idx = mats.index(m_corte)
            for f in novas:
                f.material_index = idx
        for f in novas:
            f.smooth = False
        if bm.faces:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.transform(mw.inverted())
        o.modifiers.clear()
        me2 = bpy.data.meshes.new(o.name)
        bm.to_mesh(me2)
        bm.free()
        for m in mats:
            me2.materials.append(m)
        o.data = me2
    return root


def bloco_corte(name, poly, y0, y1, m, furos=(), y_furo=0.1):
    """Bloco (piso, laje, parede, fundação) de perfil `poly` (plano x-z, shapely ou lista de pontos) de y0 a y1.
    Na faixa da frente [y0, y0 + y_furo] os `furos` (polígonos shapely, ex.: canos com folga) são vazados, para o cano
    em corte aparecer atravessando o bloco. Retorna a lista de objetos."""
    P = poly if hasattr(poly, "exterior") else sg.Polygon(poly)
    out = []
    frente = P.difference(unary_union(list(furos))) if furos else P
    yf = min(y1, y0 + y_furo) if furos else y1
    for i, p in enumerate(mt.polys(frente)):
        out.append(prism(f"{name}_f{i}", p, y0, yf, m))
    if yf < y1:
        out.append(prism(name + "_t", P, yf, y1, m))
    return out


# ---------------------------------------------------------------- canos de esgoto em corte
def _caminho_suave(pts, rc, n=7, min_giro=0.45):
    """Arredonda os cantos (giro maior que `min_giro` rad) de uma polilinha [(x, z)] com arcos de raio rc."""
    P = [Vector((p[0], p[1])) for p in pts]
    if rc <= 0 or len(P) < 3:
        return [(p.x, p.y) for p in P]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        A, B, C = P[i - 1], P[i], P[i + 1]
        u, v = A - B, C - B
        la, lc = u.length, v.length
        if la < 1e-9 or lc < 1e-9:
            continue
        u, v = u / la, v / lc
        phi = math.acos(max(-1.0, min(1.0, u.dot(v))))      # π = sem curva
        if math.pi - phi < min_giro:
            out.append(B)
            continue
        d = min(rc / math.tan(phi / 2), la * 0.5, lc * 0.5)
        r = d * math.tan(phi / 2)
        P1, P2 = B + u * d, B + v * d
        Cc = B + (u + v).normalized() * (r / math.sin(phi / 2))
        a1 = math.atan2(P1.y - Cc.y, P1.x - Cc.x)
        a2 = math.atan2(P2.y - Cc.y, P2.x - Cc.x)
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for j in range(n + 1):
            a = a1 + da * j / n
            out.append(Vector((Cc.x + r * math.cos(a), Cc.y + r * math.sin(a))))
    out.append(P[-1])
    res = [out[0]]
    for p in out[1:]:
        if (p - res[-1]).length > 1e-5:
            res.append(p)
    return [(p.x, p.y) for p in res]


def _meio_tubo(bm, cam, ro, ri, y0, seg=10, mi=(0, 1, 2), aberturas=(), pontas=(True, True)):
    """Meio tubo (lado y >= y0) ao longo de cam [(x, z)]: casca externa (mi[0]), interna (mi[1]), faces do corte e
    das pontas (mi[2]). aberturas: [(x0, z0, x1, z1, lado)] — nos trechos com o meio dentro do retângulo, abre a
    parede do lado +n (lado=1: em cima num cano que corre para +x) ou -n (lado=-1), para encaixar outro cano.
    pontas: (início, fim) com a borda (anel) na ponta; sem borda, a ponta pode entrar dentro de outro cano."""
    P = [Vector(p) for p in cam]
    n = len(P)
    rings_o, rings_i = [], []
    for i, p in enumerate(P):
        if i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = (P[i] - P[i - 1]).normalized() + (P[i + 1] - P[i]).normalized()
        t.normalize()
        nx, nz = -t.y, t.x
        ro_, ri_ = [], []
        for j in range(seg + 1):
            th = math.pi * j / seg
            c, s = math.cos(th), math.sin(th)
            ro_.append(bm.verts.new((p.x + ro * c * nx, y0 + ro * s, p.y + ro * c * nz)))
            ri_.append(bm.verts.new((p.x + ri * c * nx, y0 + ri * s, p.y + ri * c * nz)))
        rings_o.append(ro_)
        rings_i.append(ri_)

    def face(vs, m, smooth):
        f = bm.faces.new(vs)
        f.material_index = m
        f.smooth = smooth

    for i in range(n - 1):
        mx, mz = (P[i].x + P[i + 1].x) / 2, (P[i].y + P[i + 1].y) / 2
        lado = next((a[4] for a in aberturas if a[0] <= mx <= a[2] and a[1] <= mz <= a[3]), 0)
        pular = range(0, seg // 2) if lado > 0 else (range(seg - seg // 2, seg) if lado < 0 else ())
        for j in range(seg):
            if j in pular:
                continue
            face([rings_o[i][j], rings_o[i + 1][j], rings_o[i + 1][j + 1], rings_o[i][j + 1]], mi[0], True)
            face([rings_i[i][j], rings_i[i][j + 1], rings_i[i + 1][j + 1], rings_i[i + 1][j]], mi[1], True)
        for j in (0, seg):
            if (j == 0 and lado > 0) or (j == seg and lado < 0):
                continue
            face([rings_o[i][j], rings_i[i][j], rings_i[i + 1][j], rings_o[i + 1][j]], mi[2], False)
    for i, tem in ((0, pontas[0]), (n - 1, pontas[1])):
        if not tem:
            continue
        for j in range(seg):
            face([rings_o[i][j], rings_o[i][j + 1], rings_i[i][j + 1], rings_i[i][j]], mi[2], False)


def _subdividir(cam, dmax=0.06):
    """Quebra trechos retos longos (aberturas e animações por dentro do cano precisam de pontos no meio)."""
    out = [cam[0]]
    for a, b in zip(cam, cam[1:]):
        A, B = Vector(a), Vector(b)
        n = max(1, int(math.ceil((B - A).length / dmax)))
        for j in range(1, n + 1):
            p = A.lerp(B, j / n)
            out.append((p.x, p.y))
    return out


def cano_corte(name, M, pts, r=0.065, esp=0.012, y=-0.015, rc=None, seg=10, m="pvc", m_in="pvc_in", aberturas=(),
               pontas=(True, True)):
    """Cano cortado ao meio no plano y (fica a metade de trás, y >= y) seguindo a polilinha pts [(x, z)], com os cantos
    arredondados (raio rc; padrão 1,8 r). Retorna (objeto, caminho suavizado): o caminho serve para a água
    (agua_cano), as bolhas de gás e a barata andarem por dentro. aberturas: furos na parede onde outro cano chega
    (veja _meio_tubo). Numa junção: abra o cano que recebe (aberturas) e faça o que chega entrar até o meio dele,
    sem a borda na ponta (pontas)."""
    cam = _subdividir(_caminho_suave(pts, 1.8 * r if rc is None else rc))
    bm = bmesh.new()
    _meio_tubo(bm, cam, r, r - esp, y, seg, aberturas=aberturas, pontas=pontas)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, [M[m], M[m_in], M[m]]), cam


def furo_cano(cam, r, folga=0.006):
    """Polígono (x-z) ocupado por um cano: use como furo em terrain() e bloco_corte()."""
    return sg.LineString(cam).buffer(r + folga, cap_style=2, join_style=1)


def caminho_sifao(x, z_topo, z_fundo, largura=0.25, z_saida=None, n=12):
    """Polilinha de um sifão em U: desce em x de z_topo até a curva (fundo em z_fundo), sobe do outro lado
    (x + largura) até z_saida. Retorna a lista [(x, z)]."""
    R = largura / 2
    zc = z_fundo + R
    pts = [(x, z_topo), (x, zc)]
    for j in range(1, n):
        a = math.pi + math.pi * j / n
        pts.append((x + R + R * math.cos(a), zc + R * math.sin(a)))
    pts += [(x + largura, zc), (x + largura, z_topo if z_saida is None else z_saida)]
    return pts


def agua_cano(name, M, cam, ri, nivel, y=-0.015, m="water_c", ate=None, de=0):
    """Água parada no cano em corte: o trecho cam[de:ate] abaixo de `nivel` (z). Frente em y + 0,002, para aparecer
    por dentro do meio tubo. Para o nível subir/descer use nivel_agua() + nivel()."""
    trecho = cam[de:ate]
    zona = sg.LineString(trecho).buffer(ri * 0.985, cap_style=2, join_style=1)
    agua = zona.intersection(sg.box(-1e4, -1e4, 1e4, nivel))
    bm = bmesh.new()
    for p in mt.polys(agua):
        mt.prism_bm(bm, mt.ring(p), y + 0.002, y + ri * 0.8)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, M[m])


def nivel_agua(o, z):
    """Nível animado: a água fica só abaixo de z (corte booleano por uma caixa invisível). Retorna a caixa:
    anime com nivel(caixa, t, z). Para encher depois de vazia, comece com z abaixo do fundo."""
    cx = box(o.name + "_nivel", -80, 80, -80, 80, -80, 0, o.data.materials[0], anchor="top")
    cx.location = (0, 0, z)
    cx.hide_render = True
    cx.display_type = "WIRE"
    b = o.modifiers.new("nivel", "BOOLEAN")
    b.operation = "INTERSECT"
    b.object = cx
    b.solver = "EXACT"
    return cx


def nivel(cx, t, z):
    k(cx, "location", t, (0, 0, z))


def bolhas_cano(name, M, cam, t0, t1, n=6, periodo=2.0, r=0.022, mat_nome="gas", inverter=False, ate=None):
    """Bolhas (gás) andando dentro do cano pelo caminho `cam` (do esgoto para cima: use inverter=True se o caminho foi
    desenhado no sentido da água). `ate`: para no ponto de índice `ate` (ex.: na água do sifão). Retorna as bolhas."""
    pts = list(reversed(cam)) if inverter else list(cam)
    if ate is not None:
        pts = pts[:ate]
    pts3 = [(x, 0.03, z) for x, z in pts]
    out = []
    for i in range(n):
        s = t0 + periodo * i / n
        if s >= t1:
            continue
        loops = max(1, int((t1 - s) / periodo))
        b = esfera(f"{name}{i}", r * (0.8 + 0.4 * ((i * 7) % 5) / 4), pts3[0], M[mat_nome], seg=12)
        mt.along(b, pts3, s, s + loops * periodo, loops=loops)
        out.append(b)
    return out


# ---------------------------------------------------------------- peças do banheiro
def ralo_grelha(name, M, r=0.085):
    """Grelha redonda de ralo (inox) com frestas; topo em z = 0 (encoste no piso). Origem no centro do topo."""
    root = empty(name)
    child(cyl(name + "_aro", r, -0.012, 0.0, (0, 0), M["grate"], seg=28), root)
    for i in range(5):
        yy = (i - 2) * r * 0.32
        half = math.sqrt(max((r * 0.82) ** 2 - yy * yy, 1e-4))
        child(box(f"{name}_f{i}", -half, half, yy - 0.009, yy + 0.009, -0.002, 0.0015, M["grate_slot"]), root)
    return root


def _toro(name, R, r, m, sx=1.0, sy=1.0, seg=28, seg2=8):
    bm = bmesh.new()
    vs = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        row = []
        for j in range(seg2):
            b = 2 * math.pi * j / seg2
            rr = R + r * math.cos(b)
            row.append(bm.verts.new((rr * math.cos(a) * sx, rr * math.sin(a) * sy, r * math.sin(b))))
        vs.append(row)
    for i in range(seg):
        for j in range(seg2):
            bm.faces.new([vs[i][j], vs[(i + 1) % seg][j], vs[(i + 1) % seg][(j + 1) % seg2], vs[i][(j + 1) % seg2]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _liso(mesh_obj(name, bm, m))


def _decal(name, poly, y0, y1, m):
    bm = bmesh.new()
    for p in mt.polys(poly):
        mt.prism_bm(bm, mt.ring(p), y0, y1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, m)


def vaso_sanitario(name, M, corte=False):
    """Vaso com caixa acoplada, de perfil: a bacia aponta para -x e a caixa fica em +x (encoste a caixa na parede).
    Origem no chão, no centro da saída de esgoto (o cano desce dali). Tampa levantada.
    corte=True: cortado ao meio no plano y = 0 local (fica a metade de trás) com o desenho de dentro: bacia, sifão do
    vaso com a água parada e a caixa com água. Retorna dict 'raiz' e, no corte, 'agua_bacia', 'agua_caixa' (anime o
    nível com nivel_agua) e 'sifao' (caminho [(x, z)] local do sifão até a saída, para a água da descarga)."""
    root = empty(name)
    P = {"raiz": root}
    child(caixa_arred(name + "_pe", -0.2, 0.12, -0.13, 0.13, 0.0, 0.31, M["porcelain"], r=0.05), root)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.13, radius2=0.205, depth=0.2,
                          matrix=Matrix.Translation((0, 0, 0.36)))
    for v in bm.verts:
        v.co.x *= 1.42
    bacia = child(_liso(mesh_obj(name + "_bacia", bm, M["porcelain"])), root, (-0.15, 0, 0))
    child(caixa_arred(name + "_apoio", -0.02, 0.31, -0.12, 0.12, 0.28, 0.46, M["porcelain"], r=0.04), root)
    child(_toro(name + "_assento", 0.17, 0.022, M["porcelain"], sx=1.45, sy=0.95), root, (-0.15, 0, 0.482))
    tampa = child(esfera(name + "_tampa", 1, (0, 0, 0), M["porcelain"], scale=(0.27, 0.19, 0.018)), root, (0.035, 0, 0.72))
    tampa.rotation_euler = (0, math.radians(-96), 0)
    child(caixa_arred(name + "_caixa", 0.08, 0.31, -0.19, 0.19, 0.46, 0.84, M["porcelain"], r=0.03), root)
    child(caixa_arred(name + "_caixa_tampa", 0.065, 0.325, -0.2, 0.2, 0.84, 0.88, M["porcelain"], r=0.015), root)
    child(cyl(name + "_botao", 0.026, 0.88, 0.894, (0.195, 0), M["chrome"], seg=16), root)
    if not corte:
        return P
    cortar_y(root, 0.0, 1)
    # desenho interno na face cortada (y = 0): cavidades, sifão do vaso e água
    sif = _caminho_suave([(-0.065, 0.225), (-0.005, 0.2), (0.05, 0.26), (0.07, 0.325), (0.088, 0.25), (0.065, 0.13),
                          (0.0, 0.04), (0.0, -0.02)], 0.03)
    canal = sg.LineString(sif).buffer(0.031, cap_style=2, join_style=1)
    cav = sg.Polygon([(-0.405, 0.458), (0.105, 0.458), (0.0, 0.3), (-0.025, 0.215), (-0.1, 0.215), (-0.175, 0.3)])
    cav = cav.buffer(0.02).buffer(-0.02)
    dentro = unary_union([cav, canal]).intersection(sg.box(-1, 0.0, 1, 2))
    _decal(name + "_dentro", dentro, -0.004, 0.0, M["porcelain_in"]).parent = root
    i_crista = max(range(len(sif)), key=lambda i: sif[i][1])
    z_agua = sif[i_crista][1] - 0.031
    subida = sg.LineString(sif[:i_crista + 1]).buffer(0.03, cap_style=2, join_style=1)
    agua = unary_union([cav, subida]).intersection(sg.box(-1, -1, 1, z_agua))
    P["agua_bacia"] = _decal(name + "_agua_bacia", agua, -0.007, -0.002, M["water_c"])
    P["agua_bacia"].parent = root
    cx = sg.box(0.105, 0.485, 0.285, 0.83)
    _decal(name + "_caixa_dentro", cx, -0.004, 0.0, M["porcelain_in"]).parent = root
    P["agua_caixa"] = _decal(name + "_agua_caixa", sg.box(0.105, 0.485, 0.285, 0.745), -0.007, -0.002, M["water_c"])
    P["agua_caixa"].parent = root
    child(box(name + "_ladrao", 0.235, 0.25, -0.012, -0.007, 0.49, 0.79, M["porcelain"]), root)
    child(box(name + "_vedante", 0.13, 0.21, -0.012, -0.006, 0.485, 0.51, M["flapper"]), root)
    P["sifao"], P["z_agua"] = sif, z_agua
    return P


def chuveiro(name, M, braco=0.32):
    """Chuveiro preso na parede (origem na parede), braço para -y e ducha virada para baixo; registro embaixo."""
    root = empty(name)
    child(tube(name + "_braco", (0, 0, 0), (0, -braco, 0.0), 0.014, M["chrome"], seg=10), root)
    child(tube(name + "_desce", (0, -braco, 0.0), (0, -braco - 0.04, -0.07), 0.014, M["chrome"], seg=10), root)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.085, radius2=0.03, depth=0.06,
                          matrix=Matrix.Translation((0, 0, 0.03)))
    child(_liso(mesh_obj(name + "_ducha", bm, M["chrome"])), root, (0, -braco - 0.05, -0.16))
    child(disc(name + "_canopla", 0.04, 0.012, M["chrome"], seg=20), root, (0, -0.004, 0))
    child(disc(name + "_registro", 0.035, 0.03, M["chrome"], seg=20), root, (0, -0.012, -1.05))
    alav = child(box(name + "_manopla", -0.06, 0.06, -0.035, -0.02, -0.01, 0.01, M["chrome"], anchor="center"), root,
                 (0, -0.01, -1.05))
    return root


def pia_banheiro(name, M, largura=0.7):
    """Gabinete com cuba de apoio e torneira, de frente para -y; origem no chão, no meio da parede (y = 0)."""
    root = empty(name)
    w = largura / 2
    child(caixa_arred(name + "_gab", -w, w, -0.45, 0.0, 0.12, 0.8, M["sink_cab"], r=0.015), root)
    child(caixa_arred(name + "_tampo", -w - 0.02, w + 0.02, -0.48, 0.0, 0.8, 0.84, M["counter"], r=0.01), root)
    for s in (-1, 1):
        child(box(f"{name}_porta{s}", s * 0.015 if s > 0 else -w + 0.02, w - 0.02 if s > 0 else -0.015, -0.47, -0.45,
                  0.16, 0.76, M["sink_cab"]), root)
        child(caixa_arred(f"{name}_pux{s}", s * 0.04 - 0.008, s * 0.04 + 0.008, -0.49, -0.47, 0.6, 0.7, M["handle"],
                          r=0.004), root)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.05], context="VERTS")
    for v in bm.verts:
        v.co.x *= 0.22; v.co.y *= 0.17; v.co.z *= 0.1
    cuba = child(_liso(mesh_obj(name + "_cuba", bm, M["porcelain"])), root, (0, -0.24, 0.94))
    cuba.modifiers.new("esp", "SOLIDIFY").thickness = 0.012
    child(tube(name + "_torneira", (0, -0.05, 0.84), (0, -0.05, 1.02), 0.013, M["chrome"], seg=10), root)
    child(tube(name + "_bica", (0, -0.05, 1.02), (0, -0.15, 1.02), 0.011, M["chrome"], seg=10), root)
    return root


def espelho(name, M, largura=0.55, altura=0.7):
    """Espelho de frente para -y (encoste em y = 0 da parede). Origem no centro."""
    root = empty(name)
    child(caixa_arred(name + "_moldura", -largura / 2, largura / 2, -0.02, 0.0, -altura / 2, altura / 2, M["chrome"],
                      r=0.012, anchor="center"), root)
    child(caixa_arred(name + "_vidro", -largura / 2 + 0.025, largura / 2 - 0.025, -0.024, -0.02, -altura / 2 + 0.025,
                      altura / 2 - 0.025, M["mirror"], r=0.01, anchor="center"), root)
    return root


def box_vidro(name, M, comprimento=1.3, altura=1.9):
    """Painel de vidro do box ao longo de +y (a partir da origem, no chão), com perfis de alumínio."""
    root = empty(name)
    child(box(name + "_vidro", -0.006, 0.006, 0.0, comprimento, 0.03, altura, M["glass_box"]), root)
    for z0, z1 in ((0.0, 0.03), (altura, altura + 0.025)):
        child(box(f"{name}_perfil{z0}", -0.014, 0.014, 0.0, comprimento, z0, z1, M["chrome"]), root)
    child(box(name + "_ponta", -0.014, 0.014, comprimento - 0.025, comprimento, 0.0, altura + 0.025, M["chrome"]), root)
    return root


def toalha(name, M, largura=0.45, altura=0.6, cor="towel"):
    """Toalha pendurada num suporte, de frente para -y (encoste em y = 0 da parede). Origem no suporte."""
    root = empty(name)
    child(tube(name + "_barra", (-largura / 2 - 0.05, -0.05, 0), (largura / 2 + 0.05, -0.05, 0), 0.012, M["chrome"]), root)
    for s in (-1, 1):
        child(tube(f"{name}_haste{s}", (s * (largura / 2 + 0.05), 0, 0), (s * (largura / 2 + 0.05), -0.05, 0), 0.01,
                   M["chrome"]), root)
    child(caixa_arred(name + "_pano", -largura / 2, largura / 2, -0.075, -0.035, -altura, 0.02, M[cor], r=0.015), root)
    child(box(name + "_faixa", -largura / 2, largura / 2, -0.078, -0.07, -altura + 0.06, -altura + 0.1, M["white"]), root)
    return root


def frasco(name, M, corpo="disinfectant", rotulo="label_lilac", tampa="cap_w", altura=0.24, largura=0.1):
    """Frasco de produto de limpeza (desinfetante, água sanitária). Origem na base; o bico fica no topo (+z).
    Para despejar, gire em y (o bico vai para +x com rotação positiva)."""
    root = empty(name)
    w, d, h = largura / 2, largura * 0.32, altura
    child(caixa_arred(name + "_corpo", -w, w, -d, d, 0, h * 0.72, M[corpo], r=0.02), root)
    child(esfera(name + "_ombro", 1, (0, 0, h * 0.72), M[corpo], scale=(w, d, h * 0.12)), root)
    child(cyl(name + "_gargalo", 0.017, h * 0.78, h * 0.9, (0, 0), M[corpo], seg=14), root)
    child(cyl(name + "_tampa", 0.021, h * 0.88, h, (0, 0), M[tampa], seg=14), root)
    child(caixa_arred(name + "_rotulo", -w - 0.003, w + 0.003, -d - 0.003, d + 0.003, h * 0.18, h * 0.52, M[rotulo],
                      r=0.012), root)
    return root


def jarra(name, M, agua="water_c"):
    """Jarra transparente com água, bico para -x e alça em +x. Origem na base."""
    root = empty(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=22, radius1=0.07, radius2=0.085, depth=0.21,
                          matrix=Matrix.Translation((0, 0, 0.105)))
    c = child(_liso(mesh_obj(name + "_corpo", bm, M["pitcher"])), root)
    c.modifiers.new("esp", "SOLIDIFY").thickness = 0.005
    child(cyl(name + "_fundo", 0.07, 0, 0.008, (0, 0), M["pitcher"], seg=22), root)
    child(cyl(name + "_agua", 0.067, 0.008, 0.15, (0, 0), M[agua], seg=22), root)
    child(cone(name + "_bico", 0.03, 0.05, M["pitcher"], seg=10), root, (-0.085, 0, 0.19)).rotation_euler = (0, math.radians(-70), 0)
    for a, b in (((0.08, 0, 0.18), (0.14, 0, 0.17)), ((0.14, 0, 0.17), (0.14, 0, 0.06)), ((0.14, 0, 0.06), (0.075, 0, 0.05))):
        child(tube(f"{name}_alca{a[2]}", a, b, 0.012, M["pitcher"], seg=8), root)
    return root


def escova(name, M):
    """Escova de limpeza: cerdas para -z na origem, cabo para +x."""
    root = empty(name)
    child(caixa_arred(name + "_base", -0.06, 0.06, -0.03, 0.03, 0.0, 0.03, M["brush"], r=0.01), root)
    child(box(name + "_cerdas", -0.055, 0.055, -0.026, 0.026, -0.03, 0.0, M["bristle"]), root)
    cabo = child(caixa_arred(name + "_cabo", 0.0, 0.26, -0.014, 0.014, 0.0, 0.025, M["brush"], r=0.01), root, (0.04, 0, 0.02))
    cabo.rotation_euler = (0, math.radians(-25), 0)
    return root


def bolo_cabelo(name, M, tam=0.05, seed=4):
    """Bolo de cabelo e sabão (sujeira do ralo)."""
    rr = random.Random(seed)
    root = empty(name)
    for i in range(7):
        a, b = Vector((rr.uniform(-1, 1), rr.uniform(-0.4, 0.4), rr.uniform(-0.5, 0.5))) * tam, \
            Vector((rr.uniform(-1, 1), rr.uniform(-0.4, 0.4), rr.uniform(-0.5, 0.5))) * tam
        child(tube(f"{name}_fio{i}", a, b, 0.004, M["hair"], seg=5), root)
    child(esfera(name + "_sabao", tam * 0.55, (0, 0, 0), M["egg"], scale=(1, 0.7, 0.6), seg=12), root)
    return root


def barata(name, M, tam=0.1):
    """Barata andando para +x (antenas na frente). Origem no chão, no meio do corpo; `tam` ≈ comprimento.
    Retorna (raiz, pernas): mexa as pernas com andar_barata(pernas, t0, t1)."""
    root = empty(name)
    s = tam
    child(esfera(name + "_corpo", 1, (0, 0, 0.17 * s), M["roach_dark"], scale=(0.4 * s, 0.22 * s, 0.1 * s)), root)
    for lado in (-1, 1):
        a = child(esfera(f"{name}_asa{lado}", 1, (-0.04 * s, lado * 0.065 * s, 0.235 * s), M["roach"],
                         scale=(0.37 * s, 0.12 * s, 0.045 * s)), root)
        a.rotation_euler = (0, 0, -lado * 0.1)
    child(esfera(name + "_cabeca", 1, (0.42 * s, 0, 0.16 * s), M["roach_dark"], scale=(0.09 * s, 0.1 * s, 0.075 * s)), root)
    for lado in (-1, 1):
        pts = [(0.48 * s, lado * 0.04 * s, 0.18 * s), (0.75 * s, lado * 0.17 * s, 0.27 * s), (1.0 * s, lado * 0.3 * s, 0.22 * s)]
        for j in range(2):
            child(tube(f"{name}_antena{lado}{j}", pts[j], pts[j + 1], 0.011 * s, M["roach_dark"], seg=5), root)
    pernas = []
    for i, (x, dx) in enumerate(((0.22, 0.12), (0.0, 0.0), (-0.2, -0.14))):
        for lado in (-1, 1):
            h = child(empty(f"{name}_perna{i}{lado}"), root, (x * s, lado * 0.12 * s, 0.15 * s))
            p1 = (dx * 0.5 * s, lado * 0.17 * s, 0.07 * s)
            p2 = (dx * s, lado * 0.3 * s, -0.15 * s)
            child(tube(f"{name}_coxa{i}{lado}", (0, 0, 0), p1, 0.016 * s, M["roach_dark"], seg=5), h)
            child(tube(f"{name}_canela{i}{lado}", p1, p2, 0.012 * s, M["roach_dark"], seg=5), h)
            pernas.append((h, i, lado))
    return root, pernas


def andar_barata(pernas, t0, t1, passo=0.07, amp=0.45):
    """Pernas alternando em tripé entre t0 e t1."""
    t, fase = t0, 0
    while t <= t1:
        for h, i, lado in pernas:
            grupo = (i + (0 if lado > 0 else 1)) % 2
            sinal = 1 if grupo == fase else -1
            k(h, "rotation_euler", t, (0, 0, sinal * amp * lado))
        fase = 1 - fase
        t += passo
    for h, i, lado in pernas:
        k(h, "rotation_euler", t1 + passo, (0, 0, 0))


def seguir_caminho(o, pts, t0, t1, eixo_frente="X", cima=(0, -1, 0), passos=None):
    """Move e gira o objeto pela polilinha 3D pts entre t0 e t1 (velocidade constante), com a frente (eixo local)
    apontando para onde ele anda. `cima`: para onde fica o "dorso" (ex.: (0, -1, 0) = virado para a câmera)."""
    P = [Vector(p) for p in pts]
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)
    o.rotation_mode = "QUATERNION"
    up = Vector(cima)
    for p, l, i in zip(P, L, range(len(P))):
        t = t0 + (t1 - t0) * l / L[-1]
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)])
        if d.length < 1e-6:
            continue
        q = d.normalized().to_track_quat(eixo_frente, "Z")
        # gira em volta da direção para o "dorso" ficar o mais perto possível de `cima`
        z_atual = q @ Vector((0, 0, 1))
        alvo = (up - d.normalized() * up.dot(d.normalized()))
        if alvo.length > 1e-6:
            ang = z_atual.angle(alvo.normalized())
            eixo = z_atual.cross(alvo.normalized())
            if eixo.length > 1e-6:
                q = Quaternion(eixo.normalized(), ang) @ q
        k(o, "location", t, tuple(p))
        k(o, "rotation_quaternion", t, q)


def ovo_podre(name, M, tam=0.12, seed=6):
    """Ovo podre (cheiro de enxofre): casca creme com manchas esverdeadas e uma rachadura. Origem na base."""
    rr = random.Random(seed)
    root = empty(name)
    R = tam / 2
    child(esfera(name + "_casca", R, (0, 0, R * 1.05), M["egg"], scale=(0.78, 0.78, 1.0)), root)
    for i in range(7):
        a, f = rr.uniform(-2.6, -0.5), rr.uniform(0.35, 1.9)
        p = Vector((0.78 * R * math.cos(a) * math.sin(f), 0.78 * R * math.sin(a) * math.sin(f), R * math.cos(f) + R * 1.05))
        m = child(esfera(f"{name}_mancha{i}", R * rr.uniform(0.12, 0.22), tuple(p), M["egg_rot"], scale=(1, 1, 0.45), seg=12), root)
        m.rotation_mode = "QUATERNION"
        m.rotation_quaternion = Vector((0, 0, 1)).rotation_difference((p - Vector((0, 0, R * 1.05))).normalized())
    zz = [(-0.5, 1.5), (-0.2, 1.25), (0.05, 1.45), (0.3, 1.2), (0.55, 1.4)]
    for j in range(len(zz) - 1):
        a = Vector((zz[j][0] * R * 0.7, -0.8 * R, zz[j][1] * R))
        b = Vector((zz[j + 1][0] * R * 0.7, -0.8 * R, zz[j + 1][1] * R))
        child(tube(f"{name}_trinca{j}", a, b, R * 0.04, M["roach_dark"], seg=4), root)
    return root


def _tubo_poli(name, pts, r, m, seg=6):
    """Tubo liso ao longo de uma polilinha 3D (uma malha só)."""
    P = [Vector(p) for p in pts]
    bm = bmesh.new()
    rings = []
    for i, p in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        q = d.to_track_quat("Z", "Y")
        rings.append([bm.verts.new(p + q @ Vector((r * math.cos(2 * math.pi * j / seg), r * math.sin(2 * math.pi * j / seg), 0)))
                      for j in range(seg)])
    for i in range(len(P) - 1):
        for j in range(seg):
            f = bm.faces.new([rings[i][j], rings[i][(j + 1) % seg], rings[i + 1][(j + 1) % seg], rings[i + 1][j]])
            f.smooth = True
    for ring_, rev in ((rings[0], True), (rings[-1], False)):
        bm.faces.new(list(reversed(ring_)) if rev else ring_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, m)


def fedor(name, M, base, n=3, altura=0.42, largura=0.16, r=0.01, mat_nome="gas", seed=1):
    """Linhas onduladas de mau cheiro subindo de `base` (x, y, z). Retorna as linhas (anime com animar_fedor)."""
    rr = random.Random(seed)
    linhas = []
    for i in range(n):
        x0 = (i - (n - 1) / 2) * largura / max(1, n - 1)
        ph = rr.uniform(0, 6.28)
        pts = [(x0 + 0.032 * math.sin(f / 14 * 2 * math.pi * 1.6 + ph), 0, f / 14 * altura) for f in range(15)]
        o = _tubo_poli(f"{name}{i}", pts, r, M[mat_nome])
        o.location = base
        o.scale = (0, 0, 0)
        linhas.append(o)
    return linhas


def animar_fedor(linhas, t0, t1, periodo=1.3, sobe=0.3):
    """Cada linha nasce, sobe e some em ciclos entre t0 e t1 (defasadas)."""
    for i, o in enumerate(linhas):
        base = Vector(o.location)
        t = t0 + periodo * i / len(linhas)
        mt.jump(o, "scale", t, (0, 0, 0), (0, 0, 0))
        while t + periodo <= t1 + 1e-6:
            k(o, "location", t, base); mt.ks(o, t, (0.6, 0.6, 0.2))
            k(o, "location", t + periodo * 0.3, base + Vector((0, 0, sobe * 0.3))); mt.ks(o, t + periodo * 0.3, 1.0)
            k(o, "location", t + periodo * 0.75, base + Vector((0, 0, sobe * 0.75))); mt.ks(o, t + periodo * 0.75, 1.0)
            k(o, "location", t + periodo, base + Vector((0, 0, sobe))); mt.ks(o, t + periodo, (0, 0, 0))
            t += periodo
        k(o, "location", t, base)


def nuvem(name, M, centro, raio=0.35, n=10, mat_nome="perfume", seed=2):
    """Nuvem de bolas lisas (perfume, gás, fumaça) em volta de `centro`. Retorna a raiz (anime com pop_in/ks)."""
    rr = random.Random(seed)
    root = empty(name, centro)
    for i in range(n):
        a = rr.uniform(0, 2 * math.pi)
        d = raio * rr.uniform(0.0, 0.75)
        p = (d * math.cos(a), d * math.sin(a) * 0.6, raio * 0.35 * rr.uniform(-1, 1))
        child(esfera(f"{name}{i}", raio * rr.uniform(0.32, 0.55), p, M[mat_nome], seg=16), root)
    return root


def bacterias(name, M, centro, raio=0.07, n=9, tam=0.012, seed=5):
    """Bactérias (cápsulas verdes) espalhadas num disco horizontal em volta de `centro`. Retorna a lista."""
    rr = random.Random(seed)
    out = []
    for i in range(n):
        a, d = rr.uniform(0, 2 * math.pi), raio * math.sqrt(rr.random())
        o = capsula(f"{name}{i}", tam, tam * 1.6, M["bact"], seg=10)
        o.location = (centro[0] + d * math.cos(a), centro[1] + d * math.sin(a), centro[2] + tam)
        o.rotation_euler = (math.pi / 2, 0, rr.uniform(0, math.pi))
        out.append(o)
    return out


# ---------------------------------------------------------------- esgoto fora de casa
def caixa_inspecao(name, M, x0, x1, z_fundo, y=-0.005, prof=0.32, esp=0.06, furos=()):
    """Caixa de inspeção de concreto em corte (metade de trás), da superfície (z = 0) até z_fundo, com tampa e
    esgoto no fundo. `furos`: polígonos (x-z) dos canos que atravessam as paredes. Retorna (raiz, esgoto)."""
    root = empty(name)
    blocos = []
    for nm, poly in (("esq", sg.box(x0, z_fundo, x0 + esp, 0.0)), ("dir", sg.box(x1 - esp, z_fundo, x1, 0.0)),
                     ("fundo", sg.box(x0, z_fundo - esp, x1, z_fundo))):
        blocos += bloco_corte(f"{name}_{nm}", poly, y, prof + esp, M["concrete_p"], furos=furos, y_furo=0.1)
    blocos.append(box(name + "_tras", x0 + esp, x1 - esp, prof, prof + esp, z_fundo, 0.0, M["concrete_p"]))
    blocos.append(box(name + "_dentro", x0 + esp, x1 - esp, prof - 0.004, prof, z_fundo, 0.0, M["concrete_in"]))
    blocos.append(box(name + "_tampa", x0 - 0.03, x1 + 0.03, y, prof + esp + 0.03, 0.0, 0.05, M["concrete_p"]))
    for b in blocos:
        b.parent = root
    esg = box(name + "_esgoto", x0 + esp, x1 - esp, y + 0.004, prof - 0.004, z_fundo, z_fundo + 0.045, M["sewage"])
    esg.parent = root
    return root, esg


def rede_esgoto(name, M, x, z, r=0.36, esp=0.07, y0=-0.02, y1=16.0, nivel_esgoto=0.35, furos=()):
    """Rede de esgoto da rua: manilha de concreto correndo em y (cortada em y0), com esgoto no fundo até
    `nivel_esgoto` (fração do diâmetro interno). `furos`: canos que chegam nela (vazados só perto do corte).
    Retorna (raiz, esgoto)."""
    root = empty(name)
    ri = r - esp
    anel = sg.Point(x, z).buffer(r, 48).difference(sg.Point(x, z).buffer(ri, 48))
    for i, metade in enumerate((sg.box(x - 2 * r, z, x + 2 * r, z + 2 * r), sg.box(x - 2 * r, z - 2 * r, x + 2 * r, z))):
        for o in bloco_corte(f"{name}_anel{i}", anel.intersection(metade), y0, y1, M["concrete_p"], furos=furos, y_furo=0.14):
            o.parent = root
    zs = z - ri + 2 * ri * nivel_esgoto
    esg = sg.Point(x, z).buffer(ri * 0.99, 48).intersection(sg.box(x - r, z - r, x + r, zs))
    e = prism(name + "_esgoto", esg, y0 + 0.004, y1, M["sewage"])
    e.parent = root
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=ri * 0.995, radius2=ri * 0.995, depth=y1 - y0,
                          matrix=Matrix.Translation((0, 0, (y1 - y0) / 2)))
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    dentro = mesh_obj(name + "_dentro", bm, M["concrete_in"])
    dentro.rotation_euler = (-math.pi / 2, 0, 0)
    dentro.location = (x, y0, z)
    dentro.parent = root
    return root, e


def terminal_ventilacao(name, M, r=0.055):
    """Ponta do tubo de ventilação (respiro) acima do telhado: luva + chapéu. Origem na ponta do cano."""
    root = empty(name)
    child(cyl(name + "_luva", r * 1.25, -0.06, 0.04, (0, 0), M["vent_cap"], seg=16), root)
    for i in range(3):
        child(cyl(f"{name}_haste{i}", 0.008, 0.04, 0.12, (math.cos(i * 2.1) * r, math.sin(i * 2.1) * r), M["vent_cap"], seg=6), root)
    child(cone(name + "_chapeu", r * 2.0, 0.08, M["vent_cap"], seg=16), root, (0, 0, 0.11))
    return root
