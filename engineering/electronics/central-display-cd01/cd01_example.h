/* SPDX-License-Identifier: CC-BY-NC-4.0 */
/* Auromix contributors. Host callbacks are not implemented here. */
#ifndef CD01_EXAMPLE_H
#define CD01_EXAMPLE_H
#include <stdint.h>
#include <stddef.h>
typedef struct {
 /* Driver0=J1pin7/U1; driver1=J1pin11/U2. Select exactly one. SPI mode0,
    MSBfirst,100kHz first-light,2MHz only after signal tests. Hold chip-select
    low across two-byte header and payload. Callbacks return0 on success.
    Caller checks pointers, power/VIO state, buffer lengths, bus exclusion. */
 int(*write_reg)(unsigned driver,uint16_t address,const uint8_t*data,size_t count);
 int(*read_reg)(unsigned driver,uint16_t address,uint8_t*data,size_t count);
 void(*vsync)(int level);
 void(*delay_us)(uint32_t us);
} cd01_io;
int cd01_init_dark(const cd01_io*io);
int cd01_stage_frame(const cd01_io*io,const uint16_t pixels[285],uint8_t master);
void cd01_commit_shared_vsync(const cd01_io*io);
int cd01_spi_header(uint16_t address,int write,uint8_t header[2]);
#endif
