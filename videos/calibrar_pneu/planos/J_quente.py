"""J_quente — "Aí o pneu tá quente, e o ar quente estufa. O número parece certo, mas quando esfria, fica baixo."

Pneu em corte com as "moléculas" de ar na seção (bolinhas). Quente: laranja e agitadas; em "estufa" o pneu enche
(shape key para pressão alta). Em "número parece certo" entra o calibrador digital (HUD) com o número "certo".
Em "quando esfria" as moléculas ficam azuis e lentas, se juntam, o pneu baixa e o número cai.
Tempos de palavras.json.
"""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tec as T
C, tc = T.C, T.tc
import bpy
import numpy as np
from mathutils import Vector

P = C.plano("J_quente")
D = P["dur"]
sc = T.setup(P)

t_quente = T.palavra(P, "pneu tá quente", padrao=0.07)
t_estufa = T.palavra(P, "estufa", padrao=0.40)
t_num = T.palavra(P, "número parece certo", padrao=0.53)
t_esfria = T.palavra(P, "quando esfria", padrao=0.79)
t_baixo = T.palavra(P, "fica baixo", fim=True, padrao=0.99)
t_frio1 = min(D - 0.05, t_esfria + 0.9)

pn = tc.pneu_animado("pneu", (1.3, 0.6), loc=(0, 0, 0), yaw=-24, seg_ang=300, cor_pegada=None)
F0 = 0.45                                                # ~pressão normal antes de estufar
tc.pneu_estado(pn, F0, C.F(0))
tc.pneu_estado(pn, F0, C.F(t_estufa))
tc.pneu_estado(pn, 0.0, C.F(t_estufa + 0.6))
tc.pneu_estado(pn, 0.0, C.F(t_esfria))
tc.pneu_estado(pn, 1.0, C.F(t_frio1))

# ---------------- moléculas de ar na seção (de cima e de baixo)
pf = pn["perfil"]
a0, r0, thk, Nn, n, dfm = pf["a0"], pf["r0"], pf["thk"], pf["Nn"], pf["n"], pf["deforma"]
mol_mat = T.mat_mix_emissivo(tc.LARANJA, "#3D8BFF", 3.5, nome="molecula")
mv = tc.no_valor(mol_mat, "mix")
T.key_no(mv, t_esfria, 0.0)
T.key_no(mv, t_frio1, 1.0)


def poligono_ar(theta):
    da, dr = dfm(a0, r0, np.full(n, theta))
    a = a0 - Nn[:, 0] * (thk + 0.006) + da
    r = r0 - Nn[:, 1] * (thk + 0.006) + dr
    pts = np.c_[a, r]
    pts = np.vstack([pts, [[a0[-1] - 0.01, pf["rb"] + 0.03], [a0[0] + 0.01, pf["rb"] + 0.03]]])
    return pts


def dentro(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            c = not c
    return c


random.seed(7)
mols = []
for theta in (0.0, math.pi):
    poly = poligono_ar(theta)
    cen = poly.mean(axis=0)
    cont = 0
    while cont < 34:
        p = (random.uniform(poly[:, 0].min(), poly[:, 0].max()), random.uniform(poly[:, 1].min(), poly[:, 1].max()))
        if not dentro(p, poly):
            continue
        cont += 1
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.0062)
        m = bpy.context.active_object
        m.data.materials.append(mol_mat)
        m.data.shade_smooth()
        m.parent = pn["pai"]
        m.visible_shadow = False
        mols.append(dict(ob=m, a=p[0], r=p[1], theta=theta, ca=cen[0], cr=cen[1],
                         y=random.uniform(-0.03, -0.006),
                         f=[random.uniform(9, 15) for _ in range(3)], ph=[random.uniform(0, 6.28) for _ in range(3)]))


def fase(t):
    """Tempo 'efetivo' das moléculas: rápidas quando quentes, lentas quando frias (integral da velocidade)."""
    passos = max(1, int(t * 24))
    s = 0.0
    for i in range(passos):
        tt = t * (i + 0.5) / passos
        s += (1.0 - 0.75 * T.suave(tt, t_esfria, t_frio1)) * (t / passos)
    return s


@T.a_cada_quadro
def agitar(t):
    frio = T.suave(t, t_esfria, t_frio1)
    est = T.suave(t, t_estufa, t_estufa + 0.6) * (1 - frio)
    amp = 0.007 * (1 - 0.6 * frio)
    contr = 0.97 + 0.02 * est - 0.10 * frio                  # quente espalha, frio se junta
    te = fase(t)
    for m in mols:
        a = m["ca"] + (m["a"] - m["ca"]) * contr + amp * math.sin(m["f"][0] * te + m["ph"][0])
        r = m["cr"] + (m["r"] - m["cr"]) * contr + amp * math.sin(m["f"][1] * te + m["ph"][1])
        y = m["y"] + 0.4 * amp * math.sin(m["f"][2] * te + m["ph"][2])
        z = -r if m["theta"] == 0.0 else r
        m["ob"].location = (a, y, z)


alvo0, alvo1 = (0.0, 0.0, 0.32), (0.0, 0.0, 0.31)
cam = T.camera((0, -3.2, 1.1), alvo0, lente=70)
T.cam_key(cam, 0, (-0.5, -3.25, 1.1), alvo0)
T.cam_key(cam, D, (-0.2, -3.0, 1.0), alvo1)
T.linear([cam])


def mostrador(h, cx, cy, valor, cor, rotulo, alpha):
    """Calibrador digital (HUD): caixa com o número em PSI."""
    k = h.k
    A = int(255 * alpha)
    w, hh = 330 * k, 170 * k
    x0, y0 = cx * k - w / 2, cy * k - hh / 2
    h.d.rounded_rectangle([x0, y0, x0 + w, y0 + hh], radius=int(18 * k), fill=(14, 17, 21, int(0.85 * A)),
                          outline=T.rgb(cor) + (A,), width=max(1, int(4 * k)))
    h.texto((cx * k + 10 * k, cy * k + 34 * k), f"{valor:d}", 96, cor, "rs", espaco=0.02, arq=T.FONTE_BLACK, alpha=A)
    h.texto((cx * k + 24 * k, cy * k + 34 * k), "PSI", 30, "#9AA6B4", "ls", alpha=A)
    h.texto((cx * k, y0 + hh + 46 * k), rotulo, 28, cor, "ms", espaco=0.14, alpha=A)


@T.hud
def desenhar(h, t):
    h.cantos()
    q = T.suave(t, t_quente, t_quente + 0.3)
    frio = T.suave(t, t_esfria, t_frio1)
    if frio < 0.5:
        h.tag((540, 250), "AR QUENTE", tc.LARANJA, 44, alpha=q * (1 - 2 * frio))
    else:
        h.tag((540, 250), "AR FRIO", "#3D8BFF", 44, alpha=2 * frio - 1, cor_txt="#FFFFFF")
    h.texto((540 * h.k, 318 * h.k), "ESTUFA O PNEU", 28, "#DDE3EA", "ms", espaco=0.14,
            alpha=255 * T.suave(t, t_estufa, t_estufa + 0.25) * (1 - frio))
    # calibrador: "parece certo" -> cai quando esfria
    g = T.suave(t, t_num, t_num + 0.3)
    val = int(round(32 - 5 * T.suave(t, t_esfria + 0.1, t_frio1)))
    if frio < 0.5:
        mostrador(h, 540, 1560, val, tc.VERDE, "PARECE CERTO", g)
    else:
        mostrador(h, 540, 1560, val, tc.VERMELHO, "FRIO: BAIXOU", g)


C.renderizar(P, sys.argv)
