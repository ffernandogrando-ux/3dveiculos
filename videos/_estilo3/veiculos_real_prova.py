"""Prova da variante ADULTA dos veículos (veiculos3, estilo="real"): estúdio de foto de montadora.

Uso:  ~/.venv-video/bin/python videos/_estilo3/veiculos_real_prova.py [carros] [motos] [--amostras 48] [--escala 1.0]
Saídas nesta pasta: carros_real.png (hatch vermelho, SUV grafite, picape branca, sedã azul),
motos_real.png (street tipo CG vermelha, trail tipo Bros preta, cub tipo Biz branca) e carro_tecnico.png (hatch
vermelho 1080x1920 no estúdio escuro de motor3d/tecnico.py, para combinar com as cenas técnicas).
Estúdio: piso cinza-escuro levemente reflexivo, fundo em degradê cinza, softbox grande em cima, 2 recortes
(rim) atrás e um preenchimento baixo na frente. AgX "Medium High Contrast".
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "motor3d"))
import bpy, bmesh
from mathutils import Vector
import veiculos3 as v3


def args():
    a = sys.argv[1:]
    alvo = [x for x in a if not x.startswith("--") and not x.replace(".", "").isdigit()]
    amostras = int(a[a.index("--amostras") + 1]) if "--amostras" in a else 48
    escala = float(a[a.index("--escala") + 1]) if "--escala" in a else 1.0
    return alvo or ["carros", "motos", "tecnico"], amostras, escala


def nova_cena(res, amostras):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = res
    c = sc.cycles
    c.device = "CPU"
    c.samples = amostras
    c.use_adaptive_sampling = True
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    if hasattr(c, "denoising_quality"):
        c.denoising_quality = "HIGH"
    c.max_bounces = 8
    c.diffuse_bounces = 3
    c.glossy_bounces = 4
    c.caustics_reflective = c.caustics_refractive = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    w = bpy.data.worlds.new("mundo")
    sc.world = w
    w.use_nodes = True
    # ambiente de estúdio: teto claro, horizonte marcado e chão escuro (é o que desenha os reflexos na lataria)
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    els = cr.color_ramp.elements
    # z da direção vai de -1 a 1; abaixo do horizonte tudo fica na cor da posição 0
    els[0].position, els[0].color = 0.0, v3.lin("#24272B")
    els[1].position, els[1].color = 1.0, v3.lin("#D9DEE4")
    for pos, cor in ((0.025, "#9AA0A7"), (0.08, "#7C828A"), (0.35, "#4E535A"), (0.7, "#8E949B")):
        e = els.new(pos)
        e.color = v3.lin(cor)
    nt.links.new(sep.outputs["Z"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.6
    return sc


def estudio(cx=0.0, fundo_y=7.0, raio=3.5):
    """Piso escuro reflexivo + fundo curvo em degradê (escuro embaixo, cinza claro no alto)."""
    bm = bmesh.new()
    perfil = [(-30.0, 0.0), (fundo_y - raio, 0.0)]
    for k in range(1, 20):
        a = math.pi / 2 * k / 20
        perfil.append((fundo_y - raio + raio * math.sin(a), raio - raio * math.cos(a)))
    perfil += [(fundo_y, raio), (fundo_y, 16.0)]
    rows = [[bm.verts.new((cx - 30 + 60 * i / 2, y, z)) for i in range(3)] for (y, z) in perfil]
    for r in range(len(rows) - 1):
        for i in range(2):
            bm.faces.new([rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]])
    m = bpy.data.materials.new("estudio")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 5.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = v3.lin("#1B1D20")
    cr.color_ramp.elements[1].position = 1.0
    cr.color_ramp.elements[1].color = v3.lin("#8C9299")
    nt.links.new(mr.outputs["Result"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    rough = nt.nodes.new("ShaderNodeMapRange")    # piso acetinado (reflexo suave), parede fosca
    rough.inputs["From Min"].default_value = 0.0
    rough.inputs["From Max"].default_value = 0.6
    rough.inputs["To Min"].default_value = 0.38
    rough.inputs["To Max"].default_value = 0.9
    nt.links.new(sep.outputs["Z"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], b.inputs["Roughness"])
    v3._obj("estudio", bm, m)


def luz(nome, pos, alvo, energia, sx, sy=None, cor="#FFFFFF", spread=None):
    d = bpy.data.lights.new(nome, "AREA")
    d.energy = energia
    if spread:
        d.spread = math.radians(spread)   # luz direcionada: não derrama no piso
    d.shape = "RECTANGLE"
    d.size = sx
    d.size_y = sy if sy else sx
    d.color = v3.lin(cor)[:3]
    o = v3._link(bpy.data.objects.new(nome, d))
    o.location = pos
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    return o


def luzes(cx, larg, k=1.0):
    """Softbox grande em cima (faixa longa ao longo da fila), 2 recortes atrás e um preenchimento baixo."""
    luz("softbox", (cx, -0.6, 4.2), (cx, -0.4, 0), 2600 * k * larg / 10, larg, 3.2, "#FFFFFF")
    luz("rim_e", (cx - larg * 0.35, 4.5, 2.6), (cx - larg * 0.15, 0, 0.6), 900 * k, 0.5, 2.5, "#EAF1FF")
    luz("rim_d", (cx + larg * 0.35, 4.5, 2.6), (cx + larg * 0.15, 0, 0.6), 900 * k, 0.5, 2.5, "#EAF1FF")
    luz("fill", (cx, -9.0, 0.9), (cx, 0, 0.5), 260 * k * larg / 10, larg * 0.9, 0.8, "#FFF4E8")
    luz("fundo", (cx, 2.2, 0.4), (cx, 7.0, 2.6), 700 * k, larg * 0.8, 0.6, "#FFFFFF")


def so_nos_veiculos(raizes):
    """Light linking: as luzes de recorte iluminam só os veículos (não fazem poça de luz no piso)."""
    col = bpy.data.collections.new("alvo_recorte")
    for r in raizes:
        for o in [r] + list(r.children_recursive):
            if o.type == "MESH":
                col.objects.link(o)
    for nome in ("rim_e", "rim_d"):
        lo = bpy.data.objects.get(nome)
        if lo is not None and hasattr(lo, "light_linking"):
            lo.light_linking.receiver_collection = col


def camera(pos, alvo, lens=60):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cam = v3._link(bpy.data.objects.new("cam", cd))
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    bpy.context.scene.camera = cam
    return cam


def render(caminho):
    t = time.time()
    bpy.context.scene.render.filepath = caminho
    bpy.ops.render.render(write_still=True)
    print(f"render {os.path.basename(caminho)}: {time.time() - t:.1f}s")


def checar_rodas(D):
    dg = bpy.context.evaluated_depsgraph_get()
    tot = 0
    for o in D["lataria"]:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        for rd in D["rodas"]:
            inv = rd.matrix_world.inverted()
            pn = [c for c in rd.children if c.name.endswith("_pneu")][0]
            R = max(pn.dimensions.x, pn.dimensions.z) / 2
            w = pn.dimensions.y / 2
            for v in me.vertices:
                p = inv @ (mw @ v.co)
                if abs(p.y) < w and p.x * p.x + p.z * p.z < (R * 0.98) ** 2:
                    tot += 1
        ev.to_mesh_clear()
    return tot


def cena_carros(amostras, escala):
    nova_cena((int(2000 * escala), int(760 * escala)), amostras)
    M = {}
    lista = [("hatch", "#D7262E"), ("suv", "#4A5058"), ("picape", "#F2F2EE"), ("seda", "#1F4E9C")]
    passo = 2.62
    raizes = []
    for k, (tipo, cor) in enumerate(lista):
        D = v3.carro(f"car_{tipo}", M, tipo, cor, estilo="real", escala=0.5)
        D["raiz"].location = ((k - 1.5) * passo, 0, 0)
        D["raiz"].rotation_euler = (0, 0, math.radians(-30))
        bpy.context.view_layer.update()
        print(tipo, "interpenetração (vértices):", checar_rodas(D))
        raizes.append(D["raiz"])
    estudio()
    luzes(0, 12)
    so_nos_veiculos(raizes)
    camera((0.0, -15.2, 1.45), (0, 0, 0.36), lens=52)
    render(os.path.join(HERE, "carros_real.png"))


def cena_motos(amostras, escala):
    nova_cena((int(1800 * escala), int(760 * escala)), amostras)
    M = {}
    lista = [("street", "#D7262E"), ("trail", "#16181B"), ("cub", "#F2F2EE")]
    passo = 1.30
    raizes = []
    for k, (tipo, cor) in enumerate(lista):
        D = v3.moto(f"moto_{tipo}", M, tipo, cor, estilo="real", escala=0.5)
        D["raiz"].location = ((k - 1) * passo, 0, 0)
        D["raiz"].rotation_euler = (0, 0, math.radians(-28))
        bpy.context.view_layer.update()
        print(tipo, "interpenetração (vértices):", checar_rodas(D))
        raizes.append(D["raiz"])
    estudio()
    luzes(0, 6, 0.6)
    so_nos_veiculos(raizes)
    camera((0.0, -6.0, 0.95), (0, 0, 0.30), lens=55)
    render(os.path.join(HERE, "motos_real.png"))


def cena_tecnico(amostras, escala):
    """O hatch vermelho sozinho, 3/4 frente, no estúdio escuro das cenas técnicas (motor3d/tecnico.py), em escala
    real (1:1, como o pneu e o motor em corte), 1080x1920, luz de produto: 2 strips laterais + topo + recorte."""
    import tecnico as tc
    tc.nova_cena(res=(int(1080 * escala), int(1920 * escala)), amostras=amostras)
    tc.estudio_tecnico(fundo_y=5.0, raio_curva=2.2, largura=28.0, strips=False, top=False, rim=False)
    D = v3.carro("hatch_tecnico", {}, "hatch", "#D7262E", estilo="real", escala=1.0)
    D["raiz"].rotation_euler = (0, 0, math.radians(-58))
    bpy.context.view_layer.update()
    print("hatch técnico interpenetração (vértices):", checar_rodas(D))
    alvo = (0.15, 0, 0.62)
    tc.luz_area("strip_esq", (-3.4, -2.2, 1.5), alvo, 0.30, 4.8, 150, abertura=70)
    tc.luz_area("strip_dir", (3.6, -1.0, 1.5), alvo, 0.30, 4.8, 110, abertura=70)
    tc.luz_area("topo", (-0.6, 0.8, 4.8), alvo, 4.0, 0.35, 14, abertura=60)
    rim = tc.luz_area("rim", (0.3, 2.6, 5.4), alvo, 4.0, 0.4, 260, abertura=40)
    rim.visible_glossy = False      # contorno sem estourar o para-brisa
    col = bpy.data.collections.new("alvo_rim_tecnico")
    for o in [D["raiz"]] + list(D["raiz"].children_recursive):
        if o.type == "MESH":
            col.objects.link(o)
    rim.light_linking.receiver_collection = col
    tc.camera((1.5, -12.5, 1.9), (0.1, 0, 0.50), lente=45)
    tc.render(os.path.join(HERE, "carro_tecnico.png"))


if __name__ == "__main__":
    alvo, amostras, escala = args()
    if "tecnico" in alvo:
        cena_tecnico(amostras, escala)
    if "carros" in alvo:
        cena_carros(amostras, escala)
    if "motos" in alvo:
        cena_motos(amostras, escala)
