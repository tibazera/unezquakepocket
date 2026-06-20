# Demos de referência

Este diretório não inclui conteúdo proprietário nem demos de terceiros sem
proveniência. Preencha `manifest.json` com arquivo, SHA-256, origem e licença
antes de promover uma demo a baseline.

Validação estrutural, permitindo entradas ainda não preenchidas:

```shell
python tools/regression/demo_regression_runner.py verify-manifest tests/reference_demos/manifest.json
```

Validação usada quando o conjunto estiver completo:

```shell
python tools/regression/demo_regression_runner.py verify-manifest tests/reference_demos/manifest.json --require-files
```

As demos devem cobrir bunnyhop, circle jump, strafe jump, ramp jump, rocket
jump, shaft tracking, teamplay, spectator e MVD. PAKs e mapas comerciais nunca
devem ser adicionados ao Git.

## Smoke demo gerada localmente

O comando instrumentado `demo_regression_generate_reference` cria uma QWD curta
em `e1m1`, aguardando o servidor local ficar ativo antes de gravar uma sequência
de input por frames. O arquivo gerado e o PAK shareware permanecem em
`tests/data/`, ignorado pelo Git. Essa demo valida o pipeline de captura; ela
não substitui demos competitivas reais nos mapas obrigatórios.

Preparação local do PAK shareware 1.06, após leitura e aceite da licença:

```shell
python tools/regression/fetch_reference_data.py --accept-shareware-license
```

O download completo é verificado por SHA-256 antes da extração. `pak0.pak`, o
ZIP e os textos de licença ficam em `tests/data/`, que é ignorado pelo Git.

```shell
python tools/regression/generate_reference_demo.py \
  --executable build-regression/unezquake \
  --quake-dir tests/data/quake \
  --output tests/data/phase0_shareware_e1m1.qwd
```
