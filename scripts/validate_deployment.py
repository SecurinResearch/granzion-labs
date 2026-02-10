#!/usr/bin/env python3
"""
Deployment validation script for Granzion Lab.

This script validates that all services are running and accessible
after deployment with `docker compose up`.

Usage:
    python scripts/validate_deployment.py
"""

import sys
import time
import requests
from typing import Dict, List, Tuple
from loguru import logger


class DeploymentValidator:
    """Validates Granzion Lab deployment."""
    
    def __init__(self):
        """Initialize validator."""
        # Use environment variables or Docker service names
        import os
        
        # Check if we're inside a container (use service names) or on host (use localhost)
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        keycloak_host = os.getenv("KEYCLOAK_HOST", "keycloak")
        puppygraph_host = os.getenv("PUPPYGRAPH_HOST", "puppygraph")
        
        self.services = {
            "PostgreSQL": {"host": postgres_host, "port": 5432},
            "Keycloak": {"host": keycloak_host, "port": 8080},
            "PuppyGraph": {"host": puppygraph_host, "port": 8081},  # Use Gremlin port
            "Granzion API": {"host": "localhost", "port": 8001},  # Same container
        }
        self.results: List[Tuple[str, bool, str]] = []
    
    def validate_all(self) -> bool:
        """
        Validate all services.
        
        Returns:
            True if all services are healthy, False otherwise
        """
        logger.info("Starting deployment validation...")
        
        # Check PostgreSQL
        self._check_postgres()
        
        # Check Keycloak
        self._check_keycloak()
        
        # Check PuppyGraph
        self._check_puppygraph()
        
        # Check Granzion API
        self._check_api()
        
        # Print results
        self._print_results()
        
        # Return overall status
        return all(result[1] for result in self.results)
    
    def _check_postgres(self):
        """Check PostgreSQL connectivity."""
        try:
            import psycopg2
            import os
            
            host = os.getenv("POSTGRES_HOST", "postgres")
            port = int(os.getenv("POSTGRES_PORT", "5432"))
            database = os.getenv("POSTGRES_DB", "granzion_lab")
            user = os.getenv("POSTGRES_USER", "granzion")
            password = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")
            
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=5
            )
            conn.close()
            self.results.append(("PostgreSQL", True, "Connected successfully"))
        except ImportError:
            self.results.append(("PostgreSQL", False, "psycopg2 not installed"))
        except Exception as e:
            self.results.append(("PostgreSQL", False, f"Connection failed: {e}"))
    
    def _check_keycloak(self):
        """Check Keycloak accessibility."""
        try:
            import os
            host = os.getenv("KEYCLOAK_HOST", "keycloak")
            port = int(os.getenv("KEYCLOAK_PORT", "8080"))
            
            # Try realm endpoint (health endpoint may not exist)
            response = requests.get(
                f"http://{host}:{port}/realms/granzion-lab",
                timeout=5
            )
            if response.status_code in [200, 404]:  # 404 is ok if realm doesn't exist yet
                self.results.append(("Keycloak", True, "Service accessible"))
            else:
                self.results.append(("Keycloak", False, f"HTTP {response.status_code}"))
        except requests.exceptions.RequestException as e:
            self.results.append(("Keycloak", False, f"Request failed: {e}"))
    
    def _check_puppygraph(self):
        """Check PuppyGraph accessibility (Gremlin API)."""
        try:
            import os
            host = os.getenv("PUPPYGRAPH_HOST", "puppygraph")
            port = int(os.getenv("PUPPYGRAPH_PORT", "8081"))  # Gremlin port
            
            # Try Gremlin endpoint
            response = requests.get(
                f"http://{host}:{port}/",
                timeout=5
            )
            # Any response means service is up
            self.results.append(("PuppyGraph", True, "Gremlin API accessible"))
        except requests.exceptions.RequestException as e:
            self.results.append(("PuppyGraph", False, f"Request failed: {e}"))
    
    def _check_api(self):
        """Check Granzion API."""
        try:
            response = requests.get(
                "http://localhost:8001/health",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.results.append(("Granzion API", True, f"Status: {data.get('status', 'unknown')}"))
            else:
                self.results.append(("Granzion API", False, f"HTTP {response.status_code}"))
        except requests.exceptions.RequestException as e:
            self.results.append(("Granzion API", False, f"Request failed: {e}"))
    
    def _print_results(self):
        """Print validation results."""
        print("\n" + "="*70)
        print("DEPLOYMENT VALIDATION RESULTS")
        print("="*70)
        
        for service, status, message in self.results:
            status_icon = "✓" if status else "✗"
            status_text = "PASS" if status else "FAIL"
            print(f"{status_icon} {service:20s} [{status_text}] {message}")
        
        print("="*70)
        
        passed = sum(1 for _, status, _ in self.results if status)
        total = len(self.results)
        print(f"\nResults: {passed}/{total} services healthy")
        
        if passed == total:
            print("✓ All services are running correctly!")
        else:
            print("✗ Some services failed validation. Check logs above.")
        print()


def main():
    """Main entry point."""
    validator = DeploymentValidator()
    
    print("Granzion Lab Deployment Validator")
    print("Waiting 5 seconds for services to stabilize...")
    time.sleep(5)
    
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
