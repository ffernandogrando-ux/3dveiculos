"""Plano I: "Ah, mas eu calibro no POSTO, depois de RODAR!"
Posto genérico sem marca (cobertura, bomba, loja, calibrador de parede com mangueira espiral). O bolinha vermelho
entra pela esquerda rodando, freia (ease de saída, rodas girando sem escorregar) e para junto ao calibrador em
"posto", com o mergulho leve da frente na freada; em "rodar" sai uma fumacinha leve do pneu dianteiro quente.
Câmera baixa de 3/4 pela frente, acompanha o carro e faz push-in no pneu no fim."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _rua as R
C = R.C
import boneco_adulto as ba
from mathutils import Vector

P = C.plano("I_posto")
D = P["dur"]
t_posto = R.palavra(P, "posto", reserva=0.47)
t_rodar = R.palavra(P, "rodar", reserva=0.86)
sc = C.setup(P)
R.dia(sc, sol=(55, 0, -40), forca=3.0)
M = {}
R.posto(M, x_cal=3.35)
c = R.carro(M, cor="vermelho")
car = c["raiz"]
xf, Rr = c["spec"]["xf"], c["spec"]["R"]
Y = 0.75
x_para = 3.35 - 0.95 - xf            # roda dianteira para logo antes do calibrador
L = 7.5                              # distância percorrida até parar
t_para = max(0.9, t_posto + 0.15)
# x(t): velocidade constante desacelerando até zero em t_para (posição amostrada, interpolação linear)
t = 0.0
while True:
    u = min(1.0, t / t_para)
    x = x_para - L * (1 - u) ** 2
    R.kloc(car, t, (x, Y, 0))
    if t >= D:
        break
    t = min(D, t + 1.0 / C.FPS * 2)
ba.suavizar(car, "LINEAR")
R.girar_rodas(c, 0.0, D, x_para - L, x_para, passo=1.0 / C.FPS)
# mergulho da frente na freada (nariz desce = +y) e volta
for tt, a in ((0, 0), (t_para - 0.35, 0.3), (t_para, 1.3), (t_para + 0.18, -0.45), (t_para + 0.36, 0.15),
              (t_para + 0.5, 0)):
    R.krot(car, tt, (0, a, 0))
# fumacinha do pneu dianteiro (lado da câmera) — começa um pouco antes de "rodar"
pn = Vector((x_para + xf, Y - 0.72, 0.25))
R.fumaca("fum", M, (pn.x + 0.05, pn.y - 0.05, 0.25), max(t_para, t_rodar - 0.5), D + 0.6, n=7)

# ---- câmera: baixa de 3/4 pela frente, segue o carro chegando e fecha no pneu
c0 = Vector((x_para + xf + 2.4, Y - 4.0, 1.05))
cam, al = R.camera(c0, (x_para - 2.0, Y, 0.8), lens=28, dof=5.6)
R.kloc(cam, 0, c0)
R.kloc(cam, t_para, c0 + Vector((-0.2, 0.15, -0.05)))
R.kloc(cam, D, c0 + Vector((-0.55, 0.6, -0.25)))
for tt in (0.0, t_para * 0.5, t_para):
    xx = x_para - L * (1 - min(1, tt / t_para)) ** 2
    R.kloc(al, tt, (xx + xf * 0.3, Y, 0.75))
R.kloc(al, D, (pn.x + 0.1, pn.y + 0.3, 0.5))

C.renderizar(P, sys.argv)
