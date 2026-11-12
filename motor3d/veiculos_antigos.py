"""Carros populares ANTIGOS brasileiros (estilo "real"), arquétipos genéricos: sem logotipo, sem nome, sem grade copiada.

Mesma técnica de veiculos3 (estilo "real"): carroceria de UMA malha por loft de anéis + Subsurf, com a silhueta
ajustada até bater com um perfil-alvo; detalhes colados por raycast. Daqui só se IMPORTA o veiculos3 (não editar lá).

Tipos (medidas reais em metros; montado 1:1 e reduzido pela raiz, escala=0.5 → 1:2 no mundo do motor):
- "quadradinho": hatch caixote dos anos 90/2000 (tipo Uno Mille). 3,69 x 1,55 x 1,44, entre-eixos 2,36, aro 13.
- "bolinha":     hatch arredondado de 1995–99 (tipo Gol "bola"). 3,81 x 1,64 x 1,40, entre-eixos 2,47, aro 13.
- "anos2000":    hatch em cunha arredondada (tipo Celta). 3,79 x 1,62 x 1,43, entre-eixos 2,44, aro 13.
- "sedan90":     sedã três volumes quadrado dos anos 90. 4,20 x 1,66 x 1,39, entre-eixos 2,55, aro 13.

carro_antigo(name, M, tipo, cor, conservacao="ok"|"gasto", escala=0.5) devolve o mesmo dict de veiculos3.carro():
raiz, rodas, lataria, rosto (None), corpo, partes, spec. Anda para +x, origem no chão no meio do entre-eixos.

Época: rodas de aço com calota plástica (furos, raios ou "turbina"), pneu de perfil alto, antena de haste no teto,
para-choques de plástico grossos, friso lateral, borrachão na base dos vidros, retrovisor pequeno preto, maçaneta de
puxar, palhetas no para-brisa, placa Mercosul sem letras. conservacao="gasto": pintura fosca com manchas, riscos e
sujeira embaixo (textura de ruído), plásticos desbotados e uma calota faltando (roda dianteira direita).
"""
import math
import bpy, bmesh
from mathutils import Vector

import veiculos3 as v3
from veiculos3 import (vazio, filho, caixa, elipsoide, torno, tubo, loft, Superficie, colar, fita, placa,
                       materiais, materiais_real, _pbr, _interp, _tag, _alvo, _fundo_real, _estacoes_real,
                       _belt_x, _larg_x, _crease_layer, lin, _no)

# ================================================================ cores de época
# nome: (hex, metálico, flocos)
COR_ANTIGA = {
    "prata": ("#AEB3B9", 0.6, True),
    "branco": ("#ECEBE4", 0.0, False),
    "vermelho": ("#B3191F", 0.05, False),
    "azul_escuro": ("#1B2C4E", 0.5, True),
    "verde_escuro": ("#1E3A2C", 0.5, True),
    "vinho": ("#561522", 0.35, True),
    "preto": ("#121315", 0.1, False),
}

ANTIGO_BASE = {  # nome: (cor, rough, metal, coat, spec, emit)
    "a_vidro": ("#121A19", 0.06, 0.0, 0.0, 0.3, 0.0),
    "a_plastico": ("#1C1D1F", 0.7, 0.0, 0.0, 0.35, 0.0),          # para-choque de plástico preto texturizado
    "a_plastico_gasto": ("#3C3D3F", 0.85, 0.0, 0.0, 0.3, 0.0),    # o mesmo, desbotado de sol
    "a_borracha": ("#0E0F10", 0.8, 0.0, 0.0, 0.3, 0.0),
    "a_aco": ("#2B2D30", 0.45, 0.4, 0.2, 0.5, 0.0),                # roda de aço pintada
    "a_calota": ("#BFC4CA", 0.3, 0.7, 0.4, 0.5, 0.0),              # plástico prateado da calota
    "a_calota_furo": ("#0B0C0D", 0.7, 0.0, 0.0, 0.2, 0.0),
    "a_porca": ("#8A9097", 0.35, 1.0, 0.0, 0.5, 0.0),
    "a_refletor": ("#E2E6EA", 0.08, 1.0, 0.0, 0.5, 0.0),
    "a_lampada": ("#FFF8E8", 0.2, 0.0, 0.0, 0.5, 1.5),
    "a_lanterna": ("#A3141B", 0.08, 0.0, 1.0, 0.7, 0.5),
    "a_lanterna_luz": ("#E8323A", 0.2, 0.0, 0.0, 0.5, 1.2),
    "a_pisca": ("#E07A12", 0.1, 0.0, 1.0, 0.6, 0.3),
    "a_re": ("#E9ECEF", 0.1, 0.0, 1.0, 0.6, 0.0),
    "a_cinza_parachoque": ("#5C6066", 0.55, 0.0, 0.1, 0.4, 0.0),
}


def _lente(name):
    """Lente de farol de vidro/acrílico transparente (por cima do refletor cromado)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1, 1, 1, 1)
    b.inputs["Roughness"].default_value = 0.04
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.5
    return m


def materiais_antigos(M):
    materiais(M)
    materiais_real(M)
    for n, (c, r, me, co, sp, e) in ANTIGO_BASE.items():
        if n not in M:
            M[n] = _pbr("va_" + n, c, r, me, co, sp, e)
    if "a_lente" not in M:
        M["a_lente"] = _lente("va_a_lente")
    return M


def _hex_metal(cor):
    if cor in COR_ANTIGA:
        return COR_ANTIGA[cor]
    hx = v3.REAL_COR.get(cor, v3.LATARIA.get(cor, cor))
    r, g, b = (int(hx.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    cinza = max(r, g, b) - min(r, g, b) < 0.08
    return hx, (0.55 if cinza and 0.3 < max(r, g, b) < 0.85 else 0.1), cinza


def pintura_antiga(name, cor, gasto=False):
    """Pintura de época. ok: verniz de fábrica um pouco menos espelhado que o carro novo. gasto: fosca (rough alta,
    coat baixo), manchas de verniz queimado, riscos finos horizontais e poeira subindo de baixo (ruído em coordenada
    de objeto, que está em metros)."""
    hx, metal, flocos = _hex_metal(cor)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    base = lin(hx)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat IOR"].default_value = 1.5
    if flocos:
        nz = _no(nt, "ShaderNodeTexNoise", Scale=900.0, Detail=1.0)
        bp = _no(nt, "ShaderNodeBump", Strength=0.05, Distance=0.02)
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    if not gasto:
        b.inputs["Base Color"].default_value = base
        b.inputs["Roughness"].default_value = 0.28
        b.inputs["Coat Weight"].default_value = 0.8
        b.inputs["Coat Roughness"].default_value = 0.05
        return m
    b.inputs["Coat Weight"].default_value = 0.15
    b.inputs["Coat Roughness"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    # manchas grandes (verniz queimado: mais claro e sem saturação)
    man = _no(nt, "ShaderNodeTexNoise", Scale=2.2, Detail=6.0, Roughness=0.6)
    nt.links.new(obj, man.inputs["Vector"])
    rm = nt.nodes.new("ShaderNodeValToRGB")
    rm.color_ramp.elements[0].position = 0.48
    rm.color_ramp.elements[1].position = 0.68
    nt.links.new(man.outputs["Fac"], rm.inputs["Fac"])
    lum = sum(base[:3]) / 3
    queimado = [base[i] * 0.55 + lum * 0.45 + 0.05 for i in range(3)] + [1.0]
    mix1 = nt.nodes.new("ShaderNodeMix")
    mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = base
    mix1.inputs["B"].default_value = queimado
    nt.links.new(rm.outputs["Color"], mix1.inputs["Factor"])
    # riscos: ruído esticado em x (muda rápido em y/z, devagar em x) → filetes horizontais finos, em manchas
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.5, 70.0, 70.0)
    nt.links.new(obj, mp.inputs["Vector"])
    rs = _no(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=2.0)
    nt.links.new(mp.outputs["Vector"], rs.inputs["Vector"])
    rr = nt.nodes.new("ShaderNodeValToRGB")
    rr.color_ramp.elements[0].position = 0.70
    rr.color_ramp.elements[1].position = 0.74
    nt.links.new(rs.outputs["Fac"], rr.inputs["Fac"])
    zona = _no(nt, "ShaderNodeTexNoise", Scale=1.4, Detail=2.0)
    nt.links.new(obj, zona.inputs["Vector"])
    rz = nt.nodes.new("ShaderNodeValToRGB")
    rz.color_ramp.elements[0].position = 0.5
    rz.color_ramp.elements[1].position = 0.62
    nt.links.new(zona.outputs["Fac"], rz.inputs["Fac"])
    risco = nt.nodes.new("ShaderNodeMath")
    risco.operation = "MULTIPLY"
    nt.links.new(rr.outputs["Color"], risco.inputs[0])
    nt.links.new(rz.outputs["Color"], risco.inputs[1])
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = lin("#B9B6AE")
    nt.links.new(risco.outputs["Value"], mix2.inputs["Factor"])
    # poeira/barro subindo de baixo (z local < ~0,55 m)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(obj, sep.inputs[0])
    pz = nt.nodes.new("ShaderNodeMapRange")
    pz.inputs["From Min"].default_value = 0.22
    pz.inputs["From Max"].default_value = 0.62
    pz.inputs["To Min"].default_value = 0.75
    pz.inputs["To Max"].default_value = 0.0
    nt.links.new(sep.outputs["Z"], pz.inputs["Value"])
    pn = _no(nt, "ShaderNodeTexNoise", Scale=9.0, Detail=4.0)
    nt.links.new(obj, pn.inputs["Vector"])
    pm = nt.nodes.new("ShaderNodeMath")
    pm.operation = "MULTIPLY"
    nt.links.new(pz.outputs["Result"], pm.inputs[0])
    nt.links.new(pn.outputs["Fac"], pm.inputs[1])
    mix3 = nt.nodes.new("ShaderNodeMix")
    mix3.data_type = "RGBA"
    nt.links.new(mix2.outputs["Result"], mix3.inputs["A"])
    mix3.inputs["B"].default_value = lin("#6B5D4A")
    nt.links.new(pm.outputs["Value"], mix3.inputs["Factor"])
    nt.links.new(mix3.outputs["Result"], b.inputs["Base Color"])
    # rugosidade: 0,5 de base, mais áspera nas manchas e na poeira
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.42
    ro.inputs["To Max"].default_value = 0.72
    nt.links.new(man.outputs["Fac"], ro.inputs["Value"])
    ro2 = nt.nodes.new("ShaderNodeMath")
    ro2.operation = "ADD"
    ro2.use_clamp = True
    nt.links.new(ro.outputs["Result"], ro2.inputs[0])
    nt.links.new(pm.outputs["Value"], ro2.inputs[1])
    nt.links.new(ro2.outputs["Value"], b.inputs["Roughness"])
    return m


def pintura_antiga_mat(M, cor, gasto=False):
    k = f"pinta_{cor}_{'g' if gasto else 'o'}"
    if k not in M:
        M[k] = pintura_antiga("va_" + k, cor, gasto)
    return M[k]


# ================================================================ roda de aço + calota
def roda_antiga(name, M, R=0.28, larg=0.155, aro_r=0.165, calota="furos", gasto=False):
    """Pneu de perfil alto (flanco ~ 12 cm no aro 13) + roda de aço pintada + calota plástica.
    calota: "furos" (anel de furos redondos), "raios" (fendas radiais), "turbina" (muitas fendas finas) ou None
    (roda de aço à mostra, com 4 porcas). Eixo y, face externa em +y, centro na origem."""
    root = vazio(name)
    w = larg / 2
    g = 0.006
    meio = [(R, 0.0, 0), (R, w * 0.18, 0), (R - g, w * 0.19, 0), (R - g, w * 0.27, 0), (R, w * 0.28, 0),
            (R, w * 0.66, 0), (R - g, w * 0.67, 0), (R - g, w * 0.74, 0), (R, w * 0.75, 0), (R, w * 0.86, 0),
            (R - 0.010, w * 0.97, 0), (R - 0.028, w * 1.02, 1)]
    flanco = [(R - 0.06, w * 1.06, 1), ((R + aro_r) / 2, w * 1.04, 1), (aro_r + 0.035, w * 0.96, 1),
              (aro_r + 0.008, w * 0.86, 1)]
    meia = meio + flanco
    perfil = [(r, -y, mi) for (r, y, mi) in reversed(meia[1:])] + meia
    pf = []
    for i, (r, y, mi) in enumerate(perfil):
        nxt = perfil[i + 1][2] if i + 1 < len(perfil) else mi
        pf.append((r, y, max(mi, nxt) if y < 0 else mi))
    filho(torno(name + "_pneu", pf, [M["r_borracha"], M["r_flanco"]], seg=96), root)
    yb = w * 0.86
    # roda de aço: aba do aro + prato rebaixado até o cubo
    aco = [(aro_r + 0.010, yb, 0), (aro_r + 0.010, yb - 0.008, 0), (aro_r - 0.004, yb - 0.014, 0),
           (aro_r - 0.012, yb - 0.035, 0), (aro_r * 0.80, yb - 0.040, 0), (aro_r * 0.70, yb - 0.030, 0),
           (aro_r * 0.45, yb - 0.020, 0), (aro_r * 0.30, yb - 0.026, 0), (0.0, yb - 0.026, 0)]
    filho(torno(name + "_aco", aco, [M["a_aco"]], seg=64), root)
    if calota is None:
        y0 = yb - 0.026
        filho(torno(name + "_cubo", [(0.0, y0 + 0.03, 0), (0.028, y0 + 0.03, 0), (0.032, y0 + 0.02, 0),
                                     (0.034, y0, 0)], [M["a_porca"]], seg=32), root)
        for k in range(4):
            a = 2 * math.pi * k / 4 + math.pi / 4
            p = caixa(f"{name}_porca{k}", (math.sin(a) * 0.05, y0 + 0.012, math.cos(a) * 0.05), (0.02, 0.022, 0.02),
                      M["a_porca"], raio=0.3)
            filho(p, root)
        for k in range(4):   # furos de ventilação da roda de aço
            a = 2 * math.pi * k / 4
            f = elipsoide(f"{name}_ventil{k}", (math.sin(a) * aro_r * 0.6, yb - 0.035, math.cos(a) * aro_r * 0.6),
                          (0.022, 0.004, 0.022), M["a_calota_furo"], seg=16)
            filho(f, root)
        return root
    # calota: prato abaulado que cobre o aro até a aba
    rc = aro_r + 0.004
    ys = yb + 0.004
    cal = [(rc, ys - 0.012, 0), (rc + 0.002, ys - 0.004, 0), (rc - 0.006, ys + 0.004, 0), (rc * 0.85, ys + 0.010, 0),
           (rc * 0.55, ys + 0.020, 0), (rc * 0.30, ys + 0.028, 0), (rc * 0.22, ys + 0.030, 0),
           (rc * 0.20, ys + 0.034, 0), (0.0, ys + 0.036, 0)]
    filho(torno(name + "_calota", cal, [M["a_calota"]], seg=72), root)

    def y_sup(r):   # altura da superfície da calota no raio r
        return _interp([(p[0], p[1]) for p in reversed(cal)], r)

    furo = M["a_calota_furo"]
    if calota == "furos":
        for k in range(10):
            a = 2 * math.pi * k / 10
            r = rc * 0.66
            filho(elipsoide(f"{name}_furo{k}", (math.sin(a) * r, y_sup(r) + 0.001, math.cos(a) * r),
                            (0.020, 0.004, 0.020), furo, seg=16), root)
    elif calota == "raios":
        for k in range(7):
            a = 2 * math.pi * k / 7
            r = rc * 0.62
            fd = caixa(f"{name}_fenda{k}", (0, 0, 0), (0.024, 0.008, rc * 0.42), furo, raio=0.45)
            fd.location = (math.sin(a) * r, y_sup(r) + 0.001, math.cos(a) * r)
            fd.rotation_euler = (0, a, 0)
            filho(fd, root)
    elif calota == "turbina":
        for k in range(16):
            a = 2 * math.pi * k / 16
            r = rc * 0.68
            fd = caixa(f"{name}_fenda{k}", (0, 0, 0), (0.010, 0.008, rc * 0.36), furo, raio=0.45)
            fd.location = (math.sin(a) * r, y_sup(r) + 0.001, math.cos(a) * r)
            fd.rotation_euler = (0, a + 0.25, 0)
            filho(fd, root)
    # miolo liso (sem logotipo)
    filho(elipsoide(name + "_miolo", (0, ys + 0.034, 0), (rc * 0.19, 0.006, rc * 0.19), M["a_calota"], seg=24),
          root)
    return root


# ================================================================ arquétipos
def _spec_antigo(tipo):
    """Perfis-alvo com x medido a partir do para-choque dianteiro (como num desenho de lado), listados da traseira
    para a frente: (x, z, material do trecho seguinte, rumo à frente). cintura = linha da base dos vidros; larguras =
    meia-largura (vista de cima); janelas e portas também em x do desenho. Tudo convertido por _alvo()."""
    s = dict(zb=0.20, zpara=0.30, tumble=0.03, teto_in=(0.02, 0.015), vidro_h=0.85, afina=0.03, quina=1.0,
             crease={1: 0.6, 2: 0.95, 3: 0.45, 4: 0.85, 5: 0.6, 6: 0.3, 7: 0.55}, crease_ponta=0.45,
             bojo=(0.03, 0.04), pilar_b="lata", parachoque="preto", farol="retangular", lanterna="vertical",
             calota="furos", friso=True)
    if tipo == "quadradinho":    # caixote: frente curta e de pé, teto reto, traseira vertical
        s.update(L=3.69, wb=2.36, fr=0.72, R=0.281, larg=0.145, aro=0.165, H=1.44)
        topo = [(3.69, 0.98, "lata"), (3.665, 1.03, "vidro"), (3.57, 1.38, "lata"), (3.50, 1.425, "teto"),
                (1.50, 1.44, "teto"), (1.40, 1.41, "vidro"), (0.92, 0.925, "lata"), (0.10, 0.82, "lata"),
                (0.02, 0.78, "lata"), (0.0, 0.74, None)]
        cintura = [(3.69, 0.99), (3.45, 0.965), (0.92, 0.925), (0.0, 0.925)]
        larguras = [(3.69, 0.755), (3.35, 0.775), (0.85, 0.775), (0.0, 0.752)]
        janelas = [(0.95, 2.20), (2.29, 3.49)]
        portas = [0.86, 2.25]
    elif tipo == "bolinha":      # tudo arredondado: capô caído, para-brisa deitado, teto em arco, vidro traseiro inclinado
        s.update(L=3.81, wb=2.47, fr=0.74, R=0.288, larg=0.175, aro=0.165, H=1.40, zb=0.21, tumble=0.075,
                 teto_in=(0.045, 0.05), vidro_h=0.82, afina=0.06, quina=1.4,
                 crease={1: 0.5, 2: 0.8, 3: 0.2, 4: 0.45, 5: 0.35, 6: 0.0, 7: 0.15}, crease_ponta=0.0,
                 bojo=(0.08, 0.12), parachoque="cor", farol="oval", lanterna="horizontal", calota="raios")
        topo = [(3.81, 0.90, "lata"), (3.76, 0.97, "lata"), (3.69, 1.00, "vidro"), (3.30, 1.325, "lata"),
                (3.12, 1.375, "teto"), (2.35, 1.40, "teto"), (1.80, 1.375, "vidro"), (1.00, 0.895, "lata"),
                (0.40, 0.80, "lata"), (0.10, 0.73, "lata"), (0.0, 0.66, None)]
        cintura = [(3.81, 0.99), (3.30, 0.975), (1.00, 0.90), (0.0, 0.90)]
        larguras = [(3.81, 0.775), (3.35, 0.815), (0.95, 0.82), (0.35, 0.80), (0.0, 0.745)]
        janelas = [(1.05, 2.43), (2.52, 3.22)]
        portas = [0.96, 2.47]
    elif tipo == "anos2000":     # cunha arredondada: frente baixa, cintura subindo, traseira alta, janelas pequenas
        s.update(L=3.79, wb=2.44, fr=0.73, R=0.280, larg=0.165, aro=0.165, H=1.43, zb=0.20, tumble=0.06,
                 teto_in=(0.04, 0.04), vidro_h=0.83, afina=0.05, quina=1.25,
                 crease={1: 0.5, 2: 0.85, 3: 0.25, 4: 0.6, 5: 0.4, 6: 0.1, 7: 0.25}, crease_ponta=0.1,
                 bojo=(0.07, 0.10), pilar_b="preto", parachoque="cor", farol="cunha", lanterna="alta",
                 calota="turbina", friso=False)
        topo = [(3.79, 0.88, "lata"), (3.75, 0.99, "lata"), (3.67, 1.07, "vidro"), (3.43, 1.375, "lata"),
                (3.28, 1.42, "teto"), (2.25, 1.43, "teto"), (1.72, 1.40, "vidro"), (0.97, 0.905, "lata"),
                (0.40, 0.78, "lata"), (0.08, 0.68, "lata"), (0.0, 0.62, None)]
        cintura = [(3.79, 1.07), (3.40, 1.065), (0.97, 0.905), (0.0, 0.905)]
        larguras = [(3.79, 0.765), (3.30, 0.81), (0.95, 0.81), (0.30, 0.79), (0.0, 0.735)]
        janelas = [(1.00, 1.96), (2.04, 2.83)]
        portas = [0.93, 1.99, 2.86]
    elif tipo == "sedan90":      # três volumes reto: capô comprido, porta-malas plano, colunas finas
        s.update(L=4.20, wb=2.55, fr=0.83, R=0.292, larg=0.185, aro=0.165, H=1.39, zb=0.19, calota="turbina",
                 lanterna="faixa")
        topo = [(4.20, 0.93, "lata"), (4.13, 0.975, "lata"), (3.62, 0.995, "lata"), (3.47, 1.01, "vidro"),
                (2.97, 1.355, "lata"), (2.88, 1.385, "teto"), (1.72, 1.395, "teto"), (1.62, 1.37, "vidro"),
                (1.02, 0.915, "lata"), (0.10, 0.80, "lata"), (0.02, 0.77, "lata"), (0.0, 0.73, None)]
        cintura = [(4.20, 0.97), (3.40, 0.965), (1.02, 0.915), (0.0, 0.915)]
        larguras = [(4.20, 0.80), (3.85, 0.83), (0.90, 0.83), (0.0, 0.805)]
        janelas = [(1.05, 2.00), (2.08, 2.93)]
        portas = [0.97, 2.04, 3.02]
    else:
        raise ValueError(tipo)
    xf = s["wb"] / 2
    s["tr"] = s["L"] - s["wb"] - s["fr"]
    s["xf"], s["xr"] = xf, -xf
    s["XF"], s["XR"] = xf + s["fr"], -xf - s["tr"]
    a = lambda x: round(xf + s["fr"] - x, 4)       # x do desenho → x do motor
    s["topo"] = _alvo(topo, s["fr"], xf)
    s["cintura"] = _alvo(cintura, s["fr"], xf)
    s["larguras"] = _alvo(larguras, s["fr"], xf)
    s["janelas"] = sorted((a(x1), a(x0)) for x0, x1 in janelas)
    s["portas"] = [a(x) for x in portas]
    s["W"] = max(w for _, w in s["larguras"])
    s["belt"] = cintura[-1][1]
    s["roof"] = s["H"]
    s["alvo"] = a
    s["tipo"] = tipo
    return s


def _anel_antigo(s, x, ponta=0.0, dz=0.0):
    """Meio anel de 9 pontos como veiculos3._anel_real, mas com o "arredondamento" do tipo: tumble (quanto a estufa
    fecha para dentro), teto_in (raio da quina do teto), quina (raio das quinas de baixo), vidro_h (coluna fina)."""
    q = s["quina"]
    W = _larg_x(s, x) * (1 - s["afina"] * ponta)
    zb = _fundo_real(s, x) + 0.03 * ponta
    zt = _interp(s["topo"], x) - 0.02 * ponta + dz
    belt = _belt_x(s, x) - 0.01 * ponta
    hc = s["roof"] - s["belt"]
    h = max(zt - belt, 0.035)
    f = min(1.0, max(0.0, (zt - s["belt"]) / hc))
    zs = min(zb + 0.07, belt - 0.30)
    zp = min(max(s["zb"] + s["zpara"], zs + 0.06), belt - 0.16)
    zs = max(zs, zb + 0.03)
    zp = max(zp, zs + 0.03)
    belt = max(belt, zp + 0.03)
    p5y = W - 0.02 - s["tumble"] * f
    a, b = s["teto_in"]
    return [
        (0.0, zb),
        (W - 0.06 * q, zb),
        (W - 0.025 * q, zs),
        (W, zp),
        (W - 0.012 * q, belt),
        (W - 0.018 - 0.01 * f, belt + min(0.025, 0.35 * h)),
        (p5y, belt + s["vidro_h"] * h),
        (p5y - a - b * f, belt + (0.975 if q <= 1 else 0.955) * h),
        (0.0, zt),
    ]


def _vincar_pontas(o, xs, val):
    """Vinca as arestas do anel da primeira e da última estação (quina da frente/traseira vista de cima)."""
    if val <= 0:
        return
    bm = bmesh.new()
    bm.from_mesh(o.data)
    lay = _crease_layer(bm)
    for e in bm.edges:
        a, b = e.verts
        for xe in (xs[0], xs[-1]):
            if abs(a.co.x - xe) < 1e-6 and abs(b.co.x - xe) < 1e-6 and (abs(a.co.y) > 1e-6 or abs(b.co.y) > 1e-6):
                e[lay] = val
    bm.to_mesh(o.data)
    bm.free()


def _corpo(name, s, mats_l, mat_seg, xs, nivel):
    dzs = [0.0] * len(xs)
    corpo = None
    for passada in range(4):
        aneis = [_anel_antigo(s, x, 1.0 if i in (0, len(xs) - 1) else 0.0, dzs[i]) for i, x in enumerate(xs)]
        if corpo is not None:
            me = corpo.data
            bpy.data.objects.remove(corpo)
            bpy.data.meshes.remove(me)
        corpo = loft(name + "_lata", xs, aneis, mats_l, mat_seg, crease=s["crease"], bojo=s["bojo"], nivel=nivel)
        _vincar_pontas(corpo, xs, s["crease_ponta"])
        if passada == 3:
            break
        sup_ = Superficie(corpo)
        for i, x in enumerate(xs):
            xm = min(max(x, s["XR"] + 0.04), s["XF"] - 0.04)
            loc, _n = sup_.raio((xm, 0, 5), (0, 0, -1))
            if loc is not None:
                dzs[i] += (_interp(s["topo"], xm) - loc.z) * 0.9
    return corpo


def _varre(X, sx, W, z, u0, u1, n, wrap=0.78, t_max=1.0):
    """Raios que varrem a frente (sx=1) ou a traseira (sx=-1) de y = u0*W até u1*W, dobrando a quina a partir de
    |u| > wrap (t_canto até t_max)."""
    out = []
    for k in range(n):
        u = u0 + (u1 - u0) * k / (n - 1)
        sy = 1 if u >= 0 else -1
        tc = min(t_max, max(0.0, (abs(u) - wrap) / (1 - wrap)) ** 1.4 * t_max)
        out.append(v3._canto(X, sy, abs(u) * W, z, tc, sx))
    return out


def carro_antigo(name, M, tipo="quadradinho", cor="branco", conservacao="ok", escala=0.5, placa_on=True, nivel=2):
    materiais_antigos(M)
    gasto = conservacao == "gasto"
    tinta = pintura_antiga_mat(M, cor, gasto)
    plast = M["a_plastico_gasto" if gasto else "a_plastico"]
    s = _spec_antigo(tipo)
    root = vazio(name)
    xs = _estacoes_real(s)
    topo, jan = s["topo"], s["janelas"]
    PINT, VIDRO, PLAST, BRILHO = 0, 1, 2, 3
    S = len(xs)

    def mat_seg(i, j):
        if i == -1 or i == S - 1:
            return PLAST if j == 1 else PINT
        xm = (xs[i] + xs[i + 1]) / 2
        tg = _tag(topo, xm)
        if j in (6, 7) and tg == "vidro":
            return VIDRO
        if j == 5:
            if any(a <= xm <= b for a, b in jan):
                return VIDRO
            if s["pilar_b"] == "preto" and len(jan) > 1 and jan[0][1] <= xm <= jan[1][0]:
                return BRILHO
        if j == 0:
            return PLAST
        if j == 1 and (i <= 1 or i >= S - 3):
            return PLAST
        return PINT

    mats_l = [tinta, M["a_vidro"], plast, M["r_preto_brilho"]]
    corpo = _corpo(name, s, mats_l, mat_seg, xs, nivel)
    filho(corpo, root)

    R, larg, W = s["R"], s["larg"], s["W"]
    XF, XR = s["XF"], s["XR"]
    yi = W - larg - 0.07
    filho(caixa(name + "_forro", ((XF + XR) / 2, 0, (s["zb"] + 2 * R + 0.05) / 2 + 0.02),
                (XF - XR - 0.5, 2 * yi, 2 * R + 0.05 - s["zb"]), M["forro"], raio=0.2), root)
    # ---- rodas: aço + calota; no "gasto" a dianteira direita (lado -y, o da câmera) perdeu a calota
    rodas = []
    for lado, xw in (("d", s["xf"]), ("t", s["xr"])):
        yw = _larg_x(s, xw) - larg / 2 - 0.018
        for sy in (1, -1):
            sem = gasto and lado == "d" and sy < 0
            rd = roda_antiga(f"{name}_roda_{lado}{'e' if sy > 0 else 'd'}", M, R, larg, s["aro"],
                             None if sem else s["calota"], gasto)
            if sy < 0:
                rd.rotation_euler = (0, 0, math.pi)
            filho(rd, root, (xw, sy * yw, R))
            rodas.append(rd)

    sup = Superficie(corpo)
    orn = []
    add = lambda *os_: orn.extend(o for o in os_ if o)

    # ---- para-choques (faixa grossa que dobra as quinas e corre um pouco pela lateral)
    cor_pc = {"preto": plast, "cor": tinta, "cinza": M["a_cinza_parachoque"]}[s["parachoque"]]
    zpc = s["zb"] + 0.16
    hpc = 0.20 if s["parachoque"] == "preto" else 0.17
    epc = 0.035 if s["parachoque"] == "preto" else 0.022
    for lado, sx, X in (("d", 1, XF), ("t", -1, XR)):
        am = _varre(X, sx, _larg_x(s, X - sx * 0.1), zpc, -0.99, 0.99, 41, wrap=0.80)
        add(fita(f"{name}_parachoque_{lado}", sup, am, hpc, epc, cor_pc, embute=0.01))
        if s["parachoque"] != "preto":   # filete preto de borracha no meio do para-choque na cor
            add(fita(f"{name}_parachoque_filete_{lado}", sup,
                     _varre(X, sx, _larg_x(s, X - sx * 0.1), zpc + 0.01, -0.97, 0.97, 41, wrap=0.80),
                     0.035, epc + 0.008, M["a_borracha"], embute=0.01))
    # ---- frente: faróis, grade, piscas
    zcap = _interp(topo, XF - 0.06)
    tp = s["farol"]
    if tp == "retangular":   # faróis retangulares de pé, grade de filetes entre eles (sem copiar desenho)
        zfa = zcap - 0.10
        for sy in (1, -1):
            am = [((XF + 3, sy * W * (0.40 + 0.47 * k / 10), zfa), (-1, 0, 0)) for k in range(11)]
            add(fita(f"{name}_farol_ref{sy}", sup, am, 0.115, 0.004, M["a_refletor"]),
                fita(f"{name}_farol{sy}", sup, am, 0.13, 0.010, M["a_lente"]),
                fita(f"{name}_farol_moldura{sy}", sup, am, 0.15, 0.002, M["r_preto_brilho"]))
            pc = [((XF + 3, sy * W * (0.89 + 0.06 * k / 4), zfa), (-1, 0, 0)) for k in range(5)]
            pc += [v3._canto(XF, sy, W * 0.96, zfa, t) for t in (0.4, 0.7, 1.0)]
            add(fita(f"{name}_pisca{sy}", sup, pc, 0.115, 0.008, M["a_pisca"]))
        add(fita(name + "_grade", sup, [((XF + 3, W * (-0.37 + 0.74 * k / 12), zfa), (-1, 0, 0)) for k in range(13)],
                 0.12, 0.004, M["r_preto_brilho"]))
        for q in range(4):
            add(fita(f"{name}_grade_filete{q}", sup, [((XF + 3, W * (-0.35 + 0.70 * k / 12), zfa - 0.045 + 0.03 * q),
                                                       (-1, 0, 0)) for k in range(13)], 0.009, 0.009, plast))
    elif tp == "oval":       # faróis ovais grandes inclinados + grade pequena (fenda) no meio
        zfa = zcap - 0.085
        for sy in (1, -1):
            for nm, raios, m_, emb in (("moldura", (0.02, 0.165, 0.092), M["r_preto_brilho"], 0.012),
                                       ("ref", (0.02, 0.150, 0.080), M["a_refletor"], 0.008),
                                       ("lente", (0.03, 0.152, 0.082), M["a_lente"], 0.010)):
                e = elipsoide(f"{name}_farol_{nm}{sy}", (0, 0, 0), raios, m_, seg=32)
                colar(e, sup, v3._canto(XF, sy, W * 0.62, zfa, 0.15)[0], v3._canto(XF, sy, W * 0.62, zfa, 0.15)[1],
                      embute=emb)
                add(e)
            lp = elipsoide(f"{name}_farol_lamp{sy}", (0, 0, 0), (0.02, 0.035, 0.035), M["a_lampada"], seg=16)
            colar(lp, sup, *v3._canto(XF, sy, W * 0.58, zfa, 0.15), embute=0.006)
            pc = [v3._canto(XF, sy, W * (0.86 + 0.10 * t), zfa - 0.005, 0.25 + 0.75 * t) for t in
                  [k / 6 for k in range(7)]]
            add(lp, fita(f"{name}_pisca{sy}", sup, pc, 0.07, 0.008, M["a_pisca"]))
        add(fita(name + "_grade", sup, [((XF + 3, W * (-0.33 + 0.66 * k / 12), zfa + 0.01), (-1, 0, 0))
                                        for k in range(13)], 0.055, 0.004, M["r_preto_brilho"]))
        add(fita(name + "_grade_filete", sup, [((XF + 3, W * (-0.31 + 0.62 * k / 12), zfa + 0.01), (-1, 0, 0))
                                               for k in range(13)], 0.008, 0.008, M["a_cinza_parachoque"]))
        # tomada de ar no para-choque
        add(fita(name + "_tomada", sup, [((XF + 3, W * (-0.45 + 0.9 * k / 12), zpc - 0.02), (-1, 0, 0))
                                         for k in range(13)], 0.06, 0.03, M["a_borracha"], embute=0.01))
    elif tp == "cunha":      # faróis grandes arredondados que sobem pela quina; grade fina; tomada larga embaixo
        zfa = zcap - 0.075
        for sy in (1, -1):
            am = [v3._canto(XF, sy, W * (0.36 + 0.60 * t), zfa + 0.025 * t, max(0, (t - 0.45) / 0.55) ** 1.3)
                  for t in [k / 16 for k in range(17)]]
            larg_f = lambda t: 0.10 + 0.07 * math.sin(math.pi * min(1, 0.15 + t * 1.0))
            add(fita(f"{name}_farol_moldura{sy}", sup, am, lambda t: larg_f(t) + 0.02, 0.002, M["r_preto_brilho"]),
                fita(f"{name}_farol_ref{sy}", sup, am[1:-1], lambda t: larg_f(t) - 0.02, 0.005, M["a_refletor"]),
                fita(f"{name}_farol{sy}", sup, am, larg_f, 0.012, M["a_lente"]))
            add(fita(f"{name}_pisca{sy}", sup, am[11:], 0.04, 0.014, M["a_pisca"]))
        add(fita(name + "_grade", sup, [((XF + 3, W * (-0.30 + 0.60 * k / 12), zfa - 0.01), (-1, 0, 0))
                                        for k in range(13)], lambda t: 0.07 - 0.02 * abs(2 * t - 1), 0.004,
                 M["r_preto_brilho"]))
        add(fita(name + "_tomada", sup, [((XF + 3, W * (-0.55 + 1.1 * k / 14), zpc - 0.03), (-1, 0, 0))
                                         for k in range(15)], 0.07, 0.03, M["a_borracha"], embute=0.01))
    # ---- traseira: lanternas
    zre = _interp(topo, XR + 0.03)
    lt = s["lanterna"]
    for sy in (1, -1):
        if lt == "vertical":     # lanternas de pé nas quinas, ao lado da tampa
            z0, z1 = zpc + 0.13, zre - 0.03
            for nm, uu, m_, e_ in (("", (0.83, 0.97), M["a_lanterna"], 0.006),):
                am = [((XR - 3, sy * W * 0.88, z0 + (z1 - z0) * k / 8), (1, 0, 0)) for k in range(9)]
                add(fita(f"{name}_lanterna{sy}", sup, am, 0.17, 0.006, M["a_lanterna"]))
                add(fita(f"{name}_lanterna_pisca{sy}", sup, am[6:], 0.17, 0.009, M["a_pisca"]))
                add(fita(f"{name}_lanterna_re{sy}", sup, am[:2], 0.17, 0.009, M["a_re"]))
        elif lt == "horizontal":  # retângulos deitados embaixo do vidro, dobrando a quina
            am = _varre(XR, -1, W, zre - 0.11, sy * 0.38, sy * 0.99, 14, wrap=0.80, t_max=0.8)
            add(fita(f"{name}_lanterna{sy}", sup, am, 0.13, 0.006, M["a_lanterna"]))
            add(fita(f"{name}_lanterna_pisca{sy}", sup, am[:4], 0.13, 0.009, M["a_pisca"]))
            add(fita(f"{name}_lanterna_re{sy}", sup, am[4:7], 0.13, 0.009, M["a_re"]))
        elif lt == "alta":        # lanternas altas e arredondadas na quina, subindo até a base do vidro
            z0, z1 = zpc + 0.15, zre + 0.10
            am = [v3._canto(XR, sy, W * 0.86, z0 + (z1 - z0) * k / 10, 0.45, sx=-1) for k in range(11)]
            add(fita(f"{name}_lanterna{sy}", sup, am, lambda t: 0.13 + 0.05 * math.sin(math.pi * t), 0.008,
                     M["a_lanterna"]))
            add(fita(f"{name}_lanterna_pisca{sy}", sup, am[5:8], 0.11, 0.012, M["a_pisca"]))
        elif lt == "faixa":       # sedã: faixa larga de ponta a ponta na tampa do porta-malas
            am = _varre(XR, -1, W, zre - 0.10, sy * 0.06, sy * 0.99, 16, wrap=0.85, t_max=0.8)
            add(fita(f"{name}_lanterna{sy}", sup, am, 0.12, 0.006, M["a_lanterna"]))
            add(fita(f"{name}_lanterna_pisca{sy}", sup, am[9:12], 0.12, 0.009, M["a_pisca"]))
            add(fita(f"{name}_lanterna_re{sy}", sup, am[5:8], 0.12, 0.009, M["a_re"]))
    # ---- laterais: friso preto, borrachão da base dos vidros, juntas de porta, maçanetas de puxar
    xa0 = s["xr"] + s["R"] + 0.11
    xa1 = s["xf"] - s["R"] - 0.11
    for sy in (1, -1):
        if s["friso"]:
            zf = s["zb"] + s["zpara"] + 0.09
            am = [((xa0 + (xa1 - xa0) * k / 20, sy * 3, zf), (0, -sy, 0)) for k in range(21)]
            add(fita(f"{name}_friso{sy}", sup, am, 0.055, 0.010, plast, embute=0.006))
        x0, x1 = jan[0][0] - 0.06, jan[-1][1] + 0.04
        am = [((x0 + (x1 - x0) * k / 30, sy * 3, _belt_x(s, x0 + (x1 - x0) * k / 30) + 0.006), (0, -sy, 0))
              for k in range(31)]
        add(fita(f"{name}_borrachao{sy}", sup, am, 0.018, 0.006, M["a_borracha"], embute=0.004))
    for k, xp in enumerate(s["portas"]):
        zt_ = _belt_x(s, xp) + 0.005
        z0 = max(_fundo_real(s, xp), s["zb"]) + 0.07
        for sy in (1, -1):
            am = [((xp, sy * 3, zz), (0, -sy, 0)) for zz in [z0 + (zt_ - z0) * q / 10 for q in range(11)]]
            add(fita(f"{name}_junta{k}{sy}", sup, am, 0.005, 0.0006, M["r_junta"], embute=0.004))
    for k in range(len(s["portas"]) - 1):
        xm = s["portas"][k + 1] - 0.13 if s["portas"][k + 1] > s["portas"][k] else s["portas"][k + 1] + 0.13
        xm = max(s["portas"][k], s["portas"][k + 1]) - 0.0
        xm = min(s["portas"][k], s["portas"][k + 1]) + 0.12      # perto da borda de trás da porta
        for sy in (1, -1):
            mc = caixa(f"{name}_macaneta{k}{sy}", (0, 0, 0), (0.018, 0.15, 0.03), M["a_borracha"], raio=0.35)
            colar(mc, sup, (xm, sy * 3, _belt_x(s, xm) - 0.07), (0, -sy, 0), embute=0.004)
            add(mc)
    # ---- retrovisor pequeno preto no canto da janela dianteira
    xb = jan[-1][1] - 0.07
    for sy in (1, -1):
        loc, nor = sup.raio((xb, sy * 3, _belt_x(s, xb) + 0.05), (0, -sy, 0))
        if loc is None:
            continue
        add(caixa(f"{name}_retro_base{sy}", loc + Vector((0, sy * 0.02, 0.0)), (0.09, 0.05, 0.08), M["a_borracha"],
                  raio=0.3),
            caixa(f"{name}_retro{sy}", loc + Vector((-0.02, sy * 0.085, 0.03)), (0.07, 0.13, 0.095),
                  M["r_plastico"], raio=0.4))
    # ---- palhetas do para-brisa (no pé do vidro)
    xw0 = max(x for x, _, tg in topo if tg == "lata" and x > 0.2)   # base do para-brisa
    for k, (ya, yb_) in enumerate(((-0.62, 0.02), (0.06, 0.66))):
        pts = []
        for t in (0.0, 0.5, 1.0):
            y = W * (ya + (yb_ - ya) * t)
            loc, _ = sup.raio((xw0 - 0.10 - 0.03 * t, y, 5), (0, 0, -1))
            if loc is not None:
                pts.append(loc + Vector((0, 0, 0.012)))
        if len(pts) > 1:
            add(tubo(f"{name}_palheta{k}", pts, 0.008, M["a_borracha"], seg=8))
    # ---- antena de haste no teto (base preta na frente do teto, haste inclinada para trás)
    xt = max(x for x, _, tg in topo if tg == "teto") - 0.10
    loc, _ = sup.raio((xt, -W * 0.35, 5), (0, 0, -1))
    if loc is not None:
        add(elipsoide(name + "_antena_base", loc, (0.03, 0.022, 0.018), M["a_borracha"], seg=16))
        ang = math.radians(28)
        p1 = loc + Vector((-math.sin(ang) * 0.62, 0, math.cos(ang) * 0.62))
        add(tubo(name + "_antena", [loc + Vector((0, 0, 0.01)), p1], 0.0045, M["a_borracha"], seg=8, suave=False))
    # ---- placas Mercosul (sem letras) no para-choque dianteiro e na tampa traseira
    if placa_on:
        for lado, sx, z, esp in (("d", 1, zpc, epc), ("t", -1, zpc + 0.24, 0.0)):
            if lado == "t" and tipo in ("quadradinho",):
                z = zpc + 0.22
            pl = placa(f"{name}_placa_{lado}", M, larg=0.40, alt=0.13, esp=0.012)
            loc, nor = sup.raio((sx * 6, 0, z), (-sx, 0, 0))
            if loc is not None:
                pl.location = loc + Vector((sx * (esp + 0.008), 0, 0))
                pl.rotation_euler = (0, 0, 0 if sx > 0 else math.pi)
                add(pl)
    for o in orn:
        filho(o, root)
    root.scale = (escala, escala, escala)
    return {"raiz": root, "rodas": rodas, "lataria": [corpo], "rosto": None, "corpo": corpo,
            "partes": {"corpo": corpo, "ornamentos": orn}, "spec": s}
