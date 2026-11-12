"""Baixa a biblioteca de material livre (CC0) do canal para assets/. Idempotente: pula o que já existe.

    python3 -I scripts/baixar_assets.py            # tudo (menos os pacotes grandes)
    python3 -I scripts/baixar_assets.py hdri       # só uma parte: hdri | texturas | modelos | sons | fontes
    GRANDES=1 python3 -I scripts/baixar_assets.py  # inclui o Downtown City MegaKit do Quaternius (223 MB)

Normalmente chamado por scripts/baixar_assets.sh. As listas abaixo SÃO o catálogo: para incluir um item, acrescente
o id aqui e rode de novo. O assets/LICENCAS.md é refeito a cada execução a partir do que existe no disco.

Fontes (todas CC0, exceto as fontes de texto, que são OFL):
  Poly Haven  https://polyhaven.com  (API https://api.polyhaven.com) - HDRIs, texturas, modelos
  ambientCG   https://ambientcg.com  (API v2)                        - texturas PBR
  Quaternius  https://quaternius.itch.io                             - pacotes low-poly (via itch; o Google Drive
                                                                       do quaternius.com responde "Quota exceeded")
  Kenney      https://opengameart.org/users/kenney                   - City Kit Roads (kenney.nl dá 403 nesta rede)
  OpenGameArt https://opengameart.org                                - sons CC0
  Google Fonts https://github.com/google/fonts                       - fontes OFL (livres p/ uso comercial)
"""
import os, sys, json, time, shutil, zipfile, subprocess, urllib.request, datetime

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
A = os.path.join(RAIZ, "assets")
UA = {"User-Agent": "assets-script/1.0"}
HOJE = datetime.date.today().isoformat()

# ------------------------------------------------------------------ catálogo
# HDRIs Poly Haven: id -> (uso, resoluções)
HDRIS = {
    "wide_street_01": ("rua larga de dia, sol", ["1k", "2k"]),
    "urban_street_01": ("rua urbana de dia", ["1k"]),
    "preller_drive": ("rua de bairro com casas, sol", ["1k"]),
    "suburban_parking_area": ("estacionamento de bairro, sol", ["1k", "2k"]),
    "kloofendal_48d_partly_cloudy_puresky": ("só céu, parcialmente nublado (luz de dia limpa)", ["1k", "2k"]),
    "mall_parking_lot": ("estacionamento de shopping (posto/estacionamento)", ["1k"]),
    "park_parking": ("estacionamento de parque", ["1k"]),
    "parking_garage": ("garagem coberta de prédio", ["1k"]),
    "autoshop_01": ("oficina mecânica", ["1k", "2k"]),
    "auto_service": ("galpão de serviço automotivo", ["1k"]),
    "skylit_garage": ("garagem com claraboia", ["1k"]),
    "machine_shop_02": ("oficina de máquinas", ["1k"]),
    "small_workshop": ("oficina pequena", ["1k"]),
    "yaris_interior_garage": ("dentro de um carro, na garagem", ["1k"]),
    "studio_small_08": ("estúdio (cenas técnicas)", ["1k"]),
    "studio_small_09": ("estúdio escuro (cenas técnicas)", ["1k"]),
    "cyclorama_hard_light": ("estúdio ciclorama, luz dura", ["1k"]),
    "modern_evening_street": ("rua ao anoitecer, luzes acesas", ["1k"]),
}
# Texturas Poly Haven (1k jpg: cor, rugosidade, normal GL): id -> uso
TEX_PH = {
    "asphalt_02": "asfalto de rua",
    "clean_asphalt": "asfalto novo/liso",
    "concrete_pavement": "calçada de concreto (placas)",
    "concrete_floor_02": "concreto liso",
    "garage_floor": "piso de garagem/oficina (manchado)",
    "concrete_floor_painted": "piso de concreto pintado",
    "painted_plaster_wall": "muro de reboco pintado",
    "concrete_block_wall": "muro de bloco de concreto",
    "brick_wall_02": "parede de tijolo",
    "metal_plate": "chapa de metal",
    "corrugated_iron": "telha/portão de zinco ondulado",
    "painted_metal_shutter": "porta de enrolar pintada (oficina)",
    "rubber_tiles": "piso de borracha",
}
# Texturas ambientCG (1K-JPG): id -> uso
TEX_ACG = {
    "Rubber004": "borracha (pneu, mangueira)",
    "Metal009": "metal escovado",
    "DiamondPlate008A": "chapa xadrez (rampa, caçamba)",
    "Road007": "asfalto com faixa pintada",
    "Asphalt031": "asfalto gasto",
    "Tiles074": "piso cerâmico (oficina/posto)",
    "Paint004": "pintura (superfície pintada)",
    "Plastic010": "plástico (para-choque, painel)",
    "Leather037": "couro (banco)",
    "PaintedPlaster017": "reboco pintado",
}
# Modelos Poly Haven (glTF 1k): id -> uso
MOD_PH = {
    "old_tyre": "pneu velho", "rusted_wheel_rim_01": "roda de aço enferrujada", "tire_pump": "bomba de encher pneu",
    "tool_cart": "carrinho de ferramentas", "metal_tool_chest": "gaveteiro de ferramentas",
    "metal_toolbox": "caixa de ferramentas", "combination_wrench": "chave combinada",
    "adjustable_wrench": "chave inglesa", "ratchet_wrench": "catraca", "pliers": "alicate",
    "screwdriver": "chave de fenda", "bench_vice_01": "morsa de bancada", "hand_truck": "carrinho de carga",
    "oil_tin": "lata de óleo", "small_oil_can_01": "almotolia", "lubricant_spray": "spray lubrificante",
    "Barrel_01": "tambor", "barrel_03": "tambor 2", "metal_jerrycan": "galão de metal",
    "plastic_jerrycan": "galão de plástico", "steel_frame_shelves_01": "estante de aço",
    "cardboard_box_01": "caixa de papelão", "plastic_crate_01": "caixa plástica",
    "korean_fire_extinguisher_01": "extintor", "WetFloorSign_01": "placa de piso molhado",
    "hanging_industrial_lamp": "luminária pendente industrial",
    "mounted_fluorescent_lights": "luminária fluorescente", "security_light": "refletor de parede",
    "rollershutter_door": "porta de enrolar", "covered_car": "carro coberto com capa",
    "street_lamp_01": "poste de luz", "street_lamp_02": "poste de luz 2", "fire_hydrant": "hidrante",
    "concrete_road_barrier": "barreira de concreto", "utility_box_01": "caixa de energia",
    "water_manhole_cover": "tampa de bueiro", "metal_trash_can": "lixeira de metal",
    "potted_plant_01": "vaso de planta", "planter_box_01": "floreira",
    "modular_electricity_poles": "postes com fiação (modular)",
}
# Pacotes itch.io do Quaternius: (página, pasta, filtro, grande?)
QUAT = [
    ("https://quaternius.itch.io/lowpoly-cars", "carros", None, False),
    ("https://quaternius.itch.io/lowpoly-modular-street", "rua_modular", None, False),
    ("https://quaternius.itch.io/downtown-city-megakit", "downtown_city", r"Standard", True),
]
# OpenGameArt: (página, arquivo, pasta destino, licença conferida na página)
OGA = [
    ("https://opengameart.org/content/city-kit-roads",
     "https://opengameart.org/sites/default/files/kenney_city-kit-roads_2.2.zip", "modelos/kenney/city_kit_roads", "CC0"),
    ("https://opengameart.org/content/car-sound-effects-pack-low-quality",
     "https://opengameart.org/sites/default/files/car_sound_effects_pack.zip", "sons/carro", "CC0"),
    ("https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx",
     "https://opengameart.org/sites/default/files/sfx_breaking_and_falling.zip", "sons/impactos", "CC0"),
] + [("https://opengameart.org/content/mechanical-sounds",
      f"https://opengameart.org/sites/default/files/{n}", "sons/mecanicos", "CC0")
     for n in ("clank1.wav", "lightclunk1.wav", "lightclunk2.wav", "mechanical1.wav", "mechanical2.wav",
               "rattle1.wav", "squeakyclick1.wav")]
# Google Fonts (OFL 1.1): arquivo no repositório google/fonts
FONTES = {
    "Anton-Regular.ttf": "ofl/anton/Anton-Regular.ttf",
    "BebasNeue-Regular.ttf": "ofl/bebasneue/BebasNeue-Regular.ttf",
    "Montserrat[wght].ttf": "ofl/montserrat/Montserrat%5Bwght%5D.ttf",
    "Oswald[wght].ttf": "ofl/oswald/Oswald%5Bwght%5D.ttf",
    "BarlowCondensed-ExtraBold.ttf": "ofl/barlowcondensed/BarlowCondensed-ExtraBold.ttf",
    "RobotoMono[wght].ttf": "ofl/robotomono/RobotoMono%5Bwght%5D.ttf",
}


# ------------------------------------------------------------------ util
def jget(url):
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception as e:
            err = e
            time.sleep(2)
    raise err


def baixar(url, dest, tam=None):
    """Baixa url -> dest (pula se já existe com o tamanho certo). Devolve True se baixou/existe."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0 and (not tam or os.path.getsize(dest) == tam):
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(["curl", "-sSfL", "--retry", "3", "-A", UA["User-Agent"], "-o", dest + ".part", url])
    if r.returncode != 0:
        print("  FALHOU:", url)
        if os.path.exists(dest + ".part"):
            os.remove(dest + ".part")
        return False
    with open(dest + ".part", "rb") as f:
        ini = f.read(64)
    if b"<!DOCTYPE html" in ini or b"<html" in ini.lower():
        print("  BLOQUEADO (veio HTML):", url)
        os.remove(dest + ".part")
        return False
    os.replace(dest + ".part", dest)
    print("  ok", os.path.relpath(dest, RAIZ))
    return True


REG = []   # (categoria, nome, uso, origem, url, licença)


# ------------------------------------------------------------------ partes
def hdri():
    for k, (uso, res) in HDRIS.items():
        f = jget("https://api.polyhaven.com/files/" + k)["hdri"]
        for r in res:
            d = f[r]["hdr"]
            baixar(d["url"], os.path.join(A, "hdri", f"{k}_{r}.hdr"), d["size"])
        baixar(f"https://cdn.polyhaven.com/asset_img/thumbs/{k}.png?width=256",
               os.path.join(A, "_miniaturas", f"hdri_{k}.png"))
        REG.append(("HDRI", k, uso, "Poly Haven", f"https://polyhaven.com/a/{k}", "CC0"))


def texturas():
    for k, uso in TEX_PH.items():
        f = jget("https://api.polyhaven.com/files/" + k)
        pasta = os.path.join(A, "texturas", k)
        for mapa, nome in (("Diffuse", "cor"), ("Rough", "rugosidade"), ("nor_gl", "normal")):
            d = f[mapa]["1k"]["jpg"]
            baixar(d["url"], os.path.join(pasta, f"{nome}.jpg"), d["size"])
        baixar(f"https://cdn.polyhaven.com/asset_img/thumbs/{k}.png?width=256",
               os.path.join(A, "_miniaturas", f"tex_{k}.png"))
        REG.append(("Textura", k, uso, "Poly Haven", f"https://polyhaven.com/a/{k}", "CC0"))
    for k, uso in TEX_ACG.items():
        pasta = os.path.join(A, "texturas", k)
        if not os.path.exists(os.path.join(pasta, "cor.jpg")):
            z = os.path.join(A, "_tmp", f"{k}_1K-JPG.zip")
            if baixar(f"https://ambientcg.com/get?file={k}_1K-JPG.zip", z):
                os.makedirs(pasta, exist_ok=True)
                with zipfile.ZipFile(z) as zf:
                    for n in zf.namelist():
                        for suf, nome in (("_Color.jpg", "cor"), ("_Roughness.jpg", "rugosidade"),
                                          ("_NormalGL.jpg", "normal"), ("_Metalness.jpg", "metal"),
                                          ("_Opacity.jpg", "opacidade")):
                            if n.endswith(suf) and "/" not in n:
                                with zf.open(n) as s, open(os.path.join(pasta, nome + ".jpg"), "wb") as o:
                                    shutil.copyfileobj(s, o)
                os.remove(z)
        baixar(f"https://acg-media.struffelproductions.com/file/ambientCG-Web/media/thumbnail/256-PNG/{k}.png",
               os.path.join(A, "_miniaturas", f"tex_{k}.png"))
        REG.append(("Textura", k, uso, "ambientCG", f"https://ambientcg.com/view?id={k}", "CC0"))


def modelos():
    for k, uso in MOD_PH.items():
        f = jget("https://api.polyhaven.com/files/" + k)["gltf"]["1k"]["gltf"]
        pasta = os.path.join(A, "modelos", "polyhaven", k)
        baixar(f["url"], os.path.join(pasta, os.path.basename(f["url"])), f["size"])
        for rel, d in f["include"].items():
            baixar(d["url"], os.path.join(pasta, rel), d["size"])
        baixar(f"https://cdn.polyhaven.com/asset_img/thumbs/{k}.png?width=256",
               os.path.join(A, "_miniaturas", f"mod_{k}.png"))
        REG.append(("Modelo", k, uso, "Poly Haven", f"https://polyhaven.com/a/{k}", "CC0"))
    for pagina, pasta, filtro, grande in QUAT:
        if grande and not os.environ.get("GRANDES"):
            REG.append(("Pacote", "quaternius/" + pasta, "NÃO baixado (grande; rode com GRANDES=1)",
                        "Quaternius (itch.io)", pagina, "CC0"))
            continue
        dz = os.path.join(A, "modelos", "quaternius", pasta)
        if not os.path.isdir(dz) or not os.listdir(dz):
            zdir = os.path.join(A, "_tmp", "q_" + pasta)
            args = [sys.executable, "-I", os.path.join(RAIZ, "scripts", "itch_baixar.py"), pagina, zdir]
            if filtro:
                args.append(filtro)
            subprocess.run(args, check=False)
            for z in sorted(os.listdir(zdir)) if os.path.isdir(zdir) else []:
                if z.endswith(".zip"):
                    with zipfile.ZipFile(os.path.join(zdir, z)) as zf:
                        zf.extractall(dz)
            shutil.rmtree(zdir, ignore_errors=True)
        REG.append(("Pacote", "quaternius/" + pasta, "veículos/rua low-poly", "Quaternius (itch.io)", pagina, "CC0"))
    for pagina, url, destino, lic in OGA:
        if not destino.startswith("modelos"):
            continue
        _oga(pagina, url, destino, lic, "Kenney City Kit Roads (ruas, cones, barreiras, placas)")


def _oga(pagina, url, destino, lic, uso):
    dz = os.path.join(A, destino)
    nome = os.path.basename(url)
    if nome.endswith(".zip"):
        marca = os.path.join(dz, ".ok_" + nome)
        if not os.path.exists(marca):
            z = os.path.join(A, "_tmp", nome)
            if baixar(url, z):
                with zipfile.ZipFile(z) as zf:
                    zf.extractall(dz)
                open(marca, "w").close()
                os.remove(z)
    else:
        baixar(url, os.path.join(dz, nome))
    REG.append(("Som" if destino.startswith("sons") else "Pacote", destino + "/" + nome, uso,
                "OpenGameArt", pagina, lic))


def sons():
    usos = {"sons/carro": "carro: motor, partida, porta, buzina, freio",
            "sons/impactos": "quebrar/cair/bater", "sons/mecanicos": "clique, catraca, metal"}
    for pagina, url, destino, lic in OGA:
        if destino.startswith("sons"):
            _oga(pagina, url, destino, lic, usos.get(destino, ""))


def fontes():
    for nome, rel in FONTES.items():
        baixar("https://raw.githubusercontent.com/google/fonts/main/" + rel, os.path.join(A, "fontes", nome))
        lic = "Apache 2.0" if rel.startswith("apache") else "SIL OFL 1.1"
        REG.append(("Fonte", nome, "texto na tela", "Google Fonts",
                    "https://github.com/google/fonts/tree/main/" + os.path.dirname(rel), lic))


def tamanho(p):
    t = 0
    for r, _, fs in os.walk(p):
        t += sum(os.path.getsize(os.path.join(r, f)) for f in fs)
    return t


PASTAS = ("hdri", "texturas", "modelos", "sons", "fontes", "_miniaturas")
MARCA = "<!-- fim da parte gerada por scripts/baixar_assets.py -->"


def licencas():
    linhas = [
        "# Licenças da biblioteca de assets", "",
        f"Gerado por `scripts/baixar_assets.py` em {HOJE}. Os binários não vão para o git; rode "
        "`bash scripts/baixar_assets.sh` para baixar de novo.", "",
        "**Resumo das licenças**", "",
        "- **CC0 1.0 (domínio público)**: Poly Haven (https://polyhaven.com/license), ambientCG "
        "(https://docs.ambientcg.com/license/), Quaternius (página de cada pacote no itch.io e "
        "https://quaternius.com/license.html), Kenney (página do OpenGameArt) e os sons do OpenGameArt listados. "
        "Uso comercial livre, sem atribuição obrigatória (dar crédito é cortesia).",
        "- **SIL OFL 1.1 / Apache 2.0**: fontes de texto do Google Fonts. Uso comercial livre, inclusive em vídeo; "
        "só não se pode vender a fonte em si.", "",
        "| Tipo | Item | Uso no canal | Origem | URL | Licença | Data |", "|---|---|---|---|---|---|---|"]
    for cat, nome, uso, ori, url, lic in REG:
        linhas.append(f"| {cat} | {nome} | {uso} | {ori} | {url} | {lic} | {HOJE} |")
    linhas += ["", "## Fontes testadas e bloqueadas nesta rede", "",
               "- quaternius.com → Google Drive: \"Quota exceeded\" em todos os arquivos (usado o espelho itch.io).",
               "- kenney.nl: 403 (usado o espelho do OpenGameArt). poly.pizza: 403. freesound, pixabay, sonniss: 403.",
               "- github.com/…/raw: 403 (usado raw.githubusercontent.com).", "",
               "Tamanho desta biblioteca (hdri, texturas, modelos, sons, fontes, miniaturas): "
               f"{sum(tamanho(os.path.join(A, d)) for d in PASTAS) / 1e6:.0f} MB.", "", MARCA,
               "Abaixo desta linha o texto é mantido entre execuções (outros itens adicionados à mão ou por outros "
               "scripts, como personagens/ e mocap/)."]
    arq = os.path.join(A, "LICENCAS.md")
    resto = ""
    if os.path.exists(arq):
        velho = open(arq).read()
        if MARCA in velho:
            resto = velho.split(MARCA, 1)[1].split("\n", 2)[-1] if velho.split(MARCA, 1)[1].count("\n") >= 2 else ""
        elif velho.strip():
            resto = "\n## Conteúdo anterior deste arquivo (preservado)\n\n" + velho
    with open(arq, "w") as f:
        f.write("\n".join(linhas) + "\n" + resto)


PARTES = {"hdri": hdri, "texturas": texturas, "modelos": modelos, "sons": sons, "fontes": fontes}

if __name__ == "__main__":
    pedidas = sys.argv[1:] or list(PARTES)
    for p in pedidas:
        print("==", p)
        try:
            PARTES[p]()
        except Exception as e:
            print("  ERRO em", p, e)
    shutil.rmtree(os.path.join(A, "_tmp"), ignore_errors=True)
    if set(pedidas) == set(PARTES):   # o LICENCAS.md só é refeito numa execução completa
        licencas()
    print("assets/:", round(tamanho(A) / 1e6), "MB")
