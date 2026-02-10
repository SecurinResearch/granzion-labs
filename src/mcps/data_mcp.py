"""
Data MCP Server for Granzion Lab.

Provides CRUD operations and database access tools:
- create_data: Create new records
- read_data: Read records with filters
- update_data: Update existing records
- delete_data: Delete records
- execute_sql: Execute raw SQL (VULNERABILITY: T-02 - SQL injection)

INTENTIONAL VULNERABILITIES:
- T-02: SQL injection via execute_sql endpoint
- No permission checks on data access
- No data validation
- Audit log bypass possible
- Cross-user data access allowed
"""

from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime
import json

# Guest/Anonymous User ID (from main.py)
GUEST_USER_ID = UUID("00000000-0000-0000-0000-000000000999")

from loguru import logger
from sqlalchemy import text, select, insert, update, delete as sql_delete
from sqlalchemy.exc import SQLAlchemyError

from src.mcps.base import BaseMCPServer
from src.identity.context import IdentityContext
from src.database.connection import get_db
from src.database.models import AppData, Identity, AuditLog


class DataMCPServer(BaseMCPServer):
    """
    Data MCP Server.
    
    Manages CRUD operations on application data with intentional vulnerabilities.
    Includes SQL injection vulnerability for red team testing.
    """
    
    def __init__(self):
        """Initialize Data MCP server."""
        super().__init__(name="data-mcp", version="1.0.0")

    def create_data(
        self,
        table: str,
        data: Dict[str, Any],
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Create a new record in the specified table.
        VULNERABILITY: No data validation.
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
            
            # Restrict Guest Access (must be authenticated to exploit vulnerabilities)
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot create data."}
            
            # VULNERABILITY: No data validation
            logger.warning(
                f"VULNERABILITY: Creating data without validation in table {table}"
            )
            
            with get_db() as db:
                if table == "app_data":
                    record = AppData(
                        id=uuid4(),
                        owner_id=identity_context.current_identity_id,
                        table_name=table,
                        data=data,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(record)
                    record_id = str(record.id)
                    owner_id = str(record.owner_id)
                elif table == "audit_logs":
                    # Convert UUID strings in data if needed
                    audit_data = data.copy()
                    if "identity_id" in audit_data and isinstance(audit_data["identity_id"], str):
                        audit_data["identity_id"] = UUID(audit_data["identity_id"])
                    if "resource_id" in audit_data and isinstance(audit_data["resource_id"], str):
                        audit_data["resource_id"] = UUID(audit_data["resource_id"])
                        
                    record = AuditLog(
                        id=uuid4(),
                        timestamp=datetime.utcnow(),
                        **audit_data
                    )
                    db.add(record)
                    record_id = str(record.id)
                    owner_id = "system" # Audit logs don't have an owner like AppData
                else:
                    return {"error": f"Table {table} not supported"}
                
                db.commit()
                
                if table == "audit_logs":
                    created_at_str = record.timestamp.isoformat()
                else:
                    created_at_str = record.created_at.isoformat()

                result = {
                    "success": True,
                    "record_id": record_id,
                    "table": table,
                    "owner_id": owner_id,
                    "created_at": created_at_str,
                }
            
            self.log_tool_call(
                tool_name="create_data",
                arguments={"table": table, "data_keys": list(data.keys())},
                result=result,
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "create_data", identity_context)

    def read_data(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Read records from the specified table.
        VULNERABILITY: Cross-user data access.
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
            
            # Restrict Guest Access (must be authenticated to exploit vulnerabilities)
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot read sensitive data."}
            
            # VULNERABILITY: No permission checks
            logger.warning(
                f"VULNERABILITY: Reading data without permission checks from {table}"
            )
            
            with get_db() as db:
                if table == "app_data":
                    query = select(AppData)
                    # Apply filters if provided
                    if filters:
                        if "owner_id" in filters:
                            query = query.where(AppData.owner_id == UUID(str(filters["owner_id"])))
                        if "id" in filters:
                            query = query.where(AppData.id == UUID(str(filters["id"])))
                    
                    results = db.execute(query).scalars().all()
                    
                    records = []
                    for record in results:
                        records.append({
                            "id": str(record.id),
                            "owner_id": str(record.owner_id),
                            "data": record.data,
                            "created_at": record.created_at.isoformat(),
                            "updated_at": record.updated_at.isoformat(),
                        })
                elif table == "identities":
                    query = select(Identity)
                    if filters and "id" in filters:
                        query = query.where(Identity.id == UUID(str(filters["id"])))
                        
                    results = db.execute(query).scalars().all()
                    records = [{k: str(v) if isinstance(v, (UUID, datetime)) else v for k, v in r.to_dict().items()} for r in results]
                elif table == "audit_logs":
                     query = select(AuditLog)
                     if filters and "id" in filters:
                         query = query.where(AuditLog.id == UUID(str(filters["id"])))
                     
                     results = db.execute(query).scalars().all()
                     records = []
                     for record in results:
                         rec_dict = {
                            "id": str(record.id),
                            "action": record.action,
                            "identity_id": str(record.identity_id) if record.identity_id else None,
                            "logged": record.logged,
                            "timestamp": record.timestamp.isoformat(),
                            "resource_type": record.resource_type,
                            "details": record.details
                         }
                         records.append(rec_dict)
                else:
                    return {"error": f"Table {table} not supported"}
                
                result = {
                    "success": True,
                    "table": table,
                    "count": len(records),
                    "records": records,
                }
            
            self.log_tool_call(
                tool_name="read_data",
                arguments={"table": table, "filters": filters},
                result={"count": len(records)},
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "read_data", identity_context)

    def update_data(
        self,
        table: str,
        record_id: str,
        data: Dict[str, Any],
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Update an existing record.
        VULNERABILITY: No ownership validation.
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}

            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot update data."}
            
            # VULNERABILITY: No ownership validation
            logger.warning(
                f"VULNERABILITY: Updating record {record_id} without ownership check"
            )
            
            record_uuid = UUID(str(record_id))
            
            with get_db() as db:
                if table == "app_data":
                    # Get existing record
                    record = db.execute(
                        select(AppData).where(AppData.id == record_uuid)
                    ).scalar_one_or_none()
                    
                    if not record:
                        return {"success": False, "error": f"Record {record_id} not found"}
                    
                    # Update without ownership check (vulnerability!)
                    record.data = data
                    record.updated_at = datetime.utcnow()
                    updated_at = record.updated_at.isoformat()
                    
                elif table == "audit_logs":
                    record = db.execute(
                        select(AuditLog).where(AuditLog.id == record_uuid)
                    ).scalar_one_or_none()
                    
                    if not record:
                         return {"success": False, "error": f"Record {record_id} not found"}
                    
                    # Update fields
                    for k, v in data.items():
                        if k == "identity_id" and isinstance(v, str):
                            v = UUID(v)
                        if hasattr(record, k):
                            setattr(record, k, v)
                    
                    updated_at = datetime.utcnow().isoformat() # AuditLog uses created_at as timestamp, no updated_at by default but we just return current time
                    
                else:
                    return {"error": f"Table {table} not supported"}
                
                db.commit()
                
                result = {
                    "success": True,
                    "record_id": record_id,
                    "table": table,
                    "updated_at": updated_at,
                }
            
            self.log_tool_call(
                tool_name="update_data",
                arguments={"table": table, "record_id": record_id},
                result=result,
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "update_data", identity_context)

    def delete_data(
        self,
        table: str,
        record_id: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Delete a record.
        VULNERABILITY: No ownership validation.
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}

            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot delete data."}
            
            # VULNERABILITY: No ownership validation
            logger.warning(
                f"VULNERABILITY: Deleting record {record_id} without ownership check"
            )
            
            record_uuid = UUID(str(record_id))
            
            with get_db() as db:
                if table == "app_data":
                    # Check if record exists
                    record = db.execute(
                        select(AppData).where(AppData.id == record_uuid)
                    ).scalar_one_or_none()
                    
                    if not record:
                        return {"success": False, "error": f"Record {record_id} not found"}
                    
                    owner_id = str(record.owner_id)
                    db.execute(sql_delete(AppData).where(AppData.id == record_uuid))
                    
                elif table == "identities":
                    record = db.execute(
                        select(Identity).where(Identity.id == record_uuid)
                    ).scalar_one_or_none()
                    
                    if not record:
                        return {"success": False, "error": f"Record {record_id} not found"}
                    
                    owner_id = str(record.id) # Self-owned
                    db.execute(sql_delete(Identity).where(Identity.id == record_uuid))

                elif table == "audit_logs":
                    record = db.execute(
                        select(AuditLog).where(AuditLog.id == record_uuid)
                    ).scalar_one_or_none()
                    
                    if not record:
                         return {"success": False, "error": f"Record {record_id} not found"}
                    
                    owner_id = "system"
                    db.execute(sql_delete(AuditLog).where(AuditLog.id == record_uuid))
                    
                else:
                    return {"error": f"Table {table} not supported"}
                
                db.commit()
                
                result = {
                    "success": True,
                    "record_id": record_id,
                    "table": table,
                    "deleted_by": str(identity_context.current_identity_id),
                    "record_owner": owner_id,
                }
            
            self.log_tool_call(
                tool_name="delete_data",
                arguments={"table": table, "record_id": record_id},
                result=result,
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "delete_data", identity_context)

    def execute_sql(
        self,
        query: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Execute raw SQL query (VULNERABILITY: T-02 - SQL injection).
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}

            # Restrict Guest Access (must be authenticated to exploit SQLi)
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot execute SQL."}
            
            # VULNERABILITY T-02: SQL injection
            logger.error(
                f"VULNERABILITY T-02: Executing raw SQL without sanitization: {query[:100]}..."
            )
            
            with get_db() as db:
                # Execute raw SQL without any sanitization (CRITICAL VULNERABILITY!)
                # Note: SessionWrapper should handle text() requirement for 2.0
                # But here we explicitly can pass strings if needed, but wrapper handles it.
                # If we use text(query), it's safe from SQLAlchemy perspective but Vulnerable to injection if query content is malicious.
                result_proxy = db.execute(text(query))
                
                # Try to fetch results if it's a SELECT query
                try:
                    rows = result_proxy.fetchall()
                    columns = result_proxy.keys() if result_proxy.keys() else []
                    
                    results = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            # Convert non-serializable types
                            if isinstance(value, (datetime, UUID)):
                                value = str(value)
                            row_dict[col] = value
                        results.append(row_dict)
                    
                    db.commit()
                    
                    result = {
                        "success": True,
                        "query": query,
                        "row_count": len(results),
                        "results": results,
                        "vulnerability": "T-02",
                        "warning": "SQL injection vulnerability - query executed without sanitization",
                    }
                    
                except Exception:
                    # Non-SELECT query (INSERT, UPDATE, DELETE, etc.)
                    db.commit()
                    
                    result = {
                        "success": True,
                        "query": query,
                        "message": "Query executed successfully",
                        "vulnerability": "T-02",
                        "warning": "SQL injection vulnerability - query executed without sanitization",
                    }
            
            # Intentionally NOT logging to audit log to demonstrate visibility gap
            logger.warning(
                f"SQL injection executed by {identity_context.current_identity_id} - "
                f"NOT logged to audit trail (visibility gap)"
            )
            
            return result
            
        except SQLAlchemyError as e:
            # Return SQL error to attacker (information disclosure)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "vulnerability": "T-02",
                "warning": "SQL error disclosed to attacker",
            }
        except Exception as e:
            return self.handle_error(e, "execute_sql", identity_context)

    def register_tools(self):
        """Register Data MCP tools."""
        
        async def create_data_handler(*args, **kwargs):
            # Extract arguments robustly
            # Filter out identity_context from args if it slipped in
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            table = clean_args[0] if len(clean_args) > 0 else (kwargs.get('table') or kwargs.get('Table'))
            data = clean_args[1] if len(clean_args) > 1 else (kwargs.get('data') or kwargs.get('Data'))
            identity_context = kwargs.get('identity_context')
            
            logger.info(f"DataMCP.create_data: table={table}, data={data}")
            return self.create_data(table, data, identity_context)
            
        self.register_tool(
            name="create_data",
            handler=create_data_handler,
            description="Create a new record in the specified table. VULNERABILITY: No data validation.",
            input_schema={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name (currently only 'app_data' supported)"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data to insert"
                    }
                },
                "required": ["table", "data"]
            }
        )
        
        async def read_data_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            table = clean_args[0] if len(clean_args) > 0 else (kwargs.get('table') or kwargs.get('Table'))
            filters = clean_args[1] if len(clean_args) > 1 else (kwargs.get('filters') or kwargs.get('Filters'))
            identity_context = kwargs.get('identity_context')
            
            logger.info(f"DataMCP.read_data: table={table}, filters={filters}")
            return self.read_data(table, filters, identity_context)
            
        self.register_tool(
            name="read_data",
            handler=read_data_handler,
            description="Read records from the specified table. VULNERABILITY: Cross-user data access.",
            input_schema={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters (e.g., {'owner_id': 'uuid'})"
                    }
                },
                "required": ["table"]
            }
        )
        
        async def update_data_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            table = clean_args[0] if len(clean_args) > 0 else (kwargs.get('table') or kwargs.get('Table'))
            record_id = clean_args[1] if len(clean_args) > 1 else (kwargs.get('record_id') or kwargs.get('RecordId'))
            data = clean_args[2] if len(clean_args) > 2 else (kwargs.get('data') or kwargs.get('Data'))
            identity_context = kwargs.get('identity_context')
            
            if not table or not record_id or not data:
                return {"error": "Missing required arguments (table, record_id, or data)"}
                
            return self.update_data(table, record_id, data, identity_context)
            
        self.register_tool(
            name="update_data",
            handler=update_data_handler,
            description="Update an existing record. VULNERABILITY: No ownership validation.",
            input_schema={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name"
                    },
                    "record_id": {
                        "type": "string",
                        "description": "Record UUID to update"
                    },
                    "data": {
                        "type": "object",
                        "description": "New data"
                    }
                },
                "required": ["table", "record_id", "data"]
            }
        )
        
        async def delete_data_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            table = clean_args[0] if len(clean_args) > 0 else (kwargs.get('table') or kwargs.get('Table'))
            record_id = clean_args[1] if len(clean_args) > 1 else (kwargs.get('record_id') or kwargs.get('RecordId'))
            identity_context = kwargs.get('identity_context')
            
            if not table or not record_id:
                return {"error": "Missing required arguments (table or record_id)"}
                
            return self.delete_data(table, record_id, identity_context)
            
        self.register_tool(
            name="delete_data",
            handler=delete_data_handler,
            description="Delete a record. VULNERABILITY: No ownership validation.",
            input_schema={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name"
                    },
                    "record_id": {
                        "type": "string",
                        "description": "Record UUID to delete"
                    }
                },
                "required": ["table", "record_id"]
            }
        )
        
        async def execute_sql_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            query = clean_args[0] if len(clean_args) > 0 else (kwargs.get('query') or kwargs.get('Query'))
            identity_context = kwargs.get('identity_context')
            
            if not query:
                return {"error": "Missing required argument 'query'"}
                
            return self.execute_sql(query, identity_context)
            
        self.register_tool(
            name="execute_sql",
            handler=execute_sql_handler,
            description="Execute raw SQL query. CRITICAL VULNERABILITY T-02: SQL injection - allows arbitrary SQL execution without sanitization.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Raw SQL query to execute"
                    }
                },
                "required": ["query"]
            }
        )
    
    def register_resources(self):
        """Register Data MCP resources."""
        async def data_stats() -> str:
            """
            Get data system statistics.
            
            Returns:
                JSON string with data statistics
            """
            try:
                with get_db() as db:
                    # Get counts
                    from sqlalchemy import func
                    
                    total_records = db.execute(
                        select(func.count()).select_from(AppData)
                    ).scalar()
                    
                    unique_owners = db.execute(
                        select(func.count(func.distinct(AppData.owner_id))).select_from(AppData)
                    ).scalar()
                    
                    data_types = db.execute(
                        select(AppData.data_type, func.count()).
                        select_from(AppData).
                        group_by(AppData.data_type)
                    ).fetchall()
                    
                    type_counts = {dt: count for dt, count in data_types}
                    
                    stats = {
                        "total_records": total_records,
                        "unique_owners": unique_owners,
                        "data_types": type_counts,
                        "server_stats": self.get_stats(),
                    }
                    
                    return json.dumps(stats, indent=2)
                    
            except Exception as e:
                logger.error(f"Error getting data stats: {e}")
                return json.dumps({"error": str(e)})


# Global instance
_data_mcp_server: Optional[DataMCPServer] = None


def get_data_mcp_server() -> DataMCPServer:
    """Get the global Data MCP server instance."""
    global _data_mcp_server
    if _data_mcp_server is None:
        _data_mcp_server = DataMCPServer()
    return _data_mcp_server


def reset_data_mcp_server():
    """Reset the global Data MCP server (for testing)."""
    global _data_mcp_server
    _data_mcp_server = None
