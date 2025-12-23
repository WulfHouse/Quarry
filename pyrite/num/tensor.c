/* Tensor implementation in C for Pyrite */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <limits.h>
#include <errno.h>

typedef struct {
    double* data;
    int64_t rows;
    int64_t cols;
} Tensor;

Tensor tensor_new(int64_t rows, int64_t cols) {
    Tensor t;
    
    /* Initialize to empty tensor (all paths must set these consistently) */
    t.data = NULL;
    t.rows = 0;
    t.cols = 0;
    
    /* Validate inputs: rows and cols must be non-negative */
    if (rows < 0 || cols < 0) {
        errno = EINVAL;
        return t;  /* Return empty tensor on negative input */
    }
    
    /* Convert to size_t for allocation math */
    size_t rows_sz = (size_t)rows;
    size_t cols_sz = (size_t)cols;
    size_t elem_size = sizeof(double);
    
    /* Check for zero-size allocation */
    if (rows_sz == 0 || cols_sz == 0) {
        return t;  /* Return empty tensor for zero-size */
    }
    
    /* Check for integer overflow: rows * cols * sizeof(double) <= SIZE_MAX */
    /* First check if cols * sizeof(double) would overflow */
    if (cols_sz > SIZE_MAX / elem_size) {
        errno = EINVAL;  /* Overflow detected in cols * elem_size */
        return t;  /* Return empty tensor on overflow */
    }
    /* Then check if rows * (cols * sizeof(double)) would overflow */
    if (rows_sz > SIZE_MAX / (cols_sz * elem_size)) {
        errno = EINVAL;  /* Overflow detected in total size */
        return t;  /* Return empty tensor on overflow */
    }
    
    /* Allocate and zero-initialize using calloc */
    t.data = (double*)calloc(rows_sz * cols_sz, elem_size);
    if (t.data == NULL) {
        errno = ENOMEM;  /* Allocation failed */
        return t;  /* Return empty tensor on allocation failure */
    }
    
    /* Success: set dimensions */
    t.rows = rows;
    t.cols = cols;
    return t;
}

/* Get element at position (r, c) from tensor.
 * 
 * Validation:
 * - Returns 0.0 and sets errno = EINVAL if t is NULL or t->data is NULL
 * - Returns 0.0 and sets errno = EINVAL if indices are out of bounds (r < 0 || r >= rows || c < 0 || c >= cols)
 * - Returns the element value on success (errno unchanged)
 * 
 * Callers can check errno to distinguish between valid zero values and error conditions.
 */
double tensor_get(Tensor* t, int64_t r, int64_t c) {
    /* Validate input: check for NULL pointers */
    if (t == NULL || t->data == NULL) {
        errno = EINVAL;
        return 0.0;
    }
    /* Validate bounds: ensure indices are within valid range */
    if (r < 0 || r >= t->rows || c < 0 || c >= t->cols) {
        errno = EINVAL;
        return 0.0;
    }
    /* Success: return element value (errno unchanged) */
    return t->data[r * t->cols + c];
}

void tensor_set(Tensor* t, int64_t r, int64_t c, double val) {
    /* Validate input */
    if (t == NULL || t->data == NULL) {
        return;  /* Early return on invalid tensor */
    }
    /* Validate bounds */
    if (r < 0 || r >= t->rows || c < 0 || c >= t->cols) {
        return;  /* Early return on out-of-bounds access */
    }
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

