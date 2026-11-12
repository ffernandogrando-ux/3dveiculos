"""Baixa os arquivos gratuitos (preço 0 / "pague o quanto quiser") de uma página do itch.io, sem login.

    python3 -I scripts/itch_baixar.py <url-da-pagina> <pasta-destino> [filtro-regex]
    python3 -I scripts/itch_baixar.py https://quaternius.itch.io/lowpoly-cars assets/modelos/quaternius/_zip

Sem pasta-destino só lista os arquivos. Pula arquivos que já existem com o mesmo tamanho (idempotente).
Usado pelo scripts/baixar_assets.sh para os pacotes CC0 do Quaternius (o Google Drive do site dá "Quota exceeded").
"""
import sys, os, re, json, urllib.request, urllib.parse, http.cookiejar

jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
op.addheaders = [("User-Agent", "Mozilla/5.0 (assets-script)")]


def get(u, data=None):
    req = urllib.request.Request(u, data=urllib.parse.urlencode(data).encode() if data else None)
    return op.open(req, timeout=300).read()


def main():
    page = sys.argv[1].rstrip("/")
    dest = sys.argv[2] if len(sys.argv) > 2 else None
    filtro = re.compile(sys.argv[3], re.I) if len(sys.argv) > 3 else None
    h = get(page).decode()
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', h).group(1)
    u = json.loads(get(page + "/download_url", {"csrf_token": csrf}))["url"]
    h2 = get(u).decode()
    ups = re.findall(r'data-upload_id="(\d+)".*?<strong class="name" title="([^"]+)"', h2, re.S)
    for uid, nome in ups:
        if filtro and not filtro.search(nome):
            continue
        if not dest:
            print(uid, nome)
            continue
        os.makedirs(dest, exist_ok=True)
        alvo = os.path.join(dest, nome.replace("/", "_"))
        r = json.loads(get(f"{page}/file/{uid}?source=view_game&as_props=1&after_download_lightbox=true",
                           {"csrf_token": csrf}))
        url = r["url"]
        with op.open(url, timeout=600) as resp:
            tam = int(resp.headers.get("Content-Length") or 0)
            if os.path.exists(alvo) and tam and os.path.getsize(alvo) == tam:
                print("ja existe:", alvo)
                continue
            with open(alvo + ".part", "wb") as f:
                while True:
                    b = resp.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
        os.replace(alvo + ".part", alvo)
        print("baixado:", alvo, os.path.getsize(alvo))


if __name__ == "__main__":
    main()
