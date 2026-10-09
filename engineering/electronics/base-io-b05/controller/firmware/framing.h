// SPDX-License-Identifier: CC-BY-NC-4.0
#ifndef ODR_FRAMING_H
#define ODR_FRAMING_H
#include "effects.h"
typedef struct { char line[32]; unsigned length; int discard; uint32_t last_rx; } Framing;
void framing_poll(Framing *f, uint32_t now);
void framing_error(Framing *f, uint32_t now);
/* Returns 0 for incomplete input, 1 for accepted command, -1 for rejected line. */
int framing_feed(Framing *f, Effects *e, unsigned char c, uint32_t now);
#endif
