#ifndef SEA_OBSERVER_H
#define SEA_OBSERVER_H

typedef struct {
    float k_s, k_nl;      /* calibrated spring curve */
    float delta_theta;    /* [rad] */
    float tau_s_hat;      /* [N.m] */
} SeaObserver;

void sea_observer_init(SeaObserver *o, float k_s, float k_nl);
float sea_observer_update(SeaObserver *o, float theta_m, float theta_l);

#endif /* SEA_OBSERVER_H */
