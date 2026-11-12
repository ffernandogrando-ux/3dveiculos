"""E_perde_ar — "Só que o pneu perde ar sozinho, um pouquinho todo mês, mesmo sem furo..."

Pneu em corte no estúdio técnico. Bolinhas de ar (ciano) atravessam devagar a borracha do flanco e o talão
e saem; a cada "mês" (3 degraus) a pressão cai um pouco e o pneu baixa / a pegada alarga.
HUD: contador "1 MÊS / 2 MESES / 3 MESES" com barra de 3 segmentos, callouts do caminho do ar.
Tempos em frações de P["dur"] (só os tempos do .srt mudam).
"""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tec as T
C, tc = T.C, T.tc
import bpy
import numpy as np
from mathutils import Vector

P = C.plano("E_perde_ar")
D = P["dur"]
sc = T.setup(P)

borr = tc.mat_borracha_viva("borr_E")
pn = tc.pneu_animado("pneu", (1.0, 0.55), loc=(0, 0, 0), yaw=-26, seg_ang=300, cor_pegada=tc.CIANO,
                     mat_borracha_pneu=borr)
# sincronia com a narração (tempos locais, lidos de palavras.json)
t_perde = T.palavra(P, "perde ar", padrao=0.10)
t_mes = T.palavra(P, "todo mês", padrao=0.35)
t_furo = T.palavra(P, "sem furo", padrao=0.52)
t_olho = T.palavra(P, "a olho nu", padrao=0.64)
t_baixo = T.palavra(P, "bem baixo", padrao=0.90)
# degraus de pressão: (tempo, estado) — cada "mês" um pouco; em "bem baixo" chega ao fim
MESES = [t_mes + 0.15, t_furo + 0.1, t_olho + 0.1]
DEGRAUS = [(MESES[0], 0.25), (MESES[1], 0.50), (MESES[2], 0.70), (t_baixo + 0.1, 1.0)]
tc.pneu_estado(pn, 0.0, C.F(0))
ant = 0.0
for tt, f in DEGRAUS:
    tc.pneu_estado(pn, ant, C.F(tt))
    tc.pneu_estado(pn, f, C.F(min(D, tt + 0.45)))
    ant = f

# ---------------- bolinhas de ar: da cavidade, atravessando flanco/talão, para fora (no plano do corte)
pf = pn["perfil"]
a0, r0, thk, Nn, n = pf["a0"], pf["r0"], pf["thk"], pf["Nn"], pf["n"]
dfm = pf["deforma"]
mat_b = tc.mat_emissivo("#7FE6FF", 3.0, "bolha", alpha=0.9)
random.seed(4)
bolhas = []
tn = (r0 - pf["rb"]) / (pf["R"] - pf["rb"])
cands = [i for i in range(n) if 0.25 < tn[i] < 0.75] + [3, 4, n - 4, n - 5] * 3
for j in range(14):
    i = random.choice(cands)
    t_ang = 0.0 if j % 3 else math.pi                     # 2/3 na seção de baixo, 1/3 em cima
    da, dr = dfm(np.array([a0[i]]), np.array([r0[i]]), np.array([t_ang]))
    def pt(prof):
        a = a0[i] - Nn[i, 0] * prof + da[0]
        r = r0[i] - Nn[i, 1] * prof + dr[0]
        return Vector((a, -0.004, -r if t_ang == 0 else r))
    ini, fim = pt(thk[i] + 0.012), pt(-0.035)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
    b = bpy.context.active_object
    b.name = f"bolha{j}"
    b.data.materials.append(mat_b)
    b.data.shade_smooth()
    b.parent = pn["pai"]
    b.visible_shadow = False
    bolhas.append((b, ini, fim, random.uniform(0, 3.0), random.uniform(2.4, 3.4), random.uniform(0.0065, 0.009)))


@T.a_cada_quadro
def mover_bolhas(t):
    liga = T.suave(t, t_perde, t_perde + 0.4)
    for b, ini, fim, fase, per, r in bolhas:
        u = ((t + fase) % per) / per
        p = ini.lerp(fim, u)
        p.x += 0.002 * math.sin(9 * u + fase)
        b.location = p
        s = r * liga * math.sin(math.pi * u) ** 0.6
        b.scale = (s, s, s)


# ---------------- câmera: push-in leve
alvo = (0.0, 0.0, 0.30)
cam = T.camera((0, -4.1, 1.3), alvo, lente=70)
tc.orbita(cam, alvo, 3.35, -4, 1.15)
cam.keyframe_insert("location", frame=C.F(0)); cam.keyframe_insert("rotation_euler", frame=C.F(0))
tc.orbita(cam, alvo, 3.15, 2, 1.10)
cam.keyframe_insert("location", frame=C.F(D)); cam.keyframe_insert("rotation_euler", frame=C.F(D))
T.linear([cam])


@T.hud
def desenhar(h, t):
    k = h.k
    h.cantos()
    mes = sum(1 for m in MESES if t >= m)
    if mes:
        txt = "1 MÊS" if mes == 1 else f"{mes} MESES"
        pop = T.suave(t, MESES[mes - 1], MESES[mes - 1] + 0.15)
        h.tag((540, 250), txt, tc.CIANO, 46 * (0.85 + 0.15 * pop), alpha=pop)
    for i in range(3):
        x0 = 390 + i * 104
        cheio = T.suave(t, MESES[i], MESES[i] + 0.45)
        h.d.rectangle([x0 * k, 300 * k, (x0 + 92) * k, 308 * k], fill=T.rgb("#2E3642") + (255,))
        if cheio > 0:
            h.d.rectangle([x0 * k, 300 * k, (x0 + 92 * cheio) * k, 308 * k], fill=T.rgb(tc.CIANO) + (255,))
    h.texto((540 * k, 350 * k), "SEM FURO NENHUM", 24, "#9AA6B4", "ms", espaco=0.16, arq=T.FONTE_MED,
            alpha=255 * T.suave(t, t_furo, t_furo + 0.25))
    # "a olho nu / bem baixo": aviso vermelho embaixo
    h.tag((540, 1700), "JÁ ESTÁ BAIXO", tc.VERMELHO, 40, alpha=T.suave(t, t_baixo, t_baixo + 0.2))
    # callouts: o caminho do ar
    mw = pn["pai"].matrix_world
    i_fl = int(np.argmin(np.abs(tn[n // 2:] - 0.5))) + n // 2
    da, dr = dfm(np.array([a0[i_fl]]), np.array([r0[i_fl]]), np.array([0.0]))
    p_fl = mw @ Vector((a0[i_fl] + da[0], -0.004, -(r0[i_fl] + dr[0])))
    da, dr = dfm(np.array([a0[4]]), np.array([r0[4]]), np.array([0.0]))
    p_tl = mw @ Vector((a0[4] + da[0], -0.004, -(r0[4] + dr[0])))
    h.callout(p_fl, (700, 1450), "PELA BORRACHA", None, tc.CIANO, lado=1, tam=30,
              crescer=T.suave(t, t_perde + 0.3, t_perde + 0.8))
    h.callout(p_tl, (330, 1560), "PELO TALÃO", None, tc.CIANO, lado=-1, tam=30,
              crescer=T.suave(t, t_perde + 0.7, t_perde + 1.2))


C.renderizar(P, sys.argv)
