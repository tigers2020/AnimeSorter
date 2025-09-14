#!/usr/bin/env node

/**
 * Simple File-based Memory System
 * Quick memory storage without MCP complexity
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

class SimpleMemory {
    constructor() {
        this.memoryFile = path.join(os.homedir(), '.cursor-simple-memory.json');
        this.memories = this.load();
    }

    load() {
        try {
            if (fs.existsSync(this.memoryFile)) {
                return JSON.parse(fs.readFileSync(this.memoryFile, 'utf8'));
            }
        } catch (error) {
            console.error('Error loading memory:', error);
        }
        return {};
    }

    save() {
        try {
            fs.writeFileSync(this.memoryFile, JSON.stringify(this.memories, null, 2));
            return true;
        } catch (error) {
            console.error('Error saving memory:', error);
            return false;
        }
    }

    set(key, value, project = null) {
        this.memories[key] = {
            value,
            project: project || process.cwd(),
            timestamp: new Date().toISOString()
        };
        this.save();
        console.log(`Memory stored: ${key}`);
    }

    get(key) {
        const memory = this.memories[key];
        if (memory) {
            console.log(`Memory retrieved: ${key}`);
            console.log(`Value: ${memory.value}`);
            console.log(`Project: ${memory.project}`);
            console.log(`Timestamp: ${memory.timestamp}`);
            return memory;
        } else {
            console.log(`Memory not found: ${key}`);
            return null;
        }
    }

    list() {
        console.log('\n=== All Memories ===');
        for (const [key, memory] of Object.entries(this.memories)) {
            console.log(`\n${key}:`);
            console.log(`  Value: ${memory.value}`);
            console.log(`  Project: ${memory.project}`);
            console.log(`  Timestamp: ${memory.timestamp}`);
        }
    }

    search(query) {
        console.log(`\n=== Search Results for: "${query}" ===`);
        const results = [];
        const lowerQuery = query.toLowerCase();

        for (const [key, memory] of Object.entries(this.memories)) {
            if (key.toLowerCase().includes(lowerQuery) ||
                memory.value.toLowerCase().includes(lowerQuery)) {
                results.push({ key, ...memory });
            }
        }

        if (results.length === 0) {
            console.log('No matching memories found.');
        } else {
            results.forEach(memory => {
                console.log(`\n${memory.key}:`);
                console.log(`  Value: ${memory.value}`);
                console.log(`  Project: ${memory.project}`);
                console.log(`  Timestamp: ${memory.timestamp}`);
            });
        }

        return results;
    }

    delete(key) {
        if (this.memories[key]) {
            delete this.memories[key];
            this.save();
            console.log(`Memory deleted: ${key}`);
        } else {
            console.log(`Memory not found: ${key}`);
        }
    }
}

// CLI Interface
const memory = new SimpleMemory();
const command = process.argv[2];
const key = process.argv[3];
const value = process.argv.slice(4).join(' ');

switch (command) {
    case 'set':
        if (!key || !value) {
            console.log('Usage: node simple-memory.js set <key> <value>');
            break;
        }
        memory.set(key, value);
        break;

    case 'get':
        if (!key) {
            console.log('Usage: node simple-memory.js get <key>');
            break;
        }
        memory.get(key);
        break;

    case 'list':
        memory.list();
        break;

    case 'search':
        if (!key) {
            console.log('Usage: node simple-memory.js search <query>');
            break;
        }
        memory.search(key);
        break;

    case 'delete':
        if (!key) {
            console.log('Usage: node simple-memory.js delete <key>');
            break;
        }
        memory.delete(key);
        break;

    default:
        console.log(`
Simple Memory System Usage:
  node simple-memory.js set <key> <value>    - Store memory
  node simple-memory.js get <key>            - Retrieve memory
  node simple-memory.js list                 - List all memories
  node simple-memory.js search <query>       - Search memories
  node simple-memory.js delete <key>         - Delete memory

Examples:
  node simple-memory.js set "user_prefs" "dark theme, compact layout"
  node simple-memory.js get "user_prefs"
  node simple-memory.js search "theme"
  node simple-memory.js list
        `);
}
