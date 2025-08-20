#!/usr/bin/env node

/**
 * TaskMaster AI with Google Gemini MCP Server
 * A Model Context Protocol server for task management using Google Gemini API
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { GoogleGenerativeAI } from '@google/generative-ai';

class TaskMasterMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'taskmaster-gemini-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Initialize Google Gemini
    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey) {
      throw new Error('GOOGLE_API_KEY environment variable is required');
    }

    this.genAI = new GoogleGenerativeAI(apiKey);
    this.model = this.genAI.getGenerativeModel({ model: 'gemini-2.5-pro' });

    // Task storage
    this.tasks = new Map();
    this.projects = new Map();
    this.taskIdCounter = 1;
    this.projectIdCounter = 1;

    this.setupToolHandlers();
  }

  setupToolHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'query_gemini',
            description: 'Send a query to Google Gemini model',
            inputSchema: {
              type: 'object',
              properties: {
                prompt: {
                  type: 'string',
                  description: 'The prompt to send to Gemini',
                },
                model: {
                  type: 'string',
                  description: 'Gemini model to use (default: gemini-2.5-pro)',
                  default: 'gemini-2.5-pro',
                },
                max_tokens: {
                  type: 'number',
                  description: 'Maximum tokens to generate',
                  default: 1000,
                },
                temperature: {
                  type: 'number',
                  description: 'Temperature for response generation (0.0-1.0)',
                  default: 0.2,
                },
              },
              required: ['prompt'],
            },
          },
          {
            name: 'analyze_code',
            description: 'Analyze code using Gemini',
            inputSchema: {
              type: 'object',
              properties: {
                code: {
                  type: 'string',
                  description: 'Code to analyze',
                },
                language: {
                  type: 'string',
                  description: 'Programming language',
                },
                task: {
                  type: 'string',
                  description: 'Analysis task (review, optimize, debug, etc.)',
                  default: 'review',
                },
              },
              required: ['code'],
            },
          },
          {
            name: 'generate_project_plan',
            description: 'Generate a project plan using Gemini',
            inputSchema: {
              type: 'object',
              properties: {
                project_description: {
                  type: 'string',
                  description: 'Description of the project',
                },
                requirements: {
                  type: 'array',
                  items: { type: 'string' },
                  description: 'List of project requirements',
                },
                technology_stack: {
                  type: 'string',
                  description: 'Technology stack to use',
                },
              },
              required: ['project_description'],
            },
          },
        ],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'query_gemini':
            return await this.queryGemini(args);
          case 'analyze_code':
            return await this.analyzeCode(args);
          case 'generate_project_plan':
            return await this.generateProjectPlan(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  async queryGemini(args) {
    const { prompt, model = 'gemini-2.5-pro', max_tokens = 1000, temperature = 0.2 } = args;

    try {
      const response = await this.callGeminiAPI(prompt, {
        model,
        max_tokens,
        temperature,
      });

      return {
        content: [
          {
            type: 'text',
            text: response,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Gemini API error: ${error.message}`);
    }
  }

  async analyzeCode(args) {
    const { code, language = 'unknown', task = 'review' } = args;

    const prompt = `
Please ${task} the following ${language} code:

\`\`\`${language}
${code}
\`\`\`

Provide:
1. Code quality assessment
2. Potential issues or bugs
3. Optimization suggestions
4. Best practices recommendations
`;

    return await this.queryGemini({ prompt });
  }

  async generateProjectPlan(args) {
    const { project_description, requirements = [], technology_stack = 'Not specified' } = args;

    const prompt = `
Create a detailed project plan for the following project:

**Project Description**: ${project_description}

**Technology Stack**: ${technology_stack}

**Requirements**:
${requirements.map(req => `- ${req}`).join('\n')}

Please provide:
1. Project overview and goals
2. Detailed task breakdown
3. Implementation phases
4. Timeline estimation
5. Risk assessment
6. Resource requirements
7. Success metrics
`;

    return await this.queryGemini({ prompt });
  }

  async callGeminiAPI(prompt, options = {}) {
    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey) {
      throw new Error('GOOGLE_API_KEY environment variable is not set');
    }

    const { model = 'gemini-2.5-pro', temperature = 0.2, max_tokens = 1000 } = options;

    // This is a simplified implementation
    // In a real implementation, you would use the Google AI SDK
    const mockResponse = `
[Gemini Response]
Model: ${model}
Temperature: ${temperature}
Max Tokens: ${max_tokens}

Your prompt: "${prompt}"

Note: This is a mock response. To use the actual Gemini API, you need to:
1. Install @google-ai/generativelanguage package
2. Implement proper API calls
3. Handle authentication properly

Your API key is configured: ${apiKey.substring(0, 10)}...
Your project: ${process.env.GOOGLE_VERTEX_PROJECT || 'Not set'}
`;

    return mockResponse;
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Google Gemini MCP server running on stdio');
  }
}

// Run the server
const server = new GeminiMCPServer();
server.run().catch(console.error);
