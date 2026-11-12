"""Peças do estilo "EXPLICATIVO TÉCNICO 3D" (direção B): pneu em corte, motor em corte, estúdio escuro e callouts.

Visual de peça de anúncio de montadora: estúdio infinito grafite com grade no piso, strip lights laterais,
materiais realistas (clearcoat, alumínio anodizado, aço, borracha, óleo âmbar) e faces de seção chapadas em laranja.
Tudo procedural (Blender/bpy + numpy). Medidas em metros, na escala real (pneu 205/55 R16, motor de 86 x 86 mm).

Uso típico:
    import tecnico as tc
    tc.nova_cena(res=(1080, 1920), amostras=48)
    tc.estudio_tecnico()
    p = tc.pneu_corte("calib", loc=(-0.33, 0, 0), yaw=-35, pressao=1.0)
    cam = tc.camera((0, -4, 1.0), (0, 0, 0.33), lente=65)
    fim = tc.callout(p["ancoras"]["cintas"], cam, dx=-0.25, dy=0.2, compr=0.18, cor=tc.CIANO)
    tc.render("quadro.png")
    xy = tc.projetar(fim["fim"])   # posição em pixels para o texto em pós (PIL)
"""
import math
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

# ============================================================ paleta (sRGB hex)
GRAFITE_ESC = "#14171C"
GRAFITE_CLA = "#22272F"
GRADE = "#2A3038"
CIANO = "#19C3E6"
LARANJA = "#FF6B1A"
VERDE = "#2BD576"
VERMELHO = "#FF3B3B"
RAIO_X = "#8FD3FF"
ACO = "#9AA3AD"
BORRACHA = "#1A1A1C"
OLEO = "#C98A1B"

_MATS = {}


def lin(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [a]


# ============================================================ cena / render
def nova_cena(res=(1080, 1920), amostras=48):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MATS.clear()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    c = sc.cycles
    c.device = "CPU"
    c.samples = amostras
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.03
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    if hasattr(c, "denoising_quality"):
        c.denoising_quality = "HIGH"
    c.max_bounces = 6
    c.diffuse_bounces = 1
    c.glossy_bounces = 2
    c.transmission_bounces = 6
    c.transparent_max_bounces = 8
    c.volume_bounces = 0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 0.5
    c.sample_clamp_indirect = 4.0
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    w = bpy.data.worlds.new("mundo")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = lin(GRAFITE_ESC)
    bg.inputs[1].default_value = 0.12
    return sc


def render(caminho):
    sc = bpy.context.scene
    sc.render.filepath = caminho
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    return caminho


def projetar(p):
    """Ponto 3D -> pixel (x, y) na imagem final (origem no canto superior esquerdo)."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    v = world_to_camera_view(sc, sc.camera, Vector(p))
    return (v.x * sc.render.resolution_x, (1 - v.y) * sc.render.resolution_y)


def camera(loc, alvo, lente=65, nome="cam"):
    cd = bpy.data.cameras.new(nome)
    cd.lens = lente
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24 * 16 / 9 / 1.5     # ~ 28,4 mm na vertical
    cd.clip_start = 0.05
    cd.clip_end = 100
    cam = bpy.data.objects.new(nome, cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    mirar(cam, alvo)
    bpy.context.scene.camera = cam
    return cam


def orbita(cam, alvo, raio, ang_graus, altura):
    """Posiciona a câmera numa órbita em torno do alvo (ângulo 0 = de frente, olhando +Y)."""
    a = math.radians(ang_graus)
    cam.location = (alvo[0] + raio * math.sin(a), alvo[1] - raio * math.cos(a), altura)
    mirar(cam, alvo)


def mirar(obj, alvo):
    d = Vector(alvo) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ============================================================ materiais
def _principled(nome):
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    return m, m.node_tree.nodes["Principled BSDF"]


def mat_pintura(cor, nome=None):
    """Pintura automotiva com verniz: coat 1.0, coat roughness 0.03."""
    m, b = _principled(nome or "pintura_" + cor)
    b.inputs["Base Color"].default_value = lin(cor)
    b.inputs["Metallic"].default_value = 0.35
    b.inputs["Roughness"].default_value = 0.32
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.03
    return m


def mat_metal(cor, rough=0.35, nome=None, aniso=0.0):
    m, b = _principled(nome or f"metal_{cor}_{rough}")
    b.inputs["Base Color"].default_value = lin(cor)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    if aniso:
        b.inputs["Anisotropic"].default_value = aniso
    return m


def mat_borracha(nome="borracha"):
    m, b = _principled(nome)
    nt = m.node_tree
    b.inputs["Base Color"].default_value = lin(BORRACHA)
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.28
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 900.0
    nz.inputs["Detail"].default_value = 2.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.08
    bp.inputs["Distance"].default_value = 0.0004
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_oleo(nome="oleo"):
    """Óleo âmbar translúcido: vidro âmbar + leve absorção em volume + um fio de emissão para ler no escuro."""
    m, b = _principled(nome)
    nt = m.node_tree
    b.inputs["Base Color"].default_value = lin("#F0B04A")
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["IOR"].default_value = 1.47
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Emission Color"].default_value = lin(OLEO)
    b.inputs["Emission Strength"].default_value = 0.35
    va = nt.nodes.new("ShaderNodeVolumeAbsorption")
    va.inputs["Color"].default_value = lin(OLEO)
    va.inputs["Density"].default_value = 3.0
    out = nt.nodes["Material Output"]
    nt.links.new(va.outputs[0], out.inputs["Volume"])
    return m


def mat_secao(cor=LARANJA, nome=None, brilho=0.55, hachura=None):
    """Face de seção chapada: cor sólida, quase sem sombreamento (emissão + difuso).
    hachura=(cor_linha, passo_m, largura_m): linhas a 45° no plano XZ do objeto (padrão de desenho técnico),
    que deixam a seção menos "bloco laranja" sem perder a leitura de corte."""
    m, b = _principled(nome or "secao_" + cor)
    b.inputs["Base Color"].default_value = lin(cor)
    b.inputs["Roughness"].default_value = 0.55
    b.inputs["Specular IOR Level"].default_value = 0.3
    b.inputs["Emission Color"].default_value = lin(cor)
    b.inputs["Emission Strength"].default_value = brilho
    if hachura:
        cl, passo, larg = hachura
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        tc_ = N.new("ShaderNodeTexCoord")
        sp = N.new("ShaderNodeSeparateXYZ")
        L.new(tc_.outputs["Object"], sp.inputs[0])
        ad = N.new("ShaderNodeMath"); ad.operation = "ADD"
        L.new(sp.outputs["X"], ad.inputs[0]); L.new(sp.outputs["Z"], ad.inputs[1])
        dv = N.new("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = passo * 1.4142
        pp = N.new("ShaderNodeMath"); pp.operation = "PINGPONG"; pp.inputs[1].default_value = 0.5
        lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = larg / passo / 2
        L.new(ad.outputs[0], dv.inputs[0]); L.new(dv.outputs[0], pp.inputs[0]); L.new(pp.outputs[0], lt.inputs[0])
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
        _sock(mx, "A").default_value = lin(cor)
        _sock(mx, "B").default_value = lin(cl)
        L.new(lt.outputs[0], _sock(mx, "Factor", "VALUE"))
        cor_out = [o for o in mx.outputs if o.type == "RGBA"][0]
        L.new(cor_out, b.inputs["Base Color"])
        L.new(cor_out, b.inputs["Emission Color"])
    return m


# seção "técnica" padrão: laranja queimado com hachura laranja-alerta (menos dominante que o laranja chapado)
SECAO_ESCURA = "#7A3010"


def mat_secao_tecnica(nome="sec_tecnica", passo=0.009, larg=0.0016):
    return mat_secao(SECAO_ESCURA, nome, 0.35, hachura=(LARANJA, passo, larg))


def mat_emissivo(cor, forca=4.0, nome=None, alpha=1.0):
    m = bpy.data.materials.new(nome or f"emis_{cor}_{forca}_{alpha}")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(cor)
    em.inputs["Strength"].default_value = forca
    if alpha < 1.0:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_raio_x(cor=RAIO_X, opac=0.15, nome="raio_x", borda=0.75):
    """Lataria fantasma: casca transparente ciano, ~opac (15 %) de frente e até 'borda' nas silhuetas
    (Fresnel/Layer Weight). Emissiva: lê bem sobre o fundo escuro e não depende da luz."""
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.45
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.2
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = opac * 0.6
    mr.inputs["To Max"].default_value = borda
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(cor)
    em.inputs["Strength"].default_value = 1.6
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    nt.links.new(pw.outputs[0], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def M(chave, fabrica):
    """Cache de materiais por nome."""
    if chave not in _MATS:
        _MATS[chave] = fabrica()
    return _MATS[chave]


# ============================================================ malhas
def malha(nome, verts, faces, mats=(), idx_mat=None, suave=None, colecao=None):
    me = bpy.data.meshes.new(nome)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, f)) for f in faces])
    me.validate(clean_customdata=False)
    me.update()
    for m in mats:
        me.materials.append(m)
    if idx_mat is not None:
        me.polygons.foreach_set("material_index", np.asarray(idx_mat, dtype=np.int32))
    if suave is not None:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(suave))
    ob = bpy.data.objects.new(nome, me)
    (colecao or bpy.context.scene.collection).objects.link(ob)
    return ob


def _normais_fora(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def _smooth(x, e0, e1):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _faixa(x, centro, largura, borda):
    """1 dentro de [centro ± largura/2], com bordas suaves de 'borda'."""
    d = np.abs(x - centro) - largura / 2
    return 1.0 - _smooth(d, -borda / 2, borda / 2)


def _casco_convexo(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def _circulo(cx, cy, r, n=48, a0=0.0, a1=2 * math.pi):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def extrudar_xz(nome, contorno, y0, y1, mats=(), suave=30):
    """Polígono 2D (x, z) extrudado ao longo de Y (de y0 a y1)."""
    n = len(contorno)
    vs = [(x, y0, z) for x, z in contorno] + [(x, y1, z) for x, z in contorno]
    fs = [list(range(n))[::-1], list(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        fs.append([i, j, n + j, n + i])
    ob = malha(nome, vs, fs, mats, suave=suave)
    _normais_fora(ob)
    return ob


def revolver(nome, perfil, eixo="Y", segs=96, mats=(), suave=40, centro=(0, 0, 0)):
    """Perfil fechado [(a, r), ...] girado 360° em torno do eixo ("X", "Y" ou "Z"). a = coordenada axial."""
    n = len(perfil)
    vs = []
    for k in range(segs):
        t = 2 * math.pi * k / segs
        c, s = math.cos(t), math.sin(t)
        for a, r in perfil:
            if eixo == "X":
                v = (a, r * s, -r * c)
            elif eixo == "Y":
                v = (r * s, a, -r * c)
            else:
                v = (r * c, r * s, a)
            vs.append((v[0] + centro[0], v[1] + centro[1], v[2] + centro[2]))
    fs = []
    for k in range(segs):
        k2 = (k + 1) % segs
        for i in range(n):
            j = (i + 1) % n
            fs.append([k * n + i, k * n + j, k2 * n + j, k2 * n + i])
    ob = malha(nome, vs, fs, mats, suave=suave)
    _normais_fora(ob)
    return ob


def cilindro(nome, r, p0, p1, segs=64, mats=(), suave=40):
    """Cilindro sólido entre os pontos p0 e p1."""
    p0, p1 = Vector(p0), Vector(p1)
    h = (p1 - p0).length
    ob = revolver(nome, [(0, 0.0), (0, r), (h, r), (h, 0.0)], eixo="Z", segs=segs, mats=mats, suave=suave)
    q = (p1 - p0).normalized().to_track_quat("Z", "Y")
    ob.matrix_world = Matrix.Translation(p0) @ q.to_matrix().to_4x4()
    aplicar_transf(ob)
    return ob


def caixa(nome, x0, x1, y0, y1, z0, z1, mats=(), chanfro=0.0, segs=3):
    vs = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    fs = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    ob = malha(nome, vs, fs, mats)
    _normais_fora(ob)
    if chanfro:
        chanfrar(ob, chanfro, segs)
    return ob


def chanfrar(ob, largura, segs=3, aplicar=True, angulo=40):
    md = ob.modifiers.new("chanfro", "BEVEL")
    md.width = largura
    md.segments = segs
    md.limit_method = "ANGLE"
    md.angle_limit = math.radians(angulo)
    md.harden_normals = False
    if aplicar:
        aplicar_mods(ob)
    return ob


def aplicar_transf(ob):
    me = ob.data
    me.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)


def aplicar_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    velho = ob.data
    ob.modifiers.clear()
    ob.data = me
    if velho.users == 0:
        bpy.data.meshes.remove(velho)
    return ob


def booleano(ob, cortador, op="DIFFERENCE", aplicar=True, apagar=True):
    md = ob.modifiers.new("bool", "BOOLEAN")
    md.operation = op
    md.object = cortador
    md.solver = "EXACT"
    if aplicar:
        aplicar_mods(ob)
    if apagar:
        bpy.data.objects.remove(cortador, do_unlink=True)
    return ob


def juntar(obs, nome):
    """Junta várias malhas num objeto só (sem booleano)."""
    bm = bmesh.new()
    mats = []
    for o in obs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        # remapeia materiais
        mapa = []
        for m in o.data.materials:
            if m not in mats:
                mats.append(m)
            mapa.append(mats.index(m))
        if mapa:
            idx = np.zeros(len(me.polygons), dtype=np.int32)
            me.polygons.foreach_get("material_index", idx)
            me.polygons.foreach_set("material_index", np.array([mapa[i] for i in idx], dtype=np.int32))
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        bpy.data.objects.remove(o, do_unlink=True)
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(nome, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def cortar_meio(ob, mat_corte, plano_y=0.0, guardar="+"):
    """Corte por Boolean com o plano y = plano_y. Guarda o lado + (ou -) e pinta a face de seção
    com mat_corte (chapada). Retorna o objeto."""
    big = 10.0
    if guardar == "+":
        cort = caixa("_cortador", -big, big, -big, plano_y, -big, big)
    else:
        cort = caixa("_cortador", -big, big, plano_y, big, -big, big)
    booleano(ob, cort)
    me = ob.data
    if mat_corte.name not in [m.name for m in me.materials if m]:
        me.materials.append(mat_corte)
    im = [m.name if m else "" for m in me.materials].index(mat_corte.name)
    n = len(me.polygons)
    cen = np.zeros(n * 3); nor = np.zeros(n * 3)
    me.polygons.foreach_get("center", cen)
    me.polygons.foreach_get("normal", nor)
    cen = cen.reshape(-1, 3); nor = nor.reshape(-1, 3)
    mw = ob.matrix_world
    sel = (np.abs(cen[:, 1] + mw.translation.y - plano_y) < 2e-4) & (np.abs(nor[:, 1]) > 0.999)
    idx = np.zeros(n, dtype=np.int32)
    me.polygons.foreach_get("material_index", idx)
    idx[sel] = im
    me.polygons.foreach_set("material_index", idx)
    # faces de seção sempre chapadas (sem suavizar com as vizinhas)
    sm = np.zeros(n, dtype=bool)
    me.polygons.foreach_get("use_smooth", sm)
    sm[sel] = False
    me.polygons.foreach_set("use_smooth", sm)
    me.update()
    return ob


# ============================================================ estúdio
def _sock(no, nome, tipo="RGBA"):
    return [s for s in no.inputs if s.name == nome and s.type == tipo][0]


def _mat_estudio():
    m = bpy.data.materials.new("estudio")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    out = N["Material Output"]
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])

    # grade do piso: distância até a linha mais próxima (pingpong) < meia espessura
    passo, esp = 0.25, 0.006

    def linha(saida):
        d = N.new("ShaderNodeMath"); d.operation = "DIVIDE"; d.inputs[1].default_value = passo
        pp = N.new("ShaderNodeMath"); pp.operation = "PINGPONG"; pp.inputs[1].default_value = 0.5
        lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = esp / 2 / passo
        L.new(saida, d.inputs[0]); L.new(d.outputs[0], pp.inputs[0]); L.new(pp.outputs[0], lt.inputs[0])
        return lt.outputs[0]
    gx = linha(sep.outputs["X"])
    gy = linha(sep.outputs["Y"])
    mx = N.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    L.new(gx, mx.inputs[0]); L.new(gy, mx.inputs[1])
    # some com a distância e na subida da parede
    vl = N.new("ShaderNodeVectorMath"); vl.operation = "LENGTH"
    L.new(tc.outputs["Object"], vl.inputs[0])
    fd = N.new("ShaderNodeMapRange")
    fd.inputs["From Min"].default_value = 1.2; fd.inputs["From Max"].default_value = 4.5
    fd.inputs["To Min"].default_value = 1.0; fd.inputs["To Max"].default_value = 0.0
    L.new(vl.outputs["Value"], fd.inputs["Value"])
    fz = N.new("ShaderNodeMapRange")
    fz.inputs["From Min"].default_value = 0.02; fz.inputs["From Max"].default_value = 0.15
    fz.inputs["To Min"].default_value = 1.0; fz.inputs["To Max"].default_value = 0.0
    L.new(sep.outputs["Z"], fz.inputs["Value"])
    m1 = N.new("ShaderNodeMath"); m1.operation = "MULTIPLY"
    m2 = N.new("ShaderNodeMath"); m2.operation = "MULTIPLY"
    L.new(mx.outputs[0], m1.inputs[0]); L.new(fd.outputs[0], m1.inputs[1])
    L.new(m1.outputs[0], m2.inputs[0]); L.new(fz.outputs[0], m2.inputs[1])
    cor_piso = N.new("ShaderNodeMix"); cor_piso.data_type = "RGBA"
    _sock(cor_piso, "A").default_value = lin("#0E1014")
    _sock(cor_piso, "B").default_value = lin("#1F242B")
    L.new(m2.outputs[0], _sock(cor_piso, "Factor", "VALUE"))
    L.new([o for o in cor_piso.outputs if o.type == "RGBA"][0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.30
    b.inputs["Specular IOR Level"].default_value = 0.22

    # parede: degradê emissivo (embaixo #22272F, em cima #14171C)
    gz = N.new("ShaderNodeMapRange")
    gz.inputs["From Min"].default_value = 0.4; gz.inputs["From Max"].default_value = 3.2
    L.new(sep.outputs["Z"], gz.inputs["Value"])
    cw = N.new("ShaderNodeMix"); cw.data_type = "RGBA"
    _sock(cw, "A").default_value = lin(GRAFITE_CLA)
    _sock(cw, "B").default_value = lin(GRAFITE_ESC)
    L.new(gz.outputs["Result"], _sock(cw, "Factor", "VALUE"))
    em = N.new("ShaderNodeEmission")
    L.new([o for o in cw.outputs if o.type == "RGBA"][0], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    # mistura piso (iluminado) -> parede (emissiva) pela altura
    fw = N.new("ShaderNodeMapRange")
    fw.inputs["From Min"].default_value = 0.05; fw.inputs["From Max"].default_value = 0.9
    L.new(sep.outputs["Z"], fw.inputs["Value"])
    ms = N.new("ShaderNodeMixShader")
    L.new(fw.outputs["Result"], ms.inputs[0])
    L.new(b.outputs[0], ms.inputs[1])
    L.new(em.outputs[0], ms.inputs[2])
    L.new(ms.outputs[0], out.inputs["Surface"])
    return m


def estudio_tecnico(fundo_y=2.4, raio_curva=1.2, largura=16.0, luz=1.0, alvo=(0, 0, 0.35),
                    strips=True, top=True, rim=True):
    """Estúdio infinito escuro (ciclorama), grade sutil no piso e luz de produto:
    2 strip lights laterais (reflexos longos), top e rim. 'luz' multiplica todas as potências."""
    perfil = []
    for i in range(30):                       # piso
        perfil.append((-9.0 + (fundo_y - raio_curva + 9.0) * i / 29, 0.0))
    for i in range(1, 25):                    # curva
        t = (math.pi / 2) * i / 24
        perfil.append((fundo_y - raio_curva + raio_curva * math.sin(t), raio_curva * (1 - math.cos(t))))
    for i in range(1, 12):                    # parede
        perfil.append((fundo_y, raio_curva + 7.0 * i / 11))
    xs = np.linspace(-largura / 2, largura / 2, 41)
    vs, fs = [], []
    n = len(perfil)
    for x in xs:
        for y, z in perfil:
            vs.append((x, y, z))
    for a in range(len(xs) - 1):
        for i in range(n - 1):
            fs.append([a * n + i, (a + 1) * n + i, (a + 1) * n + i + 1, a * n + i + 1])
    ob = malha("estudio", vs, fs, [_mat_estudio()], suave=80)
    for f in ob.data.polygons:
        f.use_smooth = True

    luzes = {}
    if strips:
        luzes["strip_esq"] = luz_area("strip_esq", (-1.9, -1.1, 1.05), alvo, 0.14, 2.6, 90 * luz, abertura=75)
        luzes["strip_dir"] = luz_area("strip_dir", (1.9, -0.7, 1.05), alvo, 0.14, 2.6, 75 * luz, abertura=75)
    if top:
        luzes["top"] = luz_area("top", (0.0, -0.2, 3.2), alvo, 1.6, 1.0, 18 * luz, abertura=55)
    if rim:
        luzes["rim"] = luz_area("rim", (0.2, 1.7, 2.3), alvo, 2.4, 0.3, 160 * luz, abertura=45)
        luzes["rim"].visible_diffuse = False          # só brilho de contorno, sem poça de luz no chão
        _excluir_da_luz(luzes["rim"], [ob])           # e sem reflexo estourado no piso
    return ob, luzes


def _excluir_da_luz(luz, objs):
    """Light linking: a luz ilumina tudo, menos 'objs'."""
    col = bpy.data.collections.new(luz.name + "_receptores")
    for o in objs:
        col.objects.link(o)
    luz.light_linking.receiver_collection = col
    for co in col.collection_objects:
        co.light_linking.link_state = "EXCLUDE"


def luz_area(nome, loc, alvo, sx, sy, potencia, cor="#FFFFFF", abertura=None):
    ld = bpy.data.lights.new(nome, "AREA")
    if abertura:
        ld.spread = math.radians(abertura)
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = sx, sy
    ld.energy = potencia
    ld.color = lin(cor)[:3]
    ob = bpy.data.objects.new(nome, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    mirar(ob, alvo)
    ob.visible_camera = False
    return ob


# ============================================================ PNEU EM CORTE
# 205/55 R16: largura 205 mm, flanco 113 mm, aro 16" (raio do talão 203 mm)
def _perfil_pneu(R=0.316, rb=0.203, A=0.1075, n=280):
    """Perfil externo liso (a, r) do talão esquerdo ao direito, passando pela banda; normais para fora."""
    B = (R - rb) / 2
    rc = rb + B
    p, q = 3.6, 13.0

    def pt(u):
        c, s = math.cos(u), math.sin(u)
        return (A * math.copysign(abs(c) ** (2 / p), c), rc + B * math.copysign(abs(s) ** (2 / q), s))
    # acha o u onde a largura bate no talão (a = 0.0805)
    lo, hi = -math.pi / 2, 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if pt(mid)[0] < 0.0805:
            lo = mid
        else:
            hi = mid
    u_end = (lo + hi) / 2
    us = np.linspace(math.pi - u_end, u_end, n)        # esquerda (talão) -> topo -> direita (talão)
    # concentra amostras na banda (onde há sulcos)
    P = np.array([pt(u) for u in us])
    # reamostra por comprimento de arco com densidade maior na banda
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    tn = (P[:, 1] - rb) / (R - rb)
    dens = 1.0 + 2.2 * _smooth(tn, 0.80, 0.95)
    w = np.r_[0, np.cumsum(((dens[1:] + dens[:-1]) / 2) * np.diff(seg))]
    alvo = np.linspace(0, w[-1], n)
    s_alvo = np.interp(alvo, w, seg)
    P = np.c_[np.interp(s_alvo, seg, P[:, 0]), np.interp(s_alvo, seg, P[:, 1])]
    # pezinho do talão até encostar no aro
    pe_e = np.array([[P[0, 0] + 0.0004, rb + 0.0055], [P[0, 0] + 0.001, rb + 0.002]])[::-1]
    pe_d = np.array([[P[-1, 0] - 0.0004, rb + 0.0055], [P[-1, 0] - 0.001, rb + 0.002]])
    P = np.vstack([pe_e, P, pe_d])
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    Nn = np.c_[-T[:, 1], T[:, 0]]
    return P, Nn


def _params_pressao(pressao, R=0.316):
    pres = max(0.25, min(1.3, pressao))
    d = 0.0135 / pres ** 1.25                       # deflexão (m): 13,5 mm calibrado, ~50 mm a 35 %
    bojo = 0.30 * d + 0.75 * max(0.0, d - 0.016)    # abaulamento do flanco (por lado)
    lift = 0.0045 * max(0.0, (0.8 - pres) / 0.3)    # centro da banda levanta quando murcho
    return d, bojo, lift, R - d                     # ... e altura do eixo


def _fazer_deforma(d, bojo, lift, h0, rb, H):
    def deforma(a, r, t):
        """Deslocamento (da, dr) da superfície externa lisa no ângulo t (0 = no chão)."""
        tnn = np.clip((r - rb) / H, 0, 1)
        w = np.exp(-(t / 0.42) ** 2)
        wb = np.exp(-(t / 0.62) ** 2)
        r1 = r - d * w * tnn ** 1.6
        # flanco dobra: bojo com o pico um pouco abaixo do meio (onde a lona "vinca")
        perfil_bojo = np.sin(math.pi * tnn ** 0.75) ** 1.8
        a1 = a + np.sign(a) * bojo * wb * perfil_bojo
        ct = np.cos(t)
        lim = np.where(ct > 1e-3, h0 / np.maximum(ct, 1e-3), 1e9)
        r1 = np.minimum(r1, lim)
        wc = np.exp(-(t / 0.30) ** 2) * np.clip(1 - (a / 0.085) ** 2, 0, 1) ** 1.5 * _smooth(tnn, 0.85, 0.97)
        r1 = r1 - lift * wc
        return a1 - a, r1 - r
    return deforma


def _tracejado(nome, pts, larg, traco, vao, mat, y=-0.0015):
    """Fita tracejada no plano y (pts = [(x, z)...])."""
    P = np.array(pts)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    vs, fs = [], []
    s0 = 0.0
    while s0 < seg[-1]:
        s1 = min(s0 + traco, seg[-1])
        ss = np.linspace(s0, s1, max(2, int((s1 - s0) / 0.0015) + 1))
        xs = np.interp(ss, seg, P[:, 0]); zs = np.interp(ss, seg, P[:, 1])
        Q = np.c_[xs, zs]
        T = np.gradient(Q, axis=0) if len(Q) > 2 else np.repeat(np.diff(Q, axis=0), 2, axis=0)
        T = T / np.maximum(np.linalg.norm(T, axis=1)[:, None], 1e-9)
        Nq = np.c_[-T[:, 1], T[:, 0]] * larg / 2
        base = len(vs)
        for q, nn in zip(Q, Nq):
            vs.append((q[0] + nn[0], y, q[1] + nn[1])); vs.append((q[0] - nn[0], y, q[1] - nn[1]))
        for k in range(len(Q) - 1):
            fs.append([base + 2 * k, base + 2 * k + 1, base + 2 * k + 3, base + 2 * k + 2])
        s0 = s1 + vao
    ob = malha(nome, vs, fs, [mat])
    ob.visible_shadow = False
    ob.visible_glossy = False
    return ob


def pneu_corte(nome, loc=(0, 0, 0), yaw=-35.0, pressao=1.0, R=0.316, rb=0.203,
               mat_secao_pneu=None, seg_ang=460, cor_pegada=None, camadas=True, fantasma=None):
    """Pneu 205/55 R16 cortado ao meio pelo plano vertical que contém o eixo (fica a metade de trás),
    com aro de liga de 5 raios inteiro, disco de freio e a pegada desenhada no chão.

    pressao: 1.0 = calibrado; 0.5 ~ murcho (metade da pressão). Controla a deflexão (achatamento da pegada),
    o abaulamento/dobra do flanco e o levantamento do centro da banda (pneu murcho apoia nos ombros).
    Eixo do pneu = X local; o pneu encosta no chão (z = 0 do 'loc').
    fantasma: cor (ex.: VERDE) para desenhar, tracejado sobre a seção de baixo, o perfil do pneu CALIBRADO
    (pressão 1.0) apoiado no mesmo chão: mostra quanto o flanco dobrou e o aro desceu.
    Retorna dict com objetos, âncoras (pontos 3D de mundo p/ callouts) e medidas da pegada."""
    H = R - rb
    d, bojo, lift, h0 = _params_pressao(pressao, R)

    P, Nn = _perfil_pneu(R, rb)
    n = len(P)
    a0, r0 = P[:, 0], P[:, 1]
    tn = np.clip((r0 - rb) / H, 0, 1)
    # espessura da borracha: flanco 7 mm, banda 19 mm, talão 16 mm
    thk = 0.0070 + 0.012 * _smooth(tn, 0.78, 0.93) * _smooth(0.115 - np.abs(a0), -0.02, 0.0) \
        + 0.009 * _smooth(0.28 - tn, 0.0, 0.2)
    I = P - Nn * thk[:, None]
    banda = _smooth(tn, 0.86, 0.93)

    # relevos do perfil (aplicados só na superfície externa, depois da deformação)
    rel = np.zeros(n)
    sulcos = [(-0.062, 0.0095), (-0.022, 0.0105), (0.022, 0.0105), (0.062, 0.0095)]
    for c, wdt in sulcos:
        rel -= 0.0078 * _faixa(a0, c, wdt, 0.0016) * banda
    flanco = (1 - banda) * _smooth(tn, 0.05, 0.12)
    rel += 0.0030 * _faixa(tn, 0.17, 0.07, 0.03) * flanco            # protetor de aro
    for c in (0.50, 0.555, 0.61):                                    # nervuras finas
        rel += 0.0008 * _faixa(tn, c, 0.012, 0.006) * flanco
    rel += 0.0012 * _faixa(tn, 0.80, 0.10, 0.04) * (1 - banda)       # degrau do ombro
    ombro = _smooth(np.abs(a0), 0.072, 0.080) * banda

    th = np.linspace(0.0, math.pi, seg_ang)[:, None]                 # 0 = embaixo (chão), pi = em cima

    deforma = _fazer_deforma(d, bojo, lift, h0, rb, H)


    da, dr = deforma(a0[None, :], r0[None, :], th)                   # (K, n)
    # sulcos transversais nos ombros (blocos), 64 passos por volta; corte cai no meio de um bloco
    passo = 64
    fr = (th * passo / (2 * math.pi)) % 1.0
    transv = _faixa(fr, 0.5, 0.20, 0.06) * ombro[None, :]
    lamelas = _faixa((th * passo * 2 / (2 * math.pi) + 0.25) % 1.0, 0.5, 0.05, 0.02) * \
        (banda * (np.abs(a0) < 0.055))[None, :]
    relevo = rel[None, :] - 0.0072 * transv - 0.0025 * lamelas
    relevo = np.minimum(relevo, rel[None, :])
    relevo = np.where(transv > 0, np.minimum(relevo, rel[None, :] - 0.0072 * transv), relevo)

    Ao = a0[None, :] + da + Nn[None, :, 0] * relevo
    Ro = r0[None, :] + dr + Nn[None, :, 1] * relevo
    Ai = I[None, :, 0] + da
    Ri = I[None, :, 1] + dr

    def xyz(A_, R_, T_):
        return np.stack([A_, R_ * np.sin(T_), -R_ * np.cos(T_)], axis=-1)

    K = seg_ang
    anel = np.concatenate([xyz(Ao, Ro, th), xyz(Ai[:, ::-1], Ri[:, ::-1], th)], axis=1)   # (K, 2n, 3)
    m2 = 2 * n
    verts = anel.reshape(-1, 3)
    kk, jj = np.meshgrid(np.arange(K - 1), np.arange(m2), indexing="ij")
    j2 = (jj + 1) % m2
    quads = np.stack([kk * m2 + jj, kk * m2 + j2, (kk + 1) * m2 + j2, (kk + 1) * m2 + jj], axis=-1).reshape(-1, 4)
    # tampas (seção) em t = 0 e t = pi: faixa externa i <-> interna i
    caps = []
    for k in (0, K - 1):
        for i in range(n - 1):
            oi, oj = k * m2 + i, k * m2 + i + 1
            ii, ij = k * m2 + (m2 - 1 - i), k * m2 + (m2 - 2 - i)
            caps.append([oi, oj, ij, ii])
    faces = np.vstack([quads, np.array(caps)])
    idx = np.r_[np.zeros(len(quads), dtype=np.int32), np.ones(len(caps), dtype=np.int32)]
    msec = mat_secao_pneu or M("sec_pneu", lambda: mat_secao("#E0601E", "sec_pneu", 0.32))
    pneu = malha(nome + "_pneu", verts, faces, [M("borracha", mat_borracha), msec], idx, suave=38)
    _normais_fora(pneu)
    sm = np.ones(len(faces), dtype=bool)
    sm[len(quads):] = False
    pneu.data.polygons.foreach_set("use_smooth", sm)

    pai = bpy.data.objects.new(nome, None)
    bpy.context.scene.collection.objects.link(pai)
    objs = [pneu]

    # ---------- camadas internas desenhadas na seção (carcaça, cintas, cinta de nylon, talão, ar)
    def ponto_sec(i, prof, t):
        """Ponto na seção a 'prof' para dentro da superfície externa lisa, no índice i, ângulo t (0 ou pi)."""
        dda, ddr = deforma(np.array([a0[i]]), np.array([r0[i]]), np.array([t]))
        a = a0[i] - Nn[i, 0] * prof + dda[0]
        r = r0[i] - Nn[i, 1] * prof + ddr[0]
        return (a, -0.0006 if True else 0, r)

    def no_plano(a, r, t, ofs=-0.0006):
        # t = 0 (embaixo): z = -r ; t = pi (em cima): z = +r ; y levemente à frente da seção
        return (a, ofs, -r if t == 0 else r)

    def fita(i0, i1, p0, p1, t, ofs):
        vs, fs = [], []
        for i in range(i0, i1 + 1):
            for prof in (p0, p1):
                prof_i = prof(i) if callable(prof) else prof
                a, _, r = ponto_sec(i, prof_i, t)
                vs.append(no_plano(a, r, t, ofs))
        for k in range(i1 - i0):
            fs.append([2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2])
        return vs, fs

    mat_carc = M("carcaca", lambda: mat_secao("#E8D7B0", "carcaca", 0.35))
    mat_cinta = M("cinta", lambda: mat_secao("#C9D2DC", "cinta", 0.45))
    mat_nylon = M("nylon", lambda: mat_secao("#FFB27A", "nylon", 0.5))
    mat_ar = M("ar", lambda: mat_emissivo(CIANO, 0.5, "ar", alpha=0.09))
    ib = np.where(banda > 0.5)[0]
    ib = ib[np.abs(a0[ib]) < 0.090]
    for t in (0.0, math.pi):
        camadas_v, camadas_f, camadas_m = [], [], []

        def add(vs, fs, mi):
            base = len(camadas_v)
            camadas_v.extend(vs)
            camadas_f.extend([[base + x for x in f] for f in fs])
            camadas_m.extend([mi] * len(fs))
        if camadas:
            # carcaça (lona têxtil) acompanhando o lado de dentro, de talão a talão
            add(*fita(2, n - 3, lambda i: thk[i] - 0.0026, lambda i: thk[i] - 0.0013, t, -0.0006), 0)
            # duas cintas de aço sob a banda
            i0, i1 = ib[0], ib[-1]
            add(*fita(i0 + 2, i1 - 2, lambda i: thk[i] - 0.0052, lambda i: thk[i] - 0.0040, t, -0.0007), 1)
            add(*fita(i0 + 5, i1 - 5, lambda i: thk[i] - 0.0070, lambda i: thk[i] - 0.0058, t, -0.0007), 1)
            # cinta de nylon (cobertura)
            add(*fita(i0, i1, lambda i: thk[i] - 0.0088, lambda i: thk[i] - 0.0079, t, -0.0007), 2)
            # arame do talão (quadradinho de aço)
            for ie in (3, n - 4):
                a, _, r = ponto_sec(ie, thk[ie] * 0.5, t)
                s = 0.0042
                base = [(a - s, r - s), (a + s, r - s), (a + s, r + s), (a - s, r + s)]
                add([no_plano(x, y, t, -0.0007) for x, y in base], [[0, 1, 2, 3]], 1)
        # ar: polígono do lado de dentro (deformado) fechado pelo aro
        vs = []
        for i in range(0, n):
            a, _, r = ponto_sec(i, thk[i] + 0.0004, t)
            vs.append(no_plano(a, r, t, -0.0005))
        vs.append(no_plano(a0[-1] - 0.004, rb + 0.016, t, -0.0005))
        vs.append(no_plano(a0[0] + 0.004, rb + 0.016, t, -0.0005))
        # fatias "horizontais" ligando a parede esquerda à direita (sem sobreposição de triângulos)
        bm = bmesh.new()
        bv = [bm.verts.new(v) for v in vs[:n]]
        for i in range(n // 2 - 1):
            j = n - 1 - i
            try:
                bm.faces.new((bv[i], bv[i + 1], bv[j - 1], bv[j]))
            except ValueError:
                pass
        if n % 2 == 1:
            try:
                bm.faces.new((bv[n // 2 - 1], bv[n // 2], bv[n // 2 + 1]))
            except ValueError:
                pass
        me = bpy.data.meshes.new(f"{nome}_ar_{int(t)}")
        bm.to_mesh(me); bm.free()
        me.materials.append(mat_ar)
        ob_ar = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(ob_ar)
        ob_ar.visible_shadow = False
        objs.append(ob_ar)
        if camadas_v:
            ob_c = malha(f"{nome}_camadas_{int(t)}", camadas_v, camadas_f, [mat_carc, mat_cinta, mat_nylon], camadas_m)
            objs.append(ob_c)

    # ---------- perfil fantasma do pneu calibrado (tracejado), apoiado no mesmo chão
    if fantasma:
        dc, bc, lc, h0c = _params_pressao(1.0, R)
        defc = _fazer_deforma(dc, bc, lc, h0c, rb, H)
        dda, ddr = defc(a0, r0, np.zeros(n))
        pts = [(a, -(r) + (h0c - h0)) for a, r in zip(a0 + dda, r0 + ddr)]
        objs.append(_tracejado(nome + "_fantasma", pts, 0.0022, 0.009, 0.006, mat_emissivo(fantasma, 3.0)))

    # ---------- aro de liga 5 raios (inteiro), cubo e disco de freio
    objs += _aro_5raios(nome)

    # ---------- pegada no chão (contorno + preenchimento)
    pts_chao = verts[np.abs(verts[:, 2] + h0) < 0.0012]
    peg = {}
    if len(pts_chao):
        ax0, ax1 = pts_chao[:, 0].min(), pts_chao[:, 0].max()
        ly = pts_chao[:, 1].max()
        peg = {"largura": ax1 - ax0, "comprimento": 2 * ly, "a0": ax0, "a1": ax1}
        if cor_pegada:
            objs += _pegada(nome, ax0, ax1, ly, -h0, cor_pegada)

    for o in objs:
        o.parent = pai
    pai.location = (loc[0], loc[1], loc[2] + h0)
    pai.rotation_euler = (0, 0, math.radians(yaw))
    bpy.context.view_layer.update()
    mw = pai.matrix_world

    # âncoras para callouts (coordenadas de mundo)
    def W(a, y, z):
        return tuple(mw @ Vector((a, y, z)))
    ic = n // 2
    i_fl = int(np.argmin(np.abs(tn[: n // 2] - 0.5)))                # meio do flanco esquerdo (embaixo)
    i_fl_d = n - 1 - i_fl
    a_fl, _, r_fl = ponto_sec(i_fl_d, 0.0, 0.0)
    a_ci, _, r_ci = ponto_sec(ic, thk[ic] - 0.0046, math.pi)
    a_ar, _, r_ar = ponto_sec(ic, thk[ic] + 0.045, math.pi)
    anc = {
        "cintas": W(a_ci, -0.001, r_ci),
        "ar": W(a_ar, -0.001, r_ar),
        "flanco": W(a_fl, -0.001, -r_fl),
        "flanco_esq": W(ponto_sec(i_fl, 0, 0.0)[0], -0.001, -ponto_sec(i_fl, 0, 0.0)[2]),
        "pegada": W(0.0, -peg.get("comprimento", 0.2) / 2 * 0.75, -h0),
        "pegada_canto": W(peg.get("a0", -0.07) * 0.8, -peg.get("comprimento", 0.2) / 2 * 0.8, -h0),
        "banda_baixo": W(0.0, -0.001, -(h0 + 0.0)),
        "topo": W(0.0, 0.0, R + 0.05),
        "centro": W(0.0, 0.0, 0.0),
    }
    return {"pai": pai, "objs": objs, "ancoras": anc, "pegada": peg, "deflexao": d, "h0": h0}


def _pegada(nome, ax0, ax1, ly, z, cor):
    """Retângulo arredondado da área de contato: borda brilhante + véu translúcido."""
    def ret(x0, x1, y0, y1, rr, nseg=6):
        cx = [(x1 - rr, y1 - rr, 0), (x0 + rr, y1 - rr, 1), (x0 + rr, y0 + rr, 2), (x1 - rr, y0 + rr, 3)]
        pts = []
        for x, y, q in cx:
            for i in range(nseg + 1):
                t = math.pi / 2 * (q + i / nseg)
                pts.append((x + rr * math.cos(t), y + rr * math.sin(t)))
        return pts
    e = 0.004
    rr = min(0.02, (ax1 - ax0) / 4)
    ext = ret(ax0 - e, ax1 + e, -ly - e, ly + e, rr + e)
    inn = ret(ax0, ax1, -ly, ly, rr)
    n = len(ext)
    zz = z + 0.0008
    vs = [(x, y, zz) for x, y in ext] + [(x, y, zz) for x, y in inn]
    fs = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    borda = malha(nome + "_pegada_borda", vs, fs, [mat_emissivo(cor, 6.0)])
    veu = malha(nome + "_pegada_veu", [(x, y, z + 0.0005) for x, y in inn], [list(range(n))],
                [mat_emissivo(cor, 1.4, alpha=0.22)])
    for o in (borda, veu):
        o.visible_shadow = False
        o.visible_glossy = False
    return [borda, veu]


def _aro_5raios(nome):
    alu = M("alu_aro", lambda: mat_metal("#DCE1E6", 0.28, "alu_aro"))
    alu_fosco = M("alu_fosco", lambda: mat_metal("#7D848C", 0.38, "alu_fosco"))
    aco = M("aco", lambda: mat_metal(ACO, 0.3, "aco"))
    aco_esc = M("aco_esc", lambda: mat_metal("#5B626B", 0.42, "aco_esc"))
    # tala (barril) com abas, assento do talão e canal central
    ext = [(-0.0880, 0.2160), (-0.0855, 0.2192), (-0.0815, 0.2185), (-0.0800, 0.2120), (-0.0790, 0.2060),
           (-0.0740, 0.2032), (-0.0500, 0.2030), (-0.0420, 0.1830), (0.0180, 0.1830), (0.0280, 0.2030),
           (0.0740, 0.2032), (0.0790, 0.2060), (0.0800, 0.2120), (0.0815, 0.2185), (0.0855, 0.2192),
           (0.0880, 0.2160)]
    inn = [(0.0870, 0.2080), (0.0820, 0.1975), (0.0330, 0.1960), (0.0240, 0.1770), (-0.0380, 0.1770),
           (-0.0460, 0.1960), (-0.0820, 0.1975), (-0.0870, 0.2080)]
    tala = revolver(nome + "_tala", ext + inn, eixo="X", segs=160, mats=[alu_fosco], suave=35)
    # cubo + 5 raios (face em +X, côncava)
    pecas = []
    for k in range(5):
        ang = 2 * math.pi * k / 5 + math.pi / 2
        vs = []
        for r, a_in, a_out, wd in ((0.058, 0.040, 0.066, 0.052), (0.120, 0.048, 0.072, 0.040),
                                   (0.1935, 0.060, 0.086, 0.044)):
            for a in (a_in, a_out):
                for s in (-1, 1):
                    tw = s * wd / 2
                    x, y = r, tw
                    yy = x * math.cos(ang) - y * math.sin(ang)
                    zz = x * math.sin(ang) + y * math.cos(ang)
                    vs.append((a, yy, zz))
        # 3 estações x (a_in, a_out) x (lados) -> 12 vértices
        fs = []
        for st in range(2):
            b0, b1 = st * 4, (st + 1) * 4
            fs += [[b0 + 0, b0 + 1, b1 + 1, b1 + 0], [b0 + 2, b1 + 2, b1 + 3, b0 + 3],
                   [b0 + 0, b1 + 0, b1 + 2, b0 + 2], [b0 + 1, b0 + 3, b1 + 3, b1 + 1]]
        fs += [[0, 2, 3, 1], [8, 9, 11, 10]]
        rp = malha(f"{nome}_raio{k}", vs, fs, [alu])
        _normais_fora(rp)
        chanfrar(rp, 0.0045, 3, angulo=30)
        sub = rp.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 1
        aplicar_mods(rp)
        rp.data.shade_smooth()
        pecas.append(rp)
    cubo = revolver(nome + "_cubo", [(0.034, 0.0), (0.034, 0.072), (0.050, 0.075), (0.066, 0.070),
                                     (0.071, 0.050), (0.071, 0.034), (0.074, 0.030), (0.074, 0.0)],
                    eixo="X", segs=96, mats=[alu], suave=30)
    tampa = revolver(nome + "_tampa", [(0.070, 0.0), (0.070, 0.029), (0.0745, 0.027), (0.0775, 0.018),
                                       (0.0785, 0.0)], eixo="X", segs=64, mats=[M("preto_brilho", lambda: mat_pintura("#15181C", "preto_brilho"))], suave=40)
    porcas = []
    for k in range(5):
        ang = 2 * math.pi * (k + 0.5) / 5 + math.pi / 2
        c = (0.0, 0.050 * math.cos(ang), 0.050 * math.sin(ang))
        po = cilindro(f"{nome}_porca{k}", 0.0085, (0.066, c[1], c[2]), (0.080, c[1], c[2]), segs=6, mats=[aco], suave=20)
        chanfrar(po, 0.0012, 1)
        porcas.append(po)
    # disco de freio ventilado (atrás do cubo)
    disco = revolver(nome + "_disco", [(0.004, 0.072), (0.004, 0.150), (0.030, 0.150), (0.030, 0.072)],
                     eixo="X", segs=128, mats=[aco_esc], suave=30)
    chapeu = revolver(nome + "_chapeu", [(0.030, 0.0), (0.030, 0.074), (0.034, 0.074), (0.034, 0.0)],
                      eixo="X", segs=96, mats=[aco], suave=30)
    return [tala, cubo, tampa, disco, chapeu] + pecas + porcas


# ============================================================ MOTOR EM CORTE (1 cilindro)
def motor_corte(nome="motor", loc=(0, 0, 0), yaw=0.0, ang_vira=80.0, nivel_oleo=0.42):
    """Motor monocilíndrico em corte pelo plano y = 0 (perpendicular ao virabrequim), metade de trás.
    Bloco, cabeçote, cárter e óleo são cortados (seção laranja); pistão, biela e virabrequim ficam inteiros.
    ang_vira: ângulo do virabrequim a partir do PMS (80° ~ pistão no meio do curso).
    nivel_oleo: fração da altura interna do cárter ocupada pelo óleo.
    Diâmetro 86 mm, curso 86 mm, biela 145 mm. Origem = eixo do virabrequim; o cárter encosta em z = 0 do 'loc'."""
    rv, Lb, rcil = 0.043, 0.145, 0.043
    phi = math.radians(ang_vira)
    pino_v = (rv * math.sin(phi), rv * math.cos(phi))                      # moente (x, z)
    z_pino = rv * math.cos(phi) + math.sqrt(Lb ** 2 - (rv * math.sin(phi)) ** 2)
    alt_comp = 0.032                                                        # pino -> topo do pistão
    z_coroa = z_pino + alt_comp
    deck = rv + Lb + alt_comp + 0.0015
    z_carter = -0.150

    sec = M("sec_motor", lambda: mat_secao_tecnica("sec_motor"))
    alu_bloco = M("alu_bloco", lambda: mat_metal("#8E97A1", 0.35, "alu_bloco"))
    alu_cab = M("alu_cab", lambda: mat_metal("#A3ABB4", 0.33, "alu_cab"))
    aco = M("aco", lambda: mat_metal(ACO, 0.28, "aco"))
    aco_pol = M("aco_pol", lambda: mat_metal("#C3CAD1", 0.12, "aco_pol"))
    aco_esc = M("aco_esc", lambda: mat_metal("#4C535C", 0.30, "aco_esc_anel"))
    alu_pist = M("alu_pist", lambda: mat_metal("#C7CDD4", 0.30, "alu_pist"))
    carter_m = M("carter", lambda: mat_metal("#3A4048", 0.45, "carter"))
    oleo = M("oleo", mat_oleo)
    cera = M("ceramica", lambda: _ceramica())
    objs = []

    # ---------- bloco
    bloco = caixa(nome + "_bloco_sup", -0.078, 0.078, -0.072, 0.072, 0.055, deck, [alu_bloco], chanfro=0.004)
    inf = caixa(nome + "_bloco_inf", -0.104, 0.104, -0.072, 0.072, -0.050, 0.075, [alu_bloco], chanfro=0.004)
    booleano(bloco, inf, "UNION")
    # nervuras externas do cárter superior
    for x in (-0.104, 0.104):
        for zz in (-0.030, 0.010, 0.050):
            nv = caixa("_nerv", x - 0.004, x + 0.004, -0.074, 0.074, zz - 0.004, zz + 0.004, chanfro=0.0015, segs=2)
            booleano(bloco, nv, "UNION")
    # cilindro (camisa) + cavidade do virabrequim + passagem da biela + galerias de água
    booleano(bloco, cilindro("_cil", rcil + 0.0004, (0, 0, 0.030), (0, 0, deck + 0.01), segs=96))
    booleano(bloco, cilindro("_cav", 0.083, (0, -0.056, 0), (0, 0.056, 0), segs=96))
    booleano(bloco, caixa("_cav2", -0.083, 0.083, -0.056, 0.056, -0.08, 0.0))
    booleano(bloco, caixa("_cav3", -0.040, 0.040, -0.040, 0.040, 0.0, 0.07, chanfro=0.006))
    for s in (-1, 1):
        booleano(bloco, caixa("_agua", s * 0.052 - 0.0065, s * 0.052 + 0.0065, -0.055, 0.055, 0.105, deck - 0.006,
                               chanfro=0.003))
    booleano(bloco, cilindro("_mancal", 0.0262, (0, -0.2, 0), (0, 0.2, 0), segs=64))
    cortar_meio(bloco, sec)
    objs.append(bloco)

    # ---------- junta + cabeçote com câmara, dutos, válvulas e vela
    junta = caixa(nome + "_junta", -0.078, 0.078, -0.072, 0.072, deck, deck + 0.0016, [M("junta", lambda: mat_metal("#2B2F35", 0.5, "junta"))])
    booleano(junta, cilindro("_jf", rcil + 0.001, (0, 0, deck - 0.01), (0, 0, deck + 0.01), segs=96))
    cortar_meio(junta, M("sec_junta", lambda: mat_secao("#20242A", "sec_junta", 0.0)))
    objs.append(junta)
    zc = deck + 0.0016
    cab = caixa(nome + "_cabecote", -0.080, 0.080, -0.072, 0.072, zc, zc + 0.092, [alu_cab], chanfro=0.004)
    tampa_v = caixa(nome + "_tampa_val", -0.074, 0.074, -0.066, 0.066, zc + 0.092, zc + 0.122,
                    [M("tampa_v", lambda: mat_pintura("#1D2127", "tampa_v"))], chanfro=0.010, segs=4)
    esf = revolver("_dome", [(0, 0.0), (0, rcil * 0.98), (0.010, rcil * 0.96), (0.018, rcil * 0.80),
                             (0.024, rcil * 0.45), (0.026, 0.0)], eixo="Z", segs=96)
    esf.location = (0, 0, zc - 0.001)
    aplicar_transf(esf)
    booleano(cab, esf)
    valvulas = []
    for s, lado in ((-1, "adm"), (1, "esc")):
        incl = math.radians(18) * s
        # sede no teto da câmara
        base = Vector((s * 0.018, 0, zc + 0.019))
        eixo = Vector((math.sin(incl), 0, math.cos(incl)))
        # duto: sai da sede, curva para o lado
        p1 = base + eixo * 0.010
        p2 = p1 + Vector((s * 0.040, 0, 0.022))
        p3 = p2 + Vector((s * 0.060, 0, 0.004))
        for qa, qb, rr in ((base - eixo * 0.004, p1 + eixo * 0.006, 0.0155), (p1, p2, 0.0150), (p2 - Vector((s * 0.004, 0, 0)), p3, 0.0150)):
            booleano(cab, cilindro("_duto", rr, tuple(qa), tuple(qb), segs=48))
        # guia + furo da haste
        booleano(cab, cilindro("_guia", 0.0045, tuple(base), tuple(base + eixo * 0.12), segs=24))
        # válvula: haste + cabeça (tulipa)
        cab_v = revolver(f"{nome}_val_{lado}", [(0.0, 0.0), (0.0, 0.0150), (0.0012, 0.0155), (0.0030, 0.0120),
                                               (0.0080, 0.0042), (0.0090, 0.0035), (0.0, 0.0)][:-1] + [(0.0090, 0.0)],
                         eixo="Z", segs=48, mats=[aco_pol], suave=40)
        q = eixo.to_track_quat("Z", "Y")
        cab_v.matrix_world = Matrix.Translation(base - eixo * 0.0015) @ q.to_matrix().to_4x4()
        aplicar_transf(cab_v)
        haste = cilindro(f"{nome}_haste_{lado}", 0.0035, tuple(base), tuple(base + eixo * 0.105), segs=24, mats=[aco_pol])
        mola = _mola(f"{nome}_mola_{lado}", base + eixo * 0.068, eixo, 0.0105, 0.030, 6, aco_esc)
        valvulas += [cab_v, haste, mola]
    # vela no centro
    booleano(cab, cilindro("_vela_f", 0.0075, (0, 0, zc + 0.015), (0, 0, zc + 0.125), segs=32))
    vela_cer = cilindro(nome + "_vela_cer", 0.0058, (0, 0, zc + 0.055), (0, 0, zc + 0.104), segs=32, mats=[cera])
    vela_aco = cilindro(nome + "_vela_aco", 0.0068, (0, 0, zc + 0.022), (0, 0, zc + 0.056), segs=6, mats=[aco])
    cortar_meio(cab, sec)
    cortar_meio(tampa_v, sec)
    objs += [cab, tampa_v, vela_cer, vela_aco] + valvulas

    # ---------- cárter (chapa) + óleo
    carter = caixa(nome + "_carter", -0.104, 0.104, -0.072, 0.072, z_carter, -0.050, [carter_m], chanfro=0.010, segs=4)
    flange = caixa(nome + "_flange", -0.110, 0.110, -0.078, 0.078, -0.058, -0.050, [carter_m], chanfro=0.002)
    booleano(carter, flange, "UNION")
    booleano(carter, caixa("_ci", -0.098, 0.098, -0.066, 0.066, z_carter + 0.005, -0.040, chanfro=0.007))
    cortar_meio(carter, sec)
    objs.append(carter)
    z_oleo0 = z_carter + 0.005
    z_oleo1 = z_oleo0 + nivel_oleo * (-0.050 - z_oleo0)
    oleo_ob = caixa(nome + "_oleo", -0.0978, 0.0978, -0.0658, 0.0658, z_oleo0 + 0.0002, z_oleo1, [oleo], chanfro=0.0068, segs=4)
    cortar_meio(oleo_ob, oleo)
    for f in oleo_ob.data.polygons:
        f.use_smooth = False
    objs.append(oleo_ob)
    # pescador de óleo (tubo) mergulhado
    pesc = cilindro(nome + "_pescador", 0.006, (0.06, 0.03, z_oleo0 + 0.012), (0.06, 0.03, -0.045), segs=24, mats=[aco])
    pesc2 = cilindro(nome + "_pescador_b", 0.016, (0.06, 0.03, z_oleo0 + 0.006), (0.06, 0.03, z_oleo0 + 0.014), segs=32, mats=[aco])
    objs += [pesc, pesc2]

    # ---------- virabrequim (inteiro): munhões, braços com contrapeso, moente
    vira = []
    vira.append(cilindro(nome + "_munhao_f", 0.0245, (0, -0.052, 0), (0, -0.030, 0), segs=64, mats=[aco_pol]))
    vira.append(cilindro(nome + "_munhao_t", 0.0245, (0, 0.030, 0), (0, 0.110, 0), segs=64, mats=[aco_pol]))
    vira.append(cilindro(nome + "_moente", 0.0215, (pino_v[0], -0.013, pino_v[1]), (pino_v[0], 0.013, pino_v[1]), segs=64, mats=[aco_pol]))
    ang_pino = math.atan2(pino_v[1], pino_v[0])
    contorno = []
    contorno += _circulo(0, 0, 0.068, 40, ang_pino + math.pi - 1.25, ang_pino + math.pi + 1.25)
    contorno += _circulo(pino_v[0], pino_v[1], 0.029, 32)
    contorno += _circulo(0, 0, 0.031, 32)
    contorno = _casco_convexo([(round(x, 6), round(z, 6)) for x, z in contorno])
    for y0, y1 in ((-0.030, -0.0135), (0.0135, 0.030)):
        br = extrudar_xz(f"{nome}_braco", contorno, y0, y1, [aco])
        chanfrar(br, 0.0025, 2)
        vira.append(br)
    objs += vira

    # ---------- biela (inteira) e pistão (inteiro, com anéis)
    pino_p = (0.0, z_pino)
    cont_b = _casco_convexo([(round(x, 6), round(z, 6)) for x, z in
                             _circulo(pino_v[0], pino_v[1], 0.034, 40) + _circulo(*pino_p, 0.0165, 32)])
    biela = extrudar_xz(nome + "_biela", cont_b, -0.011, 0.011, [aco])
    # alívio em "I" nas duas faces
    dirb = Vector((pino_p[0] - pino_v[0], pino_p[1] - pino_v[1])).normalized()
    perp = Vector((-dirb.y, dirb.x))
    c0 = Vector(pino_v) + dirb * 0.048
    c1 = Vector(pino_p) - dirb * 0.030
    rec = [tuple(c0 + perp * 0.0105), tuple(c1 + perp * 0.0065), tuple(c1 - perp * 0.0065), tuple(c0 - perp * 0.0105)]
    for y0, y1 in ((-0.02, -0.0065), (0.0065, 0.02)):
        cut = extrudar_xz("_rebaixo", rec, y0, y1)
        chanfrar(cut, 0.002, 2)
        booleano(biela, cut)
    chanfrar(biela, 0.0015, 2)
    # parafusos da capa
    for s in (-1, 1):
        pc = Vector(pino_v) + perp * (0.0255 * s) - dirb * 0.002
        objs.append(cilindro(f"{nome}_paraf{s}", 0.0042, (pc.x, -0.0125, pc.y), (pc.x, 0.0125, pc.y), segs=6, mats=[aco_esc]))
    objs.append(biela)

    hp = 0.066
    perfil_p = [(z_coroa - hp, 0.0), (z_coroa - hp, rcil - 0.0012), (z_coroa - 0.026, rcil - 0.0006)]
    # canaletas dos anéis
    zs_aneis = [z_coroa - 0.0065, z_coroa - 0.0115, z_coroa - 0.0170]
    for zr in sorted(zs_aneis):
        perfil_p += [(zr - 0.0011, rcil - 0.0004), (zr - 0.0011, rcil - 0.0035), (zr + 0.0011, rcil - 0.0035),
                     (zr + 0.0011, rcil - 0.0004)]
    perfil_p += [(z_coroa - 0.0012, rcil - 0.0006), (z_coroa, rcil - 0.0022), (z_coroa - 0.0018, 0.012), (z_coroa - 0.0018, 0.0)]
    pistao = revolver(nome + "_pistao", perfil_p, eixo="Z", segs=128, mats=[alu_pist], suave=30)
    booleano(pistao, caixa("_saia", -0.06, 0.06, -0.026, 0.026, z_coroa - hp - 0.01, z_pino + 0.006, chanfro=0.004))
    # rebaixo lateral do pino (bossa)
    for s in (-1, 1):
        booleano(pistao, cilindro("_bossa", 0.0125, (0, s * 0.045, z_pino), (0, s * 0.036, z_pino), segs=48))
    objs.append(pistao)
    pino_pist = cilindro(nome + "_pino", 0.0115, (0, -0.0385, z_pino), (0, 0.0385, z_pino), segs=48, mats=[aco_pol])
    objs.append(pino_pist)
    aneis = []
    for i, zr in enumerate(zs_aneis):
        alt = 0.0019 if i < 2 else 0.0021
        an = revolver(f"{nome}_anel{i}", [(zr - alt / 2, rcil - 0.0031), (zr - alt / 2, rcil - 0.0001),
                                          (zr + alt / 2, rcil - 0.0001), (zr + alt / 2, rcil - 0.0031)],
                      eixo="Z", segs=128, mats=[aco_esc if i < 2 else aco], suave=30)
        aneis.append(an)
    objs += aneis

    pai = bpy.data.objects.new(nome, None)
    bpy.context.scene.collection.objects.link(pai)
    for o in objs:
        o.parent = pai
    pai.location = (loc[0], loc[1], loc[2] - z_carter)
    pai.rotation_euler = (0, 0, math.radians(yaw))
    bpy.context.view_layer.update()
    mw = pai.matrix_world

    def W(x, y, z):
        return tuple(mw @ Vector((x, y, z)))
    ang_a = math.radians(-125)
    anc = {
        "aneis": W(rcil * math.cos(ang_a), rcil * math.sin(ang_a), zs_aneis[1]),
        "aneis_esq": W(-rcil * 0.98, -0.006, zs_aneis[1]),
        "oleo": W(0.060, -0.0005, (z_oleo0 + z_oleo1) / 2),
        "pistao": W(0.0, -rcil, z_coroa - 0.035),
        "biela": W((pino_v[0] + pino_p[0]) / 2, -0.011, (pino_v[1] + pino_p[1]) / 2),
        "vira": W(0, -0.150, 0),
        "camara": W(0, -0.0005, zc + 0.012),
        "topo": W(0, 0, zc + 0.122),
        "base": W(0, 0, z_carter),
        "centro": W(0, 0, (z_carter + zc + 0.122) / 2),
    }
    paraf = [o for o in objs if "_paraf" in o.name]
    loc_anc = {"aneis": Vector((rcil * math.cos(ang_a), rcil * math.sin(ang_a), zs_aneis[1])),
               "oleo": Vector((0.060, -0.0005, (z_oleo0 + z_oleo1) / 2))}
    return {"pai": pai, "objs": objs, "ancoras": anc, "z_coroa": z_coroa, "z_oleo": (z_oleo0, z_oleo1),
            "grupos": {"vira": vira, "biela": [biela] + paraf, "pistao": [pistao, pino_pist] + aneis},
            "geo": {"rv": rv, "Lb": Lb, "phi0": phi, "pino_v": pino_v, "z_pino": z_pino},
            "loc_anc": loc_anc}


def motor_pose(mt, ang_vira):
    """Gira o virabrequim para 'ang_vira' (graus a partir do PMS) e leva biela e pistão junto (cinemática real
    biela-manivela). Devolve as âncoras de mundo atualizadas ("aneis" anda com o pistão)."""
    g = mt["geo"]
    rv, Lb, phi0 = g["rv"], g["Lb"], g["phi0"]
    phi = math.radians(ang_vira)
    B0 = Vector((g["pino_v"][0], g["pino_v"][1]))
    S0 = Vector((0.0, g["z_pino"]))
    B1 = Vector((rv * math.sin(phi), rv * math.cos(phi)))
    S1 = Vector((0.0, rv * math.cos(phi) + math.sqrt(Lb ** 2 - (rv * math.sin(phi)) ** 2)))
    Rv = Matrix.Rotation(phi - phi0, 4, "Y")
    for o in mt["grupos"]["vira"]:
        o.matrix_basis = Rv
    a_old = math.atan2(S0.y - B0.y, S0.x - B0.x)
    a_new = math.atan2(S1.y - B1.y, S1.x - B1.x)
    Mb = (Matrix.Translation((B1.x, 0, B1.y)) @ Matrix.Rotation(-(a_new - a_old), 4, "Y")
          @ Matrix.Translation((-B0.x, 0, -B0.y)))
    for o in mt["grupos"]["biela"]:
        o.matrix_basis = Mb
    Mp = Matrix.Translation((0, 0, S1.y - S0.y))
    for o in mt["grupos"]["pistao"]:
        o.matrix_basis = Mp
    bpy.context.view_layer.update()
    mw = mt["pai"].matrix_world
    return {"aneis": tuple(mw @ (Mp @ mt["loc_anc"]["aneis"])), "oleo": tuple(mw @ mt["loc_anc"]["oleo"])}


def _ceramica():
    m, b = _principled("ceramica")
    b.inputs["Base Color"].default_value = lin("#ECEFF2")
    b.inputs["Roughness"].default_value = 0.18
    return m


def _mola(nome, base, eixo, r, alt, voltas, mat):
    """Mola helicoidal (tubo) ao longo de 'eixo' a partir de 'base'."""
    cu = bpy.data.curves.new(nome, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0016
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    n = voltas * 24
    sp.points.add(n)
    for i in range(n + 1):
        t = i / n
        a = 2 * math.pi * voltas * t
        sp.points[i].co = (r * math.cos(a), r * math.sin(a), alt * t, 1)
    ob = bpy.data.objects.new(nome, cu)
    bpy.context.scene.collection.objects.link(ob)
    cu.materials.append(mat)
    q = Vector(eixo).to_track_quat("Z", "Y")
    ob.matrix_world = Matrix.Translation(Vector(base)) @ q.to_matrix().to_4x4()
    return ob


# ============================================================ CALLOUT
def callout(ancora, cam, dx=0.2, dy=0.15, compr=0.15, cor=CIANO, espessura=0.0016, bolinha=0.006,
            etiqueta3d=None, nome="callout", sentido=None):
    """Linha de chamada: bolinha na âncora -> diagonal -> trecho horizontal (no plano da câmera).
    dx, dy: deslocamento do cotovelo em metros, nos eixos direita/cima da câmera (mesma profundidade da âncora).
    compr: comprimento do trecho horizontal (sinal segue dx).
    etiqueta3d: texto opcional em 3D (FONT) sobre o trecho horizontal; normalmente o texto vai em pós (PIL),
    posicionado com projetar(resultado["fim"]) e projetar(resultado["cotovelo"]).
    Retorna dict {"ancora", "cotovelo", "fim", "objs"}."""
    mr = cam.matrix_world.to_3x3()
    dir_d = mr @ Vector((1, 0, 0))
    dir_c = mr @ Vector((0, 1, 0))
    a = Vector(ancora)
    cot = a + dir_d * dx + dir_c * dy
    sentido = sentido if sentido is not None else (1 if dx >= 0 else -1)
    fim = cot + dir_d * (compr * sentido)
    m = mat_emissivo(cor, 5.0, nome + "_mat")
    cu = bpy.data.curves.new(nome, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = espessura
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(2)
    for i, p in enumerate((a, cot, fim)):
        sp.points[i].co = (p.x, p.y, p.z, 1)
    cu.materials.append(m)
    lin_ob = bpy.data.objects.new(nome, cu)
    bpy.context.scene.collection.objects.link(lin_ob)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=bolinha, location=a, segments=24, ring_count=12)
    bol = bpy.context.active_object
    bol.name = nome + "_bolinha"
    bol.data.materials.append(m)
    bol.data.shade_smooth()
    # anel externo (halo) em volta da bolinha, virado para a câmera
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=bolinha * 2.1, location=a, fill_type="NOTHING")
    hal = bpy.context.active_object
    hal.name = nome + "_halo"
    hal.rotation_euler = cam.matrix_world.to_euler()
    aplicar_mods_curva_circulo(hal, espessura * 0.8)
    hal.data.materials.clear()
    hal.data.materials.append(m)
    objs = [lin_ob, bol, hal]
    for o in objs:
        o.visible_shadow = False
        o.visible_glossy = False
        o.visible_diffuse = False
    if etiqueta3d:
        td = bpy.data.curves.new(nome + "_txt", "FONT")
        td.body = etiqueta3d
        td.size = 0.03
        to = bpy.data.objects.new(nome + "_txt", td)
        bpy.context.scene.collection.objects.link(to)
        to.location = fim if dx < 0 else cot
        to.rotation_euler = cam.matrix_world.to_euler()
        td.materials.append(m)
        objs.append(to)
    return {"ancora": tuple(a), "cotovelo": tuple(cot), "fim": tuple(fim), "objs": objs}


def callout_tela(ancora, cam, cotovelo, fim_x, frente=0.75, cor=CIANO, esp_px=2.4, bolinha_px=7.0,
                 nome="callout"):
    """Callout com o cotovelo e a ponta dados em PIXELS da imagem final (mais fácil de diagramar em 9:16).
    cotovelo = (x, y) em px; fim_x = x da ponta em px. A bolinha fica na âncora (3D); o cotovelo e a ponta
    ficam no mesmo raio de visão, mas a 'frente' x a profundidade da âncora: na tela é igual, e assim a linha
    passa na frente do piso e das peças em vez de entrar nelas."""
    sc = bpy.context.scene
    W, H = sc.render.resolution_x, sc.render.resolution_y
    cd = cam.data
    mi = cam.matrix_world
    a = Vector(ancora)
    prof = -(mi.inverted() @ a).z
    sh = cd.sensor_height
    sw = sh * W / H

    def ponto(px, py, d):
        x = (px / W - 0.5) * sw / cd.lens * d
        y = (0.5 - py / H) * sh / cd.lens * d
        return mi @ Vector((x, y, -d))
    d2 = prof * frente
    cot = ponto(cotovelo[0], cotovelo[1], d2)
    fim = ponto(fim_x, cotovelo[1], d2)
    # espessura e bolinha medidas em px (base 1080 de largura), convertidas para metros na profundidade certa
    k = W / 1080
    mpp = sh / cd.lens / H
    ax, ay = projetar(a)
    a2 = ponto(ax, ay, prof * 0.97)                 # bolinha um tiquinho à frente da superfície
    esp = esp_px * k * mpp * d2 / 2
    bol = bolinha_px * k * mpp * prof * 0.97
    return _linha_callout([a2, cot, fim], cam, cor, esp, bol, nome)


def _linha_callout(pts, cam, cor, espessura, bolinha, nome):
    m = mat_emissivo(cor, 5.0, nome + "_mat")
    cu = bpy.data.curves.new(nome, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = espessura
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p.x, p.y, p.z, 1)
    cu.materials.append(m)
    lin_ob = bpy.data.objects.new(nome, cu)
    bpy.context.scene.collection.objects.link(lin_ob)
    a = pts[0]
    bpy.ops.mesh.primitive_uv_sphere_add(radius=bolinha, location=a, segments=24, ring_count=12)
    bol = bpy.context.active_object
    bol.name = nome + "_bolinha"
    bol.data.materials.append(m)
    bol.data.shade_smooth()
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=bolinha * 2.1, location=a, fill_type="NOTHING")
    hal = bpy.context.active_object
    hal.name = nome + "_halo"
    hal.rotation_euler = cam.matrix_world.to_euler()
    aplicar_mods_curva_circulo(hal, espessura * 0.8)
    hal.data.materials.clear()
    hal.data.materials.append(m)
    objs = [lin_ob, bol, hal]
    for o in objs:
        o.visible_shadow = False
        o.visible_glossy = False
        o.visible_diffuse = False
    return {"ancora": tuple(a), "cotovelo": tuple(pts[1]), "fim": tuple(pts[-1]), "objs": objs}


def aplicar_mods_curva_circulo(ob, esp):
    """Troca o círculo (só arestas) por um tubo fino: converte para curva com bevel."""
    ob.modifiers.clear()
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="CURVE")
    ob.data.bevel_depth = esp
    ob.data.bevel_resolution = 2
    ob.select_set(False)
    return ob


# ============================================================ CORRENTE DE MOTO (transmissão secundária)
PASSO_520 = 0.015875          # corrente 520: passo 5/8"


def _coroa_perfil(N, p, rolete=0.0051, gasto=0.0, n_amostra=None):
    """Contorno 2D (x, z) de coroa/pinhão com N dentes. Raio de assento = N*p/(2*pi) (assim os roletes
    espaçados de p no arco caem exatamente nos vales). gasto (0..1): dente "barbatana de tubarão" —
    ponta puxada para um lado, mais baixa e afinada, vale alargado."""
    R = N * p / (2 * math.pi)
    n_amostra = n_amostra or N * 24
    us = np.linspace(0, 1, n_amostra, endpoint=False)
    pts = []
    h = 0.62 * p * (1 - 0.18 * gasto)                 # altura do dente acima do assento
    for u in us:
        k = u * N
        f = k - math.floor(k)                          # 0 = vale (assento), 0.5 = ponta
        # vale: arco do rolete (alargado se gasto)
        larg_vale = 0.21 + 0.07 * gasto
        ponta = 0.5 + 0.13 * gasto                     # ponta deslocada (gancho)
        if f < larg_vale or f > 1 - larg_vale:
            g = f if f < 0.5 else f - 1
            x = g / larg_vale
            r = R - rolete * 0.95 * math.sqrt(max(0.0, 1 - x * x)) + rolete * 0.05
        else:
            if f < ponta:
                t = (f - larg_vale) / (ponta - larg_vale)
            else:
                t = (1 - larg_vale - f) / (1 - larg_vale - ponta)
            t = max(0.0, min(1.0, t))
            forma = math.sin(t * math.pi / 2) ** (0.9 if gasto < 0.5 else 0.6)
            if gasto < 0.5:
                forma = min(forma, 0.86) / 0.86            # dente sadio: topo chato
            r = R + 0.05 * rolete + h * forma
        a = 2 * math.pi * u
        pts.append((r * math.sin(a), r * math.cos(a)))
    return pts, R


def _engrenagem(nome, N, p, esp, mats, gasto=0.0, furos=5, r_cubo=None, chanfro=0.0008):
    pts, R = _coroa_perfil(N, p, gasto=gasto)
    ob = extrudar_xz(nome, pts, -esp / 2, esp / 2, mats, suave=25)
    if furos and R > 0.06:
        for k in range(furos):
            a = 2 * math.pi * (k + 0.5) / furos
            cont = []
            r0, r1 = R * 0.42, R * 0.70
            for j in range(16):
                aa = a - 0.30 + 0.60 * j / 15
                cont.append((r1 * math.sin(aa), r1 * math.cos(aa)))
            for j in range(16):
                aa = a + 0.20 - 0.40 * j / 15
                cont.append((r0 * math.sin(aa), r0 * math.cos(aa)))
            cut = extrudar_xz("_furo", cont, -esp, esp)
            chanfrar(cut, 0.004, 3, angulo=30)
            booleano(ob, cut)
    r_cubo = r_cubo or min(0.028, R * 0.3)
    booleano(ob, cilindro("_bore", r_cubo * 0.55, (0, -esp, 0), (0, esp, 0), segs=48))
    chanfrar(ob, chanfro, 1, angulo=30)
    # faces planas (as duas faces da chapa) sempre chapadas: sem estrias de sombreamento nos n-gons
    me = ob.data
    nor = np.zeros(len(me.polygons) * 3); me.polygons.foreach_get("normal", nor)
    sm = np.abs(nor.reshape(-1, 3)[:, 1]) < 0.98
    me.polygons.foreach_set("use_smooth", sm)
    me.update()
    return ob, R


def _caminho_corrente(r1, r2, D):
    """Caminho aberto entre o pinhão (centro 0,0, raio r1) e a coroa (centro D,0, raio r2) em (x, z).
    Devolve função s -> (ponto, tangente) e o comprimento total. Começa no ponto tangente de cima do pinhão
    e segue para a coroa (sentido horário na vista)."""
    nx = (r2 - r1) / D
    sz = math.sqrt(1 - nx * nx)
    P1t = Vector((-r1 * nx, r1 * sz)); P2t = Vector((D - r2 * nx, r2 * sz))
    P2b = Vector((D - r2 * nx, -r2 * sz)); P1b = Vector((-r1 * nx, -r1 * sz))
    a2t = math.atan2(sz, -nx); a2b = math.atan2(-sz, -nx)
    span2 = a2t - a2b
    span1 = 2 * math.pi - span2
    L1 = (P2t - P1t).length
    segs = [("lin", P1t, P2t, L1), ("arc2", a2t, -span2, r2 * span2), ("lin", P2b, P1b, L1),
            ("arc1", a2b, -span1, r1 * span1)]
    total = sum(sg[3] for sg in segs)

    def em(s_):
        s_ = s_ % total
        for tipo, A, B, Ls in segs:
            if s_ <= Ls:
                t = s_ / Ls
                if tipo == "lin":
                    return A.lerp(B, t), "lin_cima" if A is P1t else "lin_baixo", t
                ang = A + B * t
                c = Vector((D, 0)) if tipo == "arc2" else Vector((0, 0))
                r = r2 if tipo == "arc2" else r1
                return c + Vector((math.cos(ang), math.sin(ang))) * r, tipo, t
            s_ -= Ls
        return P1t, "lin_cima", 0.0
    return em, total


def _instancias(nome, molde_vs, molde_fs, mats_idx, matrizes, mats):
    """Junta várias cópias transformadas de uma malha-molde (lista de vértices/faces) num objeto só."""
    V = np.array(molde_vs, dtype=float)
    Vh = np.c_[V, np.ones(len(V))]
    vs, fs, mi = [], [], []
    for Mx in matrizes:
        A = np.array(Mx)
        base = len(vs)
        vs.extend((Vh @ A.T)[:, :3].tolist())
        fs.extend([[base + i for i in f] for f in molde_fs])
        mi.extend(mats_idx)
    ob = malha(nome, vs, fs, mats, mi, suave=35)
    return ob


def _molde_de(ob):
    me = ob.data
    vs = [tuple(v.co) for v in me.vertices]
    fs = [list(pg.vertices) for pg in me.polygons]
    mi = [pg.material_index for pg in me.polygons]
    bpy.data.objects.remove(ob, do_unlink=True)
    return vs, fs, mi


def mat_aco_lubrificado(nome="aco_lub", tinta="#FAEACB"):
    """Aço polido com película de óleo (coat; 'tinta' = cor da película, âmbar onde o óleo acumula)."""
    m, b = _principled(nome)
    b.inputs["Base Color"].default_value = lin("#B8C0C9")
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.16
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.03
    b.inputs["Coat Tint"].default_value = lin(tinta)
    b.inputs["Coat IOR"].default_value = 1.47
    return m


def mat_aco_enferrujado(nome="aco_ferrugem", quanto=0.65, base="#7C848D"):
    """Aço seco e fosco com manchas de ferrugem laranja-marrom (ruído em 2 escalas)."""
    m, b = _principled(nome)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    tcn = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 45.0
    nz.inputs["Detail"].default_value = 8.0
    nz.inputs["Roughness"].default_value = 0.65
    L.new(tcn.outputs["Object"], nz.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.62 - 0.25 * quanto
    mr.inputs["From Max"].default_value = 0.70 - 0.25 * quanto
    L.new(nz.outputs["Fac"], mr.inputs["Value"])
    nz2 = N.new("ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value = 900.0
    L.new(tcn.outputs["Object"], nz2.inputs["Vector"])
    ru = N.new("ShaderNodeMix"); ru.data_type = "RGBA"
    _sock(ru, "A").default_value = lin("#341A0C")
    _sock(ru, "B").default_value = lin("#5E2C12")
    L.new(nz2.outputs["Fac"], _sock(ru, "Factor", "VALUE"))
    cm = N.new("ShaderNodeMix"); cm.data_type = "RGBA"
    _sock(cm, "A").default_value = lin(base)
    L.new([o for o in ru.outputs if o.type == "RGBA"][0], _sock(cm, "B"))
    L.new(mr.outputs["Result"], _sock(cm, "Factor", "VALUE"))
    L.new([o for o in cm.outputs if o.type == "RGBA"][0], b.inputs["Base Color"])
    inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 0.85
    L.new(mr.outputs["Result"], inv.inputs[1])
    L.new(inv.outputs[0], b.inputs["Metallic"])
    rg = N.new("ShaderNodeMapRange")
    rg.inputs["To Min"].default_value = 0.55; rg.inputs["To Max"].default_value = 0.9
    L.new(mr.outputs["Result"], rg.inputs["Value"])
    L.new(rg.outputs["Result"], b.inputs["Roughness"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35
    bp.inputs["Distance"].default_value = 0.0003
    L.new(nz2.outputs["Fac"], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def corrente_moto(nome, loc=(0, 0, 0), estado="lubrificada", dentes=(14, 40), entre_eixos=0.30,
                  yaw=0.0, inclina=0.0, passo=PASSO_520):
    """Pinhão + coroa + corrente de rolos 520 (elos internos e externos, pinos rebitados, roletes).
    Plano da transmissão = XZ local (eixos ao longo de Y); pinhão em x = 0, coroa em x = +entre_eixos.
    estado: "lubrificada" (aço brilhante com película âmbar, corrente justa) ou
            "seca" (fosca, ferrugem laranja-marrom, elos esticados ~3 %, folga/barriga no ramo de baixo,
            roletes subindo nos dentes da coroa e dentes gastos em "barbatana").
    Retorna dict(pai, objs, ancoras, info)."""
    seca = estado == "seca"
    n1, n2 = dentes
    p = passo
    if seca:
        m_corr = M("aco_ferrugem", lambda: mat_aco_enferrujado("aco_ferrugem", 0.75, "#4F555C"))
        m_rol = M("aco_ferrugem2", lambda: mat_aco_enferrujado("aco_ferrugem2", 0.95, "#43484E"))
        m_eng = M("aco_ferr_eng", lambda: mat_aco_enferrujado("aco_ferr_eng", 0.35, "#5D646B"))
    else:
        m_corr = M("aco_lub", lambda: mat_aco_lubrificado("aco_lub", "#FFFFFF"))
        m_rol = M("aco_lub_rol", lambda: mat_aco_lubrificado("aco_lub_rol", "#E6A93E"))
        m_eng = M("aco_eng", lambda: mat_metal("#7F8892", 0.26, "aco_eng"))
    m_pino = M("aco_pino_" + estado, lambda: mat_metal("#D0D6DC" if not seca else "#6F757C", 0.18 if not seca else 0.6,
                                                        "aco_pino_" + estado))
    objs = []
    gasto = 0.85 if seca else 0.0
    pinhao, R1 = _engrenagem(nome + "_pinhao", n1, p, 0.0075, [m_eng], gasto=gasto * 0.6, furos=0)
    coroa, R2 = _engrenagem(nome + "_coroa", n2, p, 0.0070, [m_eng], gasto=gasto, furos=5)
    coroa.data.transform(Matrix.Translation((entre_eixos, 0, 0)))
    objs += [pinhao, coroa]
    # cubo/eixo de saída e cubo da roda (simples)
    objs.append(cilindro(nome + "_eixo", 0.011, (0, -0.03, 0), (0, 0.03, 0), segs=6, mats=[m_pino]))
    objs.append(cilindro(nome + "_cubo", 0.034, (entre_eixos, 0.004, 0), (entre_eixos, 0.03, 0), segs=48,
                         mats=[M("alu_cubo", lambda: mat_metal("#8E97A1", 0.35, "alu_cubo"))]))
    for k in range(5):
        a = 2 * math.pi * k / 5
        x, z = entre_eixos + 0.024 * math.sin(a), 0.024 * math.cos(a)
        objs.append(cilindro(f"{nome}_paraf{k}", 0.0042, (x, -0.0055, z), (x, 0.031, z), segs=6, mats=[m_pino]))

    # caminho dos roletes: seca = elos esticados -> roletes sobem nos dentes (raio maior) e passo maior
    folga_r = 0.0026 if seca else 0.0
    pe = p * (1.03 if seca else 1.0)
    em, total = _caminho_corrente(R1 + folga_r * 0.5, R2 + folga_r, entre_eixos)
    nel = int(round(total / pe))
    if nel % 2:
        nel += 1
    pe = total / nel
    barriga = 0.030 if seca else 0.0015
    pts = []
    for k in range(nel):
        q, tipo, t = em(k * pe)
        q = Vector(q)
        if tipo == "lin_baixo":
            q.y -= barriga * math.sin(math.pi * t)                 # ramo de baixo "barrigudo"
        pts.append(q)
    # moldes: placa interna, placa externa, rolete, pino
    def placa(nome_, r_olho, cintura, esp, y):
        cont = []
        for cx, a0, a1 in ((0.0, math.pi / 2, 3 * math.pi / 2), (p, -math.pi / 2, math.pi / 2)):
            for j in range(17):
                a = a0 + (a1 - a0) * j / 16
                cont.append((cx + r_olho * math.cos(a), r_olho * math.sin(a)))
            # cintura (lado de baixo/cima)
            if cx == 0.0:
                cont.append((p / 2, -cintura))
            else:
                cont.append((p / 2, cintura))
        ob = extrudar_xz(nome_, cont, y - esp / 2, y + esp / 2, suave=30)
        chanfrar(ob, 0.00035, 1, angulo=30)
        return ob
    yi, ye = 0.0040, 0.0058                     # meia-largura: placas internas / externas
    molde_int = []
    for sy in (-1, 1):
        molde_int.append(placa("_pi", 0.0071, 0.0060, 0.0015, sy * yi))
    ob_r = cilindro("_rol", 0.0050, (0, -yi + 0.0008, 0), (0, yi - 0.0008, 0), segs=20)
    ob_r2 = cilindro("_rol2", 0.0050, (p, -yi + 0.0008, 0), (p, yi - 0.0008, 0), segs=20)
    molde_ext = [placa("_pe", 0.0071, 0.0064, 0.0015, sy * ye) for sy in (-1, 1)]
    pinos = [cilindro("_pino", 0.0026, (cx, -ye - 0.0013, 0), (cx, ye + 0.0013, 0), segs=14) for cx in (0.0, p)]
    mi_ = juntar(molde_int, "_mi"); mr_ = juntar([ob_r, ob_r2], "_mr")
    me_ = juntar(molde_ext, "_me"); mp_ = juntar(pinos, "_mp")
    Vi, Fi, _ = _molde_de(mi_); Vr, Fr, _ = _molde_de(mr_)
    Ve, Fe, _ = _molde_de(me_); Vp, Fp, _ = _molde_de(mp_)
    mat_int, mat_ext = [], []
    for k in range(nel):
        a, b = pts[k], pts[(k + 1) % nel]
        d = b - a
        ang = math.atan2(d.y, d.x)
        esc = d.length / p
        Mx = (Matrix.Translation((a.x, 0, a.y)) @ Matrix.Rotation(-ang, 4, "Y")
              @ Matrix.Diagonal((esc, 1, 1, 1)))
        (mat_int if k % 2 == 0 else mat_ext).append(Mx)
    objs.append(_instancias(nome + "_placas_int", Vi, Fi, [0] * len(Fi), mat_int, [m_corr]))
    objs.append(_instancias(nome + "_roletes", Vr, Fr, [0] * len(Fr), mat_int, [m_rol]))
    objs.append(_instancias(nome + "_placas_ext", Ve, Fe, [0] * len(Fe), mat_ext, [m_corr]))
    objs.append(_instancias(nome + "_pinos", Vp, Fp, [0] * len(Fp), mat_ext, [m_pino]))

    pai = bpy.data.objects.new(nome, None)
    bpy.context.scene.collection.objects.link(pai)
    for o in objs:
        o.parent = pai
    pai.location = loc
    pai.rotation_euler = (math.radians(inclina), 0, math.radians(yaw))
    bpy.context.view_layer.update()
    mw = pai.matrix_world

    def W(x, y, z):
        return tuple(mw @ Vector((x, y, z)))
    # âncoras
    meio_baixo = min(range(nel), key=lambda k: (pts[k].x - entre_eixos * 0.5) ** 2 + (pts[k].y + 1) * 0)
    baixos = [k for k in range(nel) if pts[k].y < 0 and 0.25 * entre_eixos < pts[k].x < 0.75 * entre_eixos]
    kb = min(baixos, key=lambda k: abs(pts[k].x - entre_eixos * 0.5)) if baixos else 0
    cimas = [k for k in range(nel) if pts[k].y > 0 and 0.3 * entre_eixos < pts[k].x < 0.7 * entre_eixos]
    kc = min(cimas, key=lambda k: abs(pts[k].x - entre_eixos * 0.45)) if cimas else 0
    a_d = math.radians(-112)                                     # dente exposto, do lado do pinhão
    r_tip = R2 + 0.6 * p
    anc = {
        "ramo_baixo": W(pts[kb].x + p / 2, -ye - 0.001, pts[kb].y),
        "ramo_cima": W(pts[kc].x + p / 2, -ye - 0.001, pts[kc].y),
        "dente": W(entre_eixos + r_tip * math.sin(a_d), -0.004, r_tip * math.cos(a_d)),
        "coroa": W(entre_eixos + R2 * 0.55 * math.sin(math.radians(200)), -0.004, R2 * 0.55 * math.cos(math.radians(200))),
        "pinhao": W(0, -0.008, 0),
        "centro": W(entre_eixos / 2, 0, 0),
        "topo": W(entre_eixos / 2, 0, R2 + 0.02),
        "esq": W(-R1 - 0.02, 0, 0), "dir": W(entre_eixos + R2 + 0.02, 0, 0),
    }
    return {"pai": pai, "objs": objs, "ancoras": anc,
            "info": {"elos": nel, "passo_efetivo": pe, "R1": R1, "R2": R2}}


# ============================================================ RAIO-X DO CARRO
def carro_raio_x(nome="carro", tipo="hatch", loc=(0, 0, 0), yaw=-30.0, opac=0.15, cor=RAIO_X, trem=True):
    """Carro 'real' de veiculos3 (não editado aqui: só importado) com a lataria trocada por raio-X ciano
    (Fresnel, ~15 %), deixando ver um trem de força simplificado (motor transversal + câmbio + semi-eixos,
    radiador, escapamento, tanque e bancos) e as rodas. Escala 1:1 (metros reais)."""
    import veiculos3 as v3
    Mv = {}
    D = v3.carro(nome, Mv, tipo, "prata", estilo="real", escala=1.0)
    rx = mat_raio_x(cor, opac, nome + "_raio_x")
    rodas = set()
    for r in D["rodas"]:
        rodas.add(r.name)
        for c in r.children_recursive:
            rodas.add(c.name)

    def troca(o):
        if o.name in rodas or o.type not in ("MESH", "CURVE"):
            return
        me = o.data
        for i in range(len(me.materials)):
            me.materials[i] = rx
        if not me.materials:
            me.materials.append(rx)
        o.visible_shadow = False
    for o in D["raiz"].children_recursive:
        troca(o)
    s = D["spec"]
    xf = s.get("xf", s["wb"] / 2)
    R = s["R"]
    objs = []
    if trem:
        alu = M("rx_alu", lambda: mat_metal("#A7AFB8", 0.33, "rx_alu"))
        aco = M("rx_aco", lambda: mat_metal(ACO, 0.3, "rx_aco"))
        preto = M("rx_preto", lambda: mat_pintura("#1A1D22", "rx_preto"))
        laranja = M("rx_motor", lambda: mat_pintura(LARANJA, "rx_motor"))
        # motor 4 cil. transversal (ao longo de y), um pouco à frente do eixo dianteiro
        xm, zm = xf + 0.20, R + 0.22
        bloco = caixa(nome + "_bloco", xm - 0.17, xm + 0.13, -0.30, 0.22, zm - 0.20, zm + 0.16, [alu], chanfro=0.02)
        cabec = caixa(nome + "_cabec", xm - 0.16, xm + 0.11, -0.29, 0.21, zm + 0.16, zm + 0.27, [alu], chanfro=0.015)
        tampa = caixa(nome + "_tampa", xm - 0.12, xm + 0.08, -0.27, 0.19, zm + 0.27, zm + 0.33, [laranja], chanfro=0.025, segs=4)
        carter = caixa(nome + "_carter", xm - 0.15, xm + 0.11, -0.28, 0.20, zm - 0.32, zm - 0.20, [preto], chanfro=0.02)
        objs += [bloco, cabec, tampa, carter]
        for k in range(4):                               # coletor de admissão
            y = -0.22 + 0.13 * k
            objs.append(cilindro(f"{nome}_adm{k}", 0.022, (xm - 0.16, y, zm + 0.20), (xm - 0.30, y, zm + 0.08), segs=24, mats=[alu]))
        objs.append(cilindro(nome + "_plenum", 0.045, (xm - 0.31, -0.28, zm + 0.06), (xm - 0.31, 0.20, zm + 0.06), segs=32, mats=[alu]))
        # câmbio (lado esquerdo do motor, +y) e semi-eixos até as rodas
        cambio = revolver(nome + "_cambio", [(0.0, 0.0), (0.0, 0.17), (0.08, 0.16), (0.20, 0.11), (0.30, 0.10),
                                             (0.30, 0.0)], eixo="Y", segs=48, mats=[alu], centro=(xm - 0.02, 0.22, zm - 0.06))
        objs.append(cambio)
        yr = s["W"] - 0.12
        for sy in (-1, 1):
            objs.append(cilindro(f"{nome}_semieixo{sy}", 0.016, (xf, sy * 0.05, R), (xf, sy * yr, R), segs=20, mats=[aco]))
        # radiador
        objs.append(caixa(nome + "_radiador", xm + 0.30, xm + 0.34, -0.36, 0.36, R - 0.05, R + 0.40,
                          [M("rx_rad", lambda: mat_metal("#59616B", 0.5, "rx_rad"))], chanfro=0.005))
        # escapamento: do motor por baixo até a traseira, com abafador
        xr = -s["wb"] / 2
        esc = [(xm - 0.05, -0.05, zm - 0.18), (xm - 0.20, -0.05, 0.22), (xf - 0.45, 0.0, 0.17), (xr + 0.3, 0.02, 0.17)]
        for a_, b_ in zip(esc[:-1], esc[1:]):
            objs.append(cilindro(nome + "_esc", 0.025, a_, b_, segs=20, mats=[aco]))
        objs.append(cilindro(nome + "_abafador", 0.09, (xr + 0.30, 0.02, 0.21), (xr - 0.25, 0.02, 0.21), segs=40, mats=[aco]))
        # tanque e bancos
        objs.append(caixa(nome + "_tanque", xr + 0.35, xr + 0.95, -0.40, 0.40, 0.20, 0.42, [preto], chanfro=0.05, segs=3))
        banco = M("rx_banco", lambda: mat_pintura("#2B3038", "rx_banco"))
        for xb, largura in ((0.05, 0.25), (-0.85, 0.62)):
            for sy in ((-1, 1) if largura < 0.5 else (0,)):
                yc = sy * 0.36
                objs.append(caixa(nome + "_assento", xb - 0.25, xb + 0.25, yc - largura, yc + largura, 0.36, 0.50, [banco], chanfro=0.04))
                objs.append(caixa(nome + "_encosto", xb - 0.30, xb - 0.18, yc - largura, yc + largura, 0.50, 1.10, [banco], chanfro=0.04))
        # volante
        bpy.ops.mesh.primitive_torus_add(major_radius=0.18, minor_radius=0.016, location=(0.62, -0.36, 0.95),
                                         rotation=(0, math.radians(-65), 0))
        vol = bpy.context.active_object
        vol.data.materials.append(preto)
        objs.append(vol)
        for o in objs:
            o.parent = D["raiz"]
    D["raiz"].location = loc
    D["raiz"].rotation_euler = (0, 0, math.radians(yaw))
    bpy.context.view_layer.update()
    mw = D["raiz"].matrix_world
    D["ancoras"] = {"motor": tuple(mw @ Vector((xf + 0.20, -0.30, R + 0.33))),
                    "cambio": tuple(mw @ Vector((xf + 0.10, 0.52, R + 0.10))),
                    "roda_d": tuple(mw @ Vector((xf, -s["W"] - 0.05, R))),
                    "escape": tuple(mw @ Vector((-s["wb"] / 2 - 0.2, 0.02, 0.21))),
                    "centro": tuple(mw @ Vector((0, 0, 0.7)))}
    D["trem"] = objs
    D["mat_raio_x"] = rx
    return D
