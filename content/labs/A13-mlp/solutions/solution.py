import mlab
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"])
y = df["{target}"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state={seed}, stratify=y)
model = make_pipeline(
    StandardScaler(), MLPClassifier(hidden_layer_sizes=({hidden},), alpha={alpha}, max_iter=500, random_state={seed})
).fit(X_train, y_train)
acc = float(model.score(X_test, y_test))
mlp = model[-1]
n_params = int(sum(w.size for w in mlp.coefs_) + sum(b.size for b in mlp.intercepts_))
deep = make_pipeline(
    StandardScaler(),
    MLPClassifier(hidden_layer_sizes=({hidden}, {hidden}), alpha={alpha}, max_iter=500, random_state={seed}),
).fit(X_train, y_train)
acc_deep = float(deep.score(X_test, y_test))
better = "deep" if acc_deep > acc else "shallow"
