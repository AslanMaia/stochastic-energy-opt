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
