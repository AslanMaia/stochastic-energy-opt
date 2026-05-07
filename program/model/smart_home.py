
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import pyomo.environ as pyo
import pandas as pd
import matplotlib.pyplot as plt

class SmartHomeStochastic:
    def __init__(self, parameters, scenarios, tariff_buy):
        self.parameters = parameters
        self.scenarios  = scenarios
        self.tariff_buy = tariff_buy
        self.results    = {}        # será preenchido em solve()

    def build(self):
        m     = pyo.ConcreteModel('SmartHome_Stochastic') # m stands for model
        self.delta = delta = 1.0

        # Conjuntos
        m.T = pyo.RangeSet(0, len(self.tariff_buy) - 1)
        m.S = pyo.Set(initialize=self.scenarios.keys())

        # Matrizes
        m.P_demand = pyo.Param(m.S, m.T,
                               initialize=lambda m, s, t: self.scenarios[s]['P_demand'][t])
        m.P_pv     = pyo.Param(m.S, m.T,
                               initialize=lambda m, s, t: self.scenarios[s]['P_pv'][t])
        m.prob     = pyo.Param(m.S,
                               initialize=lambda m, s: self.scenarios[s]['prob'])
        m.tariff   = pyo.Param(m.T,
                               initialize=lambda m, t: self.tariff_buy[t])

        # Componentes
        eff       = self.parameters['BESS']['eff']
        beta      = self.parameters['BESS']['self_discharge']
        init_cap  = self.parameters['BESS']['initial capacity']
        Pmax_grid = self.parameters['Grid']['Pmax']
        
        ### VARIÁVEIS ─────────────────────────────────────────────────────────────────────

        # Variáveis decisão de capacidade (1ª etapa) note que as variaveis de decisão estão em MAIÚSCULO
        m.BESS_capacity = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, 20))
        m.BESS_Pmax     = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, 1e6))

        # Binárias para operação (1ª etapa, mesma para todos os cenários)
        m.state = pyo.Var(m.T, within=pyo.Binary)

        # Variáveis operacionais (2ª etapa)
        m.Pgrid_buy       = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, Pmax_grid))
        m.Pgrid_sell      = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, Pmax_grid))
        m.Pgrid           = pyo.Var(m.S, m.T, within=pyo.Reals,            bounds=(-Pmax_grid, Pmax_grid))

        m.Pbess_charge    = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, 1e6))
        m.Pbess_discharge = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, 1e6))
        m.E_bess          = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, 20))

        ### RESTRIÇÕES ──────────────────────────────────────────────────────────────────────

        # 1. Limites físicos e operacionais
        def energy_capacity_limit(m, t):
            return m.E_bess[t] <= m.BESS_capacity
        m.energy_cap = pyo.Constraint(m.T, rule=energy_capacity_limit)

        def charge_limit_rule(m,t):
            return m.Pbess_charge[t] <= m.BESS_Pmax
        m.charge_limit = pyo.Constraint(m.T, rule=charge_limit_rule)

        def discharge_limit_rule(m,t):
            return m.Pbess_discharge[t] <= m.BESS_Pmax
        m.discharge_limit = pyo.Constraint(m.T, rule=discharge_limit_rule)

        def befficiency_limit_rule(m, t):
            return m.BESS_Pmax <= m.BESS_capacity * 0.5  # força BESS_Pmax a ser menor
        m.befficiency_limit = pyo.Constraint(m.T, rule=befficiency_limit_rule)

        # 2. Evita carga e descarga simultâneas
        def power_used_limit_rule(m, t):
            return m.Pbess_charge[t] + m.Pbess_discharge[t] <= m.BESS_Pmax 
        m.power_used_limit = pyo.Constraint(m.T, rule=power_used_limit_rule)

        def no_simultaneous_charge(m, t):
            return m.Pbess_charge[t] <= m.state[t] * 1e6
        m.no_simul_charge = pyo.Constraint(m.T, rule=no_simultaneous_charge)

        def no_simultaneous_discharge(m, t):
            return m.Pbess_discharge[t] <= (1 - m.state[t]) * 1e6
        m.no_simul_discharge = pyo.Constraint(m.T, rule=no_simultaneous_discharge)


        # 3. Balanços
        def power_balance_rule(m, s, t):
            return (+ m.Pgrid_buy[s, t]
                    + m.P_pv[s, t]
                    + m.Pbess_discharge[t]
                    ==
                    + m.Pgrid_sell[s, t]
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

        # Objetivo -------------------------------------------------------------
        
        self.CAPEX_BESS        = 56.0 * 4.96                    # BRL/kWh
        self.CAPEX_BESS_DAILY  = self.CAPEX_BESS / (10 * 365.0)   # BRL/kWh/dia
        
        self.OPEX_BESS         = self.delta * sum(m.prob[s] * sum(m.tariff[t] * m.Pgrid_buy[s, t] - 0.7 * m.tariff[t] * m.Pgrid_sell[s, t]for t in m.T)for s in m.S)
        
        def objective_rule(m):
            return (m.BESS_capacity * self.CAPEX_BESS_DAILY + self.OPEX_BESS) # BRL/dia
        self.objective = m.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

        self.model = m

    def solve(self):
        solver   = SolverFactory('highs')
        solution = solver.solve(self.model)

        m = self.model

        if (solution.solver.status == SolverStatus.ok and solution.solver.termination_condition == TerminationCondition.optimal):
            print(f"\n✓ Objetivo total: {pyo.value(m.objective):.4f} BRL/dia")
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
                    'PV':              pyo.value(m.P_pv[s, t]),
                    'Demanda':         pyo.value(m.P_demand[s, t]),
                    'BESS_carga':      pyo.value(m.Pbess_charge[t]),
                    'BESS_descarga':   pyo.value(m.Pbess_discharge[t]),
                    'E_BESS':          pyo.value(m.E_bess[t]),
                    'state':           int(round(pyo.value(m.state[t]))),
                })

            df = pd.DataFrame(rows)
            print(f"\n {s} (π={self.scenarios[s]['prob']})")
            print(df.round(2).to_string(index=False))
            self.results[s] = df