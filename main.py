#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Credit Risk Analysis System - Production Version with Security
Flask REST API with JWT Authentication, Rate Limiting, Database Integration
"""
from flask import Flask, request, jsonify, send_file, Response
import json
from flask_restx import Api, Resource, fields, Namespace as NS
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError, JWTExtendedException
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import time
import bleach
import hashlib
import threading
import uuid

# Import database models
from models import (
    db, User, Application, ManualOverride, AuditLog, ModelPerformance,
    DataRetentionLog, GDPRRequest, ComplianceReport, ModelValidation, CustomerAppeal
)

# Import compliance utilities
from compliance import (
    ComplianceManager, BaselCalculator, BDDKClassifier, 
    ModelRiskManager, AppealManager
)

# Import original model class
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from training_pipeline import build_pipeline
import joblib
import json
from pathlib import Path
from pydantic import BaseModel, field_validator, ValidationError
import pandas as pd
import numpy as np
# SHAP is optional. Avoid startup failure on environments without numba/coverage compat.
try:
    import shap  # type: ignore
    SHAP_AVAILABLE = True
except Exception:
    SHAP_AVAILABLE = False
    print("WARN: SHAP not available. Explanations disabled in secure API.")

# Load environment variables
load_dotenv()

# Initialize Flask app
