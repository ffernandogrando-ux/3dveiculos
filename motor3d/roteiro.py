"""Tempos tirados do .srt pela frase falada, para a cena se reajustar sozinha quando chegar uma gravação nova.

Cada palavra de uma legenda recebe um pedaço do tempo da linha, proporcional às sílabas. A cena pede o tempo de uma
frase em vez de escrever o número:

    R = Roteiro("roteiro.srt")
    R.t("um mês")                  # início da frase (1ª ocorrência)
    R.fim("a mancha volta inteira") # fim da frase
    R.t("vapor", depois=40)        # 1ª ocorrência depois de 40 s

A busca ignora acentos, maiúsculas e pontuação, troca números por extenso ("20" = "vinte") e aceita pequenas
diferenças de transcrição do CapCut (busca aproximada). Se não achar, o erro mostra o trecho mais parecido.
"""
import re, difflib, unicodedata

NUMEROS = {"0": "zero", "1": "um", "2": "dois", "3": "tres", "4": "quatro", "5": "cinco", "6": "seis", "7": "sete",
           "8": "oito", "9": "nove", "10": "dez", "15": "quinze", "20": "vinte", "30": "trinta"}


def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    w = re.sub(r"[^a-z0-9]", "", w)
    return NUMEROS.get(w, w)


def silabas(w):
    return max(1, len(re.findall(r"[aeiou]+", norm(w))))


def _ts(s):
    h, m, r = s.strip().split(":")
    sec, ms = r.replace(".", ",").split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def ler_srt(path):
    out = []
    for bloco in open(path, encoding="utf-8-sig").read().replace("\r", "").strip().split("\n\n"):
        L = [x for x in bloco.strip().split("\n") if x.strip()]
        i = next(j for j, x in enumerate(L) if "-->" in x)
        a, b = L[i].split("-->")
        out.append((_ts(a), _ts(b), " ".join(L[i + 1:])))
    return out


class Roteiro:
    def __init__(self, path):
        self.linhas = ler_srt(path)
        self.pal = []                       # (palavra normalizada, início, fim, nº da linha)
        for n, (a, b, txt) in enumerate(self.linhas, 1):
            ws = [w for w in txt.split() if norm(w)]
            pesos = [silabas(w) + 0.4 for w in ws]
            tot = sum(pesos) or 1
            t = a
            for w, p in zip(ws, pesos):
                d = (b - a) * p / tot
                self.pal.append((norm(w), t, t + d, n))
                t += d
        self.duracao = self.linhas[-1][1]

    def _busca(self, frase, depois=0.0, n=1):
        alvo = [norm(w) for w in frase.split() if norm(w)]
        k = len(alvo)
        seq = [p[0] for p in self.pal]
        achados = [i for i in range(len(seq) - k + 1) if seq[i:i + k] == alvo and self.pal[i][1] >= depois - 1e-6]
        if len(achados) >= n:
            return achados[n - 1], k
        # busca aproximada (transcrição diferente): melhor janela de k-1..k+1 palavras depois de `depois`
        ja = " ".join(alvo)
        melhor = (0.0, None, k)
        for kk in (k - 1, k, k + 1):
            if kk < 1:
                continue
            for i in range(len(seq) - kk + 1):
                if self.pal[i][1] < depois - 1e-6:
                    continue
                r = difflib.SequenceMatcher(None, ja, " ".join(seq[i:i + kk])).ratio()
                if r > melhor[0] + 1e-9:
                    melhor = (r, i, kk)
        if melhor[1] is not None and melhor[0] >= 0.72 and n == 1:
            return melhor[1], melhor[2]
        perto = " ".join(seq[melhor[1]:melhor[1] + melhor[2]]) if melhor[1] is not None else "-"
        raise KeyError(f"frase não encontrada no .srt: '{frase}' (depois de {depois:.2f} s; mais parecido: '{perto}')")

    def t(self, frase, depois=0.0, n=1):
        i, _ = self._busca(frase, depois, n)
        return round(self.pal[i][1], 3)

    def fim(self, frase, depois=0.0, n=1):
        i, k = self._busca(frase, depois, n)
        return round(self.pal[i + k - 1][2], 3)

    def linha(self, frase, depois=0.0):
        """(início, fim) da legenda inteira onde a frase começa."""
        i, _ = self._busca(frase, depois)
        a, b, _ = self.linhas[self.pal[i][3] - 1]
        return a, b
