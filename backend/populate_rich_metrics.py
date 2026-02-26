#!/usr/bin/env python3
"""
Populate Elasticsearch with RICH, VARIED metrics data for comprehensive analysis

Generates:
- 30 days of detailed metrics with realistic patterns
- Multiple metric types (latency, errors, resources, throughput)
- Regional variations
- Anomalies and incidents
- Trends and seasonality
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
import random
import math
from elasticsearch import Elasticsearch
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class RichMetricsPopulator:
    def __init__(self):
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
        
        self.regions = ["us-west-1", "us-east-1", "eu-west-1", "ap-south-1", "ap-northeast-1"]
        
        # Comprehensive metric definitions
        self.metric_configs = {
            # Latency metrics (milliseconds)
            "p99_latency": {"base": 250, "variance": 100, "spike_chance": 0.02, "spike_multiplier": 4},
            "p95_latency": {"base": 180, "variance": 60, "spike_chance": 0.03, "spike_multiplier": 3},
            "p90_latency": {"base": 150, "variance": 50, "spike_chance": 0.04, "spike_multiplier": 2.5},
            "p75_latency": {"base": 120, "variance": 40, "spike_chance": 0.05, "spike_multiplier": 2},
            "p50_latency": {"base": 80, "variance": 30, "spike_chance": 0.05, "spike_multiplier": 1.8},
            
            # Error rates (percentage)
            "error_rate": {"base": 0.5, "variance": 0.3, "spike_chance": 0.01, "spike_multiplier": 10},
            "timeout_rate": {"base": 0.2, "variance": 0.15, "spike_chance": 0.015, "spike_multiplier": 8},
            "5xx_rate": {"base": 0.3, "variance": 0.2, "spike_chance": 0.012, "spike_multiplier": 12},
            "4xx_rate": {"base": 2.0, "variance": 1.0, "spike_chance": 0.02, "spike_multiplier": 3},
            
            # Success metrics (percentage)
            "success_rate": {"base": 99.5, "variance": 0.3, "spike_chance": 0.01, "spike_multiplier": 0.95},
            "availability": {"base": 99.9, "variance": 0.05, "spike_chance": 0.005, "spike_multiplier": 0.98},
            
            # Resource utilization (percentage)
            "cpu_usage": {"base": 45, "variance": 15, "spike_chance": 0.03, "spike_multiplier": 1.8},
            "memory_usage": {"base": 60, "variance": 10, "spike_chance": 0.02, "spike_multiplier": 1.5},
            "disk_usage": {"base": 35, "variance": 5, "spike_chance": 0.01, "spike_multiplier": 1.3},
            "network_usage": {"base": 40, "variance": 20, "spike_chance": 0.04, "spike_multiplier": 2},
            
            # Throughput metrics (count)
            "request_count": {"base": 1000, "variance": 400, "spike_chance": 0.05, "spike_multiplier": 3},
            "requests_per_second": {"base": 150, "variance": 60, "spike_chance": 0.05, "spike_multiplier": 2.5},
            "active_connections": {"base": 500, "variance": 200, "spike_chance": 0.03, "spike_multiplier": 2},
            "concurrent_users": {"base": 300, "variance": 150, "spike_chance": 0.04, "spike_multiplier": 2.2},
            
            # Queue and processing metrics
            "queue_depth": {"base": 50, "variance": 30, "spike_chance": 0.04, "spike_multiplier": 5},
            "processing_time": {"base": 100, "variance": 40, "spike_chance": 0.03, "spike_multiplier": 3},
            "backlog_size": {"base": 20, "variance": 15, "spike_chance": 0.02, "spike_multiplier": 8},
            
            # Cache metrics (percentage)
            "cache_hit_rate": {"base": 85, "variance": 5, "spike_chance": 0.02, "spike_multiplier": 0.7},
            "cache_miss_rate": {"base": 15, "variance": 5, "spike_chance": 0.02, "spike_multiplier": 2},
            
            # Database metrics
            "db_query_time": {"base": 50, "variance": 25, "spike_chance": 0.03, "spike_multiplier": 4},
            "db_connection_pool": {"base": 80, "variance": 10, "spike_chance": 0.02, "spike_multiplier": 1.2},
            "db_slow_queries": {"base": 5, "variance": 3, "spike_chance": 0.03, "spike_multiplier": 5},
            
            # API metrics
            "api_response_size": {"base": 2048, "variance": 1024, "spike_chance": 0.02, "spike_multiplier": 3},
            "api_request_size": {"base": 512, "variance": 256, "spike_chance": 0.02, "spike_multiplier": 2},
        }
    
    def calculate_time_factors(self, timestamp):
        """Calculate various time-based factors for realistic patterns"""
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        day_of_month = timestamp.day
        
        # Business hours (9am-5pm weekdays)
        is_business_hours = (9 <= hour <= 17) and (day_of_week < 5)
        business_factor = 1.5 if is_business_hours else 0.7
        
        # Weekend factor
        weekend_factor = 0.5 if day_of_week >= 5 else 1.0
        
        # Daily cycle (peak at noon, low at 3am)
        daily_cycle = 0.5 + 0.5 * math.sin((hour - 6) * math.pi / 12)
        
        # Weekly cycle (Monday high, Friday higher, weekend low)
        weekly_pattern = [1.0, 0.95, 0.9, 0.95, 1.1, 0.8, 0.6]
        weekly_factor = weekly_pattern[day_of_week]
        
        # Monthly cycle (end of month spike)
        monthly_factor = 1.0 + (0.3 if day_of_month >= 25 else 0)
        
        return {
            "business": business_factor,
            "weekend": weekend_factor,
            "daily": daily_cycle,
            "weekly": weekly_factor,
            "monthly": monthly_factor
        }
    
    def generate_metric_value(self, metric_name, config, factors, service, region):
        """Generate a realistic metric value with patterns and anomalies"""
        base = config["base"]
        variance = config["variance"]
        
        # Apply time-based factors
        value = base * factors["business"] * factors["weekend"] * factors["daily"] * factors["weekly"] * factors["monthly"]
        
        # Add random variance
        value += random.uniform(-variance, variance)
        
        # Service-specific adjustments
        service_multipliers = {
            "database": 1.2,  # Database tends to be slower
            "cache": 0.6,     # Cache is faster
            "api-gateway": 1.1,  # Gateway has overhead
            "frontend": 0.8   # Frontend is optimized
        }
        value *= service_multipliers.get(service, 1.0)
        
        # Region-specific adjustments
        region_multipliers = {
            "us-west-1": 1.0,
            "us-east-1": 0.95,
            "eu-west-1": 1.1,
            "ap-south-1": 1.15,
            "ap-northeast-1": 1.05
        }
        value *= region_multipliers.get(region, 1.0)
        
        # Random spikes/anomalies
        if random.random() < config["spike_chance"]:
            value *= config["spike_multiplier"]
            is_anomaly = True
        else:
            is_anomaly = False
        
        # Ensure reasonable bounds
        if "rate" in metric_name or "usage" in metric_name or "hit_rate" in metric_name:
            value = max(0, min(100, value))
        elif "latency" in metric_name or "time" in metric_name:
            value = max(1, value)
        else:
            value = max(0, value)
        
        return round(value, 2), is_anomaly
    
    def populate_metrics(self, days=30):
        """Populate comprehensive metrics data"""
        logger.info(f"\n📊 Generating {days} days of rich metrics data...")
        logger.info(f"Services: {len(self.services)}")
        logger.info(f"Regions: {len(self.regions)}")
        logger.info(f"Metrics: {len(self.metric_configs)}")
        
        docs = []
        now = datetime.utcnow()
        total_points = 0
        anomaly_count = 0
        
        # Generate data points every 5 minutes
        for day in range(days):
            for hour in range(24):
                for minute in range(0, 60, 5):
                    timestamp = now - timedelta(days=days-day-1, hours=23-hour, minutes=59-minute)
                    factors = self.calculate_time_factors(timestamp)
                    
                    for service in self.services:
                        for region in self.regions:
                            for metric_name, config in self.metric_configs.items():
                                value, is_anomaly = self.generate_metric_value(
                                    metric_name, config, factors, service, region
                                )
                                
                                doc = {
                                    "@timestamp": timestamp.isoformat(),
                                    "service": service,
                                    "region": region,
                                    "environment": "production",
                                    "metric_name": metric_name,
                                    "value": value,
                                    "is_anomaly": is_anomaly,
                                    "hour_of_day": timestamp.hour,
                                    "day_of_week": timestamp.weekday(),
                                    "business_hours": factors["business"] > 1.0
                                }
                                
                                docs.append(doc)
                                total_points += 1
                                if is_anomaly:
                                    anomaly_count += 1
                                
                                # Bulk index every 5000 documents
                                if len(docs) >= 5000:
                                    self.bulk_index(docs)
                                    docs = []
                                    logger.info(f"  Indexed {total_points:,} data points ({anomaly_count} anomalies)...")
        
        # Index remaining documents
        if docs:
            self.bulk_index(docs)
        
        logger.info(f"\n✅ Generated {total_points:,} metric data points")
        logger.info(f"   - {anomaly_count:,} anomalies detected ({anomaly_count/total_points*100:.2f}%)")
        logger.info(f"   - {len(self.services)} services")
        logger.info(f"   - {len(self.regions)} regions")
        logger.info(f"   - {len(self.metric_configs)} metric types")
        logger.info(f"   - {days} days of data")
    
    def bulk_index(self, docs):
        """Bulk index documents to Elasticsearch"""
        operations = []
        for doc in docs:
            operations.append({"index": {"_index": "metrics"}})
            operations.append(doc)
        
        try:
            self.es.bulk(operations=operations, refresh=False)
        except Exception as e:
            logger.error(f"Error indexing: {e}")
    
    def create_sample_anomalies(self):
        """Create specific anomaly records for testing"""
        logger.info("\n🔍 Creating sample anomaly records...")
        
        now = datetime.utcnow()
        anomalies = []
        
        # Recent anomalies (last 24 hours)
        for i in range(20):
            hours_ago = random.randint(1, 24)
            timestamp = now - timedelta(hours=hours_ago)
            
            service = random.choice(self.services)
            region = random.choice(self.regions)
            metric = random.choice(list(self.metric_configs.keys()))
            
            # Generate anomalous value
            config = self.metric_configs[metric]
            base_value = config["base"]
            anomalous_value = base_value * config["spike_multiplier"]
            expected_value = base_value
            deviation = abs(anomalous_value - expected_value) / (expected_value * 0.1 + 1)
            
            anomaly = {
                "id": f"ANOM-{1000+i:04d}",
                "detected_at": timestamp.isoformat(),
                "service": service,
                "region": region,
                "environment": "production",
                "metric": metric,
                "current_value": round(anomalous_value, 2),
                "expected_value": round(expected_value, 2),
                "deviation_sigma": round(deviation, 2),
                "severity": "Sev-1" if deviation > 5 else "Sev-2" if deviation > 3 else "Sev-3",
                "status": "active" if hours_ago < 6 else "investigating",
                "tags": {
                    "auto_detected": True,
                    "confidence": round(random.uniform(0.7, 0.99), 2)
                }
            }
            
            anomalies.append(anomaly)
        
        # Bulk index anomalies
        operations = []
        for anomaly in anomalies:
            operations.append({"index": {"_index": "anomaly-records"}})
            operations.append(anomaly)
        
        self.es.bulk(operations=operations, refresh=True)
        logger.info(f"✅ Created {len(anomalies)} sample anomaly records")
    
    def refresh_indices(self):
        """Refresh indices to make data searchable"""
        logger.info("\n🔄 Refreshing indices...")
        self.es.indices.refresh(index="metrics")
        self.es.indices.refresh(index="anomaly-records")
        logger.info("✅ Indices refreshed")


def main():
    logger.info("=" * 60)
    logger.info("ElasticSeer - Rich Metrics Data Population")
    logger.info("=" * 60)
    
    populator = RichMetricsPopulator()
    
    # Populate 30 days of metrics
    populator.populate_metrics(days=30)
    
    # Create sample anomalies
    populator.create_sample_anomalies()
    
    # Refresh indices
    populator.refresh_indices()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Data population complete!")
    logger.info("=" * 60)
    logger.info("\nYou can now:")
    logger.info("  - Analyze metrics: 'Analyze metrics for api-gateway'")
    logger.info("  - Check anomalies: 'Show anomalies for auth-service'")
    logger.info("  - View trends: 'Show me performance trends over 7 days'")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
