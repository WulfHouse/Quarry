# Pyrite Language Support for VSCode

Official VSCode extension for the Pyrite programming language.

## Features

- **Syntax Highlighting** - Full syntax highlighting for Pyrite code
- **Language Server** - Intelligent code completion, hover information, and diagnostics
- **Go to Definition** - Jump to symbol definitions
- **Error Diagnostics** - Real-time error checking as you type
- **Auto-completion** - Context-aware code completion
- **Hover Information** - Type information and documentation on hover

## Installation

### From Marketplace (Coming Soon)

1. Open VSCode
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Pyrite"
4. Click Install

### From Source

1. Clone the Pyrite repository
2. Navigate to `vscode-pyrite/`
3. Run `npm install`
4. Run `npm run compile`
5. Press F5 to launch Extension Development Host

## Requirements

- Quarry installed (includes Forge, the Pyrite compiler)
- Python 3.10+ (for LSP server)

## Configuration

Configure the extension in VSCode settings:

```json
{
  "pyrite.lsp.enabled": true,
  "pyrite.lsp.path": "",  // Auto-detect by default
  "pyrite.lsp.trace.server": "off"  // or "messages" or "verbose" for debugging
}
```

## Usage

1. Create a `.pyrite` file
2. Start typing - syntax highlighting and LSP features activate automatically
3. Hover over variables to see type information
4. Use Ctrl+Click (Cmd+Click on macOS) to go to definitions
5. Press Ctrl+Space for auto-completion

## Example

```pyrite
fn main():
    let data = List[int]([1, 2, 3])
    
    for item in data:
        print(item)
```

## Troubleshooting

### LSP server not starting

- Check that Quarry is installed: `quarry --version` or `forge --version`
- Check LSP server location: `~/.pyrite/forge/lsp/pyrite-lsp.py`
- Enable verbose logging: Set `"pyrite.lsp.trace.server": "verbose"`
- Check Output panel: View → Output → Pyrite Language Server

### Syntax highlighting not working

- Ensure file has `.pyrite` extension
- Reload window: Ctrl+Shift+P → "Reload Window"

## Contributing

Report issues at: [https://github.com/WulfHouse/Quarry/issues](https://github.com/WulfHouse/Quarry/issues)

## License

WulfHouse Source-Available Non-Compete License (WSANCL) v1.0 - See [LICENSE.md](../LICENSE.md) for details
