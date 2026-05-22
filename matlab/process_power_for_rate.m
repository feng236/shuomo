function p = process_power_for_rate(rateTph, params)
%PROCESS_POWER_FOR_RATE Convert ammonia production rate to process power.
p = (params.alk_mw_36 + params.pem_mw_36 + params.nh3_mw_36) / params.nh3_rate_tph_36 * rateTph;
end
