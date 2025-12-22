/* String implementation in C for Pyrite standard library */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>

/* String structure: { data_ptr, length } */
typedef struct {
    char* data;
    int64_t len;
} String;

/* Create string from C string */
String string_new(const char* cstr) {
    String s;
    s.len = strlen(cstr);
    s.data = malloc(s.len + 1);
    memcpy(s.data, cstr, s.len + 1);
    return s;
}

/* Create empty string */
String string_empty() {
    String s;
    s.data = malloc(1);
    s.data[0] = '\0';
    s.len = 0;
    return s;
}

/* Get string length */
int string_length(String* s) {
    return (int)s->len;  /* Cast i64 to int for compatibility */
}

/* Clone string */
String string_clone(String* s) {
    String new_s;
    new_s.len = s->len;
    new_s.data = malloc(s->len + 1);
    memcpy(new_s.data, s->data, s->len + 1);
    return new_s;
}

/* Free string memory */
void string_drop(String* s) {
    if (s->data) {
        free(s->data);
        s->data = NULL;
    }
    s->len = 0;
}

/* StringBuilder for efficient concatenation */
typedef struct {
    char* data;
    int64_t len;
    int64_t cap;
} StringBuilder;

/* Create new string builder */
StringBuilder string_builder_new() {
    StringBuilder sb;
    sb.cap = 64;
    sb.data = malloc(sb.cap);
    sb.len = 0;
    sb.data[0] = '\0';
    return sb;
}

/* Append to string builder */
void string_builder_append(StringBuilder* sb, const char* str) {
    int64_t str_len = strlen(str);
    
    /* Grow if needed */
    while (sb->len + str_len >= sb->cap) {
        sb->cap *= 2;
        sb->data = realloc(sb->data, sb->cap);
    }
    
    /* Append */
    memcpy(sb->data + sb->len, str, str_len);
    sb->len += str_len;
    sb->data[sb->len] = '\0';
}

/* Append single character to string builder */
void string_builder_append_char(StringBuilder* sb, uint8_t ch) {
    /* Grow if needed */
    if (sb->len + 1 >= sb->cap) {
        sb->cap = sb->cap == 0 ? 64 : sb->cap * 2;
        sb->data = realloc(sb->data, sb->cap);
    }
    
    /* Append character */
    sb->data[sb->len] = (char)ch;
    sb->len++;
    sb->data[sb->len] = '\0';
}

/* Convert string builder to string */
String string_builder_to_string(StringBuilder* sb) {
    String s;
    s.len = sb->len;
    s.data = malloc(s.len + 1);
    memcpy(s.data, sb->data, s.len + 1);
    return s;
}

/* Free string builder */
void string_builder_drop(StringBuilder* sb) {
    if (sb->data) {
        free(sb->data);
        sb->data = NULL;
    }
    sb->len = 0;
    sb->cap = 0;
}

/* Format string with placeholders - basic implementation */
/* Format string: format("Hello {}, value: {}", "world", 42) */
/* For MVP, we'll implement a simple version that handles {} placeholders */
String string_format(const char* fmt, int argc, const char** argv) {
    StringBuilder sb = string_builder_new();
    const char* p = fmt;
    int arg_index = 0;
    
    while (*p) {
        if (*p == '{' && *(p + 1) == '}') {
            /* Placeholder found */
            if (arg_index < argc) {
                string_builder_append(&sb, argv[arg_index]);
                arg_index++;
                p += 2; /* Skip {} */
            } else {
                /* Not enough arguments - append literal {} */
                string_builder_append(&sb, "{}");
                p += 2;
            }
        } else if (*p == '{' && *(p + 1) == '{') {
            /* Escaped { */
            string_builder_append(&sb, "{");
            p += 2;
        } else if (*p == '}' && *(p + 1) == '}') {
            /* Escaped } */
            string_builder_append(&sb, "}");
            p += 2;
        } else {
            /* Regular character */
            char ch[2] = {*p, '\0'};
            string_builder_append(&sb, ch);
            p++;
        }
    }
    
    String result = string_builder_to_string(&sb);
    string_builder_drop(&sb);
    return result;
}

/* Convert integer to string */
String string_from_int(int64_t value) {
    char buffer[32];
    snprintf(buffer, sizeof(buffer), "%lld", (long long)value);
    return string_new(buffer);
}

/* Convert float to string */
String string_from_float(double value) {
    char buffer[64];
    snprintf(buffer, sizeof(buffer), "%g", value);
    return string_new(buffer);
}

/* Convert bool to string */
String string_from_bool(int8_t value) {
    return string_new(value ? "true" : "false");
}

/* List structure for string_split return type (matches list.c) */
typedef struct {
    void* data;
    int64_t len;
    int64_t cap;
} List;

/* Forward declarations for list functions (defined in list.c, linked at runtime) */
extern List list_new(int64_t elem_size);
extern void list_push(List* list, void* elem, int64_t elem_size);
extern int64_t list_length(List* list);

/* Helper: Create String from bytes */
static String string_create_from_bytes(const char* bytes, int64_t len) {
    String s;
    s.len = len;
    s.data = malloc(len + 1);
    if (s.data && len > 0) {
        memcpy(s.data, bytes, len);
    }
    if (s.data) {
        s.data[len] = '\0';
    }
    return s;
}

/* Split string by delimiter, returning List of Strings
 * 
 * Behavior:
 * - Empty string -> returns empty list
 * - Delimiter not found -> returns list with single element (original string)
 * - Empty delimiter -> returns list with single element (original string)
 * - Normal split -> returns list of segments
 */
/* Return type changed to void* (opaque pointer) for MVP
 * Full List support will be added in M32
 */
void* string_split(String* s, String* delimiter) {
    List result = list_new(sizeof(String));
    
    /* Handle empty string */
    if (s->len == 0) {
        List* heap_list = malloc(sizeof(List));
        *heap_list = result;
        return (void*)heap_list;
    }
    
    /* Extract delimiter C string */
    const char* delim_cstr = delimiter->data;
    
    /* Handle empty delimiter - return single-element list with original string */
    if (delim_cstr == NULL || delimiter->len == 0) {
        String copy = string_clone(s);
        list_push(&result, &copy, sizeof(String));
        List* heap_list = malloc(sizeof(List));
        *heap_list = result;
        return (void*)heap_list;
    }
    
    int64_t delim_len = delimiter->len;
    const char* start = s->data;
    const char* end = s->data + s->len;
    const char* current = start;
    
    /* Find all occurrences of delimiter */
    while (current < end) {
        const char* found = strstr(current, delim_cstr);
        
        if (found == NULL) {
            /* No more delimiters - add remaining string */
            int64_t remaining_len = end - current;
            if (remaining_len > 0) {
                String segment = string_create_from_bytes(current, remaining_len);
                list_push(&result, &segment, sizeof(String));
            }
            break;
        } else {
            /* Found delimiter - add segment before it */
            int64_t segment_len = found - current;
            if (segment_len > 0) {
                String segment = string_create_from_bytes(current, segment_len);
                list_push(&result, &segment, sizeof(String));
            }
            /* Move past delimiter */
            current = found + delim_len;
        }
    }
    
    /* If no segments found (delimiter not in string), return original string */
    if (list_length(&result) == 0) {
        String copy = string_clone(s);
        list_push(&result, &copy, sizeof(String));
    }
    
    /* Allocate List on heap and return pointer */
    List* heap_list = malloc(sizeof(List));
    *heap_list = result;
    return (void*)heap_list;
}

/* Trim leading and trailing whitespace from string
 * Whitespace: space, tab, newline, carriage return
 * Returns new String (immutable)
 */
String string_trim(String* s) {
    if (s->len == 0) {
        return string_empty();
    }
    
    const char* start = s->data;
    const char* end = s->data + s->len;
    const char* trimmed_start = start;
    const char* trimmed_end = end;
    
    /* Find first non-whitespace */
    while (trimmed_start < end) {
        char ch = *trimmed_start;
        if (ch != ' ' && ch != '\t' && ch != '\n' && ch != '\r') {
            break;
        }
        trimmed_start++;
    }
    
    /* Find last non-whitespace */
    while (trimmed_end > trimmed_start) {
        char ch = *(trimmed_end - 1);
        if (ch != ' ' && ch != '\t' && ch != '\n' && ch != '\r') {
            break;
        }
        trimmed_end--;
    }
    
    /* Create new string from trimmed portion */
    int64_t trimmed_len = trimmed_end - trimmed_start;
    if (trimmed_len <= 0) {
        return string_empty();
    }
    
    return string_create_from_bytes(trimmed_start, trimmed_len);
}

/* Check if string starts with prefix
 * Returns 1 if true, 0 if false
 * Empty prefix returns 1 (matches Python behavior)
 */
int string_starts_with(String s, String prefix) {
    /* Returns 1 if true, 0 if false */
    if (prefix.data == NULL || prefix.len == 0) {
        return 1;  /* Empty prefix matches */
    }
    
    int64_t prefix_len = prefix.len;
    if (s.len < prefix_len) {
        return 0;  /* String shorter than prefix */
    }
    
    /* Compare bytes */
    return memcmp(s.data, prefix.data, prefix_len) == 0;
}

/* Check if string contains substring
 * Returns 1 if found, 0 if not found
 * Empty substring returns 1 (matches Python behavior)
 */
int string_contains(String* s, String* substr) {
    /* Returns 1 if found, 0 if not found */
    if (substr->data == NULL || substr->len == 0) {
        return 1;  /* Empty substring matches */
    }
    
    /* Use strstr to find substring */
    /* Note: strstr expects null-terminated strings, which String has */
    return strstr(s->data, substr->data) != NULL;
}

/* Get substring from start to end (exclusive)
 * Bounds: start >= 0, end <= s.len, start <= end
 * Out of bounds: returns empty string (for MVP, can panic later)
 */
String string_substring(String* s, int64_t start, int64_t end) {
    /* Validate bounds */
    if (start < 0) {
        start = 0;
    }
    if (end > s->len) {
        end = s->len;
    }
    if (start > end) {
        return string_empty();  /* Invalid range */
    }
    if (start == end) {
        return string_empty();  /* Empty substring */
    }
    
    /* Create substring */
    int64_t len = end - start;
    return string_create_from_bytes(s->data + start, len);
}

