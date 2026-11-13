# Motor 3D — vídeos explicativos verticais (9:16)

Cada vídeo é uma pasta com dois arquivos próprios; todo o resto vem deste motor.

| Arquivo | O que faz |
|---|---|
| `motor.py` | render, materiais (inclui mosaico de lixo, brita, prédio com janelas), peças (caixa, cilindro, tubo, seta, texto, prisma de perfil), terreno em corte com recortes, decoração, animações (pop, crescer, encher por chave de forma, mover, tremular, gotejar), céu (dia/noite, pôr do sol, chuva) e câmeras com cortes e tremor |
| `render.py` | quadros de teste (`stills`) e render por faixa de quadros (`range`, retomável) |
| `transicoes.py` | aplica as transições com desfoque nos cortes do `cortes.json` (e o efeito "rebobinar") e gera os MP4 |
| `sons.py` | efeitos (biblioteca CC0 em `../biblioteca_sons` + sintetizados) e mixador |
| `pecas.py` | catálogo de peças reutilizáveis (máquinas, prédio, poço, usina, animais, pessoa, fogo, jornal…) — veja `catalogo.jpg`; `catalogo.py` refaz a imagem |
| `pecas_esgoto.py` | peças de banheiro/esgoto do vídeo do ralo (vaso em corte, canos em corte com água, ralo, frascos, barata, rede da rua; `cortar_y` corta qualquer peça ao meio) — prévia em `videos/ralo_esgoto/previa_cenario.jpg`. Repete alguns nomes do banheiro de `pecas.py` com outros parâmetros: use um ou outro |
| `simready.py` | modelos 3D prontos da NVIDIA (SimReady, CC BY 4.0, ~2.700 objetos reais): baixa, importa no estilo lowpoly ou realista e gera o crédito — guia em `SIMREADY.md` |
| `benchmark.py` | teste comparativo de configurações de render |

## Fluxo de um vídeo novo
0. `bash scripts/instalar.sh` (na raiz do repositório) e use `PY=~/.venv-video/bin/python`.
1. Pasta nova `videos/<tema>/` com `roteiro.srt`, `cena.py` (história visual, tempos do .srt) e `efeitos.py` (lista de sons). Modelo: `videos/aterro_sanitario/`.
2. `$PY cena.py` → `<tema>.blend` + `cortes.json`.
3. Quadros de teste: `$PY motor3d/render.py stills <tema>.blend <pasta> 8 <t1> <t2> ...`
4. Render (o vídeo inteiro cabe numa tarefa só; duas metades em paralelo ganham ~5%): `$PY motor3d/render.py range <tema>.blend <pasta_quadros> 4 1 <último_quadro>`
5. `$PY efeitos.py` → `efeitos.wav`
6. `$PY motor3d/transicoes.py <pasta_quadros> videos/<tema>/cortes.json <saida> <tema> videos/<tema>/efeitos.wav`

Requisitos (venv): `bpy`, `numpy`, `scipy`, `pillow`, `shapely`; `ffmpeg` no sistema.

## Configuração de render (teste comparativo de 30/10/2026, 120 quadros da cena do aterro, CPU 4 núcleos, sem GPU)
| Configuração | s/quadro | Velocidade | Fidelidade (SSIM vs atual) | Vídeo de 70 s |
|---|---|---|---|---|
| Cycles 16 amostras (antigo padrão) | 4,22 | 1,0x | referência | ~2 h |
| **Cycles otimizado, 4 amostras (padrão atual)** | 1,47 | 2,9x | 0,994 | **~41 min** |
| Cycles otimizado, 8 amostras | 2,06 | 2,0x | 0,995 | ~58 min |
| EEVEE 4 amostras (software) | 3,23 | 1,3x | 0,983 (aparência muda) | ~1 h 30 |
| EEVEE 16 amostras (software) | 9,29 | 0,5x | 0,948 (aparência muda) | ~4 h 20 |

"Otimizado" = dados persistentes entre quadros, 3 rebatimentos (difuso/brilho/transmissão 1), sem cáusticas,
amostragem adaptativa e remoção de ruído OpenImageDenoise. Tudo isso já vem no `setup()` do motor.
Tempos de vídeo estimados pelo trecho testado, que é dos mais pesados (média real do aterro com 16 amostras: 3,7 s/quadro).
Material completo do teste: `teste_render/` (quadro lado a lado, vídeo comparativo e `resultados.json`).

Atualização 31/10/2026: o denoise passou para `denoising_quality = "FAST"` (cena do quarto do mofo: 5,6 → 2,4 s/quadro,
diferença média de 1,3/255 por pixel). Rodar dois renders em paralelo na mesma máquina ficou mais lento que um só.

Atualização 31/10/2026 (tarde, vídeo do banheiro, máquina mais lenta: o quarto do mofo deu 4,6 s/quadro): cena com prédio
de 5 andares, vapor translúcido e céu animado estava em 6,8 s/quadro. O custo era a amostragem de importância do céu
(refeita a cada quadro porque a cor do céu é animada) e a emissão dos materiais virando luz. Com
`world.cycles.sampling_method = "NONE"` e `emission_sampling = "NONE"` caiu para ~4 s/quadro, sem diferença visível.
Vídeo de 76 s ≈ 2 h: divida em duas tarefas de ~1 h (limite de 2 h por tarefa em segundo plano).

`roteiro.py`: tempos pela frase falada (`Roteiro("roteiro.srt").t("um mês")`), com busca aproximada para diferenças de
transcrição do CapCut. Use quando o roteiro é escrito antes da gravação: a cena se reajusta ao .srt real.
