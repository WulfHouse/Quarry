/* Path utilities - C implementation
 *
 * This provides cross-platform path manipulation utilities, called from Pyrite via FFI.
 * The logic matches Python pathlib behavior for compatibility.
 */

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <limits.h>

#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#define PATH_SEP '\\'
#define PATH_SEP_STR "\\"
#define IS_PATH_SEP(c) ((c) == '\\' || (c) == '/')
#else
#include <unistd.h>
#include <sys/stat.h>
#define PATH_SEP '/'
#define PATH_SEP_STR "/"
#define IS_PATH_SEP(c) ((c) == '/')
#endif

#define MAX_PATH_LEN 4096
#define MAX_JSON_LEN 8192

/* Helper: Check if character is path separator (cross-platform) */
static bool is_sep(char c) {
    return IS_PATH_SEP(c);
}

/* Helper: Skip trailing separators */
static const char* skip_trailing_seps(const char* s) {
    const char* end = s + strlen(s) - 1;
    while (end > s && is_sep(*end)) {
        end--;
    }
    return end + 1;
}

/* Check if path is absolute */
int32_t is_absolute_c(const uint8_t* path, int64_t path_len, int32_t* result) {
    if (!path || !result || path_len <= 0) {
        return -1;
    }
    
    char* path_str = (char*)malloc(path_len + 1);
    if (!path_str) {
        return -1;
    }
    memcpy(path_str, path, path_len);
    path_str[path_len] = '\0';
    
#ifdef _WIN32
    // Windows: absolute if starts with drive letter (C:) or UNC (\\)
    if (path_len >= 2) {
        // Drive letter: C: or c:
        if (((path_str[0] >= 'A' && path_str[0] <= 'Z') || 
             (path_str[0] >= 'a' && path_str[0] <= 'z')) && 
            path_str[1] == ':') {
            *result = 1;
            free(path_str);
            return 0;
        }
        // UNC: \\server\share
        if (path_str[0] == '\\' && path_str[1] == '\\') {
            *result = 1;
            free(path_str);
            return 0;
        }
    }
#else
    // POSIX: absolute if starts with /
    if (path_len > 0 && path_str[0] == '/') {
        *result = 1;
        free(path_str);
        return 0;
    }
#endif
    
    *result = 0;
    free(path_str);
    return 0;
}

/* Normalize path (resolve . and .., normalize separators) */
static void normalize_path(char* path) {
    if (!path || strlen(path) == 0) {
        return;
    }
    
    int len = strlen(path);
    char* result = (char*)malloc(len + 1);
    if (!result) {
        return;
    }
    
    int result_pos = 0;
    bool is_abs = false;
    
#ifdef _WIN32
    // Check for absolute path (drive or UNC)
    if (len >= 2 && ((path[0] >= 'A' && path[0] <= 'Z') || (path[0] >= 'a' && path[0] <= 'z')) && path[1] == ':') {
        result[result_pos++] = path[0];
        result[result_pos++] = ':';
        is_abs = true;
        if (len > 2 && is_sep(path[2])) {
            result[result_pos++] = PATH_SEP;
        }
    } else if (len >= 2 && path[0] == '\\' && path[1] == '\\') {
        result[result_pos++] = '\\';
        result[result_pos++] = '\\';
        is_abs = true;
    }
#else
    if (len > 0 && path[0] == '/') {
        result[result_pos++] = '/';
        is_abs = true;
    }
#endif
    
    // Parse components
    const char* start = path + (is_abs ? (len >= 2 && path[1] == ':' ? 2 : (path[0] == '/' ? 1 : 0)) : 0);
    if (is_abs && len >= 2 && path[1] == ':') {
        start = path + 2;
    } else if (is_abs && path[0] == '/') {
        start = path + 1;
    }
    
    char components[256][256];
    int comp_count = 0;
    const char* comp_start = start;
    
    for (int i = 0; i <= len; i++) {
        char c = (i < len) ? path[i] : '\0';
        if (is_sep(c) || c == '\0') {
            int comp_len = &path[i] - comp_start;
            if (comp_len > 0) {
                if (comp_len == 1 && comp_start[0] == '.') {
                    // Skip .
                } else if (comp_len == 2 && comp_start[0] == '.' && comp_start[1] == '.') {
                    // Go up one level
                    if (comp_count > 0) {
                        comp_count--;
                    }
                } else {
                    // Add component
                    if (comp_len < 256) {
                        memcpy(components[comp_count], comp_start, comp_len);
                        components[comp_count][comp_len] = '\0';
                        comp_count++;
                    }
                }
            }
            comp_start = &path[i + 1];
        }
    }
    
    // Rebuild path
    result_pos = 0;
    if (is_abs) {
#ifdef _WIN32
        if (len >= 2 && path[1] == ':') {
            result[result_pos++] = path[0];
            result[result_pos++] = ':';
            result[result_pos++] = PATH_SEP;
        } else if (len >= 2 && path[0] == '\\' && path[1] == '\\') {
            result[result_pos++] = '\\';
            result[result_pos++] = '\\';
        } else {
            result[result_pos++] = PATH_SEP;
        }
#else
        result[result_pos++] = '/';
#endif
    }
    
    for (int i = 0; i < comp_count; i++) {
        if (i > 0) {
            result[result_pos++] = PATH_SEP;
        }
        int comp_len = strlen(components[i]);
        memcpy(&result[result_pos], components[i], comp_len);
        result_pos += comp_len;
    }
    result[result_pos] = '\0';
    
    memcpy(path, result, result_pos + 1);
    free(result);
}

/* Resolve path to absolute */
int32_t resolve_path_c(const uint8_t* path, int64_t path_len,
                       const uint8_t* base, int64_t base_len,
                       uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!path || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    char* path_str = (char*)malloc(path_len + 1);
    if (!path_str) {
        return -1;
    }
    memcpy(path_str, path, path_len);
    path_str[path_len] = '\0';
    
    char* base_str = NULL;
    if (base && base_len > 0) {
        base_str = (char*)malloc(base_len + 1);
        if (!base_str) {
            free(path_str);
            return -1;
        }
        memcpy(base_str, base, base_len);
        base_str[base_len] = '\0';
    }
    
    char resolved[MAX_PATH_LEN];
    
    // Check if path is absolute
    int32_t is_abs = 0;
    is_absolute_c(path, path_len, &is_abs);
    
    if (is_abs) {
        // Path is absolute, just normalize it
        strncpy(resolved, path_str, MAX_PATH_LEN - 1);
        resolved[MAX_PATH_LEN - 1] = '\0';
        normalize_path(resolved);
    } else {
        // Path is relative, resolve against base or CWD
        if (base_str) {
            // Resolve against base
            strncpy(resolved, base_str, MAX_PATH_LEN - 1);
            resolved[MAX_PATH_LEN - 1] = '\0';
            normalize_path(resolved);
            
            // Append path
            int resolved_len = strlen(resolved);
            if (resolved_len > 0 && !is_sep(resolved[resolved_len - 1])) {
                resolved[resolved_len++] = PATH_SEP;
            }
            strncat(resolved, path_str, MAX_PATH_LEN - resolved_len - 1);
        } else {
            // Resolve against current working directory
#ifdef _WIN32
            if (_getcwd(resolved, MAX_PATH_LEN) == NULL) {
                free(path_str);
                if (base_str) free(base_str);
                return -1;
            }
#else
            if (getcwd(resolved, MAX_PATH_LEN) == NULL) {
                free(path_str);
                if (base_str) free(base_str);
                return -1;
            }
#endif
            int resolved_len = strlen(resolved);
            if (resolved_len > 0 && !is_sep(resolved[resolved_len - 1])) {
                resolved[resolved_len++] = PATH_SEP;
            }
            strncat(resolved, path_str, MAX_PATH_LEN - resolved_len - 1);
        }
        normalize_path(resolved);
    }
    
    // Copy to result
    int resolved_len = strlen(resolved);
    if (resolved_len >= result_cap) {
        free(path_str);
        if (base_str) free(base_str);
        return -1;
    }
    memcpy(result, resolved, resolved_len);
    result[resolved_len] = '\0';
    *result_len = resolved_len;
    
    free(path_str);
    if (base_str) free(base_str);
    return 0;
}

/* Join path components */
int32_t join_paths_c(const uint8_t* parts_json, int64_t json_len,
                     uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!parts_json || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    // Simple JSON array parsing for path strings
    char* json_str = (char*)malloc(json_len + 1);
    if (!json_str) {
        return -1;
    }
    memcpy(json_str, parts_json, json_len);
    json_str[json_len] = '\0';
    
    char parts[64][MAX_PATH_LEN];
    int part_count = 0;
    const char* pos = json_str;
    
    // Skip opening bracket
    while (*pos && (*pos == '[' || *pos == ' ' || *pos == '\t' || *pos == '\n')) pos++;
    
    // Parse quoted strings
    while (*pos && *pos != ']' && part_count < 64) {
        while (*pos && (*pos == ' ' || *pos == '\t' || *pos == ',' || *pos == '\n')) pos++;
        if (*pos == ']') break;
        
        if (*pos == '"') {
            pos++; // Skip opening quote
            const char* str_start = pos;
            while (*pos && *pos != '"') pos++;
            if (*pos == '"') {
                int str_len = pos - str_start;
                if (str_len < MAX_PATH_LEN) {
                    memcpy(parts[part_count], str_start, str_len);
                    parts[part_count][str_len] = '\0';
                    part_count++;
                }
                pos++; // Skip closing quote
            }
        } else {
            pos++;
        }
    }
    
    if (part_count == 0) {
        result[0] = '\0';
        *result_len = 0;
        free(json_str);
        return 0;
    }
    
    // Join parts
    char joined[MAX_PATH_LEN] = {0};
    strncpy(joined, parts[0], MAX_PATH_LEN - 1);
    
    for (int i = 1; i < part_count; i++) {
        // Check if part is absolute (overrides previous)
        int32_t is_abs = 0;
        is_absolute_c((uint8_t*)parts[i], strlen(parts[i]), &is_abs);
        
        if (is_abs) {
            strncpy(joined, parts[i], MAX_PATH_LEN - 1);
        } else {
            int joined_len = strlen(joined);
            if (joined_len > 0 && !is_sep(joined[joined_len - 1])) {
                joined[joined_len++] = PATH_SEP;
            }
            strncat(joined, parts[i], MAX_PATH_LEN - joined_len - 1);
        }
    }
    
    // Copy to result
    int joined_len = strlen(joined);
    if (joined_len >= result_cap) {
        free(json_str);
        return -1;
    }
    memcpy(result, joined, joined_len);
    result[joined_len] = '\0';
    *result_len = joined_len;
    
    free(json_str);
    return 0;
}

/* Get relative path from base to path */
int32_t relative_path_c(const uint8_t* path, int64_t path_len,
                        const uint8_t* base, int64_t base_len,
                        uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!path || !base || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    // Resolve both paths to absolute
    char path_abs[MAX_PATH_LEN];
    char base_abs[MAX_PATH_LEN];
    int64_t path_abs_len = 0;
    int64_t base_abs_len = 0;
    
    if (resolve_path_c(path, path_len, NULL, 0, (uint8_t*)path_abs, MAX_PATH_LEN, &path_abs_len) != 0) {
        return -1;
    }
    if (resolve_path_c(base, base_len, NULL, 0, (uint8_t*)base_abs, MAX_PATH_LEN, &base_abs_len) != 0) {
        return -1;
    }
    
    // Normalize paths (lowercase on Windows for comparison)
#ifdef _WIN32
    for (int i = 0; i < path_abs_len; i++) {
        if (path_abs[i] >= 'A' && path_abs[i] <= 'Z') {
            path_abs[i] = path_abs[i] - 'A' + 'a';
        }
    }
    for (int i = 0; i < base_abs_len; i++) {
        if (base_abs[i] >= 'A' && base_abs[i] <= 'Z') {
            base_abs[i] = base_abs[i] - 'A' + 'a';
        }
    }
#endif
    
    // Check if paths are on same root (Windows: same drive, POSIX: always same)
#ifdef _WIN32
    if (path_abs_len >= 2 && base_abs_len >= 2) {
        if (path_abs[0] != base_abs[0] || path_abs[1] != ':' || base_abs[1] != ':') {
            // Different drives or not drive paths
            if (path_abs[0] != '\\' || base_abs[0] != '\\') {
                // Return null (no relative path)
                memcpy(result, "null", 4);
                *result_len = 4;
                return 0;
            }
        }
    }
#endif
    
    // Find common prefix
    int common_len = 0;
    int min_len = (path_abs_len < base_abs_len) ? path_abs_len : base_abs_len;
    
    for (int i = 0; i < min_len; i++) {
        if (path_abs[i] == base_abs[i]) {
            if (is_sep(path_abs[i])) {
                common_len = i + 1;
            }
        } else {
            break;
        }
    }
    
    // Build relative path
    char relative[MAX_PATH_LEN] = {0};
    int rel_pos = 0;
    
    // Count .. needed for base
    const char* base_remainder = base_abs + common_len;
    int dotdot_count = 0;
    const char* p = base_remainder;
    while (*p) {
        if (is_sep(*p)) {
            dotdot_count++;
        }
        p++;
    }
    if (strlen(base_remainder) > 0 && !is_sep(base_remainder[strlen(base_remainder) - 1])) {
        dotdot_count++;
    }
    
    // Add .. components
    for (int i = 0; i < dotdot_count && rel_pos < MAX_PATH_LEN - 4; i++) {
        if (i > 0) {
            relative[rel_pos++] = PATH_SEP;
        }
        relative[rel_pos++] = '.';
        relative[rel_pos++] = '.';
    }
    
    // Add path remainder
    const char* path_remainder = path_abs + common_len;
    if (strlen(path_remainder) > 0) {
        if (rel_pos > 0 && !is_sep(relative[rel_pos - 1])) {
            relative[rel_pos++] = PATH_SEP;
        }
        int remainder_len = strlen(path_remainder);
        if (rel_pos + remainder_len < MAX_PATH_LEN) {
            memcpy(&relative[rel_pos], path_remainder, remainder_len);
            rel_pos += remainder_len;
        }
    }
    
    if (rel_pos == 0) {
        relative[rel_pos++] = '.';
    }
    relative[rel_pos] = '\0';
    
    // Copy to result
    if (rel_pos >= result_cap) {
        return -1;
    }
    memcpy(result, relative, rel_pos);
    result[rel_pos] = '\0';
    *result_len = rel_pos;
    
    return 0;
}
