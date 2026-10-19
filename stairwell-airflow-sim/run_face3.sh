#!/bin/bash
# 臉在斜上方：空氣牆 W 剩下的 5 組＋無側風延長到 24 秒重算的 B、C；有空出的 CPU 就接著跑
cd "$(dirname "$0")"
ORDER="B_vc00 W20_vc15 W40_vc30 C_vc00 W20_vc30 W40_vc00 W20_vc00 $EXTRA"
run_one() {
  d=runs_face/$1
  [ -f "$d/mean_c.f32" ] && return
  s=$(date +%s); OMP_NUM_THREADS=1 nice ./solver/lbm2d "$d" > "$d/log.txt" 2>&1; rc=$?
  echo "$(date +%H:%M:%S) $1 rc=$rc $(( $(date +%s) - s ))s" >> runs_face/run2.log
}
for c in $ORDER; do
  while [ "$(pgrep -xc lbm2d)" -ge 4 ]; do sleep 20; done
  run_one "$c" &
  sleep 5
done
wait
while pgrep -x lbm2d > /dev/null; do sleep 20; done
echo ALL_DONE >> runs_face/run2.log
