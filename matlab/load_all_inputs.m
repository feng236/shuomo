function data = load_all_inputs(dataDir, params)
%LOAD_ALL_INPUTS Read the eight competition attachments needed by MATLAB.
dataDir = string(dataDir);
loadDf = readtable(find_attachment(dataDir, 1), VariableNamingRule="preserve");
typicalDf = readtable(find_attachment(dataDir, 2), VariableNamingRule="preserve");
windDf = readtable(find_attachment(dataDir, 3), VariableNamingRule="preserve");
pvDf = readtable(find_attachment(dataDir, 4), VariableNamingRule="preserve");

data.times = string(loadDf{:, 1});
data.load_pu = double(loadDf{:, 2});
data.base_load_mw = params.conv_peak_mw * data.load_pu;
data.typical_wind_pu = double(typicalDf{:, 2});
data.typical_pv_pu = double(typicalDf{:, 3});
data.wind_scen_pu = double(windDf{:, 2:7});
data.pv_scen_pu = double(pvDf{:, 2:5});
data.tou_price = params.tou_price;

assert(numel(data.times) == 24, "附件1应包含24行小时数据。");
assert(all(size(data.wind_scen_pu) == [24, 6]), "附件3应为24x6风电场景。");
assert(all(size(data.pv_scen_pu) == [24, 4]), "附件4应为24x4光伏场景。");
end

function path = find_attachment(dataDir, no)
files = [dir(fullfile(dataDir, "*.xlsx")); dir(fullfile(dataDir, "*.xls"))];
needle = "附件" + string(no);
for i = 1:numel(files)
    if contains(string(files(i).name), needle) || contains(lower(string(files(i).name)), "attachment" + string(no))
        path = fullfile(files(i).folder, files(i).name);
        return
    end
end
error("Cannot find attachment %d in %s", no, dataDir);
end
