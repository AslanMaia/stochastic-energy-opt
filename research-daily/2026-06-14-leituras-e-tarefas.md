# Pesquisa diária — 14/06/2026

Continuação do apoio à escrita (BEPE) e à IC. Entrada **complementar** às de 12/06 e 13/06 — não repete artigos nem tarefas já listados. Os dias anteriores cobriram: ponderação do blecaute, formulação no texto, revisão bibliográfica, tabela comparativa, degradação, geração de cenários (12/06); SoC terminal, C-rate replicada, piso −5 kW do `Pgrid`, VSS/EVPI, fator 0,7 / Lei 14.300 (13/06).

Hoje o foco está em três frentes ainda **não tocadas**, que a releitura do `v2.1.py` evidencia e que são caras a uma banca FAPESP: (1) o objetivo é **risco-neutro** (valor esperado) num trabalho cujo diferencial é resiliência; (2) a **estrutura de correlação dos cenários** é forte e implícita; (3) o horizonte de 25 anos é representado por **um único dia típico × 365**, sem sazonalidade nem escalonamento tarifário. Sem alterar código.

---

## 1. Três observações novas no código (análise no papel)

Distintas das de 12/06 e 13/06. Documentá-las já adianta a metodologia e antecipa críticas.

### 1.1. O objetivo é risco-neutro — incoerência com o discurso de resiliência ⭐

O `objective_rule` minimiza o **valor esperado** do VPL: a OPEX entra ponderada por `prob[s] · blackout_prob[b]` e somada. Isso é uma formulação **risco-neutra**: trata um custo altíssimo num cenário de blecaute exatamente como trata uma pequena economia no cenário base, desde que as médias se compensem. Mas o argumento central do trabalho é justamente proteger o usuário contra eventos **de cauda** (blecaute, alta demanda). Um decisor avesso a risco não quer minimizar a média — quer limitar o pior caso.

A ferramenta padrão é incorporar uma medida de risco como o **CVaR (Conditional Value-at-Risk)** ao objetivo, tipicamente como `(1−κ)·E[custo] + κ·CVaR_α[custo]`, penalizando a cauda dos cenários mais caros. É linearizável (Rockafellar & Uryasev) e cabe direto num MILP. Vale escrever meia a uma página: (a) explicitar que o modelo atual é risco-neutro; (b) formular a variante com CVaR; (c) argumentar que reportar a fronteira custo-esperado × CVaR é o que conecta numericamente o modelo ao discurso de resiliência. É, hoje, a lacuna conceitual de maior valor para o BEPE.

### 1.2. Os cenários embutem uma correlação PV↔demanda perfeita (e não declarada)

Nos `scenarios`, "alta_demanda" combina demanda +50% **com** PV −50%, e "alta_geracao" combina demanda −50% **com** PV +50%. Ou seja, os dois piores/melhores fatores estão **perfeitamente anticorrelacionados e colados** — não há, por exemplo, um cenário "alta demanda + alta geração". Isso é uma hipótese de dependência forte, provavelmente conservadora no eixo demanda, mas que reduz drasticamente o espaço amostral (3 cenários sobre 2 fontes de incerteza que poderiam gerar 4+ combinações). Para a banca, é um ponto frágil: "por que esses três pontos?". Vale documentar a estrutura de correlação assumida e registrar como melhoria a separação dos fatores (PV e demanda como incertezas próprias, com sua matriz de correlação).

Subponto físico relacionado: em "alta_geracao", `P_pv_used = v · 1.5 / max(P_pv_data)`, cujo **pico passa de 1,0** — isto é, o perfil pede do gerador **mais que a potência nominal** `PV_Pmax`. Como `P_pv` multiplica `PV_Pmax`, o cenário de alta geração entrega até 1,5× a placa instalada, o que é fisicamente limitado por *clipping* do inversor. Anotar como hipótese a revisar (capacidade × fator de capacidade).

### 1.3. Um único dia típico × 365 — sem sazonalidade nem escalonamento de preço

A OPEX anual é `365 · (custo do dia)`, e o VPL repete esse mesmo valor por 25 anos descontado a `r=0,05`. Duas simplificações se escondem aí: (i) **um só dia representa o ano inteiro** — não há dia de verão vs. inverno, útil vs. fim de semana, que mudam muito o perfil PV e a demanda e, portanto, o dimensionamento ótimo; (ii) o custo operacional é **constante em termos nominais** ao longo de 25 anos — sem reajuste tarifário/inflação de energia (o comentário `# r. infl` sugere que `r` mistura desconto e inflação, mas não há escalonamento explícito do preço da energia). Vale registrar ambas como hipóteses e apontar o caminho usual: **dias representativos** (clustering sazonal, incluindo dias extremos) e uma trajetória de preço da energia ao longo do horizonte.

---

## 2. Artigos recomendados para leitura (novos — não repetem 12–13/06)

### A. Aversão a risco / CVaR em dimensionamento estocástico ⭐

Esta é a frente mais importante de hoje: dá rigor ao "diferencial de resiliência".

- ⭐ **Optimization of Conditional Value-at-Risk** (Rockafellar & Uryasev, *Journal of Risk*, 2000). Artigo fundador do CVaR e de sua linearização — a base teórica para introduzir risco no seu MILP. Cite-o ao formular a variante risco-averso.
- ⭐ **Economic-environmental analysis of a renewable-based microgrid under a CVaR-based two-stage stochastic model** (*Sustainable Cities and Society*, 2021). Exemplo direto de CVaR acoplado a um modelo estocástico bietápico de microrrede em MILP — espelha exatamente o passo que o seu trabalho pode dar.
- **Risk-averse microgrid planning/operation under demand uncertainty and storage degradation** (*Computers & Industrial Engineering*, 2026). CVaR sobre o custo de 2ª etapa para proteger contra cenários extremos de demanda; conecta risco + degradação (pilar D de 12/06).
- **Risk-Averse Optimization for Resilience Enhancement of Complex Engineering Systems under Uncertainties** (arXiv, 2020). Bom para fundamentar conceitualmente "resiliência = controle de cauda", não média.

### B. Dias representativos e agregação temporal (fundamenta a observação 1.3) ⭐

- ⭐ **Time-series aggregation for the optimization of energy systems: goals, challenges, approaches** (*Optimization Online*, 2022). Panorama de referência: como escolher número de dias, e a recomendação prática de **incluir dias extremos** além dos agregados — diretamente aplicável ao seu caso, em que o blecaute é um "dia extremo".
- **Representative days selection for district energy system optimisation** (*Applied Energy*, 2019). Mostra que o dimensionamento ótimo muda de forma relevante conforme o número e a ordem dos dias representativos — argumento de que "um dia × 365" pode enviesar o seu resultado.
- **Improvement of representative days selection by incorporating extreme net-load days** (*Applied Energy*, 2020). Como garantir que a variabilidade/intermitência renovável seja capturada — útil se você for evoluir os cenários.

### C. Estrutura de correlação dos cenários (fundamenta a observação 1.2)

- Reaproveite o panorama de geração de cenários de 12/06 (**EJOR 2016**), mas leia-o agora com foco em **dependência/correlação** (moment matching preserva covariâncias; sampling de uma conjunta) — exatamente o que justifica trocar os 3 pontos colados por uma amostragem que respeite a correlação real PV↔demanda. (Sem nova fonte obrigatória; é releitura dirigida.)

---

## 3. O que trabalhar na IC hoje (sem mexer no código)

Etapas independentes, em ordem de prioridade, para que cada uma feche com qualidade mesmo faltando tempo.

**Tarefa 1 — Documentar a natureza risco-neutra do objetivo e esboçar a variante CVaR (observação 1.1).** ⭐ Meia a uma página: declarar que o modelo atual minimiza o valor esperado; escrever a forma `(1−κ)·E[·] + κ·CVaR_α[·]` e a sua linearização; explicar por que reportar a fronteira custo × risco é o que sustenta numericamente o discurso de resiliência. Ancorar em Rockafellar & Uryasev e no artigo CVaR-bietápico do bloco A. É a tarefa de maior valor conceitual hoje.

**Tarefa 2 — Escrever a subseção "Estrutura e correlação dos cenários" (observação 1.2).** ⭐ Tornar explícita, no texto, a hipótese de anticorrelação PV↔demanda hoje embutida; listar as combinações ausentes (ex.: alta demanda + alta geração); e registrar o fator de capacidade >1 do cenário de alta geração como hipótese a revisar. Decisão de modelagem documentada + crítica antecipada.

**Tarefa 3 — Redigir as hipóteses de "dia típico" e horizonte (observação 1.3).** Um a dois parágrafos: justificar o uso de um dia representativo × 365, apontar a ausência de sazonalidade e de escalonamento tarifário no VPL, e citar o caminho de dias representativos (bloco B) como melhoria futura — destacando que o blecaute deve ser tratado como "dia extremo" a incluir explicitamente.

**Tarefa 4 — Atualizar a "dívida técnica de modelagem" e as perguntas ao orientador.** Acrescentar às listas dos dias anteriores: (a) adotar objetivo risco-averso (CVaR) já nesta etapa do BEPE ou na próxima versão? (b) separar PV e demanda como incertezas próprias, com correlação explícita? (c) migrar de um dia típico para dias representativos sazonais? (d) modelar escalonamento do preço da energia ao longo dos 25 anos? Só registro, sem alterar código.

---

## 4. Sugestão de prioridade para hoje

Se o tempo for curto: **Tarefa 1** (risco-neutro × CVaR — é o elo que falta entre a formulação e a tese de resiliência) e **Tarefa 2** (estrutura dos cenários — ponto que a banca quase certamente questionará). A Tarefa 3 é rápida e fecha a discussão de horizonte/representatividade.

---

## Fontes

- [Optimization of Conditional Value-at-Risk (Rockafellar & Uryasev, Journal of Risk, 2000)](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf)
- [Economic-environmental analysis of a renewable-based microgrid under a CVaR-based two-stage stochastic model (Sustainable Cities and Society, 2021)](https://www.sciencedirect.com/science/article/abs/pii/S2210670721005527)
- [Risk-averse microgrid reconfiguration under demand uncertainty and storage degradation (Computers & Industrial Engineering, 2026)](https://www.sciencedirect.com/science/article/pii/S0360835226001270)
- [Risk-Averse Optimization for Resilience Enhancement of Complex Engineering Systems under Uncertainties (arXiv, 2020)](https://arxiv.org/pdf/2009.02351)
- [Time-series aggregation for the optimization of energy systems: goals, challenges, approaches (Optimization Online, 2022)](https://optimization-online.org/wp-content/uploads/2022/01/8753.pdf)
- [Representative days selection for district energy system optimisation (Applied Energy, 2019)](https://www.sciencedirect.com/science/article/abs/pii/S0306261919306622)
- [Improvement of representative days selection by incorporating extreme net-load days (Applied Energy, 2020)](https://www.sciencedirect.com/science/article/abs/pii/S0306261920307364)
