/* Dependency source parsing - C implementation
 *
 * This provides the core logic for parsing dependency sources from TOML values,
 * called from Pyrite via FFI. The logic matches the Python implementation
 * in quarry/dependency.py
 */

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#define MAX_STRING_LEN 1024
#define MAX_JSON_LEN 8192

/* Helper: Check if string starts with prefix */
static bool starts_with(const char* str, const char* prefix) {
    return strncmp(str, prefix, strlen(prefix)) == 0;
}

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

/* Get JSON object field value */
static int get_json_field(const char* json, const char* field_name, char* result, int max_len) {
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
            
            // Parse value
            if (*pos == '"') {
                return parse_json_string(pos, result, max_len);
            } else if (*pos == '{') {
                // Nested object - return empty for now (not needed for our use case)
                return 0;
            } else {
                // Other types - skip
                return 0;
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

/* Check if JSON is an object (starts with '{') */
static bool is_json_object(const char* json) {
    const char* pos = skip_whitespace(json);
    return *pos == '{';
}

/* Parse dependency source from JSON value */
int32_t parse_dependency_source_c(const uint8_t* name, int64_t name_len,
                                  const uint8_t* value_json, int64_t value_json_len,
                                  uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!name || !value_json || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    // Convert to null-terminated strings
    char* json_str = (char*)malloc(value_json_len + 1);
    if (!json_str) {
        return -1;
    }
    memcpy(json_str, value_json, value_json_len);
    json_str[value_json_len] = '\0';
    
    int json_pos = 0;
    
    // Check if value is a string or object
    if (is_json_object(json_str)) {
        // Parse as dict/object
        char git_url[MAX_STRING_LEN] = {0};
        char path_value[MAX_STRING_LEN] = {0};
        char version_value[MAX_STRING_LEN] = {0};
        char branch_value[MAX_STRING_LEN] = {0};
        char tag_value[MAX_STRING_LEN] = {0};
        char rev_value[MAX_STRING_LEN] = {0};
        char commit_value[MAX_STRING_LEN] = {0};
        char checksum_value[MAX_STRING_LEN] = {0};
        char hash_value[MAX_STRING_LEN] = {0};
        
        // Check for git dependency
        if (get_json_field(json_str, "git", git_url, MAX_STRING_LEN) >= 0) {
            // Git dependency
            get_json_field(json_str, "branch", branch_value, MAX_STRING_LEN);
            get_json_field(json_str, "tag", tag_value, MAX_STRING_LEN);
            get_json_field(json_str, "rev", rev_value, MAX_STRING_LEN);
            get_json_field(json_str, "commit", commit_value, MAX_STRING_LEN);
            
            // Priority: branch > tag > rev
            const char* git_branch = branch_value[0] ? branch_value : 
                                     (tag_value[0] ? tag_value : 
                                      (rev_value[0] ? rev_value : NULL));
            
            // Build JSON result
            if (json_pos + 50 < result_cap) {
                json_pos += snprintf((char*)result + json_pos, result_cap - json_pos,
                    "{\"type\":\"git\",\"git_url\":\"%s\"", git_url);
            }
            
            if (git_branch && json_pos + strlen(git_branch) + 30 < result_cap) {
                json_pos += snprintf((char*)result + json_pos, result_cap - json_pos,
                    ",\"git_branch\":\"%s\"", git_branch);
            }
            
            if (commit_value[0] && json_pos + strlen(commit_value) + 30 < result_cap) {
                json_pos += snprintf((char*)result + json_pos, result_cap - json_pos,
                    ",\"commit\":\"%s\"", commit_value);
            }
            
            if (json_pos + 2 < result_cap) {
                result[json_pos++] = '}';
                result[json_pos] = '\0';
            }
        }
        // Check for path dependency
        else if (get_json_field(json_str, "path", path_value, MAX_STRING_LEN) >= 0) {
            // Path dependency
            get_json_field(json_str, "hash", hash_value, MAX_STRING_LEN);
            
            // Build JSON result
            if (json_pos + 50 < result_cap) {
                json_pos += snprintf((char*)result + json_pos, result_cap - json_pos,
                    "{\"type\":\"path\",\"path\":\"%s\"", path_value);
            }
            
            if (hash_value[0] && json_pos + strlen(hash_value) + 30 < result_cap) {
                json_pos += snprintf((char*)result + json_pos, result_cap - json_pos,
                    ",\"hash\":\"%s\"", hash_value);
            }
            
            if (json_pos + 2 < result_cap) {
                result[json_pos++] = '}';
                result[json_pos] = '\0';
            }
        }
        // Check for registry dependency with version
        else if (get_json_field(json_str, "version", version_value, MAX_STRING_LEN) >= 0) {
            // Registry dependency with explicit version
            get_json_field(json_str, "checksum", checksum_value, MAX_STRING_LEN);
            
            // Build JSON result
            if (json_pos + 50 < result_cap) {
                json_pos += snprintf((char*)result + json_pos, result_cap - json_pos,
                    "{\"type\":\"registry\",\"version\":\"%s\"", version_value);
            }
            
            if (checksum_value[0] && json_pos + strlen(checksum_value) + 30 < result_cap) {
                json_pos += snprintf((char*)result + json_pos, result_cap - json_pos,
                    ",\"checksum\":\"%s\"", checksum_value);
            }
            
            if (json_pos + 2 < result_cap) {
                result[json_pos++] = '}';
                result[json_pos] = '\0';
            }
        } else {
            // Invalid dict - return null
            if (json_pos + 4 < result_cap) {
                memcpy(result, "null", 4);
                json_pos = 4;
                result[json_pos] = '\0';
            }
        }
    } else {
        // Parse as string (registry dependency)
        char version_str[MAX_STRING_LEN] = {0};
        int len = parse_json_string(json_str, version_str, MAX_STRING_LEN);
        
        if (len >= 0) {
            // Build JSON result
            if (json_pos + strlen(version_str) + 50 < result_cap) {
                json_pos += snprintf((char*)result + json_pos, result_cap - json_pos,
                    "{\"type\":\"registry\",\"version\":\"%s\"}", version_str);
            }
        } else {
            // Invalid string - return null
            if (json_pos + 4 < result_cap) {
                memcpy(result, "null", 4);
                json_pos = 4;
                result[json_pos] = '\0';
            }
        }
    }
    
    *result_len = json_pos;
    free(json_str);
    return 0;
}
