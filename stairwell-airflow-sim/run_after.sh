#!/bin/bash
# 等主執行器（PID 參數）結束後，再跑一次 run_all.sh 補齊缺少結果的算例
cd "$(dirname "$0")"
while kill -0 "$1" 2>/dev/null; do sleep 20; done
echo "$(date +%H:%M:%S) main runner ended; resuming"
./run_all.sh
