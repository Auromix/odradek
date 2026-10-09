// SPDX-License-Identifier: CC-BY-NC-4.0
#ifndef ODR_EFFECTS_H
#define ODR_EFFECTS_H
#include <stdint.h>
typedef struct { uint32_t epoch, period, on_ms; uint16_t level; uint8_t mode; } Effects;
void effects_init(Effects *e);
int effects_command(Effects *e, const char *line, uint32_t now);
uint16_t effects_value(const Effects *e, uint32_t now);
#endif
