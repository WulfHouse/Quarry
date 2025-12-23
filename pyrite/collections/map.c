/* Map[K, V] implementation in C for Pyrite standard library */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define INITIAL_CAPACITY 16
#define LOAD_FACTOR 0.75

/* Hash map entry */
typedef struct MapEntry {
    void* key;
    void* value;
    uint64_t hash;
    struct MapEntry* next;  /* For collision chaining */
} MapEntry;

/* Map structure */
typedef struct {
    MapEntry** buckets;
    int64_t len;
    int64_t cap;
    int64_t key_size;
    int64_t value_size;
} Map;

/* Simple hash function (FNV-1a) */
uint64_t hash_bytes(const void* data, size_t len) {
    uint64_t hash = 14695981039346656037ULL;
    const uint8_t* bytes = (const uint8_t*)data;
    
    for (size_t i = 0; i < len; i++) {
        hash ^= bytes[i];
        hash *= 1099511628211ULL;
    }
    
    return hash;
}

/* Create new map */
Map map_new(int64_t key_size, int64_t value_size) {
    Map map;
    map.buckets = calloc(INITIAL_CAPACITY, sizeof(MapEntry*));
    map.len = 0;
    map.cap = INITIAL_CAPACITY;
    map.key_size = key_size;
    map.value_size = value_size;
    return map;
}

/* Insert key-value pair */
void map_insert(Map* map, void* key, void* value) {
    uint64_t hash = hash_bytes(key, map->key_size);
    int64_t index = hash % map->cap;
    
    /* Check if key exists */
    MapEntry* entry = map->buckets[index];
    while (entry) {
        if (entry->hash == hash && memcmp(entry->key, key, map->key_size) == 0) {
            /* Update existing */
            memcpy(entry->value, value, map->value_size);
            return;
        }
        entry = entry->next;
    }
    
    /* Insert new entry */
    MapEntry* new_entry = malloc(sizeof(MapEntry));
    new_entry->key = malloc(map->key_size);
    new_entry->value = malloc(map->value_size);
    memcpy(new_entry->key, key, map->key_size);
    memcpy(new_entry->value, value, map->value_size);
    new_entry->hash = hash;
    new_entry->next = map->buckets[index];
    map->buckets[index] = new_entry;
    map->len++;
}

/* Get value for key */
void* map_get(Map* map, void* key) {
    uint64_t hash = hash_bytes(key, map->key_size);
    int64_t index = hash % map->cap;
    
    MapEntry* entry = map->buckets[index];
    while (entry) {
        if (entry->hash == hash && memcmp(entry->key, key, map->key_size) == 0) {
            return entry->value;
        }
        entry = entry->next;
    }
    
    return NULL;  /* Not found */
}

/* Check if map contains key */
int map_contains(Map* map, void* key) {
    return map_get(map, key) != NULL;
}

/* Get map length */
int64_t map_length(Map* map) {
    return map->len;
}

/* Free map memory */
void map_drop(Map* map) {
    for (int64_t i = 0; i < map->cap; i++) {
        MapEntry* entry = map->buckets[i];
        while (entry) {
            MapEntry* next = entry->next;
            free(entry->key);
            free(entry->value);
            free(entry);
            entry = next;
        }
    }
    free(map->buckets);
    map->buckets = NULL;
    map->len = 0;
    map->cap = 0;
}

/* Pyrite wrappers */
Map Map_new(int64_t key, int64_t val) { return map_new(key, val); }
void Map_insert(Map* m, void* k, void* v) { map_insert(m, k, v); }
void* Map_get(Map* map, void* key) { return map_get(map, key); }
int Map_contains(Map* m, void* k) { return map_contains(m, k); }
int64_t Map_length(Map* m) { return map_length(m); }
void Map_drop(Map* m) { map_drop(m); }
