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
| `motor3d/simready.py` | peças reais de carro da NVIDIA (motor, freio, suspensão, câmbio...; CC BY 4.0, crédito na descrição): guia e lista por tema em `motor3d/SIMREADY.md` |
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

**Pendente, nesta ordem:**
1. **Usuário aprovar** o nome (proposta: Raio-X do Motor, @raioxdomotor) e o estilo "Oficina de bolso".
2. **Prévia do estilo:** criar `motor3d/pecas_veiculos.py` (começar por `parafuso()`, `carro_chibi()`,
   `palco_oficina()`, `pneu_corte()`) e `videos/_estilo/mockup.py` com 3 quadros de teste, no molde de
   `videos/_estilo_b/mockup.py`. Mostrar ao usuário.
3. Roteiros têm 196–229 palavras (a regra diz 160–190; o roteiro de hábitos "soneca" tem 211 e fecha em ~70 s).
   Enxugar só se o usuário pedir ou se a narração gravada passar de 75 s.
4. Roteiro 01: a fonte do Departamento de Energia dos EUA foi citada por reportagens; conferir a página original.
5. Quando o usuário mandar o .srt de um roteiro: produzir o vídeo (skill `produzir-video-3d`).
6. Escrever os roteiros 05–10 da ordem em `referencias/02_pautas.md`, sempre com fonte.


Arquivos pesados (.blend, quadros, .wav e .mp4 gerados) não vão para o repositório.
