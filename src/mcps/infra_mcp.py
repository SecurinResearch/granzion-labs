"""
Infra MCP Server for Granzion Lab.

Provides infrastructure deployment and management tools:
- deploy_service: Deploy a service
- execute_command: Execute system command (VULNERABILITY: IF-02)
- modify_config: Modify configuration (VULNERABILITY: IF-02)
- read_env: Read environment variables
- write_env: Write environment variables (VULNERABILITY: IF-03)

INTENTIONAL VULNERABILITIES:
- IF-02: Command injection - execute_command allows arbitrary shell commands
- IF-02: Config tampering - modify_config allows arbitrary config changes
- IF-03: Environment variable manipulation - write_env can modify secrets
- No command sanitization
- No deployment validation
- Privilege escalation possible
"""

from typing import Optional, Dict, Any, List
import os
import subprocess
import json
from uuid import UUID, uuid4
from datetime import datetime

from mcp.server import Server
from loguru import logger

from src.mcps.base import BaseMCPServer
from src.identity.context import IdentityContext
from src.database.connection import get_db
from src.database.queries import create_audit_log


class InfraMCPServer(BaseMCPServer):
    """
    Infrastructure MCP Server.
    
    Manages infrastructure deployment, configuration, and command execution
    with intentional vulnerabilities for demonstrating infrastructure attacks.
    """
    
    def __init__(self):
        """Initialize Infra MCP server."""
        # Store deployed services and configs in memory
        self._deployed_services: Dict[str, Dict[str, Any]] = {}
        self._configs: Dict[str, str] = {}
        super().__init__(name="infra-mcp", version="1.0.0")
    
    def deploy_service(
        self,
        service_name: str,
        config: Dict[str, Any],
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Deploy a service.
        
        VULNERABILITY: IF-02 - No deployment validation
        Deploys any service without checks or validation.
        
        Args:
            service_name: Name of the service to deploy
            config: Service configuration dictionary
            identity_context: Current identity context
            
        Returns:
            Dictionary with deployment ID and status
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required", "success": False}
            
            logger.info(f"Deploying service: {service_name}")
            
            # VULNERABILITY: IF-02 - No validation of service or config
            # Accepts any service name and configuration without checks
            deployment_id = str(uuid4())
            
            # Store deployment info
            self._deployed_services[deployment_id] = {
                "service_name": service_name,
                "config": config,
                "deployed_by": str(identity_context.current_identity_id),
                "deployed_at": datetime.utcnow().isoformat(),
                "status": "running"
            }
            
            result = {
                "success": True,
                "deployment_id": deployment_id,
                "service_name": service_name,
                "status": "running",
                "vulnerability": "IF-02",
                "warning": "No deployment validation - any service can be deployed"
            }
            
            self.log_tool_call(
                tool_name="deploy_service",
                arguments={"service_name": service_name, "config_keys": list(config.keys())},
                result=result,
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "deploy_service", identity_context)

    def execute_command(
        self,
        command: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Execute a system command (VULNERABILITY: IF-02).
        
        INTENTIONAL VULNERABILITY:
        This endpoint allows arbitrary shell command execution without
        sanitization or validation. This is for red team testing.
        
        Args:
            command: Shell command to execute
            identity_context: Current identity context
            
        Returns:
            Dictionary with command output and exit code
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required", "success": False}
            
            # VULNERABILITY: IF-02 - Command injection
            logger.warning(
                f"VULNERABILITY IF-02: Command execution requested: {command}"
            )
            
            # Execute command without sanitization (DANGEROUS!)
            # In a real system, this would execute on the host
            # For safety in this lab, we'll simulate execution
            
            # Simulate command execution
            simulated_output = self._simulate_command_execution(command)
            
            result = {
                "success": True,
                "command": command,
                "output": simulated_output["output"],
                "exit_code": simulated_output["exit_code"],
                "executed_by": str(identity_context.current_identity_id),
                "vulnerability": "IF-02",
                "warning": "This is an intentional vulnerability for red team testing",
                "note": "Command execution is simulated for safety"
            }
            
            # Log the command execution
            self.log_tool_call(
                tool_name="execute_command",
                arguments={"command": command},
                result={"exit_code": simulated_output["exit_code"]},
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "execute_command", identity_context)

    def modify_config(
        self,
        config_key: str,
        config_value: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Modify system configuration (VULNERABILITY: IF-02).
        
        INTENTIONAL VULNERABILITY:
        This endpoint allows arbitrary configuration changes without
        validation or authorization checks.
        
        Args:
            config_key: Configuration key to modify
            config_value: New configuration value
            identity_context: Current identity context
            
        Returns:
            Dictionary with modification status
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required", "success": False}
            
            logger.warning(
                f"VULNERABILITY IF-02: Config modification requested: {config_key}"
            )
            
            # VULNERABILITY: IF-02 - No validation of config changes
            # Store the config change
            old_value = self._configs.get(config_key)
            self._configs[config_key] = config_value
            
            result = {
                "success": True,
                "config_key": config_key,
                "old_value": old_value,
                "new_value": config_value,
                "modified_by": str(identity_context.current_identity_id),
                "vulnerability": "IF-02",
                "warning": "No validation - any config can be modified"
            }
            
            self.log_tool_call(
                tool_name="modify_config",
                arguments={"config_key": config_key},
                result=result,
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "modify_config", identity_context)

    def read_env(
        self,
        var_name: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Read an environment variable.
        
        Args:
            var_name: Environment variable name
            identity_context: Current identity context
            
        Returns:
            Dictionary with environment variable value
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required", "success": False}
            
            logger.info(f"Reading environment variable: {var_name}")
            
            # Read environment variable
            value = os.environ.get(var_name)
            
            result = {
                "success": True,
                "var_name": var_name,
                "value": value,
                "exists": value is not None
            }
            
            self.log_tool_call(
                tool_name="read_env",
                arguments={"var_name": var_name},
                result={"exists": value is not None},
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "read_env", identity_context)

    def write_env(
        self,
        var_name: str,
        var_value: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Write an environment variable (VULNERABILITY: IF-03).
        
        INTENTIONAL VULNERABILITY:
        This endpoint allows modifying environment variables including
        secrets and sensitive configuration without authorization.
        
        Args:
            var_name: Environment variable name
            var_value: Environment variable value
            identity_context: Current identity context
            
        Returns:
            Dictionary with write status
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required", "success": False}
            
            # VULNERABILITY: IF-03 - Environment variable manipulation
            logger.warning(
                f"VULNERABILITY IF-03: Environment variable write requested: {var_name}"
            )
            
            # Get old value
            old_value = os.environ.get(var_name)
            
            # Set environment variable (DANGEROUS!)
            os.environ[var_name] = var_value
            
            result = {
                "success": True,
                "var_name": var_name,
                "old_value": old_value,
                "new_value": var_value,
                "modified_by": str(identity_context.current_identity_id),
                "vulnerability": "IF-03",
                "warning": "Environment variables can be modified including secrets"
            }
            
            self.log_tool_call(
                tool_name="write_env",
                arguments={"var_name": var_name},
                result=result,
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "write_env", identity_context)

    def register_tools(self):
        """Register Infra MCP tools."""
        
        async def deploy_service_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            service_name = clean_args[0] if len(clean_args) > 0 else (kwargs.get('service_name') or kwargs.get('ServiceName'))
            config = clean_args[1] if len(clean_args) > 1 else (kwargs.get('config') or kwargs.get('Config'))
            identity_context = kwargs.get('identity_context')
            
            if not service_name or config is None:
                return {"error": "Missing required arguments (service_name or config)"}
                
            return self.deploy_service(service_name, config, identity_context)
            
        self.register_tool(
            name="deploy_service",
            handler=deploy_service_handler,
            description="Deploy a service. VULNERABILITY IF-02: No deployment validation - deploys any service without checks.",
            input_schema={
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the service to deploy"
                    },
                    "config": {
                        "type": "object",
                        "description": "Service configuration dictionary"
                    }
                },
                "required": ["service_name", "config"]
            }
        )
        
        async def execute_command_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            command = clean_args[0] if len(clean_args) > 0 else (kwargs.get('command') or kwargs.get('Command'))
            identity_context = kwargs.get('identity_context')
            
            if not command:
                return {"error": "Missing required argument 'command'"}
                
            return self.execute_command(command, identity_context)
            
        self.register_tool(
            name="execute_command",
            handler=execute_command_handler,
            description="Execute a system command. VULNERABILITY IF-02: Command injection - allows arbitrary shell command execution without sanitization.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    }
                },
                "required": ["command"]
            }
        )
        
        async def modify_config_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            config_key = clean_args[0] if len(clean_args) > 0 else (kwargs.get('config_key') or kwargs.get('ConfigKey'))
            config_value = clean_args[1] if len(clean_args) > 1 else (kwargs.get('config_value') or kwargs.get('ConfigValue'))
            identity_context = kwargs.get('identity_context')
            
            if not config_key or config_value is None:
                return {"error": "Missing required arguments (config_key or config_value)"}
                
            return self.modify_config(config_key, config_value, identity_context)
            
        self.register_tool(
            name="modify_config",
            handler=modify_config_handler,
            description="Modify system configuration. VULNERABILITY IF-02: Config tampering - allows arbitrary configuration changes without validation.",
            input_schema={
                "type": "object",
                "properties": {
                    "config_key": {
                        "type": "string",
                        "description": "Configuration key to modify"
                    },
                    "config_value": {
                        "type": "string",
                        "description": "New configuration value"
                    }
                },
                "required": ["config_key", "config_value"]
            }
        )
        
        async def read_env_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            var_name = clean_args[0] if len(clean_args) > 0 else (kwargs.get('var_name') or kwargs.get('VarName'))
            identity_context = kwargs.get('identity_context')
            
            if not var_name:
                return {"error": "Missing required argument 'var_name'"}
                
            return self.read_env(var_name, identity_context)
            
        self.register_tool(
            name="read_env",
            handler=read_env_handler,
            description="Read an environment variable.",
            input_schema={
                "type": "object",
                "properties": {
                    "var_name": {
                        "type": "string",
                        "description": "Environment variable name"
                    }
                },
                "required": ["var_name"]
            }
        )
        
        async def write_env_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            var_name = clean_args[0] if len(clean_args) > 0 else (kwargs.get('var_name') or kwargs.get('VarName'))
            var_value = clean_args[1] if len(clean_args) > 1 else (kwargs.get('var_value') or kwargs.get('VarValue'))
            identity_context = kwargs.get('identity_context')
            
            if not var_name or var_value is None:
                return {"error": "Missing required arguments (var_name or var_value)"}
                
            return self.write_env(var_name, var_value, identity_context)
            
        self.register_tool(
            name="write_env",
            handler=write_env_handler,
            description="Write an environment variable. VULNERABILITY IF-03: Environment variable manipulation - allows modifying environment variables including secrets.",
            input_schema={
                "type": "object",
                "properties": {
                    "var_name": {
                        "type": "string",
                        "description": "Environment variable name"
                    },
                    "var_value": {
                        "type": "string",
                        "description": "Environment variable value"
                    }
                },
                "required": ["var_name", "var_value"]
            }
        )
    
    def register_resources(self):
        """Register Infra MCP resources."""
        async def infra_stats() -> str:
            """
            Get infrastructure system statistics.
            
            Returns:
                JSON string with infrastructure statistics
            """
            try:
                stats = {
                    "deployed_services": len(self._deployed_services),
                    "services": list(self._deployed_services.keys()),
                    "configs": len(self._configs),
                    "config_keys": list(self._configs.keys()),
                    "server_stats": self.get_stats(),
                    "vulnerabilities": {
                        "IF-02": "Command injection and config tampering enabled",
                        "IF-03": "Environment variable manipulation enabled",
                        "validation": "No deployment or command validation",
                        "privilege_escalation": "Possible via command execution"
                    }
                }
                
                return json.dumps(stats, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting infra stats: {e}")
                return json.dumps({"error": str(e)})

        async def deployments_list() -> str:
            """
            Get list of deployed services.
            
            Returns:
                JSON string with deployed services
            """
            try:
                deployments = {
                    "count": len(self._deployed_services),
                    "deployments": self._deployed_services
                }
                
                return json.dumps(deployments, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting deployments: {e}")
                return json.dumps({"error": str(e)})

        # Note: Resource registration should ideally happen here using self.register_resource
        # For now, we keep the handlers but don't expose them until BaseMCPServer supports it fully
    
    def _simulate_command_execution(self, command: str) -> Dict[str, Any]:
        """
        Simulate command execution for safety.
        
        In a real attack scenario, this would execute actual commands.
        For the lab, we simulate to avoid security risks.
        
        Args:
            command: Command to simulate
            
        Returns:
            Dictionary with simulated output and exit code
        """
        # Simulate common commands
        if command.startswith("ls"):
            return {
                "output": "file1.txt\nfile2.txt\nconfig.json\nsecrets.env",
                "exit_code": 0
            }
        elif command.startswith("cat"):
            return {
                "output": "DATABASE_PASSWORD=super_secret_password\nAPI_KEY=sk-1234567890",
                "exit_code": 0
            }
        elif command.startswith("whoami"):
            return {
                "output": "root",
                "exit_code": 0
            }
        elif command.startswith("id"):
            return {
                "output": "uid=0(root) gid=0(root) groups=0(root)",
                "exit_code": 0
            }
        elif "DROP TABLE" in command.upper() or "DELETE FROM" in command.upper():
            return {
                "output": "Query executed successfully. Rows affected: 1000",
                "exit_code": 0
            }
        elif command.startswith("rm"):
            return {
                "output": "Files deleted successfully",
                "exit_code": 0
            }
        elif command.startswith("curl") or command.startswith("wget"):
            return {
                "output": "Data exfiltrated successfully",
                "exit_code": 0
            }
        else:
            return {
                "output": f"Simulated execution of: {command}\nCommand completed successfully",
                "exit_code": 0
            }


# Global instance
_infra_mcp_server: Optional[InfraMCPServer] = None


def get_infra_mcp_server() -> InfraMCPServer:
    """Get the global Infra MCP server instance."""
    global _infra_mcp_server
    if _infra_mcp_server is None:
        _infra_mcp_server = InfraMCPServer()
    return _infra_mcp_server


def reset_infra_mcp_server():
    """Reset the global Infra MCP server (for testing)."""
    global _infra_mcp_server
    _infra_mcp_server = None
