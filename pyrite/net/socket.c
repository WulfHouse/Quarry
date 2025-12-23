/* TCP implementation in C for Pyrite */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>
#include <errno.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#endif

typedef struct {
    char* data;
    int64_t len;
} String;

extern String string_new(const char* cstr);

int32_t net_init() {
#ifdef _WIN32
    WSADATA wsaData;
    return WSAStartup(MAKEWORD(2, 2), &wsaData);
#else
    return 0;
#endif
}

int64_t tcp_connect(const char* address, int32_t port) {
    int64_t sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return -1;
    
    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(port);
    
    if (inet_pton(AF_INET, address, &serv_addr.sin_addr) <= 0) {
#ifdef _WIN32
        closesocket(sock);
#else
        close(sock);
#endif
        return -1;
    }
    
    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
#ifdef _WIN32
        closesocket(sock);
#else
        close(sock);
#endif
        return -1;
    }
    
    return sock;
}

/**
 * Sends data over a TCP socket with proper error handling and partial send support.
 * 
 * This function safely handles send operations with the following constraints:
 * - Validates that len is non-negative and <= INT32_MAX
 * - Rejects requests for len > INT32_MAX with EINVAL (since return type is int32_t)
 * - Handles partial sends by looping until all data is sent
 * - Retries on EINTR (interrupted system call)
 * - Returns the total number of bytes sent, or -1 on error
 * 
 * Note: We limit the maximum send size to INT32_MAX bytes to ensure the return
 * value accurately reflects the number of bytes sent without truncation. For larger
 * transfers, callers should split the data into multiple calls.
 * 
 * Behavior:
 * - len < 0: Returns -1 and sets errno/WSASetLastError to EINVAL
 * - len == 0: Returns 0 (no-op)
 * - len > INT32_MAX: Returns -1 and sets errno/WSASetLastError to EINVAL
 * - 0 < len <= INT32_MAX: Performs send() until all data is sent, handling partial sends
 * 
 * On error after partial send, returns -1. The caller cannot determine how much was sent.
 * 
 * @param sock The socket file descriptor
 * @param data Pointer to the data buffer to send
 * @param len Number of bytes to send (must be 0 <= len <= INT32_MAX)
 * @return Total number of bytes sent on success, or -1 on error
 */
int32_t tcp_send(int64_t sock, const char* data, int64_t len) {
    // Validate input: len must be non-negative
    if (len < 0) {
#ifdef _WIN32
        WSASetLastError(WSAEINVAL);
#else
        errno = EINVAL;
#endif
        return -1;
    }
    
    // Validate input: len must not exceed INT32_MAX to prevent truncation
    if (len > (int64_t)INT32_MAX) {
#ifdef _WIN32
        WSASetLastError(WSAEINVAL);
#else
        errno = EINVAL;
#endif
        return -1;
    }
    
    // Handle zero-length send (not an error, just a no-op)
    if (len == 0) {
        return 0;
    }
    
    // Validate that data pointer is not NULL
    if (data == NULL) {
#ifdef _WIN32
        WSASetLastError(WSAEINVAL);
#else
        errno = EINVAL;
#endif
        return -1;
    }
    
    // Cast is safe here because we validated len <= INT32_MAX
    int32_t total_sent = 0;
    const char* current_data = data;
    int32_t remaining = (int32_t)len;
    
    // Loop until all data is sent, handling partial sends
    while (remaining > 0) {
        int sent;
        
#ifdef _WIN32
        sent = send((SOCKET)sock, current_data, remaining, 0);
        if (sent == SOCKET_ERROR) {
            int error = WSAGetLastError();
            // On Windows, WSAEINTR is not typically returned by send,
            // but we handle it for completeness
            if (error == WSAEINTR) {
                continue;  // Retry on interrupt
            }
            // Other errors: return -1 (partial send may have occurred)
            return -1;
        }
#else
        sent = send((int)sock, current_data, (size_t)remaining, 0);
        if (sent < 0) {
            // Retry on EINTR (interrupted system call)
            if (errno == EINTR) {
                continue;  // Retry the send
            }
            // Other errors: return -1 (partial send may have occurred)
            return -1;
        }
#endif
        
        // Update progress: advance buffer and reduce remaining
        total_sent += sent;
        current_data += sent;
        remaining -= sent;
    }
    
    // Return total bytes sent (guaranteed to equal len on success)
    return total_sent;
}

/**
 * Receives data from a TCP socket with proper error handling.
 * 
 * This function safely handles receive operations with the following constraints:
 * - Validates that len is non-negative and <= INT32_MAX
 * - Rejects requests for len > INT32_MAX with EINVAL (since return type is int32_t)
 * - Returns the actual number of bytes received (may be less than len)
 * - Returns 0 on EOF (connection closed by peer)
 * - Returns -1 on error (errno/WSAGetLastError set by the system)
 * 
 * Note: Unlike send operations which can be chunked transparently, receive operations
 * cannot be safely chunked because we don't know how much data is available. Therefore,
 * we limit the maximum receive size to INT32_MAX bytes to ensure the return value
 * accurately reflects the number of bytes received without truncation.
 * 
 * Behavior:
 * - len < 0: Returns -1 and sets errno/WSASetLastError to EINVAL
 * - len == 0: Returns 0 (no-op)
 * - len > INT32_MAX: Returns -1 and sets errno/WSASetLastError to EINVAL
 * - 0 < len <= INT32_MAX: Performs recv() and returns actual bytes received
 * 
 * @param sock The socket file descriptor
 * @param buf Pointer to the buffer where received data will be stored
 * @param len Maximum number of bytes to receive (must be 0 <= len <= INT32_MAX)
 * @return Number of bytes received (0 to INT32_MAX), 0 on EOF, or -1 on error
 */
int32_t tcp_recv(int64_t sock, char* buf, int64_t len) {
    // Validate input: len must be non-negative
    if (len < 0) {
#ifdef _WIN32
        WSASetLastError(WSAEINVAL);
#else
        errno = EINVAL;
#endif
        return -1;
    }
    
    // Validate input: len must not exceed INT32_MAX to prevent truncation
    if (len > (int64_t)INT32_MAX) {
#ifdef _WIN32
        WSASetLastError(WSAEINVAL);
#else
        errno = EINVAL;
#endif
        return -1;
    }
    
    // Handle zero-length receive (not an error, just a no-op)
    if (len == 0) {
        return 0;
    }
    
    // Validate that buffer pointer is not NULL
    if (buf == NULL) {
#ifdef _WIN32
        WSASetLastError(WSAEINVAL);
#else
        errno = EINVAL;
#endif
        return -1;
    }
    
    // Perform the receive operation
    // Cast is safe here because we validated len <= INT32_MAX
    int recv_len = (int)len;
    
#ifdef _WIN32
    int result = recv((SOCKET)sock, buf, recv_len, 0);
    if (result == SOCKET_ERROR) {
        // Error occurred - WSAGetLastError is already set by recv
        return -1;
    }
#else
    int result = recv((int)sock, buf, (size_t)recv_len, 0);
    if (result < 0) {
        // Error occurred - errno is already set by recv
        return -1;
    }
#endif
    
    // Return actual bytes received (0 indicates EOF, > 0 indicates data received)
    return (int32_t)result;
}

void tcp_close(int64_t sock) {
#ifdef _WIN32
    closesocket(sock);
#else
    close(sock);
#endif
}

