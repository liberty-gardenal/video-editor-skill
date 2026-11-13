# Instalação

Este guia assume Claude Code instalado. Detalhes de requisitos estão no README.

## 1. Pelo marketplace de plugins do Claude Code

```bash
claude plugin marketplace add liberty-gardenal/video-editor-skill
claude plugin install video-editor@video-editor-skill
```

Dentro de uma sessão: `/plugin marketplace add liberty-gardenal/video-editor-skill` e
`/plugin install video-editor@video-editor-skill`. A skill aparece como
`/video-editor:editor-de-video` e os subagentes como `ve-*`. Para atualizar, use o fluxo
de atualização de plugins do Claude Code e recarregue a sessão.

Nesse modo o `bin/` do plugin entra no PATH do Bash do Claude Code: dentro de uma sessão,
basta rodar `vedit` (teste com `vedit doctor`). Fora do Claude Code (num terminal comum) o
`vedit` não estará no PATH; para isso use o caminho 2.

Como o plugin traz uma CLI, ele é para o **Claude Code** (CLI, app desktop e IDE), não para o
chat do claude.ai.

## 2. Clone + `install.sh`

```bash
git clone https://github.com/liberty-gardenal/video-editor-skill.git
cd video-editor-skill
./install.sh
vedit doctor
```

O `install.sh` instala a skill e os agentes para o seu usuário e põe o `vedit` em
`~/.local/bin/vedit` (veja `./install.sh --help` para as opções exatas). Se `~/.local/bin`
não estiver no PATH, chame `~/.local/bin/vedit` pelo caminho completo ou acrescente a pasta
ao PATH. Depois, `vedit setup` cria a `.venv/` e instala Pillow + numpy; `vedit setup --all`
acrescenta faster-whisper (transcrição) e opencv-python (`reframe`).

## 3. Só num projeto

```bash
./install.sh --project /caminho/do/projeto
```

Instala a skill e os agentes dentro do `.claude/` do projeto, sem mexer no resto da máquina.
A CLI fica em `<projeto>/.claude/bin/vedit`; chame por esse caminho.

## 4. Dependência: HyperFrames

Necessário para motion, gráficos e legenda animada. Comandos (README do HyperFrames):

```bash
claude plugin marketplace add heygen-com/hyperframes
claude plugin install hyperframes@hyperframes
```

Alternativa para outros agentes: `npx skills add heygen-com/hyperframes`. Exige Node.js 22+
e FFmpeg. Repositório: https://github.com/heygen-com/hyperframes. Qualquer outro detalhe:
confira no README do HyperFrames.

## 5. Dependências do sistema

`vedit doctor` diz o que falta e imprime o comando de correção para o seu sistema.

| Sistema | ffmpeg | Observação |
|---|---|---|
| macOS | `brew install ffmpeg` | A fórmula padrão pode vir sem libass; sem ele, a legenda queimada usa o fallback com Pillow (mais lento). Para libass, use uma build de ffmpeg que o inclua. |
| macOS Intel antigo | idem | Alguns pacotes não têm binário pronto e compilam por horas; não instale nada pesado no meio de um trabalho. |
| Linux (Debian/Ubuntu) | `sudo apt install ffmpeg` | Normalmente já inclui libass. |
| Windows | use WSL e siga o Linux | |

Python 3.10 ou superior; o `bin/vedit` escolhe a `.venv/` do repositório ou o Python do
sistema. Node 22+ só é necessário para o HyperFrames. Chrome ou Chromium é usado pelo
HyperFrames e para texto HTML -> PNG.

## 6. Conferir

```bash
vedit doctor
```
Saída com código 0 significa que o obrigatório está presente. Falta de HyperFrames é avisada
separadamente: o resto do pack funciona sem ele, menos o motion.

## Problemas comuns

- `vedit: command not found`: no plugin, reinicie a sessão do Claude Code (o `bin/` entra no PATH ao carregar o plugin); com `install.sh`, use `~/.local/bin/vedit` ou ponha essa pasta no PATH; num projeto, `<projeto>/.claude/bin/vedit`.
- Transcrição lenta: em CPU, vídeos longos levam tempo; rode em segundo plano com log.
- HDR do celular fica lavado: o ffmpeg está sem o filtro `zscale`; a conversão sai sem tone mapping. Use um ffmpeg com `zscale` (`vedit doctor` avisa).
- Legenda sem libass: normal; o `vedit burn` cai no fallback.
- `reframe` pede OpenCV: é opcional (`vedit setup --all`); sem ele, use `crop_x` manual (e lembre que `reframe` é experimental).
