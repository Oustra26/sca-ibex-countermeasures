#include <stdint.h>

volatile uint32_t secret_fixed = 0xBBBBBBBB;

volatile uint32_t inputs[16] = {
    0x00000000, 0x11111111, 0x22222222, 0x33333333,
    0x44444444, 0x55555555, 0x66666666, 0x77777777,
    0x88888888, 0x99999999, 0xAAAAAAAA, 0xCCCCCCCC,
    0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678
};

volatile uint32_t dualrail_true_out[16];
volatile uint32_t dualrail_false_out[16];
volatile uint32_t sca_sink = 0;

__attribute__((noinline))
static uint32_t dualrail_true(uint32_t a, uint32_t b) {
    uint32_t x;
    asm volatile(
        "xor %[x], %[a], %[b]\n"
        : [x] "=&r" (x) : [a] "r" (a), [b] "r" (b));
    return x;
}

__attribute__((noinline))
static uint32_t dualrail_false(uint32_t x) {
    uint32_t y;
    asm volatile(
        "xori %[y], %[x], -1\n"
        : [y] "=&r" (y) : [x] "r" (x));
    return y;
}

int main(void) {
    uint32_t acc = 0;
    for (int i = 0; i < 16; i++) {
        uint32_t x_true  = dualrail_true(inputs[i], secret_fixed);
        uint32_t x_false = dualrail_false(x_true);
        dualrail_true_out[i]  = x_true;
        dualrail_false_out[i] = x_false;
        acc ^= x_true;
    }
    sca_sink = acc;
    return 0;
}
