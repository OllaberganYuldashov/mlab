import mlab
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"])
y = df["{target}"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state={seed}, stratify=y)
scaler = StandardScaler().fit(X_train)
X_train_s = scaler.transform(X_train)
X_test_s = scaler.transform(X_test)

model = LogisticRegression(C={c}, max_iter=1000).fit(X_train_s, y_train)
acc = model.score(X_test_s, y_test)
proba = model.predict_proba(X_test_s)
confidence = float(proba.max(axis=1).mean())
least_sure = int(proba.max(axis=1).argmin())
least_sure_class = model.predict(X_test_s)[least_sure]
