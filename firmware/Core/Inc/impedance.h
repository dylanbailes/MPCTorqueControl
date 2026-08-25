#ifndef IMPEDANCE_H
#define IMPEDANCE_H

#include "learned_model.h"

typedef struct {
    float k_imp, b_imp;   /* virtual spring-damper  */
    float k_obs;          /* momentum observer gain */
    float rho;            /* observer state         */
    float tau_coll_hat;   /* collision torque estimate */
    float theta_d;        /* desired position       */
} Impedance;

void impedance_init(Impedance *z, float k_imp, float b_imp, float k_obs);
float impedance_reference(const Impedance *z, float theta_l, float omega_l);
float impedance_observer_update(Impedance *z, float tau_m, float tau_s_hat,
                                float omega_m, float dt);

#endif /* IMPEDANCE_H */
