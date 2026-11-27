import mlab
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"])
y = df["{target}"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state={seed}, stratify=y)
scaler = StandardScaler().fit(X_train)
X_train_s = scaler.transform(X_train)
X_test_s = scaler.transform(X_test)

svm_linear = SVC(kernel="linear", C={c}).fit(X_train_s, y_train)
linear_acc = svm_linear.score(X_test_s, y_test)
svm_rbf = SVC(kernel="rbf", C={c}, gamma="scale").fit(X_train_s, y_train)
rbf_acc = svm_rbf.score(X_test_s, y_test)
n_support = int(svm_rbf.n_support_.sum())
best_kernel = "linear" if linear_acc >= rbf_acc else "rbf"
