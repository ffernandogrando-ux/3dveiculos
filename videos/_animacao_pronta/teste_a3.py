"""Teste A3: "o cara" (motor3d/personagem_q.py: corpo Quaternius, regata branca, jeans, tênis, rosto pintado) na rua
do vídeo 02: anda até o carro, para, chuta o pneu e dá de ombros, com o rosto reagindo (careta ao olhar o pneu,
desdém no "tá bom ainda").
    AMOSTRAS=8 ~/.venv-video/bin/python teste_a3.py teste 1.0 2.4 3.8
    AMOSTRAS=8 ~/.venv-video/bin/python teste_a3.py video 12
"""
import os, sys, math, subprocess, time
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "videos", "calibrar_pneu", "planos"))
import _rua as R
C = R.C
import bpy
from mathutils import Vector
import personagem_q as pq

FPS, D = 24, 4.8
P0 = {"nome": "teste_a3", "ini": 0.0, "fim": D, "dur": D}
sc = C.setup(P0, amostras=int(os.environ.get("AMOSTRAS", 8)))
R.dia(sc, sol=(50, 0, -35))
M = {}
c, xf, pn = R.cena_carro_rua(M)
yT = pn.y

Q = pq.personagem("cara")
t_para, t_chute, t_omb = 1.6, 1.9, 3.1
p_fim = Vector((pn.x + 0.05, yT - 0.62, 0))
p_ini = p_fim - Vector((2.35, 0.18, 0))
pq.animar(Q, [("andar", 0.0, t_para, p_ini, p_fim), ("parado", t_para), ("chutar", t_chute), ("ombros", t_omb),
              ("virar", t_para - 0.1, t_chute, 150), ("virar", t_omb - 0.05, t_omb + 0.4, 55)])
# rosto: neutro andando → careta ao olhar o pneu → desdém no "tá bom ainda" (fala curta)
pq.piscar(Q, 0.0, D)
pq.rosto(Q, "neutro", 0.0)
pq.rosto(Q, "neutro", t_para - 0.1)
pq.rosto(Q, "careta", t_para + 0.25)
pq.rosto(Q, "careta", t_omb)
pq.rosto(Q, "desdem", t_omb + 0.35)
V = Q["rosto"]
for t, v in ((0, 0.0), (t_para, -0.5), (t_omb, -0.5), (t_omb + 0.35, 0.0)):
    C.key_val(V["olhar_z"], t, v)
R.fala(V, t_omb + 0.45, t_omb + 1.1, forte=0.5, seed=3)

t_tum = t_chute + 0.5
for k in range(8):
    a = 0.8 * math.exp(-k * 0.45) * (1 if k % 2 == 0 else -1) if k else 0.0
    R.krot(c["raiz"], t_tum + k * 0.06, (a, 0, 0))

# câmera: começa aberta (chegada) e fecha no rosto durante o "tá bom"
c0 = Vector((pn.x + 2.7, yT - 2.6, 1.05))
a0 = Vector((pn.x - 0.5, yT - 0.5, 0.85))
cam, al = R.camera(c0, a0, lens=26, dof=5.6)
R.kloc(cam, 0, c0)
R.kloc(cam, t_omb, c0 + (a0 - c0) * 0.08)
R.kloc(cam, D, c0 + (a0 - c0) * 0.3 + Vector((0, 0, 0.25)))
R.kloc(al, 0, a0)
R.kloc(al, t_omb, a0)
R.kloc(al, D, p_fim + Vector((0, 0, 1.35)))

a = [x for x in sys.argv[1:] if x != "--"]
modo = a[0] if a else "teste"
saida = os.path.join(AQUI, "_quadros_a3")
os.makedirs(saida, exist_ok=True)
if modo == "teste":
    for t in map(float, a[1:] or ["1.0", "2.4", "3.8"]):
        sc.frame_set(C.F(t))
        sc.render.filepath = os.path.join(AQUI, f"teste_a3_{t:04.2f}.png")
        t0 = time.time(); bpy.ops.render.render(write_still=True); print("quadro %.1fs" % (time.time() - t0))
else:
    fps_v = int(a[1]) if len(a) > 1 else 12
    fs = list(range(1, C.F(D) + 1, FPS // fps_v))
    for i, f in enumerate(fs):
        p = os.path.join(saida, f"{i:04d}.png")
        if os.path.exists(p):
            continue
        sc.frame_set(f)
        sc.render.filepath = p
        t0 = time.time(); bpy.ops.render.render(write_still=True); print("quadro %d %.1fs" % (i, time.time() - t0), flush=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps_v), "-i", os.path.join(saida, "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", os.path.join(AQUI, "teste_a3.mp4")], check=True)
