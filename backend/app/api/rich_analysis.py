"""
Rich Analysis API - Direct Elasticsearch queries with formatted responses

This bypasses the agent and provides rich, data-driven analysis directly
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from app.core.config import settings
import statistics

router = APIRouter(prefix="/api/analysis", tags=["rich-analysis"])

# Initialize Elasticsearch
es = Elasticsearch(
    hosts=[settings.elasticsearch_url],
    api_key=settings.elasticsearch_api_key,
    verify_certs=True
)


class AnalyzeServiceRequest(BaseModel):
    service: str
    hours: int = 24


@router.post("/service_metrics")
async def analyze_service_metrics(request: AnalyzeServiceRequest):
    """
    Provide RICH analysis of service metrics with actual data
    """
    try:
        service = request.service
        hours = request.hours
        
        # Calculate time range
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)
        
        # Query metrics from Elasticsearch
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"service": service}},
                        {"range": {"@timestamp": {"gte": start_time.isoformat(), "lte": now.isoformat()}}}
                    ]
                }
            },
            "size": 0,
            "aggs": {
                "by_metric": {
                    "terms": {"field": "metric_name", "size": 20},
                    "aggs": {
                        "avg_value": {"avg": {"field": "value"}},
                        "max_value": {"max": {"field": "value"}},
                        "min_value": {"min": {"field": "value"}},
                        "by_region": {
                            "terms": {"field": "region", "size": 10},
                            "aggs": {
                                "avg_value": {"avg": {"field": "value"}},
                                "max_value": {"max": {"field": "value"}}
                            }
                        }
                    }
                },
                "anomalies": {
                    "filter": {"term": {"is_anomaly": True}},
                    "aggs": {
                        "count": {"value_count": {"field": "value"}}
                    }
                }
            }
        }
        
        result = es.search(index="metrics", body=query)
        
        # Parse results
        metrics_data = {}
        for bucket in result['aggregations']['by_metric']['buckets']:
            metric_name = bucket['key']
            metrics_data[metric_name] = {
                "avg": round(bucket['avg_value']['value'], 2) if bucket['avg_value']['value'] else 0,
                "max": round(bucket['max_value']['value'], 2) if bucket['max_value']['value'] else 0,
                "min": round(bucket['min_value']['value'], 2) if bucket['min_value']['value'] else 0,
                "regions": {}
            }
            
            for region_bucket in bucket['by_region']['buckets']:
                region = region_bucket['key']
                metrics_data[metric_name]['regions'][region] = {
                    "avg": round(region_bucket['avg_value']['value'], 2) if region_bucket['avg_value']['value'] else 0,
                    "max": round(region_bucket['max_value']['value'], 2) if region_bucket['max_value']['value'] else 0
                }
        
        anomaly_count = result['aggregations']['anomalies']['count']['value']
        
        # Format rich response
        response = format_service_analysis(service, hours, metrics_data, anomaly_count)
        
        return {
            "success": True,
            "service": service,
            "time_range_hours": hours,
            "analysis": response,
            "raw_data": metrics_data,
            "anomaly_count": anomaly_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


def format_service_analysis(service: str, hours: int, metrics: Dict, anomaly_count: int) -> str:
    """Format rich analysis response with actual data"""
    
    lines = []
    lines.append(f"# 📊 {service.upper()} Metrics Analysis (Last {hours} Hours)")
    lines.append("")
    
    # Latency Analysis
    if any(k in metrics for k in ['p99_latency', 'p95_latency', 'p50_latency']):
        lines.append("## ⏱️ Latency Metrics")
        
        if 'p99_latency' in metrics:
            m = metrics['p99_latency']
            status = "🚨 CRITICAL" if m['max'] > 1000 else "⚠️ ELEVATED" if m['max'] > 500 else "✅ NORMAL"
            lines.append(f"- **P99 Latency**: {m['avg']}ms (avg), {m['max']}ms (max), {m['min']}ms (min) {status}")
        
        if 'p95_latency' in metrics:
            m = metrics['p95_latency']
            lines.append(f"- **P95 Latency**: {m['avg']}ms (avg), {m['max']}ms (max), {m['min']}ms (min)")
        
        if 'p50_latency' in metrics:
            m = metrics['p50_latency']
            lines.append(f"- **P50 Latency**: {m['avg']}ms (avg), {m['max']}ms (max), {m['min']}ms (min)")
        
        lines.append("")
    
    # Error Rate Analysis
    if 'error_rate' in metrics:
        lines.append("## 🔴 Error Metrics")
        m = metrics['error_rate']
        status = "🚨 CRITICAL" if m['max'] > 5 else "⚠️ ELEVATED" if m['max'] > 1 else "✅ HEALTHY"
        lines.append(f"- **Error Rate**: {m['avg']}% (avg), {m['max']}% (max) {status}")
        
        if m['max'] > 1:
            lines.append(f"  - ⚠️ Peak error rate of {m['max']}% detected")
        
        lines.append("")
    
    # Resource Usage
    if any(k in metrics for k in ['cpu_usage', 'memory_usage', 'disk_usage']):
        lines.append("## 💻 Resource Usage")
        
        if 'cpu_usage' in metrics:
            m = metrics['cpu_usage']
            status = "🚨 CRITICAL" if m['max'] > 90 else "⚠️ HIGH" if m['max'] > 75 else "✅ NORMAL"
            lines.append(f"- **CPU**: {m['avg']}% (avg), {m['max']}% (max) {status}")
        
        if 'memory_usage' in metrics:
            m = metrics['memory_usage']
            status = "🚨 CRITICAL" if m['max'] > 90 else "⚠️ HIGH" if m['max'] > 80 else "✅ NORMAL"
            lines.append(f"- **Memory**: {m['avg']}% (avg), {m['max']}% (max) {status}")
        
        if 'disk_usage' in metrics:
            m = metrics['disk_usage']
            status = "🚨 CRITICAL" if m['max'] > 90 else "⚠️ HIGH" if m['max'] > 80 else "✅ NORMAL"
            lines.append(f"- **Disk**: {m['avg']}% (avg), {m['max']}% (max) {status}")
        
        lines.append("")
    
    # Request Metrics
    if 'request_count' in metrics:
        lines.append("## 📈 Traffic Metrics")
        m = metrics['request_count']
        lines.append(f"- **Request Count**: {int(m['avg'])} (avg), {int(m['max'])} (max)")
        lines.append("")
    
    # Regional Breakdown
    lines.append("## 🌍 Regional Performance")
    
    # Get error rates by region if available
    if 'error_rate' in metrics and metrics['error_rate']['regions']:
        regions = metrics['error_rate']['regions']
        sorted_regions = sorted(regions.items(), key=lambda x: x[1]['max'], reverse=True)
        
        for region, data in sorted_regions:
            if data['max'] > 5:
                status = "🚨 CRITICAL"
            elif data['max'] > 1:
                status = "⚠️ DEGRADED"
            else:
                status = "✅ HEALTHY"
            
            lines.append(f"- **{region}**: {data['avg']}% errors (avg), {data['max']}% (max) {status}")
    else:
        lines.append("- Regional data available for all metrics")
    
    lines.append("")
    
    # Anomalies
    if anomaly_count > 0:
        lines.append("## 🔍 Anomalies Detected")
        lines.append(f"- **{anomaly_count} anomalies** detected in the last {hours} hours")
        lines.append(f"- Run `show anomalies for {service}` for details")
        lines.append("")
    
    # Recommendations
    lines.append("## 💡 Recommendations")
    
    recommendations = []
    
    # Check for high error rates
    if 'error_rate' in metrics and metrics['error_rate']['max'] > 5:
        recommendations.append(f"🚨 **URGENT**: Error rate spiked to {metrics['error_rate']['max']}% - investigate immediately")
    
    # Check for high latency
    if 'p99_latency' in metrics and metrics['p99_latency']['max'] > 1000:
        recommendations.append(f"⚠️ **HIGH PRIORITY**: P99 latency reached {metrics['p99_latency']['max']}ms - check database connections")
    
    # Check for high CPU
    if 'cpu_usage' in metrics and metrics['cpu_usage']['max'] > 90:
        recommendations.append(f"⚠️ CPU usage at {metrics['cpu_usage']['max']}% - consider scaling up")
    
    # Check for high memory
    if 'memory_usage' in metrics and metrics['memory_usage']['max'] > 90:
        recommendations.append(f"⚠️ Memory usage at {metrics['memory_usage']['max']}% - check for memory leaks")
    
    # Check regional issues
    if 'error_rate' in metrics and metrics['error_rate']['regions']:
        for region, data in metrics['error_rate']['regions'].items():
            if data['max'] > 5:
                recommendations.append(f"🚨 **{region}** region critical - {data['max']}% error rate")
    
    if recommendations:
        for rec in recommendations:
            lines.append(f"- {rec}")
    else:
        lines.append("- ✅ Service operating within normal parameters")
        lines.append("- Continue monitoring for trends")
    
    return "\n".join(lines)


@router.get("/service_health")
async def compare_service_health():
    """Compare health across all services"""
    try:
        # Query last hour of metrics
        now = datetime.utcnow()
        start_time = now - timedelta(hours=1)
        
        query = {
            "query": {
                "range": {"@timestamp": {"gte": start_time.isoformat(), "lte": now.isoformat()}}
            },
            "size": 0,
            "aggs": {
                "by_service": {
                    "terms": {"field": "service", "size": 20},
                    "aggs": {
                        "avg_latency": {
                            "avg": {
                                "field": "value",
                                "script": {
                                    "source": "doc['metric_name'].value == 'p99_latency' ? doc['value'].value : 0"
                                }
                            }
                        },
                        "avg_error_rate": {
                            "avg": {
                                "field": "value",
                                "script": {
                                    "source": "doc['metric_name'].value == 'error_rate' ? doc['value'].value : 0"
                                }
                            }
                        },
                        "avg_cpu": {
                            "avg": {
                                "field": "value",
                                "script": {
                                    "source": "doc['metric_name'].value == 'cpu_usage' ? doc['value'].value : 0"
                                }
                            }
                        }
                    }
                }
            }
        }
        
        result = es.search(index="metrics", body=query)
        
        services = []
        for bucket in result['aggregations']['by_service']['buckets']:
            services.append({
                "service": bucket['key'],
                "latency": round(bucket['avg_latency']['value'], 2),
                "error_rate": round(bucket['avg_error_rate']['value'], 2),
                "cpu": round(bucket['avg_cpu']['value'], 2)
            })
        
        # Sort by error rate (worst first)
        services.sort(key=lambda x: x['error_rate'], reverse=True)
        
        return {
            "success": True,
            "services": services,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/active_anomalies")
async def get_active_anomalies():
    """Get all active anomalies"""
    try:
        query = {
            "query": {
                "terms": {"status": ["active", "investigating"]}
            },
            "sort": [{"deviation_sigma": "desc"}, {"detected_at": "desc"}],
            "size": 50
        }
        
        result = es.search(index="anomaly-records", body=query)
        
        anomalies = []
        for hit in result['hits']['hits']:
            anomalies.append(hit['_source'])
        
        return {
            "success": True,
            "count": len(anomalies),
            "anomalies": anomalies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get anomalies: {str(e)}")


@router.get("/incident_stats")
async def get_incident_statistics():
    """Get incident statistics by service"""
    try:
        query = {
            "size": 0,
            "aggs": {
                "by_service": {
                    "terms": {"field": "service", "size": 20},
                    "aggs": {
                        "total": {"value_count": {"field": "id"}},
                        "sev1": {
                            "filter": {"term": {"severity": "Sev-1"}}
                        },
                        "sev2": {
                            "filter": {"term": {"severity": "Sev-2"}}
                        },
                        "sev3": {
                            "filter": {"term": {"severity": "Sev-3"}}
                        },
                        "avg_mttr": {"avg": {"field": "mttr_minutes"}}
                    }
                }
            }
        }
        
        result = es.search(index="incident-history", body=query)
        
        stats = []
        for bucket in result['aggregations']['by_service']['buckets']:
            stats.append({
                "service": bucket['key'],
                "total_incidents": bucket['total']['value'],
                "sev1_count": bucket['sev1']['doc_count'],
                "sev2_count": bucket['sev2']['doc_count'],
                "sev3_count": bucket['sev3']['doc_count'],
                "avg_mttr_minutes": round(bucket['avg_mttr']['value'], 1) if bucket['avg_mttr']['value'] else 0
            })
        
        # Sort by total incidents
        stats.sort(key=lambda x: x['total_incidents'], reverse=True)
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")



class ComprehensiveMetricsRequest(BaseModel):
    service: str
    time_range: str = "24h"
    include_comparison: bool = True


@router.post("/comprehensive_metrics")
async def comprehensive_metrics_analysis(request: ComprehensiveMetricsRequest):
    """
    COMPREHENSIVE metrics analysis with rich visualizations and insights
    Returns: statistics, trends, comparisons, anomalies, and recommendations
    """
    try:
        service = request.service
        time_range = request.time_range
        
        # Parse time range
        hours_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
        hours = hours_map.get(time_range, 24)
        
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)
        
        # Query current period metrics
        current_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"service": service}},
                        {"range": {"@timestamp": {"gte": start_time.isoformat(), "lte": now.isoformat()}}}
                    ]
                }
            },
            "size": 0,
            "aggs": {
                "by_metric": {
                    "terms": {"field": "metric_name", "size": 50},
                    "aggs": {
                        "stats": {
                            "stats": {"field": "value"}
                        },
                        "percentiles": {
                            "percentiles": {
                                "field": "value",
                                "percents": [50, 75, 90, 95, 99]
                            }
                        },
                        "over_time": {
                            "date_histogram": {
                                "field": "@timestamp",
                                "fixed_interval": f"{max(1, hours//12)}h"
                            },
                            "aggs": {
                                "avg_value": {"avg": {"field": "value"}},
                                "max_value": {"max": {"field": "value"}}
                            }
                        }
                    }
                },
                "anomaly_count": {
                    "filter": {"term": {"is_anomaly": True}}
                }
            }
        }
        
        current_result = es.search(index="metrics", body=current_query)
        
        # Query previous period for comparison
        comparison_data = None
        if request.include_comparison:
            prev_start = start_time - timedelta(hours=hours)
            prev_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"service": service}},
                            {"range": {"@timestamp": {"gte": prev_start.isoformat(), "lt": start_time.isoformat()}}}
                        ]
                    }
                },
                "size": 0,
                "aggs": {
                    "by_metric": {
                        "terms": {"field": "metric_name", "size": 50},
                        "aggs": {
                            "avg_value": {"avg": {"field": "value"}},
                            "max_value": {"max": {"field": "value"}}
                        }
                    }
                }
            }
            
            prev_result = es.search(index="metrics", body=prev_query)
            comparison_data = {}
            for bucket in prev_result['aggregations']['by_metric']['buckets']:
                comparison_data[bucket['key']] = {
                    "avg": bucket['avg_value']['value'],
                    "max": bucket['max_value']['value']
                }
        
        # Build comprehensive analysis
        analysis = build_comprehensive_analysis(
            service,
            time_range,
            current_result,
            comparison_data
        )
        
        return {
            "success": True,
            "service": service,
            "time_range": time_range,
            "generated_at": now.isoformat(),
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive analysis failed: {str(e)}")


def build_comprehensive_analysis(service: str, time_range: str, current_data: Dict, comparison_data: Dict = None) -> str:
    """Build rich, comprehensive analysis with tables, trends, and insights"""
    
    lines = []
    lines.append(f"# 📊 Comprehensive Metrics Analysis: {service.upper()}")
    lines.append(f"**Time Range**: Last {time_range} | **Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Extract metrics data
    metrics_buckets = current_data['aggregations']['by_metric']['buckets']
    anomaly_count = current_data['aggregations']['anomaly_count']['doc_count']
    
    if not metrics_buckets:
        lines.append("⚠️ **No metrics data found for this service in the specified time range.**")
        return "\n".join(lines)
    
    # 1. EXECUTIVE SUMMARY
    lines.append("## 📋 Executive Summary")
    lines.append("")
    
    # Calculate health score
    health_issues = []
    for bucket in metrics_buckets:
        metric_name = bucket['key']
        stats = bucket['stats']
        
        if metric_name == 'error_rate' and stats['max'] > 5:
            health_issues.append(f"High error rate: {stats['max']:.2f}%")
        elif metric_name == 'p99_latency' and stats['max'] > 1000:
            health_issues.append(f"High latency: {stats['max']:.0f}ms")
        elif metric_name == 'cpu_usage' and stats['max'] > 90:
            health_issues.append(f"CPU saturation: {stats['max']:.1f}%")
        elif metric_name == 'memory_usage' and stats['max'] > 90:
            health_issues.append(f"Memory pressure: {stats['max']:.1f}%")
    
    if health_issues:
        lines.append(f"**Status**: 🚨 **ATTENTION REQUIRED** ({len(health_issues)} issues detected)")
        for issue in health_issues:
            lines.append(f"- ⚠️ {issue}")
    elif anomaly_count > 5:
        lines.append(f"**Status**: ⚠️ **MONITORING** ({anomaly_count} anomalies detected)")
    else:
        lines.append("**Status**: ✅ **HEALTHY** (All metrics within normal range)")
    
    lines.append("")
    lines.append(f"**Metrics Tracked**: {len(metrics_buckets)} | **Anomalies**: {anomaly_count}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 2. KEY METRICS TABLE
    lines.append("## 📈 Key Metrics Overview")
    lines.append("")
    lines.append("| Metric | Current Avg | Min | Max | P95 | P99 | Trend |")
    lines.append("|--------|-------------|-----|-----|-----|-----|-------|")
    
    for bucket in metrics_buckets[:10]:  # Top 10 metrics
        metric_name = bucket['key']
        stats = bucket['stats']
        percentiles = bucket['percentiles']['values']
        
        # Calculate trend
        trend = "→"
        if comparison_data and metric_name in comparison_data:
            prev_avg = comparison_data[metric_name]['avg']
            curr_avg = stats['avg']
            if curr_avg > prev_avg * 1.1:
                trend = "📈 +{:.1f}%".format(((curr_avg - prev_avg) / prev_avg) * 100)
            elif curr_avg < prev_avg * 0.9:
                trend = "📉 -{:.1f}%".format(((prev_avg - curr_avg) / prev_avg) * 100)
        
        # Format values based on metric type
        if 'latency' in metric_name:
            unit = "ms"
            fmt = ".0f"
        elif 'rate' in metric_name or 'usage' in metric_name:
            unit = "%"
            fmt = ".1f"
        else:
            unit = ""
            fmt = ".2f"
        
        lines.append(f"| {metric_name} | {stats['avg']:{fmt}}{unit} | {stats['min']:{fmt}}{unit} | {stats['max']:{fmt}}{unit} | {percentiles.get('95.0', 0):{fmt}}{unit} | {percentiles.get('99.0', 0):{fmt}}{unit} | {trend} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 3. PERFORMANCE ANALYSIS
    lines.append("## ⚡ Performance Analysis")
    lines.append("")
    
    # Latency analysis
    latency_metrics = [b for b in metrics_buckets if 'latency' in b['key']]
    if latency_metrics:
        lines.append("### Response Time Distribution")
        lines.append("")
        for bucket in latency_metrics:
            metric_name = bucket['key']
            percentiles = bucket['percentiles']['values']
            
            lines.append(f"**{metric_name}**:")
            lines.append(f"- P50 (Median): {percentiles.get('50.0', 0):.0f}ms")
            lines.append(f"- P75: {percentiles.get('75.0', 0):.0f}ms")
            lines.append(f"- P90: {percentiles.get('90.0', 0):.0f}ms")
            lines.append(f"- P95: {percentiles.get('95.0', 0):.0f}ms")
            lines.append(f"- P99: {percentiles.get('99.0', 0):.0f}ms")
            
            # Performance assessment
            p99 = percentiles.get('99.0', 0)
            if p99 > 1000:
                lines.append(f"  - 🚨 **CRITICAL**: P99 latency exceeds 1 second")
            elif p99 > 500:
                lines.append(f"  - ⚠️ **WARNING**: P99 latency elevated")
            else:
                lines.append(f"  - ✅ **GOOD**: Latency within acceptable range")
            
            lines.append("")
    
    # Error rate analysis
    error_metrics = [b for b in metrics_buckets if 'error' in b['key']]
    if error_metrics:
        lines.append("### Error Rate Analysis")
        lines.append("")
        for bucket in error_metrics:
            metric_name = bucket['key']
            stats = bucket['stats']
            
            lines.append(f"**{metric_name}**:")
            lines.append(f"- Average: {stats['avg']:.2f}%")
            lines.append(f"- Peak: {stats['max']:.2f}%")
            
            if stats['max'] > 5:
                lines.append(f"  - 🚨 **CRITICAL**: Error rate spike detected")
            elif stats['max'] > 1:
                lines.append(f"  - ⚠️ **WARNING**: Elevated error rate")
            else:
                lines.append(f"  - ✅ **HEALTHY**: Error rate within SLA")
            
            lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 4. RESOURCE UTILIZATION
    lines.append("## 💻 Resource Utilization")
    lines.append("")
    
    resource_metrics = [b for b in metrics_buckets if any(x in b['key'] for x in ['cpu', 'memory', 'disk'])]
    if resource_metrics:
        lines.append("| Resource | Avg Usage | Peak Usage | Status |")
        lines.append("|----------|-----------|------------|--------|")
        
        for bucket in resource_metrics:
            metric_name = bucket['key']
            stats = bucket['stats']
            
            if stats['max'] > 90:
                status = "🚨 CRITICAL"
            elif stats['max'] > 75:
                status = "⚠️ HIGH"
            else:
                status = "✅ NORMAL"
            
            lines.append(f"| {metric_name} | {stats['avg']:.1f}% | {stats['max']:.1f}% | {status} |")
        
        lines.append("")
    else:
        lines.append("*No resource utilization metrics available*")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 5. TREND ANALYSIS
    lines.append("## 📊 Trend Analysis")
    lines.append("")
    
    if comparison_data:
        lines.append("### Period-over-Period Comparison")
        lines.append("")
        lines.append("| Metric | Previous Period | Current Period | Change |")
        lines.append("|--------|----------------|----------------|--------|")
        
        for bucket in metrics_buckets[:8]:
            metric_name = bucket['key']
            curr_avg = bucket['stats']['avg']
            
            if metric_name in comparison_data:
                prev_avg = comparison_data[metric_name]['avg']
                change_pct = ((curr_avg - prev_avg) / prev_avg * 100) if prev_avg > 0 else 0
                
                if abs(change_pct) > 20:
                    indicator = "🚨" if change_pct > 0 else "📉"
                elif abs(change_pct) > 10:
                    indicator = "⚠️" if change_pct > 0 else "📊"
                else:
                    indicator = "→"
                
                lines.append(f"| {metric_name} | {prev_avg:.2f} | {curr_avg:.2f} | {indicator} {change_pct:+.1f}% |")
        
        lines.append("")
    else:
        lines.append("*Enable comparison to see period-over-period trends*")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 6. ANOMALIES
    if anomaly_count > 0:
        lines.append("## 🔍 Anomaly Detection")
        lines.append("")
        lines.append(f"**{anomaly_count} anomalies** detected in the last {time_range}")
        lines.append("")
        lines.append("Anomalies indicate unusual patterns that may require investigation:")
        lines.append(f"- Run `show anomalies for {service}` for detailed breakdown")
        lines.append(f"- Check `investigate incident INC-XXXX` for related incidents")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # 7. ACTIONABLE RECOMMENDATIONS
    lines.append("## 💡 Actionable Recommendations")
    lines.append("")
    
    recommendations = []
    priority_actions = []
    
    # Analyze each metric for recommendations
    for bucket in metrics_buckets:
        metric_name = bucket['key']
        stats = bucket['stats']
        
        if metric_name == 'error_rate':
            if stats['max'] > 10:
                priority_actions.append(f"🚨 **IMMEDIATE**: Error rate at {stats['max']:.1f}% - Investigate logs and recent deployments")
            elif stats['max'] > 5:
                recommendations.append(f"⚠️ Error rate elevated to {stats['max']:.1f}% - Review error logs")
        
        elif metric_name == 'p99_latency':
            if stats['max'] > 2000:
                priority_actions.append(f"🚨 **IMMEDIATE**: P99 latency at {stats['max']:.0f}ms - Check database queries and external dependencies")
            elif stats['max'] > 1000:
                recommendations.append(f"⚠️ P99 latency at {stats['max']:.0f}ms - Consider query optimization")
        
        elif metric_name == 'cpu_usage':
            if stats['max'] > 95:
                priority_actions.append(f"🚨 **IMMEDIATE**: CPU at {stats['max']:.1f}% - Scale horizontally or optimize hot paths")
            elif stats['max'] > 85:
                recommendations.append(f"⚠️ CPU usage high at {stats['max']:.1f}% - Plan for capacity increase")
        
        elif metric_name == 'memory_usage':
            if stats['max'] > 95:
                priority_actions.append(f"🚨 **IMMEDIATE**: Memory at {stats['max']:.1f}% - Check for memory leaks")
            elif stats['max'] > 85:
                recommendations.append(f"⚠️ Memory usage high at {stats['max']:.1f}% - Review memory allocation")
    
    if priority_actions:
        lines.append("### 🚨 Priority Actions")
        for action in priority_actions:
            lines.append(f"- {action}")
        lines.append("")
    
    if recommendations:
        lines.append("### ⚠️ Recommendations")
        for rec in recommendations:
            lines.append(f"- {rec}")
        lines.append("")
    
    if not priority_actions and not recommendations:
        lines.append("✅ **All systems operating normally**")
        lines.append("")
        lines.append("Continue monitoring:")
        lines.append("- Set up alerts for error rate > 5%")
        lines.append("- Monitor P99 latency trends")
        lines.append("- Track resource utilization growth")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 8. NEXT STEPS
    lines.append("## 🎯 Next Steps")
    lines.append("")
    lines.append("1. **Monitor**: Continue tracking key metrics")
    lines.append("2. **Investigate**: Review any anomalies or spikes")
    lines.append("3. **Optimize**: Address performance bottlenecks")
    lines.append("4. **Scale**: Plan capacity based on trends")
    lines.append("")
    lines.append("**Commands**:")
    lines.append(f"- `show anomalies for {service}` - View detailed anomalies")
    lines.append(f"- `show incidents for {service}` - Check related incidents")
    lines.append(f"- `analyze {service} over 7d` - Extended trend analysis")
    
    return "\n".join(lines)
