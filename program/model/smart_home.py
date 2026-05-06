# model/smart_home.py
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import pyomo.environ as pyo
import pandas as pd
import matplotlib.pyplot as plt

class SmartHomeStochastic:
    def __init__(self, parameters, scenarios, tariff_buy):
        # Atributos do objeto — precisam de self para sobreviver entre métodos
        self.parameters = parameters
        self.scenarios  = scenarios
        self.tariff_buy = tariff_buy
        self.results    = {}        # será preenchido em solve()

    def build(self):
        m     = pyo.ConcreteModel('SmartHome_Stochastic')
        delta = 1.0

        self.CAPEX_PV          = CAPEX_PV          = 600.0 * 4.96           # BRL/kW
        self.OPEX_PV_RATE      = OPEX_PV_RATE      = 0.05 * self.CAPEX_PV   # 5% do CAPEX (taxa anual)
        self.CAPEX_BESS        = CAPEX_BESS        = 800.0 * 4.96           # BRL/kWh
        self.OPEX_BESS_PER_KWH = OPEX_BESS_PER_KWH = 0.24 * 4.96            # BRL/kWh (anual, por kWh de capacidade)


        # Conjuntos
        m.T = pyo.RangeSet(0, len(self.tariff_buy) - 1)
        m.S = pyo.Set(initialize=self.scenarios.keys())

        # Parâmetros [matrizes]
        m.P_demand = pyo.Param(m.S, m.T,
                               initialize=lambda m, s, t: self.scenarios[s]['P_demand'][t])
        m.P_pv     = pyo.Param(m.S, m.T,
                               initialize=lambda m, s, t: self.scenarios[s]['P_pv'][t])
        m.prob     = pyo.Param(m.S,
                               initialize=lambda m, s: self.scenarios[s]['prob'])
        m.tariff   = pyo.Param(m.T,
                               initialize=lambda m, t: self.tariff_buy[t])

        # Perfil PV normalizado por cenário (0..1)
        def pv_profile_init(m, s, t):
            pv_list = self.scenarios[s]['P_pv']
            peak = max(pv_list) if max(pv_list) > 0 else 1.0
            return pv_list[t] / peak
        m.PV_profile = pyo.Param(m.S, m.T, initialize=pv_profile_init)

        # Parâmetros BESS
        Pmax_bess = self.parameters['BESS']['Pmax']
        eff       = self.parameters['BESS']['eff']
        beta      = self.parameters['BESS']['self_discharge']
        init_cap  = self.parameters['BESS']['initial capacity']
        Pmax_grid = self.parameters['Grid']['Pmax']

        # Limites realistas
        PV_cap_upper = 10.0    # kW máxima permitida (ajustável)
        BESS_cap_upper = 20.0  # kWh máxima permitida (ajustável)
        max_charge_rate = 1.0  

        # Variáveis decisão de capacidade (1ª etapa)
        m.PV_cap = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, PV_cap_upper))
        m.BESS_capacity = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, BESS_cap_upper))

        # Binárias para operação (1ª etapa, mesma para todos os cenários)
        m.state = pyo.Var(m.T, within=pyo.Binary)

        # Variáveis operacionais (2ª etapa)
        m.Pgrid_buy       = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, Pmax_grid))
        m.Pgrid_sell      = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, Pmax_grid))
        m.Pgrid           = pyo.Var(m.S, m.T, within=pyo.Reals,            bounds=(-Pmax_grid, Pmax_grid))

        m.Pbess_charge    = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, Pmax_bess))
        m.Pbess_discharge = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, Pmax_bess))
        m.E_bess          = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, BESS_cap_upper))

        # Variável auxiliar para linearizar BESS_capacity * state[t]
        m.BESS_cap_on = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, BESS_cap_upper))

        # Limita energia armazenada pela capacidade decisão
        def bess_capacity_limit(m, t):
            return m.E_bess[t] <= m.BESS_capacity
        m.bess_cap_limit = pyo.Constraint(m.T, rule=bess_capacity_limit)

        # Linearização: BESS_cap_on approximates BESS_capacity * state[t]
        def cap_on_ub1(m, t):
            return m.BESS_cap_on[t] <= m.BESS_capacity
        m.cap_on_ub1 = pyo.Constraint(m.T, rule=cap_on_ub1)

        def cap_on_ub2(m, t):
            return m.BESS_cap_on[t] <= BESS_cap_upper * m.state[t]
        m.cap_on_ub2 = pyo.Constraint(m.T, rule=cap_on_ub2)

        def cap_on_lb(m, t):
            return m.BESS_cap_on[t] >= m.BESS_capacity - BESS_cap_upper * (1 - m.state[t])
        m.cap_on_lb = pyo.Constraint(m.T, rule=cap_on_lb)

        # Limita potência de descarga/carga pela capacidade (C-rate)
        def bess_discharge_limit(m, s, t):
            return m.Pbess_discharge[t] <= max_charge_rate * m.BESS_cap_on[t]
        m.dis_limit = pyo.Constraint(m.S, m.T, rule=bess_discharge_limit)

        def bess_charge_limit(m, s, t):
            return m.Pbess_charge[t] <= max_charge_rate * (m.BESS_capacity - m.BESS_cap_on[t])
        m.ch_limit = pyo.Constraint(m.S, m.T, rule=bess_charge_limit)

        # Restrições ──────────────────────────────────────────────────────────────────────
        def power_balance_rule(m, s, t):
            return (+ m.Pgrid[s, t]
                    + m.PV_profile[s, t] * m.PV_cap
                    + m.Pbess_discharge[t]
                    ==
                    + m.P_demand[s, t]
                    + m.Pbess_charge[t])
        m.power_balance = pyo.Constraint(m.S, m.T, rule=power_balance_rule)

        def grid_balance_rule(m, s, t):
            return m.Pgrid[s, t] == m.Pgrid_buy[s, t] - m.Pgrid_sell[s, t]
        m.grid_balance = pyo.Constraint(m.S, m.T, rule=grid_balance_rule)

        def bess_energy_rule(m, t):
            charge    = eff * delta * m.Pbess_charge[t]
            discharge = delta * m.Pbess_discharge[t] / eff
            loss      = beta * delta * m.E_bess[t]

            if t == 0:
                E_prev = init_cap
            else:
                E_prev = m.E_bess[t-1]
            return m.E_bess[t] == E_prev + charge - discharge - loss
        m.bess_energy = pyo.Constraint(m.T, rule=bess_energy_rule)

        # Objetivo: custo esperado operacional + custo diário da capacidade (BRL/dia)
        def objective_rule(m):
            operational = delta * sum(
                m.prob[s] * sum(
                    m.tariff[t] * m.Pgrid_buy[s, t] - 0.7 * m.tariff[t] * m.Pgrid_sell[s, t]
                    for t in m.T
                )
                for s in m.S
            )

            annual_capex_pv = CAPEX_PV * m.PV_cap
            annual_opex_pv = OPEX_PV_RATE * CAPEX_PV * m.PV_cap
            annual_capex_bess = CAPEX_BESS * m.BESS_capacity
            annual_opex_bess = OPEX_BESS_PER_KWH * m.BESS_capacity

            daily_capacity_cost = (annual_capex_pv + annual_opex_pv + annual_capex_bess + annual_opex_bess) / 365.0

            return operational + daily_capacity_cost
        m.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

        self.model = m

    def solve(self):
        solver   = SolverFactory('highs')
        solution = solver.solve(self.model)

        m = self.model
        if (solution.solver.status == SolverStatus.ok and
                solution.solver.termination_condition == TerminationCondition.optimal):
            # calculo operacional explicitamente
            operational_val = pyo.value(delta * sum(
                m.prob[s] * sum(
                    m.tariff[t] * m.Pgrid_buy[s, t] - 0.7 * m.tariff[t] * m.Pgrid_sell[s, t]
                    for t in m.T
                )
                for s in m.S
            ))

            pv_cap = pyo.value(m.PV_cap)
            bess_cap = pyo.value(m.BESS_capacity)

            annual_capex_pv = CAPEX_PV * pv_cap
            annual_opex_pv = OPEX_PV_RATE * CAPEX_PV * pv_cap
            annual_capex_bess = CAPEX_BESS * bess_cap
            annual_opex_bess = OPEX_BESS_PER_KWH * bess_cap
            daily_capacity_cost = (annual_capex_pv + annual_opex_pv + annual_capex_bess + annual_opex_bess) / 365.0

            print(f"\n✓ Objetivo total: {pyo.value(m.objective):.4f} BRL/dia")
            print(f"  Operacional (custo esperado diário): {operational_val:.4f} BRL/dia")
            print(f"  PV_cap (kW): {pv_cap:.4f} -> custo diário PV: {(annual_capex_pv+annual_opex_pv)/365.0:.4f} BRL/dia")
            print(f"  BESS_cap (kWh): {bess_cap:.4f} -> custo diário BESS: {(annual_capex_bess+annual_opex_bess)/365.0:.4f} BRL/dia")
            print(f"  Daily capacity cost (PV+BESS): {daily_capacity_cost:.4f} BRL/dia")
        else:
            print("✗ Solver não encontrou solução ótima.")
            print(f"  Status: {solution.solver.status}")
            print(f"  Termination: {solution.solver.termination_condition}")
            return

        # Coleta resultados em self.results para o plot usar depois
        for s in m.S:
            rows = []
            for t in m.T:
                rows.append({
                    'Hora':            t,
                    'Rede_compra':     pyo.value(m.Pgrid_buy[s, t]),
                    'Rede_venda':      pyo.value(m.Pgrid_sell[s, t]),
                    'PV':              pyo.value(m.PV_profile[s, t]) * pyo.value(m.PV_cap),
                    'Demanda':         pyo.value(m.P_demand[s, t]),
                    'BESS_carga':      pyo.value(m.Pbess_charge[t]),
                    'BESS_descarga':   pyo.value(m.Pbess_discharge[t]),
                    'E_BESS':          pyo.value(m.E_bess[t]),
                    'state':           int(pyo.value(m.state[t])),
                })

            df = pd.DataFrame(rows)
            print(f"\n {s} (π={self.scenarios[s]['prob']})")
            print(df.round(2).to_string(index=False))
            self.results[s] = df

    def plot(self):
        horas     = list(self.model.T)
        cenarios  = list(self.results.keys())
        n         = len(cenarios)

        fig, axes = plt.subplots(nrows=n, ncols=2, figsize=(14, 4 * n), sharey=False)
        fig.suptitle("Resultados (BRL)", fontsize=14, fontweight='bold')

        for i, s in enumerate(cenarios):
            df  = self.results[s]
            ax1 = axes[i, 0]
            ax2 = axes[i, 1]

            prob = self.scenarios[s]['prob']

            ax1.plot(horas, df['Demanda'],       label='Demanda',      color='black',  linewidth=2)
            ax1.plot(horas, df['PV'],            label='PV',           color='orange', linewidth=1.5)
            ax1.plot(horas, df['Rede_compra'],   label='Rede compra',  color='steelblue', linewidth=1.5)
            ax1.plot(horas, df['Rede_venda'],    label='Rede venda',   color='green',  linewidth=1.5, linestyle='--')
            ax1.plot(horas, df['BESS_descarga'], label='BESS descarga',color='red',    linewidth=1.5, linestyle='-.')
            ax1.plot(horas, df['BESS_carga'],    label='BESS carga',   color='purple', linewidth=1.5, linestyle=':')

            ax1.set_title(f"Cenário: {s}  (π = {prob})")
            ax1.set_ylabel("Potência [kW]")
            ax1.set_xlabel("Hora")
            ax1.legend(fontsize=8)
            ax1.grid(True, alpha=0.3)

            ax2.fill_between(horas, df['E_BESS'], alpha=0.4, color='purple', label='E_BESS')
            ax2.plot(horas, df['E_BESS'], color='purple', linewidth=1.5)

            try:
                cap_max = pyo.value(self.model.BESS_capacity)
            except Exception:
                cap_max = self.parameters['BESS']['capacity']
            ax2.axhline(cap_max, color='red', linestyle='--', linewidth=1, label=f'Cap. máx. ({cap_max} kWh)')

            ax2.set_title(f"Bateria — {s}")
            ax2.set_ylabel("Energia [kWh]")
            ax2.set_xlabel("Hora")
            ax2.set_ylim(0, cap_max * 1.15)
            ax2.legend(fontsize=8)
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()
