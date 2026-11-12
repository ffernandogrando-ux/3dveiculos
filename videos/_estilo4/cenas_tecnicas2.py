"""Cenas técnicas, 2ª leva (estilo "EXPLICATIVO TÉCNICO 3D", direção B).

  corrente -> tecnico_corrente.png : corrente de moto LUBRIFICADA x SECA (ferrugem, elo esticado, dente gasto)
  raiox    -> tecnico_raiox.png    : carro (veiculos3, estilo="real") com lataria em raio-X ciano e trem de força
  anim     -> teste_motor.mp4      : 48 quadros (2 s a 24 fps), 720x1280, órbita de 15° no motor em corte,
                                     virabrequim girando 1 volta e callouts reprojetados quadro a quadro

Uso:  ~/.venv-video/bin/python videos/_estilo4/cenas_tecnicas2.py corrente|raiox|anim [escala] [amostras]
"""
import os, sys, time, math, shutil, subprocess
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "motor3d"))
sys.path.insert(0, AQUI)
import bpy
import tecnico as tc
import mecanismo_prova as mp
from mecanismo_prova import HUD, chamada, p2


# ------------------------------------------------------------ corrente
def cena_corrente(escala, amostras):
    tc.nova_cena(res=(int(1080 * escala), int(1920 * escala)), amostras=amostras)
    tc.estudio_tecnico(alvo=(0, 0, 0.5), luz=0.35)
    # rebatedor frontal: metal virado para a câmera precisa de algo claro para refletir
    fr = tc.luz_area("frente", (0.3, -2.6, 1.9), (0, 0, 0.55), 1.8, 0.7, 28, abertura=60)
    yaw = -14
    lub = tc.corrente_moto("lub", loc=(-0.155, 0.0, 0.76), estado="lubrificada", yaw=yaw)
    sec = tc.corrente_moto("seca", loc=(-0.155, 0.0, 0.38), estado="seca", yaw=yaw)
    alvo = (0.0, 0.0, 0.60)
    cam = tc.camera((0, -3.4, 0.9), alvo, lente=98)
    tc.orbita(cam, alvo, 3.4, 0.0, 0.99)
    bpy.context.view_layer.update()
    co = []
    co.append(chamada(lub["ancoras"]["ramo_cima"], cam, (620, 330, 1), "PELÍCULA DE ÓLEO", "ROLA LISO", tc.VERDE, escala, 32))
    co.append(chamada(sec["ancoras"]["dente"], cam, (520, 1050, 1), "DENTE GASTO", "BICO DE TUBARÃO", tc.LARANJA, escala, 32))
    co.append(chamada(sec["ancoras"]["ramo_baixo"], cam, (560, 1740, -1), "ELO ESTICADO", "CORRENTE COM FOLGA", tc.VERMELHO, escala, 32))
    return lub, sec, co


def pos_corrente(caminho, lub, sec, co):
    h = HUD(caminho)
    h.cantos()
    h.cabecalho("CORRENTE DA MOTO", "03 / TRANSMISSÃO")
    for p, txt, cor, sub in ((lub, "LUBRIFICADA", tc.VERDE, "ÓLEO EM DIA"), (sec, "SECA", tc.VERMELHO, "SEM LUBRIFICAÇÃO")):
        _, y = p2(p["ancoras"]["topo"])
        h.caixa_tag((100 * h.k, y - 70 * h.k), txt, cor, 30, ancora="l")
        h.texto((100 * h.k, y - 24 * h.k), sub, 19, "#9AA6B4", "ls", espaco=0.14, arq=mp.FONTE_MED)
    for c in co:
        h.etiqueta(p2(c["cotovelo"]), p2(c["fim"]), c["titulo"], c["sub"], c["cor"], tam=c["tam"])
    h.salvar(caminho)


# ------------------------------------------------------------ raio-X
def cena_raiox(escala, amostras):
    tc.nova_cena(res=(int(1080 * escala), int(1920 * escala)), amostras=amostras)
    bpy.context.scene.cycles.transparent_max_bounces = 24
    tc.estudio_tecnico(alvo=(0, 0, 0.6), luz=1.4)
    D = tc.carro_raio_x("carro", "hatch", loc=(0.0, 0.0, 0.0), yaw=-58)
    alvo = (0.05, 0.0, 0.55)
    cam = tc.camera((0, -7, 3), alvo, lente=55)
    tc.orbita(cam, alvo, 7.6, 0.0, 3.6)
    bpy.context.view_layer.update()
    co = []
    co.append(chamada(D["ancoras"]["motor"], cam, (300, 700, -1), "MOTOR", "1.0 · 4 CILINDROS", tc.CIANO, escala, 36))
    co.append(chamada(D["ancoras"]["cambio"], cam, (760, 640, 1), "CÂMBIO", None, tc.CIANO, escala, 36))
    co.append(chamada(D["ancoras"]["escape"], cam, (760, 1500, 1), "ESCAPAMENTO", None, tc.CIANO, escala, 32))
    return D, co


def pos_raiox(caminho, D, co):
    h = HUD(caminho)
    h.cantos()
    h.cabecalho("RAIO-X DO CARRO", "04 / POR DENTRO")
    for c in co:
        h.etiqueta(p2(c["cotovelo"]), p2(c["fim"]), c["titulo"], c["sub"], c["cor"], tam=c["tam"])
    h.salvar(caminho)


# ------------------------------------------------------------ animação do motor
def anim_motor(amostras=16, quadros=48, res=(720, 1280)):
    escala = res[0] / 1080
    tc.nova_cena(res=res, amostras=amostras)
    sc = bpy.context.scene
    sc.render.use_persistent_data = True
    tc.estudio_tecnico(alvo=(0, 0, 0.25), luz=0.55)
    mt = tc.motor_corte("motor", loc=(0.055, 0, 0), yaw=-20, ang_vira=80)
    alvo = (0.0, 0.0, 0.25)
    cam = tc.camera((0, -2.8, 0.7), alvo, lente=85)
    pasta = os.path.join(AQUI, "_quadros_motor")
    shutil.rmtree(pasta, ignore_errors=True)
    os.makedirs(pasta)
    tempos = []
    for f in range(quadros):
        t = f / quadros
        ease = 0.5 - 0.5 * math.cos(math.pi * t)               # órbita com entrada/saída suaves
        tc.orbita(cam, alvo, 2.8, -7.5 + 15.0 * ease, 0.72)
        anc = tc.motor_pose(mt, 80 + 360.0 * t)
        bpy.context.view_layer.update()
        # callouts refeitos a cada quadro (âncora "aneis" anda com o pistão)
        for o in [o for o in bpy.data.objects if o.name.startswith("c_")]:
            bpy.data.objects.remove(o, do_unlink=True)
        co = [chamada(anc["aneis"], cam, (420, 720, -1), "ANÉIS", "VEDAM O CILINDRO", tc.CIANO, escala, 40),
              chamada(anc["oleo"], cam, (1010, 1640, -1), "ÓLEO", "LUBRIFICA E ESFRIA", tc.CIANO, escala, 40)]
        out = os.path.join(pasta, f"q{f:03d}.png")
        t0 = time.time()
        tc.render(out)
        tempos.append(time.time() - t0)
        h = HUD(out)
        h.cantos()
        h.cabecalho("MOTOR EM CORTE", "02 / LUBRIFICAÇÃO")
        for c in co:
            h.etiqueta(p2(c["cotovelo"]), p2(c["fim"]), c["titulo"], c["sub"], c["cor"], tam=c["tam"])
        h.salvar(out)
        print(f"quadro {f + 1}/{quadros}: {tempos[-1]:.1f}s", flush=True)
    mp4 = os.path.join(AQUI, "teste_motor.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(pasta, "q%03d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", mp4], check=True)
    print(f"ANIM: {quadros} quadros, média {sum(tempos) / len(tempos):.1f}s/quadro "
          f"(min {min(tempos):.1f}, máx {max(tempos):.1f}), total {sum(tempos):.0f}s -> {mp4}")


if __name__ == "__main__":
    args = sys.argv[1:]
    qual = args[0] if args else "corrente"
    escala = float(args[1]) if len(args) > 1 else 1.0
    amostras = int(args[2]) if len(args) > 2 else 16
    if qual == "corrente":
        t0 = time.time(); lub, sec, co = cena_corrente(escala, amostras); t1 = time.time()
        out = os.path.join(AQUI, "tecnico_corrente.png"); tc.render(out); t2 = time.time()
        pos_corrente(out, lub, sec, co)
        print(f"CORRENTE: montagem {t1 - t0:.1f}s, render {t2 - t1:.1f}s; {lub['info']} | {sec['info']}")
    elif qual == "raiox":
        t0 = time.time(); D, co = cena_raiox(escala, amostras); t1 = time.time()
        out = os.path.join(AQUI, "tecnico_raiox.png"); tc.render(out); t2 = time.time()
        pos_raiox(out, D, co)
        print(f"RAIOX: montagem {t1 - t0:.1f}s, render {t2 - t1:.1f}s")
    elif qual == "anim":
        anim_motor(amostras)
