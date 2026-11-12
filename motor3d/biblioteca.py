"""Biblioteca de material livre (CC0) do canal: HDRIs, texturas PBR e modelos baixados em assets/.

Baixar/atualizar:  bash scripts/baixar_assets.sh        (licenças em assets/LICENCAS.md)

    import biblioteca as bib
    bib.hdri("wide_street_01", forca=1.0, rotacao=90)                 # luz + reflexos de rua de dia
    asf = bib.textura_pbr("asphalt_02", escala=4)                     # material Principled (cor+rugosidade+normal)
    chao = mt.box("chao", -10, 10, -10, 10, -0.05, 0, asf)            # UV automática: escala em metros (veja abaixo)
    cone = bib.importar_modelo("kenney/.../construction-cone.glb", escala=1, loc=(1, 2, 0), rot=(0, 0, 30))
    bib.catalogo()                                                    # dict {tipo: [nomes]}; print(bib.catalogo())

Convenções:
- `nome` aceita o id do Poly Haven/ambientCG (ex. "asphalt_02", "Rubber004") ou um caminho de arquivo.
- As texturas usam coordenadas de OBJETO em metros projetadas em caixa (Box), então funcionam em qualquer malha do
  motor (mt.box, mt.cyl...) sem desdobrar UV; `escala` = quantas repetições por metro... na verdade, tamanho em metros
  de UMA repetição da textura (ex. 2.0 = um ladrilho de 2 m). Use `uv=True` para usar a UV da malha (modelos).
- Rotação em graus; posições em metros.
"""
import os, math, glob
import bpy

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ASSETS = os.path.join(RAIZ, "assets")
HDRI_DIR = os.path.join(ASSETS, "hdri")
TEX_DIR = os.path.join(ASSETS, "texturas")
MOD_DIR = os.path.join(ASSETS, "modelos")


# ================================================================ catálogo
def catalogo(imprimir=False):
    """Tudo o que está baixado: {"hdri": [...], "texturas": [...], "modelos": [caminhos relativos a assets/modelos]}."""
    hd = sorted({os.path.basename(f).rsplit("_", 1)[0] for f in glob.glob(os.path.join(HDRI_DIR, "*.hdr"))})
    tx = sorted(d for d in os.listdir(TEX_DIR) if os.path.isfile(os.path.join(TEX_DIR, d, "cor.jpg"))) \
        if os.path.isdir(TEX_DIR) else []
    md = []
    for ext in ("glb", "gltf", "fbx", "obj", "blend"):
        md += glob.glob(os.path.join(MOD_DIR, "**", "*." + ext), recursive=True)
    md = sorted(os.path.relpath(f, MOD_DIR) for f in md)
    c = {"hdri": hd, "texturas": tx, "modelos": md}
    if imprimir:
        for k, v in c.items():
            print(f"== {k} ({len(v)})")
            for n in v:
                print("  ", n)
    return c


def _achar_hdri(nome, res=None):
    if os.path.isfile(nome):
        return nome
    ordem = [res] if res else ["2k", "1k", "4k"]
    for r in ordem:
        f = os.path.join(HDRI_DIR, f"{nome}_{r}.hdr")
        if os.path.isfile(f):
            return f
    raise FileNotFoundError(f"HDRI '{nome}' não está em assets/hdri (rode scripts/baixar_assets.sh). "
                            f"Disponíveis: {catalogo()['hdri']}")


def _achar_modelo(caminho):
    if os.path.isfile(caminho):
        return caminho
    for base in (MOD_DIR, ASSETS):
        f = os.path.join(base, caminho)
        if os.path.isfile(f):
            return f
    # id do Poly Haven ("old_tyre") ou nome solto: procura o primeiro arquivo com esse nome
    for ext in ("gltf", "glb", "fbx", "obj", "blend"):
        hits = glob.glob(os.path.join(MOD_DIR, "**", f"{caminho}*.{ext}"), recursive=True)
        if hits:
            return sorted(hits, key=len)[0]
    raise FileNotFoundError(f"modelo '{caminho}' não encontrado em assets/modelos")


# ================================================================ HDRI
def hdri(nome, forca=1.0, rotacao=0.0, res=None, fundo=None, fundo_forca=None, cena=None):
    """Mundo com o HDRI `nome` (id Poly Haven, ex. "wide_street_01"). rotacao em graus (gira em Z: move o sol).
    fundo: None = a câmera vê o próprio HDRI; uma cor "#RRGGBB" = a câmera vê essa cor chapada (o HDRI continua
    iluminando) — útil para cenas técnicas escuras ou quando o fundo do HDRI distrai. Devolve o World."""
    sc = cena or bpy.context.scene
    w = bpy.data.worlds.new("hdri_" + os.path.basename(nome))
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rotacao))
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(_achar_hdri(nome, res), check_existing=True)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = forca
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    if fundo is None:
        nt.links.new(bg.outputs[0], out.inputs["Surface"])
    else:
        h = fundo.lstrip("#")
        cor = [((int(h[i:i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4)] + [1.0]
        b2 = nt.nodes.new("ShaderNodeBackground")
        b2.inputs["Color"].default_value = cor
        b2.inputs["Strength"].default_value = fundo_forca if fundo_forca is not None else 1.0
        lp = nt.nodes.new("ShaderNodeLightPath")
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0])
        nt.links.new(bg.outputs[0], mx.inputs[1])
        nt.links.new(b2.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return w


# ================================================================ texturas PBR
_CACHE_MAT = {}


def _img(caminho, cor=True):
    im = bpy.data.images.load(caminho, check_existing=True)
    if not cor:
        im.colorspace_settings.name = "Non-Color"
    return im


def textura_pbr(nome, escala=1.0, uv=False, rugosidade=None, metal=None, tinta=None, normal=1.0, rot=0.0,
                nome_material=None):
    """Material Principled com cor + rugosidade + normal (e metal, se o pacote tiver) da textura `nome`
    (pasta em assets/texturas: id do Poly Haven ou do ambientCG).
    escala: tamanho em metros de uma repetição (coordenada de objeto, projeção Box) — ou, com uv=True,
            repetições por unidade de UV.
    rugosidade/metal: número para sobrescrever o mapa; tinta: "#RRGGBB" multiplica a cor (tingir muro, carro...).
    normal: força do relevo. rot: giro da textura em graus. Materiais iguais são reaproveitados (cache)."""
    chave = (nome, escala, uv, rugosidade, metal, tinta, normal, rot, nome_material)
    m = _CACHE_MAT.get(chave)
    if m and m.name in bpy.data.materials:
        return m
    pasta = nome if os.path.isdir(nome) else os.path.join(TEX_DIR, nome)
    if not os.path.isfile(os.path.join(pasta, "cor.jpg")):
        raise FileNotFoundError(f"textura '{nome}' não está em assets/texturas. Disponíveis: {catalogo()['texturas']}")
    m = bpy.data.materials.new(nome_material or ("pbr_" + os.path.basename(pasta)))
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    if uv:
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
        mp.inputs["Scale"].default_value = (escala, escala, escala)
    else:
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        s = 1.0 / max(escala, 1e-4)
        mp.inputs["Scale"].default_value = (s, s, s)
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))

    def tex(arq, cor=True):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _img(os.path.join(pasta, arq), cor)
        if not uv:
            t.projection = "BOX"
            t.projection_blend = 0.2
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        return t

    tcor = tex("cor.jpg")
    if tinta:
        h = tinta.lstrip("#")
        c = [((int(h[i:i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4)] + [1.0]
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        nt.links.new(tcor.outputs["Color"], mx.inputs["A"])
        mx.inputs["B"].default_value = c
        nt.links.new(mx.outputs["Result"], b.inputs["Base Color"])
    else:
        nt.links.new(tcor.outputs["Color"], b.inputs["Base Color"])
    if rugosidade is not None:
        b.inputs["Roughness"].default_value = rugosidade
    elif os.path.isfile(os.path.join(pasta, "rugosidade.jpg")):
        nt.links.new(tex("rugosidade.jpg", False).outputs["Color"], b.inputs["Roughness"])
    if metal is not None:
        b.inputs["Metallic"].default_value = metal
    elif os.path.isfile(os.path.join(pasta, "metal.jpg")):
        nt.links.new(tex("metal.jpg", False).outputs["Color"], b.inputs["Metallic"])
    if normal and os.path.isfile(os.path.join(pasta, "normal.jpg")):
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal
        nt.links.new(tex("normal.jpg", False).outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    _CACHE_MAT[chave] = m
    return m


# ================================================================ modelos
def importar_modelo(caminho, escala=1.0, loc=(0, 0, 0), rot=(0, 0, 0), nome=None, colecao=None, apoiar=True,
                    so=None, sem=None, centralizar=False, material=None):
    """Importa GLB/GLTF/FBX/OBJ/BLEND e devolve um Empty-raiz com tudo pendurado (mova/anime só a raiz).
    caminho: arquivo, caminho relativo a assets/modelos, ou id do Poly Haven ("old_tyre").
    escala: multiplicador; rot: graus (X, Y, Z); apoiar=True põe a base do modelo em z=0 da raiz.
    Em .blend, importa todos os objetos (ou só `colecao`, se dada).
    so / sem: regex no nome dos objetos para ficar só com uma variante de um kit (ex. o hidrante do Poly Haven vem
    em duas versões: sem="aged"); centralizar=True põe o centro (x, y) do que sobrou na origem da raiz."""
    import re
    f = _achar_modelo(caminho)
    ext = f.rsplit(".", 1)[1].lower()
    antes = set(bpy.data.objects)
    if ext in ("glb", "gltf"):
        bpy.ops.import_scene.gltf(filepath=f)
    elif ext == "fbx":
        if hasattr(bpy.ops.wm, "fbx_import"):
            bpy.ops.wm.fbx_import(filepath=f)
        else:
            bpy.ops.import_scene.fbx(filepath=f)
    elif ext == "obj":
        bpy.ops.wm.obj_import(filepath=f, forward_axis="NEGATIVE_Z", up_axis="Y")
    elif ext == "blend":
        with bpy.data.libraries.load(f, link=False) as (src, dst):
            if colecao:
                dst.collections = [c for c in src.collections if c == colecao]
            else:
                dst.objects = list(src.objects)
        cena = bpy.context.scene.collection
        if colecao:
            for c in dst.collections:
                cena.children.link(c)
        else:
            for o in dst.objects:
                if o is not None and o.type not in ("CAMERA", "LIGHT"):
                    cena.objects.link(o)
    else:
        raise ValueError("formato não suportado: " + ext)
    novos = [o for o in bpy.data.objects if o not in antes]
    if ext == "blend" and not colecao:
        # câmeras/luzes do arquivo de origem não entram
        novos = [o for o in novos if o.type not in ("CAMERA", "LIGHT") and o.users_scene]
    for o in [o for o in novos if o.type in ("CAMERA", "LIGHT")]:
        bpy.data.objects.remove(o, do_unlink=True)
        novos.remove(o)
    if so or sem:
        def fica(o):
            n = o.name
            return (not so or re.search(so, n, re.I)) and not (sem and re.search(sem, n, re.I))
        manter = {o for o in novos if fica(o)}
        for o in list(manter):               # mantém os pais (vazios de agrupamento) do que ficou
            p = o.parent
            while p is not None and p in novos:
                manter.add(p)
                p = p.parent
        for o in [o for o in novos if o not in manter]:
            bpy.data.objects.remove(o, do_unlink=True)
        novos = [o for o in novos if o in manter]
    if material is not None:
        for o in novos:
            if o.type == "MESH":
                o.data.materials.clear()
                o.data.materials.append(material)
    raiz = bpy.data.objects.new(nome or ("mod_" + os.path.splitext(os.path.basename(f))[0]), None)
    bpy.context.scene.collection.objects.link(raiz)
    raiz.empty_display_size = 0.3
    bpy.context.view_layer.update()
    topo = [o for o in novos if o.parent is None or o.parent not in novos]
    zmin = cx = cy = 0.0
    if apoiar or centralizar:
        pts = [o.matrix_world @ v.co for o in novos if o.type == "MESH" for v in o.data.vertices]
        if pts and apoiar:
            zmin = min(p.z for p in pts)
        if pts and centralizar:
            cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2
            cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2
    for o in topo:
        mw = o.matrix_world.copy()
        o.parent = raiz
        o.matrix_parent_inverse.identity()
        o.matrix_world = mw
        o.location.z -= zmin
        o.location.x -= cx
        o.location.y -= cy
    raiz.scale = (escala, escala, escala)
    raiz.location = loc
    raiz.rotation_euler = tuple(math.radians(a) for a in rot)
    for o in novos:
        o.select_set(False)
    return raiz


def dimensoes(raiz):
    """(largura x, profundidade y, altura z) em metros do modelo importado (já com a escala da raiz)."""
    from mathutils import Vector
    bpy.context.view_layer.update()
    pts = []
    for o in raiz.children_recursive:
        if o.type == "MESH":
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    if not pts:
        return (0, 0, 0)
    return tuple(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))
