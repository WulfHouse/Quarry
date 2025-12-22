/* TOML parsing functions - C implementation
 *
 * This provides simple TOML parsing for Quarry, called from Pyrite via FFI.
 * The logic matches the Python implementation in quarry/dependency.py and quarry/workspace.py
 */

#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <stdint.h>

/* Helper: Skip whitespace */
static void skip_whitespace(const char** str) {
    while (**str && isspace((unsigned char)**str)) {
        (*str)++;
    }
}

/* Helper: Trim string (modifies in place) */
static void trim_string(char* str) {
    int start = 0;
    int end = strlen(str) - 1;
    
    // Skip leading whitespace
    while (start <= end && isspace((unsigned char)str[start])) {
        start++;
    }
    
    // Skip trailing whitespace
    while (end >= start && isspace((unsigned char)str[end])) {
        end--;
    }
    
    // Move trimmed string to start
    int len = end - start + 1;
    if (start > 0) {
        memmove(str, str + start, len);
    }
    str[len] = '\0';
}

/* Helper: Unquote string (removes surrounding quotes) */
static void unquote_string(char* str) {
    int len = strlen(str);
    if (len >= 2) {
        if ((str[0] == '"' && str[len-1] == '"') ||
            (str[0] == '\'' && str[len-1] == '\'')) {
            memmove(str, str + 1, len - 2);
            str[len - 2] = '\0';
        }
    }
}

/* Parse dependencies section from TOML text (buffer-based FFI)
 * Input: toml_text (UTF-8 bytes), text_len (length)
 * Output: Writes JSON string to result buffer, sets result_len
 * Returns: 0 on success, -1 on error
 */
int32_t parse_dependencies_simple_c(const uint8_t* toml_text, int64_t text_len,
                                     uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!toml_text || !result || result_cap < 2) {
        if (result_len) *result_len = 0;
        return -1;
    }
    
    // Convert to null-terminated string for easier manipulation
    char* text = (char*)malloc(text_len + 1);
    if (!text) {
        if (result_len) *result_len = 0;
        return -1;
    }
    memcpy(text, toml_text, text_len);
    text[text_len] = '\0';
    
    // Build JSON in result buffer
    int json_pos = 0;
    int first = 1;
    
    // Start JSON object
    if (json_pos < result_cap - 1) {
        result[json_pos++] = '{';
    }
    
    int in_dependencies = 0;
    const char* line_start = text;
    
    // Process line by line
    while (*line_start && json_pos < result_cap - 10) {
        // Find end of line
        const char* line_end = line_start;
        while (*line_end && *line_end != '\n' && *line_end != '\r') {
            line_end++;
        }
        
        // Copy line to buffer
        int line_len = line_end - line_start;
        char* line = (char*)malloc(line_len + 1);
        if (!line) {
            free(text);
            if (result_len) *result_len = 0;
            return -1;
        }
        memcpy(line, line_start, line_len);
        line[line_len] = '\0';
        trim_string(line);
        
        // Check for [dependencies] section
        if (strcmp(line, "[dependencies]") == 0) {
            in_dependencies = 1;
            free(line);
            line_start = line_end;
            if (*line_start == '\r') line_start++;
            if (*line_start == '\n') line_start++;
            continue;
        }
        
        // Check for next section (stops dependencies parsing)
        if (line[0] == '[' && line[strlen(line) - 1] == ']') {
            if (in_dependencies) {
                free(line);
                break;
            }
            free(line);
            line_start = line_end;
            if (*line_start == '\r') line_start++;
            if (*line_start == '\n') line_start++;
            continue;
        }
        
        // Parse dependency line: name = "version"
        if (in_dependencies) {
            char* eq_pos = strchr(line, '=');
            if (eq_pos) {
                // Split at =
                *eq_pos = '\0';
                char* name = line;
                char* value = eq_pos + 1;
                
                trim_string(name);
                trim_string(value);
                unquote_string(value);
                
                // Add comma if not first
                if (!first) {
                    if (json_pos < result_cap - 1) {
                        result[json_pos++] = ',';
                    }
                }
                first = 0;
                
                // Add "name": "value"
                int name_len = strlen(name);
                int value_len = strlen(value);
                int needed = name_len + value_len + 10; // quotes, colons, etc.
                
                if (json_pos + needed < result_cap - 1) {
                    result[json_pos++] = '"';
                    memcpy(result + json_pos, name, name_len);
                    json_pos += name_len;
                    result[json_pos++] = '"';
                    result[json_pos++] = ':';
                    result[json_pos++] = '"';
                    memcpy(result + json_pos, value, value_len);
                    json_pos += value_len;
                    result[json_pos++] = '"';
                }
            }
        }
        
        free(line);
        line_start = line_end;
        if (*line_start == '\r') line_start++;
        if (*line_start == '\n') line_start++;
    }
    
    // Close JSON object
    if (json_pos < result_cap - 1) {
        result[json_pos++] = '}';
    }
    result[json_pos] = '\0';
    
    if (result_len) *result_len = json_pos;
    free(text);
    return 0;
}

/* Parse workspace members from TOML text (buffer-based FFI)
 * Input: workspace_text (UTF-8 bytes), text_len (length)
 * Output: Writes JSON string to result buffer, sets result_len
 * Returns: 0 on success, -1 on error
 */
int32_t parse_workspace_simple_c(const uint8_t* workspace_text, int64_t text_len,
                                  uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!workspace_text || !result || result_cap < 2) {
        if (result_len) *result_len = 0;
        return -1;
    }
    
    // Convert to null-terminated string for easier manipulation
    char* text = (char*)malloc(text_len + 1);
    if (!text) {
        if (result_len) *result_len = 0;
        return -1;
    }
    memcpy(text, workspace_text, text_len);
    text[text_len] = '\0';
    
    // Build JSON in result buffer
    int json_pos = 0;
    int first = 1;
    
    // Start JSON array
    if (json_pos < result_cap - 1) {
        result[json_pos++] = '[';
    }
    
    int in_workspace = 0;
    const char* line_start = text;
    
    // Process line by line
    while (*line_start && json_pos < result_cap - 10) {
        // Find end of line
        const char* line_end = line_start;
        while (*line_end && *line_end != '\n' && *line_end != '\r') {
            line_end++;
        }
        
        // Copy line to buffer
        int line_len = line_end - line_start;
        char* line = (char*)malloc(line_len + 1);
        if (!line) {
            free(text);
            if (result_len) *result_len = 0;
            return -1;
        }
        memcpy(line, line_start, line_len);
        line[line_len] = '\0';
        trim_string(line);
        
        // Check for [workspace] section
        if (strcmp(line, "[workspace]") == 0) {
            in_workspace = 1;
            free(line);
            line_start = line_end;
            if (*line_start == '\r') line_start++;
            if (*line_start == '\n') line_start++;
            continue;
        }
        
        // Check for members = [...] line
        if (in_workspace && strncmp(line, "members", 7) == 0) {
            char* eq_pos = strchr(line, '=');
            if (eq_pos) {
                char* value_part = eq_pos + 1;
                trim_string(value_part);
                
                // Find array content between [ and ]
                char* bracket_start = strchr(value_part, '[');
                char* bracket_end = strrchr(value_part, ']');
                
                if (bracket_start && bracket_end && bracket_end > bracket_start) {
                    // Extract content between brackets
                    int content_len = bracket_end - bracket_start - 1;
                    char* content = (char*)malloc(content_len + 1);
                    if (content) {
                        memcpy(content, bracket_start + 1, content_len);
                        content[content_len] = '\0';
                        
                        // Parse quoted strings
                        const char* pos = content;
                        while (*pos && json_pos < result_cap - 10) {
                            skip_whitespace(&pos);
                            if (*pos == '"') {
                                pos++; // Skip opening quote
                                const char* str_start = pos;
                                while (*pos && *pos != '"') {
                                    pos++;
                                }
                                if (*pos == '"') {
                                    int str_len = pos - str_start;
                                    
                                    // Add comma if not first
                                    if (!first) {
                                        if (json_pos < result_cap - 1) {
                                            result[json_pos++] = ',';
                                        }
                                    }
                                    first = 0;
                                    
                                    // Add quoted string to JSON
                                    if (json_pos + str_len + 5 < result_cap - 1) {
                                        result[json_pos++] = '"';
                                        memcpy(result + json_pos, str_start, str_len);
                                        json_pos += str_len;
                                        result[json_pos++] = '"';
                                    }
                                    
                                    pos++; // Skip closing quote
                                }
                            } else {
                                pos++;
                            }
                            skip_whitespace(&pos);
                            if (*pos == ',') pos++;
                        }
                        
                        free(content);
                    }
                }
            }
            free(line);
            line_start = line_end;
            if (*line_start == '\r') line_start++;
            if (*line_start == '\n') line_start++;
            continue;
        }
        
        // Check for next section (stops parsing)
        if (line[0] == '[') {
            free(line);
            break;
        }
        
        free(line);
        line_start = line_end;
        if (*line_start == '\r') line_start++;
        if (*line_start == '\n') line_start++;
    }
    
    // Close JSON array
    if (json_pos < result_cap - 1) {
        result[json_pos++] = ']';
    }
    result[json_pos] = '\0';
    
    if (result_len) *result_len = json_pos;
    free(text);
    return 0;
}
