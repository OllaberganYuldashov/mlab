def test_ax(ns, params):
    from matplotlib.axes import Axes
    ax = ns.get("ax")
    assert isinstance(ax, Axes), "`ax` matplotlib o'qi bo'lishi kerak (fig, ax = plt.subplots())"
    assert len(ax.patches) > 0, "histogramma chizilmagan"
