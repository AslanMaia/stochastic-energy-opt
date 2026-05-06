from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import pyomo.environ as pyo
import pandas as pd
import matplotlib.pyplot as plt

def bess_sweep(pv_opt, parameters, scenarios, tariff_buy):
    """Varre capacidades de BESS com PV fixo em pv_opt repassa ao modelo."""
    bess_list = [0, 1, 2, 4, 8, 12, 16, 20]
    rows = []
    for b in bess_list:
        # Cria nova instância do modelo (importa a classe localmente para evitar circular)
        from model.smart_home import SmartHomeStochastic
        sh2 = SmartHomeStochastic(parameters, scenarios, tariff_buy)
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


def plot_results(sh):
    """Plot dos resultados já gerados em `sh.results`.

    Recebe uma instância `SmartHomeStochastic` (ou objeto com atributos
    `model`, `results`, `scenarios` e `parameters`) e plota os gráficos por
    cenário.
    """
    import numpy as _np

    m = sh.model
    horas = list(m.T)
    cenarios = list(sh.results.keys())
    n = len(cenarios)

    fig, axes = plt.subplots(nrows=n, ncols=2, figsize=(14, 4 * n), sharey=False)
    fig.suptitle("Resultados (BRL)", fontsize=14, fontweight='bold')

    for i, s in enumerate(cenarios):
        df = sh.results[s]
        if n == 1:
            ax1, ax2 = axes
        else:
            ax1 = axes[i, 0]
            ax2 = axes[i, 1]

        prob = sh.scenarios[s]['prob']

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
            cap_max = pyo.value(sh.model.BESS_capacity)
        except Exception:
            cap_max = sh.parameters['BESS']['capacity']
        ax2.axhline(cap_max, color='red', linestyle='--', linewidth=1, label=f'Cap. máx. ({cap_max} kWh)')

        ax2.set_title(f"Bateria — {s}")
        ax2.set_ylabel("Energia [kWh]")
        ax2.set_xlabel("Hora")
        ax2.set_ylim(0, cap_max * 1.15)
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()