# Dados horários
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
# Tarifas já em BRL (USD->BRL aplicado previamente: *4.96)
tariff_buy = [
    1.111982, 1.111982, 1.111982, 1.111982, 1.111982, 1.111982,
    1.111982, 1.111982, 1.111982, 1.111982, 1.111982, 1.111982,
    1.111982, 1.111982, 1.111982, 1.111982, 1.111982, 1.618398,
    2.568883, 2.568883, 2.568883, 1.618398, 1.111982, 1.111982
]  # BRL/kWh

parameters = {
    "Grid": {"Pmax": 90},
    "BESS": {
        "Pmax": 5.0,
        "eff": 0.90,
        "self_discharge": 0.01,
        "capacity": 8,
        "initial capacity": 0,
    }
}

scenarios = {
    "base": {
        "P_demand": P_demand_data,
        "P_pv":     P_pv_data,
        "prob":     0.34,
    },
    "alta_demanda": {
        "P_demand": [round(x * 1.5, 4) for x in P_demand_data],
        "P_pv":     [round(x * 0.5, 4) for x in P_pv_data],
        "prob":     0.33,
    },
    "alta_geracao": {
        "P_demand": [round(x * 0.5, 4) for x in P_demand_data],
        "P_pv":     [round(x * 1.5, 4) for x in P_pv_data],
        "prob":     0.33,
    },
}