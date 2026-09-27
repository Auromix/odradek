/* SPDX-License-Identifier: CC-BY-NC-4.0 */
/* Auromix contributors. Host-independent example, not executed on hardware. */
#ifndef ULP02_EXAMPLE_H
#define ULP02_EXAMPLE_H
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
} ulp02_io;
int ulp02_init_dark(const ulp02_io *io);
int ulp02_frame(const ulp02_io *io,const uint16_t pixel[113],uint8_t master);
void ulp02_spi_header(uint16_t address,int write,uint8_t header[2]);
#endif
