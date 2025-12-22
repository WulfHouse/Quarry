/* Version comparison functions - C implementation
 *
 * This provides the core logic for version comparison, called from Pyrite via FFI.
 * The logic matches the Python implementation in quarry/main.py and quarry/dependency.py
 */

#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <stdint.h>

/* Compare two version strings
 * Returns: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
 */
int32_t version_compare_c(const uint8_t* v1, int64_t v1_len, const uint8_t* v2, int64_t v2_len) {
    // Convert to null-terminated strings for easier manipulation
    char* s1 = (char*)malloc(v1_len + 1);
    char* s2 = (char*)malloc(v2_len + 1);
    memcpy(s1, v1, v1_len);
    memcpy(s2, v2, v2_len);
    s1[v1_len] = '\0';
    s2[v2_len] = '\0';
    
    // Parse version parts
    int parts1[32], parts2[32];
    int count1 = 0, count2 = 0;
    
    // Parse v1
    char* token = strtok(s1, ".");
    while (token && count1 < 32) {
        parts1[count1++] = atoi(token);
        token = strtok(NULL, ".");
    }
    
    // Parse v2
    memcpy(s1, v1, v1_len);  // Reset for strtok
    s1[v1_len] = '\0';
    token = strtok(s2, ".");
    while (token && count2 < 32) {
        parts2[count2++] = atoi(token);
        token = strtok(NULL, ".");
    }
    
    // Compare parts (treat missing parts as 0)
    int max_count = count1 > count2 ? count1 : count2;
    for (int i = 0; i < max_count; i++) {
        int part1 = (i < count1) ? parts1[i] : 0;
        int part2 = (i < count2) ? parts2[i] : 0;
        if (part1 < part2) {
            free(s1);
            free(s2);
            return -1;
        } else if (part1 > part2) {
            free(s1);
            free(s2);
            return 1;
        }
    }
    
    free(s1);
    free(s2);
    return 0;
}

/* Check if version satisfies constraint
 * Returns: 1 if true, 0 if false
 */
int32_t version_satisfies_c(const uint8_t* version, int64_t version_len,
                            const uint8_t* constraint, int64_t constraint_len) {
    char* version_str = (char*)malloc(version_len + 1);
    char* constraint_str = (char*)malloc(constraint_len + 1);
    memcpy(version_str, version, version_len);
    memcpy(constraint_str, constraint, constraint_len);
    version_str[version_len] = '\0';
    constraint_str[constraint_len] = '\0';
    
    // "*" matches any version
    if (strcmp(constraint_str, "*") == 0) {
        free(version_str);
        free(constraint_str);
        return 1;
    }
    
    // ">=" constraint
    if (strncmp(constraint_str, ">=", 2) == 0) {
        char* min_version = constraint_str + 2;
        // Skip whitespace
        while (*min_version == ' ' || *min_version == '\t') min_version++;
        int cmp = version_compare_c((uint8_t*)version_str, version_len,
                                     (uint8_t*)min_version, strlen(min_version));
        free(version_str);
        free(constraint_str);
        return cmp >= 0 ? 1 : 0;
    }
    
    // "~>" pessimistic constraint
    if (strncmp(constraint_str, "~>", 2) == 0) {
        char* base_version = constraint_str + 2;
        while (*base_version == ' ' || *base_version == '\t') base_version++;
        
        // Extract major.minor prefix
        char* dot = strchr(base_version, '.');
        if (dot) {
            int major_len = dot - base_version;
            char prefix[64];
            // Build prefix like "1.0" (without trailing dot for startswith check)
            snprintf(prefix, sizeof(prefix), "%.*s", major_len, base_version);
            strncat(prefix, ".", sizeof(prefix) - strlen(prefix) - 1);
            
            // Check if version starts with prefix (e.g., "1.5.0" starts with "1.0.")
            int prefix_len = strlen(prefix);
            if (strlen(version_str) >= prefix_len) {
                int result = strncmp(version_str, prefix, prefix_len) == 0 ? 1 : 0;
                free(version_str);
                free(constraint_str);
                return result;
            } else {
                free(version_str);
                free(constraint_str);
                return 0;
            }
        } else {
            // No dot: check if version starts with base_version
            int base_len = strlen(base_version);
            int result = strncmp(version_str, base_version, base_len) == 0 ? 1 : 0;
            free(version_str);
            free(constraint_str);
            return result;
        }
    }
    
    // Exact match
    int result = strcmp(version_str, constraint_str) == 0 ? 1 : 0;
    free(version_str);
    free(constraint_str);
    return result;
}

/* Get latest version from JSON array
 * Input: JSON string like '["1.0.0", "2.0.0", "1.5.0"]'
 * Output: Writes latest version to result buffer
 * Returns: 0 on success, -1 on error
 */
int32_t version_latest_c(const uint8_t* versions_json, int64_t json_len,
                         uint8_t* result, int64_t result_cap, int64_t* result_len) {
    // Simplified JSON parsing for MVP
    // For full implementation, use a proper JSON parser
    // This is a placeholder that demonstrates the interface
    
    // For MVP: Return error (not implemented yet)
    *result_len = 0;
    return -1;
}

/* Helper: Check if string starts with prefix */
static int starts_with(const char* str, const char* prefix) {
    return strncmp(str, prefix, strlen(prefix)) == 0;
}

/* Helper: Trim whitespace from start of string (modifies in place) */
static char* trim_start(char* str) {
    while (*str == ' ' || *str == '\t') {
        str++;
    }
    return str;
}

/* Helper: Check if version string starts with prefix (e.g., "1.0.0" starts with "1.0", but "1.5.0" does not) */
static int version_starts_with(const char* version, const char* prefix) {
    // Check if version starts with prefix (Python's startswith behavior)
    // "1.0.0" starts with "1.0", "1.5.0" does not start with "1.0"
    int prefix_len = strlen(prefix);
    if (strlen(version) < prefix_len) {
        return 0;
    }
    return strncmp(version, prefix, prefix_len) == 0;
}

/* Select version from available versions based on constraint (buffer-based FFI)
 * Input: constraint (UTF-8 bytes), available_versions_json (JSON array string)
 * Output: Writes JSON string (version or null) to result buffer, sets result_len
 * Returns: 0 on success, -1 on error
 */
int32_t version_select_c(const uint8_t* constraint, int64_t constraint_len,
                          const uint8_t* versions_json, int64_t json_len,
                          uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!constraint || !versions_json || !result || result_cap < 2) {
        if (result_len) *result_len = 0;
        return -1;
    }
    
    // Convert constraint to null-terminated string
    char* constraint_str = (char*)malloc(constraint_len + 1);
    if (!constraint_str) {
        if (result_len) *result_len = 0;
        return -1;
    }
    memcpy(constraint_str, constraint, constraint_len);
    constraint_str[constraint_len] = '\0';
    
    // Convert versions JSON to null-terminated string
    char* json_str = (char*)malloc(json_len + 1);
    if (!json_str) {
        free(constraint_str);
        if (result_len) *result_len = 0;
        return -1;
    }
    memcpy(json_str, versions_json, json_len);
    json_str[json_len] = '\0';
    
    // Parse constraint
    int json_pos = 0;
    
    // Handle "*" constraint
    if (strcmp(constraint_str, "*") == 0) {
        // Find latest version by parsing JSON array and comparing
        // Simple JSON parsing: find all quoted strings, compare them
        const char* pos = json_str;
        char* versions[256];
        int version_count = 0;
        
        // Skip opening bracket
        while (*pos && (*pos == '[' || *pos == ' ' || *pos == '\t' || *pos == '\n')) pos++;
        
        // Parse quoted strings
        while (*pos && version_count < 256) {
            // Skip whitespace and commas
            while (*pos && (*pos == ' ' || *pos == '\t' || *pos == ',' || *pos == '\n')) pos++;
            if (*pos == ']') break;
            
            // Find quoted string
            if (*pos == '"') {
                pos++; // Skip opening quote
                const char* str_start = pos;
                while (*pos && *pos != '"') pos++;
                if (*pos == '"') {
                    int str_len = pos - str_start;
                    char* version = (char*)malloc(str_len + 1);
                    memcpy(version, str_start, str_len);
                    version[str_len] = '\0';
                    versions[version_count++] = version;
                    pos++; // Skip closing quote
                }
            } else {
                pos++;
            }
        }
        
        // Find latest version by comparing all
        if (version_count > 0) {
            char* latest = versions[0];
            for (int i = 1; i < version_count; i++) {
                int cmp = version_compare_c((uint8_t*)versions[i], strlen(versions[i]),
                                            (uint8_t*)latest, strlen(latest));
                if (cmp > 0) {
                    latest = versions[i];
                }
            }
            
            // Write result as JSON string
            int latest_len = strlen(latest);
            if (json_pos + latest_len + 5 < result_cap) {
                result[json_pos++] = '"';
                memcpy(result + json_pos, latest, latest_len);
                json_pos += latest_len;
                result[json_pos++] = '"';
            }
            
            // Free allocated versions
            for (int i = 0; i < version_count; i++) {
                free(versions[i]);
            }
        } else {
            // No versions: return null
            if (json_pos + 4 < result_cap) {
                memcpy(result + json_pos, "null", 4);
                json_pos += 4;
            }
        }
    }
    // Handle ">=" constraint
    else if (starts_with(constraint_str, ">=")) {
        char* min_version = trim_start(constraint_str + 2);
        
        // Parse versions and filter
        const char* pos = json_str;
        char* versions[256];
        int version_count = 0;
        
        while (*pos && (*pos == '[' || *pos == ' ' || *pos == '\t' || *pos == '\n')) pos++;
        
        while (*pos && version_count < 256) {
            while (*pos && (*pos == ' ' || *pos == '\t' || *pos == ',' || *pos == '\n')) pos++;
            if (*pos == ']') break;
            
            if (*pos == '"') {
                pos++;
                const char* str_start = pos;
                while (*pos && *pos != '"') pos++;
                if (*pos == '"') {
                    int str_len = pos - str_start;
                    char* version = (char*)malloc(str_len + 1);
                    memcpy(version, str_start, str_len);
                    version[str_len] = '\0';
                    
                    // Check if version >= min_version
                    int cmp = version_compare_c((uint8_t*)version, str_len,
                                                (uint8_t*)min_version, strlen(min_version));
                    if (cmp >= 0) {
                        versions[version_count++] = version;
                    } else {
                        free(version);
                    }
                    pos++;
                }
            } else {
                pos++;
            }
        }
        
        // Find latest from matching versions
        if (version_count > 0) {
            char* latest = versions[0];
            for (int i = 1; i < version_count; i++) {
                int cmp = version_compare_c((uint8_t*)versions[i], strlen(versions[i]),
                                            (uint8_t*)latest, strlen(latest));
                if (cmp > 0) {
                    latest = versions[i];
                }
            }
            
            int latest_len = strlen(latest);
            if (json_pos + latest_len + 5 < result_cap) {
                result[json_pos++] = '"';
                memcpy(result + json_pos, latest, latest_len);
                json_pos += latest_len;
                result[json_pos++] = '"';
            }
            
            for (int i = 0; i < version_count; i++) {
                free(versions[i]);
            }
        } else {
            if (json_pos + 4 < result_cap) {
                memcpy(result + json_pos, "null", 4);
                json_pos += 4;
            }
        }
    }
    // Handle "~>" constraint
    else if (starts_with(constraint_str, "~>")) {
        char* base_version = trim_start(constraint_str + 2);
        
        // Extract major.minor prefix from base_version (e.g., "1.0" from "~>1.0" or "~>1.0.5")
        // Python code: parts = base_version.split('.'); if len(parts) >= 2: major = parts[0]; minor = parts[1]
        // Then checks: v.startswith(f"{major}.{minor}") -> "1.0"
        char* first_dot = strchr(base_version, '.');
        if (first_dot) {
            // Find second dot (if exists) to determine prefix end
            char* second_dot = strchr(first_dot + 1, '.');
            int prefix_len;
            if (second_dot) {
                prefix_len = second_dot - base_version;  // "1.0" from "1.0.5"
            } else {
                prefix_len = strlen(base_version);  // "1.0" from "1.0"
            }
            
            char prefix[64];
            if (prefix_len < sizeof(prefix)) {
                strncpy(prefix, base_version, prefix_len);
                prefix[prefix_len] = '\0';
            } else {
                prefix[0] = '\0';
            }
            
            // Parse versions and filter by prefix (version must start with "major.minor")
            const char* pos = json_str;
            char* versions[256];
            int version_count = 0;
            
            while (*pos && (*pos == '[' || *pos == ' ' || *pos == '\t' || *pos == '\n')) pos++;
            
            while (*pos && version_count < 256) {
                while (*pos && (*pos == ' ' || *pos == '\t' || *pos == ',' || *pos == '\n')) pos++;
                if (*pos == ']') break;
                
                if (*pos == '"') {
                    pos++;
                    const char* str_start = pos;
                    while (*pos && *pos != '"') pos++;
                    if (*pos == '"') {
                        int str_len = pos - str_start;
                        char* version = (char*)malloc(str_len + 1);
                        memcpy(version, str_start, str_len);
                        version[str_len] = '\0';
                        
                        // Check if version starts with prefix (e.g., "1.5.0" starts with "1.0.")
                        if (version_starts_with(version, prefix)) {
                            versions[version_count++] = version;
                        } else {
                            free(version);
                        }
                        pos++;
                    }
                } else {
                    pos++;
                }
            }
            
            // Find latest from matching versions
            if (version_count > 0) {
                char* latest = versions[0];
                for (int i = 1; i < version_count; i++) {
                    int cmp = version_compare_c((uint8_t*)versions[i], strlen(versions[i]),
                                                (uint8_t*)latest, strlen(latest));
                    if (cmp > 0) {
                        latest = versions[i];
                    }
                }
                
                int latest_len = strlen(latest);
                if (json_pos + latest_len + 5 < result_cap) {
                    result[json_pos++] = '"';
                    memcpy(result + json_pos, latest, latest_len);
                    json_pos += latest_len;
                    result[json_pos++] = '"';
                }
                
                for (int i = 0; i < version_count; i++) {
                    free(versions[i]);
                }
            } else {
                if (json_pos + 4 < result_cap) {
                    memcpy(result + json_pos, "null", 4);
                    json_pos += 4;
                }
            }
        } else {
            // No dot in base_version: exact match only
            if (json_pos + 4 < result_cap) {
                memcpy(result + json_pos, "null", 4);
                json_pos += 4;
            }
        }
    }
    // Exact version match
    else {
        // Check if constraint exists in versions JSON
        int found = 0;
        const char* pos = json_str;
        
        while (*pos) {
            if (*pos == '"') {
                pos++;
                const char* str_start = pos;
                while (*pos && *pos != '"') pos++;
                if (*pos == '"') {
                    int str_len = pos - str_start;
                    if (str_len == constraint_len && 
                        strncmp(str_start, constraint_str, constraint_len) == 0) {
                        found = 1;
                        break;
                    }
                    pos++;
                }
            } else {
                pos++;
            }
        }
        
        if (found) {
            // Return constraint as JSON string
            if (json_pos + constraint_len + 5 < result_cap) {
                result[json_pos++] = '"';
                memcpy(result + json_pos, constraint_str, constraint_len);
                json_pos += constraint_len;
                result[json_pos++] = '"';
            }
        } else {
            // Return null
            if (json_pos + 4 < result_cap) {
                memcpy(result + json_pos, "null", 4);
                json_pos += 4;
            }
        }
    }
    
    result[json_pos] = '\0';
    if (result_len) *result_len = json_pos;
    
    free(constraint_str);
    free(json_str);
    return 0;
}

/* Check if version string is valid semantic version format
 * Pattern: ^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$
 * Returns: 1 if valid semver, 0 if invalid
 */
int32_t is_semver_c(const uint8_t* version, int64_t version_len, int32_t* result) {
    if (!version || version_len <= 0 || !result) {
        return -1;
    }
    
    // Convert to null-terminated string
    char* version_str = (char*)malloc(version_len + 1);
    if (!version_str) {
        return -1;
    }
    memcpy(version_str, version, version_len);
    version_str[version_len] = '\0';
    
    // Manual parsing: ^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$
    const char* pos = version_str;
    
    // Must start with digit (major version)
    if (!isdigit(*pos)) {
        free(version_str);
        *result = 0;
        return 0;
    }
    
    // Parse major version (one or more digits)
    while (isdigit(*pos)) pos++;
    
    // Must have dot
    if (*pos != '.') {
        free(version_str);
        *result = 0;
        return 0;
    }
    pos++;
    
    // Must have digit (minor version)
    if (!isdigit(*pos)) {
        free(version_str);
        *result = 0;
        return 0;
    }
    
    // Parse minor version (one or more digits)
    while (isdigit(*pos)) pos++;
    
    // Must have dot
    if (*pos != '.') {
        free(version_str);
        *result = 0;
        return 0;
    }
    pos++;
    
    // Must have digit (patch version)
    if (!isdigit(*pos)) {
        free(version_str);
        *result = 0;
        return 0;
    }
    
    // Parse patch version (one or more digits)
    while (isdigit(*pos)) pos++;
    
    // Optional pre-release suffix: -[a-zA-Z0-9.-]+
    if (*pos == '-') {
        pos++;
        
        // Must have at least one character after hyphen
        if (!(*pos && (isalnum(*pos) || *pos == '.' || *pos == '-'))) {
            free(version_str);
            *result = 0;
            return 0;
        }
        
        // Parse pre-release identifier (one or more alphanumeric, dots, or hyphens)
        // Python regex [a-zA-Z0-9.-]+ allows hyphens anywhere, including at the end
        while (*pos && (isalnum(*pos) || *pos == '.' || *pos == '-')) {
            pos++;
        }
    }
    
    // Must be at end of string (Python regex $ matches before newline, so we allow \n)
    // For equivalence, we match Python behavior: $ matches end of string or before newline
    if (*pos != '\0' && *pos != '\n') {
        free(version_str);
        *result = 0;
        return 0;
    }
    
    free(version_str);
    *result = 1;
    return 0;
}

/* Check if package name is valid
 * Pattern: ^[a-zA-Z0-9_-]+$ (but cannot start/end with hyphen or underscore)
 * Returns: 1 if valid, 0 if invalid
 */
int32_t is_valid_package_name_c(const uint8_t* name, int64_t name_len, int32_t* result) {
    if (!name || name_len <= 0 || !result) {
        return -1;
    }
    
    // Empty string is invalid
    if (name_len == 0) {
        *result = 0;
        return 0;
    }
    
    // Convert to null-terminated string for easier manipulation
    char* name_str = (char*)malloc(name_len + 1);
    if (!name_str) {
        return -1;
    }
    memcpy(name_str, name, name_len);
    name_str[name_len] = '\0';
    
    // Check first character (cannot be hyphen or underscore)
    if (name_str[0] == '-' || name_str[0] == '_') {
        free(name_str);
        *result = 0;
        return 0;
    }
    
    // Check last character (cannot be hyphen or underscore)
    if (name_str[name_len - 1] == '-' || name_str[name_len - 1] == '_') {
        free(name_str);
        *result = 0;
        return 0;
    }
    
    // Check all characters are alphanumeric, hyphen, or underscore
    // Python regex $ matches before newline, so we allow \n at the end for equivalence
    for (int64_t i = 0; i < name_len; i++) {
        char c = name_str[i];
        // Allow newline at end (Python regex $ behavior)
        if (i == name_len - 1 && c == '\n') {
            break;
        }
        if (!(isalnum(c) || c == '-' || c == '_')) {
            free(name_str);
            *result = 0;
            return 0;
        }
    }
    
    free(name_str);
    *result = 1;
    return 0;
}

/* Normalize string (trim whitespace and convert to lowercase)
 * Input: s (UTF-8 bytes)
 * Output: Writes normalized string to result buffer, sets result_len
 * Returns: 0 on success, -1 on error
 */
int32_t normalize_string_c(const uint8_t* s, int64_t s_len,
                           uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!s || s_len < 0 || !result || result_cap <= 0 || !result_len) {
        if (result_len) *result_len = 0;
        return -1;
    }
    
    if (s_len == 0) {
        *result_len = 0;
        return 0;
    }
    
    // Convert to null-terminated string
    char* s_str = (char*)malloc(s_len + 1);
    if (!s_str) {
        if (result_len) *result_len = 0;
        return -1;
    }
    memcpy(s_str, s, s_len);
    s_str[s_len] = '\0';
    
    // Trim leading whitespace
    char* start = s_str;
    while (*start && (*start == ' ' || *start == '\t' || *start == '\n' || *start == '\r')) {
        start++;
    }
    
    // Trim trailing whitespace
    char* end = s_str + s_len - 1;
    while (end >= start && (*end == ' ' || *end == '\t' || *end == '\n' || *end == '\r')) {
        *end = '\0';
        end--;
    }
    
    int64_t trimmed_len = strlen(start);
    
    // Convert to lowercase and copy to result buffer
    int64_t output_len = 0;
    for (int64_t i = 0; i < trimmed_len && output_len < result_cap - 1; i++) {
        result[output_len++] = (uint8_t)tolower((unsigned char)start[i]);
    }
    
    result[output_len] = '\0';
    *result_len = output_len;
    
    free(s_str);
    return 0;
}
