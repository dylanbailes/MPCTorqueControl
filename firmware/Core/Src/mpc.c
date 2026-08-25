#include "mpc.h"
#include "admm.h"
#include <math.h>

/* Condensed MPC (port of model/mpc.py::SeaMPC).  The gradient is the
 * constant affine map
 *     g(U) = MPC_MX x0 + MPC_MY yref + MPC_MPREV u_prev
 * and the box constraints are the current + slew limits.  The ADMM solver
 * runs 25 warm-started iterations — well within the 2 kHz torque-loop
 * budget on the G431 at 170 MHz. */

static AdmmSolver s_admm;
static float s_lo[MPC_N], s_hi[MPC_N], s_g[MPC_N], s_u[MPC_N];

void mpc_init(const MpcConfig *cfg) {
    admm_init(&s_admm, MPC_L, MPC_N, MPC_RHO, cfg->max_iter);
}

/* One torque-loop step.  x0 = [theta_m, omega_m, theta_l, omega_l],
 * yref = torque reference [N.m].  Returns the current command [A] that
 * the torque loop applies (before the learned feedforward). */
float mpc_step(float *x0, float yref) {
    int n = MPC_N;
    /* gradient (affine in x0, yref, u_prev) */
    for (int i = 0; i < n; i++) {
        float g = 0.0f;
        for (int j = 0; j < MPC_NX; j++) g += MPC_MX[i * MPC_NX + j] * x0[j];
        s_g[i] = g + MPC_MY[i] * yref + MPC_MPREV[i] * mpc_u_prev;
    }
    /* bounds: |u| <= U_MAX, |u0 - u_prev| <= DU_MAX */
    for (int i = 0; i < n; i++) { s_lo[i] = -MPC_U_MAX; s_hi[i] = MPC_U_MAX; }
    s_lo[0] = fmaxf(-MPC_U_MAX, mpc_u_prev - MPC_DU_MAX);
    s_hi[0] = fminf(MPC_U_MAX, mpc_u_prev + MPC_DU_MAX);

    admm_solve(&s_admm, s_g, s_lo, s_hi, s_u);
    float u = s_u[0];
    mpc_u_prev = u;
    return u;
}

float mpc_u_prev = 0.0f;
