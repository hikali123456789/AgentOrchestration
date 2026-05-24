#!/usr/bin/env python3
"""
Container release push script with registry namespace allowlist validation.

Validates image tags and registry namespaces against approved allowlist
before pushing to prevent unintended releases.
"""

import argparse
import logging
import re
import sys
from typing import Set, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class RegistryTarget:
    """Parsed container registry target."""
    host: str
    namespace: str
    image: str
    tag: str
    
    @property
    def full_path(self) -> str:
        return f"{self.host}/{self.namespace}/{self.image}:{self.tag}"


class PushValidationError(Exception):
    """Raised when push validation fails."""
    pass


class ReleasePushValidator:
    """
    Validates container release push targets against approved allowlist.
    
    Ensures images are only pushed to approved registry namespaces,
    preventing accidental releases to unintended locations.
    """
    
    # Approved registry namespaces (host/namespace pairs)
    APPROVED_REGISTRIES: Set[Tuple[str, str]] = {
        ("docker.io", "agentorch"),
        ("ghcr.io", "orchestration-agent"),
        ("registry.example.com", "production"),
    }
    
    # Valid tag patterns (semver, git sha, latest)
    VALID_TAG_PATTERNS = [
        r"^latest$",
        r"^v\d+\.\d+\.\d+$",  # semver
        r"^\d+\.\d+\.\d+$",   # plain semver
        r"^[a-f0-9]{7,40}$",   # git sha
    ]
    
    def __init__(self, approved_registries: Set[Tuple[str, str]] = None):
        self.approved_registries = approved_registries or self.APPROVED_REGISTRIES
    
    def parse_target(self, image_ref: str) -> RegistryTarget:
        """
        Parse a container image reference.
        
        Args:
            image_ref: Full image reference (e.g., docker.io/ns/img:tag)
            
        Returns:
            Parsed RegistryTarget
        """
        # Remove protocol if present
        image_ref = image_ref.replace("https://", "").replace("http://", "")
        
        # Split tag
        if ":" in image_ref:
            image_part, tag = image_ref.rsplit(":", 1)
        else:
            image_part = image_ref
            tag = "latest"
        
        # Split into components
        parts = image_part.split("/")
        
        if len(parts) == 3:
            host, namespace, image = parts
        elif len(parts) == 2:
            # Default to docker.io
            host = "docker.io"
            namespace, image = parts
        else:
            raise PushValidationError(f"Invalid image reference format: {image_ref}")
        
        return RegistryTarget(host=host, namespace=namespace, image=image, tag=tag)
    
    def validate_tag(self, tag: str) -> bool:
        """
        Validate image tag format.
        
        Args:
            tag: Image tag to validate
            
        Returns:
            True if valid
        """
        for pattern in self.VALID_TAG_PATTERNS:
            if re.match(pattern, tag):
                return True
        
        logger.error(f"Invalid tag format: {tag}")
        return False
    
    def validate_registry(self, target: RegistryTarget) -> bool:
        """
        Validate registry namespace is in allowlist.
        
        Args:
            target: Parsed registry target
            
        Returns:
            True if approved
        """
        registry_key = (target.host, target.namespace)
        
        if registry_key not in self.approved_registries:
            logger.error(
                f"Registry namespace not approved: {target.host}/{target.namespace}"
            )
            logger.info(f"Approved registries: {self.approved_registries}")
            return False
        
        return True
    
    def validate(self, image_ref: str) -> RegistryTarget:
        """
        Validate image reference for push.
        
        Args:
            image_ref: Full image reference
            
        Returns:
            Validated RegistryTarget
            
        Raises:
            PushValidationError: If validation fails
        """
        logger.info(f"Validating push target: {image_ref}")
        
        # Parse target
        try:
            target = self.parse_target(image_ref)
        except PushValidationError:
            raise
        except Exception as e:
            raise PushValidationError(f"Failed to parse image reference: {e}")
        
        # Validate tag
        if not self.validate_tag(target.tag):
            raise PushValidationError(f"Invalid tag: {target.tag}")
        
        # Validate registry namespace (allowlist check)
        if not self.validate_registry(target):
            raise PushValidationError(
                f"Registry not in allowlist: {target.host}/{target.namespace}"
            )
        
        logger.info(f"Push target validated: {target.full_path}")
        logger.info(f"Approved registry: {target.host}/{target.namespace}")
        
        return target
    
    def push(self, image_ref: str, dry_run: bool = False) -> bool:
        """
        Validate and push image.
        
        Args:
            image_ref: Image reference to push
            dry_run: If True, only validate without pushing
            
        Returns:
            True if successful
        """
        try:
            target = self.validate(image_ref)
        except PushValidationError as e:
            logger.error(f"Push validation failed: {e}")
            return False
        
        if dry_run:
            logger.info(f"[DRY RUN] Would push to: {target.full_path}")
            return True
        
        # Actual push would happen here
        logger.info(f"Pushing to: {target.full_path}")
        # subprocess.run(["docker", "push", target.full_path], check=True)
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Container release push script with allowlist validation"
    )
    parser.add_argument("image", help="Image reference to push")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only, do not push"
    )
    parser.add_argument(
        "--approved-registry",
        action="append",
        help="Additional approved registry (format: host/namespace)"
    )
    
    args = parser.parse_args()
    
    # Build validator with optional additional registries
    approved = set(ReleasePushValidator.APPROVED_REGISTRIES)
    if args.approved_registry:
        for reg in args.approved_registry:
            parts = reg.split("/")
            if len(parts) == 2:
                approved.add((parts[0], parts[1]))
    
    validator = ReleasePushValidator(approved_registries=approved)
    
    # Validate and push
    success = validator.push(args.image, dry_run=args.dry_run)
    
    if not success:
        sys.exit(1)
    
    logger.info("Push completed successfully")


if __name__ == "__main__":
    main()