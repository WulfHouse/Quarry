/* List[T] implementation in C for Pyrite standard library */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* List structure: { data_ptr, length, capacity } */
typedef struct {
    void* data;
    int64_t len;
    int64_t cap;
} List;

/* Create new empty list */
List list_new(int64_t elem_size) {
    List list;
    list.data = NULL;
    list.len = 0;
    list.cap = 0;
    return list;
}

/* Create list with capacity */
List list_with_capacity(int64_t elem_size, int64_t capacity) {
    List list;
    list.data = malloc(elem_size * capacity);
    list.len = 0;
    list.cap = capacity;
    return list;
}

/* Push element to list */
void list_push(List* list, void* elem, int64_t elem_size) {
    if (list->len >= list->cap) {
        /* Grow capacity */
        int64_t new_cap = list->cap == 0 ? 4 : list->cap * 2;
        void* new_data = realloc(list->data, elem_size * new_cap);
        if (!new_data) {
            /* Allocation failed */
            return;
        }
        list->data = new_data;
        list->cap = new_cap;
    }
    
    /* Copy element */
    char* dest = ((char*)list->data) + (list->len * elem_size);
    memcpy(dest, elem, elem_size);
    list->len++;
}

/* Pop element from list */
int list_pop(List* list, void* out, int64_t elem_size) {
    if (list->len == 0) {
        return 0;  /* Empty */
    }
    
    list->len--;
    char* src = ((char*)list->data) + (list->len * elem_size);
    memcpy(out, src, elem_size);
    return 1;  /* Success */
}

/* Get element at index */
void* list_get(List* list, int64_t index, int64_t elem_size) {
    if (index < 0 || index >= list->len) {
        return NULL;  /* Out of bounds */
    }
    
    return ((char*)list->data) + (index * elem_size);
}

/* Get list length */
int64_t list_length(List* list) {
    return list->len;
}

/* Check if list is empty */
int list_is_empty(List* list) {
    return list->len == 0;
}

/* Free list memory */
void list_drop(List* list) {
    if (list->data) {
        free(list->data);
        list->data = NULL;
    }
    list->len = 0;
    list->cap = 0;
}

/* Clone list */
List list_clone(List* list, int64_t elem_size) {
    List new_list = list_with_capacity(elem_size, list->cap);
    if (list->data && new_list.data) {
        memcpy(new_list.data, list->data, elem_size * list->len);
        new_list.len = list->len;
    }
    return new_list;
}

