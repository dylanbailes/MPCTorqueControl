#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

/* AS5048A magnetic encoder (14-bit) with filtered velocity (port of the
 * Savitzky-Golay approach used in learn/system_id.py — here a one-pole
 * filter on the wrapped angle difference). */

typedef struct {
    uint16_t (*read_word)(uint8_t reg);   /* platform SPI read          */
    float angle;                          /* [rad], 0..2pi              */
    float velocity;                       /* [rad/s], filtered          */
    float prev_angle;
    float prev_velocity;
    uint8_t valid;
} Encoder;

void encoder_init(Encoder *e, uint16_t (*read_word)(uint8_t reg));
float encoder_update(Encoder *e, float dt);   /* returns angle [rad] */

#endif /* ENCODER_H */
