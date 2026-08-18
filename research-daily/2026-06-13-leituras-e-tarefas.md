# Pesquisa diária — 13/06/2026

Continuação do apoio à escrita (BEPE) e à IC. Entrada **complementar** à de 12/06 — não repete os artigos e tarefas de ontem. Hoje o foco está em três frentes metodológicas que a leitura do `v2.1.py` revelou e que ainda não estavam cobertas: (1) condição de estado de carga terminal/cíclico, (2) quantificação do valor da estocasticidade (VSS/EVPI), e (3) fundamentação regulatória do fator de venda 0,7. Sem alterar código.

---

## 1. Três observações novas no código (análise no papel)

Relendo `v2.1.py` para hoje, três pontos se destacam — distintos da ponderação do blecaute discutida ontem. Documentá-los já adianta a seção de metodologia e antecipa críticas de banca.

### 1.1. Não há condição de SoC terminal — a bateria "esvazia de graça" no fim do dia ⭐

A recursão de energia (`bess_energy_rule`) parte de `E_bess_init` (1ª etapa) em `t=0`, mas **nenhuma restrição obriga o SoC final (`t=23`) a voltar ao nível inicial**. Como o objetivo penaliza importação da rede, o otimizador tende a descarregar a bateria até o fim do dia sem precisar recarregá-la — energia que aparece como "grátis". Mas o dia é depois multiplicado por 365 no OPEX, ou seja, é tratado como representativo de um dia típico que se repete. Isso introduz um viés sistemático: subestima o custo operacional e pode subdimensionar o BESS.

A correção usual é uma **condição cíclica** `E_bess[s, 23, b] == E_bess_init` (ou `>= E_bess_init`), garantindo que cada dia "devolva" o que consumiu. Vale escrever meia página comparando as duas opções (igualdade estrita vs. piso) e suas implicações no dimensionamento. É uma decisão de modelagem documentada e provável correção futura.

### 1.2. Restrição de C-rate replicada 24× sobre `m.T`

`befficiency_limit` é definida sobre `m.T`, gerando 24 cópias idênticas de `BESS_Pmax <= BESS_capacity * 0.5` (nenhuma depende de `t`). O próprio comentário do código já aponta a alternativa correta: `pyo.Constraint(expr=m.BESS_Pmax <= m.BESS_capacity * 0.5)`. Não muda a solução, mas infla o modelo e atrapalha a contagem de restrições que costuma entrar no texto. Anotar como ajuste de limpeza.

### 1.3. Limite inferior de `Pgrid` em −5 kW, assimétrico ao `Pmax_grid` de 20 kW

`m.Pgrid` tem `bounds=(-5, Pmax_grid)`, mas a venda (`Pgrid_sell`) é limitada a `Pmax_grid = 20`. O piso de −5 limita a injeção a 5 kW de forma implícita e silenciosa — provavelmente não intencional. Vale confirmar no papel qual é o limite físico real de injeção do contrato/inversor e registrar a hipótese, porque isso afeta diretamente quanto excedente solar o modelo pode monetizar.

---

## 2. Artigos recomendados para leitura (novos — não repetem 12/06)

### A. Avaliação do modelo estocástico: VSS e EVPI ⭐

Esta é a lacuna mais importante para o rigor do BEPE: o trabalho **afirma** ser estocástico, mas ainda não **quantifica** o ganho de sê-lo. Reportar VSS e EVPI é praticamente esperado em avaliação FAPESP.

- ⭐ **The value of the stochastic solution in multistage problems** (Escudero et al., *TOP*, 2007). Define formalmente VSS e EVPI e estende para múltiplos estágios. Base teórica para a sua seção de avaliação.
- **Performance of stochastic programming solutions** (Maggioni & Wallace). Discute cotas e medidas de qualidade da solução estocástica — útil para interpretar VSS pequeno vs. grande.

Como aplicar (sem código hoje, só o plano): VSS = EEV − RP, onde RP é o ótimo do seu modelo (já o tem), e EEV é o custo de **fixar** o dimensionamento obtido resolvendo o problema do valor esperado (cenário base apenas) e depois avaliá-lo em todos os cenários. EVPI = RP − WS, onde WS é a média dos ótimos resolvidos cenário a cenário com informação perfeita. Vale escrever o passo a passo desses três experimentos para rodar depois.

### B. Operação em horizonte rolante / SoC terminal (fundamenta a observação 1.1)

- ⭐ **Optimal Battery Energy Storage Dispatch for the Day-Ahead Electricity Market** (*Batteries*, MDPI, 2024). Trata explicitamente a continuidade do SoC entre dias e a imposição de SoC terminal — referência direta para justificar a restrição cíclica.
- **Rolling intrinsic for battery valuation in day-ahead and intraday markets** (arXiv 2510.01956, 2025). Mostra por que otimizar um dia isolado superestima o valor da bateria, e como reformular limites anuais (ex.: ciclos) em restrições diárias equivalentes — conecta também com degradação (pilar D de ontem).

### C. Contexto regulatório brasileiro: o fator 0,7 e a tarifa ⭐

O `0.7 * tariff` na venda é hoje um número "mágico". Fundamentá-lo na regulação vigente fortalece muito a defesa e diferencia o trabalho da literatura internacional.

- ⭐ **Lei nº 14.300/2022 — Marco Legal da Microgeração e Minigeração Distribuída** (texto oficial, MME). Institui o Sistema de Compensação de Energia Elétrica (SCEE) e o pagamento gradual da TUSD **Fio B** sobre a energia injetada. É exatamente o mecanismo que o seu fator 0,7 tenta aproximar: a energia injetada deixa de ser compensada 1:1 e passa a ter desconto crescente.
- **Análises do marco legal da GD** (resumos técnicos). Apontam redução média de compensação da ordem de ~31% (componente Fio B) e a transição escalonada (Fio B cobrado em percentuais crescentes ao longo dos anos até 2029). Útil para argumentar que o fator de venda **deveria ser dependente do ano** dentro do horizonte de 25 anos — em vez de um 0,7 fixo.

---

## 3. O que trabalhar na IC hoje (sem mexer no código)

Em ordem de prioridade, etapas independentes para que cada uma feche com qualidade mesmo faltando tempo.

**Tarefa 1 — Documentar a condição de SoC terminal (observação 1.1).** ⭐ Escrever meia a uma página: descrever o viés atual, formular a restrição cíclica (igualdade e piso), e explicar o impacto esperado no dimensionamento. Ancorar nos artigos do bloco B. É a tarefa que mais protege a validade dos resultados hoje.

**Tarefa 2 — Planejar a avaliação VSS/EVPI no papel.** ⭐ Redigir o protocolo dos três experimentos (RP, EEV, WS), com as fórmulas VSS = EEV − RP e EVPI = RP − WS, e uma frase sobre como cada um será implementado a partir do modelo atual. Vira uma subseção pronta de "Avaliação do modelo" e uma lista de execução para quando voltar ao código.

**Tarefa 3 — Fundamentar o fator de venda 0,7 na Lei 14.300.** ⭐ Um a dois parágrafos ligando o `0.7 * tariff` ao desconto da TUSD Fio B do SCEE, registrando que o valor correto é escalonado por ano até ~2029 e que o modelo hoje usa um proxy constante. Decisão de modelagem documentada + provável melhoria futura.

**Tarefa 4 — Anotar os ajustes 1.2 e 1.3 como "dívida técnica de modelagem".** Lista curta para a próxima sessão de código: (a) trocar a restrição de C-rate replicada por uma única `Constraint(expr=...)`; (b) revisar o piso −5 kW de `Pgrid` e alinhá-lo ao limite real de injeção. Só registro, sem alterar nada.

**Tarefa 5 (curta) — Atualizar as perguntas para o orientador.** Acrescentar às de ontem: (i) impor SoC terminal por igualdade ou por piso? (ii) reportar VSS/EVPI já nesta etapa do BEPE? (iii) tornar o fator de venda dependente do ano conforme o cronograma da Lei 14.300? (iv) qual o limite contratual real de injeção na rede?

---

## 4. Sugestão de prioridade para hoje

Se o tempo for curto: **Tarefa 1** (SoC terminal — maior risco à validade) e **Tarefa 2** (protocolo VSS/EVPI — alto valor para o BEPE e ainda não existia no texto). A Tarefa 3 é rápida e fecha um ponto que a banca certamente questionaria.

---

## Fontes

- [The value of the stochastic solution in multistage problems (TOP, 2007)](https://link.springer.com/article/10.1007/s11750-007-0005-4)
- [Performance of stochastic programming solutions (Operations Research)](https://ap-rg.eu/wp-content/uploads/2020/05/Performance.pdf)
- [Optimal Battery Energy Storage Dispatch for the Day-Ahead Electricity Market (Batteries, MDPI, 2024)](https://www.mdpi.com/2313-0105/10/7/228)
- [Rolling intrinsic for battery valuation in day-ahead and intraday markets (arXiv, 2025)](https://arxiv.org/pdf/2510.01956)
- [Lei nº 14.300/2022 — texto oficial (MME)](https://www.gov.br/mme/pt-br/acesso-a-informacao/legislacao/leis/lei-n-14-300-2022.pdf/view)
- [Análise completa do Marco Legal da GD — Lei 14.300/2022](https://energiasroraima.com.br/wp-content/uploads/2022/04/Analise-Completa-Marco-Legal-da-GD-Lei-14.300-de-2022.pdf)
