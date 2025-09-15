# Docker Deployment Guide

## Prerequisites

1. Docker and Docker Compose installed
2. Google Drive API credentials file

## Setup

1. **Create credentials directory**:
   ```bash
   mkdir -p deployment/credentials
   ```

2. **Place your Google Drive credentials**:
   ```bash
   # Copy your service account credentials file
   cp path/to/your-service-account.json deployment/credentials/google_drive_credentials.json

   # Or if you have existing credentials:
   cp deployment/credentials/google_service_account.json deployment/credentials/google_drive_credentials.json
   ```

3. **Build and run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

3. **Check logs**:
   ```bash
   docker-compose logs -f mcp-server
   ```

## Testing the HTTP endpoint

The MCP server will be available at `http://localhost:9801/mcp`

## Configuration

Edit `docker-compose.yml` to customize:
- Port mapping
- Environment variables
- Volume mounts

## Using with Claude Code

In your Claude Code configuration, add:

```json
{
  "mcpServers": {
    "mindmup-gdrive": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:9801/mcp"
      ]
    }
  }
}
```

Replace `YOUR_SERVER_IP` with your actual server IP address.

## Troubleshooting

- Check logs: `docker-compose logs mcp-server`
- Restart service: `docker-compose restart mcp-server`
- Rebuild: `docker-compose up --build -d`