#include "admm.h"

/* Warm-started ADMM for the box-constrained QP
 *     min 0.5 U' H U + g' U   s.t.  lo <= U <= hi
 * using the precomputed Cholesky factor L (L L' = H + rho I) from
 * mpc_model.h.  Each iteration is two triangular solves + a box project.
 * Port of model/qp.py::AdmmQP. */

static void tri_solve_lower(const float *L, const float *b, float *x, int n) {
    for (int i = 0; i < n; i++) {
        float acc = b[i];
        for (int j = 0; j < i; j++) acc -= L[i * n + j] * x[j];
        x[i] = acc / L[i * n + i];
    }
}

static void tri_solve_upper(const float *L, const float *b, float *x, int n) {
    for (int i = n - 1; i >= 0; i--) {
        float acc = b[i];
        for (int j = i + 1; j < n; j++) acc -= L[j * n + i] * x[j];
        x[i] = acc / L[i * n + i];
    }
}

static float clampf_(float v, float lo, float hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

void admm_init(AdmmSolver *s, const float *L, int n, float rho, int max_iter) {
    s->L = L;
    s->n = n;
    s->rho = rho;
    s->max_iter = max_iter;
    s->iterations = 0;
    for (int i = 0; i < n; i++) { s->z[i] = 0.0f; s->lam[i] = 0.0f; }
}

void admm_warm_start(AdmmSolver *s, const float *u) {
    for (int i = 0; i < s->n; i++) s->z[i] = u[i];
}

/* Solves with the given gradient and box bounds; result in s->z, and u0 in
 * s->z[0].  Warm-started from the previous call. */
void admm_solve(AdmmSolver *s, const float *g, const float *lo, const float *hi,
                float *u_out) {
    int n = s->n;
    float rho = s->rho;
    static float u[MPC_N_MAX], rhs[MPC_N_MAX];
    for (int it = 0; it < s->max_iter; it++) {
        s->iterations = it + 1;
        for (int i = 0; i < n; i++)
            rhs[i] = -g[i] + rho * (s->z[i] - s->lam[i]);
        tri_solve_lower(s->L, rhs, u, n);
        tri_solve_upper(s->L, u, rhs, n);   /* rhs <- L'^{-1} u */
        float max_d = 0.0f;
        float max_primal = 0.0f;
        for (int i = 0; i < n; i++) {
            float z_new = clampf_(rhs[i] + s->lam[i], lo[i], hi[i]);
            float d = z_new - s->z[i];
            if (d < 0.0f) d = -d;
            if (d > max_d) max_d = d;
            float primal = rhs[i] - z_new;
            if (primal < 0.0f) primal = -primal;
            if (primal > max_primal) max_primal = primal;
            s->lam[i] += rhs[i] - z_new;
            s->z[i] = z_new;
        }
        if (it > 0 && max_primal < 1e-8f && rho * max_d < 1e-8f) break;
    }
    for (int i = 0; i < n; i++) u_out[i] = s->z[i];
}
