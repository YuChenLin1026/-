#!/bin/bash
# S6 掃描：4 個並行行程，大的先跑
cd "$(dirname "$0")"
ORDER="C_q40_vc15 C_q40_vc30 C_q20_vc15 C_q20_vc30 C_q05_vc30 C_q10_vc30 W_q05_vc30 W_q10_vc30 W_q20_vc30 W_q40_vc30 Wd_q20_vc30 Wd_q40_vc30 C_q05_vc00 C_q10_vc15 W_q40_vc15 C_q05_vc15 W_q05_vc15 W_q10_vc15 W_q20_vc15 W_q05_vc00"
run_one() {
  d=runs_zone/$1
  [ -f "$d/mean_c.f32" ] && return
  s=$(date +%s); OMP_NUM_THREADS=1 ./solver/lbm2d "$d" > "$d/log.txt" 2>&1; rc=$?
  echo "$(date +%H:%M:%S) $1 rc=$rc $(( $(date +%s) - s ))s"
}
export -f run_one
echo $ORDER | tr ' ' '\n' | xargs -P 4 -I{} bash -c 'run_one {}'
echo ALL_DONE
