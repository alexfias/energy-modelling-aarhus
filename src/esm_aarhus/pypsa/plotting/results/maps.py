import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.patches import Wedge, Circle

def _default_colors(keys):
    cmap = plt.get_cmap("tab20")
    return {k: cmap(i % 20) for i, k in enumerate(keys)}

def _draw_pie(ax, x, y, fracs, colors, radius):
    if radius <= 0 or np.isnan(radius) or len(fracs) == 0:
        return
    start = 0.0
    for frac, c in zip(fracs, colors):
        if frac <= 0:
            continue
        theta1 = start * 360
        theta2 = (start + frac) * 360
        ax.add_patch(Wedge((x, y), r=radius, theta1=theta1, theta2=theta2,
                           facecolor=c, edgecolor="white", linewidth=0.3, zorder=5))
        start += frac
    ax.add_patch(Circle((x, y), radius=radius, facecolor="none",
                        edgecolor="k", linewidth=0.4, zorder=6))


def plot_generators_on_map(
    n,
    mode="scatter",                   # "scatter" or "pies"
    carriers=None,                    # None -> all carriers present in n.generators
    value="capacity",                 # for pies: "capacity" (p_nom) or "energy" (sum of p over snapshots)
    size_reference=None,              # pies: the largest circle corresponds to this total (MW or MWh)
    annotate_sizes=(2e3, 10e3, 25e3), # pies: example totals for size legend
    carrier_colors=None,              # dict carrier->color; otherwise auto
    plot_lines=True,                  # draw transmission lines for context
    linewidth_lines=0.4,
    scatter_size=10,                  # marker size for scatter mode
    title=None
):
    # --- Coordinates
    if not {"x","y"}.issubset(n.buses.columns):
        raise ValueError("n.buses must have 'x' and 'y' columns (lon/lat degrees).")
    bus_xy = n.buses[["x","y"]].copy()

    # --- Carriers
    all_carriers = list(pd.unique(n.generators.carrier))
    if carriers is None:
        carriers = all_carriers
    carriers = [c for c in carriers if c in all_carriers]
    if len(carriers) == 0:
        raise ValueError("No generators for the requested carriers.")
    if carrier_colors is None:
        carrier_colors = _default_colors(carriers)

    # --- Figure & map
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(11, 10))
    ax = plt.axes(projection=proj)

    # Background features
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f7f7f7")
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#e6f0ff")
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.6)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4)
    ax.add_feature(cfeature.LAKES.with_scale("50m"), edgecolor="0.5", facecolor="none", linewidth=0.3, alpha=0.7)
    ax.gridlines(draw_labels=True, linewidth=0.2, color="gray", alpha=0.5)

    # Map extent from buses (+ small padding)
    xmin, xmax = bus_xy.x.min(), bus_xy.x.max()
    ymin, ymax = bus_xy.y.min(), bus_xy.y.max()
    dx, dy = xmax - xmin, ymax - ymin
    ax.set_extent([xmin - 0.03*dx, xmax + 0.03*dx, ymin - 0.03*dy, ymax + 0.03*dy], crs=proj)

    # --- Optional: thin network lines for context
    if plot_lines and len(getattr(n, "lines", pd.DataFrame())):
        # join line endpoints
        buses = n.buses[["x","y"]]
        for _, ln in n.lines.iterrows():
            if ln.bus0 in buses.index and ln.bus1 in buses.index:
                x0, y0 = buses.loc[ln.bus0, ["x","y"]]
                x1, y1 = buses.loc[ln.bus1, ["x","y"]]
                ax.plot([x0, x1], [y0, y1], transform=proj, color="lightgray",
                        linewidth=linewidth_lines, alpha=0.8, zorder=1)

    # --- SCATTER MODE: plot each generator as a point colored by carrier
    if mode == "scatter":
        gens = n.generators.copy()
        gens["x"] = gens.bus.map(bus_xy["x"])
        gens["y"] = gens.bus.map(bus_xy["y"])
        handles = []
        for c in carriers:
            sub = gens[gens.carrier == c]
            if sub.empty: 
                continue
            h = ax.scatter(sub["x"], sub["y"], s=scatter_size, transform=proj,
                           color=carrier_colors[c], label=c, alpha=0.9, zorder=3, edgecolors="k", linewidths=0.2)
            handles.append(h)
        if handles:
            ax.legend(title="Generator carrier", loc="lower left", frameon=True)

    # --- PIES MODE: per-bus generation/capacity mix
    elif mode == "pies":
        gens = n.generators[n.generators.carrier.isin(carriers)].copy()
        if value == "capacity":
            gen_value = gens["p_nom_opt"].fillna(0.0)  # MW
        elif value == "energy":
            P = n.generators_t.p[gens.index]
            weights = getattr(n.snapshot_weightings, "generators", None)
            if isinstance(weights, pd.Series) and len(weights) == len(P):
                gen_value = (P.mul(weights, axis=0)).sum()  # MWh
            else:
                gen_value = P.sum()  # MWh (unweighted)
            gen_value = gen_value.reindex(gens.index).fillna(0.0)
        else:
            raise ValueError("value must be 'capacity' or 'energy'.")

        gens["value"] = gen_value
        bus_carrier = gens.groupby(["bus","carrier"])["value"].sum().unstack(fill_value=0.0)
        for c in carriers:
            if c not in bus_carrier.columns:
                bus_carrier[c] = 0.0
        bus_carrier = bus_carrier[carriers]
        totals = bus_carrier.sum(axis=1)
        bus_carrier = bus_carrier.loc[totals > 0]
        totals = totals.loc[totals > 0]

        # circle scaling
        # largest circle radius ~ 2% of the larger map span by default
        map_span = max(dx, dy)
        max_r = 0.05 * map_span
        min_r = 0.005 * map_span
        ref = totals.max() if size_reference is None else float(size_reference)

        # draw pies
        colors = [carrier_colors[c] for c in carriers]
        for bus, row in bus_carrier.iterrows():
            x, y = bus_xy.loc[bus, ["x","y"]]
            total = row.sum()
            fracs = (row / total).values if total > 0 else []
            r = np.clip((total / ref) * max_r, a_min=min_r, a_max=max_r)
            _draw_pie(ax, float(x), float(y), fracs, colors, r)

        # legends
        handles = [plt.Line2D([0],[0], marker="o", color="w",
                              markerfacecolor=carrier_colors[c], markersize=10, label=c) for c in carriers]
        leg1 = ax.legend(handles=handles, title="Carrier", loc="upper left", frameon=True)
        ax.add_artist(leg1)

        if annotate_sizes:
            from matplotlib.legend_handler import HandlerPatch
            class HandlerCircle(HandlerPatch):
                def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
                    return [Circle((width/2, height/2), orig_handle.get_radius())]
            size_labels, size_handles = [], []
            for s in annotate_sizes:
                r = np.clip((s / ref) * max_r, a_min=min_r, a_max=max_r)
                size_handles.append(Circle((0,0), r, facecolor="none", edgecolor="k"))
                size_labels.append(f"{s/1e3:.0f} GW" if value=="capacity" else f"{s/1e3:.0f} GWh")
            leg2 = ax.legend(size_handles, size_labels, title="Circle = total", loc="lower left",
                             handler_map={Circle: HandlerCircle()})
            ax.add_artist(leg2)
    else:
        raise ValueError("mode must be 'scatter' or 'pies'.")

    # Title
    if title is None:
        if mode == "scatter":
            title = "Generators by carrier (points) with map background"
        else:
            unit = "MW" if value=="capacity" else "MWh"
            title = f"Per-bus generator mix ({value}, pies; size ∝ total {unit})"
    ax.set_title(title)
    plt.tight_layout()
    return fig, ax



def plot_storage_units_on_map(
    n,
    mode="pies",                       # "scatter" or "pies"
    carriers=None,                     # None -> all carriers present in n.storage_units
    value="energy_capacity",           # "energy_capacity" | "power_capacity" | "energy_dispatch"
    size_reference=None,               # pies: largest circle corresponds to this total (MWh or MW)
    annotate_sizes=(5e3, 20e3, 50e3),  # example totals for legend (MWh or MW)
    carrier_colors=None,
    plot_lines=True,
    linewidth_lines=0.4,
    scatter_size=12,
    title=None
):
    # --- Coordinates
    if not {"x","y"}.issubset(n.buses.columns):
        raise ValueError("n.buses must have 'x' and 'y' columns (lon/lat degrees).")
    bus_xy = n.buses[["x","y"]].copy()

    if not hasattr(n, "storage_units") or n.storage_units.empty:
        raise ValueError("Network has no storage_units.")

    # --- Carriers
    all_carriers = list(pd.unique(n.storage_units.carrier))
    if carriers is None:
        carriers = all_carriers
    carriers = [c for c in carriers if c in all_carriers]
    if len(carriers) == 0:
        raise ValueError("No storage_units for the requested carriers.")

    if carrier_colors is None:
        carrier_colors = _default_colors(carriers)

    # --- Figure & map
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(11, 10))
    ax = plt.axes(projection=proj)

    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f7f7f7")
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#e6f0ff")
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.6)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4)
    ax.add_feature(cfeature.LAKES.with_scale("50m"), edgecolor="0.5", facecolor="none",
                   linewidth=0.3, alpha=0.7)
    ax.gridlines(draw_labels=True, linewidth=0.2, color="gray", alpha=0.5)

    xmin, xmax = bus_xy.x.min(), bus_xy.x.max()
    ymin, ymax = bus_xy.y.min(), bus_xy.y.max()
    dx, dy = xmax - xmin, ymax - ymin
    ax.set_extent([xmin - 0.03*dx, xmax + 0.03*dx, ymin - 0.03*dy, ymax + 0.03*dy], crs=proj)

    # --- Optional lines
    if plot_lines and len(getattr(n, "lines", pd.DataFrame())):
        buses = n.buses[["x","y"]]
        for _, ln in n.lines.iterrows():
            if ln.bus0 in buses.index and ln.bus1 in buses.index:
                x0, y0 = buses.loc[ln.bus0, ["x","y"]]
                x1, y1 = buses.loc[ln.bus1, ["x","y"]]
                ax.plot([x0, x1], [y0, y1], transform=proj, color="lightgray",
                        linewidth=linewidth_lines, alpha=0.8, zorder=1)

    su = n.storage_units[n.storage_units.carrier.isin(carriers)].copy()
    su["x"] = su.bus.map(bus_xy["x"])
    su["y"] = su.bus.map(bus_xy["y"])

    # --- SCATTER MODE
    if mode == "scatter":
        handles = []
        for c in carriers:
            sub = su[su.carrier == c]
            if sub.empty:
                continue
            h = ax.scatter(sub["x"], sub["y"], s=scatter_size, transform=proj,
                           color=carrier_colors[c], label=c, alpha=0.9,
                           zorder=3, edgecolors="k", linewidths=0.2)
            handles.append(h)
        if handles:
            ax.legend(title="Storage carrier", loc="lower left", frameon=True)

    # --- PIES MODE
    elif mode == "pies":
        if value == "energy_capacity":
            # MWh = MW * h
            su_value = su["p_nom_opt"].fillna(0.0) * su["max_hours"].fillna(0.0)
            unit = "MWh"
        elif value == "power_capacity":
            su_value = su["p_nom_opt"].fillna(0.0)
            unit = "MW"
        elif value == "energy_dispatch":
            # MWh (sign depends on PyPSA convention; absolute if you want magnitude)
            P = n.storage_units_t.p[su.index]
            weights = getattr(n.snapshot_weightings, "generators", None)
            if isinstance(weights, pd.Series) and len(weights) == len(P):
                su_value = (P.mul(weights, axis=0)).sum()
            else:
                su_value = P.sum()
            su_value = su_value.reindex(su.index).fillna(0.0)
            unit = "MWh"
        else:
            raise ValueError("value must be 'energy_capacity', 'power_capacity', or 'energy_dispatch'.")

        su["value"] = su_value

        bus_carrier = su.groupby(["bus","carrier"])["value"].sum().unstack(fill_value=0.0)
        for c in carriers:
            if c not in bus_carrier.columns:
                bus_carrier[c] = 0.0
        bus_carrier = bus_carrier[carriers]

        totals = bus_carrier.sum(axis=1)
        bus_carrier = bus_carrier.loc[totals > 0]
        totals = totals.loc[totals > 0]

        map_span = max(dx, dy)
        max_r = 0.1 * map_span
        min_r = 0.003 * map_span
        ref = totals.max() if size_reference is None else float(size_reference)

        colors = [carrier_colors[c] for c in carriers]
        for bus, row in bus_carrier.iterrows():
            x, y = bus_xy.loc[bus, ["x","y"]]
            total = row.sum()
            fracs = (row / total).values if total > 0 else []
            r = np.clip((total / ref) * max_r, a_min=min_r, a_max=max_r)
            _draw_pie(ax, float(x), float(y), fracs, colors, r)

        handles = [plt.Line2D([0],[0], marker="o", color="w",
                              markerfacecolor=carrier_colors[c], markersize=10, label=c)
                   for c in carriers]
        leg1 = ax.legend(handles=handles, title="Carrier", loc="upper left", frameon=True)
        ax.add_artist(leg1)

        if annotate_sizes:
            from matplotlib.legend_handler import HandlerPatch
            class HandlerCircle(HandlerPatch):
                def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
                    return [Circle((width/2, height/2), orig_handle.get_radius())]

            size_labels, size_handles = [], []
            for s in annotate_sizes:
                r = np.clip((s / ref) * max_r, a_min=min_r, a_max=max_r)
                size_handles.append(Circle((0,0), r, facecolor="none", edgecolor="k"))
                size_labels.append(f"{s/1e3:.0f} GWh" if unit == "MWh" else f"{s/1e3:.0f} GW")
            leg2 = ax.legend(size_handles, size_labels, title=f"Circle = total {unit}",
                             loc="lower left", handler_map={Circle: HandlerCircle()})
            ax.add_artist(leg2)

    else:
        raise ValueError("mode must be 'scatter' or 'pies'.")

    if title is None:
        if mode == "scatter":
            title = "Storage units by carrier (points)"
        else:
            title = f"Per-bus storage mix ({value}, pies; size ∝ total)"
    ax.set_title(title)
    plt.tight_layout()
    return fig, ax



