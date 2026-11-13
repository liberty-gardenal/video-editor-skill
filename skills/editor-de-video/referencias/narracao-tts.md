> **Leia quando** o vídeo usa narração sintetizada (TTS) ou gravada em um único take: escrever o roteiro, chamar uma API de voz, cortar um take em um arquivo por cena e derivar a duração das cenas.
> **Provider-agnóstico:** vale para qualquer serviço de TTS. Nunca procure chaves de API na máquina: pergunte ao humano.

# Narração (TTS) e corte do take

## 1. Fluxo

```
roteiro por cena -> TTS (manual na interface do serviço ou por API) -> transcrição por palavra
-> âncoras (última palavra de cada cena) -> cortar o take em 1 arquivo por cena
-> apertar pausas -> retranscrever cada pedaço (verificar) -> duração de cada cena = duração da voz
-> mix (-14 LUFS) -> `vedit verify`
```

Dois caminhos: **manual** (o humano gera na interface, escolhe e ajusta a voz, e manda o áudio; o mais comum e o que preserva o gosto dele) e **API** (frase a frase por código, já cortada por cena e em cache). Em ambos, o resto do fluxo é igual.

## 2. Escrever o roteiro para a voz

| Regra | Motivo |
|---|---|
| Frases **curtas, uma por cena** | o TTS respira em ponto final e reticências; cena = frase facilita o corte e a âncora |
| **Números por extenso** do jeito que devem ser lidos ("duzentos e oitenta e nove"); na tela vai "R$ 289" | o TTS lê algarismos de modos imprevisíveis (ano, telefone, moeda) |
| Evitar reticências e travessões para pausa dramática | geram pausas longas que depois precisam ser cortadas |
| Siglas e marcas lidas por extenso ou com grafia fonética combinada | pronúncia previsível; conferir na retranscrição |
| **Linha em branco entre roteiros** quando gerar vários num só take | a pausa entre eles vira o ponto de corte |
| Texto de tela != fala | a tela leva a versão curta (3-6 palavras); a voz explica |
| Entregar ao humano o texto em blocos prontos para colar, com voz e ajustes sugeridos | evita retrabalho de formatação |
| CTA de baixo atrito; sem afirmação proibida pelo cliente ou pela política ("o mais barato", "100%") | anúncio reprovado custa mais que a copy |

Voz: tom de conversa em geral rende melhor que locução; estabilidade média e similaridade média-alta foram bem recebidas num caso (ajustes e nomes variam por serviço: registre os usados). O humano escolhe; o agente não decide gosto.

## 3. Higiene de API (provider-agnóstica)

- **Chave:** nunca procurar em variáveis, arquivos `.env`, chaveiro ou histórico da máquina; isso é exploração de credencial e é bloqueado. **Peça ao humano** a chave ou o áudio pronto. Não copie a chave para arquivos novos, notas ou logs; leia de variável de ambiente fornecida por ele.
- **Cache por hash do texto** (+ voz + parâmetros + modelo): não pague duas vezes pela mesma frase; trocar um trecho do roteiro refaz só aquela frase.
- **Retry com backoff** em 429 e 5xx; **concorrência baixa** (ex.: 3) respeitando o limite do plano.
- Confira a **cota** antes de lotes (planos gratuitos costumam ter poucos milhares de caracteres por mês e sem clonagem de voz) e avise o humano do consumo estimado.
- Valide o formato da chamada na **documentação atual** do provedor antes de usar um endpoint que nunca rodou; formatos mudam.
- Guarde por frase: texto, parâmetros, hash, caminho do áudio, duração. Isso alimenta a duração das cenas.
- **Licença comercial:** planos gratuitos costumam **não** cobrir uso comercial (às vezes exigem atribuição). Para **anúncio pago**, a narração tem de sair de plano pago com direito comercial; confirme com o humano qual conta gerou o áudio e guarde o comprovante. Vozes clonadas ou "de biblioteca" têm termos próprios: leia-os. Marque o conteúdo sintético se a plataforma exigir rótulo de IA.

## 4. Cortar um take em um arquivo por cena

1. **Transcrever por palavra** (`vedit transcribe`, saída `words.json`). Com mais de um roteiro no take, transcreva cada parte separadamente.
2. **Âncoras:** liste a **última palavra de cada frase/cena** na ordem de leitura e ande pelo `words.json` para achar o intervalo de cada linha. Palavras repetidas exigem conferir a ocorrência.
3. **Ponto de corte:** a **janela de 20 ms mais silenciosa** (energia média móvel) entre o fim de uma linha e o começo da próxima. O ASR às vezes cola a palavra seguinte à anterior (gap < 0,12 s): nesse caso procure de `fim - 0,03 s` até `fim + 0,6 s`.
4. **Apertar o ritmo** (ffmpeg, por pedaço):

```
silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,
silenceremove=stop_periods=-1:stop_duration=0.14:stop_threshold=-40dB:stop_silence=0.1,
areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.04,areverse,
atempo=1.05,afade=t=in:d=0.01
```

   - Apara início e fim e limita toda pausa interna a ~0,1-0,14 s (`stop_periods` negativo remove silêncio no meio, conforme a doc do ffmpeg).
   - **`atempo`:** 1,05x ainda soa natural; 1,10x foi o limite aceitável em um caso; acima disso a voz soa acelerada e artefatos aparecem. A faixa aceita pelo filtro varia por versão (tradicionalmente 0,5-2,0; encadeie para extremos), mas o limite é perceptual, não técnico.
   - Se o humano pediu "mais dinâmico, tem muitas pausas": resultado típico de ~15-17% de redução da fala sem perder palavra.
5. **Verificar:** **retranscreva cada pedaço** e compare com o texto do roteiro. Acha-se palavra cortada sem precisar ouvir; ainda assim o humano ouve.
6. Narração que já vem ritmada: só corte e normalize. Narração com respiros longos: remova pausas (detecção a -40 dB, ~0,22 s, manter ~0,07 s) e acelere pouco; se a meta de duração for impossível sem cortar fala, avise o humano em vez de forçar.

## 5. Um arquivo por cena é melhor que um stem único

- A duração da cena **vem da voz**, não de um relógio: `dur = max(minimo, 0,06 + duracao_da_voz + 0,1)` arredondada a quadro; cartão final `+ ~1,4-1,6 s` de hold após a última palavra (reduza para ~1,0 se parecer longo).
- Trocar uma frase não desloca o resto da timeline; refaz só aquela cena (cache por cena com chave `(cena, dur, assets)`).
- No mix, posicione cada `voz_i` com `adelay` no início da sua cena; depois `highpass=80` + `acompressor` leve. A voz também é a *chave* do sidechain da música (ver `audio.md`).
- **Fala longa (> ~4 s)**: divida a cena em 2 tomadas/visuais para nada ficar parado mais de ~3 s.
- Cena sem fala (apenas visual) usa duração mínima (~1,4 s).

## 6. Prévia e aprovação

- **Nunca** mostre preview com voz de sistema robótica como placeholder: o humano rejeita o preview inteiro (e sem música também). Peça a narração real ou gere por API antes de montar o preview.
- Fluxo seguro: preview 540x960 com a voz real -> lista de textos inventados e números -> aprovação -> final 1080x1920.
- Avise quando a duração final fugir da meta (ex.: narração de 45 s para uma meta de 30-35 s) e proponha cortes de roteiro, não de fala aleatória.
- O agente não ouve: valide a voz por transcrição, loudness e duração; peça ao humano para ouvir (ver `audio.md`, seção 10).

## 6b. Exemplo genérico de roteiro e tabela de cenas

Roteiro (uma frase por cena; números por extenso):

```
Seu sofá já foi novo. Lembra?

Umidade, areia e animais deixam sujeira funda.

Aspirar só tira a camada de cima.

Nós extraímos o resto com água quente.

Mesmo sofá. Sem filtro.

Nota quatro vírgula nove no Google.

Mande uma foto no WhatsApp e receba o preço em minutos.
```

| Cena | Tela (3-6 palavras) | Voz | Duração |
|---|---|---|---|
| 1 | "Lembra do dia um?" | frase 1 | 0,06 + voz + 0,1 (mín. 1,4 s) |
| 2-4 | dor, mecanismo, prova | frases 2-4 | idem; voz > 4 s = 2 tomadas |
| 5 | antes/depois dividido | frase 5 | idem |
| 6 | nota e oferta | frase 6 | idem |
| 7 | cartão final: ação única + telefone | frase 7 | idem + hold de 1,4-1,6 s |

Os dados do exemplo são inventados; a nota e o preço reais vêm do cliente e são conferidos antes de ir ao ar.

## 7. Checklist

- [ ] Roteiro em frases curtas, números por extenso, blocos separados por linha em branco
- [ ] Plano/licença do TTS confere com o uso (pago/comercial para anúncio)
- [ ] Chave fornecida pelo humano; nada procurado na máquina
- [ ] `words.json` do take; âncoras conferidas (ocorrência correta)
- [ ] Cortes na janela de 20 ms mais silenciosa; sem palavra cortada (retranscrição)
- [ ] `atempo` <= 1,10; pausas internas <= ~0,14 s
- [ ] Duração de cada cena derivada da voz; cartão final com hold
- [ ] Mix -14 LUFS / -1,5 dBTP; preview com voz real aprovada

## Fontes
- FFmpeg Filters Documentation, https://ffmpeg.org/ffmpeg-filters.html (aberta em 2026-11: semântica de `silenceremove` com `stop_periods` negativo).
- TikTok, "Creative best practices", https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en (aberta em 2026-11: usar som/música e voz em criativo pago).
- Parâmetros de corte, `atempo` e duração por cena: medições operacionais próprias. Termos de licença de cada provedor de TTS: **não consultados**; leia a política atual do provedor.
