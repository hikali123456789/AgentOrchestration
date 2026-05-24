"""Tests for dataset export with schema versioning."""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from src.common.export import (
    ExportMetadata,
    DatasetExporter,
    export_agents_snapshot,
    EXPORT_SCHEMA_VERSION,
    SCHEMA_COMPATIBILITY
)


class TestExportMetadata:
    """Tests for ExportMetadata class."""

    def test_default_schema_version(self):
        metadata = ExportMetadata()
        assert metadata.schema_version == EXPORT_SCHEMA_VERSION
        assert metadata.schema_version == "1.0.0"

    def test_custom_schema_version(self):
        metadata = ExportMetadata(schema_version="2.0.0")
        assert metadata.schema_version == "2.0.0"

    def test_generated_at_is_utc(self):
        metadata = ExportMetadata()
        assert metadata.generated_at.tzinfo == timezone.utc

    def test_to_dict_contains_required_fields(self):
        metadata = ExportMetadata(fields={"id": "test field"})
        d = metadata.to_dict()
        assert "schema_version" in d
        assert "generated_at" in d
        assert "fields" in d
        assert "schema_compatibility" in d

    def test_from_dict_roundtrip(self):
        original = ExportMetadata(fields={"name": "agent name"})
        d = original.to_dict()
        restored = ExportMetadata.from_dict(d)
        assert restored.schema_version == original.schema_version
        assert restored.fields == original.fields


class TestDatasetExporter:
    """Tests for DatasetExporter class."""

    def test_export_creates_files(self, tmp_path):
        exporter = DatasetExporter(output_dir=str(tmp_path))
        data = [{"id": "1", "name": "agent1"}]
        fields = {"id": "identifier", "name": "display name"}

        data_file, meta_file = exporter.export(data, "test_export", fields)

        assert data_file.exists()
        assert meta_file.exists()

    def test_export_includes_metadata_in_file(self, tmp_path):
        exporter = DatasetExporter(output_dir=str(tmp_path))
        data = [{"id": "1"}]
        fields = {"id": "identifier"}

        data_file, _ = exporter.export(data, "test", fields)

        with open(data_file) as f:
            content = json.load(f)

        assert "_metadata" in content
        assert "schema_version" in content["_metadata"]
        assert "records" in content
        assert content["records"] == data

    def test_export_metadata_sidecar(self, tmp_path):
        exporter = DatasetExporter(output_dir=str(tmp_path))
        data = [{"id": "1"}]
        fields = {"id": "unique identifier"}

        _, meta_file = exporter.export(data, "test", fields)

        with open(meta_file) as f:
            metadata = json.load(f)

        assert metadata["schema_version"] == EXPORT_SCHEMA_VERSION
        assert metadata["fields"] == fields

    def test_validate_supported_schema_version(self, tmp_path):
        exporter = DatasetExporter(output_dir=str(tmp_path))
        metadata = {"schema_version": "1.0.0"}
        assert exporter.validate_schema_version(metadata) is True

    def test_validate_unsupported_schema_version(self, tmp_path):
        exporter = DatasetExporter(output_dir=str(tmp_path))
        metadata = {"schema_version": "0.0.1"}
        assert exporter.validate_schema_version(metadata) is False


class TestExportAgentsSnapshot:
    """Tests for export_agents_snapshot helper."""

    def test_export_agents_snapshot(self, tmp_path):
        # Create mock registry
        class MockRegistry:
            def list(self):
                return [{"id": "a1", "name": "agent1", "type": "worker"}]

        registry = MockRegistry()
        data_file, meta_file = export_agents_snapshot(registry, str(tmp_path))

        assert data_file.exists()
        assert meta_file.exists()

        with open(data_file) as f:
            content = json.load(f)

        assert content["_metadata"]["schema_version"] == EXPORT_SCHEMA_VERSION
        assert "id" in content["_metadata"]["fields"]
        assert len(content["records"]) == 1


class TestSchemaVersionConstants:
    """Tests for schema version constants."""

    def test_schema_version_is_semver(self):
        parts = EXPORT_SCHEMA_VERSION.split(".")
        assert len(parts) == 3
        for p in parts:
            assert p.isdigit()

    def test_compatibility_has_minimum(self):
        assert "minimum_supported" in SCHEMA_COMPATIBILITY
        assert SCHEMA_COMPATIBILITY["minimum_supported"] == EXPORT_SCHEMA_VERSION