#!/usr/bin/env python3
"""
Populate Elasticsearch with COMPREHENSIVE realistic data for ElasticSeer

This script generates:
1. 30 days of metrics with realistic patterns (daily/weekly cycles)
2. Detailed application logs with errors and warnings
3. Multiple anomalies and incidents
4. Geo-distributed data across regions
5. Service dependencies and correlations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from datetime import datetime, timedelta
import random
import math
from elasticsearch import Elasticsearch
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ComprehensiveDataPopulator:
    def __init__(self):
        # Initialize Elasticsearch
        self.es = Elasticsearch(
            hosts=[settings.elasticsearch_url],
            api_key=settings.elasticsearch_api_key,
            verify_certs=True
        )
        
        self.services = [
            "api-gateway",
            "auth-service", 
            "payment-service",
            "user-service",
            "order-service",
            "inventory-service",
            "notification-service",
            "database",
            "cache",
            "frontend"
        ]
        
        self.regions = ["us-west-1", "us-east-1", "eu-west-1", "ap-south-1"]
        
        self.metrics = [
            "p99_latency",
            "p95_latency", 
            "p50_latency",
            "error_rate",
            "success_rate",
            "cpu_usage",
            "memory_usage",
            "disk_usage",
            "request_count",
            "active_connections",
            "queue_depth",
            "cache_hit_rate"
        ]
    
    def generate_realistic_metrics(self, days=30):
        """Generate realistic metrics with daily/weekly patterns and anomalies"""
        logger.info(f"\n📊 Generating {days} days of realistic metrics data...")
        
        docs = []
        now = datetime.utcnow()
        total_points = 0
        
        for day in range(days):
            for hour in range(24):
                for minute in range(0, 60, 5):  # Every 5 minutes for reasonable data size
                    timestamp = now - timedelta(days=days-day-1, hours=23-hour, minutes=59-minute)
                    
                    # Calculate time-based factors
                    hour_of_day = timestamp.hour
                    day_of_week = timestamp.weekday()
                    
                    # Business hours factor (9am-5pm weekdays have more traffic)
                    is_business_hours = (9 <= hour_of_day <= 17) and (day_of_week < 5)
                    business_factor = 1.5 if is_business_hours else 0.7
                    
                    # Weekend factor
                    weekend_factor = 0.5 if day_of_week >= 5 else 1.0
                    
                    # Daily cycle (peak at noon, low at 3am)
                    daily_cycle = 0.5 + 0.5 * math.sin((hour_of_day - 6) * math.pi / 12)
                    
                    for region in self.regions:
                        # Regional time offset
                        region_offset = {"us-west-1": 0, "us-east-1": 3, "eu-west-1": 8, "ap-south-1": 12.5}
                        region_hour = (hour_of_day + region_offset[region]) % 24
                        region_cycle = 0.5 + 0.5 * math.sin((region_hour - 6) * math.pi / 12)
                        
                        for service in self.services:
                            for metric in self.metrics:
                                # Base value with realistic patterns
                                base_value = self._get_base_value(metric, service)
                                
                                # Apply time-based variations
                                value = base_value * business_factor * weekend_factor * daily_cycle * region_cycle
                                
                                # Add random noise
                                value *= random.uniform(0.95, 1.05)
                                
                                # Inject anomalies (2% chance)
                                is_anomaly = False
                                if random.random() < 0.02:
                                    anomaly_type = random.choice(['spike', 'drop', 'sustained'])
                                    if anomaly_type == 'spike':
                                        value *= random.uniform(3, 8)
                                    elif anomaly_type == 'drop':
                                        value *= random.uniform(0.1, 0.3)
                                    else:  # sustained
                                        value *= random.uniform(2, 3)
                                    is_anomaly = True
                                
                                doc = {
                                    "@timestamp": timestamp.isoformat(),
                                    "metric_name": metric,
                                    "value": round(value, 2),
                                    "service": service,
                                    "environment": "production",
                                    "region": region,
                                    "cluster": f"prod-{region}",
                                    "is_anomaly": is_anomaly,
                                    "tags": {
                                        "business_hours": is_business_hours,
                                        "day_of_week": day_of_week,
                                        "hour_of_day": hour_of_day
                                    }
                                }
                                docs.append(doc)
                                total_points += 1
        
        logger.info(f"  Generated {len(docs):,} metric documents ({total_points:,} data points)")
        return docs
    
    def _get_base_value(self, metric, service):
        """Get realistic base values for different metrics"""
        base_values = {
            "p99_latency": {"api-gateway": 200, "auth-service": 150, "payment-service": 300, 
                           "user-service": 100, "order-service": 250, "inventory-service": 180,
                           "notification-service": 120, "database": 50, "cache": 10, "frontend": 500},
            "p95_latency": {"api-gateway": 150, "auth-service": 100, "payment-service": 200,
                           "user-service": 80, "order-service": 180, "inventory-service": 120,
                           "notification-service": 90, "database": 30, "cache": 5, "frontend": 350},
            "p50_latency": {"api-gateway": 80, "auth-service": 50, "payment-service": 100,
                           "user-service": 40, "order-service": 90, "inventory-service": 60,
                           "notification-service": 45, "database": 15, "cache": 2, "frontend": 200},
            "error_rate": {"api-gateway": 0.5, "auth-service": 0.3, "payment-service": 0.8,
                          "user-service": 0.2, "order-service": 0.6, "inventory-service": 0.4,
                          "notification-service": 1.0, "database": 0.1, "cache": 0.05, "frontend": 0.7},
            "success_rate": {"api-gateway": 99.5, "auth-service": 99.7, "payment-service": 99.2,
                            "user-service": 99.8, "order-service": 99.4, "inventory-service": 99.6,
                            "notification-service": 99.0, "database": 99.9, "cache": 99.95, "frontend": 99.3},
            "cpu_usage": {"api-gateway": 45, "auth-service": 35, "payment-service": 55,
                         "user-service": 30, "order-service": 50, "inventory-service": 40,
                         "notification-service": 25, "database": 60, "cache": 20, "frontend": 15},
            "memory_usage": {"api-gateway": 60, "auth-service": 50, "payment-service": 70,
                            "user-service": 45, "order-service": 65, "inventory-service": 55,
                            "notification-service": 40, "database": 75, "cache": 80, "frontend": 35},
            "disk_usage": {"api-gateway": 30, "auth-service": 25, "payment-service": 35,
                          "user-service": 20, "order-service": 40, "inventory-service": 45,
                          "notification-service": 15, "database": 70, "cache": 10, "frontend": 25},
            "request_count": {"api-gateway": 1000, "auth-service": 500, "payment-service": 200,
                             "user-service": 800, "order-service": 300, "inventory-service": 400,
                             "notification-service": 600, "database": 2000, "cache": 5000, "frontend": 1500},
            "active_connections": {"api-gateway": 100, "auth-service": 50, "payment-service": 30,
                                  "user-service": 80, "order-service": 40, "inventory-service": 60,
                                  "notification-service": 70, "database": 200, "cache": 500, "frontend": 150},
            "queue_depth": {"api-gateway": 10, "auth-service": 5, "payment-service": 20,
                           "user-service": 3, "order-service": 15, "inventory-service": 8,
                           "notification-service": 50, "database": 25, "cache": 2, "frontend": 12},
            "cache_hit_rate": {"api-gateway": 85, "auth-service": 90, "payment-service": 75,
                              "user-service": 88, "order-service": 80, "inventory-service": 82,
                              "notification-service": 70, "database": 0, "cache": 95, "frontend": 78}
        }
        
        return base_values.get(metric, {}).get(service, 100)
    
    def generate_application_logs(self, days=7):
        """Generate realistic application logs"""
        logger.info(f"\n📝 Generating {days} days of application logs...")
        
        docs = []
        now = datetime.utcnow()
        
        log_levels = ["INFO", "WARN", "ERROR", "DEBUG"]
        log_templates = {
            "INFO": [
                "Request processed successfully",
                "User authenticated",
                "Cache hit for key",
                "Database query executed",
                "API call completed",
                "Service health check passed"
            ],
            "WARN": [
                "High memory usage detected",
                "Slow query detected",
                "Cache miss rate increasing",
                "Connection pool near capacity",
                "Rate limit approaching",
                "Deprecated API endpoint used"
            ],
            "ERROR": [
                "Database connection failed",
                "Authentication token expired",
                "Payment processing failed",
                "Service timeout",
                "Invalid request parameters",
                "External API unavailable"
            ],
            "DEBUG": [
                "Request headers logged",
                "Query parameters parsed",
                "Cache lookup performed",
                "Middleware executed",
                "Response serialized",
                "Connection established"
            ]
        }
        
        for day in range(days):
            # More logs during business hours
            logs_per_day = random.randint(5000, 10000)
            
            for _ in range(logs_per_day):
                timestamp = now - timedelta(
                    days=days-day-1,
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                
                # Weight log levels (more INFO, fewer ERROR)
                level = random.choices(
                    log_levels,
                    weights=[70, 20, 5, 5]
                )[0]
                
                service = random.choice(self.services)
                region = random.choice(self.regions)
                message = random.choice(log_templates[level])
                
                doc = {
                    "@timestamp": timestamp.isoformat(),
                    "level": level,
                    "message": message,
                    "service": service,
                    "environment": "production",
                    "region": region,
                    "trace_id": f"trace-{random.randint(100000, 999999)}",
                    "span_id": f"span-{random.randint(1000, 9999)}",
                    "user_id": f"user-{random.randint(1, 10000)}" if random.random() > 0.3 else None,
                    "request_id": f"req-{random.randint(100000, 999999)}",
                    "duration_ms": random.randint(10, 5000) if level != "DEBUG" else None
                }
                
                docs.append(doc)
        
        logger.info(f"  Generated {len(docs):,} log documents")
        return docs
    
    def generate_detailed_incidents(self):
        """Generate detailed incident records with rich context"""
        logger.info(f"\n🚨 Generating detailed incident history...")
        
        incidents = [
            {
                "id": "INC-001",
                "title": "Critical API Gateway Latency Spike",
                "severity": "Sev-1",
                "status": "resolved",
                "service": "api-gateway",
                "region": "us-west-1",
                "anomaly": {
                    "metric": "p99_latency",
                    "current_value": 2500.0,
                    "expected_value": 200.0,
                    "deviation_sigma": 11.5,
                    "severity": "Sev-1",
                    "detected_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                    "service": "api-gateway",
                    "environment": "production",
                    "region": "us-west-1"
                },
                "diagnosis": {
                    "root_cause": "Database connection pool exhaustion",
                    "affected_component": "api-gateway",
                    "impact_explanation": "All API requests timing out due to waiting for database connections",
                    "confidence": 0.95,
                    "correlated_metrics": ["active_connections", "queue_depth", "error_rate"]
                },
                "remediation": {
                    "file_path": "src/config/database.py",
                    "explanation": "Increased connection pool size from 10 to 50 and added connection timeout",
                    "pr_url": "https://github.com/SVstudent/cozy-bookstore/pull/123"
                },
                "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "resolved_at": (datetime.utcnow() - timedelta(days=5, hours=2)).isoformat(),
                "mttr_minutes": 120,
                "description": "Critical latency spike in API gateway causing production outage affecting 100% of users"
            },
            {
                "id": "INC-002",
                "title": "Authentication Service Error Rate Spike",
                "severity": "Sev-2",
                "status": "resolved",
                "service": "auth-service",
                "region": "us-east-1",
                "anomaly": {
                    "metric": "error_rate",
                    "current_value": 15.0,
                    "expected_value": 0.3,
                    "deviation_sigma": 8.2,
                    "severity": "Sev-2",
                    "detected_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                    "service": "auth-service",
                    "environment": "production",
                    "region": "us-east-1"
                },
                "diagnosis": {
                    "root_cause": "JWT token validation failing due to expired signing key",
                    "affected_component": "auth-service",
                    "impact_explanation": "15% of authentication requests failing, affecting user login",
                    "confidence": 0.88,
                    "correlated_metrics": ["error_rate", "success_rate"]
                },
                "remediation": {
                    "file_path": "src/auth/jwt_validator.py",
                    "explanation": "Updated key rotation logic to refresh before expiration",
                    "pr_url": "https://github.com/SVstudent/cozy-bookstore/pull/124"
                },
                "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "resolved_at": (datetime.utcnow() - timedelta(days=3, hours=1)).isoformat(),
                "mttr_minutes": 60,
                "description": "Authentication failures due to JWT validation errors"
            },
            {
                "id": "INC-003",
                "title": "Cache Service Memory Leak",
                "severity": "Sev-2",
                "status": "resolved",
                "service": "cache",
                "region": "eu-west-1",
                "anomaly": {
                    "metric": "memory_usage",
                    "current_value": 95.0,
                    "expected_value": 80.0,
                    "deviation_sigma": 9.0,
                    "severity": "Sev-2",
                    "detected_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    "service": "cache",
                    "environment": "production",
                    "region": "eu-west-1"
                },
                "diagnosis": {
                    "root_cause": "Memory leak in cache eviction logic",
                    "affected_component": "cache",
                    "impact_explanation": "Cache service approaching OOM, degraded performance",
                    "confidence": 0.92,
                    "correlated_metrics": ["memory_usage", "cache_hit_rate"]
                },
                "remediation": {
                    "file_path": "src/cache/eviction.py",
                    "explanation": "Fixed memory leak by properly releasing references in eviction callback",
                    "pr_url": "https://github.com/SVstudent/cozy-bookstore/pull/125"
                },
                "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "resolved_at": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                "mttr_minutes": 180,
                "description": "Memory leak causing cache service instability"
            },
            {
                "id": "INC-004",
                "title": "Payment Service Timeout Cascade",
                "severity": "Sev-1",
                "status": "resolved",
                "service": "payment-service",
                "region": "us-west-1",
                "anomaly": {
                    "metric": "p99_latency",
                    "current_value": 5000.0,
                    "expected_value": 300.0,
                    "deviation_sigma": 15.7,
                    "severity": "Sev-1",
                    "detected_at": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "service": "payment-service",
                    "environment": "production",
                    "region": "us-west-1"
                },
                "diagnosis": {
                    "root_cause": "External payment gateway timeout causing cascading failures",
                    "affected_component": "payment-service",
                    "impact_explanation": "Payment processing failing, affecting order completion",
                    "confidence": 0.97,
                    "correlated_metrics": ["p99_latency", "error_rate", "queue_depth"]
                },
                "remediation": {
                    "file_path": "src/payment/gateway_client.py",
                    "explanation": "Added circuit breaker pattern and reduced timeout from 30s to 5s",
                    "pr_url": "https://github.com/SVstudent/cozy-bookstore/pull/126"
                },
                "created_at": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "resolved_at": (datetime.utcnow() - timedelta(days=7, hours=4)).isoformat(),
                "mttr_minutes": 240,
                "description": "Payment gateway timeouts causing order processing failures"
            },
            {
                "id": "INC-005",
                "title": "Database CPU Saturation",
                "severity": "Sev-2",
                "status": "resolved",
                "service": "database",
                "region": "ap-south-1",
                "anomaly": {
                    "metric": "cpu_usage",
                    "current_value": 98.0,
                    "expected_value": 60.0,
                    "deviation_sigma": 12.7,
                    "severity": "Sev-2",
                    "detected_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                    "service": "database",
                    "environment": "production",
                    "region": "ap-south-1"
                },
                "diagnosis": {
                    "root_cause": "Unoptimized query causing full table scan",
                    "affected_component": "database",
                    "impact_explanation": "Database CPU at 98%, all queries slowing down",
                    "confidence": 0.94,
                    "correlated_metrics": ["cpu_usage", "p99_latency", "active_connections"]
                },
                "remediation": {
                    "file_path": "src/database/queries.py",
                    "explanation": "Added index on user_id column and optimized JOIN query",
                    "pr_url": "https://github.com/SVstudent/cozy-bookstore/pull/127"
                },
                "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                "resolved_at": (datetime.utcnow() - timedelta(days=2, hours=1, minutes=30)).isoformat(),
                "mttr_minutes": 90,
                "description": "Database performance degradation due to unoptimized query"
            },
            {
                "id": "INC-006",
                "title": "Notification Service Queue Backup",
                "severity": "Sev-3",
                "status": "in_progress",
                "service": "notification-service",
                "region": "us-east-1",
                "anomaly": {
                    "metric": "queue_depth",
                    "current_value": 5000.0,
                    "expected_value": 50.0,
                    "deviation_sigma": 10.2,
                    "severity": "Sev-3",
                    "detected_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "service": "notification-service",
                    "environment": "production",
                    "region": "us-east-1"
                },
                "diagnosis": {
                    "root_cause": "Email service rate limiting causing queue backup",
                    "affected_component": "notification-service",
                    "impact_explanation": "Notifications delayed by 30+ minutes",
                    "confidence": 0.85,
                    "correlated_metrics": ["queue_depth", "error_rate"]
                },
                "remediation": None,
                "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "resolved_at": None,
                "mttr_minutes": None,
                "description": "Notification queue backing up due to external service rate limits"
            }
        ]
        
        logger.info(f"  Generated {len(incidents)} detailed incident records")
        return incidents
    
    def generate_anomaly_records(self):
        """Generate anomaly detection records"""
        logger.info(f"\n🔍 Generating anomaly records...")
        
        anomalies = []
        now = datetime.utcnow()
        
        # Generate 50 anomalies over the past 30 days
        for i in range(50):
            days_ago = random.randint(0, 30)
            timestamp = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            service = random.choice(self.services)
            metric = random.choice(self.metrics)
            region = random.choice(self.regions)
            
            base_value = self._get_base_value(metric, service)
            anomaly_value = base_value * random.uniform(3, 10)
            deviation = random.uniform(5, 15)
            
            severity = "Sev-1" if deviation > 10 else "Sev-2" if deviation > 7 else "Sev-3"
            
            anomaly = {
                "id": f"ANOM-{i+1:03d}",
                "metric": metric,
                "service": service,
                "region": region,
                "environment": "production",
                "detected_at": timestamp.isoformat(),
                "current_value": round(anomaly_value, 2),
                "expected_value": round(base_value, 2),
                "deviation_sigma": round(deviation, 2),
                "severity": severity,
                "status": "resolved" if days_ago > 1 else "active",
                "duration_minutes": random.randint(5, 180) if days_ago > 1 else None
            }
            
            anomalies.append(anomaly)
        
        logger.info(f"  Generated {len(anomalies)} anomaly records")
        return anomalies
    
    def bulk_index(self, index_name, docs, batch_size=1000):
        """Bulk index documents to Elasticsearch in batches"""
        if not docs:
            logger.warning(f"  ⚠ No documents to index for {index_name}")
            return 0
        
        logger.info(f"\n💾 Indexing {len(docs):,} documents to '{index_name}'...")
        
        from elasticsearch.helpers import bulk
        
        total_success = 0
        total_failed = 0
        
        # Process in batches
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i+batch_size]
            
            actions = [
                {
                    "_index": index_name,
                    "_source": doc
                }
                for doc in batch
            ]
            
            try:
                success, failed = bulk(self.es, actions, raise_on_error=False)
                total_success += success
                total_failed += len(failed) if failed else 0
                
                if (i + batch_size) % 10000 == 0:
                    logger.info(f"  Progress: {i+batch_size:,}/{len(docs):,} documents")
                    
            except Exception as e:
                logger.error(f"  ❌ Batch indexing failed: {e}")
                total_failed += len(batch)
        
        logger.info(f"  ✓ Indexed {total_success:,} documents")
        if total_failed:
            logger.warning(f"  ⚠ Failed to index {total_failed:,} documents")
        
        return total_success
    
    async def populate_all(self):
        """Populate all indices with comprehensive data"""
        logger.info("="*70)
        logger.info("ElasticSeer COMPREHENSIVE Data Population")
        logger.info("="*70)
        
        # Check connection
        if not self.es.ping():
            logger.error("❌ Cannot connect to Elasticsearch")
            return False
        
        logger.info("✓ Connected to Elasticsearch")
        
        # 1. Generate and index metrics (7 days for faster population)
        metrics_docs = self.generate_realistic_metrics(days=7)
        metrics_count = self.bulk_index("metrics", metrics_docs)
        
        # 2. Generate and index logs (3 days for faster population)
        log_docs = self.generate_application_logs(days=3)
        log_count = self.bulk_index("logs", log_docs)
        
        # 3. Generate and index incidents
        incident_docs = self.generate_detailed_incidents()
        incident_count = self.bulk_index("incident-history", incident_docs)
        
        # 4. Generate and index anomalies
        anomaly_docs = self.generate_anomaly_records()
        anomaly_count = self.bulk_index("anomaly-records", anomaly_docs)
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("✅ COMPREHENSIVE Data Population Complete!")
        logger.info("="*70)
        logger.info(f"\n📊 Summary:")
        logger.info(f"   Metrics: {metrics_count:,} documents (7 days, 10 services, 4 regions)")
        logger.info(f"   Logs: {log_count:,} documents (3 days)")
        logger.info(f"   Incidents: {incident_count} detailed incidents")
        logger.info(f"   Anomalies: {anomaly_count} anomaly records")
        
        logger.info(f"\n🎯 Your agent can now:")
        logger.info(f"   ✓ Analyze 7 days of time-series metrics")
        logger.info(f"   ✓ Detect patterns and trends")
        logger.info(f"   ✓ Search through {log_count:,} log entries")
        logger.info(f"   ✓ Correlate incidents across regions")
        logger.info(f"   ✓ Identify anomalies and their impact")
        
        logger.info(f"\n💬 Try asking the agent:")
        logger.info(f'   "Show me metrics for api-gateway in us-west-1"')
        logger.info(f'   "What anomalies were detected in the last 7 days?"')
        logger.info(f'   "Analyze error logs from the payment-service"')
        logger.info(f'   "Show me incidents with high severity"')
        logger.info(f'   "What patterns do you see in the database metrics?"')
        
        return True


async def main():
    populator = ComprehensiveDataPopulator()
    success = await populator.populate_all()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
