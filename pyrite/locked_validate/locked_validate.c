/* Locked validation operations - C implementation
 *
 * This provides validation of lockfile consistency, called from Pyrite via FFI.
 * The logic matches the Python implementation in quarry/main.py cmd_build().
 * 
 * Note: Version constraint checking is done in Python bridge (calls version_bridge).
 * This C implementation handles structural checks only (missing, type mismatch).
 */

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#define MAX_STRING_LEN 1024
#define MAX_JSON_LEN 65536
#define MAX_DEPS 256
#define MAX_ERRORS 64
#define MAX_ERROR_LEN 256

/* Dependency entry structure */
typedef struct {
    char name[MAX_STRING_LEN];
    char type[MAX_STRING_LEN];
    char version[MAX_STRING_LEN];
    char git_url[MAX_STRING_LEN];
    char git_branch[MAX_STRING_LEN];
    char commit[MAX_STRING_LEN];
    char path[MAX_STRING_LEN];
    char checksum[MAX_STRING_LEN];
    char hash[MAX_STRING_LEN];
} DepEntry;

/* Helper: Skip whitespace */
static const char* skip_whitespace(const char* s) {
    while (*s && (*s == ' ' || *s == '\t' || *s == '\n' || *s == '\r')) {
        s++;
    }
    return s;
}

/* Helper: Find end of JSON string (handles escaped quotes) */
static const char* find_string_end(const char* s) {
    if (*s != '"') return s;
    s++; // Skip opening quote
    while (*s) {
        if (*s == '\\' && *(s + 1) == '"') {
            s += 2; // Skip escaped quote
        } else if (*s == '"') {
            return s; // Found closing quote
        } else {
            s++;
        }
    }
    return s; // No closing quote found
}

/* Parse JSON string value */
static int parse_json_string(const char* json, char* result, int max_len) {
    const char* pos = skip_whitespace(json);
    if (*pos != '"') return -1;
    
    pos++; // Skip opening quote
    const char* start = pos;
    const char* end = find_string_end(start - 1);
    if (*end != '"') return -1;
    
    int len = end - start;
    if (len >= max_len) return -1;
    
    // Copy string, handling escapes
    int result_pos = 0;
    while (start < end) {
        if (*start == '\\' && start + 1 < end) {
            start++; // Skip backslash
            if (*start == 'n') {
                result[result_pos++] = '\n';
            } else if (*start == 't') {
                result[result_pos++] = '\t';
            } else if (*start == 'r') {
                result[result_pos++] = '\r';
            } else if (*start == '\\') {
                result[result_pos++] = '\\';
            } else if (*start == '"') {
                result[result_pos++] = '"';
            } else {
                result[result_pos++] = *start;
            }
            start++;
        } else {
            result[result_pos++] = *start++;
        }
    }
    result[result_pos] = '\0';
    return result_pos;
}

/* Get JSON object field value as string */
static int get_json_field_string(const char* json, const char* field_name, char* result, int max_len) {
    const char* pos = json;
    int field_len = strlen(field_name);
    
    // Find field name
    while (*pos) {
        pos = skip_whitespace(pos);
        if (*pos == '}') break;
        
        // Check if this is our field
        if (*pos == '"' && strncmp(pos + 1, field_name, field_len) == 0 && pos[field_len + 1] == '"') {
            pos += field_len + 2; // Skip "field_name"
            pos = skip_whitespace(pos);
            if (*pos != ':') continue;
            pos++; // Skip colon
            pos = skip_whitespace(pos);
            
            // Parse string value
            if (*pos == '"') {
                return parse_json_string(pos, result, max_len);
            }
        }
        
        // Skip to next field
        while (*pos && *pos != ',' && *pos != '}') {
            if (*pos == '"') {
                pos = find_string_end(pos) + 1;
            } else {
                pos++;
            }
        }
        if (*pos == ',') pos++;
    }
    
    return -1; // Field not found
}

/* Parse dependencies from JSON */
static int parse_deps_json(const char* json_str, DepEntry* deps, int max_deps) {
    const char* pos = json_str;
    int dep_count = 0;
    
    // Skip opening brace
    while (*pos && (*pos == '{' || *pos == ' ' || *pos == '\t' || *pos == '\n')) pos++;
    
    // Parse dependency entries
    while (*pos && *pos != '}' && dep_count < max_deps) {
        // Skip whitespace and commas
        while (*pos && (*pos == ' ' || *pos == '\t' || *pos == ',' || *pos == '\n')) pos++;
        if (*pos == '}') break;
        
        // Parse dependency name (key)
        if (*pos != '"') break;
        pos++; // Skip opening quote
        const char* name_start = pos;
        while (*pos && *pos != '"') pos++;
        if (*pos != '"') break;
        int name_len = pos - name_start;
        if (name_len >= MAX_STRING_LEN) break;
        memcpy(deps[dep_count].name, name_start, name_len);
        deps[dep_count].name[name_len] = '\0';
        pos++; // Skip closing quote
        
        // Skip colon
        while (*pos && (*pos == ':' || *pos == ' ' || *pos == '\t')) pos++;
        
        // Parse dependency value (object)
        if (*pos != '{') break;
        pos++; // Skip opening brace
        
        // Parse fields
        get_json_field_string(pos, "type", deps[dep_count].type, MAX_STRING_LEN);
        get_json_field_string(pos, "version", deps[dep_count].version, MAX_STRING_LEN);
        get_json_field_string(pos, "git_url", deps[dep_count].git_url, MAX_STRING_LEN);
        get_json_field_string(pos, "git_branch", deps[dep_count].git_branch, MAX_STRING_LEN);
        get_json_field_string(pos, "commit", deps[dep_count].commit, MAX_STRING_LEN);
        get_json_field_string(pos, "path", deps[dep_count].path, MAX_STRING_LEN);
        get_json_field_string(pos, "checksum", deps[dep_count].checksum, MAX_STRING_LEN);
        get_json_field_string(pos, "hash", deps[dep_count].hash, MAX_STRING_LEN);
        
        // Skip to closing brace
        while (*pos && *pos != '}') pos++;
        if (*pos == '}') pos++;
        
        dep_count++;
    }
    
    return dep_count;
}

/* Find dependency by name */
static DepEntry* find_dep(DepEntry* deps, int count, const char* name) {
    for (int i = 0; i < count; i++) {
        if (strcmp(deps[i].name, name) == 0) {
            return &deps[i];
        }
    }
    return NULL;
}

/* Validate locked dependencies */
int32_t validate_locked_deps_c(const uint8_t* toml_deps_json, int64_t toml_json_len,
                                 const uint8_t* lockfile_deps_json, int64_t lockfile_json_len,
                                 uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!toml_deps_json || !lockfile_deps_json || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    // Convert to null-terminated strings
    char* toml_str = (char*)malloc(toml_json_len + 1);
    char* lockfile_str = (char*)malloc(lockfile_json_len + 1);
    if (!toml_str || !lockfile_str) {
        if (toml_str) free(toml_str);
        if (lockfile_str) free(lockfile_str);
        return -1;
    }
    memcpy(toml_str, toml_deps_json, toml_json_len);
    toml_str[toml_json_len] = '\0';
    memcpy(lockfile_str, lockfile_deps_json, lockfile_json_len);
    lockfile_str[lockfile_json_len] = '\0';
    
    // Parse dependencies
    DepEntry toml_deps[MAX_DEPS];
    DepEntry lockfile_deps[MAX_DEPS];
    int toml_count = parse_deps_json(toml_str, toml_deps, MAX_DEPS);
    int lockfile_count = parse_deps_json(lockfile_str, lockfile_deps, MAX_DEPS);
    
    // Collect errors and warnings
    char errors[MAX_ERRORS][MAX_ERROR_LEN];
    char warnings[MAX_ERRORS][MAX_ERROR_LEN];
    int error_count = 0;
    int warning_count = 0;
    bool valid = true;
    
    // Check each TOML dependency
    for (int i = 0; i < toml_count; i++) {
        DepEntry* toml_dep = &toml_deps[i];
        DepEntry* lockfile_dep = find_dep(lockfile_deps, lockfile_count, toml_dep->name);
        
        if (!lockfile_dep) {
            // Missing dependency in lockfile
            if (error_count < MAX_ERRORS) {
                snprintf(errors[error_count], MAX_ERROR_LEN,
                    "Quarry.lock is outdated. Dependency '%s' in Quarry.toml not found in lockfile.", toml_dep->name);
                error_count++;
                valid = false;
            }
            continue;
        }
        
        // Check source type match
        if (strcmp(toml_dep->type, lockfile_dep->type) != 0) {
            // Type mismatch
            if (error_count < MAX_ERRORS) {
                snprintf(errors[error_count], MAX_ERROR_LEN,
                    "Quarry.lock is outdated. Source type mismatch for '%s'.", toml_dep->name);
                error_count++;
                valid = false;
            }
            continue;
        }
        
        // For registry dependencies, version constraint checking is done in Python bridge
        // For git/path dependencies, structural checks are sufficient
        // (URL/path matching is done in Python bridge if needed)
    }
    
    // Check for extra dependencies in lockfile (warnings)
    for (int i = 0; i < lockfile_count; i++) {
        DepEntry* lockfile_dep = &lockfile_deps[i];
        DepEntry* toml_dep = find_dep(toml_deps, toml_count, lockfile_dep->name);
        
        if (!toml_dep) {
            // Extra dependency in lockfile
            if (warning_count < MAX_ERRORS) {
                snprintf(warnings[warning_count], MAX_ERROR_LEN,
                    "Quarry.lock contains '%s' which is not in Quarry.toml", lockfile_dep->name);
                warning_count++;
            }
        }
    }
    
    // Build JSON result
    int json_pos = 0;
    if (json_pos + 2 < result_cap) {
        result[json_pos++] = '{';
    }
    
    // Write "valid" field
    int needed = snprintf((char*)result + json_pos, result_cap - json_pos,
        "\"valid\":%s", valid ? "true" : "false");
    if (needed > 0 && json_pos + needed < result_cap) {
        json_pos += needed;
    }
    
    // Write "errors" array
    if (json_pos + 20 < result_cap) {
        result[json_pos++] = ',';
        result[json_pos++] = '"';
        result[json_pos++] = 'e';
        result[json_pos++] = 'r';
        result[json_pos++] = 'r';
        result[json_pos++] = 'o';
        result[json_pos++] = 'r';
        result[json_pos++] = 's';
        result[json_pos++] = '"';
        result[json_pos++] = ':';
        result[json_pos++] = '[';
    }
    
    for (int i = 0; i < error_count && json_pos < result_cap - 100; i++) {
        if (i > 0 && json_pos < result_cap - 1) {
            result[json_pos++] = ',';
        }
        needed = snprintf((char*)result + json_pos, result_cap - json_pos,
            "\"%s\"", errors[i]);
        if (needed > 0 && json_pos + needed < result_cap) {
            json_pos += needed;
        }
    }
    
    if (json_pos + 2 < result_cap) {
        result[json_pos++] = ']';
    }
    
    // Write "warnings" array
    if (json_pos + 20 < result_cap) {
        result[json_pos++] = ',';
        result[json_pos++] = '"';
        result[json_pos++] = 'w';
        result[json_pos++] = 'a';
        result[json_pos++] = 'r';
        result[json_pos++] = 'n';
        result[json_pos++] = 'i';
        result[json_pos++] = 'n';
        result[json_pos++] = 'g';
        result[json_pos++] = 's';
        result[json_pos++] = '"';
        result[json_pos++] = ':';
        result[json_pos++] = '[';
    }
    
    for (int i = 0; i < warning_count && json_pos < result_cap - 100; i++) {
        if (i > 0 && json_pos < result_cap - 1) {
            result[json_pos++] = ',';
        }
        needed = snprintf((char*)result + json_pos, result_cap - json_pos,
            "\"%s\"", warnings[i]);
        if (needed > 0 && json_pos + needed < result_cap) {
            json_pos += needed;
        }
    }
    
    if (json_pos + 2 < result_cap) {
        result[json_pos++] = ']';
        result[json_pos++] = '}';
    }
    result[json_pos] = '\0';
    *result_len = json_pos;
    
    free(toml_str);
    free(lockfile_str);
    return 0;
}
