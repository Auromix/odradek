/* SPDX-License-Identifier: CC-BY-NC-4.0 */
/* Auromix contributors. Host-independent example, not executed on hardware. */
#ifndef FPL01_LOWER_EXAMPLE_H
#define FPL01_LOWER_EXAMPLE_H
#include <stdint.h>
#include <stddef.h>
typedef struct {
    /* Functions return 0 on success. SPI mode0, MSB-first, 100 kHz first light.
       Hold SS low across 2-byte address header plus payload; read timing follows
       TI SNVU786. Read-only/reserved addresses are never included by generator. */
    int (*write_reg)(uint16_t address,const uint8_t *data,size_t count);
    int (*read_reg)(uint16_t address,uint8_t *data,size_t count);
    void (*vsync)(int level);
    void (*delay_us)(uint32_t us);
} fpl01_lower_io;
int fpl01_lower_init_dark(const fpl01_lower_io *io);
int fpl01_lower_frame(const fpl01_lower_io *io,const uint16_t pixel[42],uint8_t master);
void fpl01_lower_spi_header(uint16_t address,int write,uint8_t header[2]);
#endif
