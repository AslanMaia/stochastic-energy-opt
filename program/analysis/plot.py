from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import pyomo.environ as pyo
import pandas as pd
import matplotlib.pyplot as plt

def bess_sweep(pv_opt, parameters, scenarios, tariff_buy, FX=1.0):
    """Varre capacidades de BESS com PV fixo em pv_opt. Recebe `FX` e o repassa ao modelo."""
    bess_list = [0, 1, 2, 4, 8, 12, 16, 20]
    rows = []
    for b in bess_list:
        # Cria nova instância do modelo (importa a classe localmente para evitar circular)
        from model.smart_home import SmartHomeStochastic
        sh2 = SmartHomeStochastic(parameters, scenarios, tariff_buy, FX)
        sh2.build()
        m2 = sh2.model
        m2.PV_cap.fix(pv_opt)
        m2.BESS_capacity.fix(b)

        sol = SolverFactory('highs').solve(m2)
        if (sol.solver.status == SolverStatus.ok and
                sol.solver.termination_condition == TerminationCondition.optimal):
            # cálculo do operacional
            operational_val = float(pyo.value(1.0 * sum(
                m2.prob[s] * sum(
                    m2.tariff[t] * m2.Pgrid_buy[s, t] - 0.7 * m2.tariff[t] * m2.Pgrid_sell[s, t]
                    for t in m2.T
                )
                for s in m2.S
            )))

            # custos anualizados (usa atributos guardados na instância)
            annual_capex_pv = sh2.CAPEX_PV * sh2.crf * pv_opt
            annual_opex_pv = sh2.OPEX_PV_RATE * sh2.CAPEX_PV * pv_opt
            annual_capex_bess = sh2.CAPEX_BESS * sh2.crf * b
            annual_opex_bess = sh2.OPEX_BESS_PER_KWH * b
            daily_capacity_cost = (annual_capex_pv + annual_opex_pv +
                                   annual_capex_bess + annual_opex_bess) / 365.0

            total = float(pyo.value(m2.objective))
            rows.append({
                'BESS_kWh': b,
                'Operational_daily_BRL': operational_val,
                'Daily_capacity_cost_BRL': daily_capacity_cost,
                'Total_daily_BRL': total
            })
        else:
            rows.append({'BESS_kWh': b, 'Operational_daily_BRL': None,
                         'Daily_capacity_cost_BRL': None, 'Total_daily_BRL': None})

    df_sweep = pd.DataFrame(rows)
    print('\nVarredura BESS (PV fixo na capacidade ótima) — valores em BRL/dia')
    print(df_sweep)

    # Plota
    plt.figure(figsize=(8,4))
    plt.plot(df_sweep['BESS_kWh'], df_sweep['Operational_daily_BRL'], marker='o', label='Operacional (BRL/dia)')
    plt.plot(df_sweep['BESS_kWh'], df_sweep['Daily_capacity_cost_BRL'], marker='o', label='Custo diário capacidade (BRL/dia)')
    plt.plot(df_sweep['BESS_kWh'], df_sweep['Total_daily_BRL'], marker='o', label='Total (BRL/dia)')
    plt.xlabel('BESS capacity [kWh]')
    plt.grid(True)
    plt.legend()
    plt.title('Diagnóstico: varredura BESS (PV fixo) — BRL/dia')
    plt.show()