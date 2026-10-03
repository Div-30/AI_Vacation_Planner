from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

TRAVEL_SERVER_PATH = Path(__file__).parent.parent / "mcp_servers" /"travel_tools_server.py"

mcp_client = MultiServerMCPClient({
    "travel_tools": {
        "command": "python",
        "args": [str(TRAVEL_SERVER_PATH)],
        "transport": "stdio",
    }
})
async def load_mcp_tools():
    return await mcp_client.get_tools()