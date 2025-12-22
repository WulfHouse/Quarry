/* File I/O implementation in C for Pyrite standard library */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <dirent.h>
#include <sys/stat.h>
#endif

/* String structure (from string.c) */
typedef struct {
    char* data;
    int64_t len;
} String;

extern String string_new(const char* cstr);
extern void string_drop(String* s);

/* Result type for file operations */
typedef struct {
    int is_ok;      /* 1 for Ok, 0 for Err */
    union {
        String value;    /* For Ok */
        String error;    /* For Err */
    } data;
} FileResult;

/* Read entire file to string - returns String directly, NULL on error */
/* For MVP: return String directly, caller checks for empty string on error */
String file_read_to_string(const char* path) {
    FILE* file = fopen(path, "r");
    if (!file) {
        /* Return empty string on error (caller should check) */
        return string_empty();
    }
    
    /* Get file size */
    fseek(file, 0, SEEK_END);
    long size = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    if (size < 0) {
        fclose(file);
        return string_empty();
    }
    
    /* Read file */
    char* buffer = malloc(size + 1);
    size_t read = fread(buffer, 1, size, file);
    buffer[read] = '\0';
    fclose(file);
    
    String result = string_new(buffer);
    free(buffer);
    
    return result;
}

/* Check if file read was successful (non-empty string) */
/* For MVP: simple check - in real implementation, use proper error handling */
int file_read_success(String* s) {
    return s->len > 0;
}

/* Write string to file - returns 1 on success, 0 on error */
/* For MVP: simple return code */
int file_write(const char* path, const char* data, int64_t len) {
    FILE* file = fopen(path, "w");
    if (!file) {
        return 0;  /* Error */
    }
    
    size_t written = fwrite(data, 1, len, file);
    fclose(file);
    
    /* Return 1 on success, 0 on error */
    return (written == len) ? 1 : 0;
}

/* Check if file exists */
int file_exists(const char* path) {
    FILE* file = fopen(path, "r");
    if (file) {
        fclose(file);
        return 1;
    }
    return 0;
}

/* File handle operations */
/* For MVP: use FILE* as opaque pointer (void*) */

/* Open file and return handle (opaque pointer) */
void* file_open(const char* path, const char* mode) {
    FILE* file = fopen(path, mode);
    return (void*)file;  /* Return NULL on error */
}

/* Read line from file handle */
/* Returns String, empty string on EOF or error */
String file_read_line(void* handle) {
    FILE* file = (FILE*)handle;
    if (!file) {
        return string_empty();
    }
    
    /* Simple line reading - read up to newline or EOF */
    char buffer[4096];  /* Max line length for MVP */
    int pos = 0;
    int c;
    
    while (pos < sizeof(buffer) - 1) {
        c = fgetc(file);
        if (c == EOF) {
            break;
        }
        if (c == '\n') {
            buffer[pos++] = '\n';
            break;
        }
        buffer[pos++] = (char)c;
    }
    
    buffer[pos] = '\0';
    
    if (pos == 0 && c == EOF) {
        /* EOF reached */
        return string_empty();
    }
    
    return string_new(buffer);
}

/* Write bytes to file handle */
int file_write_bytes(void* handle, const char* data, int64_t len) {
    FILE* file = (FILE*)handle;
    if (!file) {
        return 0;
    }
    
    size_t written = fwrite(data, 1, len, file);
    return (written == len) ? 1 : 0;
}

/* Close file handle */
void file_close(void* handle) {
    FILE* file = (FILE*)handle;
    if (file) {
        fclose(file);
    }
}

/* Directory entry structure */
typedef struct {
    char* name;
    int is_dir;
} DirEntry;

/* Directory listing structure */
typedef struct {
    DirEntry* entries;
    int count;
    int capacity;
} DirListing;

/* Read directory - returns list of file/directory names */
/* For MVP, simplified implementation */
DirListing file_read_dir(const char* path) {
    DirListing listing;
    listing.count = 0;
    listing.capacity = 16;
    listing.entries = malloc(sizeof(DirEntry) * listing.capacity);
    
#ifdef _WIN32
    /* Windows implementation */
    char search_path[1024];
    snprintf(search_path, sizeof(search_path), "%s\\*", path);
    
    WIN32_FIND_DATA find_data;
    HANDLE find_handle = FindFirstFile(search_path, &find_data);
    
    if (find_handle != INVALID_HANDLE_VALUE) {
        do {
            /* Skip . and .. */
            if (strcmp(find_data.cFileName, ".") == 0 || 
                strcmp(find_data.cFileName, "..") == 0) {
                continue;
            }
            
            /* Grow if needed */
            if (listing.count >= listing.capacity) {
                listing.capacity *= 2;
                listing.entries = realloc(listing.entries, sizeof(DirEntry) * listing.capacity);
            }
            
            /* Add entry */
            listing.entries[listing.count].name = malloc(strlen(find_data.cFileName) + 1);
            strcpy(listing.entries[listing.count].name, find_data.cFileName);
            listing.entries[listing.count].is_dir = (find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
            listing.count++;
        } while (FindNextFile(find_handle, &find_data));
        
        FindClose(find_handle);
    }
#else
    /* Unix/Linux implementation */
    DIR* dir = opendir(path);
    if (dir) {
        struct dirent* entry;
        while ((entry = readdir(dir)) != NULL) {
            /* Skip . and .. */
            if (strcmp(entry->d_name, ".") == 0 || 
                strcmp(entry->d_name, "..") == 0) {
                continue;
            }
            
            /* Grow if needed */
            if (listing.count >= listing.capacity) {
                listing.capacity *= 2;
                listing.entries = realloc(listing.entries, sizeof(DirEntry) * listing.capacity);
            }
            
            /* Add entry */
            listing.entries[listing.count].name = malloc(strlen(entry->d_name) + 1);
            strcpy(listing.entries[listing.count].name, entry->d_name);
            listing.entries[listing.count].is_dir = (entry->d_type == DT_DIR);
            listing.count++;
        }
        closedir(dir);
    }
#endif
    
    return listing;
}

/* Old free function kept for reference */
void file_read_dir_free_old(DirListing* listing) {
    for (int i = 0; i < listing->count; i++) {
        free(listing->entries[i].name);
    }
    free(listing->entries);
    listing->count = 0;
    listing->capacity = 0;
}

