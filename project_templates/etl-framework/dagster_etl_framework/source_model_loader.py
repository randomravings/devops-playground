"""Load source model from YAML configuration file."""

import yaml
from pathlib import Path
from typing import Dict, List
from dagster_etl_framework.source_model import (
    SourceFieldType, SourceField, Source, Relation,
    DimensionField, DimensionSource, Dimension,
    FactField, FactSource, Fact, DimensionLookup,
    SourceModel
)


def build_source_model_from_dict(config: dict) -> SourceModel:
    """
    Build source model from a configuration dictionary.
    
    Args:
        config: Dictionary containing 'sources', 'dimensions', and/or 'facts' sections
    
    Returns:
        SourceModel instance populated from configuration
    """
    model = SourceModel(sources={}, relations={}, dimensions={}, facts={})
    
    # First pass: Create all sources
    if 'sources' in config:
        for source_name, source_config in config['sources'].items():
            fields_list = []
            for field_config in source_config['fields']:
                field = SourceField(
                    name=field_config['name'],
                    dtype=field_config.get('dtype')
                )
                fields_list.append(field)
            
            source = Source(
                name=source_name,
                ext_name=source_config['ext_name'],
                fields={field.name: field for field in fields_list},
                primary_key=source_config.get('primary_key')
            )
            
            model.sources[source_name] = source
        
        # Second pass: Create all relations
        for source_name, source_config in config['sources'].items():
            if 'relations' in source_config:
                relations = {}
                for relation_config in source_config['relations']:
                    primary_name = relation_config['primary']
                    relation = Relation(
                        foreign=source_name,
                        foreign_key=relation_config['foreign_key'],
                        primary=primary_name
                    )
                    relations[primary_name] = relation
                
                model.relations[source_name] = relations
    
    # Third pass: Create all dimensions
    if 'dimensions' in config:
        for dim_name, dim_config in config['dimensions'].items():
            dim_sources = {}
            for source_name, source_config in dim_config['sources'].items():
                fields_list = []
                for field_config in source_config['fields']:
                    field = DimensionField(
                        name=field_config['name'],
                        type=SourceFieldType(field_config['type']),
                        source_field=field_config.get('source_field'),
                        alias=field_config.get('alias')
                    )
                    fields_list.append(field)
                
                dim_source = DimensionSource(
                    name=source_name,
                    fields=fields_list
                )
                dim_sources[source_name] = dim_source
            
            dimension = Dimension(
                name=dim_name,
                sources=dim_sources
            )
            model.dimensions[dim_name] = dimension
    
    # Fourth pass: Create all facts
    if 'facts' in config:
        for fact_name, fact_config in config['facts'].items():
            fact_sources = {}
            for source_name, source_config in fact_config['sources'].items():
                fields_list = []
                for field_config in source_config['fields']:
                    field = FactField(
                        name=field_config['name'],
                        type=SourceFieldType(field_config['type']),
                        source_field=field_config.get('source_field'),
                        alias=field_config.get('alias')
                    )
                    fields_list.append(field)
                
                fact_source = FactSource(
                    name=source_name,
                    fields=fields_list
                )
                fact_sources[source_name] = fact_source
            
            # Parse dimension lookups if present
            dimension_lookups = []
            if 'dimension_lookups' in fact_config:
                for lookup_config in fact_config['dimension_lookups']:
                    lookup = DimensionLookup(
                        dimension=lookup_config['dimension'],
                        business_keys=lookup_config['business_keys'],
                        surrogate_key=lookup_config['surrogate_key'],
                        lookup_strategy=lookup_config.get('lookup_strategy', 'current')
                    )
                    dimension_lookups.append(lookup)
            
            fact = Fact(
                name=fact_name,
                sources=fact_sources,
                dimension_lookups=dimension_lookups
            )
            model.facts[fact_name] = fact
    
    return model


def load_source_model(config_path: str = None) -> SourceModel:
    """
    Load source model from YAML configuration file.
    
    Args:
        config_path: Path to YAML config file. If None, uses default location.
    
    Returns:
        SourceModel instance populated from configuration
    """
    if config_path is None:
        # Default to source_model.yaml in same directory as this file
        config_path = Path(__file__).parent / "source_model.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return build_source_model_from_dict(config)
