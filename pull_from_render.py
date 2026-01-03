#!/usr/bin/env python3
"""
Pull environment variables from a Render service and create/update .env file.
Useful for syncing production config to local development.
"""

import os
import sys
import getpass
import render_manager


def main():
    """Pull environment variables from Render."""
    print("=" * 60)
    print("PULL ENVIRONMENT VARIABLES FROM RENDER")
    print("=" * 60)

    # Ask for Render API key if not in environment
    api_key = os.getenv('RENDER_API_KEY')
    if not api_key:
        print("\nRENDER_API_KEY not found in environment.")
        api_key = getpass.getpass("Enter your Render API key: ").strip()
        if not api_key:
            print("Error: API key is required!")
            sys.exit(1)

    # Ask for service ID
    print("\nEnter the Render service ID to pull from.")
    print("(You can find this in the Render dashboard URL: srv-...)")
    service_id = input("Service ID: ").strip()

    if not service_id:
        print("Error: Service ID is required!")
        sys.exit(1)

    # Initialize Render manager
    rm = render_manager.RenderManager(api_key)

    # Get service info
    print(f"\nFetching service info for {service_id}...")
    success, service_info = rm.get_service(service_id)

    if not success:
        print(f"Error: Failed to get service info: {service_info}")
        sys.exit(1)

    service_name = service_info.get('name', 'Unknown')
    print(f"✓ Found service: {service_name}")

    # Get environment variables
    print("\nFetching environment variables...")
    success, env_vars = rm.get_env_vars(service_id)

    if not success:
        print(f"Error: Failed to get environment variables: {env_vars}")
        sys.exit(1)

    print(f"✓ Found {len(env_vars)} environment variables")

    # Display variables (mask sensitive values)
    print("\nEnvironment variables:")
    for var in env_vars:
        key = var['key']
        value = var['value']
        # Mask sensitive values
        if any(sensitive in key.upper() for sensitive in ['KEY', 'TOKEN', 'SECRET', 'PASSWORD']):
            display_value = value[:8] + '...' if len(value) > 8 else '***'
        else:
            display_value = value
        print(f"  {key} = {display_value}")

    # Ask if user wants to save to .env
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        print(f"\nWarning: .env file already exists!")
        response = input("Overwrite existing .env file? (y/N): ").strip().lower()
        if response != 'y':
            # Offer to merge
            response = input("Merge with existing .env (add/update variables)? (y/N): ").strip().lower()
            if response != 'y':
                print("Cancelled.")
                sys.exit(0)
            merge = True
        else:
            merge = False
    else:
        response = input("\nSave to .env file? (y/N): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            sys.exit(0)
        merge = False

    # Load existing env if merging
    existing_vars = {}
    if merge and os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_vars[key] = value

    # Write .env file
    with open(env_path, 'w') as f:
        f.write("# Inception Environment Variables\n")
        f.write(f"# Pulled from Render service: {service_name} ({service_id})\n")
        f.write("# DO NOT commit this file to git!\n\n")

        # Group variables by category
        categories = {
            'Dashboard': ['DASHBOARD_PASSWORD', 'SECRET_KEY', 'DASHBOARD_HOST', 'DASHBOARD_PORT'],
            'AI API': ['ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN'],
            'GitHub': ['GITHUB_TOKEN'],
            'Render': ['RENDER_API_KEY', 'RENDER_OWNER_ID'],
            'Other': []
        }

        # Categorize variables
        categorized = {cat: [] for cat in categories}
        for var in env_vars:
            key = var['key']
            value = var['value']
            found = False
            for cat, keys in categories.items():
                if cat != 'Other' and key in keys:
                    categorized[cat].append((key, value))
                    found = True
                    break
            if not found:
                categorized['Other'].append((key, value))

        # Add merged variables that weren't in Render
        if merge:
            for key, value in existing_vars.items():
                if not any(var['key'] == key for var in env_vars):
                    categorized['Other'].append((key, value))

        # Write by category
        for cat, vars_list in categorized.items():
            if vars_list:
                f.write(f"# {cat} Settings\n")
                for key, value in sorted(vars_list):
                    f.write(f"{key}={value}\n")
                f.write("\n")

    action = "merged with" if merge else "saved to"
    print(f"\n✓ Environment variables {action} {env_path}")

    # Also save the Render API key we used
    if not merge or 'RENDER_API_KEY' not in existing_vars:
        with open(env_path, 'a') as f:
            f.write(f"# Render API key used for this pull\n")
            f.write(f"RENDER_API_KEY={api_key}\n")
        print(f"✓ Added RENDER_API_KEY to .env")

    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("\n1. Review the .env file and update any values as needed")
    print("2. Run the startup script:")
    print("   ./start_local.sh")
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
