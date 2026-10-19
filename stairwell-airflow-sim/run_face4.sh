#!/bin/bash
# D 無側風延長到 24 秒重算；有空出的 CPU 就跑（先等 3 秒再確認一次，避免和 run_face3 搶同一格）
cd "$(dirname "$0")"
d=runs_face/D_vc00
while true; do
  if [ "$(pgrep -xc lbm2d)" -lt 4 ]; then sleep 3; [ "$(pgrep -xc lbm2d)" -lt 4 ] && break; fi
  sleep 20
done
s=$(date +%s); OMP_NUM_THREADS=1 nice ./solver/lbm2d "$d" > "$d/log.txt" 2>&1; rc=$?
echo "$(date +%H:%M:%S) D_vc00 rc=$rc $(( $(date +%s) - s ))s" >> runs_face/run2.log
