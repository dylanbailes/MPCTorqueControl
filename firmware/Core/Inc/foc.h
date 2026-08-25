#ifndef FOC_H
#define FOC_H

#include <stdint.h>

/* Field-oriented control math + current loop (port of model/foc.py).
 * Run from the 10 kHz TIM2 ISR. */

typedef struct {
    float R, L, Ke;           /* motor parameters          */
    float v_max;              /* Vbus/sqrt(3)              */
    float kp, ki;             /* current-loop PI gains     */
    float iq_ref;             /* torque command [A]        */
    float iq, id;             /* measured currents         */
    float iq_int;             /* integrator state          */
    float vd, vq;             /* applied voltages          */
    float theta_e;            /* electrical angle          */
    float duty[3];            /* duty cycles 0..1          */
} FocCtl;

void foc_init(FocCtl *f, float R, float L, float Ke, float v_max,
              float loop_hz);
void foc_set_torque(FocCtl *f, float iq_ref);   /* torque loop -> current cmd */
float foc_current_loop(FocCtl *f, float ia, float ib, float theta_m,
                       float dt);               /* returns applied vq (debug) */
float foc_align(FocCtl *f, float duty_a, float duty_b, float duty_c,
                float theta_m);

/* pure math (unit-testable) */
void foc_clarke(float ia, float ib, float ic, float *i_alpha, float *i_beta);
void foc_park(float i_alpha, float i_beta, float theta_e,
              float *i_d, float *i_q);
void foc_inv_park(float v_d, float v_q, float theta_e,
                  float *v_alpha, float *v_beta);
void foc_svpwm(float v_alpha, float v_beta, float v_max, float duty[3]);
float foc_mech_to_elec(float theta_m, int pole_pairs);

#endif /* FOC_H */
