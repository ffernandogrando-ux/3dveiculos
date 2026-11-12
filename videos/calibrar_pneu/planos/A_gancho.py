"""Plano A (gancho): "Você conhece alguém que só calibra o pneu quando ele já tá com cara de murcho?"
Rua de bairro de dia; o "bolinha" vermelho gasto estacionado, pneu dianteiro meio baixo. O cara (polo tijolo, jeans)
está na frente do carro com a chave na mão; em "pneu" vira a cabeça e se inclina para olhar o pneu de longe; vai
apertando o olho (careta), leva a mão ao queixo e inclina a cabeça; em "murcho" a careta chega no máximo.
Câmera: push-in leve (4 %) que desliza o alvo do carro para o pneu."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _rua as R
C = R.C
import boneco_adulto as ba

P = C.plano("A_gancho")
D = P["dur"]
t_pneu = R.palavra(P, "pneu", reserva=0.5)
t_murcho = R.palavra(P, "murcho", "muxo", reserva=0.92)
sc = C.setup(P)
R.dia(sc, sol=(50, 0, -35))
M = {}
R.rua(M)
c = R.carro(M, cor="vermelho")
c["raiz"].location = (0, 2.95, 0)
xf = c["spec"]["xf"]
# pneu da frente (lado da câmera) meio murcho: achata e alarga
rd = R.roda_dd(c)
for o in rd.children:
    if o.name.endswith("_pneu"):
        o.scale = (1.035, 1.07, 0.93)
rd.location.z -= c["spec"]["R"] * 0.06
pneu = rd.matrix_world.translation if False else (xf, 2.95 - 0.66, 0.28)

# ---- o cara
Z = ba.ze_adulto("cara", M, expressao="neutro", maos="todas", **R.CARA)
Z["raiz"].location = (xf - 1.45, 1.4, 0)
Z["raiz"].rotation_euler = (0, 0, math.radians(80))
arm, V = Z["arm"], Z["rosto"]
ba.mao(Z, "e", "punho", 1)            # chave do carro na mão esquerda
chave = R.mt.box("chave", -0.012, 0.012, -0.004, 0.004, -0.05, 0.0, R._m(M, "chave", "#B9C0C8", 0.3, 1.0))
R.bpy.context.view_layer.update()
chave.location = Z["raiz"].matrix_world @ R.Vector((0.268, -0.03, 0.78))
ba._no_osso(chave, arm, "mao_e")

neutra = {"tronco": (0, -3, 0), "pescoco": (0, 0, 0), "cabeca": (-2, 3, -22),
          "ombro_d": (0, 6, 0), "cotovelo_d": (-10, 0, 0), "ombro_e": (-8, -6, 0), "cotovelo_e": (-35, 0, 0)}
cintura = dict(ombro_e=(5, -28, -20), cotovelo_e=(-70, 0, -30), ombro_d=(5, 28, 20), cotovelo_d=(-70, 0, 30))
olha = dict(neutra, tronco=(9, -2, 8), pescoco=(7, 0, 6), cabeca=(13, 0, 12), **cintura)
R.pose(Z, 0.0, neutra)
R.pose(Z, max(0.4, t_pneu - 1.0), dict(neutra, cabeca=(0, 1, -18)))          # olha o carro, respira
t1 = t_pneu + 0.12
R.pose(Z, t1 + 0.5, olha)                                                   # mãos na cintura, olha o pneu
R.pose(Z, t1 + 1.1, dict(olha, tronco=(11, -2, 7), cabeca=(15, -3, 13)))
R.pose(Z, t_murcho - 0.2, dict(olha, tronco=(12, -4, 7), cabeca=(15, -12, 14)))  # inclina a cabeça: "hmm"
R.pose(Z, D, dict(olha, tronco=(12, -4, 7), cabeca=(16, -13, 14)))
ba.mao(Z, "d", "relaxada", 1)
ba.mao(Z, "d", "punho", C.F(t1 + 0.3))
# rosto: olhar desce para o pneu, olho aperta, sobrancelha franze, boca torce
for no, keys in (("olhar_z", [(0, 0.0), (t1 + 0.3, -0.7), (D, -0.75)]),
                 ("olhar_x", [(0, 0.0), (t1 + 0.3, 0.2), (D, 0.2)]),
                 ("abre_olho", [(0, 1.0), (t1, 1.0), (t1 + 0.6, 0.75), (t_murcho, 0.5), (D, 0.48)]),
                 ("sobr_inc", [(0, 0.0), (t1 + 0.6, 0.15), (t_murcho, 0.4), (D, 0.42)]),
                 ("sobr_alt", [(0, 0.0), (t1 + 0.6, -0.2), (t_murcho, -0.5), (D, -0.5)]),
                 ("sorriso", [(0, 0.15), (t1 + 0.6, -0.1), (t_murcho, -0.45), (D, -0.45)])):
    for t, v in keys:
        C.key_val(V[no], t, v)
R.piscar(V, max(0.3, t_pneu - 0.7))

# ---- câmera: baixa, atrás do pneu murcho (primeiro plano à esquerda), o cara de frente olhando para ele.
# Push-in de 4 % e o alvo desce do rosto para entre o rosto e o pneu.
c0, a0 = (xf + 1.45, -0.55, 0.6), (xf - 0.65, 1.65, 1.0)
cam, al = R.camera(c0, a0, lens=24, dof=5.6)
p0, p1 = R.Vector(c0), R.Vector(a0)
R.kloc(cam, 0, p0)
R.kloc(cam, D, p0 + (p1 - p0) * 0.04)
R.kloc(al, 0, p1)
R.kloc(al, t1, p1)
R.kloc(al, D, (xf - 0.5, 1.75, 0.9))

C.renderizar(P, sys.argv)
