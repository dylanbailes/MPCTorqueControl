#ifndef TASKS_H
#define TASKS_H

#include <stdint.h>

/* platform glue (implement per CubeMX project) */
float  adc_phase_a(void);
float  adc_phase_b(void);
uint16_t spi1_read_word(uint16_t reg);  /* legacy motor SPI scaffold */
uint16_t spi2_read_word(uint16_t reg);  /* output SPI scaffold */
void   pwm_update(void *foc);           /* write duty -> TIM1 */
void   cdc_send(const char *s, int len);
void   start_timers(void);
void   osDelay(uint32_t ms);
uint32_t osKernelGetTickCount(void);

extern volatile uint8_t g_imp_active;

void current_loop_isr(void);
void torque_loop_isr(void);
void telemetry_task(void *arg);
void control_init(void);

#endif /* TASKS_H */
