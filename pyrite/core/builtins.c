/* Core builtins for Pyrite */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

/* Print integer */
void pyrite_print_int(int32_t value) {
    printf("%d\n", value);
}

/* Print float */
void pyrite_print_f64(double value) {
    printf("%f\n", value);
}

/* Print bool */
void pyrite_print_bool(int8_t value) {
    printf("%s\n", value ? "true" : "false");
}

/* Print string */
void pyrite_print_str(const char* value) {
    printf("%s\n", value);
}

/* Panic (for runtime errors) */
void pyrite_panic(const char* message) {
    fprintf(stderr, "panic: %s\n", message);
    exit(1);
}

/* Array bounds check */
void pyrite_check_bounds(int64_t index, int64_t length) {
    if (index < 0 || index >= length) {
        pyrite_panic("index out of bounds");
    }
}

/* Assert function for tests */
void pyrite_assert(int8_t condition, const char* message) {
    if (!condition) {
        if (message && message[0] != '\0') {
            fprintf(stderr, "assertion failed: %s\n", message);
        } else {
            fprintf(stderr, "assertion failed\n");
        }
        exit(1);
    }
}

/* Fail function for tests */
void pyrite_fail(const char* message) {
    if (message && message[0] != '\0') {
        fprintf(stderr, "test failed: %s\n", message);
    } else {
        fprintf(stderr, "test failed\n");
    }
    exit(1);
}

