# MindMup2 Google Drive MCP Server

A Model Context Protocol (MCP) server that provides seamless integration between MindMup mind maps and Google Drive. This server enables you to search, retrieve, and parse MindMup files stored in your Google Drive directly through the MCP interface.

## 💫 Result

## ✨ Feature

- **Search MindMup Files**: Find MindMup files across your entire Google Drive or within specific folders (Currently supports read-only operations for MindMup files.)
- **Google Drive Integration**: List and filter files in Google Drive with various criteria
- **MindMup Parsing**: Parse and extract content from MindMup mind map files
- **FastMCP Server**: Built on FastMCP framework for high performance
- **Docker Support**: Containerized deployment with Docker Compose

## 🧠 Business Value

- **Unified Knowledge Management**: Centralize mind map access across Google Drive through a single MCP interface
- **Enhanced Productivity**: Quick search and retrieval of mind maps without switching between applications
- **Developer Integration**: Seamlessly integrate mind mapping capabilities into existing workflows and tools
- **Scalable Architecture**: Handle large collections of mind maps with efficient filtering and parsing
- **Cross-Platform Compatibility**: Access mind maps from any MCP-compatible client or application

## 🏗️ Project Structure

```
src/
├── deployment/
│   ├── credentials/
│   │   └── google_service_account.json # Google Cloud Service Account credentials
│   ├── docker-compose-dev.yml
│   ├── docker-compose-prod.yml
│   ├── Dockerfile
├── core/
│   ├── mcp_server.py      # Main MCP server implementation
│   ├── gdrive_client.py   # Google Drive API client
│   ├── mindmup_manager.py # MindMup file management
│   └── mindmup_parser.py  # MindMup file parsing
├── models/
│   ├── file_models.py     # File-related data models
│   └── mindmap_models.py  # Mind map data models
└── utils/
    ├── enum.py           # Enumerations and constants
    └── logger.py         # Logging utilities
```

## 🚀 Getting Started

- Python 3.12+
- Google API client libraries
- Google Drive API credentials:
   - 1. Create a project in Google Cloud Console
   - 2. Enable Google Drive API (Link: https://console.cloud.google.com/apis/library/drive.googleapis.com?authuser=2&project=mcp-minmup2)
   - 3. Create credentials -- Service Account
   - 4. Configure authentication, the setup structure kindly refer to Project Structure

### Docker Deployment

For development:
```bash
make run-dev-docker
```

For production:
```bash
make run-prod
```
### MCP Client Configuration

Add this server to your MCP client configuration:

```json
{
  "mcpServers": {
    "mindmup-gdrive": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:9802/sse"]
    }
  }
}
```

## 🔍 Future Plan
- **Create MindMup Files**: Create new mind maps directly through MCP interface
- **Edit MindMup Content**: Modify existing mind map nodes and structure
- **Export Features**: Export mind maps to various formats (PDF, PNG, SVG)
- **Sync Operations**: Two-way synchronization between local and cloud mind maps
- **Advanced Tagging**: Add metadata and tags to mind map nodes
- **Plugin System**: Extensible plugin architecture for custom functionality
