"""Dataset export utilities with schema versioning."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

# Current schema version - increment when field structure changes
EXPORT_SCHEMA_VERSION = "1.0.0"
SCHEMA_COMPATIBILITY = {"minimum_supported": "1.0.0"}


class ExportMetadata:
    """Metadata for dataset exports including schema version and field dictionary."""

    def __init__(
        self,
        schema_version: str = EXPORT_SCHEMA_VERSION,
        generated_at: Optional[datetime] = None,
        fields: Optional[Dict[str, str]] = None
    ):
        self.schema_version = schema_version
        self.generated_at = generated_at or datetime.now(timezone.utc)
        self.fields = fields or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "schema_compatibility": SCHEMA_COMPATIBILITY,
            "generated_at": self.generated_at.isoformat(),
            "fields": self.fields
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportMetadata":
        return cls(
            schema_version=data.get("schema_version", EXPORT_SCHEMA_VERSION),
            generated_at=datetime.fromisoformat(data["generated_at"]) if "generated_at" in data else None,
            fields=data.get("fields", {})
        )


class DatasetExporter:
    """Exports datasets with schema versioning and field dictionaries."""

    def __init__(self, output_dir: str = "exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        data: List[Dict[str, Any]],
        name: str,
        fields: Dict[str, str],
        format: str = "json"
    ) -> tuple[Path, Path]:
        """
        Export dataset with metadata sidecar.

        Args:
            data: List of records to export
            name: Base name for the export file
            fields: Dictionary mapping field names to descriptions
            format: Export format (json)

        Returns:
            Tuple of (data_file_path, metadata_file_path)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"{name}_{timestamp}"

        # Create metadata
        metadata = ExportMetadata(fields=fields)

        # Write data file with embedded schema version in header
        data_file = self.output_dir / f"{base_name}.json"
        export_payload = {
            "_metadata": metadata.to_dict(),
            "records": data
        }

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(export_payload, f, indent=2, default=str)

        # Write metadata sidecar
        meta_file = self.output_dir / f"{base_name}.metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        return data_file, meta_file

    def validate_schema_version(self, metadata: Dict[str, Any]) -> bool:
        """
        Validate that the schema version is supported.

        Args:
            metadata: Metadata dictionary from an export file

        Returns:
            True if schema version is supported, False otherwise
        """
        version = metadata.get("schema_version", "0.0.0")
        min_supported = SCHEMA_COMPATIBILITY["minimum_supported"]

        # Simple version comparison (assumes semver)
        def parse_version(v: str) -> tuple:
            return tuple(int(x) for x in v.split("."))

        return parse_version(version) >= parse_version(min_supported)


def export_agents_snapshot(registry, output_dir: str = "exports") -> tuple[Path, Path]:
    """
    Export a snapshot of agent registry data.

    Args:
        registry: AgentRegistry instance
        output_dir: Directory for export files

    Returns:
        Tuple of (data_file_path, metadata_file_path)
    """
    exporter = DatasetExporter(output_dir)

    agents = registry.list()
    fields = {
        "id": "Unique agent identifier",
        "name": "Agent display name",
        "type": "Agent type classification",
        "status": "Current agent status",
        "created_at": "Agent registration timestamp",
        "config": "Agent configuration dictionary"
    }

    return exporter.export(
        data=agents,
        name="agents_snapshot",
        fields=fields
    )