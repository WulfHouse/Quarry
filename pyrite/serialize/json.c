/* JSON implementation in C for Pyrite */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct {
    char* data;
    int64_t len;
} String;

extern String string_new(const char* cstr);
extern String string_empty();

/* Simple JSON serialization for primitive types */
String json_serialize_bool(int8_t value) {
    return string_new(value ? "true" : "false");
}

String json_serialize_i64(int64_t value) {
    char buf[32];
    sprintf(buf, "%lld", value);
    return string_new(buf);
}

String json_serialize_f64(double value) {
    char buf[64];
    sprintf(buf, "%f", value);
    return string_new(buf);
}

String json_serialize_str(const char* value) {
    int64_t len = strlen(value);
    char* result = malloc(len + 3);
    if (result == NULL) {
        String s;
        s.data = NULL;
        s.len = 0;
        return s;
    }
    result[0] = '"';
    memcpy(result + 1, value, len);
    result[len + 1] = '"';
    result[len + 2] = '\0';
    String s;
    s.data = result;
    s.len = len + 2;
    return s;
}

