#include "safety.h"

/* Stall detector + safe-stop (port of model/impedance.py::ImpedanceSafety).
 * Fires when the load is pinned (|omega_l| ~ 0) while torque builds, and
 * on the filtered torque residual; then the current command is set to
 * zero ("give way"). */

void safety_init(Safety *s, float tau_thresh, float stall_tau_thresh,
                 float debounce, float stall_debounce) {
    s->tau_thresh = tau_thresh;
    s->stall_tau_thresh = stall_tau_thresh;
    s->debounce = debounce;
    s->stall_debounce = stall_debounce;
    s->t_momentum = 0.0f;
    s->t_stall = 0.0f;
    s->detected = 0;
    s->source = 0;
}

void safety_check(Safety *s, float tau_coll_hat, float tau_s_hat,
                  float omega_l, float dt) {
    if (s->detected) return;
    if (fabsf(tau_coll_hat) > s->tau_thresh) s->t_momentum += dt;
    else s->t_momentum = 0.0f;
    if (fabsf(omega_l) < 0.05f && fabsf(tau_s_hat) > s->stall_tau_thresh)
        s->t_stall += dt;
    else
        s->t_stall = 0.0f;
    if (s->t_momentum >= s->debounce) { s->detected = 1; s->source = 1; }
    else if (s->t_stall >= s->stall_debounce) { s->detected = 1; s->source = 2; }
}

float safety_apply(const Safety *s, float u_cmd) {
    return s->detected ? 0.0f : u_cmd;
}
