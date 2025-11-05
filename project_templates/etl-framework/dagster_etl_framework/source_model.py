"""Data model definitions for ETL source metadata and analytical model."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict


class SourceFieldType(str, Enum):
    """Field type for change tracking in SCD Type 2 dimensions."""
    ATT = "ATT"  # Regular attribute (fact table field)
    KEY = "KEY"  # Business key
    EDT = "EDT"  # Extract date/timestamp
    T1 = "T1"   # Type 1 field (update in place)
    T2 = "T2"   # Type 2 field (create new version)


@dataclass
class SourceField:
    """Source field definition (physical structure only)."""
    # Name of the source field
    name: str
    # Data type to map to (None for auto-detect)
    dtype: str = None


@dataclass
class Source:
    """Source definition (physical data source)."""
    # Name of the source
    name: str
    # Physical name of source (file name, table name, etc.)
    ext_name: str
    # Source field list
    fields: dict[str, SourceField]
    # Primary key field(s) for this source
    primary_key: List[str] = None


@dataclass
class Relation:
    """Relation definition between sources."""
    # The table that is referencing the primary table
    foreign: str
    # Foreign key field(s), order must match primary key order in referenced table
    foreign_key: List[str]
    # The table being referenced
    primary: str


@dataclass
class DimensionField:
    """Field definition within a dimension (analytical model)."""
    # Field name
    name: str
    # Field type for SCD tracking
    type: SourceFieldType
    # Source field name (if different from name)
    source_field: str = None
    # Alias used for disambiguation
    alias: str = None

    def __post_init__(self):
        # Default source_field to name if not provided
        if self.source_field is None:
            self.source_field = self.name


@dataclass
class DimensionSource:
    """Source contribution to a dimension."""
    # Name of the source table
    name: str
    # Fields from this source used in the dimension
    fields: List[DimensionField]


@dataclass
class Dimension:
    """Dimension definition (analytical model)."""
    # Name of the dimension
    name: str
    # Sources that contribute to this dimension
    sources: Dict[str, DimensionSource]


@dataclass
class FactField:
    """Field definition within a fact table (analytical model)."""
    # Field name
    name: str
    # Field type (typically ATT, KEY, or EDT)
    type: SourceFieldType
    # Source field name (if different from name)
    source_field: str = None
    # Alias used for disambiguation
    alias: str = None

    def __post_init__(self):
        # Default source_field to name if not provided
        if self.source_field is None:
            self.source_field = self.name


@dataclass
class FactSource:
    """Source contribution to a fact table."""
    # Name of the source table
    name: str
    # Fields from this source used in the fact
    fields: List[FactField]


@dataclass
class DimensionLookup:
    """Dimension lookup specification for fact table."""
    # Name of the dimension to lookup (e.g., 'dim_customers')
    dimension: str
    # Business keys in the fact staging that map to dimension
    business_keys: List[str]
    # Surrogate key column name in the fact
    surrogate_key: str
    # Lookup strategy: 'current' (SCD current records), 'direct' (non-SCD), 'point_in_time' (SCD as-of date)
    lookup_strategy: str = "current"


@dataclass
class Fact:
    """Fact table definition (analytical model)."""
    # Name of the fact table
    name: str
    # Sources that contribute to this fact
    sources: Dict[str, FactSource]
    # Dimension lookups for translating business keys to surrogate keys
    dimension_lookups: List[DimensionLookup] = field(default_factory=list)


@dataclass
class SourceModel:
    """Complete data model with sources (physical) and analytical model (dimensions/facts)."""
    # Physical sources
    sources: dict[str, Source]
    # Source relationships
    relations: dict[str, dict[str, Relation]]
    # Analytical dimensions
    dimensions: dict[str, Dimension] = None
    # Analytical facts
    facts: dict[str, Fact] = None

    def __post_init__(self):
        # Initialize empty dicts if None
        if self.dimensions is None:
            self.dimensions = {}
        if self.facts is None:
            self.facts = {}
