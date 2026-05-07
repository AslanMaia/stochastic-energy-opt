import matplotlib.pyplot as plt
import pyomo.environ as pyo

def plot(results, model, scenarios):
    horas    = list(model.T)
    cenarios = list(results.keys())
    n        = len(cenarios)

    fig, axes = plt.subplots(nrows=n, ncols=2, figsize=(14, 4 * n), sharey=False)
    fig.suptitle("Resultados (BRL)", fontsize=14, fontweight='bold')

    for i, s in enumerate(cenarios):
        df  = results[s]
        ax1 = axes[i, 0]
        ax2 = axes[i, 1]

        prob = scenarios[s]['prob']

        ax1.plot(horas, df['Demanda'],       label='Demanda',       color='black',     linewidth=2)
        ax1.plot(horas, df['PV'],            label='PV',            color='orange',    linewidth=1.5)
        ax1.plot(horas, df['Rede_compra'],   label='Rede compra',   color='steelblue', linewidth=1.5)
        ax1.plot(horas, df['Rede_venda'],    label='Rede venda',    color='green',     linewidth=1.5, linestyle='--')
        ax1.plot(horas, df['BESS_descarga'], label='BESS descarga', color='red',       linewidth=1.5, linestyle='-.')
        ax1.plot(horas, df['BESS_carga'],    label='BESS carga',    color='purple',    linewidth=1.5, linestyle=':')

        ax1.set_title(f"Cenário: {s}  (π = {prob})")
        ax1.set_ylabel("Potência [kW]")
        ax1.set_xlabel("Hora")
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

        cap_max = pyo.value(model.BESS_capacity)

        ax2.fill_between(horas, df['E_BESS'], alpha=0.4, color='purple', label='E_BESS')
        ax2.plot(horas, df['E_BESS'], color='purple', linewidth=1.5)
        ax2.axhline(cap_max, color='red', linestyle='--', linewidth=1, label=f'Cap. máx. ({cap_max:.2f} kWh)')

        ax2.set_title(f"Bateria — {s}")
        ax2.set_ylabel("Energia [kWh]")
        ax2.set_xlabel("Hora")
        ax2.set_ylim(0, max(cap_max * 1.15, 0.1))
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()