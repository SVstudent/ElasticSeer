#!/usr/bin/env python3
"""
Initialize Elasticsearch indices for ElasticSeer

This script creates all required Elasticsearch indices with their mappings.
Run this before starting the ElasticSeer application.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from elasticsearch import Elasticsearch
from app.elasticsearch_mappings_serverless import create_all_indices, verify_all_indices
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize Elasticsearch indices"""
    try:
        # Create Elasticsearch client
        logger.info(f"Connecting to Elasticsearch at {settings.elasticsearch_url}")
        
        # Build connection parameters
        es_params = {
            "hosts": [settings.elasticsearch_url],
            "verify_certs": True
        }
        
        # Use API key if available, otherwise use basic auth
        if settings.elasticsearch_api_key:
            es_params["api_key"] = settings.elasticsearch_api_key
        elif settings.elasticsearch_user and settings.elasticsearch_password:
            es_params["basic_auth"] = (settings.elasticsearch_user, settings.elasticsearch_password)
        
        es_client = Elasticsearch(**es_params)
        
        # Test connection
        if not es_client.ping():
            logger.error("Failed to connect to Elasticsearch")
            sys.exit(1)
        
        logger.info("Successfully connected to Elasticsearch")
        
        # Check if indices already exist
        existing = verify_all_indices(es_client)
        if all(existing.values()):
            logger.info("All indices already exist:")
            for index_name, exists in existing.items():
                logger.info(f"  ✓ {index_name}")
            
            response = input("\nDo you want to recreate them? This will DELETE all data! (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Skipping index creation")
                return
            overwrite = True
        else:
            overwrite = False
            logger.info("Creating missing indices...")
        
        # Create indices
        results = create_all_indices(es_client, overwrite=overwrite)
        
        # Print results
        logger.info("\nIndex creation results:")
        for index_name, success in results.items():
            status = "✓" if success else "✗"
            logger.info(f"  {status} {index_name}")
        
        # Verify all indices exist
        verification = verify_all_indices(es_client)
        if all(verification.values()):
            logger.info("\n✓ All indices created successfully!")
        else:
            logger.error("\n✗ Some indices failed to create:")
            for index_name, exists in verification.items():
                if not exists:
                    logger.error(f"  ✗ {index_name}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error initializing Elasticsearch: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
