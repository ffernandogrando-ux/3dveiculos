"""Prancha de catálogo da biblioteca de assets: miniatura de tudo o que está em assets/ (sem renderizar nada).

    python3 videos/_assets/catalogo.py        ->  videos/_assets/catalogo.jpg

Miniaturas: as oficiais do Poly Haven/ambientCG (baixadas em assets/_miniaturas pelo baixar_assets.py) e, para os
pacotes do Quaternius/Kenney, as imagens de prévia que vêm dentro dos pacotes (quando houver); HDRIs sem miniatura
são reduzidos do próprio .hdr. Rótulo = id usado em motor3d/biblioteca.py.
"""
import os, glob, re
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
A = os.path.abspath(os.path.join(AQUI, "..", "..", "assets"))
MIN = os.path.join(A, "_miniaturas")
T = 150            # lado da miniatura
COLS = 12
FONTE = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
FONTE_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"


def fonte(p, s):
    try:
        return ImageFont.truetype(p, s)
    except OSError:
        return ImageFont.load_default()


def thumb_quadrado(img, lado=T, fundo="#2a2d33"):
    img = img.convert("RGBA")
    img.thumbnail((lado, lado))
    q = Image.new("RGB", (lado, lado), fundo)
    q.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2), img)
    return q


def secoes():
    S = []
    hd = sorted({os.path.basename(f).rsplit("_", 1)[0] for f in glob.glob(os.path.join(A, "hdri", "*.hdr"))})
    S.append(("HDRIs (Poly Haven, CC0) — bib.hdri(id)", [(k, os.path.join(MIN, f"hdri_{k}.png")) for k in hd]))
    tx = sorted(d for d in os.listdir(os.path.join(A, "texturas")))
    S.append(("Texturas PBR (Poly Haven / ambientCG, CC0) — bib.textura_pbr(id)",
              [(k, os.path.join(MIN, f"tex_{k}.png") if os.path.exists(os.path.join(MIN, f"tex_{k}.png"))
                else os.path.join(A, "texturas", k, "cor.jpg")) for k in tx]))
    md = sorted(os.listdir(os.path.join(A, "modelos", "polyhaven")))
    S.append(("Modelos (Poly Haven, CC0) — bib.importar_modelo(id)", [(k, os.path.join(MIN, f"mod_{k}.png")) for k in md]))
    # pacotes: prévia geral de cada pacote + prévias individuais escolhidas do Kenney
    pac = []
    for f in sorted(glob.glob(os.path.join(A, "modelos", "quaternius", "*", "**", "Preview*.png"), recursive=True)):
        pac.append(("quaternius/" + os.path.relpath(f, os.path.join(A, "modelos", "quaternius")).split(os.sep)[0], f))
    kp = os.path.join(A, "modelos", "kenney", "city_kit_roads", "Previews")
    for n in ("construction-cone", "construction-barrier", "construction-light", "construction-fence",
              "light-curved", "light-square-double", "road-sign-stop", "road-sign-warning", "traffic-light",
              "dumpster", "electricity-pole", "road-straight", "road-crossroad-line", "road-bend-sidewalk"):
        f = os.path.join(kp, n + ".png")
        if os.path.exists(f):
            pac.append(("kenney/" + n, f))
    S.append(("Pacotes (Quaternius / Kenney, CC0) — prévias dos pacotes", pac))
    return S


def main():
    S = secoes()
    f, fb = fonte(FONTE, 11), fonte(FONTE_B, 20)
    lab = 18
    alt = 70
    for _, itens in S:
        alt += 40 + ((len(itens) + COLS - 1) // COLS) * (T + lab + 8)
    W = COLS * (T + 8) + 16
    out = Image.new("RGB", (W, alt + 20), "#16181c")
    d = ImageDraw.Draw(out)
    d.text((16, 18), "Biblioteca de assets do canal (assets/) — tudo CC0, licenças em assets/LICENCAS.md",
           fill="#ffd36b", font=fonte(FONTE_B, 24))
    y = 70
    for tit, itens in S:
        d.text((16, y), f"{tit}  [{len(itens)}]", fill="#e8e8e8", font=fb)
        y += 40
        for i, (nome, p) in enumerate(itens):
            x = 16 + (i % COLS) * (T + 8)
            yy = y + (i // COLS) * (T + lab + 8)
            try:
                if p and p.endswith(".hdr"):
                    raise OSError
                im = thumb_quadrado(Image.open(p)) if p else Image.new("RGB", (T, T), "#2a2d33")
            except Exception:
                im = Image.new("RGB", (T, T), "#2a2d33")
            out.paste(im, (x, yy))
            d.text((x, yy + T + 3), nome[:24], fill="#b8bcc4", font=f)
        y += ((len(itens) + COLS - 1) // COLS) * (T + lab + 8)
    saida = os.path.join(AQUI, "catalogo.jpg")
    out.save(saida, quality=88)
    print("salvo:", saida, out.size)


if __name__ == "__main__":
    main()
