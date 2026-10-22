import json
import os

os.makedirs(r"c:\src\FinWise-ML-Projem\grafana\dashboards", exist_ok=True)

# 1. model_performance.json
model_performance = {
  "title": "Model Performance",
  "uid": "model_perf_1",
  "refresh": "30s",
  "panels": [
    {
      "title": "Model Accuracy over Time",
      "type": "gauge",
      "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
      "targets": [{"expr": "model_accuracy", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "AUC-ROC Trend",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 16, "x": 8, "y": 0},
      "targets": [{"expr": "model_auc_roc", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Precision & Recall",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
      "targets": [
        {"expr": "model_precision", "refId": "A"},
        {"expr": "model_recall", "refId": "B"}
      ],
      "datasource": "${datasource}"
    },
    {
      "title": "Prediction Latency (P95/P99)",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
      "targets": [
        {"expr": "histogram_quantile(0.95, sum(rate(model_prediction_latency_seconds_bucket[5m])) by (le))", "refId": "A", "legendFormat": "P95"},
        {"expr": "histogram_quantile(0.99, sum(rate(model_prediction_latency_seconds_bucket[5m])) by (le))", "refId": "B", "legendFormat": "P99"}
      ],
      "datasource": "${datasource}"
    },
    {
      "title": "PSI Drift Metric",
      "type": "stat",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
      "targets": [{"expr": "model_dataset_drift", "refId": "A"}],
      "fieldConfig": {
        "defaults": {
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "orange", "value": 0.2},
              {"color": "red", "value": 0.3}
            ]
          }
        }
      },
      "datasource": "${datasource}"
    },
    {
      "title": "KS-Test Metric",
      "type": "stat",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
      "targets": [{"expr": "model_ks_test", "refId": "A"}],
      "fieldConfig": {
        "defaults": {
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "orange", "value": 0.05},
              {"color": "red", "value": 0.1}
            ]
          }
        }
      },
      "datasource": "${datasource}"
    }
  ],
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus",
        "current": {"value": "default"}
      }
    ]
  }
}

# 2. fairness_monitoring.json
fairness_monitoring = {
  "title": "Fairness Monitoring",
  "uid": "fairness_mon_1",
  "refresh": "30s",
  "panels": [
    {
      "title": "Disparate Impact Ratio",
      "type": "gauge",
      "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
      "targets": [{"expr": "finwise_fairness_di_ratio", "refId": "A"}],
      "fieldConfig": {
        "defaults": {
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "red", "value": null},
              {"color": "orange", "value": 0.75},
              {"color": "green", "value": 0.8}
            ]
          }
        }
      },
      "datasource": "${datasource}"
    },
    {
      "title": "DI Trend over Time",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 16, "x": 8, "y": 0},
      "targets": [{"expr": "finwise_fairness_di_ratio", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Group-wise Approval Rates",
      "type": "barchart",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
      "targets": [{"expr": "finwise_fairness_group_approval_rate", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Fairness Alert History",
      "type": "table",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
      "targets": [{"expr": "ALERTS{alertname=~\"LowDisparateImpact|VeryLowDisparateImpact\"}", "refId": "A"}],
      "datasource": "${datasource}"
    }
  ],
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus",
        "current": {"value": "default"}
      }
    ]
  }
}

# 3. api_health.json
api_health = {
  "title": "API Health",
  "uid": "api_health_1",
  "refresh": "10s",
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
      "targets": [{"expr": "sum(rate(http_requests_total[5m])) by (endpoint)", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Error Rate (4xx/5xx)",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
      "targets": [{"expr": "sum(rate(http_requests_total{status=~\"4..|5..\"}[5m])) by (status)", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Response Time (P50/P95/P99)",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 16, "x": 0, "y": 8},
      "targets": [
        {"expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "refId": "A", "legendFormat": "P50"},
        {"expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "refId": "B", "legendFormat": "P95"},
        {"expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "refId": "C", "legendFormat": "P99"}
      ],
      "datasource": "${datasource}"
    },
    {
      "title": "Active Connections",
      "type": "stat",
      "gridPos": {"h": 8, "w": 8, "x": 16, "y": 8},
      "targets": [{"expr": "http_active_connections", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Top Slowest Endpoints",
      "type": "table",
      "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16},
      "targets": [{"expr": "topk(5, sum(rate(http_request_duration_seconds_sum[5m])) by (endpoint) / sum(rate(http_request_duration_seconds_count[5m])) by (endpoint))", "refId": "A"}],
      "datasource": "${datasource}"
    }
  ],
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus",
        "current": {"value": "default"}
      }
    ]
  }
}

# 4. system_resources.json
system_resources = {
  "title": "System Resources",
  "uid": "system_resources_1",
  "refresh": "30s",
  "panels": [
    {
      "title": "CPU Usage %",
      "type": "gauge",
      "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
      "targets": [{"expr": "system_cpu_usage_percent", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Memory Usage %",
      "type": "gauge",
      "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
      "targets": [{"expr": "system_memory_usage_percent", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Disk Usage %",
      "type": "gauge",
      "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
      "targets": [{"expr": "system_disk_usage_percent", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "PostgreSQL Active Connections",
      "type": "stat",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
      "targets": [{"expr": "pg_stat_activity_count", "refId": "A"}],
      "datasource": "${datasource}"
    },
    {
      "title": "Redis Memory Usage",
      "type": "stat",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
      "targets": [{"expr": "redis_memory_used_bytes", "refId": "A"}],
      "datasource": "${datasource}"
    }
  ],
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus",
        "current": {"value": "default"}
      }
    ]
  }
}

base_dir = r"c:\src\FinWise-ML-Projem\grafana\dashboards"
with open(os.path.join(base_dir, "model_performance.json"), "w") as f:
    json.dump(model_performance, f, indent=2)
with open(os.path.join(base_dir, "fairness_monitoring.json"), "w") as f:
    json.dump(fairness_monitoring, f, indent=2)
with open(os.path.join(base_dir, "api_health.json"), "w") as f:
    json.dump(api_health, f, indent=2)
with open(os.path.join(base_dir, "system_resources.json"), "w") as f:
    json.dump(system_resources, f, indent=2)

print("Dashboards created successfully!")
