#include "tasks.h"
#include "foc.h"
#include "encoder.h"
#include "sea_observer.h"
#include "mpc.h"
#include "impedance.h"
#include "safety.h"
#include <stdio.h>
#include <string.h>

/* ======================================================================
 * Global control state (the "plant twin" in firmware)
 * ====================================================================== */

FocCtl      g_foc;
Encoder     g_enc_m;      /* motor-side MT6701 ABZ timer encoder */
Encoder     g_enc_l;      /* output-side AS5048A encoder (SPI) */
SeaObserver g_obs;
Impedance   g_imp;
Safety      g_safety;
MpcConfig   g_mpc_cfg = { .max_iter = MPC_MAX_ITER };

volatile float g_tau_ref = 0.0f;   /* torque reference from impedance/task */
volatile float g_iq_cmd = 0.0f;    /* applied current command (debug)      */
volatile float g_tau_s_hat = 0.0f;
volatile float g_tau_coll_hat = 0.0f;
volatile uint8_t g_safety_fired = 0;

/* ======================================================================
 * 10 kHz current loop (TIM2 ISR) — FOC + current PI
 * ====================================================================== */
void current_loop_isr(void) {
    float ia = adc_phase_a();
    float ib = adc_phase_b();
    float theta_m = g_enc_m.angle;
    float dt = 1.0f / 10000.0f;
    (void)foc_current_loop(&g_foc, ia, ib, theta_m, g_enc_m.velocity, dt);
    pwm_update(&g_foc);   /* write duty cycles to TIM1 */
}

/* ======================================================================
 * 2 kHz torque loop (TIM3 ISR) — observer + MPC + learned FF + safety
 * ====================================================================== */
/* Learned-FF history (dynamic features): previous LEARNED_LAG commands and
 * velocities, newest first — must match the Python residual's lag order.
 * The call below passes the history by name (w_prev1..2 / u_prev1..2), so
 * a re-export with a different lag would silently break the call — make
 * that a compile error instead. */
_Static_assert(LEARNED_LAG == 2, "tasks.c FF call is hardcoded for lag=2");
static float g_ff_u_prev[LEARNED_LAG] = {0.0f};
static float g_ff_w_prev[LEARNED_LAG] = {0.0f};

void torque_loop_isr(void) {
    float dt = 1.0f / 2000.0f;
    encoder_update(&g_enc_m, dt);
    encoder_update(&g_enc_l, dt);
    float theta_m = g_enc_m.angle, theta_l = g_enc_l.angle;
    float omega_m = g_enc_m.velocity, omega_l = g_enc_l.velocity;

    g_tau_s_hat = sea_observer_update(&g_obs, theta_m, theta_l);

    /* impedance outer loop (overrides external reference when active) */
    float tau_ref = g_tau_ref;
    if (g_imp_active) {
        tau_ref = impedance_reference(&g_imp, theta_l, omega_l);
    }

    /* MPC torque controller */
    float x0[4] = { theta_m, omega_m, theta_l, omega_l };
    float u_mpc = mpc_step(x0, tau_ref);

    /* learned disturbance feedforward (friction + cogging + ripple) — the
     * dynamic (lagged) features need the previous commands and velocities */
    float u_ff = learned_feedforward(theta_m, omega_m, u_mpc,
                                     g_ff_w_prev[0], g_ff_w_prev[1],
                                     g_ff_u_prev[0], g_ff_u_prev[1]); /* A */
    float u = u_mpc + u_ff;

    /* shift FF history for the next tick (newest first) */
    for (int i = LEARNED_LAG - 1; i > 0; i--) {
        g_ff_w_prev[i] = g_ff_w_prev[i - 1];
        g_ff_u_prev[i] = g_ff_u_prev[i - 1];
    }
    g_ff_w_prev[0] = omega_m;
    g_ff_u_prev[0] = u_mpc;

    /* momentum observer + safety */
    float tau_m = g_foc.Ke * g_foc.iq;   /* Kt = Ke in SI */
    g_tau_coll_hat = impedance_observer_update(&g_imp, tau_m, g_tau_s_hat,
                                               omega_m, dt);
    safety_check(&g_safety, g_tau_coll_hat, g_tau_s_hat, omega_l, dt);
    u = safety_apply(&g_safety, u);
    g_safety_fired = g_safety.detected;

    /* Feedforward shares MPC's current budget, matching the simulation. */
    u = fmaxf(-MPC_U_MAX, fminf(MPC_U_MAX, u));
    mpc_u_prev = u;
    g_iq_cmd = u;
    foc_set_torque(&g_foc, u);
}

/* ======================================================================
 * 1 kHz telemetry task — stream state over USB-CDC
 * ====================================================================== */
void telemetry_task(void *arg) {
    (void)arg;
    char line[96];
    for (;;) {
        osDelay(1000 / 1000);
        snprintf(line, sizeof(line),
                 "%lu %f %f %f %f %f %u",
                 (unsigned long)osKernelGetTickCount(),
                 g_enc_m.angle, g_enc_l.angle,
                 g_tau_s_hat, g_tau_ref, g_iq_cmd, g_safety_fired);
        cdc_send(line, strlen(line));
    }
}

/* ======================================================================
 * Init (called from main after HAL_Init + SystemClock_Config)
 * ====================================================================== */
void control_init(void) {
    /* calibrated from system ID (see docs/milestones.md) */
    foc_init(&g_foc, 1.5f, 3.0e-4f, 0.1f, 13.86f, 10000.0f);
    /* TODO: replace the motor-side SPI callback with MT6701 ABZ timer
     * initialization when the encoder driver is migrated; the load-side
     * AS5048A remains on SPI1. */
    encoder_init(&g_enc_m, spi1_read_word);
    encoder_init(&g_enc_l, spi2_read_word);
    sea_observer_init(&g_obs, 0.985f, 0.0f);          /* calibrated k_s */
    impedance_init(&g_imp, 0.8f, 0.15f, 100.0f);     /* HRI impedance  */
    safety_init(&g_safety, 0.40f, 0.15f, 0.05f, 0.08f);
    mpc_init(&g_mpc_cfg);
    mpc_u_prev = 0.0f;
    g_imp.theta_d = 0.5f;    /* demo: swing toward 0.5 rad */
    g_imp_active = 1;
    start_timers();          /* TIM2 @10 kHz, TIM3 @2 kHz, ADC/PWM init */
}
