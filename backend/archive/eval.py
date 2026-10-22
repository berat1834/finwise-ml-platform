import joblib
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
from training_pipeline import load_data, build_feature_lists, split_dataset
from app.ml.model_constants import PRODUCTION_MODEL_PATH

def evaluate():
    print("Loading data...")
    df = load_data('credit_risk_dataset.csv')
    num_cols, cat_cols = build_feature_lists(df)
    X_train, X_test, y_train, y_test = split_dataset(df, test_size=0.2)
    
    print("Loading model...")
    model = joblib.load(PRODUCTION_MODEL_PATH)
    
    print("Predicting...")
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else model.predict(X_test)
    
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(f"AUC: {roc_auc_score(y_test, y_proba):.4f}")
    print("Classification Report:")
    print(classification_report(y_test, y_pred))

if __name__ == '__main__':
    evaluate()
