# Playbook: estudar vídeos de referência antes de editar

Objetivo: o usuário traz um ou mais vídeos ("quero nesse estilo") e você transforma isso em
uma **ficha de estilo** curta e mensurável, depois aplica via EDL e flags do `vedit`.
Estude a técnica, nunca reuse o material: imagem, fala, marca e rosto da referência
continuam sendo de quem os fez.

Referências: `formatos-virais.md` (repertório e receitas), `legendas.md`, `enquadramento-vertical.md`,
`motion.md`, `cortes-e-ritmo.md`. Depois, o playbook do material do usuário
(`cortes-de-video-longo.md` ou `talking-head-reel.md`).

## Fase 0 — o que o usuário quer copiar
Pergunte uma vez, curto: quais referências, e **o que** nelas interessa (layout, legenda,
ritmo, manchete, b-roll)? "Tudo" não é resposta útil: peça os dois ou três pontos que mais
pesam. Avise que isso estuda a forma, não garante o desempenho da referência.

## Fase 1 — medir cada referência
```bash
vedit analyze ref1.mp4 -o estudo/ref1 --scene 0.3 --hook-seconds 6
vedit analyze ref2.mp4 -o estudo/ref2 --words ref2-words.json
```
- Cada comando grava `analise.json`, `analise.md`, `gancho.jpg` e `completo.jpg`.
- `--words` aproveita um `words.json` que você já tenha; `--transcribe` transcreve a
  referência (lento em CPU; só se a velocidade de fala ou a legenda importarem).
- `--scene` menor detecta mais cortes, mas abaixo de 0.3 vira falso corte de zoom e gesto:
  não baixe. **A detecção de cortes é um limite inferior**: fusão rápida, whip-pan e troca
  dentro de janela podem passar; um número de cortes baixo não prova que o vídeo é parado.
- Em layout empilhado (b-roll em cima, locutor embaixo) a tela cheia fica cega: use
  `--region 0:0.48` (repetível) para medir só a faixa da janela. Sem `--region` e com menos
  de 1 corte a cada 20 s, o comando já testa as metades de cima e de baixo sozinho.
- Flashes de ~0,1 s contavam em dobro; `--merge 0.15` (padrão) funde e mostra as detecções
  brutas ao lado.

## Fase 2 — ler e olhar
1. Leia `analise.md` inteiro (curto): duração, cortes, tamanho de plano (mediana e maior
   trecho sem corte), loudness, true peak, palavras por segundo.
2. Abra `gancho.jpg` (primeiros segundos) e `completo.jpg` (prancha do vídeo todo). Você vê
   imagem; **não ouve áudio**: nada de opinião sobre voz, música ou mixagem além do medido.
3. Percorra a lista de observação e anote o que **vê**, não o que presume:

| Item | O que anotar |
|---|---|
| Layout | tela cheia, janela de b-roll em cima + fala embaixo, tela preta com conteúdo menor; fração da altura da janela; alterna ou não |
| Gancho | manchete no quadro 0? montagem de imagens? abertura seca? rosto conhecido? |
| Legenda | modo (bloco, palavra, karaoke), caixa (alta, frase), cor, posição vertical (costura, 0,6-0,8, topo), destaque (cor, tamanho, nenhum) |
| Manchete/faixa | fixa quando, em quantas linhas, cor da caixa, onde fica |
| Inserts | frequência de troca, duração de cada um, aparecem na palavra nomeada? cartões de prova? |
| Ritmo | mediana de plano, punch-in alternado, longos sem corte, trechos de cortes concentrados no começo |
| Fechamento | CTA, cartão final, ou termina seco |
| Defeitos | legenda sobre cartão, erro de grafia, pico de áudio |

Cuide da amostra: com uma única referência, a ficha vale para ela; com duas ou três, só o que
**se repete** é "estilo". Registre o que não pôde confirmar (áudio, cortes mascarados).

## Fase 3 — ficha de estilo (escreva antes de editar)
Máximo ~12 linhas, em arquivo ou na resposta:

```text
Formato:        apresentador + janela de b-roll (ref1, ref2)
Layout:         lower, split_at 0.45; alterna com tela cheia nos cortes
Legenda:        --mode bloco --case sentence --max-words 3; y na costura (padrão lower)
Ênfase:         salto de tamanho em número (--emphasis), sem cor
Manchete:       2 linhas, caixa vermelha, do 0 s ao fim (--headline ... --headline-start 0)
Inserts:        troca a cada 1,5-3 s; cartão de prova 2 s em número citado
Ritmo:          mediana de plano ~2,5 s; punch-in 1,25x a cada ~3 s
Fechamento:     seco, sem CTA (decisão: manter ou pôr CTA?)
Não copiar:     pico de áudio, legenda sobre cartão
```

Mostre a ficha ao usuário. **Portão:** só prossiga com o ok. Onde a ficha pede algo que o
`vedit` não faz (texto animado, transição, matte, cantos arredondados, PiP), diga e proponha
HyperFrames ou a versão simples.

## Fase 4 — aplicar
1. Siga o playbook do material do usuário (`cortes-de-video-longo.md` ou
   `talking-head-reel.md`), com os passos opcionais de b-roll, cartões e manchete.
2. Traduza a ficha em EDL (`layout: "lower"`, `overlays`, `zoom` alternado) e flags de
   `vedit captions` (`--mode`, `--case`, `--emphasis`, `--headline*`). Montagem em
   `formatos-virais.md`, seção 5.
3. Prévia, aprovação, final; `vedit verify` no arquivo final, com o **seu** alvo de áudio
   (-14 LUFS, -1,5 dBTP), não o da referência.
4. Rode `vedit analyze` no resultado e compare com a ficha (mediana de plano, cobertura de
   inserts, posição de legenda). Divergência grande: explique ou corrija.

## Checklist
- [ ] Cada referência foi medida com `vedit analyze` e vista (`gancho.jpg`, `completo.jpg`).
- [ ] Ficha de estilo curta, aprovada pelo usuário.
- [ ] Nenhum material, rosto, marca ou fala da referência foi reutilizado.
- [ ] O que o `vedit` não faz foi dito, com a alternativa.
- [ ] Alvo de áudio da skill mantido; picos da referência não copiados.
- [ ] Texto novo (manchete, rótulos) listado para revisão do usuário; nenhuma promessa de desempenho.
