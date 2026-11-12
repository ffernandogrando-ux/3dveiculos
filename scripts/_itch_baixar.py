"""Baixa os arquivos gratuitos ("name your own price", mínimo 0) de uma página do itch.io, como o botão
"No thanks, just take me to the downloads". Uso: python _itch_baixar.py <url_do_jogo> <pasta> [regex_do_nome]"""
import sys, re, json, os, urllib.request, urllib.parse, http.cookiejar

url, pasta = sys.argv[1].rstrip("/"), sys.argv[2]
filtro = re.compile(sys.argv[3] if len(sys.argv) > 3 else ".")
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [("User-Agent", "Mozilla/5.0")]
html = op.open(url, timeout=60).read().decode("utf-8", "replace")
tok = re.search(r'csrf_token" value="([^"]+)"', html).group(1)
# lista de uploads (na página do jogo: div.upload com o nome; o id vem do botão da página de download)
r = json.load(op.open(urllib.request.Request(url + "/download_url", data=urllib.parse.urlencode({"csrf_token": tok}).encode(),
                                             headers={"X-Requested-With": "XMLHttpRequest"}), timeout=60))
pg = op.open(r["url"], timeout=60).read().decode("utf-8", "replace")
ups = re.findall(r'data-upload_id="(\d+)".*?title="([^"]+)"', pg)
os.makedirs(pasta, exist_ok=True)
for uid, nome in ups:
    if not filtro.search(nome):
        continue
    dest = os.path.join(pasta, nome)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print("já existe:", nome); continue
    req = urllib.request.Request(f"{url}/file/{uid}?source=view_game&as_props=1&after_download_lightbox=true",
                                 data=urllib.parse.urlencode({"csrf_token": tok}).encode(),
                                 headers={"X-Requested-With": "XMLHttpRequest"})
    j = json.load(op.open(req, timeout=60))
    if "url" not in j:
        print("sem acesso:", nome, j); continue
    with op.open(j["url"], timeout=600) as f, open(dest + ".part", "wb") as o:
        while b := f.read(1 << 20):
            o.write(b)
    os.replace(dest + ".part", dest)
    print("baixado:", nome, os.path.getsize(dest))
