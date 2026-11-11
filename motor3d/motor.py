"""Motor de cenas 3D low-poly para vídeos explicativos verticais (Blender / bpy).

Reúne o que é igual em todo vídeo: configuração de render, materiais, peças geométricas,
terreno em corte, decoração, animações (pop, crescer, mover, chave de forma), céu/sol e câmeras.
Cada vídeo tem só o seu cena.py, que importa este módulo e descreve a história.
Tempos sempre em segundos (os mesmos do .srt).
"""
import bpy, bmesh, math, random, json
from mathutils import Vector, Matrix

try:
    import shapely.geometry as sg
    from shapely.ops import unary_union
except ImportError:  # terreno com recortes precisa de shapely
    sg = None

FPS = 24
scene = None


def F(t):
    return int(round(t * FPS)) + 1


# ================================================================ configuração
def setup(duration, fps=24, samples=4, res=(576, 1024)):
    """Render padrão = Cycles otimizado (teste de 30/10/2026: 2,9x mais rápido que 16 amostras, SSIM 0,994,
    sem cintilação visível). Use samples=8 se aparecerem manchas em cenas com muito vidro/brilho/noite."""
    global FPS, scene
    FPS = fps
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = F(duration)
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.engine = "CYCLES"
    scene.render.threads_mode = "AUTO"
    scene.render.use_persistent_data = True       # mantém a cena carregada entre um quadro e outro
    c = scene.cycles
    c.samples = samples
    c.use_adaptive_sampling = True
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    if hasattr(c, "denoising_quality"):          # 31/10/2026: "FAST" = 2,3x mais rápido, diferença invisível
        c.denoising_quality = "FAST"
        c.denoising_prefilter = "FAST"
    c.max_bounces = 3
    c.diffuse_bounces = 1
    c.glossy_bounces = 1
    c.transmission_bounces = 1
    c.volume_bounces = 0
    c.transparent_max_bounces = 4
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    if hasattr(c, "use_light_tree"):
        c.use_light_tree = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    random.seed(7)
    return scene


def save(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("salvo:", path)


# ================================================================ materiais
def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def mat(name, hexcol, rough=0.85, alpha=1.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexcol)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Emission Color"].default_value = lin(hexcol)
    b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def bsdf(m):
    return m.node_tree.nodes["Principled BSDF"]


def key_input(m, inp, t, value):
    s = bsdf(m).inputs[inp]
    s.default_value = value
    s.keyframe_insert("default_value", frame=F(t))


def glow(m, t0, t1, hexcol="#ffc928", peak=1.4, pulses=2):
    """Pisca o material (destaque amarelo) entre t0 e t1."""
    key_input(m, "Emission Color", t0, lin(hexcol))
    key_input(m, "Emission Strength", t0, 0.0)
    step = (t1 - t0) / (pulses * 2)
    for i in range(pulses):
        key_input(m, "Emission Strength", t0 + step * (2 * i + 1), peak)
        key_input(m, "Emission Strength", t0 + step * (2 * i + 2), 0.25 if i < pulses - 1 else 0.0)


def _coord_node(nt):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return tc.outputs["Object"]


def building_mat(name, wall="#e9e6df", win="#6c9ee0"):
    """Paredes com janelas (Brick Texture nas faces verticais)."""
    m = mat(name, wall)
    nt = m.node_tree
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Scale"].default_value = 0.42
    br.inputs["Mortar Size"].default_value = 0.11
    br.inputs["Color1"].default_value = lin(win)
    br.inputs["Color2"].default_value = lin(win)
    br.inputs["Mortar"].default_value = lin(wall)
    nt.links.new(_coord_node(nt), sep.inputs[0])
    nt.links.new(sep.outputs["X"], add.inputs[0])
    nt.links.new(sep.outputs["Y"], add.inputs[1])
    nt.links.new(add.outputs[0], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], bsdf(m).inputs["Base Color"])
    return m


def mosaic_mat(name, base="#6b5f52", scale=3.5, mix=0.6, sat=0.75, rough=0.8, val=0.85):
    """Mosaico de cores aleatórias (lixo misturado). Voronoi -> cor por célula."""
    m = mat(name, base, rough=rough)
    nt = m.node_tree
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = scale
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = sat
    hsv.inputs["Value"].default_value = val
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    sock(mx.inputs, "Factor", "VALUE").default_value = mix
    sock(mx.inputs, "A", "RGBA").default_value = lin(base)
    nt.links.new(_coord_node(nt), vor.inputs["Vector"])
    nt.links.new(vor.outputs["Color"], hsv.inputs["Color"])
    nt.links.new(hsv.outputs["Color"], sock(mx.inputs, "B", "RGBA"))
    nt.links.new(sock(mx.outputs, "Result", "RGBA"), bsdf(m).inputs["Base Color"])
    return m


def sock(sockets, name, typ):
    """Socket pelo nome E tipo (o nó Mix tem várias entradas 'A'/'B', uma por tipo)."""
    return next(s for s in sockets if s.name == name and s.type == typ)


def node_of(m, idname):
    return next(n for n in m.node_tree.nodes if n.bl_idname == idname)


def stones_mat(name, light="#b9b6ae", dark="#6d6a66", scale=5.0):
    """Pedras/brita: células claras com juntas escuras."""
    m = mat(name, light)
    nt = m.node_tree
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = scale
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = lin(dark)
    ramp.color_ramp.elements[1].position = 0.12
    ramp.color_ramp.elements[1].color = lin(light)
    nt.links.new(_coord_node(nt), vor.inputs["Vector"])
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf(m).inputs["Base Color"])
    return m


# ================================================================ geometria
def link(o):
    scene.collection.objects.link(o)
    return o


def mesh_obj(name, bm, m, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    for mm in (m if isinstance(m, list) else [m]):
        me.materials.append(mm)
    o.location = loc
    return link(o)


def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    return link(e)


def box_bm(bm, x0, x1, y0, y1, z0, z1, mat_index=0):
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((cx, cy, cz)) @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1)))
    for v in res["verts"]:
        for f in v.link_faces:
            f.material_index = mat_index
    return res


def box(name, x0, x1, y0, y1, z0, z1, m, anchor="bottom"):
    """Caixa com origem no centro da base (bottom), topo (top), centro (center) ou lado esquerdo (left)."""
    ox, oy = (x0 + x1) / 2, (y0 + y1) / 2
    oz = {"bottom": z0, "top": z1, "center": (z0 + z1) / 2, "left": (z0 + z1) / 2}[anchor]
    if anchor == "left":
        ox = x0
    bm = bmesh.new()
    box_bm(bm, x0 - ox, x1 - ox, y0 - oy, y1 - oy, z0 - oz, z1 - oz)
    return mesh_obj(name, bm, m, (ox, oy, oz))


def cyl(name, r, z0, z1, loc_xy, m, seg=16, anchor="bottom"):
    bm = bmesh.new()
    oz = z0 if anchor == "bottom" else z1
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=z1 - z0,
                          matrix=Matrix.Translation((0, 0, (z0 + z1) / 2 - oz)))
    return mesh_obj(name, bm, m, (loc_xy[0], loc_xy[1], oz))


def orient(o, direction):
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(direction).normalized())


def tube(name, p0, p1, r, m, seg=14):
    """Cilindro de p0 até p1 com origem em p0 (grow_z faz ele 'sair' de p0)."""
    p0, p1 = Vector(p0), Vector(p1)
    o = cyl(name, r, 0, (p1 - p0).length, (0, 0), m, seg=seg)
    o.location = p0
    orient(o, p1 - p0)
    return o


def ball(name, r, loc, m, sub=1, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r, matrix=Matrix.Diagonal((*scale, 1)))
    return mesh_obj(name, bm, m, loc)


def arrow(name, length, m, loc, direction=(0, 0, -1), r=0.12, head=0.35):
    """Seta com origem na ponta, apontando para `direction`."""
    bm = bmesh.new()
    hl = min(head * 2.2, length * 0.5)
    shaft = length - hl
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r, depth=shaft,
                          matrix=Matrix.Translation((0, 0, -hl - shaft / 2)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=head, radius2=0.0, depth=hl,
                          matrix=Matrix.Translation((0, 0, -hl / 2)) @ Matrix.Rotation(math.pi, 4, "X"))
    o = mesh_obj(name, bm, m, loc)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(direction).normalized())
    return o


def text(name, body, size, loc, m, rot=(math.pi / 2, 0, 0), align="CENTER", extrude=0.01):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.extrude = extrude
    o = bpy.data.objects.new(name, cu)
    o.data.materials.append(m)
    o.location = loc
    o.rotation_euler = rot
    return link(o)


# ---------------------------------------------------------------- prismas de perfil (corte x-z, extrudado em y)
def polys(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon" and g.area > 1e-6]


def ring(poly):
    p = poly.simplify(0.0005)
    return [(x, z) for x, z in list(p.exterior.coords)[:-1]]


def prism_bm(bm, pts, y0, y1):
    front = [bm.verts.new((x, y0, z)) for x, z in pts]
    back = [bm.verts.new((x, y1, z)) for x, z in pts]
    bm.faces.new(front)
    bm.faces.new(back[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([front[i], front[j], back[j], back[i]])


def prism(name, poly, y0, y1, m, origin=None, along=None):
    """Prisma a partir de um polígono no plano x-z (shapely ou lista de pontos).
    origin=(x,z) e along=(dx,dz): eixo local X fica alinhado a `along`, para crescer com scale.x."""
    pts = ring(poly) if hasattr(poly, "exterior") else list(poly)
    ox, oz = origin if origin else (0.0, 0.0)
    if along:
        d = Vector((along[0], along[1])).normalized()
        n = Vector((-d.y, d.x))
        pts = [((x - ox) * d.x + (z - oz) * d.y, (x - ox) * n.x + (z - oz) * n.y) for x, z in pts]
    else:
        pts = [(x - ox, z - oz) for x, z in pts]
    bm = bmesh.new()
    prism_bm(bm, pts, y0, y1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_obj(name, bm, m, (ox, 0, oz))
    if along:
        o.rotation_euler = (0, math.atan2(-d.y, d.x), 0)
    return o


def prism_fill(name, poly, y0, y1, m, zb):
    """Prisma que 'enche' de baixo para cima (chave de forma 'cheio').
    Os vértices acima de zb nascem colapsados na base e sobem pelas paredes inclinadas."""
    pts = ring(poly) if hasattr(poly, "exterior") else list(poly)
    o = prism(name, pts, y0, y1, m)
    me = o.data
    full = [v.co.copy() for v in me.vertices]
    base = [x for x, z in pts if abs(z - zb) < 1e-3]
    xmin, xmax = (min(base), max(base)) if base else (min(x for x, _ in pts), max(x for x, _ in pts))
    cx = (xmin + xmax) / 2
    col = [Vector((xmin if c.x < cx else xmax, c.y, zb - 0.03)) if c.z > zb + 1e-3 else c.copy() for c in full]
    o.shape_key_add(name="Basis")
    kb = me.shape_keys.key_blocks["Basis"]
    for i, c in enumerate(col):
        kb.data[i].co = c
        me.vertices[i].co = c
    kf = o.shape_key_add(name="cheio", from_mix=False)
    for i, c in enumerate(full):
        kf.data[i].co = c
    return o


def add_relative_key(o, name, poly, relative_to="cheio"):
    """Segunda forma (ex.: lixo compactado) relativa à forma 'cheio'. Mesma contagem de vértices."""
    pts = ring(poly) if hasattr(poly, "exterior") else list(poly)
    me = o.data
    kc = me.shape_keys.key_blocks[relative_to]
    k2 = o.shape_key_add(name=name, from_mix=False)
    k2.relative_key = kc
    y0, y1 = min(v.co.y for v in me.vertices), max(v.co.y for v in me.vertices)
    n = len(pts)
    coords = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
    if len(coords) != len(me.vertices):
        raise ValueError(f"{o.name}: forma '{name}' com {len(coords)} vértices, malha tem {len(me.vertices)}")
    for i, c in enumerate(coords):
        k2.data[i].co = c
    return k2


def shape(o, key, t, v):
    kb = o.data.shape_keys.key_blocks[key]
    kb.value = v
    kb.keyframe_insert("value", frame=F(t))


def fill(o, t0, t1, key="cheio", v0=0.0, v1=1.0):
    """Mostra o objeto em t0 e anima a chave de forma até t1."""
    hide_until(o, t0)
    shape(o, key, t0, v0)
    shape(o, key, t1, v1)


# ---------------------------------------------------------------- terreno em corte
LAYERS = [("grass", -0.2, 0.0), ("soft", -2.5, -0.2), ("mid", -5.0, -2.5), ("firm", -7.5, -5.0),
          ("aquifer", -10.5, -7.5), ("rock", -13.0, -10.5), ("base", -60.0, -13.0)]


def terrain(name, x0, x1, regions, M, layers=LAYERS, layer_mat=None):
    """Terreno em corte (face frontal em y = y0 da primeira região).
    regions: [(y0, y1, [recortes shapely no plano x-z])]. Retorna os objetos por material."""
    groups = {}
    for (y0, y1, notches) in regions:
        cut = unary_union(notches) if notches else None
        for lname, z0, z1 in layers:
            band = sg.box(x0, z0, x1, z1)
            geom = band.difference(cut) if cut is not None else band
            for p in polys(geom):
                groups.setdefault(lname, bmesh.new())
                prism_bm(groups[lname], ring(p), y0, y1)
    out = {}
    for lname, bm in groups.items():
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        out[lname] = mesh_obj(f"{name}_{lname}", bm, M[(layer_mat or {}).get(lname, lname)])
    return out


def far_ground(M, x0=-400, x1=400, y0=14, sea_from=None):
    bm = bmesh.new()
    box_bm(bm, x0, x1 if sea_from is None else sea_from, y0, 400, -1, -0.02)
    mesh_obj("far_grass", bm, M["grass"])


# ---------------------------------------------------------------- decoração
def decor(M, fence=(-22, 42, 14.9), trees=(), clouds=(), seed=3):
    rnd = random.Random(seed)
    if fence:
        fx0, fx1, fy = fence
        fb = bmesh.new()
        x = fx0
        while x <= fx1:
            box_bm(fb, x - 0.07, x + 0.07, fy, fy + 0.14, 0, 1.0)
            x += 1.3
        box_bm(fb, fx0, fx1, fy + 0.05, fy + 0.1, 0.62, 0.74)
        box_bm(fb, fx0, fx1, fy + 0.05, fy + 0.1, 0.30, 0.42)
        mesh_obj("fence", fb, M["fence"])
    if trees:
        tb, lb = bmesh.new(), bmesh.new()
        for x, y in trees:
            s = rnd.uniform(0.8, 1.3)
            box_bm(tb, x - 0.18 * s, x + 0.18 * s, y - 0.18 * s, y + 0.18 * s, 0, 1.6 * s)
            bmesh.ops.create_icosphere(lb, subdivisions=1, radius=1.25 * s,
                                       matrix=Matrix.Translation((x, y, 2.4 * s)) @ Matrix.Rotation(rnd.random() * 3, 4, "Z"))
        mesh_obj("trunks", tb, M["trunk"])
        mesh_obj("leaves", lb, M["leaf"])
    if clouds:
        cb = bmesh.new()
        for cx, cy, cz in clouds:
            for dx, dz, r in [(0, 0, 3), (3, 0.4, 2.4), (-3, -0.2, 2.2), (1.5, 1.6, 2)]:
                bmesh.ops.create_icosphere(cb, subdivisions=1, radius=r,
                                           matrix=Matrix.Translation((cx + dx, cy, cz + dz)) @ Matrix.Diagonal((1.3, 1, 0.7, 1)))
        mesh_obj("clouds", cb, M["cloud"])


def house(name, cx, y0, M, w=3.4, d=3.2, h=2.6, win=None, wall=None, roof=None):
    bm = bmesh.new()
    box_bm(bm, cx - w / 2, cx + w / 2, y0, y0 + d, 0, h, 0)
    v = [bm.verts.new(p) for p in [(cx - w / 2 - 0.25, y0 - 0.25, h), (cx + w / 2 + 0.25, y0 - 0.25, h), (cx, y0 - 0.25, h + 1.4),
                                   (cx - w / 2 - 0.25, y0 + d + 0.25, h), (cx + w / 2 + 0.25, y0 + d + 0.25, h), (cx, y0 + d + 0.25, h + 1.4)]]
    for f in [(0, 1, 2), (5, 4, 3), (0, 2, 5, 3), (1, 4, 5, 2), (0, 3, 4, 1)]:
        bm.faces.new([v[i] for i in f]).material_index = 1
    box_bm(bm, cx - 0.35, cx + 0.35, y0 - 0.03, y0, 0, 1.5, 2)
    box_bm(bm, cx - 1.4, cx - 0.7, y0 - 0.03, y0, 1.0, 1.7, 3)
    box_bm(bm, cx + 0.7, cx + 1.4, y0 - 0.03, y0, 1.0, 1.7, 3)
    return mesh_obj(name, bm, [wall or M["white"], roof or M["roof"], M["wood"], win or M["glass"]])


# ================================================================ animação
def k(o, path, t, value):
    setattr(o, path, value)
    o.keyframe_insert(path, frame=F(t))


def ks(o, t, s):
    k(o, "scale", t, (s, s, s) if isinstance(s, (int, float)) else s)


def hide_until(o, t):
    """Escala 0 até o quadro anterior a t, 1 em t."""
    o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=F(t) - 1)
    o.scale = (1, 1, 1); o.keyframe_insert("scale", frame=F(t))


def hide_from(o, t):
    o.scale = (1, 1, 1); o.keyframe_insert("scale", frame=F(t) - 1)
    o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=F(t))


def pop_in(o, t, d=0.35, s=1.0):
    ks(o, t, 0.0)
    ks(o, t + d * 0.65, 1.12 * s)
    ks(o, t + d, s)


def pop_out(o, t, d=0.25, s=1.0):
    ks(o, t, s)
    ks(o, t + d * 0.35, 1.1 * s)
    ks(o, t + d, 0.0)


def grow(o, t0, t1, axis="z", frm=0.0, to=1.0):
    """Cresce num eixo local (origem do objeto fica parada). Escala 0 total antes/depois."""
    i = "xyz".index(axis)
    def sv(v):
        s = [1.0, 1.0, 1.0]; s[i] = v; return tuple(s)
    if frm == 0:
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=F(t0) - 1)
    ks(o, t0, sv(frm))
    ks(o, t1, sv(to))
    if to == 0:
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=F(t1) + 1)


def grow_z(o, t0, t1, frm=0.0, to=1.0):
    grow(o, t0, t1, "z", frm, to)


def move(o, t0, t1, a, b):
    k(o, "location", t0, a)
    k(o, "location", t1, b)


def path(o, pts):
    """pts: [(t, (x,y,z)), ...]"""
    for t, p in pts:
        k(o, "location", t, p)


def jump(o, attr, t, before, after):
    setattr(o, attr, before); o.keyframe_insert(attr, frame=F(t) - 1)
    setattr(o, attr, after); o.keyframe_insert(attr, frame=F(t))


def flicker(o, t0, t1, base=1.0, amp=0.25, every=2, rnd=None):
    """Chama tremulando: escala aleatória a cada `every` quadros."""
    rnd = rnd or random.Random(hash(o.name) & 0xffff)
    f = F(t0)
    while f <= F(t1):
        sx = base * (1 + rnd.uniform(-amp, amp) * 0.5)
        o.scale = (sx, sx, base * (1 + rnd.uniform(-amp, amp)))
        o.keyframe_insert("scale", frame=f)
        f += every


def loop_fall(o, t0, t1, top, bottom, period, phase=0.0):
    """Gota/partícula que cai de top até bottom repetidamente (chuva, gotejamento)."""
    hide_until(o, t0)
    t = t0 + phase
    jump(o, "location", t, Vector(bottom), Vector(top))
    while t + period <= t1:
        k(o, "location", t + period * 0.98, Vector(bottom))
        t += period
        if t + period <= t1:
            jump(o, "location", t, Vector(bottom), Vector(top))
    hide_from(o, t1)


def along(o, pts, t0, t1, loops=1, hide=True):
    """Move uma bolinha ao longo de uma polilinha [p0, p1, ...] em velocidade constante, `loops` vezes."""
    pts = [Vector(p) for p in pts]
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    per = (t1 - t0) / loops
    if hide:
        hide_until(o, t0)
    for n in range(loops):
        base = t0 + n * per
        for p, l in zip(pts, L):
            tt = base + per * l / L[-1]
            if n > 0 and l == 0:
                jump(o, "location", tt, pts[-1], p)
            else:
                k(o, "location", tt, p)
    if hide:
        hide_from(o, t1)


# ================================================================ céu, sol, câmeras
class Sky:
    def __init__(self, top="#5fa3e0", horizon="#dcecf7", sun_energy=3.6):
        world = bpy.data.worlds.new("sky")
        scene.world = world
        world.use_nodes = True
        wn = world.node_tree
        self.bg = wn.nodes["Background"]
        tc = wn.nodes.new("ShaderNodeTexCoord")
        sep = wn.nodes.new("ShaderNodeSeparateXYZ")
        self.ramp = wn.nodes.new("ShaderNodeValToRGB")
        r = self.ramp.color_ramp
        r.elements[0].position, r.elements[0].color = 0.0, lin(horizon)
        r.elements[1].position, r.elements[1].color = 0.45, lin(top)
        wn.links.new(tc.outputs["Generated"], sep.inputs[0])
        wn.links.new(sep.outputs["Z"], self.ramp.inputs["Fac"])
        wn.links.new(self.ramp.outputs["Color"], self.bg.inputs["Color"])
        self.bg.inputs["Strength"].default_value = 1.0
        self.sun_d = bpy.data.lights.new("sun", "SUN")
        self.sun_d.energy = sun_energy
        self.sun_d.angle = math.radians(6)
        self.sun = link(bpy.data.objects.new("sun", self.sun_d))
        self.sun.rotation_euler = (math.radians(50), math.radians(-18), math.radians(-35))
        self.top, self.horizon, self.energy = top, horizon, sun_energy

    def state(self, t, energy, strength, top, horizon, sun_col="#ffffff"):
        self.sun_d.energy = energy
        self.sun_d.keyframe_insert("energy", frame=F(t))
        self.sun_d.color = lin(sun_col)[:3]
        self.sun_d.keyframe_insert("color", frame=F(t))
        self.bg.inputs["Strength"].default_value = strength
        self.bg.inputs["Strength"].keyframe_insert("default_value", frame=F(t))
        for el, c in zip(self.ramp.color_ramp.elements, (horizon, top)):
            el.color = lin(c)
            el.keyframe_insert("color", frame=F(t))

    def day(self, t):
        self.state(t, self.energy, 1.0, self.top, self.horizon)

    def sunset(self, t0, t1):
        """Entardecer (fim do dia) entre t0 e t1."""
        self.day(t0)
        self.state(t1, 2.2, 0.75, "#5b6fae", "#ffb36b", "#ffb070")

    def day_night(self, t0, cycles=2, step=0.3):
        for i in range(cycles * 2 + 1):
            if i % 2 == 0:
                self.day(t0 + i * step)
            else:
                self.state(t0 + i * step, 0.15, 0.18, "#1b2747", "#41507a")


def cameras(shots, shakes=(), lens=35, seed=11):
    """shots: [(t_inicio, [(t, pos_camera, alvo), ...]), ...] — cada plano é uma câmera própria (corte seco).
    shakes: [(t0, t1, amplitude)] — tremor aplicado ao conjunto câmera+alvo ativo nesse intervalo."""
    rnd = random.Random(seed)
    rigs = []
    for si, (t_start, wps) in enumerate(shots):
        rig = empty(f"rig{si}")
        cd = bpy.data.cameras.new(f"cam{si}")
        cd.lens = lens
        cd.sensor_fit = "AUTO"
        cd.clip_end = 2000
        cam = link(bpy.data.objects.new(f"cam{si}", cd))
        tgt = empty(f"tgt{si}")
        cam.parent = rig
        tgt.parent = rig
        con = cam.constraints.new("TRACK_TO")
        con.target = tgt
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        for t, c, g in wps:
            k(cam, "location", t, c)
            k(tgt, "location", t, g)
        mk = scene.timeline_markers.new(f"shot{si}", frame=F(t_start))
        mk.camera = cam
        if si == 0:
            scene.camera = cam
        t_end = shots[si + 1][0] if si + 1 < len(shots) else 1e9
        for (a, b, amp) in shakes:
            if a >= t_end or b <= t_start:
                continue
            k(rig, "location", max(a, t_start), (0, 0, 0))
            f = F(max(a, t_start)) + 1
            while f < F(min(b, t_end)):
                rig.location = (rnd.uniform(-amp, amp), rnd.uniform(-amp, amp) * 0.3, rnd.uniform(-amp, amp))
                rig.keyframe_insert("location", frame=f)
                f += 2
            k(rig, "location", min(b, t_end), (0, 0, 0))
        rigs.append(cam)
    return rigs


def write_cuts(path, whips, duration):
    with open(path, "w") as fh:
        json.dump({"fps": FPS, "duracao": duration, "transicoes": whips}, fh, indent=1)
