#!/usr/bin/env node

/**
 * Simple Memory MCP Server
 * Stores and retrieves persistent memory for AI assistants
 */

const fs = require('fs');
const path = require('path');

class MemoryServer {
    constructor() {
        // Use user home directory for global memory across all projects
        const homeDir = require('os').homedir();
        this.memoryFile = path.join(homeDir, '.cursor-global-memory.json');
        this.memories = this.loadMemories();
    }

    loadMemories() {
        try {
            if (fs.existsSync(this.memoryFile)) {
                const data = fs.readFileSync(this.memoryFile, 'utf8');
                return JSON.parse(data);
            }
        } catch (error) {
            console.error('Error loading memories:', error);
        }
        return {};
    }

    saveMemories() {
        try {
            fs.writeFileSync(this.memoryFile, JSON.stringify(this.memories, null, 2));
            return true;
        } catch (error) {
            console.error('Error saving memories:', error);
            return false;
        }
    }

    storeMemory(key, value, metadata = {}) {
        const timestamp = new Date().toISOString();
        const currentProject = process.cwd();

        this.memories[key] = {
            value,
            metadata: {
                ...metadata,
                project: currentProject,
                projectName: path.basename(currentProject)
            },
            timestamp,
            accessCount: 0
        };
        this.saveMemories();
        return { success: true, key, timestamp, project: currentProject };
    }

    retrieveMemory(key) {
        if (this.memories[key]) {
            this.memories[key].accessCount++;
            this.memories[key].lastAccessed = new Date().toISOString();
            this.saveMemories();
            return this.memories[key];
        }
        return null;
    }

    searchMemories(query, projectFilter = null) {
        const results = [];
        const lowerQuery = query.toLowerCase();

        for (const [key, memory] of Object.entries(this.memories)) {
            // Apply project filter if specified
            if (projectFilter && memory.metadata?.project !== projectFilter) {
                continue;
            }

            if (key.toLowerCase().includes(lowerQuery) ||
                memory.value.toLowerCase().includes(lowerQuery)) {
                results.push({ key, ...memory });
            }
        }

        return results.sort((a, b) => b.accessCount - a.accessCount);
    }

    deleteMemory(key) {
        if (this.memories[key]) {
            delete this.memories[key];
            this.saveMemories();
            return { success: true, key };
        }
        return { success: false, key, error: 'Memory not found' };
    }

    listMemories(projectFilter = null) {
        const results = [];

        for (const [key, memory] of Object.entries(this.memories)) {
            // Apply project filter if specified
            if (projectFilter && memory.metadata?.project !== projectFilter) {
                continue;
            }

            results.push({
                key,
                timestamp: memory.timestamp,
                accessCount: memory.accessCount,
                project: memory.metadata?.project,
                projectName: memory.metadata?.projectName
            });
        }

        return results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }

    getMemoriesByProject(projectPath = null) {
        const currentProject = projectPath || process.cwd();
        return this.listMemories(currentProject);
    }

    getGlobalMemories() {
        return this.listMemories(); // No filter = all memories
    }
}

// MCP Server Implementation
const memoryServer = new MemoryServer();

// Handle MCP protocol messages
process.stdin.on('data', (data) => {
    try {
        const message = JSON.parse(data.toString());

        switch (message.method) {
            case 'tools/list':
                const response = {
                    jsonrpc: '2.0',
                    id: message.id,
                    result: {
                        tools: [
                            {
                                name: 'store_memory',
                                description: 'Store information in persistent memory',
                                inputSchema: {
                                    type: 'object',
                                    properties: {
                                        key: { type: 'string', description: 'Unique key for the memory' },
                                        value: { type: 'string', description: 'Information to store' },
                                        metadata: { type: 'object', description: 'Additional metadata' }
                                    },
                                    required: ['key', 'value']
                                }
                            },
                            {
                                name: 'retrieve_memory',
                                description: 'Retrieve information from persistent memory',
                                inputSchema: {
                                    type: 'object',
                                    properties: {
                                        key: { type: 'string', description: 'Key of the memory to retrieve' }
                                    },
                                    required: ['key']
                                }
                            },
                            {
                                name: 'search_memories',
                                description: 'Search through memories (optionally filter by current project)',
                                inputSchema: {
                                    type: 'object',
                                    properties: {
                                        query: { type: 'string', description: 'Search query' },
                                        projectOnly: { type: 'boolean', description: 'Search only current project memories' }
                                    },
                                    required: ['query']
                                }
                            },
                            {
                                name: 'delete_memory',
                                description: 'Delete a memory by key',
                                inputSchema: {
                                    type: 'object',
                                    properties: {
                                        key: { type: 'string', description: 'Key of the memory to delete' }
                                    },
                                    required: ['key']
                                }
                            },
                            {
                                name: 'list_memories',
                                description: 'List memory keys and metadata (optionally filter by current project)',
                                inputSchema: {
                                    type: 'object',
                                    properties: {
                                        projectOnly: { type: 'boolean', description: 'List only current project memories' }
                                    }
                                }
                            },
                            {
                                name: 'get_project_memories',
                                description: 'Get all memories for a specific project',
                                inputSchema: {
                                    type: 'object',
                                    properties: {
                                        projectPath: { type: 'string', description: 'Project path (optional, defaults to current)' }
                                    }
                                }
                            },
                            {
                                name: 'get_global_memories',
                                description: 'Get all memories across all projects',
                                inputSchema: {
                                    type: 'object',
                                    properties: {}
                                }
                            }
                        ]
                    }
                };
                console.log(JSON.stringify(response));
                break;

            case 'tools/call':
                const { name, arguments: args } = message.params;
                let result;

                switch (name) {
                    case 'store_memory':
                        result = memoryServer.storeMemory(args.key, args.value, args.metadata);
                        break;
                    case 'retrieve_memory':
                        result = memoryServer.retrieveMemory(args.key);
                        break;
                    case 'search_memories':
                        const projectFilter = args.projectOnly ? process.cwd() : null;
                        result = memoryServer.searchMemories(args.query, projectFilter);
                        break;
                    case 'delete_memory':
                        result = memoryServer.deleteMemory(args.key);
                        break;
                    case 'list_memories':
                        const listProjectFilter = args.projectOnly ? process.cwd() : null;
                        result = memoryServer.listMemories(listProjectFilter);
                        break;
                    case 'get_project_memories':
                        result = memoryServer.getMemoriesByProject(args.projectPath);
                        break;
                    case 'get_global_memories':
                        result = memoryServer.getGlobalMemories();
                        break;
                    default:
                        result = { error: 'Unknown tool' };
                }

                const toolResponse = {
                    jsonrpc: '2.0',
                    id: message.id,
                    result: { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] }
                };
                console.log(JSON.stringify(toolResponse));
                break;

            default:
                const errorResponse = {
                    jsonrpc: '2.0',
                    id: message.id,
                    error: { code: -32601, message: 'Method not found' }
                };
                console.log(JSON.stringify(errorResponse));
        }
    } catch (error) {
        const errorResponse = {
            jsonrpc: '2.0',
            id: null,
            error: { code: -32700, message: 'Parse error' }
        };
        console.log(JSON.stringify(errorResponse));
    }
});
