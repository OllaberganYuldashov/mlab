import mlab
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

df = mlab.load("{dataset}")
X = df[{features}]
y = df["{target}"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state={seed})
model = LinearRegression().fit(X_train, y_train)
pred = model.predict(X_test)
r2 = r2_score(y_test, pred)
mse = mean_squared_error(y_test, pred)
