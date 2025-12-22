import * as path from 'path';
import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
    console.log('Pyrite extension activated');

    // Check if LSP is enabled
    const config = vscode.workspace.getConfiguration('pyrite');
    if (!config.get('lsp.enabled', true)) {
        console.log('Pyrite LSP disabled by configuration');
        return;
    }

    // Find pyrite-lsp executable
    const lspPath = findLspServer();
    if (!lspPath) {
        vscode.window.showWarningMessage(
            'Pyrite LSP server not found. Please install Pyrite or configure pyrite.lsp.path'
        );
        return;
    }

    // Configure server options
    const serverOptions: ServerOptions = {
        command: 'python',
        args: [lspPath],
        transport: TransportKind.stdio
    };

    // Configure client options
    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'pyrite' }
        ],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.pyrite')
        }
    };

    // Create language client
    client = new LanguageClient(
        'pyrite-lsp',
        'Pyrite Language Server',
        serverOptions,
        clientOptions
    );

    // Start the client
    client.start();

    console.log('Pyrite LSP client started');
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}

function findLspServer(): string | null {
    // Check configuration first
    const config = vscode.workspace.getConfiguration('pyrite');
    const configPath = config.get<string>('lsp.path');
    if (configPath) {
        return configPath;
    }

    // Try to find in PATH
    const homeDir = process.env.HOME || process.env.USERPROFILE;
    if (!homeDir) {
        return null;
    }

    // Check common installation locations
    const candidates = [
        path.join(homeDir, '.pyrite', 'forge', 'lsp', 'pyrite-lsp.py'),
        path.join(homeDir, '.pyrite', 'lsp', 'pyrite-lsp.py'),
        '/usr/local/lib/pyrite/lsp/pyrite-lsp.py',
        'C:\\Program Files\\Pyrite\\lsp\\pyrite-lsp.py'
    ];

    for (const candidate of candidates) {
        try {
            const fs = require('fs');
            if (fs.existsSync(candidate)) {
                console.log(`Found LSP server at: ${candidate}`);
                return candidate;
            }
        } catch (e) {
            // Continue to next candidate
        }
    }

    console.log('LSP server not found in standard locations');
    return null;
}

