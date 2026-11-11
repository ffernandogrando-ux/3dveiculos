"""Teste comparativo de configurações de render no mesmo trecho de uma cena.

Uso:  python benchmark.py <arquivo.blend> <pasta_saida> <config> <quadro_ini> <quadro_fim>
config: ref | otimizado | otimizado4 | eevee | eevee4
Grava os PNG em <pasta_saida>/<config>/ e os tempos em <pasta_saida>/<config>.json.
"""
import bpy, sys, os, time, json

blend, out, cfg, a, b = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
s = bpy.context.scene
r = s.render
r.threads_mode = "AUTO"

if cfg == "ref":                       # o que o motor usa hoje
    s.cycles.samples = 16
elif cfg.startswith("otimizado"):
    s.cycles.samples = 4 if cfg == "otimizado4" else 8
    s.cycles.use_denoising = True
    s.cycles.denoiser = "OPENIMAGEDENOISE"
    s.cycles.use_adaptive_sampling = True
    s.cycles.max_bounces = 3
    s.cycles.diffuse_bounces = 1
    s.cycles.glossy_bounces = 1
    s.cycles.transmission_bounces = 1
    s.cycles.volume_bounces = 0
    s.cycles.transparent_max_bounces = 4
    s.cycles.caustics_reflective = False
    s.cycles.caustics_refractive = False
    s.cycles.blur_glossy = 1.0
    if hasattr(s.cycles, "use_light_tree"):
        s.cycles.use_light_tree = False
    r.use_persistent_data = True
elif cfg.startswith("eevee"):
    r.engine = "BLENDER_EEVEE"
    e = s.eevee
    e.taa_render_samples = 4 if cfg == "eevee4" else 16
    if hasattr(e, "use_raytracing"):
        e.use_raytracing = False
    if hasattr(e, "use_shadows"):
        e.use_shadows = True

dst = os.path.join(out, cfg)
os.makedirs(dst, exist_ok=True)
info = {"config": cfg, "engine": r.engine, "threads": r.threads, "frames": {}}
if r.engine == "CYCLES":
    info.update(samples=s.cycles.samples, denoiser=s.cycles.denoiser, device=s.cycles.device,
                persistent=r.use_persistent_data, max_bounces=s.cycles.max_bounces)
print("config", info, flush=True)


def camera_at(frame):
    ms = sorted((m for m in s.timeline_markers if m.frame <= frame and m.camera), key=lambda m: m.frame)
    if ms:
        s.camera = ms[-1].camera


t_all = time.time()
for f in range(a, b + 1):
    s.frame_set(f)
    camera_at(f)
    r.filepath = os.path.join(dst, f"{f:04d}.png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    info["frames"][f] = round(dt, 3)
    print(f"quadro {f}: {dt:.2f}s", flush=True)
info["total_s"] = round(time.time() - t_all, 1)
ts = list(info["frames"].values())
info["media_s"] = round(sum(ts) / len(ts), 3)
info["media_sem_primeiro_s"] = round(sum(ts[1:]) / max(1, len(ts) - 1), 3)
json.dump(info, open(os.path.join(out, cfg + ".json"), "w"), indent=1)
print("RESUMO", cfg, "média %.2fs/quadro (sem o 1º: %.2fs), total %.0fs" % (info["media_s"], info["media_sem_primeiro_s"], info["total_s"]), flush=True)
