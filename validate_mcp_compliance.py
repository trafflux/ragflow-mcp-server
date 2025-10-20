#!/usr/bin/env python3
"""
Docker MCP Registry Compliance Validator

Validates that the RAGFlow MCP Server meets all Docker MCP Registry requirements.
"""

import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)


def validate_server_yaml(path: Path) -> bool:
    """Validate server.yaml structure and content."""
    print("\n🔍 Validating server.yaml...")
    
    if not path.exists():
        print(f"  ❌ server.yaml not found at {path}")
        return False
    
    try:
        with open(path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"  ❌ Invalid YAML syntax: {e}")
        return False
    
    # Required top-level fields
    required_fields = {
        'name': str,
        'type': str,
        'meta': dict,
        'about': dict,
        'source': dict,
        'config': dict,
        'tools': list,
    }
    
    for field, expected_type in required_fields.items():
        if field not in config:
            print(f"  ❌ Missing required field: {field}")
            return False
        if not isinstance(config[field], expected_type):
            print(f"  ❌ Field '{field}' should be {expected_type.__name__}, got {type(config[field]).__name__}")
            return False
    
    # Validate meta section
    if 'category' not in config['meta']:
        print("  ❌ meta.category is required")
        return False
    if 'tags' not in config['meta'] or not isinstance(config['meta']['tags'], list):
        print("  ❌ meta.tags must be a list")
        return False
    
    # Validate about section
    required_about = ['title', 'description']
    for field in required_about:
        if field not in config['about']:
            print(f"  ❌ about.{field} is required")
            return False
    
    # Validate source section
    if 'project' not in config['source']:
        print("  ❌ source.project (GitHub URL) is required")
        return False
    
    # Validate config section
    if 'description' not in config['config']:
        print("  ⚠️  config.description is recommended")
    
    # Validate tools
    if len(config['tools']) == 0:
        print("  ❌ At least one tool must be defined")
        return False
    
    for tool in config['tools']:
        if 'name' not in tool:
            print("  ❌ Tool missing 'name' field")
            return False
        if 'description' not in tool:
            print(f"  ⚠️  Tool '{tool['name']}' missing description")
    
    print(f"  ✅ server.yaml is valid")
    print(f"     - Name: {config['name']}")
    print(f"     - Category: {config['meta']['category']}")
    print(f"     - Tools: {len(config['tools'])}")
    print(f"     - Tags: {', '.join(config['meta']['tags'][:3])}{'...' if len(config['meta']['tags']) > 3 else ''}")
    
    return True


def validate_tools_json(path: Path) -> bool:
    """Validate tools.json structure."""
    print("\n🔍 Validating tools.json...")
    
    if not path.exists():
        print(f"  ❌ tools.json not found at {path}")
        return False
    
    try:
        with open(path) as f:
            tools = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON syntax: {e}")
        return False
    
    if not isinstance(tools, list):
        print("  ❌ tools.json must be a JSON array")
        return False
    
    if len(tools) == 0:
        print("  ❌ tools.json must contain at least one tool")
        return False
    
    for i, tool in enumerate(tools):
        if 'name' not in tool:
            print(f"  ❌ Tool {i} missing 'name' field")
            return False
        if 'description' not in tool:
            print(f"  ⚠️  Tool '{tool['name']}' missing description")
        if 'arguments' not in tool:
            print(f"  ⚠️  Tool '{tool['name']}' missing arguments list")
    
    print(f"  ✅ tools.json is valid")
    print(f"     - Tools defined: {len(tools)}")
    for tool in tools:
        print(f"     - {tool['name']}: {len(tool.get('arguments', []))} arguments")
    
    return True


def validate_dockerfile(path: Path) -> bool:
    """Validate Dockerfile best practices."""
    print("\n🔍 Validating Dockerfile...")
    
    if not path.exists():
        print(f"  ❌ Dockerfile not found at {path}")
        return False
    
    with open(path) as f:
        content = f.read()
    
    checks = {
        'FROM': 'Base image specified',
        'WORKDIR': 'Working directory set',
        'USER': 'Non-root user specified (security)',
        'ENTRYPOINT': 'Entrypoint defined',
    }
    
    passed = True
    for keyword, description in checks.items():
        if keyword in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ Missing: {description}")
            passed = False
    
    # Check for security best practices
    if 'USER root' in content or not 'USER' in content:
        print("  ⚠️  Container may run as root (security concern)")
    
    if '--no-cache-dir' in content:
        print("  ✅ Using pip without cache (good practice)")
    
    if 'rm -rf' in content:
        print("  ✅ Cleaning up package manager cache (smaller image)")
    
    return passed


def validate_entrypoint(path: Path) -> bool:
    """Validate docker-entrypoint.sh."""
    print("\n🔍 Validating docker-entrypoint.sh...")
    
    if not path.exists():
        print(f"  ❌ docker-entrypoint.sh not found at {path}")
        return False
    
    with open(path) as f:
        content = f.read()
    
    if not content.startswith('#!/bin/bash') and not content.startswith('#!/bin/sh'):
        print("  ⚠️  Script should start with shebang (#!/bin/bash or #!/bin/sh)")
    
    if 'set -e' in content:
        print("  ✅ Error handling enabled (set -e)")
    
    if 'RAGFLOW_API_KEY' in content:
        print("  ✅ Checks for RAGFLOW_API_KEY")
    
    if 'exec' in content:
        print("  ✅ Uses exec for proper signal handling")
    
    if 'uv run' in content:
        print("  ✅ Uses uv for Python package management")
    else:
        print("  ⚠️  Should use 'uv run' for Python execution")
    
    print("  ✅ docker-entrypoint.sh looks good")
    return True


def validate_pyproject_toml(path: Path) -> bool:
    """Validate pyproject.toml."""
    print("\n🔍 Validating pyproject.toml...")
    
    if not path.exists():
        print(f"  ⚠️  pyproject.toml not found (optional)")
        return True
    
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            print("  ⚠️  Cannot validate TOML (tomllib not available)")
            return True
    
    with open(path, 'rb') as f:
        try:
            config = tomllib.load(f)
        except Exception as e:
            print(f"  ❌ Invalid TOML syntax: {e}")
            return False
    
    if 'project' in config:
        project = config['project']
        if 'name' in project:
            print(f"  ✅ Project name: {project['name']}")
        if 'version' in project:
            print(f"  ✅ Version: {project['version']}")
        if 'license' in project:
            print(f"  ✅ License: {project['license'].get('text', 'specified')}")
    
    return True


def main():
    """Run all validations."""
    print("=" * 60)
    print("🐳 Docker MCP Registry Compliance Validator")
    print("=" * 60)
    
    repo_root = Path(__file__).parent
    
    results = {
        'server.yaml': validate_server_yaml(repo_root / 'server.yaml'),
        'tools.json': validate_tools_json(repo_root / 'tools.json'),
        'Dockerfile': validate_dockerfile(repo_root / 'Dockerfile'),
        'docker-entrypoint.sh': validate_entrypoint(repo_root / 'docker-entrypoint.sh'),
        'pyproject.toml': validate_pyproject_toml(repo_root / 'pyproject.toml'),
    }
    
    print("\n" + "=" * 60)
    print("📊 Validation Summary")
    print("=" * 60)
    
    for file, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {file}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All validations passed! Ready for Docker MCP Registry submission.")
        print("\n📝 Next steps:")
        print("  1. Review CONTRIBUTING_DOCKER_MCP.md for submission process")
        print("  2. Test locally with: docker mcp catalog import ./server.yaml")
        print("  3. Submit PR to https://github.com/docker/mcp-servers")
        return 0
    else:
        print("\n⚠️  Some validations failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
