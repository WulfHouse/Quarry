/* Tensor implementation in C for Pyrite */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct {
    double* data;
    int64_t rows;
    int64_t cols;
} Tensor;

Tensor tensor_new(int64_t rows, int64_t cols) {
    Tensor t;
    t.data = malloc(rows * cols * sizeof(double));
    if (t.data == NULL) {
        /* Allocation failed - return empty tensor */
        t.data = NULL;
        t.rows = 0;
        t.cols = 0;
        return t;
    }
    t.rows = rows;
    t.cols = cols;
    memset(t.data, 0, rows * cols * sizeof(double));
    return t;
}

double tensor_get(Tensor* t, int64_t r, int64_t c) {
    return t->data[r * t->cols + c];
}

void tensor_set(Tensor* t, int64_t r, int64_t c, double val) {
    t->data[r * t->cols + c] = val;
}

void tensor_drop(Tensor* t) {
    if (t->data) {
        free(t->data);
        t->data = NULL;
    }
    t->rows = 0;
    t->cols = 0;
}

