"""Cenário do vídeo do ralo com cheiro de esgoto: banheiro térreo em corte + encanamento até a rede da rua.

Uso:  python cenario.py   ->  cenario.blend (prévia: um enquadramento por segundo, t = 0..5, para render.py stills)
A cena do vídeo (cena.py, feita quando chegar o .srt) importa materiais() e montar() daqui e anima a história.

Corte em y = 0 (câmera em y negativo). Canos de PVC cortados ao meio em y = YC, piso e lajes começam em y = 0,003.
Antes do "raio-x" a frente fica fechada pela PELE (piso + solo de y = -0,25 a 0) e o vaso e a grelha aparecem
inteiros; no raio-x a pele cai e entram as versões cortadas.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "motor3d"))
import bpy, bmesh
from mathutils import Vector
import shapely.geometry as sg
from shapely.ops import unary_union
import motor as mt
import pecas_esgoto as pc  # peças de banheiro/esgoto do ralo (veja o módulo)
from motor import (mat, lin, box, cyl, tube, ball, empty, prism, polys, pop_in, pop_out, hide_until, hide_from, jump, k,
                   glow, terrain, decor, far_ground, Sky, cameras, save, LAYERS)

HERE = os.path.dirname(os.path.abspath(__file__))

FL, H = 0.30, 2.9                 # piso acabado e forro
X0, X1, WE = 0.0, 3.0, 0.15       # faces internas das paredes laterais e espessura
YB = 2.5                          # face interna da parede do fundo
YP = 0.003                        # frente do piso/lajes (atrás do corte dos canos)
YC = -0.015                       # plano de corte dos canos
RALO_X, VASO_X, RESP_X = 0.55, 2.67, 2.88
CX0, CX1, CX_FUNDO = 3.9, 4.55, -0.62          # caixa de inspeção
REDE = (7.8, -1.45, 0.36)                      # rede de esgoto da rua (x, z, raio)
R_RAMAL, R_COL, R_RESP, ESP = 0.065, 0.085, 0.055, 0.012
CASA = [("soft", -2.5, 0.10), ("mid", -5.0, -2.5), ("firm", -7.5, -5.0), ("aquifer", -10.5, -7.5),
        ("rock", -13.0, -10.5), ("base", -60.0, -13.0)]
RUA = [("gravel", -0.3, -0.05), ("soft", -2.5, -0.3), ("mid", -5.0, -2.5), ("firm", -7.5, -5.0),
       ("aquifer", -10.5, -7.5), ("rock", -13.0, -10.5), ("base", -60.0, -13.0)]


def materiais():
    M = {n: mat(n, c, **kw) for n, c, kw in [
        ("grass", "#6cc24a", {}), ("soft", "#c8945c", {}), ("mid", "#a87447", {}), ("firm", "#8a5d3b", {}),
        ("aquifer", "#86b4d8", {}), ("rock", "#6e6c75", {}), ("base", "#9b9ba0", {}),
        ("fence", "#ffffff", {}), ("trunk", "#7a5230", {}), ("leaf", "#3f9b46", {}), ("cloud", "#ffffff", {}),
        ("rint", "#e2d6bf", {}), ("paint_b", "#f5f3ee", {}), ("ceiling", "#fbf8f1", {}), ("contrapiso", "#b9b6ad", {}),
        ("lastro", "#9a9a9e", {}), ("fundacao", "#8c8e93", {}), ("gravel", "#8d8a84", {}), ("asphalt", "#3d3f45", {}),
        ("sidewalk", "#cfccc5", {}), ("roof_t", "#c9483a", {}), ("attic", "#c9b08a", {}), ("frame_w", "#f4f2ec", {}),
        ("reveal", "#f3ead8", {"emit": 0.3}), ("win_glass", "#bfe3f5", {"alpha": 0.35, "rough": 0.1}),
        ("rug_b", "#f2b544", {}), ("lamp", "#fff2c8", {"emit": 3.0}), ("stream", "#b57be0", {"emit": 0.4}),
        ("shirt_y", "#f6c343", {"rough": 0.7}), ("haze_low", "#9cc25a", {"alpha": 0.2, "emit": 0.15}),
    ]}
    pc.materiais_banheiro(M)
    pc.materiais_personagem(M)
    M["tile_b"] = pc.ladrilho_mat("tile_b", "#9ad9cf", "#90d3c8", "#ffffff", escala=5.0)
    M["tile_faixa"] = pc.ladrilho_mat("tile_faixa", "#2f9e90", "#2b9487", "#ffffff", escala=5.0)
    M["floor_b"] = pc.ladrilho_mat("floor_b", "#e6e9ec", "#cfd5da", "#b4bcc3", escala=3.0, piso=True, alt=0.5, larg=0.5)
    return M


def tampao(name, poly, furo, y0, m, fundo=0.1, exceto=()):
    """Tampa o rasgo de um furo num bloco (some quando o cano daquele furo aparece). `exceto`: furos de outros canos
    que continuam abertos."""
    g = (poly if hasattr(poly, "exterior") else sg.Polygon(poly)).intersection(furo)
    if exceto:
        g = g.difference(unary_union(list(exceto)))
    return [prism(f"{name}{i}", p, y0, y0 + fundo, m) for i, p in enumerate(polys(g))]


def montar(M):
    S = {}
    # ================================================================ canos (caminhos no plano x-z)
    sif = pc.caminho_sifao(RALO_X, FL - 0.012, -0.24, largura=0.25, z_saida=0.0)
    ramal, ramal_cam = pc.cano_corte("ramal_ralo", M, sif + [(1.05, 0.0), (1.05, -0.33)], r=R_RAMAL, esp=ESP, y=YC)
    col_pts = [(1.05, -0.2), (1.05, -0.46), (3.4, -0.495), (CX0 + 0.065, -0.505)]
    ab_vaso = (VASO_X - 0.09, -1.0, VASO_X + 0.09, 0.0, 1)
    ab_resp = (RESP_X - 0.06, -1.0, RESP_X + 0.06, 0.0, 1)
    # cada cano num plano de corte um pouco diferente: bordas sobrepostas no mesmo plano saem pretas no Cycles
    col_a, col_cam = pc.cano_corte("coletor", M, col_pts, r=R_COL, esp=ESP, y=YC - 0.002, aberturas=[ab_vaso])
    col_b, _ = pc.cano_corte("coletor_ventilado", M, col_pts, r=R_COL, esp=ESP, y=YC - 0.002, aberturas=[ab_vaso, ab_resp])
    col_b.scale = (0, 0, 0)                      # entra no lugar do coletor quando o respiro é instalado
    queda, queda_cam = pc.cano_corte("queda_vaso", M, [(VASO_X, FL - 0.004), (VASO_X, -0.475)], r=R_COL, esp=ESP,
                                     y=YC - 0.001, pontas=(True, False))
    resp, resp_cam = pc.cano_corte("respiro", M, [(RESP_X, -0.475), (RESP_X, 0.13), (3.075, 0.24), (3.075, 3.58)],
                                   r=R_RESP, esp=ESP, y=YC - 0.003, pontas=(False, True))
    pred, pred_cam = pc.cano_corte("ramal_predial", M, [(CX1 - 0.065, -0.55), (6.9, -0.8), (7.45, -1.22)], r=R_COL,
                                   esp=ESP, y=YC - 0.002)
    term = pc.terminal_ventilacao("respiro_ponta", M, r=R_RESP)
    term.location = (3.075, -0.005, 3.58)
    S.update(ramal=ramal, ramal_cam=ramal_cam, coletor=col_a, coletor_b=col_b, col_cam=col_cam, queda=queda,
             queda_cam=queda_cam, respiro=resp, resp_cam=resp_cam, respiro_ponta=term, predial=pred, pred_cam=pred_cam)

    f_ramal, f_col = pc.furo_cano(ramal_cam, R_RAMAL), pc.furo_cano(col_cam, R_COL)
    f_queda, f_resp = pc.furo_cano(queda_cam, R_COL), pc.furo_cano(resp_cam, R_RESP)
    f_pred = pc.furo_cano(pred_cam, R_COL)
    canos = [f_ramal, f_col, f_queda, f_resp, f_pred]

    # água parada no sifão do ralo (fecho hídrico): nível da soleira da saída
    ri = R_RAMAL - ESP
    i_fim = next(i for i, (x, z) in enumerate(ramal_cam) if x > RALO_X + 0.25 + 1e-4)
    z_fecho = 0.0 - ri - 0.002
    agua = pc.agua_cano("agua_sifao", M, ramal_cam, ri, z_fecho, y=YC, ate=i_fim)
    S["agua_sifao"], S["z_fecho"] = agua, z_fecho
    S["nivel_sifao"] = pc.nivel_agua(agua, z_fecho + 0.001)
    S["z_fundo_sifao"] = -0.24 - ri
    S["i_sifao"] = i_fim                          # índice do caminho onde termina o sifão (início do braço)

    # ================================================================ terreno em corte
    fund_e = sg.box(-WE, -0.45, X0, 0.10)
    fund_d = sg.box(X1, -0.45, X1 + WE, 0.10)
    caixa_r = sg.box(CX0, CX_FUNDO - 0.06, CX1, 0.0)
    rede_c = sg.Point(REDE[0], REDE[1]).buffer(REDE[2] + 0.005, 48)
    terrain("solo_casa", -WE, X1 + WE, [(0, 0.1, canos + [fund_e, fund_d]), (0.1, YB + WE, [fund_e, fund_d])], M, layers=CASA)
    terrain("solo_casa_fundo", -WE, X1 + WE, [(YB + WE, 16, [])], M)
    terrain("solo_esq", -10, -WE, [(0, 16, [])], M)
    terrain("solo_quintal", X1 + WE, 5.6, [(0, 0.1, canos + [caixa_r]), (0.1, 0.4, [caixa_r]), (0.4, 16, [])], M)
    terrain("solo_rua", 5.6, 16, [(0, 0.1, canos + [rede_c]), (0.1, 16, [rede_c])], M, layers=RUA)
    far_ground(M, y0=16)
    decor(M, fence=(-10, 5.2, 12.0), trees=[(-2.0, 4.0), (-4.2, 8.0), (-1.2, 9.5), (4.6, 5.0), (4.3, 9.0), (10.5, 10.0)],
          clouds=[(-12, 60, 22), (6, 70, 26), (22, 65, 20)])
    box("calcada", 5.6, 6.6, 0.0, 16, -0.05, 0.12, M["sidewalk"])
    box("meio_fio", 6.6, 6.68, 0.0, 16, -0.05, 0.13, M["concrete_p"])
    box("asfalto", 6.68, 16, 0.0, 16, -0.05, 0.03, M["asphalt"])
    for i in range(4):                            # faixa tracejada no meio da rua
        box(f"faixa_rua{i}", 11.0, 11.12, 1.0 + i * 3.5, 2.8 + i * 3.5, 0.03, 0.035, M["paint_b"])

    # fundações e piso (camadas visíveis no corte, furadas onde passam os canos)
    for nm, poly in (("fund_e", fund_e), ("fund_d", fund_d)):
        pc.bloco_corte(nm, poly, 0.0, YB + WE, M["fundacao"], furos=canos)
    outros = [f_ramal, f_col, f_queda, f_pred]
    S["tampas_resp"] = tampao("tampa_resp_fund", fund_d, f_resp, 0.0, M["fundacao"], exceto=outros)
    piso = [("piso", FL - 0.015, FL, "floor_b"), ("contrapiso", 0.18, FL - 0.015, "contrapiso"), ("lastro", 0.10, 0.18, "lastro")]
    for nm, z0, z1, mm in piso:
        poly = sg.box(X0, z0, X1, z1)
        pc.bloco_corte(nm, poly, YP, YB, M[mm], furos=canos)
        S["tampas_resp"] += tampao(f"tampa_resp_{nm}", poly, f_resp, YP, M[mm], exceto=outros)
    S["tampas_resp"] += tampao("tampa_resp_solo", sg.box(X0, -0.45, X1, 0.10), f_resp, 0.0, M["soft"], exceto=outros)

    # ================================================================ paredes, forro, telhado
    box("parede_e", -WE, X0, 0.0, YB + WE, 0.10, H, M["rint"])
    parede_d = sg.box(X1, 0.10, X1 + WE, H)
    pc.bloco_corte("parede_d", parede_d, 0.0, YB + WE, M["rint"], furos=[f_resp])
    S["tampas_resp"] += tampao("tampa_resp_parede", parede_d, f_resp, 0.0, M["rint"])
    WIN = (1.62, 2.28, 2.12, 2.58)                       # janela basculante no fundo: x0, x1, z0, z1
    janela = sg.box(WIN[0], WIN[2], WIN[1], WIN[3])
    for nm, (a, b, c, d) in (("i", (-WE, X1 + WE, 0.10, WIN[2])), ("s", (-WE, X1 + WE, WIN[3], H)),
                             ("e", (-WE, WIN[0], WIN[2], WIN[3])), ("d", (WIN[1], X1 + WE, WIN[2], WIN[3]))):
        box("parede_fundo_" + nm, a, b, YB, YB + WE, c, d, M["rint"])
    for nm, a in (("vi", (WIN[0], WIN[1], WIN[2], WIN[2] + 0.01)), ("vs", (WIN[0], WIN[1], WIN[3] - 0.01, WIN[3])),
                  ("ve", (WIN[0], WIN[0] + 0.01, WIN[2], WIN[3])), ("vd", (WIN[1] - 0.01, WIN[1], WIN[2], WIN[3]))):
        box("vao_" + nm, a[0], a[1], YB, YB + WE, a[2], a[3], M["reveal"])
    for nm, a in (("i", (WIN[0] - 0.04, WIN[1] + 0.04, WIN[2] - 0.04, WIN[2])),
                  ("s", (WIN[0] - 0.04, WIN[1] + 0.04, WIN[3], WIN[3] + 0.04)),
                  ("e", (WIN[0] - 0.04, WIN[0], WIN[2], WIN[3])), ("d", (WIN[1], WIN[1] + 0.04, WIN[2], WIN[3]))):
        box("jan_" + nm, a[0], a[1], YB - 0.02, YB + 0.02, a[2], a[3], M["frame_w"])
    for j in range(3):                                    # basculante: três lâminas de vidro inclinadas
        z = WIN[2] + 0.08 + j * 0.15
        l = box(f"jan_lamina{j}", WIN[0] + 0.01, WIN[1] - 0.01, -0.006, 0.006, -0.06, 0.06, M["win_glass"], anchor="center")
        l.location = (l.location.x, YB + 0.07, z)
        l.rotation_euler = (math.radians(35), 0, 0)
    # revestimento: azulejo até 1,5 m (com faixa), pintura acima
    ZT = FL + 1.5
    box("azul_e", X0, X0 + 0.012, 0.0, YB, FL, ZT, M["tile_b"])
    box("azul_d", X1 - 0.012, X1, 0.0, YB, FL, ZT, M["tile_b"])
    box("azul_f", X0, X1, YB - 0.012, YB, FL, ZT, M["tile_b"])
    for nm, a in (("e", (X0, X0 + 0.016, 0.0, YB)), ("d", (X1 - 0.016, X1, 0.0, YB)), ("f", (X0, X1, YB - 0.016, YB))):
        box("faixa_" + nm, a[0], a[1], a[2], a[3], ZT - 0.1, ZT, M["tile_faixa"])
    box("pint_e", X0, X0 + 0.006, 0.0, YB, ZT, H, M["paint_b"])
    box("pint_d", X1 - 0.006, X1, 0.0, YB, ZT, H, M["paint_b"])
    for nm, (a, b, c, d) in (("i", (X0, X1, ZT, WIN[2])), ("s", (X0, X1, WIN[3], H)), ("e", (X0, WIN[0], WIN[2], WIN[3])),
                             ("d", (WIN[1], X1, WIN[2], WIN[3]))):
        box("pint_f_" + nm, a, b, YB - 0.006, YB, c, d, M["paint_b"])
    forro = sg.box(-WE, H, X1 + WE, H + 0.1)
    pc.bloco_corte("forro", forro, 0.0, YB + WE, M["ceiling"], furos=[f_resp])
    S["tampas_resp"] += tampao("tampa_resp_forro", forro, f_resp, 0.0, M["ceiling"])
    prism("oitao", [(-WE, H + 0.1), (X1 + WE, H + 0.1), (1.5, 4.0)], YB, YB + WE, M["attic"])
    agua_e = [(-0.5, 2.95), (1.5, 4.05), (1.5, 4.2), (-0.5, 3.1)]
    agua_d = [(3.5, 2.95), (3.5, 3.1), (1.5, 4.2), (1.5, 4.05)]
    prism("telhado_e", agua_e, -0.1, YB + WE + 0.3, M["roof_t"])
    td = sg.Polygon(agua_d)
    pc.bloco_corte("telhado_d", td, -0.1, YB + WE + 0.3, M["roof_t"], furos=[f_resp], y_furo=0.2)
    S["tampas_resp"] += tampao("tampa_resp_telhado", td, f_resp, -0.1, M["roof_t"], fundo=0.2)

    # ================================================================ louças e objetos do banheiro
    vaso = pc.vaso_sanitario("vaso", M)
    vaso["raiz"].location = (VASO_X, 0, FL)
    vaso_c = pc.vaso_sanitario("vaso_corte", M, corte=True)
    vaso_c["raiz"].location = (VASO_X, 0, -100)          # guardado longe (tem água com nível booleano: não use escala 0)
    S["vaso"], S["vaso_corte"] = vaso, vaso_c
    S["nivel_bacia"] = pc.nivel_agua(vaso_c["agua_bacia"], FL + vaso_c["z_agua"] + 0.001)
    S["nivel_caixa"] = pc.nivel_agua(vaso_c["agua_caixa"], FL + 0.746)
    gr = pc.ralo_grelha("grelha", M)
    gr.location = (RALO_X, 0, FL + 0.002)
    gr_c = pc.ralo_grelha("grelha_corte", M)
    gr_c.location = (RALO_X, 0, FL + 0.002)
    pc.cortar_y(gr_c, 0.0, 1)
    gr_c.scale = (0, 0, 0)
    S["grelha"], S["grelha_corte"] = gr, gr_c

    ch = pc.chuveiro("chuveiro", M)
    ch.location = (RALO_X, YB - 0.012, FL + 2.0)
    bx = pc.box_vidro("box", M, comprimento=1.35, altura=1.95)
    bx.location = (1.15, 0.0, FL)
    pia = pc.pia_banheiro("pia", M, largura=0.72)
    pia.location = (1.98, YB - 0.012, FL)
    esp = pc.espelho("espelho", M, largura=0.55, altura=0.62)
    esp.location = (1.98, YB - 0.012, FL + 1.5)
    tl = pc.toalha("toalha", M, largura=0.3, altura=0.55)
    tl.location = (1.36, YB - 0.012, FL + 1.38)
    pl = pc.vaso_planta("planta_pia", M, altura=0.28, folhas=7, seed=4)
    pl.location = (2.24, YB - 0.2, FL + 0.84)
    ball("tapete", 1, (1.75, 0.75, FL + 0.004), M["rug_b"], sub=2, scale=(0.42, 0.28, 0.004))
    cyl("plafon", 0.2, H - 0.03, H, (1.5, 1.2), M["lamp"], seg=32)

    # ================================================================ fora de casa: caixa de inspeção e rede da rua
    cx_root, cx_esg = pc.caixa_inspecao("caixa_insp", M, CX0, CX1, CX_FUNDO, y=-0.005, furos=[f_col, f_pred])
    rede, rede_esg = pc.rede_esgoto("rede", M, REDE[0], REDE[1], r=REDE[2], furos=[f_pred])
    S.update(caixa=cx_root, caixa_esgoto=cx_esg, rede=rede, rede_esgoto=rede_esg)

    # ================================================================ pele da frente (some no raio-x)
    pele = empty("pele")
    pele_parts = []
    for nm, z0, z1, mm in piso:
        pele_parts.append(box("pele_" + nm, X0, X1, -0.25, YP, z0, z1, M[mm]))
    for nm, x0, x1 in (("fe", -WE, X0), ("fd", X1, X1 + WE)):
        pele_parts.append(box("pele_" + nm, x0, x1, -0.25, YP, -0.45, FL, M["fundacao"]))
    solo = terrain("pele_solo", -WE, X1 + WE, [(-0.25, YP, [fund_e, fund_d])], M, layers=CASA)
    pele_parts += list(solo.values())
    for o in pele_parts:
        o.parent = pele
    S["pele"] = pele

    # ================================================================ morador
    mor = pc.personagem("morador", M, camisa="shirt_y", altura=1.12)
    S["morador"] = mor
    fr = pc.frasco("frasco", M)
    fr.parent = mor["mao_d"]
    fr.location = (0.0, -0.02, -0.06)
    fr.rotation_euler = (math.radians(-70), 0, 0)
    S["frasco"] = fr

    # ================================================================ céu e luzes
    sky = Sky(top="#8fc3ef", horizon="#fde6c8", sun_energy=2.4)
    sky.sun_d.angle = math.radians(14)
    S["sky"] = sky
    S["luzes"] = {}
    for nome, loc, rot, e, s_, cor in (("luz_frente", (1.8, -4.8, 2.6), (72, 0, 0), 170, 7.0, "#fff1dc"),
                                       ("luz_baixa", (3.0, -4.0, -0.8), (90, 0, 0), 70, 7.0, "#ffffff"),
                                       ("luz_teto", (1.5, 1.2, H - 0.06), (0, 0, 0), 45, 2.4, "#fff4e0")):
        d = bpy.data.lights.new(nome, "AREA"); d.energy = e; d.size = s_; d.color = lin(cor)[:3]
        o = mt.link(bpy.data.objects.new(nome, d)); o.location = loc
        o.rotation_euler = tuple(math.radians(a) for a in rot)
        S["luzes"][nome] = d
    return S


def luzes(S, t, fator):
    """Muda a força das luzes de área no tempo t (fator 1 = dia; ~0,35 = noite com a luz do banheiro)."""
    base = {"luz_frente": 170, "luz_baixa": 70, "luz_teto": 45}
    for nome, d in S["luzes"].items():
        d.energy = base[nome] * (fator if nome != "luz_teto" else max(fator, 0.8))
        d.keyframe_insert("energy", frame=mt.F(t))


# ==================================================================== prévia (6 quadros de teste)
def bolhas_fixas(nome, M, cam, fracs, r=0.022, y=0.03):
    """Bolhas paradas ao longo de um caminho (frações do comprimento) — só para a prévia."""
    P = [Vector(p) for p in cam]
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)
    out = []
    for i, f in enumerate(fracs):
        s = f * L[-1]
        j = max(1, next((j for j in range(len(L)) if L[j] >= s), len(L) - 1))
        a, b = P[j - 1], P[j]
        u = 0 if L[j] == L[j - 1] else (s - L[j - 1]) / (L[j] - L[j - 1])
        p = a.lerp(b, u)
        out.append(pc.esfera(f"{nome}{i}", r * (0.8 + 0.5 * ((i * 7) % 4) / 3), (p.x, y, p.y), M["gas"], seg=12))
    return out


def previa(M, S):
    mor = S["morador"]
    R = mor["raiz"]
    R.location = (0.78, 0.5, FL)
    R.rotation_euler = (0, 0, math.radians(-28))
    despeja = (math.radians(-58), 0, math.radians(12))
    k(mor["braco_d"], "rotation_euler", 0.0, despeja)
    jump(mor["braco_d"], "rotation_euler", 0.5, despeja, (0, 0, 0))
    S["frasco"].rotation_euler = (math.radians(-140), 0, 0)
    jump(mor["braco_e"], "rotation_euler", 1.5, (0, 0, 0), (math.radians(-150), 0, math.radians(-30)))   # mão na cabeça
    pc.rosto_expr(mor, 1.5, olhos="fechados", boca="triste")
    jump(S["frasco"], "scale", 0.5, (1, 1, 1), (0, 0, 0))
    # jato de desinfetante (do bico até o ralo, em arco) e perfume (t = 0)
    mt.scene.frame_set(1)
    bpy.context.view_layer.update()
    bico = bpy.data.objects["frasco_tampa"].matrix_world @ Vector((0, 0, 0.03))
    alvo = Vector((RALO_X, 0.0, FL + 0.005))
    ctrl = Vector((bico.x + (alvo.x - bico.x) * 0.55, (bico.y + alvo.y) / 2, bico.z + 0.04))
    arco = [tuple((1 - u) ** 2 * bico + 2 * (1 - u) * u * ctrl + u * u * alvo) for u in [i / 12 for i in range(13)]]
    jato = pc._tubo_poli("jato", arco, 0.009, M["stream"])
    jump(jato, "scale", 0.5, (1, 1, 1), (0, 0, 0))
    perf = pc.nuvem("perfume", M, (RALO_X - 0.12, 0.2, FL + 0.45), raio=0.2, n=12, seed=9)
    jump(perf, "scale", 0.5, (1, 1, 1), (0, 0, 0))
    # raio-x: pele some, entram vaso e grelha cortados (t >= 1)
    jump(S["pele"], "scale", 0.5, (1, 1, 1), (0, 0, 0))
    jump(S["vaso"]["raiz"], "scale", 0.5, (1, 1, 1), (0, 0, 0))
    jump(S["vaso_corte"]["raiz"], "location", 0.5, (VASO_X, 0, -100), (VASO_X, 0, FL))
    jump(S["grelha"], "scale", 0.5, (1, 1, 1), (0, 0, 0))
    jump(S["grelha_corte"], "scale", 0.5, (0, 0, 0), (1, 1, 1))
    # sifão: cheio em t = 0..1 (gás preso embaixo da água), vazio em t >= 1,5
    nv = S["nivel_sifao"]
    jump(nv, "location", 1.5, (0, 0, S["z_fecho"] + 0.001), (0, 0, -1.0))
    i0 = S["i_sifao"]
    presas = bolhas_fixas("gas_preso", M, S["ramal_cam"][i0 - 3:], [0.05, 0.12, 0.3, 0.55, 0.8, 0.95])
    for b in presas:
        jump(b, "scale", 1.5, (1, 1, 1), (0, 0, 0))
    subindo = bolhas_fixas("gas_sobe", M, list(reversed(S["ramal_cam"])), [0.35, 0.5, 0.62, 0.72, 0.8, 0.88, 0.95, 0.99])
    for b in subindo:
        hide_until(b, 1.5)
    bolhas_fixas("gas_col", M, list(reversed(S["col_cam"])), [0.05, 0.25, 0.45, 0.6, 0.75, 0.9])
    bolhas_fixas("gas_pred", M, list(reversed(S["pred_cam"])), [0.1, 0.3, 0.5, 0.7, 0.9])
    for i in range(5):
        pc.esfera(f"gas_rede{i}", 0.03, (REDE[0] - 0.15 + i * 0.07, 0.02 + 0.05 * i, REDE[1] - 0.12 + 0.06 * (i % 3)),
                  M["gas"], seg=12)
    linhas = pc.fedor("fedor", M, (RALO_X, 0.06, FL + 0.03), n=3, altura=0.45)
    for o in linhas:
        jump(o, "scale", 1.5, (0, 0, 0), (1, 1, 1))
    for i, p in enumerate([(0.42, 0.25, 0.75), (0.7, 0.35, 0.95), (0.5, 0.5, 1.2), (0.85, 0.2, 1.35), (0.3, 0.4, 1.5)]):
        b = pc.esfera(f"gas_ar{i}", 0.035, (p[0], p[1], FL + p[2]), M["gas"], seg=12)
        hide_until(b, 1.5)
    # descarga (t = 4): caixa vazia, água descendo pelo cano do vaso
    jump(S["nivel_caixa"], "location", 3.5, (0, 0, FL + 0.746), (0, 0, FL + 0.55))
    for i in range(5):
        b = pc.esfera(f"descarga{i}", 0.03, (VASO_X + 0.01 * (i % 2), 0.03, FL - 0.1 - i * 0.12), M["water_c"], seg=12)
        hide_until(b, 3.5)
        hide_from(b, 4.5)
    # respiro aparece na prévia larga (t = 3) só para conferir o desenho
    for o in (S["respiro"], S["respiro_ponta"], S["coletor_b"]):
        jump(o, "scale", 2.5, (0, 0, 0), (1, 1, 1))
        jump(o, "scale", 3.5, (1, 1, 1), (0, 0, 0))
    jump(S["coletor"], "scale", 2.5, (1, 1, 1), (0, 0, 0))
    jump(S["coletor"], "scale", 3.5, (0, 0, 0), (1, 1, 1))
    for o in S["tampas_resp"]:
        jump(o, "scale", 2.5, (1, 1, 1), (0, 0, 0))
        jump(o, "scale", 3.5, (0, 0, 0), (1, 1, 1))
    # noite (t = 5): barata saindo pela grelha e frascos vazios
    S["sky"].day(4.4)
    S["sky"].state(4.6, 0.15, 0.18, "#1b2747", "#41507a")
    luzes(S, 4.4, 1.0)
    luzes(S, 4.6, 0.35)
    bar, pernas = pc.barata("barata", M, tam=0.17)
    bar.location = (RALO_X + 0.03, 0.07, FL + 0.004)
    bar.rotation_euler = (0, 0, math.radians(-35))
    hide_until(bar, 4.5)
    for i in range(4):
        f = pc.frasco(f"vazio{i}", M)
        f.location = (RALO_X + 0.2 + 0.11 * i, 0.32 + 0.05 * (i % 2), FL + 0.05)
        f.rotation_euler = (math.radians(90), 0, math.radians(20 + 35 * i))
        hide_until(f, 4.5)
    # câmeras: uma por segundo
    shots = [
        (0.0, [(0.0, (0.12, -2.05, 1.5), (0.62, 0.3, 0.86))]),
        (1.0, [(1.0, (0.72, -1.1, 0.05), (0.72, 0.3, -0.05))]),
        (2.0, [(2.0, (1.5, -6.3, 1.25), (1.5, 0.6, 0.95))]),
        (3.0, [(3.0, (5.8, -7.6, -0.1), (5.8, 0.5, -0.55))]),
        (4.0, [(4.0, (2.5, -1.8, 0.75), (2.62, 0.2, 0.42))]),
        (5.0, [(5.0, (0.95, -1.25, 0.95), (0.6, 0.15, 0.25))]),
    ]
    cameras(shots)


if __name__ == "__main__":
    mt.setup(6.0)
    M = materiais()
    S = montar(M)
    previa(M, S)
    save(os.path.join(HERE, "cenario.blend"))
