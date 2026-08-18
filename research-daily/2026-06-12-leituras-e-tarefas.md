# Pesquisa diária — 12/06/2026

Auxílio à escrita (BEPE) e à IC: o que ler e o que trabalhar hoje. Sem alterar código.

---

## 1. Artigos recomendados para leitura

Organizados pelos quatro pilares que a sua escrita precisa sustentar. Priorize os marcados com ⭐.

### A. Núcleo metodológico — modelo bietápico de dimensionamento PV+BESS

Estes são os artigos "espelho" do seu modelo; cite-os para posicionar a contribuição.

- ⭐ **A multi-year two-stage stochastic programming model for optimal design and operation of residential PV-battery systems** (Energy and Buildings, 2021). É o trabalho mais próximo da sua formulação: 1ª etapa = dimensionamento, 2ª etapa = operação por cenário, horizonte plurianual. Use para justificar a estrutura here-and-now / recourse e para comparar premissas.
- ⭐ **Optimal energy management and sizing of renewable energy and battery systems in residential sectors via a stochastic MILP model** (2020). Referência direta para "sizing + dispatch" em MILP estocástico residencial.
- **Stochastic multi-objective optimal sizing of BESS for a residential home** (Journal of Energy Storage, 2022). Útil se você quiser evoluir para multiobjetivo (custo vs. importação da rede / vs. ciclos).
- **Residential PV-battery scheduling with stochastic optimization and neural network-driven scenario generation** (Journal of Energy Storage, 2024). Conecta o seu modelo ao item C (geração de cenários data-driven).

### B. Resiliência / blecaute (o seu diferencial)

O tratamento de blecaute é o ponto mais original do seu modelo — vale fundamentar bem.

- ⭐ **Resilience-oriented optimization of hospital microgrids with critical load support using ESS and PV under grid outage conditions** (Scientific Reports, 2026). MILP com cenários de blecaute via Monte Carlo, métrica de *Energy Not Supplied* (ENS) e suporte a carga crítica. Traz duas ideias que você pode importar: (1) métrica ENS para quantificar resiliência em vez de só forçar `Pgrid=0`; (2) sensibilidade à *duração* do blecaute (a resiliência cai muito acima de 6 h sem sobredimensionar o BESS) — relevante porque o seu modelo fixa duração de 3 h.
- **Scenario-Based Stochastic MPC for Energy Hubs under Persistent Grid Outages** (arXiv 2604.18268, 2024). Modela blecautes com cadeia de Markov em tempo contínuo — referência para justificar (ou criticar) a sua hipótese de blecaute uniforme e independente.

### C. Geração e redução de cenários (lacuna atual: só 3 cenários ±50%)

Para a banca/BEPE, a forma como você constrói os cenários é um ponto frequentemente atacado. Leia ao menos um destes.

- ⭐ **An empirical analysis of scenario generation methods for stochastic optimization** (EJOR, 2016). Panorama comparativo (sampling, moment matching, clustering). Bom para a seção de metodologia justificar a escolha.
- **Multi-stage scenario generation by combined moment matching and scenario reduction** (Economic Modelling, 2014) — clássico de moment matching.
- **Scenario reduction and scenario tree generation using Sinkhorn distance** (Computers & Chemical Engineering, 2022) — abordagem recente, caso queira algo "estado da arte".

### D. Degradação da bateria (lacuna atual: BESS sem envelhecimento no horizonte de 25 anos)

- ⭐ **A MILP model for BESS sizing optimization considering aging effects and emission costs** (Journal of Energy Storage, 2025). Mostra como linearizar degradação dentro do MILP — diretamente aplicável.
- **Battery aging in multi-energy microgrid design using MILP** (Applied Energy, 2019). Clássico; relata que ignorar envelhecimento superdimensiona o storage (efeito de 6–92% no dimensionamento ótimo). Argumento forte para incluir degradação.
- **A stochastic method for behind-the-meter PV-battery sizing with degradation minimization by limiting battery cycling** (Journal of Energy Storage, 2024). Une estocástico + degradação — combinação exata do seu próximo passo natural.

---

## 2. O que trabalhar na IC hoje (sem mexer no código)

Tudo aqui é leitura, escrita ou análise no papel — coerente com "não alterar nada do código por hora". Listei em ordem de prioridade e separei em etapas independentes, para que cada uma possa ser concluída com qualidade mesmo que falte tempo.

### Tarefa 1 — Revisar uma hipótese de modelagem do blecaute (análise no papel) ⭐

Ao reler `v2.1.py` notei um ponto que vale verificar **antes** de escrever a metodologia, porque afeta a interpretação dos resultados:

> No objetivo, a OPEX é ponderada por `blackout_prob[b] · prob[s]`. Como `Σ_b blackout_prob[b] = 0,05` e `Σ_s prob[s] = 1,0`, o custo operacional total entra no VPL multiplicado por **0,05**. Não há um estado "sem blecaute" (95% do tempo) compondo a OPEX.

Hoje, sem tocar no código, vale: (a) confirmar no papel se essa era a intenção (modelo conta só o custo *durante* janelas de blecaute?) e (b) escrever meia página descrevendo como deveria ser a ponderação correta — tipicamente um cenário base "rede disponível" com peso 0,95 mais as 8 janelas somando 0,05. Isso vira uma decisão de modelagem documentada (e provável correção futura).

### Tarefa 2 — Escrever a seção "Formulação Matemática" do texto BEPE/IC ⭐

O README já tem a formulação em LaTeX praticamente pronta (objetivo, balanço de potência, estado de carga, exclusão mútua, blecaute). Hoje dá para transpor isso para o texto da pesquisa, acrescentando para cada conjunto de restrições uma frase de justificativa física/econômica e a citação dos artigos do bloco A. Etapa autocontida e de alto valor para o BEPE.

### Tarefa 3 — Redigir a revisão bibliográfica (1–2 páginas)

Com os artigos da Seção 1, escrever o "estado da arte" em quatro parágrafos: (1) dimensionamento bietápico PV+BESS, (2) resiliência/blecaute, (3) geração de cenários, (4) degradação. Em cada parágrafo, fechar com a lacuna que o seu trabalho preenche. Use os artigos ⭐ como âncora de cada parágrafo.

### Tarefa 4 — Montar a tabela comparativa "meu modelo vs. literatura"

Uma tabela (linhas = artigos do bloco A/B; colunas = bietápico? blecaute? degradação? geração de cenários data-driven? contexto Brasil/tarifa branca?). Ela evidencia visualmente a contribuição e costuma ser muito bem recebida em banca/avaliação FAPESP. Só leitura + síntese, sem código.

### Tarefa 5 (curta) — Anotar perguntas de pesquisa para o orientador

A partir das leituras de hoje, listar decisões em aberto: duração de blecaute fixa vs. variável; incluir degradação agora ou na próxima versão; trocar os 3 cenários por geração data-driven; e fundamentar o fator 0,7 de venda na regulação brasileira vigente (Lei 14.300/2022, REN ANEEL 1.000). Isso direciona a próxima reunião.

---

## 3. Sugestão de prioridade para hoje

Se o tempo for curto, faça **Tarefa 1** (análise da ponderação do blecaute — é a que mais protege a validade dos resultados) e comece a **Tarefa 2** (formulação no texto, que já está 80% pronta no README). As demais ficam para os próximos dias.

---

## Fontes

- [Multi-year two-stage stochastic model for residential PV-battery systems (Energy and Buildings, 2021)](https://www.sciencedirect.com/science/article/abs/pii/S0378778821001195)
- [Optimal energy management and sizing via stochastic MILP (2020)](https://www.researchgate.net/publication/342588439_Optimal_energy_management_and_sizing_of_renewable_energy_and_battery_systems_in_residential_sectors_via_a_stochastic_MILP_model)
- [Stochastic multi-objective optimal sizing of BESS for a residential home (2022)](https://www.sciencedirect.com/science/article/pii/S2352152X22023921)
- [Residential PV-battery scheduling with NN-driven scenario generation (2024)](https://www.sciencedirect.com/science/article/pii/S235248472400372X)
- [Resilience-oriented optimization of hospital microgrids under grid outage (Scientific Reports, 2026)](https://www.nature.com/articles/s41598-026-34992-x)
- [Scenario-Based Stochastic MPC for Energy Hubs under Persistent Grid Outages (arXiv, 2024)](https://arxiv.org/abs/2604.18268)
- [An empirical analysis of scenario generation methods for stochastic optimization (EJOR, 2016)](https://www.sciencedirect.com/science/article/abs/pii/S0377221716303411)
- [Multi-stage scenario generation: moment matching + reduction (2014)](https://www.sciencedirect.com/science/article/abs/pii/S0167637714000856)
- [Scenario reduction using Sinkhorn distance (2022)](https://www.sciencedirect.com/science/article/abs/pii/S0098135422004550)
- [MILP for BESS sizing considering aging and emission costs (2025)](https://www.sciencedirect.com/science/article/pii/S266695522500053X)
- [Battery aging in multi-energy microgrid design using MILP (2019)](https://www.sciencedirect.com/science/article/abs/pii/S0306261918315058)
- [Stochastic BTM PV-battery sizing with degradation minimization (2024)](https://www.sciencedirect.com/science/article/pii/S2352152X24007837)
