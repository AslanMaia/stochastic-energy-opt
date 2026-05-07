from data.inputs import parameters, scenarios, tariff_buy
from model.smart_home import SmartHomeStochastic
from analysis.plot import plot

sh = SmartHomeStochastic(parameters, scenarios, tariff_buy)
sh.build()
sh.solve()
plot(sh.results, sh.model, scenarios)