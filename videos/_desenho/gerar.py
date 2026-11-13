"""Gera desenho com Gemini (imagem). Uso: python gerar.py saida.png "prompt" [referencia.png ...]"""
import sys, json, base64, urllib.request
MOD = "gemini-3.1-flash-image"
saida, prompt, refs = sys.argv[1], sys.argv[2], sys.argv[3:]
parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(open(r, "rb").read()).decode()}} for r in refs]
body = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}}}
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MOD}:generateContent",
                             json.dumps(body).encode(), {"Content-Type": "application/json", "x-goog-api-key": "x"})
r = json.load(urllib.request.urlopen(req, timeout=300))
for p in r["candidates"][0]["content"]["parts"]:
    if "inlineData" in p:
        open(saida, "wb").write(base64.b64decode(p["inlineData"]["data"])); print("ok", saida); break
else:
    print(json.dumps(r)[:800])
