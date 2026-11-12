"""Veículos 3D "brinquedo de vinil" (3ª versão) — carros e motos lisos, sem emendas.

Técnica:
- Carroceria = UMA malha de gaiola (bmesh, só quads) feita por "loft": anéis transversais ao longo de x, fechados
  nas pontas com tampa em quads, + Subdivision Surface (nível 2 na viewport, 3 no render). Vidros, capota
  marítima, para-choque e moldura de SUV são FACES da própria malha com outro material (material_index), então
  não há emenda nenhuma: a borda do vidro é uma curva lisa da própria superfície.
- Caixas de roda: o fundo da carroceria sobe em arco sobre cada eixo (túnel em toda a largura), com um "forro"
  escuro escondido por dentro. A roda nunca encosta na lata.
- Rodas: UMA malha de torno (perfil girado) com pneu toroidal liso + aro + cubo (material por faixa do perfil).
- Detalhes (faróis, lanternas, placa, olhos, boca) são colados na superfície final por raycast (BVHTree da malha
  já subdividida), orientados pela normal, levemente embutidos: nada flutua nem atravessa.
- Materiais "vinil acetinado": Principled, roughness ~0.4, coat leve.

Convenção (igual a pecas_veiculos): anda para +x, origem no chão no meio do entre-eixos, rodas giram em y.
carro(...) e moto(...) devolvem dict: raiz, rodas, lataria (malhas na cor), rosto (dict ou None) e partes.
"""
import math
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

# ================================================================ cores
LATARIA = {"branco": "#F4F4F0", "prata": "#C4C9CF", "cinza": "#868D95", "preto": "#3A3F47",   # cores vivas (aprovadas)
           "vermelho": "#FF2E3B", "azul": "#1E5BFF", "laranja": "#FF6A00", "amarelo": "#FFC400",
           "verde": "#00B37A", "roxo": "#7A3CFF"}

BASE = {  # nome: (cor, rugosidade, coat, emissão, metálico)
    "vidro": ("#28405A", 0.08, 0.35, 0.0, 0.0),
    "plastico": ("#33373E", 0.55, 0.1, 0.0, 0.0),
    "grade": ("#2A2E34", 0.6, 0.0, 0.0, 0.0),
    "pneu": ("#2B2E33", 0.7, 0.05, 0.0, 0.0),
    "aro": ("#E4E7EB", 0.32, 0.3, 0.0, 0.0),
    "cubo": ("#9AA3AC", 0.35, 0.2, 0.0, 0.0),
    "forro": ("#1C1F23", 0.9, 0.0, 0.0, 0.0),
    "farol": ("#FFF6DA", 0.2, 0.5, 0.45, 0.0),
    "lanterna": ("#E5484D", 0.25, 0.5, 0.5, 0.0),
    "pisca": ("#FF9A2E", 0.25, 0.5, 0.4, 0.0),
    "placa": ("#F7F7F2", 0.45, 0.2, 0.0, 0.0),
    "placa_faixa": ("#1F4FA3", 0.45, 0.2, 0.0, 0.0),
    "olho": ("#FFFFFF", 0.3, 0.5, 0.0, 0.0),
    "pupila": ("#161A1F", 0.25, 0.6, 0.0, 0.0),
    "brilho": ("#FFFFFF", 0.3, 0.0, 2.0, 0.0),
    "boca": ("#4A2328", 0.5, 0.2, 0.0, 0.0),
    "cromo": ("#D5DAE0", 0.22, 0.3, 0.0, 0.7),
    "motor": ("#6E767F", 0.45, 0.1, 0.0, 0.3),
    "banco": ("#2E3238", 0.6, 0.05, 0.0, 0.0),
    "refletivo": ("#EEF2F6", 0.2, 0.4, 0.15, 0.0),
    "bau": ("#FF6A00", 0.4, 0.3, 0.0, 0.0),
}


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def vinil(name, hexcol, rough=0.4, coat=0.25, emit=0.0, metal=0.0):
    """Vinil acetinado: Principled liso, coat leve (o brilho "de brinquedo novo")."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexcol)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k, v in (("Coat Weight", coat), ("Coat Roughness", 0.18)):
        if k in b.inputs:
            b.inputs[k].default_value = v
    if name.endswith("vidro"):
        _vidro_degrade(m, b)
    if emit:
        b.inputs["Emission Color"].default_value = lin(hexcol)
        b.inputs["Emission Strength"].default_value = emit
    return m


def _vidro_degrade(m, b):
    """Vidro de brinquedo: azul-petróleo escuro no centro, clareando para as bordas (Fresnel) e de baixo
    para cima, + reflexo nítido das luzes. Nunca fica "azul chapado"."""
    nt = m.node_tree
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.45
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    rz = nt.nodes.new("ShaderNodeMapRange")       # z do objeto: cintura (~0,85) -> teto (~1,5)
    rz.inputs["From Min"].default_value = 0.85
    rz.inputs["From Max"].default_value = 1.55
    nt.links.new(sep.outputs["Z"], rz.inputs["Value"])
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(lw.outputs["Facing"], mx.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.55
    nt.links.new(rz.outputs["Result"], mul.inputs[0])
    nt.links.new(mul.outputs[0], mx.inputs[1])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = lin("#1C3350")
    cr.color_ramp.elements[1].color = lin("#7FA6CC")
    nt.links.new(mx.outputs[0], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.45


def materiais(M=None):
    M = {} if M is None else M
    for n, (c, r, co, e, me) in BASE.items():
        if n not in M:
            M[n] = vinil("v3_" + n, c, r, co, e, me)
    return M


def lataria_mat(M, cor):
    """cor = nome em LATARIA, chave de M ou hex '#rrggbb'."""
    materiais(M)
    if cor in M:
        return M[cor]
    hx = LATARIA.get(cor, cor)
    k = "lata_" + hx.lstrip("#")
    if k not in M:
        M[k] = vinil("v3_" + k, hx, rough=0.38, coat=0.35)
    return M[k]


def _escuro(hx, f=0.7):
    hx = LATARIA.get(hx, hx).lstrip("#")
    r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02X%02X%02X" % (int(r * f), int(g * f), int(b * f))


# ================================================================ objetos básicos
def _link(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def _obj(name, bm, mats, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        me.materials.append(m)
    if smooth:
        me.shade_smooth()
    return _link(bpy.data.objects.new(name, me))


def vazio(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.empty_display_size = 0.2
    return _link(e)


def filho(o, pai, loc=None):
    o.parent = pai
    if loc is not None:
        o.location = loc
    return o


def _subsurf(o, nivel=2, render=3):
    s = o.modifiers.new("liso", "SUBSURF")
    s.levels = nivel
    s.render_levels = render
    s.quality = 3
    return o


def _crease_layer(bm):
    lay = bm.edges.layers.float.get("crease_edge")
    return lay if lay is not None else bm.edges.layers.float.new("crease_edge")


def caixa(name, centro, tam, m, raio=0.3, nivel=2):
    """Caixa lisa de brinquedo: cubo com chanfro de 1 segmento + subdivisão (cantos redondos, faces retas).
    raio = fração (0–0.5) da menor medida que vira arredondado."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * tam[0], v.co.y * tam[1], v.co.z * tam[2]))
    off = min(tam) * raio
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=off, segments=1, profile=0.5, affect="EDGES")
    o = _obj(name, bm, m)
    o.location = centro
    return _subsurf(o, nivel, nivel + 1)


def elipsoide(name, centro, raios, m, seg=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * raios[0], v.co.y * raios[1], v.co.z * raios[2]))
    o = _obj(name, bm, m)
    o.location = centro
    return o


def calota(name, raio, ang_max, m, seg=32, aneis=10, esp=0.0):
    """Pedaço de esfera em volta do polo +z (de 0 até ang_max graus). Usado para pálpebra."""
    bm = bmesh.new()
    polo = bm.verts.new((0, 0, raio))
    prev = None
    for i in range(1, aneis + 1):
        t = math.radians(ang_max) * i / aneis
        ring = [bm.verts.new((raio * math.sin(t) * math.cos(2 * math.pi * k / seg),
                              raio * math.sin(t) * math.sin(2 * math.pi * k / seg), raio * math.cos(t)))
                for k in range(seg)]
        for k in range(seg):
            k2 = (k + 1) % seg
            if prev is None:
                bm.faces.new([polo, ring[k], ring[k2]])
            else:
                bm.faces.new([prev[k], ring[k], ring[k2], prev[k2]])
        prev = ring
    o = _obj(name, bm, m)
    if esp:
        s = o.modifiers.new("esp", "SOLIDIFY")
        s.thickness = esp
        s.offset = 1
    return o


def torno(name, perfil, mats, seg=64):
    """Sólido de revolução em torno do eixo y. perfil = [(r, y, mat_index_do_trecho_seguinte), ...]."""
    bm = bmesh.new()
    rings = []
    for r, y, _ in perfil:
        if r < 1e-6:
            rings.append([bm.verts.new((0, y, 0))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / seg), y, r * math.sin(2 * math.pi * k / seg)))
                          for k in range(seg)])
    for i in range(len(perfil) - 1):
        a, b, mi = rings[i], rings[i + 1], perfil[i][2]
        for k in range(seg):
            k2 = (k + 1) % seg
            if len(a) == 1:
                f = bm.faces.new([a[0], b[k], b[k2]])
            elif len(b) == 1:
                f = bm.faces.new([a[k], b[0], a[k2]])
            else:
                f = bm.faces.new([a[k], b[k], b[k2], a[k2]])
            f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mats)


def _catmull(pts, n=6):
    """Amostra uma curva Catmull-Rom que passa pelos pontos."""
    P = [Vector(p) for p in pts]
    if len(P) < 3:
        return P
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(n):
            t = s / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(P[-2])
    return out


def tubo(name, pts, r, m, seg=16, suave=True, tampa=True):
    """Tubo liso por uma lista de pontos (curva suave), pontas arredondadas. r = raio ou lista de raios."""
    P = _catmull(pts, 8) if suave and len(pts) > 2 else [Vector(p) for p in pts]
    if not isinstance(r, (list, tuple)):
        R = [r] * len(P)
    else:  # raios dados por ponto de controle: interpola
        R = [r[min(int(i / max(1, len(P) - 1) * (len(r) - 1) + 0.5), len(r) - 1)] for i in range(len(P))]
        R = [r[0] + (r[-1] - r[0]) * i / max(1, len(P) - 1) for i in range(len(P))] if len(r) == 2 else R
    T = []
    for i in range(len(P)):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, len(P) - 1)]
        T.append((b - a).normalized())
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - T[0] * up.dot(T[0])).normalized()
    bm = bmesh.new()
    rings = []

    def anel(c, t, n, rr):
        b2 = t.cross(n)
        return [bm.verts.new(c + (n * math.cos(2 * math.pi * k / seg) + b2 * math.sin(2 * math.pi * k / seg)) * rr)
                for k in range(seg)]

    frames = []
    for i in range(len(P)):
        if i > 0:
            N = (N - T[i] * N.dot(T[i])).normalized()
        frames.append(N.copy())
    if tampa:
        for a in (80, 60, 35):
            ang = math.radians(a)
            rings.append(anel(P[0] - T[0] * R[0] * math.sin(ang), T[0], frames[0], R[0] * math.cos(ang)))
    for i in range(len(P)):
        rings.append(anel(P[i], T[i], frames[i], R[i]))
    if tampa:
        for a in (35, 60, 80):
            ang = math.radians(a)
            rings.append(anel(P[-1] + T[-1] * R[-1] * math.sin(ang), T[-1], frames[-1], R[-1] * math.cos(ang)))
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            bm.faces.new([a[k], a[k2], b[k2], b[k]])
    if tampa:
        p0 = bm.verts.new(P[0] - T[0] * R[0])
        p1 = bm.verts.new(P[-1] + T[-1] * R[-1])
        for k in range(seg):
            k2 = (k + 1) % seg
            bm.faces.new([p0, rings[0][k2], rings[0][k]])
            bm.faces.new([p1, rings[-1][k], rings[-1][k2]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, m)


# ================================================================ loft (a carroceria em uma malha só)
def loft(name, xs, aneis, mats, mat_seg=None, crease=None, bojo=(0.06, 0.06), nivel=2):
    """Malha de gaiola em quads: anéis transversais (metade +y, do centro de baixo ao centro de cima, N pontos
    (y, z)) nas estações xs, espelhados em -y e fechados nas duas pontas por uma tampa de quads.
    mat_seg(i, j) -> material_index do trecho entre as estações i, i+1 e os pontos j, j+1 (índice -1 = tampa
    traseira, len(xs)-1 = tampa dianteira; j = número do quad da tampa). crease = {j: valor} nas arestas
    longitudinais do ponto j. bojo = quanto a tampa (trás, frente) estufa para fora."""
    bm = bmesh.new()
    N = len(aneis[0])
    S = len(xs)
    V = []
    for i, x in enumerate(xs):
        ring = aneis[i]
        pos = [bm.verts.new((x, y, z)) for (y, z) in ring]
        neg = {j: bm.verts.new((x, -ring[j][0], ring[j][1])) for j in range(1, N - 1)}
        V.append((pos, neg))

    def vp(i, j):
        return V[i][0][j]

    def vn(i, j):
        return V[i][0][j] if j in (0, N - 1) else V[i][1][j]

    for i in range(S - 1):
        for j in range(N - 1):
            mi = mat_seg(i, j) if mat_seg else 0
            f1 = bm.faces.new([vp(i, j), vp(i + 1, j), vp(i + 1, j + 1), vp(i, j + 1)])
            f2 = bm.faces.new([vn(i, j), vn(i, j + 1), vn(i + 1, j + 1), vn(i + 1, j)])
            f1.material_index = f2.material_index = mi
    # tampas: coluna central de vértices internos c1..c_{N-4}; quads [c_{k-1}, L_k, L_{k+1}, c_k]
    for ponta, i, sx in (("tras", 0, -1), ("frente", S - 1, 1)):
        x = xs[i]
        b = bojo[0] if ponta == "tras" else bojo[1]
        ring = aneis[i]
        nin = N - 4
        C = [vp(i, 0)]
        for k in range(1, nin + 1):
            z = ring[k + 1][1]
            # estufa mais no meio da tampa
            f = math.sin(math.pi * k / (nin + 1))
            C.append(bm.verts.new((x + sx * b * (0.55 + 0.45 * f), 0, z)))
        C.append(vp(i, N - 1))
        idx = -1 if ponta == "tras" else S - 1
        for side in (vp, vn):
            for k in range(1, N - 2):
                c0 = C[k - 1]
                c1 = C[k] if k < N - 3 else C[-1]
                if k == N - 3:
                    quad = [c0, side(i, k), side(i, k + 1), C[-1]]
                else:
                    quad = [c0, side(i, k), side(i, k + 1), C[k]]
                f = bm.faces.new(quad)
                f.material_index = mat_seg(idx, k) if mat_seg else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # normais para fora: confere pelo volume
    if crease:
        lay = _crease_layer(bm)
        for e in bm.edges:
            a, b2 = e.verts
            if abs(a.co.x - b2.co.x) < 1e-9:
                continue
            for j, val in crease.items():
                for i in range(S - 1):
                    for fn in (vp, vn):
                        if {a, b2} == {fn(i, j), fn(i + 1, j)}:
                            e[lay] = val
    o = _obj(name, bm, mats)
    return _subsurf(o, nivel, nivel + 1)


# ================================================================ colar na superfície
class Superficie:
    """BVH da malha final (com subdivisão) de um objeto sem transformação: acha ponto e normal por raio."""

    def __init__(self, obj):
        dg = bpy.context.evaluated_depsgraph_get()
        self.bvh = BVHTree.FromObject(obj, dg)

    def raio(self, origem, direcao):
        loc, nor, _, _ = self.bvh.ray_cast(Vector(origem), Vector(direcao).normalized())
        return loc, nor


def _orientar(o, normal, rolar=0.0):
    """Gira o objeto para que o eixo local +x aponte na normal (mantendo z "para cima")."""
    n = Vector(normal).normalized()
    q = n.to_track_quat("X", "Z")
    if rolar:
        q = q @ Quaternion((1, 0, 0), rolar)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = q
    return o


def colar(o, sup, origem, direcao, embute=0.0, rolar=0.0, alinhar=True):
    loc, nor = sup.raio(origem, direcao)
    if loc is None:
        return None
    o.location = loc - nor * embute
    if alinhar:
        _orientar(o, nor, rolar)
    return loc, nor


# ================================================================ placa
def placa(name, M, larg=0.34, alt=0.11, esp=0.02):
    """Placa Mercosul sem letras: branca, faixa azul no alto. Frente = +x (plano yz)."""
    root = vazio(name)
    p = caixa(name + "_base", (0, 0, 0), (esp, larg, alt), M["placa"], raio=0.35)
    filho(p, root)
    fx = caixa(name + "_faixa", (esp * 0.18, 0, alt * 0.32), (esp * 0.7, larg * 0.92, alt * 0.22), M["placa_faixa"],
               raio=0.4)
    filho(fx, root)
    return root


# ================================================================ roda
def roda(name, M, R=0.3, larg=0.24, cor_aro="aro"):
    """Pneu toroidal liso + aro (prato) + cubo numa malha só de torno. Eixo y, centro na origem."""
    w = larg / 2
    perfil = [
        (0.0, w * 0.62, 2), (R * 0.10, w * 0.62, 2), (R * 0.17, w * 0.58, 2), (R * 0.20, w * 0.50, 1),
        (R * 0.36, w * 0.46, 1), (R * 0.50, w * 0.50, 1), (R * 0.555, w * 0.62, 1), (R * 0.585, w * 0.66, 1),
        (R * 0.61, w * 0.62, 0),
        (R * 0.66, w * 0.80, 0), (R * 0.76, w * 0.97, 0), (R * 0.87, w * 1.0, 0), (R * 0.95, w * 0.92, 0),
        (R * 0.99, w * 0.70, 0), (R * 1.0, w * 0.35, 0), (R * 1.0, 0.0, 0),
    ]
    tras = [(r, -y, mi) for (r, y, mi) in reversed(perfil[:-1])]
    # o índice de material vale para o trecho seguinte: no lado espelhado, desloca uma posição
    tras = [(tras[i][0], tras[i][1], tras[i + 1][2] if i + 1 < len(tras) else 2) for i in range(len(tras))]
    prof = perfil + tras
    return torno(name, prof, [M["pneu"], M[cor_aro], M["cubo"]], seg=64)


# ================================================================ carros
def _spec(tipo):
    """Proporções de cada arquétipo (unidades ~ metros de brinquedo). topo = perfil do alto da lata
    [(x, z, material do trecho seguinte)], janelas = trechos (x0, x1) com vidro lateral."""
    s = dict(R=0.33, larg=0.27, W=0.62, zb=0.14, belt=0.86, roof=1.50, tumble=0.23,
             cover=False, clad=False, rails=False, santo=False)
    if tipo == "hatch":       # Polo / Argo / HB20 / Onix
        s.update(wb=1.20, fr=0.48, tr=0.42)
        P = lambda xf, xr, XF, XR: dict(
            topo=[(XR, 0.98, "lata"), (XR + 0.04, 1.02, "vidro"), (XR + 0.22, 1.46, "teto"),
                  (XF - 0.80, 1.50, "vidro"), (XF - 0.58, 1.33, "vidro"), (XF - 0.38, 0.96, "lata"),
                  (XF, 0.89, None)],
            janelas=[(XR + 0.28, -0.10), (-0.02, XF - 0.76)])
    elif tipo == "popular":   # Mobi: mais curto e alto
        s.update(wb=1.06, fr=0.46, tr=0.40, W=0.60, R=0.32, belt=0.84, roof=1.52, zb=0.14)
        P = lambda xf, xr, XF, XR: dict(
            topo=[(XR, 0.96, "lata"), (XR + 0.03, 0.99, "vidro"), (XR + 0.13, 1.47, "teto"),
                  (XF - 0.72, 1.52, "vidro"), (XF - 0.53, 1.36, "vidro"), (XF - 0.35, 0.94, "lata"),
                  (XF, 0.88, None)],
            janelas=[(XR + 0.19, -0.08), (0.0, XF - 0.68)])
    elif tipo == "suv":       # T-Cross / Creta
        s.update(wb=1.30, fr=0.52, tr=0.46, W=0.66, R=0.36, larg=0.29, zb=0.18, belt=0.94, roof=1.60,
                 tumble=0.19, clad=True, rails=True)
        P = lambda xf, xr, XF, XR: dict(
            topo=[(XR, 1.06, "lata"), (XR + 0.04, 1.10, "vidro"), (XR + 0.14, 1.56, "teto"),
                  (XF - 0.80, 1.60, "vidro"), (XF - 0.60, 1.42, "vidro"), (XF - 0.40, 1.04, "lata"),
                  (XF, 0.99, None)],
            janelas=[(XR + 0.20, -0.10), (-0.02, XF - 0.74)])
    elif tipo == "picape":    # Strada / Saveiro, com capota marítima
        s.update(wb=1.40, fr=0.50, tr=0.56, W=0.64, R=0.34, larg=0.28, zb=0.17, belt=0.90, roof=1.50,
                 cover=True, santo=True, xc=-0.18)
        P = lambda xf, xr, XF, XR: dict(
            topo=[(XR, 0.97, "capota"), (s["xc"] - 0.07, 0.97, "lata"), (s["xc"] - 0.05, 1.08, "vidro"),
                  (s["xc"] + 0.03, 1.47, "teto"), (XF - 0.82, 1.50, "vidro"), (XF - 0.60, 1.33, "vidro"),
                  (XF - 0.40, 1.00, "lata"), (XF, 0.93, None)],
            janelas=[(s["xc"] + 0.10, XF - 0.78)])
    elif tipo == "seda":      # figurante de 3 volumes
        s.update(wb=1.30, fr=0.48, tr=0.58, R=0.32, belt=0.84, roof=1.44, zb=0.13)
        P = lambda xf, xr, XF, XR: dict(
            topo=[(XR, 0.95, "lata"), (XR + 0.26, 0.99, "vidro"), (XR + 0.56, 1.40, "teto"),
                  (XF - 0.82, 1.44, "vidro"), (XF - 0.60, 1.29, "vidro"), (XF - 0.40, 0.94, "lata"),
                  (XF, 0.88, None)],
            janelas=[(XR + 0.60, -0.10), (-0.02, XF - 0.78)])
    else:
        raise ValueError(tipo)
    s["xf"], s["xr"] = s["wb"] / 2, -s["wb"] / 2
    s["XF"], s["XR"] = s["xf"] + s["fr"], s["xr"] - s["tr"]
    s.update(P(s["xf"], s["xr"], s["XF"], s["XR"]))
    return s


def _interp(pts, x):
    for (x0, z0, *_), (x1, z1, *_) in zip(pts, pts[1:]):
        if x0 - 1e-9 <= x <= x1 + 1e-9:
            t = 0 if x1 == x0 else (x - x0) / (x1 - x0)
            return z0 + (z1 - z0) * t
    return pts[0][1] if x < pts[0][0] else pts[-1][1]


def _tag(pts, x):
    for (x0, _, tg), (x1, *_) in zip(pts, pts[1:]):
        if x0 - 1e-9 <= x <= x1 + 1e-9:
            return tg
    return "lata"


def _fundo(s, x):
    """Altura do fundo da lata: plano, subindo em arco sobre cada roda (caixa de roda)."""
    R = s["R"]
    Ra = R + 0.06
    z = s["zb"]
    for xw in (s["xf"], s["xr"]):
        d = abs(x - xw)
        if d <= Ra:
            z = max(z, R + math.sqrt(max(Ra * Ra - d * d, 0)) + 0.025)
    return z


def _estacoes(s):
    R = s["R"]
    Ra = R + 0.06
    xs = {s["XR"], s["XR"] + 0.07, s["XF"], s["XF"] - 0.07}
    for x, _, _ in s["topo"]:
        xs.add(x)
    for a, b in s["janelas"]:
        xs.update((a, b))
    for xw in (s["xf"], s["xr"]):
        for d in (-1.16, -1.04, -1.0, -0.72, -0.36, 0.0, 0.36, 0.72, 1.0, 1.04, 1.16):
            xs.add(xw + d * Ra)
    xs = sorted(x for x in xs if s["XR"] - 1e-6 <= x <= s["XF"] + 1e-6)
    # junta estações muito próximas
    out = []
    for x in xs:
        if out and x - out[-1] < 0.012:
            continue
        out.append(x)
    # garante as pontas
    out[0], out[-1] = s["XR"], s["XF"]
    return out


def _anel_carro(s, x, ponta=0.0):
    """Meio anel (do centro de baixo ao centro de cima), 9 pontos:
    0 fundo, 1 quina de baixo, 2 soleira, 3 topo do para-choque, 4 linha de cintura, 5 base do vidro,
    6 topo do vidro, 7 calha do teto, 8 centro do teto/capô."""
    W = s["W"] * (1 - 0.09 * ponta)
    zb = _fundo(s, x) + 0.04 * ponta
    belt = s["belt"]
    zt = _interp(s["topo"], x) - 0.025 * ponta
    hc = s["roof"] - belt
    h = max(zt - belt, 0.03)
    f = min(1.0, h / hc)
    zs = min(zb + 0.08, belt - 0.10)
    zp = min(max(s["zb"] + 0.24, zs + 0.05), belt - 0.05)
    p5y = W - 0.05 - s["tumble"] * f
    return [
        (0.0, zb),
        (W - 0.10, zb),
        (W, zs),
        (W, zp),
        (W, belt),
        (W - 0.02 - 0.03 * f, belt + min(0.05, 0.45 * h)),
        (p5y, belt + 0.78 * h),
        (p5y - 0.08 - 0.10 * f, belt + 0.93 * h),
        (0.0, zt),
    ]


def aro_mat(M, cor=None):
    """Chave de M do material do aro: None = aro claro padrão; senão cor (nome da LATARIA ou hex)."""
    materiais(M)
    if not cor:
        return "aro"
    hx = LATARIA.get(cor, cor)
    k = "aro_" + hx.lstrip("#")
    if k not in M:
        M[k] = vinil("v3_" + k, hx, rough=0.32, coat=0.35)
    return k


def carro(name, M, tipo="hatch", cor="prata", rosto=False, humor="feliz", olhar=(0.0, 0.0), placa_on=True,
          nivel=2, aro=None, retrovisor=True, estilo="chibi", escala=0.5):
    """Carro de brinquedo de vinil. tipo: hatch | popular | suv | picape | seda. cor: nome, chave de M ou hex.
    rosto=True põe olhos NOS FARÓIS e boca na grade (humor: feliz | preocupado | assustado | bravo).
    aro=None (claro) ou cor do aro ('vermelho', '#FFC400'...). retrovisor=True põe os espelhinhos.
    estilo="real": variante adulta (proporção real em metros, reduzida por `escala`; sem rosto).
    Devolve dict(raiz, rodas, lataria, rosto, corpo, partes)."""
    if estilo == "real":
        return _carro_real(name, M, tipo, cor, placa_on, nivel, escala)
    materiais(M)
    lat = lataria_mat(M, cor)
    s = _spec(tipo)
    root = vazio(name)
    xs = _estacoes(s)
    aneis = []
    for i, x in enumerate(xs):
        ponta = 1.0 if i in (0, len(xs) - 1) else 0.0
        aneis.append(_anel_carro(s, x, ponta))
    topo = s["topo"]
    jan = s["janelas"]
    # materiais da malha: 0 lata, 1 vidro, 2 plástico (moldura/capota), 3 grade
    LATA, VIDRO, PLAST, GRADE = 0, 1, 2, 3

    def arco(xm):
        return any(abs(xm - xw) <= s["R"] + 0.06 for xw in (s["xf"], s["xr"]))

    S = len(xs)

    def mat_seg(i, j):
        # j (laterais): 0 fundo, 1 quina, 2 para-choque, 3 lateral, 4 ombro, 5 vidro lateral, 6 calha, 7 alto
        if i == -1 or i == S - 1:  # tampas: quads 1..6 de baixo para cima
            return PLAST if j in (1, 2) else LATA
        xm = (xs[i] + xs[i + 1]) / 2
        tg = _tag(topo, xm)
        if j in (6, 7) and tg == "vidro":
            return VIDRO
        if j in (6, 7) and tg == "capota":
            return PLAST
        if j == 5 and any(a <= xm <= b for a, b in jan):
            return VIDRO
        if j in (1, 2) and (i == 0 or i == S - 2):
            return PLAST           # para-choque abraça as quinas
        if s["clad"] and (j in (0, 1, 2) or (j == 3 and arco(xm))):
            return PLAST           # moldura preta do SUV (saia + para-lamas)
        return LATA

    corpo = loft(name + "_lata", xs, aneis, [lat, M["vidro"], M["plastico"], M["grade"]], mat_seg,
                 crease={4: 0.35}, bojo=(0.10, 0.12), nivel=nivel)
    filho(corpo, root)
    partes = {"corpo": corpo}

    # forro escuro das caixas de roda (fica dentro da lata; só aparece pelo túnel do arco)
    R = s["R"]
    yi = s["W"] - s["larg"] * 0.85 - 0.03
    forro = caixa(name + "_forro", ((s["XF"] + s["XR"]) / 2, 0, (s["zb"] + 2 * R + 0.06) / 2 + 0.02),
                  (s["XF"] - s["XR"] - 0.35, 2 * yi, 2 * R + 0.06 - s["zb"]), M["forro"], raio=0.2)
    filho(forro, root)

    # rodas
    rodas = []
    yw = s["W"] - s["larg"] * 0.32
    for lado, xw in (("d", s["xf"]), ("t", s["xr"])):
        for sy in (1, -1):
            rd = roda(f"{name}_roda_{lado}{'e' if sy > 0 else 'd'}", M, R, s["larg"], aro_mat(M, aro))
            if sy < 0:
                rd.rotation_euler = (0, 0, math.pi)
            filho(rd, root, (xw, sy * yw, R))
            rodas.append(rd)

    sup = Superficie(corpo)
    belt = s["belt"]
    W = s["W"]
    ornam = []
    rosto_d = None
    # faróis / olhos
    zf = belt - 0.07
    if rosto:
        rosto_d = _rosto_carro(name, M, sup, s, humor, olhar, lat)
        for o in rosto_d["objetos"]:
            filho(o, root)
    else:
        for sy in (1, -1):
            f = elipsoide(f"{name}_farol{sy}", (0, 0, 0), (0.03, 0.10, 0.055), M["farol"])
            colar(f, sup, (5, sy * W * 0.64, zf), (-1, 0, 0), embute=0.008)
            ornam.append(f)
        # grade larga logo acima do para-choque (lê como grade, não como boca)
        g = caixa(f"{name}_grade", (0, 0, 0), (0.05, W * 0.92, 0.07), M["grade"], raio=0.4)
        colar(g, sup, (5, 0, s["zb"] + 0.24 + 0.05), (-1, 0, 0), embute=0.02)
        ornam.append(g)
    # retrovisores: haste curta saindo da lateral, logo atrás da base do para-brisa
    if retrovisor:
        xb = max(x for x, _, tg in topo[:-1] if tg == "lata" and x > 0) - 0.05
        for sy in (1, -1):
            loc, nor = sup.raio((xb, sy * 5, belt + 0.07), (0, -sy, 0))
            if loc is None:
                continue
            # haste curta e grossa + "orelha" larga: lê como retrovisor, não como antena
            ponta = loc + Vector((-0.01, sy * 0.06, 0.03))
            hs = tubo(f"{name}_haste_retro{sy}", [loc - nor * 0.02, ponta], 0.026, lat, suave=False)
            cx = caixa(f"{name}_retrovisor{sy}", ponta + Vector((-0.015, sy * 0.06, 0.03)), (0.065, 0.15, 0.11),
                       lat, raio=0.3)
            cx.rotation_euler = (0, 0, math.radians(-12) * sy)
            ornam += [hs, cx]
    # piscas
    for sy in (1, -1):
        p = elipsoide(f"{name}_pisca{sy}", (0, 0, 0), (0.02, 0.035, 0.022), M["pisca"])
        colar(p, sup, (5, sy * W * 0.80, s["zb"] + 0.165), (-1, 0, 0), embute=0.006)
        ornam.append(p)
    # lanternas traseiras
    for sy in (1, -1):
        lt = elipsoide(f"{name}_lanterna{sy}", (0, 0, 0), (0.03, 0.10, 0.05), M["lanterna"])
        colar(lt, sup, (-5, sy * W * 0.68, belt - 0.07), (1, 0, 0), embute=0.004)
        ornam.append(lt)
    # placas
    if placa_on:
        for lado, sx, z in (("d", 1, s["zb"] + 0.12), ("t", -1, s["zb"] + 0.20 if not s["cover"] else s["zb"] + 0.2)):
            pl = placa(f"{name}_placa_{lado}", M)
            loc, nor = sup.raio((sx * 5, 0, z), (-sx, 0, 0))
            pl.location = loc + nor * 0.004
            pl.rotation_euler = (0, 0, 0 if sx > 0 else math.pi)
            ornam.append(pl)
    # barras de teto (SUV)
    if s["rails"]:
        for sy in (1, -1):
            pts = []
            for x in (s["xr"] - 0.12, s["xr"] + 0.25, s["xf"] - 0.50, s["xf"] - 0.40):
                loc, nor = sup.raio((x, sy * (W - 0.24), 5), (0, 0, -1))
                pts.append(loc + Vector((0, 0, 0.035)))
            pts[0].z -= 0.035
            pts[-1].z -= 0.035
            ornam.append(tubo(f"{name}_barra{sy}", pts, 0.022, M["plastico"]))
    # santo-antônio (picape)
    if s["santo"]:
        xs_ = s["xc"] - 0.16
        loc, _ = sup.raio((xs_, W - 0.10, 5), (0, 0, -1))
        z0 = loc.z - 0.02
        pts = [(xs_, W - 0.10, z0), (xs_, W - 0.12, z0 + 0.20), (xs_, W - 0.24, z0 + 0.26), (xs_, 0, z0 + 0.27)]
        pts = pts + [(p[0], -p[1], p[2]) for p in reversed(pts[:-1])]
        ornam.append(tubo(f"{name}_santo", pts, 0.028, M["plastico"]))
    for o in ornam:
        filho(o, root)
    partes["ornamentos"] = ornam
    return {"raiz": root, "rodas": rodas, "lataria": [corpo], "rosto": rosto_d, "corpo": corpo, "partes": partes,
            "spec": s}


def _rosto_carro(name, M, sup, s, humor, olhar, lat):
    """Olhos nos faróis + boca na grade. Os olhos olham para +x (frente do carro)."""
    W, belt = s["W"], s["belt"]
    objs = []
    olhos = []
    ro = 0.19
    for sy in (1, -1):
        e = vazio(f"{name}_olho{sy}")
        loc, nor = sup.raio((5, sy * W * 0.50, belt - 0.10), (-1, 0, 0))
        e.location = loc - nor * 0.05
        _orientar(e, nor)
        bola = elipsoide(f"{name}_olho{sy}_branco", (0, 0, 0), (0.085, ro * 0.95, ro * 0.92), M["olho"])
        filho(bola, e)
        ox, oz = olhar
        pr = 0.085 if humor != "assustado" else 0.055
        px, pz = ox * 0.06 - sy * 0.012, oz * 0.06 - 0.01
        pu = elipsoide(f"{name}_olho{sy}_pupila", (0.068, px, pz), (0.026, pr, pr * 1.12), M["pupila"])
        filho(pu, e)
        # brilho duplo (lê bem no celular): um grande no alto, um pequeno embaixo
        for k, (dy, dz, r) in enumerate(((0.032, 0.036, 0.024), (-0.03, -0.034, 0.012))):
            br = elipsoide(f"{name}_olho{sy}_brilho{k}", (0.092, px + dy, pz + dz), (0.008, r, r), M["brilho"])
            filho(br, e)
        if humor in ("preocupado", "bravo"):
            # pálpebra na cor da lata: calota de esfera cobrindo o alto do olho, inclinada
            p = calota(f"{name}_olho{sy}_palpebra", 1.0, 70, lat)
            p.scale = (0.092, ro * 1.03, ro * 1.07)
            tilt = (-0.38 if humor == "preocupado" else 0.42) * sy
            p.rotation_euler = (tilt, 0, 0)
            filho(p, e)
        objs.append(e)
        olhos.append(e)
    # boca: curva amostrada sobre a grade, colada na superfície
    zb = s["zb"] + 0.34
    largura = W * 0.28
    pts = []
    n = 9
    for k in range(n):
        t = -1 + 2 * k / (n - 1)
        if humor == "feliz":
            dz = -0.05 * (1 - t * t)
        elif humor == "preocupado":
            dz = 0.03 * (1 - t * t)
        elif humor == "bravo":
            dz = 0.012 * (1 - t * t)
        else:  # assustado: boca em "o"
            ang = math.pi * (k / (n - 1)) * 2
            pts.append((0.045 * math.cos(ang), zb + 0.045 * math.sin(ang)))
            continue
        pts.append((t * largura, zb + 0.03 + dz))
    p3 = []
    for y, z in pts:
        loc, nor = sup.raio((5, y, z), (-1, 0, 0))
        p3.append(loc + nor * 0.004)
    boca = tubo(f"{name}_boca", p3, 0.016, M["boca"])
    objs.append(boca)
    return {"objetos": objs, "olhos": olhos, "boca": boca}


# ================================================================ motos
def _anel_moto(W, zb, zt, ponta=0.0):
    W = W * (1 - 0.25 * ponta)
    h = zt - zb
    return [(0.0, zb), (W * 0.55, zb + 0.02 * h), (W, zb + 0.42 * h), (W * 0.93, zb + 0.78 * h),
            (W * 0.55, zt - 0.01), (0.0, zt)]


def _moto_corpo(name, est, mats, mat_seg, bojo=(0.03, 0.03)):
    """est = [(x, W, zb, zt), ...] de trás para a frente."""
    xs = [e[0] for e in est]
    aneis = [_anel_moto(e[1], e[2], e[3], 1.0 if i in (0, len(est) - 1) else 0.0) for i, e in enumerate(est)]
    return loft(name, xs, aneis, mats, mat_seg, bojo=bojo)


MOTOS = {
    # R, largura do pneu, eixos, carroceria [(x, meia-largura, fundo, topo)] de trás p/ frente, banco (x0, x1),
    # cabeça do garfo, altura do motor
    "street": dict(R=0.28, larg=0.17, xr=-0.48, xf=0.50, zc=0.33,
                   est=[(-0.70, 0.07, 0.70, 0.79), (-0.62, 0.09, 0.66, 0.81), (-0.46, 0.11, 0.60, 0.82),
                        (-0.22, 0.12, 0.57, 0.82), (-0.04, 0.13, 0.59, 0.84), (0.06, 0.155, 0.62, 0.91),
                        (0.20, 0.165, 0.65, 0.95), (0.31, 0.135, 0.71, 0.93), (0.37, 0.09, 0.77, 0.90)],
                   banco=(-0.54, -0.02), cabeca=(0.40, 0.99)),
    "trail": dict(R=0.31, larg=0.17, xr=-0.52, xf=0.56, zc=0.42,
                  est=[(-0.78, 0.065, 0.83, 0.90), (-0.70, 0.085, 0.79, 0.93), (-0.50, 0.10, 0.72, 0.94),
                       (-0.24, 0.11, 0.68, 0.95), (-0.04, 0.13, 0.68, 0.97), (0.05, 0.18, 0.68, 1.05),
                       (0.17, 0.20, 0.69, 1.10), (0.29, 0.19, 0.74, 1.09), (0.37, 0.12, 0.84, 1.03)],
                  banco=(-0.64, 0.02), cabeca=(0.42, 1.10)),
    "cub": dict(R=0.24, larg=0.155, xr=-0.46, xf=0.54, zc=0.24,
                est=[(-0.70, 0.09, 0.58, 0.67), (-0.62, 0.13, 0.55, 0.73), (-0.44, 0.16, 0.54, 0.75),
                     (-0.28, 0.16, 0.48, 0.74), (-0.16, 0.16, 0.32, 0.57), (-0.06, 0.17, 0.27, 0.42),
                     (0.04, 0.19, 0.27, 0.45), (0.12, 0.26, 0.28, 0.62), (0.20, 0.30, 0.30, 0.88),
                     (0.28, 0.29, 0.34, 0.96), (0.33, 0.22, 0.40, 0.97)],
                banco=(-0.60, -0.16), cabeca=(0.37, 0.98)),
}


def moto(name, M, tipo="street", cor="vermelho", bau=False, estilo="chibi", escala=0.5):
    """Moto de brinquedo de vinil. tipo: street (a "160 de todo dia") | cub (motoneta 110/125) | trail.
    bau=True põe o baú de entregador (laranja com faixa refletiva) na grelha.
    estilo="real": variante adulta (CG 160 / Bros / Biz em proporção real, reduzida por `escala`).
    Devolve dict(raiz, rodas, lataria, rosto=None, corpo, partes)."""
    if estilo == "real":
        return _moto_real(name, M, tipo, cor, escala)
    materiais(M)
    lat = lataria_mat(M, cor)
    P = MOTOS[tipo]
    R, larg, xr, xf, zc, est, banco = (P[k] for k in ("R", "larg", "xr", "xf", "zc", "est", "banco"))
    cab = Vector((P["cabeca"][0], 0, P["cabeca"][1]))
    root = vazio(name)
    partes, lataria = [], []

    def add(o, lata=False):
        filho(o, root)
        partes.append(o)
        if lata:
            lataria.append(o)
        return o

    # ---- carroceria (tanque + banco + rabeta, ou escudo + assoalho + traseira na cub): uma malha só
    xs = [e[0] for e in est]

    def mat_seg(i, j):
        if i < 0 or i >= len(xs) - 1:
            return 0
        xm = (xs[i] + xs[i + 1]) / 2
        return 1 if (banco[0] <= xm <= banco[1] and j >= 3) else 0

    corpo = add(_moto_corpo(name + "_corpo", est, [lat, M["banco"]], mat_seg), True)

    # ---- rodas
    rodas = []
    for lado, x in (("t", xr), ("d", xf)):
        rd = roda(f"{name}_roda_{lado}", M, R, larg)
        filho(rd, root, (x, 0, R))
        rodas.append(rd)

    # ---- garfo, mesa e guidão (tudo amarrado na cabeça)
    yg = larg / 2 + 0.03
    for sy in (1, -1):
        add(tubo(f"{name}_garfo{sy}", [(xf, sy * yg, R), (cab.x, sy * yg, cab.z + 0.01)], 0.024, M["cromo"],
                 suave=False))
        add(elipsoide(f"{name}_cubo_d{sy}", (xf, sy * (yg + 0.005), R), (0.035, 0.02, 0.035), M["plastico"]))
    mesa = add(caixa(name + "_mesa", (cab.x - 0.01, 0, cab.z + 0.02), (0.09, 2 * yg + 0.07, 0.045),
                     M["plastico"], raio=0.45))
    gz = cab.z + 0.05
    gl = 0.27 if tipo != "trail" else 0.31
    gx = cab.x - 0.02
    add(tubo(f"{name}_guidao", [(gx - 0.09, -gl, gz + 0.05), (gx - 0.03, -gl * 0.55, gz + 0.02), (gx, 0, gz),
                                (gx - 0.03, gl * 0.55, gz + 0.02), (gx - 0.09, gl, gz + 0.05)], 0.017, M["plastico"]))
    for sy in (1, -1):
        add(tubo(f"{name}_manopla{sy}", [(gx - 0.07, sy * (gl - 0.08), gz + 0.042),
                                          (gx - 0.095, sy * (gl + 0.005), gz + 0.052)], 0.025, M["banco"],
                 suave=False))
        add(tubo(f"{name}_haste{sy}", [(gx - 0.035, sy * gl * 0.5, gz + 0.02), (gx - 0.05, sy * gl * 0.6, gz + 0.12)],
                 0.008, M["plastico"], suave=False))
        add(elipsoide(f"{name}_espelho{sy}", (gx - 0.052, sy * gl * 0.62, gz + 0.145), (0.016, 0.042, 0.03),
                      M["plastico"]))

    # ---- farol e para-lama dianteiro
    if tipo == "cub":
        add(caixa(name + "_carenagem", (cab.x + 0.0, 0, gz + 0.01), (0.20, 0.30, 0.11), lat, raio=0.45), True)
        add(elipsoide(name + "_farol", (cab.x + 0.095, 0, gz + 0.005), (0.022, 0.085, 0.04), M["farol"]))
        add(_paralama(name + "_paralama_d", R, 0.14, (-15, 105), lat, (xf, 0, R)), True)
        for sy in (1, -1):
            add(elipsoide(f"{name}_pisca_d{sy}", (cab.x + 0.07, sy * 0.13, gz + 0.0), (0.022, 0.022, 0.016),
                          M["pisca"]))
    else:
        fz = cab.z - 0.04
        add(elipsoide(name + "_farol_concha", (cab.x + 0.075, 0, fz), (0.07, 0.085, 0.085), lat), True)
        add(elipsoide(name + "_farol", (cab.x + 0.13, 0, fz), (0.024, 0.068, 0.068), M["farol"]))
        for sy in (1, -1):
            add(elipsoide(f"{name}_pisca_d{sy}", (cab.x + 0.05, sy * 0.125, fz - 0.01), (0.022, 0.02, 0.016),
                          M["pisca"]))
        if tipo == "street":
            add(_paralama(name + "_paralama_d", R, 0.12, (15, 100), lat, (xf, 0, R)), True)
        else:  # trail: para-lama alto, preso no pé da mesa, abaixo do farol
            # "bico": sai de baixo do farol, abraçado pelo garfo, e desce para a frente afinando
            p0 = Vector((cab.x - 0.03, 0, cab.z - 0.15))
            pts = [Vector((0, 0, 0)), Vector((0.17, 0, -0.05)), Vector((0.33, 0, -0.14))]
            pl = tubo(name + "_paralama_d", pts, [0.06, 0.022], lat)
            pl.scale = (1, 1.6, 0.6)
            pl.location = p0
            add(pl, True)

    # ---- motor, quadro, escape
    if tipo == "cub":
        mot = add(caixa(name + "_motor", (-0.10, 0, zc), (0.30, 0.17, 0.17), M["motor"], raio=0.4))
        esc = [(0.02, -0.07, zc - 0.03), (-0.08, -0.13, zc - 0.07), (-0.30, -0.14, zc - 0.04)]
        mufla = [(-0.26, -0.15, zc - 0.03), (-0.56, -0.15, zc + 0.04)]
    else:
        mot = add(caixa(name + "_motor", (0.05, 0, zc + 0.02), (0.32, 0.18, 0.24), M["motor"], raio=0.35))
        cil = add(caixa(name + "_cilindro", (0.15, 0, zc + 0.19), (0.13, 0.13, 0.20), M["motor"], raio=0.35))
        cil.rotation_euler = (0, math.radians(-22), 0)
        add(tubo(name + "_quadro", [cab + Vector((-0.04, 0, -0.07)), Vector((0.25, 0, zc + 0.30)),
                                    Vector((0.17, 0, zc + 0.12))], 0.028, M["plastico"]))
        if tipo == "street":
            esc = [(0.22, -0.05, zc + 0.10), (0.24, -0.12, zc - 0.06), (0.04, -0.15, zc - 0.13),
                   (-0.20, -0.18, zc - 0.10)]
            mufla = [(-0.16, -0.19, zc - 0.10), (-0.50, -0.19, zc - 0.02)]
        else:
            esc = [(0.22, -0.05, zc + 0.10), (0.22, -0.12, zc - 0.05), (0.02, -0.15, zc - 0.04),
                   (-0.24, -0.18, zc + 0.14)]
            mufla = [(-0.20, -0.19, zc + 0.13), (-0.54, -0.19, zc + 0.30)]
    add(tubo(name + "_escape", esc, 0.022, M["cromo"]))
    add(tubo(name + "_silencioso", mufla, [0.046, 0.040], M["cromo"], suave=False))

    # ---- balança e amortecedores
    piv = Vector((mot.location.x - 0.13, 0, R + 0.06 if tipo != "cub" else zc + 0.02))
    ztopo_amort = _interp([(e[0], e[2]) for e in est], xr + 0.02) + 0.03
    for sy in (1, -1):
        y = sy * (larg / 2 + 0.035)
        add(tubo(f"{name}_balanca{sy}", [(xr, y, R), (piv.x, y * 0.85, piv.z)], 0.02, M["plastico"], suave=False))
        add(elipsoide(f"{name}_cubo_t{sy}", (xr, y + sy * 0.005, R), (0.035, 0.02, 0.035), M["plastico"]))
        if tipo != "cub":
            a0 = Vector((xr + 0.07, y, R + 0.03))
            a1 = Vector((xr + 0.01, y, ztopo_amort))
            add(tubo(f"{name}_amortecedor{sy}", [a0, a1], 0.016, M["cromo"], suave=False))
            add(tubo(f"{name}_mola{sy}", [a0.lerp(a1, 0.3), a0.lerp(a1, 0.85)], 0.028, M["pisca"], suave=False))

    # ---- traseira: para-lama em arco com a placa, lanterna, piscas, grelha
    if tipo != "cub":
        add(_paralama(name + "_paralama_t", R, 0.12, (95, 160), M["plastico"], (xr, 0, R)))
        ang = math.radians(150)
        nrm = Vector((math.cos(ang), 0, math.sin(ang)))
        pq = placa(name + "_placa", M, larg=0.15, alt=0.11, esp=0.014)
        pq.location = Vector((xr, 0, R)) + nrm * (R + 0.06)
        _orientar(pq, nrm)
        add(pq)
    else:
        pq = placa(name + "_placa", M, larg=0.15, alt=0.11, esp=0.014)
        nrm = Vector((-0.94, 0, -0.34))
        pq.location = Vector((est[0][0] + 0.01, 0, est[0][2] - 0.02))
        _orientar(pq, nrm)
        add(pq)
    xt, zt0, zt1 = est[0][0], est[0][2], est[0][3]
    add(elipsoide(name + "_lanterna", (xt - 0.012, 0, (zt0 + zt1) / 2), (0.028, 0.05, 0.028), M["lanterna"]))
    for sy in (1, -1):
        add(elipsoide(f"{name}_pisca_t{sy}", (xt + 0.04, sy * (est[0][1] + 0.025), zt0 + 0.02), (0.022, 0.02, 0.016),
                      M["pisca"]))
    topo_x = [(e[0], e[3]) for e in est]
    gw = 0.085
    if not bau:  # grelha pequena apoiada no alto da rabeta, atrás do banco
        gx0, gx1 = xt + 0.03, banco[0] + 0.05
        gz_ = _interp(topo_x, (gx0 + gx1) / 2) + 0.012
        add(tubo(name + "_grelha", [(gx1, gw, gz_ - 0.01), (gx0 + 0.04, gw, gz_), (gx0, gw * 0.55, gz_),
                                    (gx0, -gw * 0.55, gz_), (gx0 + 0.04, -gw, gz_), (gx1, -gw, gz_ - 0.01)],
                 0.013, M["plastico"]))
    else:  # bagageiro de entregador: grelha plana que passa da rabeta, com 2 escoras, e o baú em cima
        gw = 0.12
        gx0, gx1 = xt - 0.15, banco[0] + 0.03
        gz_ = max(_interp(topo_x, x) for x in (xt, (xt + gx1) / 2, gx1)) + 0.03
        add(tubo(name + "_grelha", [(gx1, gw, gz_), (gx0 + 0.04, gw, gz_), (gx0, gw * 0.6, gz_),
                                    (gx0, -gw * 0.6, gz_), (gx0 + 0.04, -gw, gz_), (gx1, -gw, gz_),
                                    (gx1, gw, gz_)], 0.014, M["plastico"], suave=False))
        for xx in (gx0 + 0.09, (gx0 + gx1) / 2 + 0.04):
            add(tubo(f"{name}_grelha_trav{xx:.2f}", [(xx, gw, gz_), (xx, -gw, gz_)], 0.011, M["plastico"],
                     suave=False))
        for sy in (1, -1):
            xe = xt + 0.08
            add(tubo(f"{name}_escora{sy}", [(gx0 + 0.06, sy * gw * 0.95, gz_),
                                             (xe, sy * gw * 0.75, _interp(topo_x, xe) - 0.05)],
                     0.013, M["plastico"], suave=False))
        bx = (gx0 + gx1) / 2
        hb = 0.34
        add(caixa(name + "_bau", (bx, 0, gz_ + 0.012 + hb / 2), (0.36, 0.38, hb), M["bau"], raio=0.13))
        add(caixa(name + "_bau_faixa", (bx - 0.182, 0, gz_ + 0.012 + hb * 0.4), (0.012, 0.28, 0.04),
                  M["refletivo"], raio=0.45))
    return {"raiz": root, "rodas": rodas, "lataria": lataria, "rosto": None, "corpo": corpo, "partes": partes}


def _paralama(name, R, larg, angulos, m, loc=(0, 0, 0)):
    """Para-lama em arco (fita grossa e lisa) em volta de uma roda de raio R, centro em loc. angulos em graus a
    partir de +x no sentido de +z (0 = frente, 90 = em cima, 180 = atrás)."""
    a0, a1 = (math.radians(a) for a in angulos)
    rr = R + 0.045
    n = 12
    pts = [(rr * math.cos(a0 + (a1 - a0) * k / n), 0, rr * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
    o = tubo(name, pts, 0.02, m, suave=False)
    o.scale = (1, larg / 0.04, 1)
    o.location = loc
    return o


# ######################################################################################################
# ESTILO "REAL" — variante adulta (anúncio de montadora). Mesma técnica (gaiola única + subdivisão + raycast),
# proporções reais em METROS, montadas em escala 1:1 e reduzidas pela raiz (escala=0.5 → 1:2 no mundo do motor).
# Sem marca, sem rosto. Arquétipos: hatch (Polo/HB20/Onix), suv (T-Cross/Creta), picape (Strada), seda.
# ######################################################################################################
REAL_COR = {"vermelho": "#D7262E", "grafite": "#4A5058", "branco": "#F2F2EE", "azul": "#1F4E9C",
            "prata": "#B9BEC4", "preto": "#16181B"}


def _no(nt, tipo, **inp):
    n = nt.nodes.new(tipo)
    for k, v in inp.items():
        n.inputs[k].default_value = v
    return n


def pintura(name, hexcol, metal=0.15, flocos=True):
    """Pintura automotiva: base viva, verniz (coat 1.0, coat roughness 0.03), roughness 0.25, metálico leve e
    "flocos" (Noise fino no normal da base, por baixo do verniz liso)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexcol)
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.03
    b.inputs["Coat IOR"].default_value = 1.5
    if flocos:
        nz = _no(nt, "ShaderNodeTexNoise", Scale=900.0, Detail=1.0)
        bp = _no(nt, "ShaderNodeBump", Strength=0.05, Distance=0.02)
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def _pbr(name, hexcol, rough, metal=0.0, coat=0.0, spec=0.5, emit=0.0, emit_cor=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexcol)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.05
    b.inputs["Specular IOR Level"].default_value = spec
    if emit:
        b.inputs["Emission Color"].default_value = lin(emit_cor or hexcol)
        b.inputs["Emission Strength"].default_value = emit
    return m


REAL_BASE = {  # nome: (cor, rough, metal, coat, spec, emit)
    "r_vidro": ("#151C24", 0.03, 0.0, 0.0, 1.0, 0.0),
    "r_plastico": ("#1A1C1F", 0.62, 0.0, 0.0, 0.4, 0.0),
    "r_preto_brilho": ("#0C0D0F", 0.12, 0.0, 1.0, 0.6, 0.0),
    "r_borracha": ("#151618", 0.82, 0.0, 0.0, 0.3, 0.0),
    "r_flanco": ("#2A2C30", 0.55, 0.0, 0.0, 0.4, 0.0),
    "r_aluminio": ("#C9CED4", 0.18, 1.0, 0.3, 0.5, 0.0),
    "r_aluminio_escuro": ("#5E646B", 0.3, 1.0, 0.2, 0.5, 0.0),
    "r_cromo": ("#E6E9EC", 0.06, 1.0, 0.0, 0.5, 0.0),
    "r_disco": ("#6D7176", 0.35, 1.0, 0.0, 0.5, 0.0),
    "r_farol_lente": ("#10161C", 0.03, 0.0, 1.0, 0.9, 0.0),
    "r_farol_refletor": ("#D9DEE3", 0.12, 1.0, 0.0, 0.5, 0.0),
    "r_drl": ("#F2F6FF", 0.2, 0.0, 0.0, 0.5, 6.0),
    "r_lanterna": ("#7A0B12", 0.06, 0.0, 1.0, 0.8, 0.6),
    "r_lanterna_luz": ("#FF2A2A", 0.2, 0.0, 0.0, 0.5, 3.0),
    "r_pisca": ("#E07A12", 0.1, 0.0, 1.0, 0.6, 0.3),
    "r_placa": ("#F4F4F0", 0.35, 0.0, 0.3, 0.5, 0.0),
    "r_placa_faixa": ("#1F4FA3", 0.35, 0.0, 0.3, 0.5, 0.0),
    "r_junta": ("#08090A", 0.9, 0.0, 0.0, 0.1, 0.0),
    "r_banco": ("#141517", 0.55, 0.0, 0.2, 0.4, 0.0),
    "r_motor": ("#3B3F44", 0.35, 0.8, 0.0, 0.5, 0.0),
    "r_motor_claro": ("#8D9399", 0.28, 1.0, 0.0, 0.5, 0.0),
    "r_corrente": ("#2A2B2D", 0.4, 0.9, 0.0, 0.5, 0.0),
    "r_painel": ("#0E1013", 0.2, 0.0, 0.8, 0.6, 0.0),
}


def materiais_real(M):
    for n, (c, r, me, co, sp, e) in REAL_BASE.items():
        if n not in M:
            M[n] = _pbr("v3_" + n, c, r, me, co, sp, e)
    for n in ("placa", "placa_faixa"):   # placa() usa estas chaves
        M.setdefault(n, M["r_" + n])
    return M


def pintura_mat(M, cor):
    hx = REAL_COR.get(cor, LATARIA.get(cor, cor))
    k = "pint_" + hx.lstrip("#")
    if k not in M:
        M[k] = pintura("v3_" + k, hx)
    return M[k]


def _liso_angulo(o, ang=40):
    me = o.data
    me.shade_smooth()
    if hasattr(me, "set_sharp_from_angle"):
        me.set_sharp_from_angle(angle=math.radians(ang))
    return o


def fita(name, sup, amostras, larg, esp, m, embute=0.004, perfil=None):
    """Faixa colada na superfície (farol em lâmina, lanterna, grade, junta de porta…). amostras = [(origem,
    direção)], raycast em cada uma; a faixa fica perpendicular à curva e à normal, com espessura esp para fora.
    larg = largura (número ou função t->largura); perfil(t) desloca a faixa ao longo da normal (abaulado)."""
    pts = []
    for o, d in amostras:
        loc, nor = sup.raio(o, d)
        if loc is not None:
            pts.append((loc, nor))
    if len(pts) < 2:
        return None
    bm = bmesh.new()
    rings = []
    n = len(pts)
    for i, (loc, nor) in enumerate(pts):
        t = i / (n - 1)
        a = pts[max(i - 1, 0)][0]
        b2 = pts[min(i + 1, n - 1)][0]
        tg = (b2 - a).normalized()
        side = nor.cross(tg).normalized()
        w = (larg(t) if callable(larg) else larg) / 2
        e = esp + (perfil(t) if perfil else 0.0)
        rings.append([bm.verts.new(loc + side * w + nor * e), bm.verts.new(loc - side * w + nor * e),
                      bm.verts.new(loc - side * w - nor * embute), bm.verts.new(loc + side * w - nor * embute)])
    for i in range(n - 1):
        a, b2 = rings[i], rings[i + 1]
        for k in range(4):
            k2 = (k + 1) % 4
            bm.faces.new([a[k], a[k2], b2[k2], b2[k]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _obj(name, bm, m)
    return _liso_angulo(o, 35)


def _canto(XF, sy, y, z, t_canto, sx=1):
    """Raio que varre a frente (sx=1) ou a traseira (sx=-1) e dobra a quina: t_canto 0 = reto, 1 = pela lateral."""
    d = Vector((-sx * (1 - t_canto), -sy * t_canto * 1.2, 0)).normalized()
    alvo = Vector((XF - sx * 0.25 * t_canto, sy * y, z))
    return alvo - d * 3.0, d


# ---------------------------------------------------------------- rodas reais
def roda_real(name, M, R=0.31, larg=0.195, aro_r=0.19, raios=5, moto=False):
    """Pneu com banda (2 sulcos) e flanco + aro de liga de N raios + disco de freio. Eixo y, centro na origem."""
    root = vazio(name)
    w = larg / 2
    if moto:   # pneu de moto: banda redonda
        meio = [(R, 0.0, 0)] + [(R - (1 - math.cos(a)) * w * 0.9, math.sin(a) * w, 0)
                                for a in (math.radians(v) for v in (20, 40, 60, 75))]
        flanco = [(R - w * 1.05, w * 0.98, 1), ((R + aro_r) / 2, w * 0.92, 1), (aro_r + 0.018, w * 0.7, 1),
                  (aro_r + 0.004, w * 0.62, 1)]
    else:
        g = 0.007
        meio = [(R, 0.0, 0), (R, w * 0.14, 0), (R - g, w * 0.15, 0), (R - g, w * 0.24, 0), (R, w * 0.25, 0),
                (R, w * 0.62, 0), (R - g, w * 0.63, 0), (R - g, w * 0.70, 0), (R, w * 0.71, 0), (R, w * 0.86, 0),
                (R - 0.008, w * 0.96, 0), (R - 0.025, w * 1.0, 1)]
        flanco = [(R - 0.06, w * 1.02, 1), ((R + aro_r) / 2 + 0.01, w * 1.0, 1), (aro_r + 0.03, w * 0.92, 1),
                  (aro_r + 0.006, w * 0.84, 1)]
    meia = meio + flanco
    perfil = [(r, -y, mi) for (r, y, mi) in reversed(meia[1:])] + meia
    # material do trecho seguinte (lado de trás espelhado)
    pf = []
    for i, (r, y, mi) in enumerate(perfil):
        nxt = perfil[i + 1][2] if i + 1 < len(perfil) else mi
        pf.append((r, y, max(mi, nxt) if y < 0 else mi))
    pneu = torno(name + "_pneu", pf, [M["r_borracha"], M["r_flanco"]], seg=96)
    filho(pneu, root)
    yb = (w * 0.84) if not moto else w * 0.62
    # aro: borda (lábio) + tambor
    aro = torno(name + "_aro", [(aro_r + 0.012, yb, 0), (aro_r + 0.012, yb - 0.008, 0), (aro_r - 0.006, yb - 0.014, 0),
                                (aro_r - 0.012, yb - 0.03, 1), (aro_r - 0.012, -yb + 0.02, 1),
                                (aro_r + 0.012, -yb, 1), (aro_r + 0.012, -yb - 0.004, 1)],
                [M["r_aluminio"], M["r_aluminio_escuro"]], seg=96)
    filho(aro, root)
    # fundo escuro atrás dos raios + disco de freio
    if raios and not moto:
        filho(torno(name + "_fundo", [(0.0, -0.01, 0), (aro_r - 0.01, -0.01, 0)], [M["r_plastico"]], seg=48), root)
    disco_r = aro_r * (0.78 if not moto else 0.75)
    ydisc = yb - 0.06 if not moto else w * 0.4
    filho(torno(name + "_disco", [(disco_r * 0.45, ydisc, 0), (disco_r, ydisc, 0), (disco_r, ydisc - 0.012, 0),
                                  (disco_r * 0.45, ydisc - 0.012, 0)], [M["r_disco"]], seg=64), root)
    # cubo + raios
    yc = yb - 0.012
    cubo = None if not raios else torno(name + "_cubo", [(0.0, yc + 0.006, 1), (0.03, yc + 0.006, 1), (0.034, yc, 0), (0.06, yc - 0.004, 0),
                                  (0.065, yc - 0.03, 0), (0.0, yc - 0.03, 0)],
                 [M["r_aluminio"], M["r_preto_brilho"]], seg=48)
    if cubo:
        filho(cubo, root)
    comp = aro_r - 0.05
    if raios == 0:   # roda raiada (arame): 32 raios cruzados entre as flanges do cubo e o aro
        for k in range(32):
            a = 2 * math.pi * k / 32
            lado = 1 if k % 2 else -1
            a0 = a + lado * 0.35
            p0 = Vector((math.sin(a0) * 0.04, lado * 0.035, math.cos(a0) * 0.04))
            p1 = Vector((math.sin(a) * (aro_r - 0.012), lado * 0.008, math.cos(a) * (aro_r - 0.012)))
            filho(tubo(f"{name}_arame{k}", [p0, p1], 0.0022, M["r_cromo"], seg=6, suave=False, tampa=False), root)
        filho(torno(name + "_cubo_arame", [(0.0, 0.05, 0), (0.035, 0.05, 0), (0.048, 0.04, 0), (0.048, -0.04, 0),
                                           (0.035, -0.05, 0), (0.0, -0.05, 0)], [M["r_aluminio"]], seg=32), root)
    for k in range(raios):
        a = 2 * math.pi * k / raios
        if moto:
            rr = caixa(f"{name}_raio{k}", (0, 0, 0), (0.016, 0.012, comp + 0.02), M["r_aluminio_escuro"], raio=0.3)
        else:
            rr = caixa(f"{name}_raio{k}", (0, 0, 0), (0.046, 0.024, comp + 0.02), M["r_aluminio"], raio=0.25)
        mid = 0.055 + comp / 2
        rr.location = (math.sin(a) * mid, yc - 0.012 - (0.006 if not moto else 0.0), math.cos(a) * mid)
        rr.rotation_euler = (0, a, 0)
        filho(rr, root)
    return root


# ---------------------------------------------------------------- carros reais
def _spec_real(tipo):
    """Arquétipos brasileiros atuais (medidas reais em metros). topo = perfil do alto [(x, z, material do trecho
    seguinte)]; janelas = vidro lateral (x0, x1); portas = x das juntas; kick = quanto a cintura sobe até a traseira."""
    s = dict(R=0.32, larg=0.205, aro=0.216, W=0.875, zb=0.19, belt=1.00, roof=1.46, tumble=0.14,
             cover=False, clad=False, rails=False, santo=False, spoiler=False, pilar_preto=False, kick=0.0)
    if tipo == "hatch":       # Polo / HB20 / Onix: 4,05 x 1,75 x 1,47 m, aro 17
        s.update(wb=2.56, fr=0.80, tr=0.62, kick=0.07, spoiler=True)
        P = lambda XF, XR: dict(
            topo=[(XR, 0.98, "lata"), (XR + 0.12, 1.08, "vidro"), (XR + 0.56, 1.40, "teto"), (0.40, 1.46, "vidro"),
                  (1.18, 1.03, "lata"), (XF - 0.20, 0.96, "lata"), (XF - 0.05, 0.90, "lata"), (XF, 0.84, None)],
            janelas=[(XR + 0.98, -0.08), (0.02, 1.12)], portas=[0.92, -0.06, -0.98])
    elif tipo == "suv":       # T-Cross / Creta: 4,15 x 1,76 x 1,60 m, vão livre alto
        s.update(wb=2.65, fr=0.85, tr=0.64, W=0.885, R=0.345, larg=0.215, aro=0.216, zb=0.27, belt=1.09,
                 roof=1.61, tumble=0.12, clad=True, rails=True, pilar_preto=True, kick=0.05, spoiler=True)
        P = lambda XF, XR: dict(
            topo=[(XR, 1.07, "lata"), (XR + 0.10, 1.17, "vidro"), (XR + 0.36, 1.55, "teto"), (0.44, 1.61, "vidro"),
                  (1.22, 1.13, "lata"), (XF - 0.22, 1.06, "lata"), (XF - 0.05, 0.99, "lata"), (XF, 0.93, None)],
            janelas=[(XR + 0.62, -0.08), (0.02, 1.15)], portas=[0.96, -0.06, -1.02])
    elif tipo == "picape":    # Strada cabine simples (2 portas) com capota marítima: 4,45 m, frente alta
        s.update(wb=2.74, fr=0.84, tr=0.82, W=0.865, R=0.33, larg=0.205, zb=0.24, belt=1.03, roof=1.55,
                 cover=True, santo=True, xc=-0.36)
        P = lambda XF, XR: dict(
            topo=[(XR, 1.05, "capota"), (s["xc"] - 0.09, 1.05, "lata"), (s["xc"] - 0.07, 1.14, "vidro"),
                  (s["xc"] + 0.03, 1.52, "teto"), (0.38, 1.55, "vidro"), (1.15, 1.08, "lata"),
                  (XF - 0.22, 1.01, "lata"), (XF - 0.05, 0.94, "lata"), (XF, 0.88, None)],
            janelas=[(s["xc"] + 0.12, 1.10)], portas=[0.94, s["xc"] + 0.05])
    elif tipo == "seda":      # Virtus / Onix Plus: 4,48 m, terceiro volume curto
        s.update(wb=2.65, fr=0.82, tr=0.98, belt=0.99, roof=1.46, kick=0.05)
        P = lambda XF, XR: dict(
            topo=[(XR, 0.99, "lata"), (XR + 0.10, 1.05, "lata"), (XR + 0.40, 1.07, "vidro"), (XR + 1.02, 1.41, "teto"),
                  (0.40, 1.46, "vidro"), (1.17, 1.02, "lata"), (XF - 0.20, 0.95, "lata"), (XF - 0.05, 0.89, "lata"),
                  (XF, 0.83, None)],
            janelas=[(XR + 1.10, -0.08), (0.02, 1.11)], portas=[0.92, -0.06, -0.98])
    else:
        raise ValueError(tipo)
    s["xf"], s["xr"] = s["wb"] / 2, -s["wb"] / 2
    s["XF"], s["XR"] = s["xf"] + s["fr"], s["xr"] - s["tr"]
    s.update(P(s["XF"], s["XR"]))
    return s


def _fundo_real(s, x):
    R = s["R"]
    Ra = R + 0.032
    z = s["zb"]
    for xw in (s["xf"], s["xr"]):
        d = abs(x - xw)
        if d <= Ra:
            z = max(z, R + math.sqrt(max(Ra * Ra - d * d, 0)) + 0.012)
    return z


def _estacoes_real(s):
    Ra = s["R"] + 0.032
    xs = {s["XR"], s["XR"] + 0.10, s["XF"], s["XF"] - 0.10}
    xs.update(x for x, _, _ in s["topo"])
    for a, b in s["janelas"]:
        xs.update((a, b))
    for xw in (s["xf"], s["xr"]):
        for d in (-1.10, -1.03, -1.0, -0.92, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 0.92, 1.0, 1.03, 1.10):
            xs.add(xw + d * Ra)
    xs = sorted(x for x in xs if s["XR"] - 1e-6 <= x <= s["XF"] + 1e-6)
    out = []
    for x in xs:
        if out and x - out[-1] < 0.018:
            continue
        out.append(x)
    # nenhum vão maior que 0,35 m
    cheio = [out[0]]
    for x in out[1:]:
        n = int((x - cheio[-1]) / 0.35)
        if n:
            x0 = cheio[-1]
            for k in range(1, n + 1):
                cheio.append(x0 + (x - x0) * k / (n + 1))
        cheio.append(x)
    cheio[0], cheio[-1] = s["XR"], s["XF"]
    return cheio


def _belt_x(s, x):
    """Linha de cintura: sobe um pouco para trás (kick-up), desce acompanhando o capô/porta-malas."""
    sobe = s.get("kick", 0.0) * min(1.0, max(0.0, (0.3 - x) / (0.3 - s["XR"])))
    return min(s["belt"] + sobe, _interp(s["topo"], x) - 0.035)


def _anel_real(s, x, ponta=0.0):
    W = s["W"] * (1 - 0.045 * ponta)
    zb = _fundo_real(s, x) + 0.03 * ponta
    zt = _interp(s["topo"], x) - 0.02 * ponta
    belt = _belt_x(s, x) - 0.01 * ponta
    hc = s["roof"] - s["belt"]
    h = max(zt - belt, 0.035)
    f = min(1.0, max(0.0, (zt - s["belt"]) / hc))
    zs = min(zb + 0.07, belt - 0.30)
    zp = min(max(s["zb"] + 0.30, zs + 0.06), belt - 0.16)
    p5y = W - 0.035 - s["tumble"] * f
    return [
        (0.0, zb),
        (W - 0.07, zb),
        (W - 0.03, zs),
        (W, zp),
        (W - 0.025, belt),
        (W - 0.03 - 0.02 * f, belt + min(0.03, 0.35 * h)),
        (p5y, belt + 0.81 * h),
        (p5y - 0.05 - 0.07 * f, belt + 0.96 * h),
        (0.0, zt),
    ]


def _carro_real(name, M, tipo, cor, placa_on=True, nivel=2, escala=0.5):
    materiais(M)
    materiais_real(M)
    tinta = pintura_mat(M, cor)
    s = _spec_real(tipo)
    root = vazio(name)
    xs = _estacoes_real(s)
    aneis = [_anel_real(s, x, 1.0 if i in (0, len(xs) - 1) else 0.0) for i, x in enumerate(xs)]
    topo, jan = s["topo"], s["janelas"]
    PINT, VIDRO, PLAST, BRILHO = 0, 1, 2, 3
    S = len(xs)
    Ra = s["R"] + 0.032

    def arco(xm):
        return any(abs(xm - xw) <= Ra * 1.12 for xw in (s["xf"], s["xr"]))

    def mat_seg(i, j):
        if i == -1 or i == S - 1:
            return PLAST if j == 1 else PINT
        xm = (xs[i] + xs[i + 1]) / 2
        tg = _tag(topo, xm)
        if j in (6, 7) and tg == "vidro":
            return VIDRO
        if j in (6, 7) and tg == "capota":
            return PLAST
        if j == 5:
            if any(a <= xm <= b for a, b in jan):
                return VIDRO
            if len(jan) > 1 and jan[0][1] <= xm <= jan[1][0]:
                return BRILHO       # coluna B em preto brilhante
            if s["pilar_preto"] and xm < jan[0][0] and tg == "teto":
                return BRILHO       # coluna C/D preta: teto "flutuante"
        if j == 0:
            return PLAST
        if j == 1 and (i <= 1 or i >= S - 3):
            return PLAST           # parte de baixo dos para-choques
        if s["clad"] and (j == 1 or (j == 2 and arco(xm))):
            return PLAST
        return PINT

    corpo = loft(name + "_lata", xs, aneis, [tinta, M["r_vidro"], M["r_plastico"], M["r_preto_brilho"]], mat_seg,
                 crease={1: 0.6, 2: 0.95, 3: 0.35, 4: 0.75, 5: 0.5}, bojo=(0.05, 0.10), nivel=nivel)
    filho(corpo, root)

    R, larg = s["R"], s["larg"]
    W = s["W"]
    yi = W - larg - 0.06
    filho(caixa(name + "_forro", ((s["XF"] + s["XR"]) / 2, 0, (s["zb"] + 2 * R + 0.05) / 2 + 0.02),
                (s["XF"] - s["XR"] - 0.5, 2 * yi, 2 * R + 0.05 - s["zb"]), M["forro"], raio=0.2), root)
    rodas = []
    yw = W - larg / 2 + 0.012
    for lado, xw in (("d", s["xf"]), ("t", s["xr"])):
        for sy in (1, -1):
            rd = roda_real(f"{name}_roda_{lado}{'e' if sy > 0 else 'd'}", M, R, larg, s["aro"])
            if sy < 0:
                rd.rotation_euler = (0, 0, math.pi)
            filho(rd, root, (xw, sy * yw, R))
            rodas.append(rd)

    sup = Superficie(corpo)
    XF, XR = s["XF"], s["XR"]
    orn = []
    zfa = _interp(topo, XF - 0.20) - 0.075         # altura dos faróis: logo abaixo da borda do capô
    # ---- faróis em lâmina (carcaça escura + DRL de LED na borda de cima) e grade
    for sy in (1, -1):
        am = [_canto(XF, sy, W * (0.36 + 0.56 * t), zfa - 0.02 + 0.05 * t, max(0, (t - 0.55) / 0.45) ** 1.5)
              for t in [k / 16 for k in range(17)]]
        f = fita(f"{name}_farol{sy}", sup, am, lambda t: 0.05 + 0.045 * math.sin(math.pi * min(1, t * 1.3)),
                 0.004, M["r_farol_lente"])
        d = fita(f"{name}_drl{sy}", sup, [(o + Vector((0, 0, 0.032)), dd) for o, dd in am[1:]],
                 0.012, 0.007, M["r_drl"])
        r_ = fita(f"{name}_refletor{sy}", sup, [(o + Vector((0, 0, -0.008)), dd) for o, dd in am[1:9]],
                  0.035, 0.006, M["r_farol_refletor"])
        orn += [x for x in (f, d, r_) if x]
    zg = zfa - 0.15
    gr = fita(name + "_grade", sup, [((XF + 3, W * (-0.50 + 1.0 * k / 16), zg), (-1, 0, 0)) for k in range(17)],
              lambda t: 0.19 - 0.06 * abs(2 * t - 1) ** 2, 0.006, M["r_preto_brilho"])
    for q in range(3):   # filetes horizontais da grade
        fl = fita(f"{name}_grade_filete{q}", sup, [((XF + 3, W * (-0.43 + 0.86 * k / 14), zg - 0.04 + 0.04 * q),
                                                    (-1, 0, 0)) for k in range(15)], 0.008, 0.009,
                  M["r_aluminio_escuro"])
        if fl:
            orn.append(fl)
    friso = fita(name + "_friso", sup, [((XF + 3, W * (-0.40 + 0.80 * k / 12), zfa - 0.045), (-1, 0, 0))
                                         for k in range(13)], 0.012, 0.009, M["r_cromo"])
    zi = s["zb"] + 0.20
    tomada = fita(name + "_tomada", sup, [((XF + 3, W * (-0.62 + 1.24 * k / 16), zi), (-1, 0, 0)) for k in range(17)],
                  lambda t: 0.10 + 0.05 * math.sin(math.pi * t), 0.004, M["r_preto_brilho"], embute=0.02)
    orn += [x for x in (gr, friso, tomada) if x]
    for sy in (1, -1):   # entradas de ar verticais nos cantos do para-choque ("presas")
        cv = fita(f"{name}_canto_ar{sy}", sup, [((XF + 3, sy * W * 0.80, zi - 0.04 + 0.22 * k / 8), (-1, 0, 0))
                                                for k in range(9)], 0.05, 0.004, M["r_preto_brilho"], embute=0.02)
        if cv:
            orn.append(cv)
    for sy in (1, -1):   # faróis de neblina nas pontas da tomada
        nb = elipsoide(f"{name}_neblina{sy}", (0, 0, 0), (0.012, 0.045, 0.022), M["r_drl"])
        colar(nb, sup, (XF + 3, sy * W * 0.70, zi + 0.01), (-1, 0, 0), embute=0.004)
        orn.append(nb)
    # ---- lanternas traseiras (lâmina que dobra a quina)
    zl = _interp(topo, XR + 0.05) - 0.10
    for sy in (1, -1):
        am = [_canto(XR, sy, W * (0.40 + 0.52 * t), zl, max(0, (t - 0.5) / 0.5) ** 1.5, sx=-1)
              for t in [k / 14 for k in range(15)]]
        lt = fita(f"{name}_lanterna{sy}", sup, am, lambda t: 0.075 - 0.02 * t, 0.004, M["r_lanterna"])
        ll = fita(f"{name}_lanterna_luz{sy}", sup, [(o + Vector((0, 0, 0.012)), dd) for o, dd in am[2:]],
                  0.010, 0.007, M["r_lanterna_luz"])
        orn += [x for x in (lt, ll) if x]
    td = fita(name + "_difusor", sup, [((XR - 3, W * (-0.6 + 1.2 * k / 14), s["zb"] + 0.12), (1, 0, 0))
                                       for k in range(15)], 0.07, 0.002, M["r_plastico"], embute=0.02)
    if td:
        orn.append(td)
    # ---- juntas de porta (frisos finos escuros) e maçanetas
    portas = s["portas"]
    for k, xp in enumerate(portas):
        zt_ = _belt_x(s, xp) - 0.015
        z0 = max(_fundo_real(s, xp), s["zb"]) + 0.09
        for sy in (1, -1):
            am = [((xp - 0.02 * (zz - z0), sy * 3, zz), (0, -sy, 0)) for zz in
                  [z0 + (zt_ - z0) * q / 10 for q in range(11)]]
            j_ = fita(f"{name}_junta{k}{sy}", sup, am, 0.006, 0.0006, M["r_junta"], embute=0.004)
            if j_:
                orn.append(j_)
    for k in range(len(portas) - 1):
        xm = portas[k + 1] - 0.16          # maçaneta perto da borda de trás de cada porta
        for sy in (1, -1):
            mc = caixa(f"{name}_macaneta{k}{sy}", (0, 0, 0), (0.022, 0.13, 0.026), tinta, raio=0.45)
            colar(mc, sup, (xm, sy * 3, _belt_x(s, xm) - 0.085), (0, -sy, 0), embute=0.006)
            orn.append(mc)
    # ---- retrovisores: base preta + concha na cor
    xb = max(x for x, _, tg in topo[:-1] if tg == "lata" and x < XF - 0.3) - 0.10
    for sy in (1, -1):
        loc, nor = sup.raio((xb, sy * 3, _belt_x(s, xb) - 0.01), (0, -sy, 0))
        if loc is None:
            continue
        base = caixa(f"{name}_retro_base{sy}", loc + Vector((0, sy * 0.04, 0.02)), (0.12, 0.10, 0.07),
                     M["r_plastico"], raio=0.35)
        concha = caixa(f"{name}_retro{sy}", loc + Vector((-0.03, sy * 0.17, 0.07)), (0.13, 0.25, 0.15),
                       tinta, raio=0.42)
        concha.rotation_euler = (0, 0, -sy * math.radians(10))
        pisca = caixa(f"{name}_retro_pisca{sy}", loc + Vector((0.03, sy * 0.20, 0.03)), (0.012, 0.15, 0.014),
                      M["r_pisca"], raio=0.4)
        orn += [base, concha, pisca]
    # ---- placas Mercosul (sem letras)
    if placa_on:
        for lado, sx, z in (("d", 1, zi + 0.12), ("t", -1, zl - 0.25)):
            pl = placa(f"{name}_placa_{lado}", M, larg=0.40, alt=0.13, esp=0.012)
            loc, nor = sup.raio((sx * 5, 0, z), (-sx, 0, 0))
            if loc is not None:
                pl.location = loc + nor * 0.004
                pl.rotation_euler = (0, 0, 0 if sx > 0 else math.pi)
                orn.append(pl)
    # ---- barras de teto (SUV) e santo-antônio (picape)
    if s["rails"]:
        for sy in (1, -1):
            pts = []
            for x in (XR + 0.35, XR + 0.7, 0.2, 0.42):
                loc, _ = sup.raio((x, sy * (W - 0.20), 5), (0, 0, -1))
                pts.append(loc + Vector((0, 0, 0.035)))
            pts[0].z -= 0.03
            pts[-1].z -= 0.03
            orn.append(tubo(f"{name}_barra{sy}", pts, 0.016, M["r_aluminio_escuro"]))
    if s["santo"]:
        xs_ = s["xc"] - 0.25
        loc, _ = sup.raio((xs_, W - 0.08, 5), (0, 0, -1))
        z0 = loc.z - 0.01
        pts = [(xs_, W - 0.08, z0), (xs_, W - 0.09, z0 + 0.26), (xs_ + 0.02, W - 0.22, z0 + 0.32),
               (xs_ + 0.02, 0, z0 + 0.33)]
        pts = pts + [(p[0], -p[1], p[2]) for p in reversed(pts[:-1])]
        orn.append(tubo(name + "_santo", pts, 0.026, M["r_preto_brilho"]))
    # spoiler pequeno na borda do teto (hatch / SUV)
    if s["spoiler"]:
        x_sp = [x for x, _, tg in topo if tg == "teto"][0]
        loc, _ = sup.raio((x_sp + 0.04, 0, 5), (0, 0, -1))
        if loc is not None:
            sp = caixa(name + "_spoiler", loc + Vector((-0.07, 0, -0.004)), (0.22, 2 * W * 0.78, 0.035),
                       tinta, raio=0.45)
            sp.rotation_euler = (0, math.radians(9), 0)
            orn.append(sp)
    # antena tubarão
    loc, _ = sup.raio((XR + 0.55, 0, 5), (0, 0, -1))
    if loc is not None and tipo != "picape":
        orn.append(caixa(name + "_antena", loc + Vector((0, 0, 0.02)), (0.16, 0.06, 0.06), M["r_preto_brilho"],
                         raio=0.45))
    for o in orn:
        filho(o, root)
    root.scale = (escala, escala, escala)
    return {"raiz": root, "rodas": rodas, "lataria": [corpo], "rosto": None, "corpo": corpo,
            "partes": {"corpo": corpo, "ornamentos": orn}, "spec": s}


# ---------------------------------------------------------------- motos reais
MOTOS_REAL = {
    # medidas em metros. Rf/Rr = raio do pneu, lf/lr = largura, aro = raio do aro (18" = 0,229; 17" = 0,216;
    # 14" = 0,178), cab = topo da coluna de direção, zc = altura do motor, est = carroceria [(x, meia-larg., fundo,
    # topo)] de trás p/ frente, banco = (x0, x1)
    "street": dict(Rf=0.30, Rr=0.31, lf=0.08, lr=0.10, af=0.229, ar=0.229, xf=0.66, xr=-0.66, raios=6,
                   cab=(0.40, 1.02), zc=0.40, guidao=1.09,
                   est=[(-0.99, 0.045, 0.80, 0.86), (-0.90, 0.075, 0.77, 0.885), (-0.72, 0.115, 0.73, 0.875),
                        (-0.42, 0.14, 0.69, 0.855), (-0.16, 0.15, 0.71, 0.86), (-0.05, 0.14, 0.77, 0.89),
                        (0.07, 0.165, 0.75, 0.98), (0.21, 0.175, 0.75, 1.025), (0.33, 0.155, 0.80, 1.03),
                        (0.41, 0.095, 0.88, 1.00)],
                   banco=(-0.82, -0.09)),
    "trail": dict(Rf=0.34, Rr=0.32, lf=0.09, lr=0.11, af=0.241, ar=0.216, xf=0.68, xr=-0.68, raios=0,
                  cab=(0.42, 1.12), zc=0.47, guidao=1.22,
                  est=[(-1.00, 0.04, 0.90, 0.95), (-0.92, 0.07, 0.86, 0.975), (-0.72, 0.11, 0.81, 0.97),
                       (-0.42, 0.13, 0.77, 0.95), (-0.14, 0.14, 0.79, 0.955), (-0.04, 0.14, 0.83, 0.99),
                       (0.08, 0.17, 0.81, 1.07), (0.22, 0.18, 0.82, 1.11), (0.34, 0.16, 0.87, 1.11),
                       (0.42, 0.095, 0.95, 1.08)],
                  banco=(-0.84, -0.06)),
    "cub": dict(Rf=0.28, Rr=0.26, lf=0.065, lr=0.085, af=0.216, ar=0.178, xf=0.62, xr=-0.62, raios=5,
                cab=(0.40, 1.00), zc=0.27, guidao=1.04,
                est=[(-0.98, 0.07, 0.64, 0.71), (-0.90, 0.13, 0.59, 0.765), (-0.70, 0.17, 0.57, 0.79),
                     (-0.45, 0.17, 0.51, 0.79), (-0.29, 0.15, 0.41, 0.70), (-0.19, 0.13, 0.31, 0.43),
                     (0.02, 0.13, 0.29, 0.37), (0.12, 0.18, 0.30, 0.60), (0.20, 0.23, 0.32, 0.90),
                     (0.29, 0.23, 0.36, 0.98), (0.35, 0.17, 0.42, 1.00)],
                banco=(-0.82, -0.27)),
}


def _casco(pts):
    """Fecho convexo 2D (x, z) — contorno da corrente em volta da coroa e do pinhão."""
    pts = sorted(set(pts))
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p_ in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p_) <= 0:
            lo.pop()
        lo.append(p_)
    for p_ in reversed(pts):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p_) <= 0:
            hi.pop()
        hi.append(p_)
    return lo[:-1] + hi[:-1]


def _moto_real(name, M, tipo, cor, escala=0.5):
    materiais(M)
    materiais_real(M)
    tinta = pintura_mat(M, cor)
    P = MOTOS_REAL[tipo]
    Rf, Rr, xf, xr, zc, est, banco = (P[k] for k in ("Rf", "Rr", "xf", "xr", "zc", "est", "banco"))
    cab = Vector((P["cab"][0], 0, P["cab"][1]))
    root = vazio(name)
    partes, lataria = [], []
    preto, cromo, alu = M["r_preto_brilho"], M["r_cromo"], M["r_aluminio"]
    fosco = M["r_plastico"]

    def add(o, lata=False):
        if o is None:
            return None
        filho(o, root)
        partes.append(o)
        if lata:
            lataria.append(o)
        return o

    # ---- carroceria: tanque (vincos por crease) + banco + rabeta numa malha só
    xs = [e[0] for e in est]
    aneis = [_anel_moto(e[1], e[2], e[3], 1.0 if i in (0, len(est) - 1) else 0.0) for i, e in enumerate(est)]

    def mat_seg(i, j):
        if i < 0 or i >= len(xs) - 1:
            return 0
        xm = (xs[i] + xs[i + 1]) / 2
        if banco[0] <= xm <= banco[1] and j >= 3:
            return 1
        if tipo != "cub" and xm < banco[0] and j <= 1:
            return 2
        return 0

    corpo = add(loft(name + "_corpo", xs, aneis, [tinta, M["r_banco"], fosco], mat_seg,
                     crease={2: 0.55, 3: 0.35}, bojo=(0.02, 0.03)), True)

    # ---- rodas
    rodas = []
    for lado, x, R, l, a in (("t", xr, Rr, P["lr"], P["ar"]), ("d", xf, Rf, P["lf"], P["af"])):
        rd = roda_real(f"{name}_roda_{lado}", M, R, l, a, raios=P["raios"], moto=True)
        filho(rd, root, (x, 0, R))
        rodas.append(rd)

    # ---- garfo: bengalas cromadas em cima, botas de alumínio embaixo; mesa; guidão
    eixo = Vector((xf, 0, Rf))
    yg = P["lf"] / 2 + 0.035
    for sy in (1, -1):
        b0 = eixo + Vector((0, sy * yg, 0))
        b1 = cab + Vector((0, sy * yg, -0.04))
        meio = b0.lerp(b1, 0.42)
        add(tubo(f"{name}_bota{sy}", [b0 - (b1 - b0).normalized() * 0.03, meio], 0.026, alu, suave=False))
        add(tubo(f"{name}_bengala{sy}", [meio, b1], 0.019, cromo, suave=False))
        add(tubo(f"{name}_eixo_d{sy}", [eixo + Vector((0, sy * 0.01, 0)), eixo + Vector((0, sy * (yg + 0.02), 0))],
                 0.012, alu, suave=False))
    add(caixa(name + "_mesa", cab + Vector((0, 0, -0.03)), (0.10, 2 * yg + 0.07, 0.035), preto, raio=0.35))
    add(caixa(name + "_mesa_inf", cab.lerp(eixo, 0.22), (0.09, 2 * yg + 0.06, 0.03), preto, raio=0.35))
    gz, gx = P["guidao"], cab.x - 0.06
    gl = 0.36 if tipo != "trail" else 0.41
    add(tubo(name + "_guidao", [(gx - 0.10, -gl, gz + 0.04), (gx - 0.03, -gl * 0.6, gz + 0.01), (gx, 0, gz),
                                (gx - 0.03, gl * 0.6, gz + 0.01), (gx - 0.10, gl, gz + 0.04)], 0.011, preto))
    add(tubo(name + "_guidao_poste", [(cab.x - 0.01, 0, cab.z - 0.02), (gx, 0, gz)], 0.016, preto, suave=False))
    for sy in (1, -1):
        add(tubo(f"{name}_manopla{sy}", [(gx - 0.075, sy * (gl - 0.12), gz + 0.028),
                                          (gx - 0.105, sy * (gl + 0.005), gz + 0.042)], 0.017, M["r_borracha"],
                 suave=False))
        add(tubo(f"{name}_manete{sy}", [(gx - 0.04, sy * (gl - 0.13), gz + 0.035), (gx + 0.02, sy * (gl - 0.04),
                                                                                  gz + 0.02)],
                 0.005, alu, suave=False))
        add(caixa(f"{name}_punho{sy}", (gx - 0.06, sy * (gl - 0.15), gz + 0.025), (0.06, 0.05, 0.05), preto,
                  raio=0.35))
        ph = Vector((gx - 0.05, sy * gl * 0.68, gz + 0.03))
        topo_h = ph + Vector((-0.03, sy * 0.04, 0.15))
        add(tubo(f"{name}_haste_esp{sy}", [ph, topo_h], 0.0055, preto, suave=False))
        e = add(caixa(f"{name}_espelho{sy}", topo_h + Vector((0, sy * 0.035, 0.03)), (0.025, 0.13, 0.085), preto,
                      raio=0.45))
        e.rotation_euler = (math.radians(-8) * sy, 0, math.radians(12) * sy)
    # painel
    add(caixa(name + "_painel", (gx + 0.03, 0, gz + 0.045), (0.08, 0.16, 0.06), M["r_painel"], raio=0.3))

    # ---- farol e para-lama dianteiro por tipo
    if tipo == "cub":
        cowl = add(caixa(name + "_carenagem", (cab.x + 0.02, 0, gz - 0.005), (0.26, 0.40, 0.12), tinta, raio=0.4),
                   True)
        far = fita(name + "_farol", Superficie(cowl), [((3, y, 0.0), (-1, 0, 0))     # coordenadas da carenagem
                                                        for y in [-0.12 + 0.24 * k / 10 for k in range(11)]],
                   0.055, 0.004, M["r_farol_lente"])
        if far:
            far.location = cowl.location
            add(far)
        pl = _paralama(name + "_paralama_d", Rf - 0.01, P["lf"] + 0.04, (-25, 115), tinta, (xf, 0, Rf))
        add(pl, True)
    else:
        fz = cab.z - 0.10
        if tipo == "street":
            carc = add(caixa(name + "_farol_carenagem", (cab.x + 0.10, 0, fz), (0.16, 0.24, 0.20), tinta,
                             raio=0.42), True)
            carc.rotation_euler = (0, math.radians(-12), 0)
            add(elipsoide(name + "_farol", (cab.x + 0.175, 0, fz), (0.022, 0.095, 0.075), M["r_farol_lente"]))
            add(elipsoide(name + "_farol_refl", (cab.x + 0.168, 0, fz), (0.02, 0.08, 0.062), M["r_farol_refletor"]))
            add(_paralama(name + "_paralama_d", Rf - 0.005, P["lf"] + 0.045, (-15, 105), tinta, (xf, 0, Rf)), True)
        else:  # trail: carenagem de farol "bico" e para-lama alto
            carc = add(caixa(name + "_farol_carenagem", (cab.x + 0.09, 0, fz + 0.02), (0.14, 0.26, 0.26), tinta,
                             raio=0.4), True)
            carc.rotation_euler = (0, math.radians(-18), 0)
            add(elipsoide(name + "_farol", (cab.x + 0.15, 0, fz + 0.01), (0.02, 0.075, 0.06), M["r_farol_lente"]))
            p0 = Vector((xf - 0.16, 0, 2 * Rf + 0.09))
            pts = [Vector((0, 0, 0)), Vector((0.20, 0, -0.01)), Vector((0.40, 0, -0.07))]
            pl = tubo(name + "_paralama_d", pts, [0.05, 0.02], tinta)
            pl.scale = (1, 1.7, 0.42)
            pl.location = p0
            add(pl, True)
        for sy in (1, -1):
            add(elipsoide(f"{name}_pisca_d{sy}", (cab.x + 0.07, sy * 0.17, fz - 0.01), (0.03, 0.022, 0.018),
                          M["r_pisca"]))

    # ---- quadro, motor com aletas, tampa lateral, escape
    if tipo == "cub":
        mot = add(caixa(name + "_carter", (-0.12, 0, zc), (0.36, 0.24, 0.20), M["r_motor"], raio=0.3))
        cil_c, cil_ang = Vector((0.14, 0, zc + 0.02)), math.radians(80)
    else:
        mot = add(caixa(name + "_carter", (-0.02, 0, zc), (0.36, 0.25, 0.26), M["r_motor"], raio=0.3))
        cil_c, cil_ang = Vector((0.15, 0, zc + 0.17)), math.radians(18)
        add(tubo(name + "_quadro", [cab + Vector((-0.03, 0, -0.10)), Vector((0.26, 0, zc + 0.36)),
                                    Vector((0.20, 0, zc + 0.10))], 0.022, preto))
        add(tubo(name + "_quadro_sup", [cab + Vector((-0.05, 0, -0.06)), Vector((-0.05, 0, est[4][2] - 0.02)),
                                        Vector((-0.20, 0, zc + 0.05))], 0.02, preto))
    # cilindro: aletas empilhadas ao longo do eixo inclinado
    eixo_c = Vector((math.sin(cil_ang), 0, math.cos(cil_ang)))
    for k in range(7):
        c = cil_c + eixo_c * (-0.06 + 0.024 * k)
        f_ = caixa(f"{name}_aleta{k}", c, (0.17, 0.17, 0.008), M["r_motor_claro"], raio=0.3, nivel=1)
        f_.rotation_euler = (0, cil_ang, 0)
        add(f_)
    nucleo = caixa(name + "_cilindro", cil_c + eixo_c * 0.01, (0.12, 0.12, 0.20), M["r_motor"], raio=0.3)
    nucleo.rotation_euler = (0, cil_ang, 0)
    add(nucleo)
    tampa_c = caixa(name + "_cabecote", cil_c + eixo_c * 0.13, (0.15, 0.15, 0.06), M["r_motor_claro"], raio=0.35)
    tampa_c.rotation_euler = (0, cil_ang, 0)
    add(tampa_c)
    ylado = -(0.125 if tipo != "cub" else 0.12)
    tl = torno(name + "_tampa_embreagem", [(0.0, 0.0, 0), (0.09, 0.0, 0), (0.105, -0.01, 0), (0.11, -0.03, 0),
                                            (0.0, -0.03, 0)], [M["r_motor_claro"]], seg=48)
    tl.location = (mot.location.x - 0.01, ylado + 0.025, zc - 0.01)
    add(tl)
    # escape: coletor saindo da frente do cilindro, desce, passa por baixo e sobe na lateral direita
    pf = cil_c + eixo_c * 0.06 + Vector((0.07, -0.03, 0))
    if tipo == "street":
        col = [pf, pf + Vector((0.04, -0.05, -0.15)), Vector((0.10, -0.12, zc - 0.17)), Vector((-0.25, -0.15, zc - 0.13))]
        silen = [(-0.22, -0.165, zc - 0.12), (-0.78, -0.18, zc + 0.07)]
        rs = [0.052, 0.042]
    elif tipo == "trail":
        col = [pf, pf + Vector((0.04, -0.05, -0.14)), Vector((0.08, -0.13, zc - 0.15)), Vector((-0.20, -0.15, zc + 0.02)),
               Vector((-0.40, -0.16, zc + 0.20))]
        silen = [(-0.36, -0.17, zc + 0.19), (-0.84, -0.18, zc + 0.38)]
        rs = [0.05, 0.04]
    else:
        col = [pf, pf + Vector((0.05, -0.06, -0.08)), Vector((0.05, -0.13, zc - 0.12)), Vector((-0.30, -0.14, zc - 0.10))]
        silen = [(-0.28, -0.155, zc - 0.09), (-0.80, -0.16, zc + 0.02)]
        rs = [0.048, 0.04]
    add(tubo(name + "_coletor", col, 0.018, cromo))
    add(tubo(name + "_silencioso", silen, rs, cromo if tipo != "trail" else preto, suave=False))
    sa, sb = Vector(silen[0]), Vector(silen[1])
    add(tubo(name + "_protetor", [sa.lerp(sb, 0.15) + Vector((0, -0.012, 0.012)), sa.lerp(sb, 0.6) + Vector((0, -0.012, 0.012))],
             rs[0] * 0.95, preto, suave=False))

    # ---- balança, amortecedores, corrente com coroa e pinhão
    piv = Vector((mot.location.x - 0.20, 0, zc + 0.03))
    ytr = P["lr"] / 2 + 0.03
    for sy in (1, -1):
        add(tubo(f"{name}_balanca{sy}", [(xr + 0.02, sy * ytr, Rr), (piv.x, sy * 0.09, piv.z)], 0.022, preto,
                 suave=False))
        if tipo != "cub" or True:
            ztop = _interp([(e[0], e[2]) for e in est], xr + 0.15) + 0.02
            a0 = Vector((xr + 0.08, sy * (ytr + 0.02), Rr + 0.06))
            a1 = Vector((xr + 0.18, sy * (ytr + 0.03), ztop))
            add(tubo(f"{name}_amort{sy}", [a0, a1], 0.011, cromo, suave=False))
            add(tubo(f"{name}_mola{sy}", [a0.lerp(a1, 0.25), a0.lerp(a1, 0.85)], 0.025,
                     M["r_motor"] if tipo != "street" else M["r_lanterna"], suave=False))
    yc_ = ytr + 0.012
    pin_c, pin_r = (piv.x + 0.08, zc - 0.02), 0.045
    cor_c, cor_r = (xr, Rr), (0.10 if tipo != "cub" else 0.085)
    pts = []
    for k in range(48):
        a = 2 * math.pi * k / 48
        pts.append((round(pin_c[0] + pin_r * math.cos(a), 5), round(pin_c[1] + pin_r * math.sin(a), 5)))
        pts.append((round(cor_c[0] + cor_r * math.cos(a), 5), round(cor_c[1] + cor_r * math.sin(a), 5)))
    h = _casco(pts)
    h.append(h[0])
    if tipo != "cub":
        add(tubo(name + "_corrente", [(x, yc_, z) for x, z in h], 0.007, M["r_corrente"], seg=8, suave=False,
                 tampa=False))
        coroa = torno(name + "_coroa", [(0.03, 0.004, 0), (cor_r - 0.004, 0.004, 0), (cor_r - 0.004, -0.004, 0),
                                        (0.03, -0.004, 0)], [M["r_motor_claro"]], seg=48)
        coroa.location = (xr, yc_, Rr)
        add(coroa)
        add(caixa(name + "_protetor_corrente", ((pin_c[0] + xr) / 2 + 0.05, yc_ + 0.01,
                                                (pin_c[1] + Rr) / 2 + cor_r * 0.8),
                  (abs(pin_c[0] - xr) * 0.75, 0.03, 0.025), preto, raio=0.4))
    else:   # na Biz a corrente vai fechada no cárter de corrente
        add(tubo(name + "_carter_corrente", [(x, yc_, z) for x, z in h], 0.03, preto, seg=12, suave=False,
                 tampa=False))
    # pedaleiras
    for sy in (1, -1):
        add(tubo(f"{name}_pedaleira{sy}", [(piv.x + 0.05, sy * 0.10, zc - 0.08), (piv.x + 0.06, sy * 0.22,
                                                                                zc - 0.07)],
                 0.013, M["r_borracha"], suave=False))
    # tampas laterais (street/trail) sob o banco
    if tipo != "cub":
        for sy in (1, -1):
            tlat = caixa(f"{name}_tampa_lat{sy}", (-0.25, sy * 0.115, est[3][2] - 0.035), (0.24, 0.04, 0.14), tinta,
                         raio=0.48)
            tlat.rotation_euler = (0, math.radians(-14), 0)
            add(tlat, True)
        add(_paralama(name + "_paralama_t", Rr - 0.005, P["lr"] + 0.04, (70, 150), fosco, (xr, 0, Rr)))

    # ---- traseira: para-lama/suporte de placa, lanterna, piscas
    xt, zt0, zt1 = est[0][0], est[0][2], est[0][3]
    add(elipsoide(name + "_lanterna", (xt - 0.005, 0, (zt0 + zt1) / 2), (0.03, 0.055, 0.03), M["r_lanterna"]))
    sup_pl = [(xt + 0.05, 0, zt0 + 0.005), (xt - 0.06, 0, zt0 - 0.08), (xt - 0.08, 0, zt0 - 0.18)]
    add(tubo(name + "_suporte_placa", sup_pl, 0.02, fosco))
    pq = placa(name + "_placa", M, larg=0.20, alt=0.17, esp=0.012)
    pq.location = (xt - 0.10, 0, zt0 - 0.21)
    _orientar(pq, Vector((-0.97, 0, 0.24)))
    add(pq)
    for sy in (1, -1):
        add(tubo(f"{name}_pisca_t_haste{sy}", [(xt + 0.02, sy * 0.03, zt0 - 0.06), (xt + 0.0, sy * 0.13, zt0 - 0.06)],
                 0.008, fosco, suave=False))
        add(elipsoide(f"{name}_pisca_t{sy}", (xt - 0.01, sy * 0.15, zt0 - 0.06), (0.03, 0.022, 0.018),
                      M["r_pisca"]))
    if tipo == "cub":   # grelha traseira típica da Biz
        gz_ = zt1 + 0.01
        add(tubo(name + "_grelha", [(banco[0] + 0.02, 0.1, gz_ - 0.01), (xt + 0.04, 0.1, gz_), (xt, 0.05, gz_),
                                    (xt, -0.05, gz_), (xt + 0.04, -0.1, gz_), (banco[0] + 0.02, -0.1, gz_ - 0.01)],
                 0.009, alu))
    root.scale = (escala, escala, escala)
    return {"raiz": root, "rodas": rodas, "lataria": lataria, "rosto": None, "corpo": corpo, "partes": partes}
