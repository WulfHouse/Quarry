/* Path operations implementation in C for Pyrite standard library */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#else
#include <sys/stat.h>
#include <unistd.h>
#endif

/* String structure (from string.c) */
typedef struct {
    char* data;
    int64_t len;
} String;

extern String string_new(const char* cstr);
extern String string_empty();

/* Join two paths - cross-platform */
String path_join(const char* base, const char* other) {
    char result[1024];
    
#ifdef _WIN32
    /* Windows: use backslash */
    if (base[strlen(base) - 1] == '\\' || base[strlen(base) - 1] == '/') {
        snprintf(result, sizeof(result), "%s%s", base, other);
    } else {
        snprintf(result, sizeof(result), "%s\\%s", base, other);
    }
#else
    /* Unix: use forward slash */
    if (base[strlen(base) - 1] == '/') {
        snprintf(result, sizeof(result), "%s%s", base, other);
    } else {
        snprintf(result, sizeof(result), "%s/%s", base, other);
    }
#endif
    
    return string_new(result);
}

/* Get parent directory - returns NULL if no parent */
String path_parent(const char* path) {
    if (!path || strlen(path) == 0) {
        return string_empty();
    }
    
    char result[1024];
    strncpy(result, path, sizeof(result) - 1);
    result[sizeof(result) - 1] = '\0';
    
    /* Find last separator */
    char* last_sep = NULL;
#ifdef _WIN32
    last_sep = strrchr(result, '\\');
    if (!last_sep) {
        last_sep = strrchr(result, '/');
    }
#else
    last_sep = strrchr(result, '/');
#endif
    
    if (last_sep && last_sep != result) {
        *last_sep = '\0';
        return string_new(result);
    } else if (last_sep == result) {
        /* Root directory */
        result[1] = '\0';
        return string_new(result);
    } else {
        /* No separator - no parent */
        return string_empty();
    }
}

/* Get file name - returns NULL if no file name */
String path_file_name(const char* path) {
    if (!path || strlen(path) == 0) {
        return string_empty();
    }
    
    /* Find last separator */
    const char* last_sep = NULL;
#ifdef _WIN32
    last_sep = strrchr(path, '\\');
    if (!last_sep) {
        last_sep = strrchr(path, '/');
    }
#else
    last_sep = strrchr(path, '/');
#endif
    
    if (last_sep) {
        return string_new(last_sep + 1);
    } else {
        return string_new(path);
    }
}

/* Check if path exists */
int path_exists(const char* path) {
    if (!path) {
        return 0;
    }
    
#ifdef _WIN32
    DWORD dwAttrib = GetFileAttributes(path);
    return (dwAttrib != INVALID_FILE_ATTRIBUTES) ? 1 : 0;
#else
    struct stat st;
    return (stat(path, &st) == 0) ? 1 : 0;
#endif
}

/* Check if path is a file */
int path_is_file(const char* path) {
    if (!path) {
        return 0;
    }
    
#ifdef _WIN32
    DWORD dwAttrib = GetFileAttributes(path);
    if (dwAttrib == INVALID_FILE_ATTRIBUTES) {
        return 0;
    }
    return !(dwAttrib & FILE_ATTRIBUTE_DIRECTORY);
#else
    struct stat st;
    if (stat(path, &st) != 0) {
        return 0;
    }
    return S_ISREG(st.st_mode) ? 1 : 0;
#endif
}

/* Check if path is a directory */
int path_is_dir(const char* path) {
    if (!path) {
        return 0;
    }
    
#ifdef _WIN32
    DWORD dwAttrib = GetFileAttributes(path);
    if (dwAttrib == INVALID_FILE_ATTRIBUTES) {
        return 0;
    }
    return (dwAttrib & FILE_ATTRIBUTE_DIRECTORY) ? 1 : 0;
#else
    struct stat st;
    if (stat(path, &st) != 0) {
        return 0;
    }
    return S_ISDIR(st.st_mode) ? 1 : 0;
#endif
}
