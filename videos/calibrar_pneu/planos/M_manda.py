"""Plano M: "MANDA esse vídeo pra quem só calibra no CHUTINHO."
O bolinha vermelho andando pela rua do bairro (≈18 km/h), rodas girando sem escorregar, carroceria com balanço leve.
A câmera acompanha o carro (presa a um vazio que anda junto) e faz uma órbita lenta de 3/4 frente para o lado,
com push-in leve; em "chutinho" a órbita termina com o pneu dianteiro em destaque."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _rua as R
C = R.C
import boneco_adulto as ba
import motor as mt
from mathutils import Vector

P = C.plano("M_manda")
D = P["dur"]
t_manda = R.palavra(P, "manda", reserva=0.03)
t_chut = R.palavra(P, "chutinho", reserva=0.78)
sc = C.setup(P)
R.dia(sc, sol=(50, 0, -35))
M = {}
R.rua(M, x0=-18, x1=26)
c = R.carro(M, cor="vermelho")
car = c["raiz"]
V = 5.0                      # m/s
Y = 0.6
x0, x1 = -5.5, -5.5 + V * (D + 0.1)
R.kloc(car, 0, (x0, Y, 0))
R.kloc(car, D + 0.1, (x1, Y, 0))
ba.suavizar(car, "LINEAR")
R.girar_rodas(c, 0.0, D + 0.1, x0, x1, passo=0.5)
# balanço leve da carroceria (rolagem/arfagem em senoides lentas)
for k in range(int(D / 0.2) + 2):
    t = k * 0.2
    R.krot(car, t, (0.35 * math.sin(t * 5.1), 0.25 * math.sin(t * 3.7 + 1), 0))
for fc in R.ba._curvas(car.animation_data.action):
    if "rotation" in fc.data_path:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"

# ---- câmera presa a um vazio que anda com o carro (mesma velocidade)
seg = mt.empty("segue", (x0, Y, 0))
R.kloc(seg, 0, (x0, Y, 0))
R.kloc(seg, D + 0.1, (x1, Y, 0))
ba.suavizar(seg, "LINEAR")
cam, al = R.camera((0, 0, 0), (0, 0, 0), lens=30, dof=6.0)
cam.parent = seg
al.parent = seg
xf = c["spec"]["xf"]
R.kloc(cam, 0, (4.6, -5.4, 1.35))
R.kloc(cam, t_chut, (2.4, -5.9, 1.1))
R.kloc(cam, D, (2.2, -5.75, 1.05))
R.kloc(al, 0, (0.4, 0, 0.62))
R.kloc(al, t_chut, (xf * 0.4, -0.2, 0.6))
R.kloc(al, D, (xf * 0.45, -0.2, 0.58))

sc.render.use_motion_blur = True          # rodas e fundo com borrão de movimento leve
sc.render.motion_blur_shutter = 0.35

C.renderizar(P, sys.argv)
