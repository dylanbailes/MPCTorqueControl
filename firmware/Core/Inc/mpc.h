#ifndef MPC_H
#define MPC_H

#include "mpc_model.h"

typedef struct {
    int max_iter;   /* ADMM iterations per solve (25 recommended) */
} MpcConfig;

extern float mpc_u_prev;   /* last applied input (slew reference) */

void mpc_init(const MpcConfig *cfg);
float mpc_step(float *x0, float yref);

#endif /* MPC_H */
