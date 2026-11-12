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
    "farol": ("#FFF6DA", 0.2, 0.5, 0.8, 0.0),
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
          nivel=2, aro=None, retrovisor=True):
    """Carro de brinquedo de vinil. tipo: hatch | popular | suv | picape | seda. cor: nome, chave de M ou hex.
    rosto=True põe olhos NOS FARÓIS e boca na grade (humor: feliz | preocupado | assustado | bravo).
    aro=None (claro) ou cor do aro ('vermelho', '#FFC400'...). retrovisor=True põe os espelhinhos.
    Devolve dict(raiz, rodas, lataria, rosto, corpo, partes)."""
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


def moto(name, M, tipo="street", cor="vermelho", bau=False):
    """Moto de brinquedo de vinil. tipo: street (a "160 de todo dia") | cub (motoneta 110/125) | trail.
    bau=True põe o baú de entregador (laranja com faixa refletiva) na grelha.
    Devolve dict(raiz, rodas, lataria, rosto=None, corpo, partes)."""
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
