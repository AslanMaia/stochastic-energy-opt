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

This repository implements a **two-stage stochastic MILP** for a residential energy system with solar PV and battery storage (BESS):

- **First stage (here-and-now):** sizing of the PV system and the BESS, decided once and shared by all scenarios.
- **Second stage (wait-and-see):** hourly operation (grid exchange, BESS charge/discharge) decided separately for each scenario of generation, demand, and grid availability.

The objective minimizes the net present value (NPV) of investment plus expected operational costs over a 25-year horizon. Rather than optimizing for a single forecast, the model selects a sizing that performs well across sunny, cloudy, high-demand, and blackout scenarios.

---

## Project Structure

```
stochastic-energy-opt/
├── math_formulation.ipynb   # Formal mathematical formulation of the model
├── v2.1.py                  # Stable version — data, SmartHomeStochastic class, entry point
├── dev/
│   ├── v2.2_unstable.py     # Development version (under debugging)
│   └── v2.2_output.png      # Latest output of v2.2
├── requirements.txt         # Python dependencies
├── LICENSE
└── README.md
```

`v2.1.py` is organized in three sections:

- **Data** — hourly demand, PV generation profiles, time-of-use tariff, and scenario/blackout parameters defined as plain Python lists and dicts.
- **`SmartHomeStochastic` class** — encapsulates `build()` (constructs the Pyomo MILP), `solve()` (calls Gurobi and collects results into DataFrames), and `plot()` (generates the figures below).
- **Entry point** — instantiates the class and runs `build → solve → plot` in sequence.

`dev/v2.2_unstable.py` extends v2.1 with a standalone baseline (cost without PV/BESS, for comparison) and PV curtailment. It is still being debugged and may not run correctly.

---

## Roadmap

- [x] Mathematical formulation (`math_formulation.ipynb`)
- [x] Stable two-stage model with PV + BESS (v2.1)
- [ ] Standalone baseline and PV curtailment (v2.2, in progress)
- [ ] Hydrogen storage constraints (electrolyzer, tank, fuel cell)

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