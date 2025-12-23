/* TCP implementation in C for Pyrite */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

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
        return -1;
    }
    
    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        return -1;
    }
    
    return sock;
}

int32_t tcp_send(int64_t sock, const char* data, int64_t len) {
    return send(sock, data, (int)len, 0);
}

int32_t tcp_recv(int64_t sock, char* buf, int64_t len) {
    return recv(sock, buf, (int)len, 0);
}

void tcp_close(int64_t sock) {
#ifdef _WIN32
    closesocket(sock);
#else
    close(sock);
#endif
}

