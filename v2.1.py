from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import pyomo.environ as pyo
import pandas as pd
import matplotlib.pyplot as plt

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

blackout = {
    "probabilidade_total" : 0.05,
    "horarios" : [0,3,6,9,12,15,18,21],
    "duracao" : 3, # horas
}

blackout['prob_por_horario'] = {
    h: blackout['probabilidade_total'] / len(blackout['horarios']) # evento independente, distribuição uniforme de probabilidade
    for h in blackout['horarios']
    }

# blackout['prob_por_horario'] = {0: 0.00625, 3: 0.00625, 6: 0.00625, 9: 0.00625, 12: 0.00625, 15: 0.00625, 18: 0.00625, 21: 0.00625}

class SmartHomeStochastic:
    def __init__(self, scenarios, tariff_buy, blackout):
        self.scenarios  = scenarios
        self.tariff_buy = tariff_buy
        self.blackout   = blackout
        self.results    = {}        # será preenchido em solve()

    def build(self):
        m     = pyo.ConcreteModel('SmartHome_Stochastic') # m stands for model
        self.delta = delta = 1.0

        # Conjuntos
        m.T = pyo.RangeSet(0, len(self.tariff_buy) - 1)
        m.S = pyo.Set(initialize=self.scenarios.keys())
        m.B = pyo.Set(initialize=self.blackout['prob_por_horario'].keys())

        # Matrizes
        m.P_demand = pyo.Param(m.S, m.T,
                               initialize=lambda m, s, t: self.scenarios[s]['P_demand'][t])
        m.P_pv     = pyo.Param(m.S, m.T,
                               initialize=lambda m, s, t: self.scenarios[s]['P_pv_used'][t])
        # Vetores rotulados
        m.prob     = pyo.Param(m.S,
                               initialize=lambda m, s: self.scenarios[s]['prob'])
        m.tariff   = pyo.Param(m.T,
                               initialize=lambda m, t: self.tariff_buy[t])
        m.blackout_prob = pyo.Param(m.B,
                                    initialize=lambda m, b: self.blackout['prob_por_horario'][b])

        # PARÂMETROS ─────────────────────────────────────────────────────────────────────
        eff       = 0.9
        beta      = 0.01 # self-discharge rate
        Pmax_grid = 20 # kW, limite de compra/venda da rede
        
        ### VARIÁVEIS ─────────────────────────────────────────────────────────────────────

        # Variáveis de decisão (1ª etapa)
        m.E_bess_init   = pyo.Var(within=pyo.NonNegativeReals)
        m.BESS_capacity = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, 200))
        m.BESS_Pmax     = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, 1e6))
        m.PV_Pmax       = pyo.Var(within=pyo.NonNegativeReals, bounds=(0, 1e6)) # kWp    

        # Variáveis operacionais (2ª etapa)
        m.Pgrid_buy       = pyo.Var(m.S, m.T, m.B, within=pyo.NonNegativeReals, bounds=(0, Pmax_grid))
        m.Pgrid_sell      = pyo.Var(m.S, m.T, m.B, within=pyo.NonNegativeReals, bounds=(0, Pmax_grid))
        m.Pgrid           = pyo.Var(m.S, m.T, m.B, within=pyo.Reals,            bounds=(-5, Pmax_grid))

        m.Pbess_charge    = pyo.Var(m.S, m.T, m.B, within=pyo.NonNegativeReals, bounds=(0, 1e6))
        m.Pbess_discharge = pyo.Var(m.S, m.T, m.B, within=pyo.NonNegativeReals, bounds=(0, 1e6))
        m.E_bess          = pyo.Var(m.S, m.T, m.B, within=pyo.NonNegativeReals, bounds=(0, 200))
        m.state           = pyo.Var(m.S, m.T, m.B, within=pyo.Binary)

        ### RESTRIÇÕES ──────────────────────────────────────────────────────────────────────

        # 1. Limites físicos e operacionais
        def energy_capacity_limit(m, s, t, b):
            return m.E_bess[s, t, b] <= m.BESS_capacity
        m.energy_cap = pyo.Constraint(m.S, m.T, m.B, rule=energy_capacity_limit)

        def charge_limit_rule(m, s, t, b):
            return m.Pbess_charge[s, t, b] <= m.BESS_Pmax
        m.charge_limit = pyo.Constraint(m.S, m.T, m.B, rule=charge_limit_rule)

        def discharge_limit_rule(m, s, t, b):
            return m.Pbess_discharge[s, t, b] <= m.BESS_Pmax
        m.discharge_limit = pyo.Constraint(m.S, m.T, m.B, rule=discharge_limit_rule)

        def befficiency_limit_rule(m, t):
            return m.BESS_Pmax <= m.BESS_capacity * 0.5  # força BESS_Pmax a ser menor usando C-rate
        m.befficiency_limit = pyo.Constraint(m.T, rule=befficiency_limit_rule)
        # Investigar -> m.befficiency_limit = pyo.Constraint(expr=m.BESS_Pmax <= m.BESS_capacity * 0.5)
        
        def init_capacity_limit(m):
            return m.E_bess_init <= m.BESS_capacity
        m.E_bess_init_cap = pyo.Constraint(rule=init_capacity_limit)

        # 2. Evita carga e descarga simultâneas
        M = 200 * 0.5 # BESS_capacity_max × C_rate
        def power_used_limit_rule(m, s, t, b):
            return m.Pbess_charge[s, t, b] + m.Pbess_discharge[s, t, b] <= m.BESS_Pmax 
        m.power_used_limit = pyo.Constraint(m.S, m.T, m.B, rule=power_used_limit_rule)

        def no_simultaneous_charge(m, s, t, b):
            return m.Pbess_charge[s, t, b] <= m.state[s, t, b] * M
        m.no_simul_charge = pyo.Constraint(m.S, m.T, m.B, rule=no_simultaneous_charge)

        def no_simultaneous_discharge(m, s, t, b):
            return m.Pbess_discharge[s, t, b] <= (1 - m.state[s, t, b]) * M
        m.no_simul_discharge = pyo.Constraint(m.S, m.T, m.B, rule=no_simultaneous_discharge)


        # 3. Balanços
        def power_balance_rule(m, s, t, b):
            return (+ m.Pgrid_buy[s, t, b]
                    + m.P_pv[s, t] * m.PV_Pmax
                    + m.Pbess_discharge[s, t, b]
                    ==
                    + m.Pgrid_sell[s, t, b]
                    + m.P_demand[s, t]
                    + m.Pbess_charge[s, t, b])
        m.power_balance = pyo.Constraint(m.S, m.T, m.B, rule=power_balance_rule)

        def grid_balance_rule(m, s, t, b):
            return m.Pgrid[s, t, b] == m.Pgrid_buy[s, t, b] - m.Pgrid_sell[s, t, b]
        m.grid_balance = pyo.Constraint(m.S, m.T, m.B, rule=grid_balance_rule)

        def bess_energy_rule(m, s, t, b):
            charge    = eff * delta * m.Pbess_charge[s, t, b]
            discharge = delta * m.Pbess_discharge[s, t, b] / eff
            loss      = beta * delta * m.E_bess[s, t, b]

            if t == 0:
                E_prev = m.E_bess_init
            else:
                E_prev = m.E_bess[s, t-1, b]
            return m.E_bess[s, t, b] == E_prev + charge - discharge - loss
        m.bess_energy = pyo.Constraint(m.S, m.T, m.B, rule=bess_energy_rule)


        dur = self.blackout['duracao']

        def blackout_grid_rule(m, s, t, b):
            if t in range(b, min(b + dur, len(self.tariff_buy))): # Rede indisponível
                return (0, m.Pgrid_buy[s, t, b], 0) # 0 <= Pgrid_buy <= 0 
            return pyo.Constraint.Skip

        def blackout_sell_rule(m, s, t, b):
            if t in range(b, min(b + dur, len(self.tariff_buy))):
                return (0, m.Pgrid_sell[s, t, b], 0)
            return pyo.Constraint.Skip

        m.blackout_grid     = pyo.Constraint(m.S, m.T, m.B, rule=blackout_grid_rule)
        m.blackout_sell_con = pyo.Constraint(m.S, m.T, m.B, rule=blackout_sell_rule)


        # Objetivo ──────────────────────────────────────────────────────────────────────
                
        self.CAPEX_BESS   = 2500 #* 4.96     # BRL/kWh
        CAPEX_PV     = 1200 #* 4.96   # BRL/kWh/dia
        
        self.OPEX         = 365 * self.delta * sum(m.blackout_prob[b] * m.prob[s] * (m.tariff[t] * m.Pgrid_buy[s, t, b] - 0.7 * m.tariff[t] * m.Pgrid_sell[s, t, b]) for b in m.B for s in m.S for t in m.T)
        
        # r. infl
        self.r = 0.05
        self.horizon = 25 # anos
        
        def objective_rule(m):
            NPV = sum((self.OPEX ) / ((1 + self.r) ** year) for year in range(25))
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

        # ✅ — escolhe um b representativo para exibir (ex: sem blackout = b=0)
        # ou agrega. Mais simples: reportar o cenário sem blackout de cada s
        b_ref = list(self.blackout['prob_por_horario'].keys())[0]
        
        for s in m.S:
            rows = []
            for t in m.T:
                rows.append({
                    'Hora':            t,
                    'Rede_compra':     pyo.value(m.Pgrid_buy[s, t, b_ref]),
                    'Rede_venda':      pyo.value(m.Pgrid_sell[s, t, b_ref]),
                    'PV':              pyo.value(m.P_pv[s, t]) * pyo.value(m.PV_Pmax),
                    'Demanda':         pyo.value(m.P_demand[s, t]),
                    'BESS_carga':      pyo.value(m.Pbess_charge[s, t, b_ref]),
                    'BESS_descarga':   pyo.value(m.Pbess_discharge[s, t, b_ref]),
                    'E_BESS':          pyo.value(m.E_bess[s, t, b_ref]),
                    'state':           int(round(pyo.value(m.state[s, t, b_ref]))),
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
            ["Horizonte",           f"{self.horizon} anos  |  r = 5%"],
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
            'pv':     dict(color="#ffa811", linewidth=2.5, linestyle=':',               label='PV gerado'),
            'buy':    dict(color="#04b82e", linewidth=2.5, linestyle='-',               label='Rede compra'),
            'sell':   dict(color="#d60000", linewidth=2.5, linestyle='-',               label='Rede venda'),
            'dis':    dict(color="#E06C1A", linewidth=2.0,                              label='BESS descarga'),
            'ch':     dict(color="#3a49ed", linewidth=2.0,                              label='BESS carga'),
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
sh = SmartHomeStochastic(scenarios, tariff_buy, blackout)
sh.build()
sh.solve()
sh.plot()