/* Set[T] implementation in C for Pyrite standard library */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define INITIAL_CAPACITY 16

typedef struct SetEntry {
    void* value;
    uint64_t hash;
    struct SetEntry* next;
} SetEntry;

typedef struct {
    SetEntry** buckets;
    int64_t len;
    int64_t cap;
    int64_t elem_size;
} Set;

/* Hash function (same as map) */
extern uint64_t hash_bytes(const void* data, size_t len);

/* Create new set */
Set set_new(int64_t elem_size) {
    Set set;
    set.buckets = calloc(INITIAL_CAPACITY, sizeof(SetEntry*));
    set.len = 0;
    set.cap = INITIAL_CAPACITY;
    set.elem_size = elem_size;
    return set;
}

/* Insert element */
void set_insert(Set* set, void* elem) {
    uint64_t hash = hash_bytes(elem, set->elem_size);
    int64_t index = hash % set->cap;
    
    /* Check if already exists */
    SetEntry* entry = set->buckets[index];
    while (entry) {
        if (entry->hash == hash && memcmp(entry->value, elem, set->elem_size) == 0) {
            return;  /* Already in set */
        }
        entry = entry->next;
    }
    
    /* Insert new */
    SetEntry* new_entry = malloc(sizeof(SetEntry));
    new_entry->value = malloc(set->elem_size);
    memcpy(new_entry->value, elem, set->elem_size);
    new_entry->hash = hash;
    new_entry->next = set->buckets[index];
    set->buckets[index] = new_entry;
    set->len++;
}

/* Check if set contains element */
int set_contains(Set* set, void* elem) {
    uint64_t hash = hash_bytes(elem, set->elem_size);
    int64_t index = hash % set->cap;
    
    SetEntry* entry = set->buckets[index];
    while (entry) {
        if (entry->hash == hash && memcmp(entry->value, elem, set->elem_size) == 0) {
            return 1;  /* Found */
        }
        entry = entry->next;
    }
    
    return 0;  /* Not found */
}

/* Get set length */
int64_t set_length(Set* set) {
    return set->len;
}

/* Free set memory */
void set_drop(Set* set) {
    for (int64_t i = 0; i < set->cap; i++) {
        SetEntry* entry = set->buckets[i];
        while (entry) {
            SetEntry* next = entry->next;
            free(entry->value);
            free(entry);
            entry = next;
        }
    }
    free(set->buckets);
    set->buckets = NULL;
    set->len = 0;
    set->cap = 0;
}

