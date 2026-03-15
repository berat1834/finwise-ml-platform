#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SLA Monitoring & Support Management System
Tracks API performance, uptime, and support metrics
"""
import time
import json
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List
import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ============================================================
# SLA CONFIGURATIONS
# ============================================================

SLA_TIERS = {
    'STARTER': {
        'response_time_ms': 2000,      # P95 response time
        'availability': 0.99,          # 99% uptime
        'requests_per_day': 1000,
        'support_response_hours': 24,
        'monthly_cost': 500,
        'description': '100 istekler/günü, E-posta desteği'
    },
    'PRO': {
        'response_time_ms': 500,
        'availability': 0.995,         # 99.5% uptime
        'requests_per_day': 50000,
        'support_response_hours': 4,
        'monthly_cost': 2000,
        'description': '50k istek/gün, 4 saat support'
    },
    'ENTERPRISE': {
        'response_time_ms': 200,
        'availability': 0.999,         # 99.9% uptime
        'requests_per_day': 1000000,
        'support_response_hours': 1,
        'monthly_cost': 10000,
        'description': 'Unlimited, 1 saat support, custom SLA'
    }
}

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class RequestMetric:
    """API request metric"""
    request_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: datetime
    customer_id: str = None
    error_message: str = None

@dataclass
class SLAViolation:
    """SLA İhlali kaydı"""
    violation_id: str
    customer_id: str
    tier: str
    metric_type: str          # response_time, availability
    threshold: float
    actual_value: float
    violation_date: datetime
    severity: str             # critical, warning
    resolved: bool = False
    resolution_notes: str = None

@dataclass
class SLAReport:
    """Aylık SLA raporu"""
    customer_id: str
    month: str
    tier: str
    uptime_percentage: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    error_rate: float
    total_requests: int
    total_violations: int
    sla_met: bool
    credit_percentage: float  # SLA İhlali kredisi


# ============================================================
# SLA MONITORING ENGINE
# ============================================================

class SLAMonitor:
    """
    SLA performansını ve uygunluğunu izler
    """
    
    def __init__(self, db_path: str = 'sla_metrics.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """SLA metrikleri için veritabanı oluştur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Request metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_metrics (
                request_id TEXT PRIMARY KEY,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                response_time_ms REAL NOT NULL,
                timestamp TEXT NOT NULL,
                customer_id TEXT,
                error_message TEXT
            )
        ''')
        
        # SLA violations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sla_violations (
                violation_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                tier TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                threshold REAL NOT NULL,
                actual_value REAL NOT NULL,
                violation_date TEXT NOT NULL,
                severity TEXT NOT NULL,
                resolved BOOLEAN DEFAULT 0,
                resolution_notes TEXT
            )
        ''')
        
        # SLA reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sla_reports (
                report_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                month TEXT NOT NULL,
                tier TEXT NOT NULL,
                uptime_percentage REAL NOT NULL,
                p95_response_time_ms REAL NOT NULL,
                p99_response_time_ms REAL NOT NULL,
                error_rate REAL NOT NULL,
                total_requests INTEGER NOT NULL,
                total_violations INTEGER NOT NULL,
                sla_met BOOLEAN NOT NULL,
                credit_percentage REAL NOT NULL,
                generated_at TEXT NOT NULL
            )
        ''')
        
        # Customer subscriptions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_subscriptions (
                customer_id TEXT PRIMARY KEY,
                tier TEXT NOT NULL,
                start_date TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                contact_email TEXT,
                contact_name TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_request(self, metric: RequestMetric):
        """API isteğini kaydet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO request_metrics 
            (request_id, endpoint, method, status_code, response_time_ms, timestamp, customer_id, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metric.request_id,
            metric.endpoint,
            metric.method,
            metric.status_code,
            metric.response_time_ms,
            metric.timestamp.isoformat(),
            metric.customer_id,
            metric.error_message
        ))
        
        conn.commit()
        conn.close()
        
        # SLA uygunluğunu kontrol et
        self._check_sla_compliance(metric)
    
    def _check_sla_compliance(self, metric: RequestMetric):
        """Metriğe karşı SLA kontrol et"""
        if not metric.customer_id:
            return
        
        # Müşteri tier'ını getir
        tier = self.get_customer_tier(metric.customer_id)
        if not tier:
            return
        
        sla = SLA_TIERS[tier]
        
        # Response time kontrolü
        if metric.response_time_ms > sla['response_time_ms']:
            self._record_violation(
                customer_id=metric.customer_id,
                tier=tier,
                metric_type='response_time',
                threshold=sla['response_time_ms'],
                actual_value=metric.response_time_ms,
                severity='warning'
            )
        
        # Error response kontrolü
        if 500 <= metric.status_code < 600:
            self._record_violation(
                customer_id=metric.customer_id,
                tier=tier,
                metric_type='error',
                threshold=0.01,  # %1 max error
                actual_value=1.0,
                severity='critical'
            )
    
    def _record_violation(self, customer_id: str, tier: str, metric_type: str, 
                         threshold: float, actual_value: float, severity: str):
        """SLA İhlaline kaydını yap"""
        violation_id = f"{customer_id}_{metric_type}_{datetime.now(timezone.utc).isoformat()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sla_violations 
            (violation_id, customer_id, tier, metric_type, threshold, actual_value, violation_date, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            violation_id, customer_id, tier, metric_type, threshold, actual_value,
            datetime.now(timezone.utc).isoformat(), severity
        ))
        
        conn.commit()
        conn.close()
        
        # Alert gönder
        self._send_alert(customer_id, severity, metric_type, actual_value, threshold)
    
    def _send_alert(self, customer_id: str, severity: str, metric_type: str, 
                    actual_value: float, threshold: float):
        """SLA ihlali alert'i gönder"""
        logger.warning(
            f"SLA_VIOLATION: Customer={customer_id}, Type={metric_type}, "
            f"Threshold={threshold}, Actual={actual_value}, Severity={severity}"
        )
        # TODO: Email/Slack notification gönder
    
    def get_customer_tier(self, customer_id: str) -> str:
        """Müşteri tier'ını getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT tier FROM customer_subscriptions WHERE customer_id = ?', (customer_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def register_customer(self, customer_id: str, tier: str, contact_email: str, contact_name: str):
        """Müşteri tier'ı kaydet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO customer_subscriptions 
            (customer_id, tier, start_date, contact_email, contact_name, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        ''', (
            customer_id, tier, datetime.now(timezone.utc).isoformat(), contact_email, contact_name
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Registered customer {customer_id} with tier {tier}")
    
    def generate_monthly_report(self, customer_id: str, month: str = None) -> SLAReport:
        """
        Aylık SLA raporu oluştur
        month format: "2026-03" (YYYY-MM)
        """
        if not month:
            now = datetime.now()
            month = f"{now.year}-{now.month:02d}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Metrics'i getir
        start_date = f"{month}-01"
        next_month = (datetime.strptime(f"{month}-01", "%Y-%m-%d") + timedelta(days=32)).replace(day=1)
        end_date = next_month.strftime("%Y-%m-%d")
        
        # Request metrics
        cursor.execute('''
            SELECT response_time_ms, status_code FROM request_metrics 
            WHERE customer_id = ? AND timestamp BETWEEN ? AND ?
        ''', (customer_id, start_date, end_date))
        
        metrics = cursor.fetchall()
        
        if not metrics:
            conn.close()
            return None
        
        response_times = [m[0] for m in metrics]
        status_codes = [m[1] for m in metrics]
        
        # Calculate percentiles
        response_times.sort()
        p95 = response_times[int(len(response_times) * 0.95)]
        p99 = response_times[int(len(response_times) * 0.99)]
        
        # Error rate
        error_count = sum(1 for code in status_codes if code >= 400)
        error_rate = error_count / len(status_codes) if status_codes else 0
        
        # Uptime (non-5xx errors)
        uptime_count = sum(1 for code in status_codes if code < 500)
        uptime_percentage = (uptime_count / len(status_codes) * 100) if status_codes else 100
        
        # Violations
        cursor.execute('''
            SELECT COUNT(*) FROM sla_violations 
            WHERE customer_id = ? AND violation_date BETWEEN ? AND ? AND resolved = 0
        ''', (customer_id, start_date, end_date))
        
        violations = cursor.fetchone()[0] or 0
        
        # Get tier
        cursor.execute('SELECT tier FROM customer_subscriptions WHERE customer_id = ?', (customer_id,))
        tier_result = cursor.fetchone()
        tier = tier_result[0] if tier_result else 'STARTER'
        
        conn.close()
        
        # Check SLA compliance
        sla = SLA_TIERS[tier]
        sla_met = (p95 <= sla['response_time_ms'] and 
                  uptime_percentage >= sla['availability'] * 100 and
                  violations == 0)
        
        # Credit if not met
        credit_percentage = 0
        if not sla_met:
            if violations > 0:
                credit_percentage = min(violations * 5, 100)  # 5% per violation, max 100%
            elif p95 > sla['response_time_ms']:
                credit_percentage = 10
            elif uptime_percentage < sla['availability'] * 100:
                credit_percentage = 20
        
        report = SLAReport(
            customer_id=customer_id,
            month=month,
            tier=tier,
            uptime_percentage=uptime_percentage,
            p95_response_time_ms=p95,
            p99_response_time_ms=p99,
            error_rate=error_rate,
            total_requests=len(metrics),
            total_violations=violations,
            sla_met=sla_met,
            credit_percentage=credit_percentage
        )
        
        # Database'e kaydet
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        report_id = f"{customer_id}_{month}"
        cursor.execute('''
            INSERT OR REPLACE INTO sla_reports
            (report_id, customer_id, month, tier, uptime_percentage, p95_response_time_ms,
             p99_response_time_ms, error_rate, total_requests, total_violations, 
             sla_met, credit_percentage, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id, customer_id, month, tier, report.uptime_percentage,
            report.p95_response_time_ms, report.p99_response_time_ms, report.error_rate,
            report.total_requests, report.total_violations, report.sla_met,
            report.credit_percentage, datetime.now(timezone.utc).isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return report
    
    def get_sla_dashboard(self, customer_id: str) -> Dict:
        """SLA dashboard verisi getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Latest report
        cursor.execute('''
            SELECT tier, uptime_percentage, p95_response_time_ms, error_rate, 
                   total_requests, total_violations, sla_met, credit_percentage
            FROM sla_reports 
            WHERE customer_id = ? 
            ORDER BY month DESC LIMIT 1
        ''', (customer_id,))
        
        latest = cursor.fetchone()
        
        if not latest:
            conn.close()
            return {'error': 'No data available'}
        
        tier, uptime, p95, error_rate, total_req, violations, sla_met, credit = latest
        
        # Recent violations
        cursor.execute('''
            SELECT metric_type, threshold, actual_value, severity, violation_date
            FROM sla_violations 
            WHERE customer_id = ? 
            ORDER BY violation_date DESC 
            LIMIT 5
        ''', (customer_id,))
        
        violations_list = cursor.fetchall()
        conn.close()
        
        dashboard = {
            'current_tier': tier,
            'current_month': {
                'uptime': f"{uptime:.2f}%",
                'p95_response_time_ms': f"{p95:.0f}ms",
                'error_rate': f"{error_rate * 100:.2f}%",
                'total_requests': total_req,
                'sla_compliance': "✅ PASSING" if sla_met else "❌ FAILING",
                'credit_percentage': f"{credit:.0f}%" if not sla_met else "0%"
            },
            'sla_targets': {
                'response_time_ms': SLA_TIERS[tier]['response_time_ms'],
                'availability': f"{SLA_TIERS[tier]['availability'] * 100:.1f}%",
                'requests_per_day': SLA_TIERS[tier]['requests_per_day'],
                'support_response_hours': SLA_TIERS[tier]['support_response_hours']
            },
            'recent_violations': [
                {
                    'type': v[0],
                    'threshold': v[1],
                    'actual': v[2],
                    'severity': v[3],
                    'date': v[4]
                } for v in violations_list
            ]
        }
        
        return dashboard


# ============================================================
# SUPPORT TICKET SYSTEM
# ============================================================

class SupportTicketSystem:
    """Müşteri desteği ticket sistemi"""
    
    def __init__(self, db_path: str = 'support_tickets.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Support ticket database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                assigned_to TEXT,
                resolution_notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_ticket(self, customer_id: str, subject: str, description: str, 
                     priority: str = 'normal') -> str:
        """Support ticket oluştur"""
        import uuid
        
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO support_tickets
            (ticket_id, customer_id, subject, description, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
        ''', (ticket_id, customer_id, subject, description, priority, now, now))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created support ticket {ticket_id} for customer {customer_id}")
        return ticket_id
    
    def get_tickets(self, customer_id: str, status: str = None) -> List[Dict]:
        """Müşteri ticket'larını getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT ticket_id, subject, priority, status, created_at, updated_at, assigned_to
                FROM support_tickets 
                WHERE customer_id = ? AND status = ?
                ORDER BY created_at DESC
            ''', (customer_id, status))
        else:
            cursor.execute('''
                SELECT ticket_id, subject, priority, status, created_at, updated_at, assigned_to
                FROM support_tickets 
                WHERE customer_id = ?
                ORDER BY created_at DESC
            ''', (customer_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'ticket_id': row[0],
                'subject': row[1],
                'priority': row[2],
                'status': row[3],
                'created_at': row[4],
                'updated_at': row[5],
                'assigned_to': row[6]
            } for row in results
        ]
    
    def resolve_ticket(self, ticket_id: str, resolution_notes: str):
        """Support ticket'ı çöz"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        cursor.execute('''
            UPDATE support_tickets 
            SET status = 'resolved', resolved_at = ?, resolution_notes = ?, updated_at = ?
            WHERE ticket_id = ?
        ''', (now, resolution_notes, now, ticket_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Resolved support ticket {ticket_id}")


if __name__ == '__main__':
    # Test
    monitor = SLAMonitor()
    
    # Register test customer
    monitor.register_customer('CUST-001', 'PRO', 'test@example.com', 'Test User')
    
    # Record test metrics
    for i in range(100):
        metric = RequestMetric(
            request_id=f"REQ-{i}",
            endpoint='/evaluate',
            method='POST',
            status_code=200,
            response_time_ms=250 + i * 2,
            timestamp=datetime.now(timezone.utc),
            customer_id='CUST-001'
        )
        monitor.record_request(metric)
    
    # Generate report
    report = monitor.generate_monthly_report('CUST-001')
    print(json.dumps(asdict(report), indent=2))
    
    # Get dashboard
    dashboard = monitor.get_sla_dashboard('CUST-001')
    print(json.dumps(dashboard, indent=2))
    
    # Test support system
    support = SupportTicketSystem()
    ticket_id = support.create_ticket('CUST-001', 'API Error', 'Getting 500 errors', 'high')
    print(f"Created ticket: {ticket_id}")
    
    tickets = support.get_tickets('CUST-001')
    print(f"Tickets: {tickets}")
