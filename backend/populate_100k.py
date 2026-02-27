#!/usr/bin/env python3
"""
Populate Elasticsearch with exactly:
- 100,000 metrics data points (service-metrics index)
- 100,000 anomaly records (metrics index with is_anomaly=True)
Spread across all 5 services, multiple regions, multiple metric types.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
import random
from elasticsearch import Elasticsearch, helpers
from app.core.config import settings

es = Elasticsearch(
    hosts=[settings.elasticsearch_url],
    api_key=settings.elasticsearch_api_key,
    verify_certs=True
)

SERVICES = ["api-gateway", "auth-service", "cache", "database", "payment-service"]
REGIONS = ["us-west-1", "us-east-1", "eu-west-1"]
ENVIRONMENTS = ["production", "staging"]

METRIC_TYPES = {
    "response_time_ms": {"min": 50, "max": 500, "anomaly_min": 800, "anomaly_max": 5000},
    "error_rate": {"min": 0.01, "max": 2.0, "anomaly_min": 5.0, "anomaly_max": 25.0},
    "cpu_usage": {"min": 10, "max": 70, "anomaly_min": 85, "anomaly_max": 100},
    "memory_usage": {"min": 30, "max": 75, "anomaly_min": 88, "anomaly_max": 100},
    "request_count": {"min": 100, "max": 5000, "anomaly_min": 50, "anomaly_max": 80},
    "throughput_mbps": {"min": 50, "max": 500, "anomaly_min": 5, "anomaly_max": 30},
    "disk_io_ops": {"min": 100, "max": 2000, "anomaly_min": 4000, "anomaly_max": 10000},
    "connection_pool_used": {"min": 5, "max": 80, "anomaly_min": 90, "anomaly_max": 100},
}

def generate_docs(count, is_anomaly, index_name):
    """Generate count documents for bulk indexing."""
    now = datetime.utcnow()
    docs = []
    for i in range(count):
        service = random.choice(SERVICES)
        region = random.choice(REGIONS)
        env = random.choice(ENVIRONMENTS)
        metric_name = random.choice(list(METRIC_TYPES.keys()))
        config = METRIC_TYPES[metric_name]
        
        # Spread over last 7 days
        offset_seconds = random.randint(0, 7 * 24 * 3600)
        timestamp = now - timedelta(seconds=offset_seconds)
        
        if is_anomaly:
            value = round(random.uniform(config["anomaly_min"], config["anomaly_max"]), 2)
        else:
            value = round(random.uniform(config["min"], config["max"]), 2)
        
        doc = {
            "_index": index_name,
            "_source": {
                "@timestamp": timestamp.isoformat(),
                "metric_name": metric_name,
                "value": value,
                "service": service,
                "region": region,
                "environment": env,
                "is_anomaly": is_anomaly,
            }
        }
        docs.append(doc)
        
        if len(docs) >= 5000:
            yield from docs
            count_so_far = i + 1
            print(f"  {'Anomalies' if is_anomaly else 'Metrics'}: {count_so_far:,}/{count:,} generated...")
            docs = []
    
    if docs:
        yield from docs


def main():
    print("=" * 60)
    print("ElasticSeer Data Population")
    print("Target: 100,000 metrics + 100,000 anomalies")
    print("=" * 60)
    
    # 1. Index 100,000 normal metrics into service-metrics
    print("\n📊 Indexing 100,000 metrics into 'service-metrics'...")
    success, errors = helpers.bulk(es, generate_docs(100_000, False, "service-metrics"), 
                                    chunk_size=5000, raise_on_error=False)
    print(f"  ✅ Metrics indexed: {success:,} success, {len(errors) if isinstance(errors, list) else errors} errors")
    
    # 2. Index 100,000 anomalies into metrics (where Observer reads from)
    print("\n🚨 Indexing 100,000 anomalies into 'metrics'...")
    success2, errors2 = helpers.bulk(es, generate_docs(100_000, True, "metrics"),
                                      chunk_size=5000, raise_on_error=False)
    print(f"  ✅ Anomalies indexed: {success2:,} success, {len(errors2) if isinstance(errors2, list) else errors2} errors")
    
    # 3. Refresh
    print("\n🔄 Refreshing indices...")
    es.indices.refresh(index="service-metrics")
    es.indices.refresh(index="metrics")
    
    # 4. Verify
    sm_count = es.count(index="service-metrics")["count"]
    m_count = es.count(index="metrics", body={"query": {"term": {"is_anomaly": True}}})["count"]
    
    print(f"\n{'=' * 60}")
    print(f"✅ DONE!")
    print(f"  service-metrics: {sm_count:,} documents")
    print(f"  metrics (anomalies): {m_count:,} documents")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
