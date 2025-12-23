/* JSON implementation in C for Pyrite */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

typedef struct {
    char* data;
    int64_t len;
} String;

extern String string_new(const char* cstr);
extern String string_empty();

/* Forward declarations */
String json_serialize_str(const char* value);

/* Helper function to escape a String for JSON (for Pyrite FFI) */
String json_escape_string(String* s) {
    if (s == NULL || s->data == NULL) {
        return string_new("\"\"");
    }
    return json_serialize_str(s->data);
}

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
    /* Check for special floating-point values (NaN, infinity) */
    /* RFC 8259 does not allow "nan" or "inf" in JSON, so return "null" */
    if (isnan(value) || isinf(value)) {
        return string_new("null");
    }
    
    /* Format finite value with compact precision (%.17g provides sufficient precision) */
    char buf[64];
    snprintf(buf, sizeof(buf), "%.17g", value);
    return string_new(buf);
}

String json_serialize_str(const char* value) {
    int64_t len = strlen(value);
    /* Calculate worst-case size: each char could become 6 chars (\uXXXX) + quotes */
    int64_t max_size = len * 6 + 3;
    char* result = malloc(max_size);
    if (result == NULL) {
        String s;
        s.data = NULL;
        s.len = 0;
        return s;
    }
    
    int64_t pos = 0;
    result[pos++] = '"';
    
    for (int64_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)value[i];
        
        /* Escape special characters */
        if (c == '"') {
            result[pos++] = '\\';
            result[pos++] = '"';
        } else if (c == '\\') {
            result[pos++] = '\\';
            result[pos++] = '\\';
        } else if (c == '\b') {
            result[pos++] = '\\';
            result[pos++] = 'b';
        } else if (c == '\f') {
            result[pos++] = '\\';
            result[pos++] = 'f';
        } else if (c == '\n') {
            result[pos++] = '\\';
            result[pos++] = 'n';
        } else if (c == '\r') {
            result[pos++] = '\\';
            result[pos++] = 'r';
        } else if (c == '\t') {
            result[pos++] = '\\';
            result[pos++] = 't';
        } else if (c < 0x20) {
            /* Control characters: escape as \uXXXX */
            result[pos++] = '\\';
            result[pos++] = 'u';
            result[pos++] = '0';
            result[pos++] = '0';
            sprintf(result + pos, "%02X", c);
            pos += 2;
        } else {
            /* Regular character */
            result[pos++] = c;
        }
    }
    
    result[pos++] = '"';
    result[pos] = '\0';
    
    /* Reallocate to actual size */
    char* final = realloc(result, pos + 1);
    if (final != NULL) {
        result = final;
    }
    
    String s;
    s.data = result;
    s.len = pos;
    return s;
}

