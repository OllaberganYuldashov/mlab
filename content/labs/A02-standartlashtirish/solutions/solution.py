import mlab
import pandas as pd

df = mlab.load("{dataset}")
x = df["{column}"]
z = (x - x.mean()) / x.std(ddof=0)
scaled = (x - x.min()) / (x.max() - x.min())
encoded = pd.get_dummies(df["{category}"], prefix="{prefix}")
