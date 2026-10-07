#include "encoder.h"
#include <math.h>

/* AS5048A: 14-bit angle over SPI, 16-bit words.
 * The CS / SPI byte transfer is platform glue; the caller provides
 * `read_word` (returns the 16-bit register value). */

#define AS5048_ANGLE_REG 0x3FFF
#define TAU (2.0f * 3.14159265f)
#define RES (TAU / 16384.0f)   /* 14-bit */

static float wrap_pi(float x) {
    while (x > 3.14159265f) x -= TAU;
    while (x < -3.14159265f) x += TAU;
    return x;
}

void encoder_init(Encoder *e, uint16_t (*read_word)(uint16_t reg)) {
    e->read_word = read_word;
    e->angle = 0.0f;
    e->velocity = 0.0f;
    e->prev_angle = 0.0f;
    e->prev_velocity = 0.0f;
    e->valid = 0;
}

/* Read the raw angle (0..2pi) and update the wrapped-difference velocity. */
float encoder_update(Encoder *e, float dt) {
    uint16_t raw = e->read_word(AS5048_ANGLE_REG);
    float angle = (float)(raw & 0x3FFF) * RES;
    if (e->valid) {
        float d = wrap_pi(angle - e->prev_angle) / dt;   /* wrapped diff  */
        e->velocity = 0.8f * e->velocity + 0.2f * d;     /* low-pass      */
    } else {
        e->velocity = 0.0f;
        e->valid = 1;
    }
    e->prev_angle = angle;
    e->angle = angle;
    return e->angle;
}
