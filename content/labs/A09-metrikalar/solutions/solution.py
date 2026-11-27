import mlab
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"])
y = (df["{target}"] == "{positive}").astype(int)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state={seed}, stratify=y)
scaler = StandardScaler().fit(X_train)
X_train_s = scaler.transform(X_train)
X_test_s = scaler.transform(X_test)
model = LogisticRegression(max_iter=1000).fit(X_train_s, y_train)
pred = model.predict(X_test_s)
cm = confusion_matrix(y_test, pred)
tn, fp, fn, tp = (int(v) for v in cm.ravel())
precision = float(precision_score(y_test, pred))
recall = float(recall_score(y_test, pred))
f1 = float(f1_score(y_test, pred))
auc = float(roc_auc_score(y_test, model.predict_proba(X_test_s)[:, 1]))
