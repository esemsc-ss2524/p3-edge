"""
Configuration management for P3-Edge application.

Handles application settings, user preferences, and secure credential storage.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet


class ConfigManager:
    """
    Manages application configuration and settings.

    Provides secure storage for sensitive data like API credentials.
    """

    def __init__(self, config_dir: str = "config") -> None:
        """
        Initialize configuration manager.

        Args:
            config_dir: Directory for configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Configuration file paths
        self.config_file = self.config_dir / "app_config.json"
        self.credentials_file = self.config_dir / "credentials.enc"
        self.key_file = self.config_dir / ".key"

        # In-memory configuration
        self.config: Dict[str, Any] = {}
        self.credentials: Dict[str, Any] = {}

        # Initialize encryption
        self._init_encryption()

        # Load configuration
        self.load_config()

    def _init_encryption(self) -> None:
        """Initialize encryption for credentials."""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new encryption key
            self.encryption_key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self.encryption_key)
            # Restrict file permissions (Unix-like systems)
            if os.name != 'nt':  # Not Windows
                os.chmod(self.key_file, 0o600)

        self.cipher = Fernet(self.encryption_key)

    def load_config(self) -> None:
        """Load configuration from files."""
        # Load application config
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            # Set default configuration
            self.config = self._get_default_config()
            self.save_config()

        # Load encrypted credentials
        if self.credentials_file.exists():
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            self.credentials = json.loads(decrypted_data.decode())

    def save_config(self) -> None:
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def save_credentials(self) -> None:
        """Save encrypted credentials to file."""
        json_data = json.dumps(self.credentials).encode()
        encrypted_data = self.cipher.encrypt(json_data)

        with open(self.credentials_file, 'wb') as f:
            f.write(encrypted_data)

        # Restrict file permissions
        if os.name != 'nt':
            os.chmod(self.credentials_file, 0o600)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "app_version": "0.1.0",
            "database": {
                "path": "data/p3edge.db",
                "encrypted": True,
                "backup_enabled": True,
                "backup_interval_days": 7
            },
            "ui": {
                "theme": "light",
                "font_size": 12,
                "window_width": 1024,
                "window_height": 768
            },
            "data_sources": {
                "smart_fridge_enabled": False,
                "smart_fridge_api_url": "",
                "receipt_scan_enabled": True,
                "email_parsing_enabled": False
            },
            "forecasting": {
                "update_interval_hours": 24,
                "confidence_threshold": 0.7,
                "forecast_horizon_days": 30
            },
            "orders": {
                "auto_approval_enabled": False,
                "approval_threshold": 50.0,
                "max_daily_orders": 2
            },
            "privacy": {
                "conversation_retention_days": 30,
                "data_retention_days": 365,
                "telemetry_enabled": False
            },
            "logging": {
                "level": "INFO",
                "max_file_size_mb": 10,
                "backup_count": 5
            },
            "llm": {
                "provider": "ollama",  # "ollama" or "gemini"
                "ollama": {
                    "model": "gemma3n:e2b-it-q4_K_M",
                    "base_url": "http://localhost:11434"
                },
                "gemini": {
                    "model": "gemini-2.5-flash-lite",
                    "temperature": 0.3,
                    "api_key_env": "GOOGLE_API_KEY"
                }
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports dot notation, e.g., "database.path")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            save: Whether to save immediately
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

        if save:
            self.save_config()

    def get_credential(self, key: str) -> Optional[str]:
        """
        Get encrypted credential.

        Args:
            key: Credential key

        Returns:
            Credential value or None if not found
        """
        return self.credentials.get(key)

    def set_credential(self, key: str, value: str, save: bool = True) -> None:
        """
        Set encrypted credential.

        Args:
            key: Credential key
            value: Credential value
            save: Whether to save immediately
        """
        self.credentials[key] = value
        if save:
            self.save_credentials()

    def remove_credential(self, key: str, save: bool = True) -> bool:
        """
        Remove a credential.

        Args:
            key: Credential key
            save: Whether to save immediately

        Returns:
            True if credential was removed
        """
        if key in self.credentials:
            del self.credentials[key]
            if save:
                self.save_credentials()
            return True
        return False

    def has_credential(self, key: str) -> bool:
        """
        Check if credential exists.

        Args:
            key: Credential key

        Returns:
            True if credential exists
        """
        return key in self.credentials

    def get_all_credentials(self) -> Dict[str, str]:
        """
        Get all credentials (for admin/debugging only).

        Returns:
            Dictionary of all credentials
        """
        return self.credentials.copy()

    def clear_credentials(self) -> None:
        """Clear all credentials."""
        self.credentials.clear()
        self.save_credentials()

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self.config = self._get_default_config()
        self.save_config()

    def export_config(self, export_path: str, include_credentials: bool = False) -> None:
        """
        Export configuration to file.

        Args:
            export_path: Path to export file
            include_credentials: Whether to include encrypted credentials
        """
        export_data = {
            "config": self.config,
        }

        if include_credentials:
            export_data["credentials"] = self.credentials

        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)

    def import_config(self, import_path: str) -> None:
        """
        Import configuration from file.

        Args:
            import_path: Path to import file
        """
        with open(import_path, 'r') as f:
            import_data = json.load(f)

        if "config" in import_data:
            self.config = import_data["config"]
            self.save_config()

        if "credentials" in import_data:
            self.credentials = import_data["credentials"]
            self.save_credentials()

    def get_database_encryption_key(self) -> Optional[str]:
        """
        Get database encryption key.

        Returns:
            Database encryption key or None if not set
        """
        return self.get_credential("database_encryption_key")

    def set_database_encryption_key(self, key: str) -> None:
        """
        Set database encryption key.

        Args:
            key: Encryption key
        """
        self.set_credential("database_encryption_key", key)

    def get_vendor_credentials(self, vendor: str) -> Dict[str, Optional[str]]:
        """
        Get credentials for a specific vendor.

        Args:
            vendor: Vendor name (amazon, walmart)

        Returns:
            Dictionary with access_token and refresh_token
        """
        return {
            "access_token": self.get_credential(f"{vendor}_access_token"),
            "refresh_token": self.get_credential(f"{vendor}_refresh_token"),
            "client_id": self.get_credential(f"{vendor}_client_id"),
            "client_secret": self.get_credential(f"{vendor}_client_secret"),
        }

    def set_vendor_credentials(
        self,
        vendor: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> None:
        """
        Set credentials for a specific vendor.

        Args:
            vendor: Vendor name
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            client_id: OAuth client ID
            client_secret: OAuth client secret
        """
        if access_token:
            self.set_credential(f"{vendor}_access_token", access_token, save=False)
        if refresh_token:
            self.set_credential(f"{vendor}_refresh_token", refresh_token, save=False)
        if client_id:
            self.set_credential(f"{vendor}_client_id", client_id, save=False)
        if client_secret:
            self.set_credential(f"{vendor}_client_secret", client_secret, save=False)

        self.save_credentials()


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get global configuration manager instance.

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reset_config_manager() -> None:
    """Reset global configuration manager (mainly for testing)."""
    global _config_manager
    _config_manager = None
