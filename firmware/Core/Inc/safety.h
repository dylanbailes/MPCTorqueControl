#ifndef SAFETY_H
#define SAFETY_H

#include <math.h>

typedef struct {
    float tau_thresh;        /* momentum-observer threshold [N.m] */
    float stall_tau_thresh;  /* stall torque threshold [N.m]      */
    float debounce;          /* momentum debounce [s]             */
    float stall_debounce;    /* stall debounce [s]                */
    float t_momentum, t_stall;
    uint8_t detected;
    uint8_t source;          /* 1 = momentum, 2 = stall           */
} Safety;

void safety_init(Safety *s, float tau_thresh, float stall_tau_thresh,
                 float debounce, float stall_debounce);
void safety_check(Safety *s, float tau_coll_hat, float tau_s_hat,
                  float omega_l, float dt);
float safety_apply(const Safety *s, float u_cmd);

#endif /* SAFETY_H */
