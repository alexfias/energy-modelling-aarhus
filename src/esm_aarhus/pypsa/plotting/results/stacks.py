import matplotlib.pyplot as plt
import pandas as pd

def generation_stack(df: pd.DataFrame, *, title="Generation stack", ax=None):
    """
    Plot a stacked area of generation by technology.

    df: DataFrame indexed by time, columns are technologies (MW).
    """
    set_defaults()
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    df.plot.area(ax=ax)
    ax.set_ylabel("MW")
    ax.set_title(title)
    return fig, ax
