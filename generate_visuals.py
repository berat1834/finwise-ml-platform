import json
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_curve

# Define constants
RANDOM_STATE = 42
MODEL_PATH = "production_model.joblib"
META_PATH = "production_model_meta.json"
DATA_PATH = "credit_risk_dataset.csv"
TARGET_COL = 'loan_status'

def plot_precision_recall_curve(model, meta, X_test, y_test):
    """Generates and saves the Precision-Recall curve."""
    print("Generating Precision-Recall curve...")
    
    probs = model.predict_proba(X_test)[:, 1]
    precision, recall, thresholds = precision_recall_curve(y_test, probs)
    
    optimal_threshold = meta['threshold']
    idx = np.argmin(np.abs(thresholds - optimal_threshold))
    
    plt.figure(figsize=(10, 7))
    plt.plot(recall, precision, label='Precision-Recall EÄŸrisi', color='navy')
    plt.scatter(recall[idx], precision[idx], marker='o', color='red', label=f'Optimal EÅŸik (~{optimal_threshold:.3f})', s=100, zorder=5)
    
    plt.title('Precision-Recall EÄŸrisi', fontsize=16)
    plt.xlabel('Geri Ã‡aÄŸÄ±rma (Recall)', fontsize=12)
    plt.ylabel('Kesinlik (Precision)', fontsize=12)
    plt.grid(True)
    plt.legend()
    
    output_path = "precision_recall_curve.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved Precision-Recall curve to {output_path}")
    plt.close()

def plot_shap_summary(model, X_test):
    """Generates and saves the SHAP summary plot."""
    print("Generating SHAP summary plot...")

    classifier = model.named_steps['clf']
    preprocessor = model.named_steps['pre']
    
    try:
        feature_names = preprocessor.get_feature_names_out()
    except Exception as e:
        print(f"Could not get feature names from preprocessor: {e}")
        print("SHAP plot will not be generated.")
        return

    X_test_sample = X_test.sample(n=500, random_state=RANDOM_STATE)
    X_test_transformed = preprocessor.transform(X_test_sample)

    explainer = shap.TreeExplainer(classifier)
    shap_values = explainer.shap_values(X_test_transformed)

    # THE FIX: Removed the unnecessary `X_test_transformed` argument for the bar plot.
    shap.summary_plot(shap_values[1], feature_names=feature_names, plot_type="bar", show=False)
    
    plt.title("SHAP Ortalama Ã–zellik Ã–nem Dereceleri", fontsize=14)
    plt.tight_layout()

    output_path = "shap_summary_plot.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved SHAP summary plot to {output_path}")
    plt.close()


def main():
    """Main function to load artifacts and generate all visuals."""
    print("Loading model and metadata...")
    try:
        model = joblib.load(MODEL_PATH)
        with open(META_PATH, 'r') as f:
            meta = json.load(f)
    except FileNotFoundError:
        print(f"Error: Make sure '{MODEL_PATH}' and '{META_PATH}' exist. Run training_pipeline.py first.")
        return

    print("Loading and splitting data for consistency...")
    df = pd.read_csv(DATA_PATH)
    if 'loan_percent_income' not in df.columns and {'loan_amnt', 'person_income'}.issubset(df.columns):
         with np.errstate(divide='ignore', invalid='ignore'):
            df['loan_percent_income'] = (df['loan_amnt'] / df['person_income']).replace([np.inf, -np.inf], np.nan)
    
    X = df.drop(columns=[TARGET_COL], errors='ignore')
    y = df[TARGET_COL]
    
    X = X[meta['categorical_cols'] + meta['numeric_cols']]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    
    plot_precision_recall_curve(model, meta, X_test, y_test)
    plot_shap_summary(model, X_test)
    
    print("\nVisuals generated successfully.")

if __name__ == "__main__":
    main()
