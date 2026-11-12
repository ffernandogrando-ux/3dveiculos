"""Peças do canal de veículos — estilo "Oficina de bolso" (referencias/03_identidade_e_estilo.md).

Mesma pegada do canal de hábitos (argila fosca + contorno fino, de pecas_habitos), com paleta própria.

- parafuso(): mascote fixo "Parafuso" (cabeça sextavada = rosto, macacão azul, luvas laranja, lanterna).
- carro_chibi(): carrinho de brinquedo arredondado. tipo: 'hatch' | 'popular' | 'suv' | 'picape' | 'seda'.
- moto_chibi(): motinho arredondada. tipo: 'street' (a "160 de todo dia") | 'cub' (motoneta 110/125) | 'trail'.
- placa_mercosul(): placa branca com faixa azul (sem texto legível de placa real).
- palco_oficina(): piso de chapa xadrez grafite + parede grafite com brilho laranja no horizonte.
Use materiais_veiculos(M) uma vez antes das peças (já chama materiais_habitos).
Convenção: veículos andam para +x (frente em +x); origem no chão, no meio do entre-eixos.
"""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
import motor as mt
from motor import mat, lin, mesh_obj, empty
from pecas import child, _liso, esfera, capsula, _arco
from pecas_habitos import argila, materiais_habitos, toro, disco

PALETA = {"grafite": "#1E2329", "laranja": "#FF7A1A", "gema": "#FFC928", "azul": "#2F6FB3", "freio": "#E5484D",
          "creme": "#FFF4E0"}

# Cores de lataria (as mais vistas na rua no Brasil + as de destaque da marca)
LATARIA = {"branco": "#F2F0EA", "prata": "#C3C8CE", "cinza": "#7D848C", "preto": "#2B2F36", "vermelho": "#D9393E",
           "azul": "#2F6FB3", "laranja": "#FF7A1A", "amarelo": "#FFC928"}

VEI = {  # nome: (cor, rugosidade)
    # Parafuso
    "aco": ("#D5DCE3", 0.35), "aco_escuro": ("#8C98A4", 0.5), "macacao": ("#2F6FB3", 0.92),
    "macacao_escuro": ("#24588F", 0.92), "luva": ("#FF7A1A", 0.85), "bota": ("#2A2E35", 0.8),
    "olho_p": ("#FFFFFF", 0.5), "pupila_p": ("#161A1F", 0.4), "boca_p": ("#6E2A2A", 0.7), "lingua_p": ("#FF8C7A", 0.8),
    "bochecha_p": ("#FF9A7A", 0.9), "sobr_p": ("#2A2E35", 0.7), "bolso_p": ("#FF7A1A", 0.9),
    "lanterna": ("#FFC928", 0.75), "lanterna_ponta": ("#2A2E35", 0.7),
    # veículos
    "pneu": ("#2A2D33", 0.95), "roda": ("#D9DDE2", 0.5), "roda_cubo": ("#8E979F", 0.6), "vidro_v": ("#2C4A63", 0.25),
    "plastico_v": ("#33373E", 0.9), "farol_v": ("#FFF6D8", 0.3), "lanterna_v": ("#E5484D", 0.4),
    "placa_v": ("#F7F7F2", 0.6), "placa_faixa": ("#1F4FA3", 0.7), "banco_v": ("#2A2D33", 0.9),
    "cromo_v": ("#C9CFD6", 0.35), "motor_v": ("#5C646D", 0.6), "bau_v": ("#FF7A1A", 0.85),
    "pisca_v": ("#FF9A2E", 0.4), "gema": ("#FFC928", 0.75), "olho_v": ("#FFFFFF", 0.4), "pupila_v": ("#161A1F", 0.4),
    "chapa": ("#3A414A", 0.55), "piso_borda": ("#1E2329", 0.9),
}


def materiais_veiculos(M):
    materiais_habitos(M)
    for n, (c, r) in VEI.items():
        if n not in M:
            M[n] = argila(n, c, rough=r)
    for n, c in LATARIA.items():
        k = "lata_" + n
        if k not in M:
            M[k] = argila(k, c, rough=0.45)
    if "farol_luz" not in M:
        M["farol_luz"] = mat("farol_luz", "#FFF2C4", rough=0.3, emit=1.5)
    if "lanterna_luz" not in M:
        M["lanterna_luz"] = mat("lanterna_luz", "#FFE9A8", rough=0.3, emit=2.0)
    if "brilho_v" not in M:
        M["brilho_v"] = mat("brilho_v", "#FFFFFF", rough=0.3, emit=1.2)
    return M


def lataria(M, cor):
    """Material de lataria: nome da LATARIA ('vermelho'), chave de M ou cor hex (#rrggbb)."""
    materiais_veiculos(M)
    if cor in M:
        return M[cor]
    if ("lata_" + cor) in M:
        return M["lata_" + cor]
    if cor.startswith("#"):
        k = "lata_" + cor[1:]
        if k not in M:
            M[k] = argila(k, cor, rough=0.45)
        return M[k]
    raise KeyError(cor)


def escurecer(nome_mat, M, f=0.62):
    """Hex da cor de um material de lataria escurecido (pálpebra dos carros)."""
    base = nome_mat[5:] if nome_mat.startswith("lata_") else nome_mat
    if base in LATARIA:
        hx = LATARIA[base]
    elif len(base) == 6 and all(c in "0123456789abcdefABCDEF" for c in base):
        hx = "#" + base
    else:
        hx = "#888888"
    r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % (int(r * f), int(g * f), int(b * f))


def _na_cor(root, m):
    """Todas as malhas (descendentes de root) que usam o material m: a 'lataria' que o raio-X deixa transparente."""
    return [o for o in root.children_recursive if o.type == "MESH" and m.name in [x.name for x in o.data.materials if x]]


# ================================================================ geometria auxiliar
def bloco(name, x0, x1, y0, y1, z0, z1, m, raio=0.05, seg=4, anchor="center"):
    """Caixa de brinquedo: cantos bem arredondados (Bevel) e sombreado liso."""
    o = mt.box(name, x0, x1, y0, y1, z0, z1, m, anchor=anchor)
    _liso(o)
    bv = o.modifiers.new("arred", "BEVEL")
    bv.width = min(raio, (x1 - x0) / 2.05, (y1 - y0) / 2.05, (z1 - z0) / 2.05)
    bv.segments = seg
    bv.limit_method = "NONE"
    bv.harden_normals = False
    return o


def casca(name, perfil, y0, y1, m, raio=0.06, seg=4):
    """Prisma de perfil lateral (lista de (x, z) no sentido anti-horário) extrudado de y0 a y1, cantos arredondados."""
    bm = bmesh.new()
    fa = [bm.verts.new((x, y0, z)) for x, z in perfil]
    fb = [bm.verts.new((x, y1, z)) for x, z in perfil]
    n = len(perfil)
    bm.faces.new(fa)
    bm.faces.new(list(reversed(fb)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([fa[i], fa[j], fb[j], fb[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _liso(mesh_obj(name, bm, m))
    bv = o.modifiers.new("arred", "BEVEL")
    bv.width = raio
    bv.segments = seg
    bv.limit_method = "ANGLE"
    bv.angle_limit = math.radians(25)
    return o


def hexagono(name, r, altura, m, raio=None, loc=(0, 0, 0)):
    """Prisma sextavado (eixo z, base em z=0), com uma face plana virada para -y. r = raio do canto."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r, radius2=r, depth=altura,
                          matrix=Matrix.Translation((0, 0, altura / 2)) @ Matrix.Rotation(math.radians(30), 4, "Z"))
    o = mesh_obj(name, bm, m, loc)
    bv = o.modifiers.new("arred", "BEVEL")
    bv.width = raio if raio is not None else r * 0.16
    bv.segments = 5
    bv.limit_method = "NONE"
    _liso(o)
    return o


def roda(name, M, r=0.3, largura=0.2, aro=0.58, cor_aro="roda"):
    """Roda de brinquedo: pneu gordinho (toro achatado) + aro claro com cubo. Eixo de rotação = y."""
    root = empty(name)
    pneu = toro(name + "_pneu", r * 0.72, r * 0.3, M["pneu"], eixo="y", seg=40, seg2=16)
    pneu.scale = (1, largura / (r * 0.6), 1)
    child(pneu, root)
    child(disco(name + "_miolo", r * 0.74, largura * 0.82, M["pneu"], eixo="y"), root)
    for s in (-1, 1):
        child(disco(f"{name}_aro{s}", r * aro, largura * 0.12, M[cor_aro], eixo="y"), root,
              (0, s * largura * 0.42, 0))
        child(esfera(f"{name}_cubo{s}", r * 0.18, (0, s * largura * 0.48, 0), M["roda_cubo"],
                     scale=(1, 0.45, 1)), root)
    return root


# ================================================================ mascote
def feixe_mat(name="feixe", cor="#FFE9A8", alpha=0.22):
    """Feixe de luz: brilho que some da lente para a ponta (coordenada 'Generated' z) e nas bordas (Fresnel)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(cor)
    em.inputs["Strength"].default_value = 1.2
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs["Z"], inv.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 1.8
    nt.links.new(inv.outputs[0], pw.inputs[0])
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "SUBTRACT"; fr.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], fr.inputs[1])
    a1 = nt.nodes.new("ShaderNodeMath"); a1.operation = "MULTIPLY"
    nt.links.new(pw.outputs[0], a1.inputs[0]); nt.links.new(fr.outputs[0], a1.inputs[1])
    a2 = nt.nodes.new("ShaderNodeMath"); a2.operation = "MULTIPLY"; a2.inputs[1].default_value = alpha
    nt.links.new(a1.outputs[0], a2.inputs[0])
    nt.links.new(a2.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    return m


def parafuso(name, M, R=0.1, pose="lanterna", olhar=(0.0, 0.0), sobrancelha=12.0, boca="sorriso", luz=False,
             mira=None, inclina=0.0, lanterna=None):
    """Mascote "Parafuso". Olha para -y; origem no chão. R = raio da cabeça sextavada (altura total ≈ 4,2 R).
    pose: 'lanterna' (lanterna erguida na mão direita), 'aponta' (braço esquerdo apontando), 'joinha', 'parado'.
    lanterna: True = na mão direita, False = guardada no cinto (padrão: na mão só nas poses 'lanterna' e 'aponta').
    boca: 'aberta' | 'sorriso' | 'o' (espanto) | 'reta'. luz=True acende a lanterna (cone de luz).
    mira: direção (x, y, z) para onde a lanterna aponta, no espaço do mascote (padrão: para a frente, para baixo e para o lado da mão).
    inclina: graus que a cabeça tomba para o lado (expressão). Retorna dict com raiz, cabeca, corpo, braco_e, braco_d,
    mao_e, mao_d (a direita dele, em -x), lanterna, luz (spot, se luz=True), olhos, pupilas, sobrancelhas e
    bocas (dict tipo→objeto; troque com hide_render)."""
    materiais_veiculos(M)
    root = empty(name)
    P = {"raiz": root}
    # ---- pernas de aço + botinas
    zq = R * 1.05          # altura do quadril
    for lado in (-1, 1):
        x = lado * R * 0.36
        perna = child(mt.cyl(f"{name}_perna{lado}", R * 0.2, R * 0.2, zq, (0, 0), M["aco_escuro"], seg=20), root, (x, 0, 0))
        _liso(perna)
        child(esfera(f"{name}_bota{lado}", R * 0.3, (x, -R * 0.1, R * 0.14), M["bota"], scale=(0.95, 1.35, 0.62)),
              root)
    # ---- corpo: macacão (barril arredondado) com bolso laranja e alças
    zc0, zc1 = zq - R * 0.15, zq + R * 1.15
    corpo = child(esfera(name + "_corpo", R * 0.72, (0, 0, (zc0 + zc1) / 2), M["macacao"],
                         scale=(1.0, 0.88, (zc1 - zc0) / (2 * R * 0.72))), root)
    P["corpo"] = corpo
    yf = -R * 0.72 * 0.88
    child(bloco(name + "_bolso", -R * 0.26, R * 0.26, -R * 0.03, R * 0.03, -R * 0.2, R * 0.16, M["bolso_p"],
                raio=R * 0.06), root, (0, yf + R * 0.04, zq + R * 0.35))
    child(esfera(name + "_bolso_luz", R * 0.03, (R * 0.16, yf - R * 0.01, zq + R * 0.45), M["brilho_v"]), root)
    for lado in (-1, 1):
        child(esfera(f"{name}_botao{lado}", R * 0.065, (lado * R * 0.42, yf + R * 0.12, zq + R * 0.82),
                     M["gema"], scale=(1, 0.5, 1)), root)
    child(toro(name + "_cinto", R * 0.7, R * 0.05, M["macacao_escuro"], eixo="z", seg=40), root,
          (0, 0, zq + R * 0.02)).scale = (1, 0.9, 1)
    # ---- pescoço = toco de haste ROSQUEADA saindo do macacão (o sinal mais forte de "parafuso")
    zp0 = zc1 - R * 0.12
    hp = R * 0.42
    child(_liso(mt.cyl(name + "_haste", R * 0.36, zp0, zp0 + hp, (0, 0), M["aco"], seg=28)), root)
    for k in range(3):
        child(toro(f"{name}_rosca{k}", R * 0.36, R * 0.06, M["aco_escuro"], eixo="z", seg=28, seg2=8), root,
              (0, 0, zp0 + R * 0.12 + k * R * 0.12))
    # ---- flange (arruela integrada) + cabeça sextavada larga e achatada = rosto
    zf = zp0 + hp
    child(disco(name + "_flange", R * 0.94, R * 0.09, M["aco_escuro"], eixo="z"), root, (0, 0, zf + R * 0.045))
    zh0 = zf + R * 0.08
    hh = R * 1.2
    cab = child(empty(name + "_cab"), root, (0, 0, zh0))
    P["cabeca"] = cab
    ch = R * 0.14
    child(hexagono(name + "_cabeca", R, hh - ch, M["aco"], raio=R * 0.1), cab)
    # chanfro do topo (cabeça de parafuso de verdade): tronco sextavado que afina
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=R, radius2=R * 0.8, depth=ch,
                          matrix=Matrix.Translation((0, 0, ch / 2)) @ Matrix.Rotation(math.radians(30), 4, "Z"))
    tp = child(mesh_obj(name + "_chanfro", bm, M["aco"]), cab, (0, 0, hh - ch))
    bv = tp.modifiers.new("arred", "BEVEL")
    bv.width = R * 0.05
    bv.segments = 3
    bv.limit_method = "NONE"
    # topo: fenda Phillips (aparece nos planos de cima)
    for ang in (0, 90):
        f = child(bloco(f"{name}_fenda{ang}", -R * 0.4, R * 0.4, -R * 0.065, R * 0.065, -R * 0.04, R * 0.04,
                        M["aco_escuro"], raio=R * 0.03), cab, (0, 0, hh - R * 0.01))
        f.rotation_euler = (0, 0, math.radians(ang + 30))
    ap = R * math.cos(math.radians(30))          # apótema: a face da frente fica em y = -ap
    yr = -ap

    # olhos
    zo = hh * 0.55
    ro = R * 0.28
    P["olhos"], P["pupilas"], P["sobrancelhas"] = [], [], []
    for lado in (-1, 1):
        c = Vector((lado * R * 0.33, yr - ro * 0.05, zo))
        olho = child(esfera(f"{name}_olho{lado}", ro, tuple(c), M["olho_p"], scale=(0.9, 0.5, 1.1)), cab)
        pp = Vector((olhar[0] * ro * 0.35 - lado * ro * 0.06, -ro * 0.36, olhar[1] * ro * 0.35 - ro * 0.04))
        pup = child(esfera(f"{name}_pupila{lado}", ro * 0.6, tuple(pp), M["pupila_p"], scale=(1, 0.45, 1.1)), olho)
        P["olhos"].append(olho)
        P["pupilas"].append(pup)
        child(esfera(f"{name}_luz{lado}", ro * 0.2, (ro * 0.2, -ro * 0.24, ro * 0.28), M["brilho_v"],
                     scale=(1, 0.5, 1)), pup)
        # sobrancelha grossa (de mecânico). sobrancelha > 0: a direita sobe e abre (curioso);
        # < 0: as duas sobem por dentro (preocupado/espanto)
        if sobrancelha >= 0:
            th = -sobrancelha * 0.8 if lado > 0 else 0.0
            dz = ro * 0.12 * sobrancelha / 12 if lado > 0 else 0.0
        else:
            th = -sobrancelha * lado      # ponta de dentro mais alta
            dz = ro * 0.12
        sb = child(bloco(f"{name}_sobr{lado}", -ro * 0.75, ro * 0.75, -ro * 0.1, ro * 0.1, -ro * 0.14, ro * 0.14,
                         M["sobr_p"], raio=ro * 0.12), cab, (lado * R * 0.33, yr - ro * 0.08, zo + ro * 1.32 + dz))
        sb.rotation_euler = (0, math.radians(th), 0)
        P["sobrancelhas"].append(sb)
        # bochecha
        child(esfera(f"{name}_boch{lado}", R * 0.1, (lado * R * 0.64, yr - R * 0.01, hh * 0.3), M["bochecha_p"],
                     scale=(1.1, 0.3, 0.7)), cab)
    # boca
    bc = (0, yr - R * 0.01, hh * 0.16)
    # todas as bocas são montadas; só a pedida aparece (P["bocas"][tipo] para trocar na animação: hide_render)
    B = {}
    B["aberta"] = child(empty(name + "_boca_aberta"), cab, bc)       # boca larga em "D", não oval no meio da cara
    child(esfera(name + "_boca", R * 0.16, (0, 0, 0), M["boca_p"], scale=(1.5, 0.35, 0.6)), B["aberta"])
    child(esfera(name + "_lingua", R * 0.08, (0, -R * 0.025, -R * 0.04), M["lingua_p"], scale=(1.4, 0.4, 0.5)),
          B["aberta"])
    child(bloco(name + "_dentes", -R * 0.17, R * 0.17, -R * 0.02, R * 0.02, -R * 0.025, R * 0.025, M["olho_p"],
                raio=R * 0.015), B["aberta"], (0, -R * 0.03, R * 0.06))
    B["o"] = child(esfera(name + "_boca_o", R * 0.09, bc, M["boca_p"], scale=(0.8, 0.35, 1.05)), cab)
    B["reta"] = child(capsula(name + "_boca_reta", R * 0.025, R * 0.22, M["boca_p"]), cab, (R * 0.11, bc[1], bc[2]))
    B["reta"].rotation_euler = (0, math.radians(90), 0)
    B["sorriso"] = child(_arco(name + "_boca_sorriso", R * 0.19, R * 0.035, M["boca_p"], ang=math.pi * 0.8), cab,
                         (0, bc[1], bc[2] + R * 0.12))
    for k, o in B.items():
        if k != boca:
            for x in [o] + list(o.children_recursive):
                x.hide_render = x.hide_viewport = True
    P["bocas"] = B
    # ---- braços (macacão) + luvas laranja
    zb = zc1 - R * 0.35
    for lado, nome in ((1, "e"), (-1, "d")):          # olhando para -y, a mão DIREITA dele fica em -x
        ombro = child(empty(f"{name}_ombro_{nome}"), root, (lado * R * 0.66, 0, zb))
        child(capsula(f"{name}_braco_{nome}", R * 0.13, R * 0.5, M["macacao"]), ombro)
        mao = child(esfera(f"{name}_mao_{nome}", R * 0.18, (0, 0, -R * 0.6), M["luva"]), ombro)
        child(toro(f"{name}_punho_{nome}", R * 0.15, R * 0.05, M["luva"], eixo="z", seg=20), ombro, (0, 0, -R * 0.46))
        P["braco_" + nome], P["mao_" + nome] = ombro, mao
        ombro.rotation_euler = (0, lado * math.radians(-28), 0)
    # ---- lanterna (corpo amarelo, cabeça grafite larga, lente que acende)
    lr = empty(name + "_lanterna")
    child(capsula(name + "_lant_corpo", R * 0.13, R * 0.55, M["lanterna"]), lr).rotation_euler = (math.radians(-90), 0, 0)
    for k in range(3):     # anéis de pegada
        child(toro(f"{name}_lant_anel{k}", R * 0.13, R * 0.025, M["lanterna_ponta"], eixo="y", seg=20), lr,
              (0, R * (0.18 + 0.12 * k), 0))
    cabl = child(mt.cyl(name + "_lant_cab", R * 0.21, 0, R * 0.24, (0, 0), M["lanterna_ponta"], seg=28), lr,
                 (0, -R * 0.02, 0))
    cabl.rotation_euler = (math.radians(90), 0, 0)
    _liso(cabl)
    child(disco(name + "_lant_lente", R * 0.17, R * 0.02, M["lanterna_luz"] if luz else M["farol_v"], eixo="y"), lr,
          (0, -R * 0.265, 0))
    if luz:
        bm = bmesh.new()
        L = R * 3.2
        bmesh.ops.create_cone(bm, cap_ends=False, segments=32, radius1=R * 0.17, radius2=R * 1.2, depth=L,
                              matrix=Matrix.Translation((0, 0, L / 2)))
        if "feixe" not in M:
            M["feixe"] = feixe_mat()
        fx = child(_liso(mesh_obj(name + "_feixe", bm, M["feixe"])), lr, (0, -R * 0.27, 0))
        fx.rotation_euler = (math.radians(90), 0, 0)
        sd = bpy.data.lights.new(name + "_spot", "SPOT")
        sd.energy = 60 * (R / 0.15) ** 2
        sd.color = lin("#FFE2A0")[:3]
        sd.spot_size = math.radians(40)
        sd.spot_blend = 0.6
        sd.shadow_soft_size = R * 0.1
        sp = child(mt.link(bpy.data.objects.new(name + "_spot", sd)), lr, (0, -R * 0.3, 0))
        sp.rotation_euler = (math.radians(90), 0, 0)      # spot aponta para -z local → -y da lanterna
        P["luz"] = sp
    P["lanterna"] = lr
    # ---- poses
    if pose in ("lanterna", "aponta"):
        P["braco_d"].rotation_euler = (math.radians(-25), math.radians(128), 0)
    if pose == "aponta":
        P["braco_e"].rotation_euler = (math.radians(-25), math.radians(-105), 0)
    if pose == "joinha":
        P["braco_e"].rotation_euler = (math.radians(-70), math.radians(-35), 0)
        dedo = child(capsula(name + "_polegar", R * 0.085, R * 0.2, M["luva"]), P["mao_e"], (0, -R * 0.03, R * 0.14))
        dedo.rotation_euler = (math.radians(180), 0, 0)
    cab.rotation_euler = (0, math.radians(inclina), 0)
    # lanterna: na mão direita, apontando para o que ela "examina", ou guardada no cinto
    if lanterna is None:
        lanterna = pose in ("lanterna", "aponta")
    bpy.context.view_layer.update()
    if lanterna:
        mao = P["mao_d"]
        alvo = Vector(mira) if mira else Vector((-0.45, -1.0, -0.55))
        lr.parent = mao
        lr.matrix_world = (Matrix.Translation(mao.matrix_world.translation)
                           @ alvo.normalized().to_track_quat("-Y", "Z").to_matrix().to_4x4())
    else:
        lr.parent = root
        lr.matrix_world = (Matrix.Translation((-R * 0.66, -R * 0.2, zq + R * 0.05))
                           @ Vector((0, 0, -1)).to_track_quat("-Y", "Z").to_matrix().to_4x4()
                           @ Matrix.Scale(0.8, 4))
    return P


# ================================================================ placa
def placa_mercosul(name, M, largura=0.36, proporcao=0.33):
    """Placa Mercosul de brinquedo: branca com faixa azul em cima e tracinhos no lugar das letras (não é placa real).
    Fica no plano y-z, de frente para +x. proporcao = altura/largura (carro ≈ 0,33; moto ≈ 0,85)."""
    materiais_veiculos(M)
    a = largura * proporcao
    root = empty(name)
    child(bloco(name + "_base", -0.008, 0.008, -largura / 2, largura / 2, -a / 2, a / 2, M["placa_v"],
                raio=min(a, largura) * 0.12), root)
    fx = min(a * 0.28, largura * 0.12)
    child(bloco(name + "_faixa", -0.006, 0.012, -largura / 2 + 0.004, largura / 2 - 0.004, a / 2 - fx, a / 2 - 0.004,
                M["placa_faixa"], raio=fx * 0.25), root)
    linhas = 1 if proporcao < 0.6 else 2
    for ln in range(linhas):
        n = 7 if linhas == 1 else (3 if ln == 0 else 4)
        zc = (-a * 0.1) if linhas == 1 else (a * 0.05 - ln * a * 0.3)
        hz = a * 0.21 if linhas == 1 else a * 0.11
        for i in range(n):
            y = (i - (n - 1) / 2) * largura * (0.12 if linhas == 1 else 0.19)
            child(bloco(f"{name}_c{ln}{i}", 0.006, 0.012, y - largura * 0.035, y + largura * 0.035, zc - hz, zc + hz,
                        M["plastico_v"], raio=0.003), root)
    return root


# ================================================================ carro
# c, l: comprimento e largura; z0: altura do assoalho; hb: altura da caixa até a linha dos vidros; hc: altura da
# cabine; r: raio da roda; ee: entre-eixos; cab: (x base traseira, x teto traseiro, x teto dianteiro, x base do
# para-brisa); capo: queda do capô.
TIPOS_CARRO = {
    "hatch": dict(c=2.0, l=1.1, z0=0.19, hb=0.44, hc=0.38, r=0.26, ee=1.3, cab=(-0.96, -0.66, 0.1, 0.5), capo=0.07),
    "popular": dict(c=1.68, l=1.04, z0=0.19, hb=0.44, hc=0.44, r=0.25, ee=1.08, cab=(-0.82, -0.62, 0.08, 0.4),
                    capo=0.06),
    "suv": dict(c=2.12, l=1.16, z0=0.3, hb=0.5, hc=0.42, r=0.3, ee=1.36, cab=(-1.0, -0.8, 0.14, 0.5), capo=0.05),
    "picape": dict(c=2.42, l=1.12, z0=0.24, hb=0.48, hc=0.44, r=0.31, ee=1.56, cab=(-0.42, -0.38, 0.3, 0.7),
                   capo=0.06),
    "seda": dict(c=2.3, l=1.1, z0=0.2, hb=0.46, hc=0.42, r=0.29, ee=1.42, cab=(-0.72, -0.5, 0.16, 0.56), capo=0.07),
}


def _vidro(name, a, b, meia_l, m, fora=1, esp=0.014, raio=0.025):
    """Vidro inclinado: segmento a→b (pontos (x, z)) extrudado em y de -meia_l a +meia_l. fora=+1/-1 escolhe o lado
    da normal para onde a placa cresce."""
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    L = math.hypot(dx, dz)
    nx, nz = dz / L * fora, -dx / L * fora
    perfil = [(ax, az), (bx, bz), (bx + nx * esp, bz + nz * esp), (ax + nx * esp, az + nz * esp)]
    if (perfil[1][0] - perfil[0][0]) * (perfil[2][1] - perfil[0][1]) - (perfil[1][1] - perfil[0][1]) * (perfil[2][0] - perfil[0][0]) < 0:
        perfil.reverse()
    return casca(name, perfil, -meia_l, meia_l, m, raio=raio, seg=3)


def carro_chibi(name, M, tipo="hatch", cor="prata", rosto=False, olhar=(0.0, 0.0), humor="feliz", placa=True,
                escala=1.0):
    """Carrinho de brinquedo. Anda para +x. tipo: 'hatch' | 'popular' (hatch de entrada) | 'suv' | 'picape' | 'seda'.
    rosto=True põe olhos nos faróis e boca na grade (planos de 'sentimento'); humor: 'feliz' | 'cansado' | 'susto'.
    escala: tamanho (1 = carro de ~2 m de comprimento). Retorna dict com raiz, corpo, lataria (todas as peças na cor,
    para o raio-X), rodas (raízes, giram em y), farois, rosto (todas as peças do rosto, para ligar/desligar),
    olhos, pupilas, bocas (dict humor→objeto)."""
    materiais_veiculos(M)
    T = TIPOS_CARRO[tipo]
    m = lataria(M, cor)
    C, Lg, z0, hb, hc, r, ee, capo = T["c"], T["l"], T["z0"], T["hb"], T["hc"], T["r"], T["ee"], T["capo"]
    cr0, cr1, cf1, cf0 = T["cab"]
    root = empty(name)
    V = {"raiz": root, "rodas": [], "farois": [], "rosto": [], "olhos": [], "pupilas": []}
    x0, x1 = -C / 2, C / 2
    zt = z0 + hb
    m_palp = lataria(M, escurecer(m.name, M))
    zt2 = zt + hc
    # ---- caixa de baixo: capô cai para a frente; porta-malas do sedã desce um pouco
    perfil = [(x0, z0 + 0.03), (x1, z0 + 0.03), (x1, zt - capo - 0.05), (x1 - 0.14, zt - capo), (cf0, zt), (x0, zt)]
    base = child(casca(name + "_base", perfil, -Lg / 2, Lg / 2, m, raio=0.13, seg=5), root)
    # ---- cabine na cor da lataria
    lc = Lg * 0.9
    cab = child(casca(name + "_cabine", [(cr0, zt - 0.04), (cf0, zt - 0.04), (cf1, zt2), (cr1, zt2)], -lc / 2, lc / 2,
                      m, raio=0.09, seg=4), root)

    def xb(t, frente):        # x da borda da cabine na altura relativa t (0 = linha dos vidros, 1 = teto)
        return (cf0 + (cf1 - cf0) * t) if frente else (cr0 + (cr1 - cr0) * t)

    # vidros laterais (dois por lado, separados pela coluna do meio; um só na picape)
    t0, t1 = 0.14, 0.84
    mg = 0.07
    zb_, zc_ = zt + hc * t0, zt + hc * t1
    pts = [(xb(t0, False) + mg, zb_), (xb(t0, True) - mg * 1.2, zb_), (xb(t1, True) - mg * 1.2, zc_),
           (xb(t1, False) + mg, zc_)]
    janelas = [pts]
    if tipo != "picape":
        xm = (pts[0][0] + pts[1][0]) / 2 - 0.02
        janelas = [[pts[0], (xm - 0.035, zb_), (xm - 0.035, zc_), pts[3]],
                   [(xm + 0.035, zb_), pts[1], pts[2], (xm + 0.035, zc_)]]
    for s in (-1, 1):
        for k, jp in enumerate(janelas):
            y0_, y1_ = (lc / 2 - 0.006, lc / 2 + 0.012) if s > 0 else (-lc / 2 - 0.012, -lc / 2 + 0.006)
            child(casca(f"{name}_janela{s}{k}", jp, y0_, y1_, M["vidro_v"], raio=0.02, seg=3), root)
    # para-brisa e vidro traseiro
    mf = 0.06
    child(_vidro(name + "_parabrisa", (xb(0.1, True) + 0.004, zt + hc * 0.1), (xb(0.88, True) + 0.004, zt + hc * 0.88),
                 lc / 2 - mf, M["vidro_v"], fora=1), root)
    child(_vidro(name + "_vidro_tras", (xb(0.12, False) - 0.004, zt + hc * 0.12),
                 (xb(0.86, False) - 0.004, zt + hc * 0.86), lc / 2 - mf - 0.04, M["vidro_v"], fora=-1), root)
    # reflexo no para-brisa
    rf = child(bloco(name + "_reflexo", -0.012, 0.012, -0.035, 0.035, -hc * 0.28, hc * 0.28, M["brilho_v"], raio=0.01),
               root, ((xb(0.5, True) + 0.022), -lc * 0.18, zt + hc * 0.5))
    rf.rotation_euler = (0, math.atan2(cf0 - cf1, hc), 0)
    # picape: caçamba com capota marítima + santo-antônio
    if tipo == "picape":
        child(bloco(name + "_capota", x0 + 0.06, cr0 - 0.06, -Lg / 2 + 0.06, Lg / 2 - 0.06, zt - 0.02, zt + 0.015,
                    M["plastico_v"], raio=0.02), root)
        xs = cr0 - 0.1
        for s in (-1, 1):
            child(mt.tube(f"{name}_santo{s}", (xs, s * (Lg / 2 - 0.1), zt), (xs + 0.03, s * (Lg / 2 - 0.12),
                                                                          zt + hc * 0.55), 0.025, M["plastico_v"]), root)
        child(mt.tube(name + "_santo_t", (xs + 0.03, -(Lg / 2 - 0.12), zt + hc * 0.55),
                      (xs + 0.03, Lg / 2 - 0.12, zt + hc * 0.55), 0.025, M["plastico_v"]), root)
    # SUV: barras de teto + moldura preta nos para-lamas e na saia
    if tipo == "suv":
        for s in (-1, 1):
            child(bloco(f"{name}_rack{s}", cr1 + 0.06, cf1 - 0.06, -0.022, 0.022, -0.02, 0.02, M["plastico_v"],
                        raio=0.015), root, ((cr1 + cf1) / 2, s * lc * 0.36, zt2 + 0.035))
            child(bloco(f"{name}_saia{s}", -ee / 2 + r * 0.9, ee / 2 - r * 0.9, -0.02, 0.02, -0.045, 0.045,
                        M["plastico_v"], raio=0.02), root, (0, s * (Lg / 2 + 0.005), z0 + 0.07))
    # ---- frente: para-choque, grade larga e baixa, faróis puxados para os lados
    zpc = z0 + 0.08
    for xs_, nm in ((x1, "dianteiro"), (x0, "traseiro")):
        child(bloco(f"{name}_pc_{nm}", -0.065, 0.065, -Lg / 2 - 0.012, Lg / 2 + 0.012, -0.075, 0.075, M["plastico_v"],
                    raio=0.06), root, (xs_, 0, zpc))
    zg = z0 + hb * 0.4
    child(bloco(name + "_grade", -0.03, 0.03, -Lg * 0.25, Lg * 0.25, -hb * 0.1, hb * 0.1, M["plastico_v"],
                raio=0.035), root, (x1 + 0.006, 0, zg))
    zf = zt - capo - hb * 0.2
    for s in (-1, 1):
        fy = s * Lg * 0.32
        fr = child(esfera(f"{name}_farol{s}", 0.1, (x1 - 0.01, fy, zf), M["farol_v"], scale=(0.42, 1.25, 0.62)), root)
        V["farois"].append(fr)
        if rosto:
            ol = child(esfera(f"{name}_olho{s}", 0.085, (x1 + 0.022, fy, zf), M["olho_v"], scale=(0.35, 1.05, 0.95)),
                       root)
            pz = {"cansado": -0.022, "susto": 0.0}.get(humor, 0.0)
            pup = child(esfera(f"{name}_pupila{s}", 0.05, (0.026, olhar[0] * 0.03 - s * 0.005, pz + olhar[1] * 0.025),
                               M["pupila_v"], scale=(0.4, 1, 1.1 if humor != "susto" else 0.75)), ol)
            child(esfera(f"{name}_luzolho{s}", 0.015, (0.02, 0.013, 0.018), M["brilho_v"]), pup)
            if humor == "cansado":    # pálpebra caída na cor da lataria
                child(esfera(f"{name}_palpebra{s}", 0.09, (x1 + 0.03, fy, zf + 0.03), m, scale=(0.36, 1.12, 0.5)), root)
        child(esfera(f"{name}_pisca{s}", 0.03, (x1 - 0.03, s * (Lg / 2 - 0.01), zf - 0.01), M["pisca_v"],
                     scale=(0.6, 0.5, 0.6)), root)
        # lanterna traseira horizontal
        child(bloco(f"{name}_lant{s}", -0.03, 0.03, -0.11, 0.11, -0.045, 0.045, M["lanterna_v"], raio=0.025), root,
              (x0 + 0.004, s * Lg * 0.33, zt - 0.1))
        # retrovisor na base do para-brisa
        child(esfera(f"{name}_retro{s}", 0.055, (cf0 - 0.04, s * (lc / 2 + 0.07), zt + 0.06), m, scale=(0.6, 0.9, 0.7)),
              root)
        # maçaneta(s)
        for xm_ in ([cf0 - 0.3] if tipo == "picape" else [cf0 - 0.3, (cr0 + cf0) / 2 - 0.25]):
            child(bloco(f"{name}_maca{s}{xm_:.2f}", -0.045, 0.045, -0.01, 0.01, -0.012, 0.012, M["plastico_v"],
                        raio=0.008), root, (xm_, s * (Lg / 2 + 0.003), zt - 0.09))
    if rosto:
        B = {"feliz": child(_arco(name + "_boca_feliz", 0.12, 0.022, M["boca_p"], ang=math.pi * 0.8), root,
                            (x1 + 0.045, 0, zg + 0.04)),
             "susto": child(esfera(name + "_boca_susto", 0.06, (x1 + 0.04, 0, zg), M["boca_p"], scale=(0.3, 0.8, 1.0)),
                            root),
             "cansado": child(_arco(name + "_boca_cansado", 0.1, 0.02, M["boca_p"], ang=math.pi * 0.6, para_cima=False),
                              root, (x1 + 0.045, 0, zg - 0.055))}
        for k, o in B.items():
            if k != "susto":
                o.rotation_euler = (0, 0, math.radians(90))
            if k != humor:
                o.hide_render = o.hide_viewport = True
        V["bocas"] = B
        V["rosto"] += list(B.values())
    if placa:
        child(placa_mercosul(name + "_placa_f", M, largura=0.3), root, (x1 + 0.07, 0, zpc))
        pt = child(placa_mercosul(name + "_placa_t", M, largura=0.3), root, (x0 - 0.012, 0, zt - hb * 0.45))
        pt.rotation_euler = (0, 0, math.pi)
    # ---- rodas (com caixa de roda escura atrás; no SUV, moldura preta saliente)
    for wx in (-ee / 2, ee / 2):
        for s in (-1, 1):
            k = f"{wx:+.1f}{s}"
            child(esfera(f"{name}_cxroda{k}", r * 1.14, (wx, s * (Lg / 2 - 0.015), r), M["pneu"], scale=(1, 0.12, 1)),
                  root)
            if tipo == "suv":
                arco = child(toro(f"{name}_arco{k}", r * 1.2, 0.035, M["plastico_v"], eixo="y", seg=32), root,
                             (wx, s * (Lg / 2 + 0.0), r))
                arco.scale = (1, 0.8, 1)
            rd = roda(f"{name}_roda{k}", M, r=r, largura=0.19)
            child(rd, root, (wx, s * (Lg / 2 - 0.045), r))
            V["rodas"].append(rd)
    V["corpo"] = base
    V["lataria"] = _na_cor(root, m)
    root.scale = (escala, escala, escala)
    return V


# ================================================================ moto
def moto_chibi(name, M, tipo="street", cor="vermelho", bau=False, rosto=False):
    """Motinho de brinquedo. Anda para +x. tipo: 'street' (a 150/160 de todo dia) | 'cub' (motoneta 110/125) |
    'trail' (160 aventureira). bau=True: baú de entregador no bagageiro. O lado do escapamento é o -y (o que a câmera
    em -y vê); a corrente fica do lado +y. Retorna dict com raiz, rodas, tanque, farois, lataria (peças na cor),
    corrente (empty no meio da transmissão; None na motoneta), olhos/pupilas (se rosto)."""
    materiais_veiculos(M)
    m = lataria(M, cor)
    root = empty(name)
    V = {"raiz": root, "rodas": [], "farois": [], "corrente": None, "olhos": [], "pupilas": []}
    trail, cub = tipo == "trail", tipo == "cub"
    r = {"street": 0.24, "cub": 0.2, "trail": 0.27}[tipo]
    ee = {"street": 1.0, "cub": 0.9, "trail": 1.06}[tipo]
    xt, xd = -ee / 2, ee / 2
    zr = r
    for wx, nm in ((xt, "tras"), (xd, "frente")):
        rd = roda(f"{name}_roda_{nm}", M, r=r, largura=0.12 if not cub else 0.1, aro=0.56 if not trail else 0.62)
        child(rd, root, (wx, 0, zr))
        V["rodas"].append(rd)
    # ---- guidão (posição comum)
    zg = zr + {"street": 0.66, "cub": 0.68, "trail": 0.76}[tipo]
    xg = xd - {"street": 0.17, "cub": 0.12, "trail": 0.19}[tipo]
    # garfo
    for s in (-1, 1):
        child(mt.tube(f"{name}_garfo{s}", (xd, s * 0.07, zr), (xg, s * 0.07, zg - 0.1), 0.024, M["cromo_v"]), root)
    child(mt.tube(name + "_guidao", (xg - 0.05, -0.23, zg + 0.02), (xg - 0.05, 0.23, zg + 0.02), 0.02, M["plastico_v"]),
          root)
    for s in (-1, 1):
        child(capsula(f"{name}_manopla{s}", 0.028, 0.07, M["banco_v"]), root,
              (xg - 0.05, s * 0.2, zg + 0.02)).rotation_euler = (math.radians(90 * s), 0, 0)
        child(mt.tube(f"{name}_haste{s}", (xg - 0.05, s * 0.15, zg + 0.03), (xg - 0.08, s * 0.19, zg + 0.12), 0.009,
                      M["plastico_v"], seg=6), root)
        child(esfera(f"{name}_retro{s}", 0.05, (xg - 0.085, s * 0.2, zg + 0.15), M["plastico_v"], scale=(0.35, 1.0, 0.75)),
              root)
    # ---- grelha (bagageiro): quase toda moto de trabalho tem
    def grelha(x0_, x1_, z_):
        for s in (-1, 1):
            child(mt.tube(f"{name}_grelha{s}", (x0_, s * 0.085, z_), (x1_, s * 0.085, z_), 0.013, M["plastico_v"], seg=8),
                  root)
        for k in range(3):
            gx = x0_ + (x1_ - x0_) * k / 2
            child(mt.tube(f"{name}_grelha_t{k}", (gx, -0.085, z_), (gx, 0.085, z_), 0.012, M["plastico_v"], seg=8), root)
        for s in (-1, 1):   # suportes até a carenagem (a grelha não flutua)
            child(mt.tube(f"{name}_grelha_s{s}", (x0_ + 0.02, s * 0.085, z_), (x0_ + 0.1, s * 0.085, z_ - 0.13), 0.011,
                          M["plastico_v"], seg=8), root)

    if cub:
        # motoneta: carenagem traseira inteira na cor, túnel baixo, escudo das pernas, farol no guidão
        zs = zr + 0.4
        # carenagem em 3 peças convexas: traseira, assoalho e escudo das pernas
        child(casca(name + "_traseira", [(xt - 0.14, zr + 0.14), (-0.1, zr + 0.05), (0.04, zr + 0.1), (0.04, zs - 0.02),
                                         (xt - 0.1, zs)], -0.13, 0.13, m, raio=0.07, seg=4), root)
        child(casca(name + "_assoalho", [(-0.12, zr + 0.04), (xd - 0.18, zr + 0.04), (xd - 0.18, zr + 0.15),
                                         (-0.06, zr + 0.15)], -0.1, 0.1, m, raio=0.04, seg=3), root)
        corpo = child(casca(name + "_escudo", [(xd - 0.29, zr + 0.06), (xd - 0.13, zr + 0.08), (xd - 0.09, zr + 0.56),
                                               (xd - 0.19, zr + 0.6)], -0.15, 0.15, m, raio=0.06, seg=4), root)
        child(casca(name + "_banco", [(xt - 0.06, zs - 0.03), (0.04, zs - 0.03), (0.02, zs + 0.06), (xt - 0.02, zs + 0.06)],
                    -0.125, 0.125, M["banco_v"], raio=0.04, seg=3), root)
        esc = corpo
        child(bloco(name + "_motor", -0.12, 0.12, -0.09, 0.09, -0.08, 0.08, M["motor_v"], raio=0.05), root,
              (-0.04, 0, zr - 0.04))
        child(capsula(name + "_escape", 0.04, 0.42, M["cromo_v"]), root, (0.05, -0.12, zr - 0.06)).rotation_euler = (
            0, math.radians(96), 0)
        # carenagem do guidão com o farol
        child(esfera(name + "_carenagem", 0.12, (xg - 0.02, 0, zg + 0.0), m, scale=(0.9, 1.25, 0.6)), root)
        V["farois"].append(child(esfera(name + "_farol", 0.07, (xg + 0.085, 0, zg - 0.0), M["farol_v"],
                                        scale=(0.35, 1.2, 0.75)), root))
        child(mt.tube(name + "_coluna", (xd - 0.03, 0, zr + 0.1), (xg - 0.01, 0, zg - 0.04), 0.03, m), root)
        child(esfera(name + "_paralama", 0.16, (xd + 0.02, 0, zr + r + 0.01), m, scale=(1.25, 0.42, 0.24)), root)
        child(esfera(name + "_lant_tras", 0.035, (xt - 0.16, 0, zr + 0.2), M["lanterna_v"], scale=(0.6, 1.4, 0.8)),
              root)
        child(placa_mercosul(name + "_placa", M, largura=0.14, proporcao=0.85), root,
              (xt - 0.15, 0, zr + 0.06)).rotation_euler = (0, math.radians(-8), math.pi)
        zgr = zs + 0.05
        grelha(xt - 0.2, xt + 0.02, zgr)
        V["tanque"] = esc
    else:
        zt = zr + (0.44 if trail else 0.38)          # topo do tanque
        # motor + cabeçote inclinado para a frente
        child(bloco(name + "_motor", -0.15, 0.15, -0.1, 0.1, -0.12, 0.12, M["motor_v"], raio=0.06), root,
              (0.0, 0, zr + 0.0))
        cab_m = child(bloco(name + "_cabecote", -0.07, 0.07, -0.08, 0.08, -0.09, 0.09, M["motor_v"], raio=0.04), root,
                      (0.12, 0, zr + 0.16))
        cab_m.rotation_euler = (0, math.radians(-25), 0)
        # quadro (tubo do pescoço ao motor)
        child(mt.tube(name + "_quadro", (xg - 0.02, 0, zg - 0.12), (0.12, 0, zr + 0.2), 0.035, M["plastico_v"]), root)
        # tanque em gota, estreito na traseira
        tq = child(esfera(name + "_tanque", 0.21, (0.1, 0, zt - 0.07), m, scale=(1.35, 0.84, 0.66)), root)
        tq.rotation_euler = (0, math.radians(8), 0)
        V["tanque"] = tq
        for s in (-1, 1):   # faixa de fábrica genérica
            child(esfera(f"{name}_tq_faixa{s}", 0.09, (0.12, s * 0.143, zt - 0.08), M["placa_v"],
                         scale=(1.25, 0.1, 0.22)), root).rotation_euler = (0, math.radians(-10), 0)
        child(esfera(name + "_tq_brilho", 0.025, (0.05, -0.1, zt + 0.03), M["brilho_v"], scale=(2.4, 0.5, 0.6)), root)
        # tampa lateral + rabeta numa peça só (debaixo do banco até a traseira)
        child(casca(name + "_lateral", [(-0.02, zt - 0.22), (0.02, zt - 0.06), (xt - 0.22, zt - 0.03),
                                        (xt - 0.14, zt - 0.13)], -0.11, 0.11, m, raio=0.05, seg=4), root)
        # banco reto de dois lugares
        xb0, xb1 = (xt - 0.02, 0.0) if not trail else (xt - 0.04, 0.04)
        child(casca(name + "_banco", [(xb0, zt - 0.06), (xb1, zt - 0.06), (xb1 - 0.03, zt + 0.04), (xb0 + 0.02, zt + 0.03)],
                    -0.115, 0.115, M["banco_v"], raio=0.04, seg=3), root)
        # lanterna + placa quase quadrada
        child(esfera(name + "_lant_tras", 0.04, (xt - 0.19, 0, zt - 0.07), M["lanterna_v"], scale=(0.6, 1.3, 0.8)), root)
        for s in (-1, 1):
            child(esfera(f"{name}_pisca_t{s}", 0.022, (xt - 0.16, s * 0.1, zt - 0.1), M["pisca_v"]), root)
        child(placa_mercosul(name + "_placa", M, largura=0.14, proporcao=0.85), root,
              (xt - 0.18, 0, zt - 0.2)).rotation_euler = (0, math.radians(-12), math.pi)
        # balança, amortecedores, corrente (lado +y) e protetor
        for s in (-1, 1):
            child(mt.tube(f"{name}_balanca{s}", (-0.08, s * 0.075, zr - 0.02), (xt, s * 0.075, zr), 0.022,
                          M["plastico_v"]), root)
            child(mt.tube(f"{name}_amort{s}", (xt + 0.02, s * 0.1, zr + 0.02), (xt + 0.12, s * 0.1, zt - 0.1), 0.022,
                          M["cromo_v"]), root)
            for k in range(4):
                tt = 0.2 + 0.2 * k
                p = Vector((xt + 0.02, s * 0.1, zr + 0.02)).lerp(Vector((xt + 0.12, s * 0.1, zt - 0.1)), tt)
                child(toro(f"{name}_mola{s}{k}", 0.03, 0.009, M["luva"], eixo="z", seg=14, seg2=6), root, tuple(p))
        child(capsula(name + "_protetor", 0.035, ee * 0.42, M["plastico_v"]), root,
              (-0.06, 0.11, zr + 0.04)).rotation_euler = (0, math.radians(-92), 0)
        V["corrente"] = child(empty(name + "_corrente"), root, ((xt - 0.06) / 2, 0.11, zr))
        # escapamento cromado do lado da câmera
        child(mt.tube(name + "_escape_c", (0.1, -0.1, zr - 0.05), (-0.12, -0.13, zr - 0.03), 0.035, M["cromo_v"]), root)
        child(capsula(name + "_escape", 0.055, 0.34, M["cromo_v"]), root, (-0.1, -0.14, zr - 0.02)).rotation_euler = (
            0, math.radians(100), 0)
        child(capsula(name + "_escape_prot", 0.045, 0.2, M["plastico_v"]), root,
              (-0.14, -0.18, zr + 0.0)).rotation_euler = (0, math.radians(100), 0)
        # carenagem do farol + farol redondo + piscas
        child(esfera(name + "_carenagem", 0.12, (xg + 0.02, 0, zg - 0.1), m, scale=(0.8, 1.05, 0.95)), root)
        V["farois"].append(child(esfera(name + "_farol", 0.085, (xg + 0.105, 0, zg - 0.1), M["farol_v"],
                                        scale=(0.32, 1, 1)), root))
        for s in (-1, 1):
            child(esfera(f"{name}_pisca_f{s}", 0.022, (xg + 0.04, s * 0.13, zg - 0.13), M["pisca_v"]), root)
        if trail:
            # para-lama alto + bico + tampas laterais "de número"
            child(esfera(name + "_paralama", 0.2, (xd + 0.03, 0, zr + r + 0.1), m, scale=(1.2, 0.4, 0.16)),
                  root).rotation_euler = (0, math.radians(8), 0)
            child(esfera(name + "_bico", 0.13, (xg + 0.1, 0, zg - 0.2), m, scale=(1.25, 0.5, 0.2)), root
                  ).rotation_euler = (0, math.radians(22), 0)
        else:
            child(esfera(name + "_paralama", 0.16, (xd + 0.02, 0, zr + r + 0.03), M["plastico_v"],
                         scale=(1.25, 0.4, 0.22)), root)
        zgr = zt - 0.02
        grelha(xt - 0.2, xt + 0.02, zgr)
        # pedaleiras
        for s in (-1, 1):
            child(capsula(f"{name}_pedal{s}", 0.015, 0.06, M["plastico_v"]), root,
                  (0.0, s * 0.12, zr - 0.08)).rotation_euler = (math.radians(90 * s), 0, 0)
    if rosto:
        f = V["farois"][0]
        for s in (-1, 1):
            ol = child(esfera(f"{name}_olho{s}", 0.04, (0.012, s * 0.035, 0.012), M["olho_v"], scale=(0.4, 0.9, 1.1)), f)
            V["olhos"].append(ol)
            V["pupilas"].append(child(esfera(f"{name}_pupila{s}", 0.024, (0.012, -s * 0.003, 0), M["pupila_v"],
                                             scale=(0.4, 1, 1.1)), ol))
    if bau:
        zb = zgr + 0.02
        # baú laranja-segurança com tampa grafite (nada de vermelho + amarelo de app de entrega)
        child(bloco(name + "_bau", -0.16, 0.16, -0.16, 0.16, 0, 0.3, M["bau_v"], raio=0.04), root,
              (xt - 0.09, 0, zb + 0.15))
        child(bloco(name + "_bau_tampa", -0.17, 0.17, -0.17, 0.17, -0.018, 0.018, M["plastico_v"], raio=0.018), root,
              (xt - 0.09, 0, zb + 0.31))
        for s in (-1, 1):   # faixa refletiva
            child(bloco(f"{name}_bau_faixa{s}", -0.13, 0.13, -0.004, 0.004, -0.02, 0.02, M["cromo_v"], raio=0.006), root,
                  (xt - 0.09, s * 0.163, zb + 0.08))
    V["lataria"] = _na_cor(root, m)
    return V


# ================================================================ palco
def chapa_xadrez_mat(name="chapa_xadrez", base="#2B3138", ressalto="#566170", passo=0.09):
    """Chapa xadrez (antiderrapante de oficina): grãos alongados em duas direções alternadas, com relevo (Bump)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.5
    if "Metallic" in bs.inputs:
        bs.inputs["Metallic"].default_value = 0.0
    nt.links.new(bs.outputs[0], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def op(o, a, b=None, v=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = o
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                nt.links.new(x, n.inputs[i])
        return n.outputs[0]

    X = op("DIVIDE", sep.outputs["X"], passo)
    Y = op("DIVIDE", sep.outputs["Y"], passo)
    cx, cy = op("FLOOR", X), op("FLOOR", Y)
    fx = op("SUBTRACT", op("FRACT", X), 0.5)
    fy = op("SUBTRACT", op("FRACT", Y), 0.5)
    par = op("MODULO", op("ADD", cx, cy), 2.0)            # 0 ou 1 (xadrez)
    sgn = op("SUBTRACT", op("MULTIPLY", par, 2.0), 1.0)   # -1 ou +1
    # gira 45° para um lado ou para o outro
    u = op("MULTIPLY", op("ADD", fx, op("MULTIPLY", fy, sgn)), 0.7071)
    v = op("MULTIPLY", op("SUBTRACT", fy, op("MULTIPLY", fx, sgn)), 0.7071)
    d = op("ADD", op("POWER", op("DIVIDE", u, 0.36), 2.0), op("POWER", op("DIVIDE", v, 0.09), 2.0))
    alt = op("SUBTRACT", 1.0, op("MINIMUM", d, 1.0))      # 1 no meio do grão, 0 fora
    alt = op("POWER", alt, 0.5)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.01
    nt.links.new(alt, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = lin(base)
    mix.inputs["B"].default_value = lin(ressalto)
    nt.links.new(op("MINIMUM", op("MULTIPLY", alt, 3.0), 1.0), mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bs.inputs["Base Color"])
    return m


def fundo_brilho_mat(name="fundo_oficina", topo="#14181D", meio="#262C34", brilho="#FF7A1A", z_brilho=0.0,
                     largura=0.4, forca=0.12):
    """Parede grafite em cor chapada (emissão) com uma faixa de brilho laranja suave na altura z_brilho."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    a = nt.nodes.new("ShaderNodeMath"); a.operation = "SUBTRACT"; a.inputs[1].default_value = z_brilho
    nt.links.new(sep.outputs["Z"], a.inputs[0])
    b = nt.nodes.new("ShaderNodeMath"); b.operation = "DIVIDE"; b.inputs[1].default_value = largura
    nt.links.new(a.outputs[0], b.inputs[0])
    c = nt.nodes.new("ShaderNodeMath"); c.operation = "POWER"; c.inputs[1].default_value = 2.0
    nt.links.new(b.outputs[0], c.inputs[0])
    e = nt.nodes.new("ShaderNodeMath"); e.operation = "MULTIPLY"; e.inputs[1].default_value = -1.0
    nt.links.new(c.outputs[0], e.inputs[0])
    ex = nt.nodes.new("ShaderNodeMath"); ex.operation = "EXPONENT"
    nt.links.new(e.outputs[0], ex.inputs[0])
    g = nt.nodes.new("ShaderNodeMath"); g.operation = "MULTIPLY"; g.inputs[1].default_value = forca
    nt.links.new(ex.outputs[0], g.inputs[0])
    # gradiente vertical topo→meio
    h = nt.nodes.new("ShaderNodeMath"); h.operation = "DIVIDE"; h.inputs[1].default_value = 4.0
    nt.links.new(a.outputs[0], h.inputs[0])
    hc = nt.nodes.new("ShaderNodeClamp")
    nt.links.new(h.outputs[0], hc.inputs[0])
    m1 = nt.nodes.new("ShaderNodeMix"); m1.data_type = "RGBA"
    m1.inputs["A"].default_value = lin(meio); m1.inputs["B"].default_value = lin(topo)
    nt.links.new(hc.outputs[0], m1.inputs["Factor"])
    m2 = nt.nodes.new("ShaderNodeMix"); m2.data_type = "RGBA"
    m2.inputs["B"].default_value = lin(brilho)
    nt.links.new(m1.outputs["Result"], m2.inputs["A"])
    nt.links.new(g.outputs[0], m2.inputs["Factor"])
    nt.links.new(m2.outputs["Result"], em.inputs["Color"])
    return m


def palco_oficina(name, M, largura=14.0, fundo_y=3.0, profundidade=8.0, altura=8.0, passo=0.09, z_brilho=0.25):
    """Piso de chapa xadrez (z=0, de y=-profundidade/2 até fundo_y) + parede grafite com brilho laranja."""
    kc, kf = f"chapa_xadrez_{passo}", f"fundo_oficina_{z_brilho}"     # cache por parâmetro
    if kc not in M:
        M[kc] = chapa_xadrez_mat(kc, passo=passo)
    if kf not in M:
        M[kf] = fundo_brilho_mat(kf, z_brilho=z_brilho)
    root = empty(name)
    bm = bmesh.new()
    y0 = -profundidade / 2
    vs = [bm.verts.new(v) for v in ((-largura / 2, y0, 0), (largura / 2, y0, 0), (largura / 2, fundo_y, 0),
                                    (-largura / 2, fundo_y, 0))]
    bm.faces.new(vs)
    child(mesh_obj(name + "_piso", bm, M[kc]), root)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-largura / 2, 0, 0), (largura / 2, 0, 0), (largura / 2, 0, altura),
                                    (-largura / 2, 0, altura))]
    bm.faces.new(vs)
    child(mesh_obj(name + "_fundo", bm, M[kf]), root, (0, fundo_y, 0))
    return root
