#!/usr/bin/env python3
"""
Module entry point for FastMCP server.

Allows execution via: python3 -m mcp_app
"""

import sys

if __name__ == "__main__":
    from mcp_app import main
    sys.exit(main())
