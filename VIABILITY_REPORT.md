# UNEZQUAKE MOBILE NEXT-GEN — Relatório de Viabilidade

**Fase:** −1 — Estudo de viabilidade e reaproveitamento  
**Data da análise:** 20 de junho de 2026  
**Estado:** concluído para decisão de arquitetura; nenhuma implementação realizada  
**Decisão:** manter o uNezQuake como base do produto e reaproveitar componentes e padrões de FTEQW, vkQuake e SDL3 de forma seletiva.

## 1. Resumo executivo

A análise **não concluiu que partir do FTEQW Android seja significativamente mais eficiente** para o produto completo definido na especificação.

FTEQW é a base com maior cobertura de plataformas e já possui Android, Vulkan e uma trilha SDL3. Isso reduz o esforço para produzir um primeiro APK. Porém:

1. o caminho Android padrão do FTEQW é nativo (`sys_droid.c`, `gl_viddroid.c` e Java próprio), não a camada SDL3 solicitada;
2. o pacote Android presente no repositório é legado: `minSdkVersion=9`, `targetSdkVersion=24`, permissão antiga de armazenamento e ausência de um projeto Gradle moderno no código analisado;
3. FTEQW é outro cliente, com arquitetura, comandos, HUD, prediction, cvars e comportamento próprios;
4. portar os recursos do uNezQuake para FTEQW não preserva automaticamente o *feeling* competitivo nem a compatibilidade comportamental exigida;
5. o uNezQuake atual já herdou do ezQuake CMake, SDL2, OpenGL moderno e uma API de renderer. Seu backend Vulkan existente está incompleto/desativado, mas a base está mais avançada que a premissa de um cliente puramente OpenGL legado.

Consequentemente, FTEQW é recomendado como **fonte de soluções Android/Vulkan e referência arquitetural**, não como novo núcleo do produto.

### Decisão formal sobre a alternativa FTEQW

| Questão | Conclusão |
|---|---|
| FTEQW chega mais rápido a um APK inicial? | Sim. |
| Esse caminho já satisfaz Android 12 + SDL3 + arquitetura proposta? | Não. O caminho Android padrão é nativo e precisa modernização substancial. |
| Portar recursos uNezQuake para FTEQW preserva comportamento competitivo por construção? | Não. Exige port e regressão de todo o comportamento diferencial. |
| FTEQW reduz significativamente o esforço do produto completo? | Não. A economia inicial é consumida pela migração semântica e validação competitiva. |
| Alternativa escolhida? | **Não. Manter uNezQuake como base.** |

Este documento é o *gate* formal anterior à implementação. A próxima fase autorizável é a Fase 0; ela não foi iniciada durante esta análise.

## 2. Escopo e método

Foram inspecionadas as versões abaixo diretamente de seus repositórios:

| Projeto | Revisão analisada | Data da revisão | Papel na análise |
|---|---:|---:|---|
| [uNezQuake](https://github.com/dusty-qw/unezquake) | `312a8ca6` | 2026-06-19 | Base atual e comportamento-alvo |
| [ezQuake](https://github.com/ezQuake/ezquake-source) | `a86996a3` | 2026-06-16 | Base competitiva e upstream arquitetural |
| [FTEQW](https://github.com/fte-team/fteqw) | `f937b9d8` | 2026-06-04 | Android, SDL3, Vulkan e portabilidade |
| [vkQuake](https://github.com/Novum/vkQuake) | `9be3a5ad` | 2026-05-29 | Backend Vulkan e migração SDL3 |

Foram examinados estrutura de fontes, CMake/Meson, plataforma, input, renderização, Android, licenças e pontos de integração. Não foram executados benchmarks, APKs ou testes em dispositivos nesta fase; esses dados pertencem à Fase 0.

## 3. Estado real do uNezQuake

O repositório atual contém aproximadamente 547 arquivos sob `src/` e é um fork recente do ezQuake com alterações relevantes em prediction, movimento, input, HUD e regras competitivas.

### 3.1 Pontos favoráveis

- CMake multiplataforma já estabelecido.
- SDL2 centraliza janela, eventos, clipboard e parte da plataforma.
- OpenGL clássico e OpenGL moderno são backends selecionáveis.
- `renderer_api_t` expõe uma tabela de operações em `r_renderer_structure.h`, cobrindo mundo, HUD, partículas, sprites, texturas, buffers e framebuffers.
- Input competitivo, aliases, cvars, demos, MVD, QTV, HUD e configurações já estão no núcleo que se deseja preservar.
- Mouse relativo, botões adicionais, roda, joystick e filtragem de eventos touch-emulados já existem na implementação SDL2.

### 3.2 Dívidas e lacunas

- `vid_sdl2.c` tem cerca de 2.080 linhas e mistura janela, modos de vídeo, eventos, mouse e detalhes de renderer. A separação de plataforma/input ainda é parcial.
- `in_sdl2.c` tem cerca de 771 linhas e contém transformação de input diretamente ligada ao comando do jogador.
- Não existe projeto Android, JNI, Gradle ou empacotamento APK.
- Não existe SDL3 no build atual.
- Há 18 arquivos `vk_*`, mas o CMake não oferece opção Vulkan, não define `RENDERER_OPTION_VULKAN`, não liga o loader Vulkan e contém criação de contexto desativada/comentada. Portanto, isso deve ser tratado como **código parcial/dormente**, não como backend Vulkan funcional.
- Foram encontrados usos de OpenGL legado em 15 arquivos. A abstração atual ajuda, mas ainda não garante a regra “nenhuma chamada OpenGL fora do backend”.
- Os submódulos `qwprot` e `vcpkg` não estavam inicializados no clone durante a inspeção. Isso deve ser normalizado na Fase 0 antes do baseline.

## 4. Comparação de arquitetura

### 4.1 Modularidade e acoplamento

| Projeto | Pontos fortes | Limitações | Avaliação para este produto |
|---|---|---|---|
| uNezQuake | API de renderer; OpenGL clássico/moderno; CMake; núcleo competitivo desejado | Janela e input concentrados em arquivos SDL2 grandes; Vulkan dormente | **Melhor base funcional** porque minimiza alteração do comportamento protegido |
| ezQuake | Arquitetura madura para QW competitivo; renderer e CMake equivalentes à origem do fork | Sem Android e ainda SDL2; não contém as diferenças recentes do uNezQuake | Boa referência e upstream, mas voltar a ele cria trabalho de reaplicação |
| FTEQW | Maior amplitude de plataforma; registro de renderers; OpenGL, Vulkan e múltiplos sistemas; Android nativo | Muitos caminhos condicionais, grande superfície multi-engine/multi-protocolo e maior complexidade | **Mais modular em cobertura**, mas não é o núcleo comportamental desejado |
| vkQuake | Renderer Vulkan maduro e focado; SDL2/SDL3 selecionável; pipeline moderno | É cliente NetQuake/QuakeSpasm, não QuakeWorld; renderer fortemente adaptado ao seu modelo interno | Melhor referência Vulkan, inadequado como base do cliente |

**Resposta direta:** FTEQW possui a arquitetura mais abrangente e a melhor separação de renderers/plataformas em termos absolutos. Para o objetivo específico — preservar integralmente o uNezQuake competitivo — o menor acoplamento de risco é obtido mantendo o uNezQuake e fortalecendo as fronteiras já existentes.

### 4.2 Separação de rendering

- **uNezQuake/ezQuake:** tabela `renderer_api_t` com operações de alto nível. É uma boa costura para evoluir, embora alguns tipos e nomes ainda carreguem herança OpenGL.
- **FTEQW:** registro por `rendererinfo_t` e suporte simultâneo a vários backends/plataformas. É o desenho mais flexível dos quatro, mas possui condicionais `GLQUAKE`/`VKQUAKE` espalhadas pela camada compartilhada.
- **vkQuake:** backend Vulkan mais completo, incluindo render passes, sincronização, descritores, buffers, pipelines, compute e cache/gestão de recursos. Sua integração é profunda com estruturas do QuakeSpasm, portanto não é copiável como módulo fechado.

## 5. Android

### 5.1 Suporte encontrado

| Projeto | Android existente | Implementação | Situação |
|---|---|---|---|
| uNezQuake | Não | — | Requer bootstrap |
| ezQuake | Não | — | Requer bootstrap |
| FTEQW | Sim | Activity/NativeActivity Java, JNI, `SurfaceView`, áudio e vídeo nativos, CMake como biblioteca compartilhada | Funcional como referência, mas legado para requisitos atuais |
| vkQuake | Não há projeto Android | SDL + Vulkan para desktop | Requer bootstrap |

O Android do FTEQW contém:

- `FTEDroidActivity.java` e `FTENativeActivity.java`;
- ponte JNI e biblioteca `ftedroid`;
- ciclo de vida de surface;
- eventos de teclado e `MotionEvent` multitouch;
- áudio Android nativo;
- configuração de botões touch;
- criação de surface Vulkan Android;
- associação de URIs/arquivos QTV, MVD, DEM, QWD, PAK, PK3 e BSP.

Entretanto, a configuração observada usa API mínima 9, target 24 e `WRITE_EXTERNAL_STORAGE`. Não foram encontrados `build.gradle`, `settings.gradle`, wrapper Gradle ou `Android.mk`. O caminho CMake padrão de Android escolhe `sys_droid.c`, `snd_droid.c` e `gl_viddroid.c`; a opção SDL3 é outro ramo de plataforma e vem desabilitada por padrão.

### 5.2 O que reaproveitar

Reaproveitamento recomendado do FTEQW:

- conceitos e casos de ciclo de vida Android;
- tratamento de perda/recriação de surface;
- mapeamento de URIs e intents de demos/QTV;
- catálogo de casos de teclado físico, mouse e multitouch;
- estratégia de criação de surface Vulkan;
- configuração declarativa de controles touch como referência de UX;
- casos de teste para pause/resume, foco e teclado virtual.

Não é recomendado copiar integralmente a Activity antiga. Para cumprir SDL3 e reduzir Java/JNI próprio, o bootstrap deve partir do projeto Android oficial do SDL3 e receber apenas os casos de uso validados no FTEQW.

## 6. Vulkan

### 6.1 Maturidade comparada

1. **vkQuake:** backend Vulkan mais maduro e focado em performance gráfica de Quake. É a principal referência técnica.
2. **FTEQW:** backend Vulkan amplo, integrado a Android e a múltiplos renderers; excelente referência de portabilidade, mas mais complexo.
3. **uNezQuake/ezQuake:** arquitetura e fontes parciais presentes, porém o backend não está habilitado pelo build atual e não deve ser considerado operacional.

### 6.2 Estratégia de reaproveitamento

Não se deve copiar o renderer do vkQuake ou FTEQW como bloco. As estruturas de mundo, materiais, HUD, partículas e recursos diferem. O reaproveitamento deve ocorrer por subsistemas:

- seleção de dispositivo e filas;
- criação de instance/device/swapchain;
- sincronização e frames em voo;
- allocator de buffers/imagens;
- upload/staging;
- descriptor pools/layouts;
- pipeline cache;
- compilação e organização de shaders;
- tratamento de resize/surface loss;
- instrumentação e nomes de debug.

O desenho deve conectar esses subsistemas à `renderer_api_t` do uNezQuake, preservando a produção de cena e os efeitos competitivos existentes.

## 7. SDL

### 7.1 Estado

- uNezQuake e ezQuake usam SDL2.
- FTEQW possui suporte condicional a SDL3 via CMake (`FTE_DEP_SDL3`), incluindo adaptações de vídeo, input, áudio e Vulkan. A opção alerta que alguns comportamentos específicos de plataforma são desativados.
- vkQuake possui opção Meson `use_sdl3` e arquivos específicos `in_sdl3.c` e `snd_sdl3.c`, mantendo SDL2 como padrão.

### 7.2 Recomendação

A migração uNezQuake SDL2 → SDL3 é menor e menos arriscada do que trocar o engine. FTEQW e vkQuake fornecem mapas concretos das mudanças de API, mas a camada nova deve ser escrita contra interfaces próprias (`PlatformSDL3` e `InputSDL3`) para não acoplar jogo e renderer ao SDL.

Antes da migração, os efeitos SDL atualmente concentrados em `vid_sdl2.c` devem ser separados sem alterar o processamento de `usercmd_t`. O tratamento competitivo de sensibilidade, aceleração e transformação do mouse permanece no núcleo até que testes demonstrem equivalência.

## 8. Input

| Requisito | uNezQuake atual | FTEQW | SDL3/Android proposto |
|---|---|---|---|
| Mouse relativo | Sim em SDL2 | Sim em SDL e Android nativo | SDL3 relative mouse + testes por dispositivo |
| Mouse absoluto | Sim para UI/cursor | Sim | SDL3 mouse/touch separados |
| Roda e múltiplos botões | Sim | Sim | Manter mapeamento uNezQuake |
| Teclado físico | Sim | Sim, inclusive Java Android | SDL3 key/scancode; validar F1–F12 e modificadores |
| USB/Bluetooth | Delegado ao SO/SDL no desktop | Eventos Android disponíveis | SDL3 fornece base; hotplug/reconexão precisam testes reais |
| Gamepad | Suporte existente | Suporte amplo | Migrar para SDL3 Gamepad API |
| Touch | Apenas filtragem de mouse sintetizado | Multitouch e botões configuráveis | Nova camada `InputAndroid` sobre eventos SDL3 |

Não há evidência suficiente para declarar suporte pronto a DeX, Desktop Mode, múltiplos monitores ou todas as combinações Bluetooth/USB em qualquer das quatro bases. Esses itens exigem matriz de dispositivos na Fase 0/9/12.

## 9. Licenciamento

Os quatro projetos analisados distribuem o engine sob GNU GPL versão 2. Em princípio, há compatibilidade para reutilização de código entre eles sob GPLv2, desde que:

- avisos de copyright e autoria sejam preservados;
- a origem de cada trecho adaptado seja registrada;
- o código-fonte correspondente e scripts de build sejam fornecidos ao distribuir binários/APKs;
- dependências e assets tenham licenças auditadas individualmente;
- conteúdo comercial do Quake não seja incluído no repositório ou APK sem autorização;
- bibliotecas Android, shaders e ferramentas incorporadas sejam registradas em `THIRD_PARTY_NOTICES`.

SDL usa licença zlib, compatível com GPL. Vulkan headers/loader e dependências adicionais devem ser confirmados nas versões efetivamente fixadas.

Esta é uma análise técnica de compatibilidade, não parecer jurídico. Antes de distribuição pública, recomenda-se revisão jurídica e uma varredura automatizada de licenças/SBOM.

## 10. Estimativa comparativa de esforço

Estimativas em **pessoa-semana**, com incerteza aproximada de ±40%, sem contar espera por aquisição de hardware, revisão de lojas ou produção de assets. Pressupõem engenheiros experientes em C, Quake, Android NDK, SDL e Vulkan.

| Entrega | uNezQuake como base | FTEQW como base + recursos uNezQuake |
|---|---:|---:|
| APK Android 12 abrindo menu | 6–10 | 3–6 |
| Cliente QW utilizável com mouse/teclado e SDL3 | 14–24 | 16–28 |
| Equivalência de configs, aliases, HUD, demos/MVD e comportamento uNezQuake | 8–14 adicionais | 24–40 adicionais |
| Vulkan compatível com aparência e HUD uNezQuake | 18–30 | 12–22 |
| Touch, DeX/desktop, monitores, UX mobile e hardening | 10–18 | 10–18 |
| Baseline, regressão, CI, benchmarks e documentação | 12–20 | 16–26 |
| **Programa completo, com sobreposição de atividades** | **58–98** | **74–124** |

FTEQW economiza aproximadamente 3–5 pessoa-semanas no bootstrap e potencialmente 6–8 no Vulkan, mas adiciona cerca de 16–26 pessoa-semanas de transplante/validação do comportamento diferencial. A vantagem inicial não é significativa no custo total e aumenta o risco principal do projeto.

As metas “120 FPS garantidos” e “240 FPS” não podem ser aceitas sem definir classes mínimas de SoC, resolução, qualidade, throttling e duração do teste. Devem se tornar metas por *hardware tier* na Fase 0.

## 11. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Alteração imperceptível de input/prediction virar diferença competitiva | Alta | Crítico | Baseline determinístico antes da refatoração; golden demos e telemetria de `usercmd` |
| SDL3 mudar scancodes, foco ou captura relativa no Android/DeX | Alta | Alto | Camada própria, testes físicos e logs de eventos brutos |
| Backend Vulkan parcial do uNezQuake induzir falsa sensação de avanço | Alta | Alto | Tratar como protótipo; inventário e teste de cobertura antes de reutilizar |
| Código Vulkan externo não encaixar nas estruturas uNezQuake | Alta | Alto | Reaproveitar subsistemas/padrões, não transplantar renderer inteiro |
| Fragmentação de drivers Vulkan Android | Alta | Alto | Baseline OpenGL ES/modern OpenGL como fallback e matriz de GPUs |
| Android moderno restringir filesystem e assets | Alta | Alto | Scoped storage/SAF, diretório app-specific e testes de importação de PAK/config/demo |
| Touch degradar competitividade ou conflitar com mouse | Média | Médio | Perfis separados e ocultação automática validada por eventos reais |
| Meta de FPS universal ser impossível | Alta | Alto | Definir tiers, resolução e cenário de benchmark |
| Licenças de assets/dependências | Média | Alto | SBOM, notices, auditoria e nenhum asset proprietário no APK |
| Escopo de 17 fases gerar grande caminho crítico | Alta | Alto | Gates mensuráveis e entregas verticais pequenas sem pular validações |

## 12. Vantagens e desvantagens das rotas

### Rota recomendada — uNezQuake como base

**Vantagens**

- Preserva por construção o núcleo competitivo e os diferenciais do produto.
- Menor risco para demos, MVD, configs, aliases, HUD e prediction.
- OpenGL moderno e uma API de renderer já existem.
- Facilita comparação binária/comportamental antes e depois de cada camada.
- Mantém relação clara com ezQuake e uNezQuake upstream.

**Desvantagens**

- Não há bootstrap Android.
- Migração SDL3 e separação de plataforma/input ainda são necessárias.
- Vulkan precisa ser reativado/reavaliado ou reconstruído por subsistemas.
- Arquivos SDL2 grandes exigem refatoração cuidadosa após o baseline.

### Rota alternativa — FTEQW Android como base

**Vantagens**

- Android, surface Vulkan, touch e JNI já têm implementações de referência.
- Renderer Vulkan e portabilidade são mais maduros.
- SDL3 já possui um caminho condicional.

**Desvantagens**

- Android existente não é o caminho SDL3 requerido e usa configuração legada.
- O primeiro APK não representa equivalência com uNezQuake.
- Requer portar extensa superfície de recursos e semântica competitiva.
- Aumenta fortemente o espaço de regressão de configs, comandos, HUD, prediction e demos.
- Traz complexidade de um engine multiprotocolo que o produto não precisa.

## 13. Recomendação técnica

Adotar uma estratégia de **núcleo conservador, bordas modernas**:

1. congelar e medir o comportamento do uNezQuake na Fase 0;
2. manter intactos física, prediction, netcode, serialização de demos/MVD, comandos, aliases e geração de `usercmd`;
3. extrair interfaces estreitas para plataforma e input ao redor do código existente;
4. migrar SDL2 para SDL3 usando vkQuake e FTEQW como referências de API;
5. iniciar Android pelo template SDL3 moderno e NDK/CMake, incorporando do FTEQW apenas casos de ciclo de vida, intents, surface e testes úteis;
6. manter OpenGL moderno como primeiro renderer Android e fallback;
7. reavaliar o Vulkan dormente do uNezQuake contra vkQuake e FTEQW, reutilizando componentes compatíveis por subsistema;
8. exigir equivalência automatizada em cada gate antes de avançar.

As fases 4 e 5 não devem ser simplesmente repetidas: o projeto já possui abstração de renderer e OpenGL moderno. Elas devem ser **auditadas contra seus critérios**, corrigidas onde incompletas e encerradas com evidências. Isso respeita a regra de não pular fases sem reimplementar trabalho já existente.

## 14. Gate para a Fase 0

Antes de qualquer refatoração, a Fase 0 deve:

- inicializar e fixar os submódulos;
- produzir builds reproduzíveis Linux e Windows;
- registrar compiladores, dependências e flags;
- definir hardware de referência e tiers Android futuros;
- obter/legalizar demos de referência;
- capturar hashes e métricas do comportamento atual;
- separar testes determinísticos de benchmarks sujeitos a ruído;
- evitar fazer CI falhar por FPS até haver runners dedicados e tolerâncias estatísticas confiáveis.

**Decisão de saída da Fase −1:** aprovada a continuidade com uNezQuake como base. A rota FTEQW-base foi formalmente avaliada e rejeitada para o escopo completo, permanecendo FTEQW como fonte prioritária de reaproveitamento seletivo.

## 15. Referências primárias

- [uNezQuake — repositório](https://github.com/dusty-qw/unezquake)
- [uNezQuake — CMake na revisão analisada](https://github.com/dusty-qw/unezquake/blob/312a8ca6e13d6f64e70f8a251477743e33a02ff4/CMakeLists.txt)
- [uNezQuake — API de renderer](https://github.com/dusty-qw/unezquake/blob/312a8ca6e13d6f64e70f8a251477743e33a02ff4/src/r_renderer_structure.h)
- [ezQuake — repositório](https://github.com/ezQuake/ezquake-source)
- [FTEQW — repositório](https://github.com/fte-team/fteqw)
- [FTEQW — CMake com SDL3 e Android](https://github.com/fte-team/fteqw/blob/f937b9d88f71fc4429db5fe56c6a98d922711b2e/CMakeLists.txt)
- [FTEQW — manifesto Android](https://github.com/fte-team/fteqw/blob/f937b9d88f71fc4429db5fe56c6a98d922711b2e/engine/droid/AndroidManifest.xml)
- [FTEQW — Activity Android](https://github.com/fte-team/fteqw/blob/f937b9d88f71fc4429db5fe56c6a98d922711b2e/engine/droid/src/com/fteqw/FTEDroidActivity.java)
- [vkQuake — repositório](https://github.com/Novum/vkQuake)
- [vkQuake — opção SDL3](https://github.com/Novum/vkQuake/blob/9be3a5addeb3023396299efd588627e39345f451/meson_options.txt)
- [SDL3 — licença](https://github.com/libsdl-org/SDL/blob/main/LICENSE.txt)
