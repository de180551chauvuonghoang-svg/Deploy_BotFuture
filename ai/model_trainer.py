import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
import os
import joblib

def load_and_preprocess_amnesia(filepath):
    """
    Loads data and applies the 'Amnesia' (Out-of-Sample) filter.
    Only returns data older than 360 days for training.
    """
    if not os.path.exists(filepath):
        print(f"❌ Error: {filepath} not found.")
        return None, None
        
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} samples total.")
    
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # AMNESIA LOGIC: Exclude last 360 days
    latest_ts = df['timestamp'].max()
    cutoff_ts = latest_ts - pd.Timedelta(days=360)
    
    print(f"Applying Amnesia Filter: Training on data BEFORE {cutoff_ts}")
    train_df = df[df['timestamp'] < cutoff_ts]
    
    if len(train_df) == 0:
        print("❌ Error: No training data left after Amnesia filter. Check data collection duration.")
        return None, None
        
    print(f"Training samples after filter: {len(train_df)}")
    
    X = train_df.drop(['outcome', 'timestamp', 'symbol'], axis=1)
    y = train_df['outcome']
    
    return X, y

def train_signal_filter():
    data_path = "data/ai_training_data.csv"
    X, y = load_and_preprocess_amnesia(data_path)
    
    if X is None:
        return

    # Split into train/validation (within the training window)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print(f"Split sizes: Train={len(X_train)}, Val={len(X_test)}")
    print(f"Win Rate in Training Set: {y_train.mean():.2%}")

    # Hyperparameter Optimization
    def objective(space):
        clf = xgb.XGBClassifier(
            n_estimators=int(space['n_estimators']),
            max_depth=int(space['max_depth']),
            learning_rate=space['learning_rate'],
            subsample=space['subsample'],
            colsample_bytree=space['colsample_bytree'],
            objective='binary:logistic',
            random_state=42,
            eval_metric='logloss'
        )
        
        clf.fit(X_train, y_train)
        pred = clf.predict(X_test)
        acc = accuracy_score(y_test, pred)
        return {'loss': -acc, 'status': STATUS_OK}

    space = {
        'n_estimators': hp.quniform('n_estimators', 50, 500, 1),
        'max_depth': hp.quniform('max_depth', 3, 10, 1),
        'learning_rate': hp.loguniform('learning_rate', np.log(0.01), np.log(0.2)),
        'subsample': hp.uniform('subsample', 0.5, 1),
        'colsample_bytree': hp.uniform('colsample_bytree', 0.5, 1)
    }

    print("--- Starting Hyperparameter Optimization (50 evals) ---")
    trials = Trials()
    best_hyperparams = fmin(fn=objective, space=space, algo=tpe.suggest, max_evals=50, trials=trials)
    
    print(f"Best Hyperparameters: {best_hyperparams}")

    # Final Training with best hyperparams
    best_clf = xgb.XGBClassifier(
        n_estimators=int(best_hyperparams['n_estimators']),
        max_depth=int(best_hyperparams['max_depth']),
        learning_rate=best_hyperparams['learning_rate'],
        subsample=best_hyperparams['subsample'],
        colsample_bytree=best_hyperparams['colsample_bytree'],
        objective='binary:logistic',
        eval_metric='logloss'
    )
    
    best_clf.fit(X_train, y_train)
    
    # Evaluation on validation set
    y_pred = best_clf.predict(X_test)
    print("\n--- Model Performance (Validation Set) ---")
    print(classification_report(y_test, y_pred))
    
    # Save Model
    os.makedirs("ai/models", exist_ok=True)
    model_file = "ai/models/signal_filter_v1.json"
    best_clf.save_model(model_file)
    
    # Save Feature List
    joblib.dump(X.columns.tolist(), "ai/models/features_list.joblib")
    
    print(f"✅ Amnesia Model saved to {model_file}")

if __name__ == "__main__":
    train_signal_filter()
