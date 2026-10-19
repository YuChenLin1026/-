#!/bin/bash
# 臉在斜上方：重新後處理（淺色＋深色）並重建報告，列出要上傳的圖檔
cd "$(dirname "$0")/analysis"
nice python3 s2f_post.py 2>/dev/null | grep -E "口鼻"
THEME=dark nice python3 s2f_post.py >/dev/null 2>&1
cd ../report && python3 make_report.py >/dev/null
ls assets | grep -E "^s2f_" | sed 's|^|assets/|'
