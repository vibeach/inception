#!/usr/bin/env python3
"""
Render API Manager
Manages Render services and environment variables for supervised projects.
"""

import requests
import json
import config


class RenderManager:
    """Manages Render API operations for projects."""

    def __init__(self, api_key=None):
        """Initialize with Render API key."""
        self.api_key = api_key or config.RENDER_API_KEY
        self.base_url = "https://api.render.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_service(self, service_id):
        """Get service details."""
        try:
            response = requests.get(
                f"{self.base_url}/services/{service_id}",
                headers=self.headers
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def get_env_vars(self, service_id):
        """Get all environment variables for a service."""
        try:
            response = requests.get(
                f"{self.base_url}/services/{service_id}/env-vars",
                headers=self.headers
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def set_env_var(self, service_id, key, value):
        """Set a single environment variable."""
        try:
            response = requests.put(
                f"{self.base_url}/services/{service_id}/env-vars",
                headers=self.headers,
                json=[{"key": key, "value": value}]
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def set_env_vars(self, service_id, env_vars):
        """
        Set multiple environment variables.

        Args:
            service_id: Render service ID
            env_vars: Dict of {key: value} or list of {"key": "...", "value": "..."}
        """
        try:
            # Convert dict to list format if needed
            if isinstance(env_vars, dict):
                env_list = [{"key": k, "value": v} for k, v in env_vars.items()]
            else:
                env_list = env_vars

            response = requests.put(
                f"{self.base_url}/services/{service_id}/env-vars",
                headers=self.headers,
                json=env_list
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def delete_env_var(self, service_id, key):
        """Delete an environment variable."""
        try:
            response = requests.delete(
                f"{self.base_url}/services/{service_id}/env-vars/{key}",
                headers=self.headers
            )
            if response.status_code == 204:
                return True, "Deleted successfully"
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def trigger_deploy(self, service_id):
        """Trigger a manual deploy."""
        try:
            response = requests.post(
                f"{self.base_url}/services/{service_id}/deploys",
                headers=self.headers,
                json={"clearCache": "do_not_clear"}
            )
            if response.status_code == 201:
                return True, response.json()
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def get_deploys(self, service_id, limit=10):
        """Get recent deploys for a service."""
        try:
            response = requests.get(
                f"{self.base_url}/services/{service_id}/deploys?limit={limit}",
                headers=self.headers
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)


# Convenience function for quick access
def get_render_manager(api_key=None):
    """Get a RenderManager instance."""
    return RenderManager(api_key)
