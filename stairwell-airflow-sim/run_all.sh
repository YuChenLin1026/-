#!/bin/bash
# 依序以 4 個並行行程執行所有 CFD case（最耗時的先跑）
cd "$(dirname "$0")"
ORDER="plain_head_vc00 coanda_head_vc00 coax_head_vc00 amp_head_vc00 plain_head_vc15 coanda_head_vc15 coax_head_vc15 amp_head_vc15 plain_free coanda_free coax_free amp_free plain_head_vc30 coanda_head_vc30 coax_head_vc30 amp_head_vc30"
run_one() {
  d=runs/$1
  [ -f "$d/mean_c.f32" ] && { echo "skip $1"; return; }
  start=$(date +%s)
  OMP_NUM_THREADS=1 ./solver/lbm2d "$d" > "$d/log.txt" 2>&1
  rc=$?
  echo "$(date +%H:%M:%S) $1 rc=$rc $(( $(date +%s) - start ))s"
}
export -f run_one
echo $ORDER | tr ' ' '\n' | xargs -P 4 -I{} bash -c 'run_one {}'
echo ALL_DONE
