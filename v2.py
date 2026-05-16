from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import pyomo.environ as pyo
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ── Dados ──────────────────────────────────────────────────────────────────────
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

scenarios = {
    "alta_geracao": {
        "P_demand" : [x * 0.5 for x in P_demand_data],
        "P_pv_used": [(v * 1.5 / max(P_pv_data)) for v in P_pv_data],
        "prob"     : 0.20,
    },
        "base": {
        "P_demand" : P_demand_data,
        "P_pv_used": [(v / max(P_pv_data)) for v in P_pv_data],
        "prob"     : 0.60,
    },
    "alta_demanda": {
        "P_demand" : [x * 1.5 for x in P_demand_data],
        "P_pv_used": [(v * 0.5 / max(P_pv_data)) for v in P_pv_data],
        "prob"     : 0.20,
    }
}


class SmartHomeStochastic:
    def __init__(self, scenarios, tariff_buy):
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
                               initialize=lambda m, s, t: self.scenarios[s]['P_pv_used'][t])
        m.prob     = pyo.Param(m.S,
                               initialize=lambda m, s: self.scenarios[s]['prob'])
        m.tariff   = pyo.Param(m.T,
                               initialize=lambda m, t: self.tariff_buy[t])

        # Propriedades
        eff       = 0.9
        beta      = 0.01 # self-discharge rate
        init_cap  = 0
        Pmax_grid = 90
        
        ### VARIÁVEIS ─────────────────────────────────────────────────────────────────────

        # Variáveis de decisão (1ª etapa), note que as variaveis de decisão estão em MAIÚSCULO
        m.BESS_capacity = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, 200))
        m.BESS_Pmax     = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, 1e6))
        m.PV_Pmax       = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, 1e6)) # kWp    

        # Binárias para operação (1ª etapa, mesma para todos os cenários)
        m.state = pyo.Var(m.T, within=pyo.Binary)

        # Variáveis operacionais (2ª etapa)
        m.Pgrid_buy       = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, Pmax_grid))
        m.Pgrid_sell      = pyo.Var(m.S, m.T, within=pyo.NonNegativeReals, bounds=(0, Pmax_grid))
        m.Pgrid           = pyo.Var(m.S, m.T, within=pyo.Reals,            bounds=(-Pmax_grid, Pmax_grid))

        m.Pbess_charge    = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, 1e6))
        m.Pbess_discharge = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, 1e6))
        m.E_bess          = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, 200))

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
            return m.BESS_Pmax <= m.BESS_capacity * 0.5  # força BESS_Pmax a ser menor usando C-rate
        m.befficiency_limit = pyo.Constraint(m.T, rule=befficiency_limit_rule)


        # 2. Evita carga e descarga simultâneas
        M = 200 * 0.5 # BESS_capacity_max × C_rate
        def power_used_limit_rule(m, t):
            return m.Pbess_charge[t] + m.Pbess_discharge[t] <= m.BESS_Pmax 
        m.power_used_limit = pyo.Constraint(m.T, rule=power_used_limit_rule)

        def no_simultaneous_charge(m, t):
            return m.Pbess_charge[t] <= m.state[t] * M
        m.no_simul_charge = pyo.Constraint(m.T, rule=no_simultaneous_charge)

        def no_simultaneous_discharge(m, t):
            return m.Pbess_discharge[t] <= (1 - m.state[t]) * M
        m.no_simul_discharge = pyo.Constraint(m.T, rule=no_simultaneous_discharge)


        # 3. Balanços
        def power_balance_rule(m, s, t):
            return (+ m.Pgrid_buy[s, t]
                    + m.P_pv[s, t] * m.PV_Pmax
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

        # Objetivo ──────────────────────────────────────────────────────────────────────
                
        self.CAPEX_BESS   = 56 * 4.96     # BRL/kWh
        CAPEX_PV     = 1200 * 4.96   # BRL/kWh/dia
        
        self.OPEX         = 365 * self.delta * sum(m.prob[s] * sum(m.tariff[t] * m.Pgrid_buy[s, t] - 0.7 * m.tariff[t] * m.Pgrid_sell[s, t]for t in m.T)for s in m.S)
        
        # r. infl
        self.r = 0.05
        
        def objective_rule(m):
            NPV = sum((self.OPEX ) / ((1 + self.r) ** year) for year in range(10))
            return (m.BESS_capacity * self.CAPEX_BESS + NPV + m.PV_Pmax  * CAPEX_PV) # anual
            
        self.objective = m.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

        self.model = m

    def solve(self):
        solver   = SolverFactory('gurobi')
        solution = solver.solve(self.model)

        m = self.model

        if (solution.solver.status == SolverStatus.ok and solution.solver.termination_condition == TerminationCondition.optimal):
            print(f"\n✓ Objetivo total: {pyo.value(m.objective):.4f} BRL/lifetime")
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
                    'PV':              pyo.value(m.P_pv[s, t]) * pyo.value(m.PV_Pmax),
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

    def plot(self):
        horas    = list(self.model.T)
        cenarios = list(self.results.keys())
        n        = len(cenarios)

        pv_opt   = pyo.value(self.model.PV_Pmax)
        bess_opt = pyo.value(self.model.BESS_capacity)
        obj_opt  = pyo.value(self.model.objective)

        # ── Figura 1: Painel de resultados ótimos ────────────────────────────────
        fig_res, ax_res = plt.subplots(figsize=(7, 3))
        ax_res.axis('off')

        dados = [
            ["PV instalado",        f"{pv_opt:.1f} kWp"],
            ["BESS instalado",      f"{bess_opt:.1f} kWh"],
            ["Custo total (VPL)",   f"R$ {obj_opt:,.0f}"],
            ["Horizonte",           "10 anos  |  r = 5%"],
            ["Cenários",            "base (60%)  |  alta geração (20%)  |  alta demanda (20%)"],
        ]

        tabela = ax_res.table(
            cellText=dados,
            colLabels=["Parâmetro", "Valor ótimo"],
            cellLoc='left',
            loc='center',
            colWidths=[0.42, 0.58],
        )
        tabela.auto_set_font_size(False)
        tabela.set_fontsize(11)
        tabela.scale(1, 2.2)

        # Estilo do cabeçalho
        for col in range(2):
            tabela[0, col].set_facecolor('#1e3a5f')
            tabela[0, col].set_text_props(color='white', fontweight='bold')

        # Linha de destaque — custo total
        for col in range(2):
            tabela[3, col].set_facecolor('#fef9c3')
            tabela[3, col].set_text_props(fontweight='bold')

        fig_res.suptitle("Dimensionamento Ótimo", fontsize=13,
                        fontweight='bold', y=0.98)
        plt.tight_layout()
        

        # ── Figura 2: Gráficos operacionais ─────────────────────────────────────
        fig, axes = plt.subplots(nrows=n, ncols=2, figsize=(15, 4.5 * n))

        STYLE = {
            'demand': dict(color='#9ca3af', linewidth=1.6, linestyle='--', alpha=0.9,   label='Demanda'),
            'pv':     dict(color='#f59e0b', linewidth=2.5, linestyle=':',               label='PV gerado'),
            'buy':    dict(color='#3b82f6', linewidth=2.5, linestyle='-',               label='Rede compra'),
            'sell':   dict(color="#00d68b", linewidth=2.5, linestyle='-',               label='Rede venda'),
            'dis':    dict(color="#c15531", linewidth=2.0,                              label='BESS descarga'),
            'ch':     dict(color="#3d1c0c", linewidth=2.0,                              label='BESS carga'),
        }

        for i, s in enumerate(cenarios):
            df   = self.results[s]
            ax1  = axes[i, 0]
            ax2  = axes[i, 1]
            prob = self.scenarios[s]['prob']

            ax1.plot(horas, df['Demanda'],       **STYLE['demand'])
            ax1.plot(horas, df['PV'],            **STYLE['pv'])
            ax1.plot(horas, df['Rede_compra'],   **STYLE['buy'])
            ax1.plot(horas, df['Rede_venda'],    **STYLE['sell'])
            ax1.plot(horas, df['BESS_descarga'], **STYLE['dis'])
            ax1.plot(horas, df['BESS_carga'],    **STYLE['ch'])

            ax1t = ax1.twinx()
            ax1t.fill_between(horas, self.tariff_buy, step='mid', alpha=0.07, color='gray')
            ax1t.set_ylabel('Tarifa [BRL/kWh]', fontsize=8, color='#9ca3af')
            ax1t.tick_params(axis='y', labelsize=7, colors='#9ca3af')
            ax1t.set_ylim(0, max(self.tariff_buy) * 5)
            ax1.set_zorder(ax1t.get_zorder() + 1)
            ax1.patch.set_visible(False)

            ax1.set_title(f"Cenário: {s}  (π = {prob})", fontsize=11, fontweight='semibold')
            ax1.set_ylabel("Potência [kW]")
            ax1.set_xlabel("Hora")
            ax1.set_xlim(0, 23)
            ax1.legend(fontsize=8, loc='upper left', framealpha=0.95)
            ax1.grid(True, alpha=0.15)

            ax2.fill_between(horas, df['E_BESS'], alpha=0.3, color='#8b5cf6')
            ax2.plot(horas, df['E_BESS'], color='#7c3aed', linewidth=2.5, label='E_BESS')
            ax2.axhline(bess_opt, color='#dc2626', linestyle='--', linewidth=1.5,
                        label=f'Capacidade ótima ({bess_opt:.1f} kWh)')

            ax2.set_title(f"Estado da Bateria — {s}", fontsize=11, fontweight='semibold')
            ax2.set_ylabel("Energia [kWh]")
            ax2.set_xlabel("Hora")
            ax2.set_xlim(0, 23)
            ax2.set_ylim(0, max(bess_opt * 1.15, 0.1))
            ax2.legend(fontsize=8, framealpha=0.95)
            ax2.grid(True, alpha=0.15)

        plt.tight_layout()
        plt.show()
# ── Execução ───────────────────────────────────────────────────────────────────
sh = SmartHomeStochastic(scenarios, tariff_buy)
sh.build()
sh.solve()
sh.plot()