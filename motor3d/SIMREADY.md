# Modelos 3D prontos da NVIDIA (SimReady Assets)

Coleção aberta com cerca de 2.700 objetos 3D reais (peças de carro, ferramentas, cozinha, banheiro, hospital,
armazém, máquinas...), publicada pela NVIDIA no Hugging Face em outubro de 2026:
https://huggingface.co/datasets/nvidia/simready-assets

- **Licença CC BY 4.0:** pode usar em vídeo monetizado, mas o **crédito na descrição do post é obrigatório**.
  `simready.creditos()` devolve o texto pronto, com os assets usados na cena.
- **Formato:** OpenUSD com materiais PBR. O `motor3d/simready.py` baixa, importa no Blender, simplifica a malha e encaixa no chão.
- **Peso:** de 0,3 a 2 GB por objeto no original (texturas 4K). O download pula o que o Blender não usa e fica em
  `~/.cache/simready` (fora do git). O primeiro uso de cada objeto leva de 20 s a 1 min.
- **Custo no render** (teste de 13/11/2026, cena com motor V8 + freio, 576x1024, Cycles 4 amostras):
  0,73 → 0,90 s/quadro no estilo lowpoly e 1,00 s/quadro no realista, cerca de +8 a +12 min num vídeo de 70 s.

## Uso numa cena
```python
import simready as sr
motor = sr.importar("engineAssembly_v8_engine_a01", estilo="lowpoly", altura=0.9, loc=(0, 0, 0.8), rot_z=0.4)
freio = sr.importar("brakeSystem_brakes_assembly_a01", altura=0.55, loc=(0.6, 0, 0.8), cores={"orange": "#E53935"})
mt.pop_in(motor, 2.0)        # o objeto devolvido é um Empty pai: anima como qualquer peça
print(sr.creditos())         # colar na descrição do post
```
- `estilo="lowpoly"` (padrão): cores chapadas e facetado, para combinar com o motor3d (low-poly). `cores` troca a cor por
  palavra do nome do material (`orange`, `black`, `chrome`, `steel`, `rubber`...).
- `estilo="realista"`: mantém os materiais metálicos/texturas da NVIDIA (texturas reduzidas a 1024 px).
- `tris=40000` (padrão) é o alvo de triângulos depois de simplificar; os originais têm de 100 mil a 1 milhão.
- `altura=` em unidades da cena (o original vem em metros, tamanho real).

## Linha de comando
```bash
PY=~/.venv-video/bin/python
$PY motor3d/simready.py buscar brake               # procura nomes (vários termos = todos precisam aparecer)
$PY motor3d/simready.py previa <nome> /tmp/p.png lowpoly   # imagem de prévia do objeto sozinho
$PY motor3d/simready.py glb <nome> saida.glb       # GLB leve (realista, ~3-5 MB) para Three.js
```

## O que serve para este canal
Este é o canal que mais aproveita a coleção: há peças reais de quase todos os sistemas do carro.
| Tema do vídeo | Busque por |
|---|---|
| Motor (esquentar parado, óleo, correia) | `engineAssembly_v8_engine`, `v6`, `v12`, `electric_engine`; `engineComponent_cylinder_piston`, `crankshaft`, `camshaft`, `timing_chain`, `belt_serpentine`, `oil_filter`, `oil_pan`, `oil_pump`, `spark_plug`, `turbocompressor`, `supercharger` |
| Freio | `brakeSystem_brakes_assembly`, `rotor`, `caliper`, `brake_pad`, `brake_booster`, `master_cylinder` |
| Suspensão e direção | `suspension_shock_absorber`, `coilover`, `control_arm`; `steeringSystem_steering_wheel`, `steering_gearbox`, `power_steering_pump`, `steering_tieRod` |
| Transmissão | `drivetrain_transmission_manual`, `transmission_auto`, `clutch_plate`, `differential`, `drive_shaft`, `axle_shaft` |
| Arrefecimento, escape, combustível, elétrica | `coolingSystem_radiator`, `thermostat`, `coolant_reservoir_tank`; `exhaustSystem_`; `fuelSystem_`; `electricalSystem_battery`, `alternator`, `starter` |
| Rodas, lataria, oficina | `wheelAssembly_`, `bodyPart_bumper_front`, `boot_lid`; `tireTool_`, `handTool_`, `powerTool_impact_wrench`, `vehicleSupport_`, `palletJack` |

Não há carro inteiro nem moto: o carro continua sendo o `carro_chibi()` do canal; os assets entram nos closes do
"mecanismo invisível" (corte do motor, disco de freio, pistão). Combina com o mascote Parafuso no estilo lowpoly.

Teste de importação: `SIMREADY_teste.jpg` (motor V8 e freio, lowpoly à esquerda e realista à direita).
