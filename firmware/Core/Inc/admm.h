#ifndef ADMM_H
#define ADMM_H

#include "mpc_model.h"   /* MPC_N, MPC_L, MPC_RHO */

#define MPC_N_MAX MPC_N

typedef struct {
    const float *L;       /* Cholesky factor of H + rho I, N x N lower   */
    int n;
    float rho;
    int max_iter;
    int iterations;
    float z[MPC_N_MAX];   /* primal iterate (warm start)                 */
    float lam[MPC_N_MAX]; /* dual iterate (warm start)                   */
} AdmmSolver;

void admm_init(AdmmSolver *s, const float *L, int n, float rho, int max_iter);
void admm_warm_start(AdmmSolver *s, const float *u);
void admm_solve(AdmmSolver *s, const float *g, const float *lo, const float *hi,
                float *u_out);

#endif /* ADMM_H */
