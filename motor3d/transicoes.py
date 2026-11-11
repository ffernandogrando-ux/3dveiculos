"""Aplica as transições com desfoque ("whip") nos cortes listados em cortes.json e gera os MP4.

Rebobinar: cortes.json pode ter "rebobinar": [{"ini": t, "fim": t, "de": t, "ate": t}] — entre ini e fim o vídeo
mostra os quadros de `ate` voltando até `de`, em preto e branco com linhas de fita. Os quadros de ini..fim não
precisam ser renderizados.

Uso:  python transicoes.py <pasta_quadros> <cortes.json> <pasta_saida> <nome> [efeitos.wav] [carimbos.json]
Com carimbos.json, desenha as palavras-chave por cima (veja carimbos.py).
Gera <nome>_9x16.mp4 (sem som) e, com o wav, <nome>_9x16_com_efeitos.mp4.
"""
import os, sys, json, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image

HALF = 5  # quadros de cada lado do corte


def hblur(img, k):
    if k < 2:
        return img
    c = np.cumsum(np.pad(img, ((0, 0), (k, k), (0, 0)), mode="wrap"), axis=1, dtype=np.float64)
    return ((c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k))[:, : img.shape[1]]


def whip(path, w, direction):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    W = a.shape[1]
    a = np.roll(a, int(direction * w * 0.45 * W), axis=1)
    a = hblur(a, int(w * 0.30 * W))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def rewind(path, f, n):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    g = a @ np.array([0.299, 0.587, 0.114])
    g = np.clip((g - 128) * 1.15 + 128, 0, 255)
    g[(np.arange(g.shape[0]) // 3) % 2 == 0] *= 0.86          # linhas de fita
    band = int((f * 37) % g.shape[0])                            # faixa de ruído correndo
    g[band:band + 14] = np.roll(g[band:band + 14], 18, axis=1) * 1.08
    a = np.repeat(np.clip(g, 0, 255)[..., None], 3, axis=2)
    return Image.fromarray(hblur(a, 3).astype(np.uint8))


def main(src, cuts_json, dst, name, wav=None, carimbos=None):
    info = json.load(open(cuts_json))
    fps = info["fps"]
    os.makedirs(dst, exist_ok=True)
    tmp = os.path.join(dst, "_quadros")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    frames = sorted(f for f in os.listdir(src) if f.endswith(".png"))
    special = {}
    for c in info["transicoes"]:
        fc = int(round(c * fps)) + 1
        for d in range(-HALF, HALF):
            w = (1 - (abs(d + 0.5) - 0.5) / HALF) ** 1.6
            special[fc + d] = (w, -1 if d < 0 else 1)
    for r in info.get("rebobinar", []):
        a, b = int(round(r["ini"] * fps)) + 1, int(round(r["fim"] * fps)) + 1
        de, ate = int(round(r["de"] * fps)) + 1, int(round(r["ate"] * fps)) + 1
        for f in range(a, b):
            sf = int(round(ate - (ate - de) * (f - a) / max(1, b - a - 1)))
            rewind(os.path.join(src, f"{sf:04d}.png"), f, b - a).save(os.path.join(tmp, f"{f:04d}.png"))
            special[f] = None
    for fn in frames:
        f = int(fn[:4])
        if f in special and special[f] is None:
            continue
        o = os.path.join(tmp, fn)
        if f in special:
            whip(os.path.join(src, fn), *special[f]).save(o)
        else:
            os.symlink(os.path.abspath(os.path.join(src, fn)), o)
    if carimbos:
        import carimbos as cb
        lista = json.load(open(carimbos))
        for fn in sorted(os.listdir(tmp)):
            t = (int(fn[:4]) - 1) / fps
            if any(c["t"] <= t <= c["fim"] for c in lista):
                p = os.path.join(tmp, fn)
                im = cb.aplicar(Image.open(p).convert("RGB"), t, lista)
                os.remove(p)
                im.save(p)
    mp4 = os.path.join(dst, f"{name}_9x16.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-start_number", str(int(frames[0][:4])),
                    "-i", os.path.join(tmp, "%04d.png"), "-c:v", "libx264", "-crf", "17", "-preset", "slow",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4], check=True)
    print("vídeo:", mp4)
    if wav:
        out = os.path.join(dst, f"{name}_9x16_com_efeitos.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-shortest", out], check=True)
        print("prévia com efeitos:", out)
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main(*[a if a else None for a in sys.argv[1:]])
