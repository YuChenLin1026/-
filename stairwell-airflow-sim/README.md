# 樓梯扶手送風模擬（第二階段研究）

樓梯逃生導引扶手系統的送風技術電腦模擬。報告由 `report/make_report.py` 產生（`report/index.html`）。

| 模擬 | 檔案 | 內容 |
|---|---|---|
| S1 | `analysis/s1_duct.py` | 扶手風道壓損、風機工作點、出風均勻度（一維管網） |
| S2 | `solver/lbm2d.c`、`cases/build.py`、`analysis/s2_post.py` | 四種出風口的 2D CFD（LBM-LES ＋ 示蹤劑），量測口鼻區供氣比例 SAF |
| S3 | `analysis/s3_filter.py` | 濾材、氣旋分級效率與煙粒徑分布 |
| S4 | `analysis/s4_exhaust.py` | 扶手當排煙管的容量上限 |
| 驗證 | `validation/poiseuille.py` | 求解器對平行板管流解析解 |

## 重現
```bash
gcc -O3 -march=native -fopenmp -o solver/lbm2d solver/lbm2d.c -lm
python3 cases/build.py          # 產生 16 個 CFD 算例
./run_all.sh                    # 4 個並行，約 2 小時
cd analysis && python3 s1_duct.py && python3 s3_filter.py && python3 s4_exhaust.py && python3 s2_post.py --video
THEME=dark python3 s2_post.py   # 深色版圖表
python3 ../report/make_report.py
```

本專案是設計研究用的電腦模型，不是消防工程設計文件，也不代表任何火場呼吸防護能力。
