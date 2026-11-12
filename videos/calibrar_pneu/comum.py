"""Infra comum dos planos do vídeo 02 (calibrar o pneu) — estilo "adulto" do canal.

Cada plano é um script em planos/ que monta a SUA cena, anima em tempo LOCAL (0 = início do plano) e renderiza os
quadros com numeração GLOBAL em quadros/ (o mesmo vídeo inteiro, 24 fps). Assim vários planos são feitos e
renderizados em paralelo e o transicoes.py junta tudo no final.

    import comum as C
    P = C.plano("D_chute")                       # dict com ini, fim, dur (s) do plano (de tempos.json)
    C.setup(P)                                   # cena 576x1024, 24 fps, Cycles, duração do plano
    ... montar e animar com C.F(t_local) ...
    C.renderizar(P, sys.argv)                    # argumentos: [teste t1 t2 ...] | [tudo] (padrão: tudo)

Tempos: tempos.json (estimados pela tabela do roteiro; quando chegar o .srt, só ele muda).
Resolução/amostras: W, H, AMOSTRAS (env AMOSTRAS) — 576x1024 é o padrão de entrega do canal.
"""
import os, sys, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "motor3d"))
import bpy
from mathutils import Vector, Quaternion
import motor as mt

FPS = 24
W, H = 576, 1024
AMOSTRAS = int(os.environ.get("AMOSTRAS", 16))
QUADROS = os.path.join(HERE, "quadros")
TESTES = os.path.join(HERE, "_testes")


def tempos():
    with open(os.path.join(HERE, "tempos.json")) as f:
        return json.load(f)


def plano(nome):
    T = tempos()["planos"][nome]
    return {"nome": nome, "ini": T[0], "fim": T[1], "dur": T[1] - T[0]}


def F(t):
    """Quadro LOCAL (1 = início do plano) para o tempo local t (s)."""
    return int(round(t * FPS)) + 1


def setup(P, amostras=None):
    sc = mt.setup(P["dur"] + 0.05, fps=FPS, samples=amostras or AMOSTRAS, res=(W, H))
    c = sc.cycles
    if hasattr(c, "denoising_quality"):
        c.denoising_quality = "HIGH"
    return sc


def key_rot(arm, osso, t, x=0.0, y=0.0, z=0.0):
    """Pose do esqueleto (boneco_adulto.girar) gravada como keyframe no tempo local t."""
    import boneco_adulto as ba
    ba.girar(arm, osso, x, y, z)
    arm.pose.bones[osso].keyframe_insert("rotation_quaternion", frame=F(t))


def key_val(no_value, t, v):
    """Keyframe num nó Value (rosto do Zé: abre_olho, sorriso, boca_aberta, sobr_alt...)."""
    no_value.outputs[0].default_value = v
    no_value.outputs[0].keyframe_insert("default_value", frame=F(t))


def renderizar(P, argv):
    """argv: ['teste', t1, t2...] = quadros de teste em _testes/<nome>_<t>.png (tempo local);
    senão renderiza o plano inteiro em quadros/NNNN.png com numeração global (pula prontos)."""
    sc = mt.scene
    a = [x for x in argv[1:] if x != "--"]
    if a and a[0] == "teste":
        os.makedirs(TESTES, exist_ok=True)
        for t in map(float, a[1:] or [P["dur"] / 2]):
            sc.frame_set(F(t))
            sc.render.filepath = os.path.join(TESTES, f"{P['nome']}_{t:05.2f}.png")
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            print(f"teste {P['nome']} t={t}: {time.time() - t0:.1f}s", flush=True)
        return
    os.makedirs(QUADROS, exist_ok=True)
    g0 = int(round(P["ini"] * FPS)) + 1            # quadro global do início
    n = int(round(P["dur"] * FPS))
    for k in range(n):
        g = g0 + k
        p = os.path.join(QUADROS, f"{g:04d}.png")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            continue
        sc.frame_set(k + 1)
        sc.render.filepath = p
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"{P['nome']} quadro {g} ({time.time() - t0:.1f}s)", flush=True)
