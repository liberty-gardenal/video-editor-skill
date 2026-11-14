# video-editor-skill

Um pack de skill para o Claude Code que o transforma num agente de edição de vídeo que
não depende de contexto prévio. A skill `editor-de-video` decide a narrativa (quais
trechos, que texto, que ritmo); subagentes leem as transcrições em contexto próprio; a CLI
`vedit` mede e renderiza com ffmpeg; o [HyperFrames](https://github.com/heygen-com/hyperframes)
compõe motion em HTML; e `vedit verify` aprova o arquivo final. Sem promessa de viralização:
o objetivo é entregar vídeo correto, medido e revisável.

## O que ele faz

Cinco fluxos de produção, cada um com um playbook passo a passo em `skills/editor-de-video/playbooks/`, mais um playbook de estudo de referência:

1. **Cortes de vídeo longo**: podcast, entrevista, live ou aula viram N clipes verticais, com revisão cega e deduplicação.
2. **Talking head para Reel**: uma gravação curta vira um Reel enxuto (retakes e silêncio, punch-ins por clipe ou rampa de zoom, legenda, capa, trilha).
3. **Motion de narração**: só um áudio vira um vídeo inteiro com cenas em HyperFrames, sincronizadas na palavra.
4. **Montagem na batida**: vários clipes de celular viram um Reel cortado no ritmo, com um momento de fala e final em loop.
5. **Anúncio com footage real**: fotos e vídeos do cliente + narração viram um criativo para social pago.

Além disso:

- **Estudar referências** (`vedit analyze` + playbook `estudar-referencia.md`): mede cortes, ritmo, loudness e gancho de vídeos que o usuário quer imitar, gera uma ficha de estilo e aplica via EDL e flags. Estuda a técnica; não reusa material de terceiros, e a detecção de cortes é um limite inferior.
- **Formatos virais observados** (`referencias/formatos-virais.md`): receitas como apresentador com janela de b-roll e corte de podcast com manchete fixa, baseadas em 12 vídeos pt-BR. São práticas observadas, não causas comprovadas de retenção.
- **B-roll simples e legenda ampliada no `vedit`**: clipe `lower` e `overlays` na EDL (janela de cima, tela cheia, cartão de prova); legenda em modo bloco, palavra ou karaoke, caixa, ênfase por tamanho e manchete fixa.

## Instalação

Guia completo em [`docs/instalacao.md`](docs/instalacao.md).

**(a) Marketplace de plugins do Claude Code**
```bash
claude plugin marketplace add liberty-gardenal/video-editor-skill
claude plugin install video-editor@video-editor-skill
```
(ou, dentro de uma sessão, `/plugin marketplace add ...` e `/plugin install ...`).
Instalado assim, o `bin/` do plugin entra no PATH do Bash do Claude Code: basta rodar `vedit`.

**(b) Clone + install.sh**
```bash
git clone https://github.com/liberty-gardenal/video-editor-skill.git
cd video-editor-skill && ./install.sh && vedit doctor
```
O `install.sh` coloca `vedit` em `~/.local/bin/vedit`; se essa pasta não estiver no PATH,
chame pelo caminho completo.

**(c) Só num projeto**
```bash
./install.sh --project .
```
Nesse modo a CLI fica em `<projeto>/.claude/bin/vedit`.

**Onde roda:** como o pack traz uma CLI (`bin/`), ele serve ao **Claude Code** (CLI, app
desktop e extensões de IDE). Não funciona no chat do claude.ai, que não executa `bin/` nem
ffmpeg local.

## Dependência: HyperFrames

Todo motion, gráfico e legenda animada em HTML é delegado ao HyperFrames (HeyGen,
Apache-2.0). Sem ele, o pack ainda corta, deixa vertical, queima legenda, trata áudio e
verifica; só o motion fica de fora. Instale (comandos do README do HyperFrames):

```bash
claude plugin marketplace add heygen-com/hyperframes
claude plugin install hyperframes@hyperframes
```

Para outros agentes: `npx skills add heygen-com/hyperframes`. Requer Node.js 22+ e FFmpeg.
Repositório: https://github.com/heygen-com/hyperframes. Detalhes da divisão de trabalho em
[`docs/hyperframes.md`](docs/hyperframes.md).

## Requisitos

| Item | Requisito |
|---|---|
| ffmpeg / ffprobe | obrigatório; recomendado com libass (legenda queimada rápida) e filtros `loudnorm`, `arnndn` |
| Python | 3.10 ou superior |
| Node.js | 22 ou superior (exigência do HyperFrames) |
| HyperFrames | necessário para motion e legenda animada |
| faster-whisper | necessário para transcrever (`vedit setup --all`, ou traga um `words.json`) |
| OpenCV | opcional (`vedit setup --all`); só para `vedit reframe` |
| Pillow + numpy | instalados por `vedit setup`; usados na legenda sem libass |
| Chrome/Chromium | usado pelo HyperFrames e por texto HTML -> PNG |

`vedit doctor` confere tudo e imprime o comando de correção de cada falta.

## Primeiro uso

Exemplos de pedido em linguagem natural:

- "Corta esse podcast em clipes verticais de até 60 segundos e me mostra os momentos antes de renderizar."
- "Faz um Reel com essa gravação minha falando: tira silêncio e repetição, põe legenda e uma capa."
- "Tenho essa narração; monta um vídeo com motion, uma cena por ideia, e me mostra a prévia."
- "Monta um vídeo no ritmo da música com esses clipes do celular, com um trecho de fala e final em loop."
- "Faz um anúncio de 25 segundos com as fotos e vídeos dessa clínica e esta narração."

O Claude roda `vedit doctor`, pergunta só o que faltar (uma rodada), e para em cada
portão para você aprovar.

## Como funciona

```text
        skill editor-de-video (decide: narrativa, trechos, textos)
                    |
     subagentes ve-* leem o digest (contexto próprio, devolvem JSON curto)
                    |
        vedit mede e renderiza (probe, transcribe, cut, captions, mix, master)
                    |
        HyperFrames compõe motion em HTML (overlays, legenda animada, card final)
                    |
        vedit verify (QC final obrigatório) + ve-qc + você ouve o áudio
```

Princípios: transcrição com tempo por palavra antes de abrir o vídeo bruto; a EDL como fonte
única de verdade, em quadro inteiro; o modelo decide e os scripts medem; prévia, aprovação,
final.

## CLI

`vedit` é o contrato entre a skill e os scripts. Referência completa em [`docs/cli.md`](docs/cli.md); todo comando aceita `--json`.
Uma EDL gera **um** vídeo (`vedit cut` concatena todos os clipes dela): para N cortes de um vídeo longo, uma EDL por corte.

| Comando | Para quê |
|---|---|
| `doctor`, `setup`, `init` | ambiente e pasta da run |
| `probe`, `sheet`, `silences` | medir e ver o material |
| `transcribe`, `digest` | texto com tempo por palavra e versão compacta para ler |
| `cut`, `edges`, `reframe`, `metrics` | EDL (inclui `lower` e `overlays`), render, bordas, enquadramento, ritmo |
| `analyze` | teardown de referência: cortes, tamanho de plano, loudness, ritmo de fala, quadros do gancho |
| `captions`, `burn`, `composite` | legenda ASS/SRT (modos, caixa, ênfase, manchete fixa, mute), queima e composição de motion transparente com legenda por cima |
| `loudness`, `extract-audio`, `mix`, `mux`, `master` | áudio (tirar do render, mixar música, recolocar, normalizar) |
| `verify` | QC final por plataforma |

## Estrutura do repositório

```
.claude-plugin/        plugin.json e marketplace.json
skills/editor-de-video/
  SKILL.md             roteador
  playbooks/           os 5 fluxos + estudo de referência
  referencias/         notas de apoio (feed, seleção, cortes, legendas, áudio, motion, QC...)
agents/                subagentes ve-*
bin/ lib/              CLI vedit
docs/                  cli.md, hyperframes.md, instalacao.md
tests/  install.sh
```

## Limites

- Não garante desempenho em nenhuma plataforma; só mede o que dá para medir no arquivo.
- O Claude não ouve áudio: valida por números (LUFS, true peak, bordas) e pede que você ouça.
- **Estado de cada parte:** `transcribe` foi exercitado manualmente em filmagem real em português (modelo `small`, CPU), mas **não tem teste automatizado**; `reframe` é **experimental e sem teste ponta a ponta**, confira na prancha; HDR sem o filtro `zscale` no ffmpeg é convertido **sem tone mapping** (as cores podem sair lavadas).
- **O que o `vedit` não faz:** J-cut/L-cut (áudio e imagem cortam no mesmo quadro), pan animado entre keyframes de `crop_x` (o crop salta; só o `zoom` tem rampa linear), texto animado ou digitado, transições (dissolve, glitch, whip), matte/oclusão, cantos arredondados e sombra em cartões, legenda bilíngue, cor por falante, picture-in-picture com etiquetas e explicadores animados (isso é do HyperFrames). Os overlays do `vedit` são só de vídeo, sem sobreposição no tempo, e não mexem no áudio. Destaque de palavra na legenda é a lista `--highlight` que o editor escolhe, não automático.
- Etapas pesadas (transcrição de vídeo longo, render de motion em alta qualidade) são lentas em CPU.
- Música e imagens de terceiros são responsabilidade de quem usa; o pack não fornece nem licencia nenhuma.

## Créditos

[HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen) para composição de
motion; [faster-whisper](https://github.com/SYSTRAN/faster-whisper) para transcrição;
[FFmpeg](https://ffmpeg.org) para tudo que é mídia; [OpenCV](https://opencv.org) com o
detector facial YuNet para o reframe opcional. Cada projeto tem a própria licença.

## Contribuindo

Veja [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licença

MIT. Veja [`LICENSE`](LICENSE).

## English summary

A Claude Code skill pack that turns Claude into a context-independent video editor. The
`editor-de-video` skill routes to five playbooks (long-form clipping, talking-head Reels,
narration-to-motion, beat-synced montage, real-footage ads). Subagents read compact
transcript digests, the `vedit` CLI (ffmpeg-based) measures and renders, HyperFrames
(HeyGen) composes HTML motion, and `vedit verify` gates delivery. Install with
`claude plugin marketplace add liberty-gardenal/video-editor-skill` then
`claude plugin install video-editor@video-editor-skill`, or clone and run `./install.sh`.
Motion work requires the HyperFrames plugin (`claude plugin marketplace add heygen-com/hyperframes`,
`claude plugin install hyperframes@hyperframes`; Node 22+ and FFmpeg). Prose in the skill is
Brazilian Portuguese. No performance guarantees; Claude cannot hear audio, so you must
listen before publishing. MIT licensed.
