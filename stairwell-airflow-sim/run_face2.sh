#!/bin/bash
# 臉在斜上方：再加第 05 章的空氣牆（W）6 組；有空出的 CPU 就接著跑
cd "$(dirname "$0")"
ORDER="W40_vc15 W20_vc15 W40_vc30 W20_vc30 W40_vc00 W20_vc00"
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
echo ALL_DONE >> runs_face/run2.log
