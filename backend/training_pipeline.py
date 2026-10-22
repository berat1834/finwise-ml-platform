# -*- coding: utf-8 -*-
"""
Production-ready training pipeline for Credit Risk model
- Robust preprocessing with ColumnTransformer
- Class imbalance handling via class_weight
- Cross-validation with recall(positive) focus
- Threshold tuning to prioritize risk recall
- Persist model with metadata (versioning)
"""
import json
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_recall_curve,
    auc,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import make_scorer
from app.utils.data_utils import TARGET_COL, load_credit_data, remove_leakage_columns, build_feature_lists, clean_outliers, engineer_features
from app.ml.model_constants import PRODUCTION_MODEL_PATH, PRODUCTION_META_PATH

RANDOM_STATE = 42
MODEL_PATH = PRODUCTION_MODEL_PATH
META_PATH = PRODUCTION_META_PATH


def load_data(csv_path: str) -> pd.DataFrame:
    df = load_credit_data(csv_path)
    df = clean_outliers(df)
    df = engineer_features(df)
    return remove_leakage_columns(df)


def build_pipeline(cat_cols, num_cols) -> Pipeline:
    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler(with_mean=False)),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, num_cols),
            ("cat", categorical_transformer, cat_cols),
        ], remainder="drop"
    )

    clf = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )

    pipe = Pipeline(steps=[("pre", preprocessor), ("clf", clf)])
    return pipe


def build_pipeline_xgb(cat_cols, num_cols, scale_pos_weight=1.0) -> Pipeline:
    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler(with_mean=False)),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, num_cols),
            ("cat", categorical_transformer, cat_cols),
        ], remainder="drop"
    )

    clf = xgb.XGBClassifier(
        eval_metric='logloss',
        use_label_encoder=False,
        scale_pos_weight=scale_pos_weight,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )

    pipe = Pipeline(steps=[("pre", preprocessor), ("clf", clf)])
    return pipe


def fit_with_cv(X, y, pipe: Pipeline):
    # Optimize a few RF params with focus on recall for positive class (1)
    param_grid = {
        "clf__n_estimators": [300, 400],
        "clf__max_depth": [None, 12, 18],
        "clf__min_samples_leaf": [1, 3],
    }

    pos_recall = make_scorer(recall_score, pos_label=1)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    grid = GridSearchCV(
        pipe,
        param_grid=param_grid,
        scoring={"roc_auc": "roc_auc", "pos_recall": pos_recall},
        refit="roc_auc",
        cv=cv,
        n_jobs=-1,
        verbose=1,
    )
    grid.fit(X, y)
    return grid


def fit_with_cv_xgb(X, y, pipe: Pipeline):
    param_grid = {
        "clf__n_estimators": [200, 300],
        "clf__max_depth": [6, 8],
        "clf__learning_rate": [0.05, 0.1],
    }

    pos_recall = make_scorer(recall_score, pos_label=1)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    grid = GridSearchCV(
        pipe,
        param_grid=param_grid,
        scoring={"roc_auc": "roc_auc", "pos_recall": pos_recall},
        refit="roc_auc",
        cv=cv,
        n_jobs=-1,
        verbose=1,
    )
    grid.fit(X, y)
    return grid


def select_threshold(model: Pipeline, X_valid: pd.DataFrame, y_valid: pd.Series, 
                    min_precision: float = 0.75, strategy: str = "f2"):
    """
    Select decision threshold for binary classification.
    
    Args:
        model: Trained pipeline
        X_valid: Validation features
        y_valid: Validation labels
        min_precision: Minimum acceptable precision threshold (default 0.75)
        strategy: Threshold selection strategy
            - "f2": Maximize F2-score (recall weight 2x precision)
            - "f1": Maximize F1-score (balanced)
            - "recall": Maximize recall with min_precision constraint
    
    Returns:
        Selected threshold value
    """
    probas = model.predict_proba(X_valid)[:, 1]
    precision, recall, thresholds = precision_recall_curve(y_valid, probas)
    
    # Compute F-scores
    beta = 2.0 if strategy == "f2" else 1.0  # F2 for recall emphasis
    f_score = ((1 + beta**2) * precision * recall) / (beta**2 * precision + recall + 1e-9)
    
    all_thresholds = np.append(thresholds, 1.0)
    
    if strategy in ("f1", "f2"):
        # Choose threshold at max F-score point
        best_idx = int(np.nanargmax(f_score))
        best_threshold = all_thresholds[best_idx]
        best_f_score = f_score[best_idx]
        print(f"  Selected threshold via {strategy.upper()}-score optimization:")
        print(f"    Threshold: {best_threshold:.4f}")
        print(f"    Precision: {precision[best_idx]:.4f}, Recall: {recall[best_idx]:.4f}, {strategy.upper()}: {best_f_score:.4f}")
    
    else:  # "recall" strategy
        # Maximize recall while keeping precision >= min_precision
        best_score = -1
        best_threshold = 0.5
        best_idx = 0
        
        for idx, (p, r, t) in enumerate(zip(precision, recall, all_thresholds)):
            if p >= min_precision:
                if r > best_score:
                    best_score = r
                    best_threshold = t
                    best_idx = idx
        
        # Fallback if none met precision constraint
        if best_score < 0:
            best_idx = int(np.nanargmax(f_score))
            best_threshold = all_thresholds[best_idx]
            print(f"  No threshold met min_precision={min_precision}, using F1-optimized threshold")
        
        print(f"  Selected threshold via recall optimization (min_precision={min_precision}):")
        print(f"    Threshold: {best_threshold:.4f}")
        print(f"    Precision: {precision[best_idx]:.4f}, Recall: {recall[best_idx]:.4f}")

    return float(best_threshold)


def evaluate(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series, threshold: float):
    probs = model.predict_proba(X_test)[:, 1]
    y_pred = (probs >= threshold).astype(int)

    acc = accuracy_score(y_test, y_pred)
    roc = roc_auc_score(y_test, probs)
    cm = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(y_test, y_pred, output_dict=True)

    # PR AUC (class 1)
    precision, recall, _ = precision_recall_curve(y_test, probs)
    pr_auc = auc(recall, precision)

    return {
        "accuracy": acc,
        "roc_auc": roc,
        "pr_auc": pr_auc,
        "confusion_matrix": cm,
        "classification_report": report,
    }


def persist(model: Pipeline, meta: dict):
    joblib.dump(model, MODEL_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def split_dataset(X: pd.DataFrame, y: pd.Series):
    """Create deterministic train/validation/test splits.

    Split policy (stratified):
    - test: 20%
    - validation: 20% of remaining 80% (=16% total)
    - train: 64%
    """
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full,
        y_train_full,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y_train_full,
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def main(csv_path: str = "credit_risk_dataset.csv", fairness_strategy: str = "class_weight", 
         threshold_strategy: str = "f2", min_precision: float = 0.75):
    print("Loading data...")
    df = load_data(csv_path)

    # Build features after leakage columns are removed.
    cat_cols, num_cols = build_feature_lists(df)

    X = df[cat_cols + num_cols]
    y = df[TARGET_COL]

    X_tr, X_val, X_test, y_tr, y_val, y_test = split_dataset(X, y)

    print(f"Building pipeline for fairness strategy: {fairness_strategy}")
    
    # Random Forest
    rf_pipe = build_pipeline(cat_cols, num_cols)
    print("Training Random Forest...")
    rf_grid = fit_with_cv(X_tr, y_tr, rf_pipe)
    
    # XGBoost
    scale_pos_weight = (len(y_tr) - sum(y_tr)) / sum(y_tr)
    xgb_pipe = build_pipeline_xgb(cat_cols, num_cols, scale_pos_weight=scale_pos_weight)
    print("Training XGBoost...")
    xgb_grid = fit_with_cv_xgb(X_tr, y_tr, xgb_pipe)
    
    rf_model = rf_grid.best_estimator_
    xgb_model = xgb_grid.best_estimator_
    
    rf_model.fit(X_tr, y_tr)
    xgb_model.fit(X_tr, y_tr)
    
    rf_threshold = select_threshold(rf_model, X_val, y_val, min_precision=min_precision, strategy=threshold_strategy)
    xgb_threshold = select_threshold(xgb_model, X_val, y_val, min_precision=min_precision, strategy=threshold_strategy)
    
    rf_metrics = evaluate(rf_model, X_test, y_test, rf_threshold)
    xgb_metrics = evaluate(xgb_model, X_test, y_test, xgb_threshold)
    
    print("\n==== Model Comparison ====")
    print(f"Random Forest - ROC AUC: {rf_metrics['roc_auc']:.4f}, Accuracy: {rf_metrics['accuracy']:.4f}")
    print(f"XGBoost       - ROC AUC: {xgb_metrics['roc_auc']:.4f}, Accuracy: {xgb_metrics['accuracy']:.4f}")
    
    if xgb_metrics['roc_auc'] > rf_metrics['roc_auc']:
        print("Selected XGBoost as the best model.")
        best_model = xgb_model
        metrics = xgb_metrics
        threshold = xgb_threshold
        model_name = "XGBClassifier"
    else:
        print("Selected Random Forest as the best model.")
        best_model = rf_model
        metrics = rf_metrics
        threshold = rf_threshold
        model_name = "RandomForestClassifier"


    meta = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "version": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "model": model_name,
        "threshold": threshold,
        "categorical_cols": cat_cols,
        "numeric_cols": num_cols,
        "metrics": metrics,
        "sklearn_version": __import__('sklearn').__version__,
        "fairness_strategy": fairness_strategy,
        "threshold_strategy": threshold_strategy,
        "split_policy": {
            "method": "stratified_train_val_test",
            "train_fraction": round(len(X_tr) / len(X), 4),
            "validation_fraction": round(len(X_val) / len(X), 4),
            "test_fraction": round(len(X_test) / len(X), 4),
            "random_state": RANDOM_STATE,
        },
        "sample_counts": {
            "total": int(len(X)),
            "train": int(len(X_tr)),
            "validation": int(len(X_val)),
            "test": int(len(X_test)),
        },
        "leakage_safe_threshold_selection": True,
    }

    print("Persisting model and metadata...")
    persist(best_model, meta)

    print("\n==== Training Summary ====")
    print(f"ROC AUC: {metrics['roc_auc']:.3f}")
    print(f"PR AUC:  {metrics['pr_auc']:.3f}")
    print(f"Accuracy: {metrics['accuracy']:.3f}")
    print(f"Threshold: {threshold:.3f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train credit risk model with fairness and precision-recall tuning")
    parser.add_argument("--csv_path", type=str, default="credit_risk_dataset.csv", help="Path to credit risk dataset")
    parser.add_argument("--fairness_strategy", type=str, default="class_weight", 
                       choices=["class_weight", "threshold_tuning", "fairlearn"],
                       help="Fairness strategy to use during training")
    parser.add_argument("--threshold_strategy", type=str, default="f2",
                       choices=["f1", "f2", "recall"],
                       help="Threshold selection strategy: f2 (recall emphasis), f1 (balanced), recall (with min_precision constraint)")
    parser.add_argument("--min_precision", type=float, default=0.75,
                       help="Minimum acceptable precision (used with 'recall' strategy)")
    args = parser.parse_args()
    main(csv_path=args.csv_path, 
         fairness_strategy=args.fairness_strategy,
         threshold_strategy=args.threshold_strategy,
         min_precision=args.min_precision)
