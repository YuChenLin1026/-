#!/bin/bash
# 等 S6 第一批結束後，跑「往斜上方送風」8 組
cd "$(dirname "$0")"
until grep -q ALL_DONE runs_zone/run.log 2>/dev/null; do sleep 20; done
ORDER="Ku_q20_vc00 Ku_q20_vc15 Ku_q10_vc00 Ku_q10_vc15 Cu_q20_vc00 Cu_q10_vc00 Cu_q20_vc15 Cu_q10_vc15"
run_one() {
  d=runs_zone/$1
  [ -f "$d/mean_c.f32" ] && return
  s=$(date +%s); OMP_NUM_THREADS=1 ./solver/lbm2d "$d" > "$d/log.txt" 2>&1; rc=$?
  echo "$(date +%H:%M:%S) $1 rc=$rc $(( $(date +%s) - s ))s"
}
export -f run_one
echo $ORDER | tr ' ' '\n' | xargs -P 4 -I{} bash -c 'run_one {}'
echo ALL_DONE
