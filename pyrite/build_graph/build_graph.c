/* Build graph algorithms - C implementation
 *
 * This provides the core logic for graph algorithms, called from Pyrite via FFI.
 * The logic matches the Python implementation in quarry/build_graph.py
 */

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#define MAX_NODES 256
#define MAX_DEPS_PER_NODE 64
#define MAX_STRING_LEN 256

/* Simple string structure for node names */
typedef struct {
    char data[MAX_STRING_LEN];
    int len;
} NodeString;

/* Graph structure */
typedef struct {
    NodeString nodes[MAX_NODES];
    NodeString deps[MAX_NODES][MAX_DEPS_PER_NODE];
    int dep_counts[MAX_NODES];
    int node_count;
} Graph;

/* Helper: Find node index by name */
int find_node_index(Graph* g, const char* name, int name_len) {
    for (int i = 0; i < g->node_count; i++) {
        if (g->nodes[i].len == name_len && 
            memcmp(g->nodes[i].data, name, name_len) == 0) {
            return i;
        }
    }
    return -1;
}

/* Helper: Add node if not exists, return index */
int get_or_add_node(Graph* g, const char* name, int name_len) {
    if (name_len >= MAX_STRING_LEN) return -1;
    
    int idx = find_node_index(g, name, name_len);
    if (idx >= 0) return idx;
    
    if (g->node_count >= MAX_NODES) return -1;
    
    idx = g->node_count++;
    memcpy(g->nodes[idx].data, name, name_len);
    g->nodes[idx].data[name_len] = '\0';
    g->nodes[idx].len = name_len;
    g->dep_counts[idx] = 0;
    return idx;
}

/* Helper: Add dependency */
void add_dependency(Graph* g, int node_idx, const char* dep_name, int dep_len) {
    if (node_idx < 0 || node_idx >= g->node_count) return;
    if (g->dep_counts[node_idx] >= MAX_DEPS_PER_NODE) return;
    if (dep_len >= MAX_STRING_LEN) return;
    
    int dep_idx = g->dep_counts[node_idx]++;
    memcpy(g->deps[node_idx][dep_idx].data, dep_name, dep_len);
    g->deps[node_idx][dep_idx].data[dep_len] = '\0';
    g->deps[node_idx][dep_idx].len = dep_len;
}

/* Parse JSON edges: {"node1": ["dep1", "dep2"], "node2": []} */
int parse_edges_json(const char* json_str, Graph* g) {
    g->node_count = 0;
    memset(g->dep_counts, 0, sizeof(g->dep_counts));
    
    const char* pos = json_str;
    
    // Skip opening brace
    while (*pos && (*pos == '{' || *pos == ' ' || *pos == '\t' || *pos == '\n')) pos++;
    
    while (*pos && *pos != '}') {
        // Skip whitespace and commas
        while (*pos && (*pos == ' ' || *pos == '\t' || *pos == ',' || *pos == '\n')) pos++;
        if (*pos == '}') break;
        
        // Parse node name (quoted string)
        if (*pos != '"') return -1;
        pos++; // Skip opening quote
        const char* node_start = pos;
        while (*pos && *pos != '"') pos++;
        if (*pos != '"') return -1;
        int node_len = pos - node_start;
        pos++; // Skip closing quote
        
        // Skip colon
        while (*pos && (*pos == ':' || *pos == ' ' || *pos == '\t')) pos++;
        
        // Get or add node
        char node_name[MAX_STRING_LEN];
        if (node_len >= MAX_STRING_LEN) return -1;
        memcpy(node_name, node_start, node_len);
        node_name[node_len] = '\0';
        int node_idx = get_or_add_node(g, node_name, node_len);
        if (node_idx < 0) return -1;
        
        // Parse dependencies array
        if (*pos == '[') {
            pos++; // Skip opening bracket
            while (*pos && *pos != ']') {
                // Skip whitespace and commas
                while (*pos && (*pos == ' ' || *pos == '\t' || *pos == ',' || *pos == '\n')) pos++;
                if (*pos == ']') break;
                
                // Parse dependency name (quoted string)
                if (*pos == '"') {
                    pos++; // Skip opening quote
                    const char* dep_start = pos;
                    while (*pos && *pos != '"') pos++;
                    if (*pos != '"') return -1;
                    int dep_len = pos - dep_start;
                    pos++; // Skip closing quote
                    
                    // Add dependency
                    char dep_name[MAX_STRING_LEN];
                    if (dep_len >= MAX_STRING_LEN) return -1;
                    memcpy(dep_name, dep_start, dep_len);
                    dep_name[dep_len] = '\0';
                    add_dependency(g, node_idx, dep_name, dep_len);
                } else {
                    pos++;
                }
            }
            if (*pos == ']') pos++; // Skip closing bracket
        } else {
            pos++; // Skip non-array value
        }
    }
    
    return 0;
}

/* Cycle detection using DFS */
bool has_cycle_dfs(Graph* g, int node_idx, bool* visited, bool* rec_stack) {
    if (rec_stack[node_idx]) {
        return true; // Cycle detected
    }
    if (visited[node_idx]) {
        return false; // Already processed
    }
    
    visited[node_idx] = true;
    rec_stack[node_idx] = true;
    
    // Check all dependencies
    for (int i = 0; i < g->dep_counts[node_idx]; i++) {
        const char* dep_name = g->deps[node_idx][i].data;
        int dep_idx = find_node_index(g, dep_name, g->deps[node_idx][i].len);
        if (dep_idx >= 0) {
            if (has_cycle_dfs(g, dep_idx, visited, rec_stack)) {
                return true;
            }
        }
    }
    
    rec_stack[node_idx] = false;
    return false;
}

/* Check if graph has cycles */
int32_t has_cycle_c(const uint8_t* edges_json, int64_t json_len, int32_t* result) {
    if (!edges_json || !result || json_len <= 0) {
        return -1;
    }
    
    // Convert to null-terminated string
    char* json_str = (char*)malloc(json_len + 1);
    if (!json_str) {
        return -1;
    }
    memcpy(json_str, edges_json, json_len);
    json_str[json_len] = '\0';
    
    // Parse graph
    Graph g;
    if (parse_edges_json(json_str, &g) != 0) {
        free(json_str);
        return -1;
    }
    
    // Initialize visited and recursion stack
    bool visited[MAX_NODES] = {false};
    bool rec_stack[MAX_NODES] = {false};
    
    // Check all nodes for cycles
    bool found_cycle = false;
    for (int i = 0; i < g.node_count; i++) {
        if (!visited[i]) {
            if (has_cycle_dfs(&g, i, visited, rec_stack)) {
                found_cycle = true;
                break;
            }
        }
    }
    
    *result = found_cycle ? 1 : 0;
    free(json_str);
    return 0;
}

/* Topological sort using Kahn's algorithm */
int32_t topological_sort_c(const uint8_t* edges_json, int64_t json_len,
                          uint8_t* result, int64_t result_cap, int64_t* result_len) {
    if (!edges_json || !result || result_cap < 2 || !result_len) {
        return -1;
    }
    
    // Convert to null-terminated string
    char* json_str = (char*)malloc(json_len + 1);
    if (!json_str) {
        return -1;
    }
    memcpy(json_str, edges_json, json_len);
    json_str[json_len] = '\0';
    
    // Parse graph
    Graph g;
    if (parse_edges_json(json_str, &g) != 0) {
        free(json_str);
        return -1;
    }
    
    // Check for cycles first
    bool visited[MAX_NODES] = {false};
    bool rec_stack[MAX_NODES] = {false};
    bool has_cycle = false;
    for (int i = 0; i < g.node_count; i++) {
        if (!visited[i]) {
            if (has_cycle_dfs(&g, i, visited, rec_stack)) {
                has_cycle = true;
                break;
            }
        }
    }
    
    if (has_cycle) {
        free(json_str);
        return -1; // Cycle detected
    }
    
    // Kahn's algorithm: build in-degree map
    int in_degree[MAX_NODES] = {0};
    for (int i = 0; i < g.node_count; i++) {
        in_degree[i] = g.dep_counts[i];
    }
    
    // Build reverse edges (which nodes depend on each node)
    int reverse_deps[MAX_NODES][MAX_NODES];
    int reverse_counts[MAX_NODES] = {0};
    for (int i = 0; i < g.node_count; i++) {
        for (int j = 0; j < g.dep_counts[i]; j++) {
            const char* dep_name = g.deps[i][j].data;
            int dep_idx = find_node_index(&g, dep_name, g.deps[i][j].len);
            if (dep_idx >= 0 && reverse_counts[dep_idx] < MAX_NODES) {
                reverse_deps[dep_idx][reverse_counts[dep_idx]++] = i;
            }
        }
    }
    
    // Start with nodes that have no dependencies (in-degree 0)
    int queue[MAX_NODES];
    int queue_start = 0;
    int queue_end = 0;
    for (int i = 0; i < g.node_count; i++) {
        if (in_degree[i] == 0) {
            queue[queue_end++] = i;
        }
    }
    
    // Build result order
    int result_order[MAX_NODES];
    int result_count = 0;
    
    while (queue_start < queue_end) {
        int current = queue[queue_start++];
        result_order[result_count++] = current;
        
        // For nodes that depend on current, reduce their in-degree
        for (int i = 0; i < reverse_counts[current]; i++) {
            int dependent = reverse_deps[current][i];
            in_degree[dependent]--;
            if (in_degree[dependent] == 0) {
                queue[queue_end++] = dependent;
            }
        }
    }
    
    // Check if all nodes were processed
    if (result_count != g.node_count) {
        free(json_str);
        return -1; // Should not happen if cycle check worked
    }
    
    // Build JSON array output
    int json_pos = 0;
    if (json_pos < result_cap - 1) {
        result[json_pos++] = '[';
    }
    
    for (int i = 0; i < result_count; i++) {
        if (i > 0 && json_pos < result_cap - 1) {
            result[json_pos++] = ',';
        }
        
        // Add quoted string
        const char* node_name = g.nodes[result_order[i]].data;
        int name_len = g.nodes[result_order[i]].len;
        if (json_pos + name_len + 5 < result_cap) {
            result[json_pos++] = '"';
            memcpy(result + json_pos, node_name, name_len);
            json_pos += name_len;
            result[json_pos++] = '"';
        } else {
            free(json_str);
            return -1; // Buffer too small
        }
    }
    
    // Close JSON array
    if (json_pos < result_cap - 1) {
        result[json_pos++] = ']';
    }
    result[json_pos] = '\0';
    *result_len = json_pos;
    
    free(json_str);
    return 0;
}
