/*
 * lbm2d.c — 2D D2Q9 lattice Boltzmann LES + passive scalar (supply-air tracer)
 *
 * 用途：比較扶手出風口（噴嘴）把「供氣」送到呼吸區的能力。
 *   - 流場：D2Q9 regularized BGK + Smagorinsky 次網格模型（Hou et al. 1996 形式）
 *   - 固體：halfway bounce-back
 *   - 噴嘴入口：平衡態速度入口（velocity prescribed, density local）
 *   - 開放邊界：平衡態 ghost（rho=1，速度取邊界格點前一步速度）+ 吸收層（黏度提高並往遠場平衡態鬆弛）
 *   - 側風：bottom 邊界以 u=(0,Vc) 進氣
 *   - 示蹤劑 c：有限體積 MUSCL(minmod)，對流形式 u·∇c + 擴散（分子 + 渦黏/Sc_t）
 *     c = 1 代表「供氣」，c = 0 代表環境（可能受污染）空氣。
 *
 * 輸入：<dir>/case.cfg（key value）、<dir>/geom.bin
 * 輸出：<dir>/mean_c.f32, mean_ux.f32, mean_uy.f32, last_c.f32, probe.txt, frames/f*.u8 (uint8 frames)
 *
 * 編譯：gcc -O3 -march=native -fopenmp -o lbm2d lbm2d.c -lm
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const int ex[9] = {0, 1, 0, -1, 0, 1, -1, -1, 1};
static const int ey[9] = {0, 0, 1, 0, -1, 1, 1, -1, -1};
static const double w[9] = {4.0 / 9, 1.0 / 9, 1.0 / 9, 1.0 / 9, 1.0 / 9,
                            1.0 / 36, 1.0 / 36, 1.0 / 36, 1.0 / 36};
static const int opp[9] = {0, 3, 4, 1, 2, 7, 8, 5, 6};

enum { FLUID = 0, SOLID = 1, INLET = 2 };

typedef struct {
  int nx, ny;
  long steps, warmup;
  int probe_every, frame_every, sponge;
  double tau0, cs, dlat, sct, vc; /* vc: crossflow (lattice units, +y from bottom) */
} Cfg;

static void die(const char *m) { fprintf(stderr, "error: %s\n", m); exit(1); }

static void read_cfg(const char *path, Cfg *c) {
  FILE *f = fopen(path, "r");
  if (!f) die("cannot open case.cfg");
  char k[64];
  double v;
  memset(c, 0, sizeof(*c));
  c->cs = 0.15; c->sct = 0.7; c->sponge = 25; c->probe_every = 20; c->frame_every = 0;
  while (fscanf(f, "%63s %lf", k, &v) == 2) {
    if (!strcmp(k, "nx")) c->nx = (int)v;
    else if (!strcmp(k, "ny")) c->ny = (int)v;
    else if (!strcmp(k, "steps")) c->steps = (long)v;
    else if (!strcmp(k, "warmup")) c->warmup = (long)v;
    else if (!strcmp(k, "probe_every")) c->probe_every = (int)v;
    else if (!strcmp(k, "frame_every")) c->frame_every = (int)v;
    else if (!strcmp(k, "sponge")) c->sponge = (int)v;
    else if (!strcmp(k, "tau0")) c->tau0 = v;
    else if (!strcmp(k, "cs")) c->cs = v;
    else if (!strcmp(k, "dlat")) c->dlat = v;
    else if (!strcmp(k, "sct")) c->sct = v;
    else if (!strcmp(k, "vc")) c->vc = v;
  }
  fclose(f);
  if (c->nx <= 0 || c->ny <= 0 || c->steps <= 0 || c->tau0 <= 0.5) die("bad cfg");
}

static inline double feq(int i, double rho, double ux, double uy) {
  double eu = ex[i] * ux + ey[i] * uy;
  double uu = ux * ux + uy * uy;
  return w[i] * rho * (1.0 + 3.0 * eu + 4.5 * eu * eu - 1.5 * uu);
}

static inline double minmod(double a, double b) {
  if (a * b <= 0) return 0;
  return fabs(a) < fabs(b) ? a : b;
}

int main(int argc, char **argv) {
  if (argc < 2) die("usage: lbm2d <case_dir>");
  const char *dir = argv[1];
  char path[1024];
  Cfg C;
  snprintf(path, sizeof path, "%s/case.cfg", dir);
  read_cfg(path, &C);
  const int nx = C.nx, ny = C.ny;
  const long N = (long)nx * ny;

  /* geom.bin: uint8 type[N], float32 inux[N], float32 inuy[N], uint8 probe[N] */
  uint8_t *type = malloc(N), *probe = malloc(N);
  float *inux = malloc(N * sizeof(float)), *inuy = malloc(N * sizeof(float));
  snprintf(path, sizeof path, "%s/geom.bin", dir);
  FILE *g = fopen(path, "rb");
  if (!g) die("cannot open geom.bin");
  if (fread(type, 1, N, g) != (size_t)N || fread(inux, sizeof(float), N, g) != (size_t)N ||
      fread(inuy, sizeof(float), N, g) != (size_t)N || fread(probe, 1, N, g) != (size_t)N)
    die("short geom.bin");
  fclose(g);

  float *f0 = malloc(9 * N * sizeof(float)), *f1 = malloc(9 * N * sizeof(float));
  int32_t *src = malloc(9 * N * sizeof(int32_t)); /* pull source index, -1 = open-boundary ghost */
  double *rho = malloc(N * sizeof(double)), *ux = malloc(N * sizeof(double)),
         *uy = malloc(N * sizeof(double)), *nut = malloc(N * sizeof(double));
  double *c = malloc(N * sizeof(double)), *cn = malloc(N * sizeof(double));
  double *sc = calloc(N, sizeof(double)), *sux = calloc(N, sizeof(double)),
         *suy = calloc(N, sizeof(double));
  double *spg = malloc(N * sizeof(double)); /* sponge viscosity multiplier */
  if (!f0 || !f1 || !src || !rho || !ux || !uy || !nut || !c || !cn || !sc || !sux || !suy || !spg)
    die("oom");

  for (int y = 0; y < ny; y++)
    for (int x = 0; x < nx; x++) {
      long n = (long)y * nx + x;
      int d = x;
      if (nx - 1 - x < d) d = nx - 1 - x;
      if (y < d) d = y;
      if (ny - 1 - y < d) d = ny - 1 - y;
      double s = 0;
      if (d < C.sponge) { s = (double)(C.sponge - d) / C.sponge; s = s * s; }
      spg[n] = 1.0 + 20.0 * s;
      rho[n] = 1.0;
      ux[n] = 0;
      uy[n] = (type[n] == SOLID) ? 0 : C.vc;
      if (type[n] == INLET) { ux[n] = inux[n]; uy[n] = inuy[n]; }
      nut[n] = 0;
      c[n] = (type[n] == INLET) ? 1.0 : 0.0;
      for (int i = 0; i < 9; i++) f0[i * N + n] = feq(i, 1.0, ux[n], uy[n]);
    }

  for (int y = 0; y < ny; y++)
    for (int x = 0; x < nx; x++) {
      long n = (long)y * nx + x;
      for (int i = 0; i < 9; i++) {
        int sx = x - ex[i], sy = y - ey[i];
        if (sx < 0 || sx >= nx || sy < 0 || sy >= ny) src[i * N + n] = -1;
        else {
          long sn = (long)sy * nx + sx;
          src[i * N + n] = (int32_t)(type[sn] == SOLID ? opp[i] * N + n : i * N + sn);
        }
      }
    }

  snprintf(path, sizeof path, "%s/probe.txt", dir);
  FILE *pf = fopen(path, "w");
  long nprobe = 0;
  for (long n = 0; n < N; n++) nprobe += probe[n];
  long navg = 0;
  int frame = 0;

  for (long t = 0; t < C.steps; t++) {
    /* ---------- LBM: pull-stream + regularized Smagorinsky collision ---------- */
#pragma omp parallel for schedule(static)
    for (int y = 0; y < ny; y++) {
      for (int x = 0; x < nx; x++) {
        long n = (long)y * nx + x;
        if (type[n] == SOLID) continue;
        double fi[9];
        for (int i = 0; i < 9; i++) {
          int32_t k = src[i * N + n];
          if (k >= 0) fi[i] = f0[k];
          else {
            /* open boundary ghost: equilibrium, rho=1 */
            double bx = ux[n], by = uy[n];
            if (y - ey[i] < 0 && C.vc > 0) { bx = 0; by = C.vc; } /* crossflow inlet */
            fi[i] = feq(i, 1.0, bx, by);
          }
        }
        double r = 0, jx = 0, jy = 0;
        for (int i = 0; i < 9; i++) { r += fi[i]; jx += fi[i] * ex[i]; jy += fi[i] * ey[i]; }
        double vx = jx / r, vy = jy / r;
        if (type[n] == INLET) {
          /* velocity inlet: density extrapolated from the downstream neighbour so the
             inlet injects mass (using the local pulled density starves the inlet). */
          vx = inux[n]; vy = inuy[n];
          int ddx = 0, ddy = 0;
          if (fabs(vx) >= fabs(vy)) ddx = vx > 0 ? 1 : -1; else ddy = vy > 0 ? 1 : -1;
          long m = (long)(y + ddy) * nx + (x + ddx);
          double rin = (x + ddx >= 0 && x + ddx < nx && y + ddy >= 0 && y + ddy < ny &&
                        type[m] != SOLID) ? rho[m] : 1.0;
          for (int i = 0; i < 9; i++) f1[i * N + n] = feq(i, rin, vx, vy);
          rho[n] = rin; ux[n] = vx; uy[n] = vy; nut[n] = 0;
          continue;
        }
        double fe[9], pxx = 0, pyy = 0, pxy = 0;
        for (int i = 0; i < 9; i++) {
          fe[i] = feq(i, r, vx, vy);
          double d = fi[i] - fe[i];
          pxx += d * ex[i] * ex[i]; pyy += d * ey[i] * ey[i]; pxy += d * ex[i] * ey[i];
        }
        double tau0 = 0.5 + (C.tau0 - 0.5) * spg[n];
        double q = sqrt(pxx * pxx + pyy * pyy + 2 * pxy * pxy);
        double tau = 0.5 * (tau0 + sqrt(tau0 * tau0 + 18.0 * sqrt(2.0) * C.cs * C.cs * q / r));
        double om = 1.0 - 1.0 / tau;
        /* absorbing layer: relax toward the far-field state (rho=1, u=(0,vc)) so that
           vortices and pressure waves leave the domain instead of reflecting */
        double sig = 0.08 * (spg[n] - 1.0) / 20.0;
        for (int i = 0; i < 9; i++) {
          double qi = pxx * (ex[i] * ex[i] - 1.0 / 3) + 2 * pxy * ex[i] * ey[i] +
                      pyy * (ey[i] * ey[i] - 1.0 / 3);
          double fpost = fe[i] + om * 4.5 * w[i] * qi;
          if (sig > 0) fpost += sig * (feq(i, 1.0, 0.0, C.vc) - fpost);
          f1[i * N + n] = fpost;
        }
        rho[n] = r; ux[n] = vx; uy[n] = vy;
        nut[n] = (tau - tau0) / 3.0;
      }
    }
    float *tmpf = f0; f0 = f1; f1 = tmpf;

    /* ---------- scalar: FV MUSCL advection + diffusion ---------- */
#pragma omp parallel for schedule(static)
    for (int y = 0; y < ny; y++) {
      for (int x = 0; x < nx; x++) {
        long n = (long)y * nx + x;
        if (type[n] == SOLID) { cn[n] = 0; continue; }
        if (type[n] == INLET) { cn[n] = 1.0; continue; }
        double div = 0;
        /* four faces: +x, -x, +y, -y. flux positive outward. */
        for (int fdir = 0; fdir < 4; fdir++) {
          int dx = (fdir == 0) - (fdir == 1), dy = (fdir == 2) - (fdir == 3);
          int x1 = x + dx, y1 = y + dy;
          double un_self = dx * ux[n] + dy * uy[n];
          double cnb, un_nb, dnb;
          int nb_ok = (x1 >= 0 && x1 < nx && y1 >= 0 && y1 < ny);
          long m = nb_ok ? (long)y1 * nx + x1 : -1;
          if (nb_ok && type[m] == SOLID) continue; /* wall: no flux */
          if (!nb_ok) {
            /* open boundary ghost: inflow brings c=0, outflow zero-gradient */
            un_nb = un_self;
            cnb = (un_self < 0) ? 0.0 : c[n];
            dnb = 0;
          } else {
            un_nb = dx * ux[m] + dy * uy[m];
            cnb = c[m];
            dnb = nut[m];
          }
          double uf = 0.5 * (un_self + un_nb);
          double cf;
          if (uf >= 0) {
            /* upwind = self; need c at x-d */
            int xb = x - dx, yb = y - dy;
            long b = (xb >= 0 && xb < nx && yb >= 0 && yb < ny) ? (long)yb * nx + xb : -1;
            if (b >= 0 && type[b] != SOLID && nb_ok)
              cf = c[n] + 0.5 * minmod(c[n] - c[b], cnb - c[n]);
            else cf = c[n];
          } else {
            int x2 = x1 + dx, y2 = y1 + dy;
            long b = (nb_ok && x2 >= 0 && x2 < nx && y2 >= 0 && y2 < ny) ? (long)y2 * nx + x2 : -1;
            if (b >= 0 && type[b] != SOLID)
              cf = cnb - 0.5 * minmod(cnb - c[n], c[b] - cnb);
            else cf = cnb;
          }
          double dif = C.dlat + 0.5 * (nut[n] + dnb) / C.sct;
          /* advective form u·∇c: subtract c·(∇·u) because the weakly compressible
             LBM velocity is not exactly divergence-free */
          div += uf * (cf - c[n]) - dif * (cnb - c[n]);
        }
        double v = c[n] - div;
        cn[n] = v < 0 ? 0 : (v > 1 ? 1 : v);
      }
    }
    double *tmp = c; c = cn; cn = tmp;

    /* ---------- diagnostics / averaging ---------- */
    if (t % 2000 == 0) {
      double umax = 0;
      long nm = 0, nbad = -1;
      for (long n = 0; n < N; n++) {
        if (type[n] == SOLID) continue;
        double u = sqrt(ux[n] * ux[n] + uy[n] * uy[n]);
        if (!(u == u)) { nbad = n; break; }
        if (u > umax) { umax = u; nm = n; }
      }
      fprintf(stderr, "step %ld/%ld umax=%.4f at (%ld,%ld) rho=%.3f\n", t, C.steps, umax, nm % nx, nm / nx, rho[nm]);
      if (nbad >= 0 || umax > 0.4) {
        long q = nbad >= 0 ? nbad : nm;
        fprintf(stderr, "unstable at step %ld near (%ld,%ld)%s\n", t, q % nx, q / nx, nbad >= 0 ? " NaN" : "");
        return 2;
      }
    }
    if (t >= C.warmup && t % 5 == 0) {
      for (long n = 0; n < N; n++) { sc[n] += c[n]; sux[n] += ux[n]; suy[n] += uy[n]; }
      navg++;
    }
    if (nprobe && t % C.probe_every == 0) {
      double s = 0;
      for (long n = 0; n < N; n++) if (probe[n]) s += c[n];
      fprintf(pf, "%ld %.6f\n", t, s / nprobe);
    }
    if (C.frame_every > 0 && t % C.frame_every == 0) {
      snprintf(path, sizeof path, "%s/frames/f%05d.u8", dir, frame++);
      FILE *fr = fopen(path, "wb");
      if (fr) {
        uint8_t *buf = malloc(N);
        for (long n = 0; n < N; n++)
          buf[n] = type[n] == SOLID ? 255 : (uint8_t)(c[n] * 254.0 + 0.5);
        fwrite(buf, 1, N, fr);
        free(buf);
        fclose(fr);
      }
    }
  }
  fclose(pf);

  float *out = malloc(N * sizeof(float));
  const char *names[3] = {"mean_c.f32", "mean_ux.f32", "mean_uy.f32"};
  double *acc[3] = {sc, sux, suy};
  for (int k = 0; k < 3; k++) {
    for (long n = 0; n < N; n++) out[n] = navg ? (float)(acc[k][n] / navg) : 0.f;
    snprintf(path, sizeof path, "%s/%s", dir, names[k]);
    FILE *o = fopen(path, "wb");
    fwrite(out, sizeof(float), N, o);
    fclose(o);
  }
  for (long n = 0; n < N; n++) out[n] = (float)c[n];
  snprintf(path, sizeof path, "%s/last_c.f32", dir);
  FILE *o = fopen(path, "wb");
  fwrite(out, sizeof(float), N, o);
  fclose(o);
  fprintf(stderr, "done: %ld averaged steps\n", navg);
  return 0;
}
