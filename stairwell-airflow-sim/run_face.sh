#!/bin/bash
# 等 S6 兩批都結束後，跑「臉在斜上方」的 S2 改版 12 組
cd "$(dirname "$0")"
until grep -q ALL_DONE runs_zone/run2.log 2>/dev/null; do sleep 20; done
ORDER="B_vc00 B_vc15 B_vc30 A_vc30 C_vc30 D_vc30 A_vc00 A_vc15 D_vc00 D_vc15 C_vc15 C_vc00"
run_one() {
  d=runs_face/$1
  [ -f "$d/mean_c.f32" ] && return
  s=$(date +%s); OMP_NUM_THREADS=1 ./solver/lbm2d "$d" > "$d/log.txt" 2>&1; rc=$?
  echo "$(date +%H:%M:%S) $1 rc=$rc $(( $(date +%s) - s ))s"
}
export -f run_one
echo $ORDER | tr ' ' '\n' | xargs -P 4 -I{} bash -c 'run_one {}'
echo ALL_DONE
