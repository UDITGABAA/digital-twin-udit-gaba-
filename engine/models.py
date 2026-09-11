"""Data models and validation schema for Cyber Digital Twin scenarios."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class AssetModel(BaseModel):
    """Represents a cyber or physical infrastructure asset."""
    id: str = Field(..., description="Unique identifier for the asset")
    name: str = Field(..., description="Descriptive asset name")
    type: str = Field(..., description="Asset type (e.g., web_server, database, bastion)")
    zone: str = Field(..., description="Network security zone (e.g., dmz, application, data_secure)")
    ip_address: Optional[str] = Field(None, description="Assigned IP address")
    os: Optional[str] = Field(None, description="Operating system")
    criticality: str = Field("medium", description="Criticality rating: low, medium, high, critical")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")


class IdentityModel(BaseModel):
    """Represents an actor or service identity within the organization."""
    id: str = Field(..., description="Unique identifier for the identity")
    name: str = Field(..., description="Human or service identity name")
    type: str = Field("human", description="Identity type: human, service_account, federated")
    role: str = Field(..., description="Functional role (e.g., customer, staff, administrator)")
    privilege_level: str = Field("standard", description="Privilege classification")
    department: Optional[str] = Field(None, description="Associated business department")


class ControlModel(BaseModel):
    """Represents a defensive security control implemented in the environment."""
    id: str = Field(..., description="Unique control identifier")
    name: str = Field(..., description="Control name")
    type: str = Field(..., description="Control type (e.g., authentication, network_defense, host_defense)")
    status: str = Field("active", description="Operational status: active, degraded, disabled")
    enabled: bool = Field(True, description="Whether this security control is actively enforced")
    framework_reference: Optional[str] = Field(None, description="Security framework mapping (e.g. NIST, CIS)")
    covered_entities: List[str] = Field(default_factory=list, description="IDs of assets or identities guarded")

    def is_active(self) -> bool:
        """Check if control is active and enabled."""
        if not self.enabled:
            return False
        return self.status.lower() not in ("disabled", "inactive", "off")


class RelationshipModel(BaseModel):
    """Represents a connection, trust relation, or access link between twin entities."""
    id: str = Field(..., description="Unique relationship identifier")
    source: str = Field(..., description="Source entity ID")
    target: str = Field(..., description="Target entity ID")
    relation_type: str = Field(..., description="Relationship semantic (e.g., ACCESSES, CONNECTS_TO, ROUTES_TO, REMOTE_ACCESS)")
    protocol: Optional[str] = Field(None, description="Communication protocol (e.g., HTTPS, gRPC, SSH)")
    port: Optional[int] = Field(None, description="Target port number")
    encrypted: bool = Field(True, description="Whether transit is encrypted")
    requires: Dict[str, List[str]] = Field(default_factory=dict, description="Required capabilities and privileges for traversal")
    grants: Dict[str, List[str]] = Field(default_factory=dict, description="Granted capabilities and privileges upon successful traversal")
    control: Optional[str] = Field(None, description="Enforced security control guarding this relationship (e.g. ctrl-mfa)")


class ScenarioModel(BaseModel):
    """Complete declarative definition of a cyber digital twin scenario."""
    scenario_id: str
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    environment: Optional[str] = None
    assets: List[AssetModel] = Field(default_factory=list)
    identities: List[IdentityModel] = Field(default_factory=list)
    controls: List[ControlModel] = Field(default_factory=list)
    relationships: List[RelationshipModel] = Field(default_factory=list)
