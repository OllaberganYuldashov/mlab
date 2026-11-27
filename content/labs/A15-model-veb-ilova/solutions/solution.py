import pickle

import mlab
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"])
y = df["{target}"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state={seed}, stratify=y)
model = make_pipeline(StandardScaler(), {estimator}).fit(X_train, y_train)
acc = float(model.score(X_test, y_test))


def predict_one(row):
    frame = pd.DataFrame([row], columns=X.columns)
    proba = model.predict_proba(frame)[0]
    best = proba.argmax()
    return str(model.classes_[best]), float(proba[best])


answer = predict_one(X.iloc[{sample}].to_dict())
blob = pickle.dumps(model)
restored = pickle.loads(blob)
same = bool((restored.predict(X_test) == model.predict(X_test)).all())
