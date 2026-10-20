#!/bin/bash
# 使用者扶手斷面 × 前兩名出風口（2D、臉在斜上方）7 組；3 個並行，留 1 核給其他工作
cd "$(dirname "$0")"
ORDER="PW40_vc15 PC40_vc15 PW40_vc30 PC40_vc30 PC05_vc15 PC05_vc30 PC05_vc00"
run_one() {
  d=runs_profile/$1
  [ -f "$d/mean_c.f32" ] && return
  s=$(date +%s); OMP_NUM_THREADS=1 nice ./solver/lbm2d "$d" > "$d/log.txt" 2>&1; rc=$?
  echo "$(date +%H:%M:%S) $1 rc=$rc $(( $(date +%s) - s ))s"
}
export -f run_one
echo $ORDER | tr ' ' '\n' | xargs -P 3 -I{} bash -c 'run_one {}'
echo ALL_DONE
