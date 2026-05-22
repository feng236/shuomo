function cost = storage_capex_daily(eCapMWh, params)
cost = eCapMWh * 1000 * params.storage_capex_yuan_per_kwh / (params.storage_life_year * 365);
end
