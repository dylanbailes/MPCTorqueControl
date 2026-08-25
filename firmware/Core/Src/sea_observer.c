#include "sea_observer.h"
#include <math.h>

/* Torque estimate from the calibrated spring curve:
 *   tau_s_hat = k_s * delta_theta + k_nl * delta_theta^3
 * (k_nl = 0 for the linear calibration; the learned disturbance model in
 * learned_model.h captures everything the linear spring + linear motor
 * model cannot see.) */

void sea_observer_init(SeaObserver *o, float k_s, float k_nl) {
    o->k_s = k_s;
    o->k_nl = k_nl;
    o->delta_theta = 0.0f;
    o->tau_s_hat = 0.0f;
}

float sea_observer_update(SeaObserver *o, float theta_m, float theta_l) {
    float d = theta_m - theta_l;
    o->delta_theta = d;
    o->tau_s_hat = o->k_s * d + o->k_nl * d * d * d;
    return o->tau_s_hat;
}
