# Biblioteca de sons (todos CC0 — domínio público, uso comercial livre, sem atribuição obrigatória)

| Pasta | Arquivos | Origem (OpenGameArt) |
|---|---|---|
| transicao | wind1.wav, wind2.wav | https://opengameart.org/content/wind1 |
| aparecer | pop.ogg | https://opengameart.org/content/bubbles-pop |
| impacto_metal, impacto_madeira, rachadura, terra_pedras, tremor (thunder), maquina_broca, maquina_bomba, agua (loop_water), obra_ambiente | sfx100v2_*.ogg | https://opengameart.org/content/100-cc0-sfx-2 |
| impacto_grave (hit.wav), tremor (earthquake.wav), arrasto (scrape2.wav), agua (tap-water-1.wav), papel (pageturn1.wav, paper-sketchbook-page-flips-1.wav), sacola (crumples1.wav, crumples2.wav), borbulhar (kettle-boil.wav) | Owlish Media | https://opengameart.org/content/sound-effects-pack |

Uso no pipeline: `motor3d/sons.py` carrega estes arquivos por categoria; se a biblioteca faltar, cai para o som sintetizado.
Para trocar um som, basta substituir o arquivo na pasta (mesmo nome) ou ajustar o mapeamento em `motor3d/sons.py`.
