# 绿电直连型电氢氨园区优化运行：V2 接口包

V2 迭代重点：
1. 按老师提示图把“表1/表2计量边界口径”设为主判断口径。
2. 保留题面公式口径作为复核指标，避免答辩时被问到公式差异。
3. 增加算法调用设计：MILP、LP容量估算、场景扩展、Pareto/TOPSIS。

推荐运行：
```bash
python main.py --data_dir /mnt/data --out_dir ./outputs
```

依赖建议：numpy scipy pandas openpyxl matplotlib。
