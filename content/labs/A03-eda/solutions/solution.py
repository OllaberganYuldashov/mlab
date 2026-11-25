import matplotlib.pyplot as plt
import mlab

df = mlab.load("{dataset}")
group_means = df.groupby("{category}")["{column}"].mean()
corr = df.select_dtypes("number").corr()["{column}"].drop("{column}").abs()
best_pair = corr.idxmax()
fig, ax = plt.subplots()
ax.hist(df["{column}"], bins={bins})
ax.set_xlabel("{column}")
ax.set_ylabel("soni")
