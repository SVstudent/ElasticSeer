"""
ElasticSeer Elasticsearch Index Mappings (Serverless Compatible)

Simplified mappings for Elasticsearch Serverless that don't include:
- Shard/replica settings (managed automatically)
- ILM policies (not supported in serverless)
- Time series mode (not supported in serverless)
"""

from typing import Dict, Any, List
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Serverless-Compatible Index Mappings
# ============================================================================

METRICS_INDEX_MAPPING = {
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
                "type": "keyword"
            },
            "environment": {
                "type": "keyword"
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
                "type": "keyword"
            },
            "trace_id": {
                "type": "keyword"
            },
            "span_id": {
                "type": "keyword"
            },
            "environment": {
                "type": "keyword"
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
    
    # Create all indices
    for index_name, mapping in indices.items():
        results[index_name] = create_index(es_client, index_name, mapping, overwrite)
    
    return results


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
