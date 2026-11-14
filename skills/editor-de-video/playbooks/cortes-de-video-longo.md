# Playbook: cortes de vídeo longo (podcast, entrevista, live, aula)

Objetivo: N clipes verticais 9:16, cada um entendível sozinho, com legenda e áudio
verificados. Ordem fixa: **texto primeiro, vídeo bruto por último**. Cada fase termina
em um portão: mostre o resultado e espere o usuário, salvo "vai até o fim".

Referências para ler nesta ordem, só quando a fase pedir: `psicologia-do-feed.md`,
`selecao-e-scoring.md`, `cortes-e-ritmo.md`, `enquadramento-vertical.md`, `legendas.md`,
`audio.md`, `verificacao.md`, `armadilhas.md`.

## Fase 0 — preparar a run
```bash
vedit init ./run-episodio          # cria 00-probe.json ... out/ qc/ (layout em referencias/formatos.md)
vedit probe bruto.mp4 > run-episodio/00-probe.json
```
Confira no probe: `avg_frame_rate` real (não a base de tempo), rotação, HDR, canais de
áudio e correlação L/R. Anote o `fps` que a EDL vai usar. Se for HDR, o `vedit cut`
converte para SDR sozinho; só avise o usuário.

## Fase 1 — transcrever (barato, decisivo, em segundo plano)
```bash
vedit transcribe bruto.mp4 -o run-episodio/01-words.json --lang pt > run-episodio/transcribe.log 2>&1 &
```
Em CPU, vídeo de horas leva tempo: dispare logo e trabalhe no que não depende dele.
Não leia o JSON. Gere o digest:
```bash
vedit digest run-episodio/01-words.json -o run-episodio/02-digest.md --every 15
```
**Portão 0:** diga duração, idioma detectado e quantos blocos o digest tem.

## Fase 2 — mapa de contexto (subagente `ve-context-mapper`)
Entrada: `02-digest.md`. Saída: `context-map.json` (premissa, blocos, temas, quem fala,
setups e payoffs por bloco, trechos de baixo valor como vinheta e propaganda). Ainda
nenhum clipe é escolhido aqui.

## Fase 3 — caçar momentos (subagente `ve-clip-hunter`)
Entrada: `02-digest.md` + `context-map.json` + o resumo de `psicologia-do-feed.md`.
Saída: `03-moments.json`, uma lista com **todo** momento defensável. Cada item tem:
`hook`, `development`, `payoff` (com citação e tempo), janela `start`/`end` aproximada,
risco de falta de contexto. Sem as três respostas, o momento não entra.

**Portão 1 — MOMENTOS.** Mostre a lista curta (título factual, tempo, a frase do gancho).
Pergunte quais seguem. Isso muitas vezes é tudo o que o usuário queria.

## Fase 4 — candidatos com in/out
Para as janelas escolhidas, leia só o trecho:
```bash
vedit digest run-episodio/01-words.json --windows "612-690,1480-1555" -o run-episodio/win.md
vedit silences bruto.mp4 --noise -35 --min 0.25 > run-episodio/silences.json
```
Reconstrua cada candidato com segmentos reais da fala, sem mudar o sentido. Comece pelo
gancho, termine depois do payoff, no silêncio após a última palavra. Corte
reformulações e vícios só se a emenda cair em vale de energia; fala contínua sem vale não
se emenda.

## Fase 5 — revisão cega (subagente `ve-blind-reviewer`)
Para **cada** candidato, uma chamada separada, passando só o transcript reconstruído, a
duração e eventos visuais confirmados. Sem notas, sem título, sem justificativa.
Veredito `stands_alone: true/false` com motivos. Hard fail derruba o clipe, mesmo com
média alta. Nada é aprovado na primeira passagem: o candidato com falha volta para a
Fase 4 uma vez; se falhar de novo, descarte.

## Fase 6 — deduplicar
Compare os aprovados pelo sentido, não pelo tempo: dois clipes com a mesma tese são um só;
fique com o melhor. Registre os descartados com o motivo em `rejected.json`. Quantidade
não é meta.

## Fase 7 — EDLs (subagente `ve-edit-director`)
Entrada: clipes aprovados, `01-words.json` por janela, probe. **Uma EDL por short**, porque
`vedit cut` renderiza um único arquivo por EDL. Saída: `edl/<id>.json` (um por clipe
aprovado, formato em `referencias/formatos.md`) e `04-plan.json` com o plano de legenda e
enquadramento de cada `id`. Cada EDL aponta para o bruto em `source` (caminho relativo ao
arquivo da EDL, por exemplo `../bruto.mp4`). Verifique cada uma:
```bash
mkdir -p run-episodio/edl
for id in c1 c2 c3; do
  vedit metrics --edl run-episodio/edl/$id.json --words run-episodio/01-words.json
done
```
Palavras por segundo, cortes por minuto e maior trecho sem corte devem fazer sentido para
o formato. (Daqui em diante, todo passo roda **por `id`**: use um laço como o acima.)

## Fase 8 — prévia dos cortes (barato)
```bash
for id in c1 c2 c3; do
  mkdir -p run-episodio/out/$id
  vedit cut --edl run-episodio/edl/$id.json -o run-episodio/out/$id/previa.mp4 --preview
  vedit edges run-episodio/out/$id/previa.mp4
done
```
`edges` reprova palavra truncada no começo ou no fim. Corrija a EDL e repita.
**Portão 2 — CORTES.** Mostre as prévias e espere o ok antes de qualquer etapa cara.

## Fase 9 — enquadramento vertical
Comece com `layout: cover` e `crop_x` manual conferido numa prancha, por `id`:
```bash
vedit sheet run-episodio/out/c1/previa.mp4 -o run-episodio/qc/c1-enq.jpg --every 3 --cols 4 --width 360
```
Dois locutores ou rosto fora do centro: `vedit reframe --edl run-episodio/edl/c1.json --write`
(opcional, exige OpenCV; **experimental e sem teste ponta a ponta**, confira o resultado na
prancha). Os keyframes de `crop_x` são constantes por trecho: o crop salta, não desliza,
então só troque na fronteira de turno de fala. `split` quando houver slide ou gráfico
junto da pessoa; `fit` quando não pode cortar nada. Rosto cortado na borda ou meia tela
vazia são falha.

## Fase 10 — legendas (por `id`)
> Corte com motion ou pedido de alta qualidade: legenda, motion e composite seguem
> `referencias/padrao-excelencia.md`, que é também o checklist de aprovação de cada `id`.

A legenda padrão fica em `--y 0.62` (centro do texto a 62% da altura). Antes de aceitar,
desenhe a faixa e o rosto numa prancha com guias (formato do `zona.json` em
`referencias/formatos.md`) e mova `--y` só se a faixa cobrir o rosto no pior quadro.
```bash
vedit captions run-episodio/01-words.json --edl run-episodio/edl/c1.json -o run-episodio/out/c1/leg.ass --srt --style viral --max-words 3 --y 0.62 --highlight "palavra1,palavra2"
vedit sheet run-episodio/out/c1/previa.mp4 -o run-episodio/qc/c1-leg.jpg --guides zona.json --every 4
```
`--highlight` é a lista de palavras que **você** escolheu destacar (raras; nunca número ou
afirmação contestável); sem ela não há destaque. Confira legenda × rosto e legenda × área
segura. Legenda animada ou motion: entregue o vertical limpo ao HyperFrames (handoff em
`referencias/motion.md`, seção 15).

### Passo opcional: janela de b-roll, cartões de prova e manchete
Para cortes de podcast no estilo observado em vídeos publicados (receitas em
`referencias/formatos-virais.md`; prática observada, não causa comprovada de retenção). O
`ve-edit-director` registra no `04-plan.json`, por `id`, o que cada insert mostra e em que
palavra entra.
- EDL: clipes `layout: "lower"` onde há b-roll em cima; `overlays` (`region` `top`/`full`/`card`, `at` em tempo de saída, sem sobreposição) com material do usuário ou licenciado.
- Alternância de punch-in (≈1,2-1,3x a cada ~2,5-4 s, nas fronteiras de frase ou turno) como clipes com `zoom` diferente.
- Legenda: `--mode`, `--case`, `--emphasis`, e manchete fixa com `--headline "L1|L2" --headline-start 0` (até 2 linhas, dentro das zonas seguras). Sob cartões a legenda cala.
Sem b-roll de verdade a mostrar, não force: a janela vazia é falha (`armadilhas.md`).

## Fase 11 — render, master, verificação (por `id`)
```bash
for id in c1 c2 c3; do
  d=run-episodio/out/$id
  vedit cut --edl run-episodio/edl/$id.json -o $d/corte.mp4
  vedit burn $d/corte.mp4 $d/leg.ass -o $d/com-leg.mp4
  vedit master $d/com-leg.mp4 -o $d/final.mp4
  vedit verify $d/final.mp4 --platform reels --source bruto.mp4 --strict-edges --json
done
```
`--strict-edges` entra aqui porque o corte é só fala: som cortado nas bordas é palavra
truncada. Depois, subagente `ve-qc` com cada `final.mp4`, o relatório do `verify` e
pranchas. Reprovou: corrija na EDL daquele `id` (não no arquivo) e refaça só o que mudou.
Música de fundo num corte é opcional: use a cadeia `extract-audio` → `mix` → `mux`
(`referencias/formatos.md`, seção 5) antes do `master`, e tire o `--strict-edges`.
**Portão 3 — ENTREGA.**

## Checklist final
- [ ] Transcrição com tempo por palavra existe e o bruto só foi aberto no corte.
- [ ] Cada clipe tem gancho, desenvolvimento e payoff e passou pela revisão cega.
- [ ] Sem clipes duplicados pelo sentido; nenhum aprovado de primeira sem revisão.
- [ ] Uma EDL por short; EDL em quadro inteiro; `edges` limpo; nenhuma palavra inventada.
- [ ] Rosto inteiro no crop; legenda fora do rosto e da área segura.
- [ ] Se usou `overlays`: `top` só sobre `lower`, sem sobreposição, legenda calada sob cartões, manchete em até 2 linhas.
- [ ] `vedit verify` passou no arquivo final, por plataforma.
- [ ] Usuário foi avisado de que o áudio precisa ser ouvido por ele.
- [ ] Nenhuma promessa de desempenho.
