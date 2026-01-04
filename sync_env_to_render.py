#!/usr/bin/env python3
"""
Sync Environment Variables to Render
Reads .env file and pushes all variables to your Render service
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    print("❌ Error: .env file not found")
    exit(1)

load_dotenv(env_path)

# Get Render credentials
RENDER_API_KEY = os.getenv('RENDER_API_KEY')
RENDER_SERVICE_ID = os.getenv('RENDER_SERVICE_ID')

if not RENDER_API_KEY or not RENDER_SERVICE_ID:
    print("❌ Error: RENDER_API_KEY or RENDER_SERVICE_ID not set in .env")
    exit(1)

# Environment variables to sync
env_vars_to_sync = {
    'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
    'CLAUDE_CODE_OAUTH_TOKEN': os.getenv('CLAUDE_CODE_OAUTH_TOKEN'),
    'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN'),
    'RENDER_API_KEY': os.getenv('RENDER_API_KEY'),
    'RENDER_OWNER_ID': os.getenv('RENDER_OWNER_ID'),
    'RENDER_SERVICE_ID': os.getenv('RENDER_SERVICE_ID'),
    'DASHBOARD_PASSWORD': os.getenv('DASHBOARD_PASSWORD'),
    'SECRET_KEY': os.getenv('SECRET_KEY'),
}

# Remove None values
env_vars_to_sync = {k: v for k, v in env_vars_to_sync.items() if v}

print(f"🚀 Syncing {len(env_vars_to_sync)} environment variables to Render...")
print(f"   Service ID: {RENDER_SERVICE_ID}")
print()

# Get existing env vars from Render
print("📥 Fetching existing environment variables from Render...")
response = requests.get(
    f'https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars',
    headers={
        'Authorization': f'Bearer {RENDER_API_KEY}',
        'Accept': 'application/json'
    }
)

if response.status_code != 200:
    print(f"❌ Error fetching env vars: {response.status_code}")
    print(response.text)
    exit(1)

response_data = response.json()

# Parse existing env vars - Render returns list of {envVar: {key, value}, cursor}
existing_env_vars = {}
if isinstance(response_data, list):
    for item in response_data:
        if 'envVar' in item:
            key = item['envVar']['key']
            existing_env_vars[key] = item['envVar'].get('value', '')

print(f"✓ Found {len(existing_env_vars)} existing variables")
print()

# Render API uses PUT to update all env vars at once
# Build the list of env var objects
env_var_list = []
for key, value in env_vars_to_sync.items():
    env_var_list.append({
        'key': key,
        'value': value
    })

# Also preserve existing vars that aren't in our sync list
for key, value in existing_env_vars.items():
    if key not in env_vars_to_sync:
        env_var_list.append({
            'key': key,
            'value': value
        })

print(f"📤 Sending {len(env_var_list)} environment variables to Render...")
print()

# Update all env vars at once
response = requests.put(
    f'https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars',
    headers={
        'Authorization': f'Bearer {RENDER_API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    json=env_var_list
)

updated = 0
created = 0
errors = 0

if response.status_code == 200:
    print("✓ Successfully updated environment variables on Render!")
    # Count what changed
    for key in env_vars_to_sync.keys():
        if key in existing_env_vars:
            if existing_env_vars[key] != env_vars_to_sync[key]:
                print(f"  🔄 Updated {key}")
                updated += 1
            else:
                print(f"  ✓ {key} (no change)")
        else:
            print(f"  ➕ Created {key}")
            created += 1
else:
    print(f"❌ Error updating env vars: {response.status_code}")
    print(response.text)
    errors = len(env_vars_to_sync)

print()
print("=" * 60)
print(f"✅ Sync Complete!")
print(f"   Updated: {updated}")
print(f"   Created: {created}")
print(f"   Errors: {errors}")
print()
print("🔄 Your Render service will automatically redeploy with the new variables.")
print("=" * 60)
