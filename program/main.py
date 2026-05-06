from data.inputs import parameters, scenarios, tariff_buy
from model.smart_home import SmartHomeStochastic
from analysis.plot import bess_sweep
import pyomo.environ as pyo

if __name__ == "__main__":
    # 1. Instancia e resolve o modelo estocástico
    sh = SmartHomeStochastic(parameters, scenarios, tariff_buy)
    sh.build()
    sh.solve()
    sh.plot()

    # 2. Diagnóstico: varredura BESS com PV fixo no ótimo
    pv_cap_val = pyo.value(sh.model.PV_cap, exception=False)
    if pv_cap_val is None:
        raise RuntimeError("PV_cap não foi atribuída — o modelo não foi resolvido corretamente")
    pv_opt = float(pv_cap_val)
    bess_sweep(pv_opt, parameters, scenarios, tariff_buy)