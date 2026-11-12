"""Prova de expressões do Zé (estilo adulto): prancha com 10 expressões + teste de fala sincronizada (lip sync)
com um trecho da narração do vídeo 02.

Uso:  ~/.venv-video/bin/python videos/_expressoes/expressoes.py [prancha] [fala]
"""
import sys, os, math, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "motor3d"))
import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont
import motor as mt
import boneco_adulto as ba

AMOSTRAS = int(os.environ.get("AMOSTRAS", 12))
NOMES = ["neutro", "sorriso", "risada", "fala", "duvida", "preocupado", "surpreso", "bravo", "careta", "desdem"]


def cena(roupa="mecanico", dur=1.0):
    sc = mt.setup(dur, samples=AMOSTRAS, res=(576, 1024))
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = -1.0
    w = bpy.data.worlds.new("m"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = mt.lin("#2A2F36")
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
    M = {}
    ba.oficina(M, largura=8, fundo_y=1.4)
    Z = ba.ze_adulto("ze", M, pose="parado", expressao="neutro")
    for pos, e, tam, cor in (((-1.6, -1.8, 1.9), 380, 1.6, "#FFE8D0"), ((1.8, -1.6, 1.6), 200, 2.0, "#DCE6FF"),
                             ((1.2, 1.0, 2.3), 600, 1.0, "#CFE0FF")):
        d = bpy.data.lights.new("a", "AREA"); d.energy, d.size = e, tam; d.color = mt.lin(cor)[:3]
        o = mt.link(bpy.data.objects.new("a", d)); o.location = pos
        o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector((0, 0, 1.62)) - Vector(pos)).to_track_quat("-Z", "Y")
    cd = bpy.data.cameras.new("c"); cd.lens = 50          # plano médio (do peito para cima), sem close colado
    cd.dof.use_dof = True; cd.dof.focus_distance = 1.75; cd.dof.aperture_fstop = 5.6
    cam = mt.link(bpy.data.objects.new("c", cd)); sc.camera = cam
    cam.location = (-0.35, -1.7, 1.62)
    cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (Vector((0, 0, 1.5)) - cam.location).to_track_quat("-Z", "Y")
    return sc, Z


def prancha():
    sc, Z = cena()
    sc.render.resolution_x, sc.render.resolution_y = 432, 540
    ims = []
    for n in NOMES:
        alvo = dict(abre_olho=1.0, sobr_alt=0.0, sobr_inc=0.0, sorriso=0.15, aperta=0.0, boca_aberta=0.0, boca_larg=0.0,
                    boca_redonda=0.0, olhar_x=0.0, olhar_z=0.0)
        alvo.update(ba.EXPRESSOES[n])
        for k, v in alvo.items():
            Z["rosto"][k].outputs[0].default_value = v
        sc.render.filepath = os.path.join(HERE, f"_e_{n}.png")
        bpy.ops.render.render(write_still=True)
        ims.append((n, Image.open(sc.render.filepath).convert("RGB")))
    f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 30)
    w, h = ims[0][1].size
    out = Image.new("RGB", (w * 5 + 40, (h + 50) * 2 + 10), "#14171C")
    d = ImageDraw.Draw(out)
    for i, (n, im) in enumerate(ims):
        x, y = 10 + (i % 5) * (w + 5), 10 + (i // 5) * (h + 50)
        out.paste(im, (x, y + 40))
        d.text((x + 6, y), n.upper(), font=f, fill="#19C3E6")
    out.save(os.path.join(HERE, "expressoes.jpg"), quality=90)
    print("prancha ok")


def fala():
    PAL = json.load(open(os.path.join(RAIZ, "videos", "calibrar_pneu", "palavras.json")))
    t0, t1 = 49.45, 53.15                       # "Esse é o máximo que o pneu aguenta, não o certo pro seu carro."
    sc, Z = cena(dur=t1 - t0)
    F = lambda t: int(round(t * 24)) + 1
    loc = lambda t: t - t0
    ba.falar(Z, PAL, t0, t1, F, loc)
    ba.piscar(Z, t0, t1, F, loc)
    ba.expressao(Z, "duvida", t0, F, loc)
    ba.expressao(Z, "surpreso", 50.05, F, loc)          # "máximo"
    ba.expressao(Z, "bravo", 51.6, F, loc)              # "não o certo"
    ba.expressao(Z, "sorriso", 52.7, F, loc)            # "seu carro"
    for t, (x, y, z) in ((t0, (0, 3, 2)), (50.1, (-5, 0, -4)), (51.7, (3, -3, 4)), (52.8, (0, 4, 0))):
        ba.girar(Z["arm"], "cabeca", x, y, z)
        Z["arm"].pose.bones["cabeca"].keyframe_insert("rotation_quaternion", frame=F(loc(t)))
    pasta = os.path.join(HERE, "_quadros_fala")
    os.makedirs(pasta, exist_ok=True)
    for f in range(1, F(t1 - t0)):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(pasta, f"{f:04d}.png")
        bpy.ops.render.render(write_still=True)
    wav = os.path.join(RAIZ, "videos", "calibrar_pneu", "narracao.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "24", "-i", os.path.join(pasta, "%04d.png"),
                    "-ss", str(t0), "-t", str(t1 - t0), "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", os.path.join(HERE, "teste_fala.mp4")], check=True)
    print("fala ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["prancha", "fala"]
    if "prancha" in a:
        prancha()
    if "fala" in a:
        fala()
