"""G_esquenta — "E tem mais. Amassado desse jeito, ele esquenta e arrasta. O motor faz mais força e o carro
bebe mais."

Pneu murcho em corte, visto de 3/4 pelo lado de fora (flanco). Em "esquenta" o flanco que dobra perto do chão
passa de vermelho-escuro a laranja/amarelo (degradê animado, pulsando de leve); em "arrasta" uma seta
vermelha de resistência aparece na pegada; em "motor faz mais força" entra o mostrador de combustível (HUD)
e em "bebe mais" o ponteiro desce para a reserva. Tempos de palavras.json.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tec as T
C, tc = T.C, T.tc
import bpy
import numpy as np
from mathutils import Vector

P = C.plano("G_esquenta")
D = P["dur"]
sc = T.setup(P, alvo=(0, 0, 0.25))

t_esq = T.palavra(P, "esquenta", padrao=0.36)
t_arr = T.palavra(P, "arrasta", padrao=0.48)
t_mot = T.palavra(P, "motor faz mais força", padrao=0.59)
t_bebe = T.palavra(P, "bebe mais", padrao=0.87)

borr = tc.mat_borracha_viva("borr_G")
pn = tc.pneu_corte("pneu", loc=(0, 0, 0), yaw=-48, pressao=0.45, seg_ang=300, mat_borracha_pneu=borr,
                   cor_pegada=tc.VERMELHO)
cal = tc.no_valor(borr, "calor")
T.key_no(cal, 0, 0.0)
T.key_no(cal, t_esq, 0.0)
T.key_no(cal, t_esq + 0.9, 0.85)
# pulsação leve depois de quente
tt = t_esq + 0.9
while tt < D:
    T.key_no(cal, tt + 0.35, 1.0)
    T.key_no(cal, tt + 0.7, 0.85)
    tt += 0.7

alvo0, alvo1 = (0.0, 0.0, 0.22), (0.0, 0.0, 0.18)
cam = T.camera((0.6, -2.4, 0.6), alvo0, lente=75)
T.cam_key(cam, 0, (0.85, -2.85, 0.62), alvo0)
T.cam_key(cam, D, (0.72, -2.55, 0.52), alvo1)
T.linear([cam])

pf = pn["perfil"]
i_fl = T.i_perfil(pn, tn_alvo=0.45, lado=1)
K = 300
a0, r0, dfm = pf["a0"], pf["r0"], pf["deforma"]
mw = pn["pai"].matrix_world


def ponto_flanco(theta):
    da, dr = dfm(np.array([a0[i_fl]]), np.array([r0[i_fl]]), np.array([theta]))
    a, r = a0[i_fl] + da[0], r0[i_fl] + dr[0]
    return mw @ Vector((a + 0.004, r * math.sin(theta), -r * math.cos(theta)))


def gauge(h, cx, cy, R, frac, alpha):
    """Mostrador de combustível simples: arco E..F, marcas, ponteiro em 'frac' (0 = E, 1 = F)."""
    k = h.k
    cx, cy, R = cx * k, cy * k, R * k
    A = int(255 * alpha)
    a0_, a1_ = 200, 340                                   # graus (PIL: 0 = direita, horário)
    h.d.arc([cx - R, cy - R, cx + R, cy + R], a0_, a1_, fill=T.rgb("#3A4452") + (A,), width=max(1, int(10 * k)))
    h.d.arc([cx - R, cy - R, cx + R, cy + R], a0_, a0_ + 22, fill=T.rgb(tc.VERMELHO) + (A,), width=max(1, int(10 * k)))
    for i in range(5):
        ang = math.radians(a0_ + (a1_ - a0_) * i / 4)
        p1 = (cx + (R - 26 * k) * math.cos(ang), cy + (R - 26 * k) * math.sin(ang))
        p2 = (cx + (R - 8 * k) * math.cos(ang), cy + (R - 8 * k) * math.sin(ang))
        h.d.line([p1, p2], fill=T.rgb("#C9D2DC") + (A,), width=max(1, int(3 * k)))
    h.texto((cx - R * 0.82, cy + 4 * k), "E", 30, tc.VERMELHO, "ms", alpha=A)
    h.texto((cx + R * 0.82, cy + 4 * k), "F", 30, "#C9D2DC", "ms", alpha=A)
    ang = math.radians(a0_ + (a1_ - a0_) * frac)
    tip = (cx + (R - 30 * k) * math.cos(ang), cy + (R - 30 * k) * math.sin(ang))
    h.d.line([(cx, cy), tip], fill=T.rgb(tc.LARANJA) + (A,), width=max(1, int(6 * k)))
    r = 12 * k
    h.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=T.rgb("#DDE3EA") + (A,))
    h.texto((cx, cy + 60 * k), "COMBUSTÍVEL", 22, "#9AA6B4", "ms", espaco=0.16, arq=T.FONTE_MED, alpha=A)


@T.hud
def desenhar(h, t):
    k = h.k
    h.cantos()
    quente = T.suave(t, t_esq, t_esq + 0.5)
    h.tag((540, 250), "ESQUENTA", tc.LARANJA, 44, alpha=quente)
    h.callout(ponto_flanco(0.25), (1010, 1150), "FLANCO DOBRA", "E AQUECE", tc.LARANJA, lado=-1, tam=32,
              crescer=T.suave(t, t_esq + 0.2, t_esq + 0.7))
    # arrasta: seta de resistência na pegada (aponta para trás, contra o movimento)
    ar = T.suave(t, t_arr, t_arr + 0.35)
    if ar > 0:
        p0 = h.px(mw @ Vector((0.0, -0.18, -pn["h0"] + 0.01)))
        p1 = h.px(mw @ Vector((0.0, 0.10, -pn["h0"] + 0.01)))
        p1 = (p0[0] + (p1[0] - p0[0]) * ar, p0[1] + (p1[1] - p0[1]) * ar)
        T.seta(h, p0, p1, tc.VERMELHO, esp=7, cab=30, alpha=255 * ar)
        h.texto((p0[0] - 20 * k, p0[1] + 60 * k), "ARRASTA", 34, tc.VERMELHO, "rs", alpha=255 * ar)
    # motor faz mais força -> mostrador; bebe mais -> ponteiro na reserva
    g = T.suave(t, t_mot, t_mot + 0.4)
    frac = 0.72 - 0.52 * T.suave(t, t_mot + 0.3, t_bebe + 0.4)
    gauge(h, 760, 1560, 150, frac, g)
    h.texto((760 * k, 1740 * k), "BEBE MAIS", 40, tc.VERMELHO, "ms", alpha=255 * T.suave(t, t_bebe, t_bebe + 0.25))


C.renderizar(P, sys.argv)
