from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import pyomo.environ as pyo
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ==================== DADOS ====================
P_demand_data = [
    1.9317, 1.6090, 1.4079, 1.3281, 1.3834, 1.6413,
    1.9395, 1.7383, 1.8341, 1.8354, 1.9312, 2.3645,
    2.2038, 2.2997, 2.1659, 2.5046, 2.7490, 4.0597,
    4.9924, 5.4257, 5.0491, 4.4294, 3.7692, 2.7716
]

P_pv_data = [
    0.0000, 0.0000, 0.0000, 0.0000, 0.0796, 0.4565,
    1.0742, 1.5790, 2.4343, 2.7488, 3.5092, 3.8988,
    3.9734, 3.7105, 3.1671, 2.7282, 2.3926, 2.1764,
    1.9083, 1.4257, 0.0034, 0.0000, 0.0000, 0.0000
]

tariff_buy = [
    0.22419, 0.22419, 0.22419, 0.22419, 0.22419, 0.22419,
    0.22419, 0.22419, 0.22419, 0.22419, 0.22419, 0.22419,
    0.22419, 0.22419, 0.22419, 0.22419, 0.22419, 0.32629,
    0.51792, 0.51792, 0.51792, 0.32629, 0.22419, 0.22419
]

# ==================== HORIZONTE MULTI-DIA ====================
HORIZON_DAYS = 3
HOURS_PER_DAY = 24
TOTAL_H = HORIZON_DAYS * HOURS_PER_DAY

def repeat24(data, days=HORIZON_DAYS):
    return data * days

P_demand_72 = repeat24(P_demand_data)
tariff_buy_72 = repeat24(tariff_buy)

# Perfis normalizados de PV (como no código original, mas sem variável de capacidade)
P_pv_norm_base_day = [v * 0.8 / max(P_pv_data) for v in P_pv_data]
P_pv_norm_alta_day = [v * 0.5 / max(P_pv_data) for v in P_pv_data]

P_pv_norm_base_72 = repeat24(P_pv_norm_base_day)
P_pv_norm_alta_72 = repeat24(P_pv_norm_alta_day)

P_demand_alta_72 = [x * 1.3 for x in P_demand_72]

scenarios = {
    "base": {
        "demand": P_demand_72,
        "pv_norm": P_pv_norm_base_72,
        "prob": 0.5,
    },
    "alta_demanda": {
        "demand": P_demand_alta_72,
        "pv_norm": P_pv_norm_alta_72,
        "prob": 0.5,
    }
}

class EnergyCommunityStochastic:
    def __init__(self, scenarios, tariff_buy):
        self.scenarios = scenarios
        self.tariff_buy = tariff_buy
        self.tariff_sell = [t * 0.95 for t in tariff_buy]
        self.delta = 1.0
        self.users = 2
        self.TOTAL_H = len(tariff_buy)

        # Primeiro estágio: dia 1; segundo estágio: dias 2 e 3
        self.T1 = list(range(0, 24))
        self.T2 = list(range(24, self.TOTAL_H))

        # Parâmetros de capacidade/operação (agora fixos, conforme formulação)
        self.PV_rated_total = 10.0     # kWp total da comunidade
        self.P_imp_max = 50.0          # kW
        self.P_exp_max = 50.0          # kW
        self.BESS_capacity = 20.0      # kWh
        self.H2_capacity = 20.0        # kg
        self.E_B_ini = 10.0            # kWh
        self.H_ini = 5.0               # kg

        self.P_bar_B_ch = 20.0         # kW
        self.P_bar_B_dis = 20.0        # kW
        self.P_bar_EL = 10.0           # kW
        self.P_bar_FC = 10.0           # kW

        self.eta_B_ch = 0.92
        self.eta_B_dis = 0.92
        self.sigma_B = 0.002

        self.eta_EL = 0.75
        self.eta_FC = 0.60
        self.sigma_H = 0.001

        self.c_curt = 0.3
        self.c_B = 0.0005
        self.c_H2 = 0.005
        self.rho_exp = 0.0

        self.gamma_grid = 0.45
        self.gamma_H2 = 0.30

        self.epsilon = 0.0             # ganho relativo mínimo
        self.epsilon_co2 = 500.0       # kg CO2, ajustável

        self.standalone_costs, self.standalone_imports = self.compute_standalone()

    def compute_standalone(self):
        standalone_costs = {i: 0.0 for i in range(self.users)}
        standalone_imports = {i: 0.0 for i in range(self.users)}

        for i in range(self.users):
            for s_name, s_data in self.scenarios.items():
                prob = s_data['prob']
                demand = s_data['demand']
                pv_norm = s_data['pv_norm']

                for t in range(self.TOTAL_H):
                    d_i = demand[t] / self.users
                    pv_avail_i = self.PV_rated_total * pv_norm[t] / self.users

                    if d_i > pv_avail_i:
                        imp_i = d_i - pv_avail_i
                        exp_i = 0.0
                    else:
                        imp_i = 0.0
                        exp_i = pv_avail_i - d_i

                    standalone_costs[i] += prob * self.delta * (
                        self.tariff_buy[t] * imp_i
                        - self.tariff_sell[t] * exp_i
                    )
                    standalone_imports[i] += prob * self.delta * self.tariff_buy[t] * imp_i

        print(f"Standalone costs: {standalone_costs}")
        return standalone_costs, standalone_imports

    def build(self):
        m = pyo.ConcreteModel('EnergyCommunity')

        # ============ SETS ============
        m.T = pyo.RangeSet(0, self.TOTAL_H - 1)
        m.I = pyo.RangeSet(0, self.users - 1)
        m.S = pyo.Set(initialize=self.scenarios.keys())
        m.T1 = pyo.Set(initialize=self.T1)
        m.T2 = pyo.Set(initialize=self.T2)

        scenario_names = list(self.scenarios.keys())
        scenario_pairs = [
            (scenario_names[i], scenario_names[j])
            for i in range(len(scenario_names))
            for j in range(i + 1, len(scenario_names))
        ]
        m.SP = pyo.Set(initialize=scenario_pairs, dimen=2)

        # ============ PARÂMETROS ============
        def demand_init(m, i, s, t):
            return self.scenarios[s]['demand'][t] / self.users

        def pv_avail_init(m, i, s, t):
            return self.PV_rated_total * self.scenarios[s]['pv_norm'][t] / self.users

        m.P_demand = pyo.Param(m.I, m.S, m.T, initialize=demand_init)
        m.P_pv_available = pyo.Param(m.I, m.S, m.T, initialize=pv_avail_init)
        m.prob = pyo.Param(m.S, initialize=lambda m, s: self.scenarios[s]['prob'])
        m.tariff_buy = pyo.Param(m.T, initialize=lambda m, t: self.tariff_buy[t])
        m.tariff_sell = pyo.Param(m.T, initialize=lambda m, t: self.tariff_sell[t])

        # ============ VARIÁVEIS ============
        m.p_imp = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, self.P_imp_max))
        m.p_exp = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, self.P_exp_max))
        m.p_PV = pyo.Var(m.I, m.S, m.T, within=pyo.NonNegativeReals)
        m.p_curt = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals)

        # BESS
        m.p_B_ch = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals)
        m.p_B_dis = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals)
        m.E_B = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, self.BESS_capacity))
        m.u_B = pyo.Var(m.S, m.T, within=pyo.Binary)

        # HESS
        m.p_EL = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals)
        m.p_FC = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals)
        m.h_prod = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals)
        m.h_FC = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals)
        m.H = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, self.H2_capacity))
        m.u_EL = pyo.Var(m.S, m.T, within=pyo.Binary)
        m.u_FC = pyo.Var(m.S, m.T, within=pyo.Binary)

        # Ganhos e emissões
        m.g = pyo.Var(m.I, within=pyo.NonNegativeReals)
        m.E_CO2 = pyo.Var(within=pyo.NonNegativeReals)

        # ============ RESTRIÇÕES ============

        # PV
        def pv_limit_rule(m, i, s, t):
            return m.p_PV[i, s, t] <= m.P_pv_available[i, s, t]
        m.pv_limit = pyo.Constraint(m.I, m.S, m.T, rule=pv_limit_rule)

        def pv_curtailment_rule(m, s, t):
            return m.p_curt[s, t] == sum(
                m.P_pv_available[i, s, t] - m.p_PV[i, s, t]
                for i in m.I
            )
        m.pv_curtailment = pyo.Constraint(m.S, m.T, rule=pv_curtailment_rule)

        # Balanço de potência
        def power_balance_rule(m, s, t):
            lhs = (
                sum(m.p_PV[i, s, t] for i in m.I)
                + m.p_imp[s, t]
                + m.p_B_dis[s, t]
                + m.p_FC[s, t]
            )
            rhs = (
                sum(m.P_demand[i, s, t] for i in m.I)
                + m.p_B_ch[s, t]
                + m.p_EL[s, t]
                + m.p_exp[s, t]
            )
            return lhs == rhs
        m.power_balance = pyo.Constraint(m.S, m.T, rule=power_balance_rule)

        # Rede/PCC
        def grid_import_limit_rule(m, s, t):
            return m.p_imp[s, t] <= self.P_imp_max
        m.grid_import_limit = pyo.Constraint(m.S, m.T, rule=grid_import_limit_rule)

        def grid_export_limit_rule(m, s, t):
            return m.p_exp[s, t] <= self.P_exp_max
        m.grid_export_limit = pyo.Constraint(m.S, m.T, rule=grid_export_limit_rule)

        # BESS
        def bess_energy_rule(m, s, t):
            if t == 0:
                E_prev = self.E_B_ini
            else:
                E_prev = m.E_B[s, t - 1]
            return m.E_B[s, t] == (
                (1 - self.sigma_B) * E_prev
                + self.eta_B_ch * m.p_B_ch[s, t] * self.delta
                - (m.p_B_dis[s, t] * self.delta) / self.eta_B_dis
            )
        m.bess_energy = pyo.Constraint(m.S, m.T, rule=bess_energy_rule)

        m.bess_initial = pyo.Constraint(m.S, rule=lambda m, s: m.E_B[s, 0] == self.E_B_ini)
        m.bess_terminal = pyo.Constraint(
            m.S,
            rule=lambda m, s: m.E_B[s, self.TOTAL_H - 1] >= self.E_B_ini
        )

        m.bess_energy_limit = pyo.Constraint(
            m.S, m.T,
            rule=lambda m, s, t: m.E_B[s, t] <= self.BESS_capacity
        )

        def bess_charge_limit_rule(m, s, t):
            return m.p_B_ch[s, t] <= self.P_bar_B_ch * m.u_B[s, t]
        m.bess_charge_limit = pyo.Constraint(m.S, m.T, rule=bess_charge_limit_rule)

        def bess_discharge_limit_rule(m, s, t):
            return m.p_B_dis[s, t] <= self.P_bar_B_dis * (1 - m.u_B[s, t])
        m.bess_discharge_limit = pyo.Constraint(m.S, m.T, rule=bess_discharge_limit_rule)

        # Hidrogênio
        def h2_production_rule(m, s, t):
            return m.h_prod[s, t] == self.eta_EL * m.p_EL[s, t] * self.delta
        m.h2_production = pyo.Constraint(m.S, m.T, rule=h2_production_rule)

        def fc_conversion_rule(m, s, t):
            return m.p_FC[s, t] * self.delta == self.eta_FC * m.h_FC[s, t]
        m.fc_conversion = pyo.Constraint(m.S, m.T, rule=fc_conversion_rule)

        def h2_storage_rule(m, s, t):
            if t == 0:
                H_prev = self.H_ini
            else:
                H_prev = m.H[s, t - 1]
            return m.H[s, t] == (
                (1 - self.sigma_H) * H_prev
                + m.h_prod[s, t]
                - m.h_FC[s, t]
            )
        m.h2_storage = pyo.Constraint(m.S, m.T, rule=h2_storage_rule)

        m.h2_initial = pyo.Constraint(m.S, rule=lambda m, s: m.H[s, 0] == self.H_ini)
        m.h2_terminal = pyo.Constraint(
            m.S,
            rule=lambda m, s: m.H[s, self.TOTAL_H - 1] >= self.H_ini
        )

        m.h2_storage_limit = pyo.Constraint(
            m.S, m.T,
            rule=lambda m, s, t: m.H[s, t] <= self.H2_capacity
        )

        def electrolyzer_limit_rule(m, s, t):
            return m.p_EL[s, t] <= self.P_bar_EL * m.u_EL[s, t]
        m.electrolyzer_limit = pyo.Constraint(m.S, m.T, rule=electrolyzer_limit_rule)

        def fc_limit_rule(m, s, t):
            return m.p_FC[s, t] <= self.P_bar_FC * m.u_FC[s, t]
        m.fc_limit = pyo.Constraint(m.S, m.T, rule=fc_limit_rule)

        def simultaneous_h2_rule(m, s, t):
            return m.u_EL[s, t] + m.u_FC[s, t] <= 1
        m.simultaneous_h2 = pyo.Constraint(m.S, m.T, rule=simultaneous_h2_rule)

        # Não-antecipatividade para t em T1
        def na_rule_factory(var_name):
            def rule(m, s1, s2, t):
                return getattr(m, var_name)[s1, t] == getattr(m, var_name)[s2, t]
            return rule

        for var_name in ['p_imp', 'p_exp', 'p_B_ch', 'p_B_dis', 'E_B', 'p_EL', 'p_FC', 'H']:
            con_name = f"na_{var_name}"
            setattr(
                m,
                con_name,
                pyo.Constraint(m.SP, m.T1, rule=na_rule_factory(var_name))
            )

        # Função objetivo: custo operacional esperado
        def total_expected_cost_rule(m):
            return sum(
                m.prob[s] * self.delta * (
                    m.tariff_buy[t] * m.p_imp[s, t]
                    - m.tariff_sell[t] * m.p_exp[s, t]
                    + self.c_curt * m.p_curt[s, t]
                    + self.c_B * (m.p_B_ch[s, t] + m.p_B_dis[s, t])
                    + self.c_H2 * m.p_EL[s, t]
                    + self.rho_exp * m.p_exp[s, t]
                )
                for s in m.S
                for t in m.T
            )
        m.total_expected_cost = pyo.Expression(rule=total_expected_cost_rule)

        # Ganho total da comunidade
        def total_gain_rule(m):
            return sum(self.standalone_costs[i] for i in m.I) - m.total_expected_cost
        m.total_gain = pyo.Expression(rule=total_gain_rule)

        m.gain_allocation = pyo.Constraint(
            rule=lambda m: sum(m.g[i] for i in m.I) == m.total_gain
        )

        m.individual_rationality = pyo.Constraint(
            m.I,
            rule=lambda m, i: m.g[i] >= 0
        )

        if self.epsilon > 0:
            m.min_relative_gain = pyo.Constraint(
                m.I,
                rule=lambda m, i: m.g[i] >= self.epsilon * self.standalone_imports[i]
            )

        # Emissões
        def co2_rule(m):
            return m.E_CO2 == sum(
                m.prob[s] * self.delta * (
                    self.gamma_grid * m.p_imp[s, t]
                    + self.gamma_H2 * m.p_EL[s, t]
                )
                for s in m.S
                for t in m.T
            )
        m.co2_emissions = pyo.Constraint(rule=co2_rule)

        if self.epsilon_co2 is not None:
            m.carbon_limit = pyo.Constraint(rule=lambda m: m.E_CO2 <= self.epsilon_co2)

        # Objetivo
        m.objective = pyo.Objective(expr=m.total_expected_cost, sense=pyo.minimize)

        self.model = m

    def solve(self):
        try:
            solver = SolverFactory('gurobi')
        except:
            solver = SolverFactory('glpk')

        solution = solver.solve(self.model, tee=True)
        m = self.model

        if (
            solution.solver.status == SolverStatus.ok
            and solution.solver.termination_condition == TerminationCondition.optimal
        ):
            print(f"\n{'='*60}")
            print(f"✓ Custo operacional esperado: {pyo.value(m.total_expected_cost):.4f} BRL")
            print(f"✓ Ganho total da comunidade: {pyo.value(m.total_gain):.4f} BRL")
            print(f"✓ CO2 emitido: {pyo.value(m.E_CO2):.4f} kg")
            print(f"\n--- Alocação de Ganhos ---")
            for i in m.I:
                gain_i = pyo.value(m.g[i])
                print(
                    f"  Usuário {i+1}: "
                    f"B_{i+1} = {self.standalone_costs[i]:.2f}, "
                    f"g_{i+1} = {gain_i:.2f}, "
                    f"C_final = {self.standalone_costs[i] - gain_i:.2f}"
                )
            print(f"{'='*60}")

            self.results = {}
            for s in m.S:
                rows = []
                for t in m.T:
                    rows.append({
                        'Hora': t,
                        'p_imp': pyo.value(m.p_imp[s, t]),
                        'p_exp': pyo.value(m.p_exp[s, t]),
                        'p_PV_total': sum(pyo.value(m.p_PV[i, s, t]) for i in m.I),
                        'p_curt': pyo.value(m.p_curt[s, t]),
                        'p_B_ch': pyo.value(m.p_B_ch[s, t]),
                        'p_B_dis': pyo.value(m.p_B_dis[s, t]),
                        'E_B': pyo.value(m.E_B[s, t]),
                        'p_EL': pyo.value(m.p_EL[s, t]),
                        'p_FC': pyo.value(m.p_FC[s, t]),
                        'H': pyo.value(m.H[s, t]),
                        'Demanda': sum(pyo.value(m.P_demand[i, s, t]) for i in m.I),
                        'u_B': pyo.value(m.u_B[s, t]),
                        'u_EL': pyo.value(m.u_EL[s, t]),
                        'u_FC': pyo.value(m.u_FC[s, t]),
                    })
                df = pd.DataFrame(rows)
                print(f"\n--- Cenário: {s} (π={self.scenarios[s]['prob']}) ---")
                print(df.round(3).to_string(index=False))
                self.results[s] = df

        else:
            print("✗ Solver não encontrou solução ótima.")
            print(f"  Status: {solution.solver.status}")
            print(f"  Termination: {solution.solver.termination_condition}")
            from pyomo.util.infeasible import log_infeasible_constraints
            log_infeasible_constraints(m)

    def plot(self):
        if not self.results:
            print("Sem resultados para plotar.")
            return

        horas = list(range(self.TOTAL_H))
        cenarios = list(self.results.keys())
        n = len(cenarios)

        fig, axes = plt.subplots(nrows=n, ncols=2, figsize=(16, 5 * n))
        if n == 1:
            axes = [axes]

        for i, s in enumerate(cenarios):
            df = self.results[s]
            prob = self.scenarios[s]['prob']

            ax1 = axes[i, 0]
            ax1.plot(horas, df['Demanda'], 'b--', label='Demanda', linewidth=2)
            ax1.plot(horas, df['p_PV_total'], 'r-', label='PV gerado', linewidth=2)
            ax1.plot(horas, df['p_imp'], 'g-', label='Grid import', linewidth=2)
            ax1.plot(horas, df['p_exp'], 'm-', label='Grid export', linewidth=2)
            ax1.plot(horas, df['p_B_ch'], 'c-', label='BESS charge', linewidth=2)
            ax1.plot(horas, df['p_B_dis'], 'y-', label='BESS discharge', linewidth=2)
            ax1.plot(horas, df['p_EL'], 'orange', label='Electrolyzer', linewidth=2)
            ax1.plot(horas, df['p_FC'], 'purple', label='Fuel Cell', linewidth=2)
            ax1.plot(horas, df['p_curt'], 'k--', label='PV curtailed', linewidth=1.5)

            ax1.set_title(f"Balanço de Potência - {s} (π={prob:.2f})", fontsize=11, fontweight='bold')
            ax1.set_ylabel("Potência [kW]")
            ax1.set_xlabel("Hora")
            ax1.set_xlim(0, self.TOTAL_H - 1)
            ax1.legend(fontsize=8, loc='upper left')
            ax1.grid(True, alpha=0.3)

            ax2 = axes[i, 1]
            ax2.fill_between(horas, df['E_B'], alpha=0.3, color='#8b5cf6', label='E_BESS')
            ax2.plot(horas, df['E_B'], color='#7c3aed', linewidth=2.5)
            ax2.fill_between(horas, df['H'], alpha=0.3, color='#f59e0b', label='H2 storage')
            ax2.plot(horas, df['H'], color='#d97706', linewidth=2.5)

            ax2.axhline(
                self.BESS_capacity,
                color='#dc2626', linestyle='--', linewidth=1.5,
                label=f'Cap. BESS ({self.BESS_capacity:.1f} kWh)'
            )
            ax2.axhline(
                self.H2_capacity,
                color='#2563eb', linestyle='--', linewidth=1.5,
                label=f'Cap. H2 ({self.H2_capacity:.1f} kg)'
            )
            ax2.axhline(0, color='#9ca3af', linestyle='-', linewidth=0.5)

            ax2.set_title(f"Armazenamento - {s}", fontsize=11, fontweight='bold')
            ax2.set_ylabel("Energia/Inventário")
            ax2.set_xlabel("Hora")
            ax2.set_xlim(0, self.TOTAL_H - 1)
            ax2.legend(fontsize=8)
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    ec = EnergyCommunityStochastic(scenarios, tariff_buy_72)
    ec.build()
    ec.solve()
    ec.plot()