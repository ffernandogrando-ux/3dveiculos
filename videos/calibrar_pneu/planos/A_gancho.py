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
R.rua(M, x0=-14, x1=40, outro_lado=-7.3)
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
Z["raiz"].location = (xf + 1.65, 0.95, 0)
Z["raiz"].rotation_euler = (0, 0, math.radians(-112))
arm, V = Z["arm"], Z["rosto"]
ba.mao(Z, "e", "punho", 1)            # chave do carro na mão esquerda
chave = R.mt.box("chave", -0.012, 0.012, -0.004, 0.004, -0.05, 0.0, R._m(M, "chave", "#B9C0C8", 0.3, 1.0))
chave.location = (0.268, -0.03, 0.78)
ba._no_osso(chave, arm, "mao_e")

neutra = {"tronco": (0, -3, 0), "pescoco": (0, 0, 0), "cabeca": (-2, 3, -6),
          "ombro_d": (0, 6, 0), "cotovelo_d": (-10, 0, 0), "mao_d": (0, 0, 0),
          "ombro_e": (-8, -6, 0), "cotovelo_e": (-35, 0, 0)}
olha = dict(neutra, tronco=(9, -2, 6), pescoco=(7, 0, 4), cabeca=(13, 0, 8))
mao_queixo = dict(ombro_d=(-48, 12, 0), cotovelo_d=(-128, 0, -22), mao_d=(-10, 0, 0))
R.pose(Z, 0.0, neutra)
R.pose(Z, max(0.4, t_pneu - 1.0), dict(neutra, cabeca=(0, 1, -2)))          # olha o carro, respira
t1 = t_pneu + 0.12
R.pose(Z, t1 + 0.45, dict(olha, ombro_d=(-4, 8, 0)))                       # baixa o olhar para o pneu
R.pose(Z, t1 + 1.05, dict(olha, cabeca=(14, -3, 9), **mao_queixo))          # mão no queixo
R.pose(Z, t_murcho - 0.25, dict(olha, tronco=(10, -3, 6), cabeca=(14, -11, 10), **mao_queixo))  # inclina a cabeça
R.pose(Z, D, dict(olha, tronco=(10, -3, 6), cabeca=(15, -12, 10),
                  **dict(mao_queixo, cotovelo_d=(-131, 0, -22))))
ba.mao(Z, "d", "relaxada", 1)
ba.mao(Z, "d", "punho", C.F(t1 + 0.7))
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
c0, a0 = (xf - 1.35, 1.6, 0.85), (xf + 1.5, 0.85, 1.05)
cam, al = R.camera(c0, a0, lens=26, dof=4.0)
p0, p1 = R.Vector(c0), R.Vector(a0)
R.kloc(cam, 0, p0)
R.kloc(cam, D, p0 + (p1 - p0) * 0.04)
R.kloc(al, 0, p1)
R.kloc(al, t1, p1)
R.kloc(al, D, (xf + 1.3, 1.0, 0.92))

C.renderizar(P, sys.argv)
