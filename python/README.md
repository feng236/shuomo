# Python专区

本目录是完整计算主线。

```powershell
cd D:\shumo\green_direct_e_h2_nh3_model_pack_v2\python
pip install -r requirements.txt
python main.py --data_dir "D:\qq file\A题\A题" --out_dir ".\outputs"
```

核心脚本：

- `main.py`：统一入口。
- `data_loader.py`：读取附件 1-8，自动解析技术参数、电价和余电上网电价。
- `optimizers.py`：离散启停和连续负荷调度。
- `metrics.py`：绿电直连指标口径。
- `reporting.py`：论文表格、验收表和图形输出。

输出表格位于 `outputs/tables`，图形位于 `outputs/figures`。
