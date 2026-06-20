# Fase 0 — regressão e benchmark

## Separação de responsabilidades

- `DemoRegressionRunner` verifica estado competitivo determinístico.
- `BenchmarkRunner` verifica performance, que depende do hardware.
- Comparação de screenshots será um gate separado por renderer e resolução.
- Testes de rede usarão servidor local controlado; não dependerão de servidores públicos.

Performance nunca substitui equivalência comportamental. Um build mais rápido que
diverge em movimento, comandos, demos ou eventos deve falhar.

## Build instrumentado

```shell
cmake -S . -B build-regression \
  -DCMAKE_BUILD_TYPE=Release \
  -DUSE_SYSTEM_LIBS=ON \
  -DENABLE_REGRESSION_HOOKS=ON
cmake --build build-regression --parallel
```

`ENABLE_REGRESSION_HOOKS` é `OFF` por padrão. Quando desabilitado,
`demo_regression.c` não entra no target e as chamadas também são removidas pelo
pré-processador.

## Telemetria

Com o build instrumentado:

```text
demo_regression_start telemetry.jsonl
timedemo2 reference.mvd 308
demo_regression_stop
```

Cada amostra registra:

- sequência e tempo da demo;
- posição, velocidade e ângulos simulados;
- estado de chão e água;
- arma e frame da arma;
- movimento, botões, impulso, ataque e pulo do `usercmd`.

Captura de baseline:

```shell
python tools/regression/demo_regression_runner.py capture \
  --baseline tests/baseline.json \
  --demo-id movement-bunnyhop \
  telemetry.jsonl
```

Comparação com tolerância máxima de 0,1%:

```shell
python tools/regression/demo_regression_runner.py compare \
  --baseline tests/baseline.json \
  --demo-id movement-bunnyhop \
  --tolerance 0.001 \
  telemetry.jsonl
```

O subcomando `run` também pode iniciar o cliente, capturar e encerrar ao fim da
demo. Ele requer o executável instrumentado e um diretório Quake fornecido
legalmente.

## Benchmark

O parser converte a saída textual existente de `timedemo` em JSON:

```shell
python tools/regression/benchmark_runner.py parse timedemo.txt \
  --output benchmark_report.json
```

O comparador aplica os limites da especificação:

```shell
python tools/regression/benchmark_runner.py compare \
  baseline_benchmark.json benchmark_report.json \
  --max-fps-drop 0.10 \
  --max-ram-growth 0.15
```

O gate de RAM só é aplicado quando ambos os relatórios contêm
`memory.peak_rss_bytes`. Gates de performance devem rodar em hardware dedicado,
não em runners compartilhados.

## Screenshots

Capturas de regressão devem usar `sshot_format tga`. Isso permite comparação
sem bibliotecas externas e evita diferenças de encoder/compressão PNG:

```shell
python tools/regression/screenshot_compare.py \
  reference.tga candidate.tga \
  --maximum-difference 0.01 \
  --report screenshot_report.json
```

O gate usa a diferença absoluta média dos canais RGB normalizada em 0–1. O
relatório também registra maior diferença de canal e proporção de pixels
alterados. Referências são específicas por renderer, resolução, mapa e config.

## Testes das ferramentas

```shell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Dados ainda necessários

`tests/reference_demos/manifest.json` mantém slots explícitos para a cobertura
obrigatória, mas nenhum arquivo sem origem/licença conhecida é incluído. O CI
valida o schema agora; `--require-files` será ativado quando o conjunto estiver
legalmente completo.
