#include <stdint.h>

volatile uint32_t secret_fixed = 0xBBBBBBBB;

volatile uint32_t inputs[16] = {
    0x00000000, 0x11111111, 0x22222222, 0x33333333,
    0x44444444, 0x55555555, 0x66666666, 0x77777777,
    0x88888888, 0x99999999, 0xAAAAAAAA, 0xCCCCCCCC,
    0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678
};

volatile uint32_t masks[16] = {
    0x13579BDF, 0x2468ACE0, 0x0F0F0F0F, 0xF0F0F0F0,
    0x55AA55AA, 0xAA55AA55, 0x12345678, 0x87654321,
    0xCAFEBABE, 0x0BADF00D, 0xDEADBEEF, 0x11223344,
    0x55667788, 0xA5A5A5A5, 0x5A5A5A5A, 0x89ABCDEF
};

volatile uint32_t share_a_out[16];
volatile uint32_t share_b_out[16];
volatile uint32_t recombined_out[16];
volatile uint32_t sca_sink = 0;

__attribute__((noinline))
static uint32_t mask_share_a(uint32_t a, uint32_t m) {
    uint32_t s;
    asm volatile(
        "xor %[s], %[a], %[m]\n"
        : [s] "=&r" (s) : [a] "r" (a), [m] "r" (m));
    return s;
}

__attribute__((noinline))
static uint32_t mask_share_b(uint32_t b, uint32_t m) {
    uint32_t s;
    asm volatile(
        "xor %[s], %[b], %[m]\n"
        "addi %[s], %[s], 0\n"
        : [s] "=&r" (s) : [b] "r" (b), [m] "r" (m));
    return s;
}

__attribute__((noinline))
static uint32_t recombine_shares(uint32_t sa, uint32_t sb) {
    uint32_t x;
    asm volatile(
        "xor  %[x], %[sa], %[sb]\n"
        "xori %[x], %[x],  0\n"
        : [x] "=&r" (x) : [sa] "r" (sa), [sb] "r" (sb));
    return x;
}

int main(void) {
    uint32_t acc = 0;
    for (int i = 0; i < 16; i++) {
        uint32_t sa = mask_share_a(inputs[i], masks[i]);
        uint32_t sb = mask_share_b(secret_fixed, masks[i]);
        share_a_out[i] = sa;
        share_b_out[i] = sb;
        uint32_t x = recombine_shares(sa, sb);
        recombined_out[i] = x;
        acc ^= x;
    }
    sca_sink = acc;
    return 0;
}
