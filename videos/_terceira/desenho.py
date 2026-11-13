"""Filtro de "desenho" sobre o render: cores achatadas (mediana + faixas de luz) e contorno preto pelas bordas."""
import numpy as np
from PIL import Image, ImageFilter


def desenho(img, faixas=5, limiar=0.11, grossura=3):
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    plano = np.asarray(img.convert("RGB").filter(ImageFilter.MedianFilter(3)),
                       np.float32) / 255
    # luz em faixas (sombra chapada) mantendo o matiz
    lum = plano.mean(axis=2, keepdims=True) + 1e-4
    q = (np.floor(lum * faixas) + 0.55) / faixas
    chapado = np.clip(plano * (0.35 + 0.65 * q / lum), 0, 1)
    # contorno: gradiente da luminância suavizada
    L = np.asarray(img.convert("L").filter(ImageFilter.GaussianBlur(1.1)), np.float32) / 255
    gx = np.abs(np.diff(L, axis=1, append=L[:, -1:]))
    gy = np.abs(np.diff(L, axis=0, append=L[-1:, :]))
    borda = ((gx + gy) > limiar).astype(np.uint8) * 255
    borda = Image.fromarray(borda).filter(ImageFilter.MaxFilter(grossura)).filter(ImageFilter.GaussianBlur(0.4))
    b = np.asarray(borda, np.float32)[..., None] / 255
    out = chapado * (1 - b * 0.92) + 0.06 * b * 0.92
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


if __name__ == "__main__":
    import sys, os
    ims = []
    for f in sys.argv[2:]:
        im = Image.open(f)
        ims.append(desenho(im))
    W, H = ims[0].size
    o = Image.new("RGB", (W * len(ims), H))
    for i, im in enumerate(ims):
        o.paste(im, (W * i, 0))
    o.save(sys.argv[1])
