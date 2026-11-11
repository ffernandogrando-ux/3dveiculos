"""Render de um .blend do motor.

Quadros de teste:   python render.py stills <arquivo.blend> <pasta_saida> <amostras> <t1> <t2> ...
Faixa de quadros:   python render.py range  <arquivo.blend> <pasta_saida> <amostras> <quadro_ini> <quadro_fim>
A faixa pula quadros já prontos (pode ser retomada a qualquer momento).
SEM_PERSISTENTE=1 desliga os dados persistentes (mais lento; use para refazer quadros que saíram com material preto).
"""
import bpy, sys, os, time

mode, blend, out, samples = sys.argv[1:5]
rest = sys.argv[5:]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
s = bpy.context.scene
s.cycles.samples = int(samples)
if os.environ.get("SEM_PERSISTENTE"):        # refazer trechos com materiais pretos (falha dos dados persistentes)
    s.render.use_persistent_data = False
fps = s.render.fps
os.makedirs(out, exist_ok=True)


def camera_at(frame):
    ms = sorted((m for m in s.timeline_markers if m.frame <= frame and m.camera), key=lambda m: m.frame)
    if ms:
        s.camera = ms[-1].camera


if mode == "stills":
    for t in map(float, rest):
        f = int(round(t * fps)) + 1
        s.frame_set(f)
        camera_at(f)
        s.render.filepath = os.path.join(out, f"t{t:05.1f}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"quadro {f} ({t}s) em {time.time() - t0:.1f}s", flush=True)
else:
    a, b = int(rest[0]), int(rest[1])
    for f in range(a, b + 1):
        p = os.path.join(out, f"{f:04d}.png")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            continue
        s.frame_set(f)
        camera_at(f)
        s.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print(f"quadro {f}", flush=True)
