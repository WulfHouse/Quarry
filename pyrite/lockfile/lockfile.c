/* Lockfile operations - C implementation
 *
 * This provides lockfile generation and reading, called from Pyrite via FFI.
 * The logic matches the Python implementation in quarry/dependency.py
 */

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#define MAX_STRING_LEN 1024
#define MAX_JSON_LEN 65536
#define MAX_TOML_LEN 65536
#define MAX_DEPS 256

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
        
        // Parse type
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

/* Compare dependency names for sorting */
static int compare_deps(const void* a, const void* b) {
    const DepEntry* dep_a = (const DepEntry*)a;
    const DepEntry* dep_b = (const DepEntry*)b;
    return strcmp(dep_a->name, dep_b->name);
}

/* Generate lockfile TOML */
int32_t generate_lockfile_c(const uint8_t* deps_json, int64_t json_len,
                            uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!deps_json || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    // Convert to null-terminated string
    char* json_str = (char*)malloc(json_len + 1);
    if (!json_str) {
        return -1;
    }
    memcpy(json_str, deps_json, json_len);
    json_str[json_len] = '\0';
    
    // Parse dependencies
    DepEntry deps[MAX_DEPS];
    int dep_count = parse_deps_json(json_str, deps, MAX_DEPS);
    
    // Sort by name (deterministic ordering)
    qsort(deps, dep_count, sizeof(DepEntry), compare_deps);
    
    // Build TOML
    int toml_pos = 0;
    
    // Write header
    if (toml_pos + 20 < result_cap) {
        memcpy(result + toml_pos, "[dependencies]\n", 15);
        toml_pos += 15;
    }
    
    // Write each dependency
    for (int i = 0; i < dep_count && toml_pos < result_cap - 200; i++) {
        DepEntry* dep = &deps[i];
        
        if (strcmp(dep->type, "registry") == 0) {
            // Registry: name = "version" or name = { version = "...", checksum = "..." }
            if (dep->checksum[0]) {
                // With checksum
                int needed = snprintf((char*)result + toml_pos, result_cap - toml_pos,
                    "%s = { version = \"%s\", checksum = \"%s\" }\n",
                    dep->name, dep->version, dep->checksum);
                if (needed > 0 && toml_pos + needed < result_cap) {
                    toml_pos += needed;
                }
            } else {
                // Simple version
                int needed = snprintf((char*)result + toml_pos, result_cap - toml_pos,
                    "%s = \"%s\"\n", dep->name, dep->version);
                if (needed > 0 && toml_pos + needed < result_cap) {
                    toml_pos += needed;
                }
            }
        } else if (strcmp(dep->type, "git") == 0) {
            // Git: name = { git = "...", branch = "...", commit = "..." }
            int needed = snprintf((char*)result + toml_pos, result_cap - toml_pos,
                "%s = { git = \"%s\"", dep->name, dep->git_url);
            if (needed > 0 && toml_pos + needed < result_cap) {
                toml_pos += needed;
            }
            
            if (dep->git_branch[0]) {
                needed = snprintf((char*)result + toml_pos, result_cap - toml_pos,
                    ", branch = \"%s\"", dep->git_branch);
                if (needed > 0 && toml_pos + needed < result_cap) {
                    toml_pos += needed;
                }
            }
            
            if (dep->commit[0]) {
                needed = snprintf((char*)result + toml_pos, result_cap - toml_pos,
                    ", commit = \"%s\"", dep->commit);
                if (needed > 0 && toml_pos + needed < result_cap) {
                    toml_pos += needed;
                }
            }
            
            if (toml_pos + 3 < result_cap) {
                result[toml_pos++] = ' ';
                result[toml_pos++] = '}';
                result[toml_pos++] = '\n';
            }
        } else if (strcmp(dep->type, "path") == 0) {
            // Path: name = { path = "...", hash = "..." }
            int needed = snprintf((char*)result + toml_pos, result_cap - toml_pos,
                "%s = { path = \"%s\"", dep->name, dep->path);
            if (needed > 0 && toml_pos + needed < result_cap) {
                toml_pos += needed;
            }
            
            if (dep->hash[0]) {
                needed = snprintf((char*)result + toml_pos, result_cap - toml_pos,
                    ", hash = \"%s\"", dep->hash);
                if (needed > 0 && toml_pos + needed < result_cap) {
                    toml_pos += needed;
                }
            }
            
            if (toml_pos + 3 < result_cap) {
                result[toml_pos++] = ' ';
                result[toml_pos++] = '}';
                result[toml_pos++] = '\n';
            }
        }
    }
    
    result[toml_pos] = '\0';
    *result_len = toml_pos;
    
    free(json_str);
    return 0;
}

/* Simple TOML parser for [dependencies] section */
static int parse_toml_dependencies(const char* toml_text, DepEntry* deps, int max_deps) {
    const char* pos = toml_text;
    int dep_count = 0;
    bool in_dependencies = false;
    
    while (*pos && dep_count < max_deps) {
        // Check for [dependencies] section
        if (strncmp(pos, "[dependencies]", 14) == 0) {
            in_dependencies = true;
            pos += 14;
            continue;
        }
        
        // Check for next section
        if (*pos == '[' && in_dependencies) {
            break; // Next section starts
        }
        
        if (in_dependencies && *pos != '\n' && *pos != ' ' && *pos != '\t') {
            // Parse dependency line
            const char* name_start = pos;
            while (*pos && *pos != ' ' && *pos != '=' && *pos != '\n') pos++;
            int name_len = pos - name_start;
            if (name_len > 0 && name_len < MAX_STRING_LEN) {
                memcpy(deps[dep_count].name, name_start, name_len);
                deps[dep_count].name[name_len] = '\0';
                
                // Skip to value
                while (*pos && (*pos == ' ' || *pos == '=' || *pos == '\t')) pos++;
                
                // Parse value (string or dict)
                if (*pos == '"') {
                    // Simple string: name = "version"
                    pos++; // Skip quote
                    const char* version_start = pos;
                    while (*pos && *pos != '"') pos++;
                    if (*pos == '"') {
                        int version_len = pos - version_start;
                        if (version_len < MAX_STRING_LEN) {
                            memcpy(deps[dep_count].version, version_start, version_len);
                            deps[dep_count].version[version_len] = '\0';
                            strcpy(deps[dep_count].type, "registry");
                            dep_count++;
                        }
                    }
                } else if (*pos == '{') {
                    // Dict: name = { ... }
                    // Simple parsing: look for type indicators
                    if (strstr(pos, "git") != NULL) {
                        strcpy(deps[dep_count].type, "git");
                        // Extract git URL, branch, commit (simplified)
                        const char* git_start = strstr(pos, "git = \"");
                        if (git_start) {
                            git_start += 7;
                            const char* git_end = git_start;
                            while (*git_end && *git_end != '"') git_end++;
                            int git_len = git_end - git_start;
                            if (git_len < MAX_STRING_LEN) {
                                memcpy(deps[dep_count].git_url, git_start, git_len);
                                deps[dep_count].git_url[git_len] = '\0';
                            }
                        }
                    } else if (strstr(pos, "path") != NULL) {
                        strcpy(deps[dep_count].type, "path");
                        // Extract path (simplified)
                        const char* path_start = strstr(pos, "path = \"");
                        if (path_start) {
                            path_start += 8;
                            const char* path_end = path_start;
                            while (*path_end && *path_end != '"') path_end++;
                            int path_len = path_end - path_start;
                            if (path_len < MAX_STRING_LEN) {
                                memcpy(deps[dep_count].path, path_start, path_len);
                                deps[dep_count].path[path_len] = '\0';
                            }
                        }
                    } else if (strstr(pos, "version") != NULL) {
                        strcpy(deps[dep_count].type, "registry");
                        // Extract version and checksum (simplified)
                        const char* version_start = strstr(pos, "version = \"");
                        if (version_start) {
                            version_start += 11;
                            const char* version_end = version_start;
                            while (*version_end && *version_end != '"') version_end++;
                            int version_len = version_end - version_start;
                            if (version_len < MAX_STRING_LEN) {
                                memcpy(deps[dep_count].version, version_start, version_len);
                                deps[dep_count].version[version_len] = '\0';
                            }
                        }
                    }
                    dep_count++;
                }
            }
        }
        
        pos++;
    }
    
    return dep_count;
}

/* Read lockfile and parse dependencies */
int32_t read_lockfile_c(const uint8_t* lockfile_text, int64_t text_len,
                        uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!lockfile_text || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    // Convert to null-terminated string
    char* toml_str = (char*)malloc(text_len + 1);
    if (!toml_str) {
        return -1;
    }
    memcpy(toml_str, lockfile_text, text_len);
    toml_str[text_len] = '\0';
    
    // Parse dependencies
    DepEntry deps[MAX_DEPS];
    int dep_count = parse_toml_dependencies(toml_str, deps, MAX_DEPS);
    
    // Build JSON output
    int json_pos = 0;
    if (json_pos + 2 < result_cap) {
        result[json_pos++] = '{';
    }
    
    for (int i = 0; i < dep_count && json_pos < result_cap - 200; i++) {
        DepEntry* dep = &deps[i];
        
        if (i > 0 && json_pos < result_cap - 1) {
            result[json_pos++] = ',';
        }
        
        // Write dependency name and value
        int needed = snprintf((char*)result + json_pos, result_cap - json_pos,
            "\"%s\":{\"type\":\"%s\"", dep->name, dep->type);
        if (needed > 0 && json_pos + needed < result_cap) {
            json_pos += needed;
        }
        
        // Add type-specific fields
        if (dep->version[0]) {
            needed = snprintf((char*)result + json_pos, result_cap - json_pos,
                ",\"version\":\"%s\"", dep->version);
            if (needed > 0 && json_pos + needed < result_cap) {
                json_pos += needed;
            }
        }
        if (dep->git_url[0]) {
            needed = snprintf((char*)result + json_pos, result_cap - json_pos,
                ",\"git_url\":\"%s\"", dep->git_url);
            if (needed > 0 && json_pos + needed < result_cap) {
                json_pos += needed;
            }
        }
        if (dep->git_branch[0]) {
            needed = snprintf((char*)result + json_pos, result_cap - json_pos,
                ",\"git_branch\":\"%s\"", dep->git_branch);
            if (needed > 0 && json_pos + needed < result_cap) {
                json_pos += needed;
            }
        }
        if (dep->commit[0]) {
            needed = snprintf((char*)result + json_pos, result_cap - json_pos,
                ",\"commit\":\"%s\"", dep->commit);
            if (needed > 0 && json_pos + needed < result_cap) {
                json_pos += needed;
            }
        }
        if (dep->path[0]) {
            needed = snprintf((char*)result + json_pos, result_cap - json_pos,
                ",\"path\":\"%s\"", dep->path);
            if (needed > 0 && json_pos + needed < result_cap) {
                json_pos += needed;
            }
        }
        if (dep->checksum[0]) {
            needed = snprintf((char*)result + json_pos, result_cap - json_pos,
                ",\"checksum\":\"%s\"", dep->checksum);
            if (needed > 0 && json_pos + needed < result_cap) {
                json_pos += needed;
            }
        }
        if (dep->hash[0]) {
            needed = snprintf((char*)result + json_pos, result_cap - json_pos,
                ",\"hash\":\"%s\"", dep->hash);
            if (needed > 0 && json_pos + needed < result_cap) {
                json_pos += needed;
            }
        }
        
        if (json_pos + 2 < result_cap) {
            result[json_pos++] = '}';
        }
    }
    
    if (json_pos + 2 < result_cap) {
        result[json_pos++] = '}';
    }
    result[json_pos] = '\0';
    *result_len = json_pos;
    
    free(toml_str);
    return 0;
}
