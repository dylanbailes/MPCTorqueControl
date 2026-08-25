#include "foc.h"
#include <math.h>

#define SQRT3 1.7320508075688772f

void foc_init(FocCtl *f, float R, float L, float Ke, float v_max,
              float loop_hz) {
    f->R = R; f->L = L; f->Ke = Ke; f->v_max = v_max;
    /* PI tuned for ~1.5 kHz current-loop bandwidth */
    f->kp = L * 2.0f * 3.14159265f * 1500.0f;
    f->ki = R * 2.0f * 3.14159265f * 1500.0f;
    (void)loop_hz;
    f->iq_ref = 0.0f; f->iq = 0.0f; f->id = 0.0f; f->iq_int = 0.0f;
    f->vd = 0.0f; f->vq = 0.0f; f->theta_e = 0.0f;
}

void foc_set_torque(FocCtl *f, float iq_ref) { f->iq_ref = iq_ref; }

void foc_clarke(float ia, float ib, float ic, float *i_alpha, float *i_beta) {
    *i_alpha = ia;
    *i_beta = (ia + 2.0f * ib) / SQRT3;
}

void foc_park(float i_alpha, float i_beta, float theta_e,
              float *i_d, float *i_q) {
    float c = cosf(theta_e), s = sinf(theta_e);
    *i_d = c * i_alpha + s * i_beta;
    *i_q = -s * i_alpha + c * i_beta;
}

void foc_inv_park(float v_d, float v_q, float theta_e,
                  float *v_alpha, float *v_beta) {
    float c = cosf(theta_e), s = sinf(theta_e);
    *v_alpha = c * v_d - s * v_q;
    *v_beta = s * v_d + c * v_q;
}

void foc_svpwm(float v_alpha, float v_beta, float v_max, float duty[3]) {
    float va = v_alpha;
    float vb = -0.5f * v_alpha + (SQRT3 / 2.0f) * v_beta;
    float vc = -0.5f * v_alpha - (SQRT3 / 2.0f) * v_beta;
    float vmin = va < vb ? (va < vc ? va : vc) : (vb < vc ? vb : vc);
    float vmax = va > vb ? (va > vc ? va : vc) : (vb > vc ? vb : vc);
    float off = 0.5f * (vmax + vmin);
    va -= off; vb -= off; vc -= off;
    duty[0] = 0.5f + 0.5f * fmaxf(-1.0f, fminf(1.0f, va / v_max));
    duty[1] = 0.5f + 0.5f * fmaxf(-1.0f, fminf(1.0f, vb / v_max));
    duty[2] = 0.5f + 0.5f * fmaxf(-1.0f, fminf(1.0f, vc / v_max));
}

float foc_mech_to_elec(float theta_m, int pole_pairs) {
    float e = pole_pairs * theta_m;
    e = e - (float)(int)(e / (2.0f * 3.14159265f)) * 2.0f * 3.14159265f;
    if (e < 0.0f) e += 2.0f * 3.14159265f;
    return e;
}

/* Called at 10 kHz with measured phase currents and the mechanical angle.
 * Drives the q-axis to iq_ref (PI + back-EMF feedforward, conditional
 * anti-windup), then SVPWM. */
float foc_current_loop(FocCtl *f, float ia, float ib, float theta_m,
                       float dt) {
    float ic = -ia - ib;
    float i_alpha, i_beta, i_d, i_q;
    foc_clarke(ia, ib, ic, &i_alpha, &i_beta);
    f->theta_e = foc_mech_to_elec(theta_m, 7);
    foc_park(i_alpha, i_beta, f->theta_e, &i_d, &i_q);
    f->iq = i_q; f->id = i_d;

    float err = f->iq_ref - i_q;
    f->iq_int += f->ki * err * dt;
    float vq = f->iq_int + f->kp * err + f->Ke * theta_m; /* back-EMF FF */
    float vq_sat = fmaxf(-f->v_max, fminf(f->v_max, vq));
    if (vq_sat != vq) f->iq_int -= f->ki * err * dt;      /* anti-windup */
    f->vq = vq_sat;
    f->vd = 0.0f;                                          /* id -> 0 */

    float v_alpha, v_beta;
    foc_inv_park(f->vd, f->vq, f->theta_e, &v_alpha, &v_beta);
    foc_svpwm(v_alpha, v_beta, f->v_max, f->duty);
    return f->vq;
}

/* Alignment: apply a known (duty_a, duty_b, duty_c) vector and record the
 * rotor angle -> derive the electrical offset for foc_mech_to_elec. */
float foc_align(FocCtl *f, float duty_a, float duty_b, float duty_c,
                float theta_m) {
    (void)duty_a; (void)duty_b; (void)duty_c; (void)f;
    return theta_m; /* placeholder: set offset so that theta_e = 0 aligns */
}
