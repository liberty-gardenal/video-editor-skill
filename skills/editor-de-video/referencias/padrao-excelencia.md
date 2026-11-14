---
uso: leia SEMPRE antes de entregar um corte de talking head, podcast ou entrevista com motion. É a linha de corte: abaixo disto, não entregue.
---

# Padrão de excelência (linha de corte)

Este arquivo registra o primeiro corte que o dono do pack aprovou como "próximo do nível de
excelência", e a versão anterior que ele reprovou como "super ruim". Entre as duas, o
material, a fala e a seleção eram os mesmos. Mudou só a execução. Use as duas como régua.

Caso de referência: corte de 47 s de um podcast de negócios (fonte 1280x720, 218 kbps,
câmera fixa). O convidado conta um caso: um jovem de 16 anos vendia brigadeiro no sinal e
pediu conselho → "não tem que vender mais, tem que vender melhor" → cada cliente do sinal
vale uma festa → meses depois, pedido de 800 para um casamento → a sacada do cartão-vale →
3 passos → "aí você começa a ganhar dinheiro".

## 1. O que foi reprovado (não repita)

| Erro da v1 | Por que ficou ruim |
|---|---|
| Layout `lower` (rosto embaixo, cópia desfocada e escura em cima) **sem motion por cima** | Metade da tela vazia e borrada parece render quebrado: o usuário leu como "cortes bugados" |
| Manchete numa caixinha amarela pequena, em 2 linhas, fixa por 8 s | "Nada profissional": parece etiqueta, não título |
| Legenda pequena (~45 px de altura de caixa alta), Helvetica condensada, contorno fino | Some no celular; parece legenda automática |
| Motion prometido, mas não entregue na prévia | Sem motion, o corte é só um talking head com legenda |
| Mesma escala em todos os cortes | Jump cut seco parece erro, não estilo |

## 2. Receita aprovada (v2)

### Enquadramento e ritmo
- **Rosto em tela cheia o vídeo inteiro** (`layout: cover`). Nada de metade de tela vazia.
  A fonte em baixa resolução fica um pouco suave; isso foi aceito, a tela vazia não.
- **Punch-in alternado a cada corte**: aberto (1,0) ↔ fechado (1,12 a 1,18). Isso transforma
  o jump cut em ritmo.
- **Zoom lento nas frases-chave** (`zoom: {"from": 1.0–1.05, "to": 1.2}`): na tese, na sacada
  e no fechamento. Teto de 1,2 para fonte 720p.
- Seleção em texto, cortes nas pausas medidas (`silencedetect` / `vedit silences`), ordem da
  fala preservada, sem trecho confuso de matemática.

### Legenda
- **Montserrat Black** (OFL), caixa alta, **tamanho 138** em 1080x1920, contorno 9, sombra 3,
  centro em y ≈ 0,70 (sobre o peito, longe do rosto).
- **Karaoke**: a palavra falada acende em amarelo `#FFD400`, o resto fica branco. No máximo
  3 palavras por bloco, com quebras semânticas manuais (ponto final no `words.json`).
- **Sem pontuação** na tela ("." e "," removidos; "?" e "%" ficam).
- **Pontes de gap**: buracos menores que 0,35 s entre blocos são fechados (sem piscar).
- **Muda (`--mute`)** sempre que o motion mostra a mesma frase: gancho, frase de impacto,
  cartão, checklist e fechamento. Legenda e motion nunca dizem a mesma coisa ao mesmo tempo.

### Motion (HyperFrames, uma trilha só)
- **Uma composição HyperFrames do comprimento do vídeo inteiro, fundo transparente**,
  renderizada em ProRes 4444 (`yuva444p12le`), sincronizada na timeline de saída. É mais
  coerente e barata que N cenas soltas, e o composite é um passo só (`vedit composite`).
- **Densidade**: um evento de motion a cada 2–4 s; o maior buraco aceito foi de ~4 s (só com
  legenda + zoom). Em 47 s foram 12 batidas.
- **Cada evento trava numa palavra falada** (entra 0,05–0,1 s antes dela).
- Tipos de batida usados (varie o registro entre vizinhas):
  1. **Gancho cinético** (0–2,3 s), palavras batendo, número gigante em amarelo.
  2. **Foto real em tela cheia** (cutaway com Ken Burns e whip/zoom-blur ≤ 0,25 s) com rótulo
     em cima: aparece onde a fala cita uma coisa concreta (o produto, a festa, o casamento).
  3. **Sticker pequeno de pergunta** no canto ("VENDER MAIS?").
  4. **Frase de impacto com negação**: "VENDER MAIS" com risco vermelho e tremida, e logo
     "VENDER MELHOR" batendo em amarelo e maior.
  5. **Contador** que pousa no número exatamente na palavra (1 → 500).
  6. **Chip de tempo** ("2 MESES / E MEIO DEPOIS").
  7. **Notificação de DM genérica** (sem logo nem marca), com a frase do caso.
  8. **Palavra-flash com ícone** ("A SACADA" + lâmpada).
  9. **Objeto desenhado em HTML** (cartão de visita 3D) cujo valor troca no tempo da fala.
  10. **Checklist de passos** com check amarelo em cada palavra-chave.
  11. **Fechamento** em amarelo, o maior texto do vídeo, com burst de moedas **atrás** do texto.
- **Sistema visual único**: branco, amarelo `#FFD400`, vermelho `#FF3B30` só para negação,
  preto translúcido nos cartões, Montserrat Black/ExtraBold + Anton para números.
- **Zonas**: rosto (y 80–800, x 250–850) nunca coberto por elemento opaco, exceto nas fotos
  em tela cheia; faixa da legenda (y 1250–1450) vazia quando a legenda está ativa; motion
  "solto" em y 840–1225 ou nos cantos de cima.

### Fotos de transição
- Fonte: Unsplash ou Pexels (licença livre). Confira cada imagem antes de usar: tem que
  mostrar o assunto, não pode ter marca d'água, logotipo nem **texto legível** (uma mesa com
  "Happy Birthday" foi trocada). Registre os links num `CREDITS.txt` e entregue junto.

### SFX
- Whoosh nas fotos, pop/click nos chips, impacto grave nos números e na frase de impacto,
  ping nos checks, som de notificação na DM. Trilha separada em −24 LUFS, misturada antes do
  master. SFX livres (os que vêm no catálogo do HyperFrames são de licença Pixabay).

### Áudio e entrega
- `vedit master` em −14 LUFS / −1,5 dBTP; `vedit verify --platform reels` aprovado.
- Aviso de "início com som alto" é aceitável quando a própria fonte começa na fala: diga isso.

## 3. Pipeline exato (o que funcionou)

```bash
vedit transcribe fonte.mp4 -o words.json        # depois: vedit digest; seleção só em texto
# EDL: todos os clipes cover, punch-in alternado e zoom ramp nas frases-chave
vedit cut --edl edl/final.json -o out/base.mp4
vedit captions words.json --edl edl/final.json -o out/leg.ass --style viral \
  --mode karaoke --max-words 3 --case upper --y 0.70 --font "Montserrat Black" \
  --size 138 --outline 9 --shadow 3 --accent "#FFD400" \
  --mute "0-2.3,10.1-12.45,30-37.7,39.1-47.2"
# motion: agente HyperFrames gera motion/out/overlay.mov (alpha) + sfx.wav na MESMA timeline
vedit composite --video out/base.mp4 --overlay motion/out/overlay.mov \
  --subs out/leg.ass --fontsdir fonts --sfx motion/out/sfx.wav -o out/comp.mov
vedit master out/comp.mov -o out/final.mp4
vedit verify out/final.mp4 --platform reels
```

Antes do brief de motion, gere a lista de palavras **na timeline de saída**
(`vedit captions ... --mode palavra --max-words 1 --srt`) e entregue-a ao agente: é ela
que sincroniza tudo.

## 4. Brief do agente de motion (modelo)

Dê ao agente (Opus, com as skills do HyperFrames): o vídeo base, a lista de palavras com
tempo de saída, as fontes, a paleta, as **zonas** (rosto, faixa da legenda, safe zone), os
**intervalos de legenda muda**, e um roteiro numerado de batidas com o texto exato e a
palavra-âncora de cada uma. Exija: saída com alpha conferida, `comp_check.mp4` com o base e
pelo menos 20 quadros revisados por ele mesmo, lista de todos os textos usados e créditos.
Depois **revise você** uma prancha de ~20 quadros e devolva as correções numeradas (ex.:
anel amarelo solto sobre o rosto, moedas cobrindo letras, texto da DM pequeno).

## 5. Linha de corte: checklist de aprovação

Reprove (não entregue) se qualquer item falhar:

- [ ] Nenhuma área da tela fica vazia, borrada ou "esperando overlay".
- [ ] Gancho animado e grande nos primeiros 2 s (não etiqueta, não caixinha).
- [ ] Legenda com altura de caixa alta ≥ ~95 px em 1080x1920, fonte black, contorno grosso,
      palavra ativa destacada, sem pontuação.
- [ ] Motion a cada 2–4 s, cada um ancorado numa palavra; nenhum buraco > ~4 s sem novidade
      visual (corte, zoom ou motion).
- [ ] Pelo menos 2 fotos reais em tela cheia onde a fala cita algo concreto.
- [ ] Pelo menos 1 frase de impacto tipográfica (com contraste, negação ou número).
- [ ] Punch-in alternado em todos os cortes; zoom lento nas frases-chave.
- [ ] Legenda muda onde o motion diz a mesma frase; legenda e motion nunca se sobrepõem.
- [ ] Nada opaco sobre o rosto; nada cortado pela safe zone; nenhum texto ilegível.
- [ ] Nenhum elemento solto que pareça bug (anéis, cursores, partículas sobre o texto).
- [ ] SFX presente e discreto; master −14 LUFS; `verify` aprovado.
- [ ] Lista de textos inventados e créditos das fotos entregues com o arquivo.

Custo de referência: o motion completo de 47 s levou ~1 h de agente; o resto (corte,
legenda, composite, master, verify) ~15 min.
