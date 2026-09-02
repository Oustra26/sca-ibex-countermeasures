#include <stdint.h>

volatile uint32_t secret_fixed = 0xBBBBBBBB;

volatile uint32_t inputs[16] = {
    0x00000000, 0x11111111, 0x22222222, 0x33333333,
    0x44444444, 0x55555555, 0x66666666, 0x77777777,
    0x88888888, 0x99999999, 0xAAAAAAAA, 0xCCCCCCCC,
    0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678
};

volatile uint32_t results[16];
volatile uint32_t sca_sink = 0;

int main(void) {
    uint32_t acc = 0;
    for (int i = 0; i < 16; i++) {
        uint32_t x;
        asm volatile(
            "xor %[x], %[a], %[b]\n"
            : [x] "=&r" (x)
            : [a] "r" (inputs[i]),
              [b] "r" (secret_fixed)
        );
        results[i] = x;
        acc ^= x;
    }
    sca_sink = acc;
    return 0;
}
