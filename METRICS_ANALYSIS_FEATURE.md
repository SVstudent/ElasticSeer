# 📊 Comprehensive Metrics Analysis Feature

## Overview

Enhanced metrics and logs analysis with rich visualizations, tables, trends, and actionable insights based on real Elasticsearch data.

---

## What's New

### Before
```
User: "Analyze metrics for api-gateway"
Agent: "I did not find any anomalies. All metrics appear normal."
```

### After
```
User: "Analyze metrics for api-gateway"
Agent: [Comprehensive analysis with]:
  - Executive summary with health status
  - Key metrics table with trends
  - Performance analysis (latency, errors)
  - Resource utilization breakdown
  - Period-over-period comparison
  - Anomaly detection
  - Actionable recommendations
  - Next steps
```

---

## New Function: `analyze_service_metrics`

### Description
Provides COMPREHENSIVE metrics analysis with:
- **Statistics**: Min, max, avg, percentiles (P50, P75, P90, P95, P99)
- **Trends**: Period-over-period comparison with % change
- **Visualizations**: Tables showing metric distributions
- **Anomaly Detection**: Identifies unusual patterns
- **Recommendations**: Actionable insights based on data
- **Health Assessment**: Overall service health status

### Parameters
```python
{
    "service": "api-gateway",        # Required
    "time_range": "24h",             # Optional: 1h, 6h, 24h, 7d
    "include_comparison": true       # Optional: Compare with previous period
}
```

---

## Example Output

### Executive Summary
```
📋 Executive Summary

Status: ⚠️ MONITORING (3 anomalies detected)

Metrics Tracked: 12 | Anomalies: 3
```

### Key Metrics Table
```
| Metric        | Current Avg | Min    | Max    | P95    | P99    | Trend      |
|---------------|-------------|--------|--------|--------|--------|------------|
| p99_latency   | 245ms       | 120ms  | 890ms  | 650ms  | 890ms  | 📈 +15.3%  |
| error_rate    | 0.8%        | 0.1%   | 3.2%   | 2.1%   | 3.2%   | → 0.0%     |
| cpu_usage     | 45.2%       | 25.0%  | 78.5%  | 72.0%  | 78.5%  | 📉 -5.2%   |
| memory_usage  | 62.1%       | 48.0%  | 85.3%  | 82.0%  | 85.3%  | 📈 +8.1%   |
```

### Performance Analysis
```
⚡ Performance Analysis

Response Time Distribution

p99_latency:
- P50 (Median): 210ms
- P75: 285ms
- P90: 450ms
- P95: 650ms
- P99: 890ms
  - ✅ GOOD: Latency within acceptable range

Error Rate Analysis

error_rate:
- Average: 0.8%
- Peak: 3.2%
  - ⚠️ WARNING: Elevated error rate
```

### Resource Utilization
```
💻 Resource Utilization

| Resource      | Avg Usage | Peak Usage | Status     |
|---------------|-----------|------------|------------|
| cpu_usage     | 45.2%     | 78.5%      | ✅ NORMAL  |
| memory_usage  | 62.1%     | 85.3%      | ⚠️ HIGH    |
| disk_usage    | 35.8%     | 42.1%      | ✅ NORMAL  |
```

### Trend Analysis
```
📊 Trend Analysis

Period-over-Period Comparison

| Metric       | Previous Period | Current Period | Change      |
|--------------|----------------|----------------|-------------|
| p99_latency  | 212.50         | 245.00         | ⚠️ +15.3%   |
| error_rate   | 0.80           | 0.80           | → +0.0%     |
| cpu_usage    | 47.70          | 45.20          | 📊 -5.2%    |
| memory_usage | 57.50          | 62.10          | ⚠️ +8.0%    |
```

### Actionable Recommendations
```
💡 Actionable Recommendations

⚠️ Recommendations
- ⚠️ Error rate elevated to 3.2% - Review error logs
- ⚠️ Memory usage high at 85.3% - Review memory allocation

🎯 Next Steps

1. Monitor: Continue tracking key metrics
2. Investigate: Review any anomalies or spikes
3. Optimize: Address performance bottlenecks
4. Scale: Plan capacity based on trends

Commands:
- `show anomalies for api-gateway` - View detailed anomalies
- `show incidents for api-gateway` - Check related incidents
- `analyze api-gateway over 7d` - Extended trend analysis
```

---

## Usage Examples

### Basic Analysis
```
User: "Analyze metrics for auth-service"
Agent: [Comprehensive analysis with all sections]
```

### With Time Range
```
User: "Analyze api-gateway metrics over the last 7 days"
Agent: [Analysis with 7-day data and trends]
```

### Multiple Services
```
User: "Compare metrics for api-gateway, auth-service, and database"
Agent: [Analyzes each service and provides comparison]
```

### Specific Focus
```
User: "Show me latency and error rate trends for payment service"
Agent: [Focused analysis on latency and errors]
```

---

## Technical Implementation

### Backend Endpoint
```python
POST /api/analysis/comprehensive_metrics
{
    "service": "api-gateway",
    "time_range": "24h",
    "include_comparison": true
}
```

### Data Sources
- **Elasticsearch**: Real metrics data from `metrics` index
- **Aggregations**: Stats, percentiles, histograms
- **Time Series**: Date histograms for trends
- **Anomalies**: Filtered queries for anomaly detection

### Analysis Components

1. **Executive Summary**
   - Health status calculation
   - Issue detection
   - Anomaly count

2. **Key Metrics Table**
   - Statistics (min, max, avg)
   - Percentiles (P50, P75, P90, P95, P99)
   - Trend indicators with % change

3. **Performance Analysis**
   - Latency distribution
   - Error rate assessment
   - SLA compliance check

4. **Resource Utilization**
   - CPU, memory, disk usage
   - Peak vs average
   - Status indicators

5. **Trend Analysis**
   - Period-over-period comparison
   - Change percentages
   - Visual indicators

6. **Anomaly Detection**
   - Count of anomalies
   - Severity assessment
   - Investigation links

7. **Recommendations**
   - Priority actions (critical issues)
   - General recommendations
   - Next steps with commands

---

## Health Status Logic

### 🚨 ATTENTION REQUIRED
- Error rate > 5%
- P99 latency > 1000ms
- CPU usage > 90%
- Memory usage > 90%

### ⚠️ MONITORING
- 5+ anomalies detected
- Elevated metrics but not critical

### ✅ HEALTHY
- All metrics within normal range
- < 5 anomalies
- No critical issues

---

## Trend Indicators

- **📈** Increase > 10%
- **📉** Decrease > 10%
- **→** Change < 10%
- **🚨** Critical increase > 20%
- **⚠️** Warning increase 10-20%

---

## Integration with Agent

The agent automatically uses `analyze_service_metrics` when:
- User asks to "analyze metrics"
- User requests "show performance"
- User wants "detailed analysis"
- User asks about "trends" or "statistics"

The agent uses `get_metrics_anomalies` for:
- Quick anomaly checks
- Simple queries
- Anomaly-focused requests

---

## Benefits

1. **Data-Driven**: Real Elasticsearch data, not generic responses
2. **Actionable**: Specific recommendations based on actual metrics
3. **Visual**: Tables and indicators for easy understanding
4. **Comprehensive**: All aspects covered in one analysis
5. **Comparative**: Period-over-period trends
6. **Proactive**: Identifies issues before they become critical

---

## Files Modified

1. **backend/app/api/agent_chat_gemini.py**
   - Added `analyze_service_metrics` function
   - Added execution logic
   - Updated system prompt
   - Added fallback response handling

2. **backend/app/api/rich_analysis.py**
   - Added `comprehensive_metrics_analysis` endpoint
   - Added `build_comprehensive_analysis` function
   - Implemented rich formatting logic

---

## Testing

```bash
# Start backend
cd backend
uvicorn app.main:app --reload --port 8001

# Test in chat UI
User: "Analyze metrics for api-gateway"
Expected: Comprehensive analysis with tables and insights
```

---

**Now metrics analysis is truly data-driven and actionable!** 📊✨
