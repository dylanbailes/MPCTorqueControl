#include "impedance.h"
#include <math.h>

/* Impedance outer loop + momentum-observer collision estimate
 * (port of model/impedance.py).  The learned friction model
 * (learned_friction in learned_model.h) sharpens the observer. */

void impedance_init(Impedance *z, float k_imp, float b_imp, float k_obs) {
    z->k_imp = k_imp;
    z->b_imp = b_imp;
    z->k_obs = k_obs;
    z->rho = 0.0f;
    z->tau_coll_hat = 0.0f;
    z->theta_d = 0.0f;
}

float impedance_reference(const Impedance *z, float theta_l, float omega_l) {
    return z->k_imp * (z->theta_d - theta_l) - z->b_imp * omega_l;
}

float impedance_observer_update(Impedance *z, float tau_m, float tau_s_hat,
                                float omega_m, float dt) {
    float fric = learned_friction(omega_m);   /* learned friction model */
    z->rho += z->k_obs * dt * (tau_m - tau_s_hat - fric - z->rho);
    z->tau_coll_hat = z->rho;
    return z->tau_coll_hat;
}
