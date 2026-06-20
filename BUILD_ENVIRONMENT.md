# Ambiente de build baseline

**Fase:** 0 — Baseline e testes de regressão  
**Data:** 20 de junho de 2026  
**Revisão do engine:** `312a8ca6e13d6f64e70f8a251477743e33a02ff4` (`2.0.1`)  
**Estado:** baseline Linux reproduzido; baseline Windows disponível no CI e pendente de reprodução local.

## Princípios do baseline

- Nenhuma alteração de física, prediction, rede, demos ou input é permitida nesta fase.
- Builds de baseline usam os dois renderers atualmente habilitados: OpenGL clássico e OpenGL moderno.
- O código Vulkan presente no repositório não está habilitado pelo CMake atual e não faz parte deste baseline.
- Resultados de performance só podem ser comparados na mesma máquina, driver, resolução, renderer, configuração e demo.
- Runners compartilhados do GitHub Actions são adequados para validar compilação, mas não para gates rígidos de FPS/RAM.

## Dependências fixadas pelo repositório

| Dependência | Fonte de fixação |
|---|---|
| `qwprot` | submódulo em `c49bc4081dcefb5b81320dba2636f3ddf1ffb9cc` |
| `vcpkg` | submódulo em `65e691fcff8fbffe91a3cb7277074bd187b54779` |
| Bibliotecas estáticas Windows/macOS | manifesto `vcpkg.json` + revisão do submódulo |
| Bibliotecas dinâmicas Linux | sistema da distribuição; versões devem ser registradas por execução |

Inicialização obrigatória:

```shell
git submodule update --init --recursive
```

## Linux baseline reproduzido

### Host

| Item | Valor |
|---|---|
| Ambiente | WSL2, Arch Linux |
| Kernel | `6.6.114.1-microsoft-standard-WSL2` |
| Arquitetura | `x86_64` |
| Compilador | GCC `16.1.1 20260430` |
| CMake | `4.3.3` |
| Gerador | Unix Makefiles |
| Configuração | Release |
| Link Time Optimization | habilitado pelo projeto |
| SDL2 | `2.32.70` |

Dependências detectadas pelo CMake:

| Biblioteca | Versão |
|---|---:|
| expat | 2.8.1 |
| freetype2 | 26.6.20 |
| libjpeg | 3.1.4.1 |
| jansson | 2.15.0 |
| minizip | 1.3.2 |
| libpcre2-8 | 10.47 |
| libpng | 1.6.58 |
| SDL2 | 2.32.70 |
| libsndfile | 1.2.2 |
| speex | 1.2.1 |
| speexdsp | 1.2.1 |
| libcurl | 8.20.0 |
| zlib | 1.3.2 |

### Comandos

```shell
cmake -S . -B build-baseline-linux \
  -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DUSE_SYSTEM_LIBS=ON

cmake --build build-baseline-linux --parallel 8
```

### Resultado

| Item | Resultado |
|---|---|
| Build | aprovado |
| Executável | `build-baseline-linux/unezquake-linux-x86_64` |
| Formato | ELF 64-bit PIE, dinamicamente ligado, não removido de símbolos |
| Build ID | `ab7edf770774f9d192e284a0c37ec54ba87bb58b` |
| SHA-256 desta execução | `e3d862dd3e0bf6bf916ceee6f36e81f09951fb2e23de1c92f0a074a652452d9b` |

O hash é registro desta execução, não promessa de build bit-a-bit reproduzível entre hosts.

### Avisos observados

O build terminou com sucesso, mas produziu avisos preexistentes:

- descarte de `const` em `fs.c`, `hud_common.c`, `sv_user.c` e `gl_drawcall_wrappers.c`;
- variáveis definidas e não usadas em `config_manager.c`, `in_sdl2.c` e `glc_sky.c`;
- GCC `-Wstringop-overflow` em chamada de `SHA1Transform` a partir de `SHA1Update`.

Esses avisos foram registrados, mas não corrigidos antes da criação do baseline comportamental.

## Windows

### Ambiente oficial atual de CI

O workflow `.github/workflows/main.yml` define:

| Item | Valor |
|---|---|
| Runner | `windows-2025-vs2026` |
| Gerador | Visual Studio 18 2026 |
| Configure preset | `msbuild-x64` |
| Build preset | `msbuild-x64-release` |
| Triplet vcpkg | `x64-windows-static` |
| Artefato | `unezquake.exe` |
| CMake no workflow | série 4.2 |

Comandos equivalentes após bootstrap:

```powershell
powershell -File bootstrap.ps1
cmake --preset msbuild-x64
cmake --build --preset msbuild-x64-release
```

### Estado local

O host Windows usado nesta análise tem Git `2.54.0.windows.1`, mas não possui CMake, MSVC, Clang, GCC/MinGW ou Ninja disponíveis no `PATH`. O WSL também não possui o cross-compiler `x86_64-w64-mingw32-gcc`.

Assim:

- a compilação Windows continua coberta pelo workflow existente;
- a reprodução local Windows permanece pendente de um toolchain MSVC/Visual Studio compatível ou MinGW-w64;
- não se deve instalar ou alterar o ambiente global silenciosamente apenas para preencher o relatório.

## Baseline de execução pendente

O executável foi compilado, mas os benchmarks de `dm2`, `aerowalk` e `ztndm3` não podem ser produzidos apenas com o código GPL do engine. São necessários assets do Quake legalmente fornecidos pelo operador e demos de referência com licença/proveniência registrada.

Quando esses dados estiverem disponíveis, cada medição deverá registrar:

- hash do executável, PAKs, mapa, demo e config;
- renderer e resolução;
- GPU, driver, CPU, RAM e modo de energia;
- FPS mínimo, médio e máximo;
- percentis de frametime;
- memória máxima e CPU;
- tempos de inicialização e carregamento;
- temperatura/throttling para Android.

## Hooks existentes úteis

O engine atual já oferece:

- `timedemo` e `timedemo2`;
- saída de frames, tempo, FPS, frametime médio, desvio e piores frames;
- `demo_benchmarkdumps`, que acrescenta resultados a `timedemo.log`;
- screenshots e seleção de renderer/resolução por cvars/linha de comando.

O build normal ainda não exporta telemetria. A Fase 0 adiciona uma instrumentação
opt-in por `ENABLE_REGRESSION_HOOKS`, desabilitada por padrão e excluída do target
de produção. O build instrumentado exporta posição, velocidade, ângulos, estado
de movimento, arma e comandos por frame em JSONL.

## Próximo gate

Antes de declarar a Fase 0 concluída:

1. obter assets e demos de referência com proveniência;
2. reproduzir o build Windows;
3. implementar e validar o `DemoRegressionRunner` determinístico;
4. capturar baseline de movimento, rede, render, input e benchmark;
5. configurar CI sem gates de performance em runners compartilhados;
6. executar os testes em Linux e Windows.
