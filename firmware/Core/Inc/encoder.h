#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

/* AS5048A magnetic encoder (14-bit) with a one-pole filtered wrapped
 * difference for velocity. System ID uses a separate offline estimator. */

typedef struct {
    uint16_t (*read_word)(uint16_t reg);  /* 14-bit SPI register address */
    float angle;                          /* [rad], 0..2pi              */
    float velocity;                       /* [rad/s], filtered          */
    float prev_angle;
    float prev_velocity;
    uint8_t valid;
} Encoder;

void encoder_init(Encoder *e, uint16_t (*read_word)(uint16_t reg));
float encoder_update(Encoder *e, float dt);   /* returns angle [rad] */

#endif /* ENCODER_H */
