# Playbook: motion de narração (só áudio -> vídeo com motion)

Objetivo: um áudio de narração vira um vídeo 9:16 inteiro em HyperFrames, com uma cena por
ideia do roteiro, entrada sincronizada na palavra, legenda queimada e card final.
Não há imagem real: só formas, ícones, texto e dados gerados.

```
áudio -> transcrição por palavra -> grupos de legenda -> uma cena por trecho do roteiro
-> prévia 540x960 -> aprovação -> final 1080x1920
```

Referências: `motion.md`, `narracao-tts.md` (se a voz for sintética), `legendas.md`,
`audio.md`, `plataformas.md`, `verificacao.md`, `armadilhas.md`. HyperFrames:
`/hyperframes:hyperframes` (roteador), `/hyperframes:faceless-explainer` ou
`/hyperframes:general-video`, `/hyperframes:hyperframes-core`, `/hyperframes:hyperframes-cli`.

## Fase 0 — kickoff (uma rodada)
Peça ou infira: o áudio da narração; o roteiro com os textos que entram na tela (se
existir); logo e cores da marca; formato (9:16; 4:5 só se pedirem); duração-alvo. Se a
narração gravada divergir do roteiro, **a narração manda**; avise a divergência.
Não faça prévia com voz de teste robótica: peça a narração real.
Se houver um projeto anterior do mesmo estilo, copie a pasta e troque roteiro e áudio em
vez de começar do zero.

## Fase 1 — áudio e transcrição
```bash
vedit init ./run-motion
vedit probe narracao.wav > run-motion/00-probe.json
vedit loudness narracao.wav
vedit transcribe narracao.wav -o run-motion/01-words.json --lang pt
vedit digest run-motion/01-words.json -o run-motion/02-digest.md
```
Narração já ritmada: só meça (`vedit loudness`); a normalização final é o `vedit master` do vídeo pronto. Respiros longos: corte pausas (`vedit silences`) e, se
precisar, acelere até 1,10x, sem comer fala. Se a meta de duração só se alcança cortando
fala, avise o usuário em vez de cortar. Leia o digest inteiro antes de desenhar.
**Portão 1:** mostre a divisão do roteiro em trechos (texto + tempo) e a duração.

## Fase 2 — grupos de legenda e storyboard em texto
Escreva à mão os grupos de legenda: `(texto exibido, nº de palavras do whisper)`. A soma
das palavras tem de bater com o `words.json` (faça uma checagem automática). O texto
exibido pode corrigir a grafia ("R $ 27 ,00" vira "R$ 27"). Números em algarismo.

Depois, uma tabela: trecho do roteiro -> **uma** ideia visual -> palavra-chave que dispara
a entrada. Metáforas concretas e simples (documento caindo, contador, carimbo, checklist,
mapa com seta, ponte). Estado de alarme com vinheta leve; solução com a cor positiva.
**Portão 2:** mostre a tabela e a lista de textos que você vai inventar para a tela.

## Fase 3 — construir em HyperFrames
Um projeto, uma composição por trecho, cada uma com `data-duration` exato. Assets locais
(fontes, GSAP, ícones) para o render ser reproduzível sem rede. Tempos de entrada vêm do
`words.json` por função (`at("palavra", n)`), nunca como números fixos; confira a
ocorrência `n`, pois palavras curtas ("o", "de", "um") se repetem. Animação por relógio
determinístico, sem depender de `onUpdate` nem de tempo real.
Siga a skill do HyperFrames (`/hyperframes:hyperframes`, `/hyperframes:hyperframes-cli`) para a
estrutura de cena, a sintaxe e a chamada da CLI dele; o handoff está em `referencias/motion.md`, seção 15.
- Elementos persistentes (contador, selo) ficam dentro da área segura e fora da faixa da legenda.
- Área segura para anúncio: nada importante nos 14% de cima nem nos 35% de baixo; conteúdo
  entre y 290 e 1000, legenda entre 1040 e 1220 (em 1080x1920).
- Legenda: 2 a 4 palavras, cada uma entra no seu tempo; contorno por `text-shadow`, não por
  `-webkit-text-stroke` (come o glifo).
- Card final segura ao menos 1,4 s depois da última palavra, com uma ação só.

## Fase 4 — trilha (opcional)
Só música livre de direitos ou sintetizada por código. Mix por `vedit mix --voice narracao.wav --music musica.wav -o run-motion/out/mix.wav --music-lufs -27 --duck`,
música cerca de 17 a 27 LUFS abaixo da voz. Sem trilha garantida, entregue sem.

## Fase 5 — lint, prancha, prévia
Com a CLI do HyperFrames: lint da composição, depois snapshots dos momentos-chave. Monte uma
prancha por cena e procure sobreposição (texto sob elemento, pílula quebrando linha,
contador com número errado no instante da fala, selo colidindo). Corrija **antes** do
render final. Erro de console em todo quadro deixa o runtime "não pronto" e trava o
snapshot: proteja valores negativos de raio e tamanho.
```bash
vedit sheet run-motion/out/previa.mp4 -o run-motion/qc/cenas.jpg --every 2 --cols 6 --width 270 --guides zona.json
```
Render de prévia: 540x960, qualidade draft.
**Portão 3:** entregue a prévia, a prancha e a **lista de textos inventados**; espere aprovação.

## Fase 6 — final
Só depois do ok: 1080x1920, 30 fps, qualidade alta, em segundo plano com log em arquivo
(efeitos como grão em tela cheia multiplicam o tempo de render). O render do HyperFrames sai
em `run-motion/out/hf.mp4`. O áudio entra por fora, com `vedit mux`, que ajusta o áudio à
duração exata do vídeo (o card final não é cortado). Sem trilha, o `--audio` é a própria
`narracao.wav`.
```bash
vedit mux --video run-motion/out/hf.mp4 --audio run-motion/out/mix.wav -o run-motion/out/final-bruto.mp4
vedit master run-motion/out/final-bruto.mp4 -o run-motion/out/final.mp4
vedit verify run-motion/out/final.mp4 --platform meta-ads --json
```
Use `--platform reels` se não for anúncio. Rode `ve-qc` e abra o arquivo.

## Checklist final
- [ ] A narração gravada manda sobre o roteiro; divergências avisadas.
- [ ] Soma das palavras dos grupos de legenda confere com o `words.json`.
- [ ] Uma ideia visual por trecho, entrando na palavra certa (ocorrência `n` conferida).
- [ ] Nada importante fora da área segura; card final com ao menos 1,4 s de cauda.
- [ ] Sem pessoas reais, logos de terceiros nem prints de sites reais, salvo se o usuário trouxe o material.
- [ ] Lista de textos inventados aprovada na prévia; só então o final.
- [ ] `vedit verify` passou; usuário ouviu o áudio.
