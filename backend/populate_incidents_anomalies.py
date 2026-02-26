#!/usr/bin/env python3
"""
Add 1000 relevant documents to anomaly-records and incident-history
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
import random
from elasticsearch import Elasticsearch
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def populate_anomalies_and_incidents():
    """Add 1000 anomalies and 1000 incidents"""
    
    es = Elasticsearch(
        hosts=[settings.elasticsearch_url],
        api_key=settings.elasticsearch_api_key,
        verify_certs=True
    )
    
    if not es.ping():
        logger.error("❌ Cannot connect to Elasticsearch")
        return False
    
    logger.info("="*70)
    logger.info("Adding 1000 Anomalies and 1000 Incidents")
    logger.info("="*70)
    
    from elasticsearch.helpers import bulk
    
    services = [
        "api-gateway", "auth-service", "payment-service", "user-service",
        "order-service", "inventory-service", "notification-service",
        "database", "cache", "frontend"
    ]
    
    regions = ["us-west-1", "us-east-1", "eu-west-1", "ap-south-1"]
    
    metrics = [
        "p99_latency", "p95_latency", "p50_latency", "error_rate",
        "success_rate", "cpu_usage", "memory_usage", "disk_usage",
        "request_count", "active_connections", "queue_depth", "cache_hit_rate"
    ]
    
    # 1. Generate 1000 anomalies
    logger.info("\n🔍 Generating 1000 anomaly records...")
    anomaly_docs = []
    now = datetime.utcnow()
    
    for i in range(1000):
        days_ago = random.randint(0, 90)  # Spread over 90 days
        hours_ago = random.randint(0, 23)
        timestamp = now - timedelta(days=days_ago, hours=hours_ago)
        
        service = random.choice(services)
        metric = random.choice(metrics)
        region = random.choice(regions)
        
        # Base values for different metrics
        base_values = {
            "p99_latency": 200, "p95_latency": 150, "p50_latency": 80,
            "error_rate": 0.5, "success_rate": 99.5, "cpu_usage": 45,
            "memory_usage": 60, "disk_usage": 30, "request_count": 1000,
            "active_connections": 100, "queue_depth": 10, "cache_hit_rate": 85
        }
        
        base_value = base_values.get(metric, 100)
        
        # Generate anomaly
        anomaly_multiplier = random.uniform(3, 15)
        anomaly_value = base_value * anomaly_multiplier
        deviation = random.uniform(5, 20)
        
        # Determine severity
        if deviation > 15:
            severity = "Sev-1"
        elif deviation > 10:
            severity = "Sev-2"
        else:
            severity = "Sev-3"
        
        # Status based on age
        if days_ago > 7:
            status = "resolved"
            duration = random.randint(5, 240)
        elif days_ago > 1:
            status = "resolved"
            duration = random.randint(5, 180)
        else:
            status = random.choice(["active", "investigating", "resolved"])
            duration = random.randint(5, 120) if status == "resolved" else None
        
        anomaly_docs.append({
            "_index": "anomaly-records",
            "_source": {
                "id": f"ANOM-{i+1:04d}",
                "metric": metric,
                "service": service,
                "region": region,
                "environment": "production",
                "detected_at": timestamp.isoformat(),
                "current_value": round(anomaly_value, 2),
                "expected_value": round(base_value, 2),
                "deviation_sigma": round(deviation, 2),
                "severity": severity,
                "status": status,
                "duration_minutes": duration,
                "tags": {
                    "auto_detected": True,
                    "confidence": round(random.uniform(0.7, 0.99), 2)
                }
            }
        })
    
    success, _ = bulk(es, anomaly_docs, raise_on_error=False)
    logger.info(f"  ✓ Added {success:,} anomaly records")
    
    # 2. Generate 1000 incidents
    logger.info("\n🚨 Generating 1000 incident records...")
    incident_docs = []
    
    incident_types = [
        "Latency Spike", "Error Rate Increase", "Memory Leak", "CPU Saturation",
        "Disk Space Critical", "Connection Pool Exhaustion", "Cache Miss Storm",
        "Database Deadlock", "API Timeout", "Service Unavailable",
        "Authentication Failure", "Payment Processing Error", "Queue Backup",
        "Network Partition", "Configuration Error"
    ]
    
    root_causes = [
        "Database connection pool exhaustion",
        "Memory leak in cache eviction logic",
        "Unoptimized query causing full table scan",
        "External API timeout",
        "JWT token validation failing",
        "Circuit breaker triggered",
        "Rate limiting from external service",
        "Network congestion",
        "Configuration mismatch",
        "Deployment rollout issue",
        "Third-party service degradation",
        "Resource quota exceeded",
        "Invalid request parameters",
        "Expired SSL certificate",
        "DNS resolution failure"
    ]
    
    for i in range(1000):
        days_ago = random.randint(0, 180)  # Spread over 6 months
        hours_ago = random.randint(0, 23)
        created_at = now - timedelta(days=days_ago, hours=hours_ago)
        
        service = random.choice(services)
        region = random.choice(regions)
        incident_type = random.choice(incident_types)
        
        # Determine severity
        severity = random.choices(
            ["Sev-1", "Sev-2", "Sev-3"],
            weights=[10, 30, 60]
        )[0]
        
        # Status based on age
        if days_ago > 30:
            status = "resolved"
        elif days_ago > 7:
            status = random.choice(["resolved", "resolved", "resolved", "closed"])
        elif days_ago > 1:
            status = random.choice(["resolved", "investigating", "closed"])
        else:
            status = random.choice(["in_progress", "investigating", "resolved"])
        
        # Calculate MTTR
        if status in ["resolved", "closed"]:
            if severity == "Sev-1":
                mttr = random.randint(30, 240)
            elif severity == "Sev-2":
                mttr = random.randint(60, 360)
            else:
                mttr = random.randint(120, 720)
            
            resolved_at = created_at + timedelta(minutes=mttr)
        else:
            mttr = None
            resolved_at = None
        
        # Select root cause
        root_cause = random.choice(root_causes)
        
        incident_docs.append({
            "_index": "incident-history",
            "_source": {
                "id": f"INC-{i+1:04d}",
                "title": f"{severity} - {service} {incident_type}",
                "severity": severity,
                "status": status,
                "service": service,
                "region": region,
                "environment": "production",
                "created_at": created_at.isoformat(),
                "resolved_at": resolved_at.isoformat() if resolved_at else None,
                "mttr_minutes": mttr,
                "description": f"{incident_type} detected in {service} service in {region}",
                "anomaly": {
                    "metric": random.choice(metrics),
                    "current_value": round(random.uniform(100, 5000), 2),
                    "expected_value": round(random.uniform(50, 500), 2),
                    "deviation_sigma": round(random.uniform(5, 20), 2),
                    "severity": severity,
                    "detected_at": created_at.isoformat(),
                    "service": service,
                    "environment": "production",
                    "region": region
                },
                "diagnosis": {
                    "root_cause": root_cause,
                    "affected_component": service,
                    "impact_explanation": f"Service degradation affecting {random.randint(1, 100)}% of requests",
                    "confidence": round(random.uniform(0.7, 0.98), 2),
                    "correlated_metrics": random.sample(metrics, k=random.randint(2, 4))
                },
                "remediation": {
                    "file_path": f"src/{service.replace('-', '_')}/{random.choice(['config', 'handler', 'client', 'service'])}.py",
                    "explanation": f"Fixed {root_cause.lower()}",
                    "pr_url": f"https://github.com/SVstudent/cozy-bookstore/pull/{random.randint(100, 999)}"
                } if status in ["resolved", "closed"] else None,
                "tags": {
                    "auto_detected": True,
                    "has_runbook": random.choice([True, False]),
                    "customer_impact": random.choice(["high", "medium", "low"])
                }
            }
        })
    
    success, _ = bulk(es, incident_docs, raise_on_error=False)
    logger.info(f"  ✓ Added {success:,} incident records")
    
    logger.info("\n" + "="*70)
    logger.info("✅ Data Population Complete!")
    logger.info("="*70)
    logger.info(f"\n📊 Summary:")
    logger.info(f"   Anomalies: 1,000 records (90 days)")
    logger.info(f"   Incidents: 1,000 records (180 days)")
    
    logger.info(f"\n💬 Try asking the agent:")
    logger.info('   "Show me all Sev-1 incidents from the last 30 days"')
    logger.info('   "What are the most common root causes?"')
    logger.info('   "Show me anomalies in the payment-service"')
    logger.info('   "Which services have the most incidents?"')
    logger.info('   "Analyze incident patterns by region"')
    
    return True


if __name__ == "__main__":
    success = populate_anomalies_and_incidents()
    sys.exit(0 if success else 1)
