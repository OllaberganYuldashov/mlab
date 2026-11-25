import mlab

df = mlab.load("{dataset}")
n_rows = len(df)
mean_value = float(df["{column}"].mean())
median_value = float(df["{column}"].median())
clean = df[(df["{column}"] >= {low}) & (df["{column}"] <= {high})].reset_index(drop=True)
removed = len(df) - len(clean)
