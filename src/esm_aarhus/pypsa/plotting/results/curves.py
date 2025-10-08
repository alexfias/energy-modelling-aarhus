import matplotlib.pyplot as plt
import pandas as pd

def price_duration_curve(price: pd.Series, *, title="Price duration curve", ax=None):
    """
    Plot price duration curve (sorted descending).
    """
    set_defaults()
    sorted_vals = price.sort_values(ascending=False).reset_index(drop=True)
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    ax.plot(sorted_vals.values)
    ax.set_xlabel("Hours (sorted)")
    ax.set_ylabel("Price")
    ax.set_title(title)
    return fig, ax
