# Fase 0 — Status

**Estado:** em andamento  
**Última atualização:** 20 de junho de 2026

## Concluído

- estudo de viabilidade e escolha formal do uNezQuake como base;
- submódulos inicializados nas revisões fixadas;
- build Linux Release normal reproduzido;
- build Linux Release instrumentado reproduzido;
- ambiente Linux e Windows documentado;
- telemetria opt-in de demos, excluída dos builds normais;
- `DemoRegressionRunner` com captura, hash e comparação a 0,1%;
- `BenchmarkRunner` com gates de queda de FPS e aumento de RAM;
- comparação de screenshots TGA com limite de 1%;
- manifesto de demos com proveniência/licença obrigatórias;
- testes unitários das ferramentas;
- workflow CI para ferramentas e build instrumentado.

## Verificado

- build normal Linux: aprovado;
- build instrumentado Linux: aprovado;
- testes Python: 7 aprovados;
- validação estrutural do manifesto: aprovada;
- `git diff --check`: aprovado.

## Pendente

- reprodução local Windows ou execução do novo workflow no GitHub;
- conjunto legal de PAK/mapas e demos de referência;
- baseline real de `dm2`, `aerowalk` e `ztndm3`;
- captura de CPU, RAM, carregamento e inicialização;
- cenários automatizados de conexão, reconexão, timeout, spectator e troca de mapa;
- referências visuais por renderer e resolução;
- testes físicos de mouse, teclado, USB e Bluetooth.

## Riscos ativos

- runners compartilhados não são estáveis para gates de performance;
- telemetria ainda precisa ser validada contra demos QWD/MVD reais;
- o aviso GCC em `SHA1Transform` permanece sem alteração até triagem isolada;
- nenhum dado proprietário deve entrar no histórico Git.

## Próxima execução automática

Quando dados forem disponibilizados em `tests/reference_demos`, o manifesto deve
ser preenchido com SHA-256, origem e licença. O CI poderá então trocar a validação
para `--require-files`, capturar `tests/baseline.json` e ativar os gates de
movimento/renderização. Até lá, o desenvolvimento permanece na Fase 0 e não
refatora o núcleo competitivo.
