import mlab
import numpy as np
from scipy.signal import correlate2d
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = mlab.load("digits")
images = df.drop(columns=["digit"]).to_numpy().reshape(-1, 8, 8)
y = df["digit"]
K = np.array({kernel})
fmap = np.maximum(correlate2d(images[{image}], K, mode="valid"), 0)
pooled = fmap.reshape(3, 2, 3, 2).max(axis=(1, 3))


def features(img):
    m = np.maximum(correlate2d(img, K, mode="valid"), 0)
    return m.reshape(3, 2, 3, 2).max(axis=(1, 3)).ravel()


F = np.array([features(img) for img in images])
F_train, F_test, y_train, y_test = train_test_split(F, y, test_size={test_size}, random_state={seed}, stratify=y)
conv_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(F_train, y_train)
acc_conv = float(conv_model.score(F_test, y_test))
P = df.drop(columns=["digit"])
P_train, P_test, _, _ = train_test_split(P, y, test_size={test_size}, random_state={seed}, stratify=y)
raw_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(P_train, y_train)
acc_raw = float(raw_model.score(P_test, y_test))
