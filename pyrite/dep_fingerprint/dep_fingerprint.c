/* Dependency normalization and fingerprinting - C implementation
 *
 * This provides dependency normalization and fingerprinting, called from Pyrite via FFI.
 * The logic matches the Python implementation for deterministic canonical forms.
 */

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#define MAX_STRING_LEN 1024
#define MAX_JSON_LEN 65536
#define MAX_DEPS 256

/* SHA-256 implementation (simplified, for deterministic hashing) */
/* Note: This is a basic implementation. For production, consider using OpenSSL. */

typedef struct {
    uint32_t h[8];
    uint64_t total_len;
    uint8_t buffer[64];
    size_t buffer_len;
} sha256_ctx;

static const uint32_t k[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f8, 0xc67178f2
};

#define ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
#define CH(x, y, z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x, y, z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x) (ROTR(x, 2) ^ ROTR(x, 13) ^ ROTR(x, 22))
#define EP1(x) (ROTR(x, 6) ^ ROTR(x, 11) ^ ROTR(x, 25))
#define SIG0(x) (ROTR(x, 7) ^ ROTR(x, 18) ^ ((x) >> 3))
#define SIG1(x) (ROTR(x, 17) ^ ROTR(x, 19) ^ ((x) >> 10))

static void sha256_init(sha256_ctx* ctx) {
    ctx->h[0] = 0x6a09e667;
    ctx->h[1] = 0xbb67ae85;
    ctx->h[2] = 0x3c6ef372;
    ctx->h[3] = 0xa54ff53a;
    ctx->h[4] = 0x510e527f;
    ctx->h[5] = 0x9b05688c;
    ctx->h[6] = 0x1f83d9ab;
    ctx->h[7] = 0x5be0cd19;
    ctx->total_len = 0;
    ctx->buffer_len = 0;
}

static void sha256_transform(sha256_ctx* ctx, const uint8_t* data) {
    uint32_t w[64];
    uint32_t a, b, c, d, e, f, g, h;
    int i;
    
    for (i = 0; i < 16; i++) {
        w[i] = ((uint32_t)data[i * 4] << 24) | ((uint32_t)data[i * 4 + 1] << 16) |
               ((uint32_t)data[i * 4 + 2] << 8) | (uint32_t)data[i * 4 + 3];
    }
    
    for (i = 16; i < 64; i++) {
        w[i] = SIG1(w[i - 2]) + w[i - 7] + SIG0(w[i - 15]) + w[i - 16];
    }
    
    a = ctx->h[0]; b = ctx->h[1]; c = ctx->h[2]; d = ctx->h[3];
    e = ctx->h[4]; f = ctx->h[5]; g = ctx->h[6]; h = ctx->h[7];
    
    for (i = 0; i < 64; i++) {
        uint32_t t1 = h + EP1(e) + CH(e, f, g) + k[i] + w[i];
        uint32_t t2 = EP0(a) + MAJ(a, b, c);
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }
    
    ctx->h[0] += a; ctx->h[1] += b; ctx->h[2] += c; ctx->h[3] += d;
    ctx->h[4] += e; ctx->h[5] += f; ctx->h[6] += g; ctx->h[7] += h;
}

static void sha256_update(sha256_ctx* ctx, const uint8_t* data, size_t len) {
    ctx->total_len += len;
    
    while (len > 0) {
        size_t to_copy = 64 - ctx->buffer_len;
        if (to_copy > len) to_copy = len;
        
        memcpy(ctx->buffer + ctx->buffer_len, data, to_copy);
        ctx->buffer_len += to_copy;
        data += to_copy;
        len -= to_copy;
        
        if (ctx->buffer_len == 64) {
            sha256_transform(ctx, ctx->buffer);
            ctx->buffer_len = 0;
        }
    }
}

static void sha256_final(sha256_ctx* ctx, uint8_t* hash) {
    uint64_t bit_len = ctx->total_len * 8;
    int i;
    
    ctx->buffer[ctx->buffer_len++] = 0x80;
    
    if (ctx->buffer_len > 56) {
        while (ctx->buffer_len < 64) {
            ctx->buffer[ctx->buffer_len++] = 0;
        }
        sha256_transform(ctx, ctx->buffer);
        ctx->buffer_len = 0;
    }
    
    while (ctx->buffer_len < 56) {
        ctx->buffer[ctx->buffer_len++] = 0;
    }
    
    for (i = 7; i >= 0; i--) {
        ctx->buffer[ctx->buffer_len++] = (bit_len >> (i * 8)) & 0xff;
    }
    
    sha256_transform(ctx, ctx->buffer);
    
    for (i = 0; i < 8; i++) {
        hash[i * 4] = (ctx->h[i] >> 24) & 0xff;
        hash[i * 4 + 1] = (ctx->h[i] >> 16) & 0xff;
        hash[i * 4 + 2] = (ctx->h[i] >> 8) & 0xff;
        hash[i * 4 + 3] = ctx->h[i] & 0xff;
    }
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

/* Compare dependency names for sorting */
static int compare_deps(const void* a, const void* b) {
    const DepEntry* dep_a = (const DepEntry*)a;
    const DepEntry* dep_b = (const DepEntry*)b;
    return strcmp(dep_a->name, dep_b->name);
}

/* Normalize dependency source (lowercase type, normalize values) */
static void normalize_dep_entry(DepEntry* dep) {
    // Normalize type to lowercase
    for (int i = 0; dep->type[i]; i++) {
        if (dep->type[i] >= 'A' && dep->type[i] <= 'Z') {
            dep->type[i] = dep->type[i] - 'A' + 'a';
        }
    }
    
    // Normalize checksum/hash format (ensure lowercase hex)
    if (dep->checksum[0]) {
        // Check if starts with "sha256:"
        if (strncmp(dep->checksum, "sha256:", 7) == 0) {
            // Lowercase hex part
            for (int i = 7; dep->checksum[i]; i++) {
                if (dep->checksum[i] >= 'A' && dep->checksum[i] <= 'F') {
                    dep->checksum[i] = dep->checksum[i] - 'A' + 'a';
                }
            }
        }
    }
    
    if (dep->hash[0]) {
        // Check if starts with "sha256:"
        if (strncmp(dep->hash, "sha256:", 7) == 0) {
            // Lowercase hex part
            for (int i = 7; dep->hash[i]; i++) {
                if (dep->hash[i] >= 'A' && dep->hash[i] <= 'F') {
                    dep->hash[i] = dep->hash[i] - 'A' + 'a';
                }
            }
        }
    }
}

/* Serialize dependency to canonical JSON (deterministic field order) */
static int serialize_dep_json(const DepEntry* dep, char* result, int max_len) {
    int pos = 0;
    
    pos += snprintf(result + pos, max_len - pos, "{\"type\":\"%s\"", dep->type);
    
    if (strcmp(dep->type, "registry") == 0) {
        if (dep->version[0]) {
            pos += snprintf(result + pos, max_len - pos, ",\"version\":\"%s\"", dep->version);
        }
        if (dep->checksum[0]) {
            pos += snprintf(result + pos, max_len - pos, ",\"checksum\":\"%s\"", dep->checksum);
        }
    } else if (strcmp(dep->type, "git") == 0) {
        if (dep->git_url[0]) {
            pos += snprintf(result + pos, max_len - pos, ",\"git_url\":\"%s\"", dep->git_url);
        }
        if (dep->git_branch[0]) {
            pos += snprintf(result + pos, max_len - pos, ",\"git_branch\":\"%s\"", dep->git_branch);
        }
        if (dep->commit[0]) {
            pos += snprintf(result + pos, max_len - pos, ",\"commit\":\"%s\"", dep->commit);
        }
    } else if (strcmp(dep->type, "path") == 0) {
        if (dep->path[0]) {
            pos += snprintf(result + pos, max_len - pos, ",\"path\":\"%s\"", dep->path);
        }
        if (dep->hash[0]) {
            pos += snprintf(result + pos, max_len - pos, ",\"hash\":\"%s\"", dep->hash);
        }
    }
    
    pos += snprintf(result + pos, max_len - pos, "}");
    
    return pos;
}

/* Normalize dependency set (sort and canonicalize) */
int32_t normalize_dependency_set_c(const uint8_t* deps_json, int64_t json_len,
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
    
    // Normalize each dependency
    for (int i = 0; i < dep_count; i++) {
        normalize_dep_entry(&deps[i]);
    }
    
    // Sort by name (deterministic ordering)
    qsort(deps, dep_count, sizeof(DepEntry), compare_deps);
    
    // Serialize to canonical JSON
    int json_pos = 0;
    json_pos += snprintf((char*)result + json_pos, result_cap - json_pos, "{");
    
    for (int i = 0; i < dep_count && json_pos < result_cap - 200; i++) {
        if (i > 0) {
            json_pos += snprintf((char*)result + json_pos, result_cap - json_pos, ",");
        }
        
        // Serialize dependency name
        json_pos += snprintf((char*)result + json_pos, result_cap - json_pos, "\"%s\":", deps[i].name);
        
        // Serialize dependency object
        char dep_json[2048];
        int dep_json_len = serialize_dep_json(&deps[i], dep_json, sizeof(dep_json));
        if (json_pos + dep_json_len < result_cap) {
            memcpy(result + json_pos, dep_json, dep_json_len);
            json_pos += dep_json_len;
        }
    }
    
    json_pos += snprintf((char*)result + json_pos, result_cap - json_pos, "}");
    
    *result_len = json_pos;
    free(json_str);
    return 0;
}

/* Compute resolution fingerprint */
int32_t compute_resolution_fingerprint_c(const uint8_t* deps_json, int64_t json_len,
                                          uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!deps_json || !result || result_cap < 65 || !result_len) {
        return -1;
    }
    
    // First normalize the dependency set
    char normalized_json[MAX_JSON_LEN];
    int64_t normalized_len = 0;
    
    int32_t norm_ret = normalize_dependency_set_c(deps_json, json_len,
                                                   (uint8_t*)normalized_json, MAX_JSON_LEN,
                                                   &normalized_len);
    if (norm_ret != 0) {
        return -1;
    }
    
    // Compute SHA-256 hash of normalized JSON
    sha256_ctx ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, (uint8_t*)normalized_json, normalized_len);
    
    uint8_t hash[32];
    sha256_final(&ctx, hash);
    
    // Convert to hex string
    const char* hex_chars = "0123456789abcdef";
    for (int i = 0; i < 32 && i * 2 + 1 < result_cap; i++) {
        result[i * 2] = hex_chars[(hash[i] >> 4) & 0xf];
        result[i * 2 + 1] = hex_chars[hash[i] & 0xf];
    }
    
    *result_len = 64; // SHA-256 produces 64 hex characters
    return 0;
}

/* Normalize a single dependency source */
int32_t normalize_dependency_source_c(const uint8_t* dep_json, int64_t json_len,
                                       uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!dep_json || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    // Wrap in a dependency set for parsing
    char wrapped_json[MAX_JSON_LEN];
    int wrapped_len = snprintf(wrapped_json, sizeof(wrapped_json), "{\"temp\":%.*s}", (int)json_len, dep_json);
    
    DepEntry deps[1];
    int dep_count = parse_deps_json(wrapped_json, deps, 1);
    if (dep_count != 1) {
        return -1;
    }
    
    // Normalize
    normalize_dep_entry(&deps[0]);
    
    // Serialize back
    int json_pos = serialize_dep_json(&deps[0], (char*)result, result_cap);
    *result_len = json_pos;
    
    return 0;
}
