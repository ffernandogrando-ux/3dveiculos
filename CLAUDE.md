# Canal de VEÍCULOS: vídeos 3D verticais (9:16) no molde "Você conhece alguém que…?"

Este é o **canal de veículos** (carro, moto e, de vez em quando, caminhão, barco e jet ski). **Não é o 3Douro**
(casa e obra) **nem o canal de hábitos** (corpo e sono). Reaproveita o motor 3D (`motor3d/`), mas o tema, o tom e o
estilo visual são próprios.

## Leia antes de qualquer coisa
- `referencias/01_regras_do_roteiro.md`: as regras do roteiro deste canal.
- `referencias/02_pautas.md`: as pautas e a ordem dos vídeos.
- `referencias/03_identidade_e_estilo.md`: nome, plano de postagem e estilo ("Oficina de bolso", mascote Parafuso). **Ainda não
  foi aprovado pelo usuário.**

## Formato do roteiro (resumo)
"Você conhece alguém que [hábito com o veículo]?" → "Esse cara nem imagina o que tá fazendo com o [motor/pneu/…]" →
"Olha só." → encenação do hábito → mecanismo invisível (corte do motor, pneu, corrente) com diminutivos e analogias
de casa → consequências no bolso e no dia a dia ("E tem mais", "Resultado", "e a conta vem…") → "e ainda acha que é
culpa de…" (do mecânico, da gasolina, do posto) → 1 a 3 objeções "Ah, mas…" (nunca mandar parar de usar: "Nada
disso!") → "O certo é simples…" → "Manda esse vídeo pra quem…" → "E aí, você…?". **Duração de 61 a 75 s**, com
160–190 palavras. Os fatos precisam de fonte (seção "Fontes"), de preferência o manual do fabricante ou órgão oficial.
**Sempre** lembrar que "o manual do seu veículo manda" quando o intervalo varia de modelo para modelo.

## Cuidados próprios do nicho
- Nada de ensinar manobra perigosa, burlar fiscalização, tirar equipamento de segurança ou mexer em freio/airbag.
- Nada de citar marca de combustível, óleo ou oficina como "a ruim". Pode citar o órgão (Inmetro, Denatran/Senatran,
  NHTSA) e o fabricante como fonte.
- Valores em R$ só como "pode passar de mil reais", nunca preço exato (muda rápido e gera briga nos comentários).

## Produção
- Responda em português. O usuário grava a narração, faz a legenda no CapCut e manda o .srt.
- Montagem: motor (`motor3d/`, guia `motor3d/LEIAME.md`) + peças do canal (a criar: `pecas_veiculos.py`). O passo a
  passo técnico da skill `produzir-video-3d` continua valendo; o estilo e o roteiro são os daqui.
- No vídeo entram etiquetas e ícones curtos (✓ ✗ ⚠ ? R$), o título "VOCÊ FAZ ISSO?" de 0 a ~4 s e o final em close do
  mascote com "?".
- Primeiro passo de qualquer sessão que vá renderizar: `bash scripts/instalar.sh`.



## Estrutura
| Pasta | Conteúdo |
|---|---|
| `referencias/01_regras_do_roteiro.md` | o molde adaptado a veículos (o que muda, vocabulário, equilíbrio de medo, checklist) |
| `referencias/02_pautas.md` | ~70 pautas por veículo e a ordem dos 10 primeiros vídeos |
| `referencias/03_identidade_e_estilo.md` | nome, bio, plano de postagem, estilo "Oficina de bolso" e a lista de peças 3D a criar |
| `referencias/base_habitos/` | análise do concorrente @construindo3d (feita para o canal de hábitos; é de onde vem o molde) |
| `roteiros/` | roteiros prontos do canal, com fontes |
| `motor3d/` | motor 3D (Blender/bpy). `pecas_habitos.py` (mascote Gota, palco micro) é o modelo para o `pecas_veiculos.py` |
| `videos/aterro_sanitario`, `mofo_*`, `ralo_esgoto` | **exemplos técnicos** de cenas prontas do motor (herança do 3Douro, outro formato) |
| `videos/_estilo_b/` | exemplo de prévia de estilo (`mockup.py` + quadros) feita para o canal de hábitos: modelo para a prévia deste canal |
| `biblioteca_sons/` | sons CC0 |
| `scripts/instalar.sh` | instala Blender/Python do motor |
| `.claude/skills/produzir-video-3d/` | passo a passo técnico de produção (cena → render → sons → MP4) |

## Onde paramos (atualize esta seção ao fim de cada sessão)
**Feito (11/11/2026):**
- Kit do canal: regras, pautas, identidade e estilo propostos (`referencias/`).
- 4 roteiros com fontes em `roteiros/`: 01 esquentar o carro parado · 02 calibrar só quando parece murcho ·
  03 corrente da moto seca · 04 jet ski guardado sem lavar por dentro.
- Motor 3D, sons e exemplos técnicos copiados do repositório 3DNOVO (canal de hábitos).

**Feito (12/11/2026):**
- Identidade v2 "Oficina de bolso" (mascote Parafuso) foi **REPROVADA** pelo usuário ("torto"). Ficou em
  `motor3d/pecas_veiculos.py` e `videos/_estilo/` só como histórico.
- **Estilo escolhido: 3D vinil com cores vivas** (direção A). Mascote humano **Zé, o mecânico**
  (`motor3d/boneco.py`): corpo inteiriço (Skin+Subsurf) com esqueleto próprio (`girar()`), rosto pintado no shader
  (nós Value animáveis), mãos por pose, boné laranja, macacão azul #1E5BFF. Sem bigode (evita lembrar o Mario).
- Veículos lisos de malha única: `motor3d/veiculos3.py` (`carro()`: hatch/popular/suv/picape/seda; `moto()`:
  street/cub/trail), cores vivas em `LATARIA`.
- Provas: `videos/_estilo3/` (`personagem_prova.py`, `veiculos_prova.py`, `quadros_teste.py` → quadros 9:16).
  Render: Standard (o AgX deixava pastel), oficina clara (parede #CFE6F2, rodapé amarelo).
- Revisado em 3 rodadas por diretor de arte + revisor técnico (agentes). Notas finais ~6,5–7,5.

**Feito (12/11/2026, tarde) — ESTILO ATUAL, preferido pelo usuário:**
- O vinil vivo foi achado **infantil**. Novo estilo **"adulto"** (prancha `videos/_estilo4/proposta_adulta.jpg`):
  - **Encenação:** Zé adulto (`motor3d/boneco_adulto.py`, `ze_adulto()`), ~40 anos, 6,5 cabeças, rosto com íris/barba,
    macacão azul-petróleo #1F4E79 + laranja; oficina real limpa (`oficina()`); veículos `estilo="real"` de
    `motor3d/veiculos3.py` (proporção real, pintura automotiva, sem rosto).
  - **Mecanismo invisível:** cena técnica escura de montadora (`motor3d/tecnico.py`: `pneu_corte`, `motor_corte`,
    `estudio_tecnico`, `callout_tela`); prova em `videos/_estilo4/mecanismo_prova.py` (~30–40 s/quadro 1080p).
  - Cenas técnicas prontas: pneu, motor, corrente da moto (`corrente_moto`), raio-X do carro (`carro_raio_x`);
    animação de teste `videos/_estilo4/teste_motor.mp4` (48 quadros 720p/16 amostras ≈ 15–18 s/quadro em CPU,
    medido com outros renders rodando junto) — `videos/_estilo4/cenas_tecnicas2.py`.
  - Zé adulto v2 com ajustes do diretor de arte (contrapposto, joelhos, bolsos, mãos, pálpebra, cabelo).
  - Ponto fraco: carros reais (hatch/SUV ainda com cara de perua); picape e motos ok.
  - Vinil vivo (`boneco.py`, `_estilo3/`) e Parafuso (`pecas_veiculos.py`, `_estilo/`) ficam só como histórico.

**Feito (12/11/2026, noite) — PRIMEIRO VÍDEO:**
- Vídeo 02 "calibrar o pneu" pronto: `videos/calibrar_pneu/saida/calibrar_pneu_9x16_com_efeitos.mp4` (66,2 s, narração
  ElevenLabs enviada pelo usuário). Fluxo novo, reutilizável: narração .wav → `faster-whisper` (venv no scratchpad;
  `palavras.json` = tempo de cada palavra) → `tempos.json` (14 planos) → `planos/*.py` (cada plano monta a própria
  cena e renderiza com numeração global, em paralelo; infra em `comum.py`, `_rua.py`, `_tec.py`) → `montar.py`
  (HUD do estilo adulto, efeitos sincronizados pelas palavras, mix com a narração, whip nas trocas rua ↔ técnico).
  Render ~2 h com 3–4 filas em CPU (12–16 amostras, 576×1024).
- Feedback do usuário na prévia: personagem e câmera **parados demais** → próximos vídeos: câmera viva (órbita,
  push-in forte, cortes a cada 1,5–2 s), mais cena técnica, personagem só em momentos curtos.
- Material livre baixado (CC0/OFL; binários fora do git, `scripts/baixar_assets.sh`, `assets/LICENCAS.md`):
  HDRIs, texturas PBR e modelos do Poly Haven/ambientCG, carros e rua Quaternius/Kenney, sons CC0, fontes;
  `motor3d/biblioteca.py` (`hdri`, `textura_pbr`, `importar_modelo`). Prova: `videos/_assets/prova_rua.png`.
- Teste de animação pronta (Quaternius + mocap CMU, `motor3d/animacao_pronta.py`) em andamento. Mixamo exige login
  do usuário (ele baixa os .fbx e envia).

**Feito (13/11/2026) — busca de estilo mais rápido:**
- Personagem: corpo contínuo Quaternius (`motor3d/personagem_q.py`, "cara": regata branca fechada, jeans, cinto,
  cabelo crespo curto, rosto limpo; original, nada de imitar personagem de jogo). Provas em `videos/_animacao_pronta/`.
- Testes de estilo: papel recortado 2D em PIL (`videos/_papel/`, ~0,6 s/quadro); câmera em terceira pessoa de jogo
  (`videos/_terceira/`: perseguição do carro → atrás do ombro → close; HUD próprio BOLSO/PNEU/MISSÃO; ~2,5 s/quadro).
  O usuário **gostou do movimento e do HUD**, achou o visual (filtro de desenho sobre o render) **ruim**; o carro
  subindo na calçada pode virar piada. Falta escolher o visual: low-poly estilizado (tipo vídeo ENEM) ou imagens IA.
- **ESTILO JOGO (atual, aprovado em teste):** câmera de terceira pessoa + HUD próprio (BOLSO/PNEU/MISSÃO/VISÃO
  RAIO-X), bairro brasileiro low-poly, cor chapada + contorno (`motor3d/estilo_jogo.py`: `bairro`, `chapar_cena`,
  `contornar_cena`), cabeça do "cara" 1,4× (Copy Scale no osso Head). Vídeo 02 refeito:
  `videos/calibrar_pneu_jogo/` (`cena.py` = rua, 2 filas ~45 min; raio-X reaproveita `calibrar_pneu/quadros`;
  `montar.py` = HUD, whip, som com ducking e -14 LUFS) → `saida/calibrar_pneu_jogo.mp4`.
- Gemini de imagem (`videos/_desenho/gerar.py`): a chave é do plano gratuito, cota 0 para imagem → precisa
  faturamento ativado pelo usuário.

**Pendente, nesta ordem:**
1. Lapidar o estilo adulto (Zé menos "manequim", carros sem cara de perua) e o usuário aprovar; aprovar o nome do canal.
2. Para animar 70 s (apontado pelo revisor): pneu com sulco + `girar_rodas()` com sinal por lado; todas as mãos
   pré-criadas com troca por `hide_render`; unificar materiais (`boneco` usa mt.mat, `veiculos3` usa vinil());
   perfil de render de vídeo (720p, 16 amostras) medido em 10 quadros.
3. Peças de corte no estilo novo: pneu em corte, motor em corte, corrente, raio-X.
3. Roteiros têm 196–229 palavras (a regra diz 160–190; o roteiro de hábitos "soneca" tem 211 e fecha em ~70 s).
   Enxugar só se o usuário pedir ou se a narração gravada passar de 75 s.
4. Roteiro 01: a fonte do Departamento de Energia dos EUA foi citada por reportagens; conferir a página original.
5. Quando o usuário mandar o .srt de um roteiro: produzir o vídeo (skill `produzir-video-3d`).
6. Escrever os roteiros 05–10 da ordem em `referencias/02_pautas.md`, sempre com fonte.


Arquivos pesados (.blend, quadros, .wav e .mp4 gerados) não vão para o repositório.
