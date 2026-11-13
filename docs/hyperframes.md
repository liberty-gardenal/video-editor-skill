# HyperFrames e este pack: quem faz o quê

[HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen, Apache-2.0) transforma
HTML, CSS e animação "seekable" em MP4 de forma determinística: o renderizador posiciona
cada quadro num Chrome headless e codifica com FFmpeg. Este pack não reimplementa isso:
**toda composição em HTML (motion, gráficos, legenda animada, card final) é delegada a ele.**

## Divisão de trabalho

| Etapa | Quem |
|---|---|
| Probe, transcrição, silêncios, digest, seleção de momentos | `vedit` + subagentes `ve-*` |
| Corte, vertical (`cover`/`split`/`fit`), stills, `speed`, rampa de zoom, HDR para SDR | `vedit cut` |
| Legenda queimada simples (estática, com `--highlight` escolhido pelo editor) | `vedit captions` + `vedit burn` |
| Motion, cartões, lower-thirds, legenda animada, card final, B-roll e overlays, pan animado, J-cut/L-cut (**o `vedit` não faz nenhum destes**) | HyperFrames (ou ffmpeg manual) |
| Mix com ducking, troca de áudio, loudness, master | `vedit extract-audio`, `vedit mix`, `vedit mux`, `vedit master` |
| Aprovação final | `vedit verify` + `ve-qc` |

## Instalação (comandos verificados no README do HyperFrames)

```bash
claude plugin marketplace add heygen-com/hyperframes
claude plugin install hyperframes@hyperframes
```

Skills avulsas (outros agentes, ou sem plugin): `npx skills add heygen-com/hyperframes`.
Uso manual da CLI: `npx hyperframes init meu-video`, `npx hyperframes preview`,
`npx hyperframes render`. Requisitos: **Node.js 22+** e **FFmpeg**. Git LFS só é necessário
para clonar o repositório do HyperFrames inteiro para desenvolvimento (baselines de teste);
quem instala o plugin não precisa. Qualquer detalhe além disso: confira no README do HyperFrames.

Instalado como plugin, o HyperFrames pede que a CLI dele seja chamada pelo lançador do
próprio plugin (não por `npx hyperframes` solto). **Siga as instruções da skill dele**
(`/hyperframes:hyperframes-cli`); este pack nunca assume um caminho fixo.

## Qual skill do HyperFrames para qual necessidade

| Necessidade | Skill (`/hyperframes:<nome>`) |
|---|---|
| Não sei por onde começar com HTML->vídeo | `hyperframes` (roteador, leia primeiro) |
| Contrato da composição (atributos de tempo, trilhas, sub-composições) | `hyperframes-core` |
| Comandos: lint, check, snapshot, preview, render | `hyperframes-cli` |
| Animação, transições, GSAP e afins | `hyperframes-animation`, `hyperframes-keyframes` |
| Direção visual, paleta, tipografia | `hyperframes-creative` |
| Voz, música, efeitos, mix dentro da composição | `media-use`, `hyperframes-audio` |
| Legenda embutida em vídeo com pessoa falando | `embedded-captions` |
| Gráficos e overlays sobre talking head ou podcast | `talking-head-recut` |
| Gráfico ou motion curto sem narração | `motion-graphics` |
| Explicar um tema só com motion (narração) | `faceless-explainer` |
| Vídeo longo ou misto, fallback geral | `general-video` |
| Vídeo guiado por música | `music-to-video` |
| Blocos prontos (transições, overlays, gráficos) | `hyperframes-registry` |

Antes de escrever motion à mão, procure um bloco pronto no catálogo do HyperFrames
(a skill `hyperframes-cli` ensina a busca).

## Lições práticas (genéricas)

- **Uma composição por trecho, com duração exata.** Facilita render parcial e correção
  localizada: se a EDL só desloca trechos sem mudar a duração, reaproveite os renders.
- **Relógio determinístico.** Toda lógica de animação deve depender do tempo da timeline
  que o renderizador posiciona, nunca de `Date.now`, `requestAnimationFrame` livre ou
  `onUpdate` que pode ser suprimido ao saltar de quadro.
- **Prévia barata antes do render caro.** Render draft em fps baixo e resolução baixa
  (540x960), prancha de quadros, correção, e só então a qualidade alta. Renders com grão
  em tela cheia, desfoque de movimento por super-amostragem ou 4K custam várias vezes mais.
- **Prancha antes do final.** Monte uma prancha por cena e procure sobreposição de texto,
  quebra de linha em pílulas, contadores com valor errado no instante da fala.
- **Entrada na palavra.** Gere os tempos de entrada a partir do `words.json` (função
  `at("palavra", n)`), nunca como números soltos. Confira a ocorrência `n`: palavras curtas
  se repetem e uma ocorrência errada desloca a cena inteira.
- **Quirks de lint e snapshot.** Ferramentas de lint e snapshot costumam ler o `index.html`
  do projeto: um `index.html` que é symlink pode falhar, uma pasta de assets em symlink
  funciona; duas composições raiz na mesma pasta dão erro. Um erro de console em todo
  quadro (por exemplo raio negativo em SVG) deixa o runtime "não pronto" e o snapshot trava:
  proteja valores com `Math.max(0, ...)`.
- **CSS: seletores amplos pegam SVG demais.** Use classes em vez de `#tela svg`. Fundos
  transparentes deixam a cena anterior aparecer: dê `background` a telas sobrepostas.
- **Contorno de texto.** `-webkit-text-stroke` come o glifo; prefira anel de `text-shadow`.
- **Tudo local.** Fontes, scripts de animação, ícones e imagens ficam na pasta do projeto;
  nada de CDN no render (reprodutibilidade e offline).
- **Safe zones.** Em 1080x1920, evite os ~14% de cima e ~35% de baixo para conteúdo
  importante em anúncio; legenda numa faixa própria (padrão do `vedit captions`: `--y 0.62`). Veja `skills/editor-de-video/referencias/plataformas.md`.
- **Texto se insere, não se gera.** Rótulos e títulos que você escreve vão numa lista para
  o usuário revisar na prévia.
- **Áudio no final.** Se o mux acontecer fora do HyperFrames, preencha o áudio até o fim
  do vídeo (para o card final não ser cortado) e masterize com `vedit master`.

## Handoff: do corte ao motion e de volta

```
vedit cut --edl 04-edl.json -o out/limpo.mp4        # vertical limpo, sem legenda
        |
        v
HyperFrames: overlays, legenda animada, card final   # usa out/limpo.mp4 como vídeo base
        |  (tempos de entrada lidos de 01-words.json, remapeados para o clipe final)
        v
out/composto.mp4
        |
        v
vedit master out/composto.mp4 -o out/final.mp4       # loudness, 48 kHz
vedit verify out/final.mp4 --platform reels --json   # obrigatório antes de entregar
```

Cuidados no handoff:
- O `words.json` está em tempo da **fonte**; para o clipe final remapeie pelos clipes da
  EDL (o `vedit captions` já faz isso para ASS; para HTML, faça o mesmo cálculo).
- Se a legenda será animada no HyperFrames, **não** queime a do `vedit burn` também.
- O vídeo base entra com áudio mudo na composição se o áudio for mixado depois; defina
  um dono do áudio e não duplique; para recolocar o áudio mixado, `vedit mux --video composto.mp4 --audio mix.wav -o ...`.
- Conferir `vedit verify` no arquivo final, nunca no intermediário.
