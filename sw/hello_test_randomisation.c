/* Version a randomisation temporelle.
   Extraite du fichier consolide hello_test.c du projet.
   Somme des delais = 30  ->  surcout de 16 x 34 + 26 x 30 = 1324 cycles
   Desynchronisation comprise entre 34 (d=0) et 164 (d=5) cycles. */

#include <stdint.h>

volatile uint32_t secret_fixed = 0xBBBBBBBB;

volatile uint32_t inputs[16] = {
    0x00000000,
    0x11111111,
    0x22222222,
    0x33333333,
    0x44444444,
    0x55555555,
    0x66666666,
    0x77777777,
    0x88888888,
    0x99999999,
    0xAAAAAAAA,
    0xCCCCCCCC,
    0xDDDDDDDD,
    0xEEEEEEEE,
    0xFFFFFFFF,
    0x12345678
};

volatile uint32_t jitters[16] = {
    0, 3, 1, 2,
    4, 0, 2, 1,
    5, 3, 0, 2,
    1, 4, 2, 0
};

volatile uint32_t randomized_out[16];
volatile uint32_t sca_sink = 0;

__attribute__((noinline))
static void random_delay(uint32_t d) {
    for (volatile uint32_t i = 0; i < d; i++) {
        asm volatile("nop");
    }
}

__attribute__((noinline))
static uint32_t sca_kernel(uint32_t a, uint32_t b) {
    uint32_t x;
    asm volatile(
        "xor %[x], %[a], %[b]\n"
        : [x] "=&r" (x)
        : [a] "r" (a), [b] "r" (b)
    );
    return x;
}

int main(void) {
    uint32_t acc = 0;

    for (int i = 0; i < 16; i++) {
        uint32_t a = inputs[i];
        uint32_t d = jitters[i];

        random_delay(d);

        uint32_t x = sca_kernel(a, secret_fixed);

        randomized_out[i] = x;
        acc ^= x;
    }

    sca_sink = acc;
    return 0;
}
