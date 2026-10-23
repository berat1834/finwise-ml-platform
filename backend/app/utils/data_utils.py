"""Shared data loading and preprocessing helpers for credit-risk training."""

import numpy as np
import pandas as pd

TARGET_COL = "loan_status"
LEAKAGE_COLS = ["loan_grade", "loan_int_rate"]

CATEGORICAL_COLS = [
    "person_home_ownership",
    "loan_intent",
    "cb_person_default_on_file",
    "age_group",
]

NUMERIC_COLS = [
    "person_age",
    "person_income",
    "person_emp_length",
    "loan_amnt",
    "loan_percent_income",
    "cb_person_cred_hist_length",
    "income_to_loan_ratio",
    "emp_stability",
]


def load_credit_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "loan_percent_income" not in df.columns and {"loan_amnt", "person_income"}.issubset(df.columns):
        with np.errstate(divide="ignore", invalid="ignore"):
            df["loan_percent_income"] = (df["loan_amnt"] / df["person_income"]).replace([np.inf, -np.inf], np.nan)
    return df


def remove_leakage_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols_to_drop = [col for col in LEAKAGE_COLS if col in df.columns]
    if not cols_to_drop:
        return df
    return df.drop(columns=cols_to_drop)


def build_feature_lists(df: pd.DataFrame):
    cat_cols = [c for c in CATEGORICAL_COLS if c in df.columns]
    num_cols = [c for c in NUMERIC_COLS if c in df.columns]
    return cat_cols, num_cols


def clean_outliers(df: pd.DataFrame) -> pd.DataFrame:
    mask = ~((df['person_age'] > 100) | (df['person_age'] < 18))
    mask = mask & ~(df['person_emp_length'] > 60)
    mask = mask & ~(df['person_income'] > 1_000_000)
    return pd.DataFrame(df.loc[mask])


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    bins = [0, 25, 35, 50, float('inf')]
    labels = ['young', 'young_adult', 'middle_aged', 'senior']
    df['age_group'] = pd.cut(df['person_age'], bins=bins, labels=labels)
    # Ensure categorical is standard object/string for simpler processing if needed
    df['age_group'] = df['age_group'].astype(str)
    
    df['income_to_loan_ratio'] = df['person_income'] / (df['loan_amnt'] + 1)
    df['emp_stability'] = df['person_emp_length'] / (df['person_age'] - 18 + 1)
    return df
