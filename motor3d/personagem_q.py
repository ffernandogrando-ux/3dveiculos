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
    "cara": dict(pele="#A86B4C", cabelo="#1E1510", camisa="#F2F1EC", calca="#3A5A86", sapato="#2B2E35",
                 sola="#E6E2DA", altura=1.76, corte="Hair_SimpleParted", roupa="civil", peca="regata"),
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


def _tecido(nome, cor, escala=420.0, contraste=0.12, rough=0.85, tipo="malha"):
    """Tecido com trama fina (por coordenada de objeto, que acompanha a deformação): 'brim' = sarja diagonal do jeans
    com desbotado; 'malha' = camiseta; 'lona' = macacão."""
    m = _mat(nome, cor, rough, sheen=0.25)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = _no(nt, "ShaderNodeTexCoord")
    wv = _no(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="DIAGONAL")
    wv.inputs["Scale"].default_value = escala
    wv.inputs["Distortion"].default_value = 0.5
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    nz = _no(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 9.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
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
    tc = _no(nt, "ShaderNodeTexCoord")
    sp = _no(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sp.inputs[0])
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


def _casca(corpo, nome, dentro, desloc, mat, cortes=(), espessura=0.0035, suavizar=0, sub=1, projetar=None):
    """Roupa = cópia do corpo com só as faces de `dentro(x,y,z)`, empurrada `desloc(x,y,z)` (m) pela normal; as
    bordas abertas são niveladas nos planos `cortes` [("z", 0.99), ("x", 0.36)...] (borda reta, sem serrilhado) e
    a espessura vem do Solidify. Mesmos grupos de vértices + Armature do corpo → deforma igual."""
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
    for _ in range(4):
        novo = {v: (v.co * 2 + sum((u.co for u in viz[v]), Vector())) / (2 + len(viz[v])) for v in borda if viz[v]}
        for v, c in novo.items():
            v.co = c
        if projetar is not None:
            for v in borda:
                v.co = projetar(v.co.copy())
    bm.to_mesh(o.data)
    bm.free()
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
    dg = bpy.context.evaluated_depsgraph_get()
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
        jeans = _tecido(nome + "_jeans", C["calca"], escala=520, tipo="brim")
        _costura(jeans, [("ret", 0.035, 0.135, 0.845, 0.945, 1),      # bolsos de trás
                         ("hz", 0.94, 0), ("hz", 0.115, 0)], cor="#C9963A")
        R.append(_casca(corpo, nome + "_calca",
                        lambda x, y, z: 0.105 < z < 0.975 and abs(x) < 0.3,
                        lambda x, y, z: 0.010 if z > 0.94 else (0.012 if z < 0.17 else 0.0075),
                        jeans, cortes=[("z", 0.975), ("z", 0.105)], espessura=0.004))
        cam = _tecido(nome + "_camisa", C["camisa"], escala=700, contraste=0.08)
        if C["peca"] == "regata":
            def tem(x, y, z):
                ax = abs(x)
                if not (0.925 < z < 1.54) or ax > 0.3:
                    return False
                if z > 1.30 and ax > 0.205 - (z - 1.30) * 0.30:
                    return False                    # cava
                corte = (1.39 + 0.13 * (ax / 0.1) ** 2) if y < 0.03 else (1.47 + 0.05 * (ax / 0.1) ** 2)
                return z < corte
            cortes = [("z", 0.925)]

            def projetar(c):
                ax, sx = abs(c.x), (1 if c.x >= 0 else -1)
                if c.z < 1.1:
                    c.z = 0.925
                    return c
                zc = (1.39 + 0.13 * (min(ax, 0.1) / 0.1) ** 2) if c.y < 0.03 else (1.47 + 0.05 * (min(ax, 0.1) / 0.1) ** 2)
                xc = 0.205 - (c.z - 1.30) * 0.30
                if ax < 0.095 and abs(c.z - zc) < 0.05:
                    c.z = zc                          # gola em U
                elif c.z > 1.28 and ax > 0.1:
                    c.x = sx * max(xc, 0.1)           # cava
                return c
        else:
            projetar = None
            def tem(x, y, z):
                ax = abs(x)
                return 0.925 < z < (1.505 if y < 0.03 else 1.525) and ax < 0.35
            cortes = [("z", 0.925), ("x", 0.35), ("z", 1.505)]
        R.append(_casca(corpo, nome + "_camisa", tem,
                        lambda x, y, z: 0.021 if z < 0.985 else (0.012 if abs(x) > 0.3 else 0.008),
                        cam, cortes=cortes, espessura=0.003, projetar=projetar))
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
        coberto = lambda x, y, z: z < 0.93 and abs(x) < 0.3
    else:
        coberto = lambda x, y, z: z < 1.42 and abs(x) < 0.25
    vg = corpo.vertex_groups.new(name="_coberto")
    vg.add([v.index for v in corpo.data.vertices if coberto(*v.co)], 1.0, "REPLACE")
    mk = corpo.modifiers.new("esconde", "MASK")
    mk.vertex_group, mk.invert_vertex_group = "_coberto", True
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
    "ombros": ("cmu", "141_21", 24, 64, 0.75),
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
