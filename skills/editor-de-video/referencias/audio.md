> **Leia quando** for tratar voz, escolher redutor de ruído, mixar música e efeitos, medir loudness ou entregar áudio para plataforma.
> **Comandos:** `vedit loudness`, `vedit master`, `vedit mix`, `vedit silences`, `vedit verify`. O agente **não ouve**: valide por números e peça ao humano para ouvir antes de publicar.

# Áudio

## 1. Diagnosticar antes de limpar

Meça (1 min): pico e clipping, ruído de fundo (RMS no percentil 10), fala (percentil 90), SNR (fala - ruído) e se os canais são a mesma fonte (`vedit probe` dá correlação L/R; já houve arquivo estéreo com R = L - 6 dB). SNR abaixo de ~20 dB com microfone distante indica **sala com eco**, não só ruído. Decida a ferramenta pelo diagnóstico, não por hábito: o mesmo redutor que salvou um vídeo estragou outro.

## 2. Redutor por tipo de gravação

| Gravação | Ferramenta | Artefato de usar a errada |
|---|---|---|
| Ruído constante, voz próxima do microfone (carro, ventilador) | rede neural leve, ex.: `arnndn` (RNNoise) com modelo adequado; `afftdn` sozinho não resolveu ruído de carro (fundo seguiu em -29 dB; RNNoise levou a ~-50 dB) | `afftdn` forte: voz aquosa |
| Voz distante + sala reverberante (reunião, palestra) | redutor/dereverberador mais forte (ex.: DeepFilterNet em binário, sem PyTorch); SNR medido subiu de 17 para 28 dB (natural) ou 38 dB (sem limite, forte) | RNNoise aqui gera som **metálico/aquoso**, e o compressor realça |
| Celular recente com áudio espacial de vários canais | gerar o mix de áudio no próprio aparelho antes de exportar (o ffmpeg pode não decodificar a faixa espacial) | enviar o arquivo cru sem tratar |
| Qualquer caso, se houver acesso | serviço web de realce de fala | timbre pode ficar artificial |
| Prevenção (o que mais melhora) | lapela sem fio no apresentador | |

- Sem poder ouvir, entregue **duas intensidades** (natural e forte) e deixe o humano escolher.
- Trocar só a voz não exige refazer o vídeo: congele a EDL, remonte a voz, regere o áudio e remuxe com `-c:v copy` (~minutos).

## 3. Compense a latência dos filtros

Redutores atrasam a saída: ~30 ms (1440 amostras a 48 kHz) no DeepFilterNet, ~10 ms no RNNoise. Sem compensar, a boca dessincroniza e o início das frases é cortado. **Meça o atraso por correlação cruzada** com o sinal original e descarte o equivalente em amostras.

## 4. Cadeia de voz (ponto de partida)

`pan` para mono se for caso -> `highpass=80` -> redutor (se o diagnóstico mandar) -> `acompressor` leve (ex.: threshold ~0,06, ratio 3, attack 4 ms, release 90 ms; ou threshold -20 dB, ratio 3:1) -> limitador. Limiares de silêncio (-35/-32 dB) **só valem sobre a voz já tratada e normalizada**: sobre áudio cru o ruído de fundo fica acima do limiar.

## 5. Loudness e true peak

| Item | Valor | Observação |
|---|---|---|
| Alvo de entrega (vídeo social) | **-14 LUFS integrado** | convenção de produção; as plataformas normalizam por conta própria e não publicam um número obrigatório para Reels/TikTok; **confirme** |
| True peak | **<= -1,5 dBTP** (default do `vedit master`; -1,0 é o mínimo comum) | margem para o AAC não clipar |
| Broadcast (referência) | EBU R128: **-23 LUFS +/- 0,5 LU** (página oficial aberta em 2026-11); o limite de true peak de -1 dBTP vem do documento completo, não confirmado na consulta | não use -23 em social: soaria baixo |
| `loudnorm` defaults do ffmpeg | I = -24, LRA = 7, TP = -2 (doc oficial) | passe sempre `I`, `TP` explícitos |
| Música sob voz | ~-24 a -27 LUFS (cerca de 10-13 dB abaixo da voz) | voz é prioridade |

`vedit master` faz `loudnorm` em duas passadas (mede, depois aplica com `measured_*` em modo linear quando possível) e `aresample=48000`, com vídeo copiado.

## 6. Armadilhas de medição

- **Mono duplicado em estéreo mede +3 LU** no `ebur128` (soma os canais). Normalize o stem já em estéreo; o contrário deixa a voz 3 dB baixa por canal.
- **Limitador de voz**: voz em -14 LUFS chegou a +1,1 dBTP. Um limitador com lookahead de ~5 ms (pico de -2,5 dBFS, 2-3 iterações de normalizar e limitar) trouxe a voz a ~-2,4 dBTP e o master ficou com < 1 dB de limitação.
- **`loudnorm` em modo dinâmico reamostra para 192 kHz** (doc oficial). Se a saída entra em `sidechaincompress` ou `amix` com stem de 48 kHz, o tempo desalinha: num caso real a música acabou aos 20 s num vídeo de 22 s e o cartão final ficou mudo. **Correção:** `aresample=48000` logo após todo `loudnorm`, `apad=whole_dur=<total>` em cada stem, `amix=duration=first:normalize=0`. Confira a duração de cada stem antes de mixar.
- Meça no **stem final** e no arquivo final: fade e limitador derrubam caudas e mudam junções.
- `afade=t=out:st=0:d=0` zera o áudio inteiro.

## 7. Mix com ducking por sidechain

```
voz:    highpass 80 -> acompressor -> asplit [vo][key]
música: atrim -> loudnorm I=-27 TP=-6 -> aresample=48000 -> fade in 0,2 / out 1,4
        -> sidechaincompress=threshold=0.02:ratio=4:attack=15:release=300 (key = voz) -> apad
sfx:    volume por tipo -> adelay -> amix -> apad
final:  amix=duration=first:normalize=0 -> loudnorm I=-14:TP=-1.5 -> aresample=48000
```

- Soa mais natural que ducking por expressão de volume. `vedit mix --voice --music --duck --music-lufs -27` implementa isso com stems alinhados em 48 kHz e duração exata.
- Dentro de expressões de `volume` do ffmpeg não existe `<` ou `>`: use `clip()`, com vírgulas escapadas.
- **Stems com a duração exata do vídeo**: `apad` + `atrim`. Ao muxar, use `-af apad -t <duração do vídeo>`; `-shortest` corta o cartão final.
- Ganhos de efeito relativos à voz (ponto de partida): impacto/clique/chime ~-10 dB do pico da voz; whoosh ~-9; teclas ~-16; riser ~-14. Pico de efeito nunca acima da voz.

## 8. Música e SFX sintetizados por código (sem licença de terceiros)

Quando não há faixa licenciada nem gerador com crédito, sintetize em NumPy a 48 kHz (custo zero, sem direitos):

| Elemento | Receita genérica |
|---|---|
| Música "leve/pop" | progressão I-V-vi-IV, acordes dedilhados (pluck de ~6 harmônicos), a partir do 2º compasso bumbo 1/3, palma 2/4, shaker em colcheias, baixo; pad suave; saturação `tanh`; 108-118 bpm |
| Música "tensa/ritmada" | ~110 bpm, bumbo 1 e 3, estalo, hi-hats, pad de serras desafinadas com passa-baixa ~1,4 kHz, baixo |
| Whoosh | ruído em banda com varredura (ex.: 500 -> 3800 Hz) |
| Pop | seno com pitch subindo |
| Brilho (sparkle) | ~5 sinos em escada (E6-C8) + shimmer |
| Impacto | seno com queda de pitch + ruído filtrado |
| Riser | ruído/tons crescentes terminando **exatamente** na junção |
| Água despejando | ruído em banda ~700 -> 520 Hz com turbulência + dezenas de bolhas (senos curtos com pitch subindo) |
| Sucção/aspirador | banda ~1,1-1,7 kHz com modulação + zumbido de motor ~118 Hz com harmônicos |

Uma trilha diferente por vídeo (muda andamento e tom). Substituir por som melhor: salvar outro wav com o mesmo nome e refazer o mix.

## 9. Colocação de SFX

- **Whoosh centrado no meio do movimento mais rápido** (o pico a poucos ms do ponto de maior velocidade).
- **Riser termina exatamente na junção** (último sample não nulo na emenda).
- **Um SFX por evento visual**; sem evento, sem som. Efeito não explica piada nem substitui contexto.
- **Som com significado vence som genérico**: água no balde, sucção do aspirador ilustram o serviço; whoosh em tudo vira ruído.
- Música sem informação essencial; o vídeo precisa funcionar sem ela.

## 10. O agente não ouve

Valide por números: LUFS integrado, true peak, RMS da cauda de música (música audível até o fim), duração de cada stem, silêncio nas bordas (`vedit edges`), correlação L/R. Declare isso no relatório e **peça ao humano para ouvir** antes de publicar. Nunca mande preview com voz sintética "de teste" robótica: o humano rejeita o preview inteiro.

## 11. Higiene de direitos

- Música de terceiros, trilha em carro/ambiente (funk, playlist) e letras: **não use** sem licença; troque por trilha sintetizada ou livre de direitos documentada.
- Palavrões e fala de terceiros: corte; confira o contexto do anúncio.
- Voz sintética em anúncio pago: confira a licença comercial do plano (ver `narracao-tts.md`).
- Em Reels/TikTok orgânicos, o catálogo de músicas da própria plataforma tem regras de uso comercial próprias; para conteúdo de marca/anúncio use sons autorizados para negócios.

## 12. Observado em referências

Medido em 12 vídeos verticais publicados (observado, sem dados de desempenho: não prova que funciona).

- **Loudness**: 8 de 12 ficam a ~1 dB de -14 LUFS; três ficam entre -16,4 e -17,1. Isso confirma -14 LUFS como alvo, sem torná-lo regra.
- **True peak**: passa de -1 dBTP em 6 de 12 (um acima de 0). Não copie: mantenha -14 LUFS e **<= -1,5 dBTP** (seção 5); pico acima disso é risco de clipar no AAC, não estilo.
- **Trilha**: nas peças de talking head/entrevista, **nenhuma trilha audível detectada**. Em três delas o nível nas lacunas entre palavras ficou 14-16 dB abaixo da fala. Limite do método: uma trilha mais de ~10 dB abaixo da voz não é resolvida assim, então isto não quer dizer "sem música".
- **Silêncios**: removidos de forma agressiva; uma peça não tem nenhuma lacuna entre palavras >= 0,4 s.
- **SFX nos cortes**: nada detectável acima do acaso. Limite: a maioria dos cortes cai sobre fala.

Conclusão: **só voz, com silêncios curtos e loudness correto, é um padrão válido para talking head**. Música é escolha, não requisito; a seção 9 já diz que o vídeo precisa funcionar sem ela. Quando houver trilha, a seção 7 vale.

## Fontes
- EBU R128, https://tech.ebu.ch/publications/r128 (aberta em 2026-11: -23 LUFS, tolerância +/- 0,5 LU; limite de true peak não constava na página).
- FFmpeg Filters Documentation, https://ffmpeg.org/ffmpeg-filters.html (aberta em 2026-11: defaults do `loudnorm`, `dual_mono`, nota de upsampling a 192 kHz, `silenceremove`, `sidechaincompress`).
- Receitas de síntese, ducking e latências: medições operacionais próprias; seção 12: medição em 12 vídeos de referência.
