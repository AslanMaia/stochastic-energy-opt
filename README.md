# Stochastic Energy Management for Residential Energy Communities

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Pyomo](https://img.shields.io/badge/Optimization-Pyomo-orange)
![Solver](https://img.shields.io/badge/Solver-Gurobi-green)
![FAPESP](https://img.shields.io/badge/Funding-FAPESP-red)
![UNICAMP](https://img.shields.io/badge/Institution-UNICAMP-blue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> *Undergraduate research project (Iniciação Científica) — CPTEn / FEEC / UNICAMP*

---

## What This Project Does

Solar generation peaks at noon. Electricity prices peak in the evening. Demand is unpredictable. Grid outages happen.

This repository implements a **two-stage stochastic MILP** that decides — before the day unfolds — the optimal sizing of a residential solar PV system and battery storage (BESS), minimizing the net present value (NPV) of total investment and operational costs over a 25-year horizon across all plausible scenarios of generation, demand, and grid availability.

Rather than optimizing for a single forecast, the model hedges: it commits to sizing decisions robust enough to perform well whether tomorrow is sunny, cloudy, high-demand, or affected by a blackout.

---

## Mathematical Formulation
# Stochastic Operation of an Export-Constrained Energy Community with Hybrid Battery--Hydrogen Storage

---

## 1. Summary

This work summarizes a candidate mathematical formulation for a grid-connected energy community (EC) operated by a centralized energy management system (EMS). The EC consists of several users, each with individual photovoltaic (PV) generation and demand, and shared community assets: a battery energy storage system (BESS) and a hydrogen energy storage system (HESS), composed of an electrolyzer, hydrogen tank, and fuel cell. The EC is connected to the main grid through a point of common coupling (PCC).

The proposed formulation follows a two-stage stochastic structure over a multi-day horizon. The first-stage decisions are common to all scenarios, whereas the second-stage decisions adapt to the realized PV and demand scenario. The model minimizes the expected operating cost of the community while:

1. Limiting or discouraging surplus export to the distribution grid.
2. Guaranteeing that all members obtain nonnegative expected gains with respect to their standalone operation.
3. Optionally imposing carbon-emission limits or using a multi-objective cost--emission framework.

---

## 2. Sets and indices

| Symbol | Description |
| :--- | :--- |
| $\mathcal{I}$ | Set of users/community members, indexed by $i$ |
| $\mathcal{T}$ | Set of time periods, indexed by $t$ |
| $\mathcal{T}^{1}$ | First-stage periods, e.g., day 1 |
| $\mathcal{T}^{2}$ | Second-stage periods, e.g., days 2--3 |
| $\Omega$ | Set of scenarios, indexed by $\omega$ |

The time horizon is partitioned as:
$$ \mathcal{T}=\mathcal{T}^{1}\cup\mathcal{T}^{2} $$

---

## 3. Parameters

| Symbol | Description |
| :--- | :--- |
| $\pi_{\omega}$ | Probability of scenario $\omega$ |
| $\Delta t$ | Duration of each time period |
| $d_{i,t,\omega}$ | Demand of user $i$ at time $t$ in scenario $\omega$ |
| $\overline{p}^{PV}_{i,t,\omega}$ | Available PV generation of user $i$ |
| $\lambda^{buy}_{t}$ | Grid energy buying tariff |
| $\lambda^{sell}_{t}$ | Grid energy selling tariff |
| $\overline{P}^{imp}$ | Maximum import power at the PCC |
| $\overline{P}^{exp}_{t}$ | Maximum export power allowed at the PCC |
| $\eta^{B,ch}, \eta^{B,dis}$ | BESS charging and discharging efficiencies |
| $\sigma^{B}$ | BESS self-discharge rate per time step |
| $\underline{E}^{B}, \overline{E}^{B}$ | Minimum and maximum BESS state of charge |
| $\overline{P}^{B,ch}, \overline{P}^{B,dis}$ | Maximum BESS charging and discharging powers |
| $E^{B,ini}$ | Initial BESS state of charge |
| $\eta^{EL}$ | Electrolyzer conversion factor from electricity to hydrogen |
| $\eta^{FC}$ | Fuel-cell conversion factor from hydrogen to electricity |
| $\sigma^{H}$ | Hydrogen storage loss rate per time step |
| $\overline{H}$ | Maximum hydrogen inventory |
| $\overline{P}^{EL}, \overline{P}^{FC}$ | Electrolyzer and fuel-cell rated powers |
| $H^{ini}$ | Initial hydrogen inventory |
| $c^{curt}$ | PV curtailment penalty |
| $c^{B}$ | BESS cycling/operation cost coefficient |
| $c^{H2}$ | Hydrogen operation cost coefficient |
| $\rho^{exp}$ | Optional export penalty coefficient |
| $\gamma^{grid}_{t}$ | Grid emission factor |
| $\gamma^{H2}$ | Optional hydrogen-related emission factor, if applicable |
| $\overline{E}^{CO2}$ | Maximum expected carbon emissions |
| $\varepsilon$ | Minimum relative gain required for all users |

---

## 4. Standalone benchmark of each user

Before solving the coordinated EC model, the expected standalone cost of each user is computed. In standalone operation, user $i$ operates independently with its own PV, demand, and grid import/export, but without access to shared BESS, hydrogen storage, or community energy sharing.

The standalone power balance is:
$$ p^{imp,stand}_{i,t,\omega}+p^{PV,stand}_{i,t,\omega} =d_{i,t,\omega}+p^{exp,stand}_{i,t,\omega}, \quad \forall i\in\mathcal{I},\; t\in\mathcal{T},\; \omega\in\Omega $$

PV generation is limited by availability:
$$ 0\le p^{PV,stand}_{i,t,\omega}\le \overline{p}^{PV}_{i,t,\omega}, \quad \forall i,t,\omega $$

The standalone operating cost of user $i$ in scenario $\omega$ is:
$$ C^{stand}_{i,\omega}=\sum_{t\in\mathcal{T}}\Delta t \left(\lambda^{buy}_{t}p^{imp,stand}_{i,t,\omega} -\lambda^{sell}_{t}p^{exp,stand}_{i,t,\omega}\right) $$

The expected standalone benchmark is:
$$ B_i=\sum_{\omega\in\Omega}\pi_{\omega}C^{stand}_{i,\omega}, \quad \forall i\in\mathcal{I} $$

This value represents the expected net electricity bill of user $i$ when operating alone.

---

## 5. Decision variables of the coordinated EC model

| Variable | Description |
| :--- | :--- |
| $p^{PV}_{i,t,\omega}$ | PV generation used from user $i$ |
| $p^{imp}_{t,\omega}$ | Grid import at the PCC |
| $p^{exp}_{t,\omega}$ | Grid export at the PCC |
| $p^{curt}_{t,\omega}$ | PV curtailment |
| $p^{B,ch}_{t,\omega}$ | BESS charging power |
| $p^{B,dis}_{t,\omega}$ | BESS discharging power |
| $E^{B}_{t,\omega}$ | BESS state of charge |
| $u^{B}_{t,\omega}$ | Binary variable for BESS charging/discharging mode |
| $p^{EL}_{t,\omega}$ | Electrolyzer power consumption |
| $h^{prod}_{t,\omega}$ | Hydrogen produced by the electrolyzer |
| $h^{FC}_{t,\omega}$ | Hydrogen consumed by the fuel cell |
| $p^{FC}_{t,\omega}$ | Fuel-cell electricity generation |
| $H_{t,\omega}$ | Hydrogen inventory in the tank |
| $u^{EL}_{t,\omega}, u^{FC}_{t,\omega}$ | Binary variables for electrolyzer and fuel-cell operation |
| $g_i$ | Expected gain allocated to user $i$ |
| $z$ | Minimum relative gain among all users |

---

## 6. Objective function

The main objective is to minimize the expected operating cost of the coordinated EC:
$$ \min C^{EC} $$

where:
$$ C^{EC}=\sum_{\omega\in\Omega}\pi_{\omega} \sum_{t\in\mathcal{T}}\Delta t \left[ \lambda^{buy}_{t}p^{imp}_{t,\omega} -\lambda^{sell}_{t}p^{exp}_{t,\omega} +c^{curt}p^{curt}_{t,\omega} +c^{B}\left(p^{B,ch}_{t,\omega}+p^{B,dis}_{t,\omega}\right) +c^{H2}p^{EL}_{t,\omega} +\rho^{exp}p^{exp}_{t,\omega} \right] $$

The term $\rho^{exp}p^{exp}_{t,\omega}$ is optional. If export is controlled through a hard PCC cap, $\rho^{exp}$ may be set to zero. If exports are only discouraged, $\rho^{exp}>0$ may be used as a soft penalty.

---

## 7. Community energy balance

The coordinated EC power balance is:
$$ \sum_{i\in\mathcal{I}}p^{PV}_{i,t,\omega} +p^{imp}_{t,\omega} +p^{B,dis}_{t,\omega} +p^{FC}_{t,\omega} = \sum_{i\in\mathcal{I}}d_{i,t,\omega} +p^{B,ch}_{t,\omega} +p^{EL}_{t,\omega} +p^{exp}_{t,\omega}, \quad \forall t\in\mathcal{T},\; \omega\in\Omega $$

PV generation is limited by availability:
$$ 0\le p^{PV}_{i,t,\omega}\le \overline{p}^{PV}_{i,t,\omega}, \quad \forall i,t,\omega $$

PV curtailment is defined as:
$$ p^{curt}_{t,\omega}=\sum_{i\in\mathcal{I}} \left(\overline{p}^{PV}_{i,t,\omega}-p^{PV}_{i,t,\omega}\right), \quad \forall t,\omega $$

---

## 8. Grid import/export and PCC export restriction

The grid exchange limits are:
$$ 0\le p^{imp}_{t,\omega}\le \overline{P}^{imp}, \quad \forall t,\omega $$

$$ 0\le p^{exp}_{t,\omega}\le \overline{P}^{exp}_{t}, \quad \forall t,\omega $$

The export limit may be parameterized as:
$$ \overline{P}^{exp}_{t}=\alpha \overline{P}^{PCC} $$

where $\alpha$ represents the export-permission level. For example, $\alpha=1$ represents free export, whereas $\alpha=0$ represents a zero-export policy.

---

## 9. BESS model

The BESS state-of-charge equation is:
$$ E^{B}_{t,\omega}=(1-\sigma^{B})E^{B}_{t-1,\omega}
+\eta^{B,ch}p^{B,ch}_{t,\omega}\Delta t
-\frac{p^{B,dis}_{t,\omega}\Delta t}{\eta^{B,dis}},
\quad \forall t,\omega. $$

The BESS energy limits are:
$$ \underline{E}^{B}\le E^{B}_{t,\omega}\le \overline{E}^{B},
\quad \forall t,\omega. $$

The BESS charging and discharging limits are:
$$ 0\le p^{B,ch}_{t,\omega}\le \overline{P}^{B,ch}u^{B}_{t,\omega},
\quad \forall t,\omega, $$

$$ 0\le p^{B,dis}_{t,\omega}\le \overline{P}^{B,dis}(1-u^{B}_{t,\omega}),
\quad \forall t,\omega, $$

$$ u^{B}_{t,\omega}\in\{0,1\},
\quad \forall t,\omega. $$

The initial condition is:
$$ E^{B}_{0,\omega}=E^{B,ini},
\quad \forall \omega. $$

A terminal condition may be imposed to avoid artificial depletion:
$$ E^{B}_{|\mathcal{T}|,\omega}\ge E^{B,ini},
\quad \forall \omega, $$

or, more strictly,
$$ E^{B}_{|\mathcal{T}|,\omega}=E^{B,ini},
\quad \forall \omega. $$

---

## 10. Hydrogen storage model

Hydrogen production by the electrolyzer is modeled as:
$$ h^{prod}_{t,\omega}=\eta^{EL}p^{EL}_{t,\omega}\Delta t,
\quad \forall t,\omega. $$

The fuel-cell conversion is represented by:
$$ p^{FC}_{t,\omega}\Delta t=\eta^{FC}h^{FC}_{t,\omega},
\quad \forall t,\omega. $$

The hydrogen inventory balance is:
$$ H_{t,\omega}=(1-\sigma^{H})H_{t-1,\omega}
+h^{prod}_{t,\omega}-h^{FC}_{t,\omega},
\quad \forall t,\omega. $$

The hydrogen storage limits are:
$$ 0\le H_{t,\omega}\le \overline{H},
\quad \forall t,\omega. $$

The electrolyzer and fuel-cell power limits are:
$$ 0\le p^{EL}_{t,\omega}\le \overline{P}^{EL}u^{EL}_{t,\omega},
\quad \forall t,\omega, $$

$$ 0\le p^{FC}_{t,\omega}\le \overline{P}^{FC}u^{FC}_{t,\omega},
\quad \forall t,\omega. $$

Simultaneous hydrogen production and electricity generation are avoided through:
$$ u^{EL}_{t,\omega}+u^{FC}_{t,\omega}\le 1,
\quad \forall t,\omega, $$

$$ u^{EL}_{t,\omega},u^{FC}_{t,\omega}\in\{0,1\},
\quad \forall t,\omega. $$

The initial and terminal hydrogen conditions are:
$$ H_{0,\omega}=H^{ini},
\quad \forall \omega, $$

$$ H_{|\mathcal{T}|,\omega}\ge H^{ini},
\quad \forall \omega, $$

or, if cyclic operation is preferred:
$$ H_{|\mathcal{T}|,\omega}=H^{ini},
\quad \forall \omega. $$

---

## 11. Two-stage stochastic structure

For first-stage periods, the decisions must be non-anticipative. Let $x_{t,\omega}$ be the vector of operational variables at time $t$ and scenario $\omega$. Then,
$$ x_{t,\omega}=x_{t,\omega'},
\quad \forall t\in\mathcal{T}^{1},\; \forall \omega,\omega'\in\Omega. $$

For the proposed model, $x_{t,\omega}$ may include:
$$ x_{t,\omega}=\left\{
 p^{imp}_{t,\omega},p^{exp}_{t,\omega},p^{B,ch}_{t,\omega},p^{B,dis}_{t,\omega},E^{B}_{t,\omega},
 p^{EL}_{t,\omega},p^{FC}_{t,\omega},H_{t,\omega}
\right\}. $$

Second-stage decisions, for $t\in\mathcal{T}^{2}$, are scenario-dependent.

---

## 12. Community gain allocation and participation guarantee

The total expected gain created by community operation is:
$$ G=\sum_{i\in\mathcal{I}}B_i-C^{EC}. $$

The gain is allocated among users through variables $g_i$:
$$ \sum_{i\in\mathcal{I}}g_i=\sum_{i\in\mathcal{I}}B_i-C^{EC}. $$

To guarantee that no user is worse off by joining the community, the following individual rationality condition is imposed:
$$ g_i\ge 0,
\quad \forall i\in\mathcal{I}. $$

The final expected cost allocated to user $i$ is:
$$ C^{final}_i=B_i-g_i. $$

Therefore, $g_i\ge 0$ implies $C^{final}_i\le B_i$, i.e., every user has a nonnegative gain relative to standalone operation.

A stronger fairness condition can be included as:
$$ g_i\ge \varepsilon R_i,
\quad \forall i\in\mathcal{I}, $$

where $R_i$ is a positive reference value. A natural choice is $R_i=B_i$ when $B_i>0$ for all users. If some users have negative standalone net costs due to high PV exports, a safer normalization is the expected gross standalone import bill:
$$ R_i=\sum_{\omega\in\Omega}\pi_{\omega}\sum_{t\in\mathcal{T}}\Delta t\lambda^{buy}_{t}p^{imp,stand}_{i,t,\omega}. $$

The auxiliary variable $z$ may also be used to measure the minimum relative gain:
$$ g_i\ge zR_i,
\quad \forall i\in\mathcal{I}. $$

Then, $z$ represents the minimum relative saving guaranteed among all community members.

---

## 13. Carbon-emission extension

A carbon-emission term can be included without changing the basic structure of the model. The expected carbon emissions may be represented as:
$$ E^{CO2}=\sum_{\omega\in\Omega}\pi_{\omega}
\sum_{t\in\mathcal{T}}\Delta t
\left(
\gamma^{grid}_{t}p^{imp}_{t,\omega}
+\gamma^{H2}p^{EL}_{t,\omega}
\right). $$

If the hydrogen is produced only from local PV surplus, the term $\gamma^{H2}p^{EL}_{t,\omega}$ may be omitted or set to zero. If grid electricity can be used for hydrogen production, this term should be treated carefully to avoid double-counting emissions already represented through $p^{imp}_{t,\omega}$.

### 13.1 Epsilon-constraint multi-objective formulation

A more rigorous multi-objective alternative is to minimize cost while imposing progressively tighter emission limits:
$$ \min C^{EC} $$

subject to
$$ E^{CO2}\le \epsilon^{CO2}_{k}. $$

The emission limits may be generated as:
$$ \epsilon^{CO2}_{k}=E^{CO2,min}+\frac{k}{K}\left(E^{CO2,cost}-E^{CO2,min}\right),
\quad k=0,1,\ldots,K, $$

where $E^{CO2,cost}$ is the emission level obtained from the cost-minimization model and $E^{CO2,min}$ is obtained by solving an emission-minimization model.

---

## 14. Final mathematical model

$$ \min C^{EC} $$

subject to
\begin{align}
&\text{standalone benchmark definitions,}\nonumber\\
&\text{community power balance,}\nonumber\\
&\text{PV limits and curtailment,}\nonumber\\
&\text{grid import/export limits and PCC export cap,}\nonumber\\
&\text{BESS operation constraints,}\nonumber\\
&\text{hydrogen operation constraints,}\nonumber\\
&\text{two-stage non-anticipativity constraints,}\nonumber\\
&\text{community gain allocation constraints,}\nonumber\\
&g_i\ge 0,\quad \forall i\in\mathcal{I},\\
&g_i\ge \varepsilon R_i,\quad \forall i\in\mathcal{I},\\
&E^{CO2}\le \epsilon^{CO2}_{k}. 
\end{align}

## Project Structure

```
stochastic-energy-opt/
├── v2.1.py            # Main model — data, SmartHomeStochastic class, entry point
├── requirements.txt   # Python dependencies
├── LICENSE
└── README.md
```

`v2.1.py` is organized in three sections:

- **Data** — hourly demand, PV generation profiles, time-of-use tariff, and scenario/blackout parameters defined as plain Python lists and dicts.
- **`SmartHomeStochastic` class** — encapsulates `build()` (constructs the Pyomo MILP), `solve()` (calls Gurobi and collects results into DataFrames), and `plot()` (generates the figures below).
- **Entry point** — instantiates the class and runs `build → solve → plot` in sequence.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/AslanMaia/stochastic-energy-opt.git
cd stochastic-energy-opt

# 2. Install Python dependencies
pip install -r requirements.txt
```

A valid **Gurobi license** is required. Academic licenses are available free of charge at [gurobi.com](https://www.gurobi.com/academia/academic-program-and-licenses/).

---

## Usage

```bash
python v2.1.py
```

The script will print the solver status, optimal objective value, and per-scenario dispatch tables to the terminal, then open two matplotlib figures.

---

## Output

**Figure 1 — Optimal sizing summary table**

Displays the optimal PV capacity (kWp), BESS capacity (kWh), and total NPV cost in a formatted table.

**Figure 2 — Per-scenario dispatch and battery state**

For each of the three scenarios, two side-by-side plots are shown:

- *Left:* hourly power flows (demand, PV generation, grid buy/sell, BESS charge/discharge) with the time-of-use tariff overlaid on a secondary axis.
- *Right:* BESS state of energy over the day, with the optimal capacity shown as a reference line.

---

## License

MIT — see `LICENSE` for details.
