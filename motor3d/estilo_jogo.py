"""Estilo "jogo low-poly" do canal: cores chapadas (sem textura/brilho), contorno preto (casco invertido) e um
bairro brasileiro de casas coloridas. Funciona em Cycles (o contorno usa Backfacing, sem EEVEE).

    import estilo_jogo as ej
    ej.bairro(M, x0=-60, x1=60, y_mf=3.9, y_mf2=-7.3)   # casas dos dois lados da rua (depois de _rua.rua())
    ej.chapar_cena(excecoes=("rosto",))                  # troca todos os materiais por cor chapada
    ej.contornar_cena()                                  # contorno preto em tudo (espessura pelo tamanho)
"""
import math, random
import bpy, bmesh
import numpy as np
import motor as mt
from motor import lin

# ---------------------------------------------------------------- cor chapada
def _cor_material(m):
    """Cor média 'representativa' de um material qualquer (rampa, textura, ou cor base)."""
    if not m.use_nodes:
        return tuple(m.diffuse_color)
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b is None:
        e = next((n for n in nt.nodes if n.type == "EMISSION"), None)
        return tuple(e.inputs["Color"].default_value) if e else (0.5, 0.5, 0.5, 1)
    entrada = b.inputs["Base Color"]
    if not entrada.is_linked:
        return tuple(entrada.default_value)
    # procura para trás: rampa → média dos elementos; imagem → média dos pixels; mix → primeira cor
    pilha, vistos = [entrada.links[0].from_node], set()
    while pilha:
        n = pilha.pop()
        if n.name in vistos:
            continue
        vistos.add(n.name)
        if n.type == "VALTORGB":
            els = n.color_ramp.elements
            return tuple(sum(e.color[i] for e in els) / len(els) for i in range(4))
        if n.type == "TEX_IMAGE" and n.image and n.image.size[0] > 0:
            px = np.array(n.image.pixels[:], np.float32).reshape(-1, 4)[::97]
            return tuple(px.mean(axis=0))
        if n.type == "RGB":
            return tuple(n.outputs[0].default_value)
        for i in n.inputs:
            if i.is_linked:
                pilha.append(i.links[0].from_node)
            elif i.type == "RGBA" and n.type in ("MIX", "MIX_RGB"):
                return tuple(i.default_value)
    return (0.5, 0.5, 0.5, 1)


def chapar(m, cor=None, sat=1.15):
    """Refaz o material como cor chapada fosca (mantém emissão de faróis/lanternas e o alfa)."""
    c = list(cor or _cor_material(m))[:3]
    # um pouco mais de saturação (vivo, sem ficar infantil)
    g = sum(c) / 3
    c = [max(0.0, g + (x - g) * sat) for x in c]
    emit = 0.0
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None
    alfa = 1.0
    if b is not None:
        if "Emission Strength" in b.inputs and not b.inputs["Emission Strength"].is_linked:
            emit = b.inputs["Emission Strength"].default_value
        if not b.inputs["Alpha"].is_linked:
            alfa = b.inputs["Alpha"].default_value
        tx = b.inputs.get("Transmission Weight")
        if tx is not None and not tx.is_linked and tx.default_value > 0.5:      # vidro → escuro chapado
            c, alfa = [0.05, 0.08, 0.12], 1.0
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*c, 1)
    p.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = 0.15
    p.inputs["Alpha"].default_value = alfa
    if emit > 0:
        p.inputs["Emission Color"].default_value = (*c, 1)
        p.inputs["Emission Strength"].default_value = emit
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    m["chapado"] = True


def chapar_cena(excecoes=("rosto", "Eyes"), cores=None):
    """Chapa todos os materiais da cena, menos os que têm alguma das `excecoes` no nome.
    cores = {trecho_do_nome: '#hex'} força uma cor (ex. {'calca': '#3D6FB6'})."""
    for m in bpy.data.materials:
        if m.get("chapado") or m.name.startswith("_contorno") or any(e in m.name for e in excecoes):
            continue
        cor = None
        for k, h in (cores or {}).items():
            if k in m.name:
                cor = lin(h)
        chapar(m, cor)


# ---------------------------------------------------------------- contorno
def _mat_contorno():
    m = bpy.data.materials.get("_contorno")
    if m:
        return m
    m = bpy.data.materials.new("_contorno")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin("#15120F")
    # preto só para o raio da câmera que vê o lado de dentro do casco; para sombra/reflexo o casco não existe
    lp = nt.nodes.new("ShaderNodeLightPath")
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(geo.outputs["Backfacing"], inv.inputs[1])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(inv.outputs[0], mul.inputs[0])
    nt.links.new(lp.outputs["Is Camera Ray"], mul.inputs[1])
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mul.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def contornar(o, esp):
    """Casco invertido: Solidify com normais viradas, só o lado de trás aparece (preto)."""
    if o.type != "MESH" or "contorno" in o.modifiers:
        return
    mc = _mat_contorno()
    if mc.name not in o.data.materials:
        o.data.materials.append(mc)
    idx = list(o.data.materials).index(mc)
    s = o.modifiers.new("contorno", "SOLIDIFY")
    s.thickness = esp
    s.offset = 1.0
    s.use_flip_normals = True
    s.use_rim = False
    s.material_offset = idx
    s.use_quality_normals = True
    # o casco usa só o material de contorno: offset leva todos os índices para >= idx (limitado ao último)


def contornar_cena(excecoes=("rosto", "Eyes", "Eyebrows", "vies", "fivela", "passante", "faixa", "junta", "vaga",
                             "borda_am", "fio_"), esp_min=0.006, esp_max=0.045):
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or any(e in o.name for e in excecoes):
            continue
        d = max(o.dimensions) if o.dimensions.length > 0 else 1.0
        contornar(o, min(esp_max, max(esp_min, d * 0.006)))


# ---------------------------------------------------------------- bairro brasileiro
PAREDES = ["#E9A23B", "#4DA6A0", "#D9654B", "#F1D06A", "#86B46A", "#C784B8", "#5E8FD8", "#EFE3CC", "#F08A6E",
           "#9ACBD9"]
TIJOLO = "#B45A3C"


def _M(M, k, cor):
    if k not in M:
        M[k] = mt.mat("bairro_" + k, cor, rough=1.0)
    return M[k]


def _casa(nome, M, x0, x1, yf, lado, rnd, padaria=False):
    """Casa de frente para a rua. yf = linha da fachada; lado = +1 (casa em y > yf) ou -1."""
    larg = x1 - x0
    andares = rnd.choice((1, 1, 2, 2, 2))
    h = 3.0 if andares == 1 else 5.8
    cor = rnd.choice(PAREDES)
    pm = _M(M, "parede_" + cor, cor)
    prof = 7.0
    y0, y1 = (yf, yf + prof) if lado > 0 else (yf - prof, yf)
    mt.box(nome, x0, x1, y0, y1, 0, h, pm)
    # segundo andar sem reboco (tijolo aparente) em algumas
    if andares == 2 and rnd.random() < 0.35:
        mt.box(nome + "_tij", x0 + 0.02, x1 - 0.02, y0 - 0.02, y1 + 0.02, 3.0, h, _M(M, "tijolo", TIJOLO))
    # platibanda (faixa no topo)
    fr = yf - 0.06 * lado
    mt.box(nome + "_plat", x0, x1, min(fr, yf), max(fr, yf), h - 0.35, h + 0.15,
           _M(M, "branco", "#F4F1EA") if rnd.random() < 0.6 else pm)
    # caixa d'água azul
    if rnd.random() < 0.55:
        mt.cyl(nome + "_cx", 0.55, h, h + 0.8, (x0 + larg * rnd.uniform(0.25, 0.75), yf + lado * 3.5),
               _M(M, "caixa", "#2F78C4"), seg=10)
    vidro = _M(M, "vidro", "#2A3A4C")
    moldura = _M(M, "moldura", "#F4F1EA")
    grade = _M(M, "grade", "#3B3F45")
    def janela(xc, zc, w=1.2, hh=1.1):
        sx = yf - lado * 0.05
        mt.box(nome + f"_jm{xc:.1f}{zc:.1f}", xc - w / 2 - 0.08, xc + w / 2 + 0.08, min(sx, yf), max(sx, yf),
               zc - hh / 2 - 0.08, zc + hh / 2 + 0.08, moldura)
        sv = yf - lado * 0.07
        mt.box(nome + f"_jv{xc:.1f}{zc:.1f}", xc - w / 2, xc + w / 2, min(sv, sx), max(sv, sx), zc - hh / 2,
               zc + hh / 2, vidro)
    if padaria:
        # porta de aço aberta + toldo listrado + placa
        mt.box(nome + "_loja", x0 + 0.6, x1 - 0.6, min(yf, yf - lado * 0.04), max(yf, yf - lado * 0.04), 0, 2.6,
               _M(M, "loja", "#3A2E28"))
        for k in range(int(larg / 0.6)):
            c = "#D63D2E" if k % 2 == 0 else "#F4F1EA"
            xa, xb = x0 + k * 0.6, min(x1, x0 + (k + 1) * 0.6)
            t = mt.box(nome + f"_toldo{k}", xa, xb, -0.65, 0.65, -0.04, 0.04, _M(M, "toldo" + c, c), anchor="center")
            t.location = ((xa + xb) / 2, yf - lado * 0.65, 2.95)
            t.rotation_euler = (math.radians(-25 * lado), 0, 0)
        mt.box(nome + "_placa", x0 + 0.4, x1 - 0.4, min(yf, yf - lado * 0.12), max(yf, yf - lado * 0.12), 3.3, 4.2,
               _M(M, "placa", "#F6D24A"))
        _texto(nome + "_txt", "PADARIA", (x0 + x1) / 2, yf - lado * 0.14, 3.75, 0.62, lado, _M(M, "tinta", "#B8261C"))
    else:
        # muro baixo + portão de grade na frente
        ym = yf - lado * 1.2
        mt.box(nome + "_muro", x0, x1, min(ym, ym - lado * 0.15), max(ym, ym - lado * 0.15), 0, 1.1, pm)
        xp = x0 + larg * 0.55
        mt.box(nome + "_portao", xp, min(x1 - 0.3, xp + 2.6), min(ym, ym - lado * 0.08), max(ym, ym - lado * 0.08),
               1.1, 2.1, grade)
        porta = rnd.choice(("#6B4A2E", "#3B3F45", "#7A2E2E"))
        mt.box(nome + "_porta", x0 + 0.6, x0 + 1.5, min(yf, yf - lado * 0.05), max(yf, yf - lado * 0.05), 0, 2.15,
               _M(M, "porta" + porta, porta))
        janela(x0 + larg * 0.62, 1.55)
    if andares == 2:
        for xc in np.linspace(x0 + 1.4, x1 - 1.4, max(1, int(larg / 3))):
            janela(float(xc), 4.3, w=1.1, hh=1.0)


def _texto(nome, s, x, y, z, tam, lado, m):
    cu = bpy.data.curves.new(nome, "FONT")
    cu.body = s
    try:
        cu.font = bpy.data.fonts.load("/usr/share/fonts/opentype/inter/Inter-Black.otf", check_existing=True)
    except Exception:
        pass
    cu.size = tam
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.extrude = 0.01
    o = mt.link(bpy.data.objects.new(nome, cu))
    o.location = (x, y, z)
    o.rotation_euler = (math.radians(90), 0, 0 if lado > 0 else math.pi)
    o.data.materials.append(m)
    return o


def _fio(nome, p0, p1, M, flecha=0.35):
    cu = bpy.data.curves.new(nome, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    n = 9
    sp.points.add(n - 1)
    for i in range(n):
        u = i / (n - 1)
        x = p0[0] + (p1[0] - p0[0]) * u
        y = p0[1] + (p1[1] - p0[1]) * u
        z = p0[2] + (p1[2] - p0[2]) * u - flecha * 4 * u * (1 - u)
        sp.points[i].co = (x, y, z, 1)
    cu.bevel_depth = 0.012
    cu.bevel_resolution = 0
    o = mt.link(bpy.data.objects.new(nome, cu))
    o.data.materials.append(_M(M, "fio", "#1C1C1E"))
    return o


def bairro(M, x0=-60, x1=60, y_mf=3.9, y_mf2=-7.3, seed=7, padaria_x=9.0):
    """Casas coloridas dos dois lados (fachada a 2,2 m do meio-fio), postes de concreto com fiação, árvores
    baixas. Chame depois de _rua.rua(M, muro=False, arvores=False, postes=False, outro_lado=y_mf2)."""
    rnd = random.Random(seed)
    for lado, yf in ((+1, y_mf + 2.2), (-1, y_mf2 - 2.2)):
        x = x0
        i = 0
        while x < x1:
            w = rnd.uniform(5.5, 8.5)
            pad = lado > 0 and x <= padaria_x < x + w
            _casa(f"casa{lado:+d}_{i}", M, x, x + w - 0.15, yf, lado, rnd, padaria=pad)
            x += w
            i += 1
        # postes de concreto + fiação
        po = _M(M, "poste_conc", "#A9A69E")
        ys = (y_mf + 0.5) if lado > 0 else (y_mf2 - 0.5)
        xs = list(range(int(x0) + 3, int(x1), 18))
        for xp in xs:
            mt.cyl(f"pc{lado:+d}_{xp}", 0.13, 0, 8.0, (xp, ys), po, seg=8)
            mt.box(f"pcb{lado:+d}_{xp}", xp - 0.05, xp + 0.05, ys - 0.7, ys + 0.7, 7.2, 7.3, po)
        for a, b in zip(xs, xs[1:]):
            for k, dz in enumerate((7.25, 6.6, 6.1)):
                dy = (-0.6, 0.0, 0.5)[k]
                _fio(f"fio_{lado:+d}_{a}_{k}", (a, ys + dy, dz), (b, ys + dy, dz), M, flecha=0.3 + k * 0.1)
    # fios atravessando a rua (bagunça boa)
    for xp in range(int(x0) + 12, int(x1), 36):
        _fio(f"fio_x{xp}", (xp, y_mf + 0.5, 7.25), (xp + 4, y_mf2 - 0.5, 7.25), M, flecha=0.6)
    # fundo: morro com casinhas no fim da rua (fecha o horizonte)
    for k in range(60):
        xx = x1 + 6 + rnd.uniform(0, 25)
        yy = rnd.uniform(-35, 35)
        zz = 2 + (xx - x1) * 0.6 + rnd.uniform(-1, 1)
        c = rnd.choice(PAREDES + [TIJOLO, TIJOLO])
        b = mt.box(f"morro{k}", xx, xx + rnd.uniform(3, 5), yy, yy + rnd.uniform(3, 6), 0, zz + rnd.uniform(2, 4),
                   _M(M, "parede_" + c, c))
