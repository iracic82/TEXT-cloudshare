"""
CloudShare API client wrapper.

Handles authentication (HMAC-SHA1) via the official cloudshare SDK
and exposes high-level helpers for environment/VM operations.
"""

import os
import time
import cloudshare


class CloudShareClient:
    def __init__(self, api_id=None, api_key=None, hostname=None):
        self.api_id = api_id or os.environ.get("CLOUDSHARE_API_ID")
        self.api_key = api_key or os.environ.get("CLOUDSHARE_API_KEY")
        self.hostname = hostname or os.environ.get("CLOUDSHARE_HOSTNAME", "use.cloudshare.com")

        if not self.api_id or not self.api_key:
            raise ValueError("CLOUDSHARE_API_ID and CLOUDSHARE_API_KEY must be set")

    def _request(self, method, path, query_params=None, content=None):
        res = cloudshare.req(
            hostname=self.hostname,
            method=method,
            apiId=self.api_id,
            apiKey=self.api_key,
            path=path,
            queryParams=query_params,
            content=content,
        )
        if res.status // 100 != 2:
            raise Exception(f"CloudShare API error {res.status}: {res.content}")
        return res.content

    # ── Environment operations ──────────────────────────────────────

    def list_envs(self):
        return self._request("GET", "envs")

    def get_env(self, env_id):
        return self._request("GET", f"envs/{env_id}")

    def get_env_extended(self, env_id):
        return self._request("GET", "envs/actions/getextended", query_params={"envId": env_id})

    def get_env_machines(self, env_id):
        return self._request("GET", "envs/actions/machines/", query_params={"eid": env_id})

    # ── VM operations ───────────────────────────────────────────────

    def execute_command(self, vm_id, command):
        """Run a command on a VM via CloudShare's executePath API."""
        return self._request("POST", "vms/actions/executepath", content={
            "vmId": vm_id,
            "path": command,
        })

    def check_execution_status(self, vm_id, execution_id):
        return self._request("GET", "vms/actions/checkexecutionstatus", query_params={
            "vmId": vm_id,
            "executionId": execution_id,
        })

    def wait_for_execution(self, vm_id, execution_id, poll_interval=5, timeout=300):
        """Poll until command execution completes. Returns the execution result."""
        start = time.time()
        while True:
            status = self.check_execution_status(vm_id, execution_id)
            if status.get("success"):
                return status
            if time.time() - start > timeout:
                raise TimeoutError(
                    f"Command execution timed out after {timeout}s. "
                    f"Last status: {status}"
                )
            time.sleep(poll_interval)

    def run_command_sync(self, vm_id, command, timeout=300):
        """Execute a command on a VM and wait for completion. Returns stdout."""
        execution = self.execute_command(vm_id, command)
        result = self.wait_for_execution(vm_id, execution["executionId"], timeout=timeout)
        return result.get("standardOutput", "")
