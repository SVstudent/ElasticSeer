"""
ElasticSeer Elasticsearch Index Mappings

This module defines Elasticsearch index mappings for all data indices used in the
ElasticSeer platform. Each mapping is optimized for its specific use case:
- Time-series mappings for metrics and logs
- Vector embeddings for semantic search
- Hybrid search (BM25 + vector) for incidents and code

All mappings follow Elasticsearch best practices for performance and scalability.
"""

from typing import Dict, Any, List
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Index Mappings
# ============================================================================

METRICS_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "refresh_interval": "5s",  # Real-time search requirement
        "index": {
            "mode": "time_series",
            "routing_path": ["service"],
            "sort": {
                "field": ["@timestamp"],
                "order": ["desc"]
            }
        }
    },
    "mappings": {
        "properties": {
            "@timestamp": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis"
            },
            "metric_name": {
                "type": "keyword"
            },
            "value": {
                "type": "float"
            },
            "service": {
                "type": "keyword",
                "time_series_dimension": True
            },
            "environment": {
                "type": "keyword",
                "time_series_dimension": True
            },
            "tags": {
                "type": "object",
                "enabled": True
            }
        }
    }
}


INCIDENT_HISTORY_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "refresh_interval": "5s",
        "analysis": {
            "analyzer": {
                "incident_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id": {
                "type": "keyword"
            },
            "severity": {
                "type": "keyword"
            },
            "status": {
                "type": "keyword"
            },
            "anomaly": {
                "type": "object",
                "properties": {
                    "metric": {"type": "keyword"},
                    "current_value": {"type": "float"},
                    "expected_value": {"type": "float"},
                    "deviation_sigma": {"type": "float"},
                    "severity": {"type": "keyword"},
                    "detected_at": {"type": "date"},
                    "service": {"type": "keyword"},
                    "environment": {"type": "keyword"}
                }
            },
            "diagnosis": {
                "type": "object",
                "properties": {
                    "root_cause": {
                        "type": "text",
                        "analyzer": "incident_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "affected_component": {"type": "keyword"},
                    "impact_explanation": {
                        "type": "text",
                        "analyzer": "incident_analyzer"
                    },
                    "confidence": {"type": "float"}
                }
            },
            "remediation": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "keyword"},
                    "explanation": {
                        "type": "text",
                        "analyzer": "incident_analyzer"
                    }
                }
            },
            "timeline": {
                "type": "nested",
                "properties": {
                    "timestamp": {"type": "date"},
                    "event_type": {"type": "keyword"},
                    "description": {"type": "text"}
                }
            },
            "created_at": {
                "type": "date"
            },
            "resolved_at": {
                "type": "date"
            },
            "mttr": {
                "type": "float"
            },
            "embedding": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "cosine"
            },
            "description": {
                "type": "text",
                "analyzer": "incident_analyzer"
            }
        }
    }
}


CODE_REPOSITORY_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "refresh_interval": "5s",
        "analysis": {
            "analyzer": {
                "code_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "file_path": {
                "type": "keyword"
            },
            "content": {
                "type": "text",
                "analyzer": "code_analyzer",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256}
                }
            },
            "embedding": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "cosine"
            },
            "functions": {
                "type": "nested",
                "properties": {
                    "name": {"type": "keyword"},
                    "signature": {"type": "text", "analyzer": "code_analyzer"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "parameters": {"type": "keyword"},
                    "return_type": {"type": "keyword"}
                }
            },
            "last_modified": {
                "type": "date"
            },
            "repository": {
                "type": "keyword"
            },
            "language": {
                "type": "keyword"
            },
            "size_bytes": {
                "type": "long"
            }
        }
    }
}


ANOMALY_RECORDS_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "refresh_interval": "5s",
        "index": {
            "lifecycle": {
                "name": "anomaly_records_policy"
            }
        }
    },
    "mappings": {
        "properties": {
            "metric": {
                "type": "keyword"
            },
            "current_value": {
                "type": "float"
            },
            "expected_value": {
                "type": "float"
            },
            "deviation_sigma": {
                "type": "float"
            },
            "severity": {
                "type": "keyword"
            },
            "detected_at": {
                "type": "date"
            },
            "service": {
                "type": "keyword"
            },
            "environment": {
                "type": "keyword"
            },
            "incident_id": {
                "type": "keyword"
            }
        }
    }
}


LOGS_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "refresh_interval": "5s",
        "index": {
            "mode": "time_series",
            "routing_path": ["service"],
            "sort": {
                "field": ["@timestamp"],
                "order": ["desc"]
            }
        }
    },
    "mappings": {
        "properties": {
            "@timestamp": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis"
            },
            "level": {
                "type": "keyword"
            },
            "message": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 512}
                }
            },
            "service": {
                "type": "keyword",
                "time_series_dimension": True
            },
            "trace_id": {
                "type": "keyword"
            },
            "span_id": {
                "type": "keyword"
            },
            "environment": {
                "type": "keyword",
                "time_series_dimension": True
            },
            "error": {
                "type": "object",
                "properties": {
                    "type": {"type": "keyword"},
                    "message": {"type": "text"},
                    "stack_trace": {"type": "text"}
                }
            }
        }
    }
}


# ============================================================================
# Index Lifecycle Management Policies
# ============================================================================

ANOMALY_RECORDS_ILM_POLICY = {
    "policy": {
        "phases": {
            "hot": {
                "min_age": "0ms",
                "actions": {
                    "rollover": {
                        "max_age": "7d",
                        "max_primary_shard_size": "50gb"
                    }
                }
            },
            "warm": {
                "min_age": "7d",
                "actions": {
                    "shrink": {
                        "number_of_shards": 1
                    },
                    "forcemerge": {
                        "max_num_segments": 1
                    }
                }
            },
            "cold": {
                "min_age": "30d",
                "actions": {
                    "freeze": {}
                }
            },
            "delete": {
                "min_age": "90d",
                "actions": {
                    "delete": {}
                }
            }
        }
    }
}


# ============================================================================
# Helper Functions
# ============================================================================

def create_index(
    es_client: Elasticsearch,
    index_name: str,
    mapping: Dict[str, Any],
    overwrite: bool = False
) -> bool:
    """
    Create an Elasticsearch index with the specified mapping.
    
    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index to create
        mapping: Index mapping configuration
        overwrite: If True, delete existing index before creating
        
    Returns:
        True if index was created successfully, False otherwise
    """
    try:
        # Check if index exists
        if es_client.indices.exists(index=index_name):
            if overwrite:
                logger.info(f"Deleting existing index: {index_name}")
                es_client.indices.delete(index=index_name)
            else:
                logger.info(f"Index already exists: {index_name}")
                return False
        
        # Create index
        logger.info(f"Creating index: {index_name}")
        es_client.indices.create(index=index_name, body=mapping)
        logger.info(f"Successfully created index: {index_name}")
        return True
        
    except RequestError as e:
        logger.error(f"Failed to create index {index_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating index {index_name}: {e}")
        return False


def index_exists(es_client: Elasticsearch, index_name: str) -> bool:
    """
    Check if an index exists.
    
    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index to check
        
    Returns:
        True if index exists, False otherwise
    """
    try:
        return es_client.indices.exists(index=index_name)
    except Exception as e:
        logger.error(f"Error checking if index exists {index_name}: {e}")
        return False


def update_mapping(
    es_client: Elasticsearch,
    index_name: str,
    mapping_update: Dict[str, Any]
) -> bool:
    """
    Update an existing index mapping.
    
    Note: Only new fields can be added. Existing field types cannot be changed.
    
    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index to update
        mapping_update: Mapping properties to add
        
    Returns:
        True if mapping was updated successfully, False otherwise
    """
    try:
        if not es_client.indices.exists(index=index_name):
            logger.error(f"Cannot update mapping: index {index_name} does not exist")
            return False
        
        logger.info(f"Updating mapping for index: {index_name}")
        es_client.indices.put_mapping(index=index_name, body=mapping_update)
        logger.info(f"Successfully updated mapping for index: {index_name}")
        return True
        
    except RequestError as e:
        logger.error(f"Failed to update mapping for {index_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating mapping for {index_name}: {e}")
        return False


def delete_index(es_client: Elasticsearch, index_name: str) -> bool:
    """
    Delete an index.
    
    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index to delete
        
    Returns:
        True if index was deleted successfully, False otherwise
    """
    try:
        if not es_client.indices.exists(index=index_name):
            logger.info(f"Index does not exist: {index_name}")
            return False
        
        logger.info(f"Deleting index: {index_name}")
        es_client.indices.delete(index=index_name)
        logger.info(f"Successfully deleted index: {index_name}")
        return True
        
    except RequestError as e:
        logger.error(f"Failed to delete index {index_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting index {index_name}: {e}")
        return False


def create_ilm_policy(
    es_client: Elasticsearch,
    policy_name: str,
    policy: Dict[str, Any]
) -> bool:
    """
    Create an Index Lifecycle Management policy.
    
    Args:
        es_client: Elasticsearch client instance
        policy_name: Name of the ILM policy
        policy: Policy configuration
        
    Returns:
        True if policy was created successfully, False otherwise
    """
    try:
        logger.info(f"Creating ILM policy: {policy_name}")
        es_client.ilm.put_lifecycle(name=policy_name, body=policy)
        logger.info(f"Successfully created ILM policy: {policy_name}")
        return True
        
    except RequestError as e:
        logger.error(f"Failed to create ILM policy {policy_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating ILM policy {policy_name}: {e}")
        return False


def create_all_indices(
    es_client: Elasticsearch,
    overwrite: bool = False
) -> Dict[str, bool]:
    """
    Create all ElasticSeer indices with their mappings.
    
    Args:
        es_client: Elasticsearch client instance
        overwrite: If True, delete existing indices before creating
        
    Returns:
        Dictionary mapping index names to creation success status
    """
    indices = {
        "metrics": METRICS_INDEX_MAPPING,
        "incident-history": INCIDENT_HISTORY_INDEX_MAPPING,
        "code-repository": CODE_REPOSITORY_INDEX_MAPPING,
        "anomaly-records": ANOMALY_RECORDS_INDEX_MAPPING,
        "logs": LOGS_INDEX_MAPPING
    }
    
    results = {}
    
    # Create ILM policy for anomaly records
    create_ilm_policy(es_client, "anomaly_records_policy", ANOMALY_RECORDS_ILM_POLICY)
    
    # Create all indices
    for index_name, mapping in indices.items():
        results[index_name] = create_index(es_client, index_name, mapping, overwrite)
    
    return results


def get_index_info(es_client: Elasticsearch, index_name: str) -> Dict[str, Any]:
    """
    Get information about an index including mapping and settings.
    
    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index
        
    Returns:
        Dictionary containing index information
    """
    try:
        if not es_client.indices.exists(index=index_name):
            return {"error": f"Index {index_name} does not exist"}
        
        mapping = es_client.indices.get_mapping(index=index_name)
        settings = es_client.indices.get_settings(index=index_name)
        stats = es_client.indices.stats(index=index_name)
        
        return {
            "name": index_name,
            "mapping": mapping,
            "settings": settings,
            "stats": {
                "doc_count": stats["_all"]["primaries"]["docs"]["count"],
                "size_bytes": stats["_all"]["primaries"]["store"]["size_in_bytes"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting info for index {index_name}: {e}")
        return {"error": str(e)}


def list_all_indices(es_client: Elasticsearch) -> List[str]:
    """
    List all ElasticSeer indices.
    
    Args:
        es_client: Elasticsearch client instance
        
    Returns:
        List of index names
    """
    try:
        all_indices = es_client.indices.get_alias(index="*")
        elasticseer_indices = [
            idx for idx in all_indices.keys()
            if idx in ["metrics", "incident-history", "code-repository", 
                      "anomaly-records", "logs"]
        ]
        return elasticseer_indices
        
    except Exception as e:
        logger.error(f"Error listing indices: {e}")
        return []


# ============================================================================
# Development Utilities
# ============================================================================

def recreate_all_indices(es_client: Elasticsearch) -> Dict[str, bool]:
    """
    Delete and recreate all indices. USE WITH CAUTION - deletes all data!
    
    This is useful for development and testing but should NEVER be used in production.
    
    Args:
        es_client: Elasticsearch client instance
        
    Returns:
        Dictionary mapping index names to recreation success status
    """
    logger.warning("Recreating all indices - this will delete all data!")
    return create_all_indices(es_client, overwrite=True)


def verify_all_indices(es_client: Elasticsearch) -> Dict[str, bool]:
    """
    Verify that all required indices exist.
    
    Args:
        es_client: Elasticsearch client instance
        
    Returns:
        Dictionary mapping index names to existence status
    """
    required_indices = [
        "metrics",
        "incident-history",
        "code-repository",
        "anomaly-records",
        "logs"
    ]
    
    results = {}
    for index_name in required_indices:
        results[index_name] = index_exists(es_client, index_name)
    
    return results
