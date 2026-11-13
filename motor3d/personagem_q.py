"""Personagens do canal sobre o corpo contínuo Quaternius (Universal Base Characters, CC0).

O corpo é um só (sem encaixe de peças); a ROUPA é malha própria: uma casca do corpo empurrada para fora pela normal,
com espessura (Solidify), bordas cortadas retas (cós, barra, gola, manga) e os MESMOS pesos do esqueleto (a casca é
cópia do corpo, então deforma junto). Assim a cintura é a borda da camiseta sobre o cós do jeans, não uma linha de cor.
O rosto é o pintado do nosso boneco (boneco_adulto._rosto) num "decal" que cobre a frente da cabeça, preso ao osso
Head; funciona com ba.falar / ba.piscar / ba.expressao (use Q no lugar de Z).

    import personagem_q as pq
    Q = pq.personagem("cara")                         # motorista: camiseta tijolo, jeans, tênis
    Z = pq.personagem("ze")                           # mecânico: macacão azul-petróleo + laranja, bota
    pq.colocar(Q, (x, y, 0), rumo=90)
    pq.animar(Q, [("andar", 0.0, 1.6, p0, p1), ("parado", 1.6), ("chutar", 1.9), ("ombros", 3.1)])
    pq.rosto(Q, "careta", 1.7); pq.rosto(Q, "desdem", 3.2)          # expressões (boneco_adulto.EXPRESSOES)
    pq.falar(Z, palavras, t0, t1, desloc=t0)          # lip sync por palavras (tempos do .wav)

Cores e peças: personagem(tipo, cores={"pele":..., "camisa":..., "calca":..., "cabelo":...}, camisa="camiseta"|"regata").
"""
import os, math
import bpy, bmesh
from mathutils import Vector, Matrix
import animacao_pronta as ap
import boneco_adulto as ba

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
UBC = os.path.join(RAIZ, "assets/personagens/quaternius_ubc/Universal Base Characters[Standard]")
CORPO = os.path.join(UBC, "Base Characters/Godot - UE/Superhero_Male_FullBody.gltf")
CABELO = os.path.join(UBC, "Hairstyles/Origin at 0/glTF (Godot)/{}.gltf")
UAL = os.path.join(RAIZ, "assets/personagens/quaternius_ual/Universal Animation Library[Standard]/Unreal-Godot/UAL1_Standard.glb")
UAL2 = os.path.join(RAIZ, "assets/personagens/quaternius_ual2/Universal Animation Library 2[Standard]/Unreal-Godot/UAL2_Standard.glb")
BVH = os.path.join(RAIZ, "assets/mocap/cmu_bvh")
FPS = 24
ALTURA_ARQ = 1.81                      # altura do corpo-base no arquivo (m)

TIPOS = {
    "cara": dict(pele="#A86B4C", cabelo="#16100C", camisa="#F0EEE8", calca="#3F5F8F", sapato="#2B2E35",
                 sola="#E6E2DA", cinto="#3A2A1E", altura=1.76, corte="crespo", roupa="civil", peca="regata"),
    "ze": dict(pele="#8A5A40", cabelo="#2A1E17", macacao="#1F4E79", detalhe="#E8590C", sapato="#2A211C",
               sola="#151515", altura=1.79, corte="Hair_SimpleParted", roupa="macacao", peca="macacao"),
}


# ===================================================================== materiais
def _lin(h):
    return ap._lin(h) + [1.0]


def _mat(nome, cor, rough=0.8, normal_img=None, normal_forca=0.5, sheen=0.0):
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = _lin(cor)
    b.inputs["Roughness"].default_value = rough
    if sheen and "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = sheen
    if normal_img:
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = normal_img
        tx.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal_forca
        nt.links.new(tx.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


def _no(nt, tipo, **kw):
    n = nt.nodes.new(tipo)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def _rest(nt):
    """Posição de REPOUSO do ponto (atributo rest_position): a trama e as costuras ficam presas ao pano quando o
    esqueleto mexe (a coordenada de objeto 'escorregaria' na malha deformada)."""
    a = _no(nt, "ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="rest_position")
    return a.outputs["Vector"]


def _tecido(nome, cor, escala=420.0, contraste=0.12, rough=0.85, tipo="malha"):
    """Tecido com trama fina (por coordenada de objeto, que acompanha a deformação): 'brim' = sarja diagonal do jeans
    com desbotado; 'malha' = camiseta; 'lona' = macacão."""
    m = _mat(nome, cor, rough, sheen=0.25)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    rp = _rest(nt)
    wv = _no(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="DIAGONAL")
    wv.inputs["Scale"].default_value = escala
    wv.inputs["Distortion"].default_value = 0.5
    nt.links.new(rp, wv.inputs["Vector"])
    nz = _no(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 9.0
    nt.links.new(rp, nz.inputs["Vector"])
    mx = _no(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mx.inputs["Factor"].default_value = contraste * (1.6 if tipo == "brim" else 1.0)
    mx.inputs[6].default_value = _lin(cor)
    nt.links.new(wv.outputs["Color"], mx.inputs[7])
    cor2 = mx.outputs[2]
    if tipo == "brim":            # desbotado claro em manchas largas (coxa/joelho)
        lv = _no(nt, "ShaderNodeMix", data_type="RGBA")
        lv.inputs[7].default_value = _lin("#7C9BC2")
        r = _no(nt, "ShaderNodeMapRange")
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = 0.5, 0.75
        r.inputs["To Max"].default_value = 0.35
        nt.links.new(nz.outputs["Fac"], r.inputs["Value"])
        nt.links.new(r.outputs[0], lv.inputs["Factor"])
        nt.links.new(cor2, lv.inputs[6])
        cor2 = lv.outputs[2]
    nt.links.new(cor2, b.inputs["Base Color"])
    bp = _no(nt, "ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.08
    bp.inputs["Distance"].default_value = 0.0005
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def _costura(m, regioes, cor="#C9963A", largura=0.0022):
    """Linhas de costura/recorte pintadas por coordenada de objeto (pespontos do jeans, bolsos, recortes do
    macacão): regioes = lista de funções-shader f(X,Y,Z) → máscara (montadas aqui com nós). Usado só p/ retângulos
    e elipses simples: ("ret", x0, x1, z0, z1, lado_y) e ("hz", z, lado_y) (linha horizontal)."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    sp = _no(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(_rest(nt), sp.inputs[0])
    X, Y, Z = sp.outputs[0], sp.outputs[1], sp.outputs[2]

    def op(o, a, bb=None):
        n = _no(nt, "ShaderNodeMath", operation=o)
        for i, x in enumerate((a, bb)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                nt.links.new(x, n.inputs[i])
        return n.outputs[0]

    AX = op("ABSOLUTE", X)
    tot = None
    for r in regioes:
        if r[0] == "ret":
            _, x0, x1, z0, z1, lado = r
            dentro = op("MULTIPLY", op("MULTIPLY", op("GREATER_THAN", AX, x0), op("LESS_THAN", AX, x1)),
                        op("MULTIPLY", op("GREATER_THAN", Z, z0), op("LESS_THAN", Z, z1)))
            dentro2 = op("MULTIPLY", op("MULTIPLY", op("GREATER_THAN", AX, x0 + largura), op("LESS_THAN", AX, x1 - largura)),
                         op("MULTIPLY", op("GREATER_THAN", Z, z0 + largura), op("LESS_THAN", Z, z1 - largura)))
            msk = op("SUBTRACT", dentro, dentro2)
        else:
            _, z, lado = r
            msk = op("LESS_THAN", op("ABSOLUTE", op("SUBTRACT", Z, z)), largura * 0.5)
        lado_ok = op("GREATER_THAN", op("MULTIPLY", Y, lado), 0.0) if lado else 1.0
        msk = op("MULTIPLY", msk, lado_ok)
        tot = msk if tot is None else op("MAXIMUM", tot, msk)
    ent = b.inputs["Base Color"]
    src = ent.links[0].from_socket if ent.links else None
    mx = _no(nt, "ShaderNodeMix", data_type="RGBA")
    if src is not None:
        nt.links.new(src, mx.inputs[6])
    else:
        mx.inputs[6].default_value = ent.default_value
    mx.inputs[7].default_value = _lin(cor)
    nt.links.new(tot, mx.inputs["Factor"])
    nt.links.new(mx.outputs[2], ent)
    return m


# ===================================================================== corpo
def _afinar(o):
    """Corpo de 'super-herói' → homem comum: peito e dorsais menos largos, braços e pescoço mais finos (malha em
    T-pose, edita o repouso: a roupa copiada depois já sai do corpo novo)."""
    def liso(v, a, b):
        t = min(max((v - a) / (b - a), 0.0), 1.0)
        return t * t * (3 - 2 * t)

    for v in o.data.vertices:
        x, y, z = v.co
        ax = abs(x)
        # braços (T-pose: eixo ao longo de x em y≈0,07, z≈1,456)
        if ax > 0.19 and z > 1.28:
            k = liso(ax, 0.19, 0.28) * (1 - liso(ax, 0.66, 0.72))
            f = 1 - 0.16 * k if ax < 0.47 else 1 - 0.10 * k
            v.co.y = 0.07 + (y - 0.07) * f
            v.co.z = 1.456 + (z - 1.456) * f
            if ax < 0.3:              # deltoide/ombro mais estreito
                v.co.x = math.copysign(ax - 0.012 * liso(ax, 0.19, 0.26), x)
        # tronco: peitoral e dorsal
        elif ax <= 0.26 and 0.95 < z < 1.56:
            w = liso(z, 0.95, 1.15) * (1 - liso(z, 1.47, 1.56))
            v.co.x = x * (1 - 0.07 * w)
            if y < 0.03:              # peito/abdome menos saltado
                v.co.y = 0.03 + (y - 0.03) * (1 - 0.13 * w)
            if 1.47 < z < 1.6 and ax < 0.2:    # trapézio
                v.co.z = z - 0.012 * liso(ax, 0.06, 0.16) * (1 - liso(z, 1.52, 1.6))
        # pescoço
        if 1.48 < z < 1.6 and ax < 0.09:
            w = liso(z, 1.48, 1.52) * (1 - liso(z, 1.56, 1.6))
            v.co.x = v.co.x * (1 - 0.1 * w)
            v.co.y = 0.03 + (v.co.y - 0.03) * (1 - 0.06 * w)
    o.data.update()


def _casca(corpo, nome, dentro, desloc, mat, cortes=(), espessura=0.0035, suavizar=0, sub=1, projetar=None,
          forma=None, vies=None, alisar=4, atributos=None):
    """Roupa = cópia do corpo com só as faces de `dentro(x,y,z)`, empurrada `desloc(x,y,z)` (m) pela normal; as
    bordas abertas são niveladas nos planos `cortes` [("z", 0.99), ("x", 0.36)...] (borda reta, sem serrilhado) e
    a espessura vem do Solidify. Mesmos grupos de vértices + Armature do corpo → deforma igual.
    forma(bm): remodela os vértices (ex.: caimento reto); vies=(largura, alto): faixa junto às bordas levantada
    `alto` m (viés/ribana/cós/barra) e marcada no atributo "vies"; atributos={nome: f(co)→(r,g,b)} por vértice."""
    o = corpo.copy()
    o.data = corpo.data.copy()
    o.name = o.data.name = nome
    for c in corpo.users_collection:
        c.objects.link(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)     # costuras de UV do glTF: sem fresta na casca
    fora = [f for f in bm.faces if not dentro(*f.calc_center_median())]
    bmesh.ops.delete(bm, geom=fora, context="FACES")
    soltos = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=soltos, context="VERTS")
    bm.normal_update()
    novo = {v: v.co + v.normal * desloc(*v.co) for v in bm.verts}
    for v, c in novo.items():
        v.co = c
    if forma:
        forma(bm)
        bm.normal_update()
    borda = [v for v in bm.verts if v.is_boundary]
    for v in borda:
        if projetar is not None:
            v.co = projetar(v.co.copy())
            continue
        if v.is_boundary:
            melhor = None
            for eixo, val in cortes:
                i = "xyz".index(eixo)
                cur = abs(v.co[i]) if eixo == "x" else v.co[i]
                d = abs(cur - val)
                if d < 0.035 and (melhor is None or d < melhor[0]):
                    melhor = (d, i, val)
            if melhor:
                _, i, val = melhor
                v.co[i] = math.copysign(val, v.co[i]) if i == 0 else val
    # borda lisa: média com os vizinhos de borda (tira o serrilhado das faces cortadas)
    viz = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in borda}
    for _ in range(alisar):
        novo = {v: (v.co * 2 + sum((u.co for u in viz[v]), Vector())) / (2 + len(viz[v])) for v in borda if viz[v]}
        for v, c in novo.items():
            v.co = c
        if projetar is not None:
            for v in borda:
                v.co = projetar(v.co.copy())
    dist = _dist_borda(bm, borda)
    fv = {}
    if vies:
        larg, alto = vies
        bm.normal_update()
        for v in bm.verts:
            d = dist.get(v, 9.0)
            k = 1.0 if d < larg * 0.7 else max(0.0, 1 - (d - larg * 0.7) / (larg * 0.3))
            fv[v.index] = k
            if k > 0:
                v.co += v.normal * alto * k
    attrs = dict(atributos or {})
    co_rep = {v.index: v.co.copy() for v in bm.verts}
    dist_i = {v.index: dist.get(v, 9.0) for v in bm.verts}
    bm.to_mesh(o.data)
    bm.free()
    a = o.data.color_attributes.new("vies", "FLOAT_COLOR", "POINT")
    for i in range(len(o.data.vertices)):
        k = fv.get(i, 0.0)
        a.data[i].color = (k, min(dist_i[i] / 0.03, 1.0), 0.0, 1.0)
    for nm, f in attrs.items():
        a = o.data.color_attributes.new(nm, "FLOAT_COLOR", "POINT")
        for i in range(len(o.data.vertices)):
            r, g, b = f(co_rep[i])
            a.data[i].color = (r, g, b, 1.0)
    o.add_rest_position_attribute = True
    o.data.materials.clear()
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    if o.data.shape_keys:
        o.shape_key_clear()
    mods = list(o.modifiers)
    for m in mods:
        if m.type != "ARMATURE":
            o.modifiers.remove(m)
    pos = 0
    if suavizar:
        sm = o.modifiers.new("liso", "SMOOTH")
        sm.factor, sm.iterations = 0.8, suavizar
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_move_to_index(modifier="liso", index=pos)
        pos += 1
    so = o.modifiers.new("espessura", "SOLIDIFY")
    so.thickness, so.offset, so.use_rim = espessura, -1.0, True
    so.use_even_offset = True
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_move_to_index(modifier="espessura", index=pos)
    if sub:
        sd = o.modifiers.new("sub", "SUBSURF")
        sd.levels = sd.render_levels = sub
    return o


def _dist_borda(bm, borda):
    """Distância (m, ao longo das arestas) de cada vértice até a borda aberta mais próxima (Dijkstra)."""
    import heapq
    d = {v: 0.0 for v in borda}
    fila = [(0.0, v.index, v) for v in borda]
    heapq.heapify(fila)
    while fila:
        dv, _, v = heapq.heappop(fila)
        if dv > d.get(v, 9.0) or dv > 0.08:
            continue
        for e in v.link_edges:
            u = e.other_vert(v)
            nd = dv + e.calc_length()
            if nd < d.get(u, 9.0):
                d[u] = nd
                heapq.heappush(fila, (nd, u.index, u))
    return d


def _cabelo(Q, corte, cor):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=CABELO.format(corte))
    hs = [o for o in bpy.data.objects if o not in antes and o.type == "MESH"]
    arm = Q["arm"]
    m = _mat(Q["nome"] + "_cabelo", cor, rough=0.65, sheen=0.1)
    # mantém o relevo dos fios (normal map do pacote)
    for h in hs:
        for ms in h.data.materials:
            for n in ms.node_tree.nodes:
                if n.type == "TEX_IMAGE" and "Normal" in (n.image.name if n.image else ""):
                    tx = m.node_tree.nodes.new("ShaderNodeTexImage")
                    tx.image = n.image
                    nm = m.node_tree.nodes.new("ShaderNodeNormalMap")
                    m.node_tree.links.new(tx.outputs["Color"], nm.inputs["Color"])
                    m.node_tree.links.new(nm.outputs["Normal"], m.node_tree.nodes["Principled BSDF"].inputs["Normal"])
                    break
        h.data.materials.clear()
        h.data.materials.append(m)
        mw = h.matrix_world.copy()
        # um pouco de volume: cresce 4 % a partir do centro do crânio
        c = Vector((0, 0.01, 1.70))
        h.matrix_world = Matrix.Translation(c) @ Matrix.Scale(1.04, 4) @ Matrix.Translation(-c) @ mw
        _no_osso(h, arm, "Head")
        for p in h.data.polygons:
            p.use_smooth = True
    return hs


def _no_osso(o, arm, osso):
    mw = o.matrix_world.copy()
    o.parent = arm
    o.parent_type = "BONE"
    o.parent_bone = osso
    bpy.context.view_layer.update()
    o.matrix_world = mw


# ===================================================================== rosto pintado (decal)
def _rosto(Q, cores, expressao="neutro"):
    """Decal do rosto: grade projetada sobre a frente da cabeça (raio de frente), 1,5 mm acima da pele, com o
    material de boneco_adulto._rosto lendo coordenadas de um vazio preso ao osso Head (olhos e boca do material
    alinhados aos da cabeça Quaternius). A borda some em degradê (alfa) sobre a pele de mesma cor."""
    from mathutils.bvhtree import BVHTree
    corpo, arm, nome = Q["corpo"], Q["arm"], Q["nome"]
    alvos = [corpo] + [o for o in Q["malhas"] if o.name.startswith("Eyes")]
    arvores = []
    for o in alvos:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.transform(o.matrix_world)
        arvores.append(BVHTree.FromBMesh(bm))
        bm.free()
    nx, nz = 34, 46
    x0, x1, z0, z1 = -0.078, 0.078, 1.548, 1.78
    vs, cols, idx = [], [], {}
    for j in range(nz + 1):
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            z = z0 + (z1 - z0) * j / nz
            hit = None
            for t in arvores:
                h = t.ray_cast(Vector((x, -0.4, z)), Vector((0, 1, 0)), 0.6)
                if h[0] is not None and (hit is None or h[3] < hit[3]):
                    hit = h
            if hit is None or hit[0].y > -0.02:
                continue
            p = hit[0] + hit[1] * 0.0015
            u, w = (x - x0) / (x1 - x0), (z - z0) / (z1 - z0)
            # borda: some nas laterais, no queixo e na testa; e onde a superfície vira de lado (normal pouco frontal)
            b = min(u, 1 - u) / 0.22
            b = min(b, w / 0.12, (1 - w) / 0.2, max(-hit[1].y - 0.25, 0) / 0.35)
            idx[(i, j)] = len(vs)
            vs.append(p)
            cols.append(max(0.0, min(1.0, b)))
    faces = []
    for j in range(nz):
        for i in range(nx):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if all(k in idx for k in q):
                faces.append([idx[k] for k in q])
    me = bpy.data.meshes.new(nome + "_rosto")
    me.from_pydata(vs, [], faces)
    at = me.color_attributes.new("borda", "FLOAT_COLOR", "POINT")
    for k, c in enumerate(cols):
        at.data[k].color = (c, c, c, 1.0)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(nome + "_rosto", me)
    for c in corpo.users_collection:
        c.objects.link(ob)
    # vazio de referência: o material espera olhos em (±0,036, z 0,016) e boca em z -0,056 (cabeça do Zé)
    ref = bpy.data.objects.new(nome + "_ref_rosto", None)
    for c in corpo.users_collection:
        c.objects.link(ref)
    ref.matrix_world = Matrix.LocRotScale(Vector((0, 0.0, 1.682)), None, Vector((0.95, 1.0, 0.97)))
    bpy.context.view_layer.update()
    _no_osso(ref, arm, "Head")
    _no_osso(ob, arm, "Head")
    P0 = dict(ba.EXPRESSOES.get(expressao, {}))
    cor = {"pele": cores["pele"], "barba": cores["cabelo"], "sobr": cores["cabelo"], "barba_forca": 0.0,
           "labio": cores.get("labio", "#9A5A4A")}
    m, V = ba._rosto(nome + "_m_rosto", P0, cor)
    nt = m.node_tree
    for n in nt.nodes:
        if n.type == "TEX_COORD":
            n.object = ref
    # sobrancelha mais fina: a 1ª divisão por 0,0055 do material é a espessura dela (a 2ª é a do lábio)
    for n in nt.nodes:
        if n.type == "MATH" and n.operation == "DIVIDE" and abs(n.inputs[1].default_value - 0.0055) < 1e-6 \
                and not n.inputs[1].links:
            n.inputs[1].default_value = cores.get("sobr_esp", 0.0036)
            break
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bs = out.inputs["Surface"].links[0].from_socket
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    ca = nt.nodes.new("ShaderNodeVertexColor")
    ca.layer_name = "borda"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(ca.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(bs, mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    me.materials.append(m)
    for o in Q["malhas"]:
        if o.name.startswith(("Eyes", "Eyebrows")):
            o.hide_render = o.hide_viewport = True
    Q["rosto"] = V
    Q["rosto_obj"] = ob
    return V


# ===================================================================== roupa do "cara" (v2)
def _liso(v, a, b):
    t = min(max((v - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


# eixo de cada perna em repouso (quadril → joelho → tornozelo), lado +x; o -x é o espelho
_PERNA = [(0.97, 0.104, 0.04), (0.542, 0.114, 0.036), (0.086, 0.114, 0.088)]


def _eixo_perna(z, sx):
    (z0, x0, y0), (z1, x1, y1), (z2, x2, y2) = _PERNA
    if z >= z1:
        t = (z - z1) / (z0 - z1)
        return sx * (x1 + (x0 - x1) * t), y1 + (y0 - y1) * t
    t = max((z - z2) / (z1 - z2), 0.0)
    return sx * (x2 + (x1 - x2) * t), y2 + (y1 - y2) * t


def _ang_perna(co):
    """(cos, sin, 1) do ângulo em volta do eixo da perna (0 = lado de fora; sin<0 = frente); (0,0,0) fora das pernas."""
    if co.z > 0.78:
        return (0.0, 0.0, 0.0)
    sx = 1 if co.x >= 0 else -1
    cx, cy = _eixo_perna(co.z, sx)
    dx, dy = (co.x - cx) * sx, co.y - cy
    r = math.hypot(dx, dy) or 1.0
    return (dx / r, dy / r, 1.0)


def _forma_calca(bm):
    """Corte reto, um pouco folgado: da coxa para baixo o pano não acompanha a perna (raio mínimo ~7,4 cm)."""
    for v in bm.verts:
        z = v.co.z
        w = 1 - _liso(z, 0.62, 0.76)
        if w <= 0:
            continue
        sx = 1 if v.co.x >= 0 else -1
        cx, cy = _eixo_perna(z, sx)
        d = Vector((v.co.x - cx, v.co.y - cy, 0))
        r = d.length
        if r < 1e-5:
            continue
        alvo = 0.074 + 0.012 * _liso(z, 0.5, 0.74)
        if r < alvo:
            novo = d.normalized() * (r + (alvo - r) * w)
            v.co.x, v.co.y = cx + novo.x, cy + novo.y


def _forma_regata(bm):
    """Caimento reto: do peito ao quadril o pano desce numa elipse (largura/profundidade do peito, ou do quadril +
    cinto se for maior) com pequenas dobras verticais, em vez de colar no abdome."""
    vs = list(bm.verts)
    peito = [v.co for v in vs if 1.22 < v.co.z < 1.28 and abs(v.co.x) < 0.2]
    if not peito:
        return
    a = max(abs(c.x) for c in peito)
    yf, yb = min(c.y for c in peito), max(c.y for c in peito)
    a = max(a, 0.185)
    yf, yb = min(yf, -0.135), max(yb, 0.135)
    yc, b = (yf + yb) / 2, (yb - yf) / 2
    for v in vs:
        z = v.co.z
        w = 1 - _liso(z, 1.18, 1.28)
        if w <= 0 or abs(v.co.x) > 0.25:
            continue
        dx, dy = v.co.x, v.co.y - yc
        th = math.atan2(dy, dx)
        re = 1.0 / math.sqrt((math.cos(th) / a) ** 2 + (math.sin(th) / b) ** 2)
        re *= 1 + 0.03 * (1 - _liso(z, 0.98, 1.2)) + 0.012 * math.sin(th * 11 + 0.7) * (1 - _liso(z, 1.0, 1.25))
        r = math.hypot(dx, dy)
        re = r + (re - r) * 0.55                  # leve folga, sem virar saco
        if r < re:
            k = (r + (re - r) * w) / r
            v.co.x, v.co.y = dx * k, yc + dy * k


def _acabamento(o, mat, raio=0.0042, lados=8, alisar=12, so_z_acima=None):
    """Viés/ribana: tubo liso seguindo cada borda aberta da casca `o` (esconde qualquer serrilhado do corte), com os
    pesos do vértice de borda mais próximo (deforma junto). so_z_acima: só as bordas acima dessa altura."""
    me = o.data
    viz = {}
    cont = {}
    for p in me.polygons:
        for k in p.edge_keys:
            cont[k] = cont.get(k, 0) + 1
    for (a, b), n in cont.items():
        if n == 1:
            viz.setdefault(a, []).append(b)
            viz.setdefault(b, []).append(a)
    feitos, lacos = set(), []
    for v0 in viz:
        if v0 in feitos:
            continue
        laco, ant, cur = [v0], None, v0
        feitos.add(v0)
        while True:
            nx = [u for u in viz[cur] if u != ant and u not in feitos]
            if not nx:
                break
            ant, cur = cur, nx[0]
            laco.append(cur)
            feitos.add(cur)
        if len(laco) > 4:
            lacos.append(laco)
    co = [v.co.copy() for v in me.vertices]
    vs, fs, origem = [], [], []
    for laco in lacos:
        if so_z_acima is not None and max(co[i].z for i in laco) < so_z_acima:
            continue
        P = [co[i].copy() for i in laco]
        n = len(P)
        for _ in range(alisar):
            P = [(P[(k - 1) % n] + P[k] * 2 + P[(k + 1) % n]) / 4 for k in range(n)]
        base = len(vs)
        for k in range(n):
            t = (P[(k + 1) % n] - P[(k - 1) % n]).normalized()
            u = t.orthogonal().normalized()
            w = t.cross(u)
            for j in range(lados):
                a = 2 * math.pi * j / lados
                vs.append(P[k] + (u * math.cos(a) + w * math.sin(a)) * raio)
                origem.append(laco[k])
        for k in range(n):
            k2 = (k + 1) % n
            for j in range(lados):
                j2 = (j + 1) % lados
                fs.append([base + k * lados + j, base + k2 * lados + j, base + k2 * lados + j2, base + k * lados + j2])
    if not vs:
        return None
    tm = bpy.data.meshes.new(o.name + "_vies")
    tm.from_pydata(vs, [], fs)
    for p in tm.polygons:
        p.use_smooth = True
    t = bpy.data.objects.new(o.name + "_vies", tm)
    for c in o.users_collection:
        c.objects.link(t)
    t.parent = o.parent
    t.matrix_world = o.matrix_world.copy()
    grupos = {g.index: t.vertex_groups.new(name=g.name) for g in o.vertex_groups}
    for i, src in enumerate(origem):
        for g in me.vertices[src].groups:
            grupos[g.group].add([i], g.weight, "REPLACE")
    am = t.modifiers.new("Armature", "ARMATURE")
    am.object = next(m.object for m in o.modifiers if m.type == "ARMATURE")
    t.add_rest_position_attribute = True
    tm.materials.append(mat)
    return t


def _regata(corpo, nome, cor):
    def gola(ax, y):
        return (1.497 + 0.03 * (ax / 0.085) ** 2) if y < 0.03 else (1.525 + 0.012 * (ax / 0.085) ** 2)

    def cava(z):
        return 0.192 - (z - 1.30) * 0.16

    def tem(x, y, z):
        ax = abs(x)
        if not (0.972 < z < 1.6) or ax > 0.3:
            return False
        if z > 1.29 and ax > cava(z):
            return False
        return not (ax < 0.085 and z > gola(ax, y))

    def projetar(c):
        ax, sx = abs(c.x), (1 if c.x >= 0 else -1)
        if c.z < 1.15:
            c.z = 0.972
            return c
        dg = abs(c.z - gola(min(ax, 0.085), c.y)) if ax < 0.105 else 9.0
        dc = abs(ax - cava(c.z)) if c.z > 1.27 else 9.0
        if dg <= dc and dg < 9:
            c.z = gola(min(ax, 0.085), c.y)
        elif dc < 9:
            c.x = sx * cava(c.z)
        return c

    m = _tecido(nome + "_m", cor, escala=900, contraste=0.05)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    # ribana: faixa da borda um pouco mais escura e com canelado vertical
    ca = _no(nt, "ShaderNodeVertexColor", layer_name="vies")
    sp = _no(nt, "ShaderNodeSeparateColor")
    nt.links.new(ca.outputs["Color"], sp.inputs[0])
    mx = _no(nt, "ShaderNodeMix", data_type="RGBA")
    nt.links.new(b.inputs["Base Color"].links[0].from_socket, mx.inputs[6])
    mx.inputs[7].default_value = _lin("#E2DFD6")
    nt.links.new(sp.outputs[0], mx.inputs["Factor"])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    o = _casca(corpo, nome, tem, lambda x, y, z: 0.009 if abs(x) > 0.16 and z > 1.3 else 0.008, m,
               espessura=0.003, projetar=projetar, forma=_forma_regata, alisar=10, vies=(0.035, 0.006))
    rib = _tecido(nome + "_ribana", "#E6E3DB", escala=1600, contraste=0.10)
    return [o, _acabamento(o, rib, raio=0.0045, so_z_acima=1.2)]


def _jeans(corpo, nome, cor):
    m = _tecido(nome + "_m", cor, escala=560, tipo="brim")
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    sp = _no(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(_rest(nt), sp.inputs[0])
    X, Y, Z = sp.outputs[0], sp.outputs[1], sp.outputs[2]
    an = _no(nt, "ShaderNodeSeparateColor")
    nt.links.new(_no(nt, "ShaderNodeVertexColor", layer_name="perna").outputs["Color"], an.inputs[0])
    CS, SN, PE = an.outputs[0], an.outputs[1], an.outputs[2]
    vi = _no(nt, "ShaderNodeSeparateColor")
    nt.links.new(_no(nt, "ShaderNodeVertexColor", layer_name="vies").outputs["Color"], vi.inputs[0])
    VI = vi.outputs[0]

    def op(o, a, bb=None):
        n = _no(nt, "ShaderNodeMath", operation=o)
        for i, x in enumerate((a, bb)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                nt.links.new(x, n.inputs[i])
        return n.outputs[0]

    def faixa(v, c, w):                       # 1 onde |v - c| < w
        return op("LESS_THAN", op("ABSOLUTE", op("SUBTRACT", v, c)), w)

    def e(*ms):
        r = ms[0]
        for x in ms[1:]:
            r = op("MULTIPLY", r, x)
        return r

    def ou(*ms):
        r = ms[0]
        for x in ms[1:]:
            r = op("MAXIMUM", r, x)
        return r

    AX = op("ABSOLUTE", X)
    frente, tras = op("LESS_THAN", Y, 0.02), op("GREATER_THAN", Y, 0.04)
    # costura lateral (escura) e pesponto ao lado (mostarda)
    lado = e(PE, op("LESS_THAN", op("ABSOLUTE", SN), 0.035), op("GREATER_THAN", CS, 0.0))
    pesp_lado = e(PE, faixa(SN, -0.07, 0.012), op("GREATER_THAN", CS, 0.0))
    dentro_perna = e(PE, op("LESS_THAN", op("ABSOLUTE", SN), 0.03), op("LESS_THAN", CS, 0.0))
    # bolso da frente: abertura curva
    d = op("SQRT", op("ADD", op("POWER", op("DIVIDE", op("SUBTRACT", AX, 0.178), 0.07), 2.0),
                      op("POWER", op("DIVIDE", op("SUBTRACT", Z, 0.985), 0.085), 2.0)))
    bolso_f = e(faixa(d, 1.0, 0.035), frente, op("GREATER_THAN", AX, 0.1), op("GREATER_THAN", Z, 0.89))
    bolso_f2 = e(faixa(d, 1.12, 0.03), frente, op("GREATER_THAN", AX, 0.1), op("GREATER_THAN", Z, 0.89))
    # braguilha (J) e costura do gancho
    brag = e(frente, ou(e(faixa(X, 0.03, 0.0018), op("GREATER_THAN", Z, 0.83), op("LESS_THAN", Z, 0.95)),
                        e(faixa(op("SQRT", op("ADD", op("POWER", op("SUBTRACT", X, 0.0), 2.0),
                                                     op("POWER", op("SUBTRACT", Z, 0.83), 2.0))), 0.03, 0.0018),
                          op("LESS_THAN", Z, 0.83), op("GREATER_THAN", X, 0.0))))
    gancho = e(faixa(X, 0.0, 0.0022), op("GREATER_THAN", Z, 0.7), op("LESS_THAN", Z, 0.95))
    # bolsos de trás (retângulo com fundo em ponta) e pala
    zb = op("SUBTRACT", 0.835, op("MULTIPLY", op("ABSOLUTE", op("SUBTRACT", AX, 0.087)), 0.35))
    dentro_b = e(tras, op("GREATER_THAN", AX, 0.035), op("LESS_THAN", AX, 0.139), op("GREATER_THAN", Z, zb),
                 op("LESS_THAN", Z, 0.925))
    dentro_b2 = e(tras, op("GREATER_THAN", AX, 0.039), op("LESS_THAN", AX, 0.135), op("GREATER_THAN", Z, op("ADD", zb, 0.004)),
                  op("LESS_THAN", Z, 0.921))
    bolso_t = op("SUBTRACT", dentro_b, dentro_b2)
    pala = e(tras, faixa(Z, op("SUBTRACT", 0.945, op("MULTIPLY", AX, 0.12)), 0.0018))
    escuro = ou(lado, dentro_perna, gancho)
    mostarda = ou(pesp_lado, bolso_f, bolso_f2, brag, bolso_t, pala,
                  e(VI, faixa(Z, 0.938, 0.0015)), e(VI, faixa(Z, 0.14, 0.0015)))
    # desbotado: frente das coxas e joelhos (+ ruído)
    fr = e(PE, op("LESS_THAN", SN, -0.2))
    gz = lambda c, w: op("EXPONENT", op("MULTIPLY", op("POWER", op("DIVIDE", op("SUBTRACT", Z, c), w), 2.0), -1.0))
    nz = _no(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 30.0
    nt.links.new(_rest(nt), nz.inputs["Vector"])
    desb = e(fr, ou(gz(0.7, 0.09), op("MULTIPLY", gz(0.5, 0.045), 0.85)),
             op("ADD", 0.35, op("MULTIPLY", nz.outputs["Fac"], 0.8)))
    barra = e(VI, op("LESS_THAN", Z, 0.5))               # barra dobrada: avesso do brim, mais claro
    cor_in = b.inputs["Base Color"].links[0].from_socket
    c = cor_in
    for msk, h, k in ((desb, "#86A3C8", 0.55), (barra, "#6E8CB8", 1.0), (escuro, "#26364F", 0.7),
                      (mostarda, "#C9963A", 1.0)):
        mx = _no(nt, "ShaderNodeMix", data_type="RGBA")
        nt.links.new(c, mx.inputs[6])
        mx.inputs[7].default_value = _lin(h)
        nt.links.new(op("MINIMUM", op("MULTIPLY", msk, k), 1.0), mx.inputs["Factor"])
        c = mx.outputs[2]
    nt.links.new(c, b.inputs["Base Color"])
    return _casca(corpo, nome, lambda x, y, z: 0.105 < z < 0.99 and abs(x) < 0.3,
                  lambda x, y, z: 0.010 if z > 0.94 else 0.008, m, cortes=[("z", 0.99), ("z", 0.105)],
                  espessura=0.004, forma=_forma_calca, vies=(0.04, 0.0035), atributos={"perna": _ang_perna})


def _cinto(Q, corpo, nome, cor="#3A2A1E", jeans_cor="#3F5F8F"):
    """Cinto de couro com espessura sobre o cós, 5 passantes de brim por cima e fivela retangular metálica."""
    couro = _mat(nome + "_couro", cor, rough=0.45)
    bt = couro.node_tree.nodes["Principled BSDF"]
    if "Coat Weight" in bt.inputs:
        bt.inputs["Coat Weight"].default_value = 0.15
    R = [_casca(corpo, nome + "_cinto", lambda x, y, z: 0.948 < z < 0.982 and abs(x) < 0.3,
                lambda x, y, z: 0.0175, couro, cortes=[("z", 0.982), ("z", 0.948)], espessura=0.005, sub=1)]
    ps = [(0.105, -1), (0.175, -1), (0.07, 1), (0.0, 1)]

    def passante(x, y, z):
        if not (0.94 < z < 0.988):
            return False
        for px, lado in ps:
            if abs(abs(x) - px) < 0.0075 and (y * lado > 0.0) and not (px == 0.0 and abs(x) > 0.0075):
                return True
        return False

    brim = _tecido(nome + "_passante", jeans_cor, escala=560, tipo="brim")
    R.append(_casca(corpo, nome + "_passantes", passante, lambda x, y, z: 0.0235, brim,
                    cortes=[("z", 0.94), ("z", 0.988)], espessura=0.003, sub=1))
    # fivela: moldura retangular (4 barras) + pino, presa ao osso pelvis, na frente do cinto
    cinto = R[0]
    fr = min((v.co for v in cinto.data.vertices if abs(v.co.x) < 0.015 and 0.955 < v.co.z < 0.975),
             key=lambda c: c.y)
    metal = _mat(nome + "_metal", "#B9B6AE", rough=0.3)
    metal.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    w, h, t, e = 0.052, 0.042, 0.006, 0.0065
    bm = bmesh.new()
    for cx, cz, sx, sz in ((0, h / 2 - t / 2, w, t), (0, -h / 2 + t / 2, w, t), (-w / 2 + t / 2, 0, t, h),
                           (w / 2 - t / 2, 0, t, h), (-0.004, 0, 0.003, h - t)):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, e, sz), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(cx, 0, cz), verts=r["verts"])
    me = bpy.data.meshes.new(nome + "_fivela")
    bm.to_mesh(me)
    bm.free()
    fv = bpy.data.objects.new(nome + "_fivela", me)
    for c in corpo.users_collection:
        c.objects.link(fv)
    me.materials.append(metal)
    bv = fv.modifiers.new("chanfro", "BEVEL")
    bv.width, bv.segments = 0.0012, 2
    fv.location = (0, fr.y - 0.007, 0.965)
    bpy.context.view_layer.update()
    _no_osso(fv, Q["arm"], "pelvis")
    R.append(fv)
    return R


def _cabelo_crespo(Q, corpo, cor, pele):
    """Cabelo crespo curto: casca do couro cabeludo com volume no topo (até ~2 cm) e degradê nas laterais e nuca
    (a casca fica rente e semitransparente perto da borda, misturando com a pele). Relevo de cachos miúdos."""
    def linha(x, y):
        ax = abs(x)
        if y < -0.045:
            zh = 1.752
        else:
            zh = 1.752 - (y + 0.045) / 0.145 * 0.125
        if ax > 0.068 and y < 0.05:
            zh = max(zh, 1.728)                  # acima das orelhas
        return zh

    def tem(x, y, z):
        return z > linha(x, y) and z > 1.6

    def desloc(x, y, z):
        return 0.0025 + 0.017 * _liso(z, 1.735, 1.80) * (1 - 0.4 * _liso(abs(x), 0.04, 0.09))

    m = bpy.data.materials.new(Q["nome"] + "_cabelo")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.85
    vo = _no(nt, "ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 420.0
    nt.links.new(_rest(nt), vo.inputs["Vector"])
    nz = _no(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1400.0
    nt.links.new(_rest(nt), nz.inputs["Vector"])
    bp = _no(nt, "ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    bp.inputs["Distance"].default_value = 0.002
    nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    ca = _no(nt, "ShaderNodeVertexColor", layer_name="vies")
    sp = _no(nt, "ShaderNodeSeparateColor")
    nt.links.new(ca.outputs["Color"], sp.inputs[0])           # G = distância da borda (0..1 em 3 cm)
    mx = _no(nt, "ShaderNodeMix", data_type="RGBA")
    mx.inputs[6].default_value = _lin("#3A2820")
    mx.inputs[7].default_value = _lin(cor)
    nt.links.new(nz.outputs["Fac"], mx.inputs["Factor"])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    tr = _no(nt, "ShaderNodeBsdfTransparent")
    ms = _no(nt, "ShaderNodeMixShader")
    al = _no(nt, "ShaderNodeMapRange")
    al.inputs["To Min"].default_value = 0.25
    nt.links.new(sp.outputs[1], al.inputs["Value"])
    nt.links.new(al.outputs[0], ms.inputs[0])
    nt.links.new(tr.outputs[0], ms.inputs[1])
    nt.links.new(b.outputs[0], ms.inputs[2])
    out = nt.nodes["Material Output"]
    nt.links.new(ms.outputs[0], out.inputs["Surface"])
    o = _casca(corpo, Q["nome"] + "_cabelo", tem, desloc, m, espessura=0.002, alisar=6, sub=1)
    o.modifiers.remove(o.modifiers["espessura"])
    return [o]


# ===================================================================== personagem
def personagem(tipo="cara", nome=None, cores=None, peca=None):
    """Cria o personagem. tipo: "cara" (motorista, roupa civil) | "ze" (mecânico, macacão). cores sobrescreve
    TIPOS[tipo] (pele, cabelo, camisa, calca, sapato, sola, macacao, detalhe). peca: "camiseta" | "regata" (cara).
    Devolve Q = {raiz, arm, corpo, roupas, rosto (nós do rosto), acoes, nome}."""
    C = dict(TIPOS[tipo], **(cores or {}))
    if peca:
        C["peca"] = peca
    nome = nome or tipo
    P = ap.importar(CORPO, nome)
    Q = dict(P, nome=nome, tipo=tipo, cores=C)
    corpo = max(P["malhas"], key=lambda m: len(m.data.vertices))
    Q["corpo"] = corpo
    arm = P["arm"]
    _afinar(corpo)
    # pele lisa (mesma cor do decal do rosto) com o relevo do pacote mais suave
    nimg = None
    for ms in corpo.data.materials:
        for n in ms.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image and "Normal" in n.image.name:
                nimg = n.image
    pele = _mat(nome + "_pele", C["pele"], rough=0.55, normal_img=nimg, normal_forca=0.35)
    b = pele.node_tree.nodes["Principled BSDF"]
    if "Subsurface Weight" in b.inputs:
        b.inputs["Subsurface Weight"].default_value = 0.06
        b.inputs["Subsurface Radius"].default_value = (0.01, 0.004, 0.002)
        if "Subsurface Scale" in b.inputs:
            b.inputs["Subsurface Scale"].default_value = 0.02
    corpo.data.materials.clear()
    corpo.data.materials.append(pele)
    R = []
    sapato = _mat(nome + "_sapato", C["sapato"], rough=0.6)
    if C["roupa"] == "civil":
        R.append(_jeans(corpo, nome + "_calca", C["calca"]))
        R += _cinto(Q, corpo, nome, C.get("cinto", "#3A2A1E"), C["calca"])
        if C["peca"] == "regata":
            R += _regata(corpo, nome + "_camisa", C["camisa"])
        else:
            cam = _tecido(nome + "_camisa", C["camisa"], escala=700, contraste=0.08)
            R.append(_casca(corpo, nome + "_camisa",
                            lambda x, y, z: 0.972 < z < (1.505 if y < 0.03 else 1.525) and abs(x) < 0.35,
                            lambda x, y, z: 0.008, cam, cortes=[("z", 0.972), ("x", 0.35), ("z", 1.505)],
                            espessura=0.003, forma=_forma_regata, vies=(0.012, 0.002)))
        R.append(_casca(corpo, nome + "_tenis", lambda x, y, z: z < 0.125,
                        lambda x, y, z: 0.016, sapato, cortes=[("z", 0.125)], espessura=0.004, suavizar=8, sub=1))
        _costura(sapato, [("hz", 0.022, 0)], cor=C["sola"], largura=0.044)    # sola clara (faixa até 2,2 cm)
    else:
        mac = _tecido(nome + "_macacao", C["macacao"], escala=380, contraste=0.10, tipo="lona")
        _costura(mac, [("ret", 0.03, 0.12, 1.30, 1.40, -1),                   # bolso do peito (laranja)
                       ("hz", 0.975, 0), ("hz", 0.36, 0)], cor=C["detalhe"], largura=0.006)
        R.append(_casca(corpo, nome + "_macacao",
                        lambda x, y, z: 0.15 < z < (1.505 if y < 0.03 else 1.53) and abs(x) < 0.33,
                        lambda x, y, z: 0.016 if abs(x) > 0.29 and z > 1.3 else (0.012 if z < 0.24 else 0.010),
                        mac, cortes=[("z", 0.15), ("x", 0.33), ("z", 1.505)], espessura=0.004))
        R.append(_casca(corpo, nome + "_bota", lambda x, y, z: z < 0.2,
                        lambda x, y, z: 0.016, sapato, cortes=[("z", 0.2)], espessura=0.005, suavizar=12, sub=1))
        _costura(sapato, [("hz", 0.016, 0)], cor=C["sola"], largura=0.032)
    Q["roupas"] = R
    # esconde o corpo onde a roupa cobre tudo (o dedo do pé ou o joelho não atravessa o tênis/jeans ao dobrar)
    if C["roupa"] == "civil":
        def coberto(x, y, z):
            ax = abs(x)
            if z < 0.93 and ax < 0.3:
                return True
            if C["peca"] == "regata" and 0.9 < z < 1.6 and ax < 0.3:       # sob a regata, longe das bordas
                gola = (1.497 + 0.03 * (min(ax, 0.085) / 0.085) ** 2) if y < 0.03 else 1.525
                if z > 1.27 and ax > 0.192 - (z - 1.30) * 0.16 - 0.012:
                    return False
                return z < gola - 0.012
            return False
    else:
        coberto = lambda x, y, z: z < 1.42 and abs(x) < 0.25
    vg = corpo.vertex_groups.new(name="_coberto")
    vg.add([v.index for v in corpo.data.vertices if coberto(*v.co)], 1.0, "REPLACE")
    mk = corpo.modifiers.new("esconde", "MASK")
    mk.vertex_group, mk.invert_vertex_group = "_coberto", True
    if C["corte"] == "crespo":
        Q["cabelo"] = _cabelo_crespo(Q, corpo, C["cabelo"], C["pele"])
    else:
        Q["cabelo"] = _cabelo(Q, C["corte"], C["cabelo"])
    _rosto(Q, C)
    s = C["altura"] / ALTURA_ARQ
    Q["raiz"].scale = (s, s, s)
    bpy.context.view_layer.update()
    return Q


def colocar(Q, pos, rumo=0.0):
    ap.colocar(Q, pos, rumo)


# ===================================================================== animação simples
_BIBLIOTECA = {}


def _acoes_ual(Q):
    if "ual" not in _BIBLIOTECA:
        _BIBLIOTECA["ual"] = ap.carregar_acoes(UAL) + ap.carregar_acoes(UAL2)
    Q["acoes"] = list(Q.get("acoes", [])) + _BIBLIOTECA["ual"]


# verbo → ("ual", ação, loop) | ("cmu", tomada, q0, q1, amplitude)
VERBOS = {
    "andar": ("ual", "Walk_Loop", True),
    "parado": ("ual", "Idle_Loop", True),
    "falar": ("ual", "Idle_Talking_Loop", True),
    "bracos_cruzados": ("ual", "Idle_FoldArms_Loop", True),
    "nao": ("ual", "Idle_No_Loop", True),
    "sim": ("ual", "Yes", False),
    "mexer": ("ual", "Fixing_Kneeling", False),
    "chutar": ("cmu", "143_24", 106, 136, 0.6),
    "ombros": ("cmu", "141_21", 24, 64, 0.6),
    "acenar": ("cmu", "141_16", 0, 60, 1.0),
    "apontar": ("cmu", "13_27", 0, 72, 1.0),
}


def animar(Q, passos, fps=FPS, transicao=0.25):
    """passos = [(verbo, t0, [t1], [p0, p1 | graus])...], em ordem. Verbos: andar (t0, t1, p0, p1: vai de p0 a p1
    sem o pé escorregar e já virado para lá), virar (t0, t1, graus), e os de VERBOS (t0, [t1]): parado, falar,
    bracos_cruzados, nao, sim, mexer, chutar, ombros, acenar, apontar. Cada verbo dura até o próximo começar."""
    _acoes_ual(Q)
    raiz = Q["raiz"]
    trechos = []
    feitos = {}
    rot = []
    corpo = [p for p in passos if p[0] != "virar"]
    for k, p in enumerate(corpo):
        verbo, t0 = p[0], p[1]
        t_fim = corpo[k + 1][1] if k + 1 < len(corpo) else (p[2] if len(p) > 2 and not isinstance(p[2], (tuple, list, Vector)) else t0 + 1.5)
        v = VERBOS[verbo]
        op = {"blend": transicao}
        if v[0] == "ual":
            nome = v[1]
            op["loop"] = v[2]
        else:
            nome = f"cmu_{verbo}"
            if nome not in feitos:
                src = ap.importar_bvh(os.path.join(BVH, v[1] + ".bvh"), "src_" + v[1])
                Q["acoes"].append(ap.retarget(src, Q["arm"], ap.MAPA_CMU_UE, v[2], v[3],
                                              nome_acao=f"{Q['nome']}_{nome}", amplitude=v[4]))
                ap.apagar(src)
                feitos[nome] = Q["acoes"][-1].name
            nome = feitos[nome]
            op["loop"] = False
        if verbo == "andar":
            t1, p0, p1 = p[2], Vector(p[3]), Vector(p[4])
            d = p1 - p0
            rumo = math.degrees(math.atan2(d.x, -d.y))
            rot.append((t0, rumo))
            raiz.rotation_euler = (0, 0, math.radians(rumo))
            op["vel"] = ap.caminhar(Q, nome, t0, t1, p0, p1, fps=fps)
        trechos.append((nome, t0, t_fim - t0, op))
    for p in passos:
        if p[0] == "virar":
            rot.append((p[1], None))
            rot.append((p[2], p[3]))
    # giros da raiz: "None" = mantém o último valor
    ult = math.degrees(raiz.rotation_euler.z)
    for t, g in sorted(rot, key=lambda r: r[0]):
        g = ult if g is None else g
        raiz.rotation_euler = (0, 0, math.radians(g))
        raiz.keyframe_insert("rotation_euler", frame=int(round(t * fps)) + 1)
        ult = g
    ap.encadear(Q, trechos, fps=fps, transicao=transicao)
    return trechos


# ===================================================================== rosto: atalhos
def _q(fps):
    return lambda t: int(round(t * fps)) + 1


def rosto(Q, nome, t, fps=FPS, sem_boca=True):
    """Expressão (boneco_adulto.EXPRESSOES) a partir do tempo t (s, tempo da cena)."""
    ba.expressao(Q, nome, t, _q(fps), sem_boca=sem_boca)


def falar(Q, palavras, t0, t1, desloc=0.0, fps=FPS, intensidade=1.0):
    """Lip sync: palavras [[p, ini, fim]...] com tempos do áudio; desloc = tempo do áudio que cai no t=0 da cena."""
    ba.falar(Q, palavras, t0, t1, _q(fps), lambda t: t - desloc, intensidade)


def piscar(Q, t0, t1, fps=FPS, semente=3):
    ba.piscar(Q, t0, t1, _q(fps), semente=semente)
