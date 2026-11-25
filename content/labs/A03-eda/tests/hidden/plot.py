def test_bins_va_nomlar(ns, params):
    ax = ns["ax"]
    assert len(ax.patches) == params["bins"]
    assert ax.get_xlabel().strip() and ax.get_ylabel().strip()
