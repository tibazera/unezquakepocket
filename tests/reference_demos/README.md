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
