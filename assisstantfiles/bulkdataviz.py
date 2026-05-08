import base64
import io
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import gaussian_kde

from assisstantfiles.plotting_utils import create_tas_figure, get_mg_number_animation


# ── Column sets ───────────────────────────────────────────────────────────────

REQUIRED_COLS   = {"SAMPLE", "PHASE"}
TAS_COLS        = {"SiO2", "Na2O", "K2O"}
HALOGEN_COLS    = {"Cl", "F", "MgO", "FeO"}
OPTIONAL_GEOCHM = [
    "SiO2", "TiO2", "Al2O3", "FeO", "MgO", "CaO", "Na2O", "K2O",
    "Cl", "F", "Cl CDL99", "F CDL99",
]

# Columns to exclude from the element dropdowns (non-geochemical / metadata)
EXCLUDE_FROM_ELEMENTS = {
    "SAMPLE", "PHASE", "pair_id", "NOTE", "FORMULA", "BASIS", "MINERAL",
    "END-MEMBER1", "END-MEMBER2", "END-MEMBER3", "END-MEMBER4",
    "DATETIME", "BEAMCURR", "BEAMCURR2", "ABSCURR", "ABSCURR2",
    "X-POS", "Y-POS", "Z-POS", "TOTAL", "TOTAL-CATIONS", "TOTAL-ATOMS",
    "Z-BAR", "OXYGEN(Halogen Equiv.)", "OXYGEN(Halogen Corr.)",
}


# ── Excel reader ──────────────────────────────────────────────────────────────

def load_excel_to_dataframe(file_like):
    """
    Read the new EPMA Excel format.
    All sheets are concatenated; SAMPLE and PHASE must exist as columns.
    """
    xl     = pd.ExcelFile(file_like)
    frames = []

    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet)
            if not df.empty:
                frames.append(df)
        except Exception as exc:
            print(f"Warning: could not parse sheet '{sheet}': {exc}")

    if not frames:
        raise ValueError("No readable sheets found in the uploaded file.")

    combined = pd.concat(frames, ignore_index=True)

    # Normalise column names — Excel can produce int headers for unnamed columns
    combined.columns = combined.columns.astype(str).str.strip()

    missing = REQUIRED_COLS - set(combined.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}. "
            "The file must contain at least SAMPLE and PHASE columns."
        )

    combined = combined.dropna(subset=["PHASE"])
    if combined.empty:
        raise ValueError("No rows with a valid PHASE value found.")

    return combined


def compute_mg_number(df):
    if "MgO" in df.columns and "FeO" in df.columns:
        denom     = df["MgO"] + df["FeO"]
        df["Mg#"] = 100 * df["MgO"] / denom.where(denom > 0)
    return df


def get_element_options(df):
    """
    Return dropdown options for the element scatter axes.
    Includes numeric wt% / measurement columns; excludes metadata and
    formula / CDL / %ERR derived columns.
    """
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    opts = []
    for c in num_cols:
        if c in EXCLUDE_FROM_ELEMENTS:
            continue
        if any(tag in c for tag in ["CDL", "%ERR", "FORMULA", "ONTIM", "STD_"]):
            continue
        opts.append({"label": c, "value": c})
    return opts


# ── Element scatter (joint + marginals) ───────────────────────────────────────

def create_element_scatter(df, x_elem, y_elem):
    """
    Joint scatter with marginal histograms, styled after the matplotlib figure.

    - Filled black markers  : Y element above detection
    - Open white markers    : Y element below detection
    - Error bars            : from %ERR columns if present
    - CDL dashed line       : median Y CDL99 if column present
    - Right marginal        : stacked histogram (above/below) + KDE for Y
    - Top marginal          : simple histogram for X
    """
    if x_elem not in df.columns or y_elem not in df.columns:
        return go.Figure().add_annotation(
            text=f"Columns '{x_elem}' or '{y_elem}' not found in data.",
            showarrow=False, font=dict(size=14)
        )

    plot_df = df[[x_elem, y_elem]].dropna().copy()
    if plot_df.empty:
        return go.Figure().add_annotation(
            text="No valid data for selected elements.",
            showarrow=False, font=dict(size=14)
        )

    # CDL detection flag for Y element
    y_cdl_col = f"{y_elem} CDL99"
    x_cdl_col = f"{x_elem} CDL99"
    has_y_cdl = y_cdl_col in df.columns
    has_x_cdl = x_cdl_col in df.columns

    idx       = plot_df.index
    y_cdl_val = None

    if has_y_cdl:
        y_cdl_series = df.loc[idx, y_cdl_col].dropna()
        y_cdl_val    = float(y_cdl_series.median()) if not y_cdl_series.empty else None
        below_y      = df.loc[idx, y_elem] < df.loc[idx, y_cdl_col]
    else:
        below_y = pd.Series(False, index=idx)

    above_idx = idx[~below_y.reindex(idx, fill_value=False)]
    below_idx = idx[ below_y.reindex(idx, fill_value=False)]

    # Error arrays (absolute, from %ERR columns)
    y_err_col = f"{y_elem} %ERR "
    x_err_col = f"{x_elem} %ERR "

    def abs_err(element, err_col, subset_idx):
        if err_col in df.columns:
            return (df.loc[subset_idx, element] * df.loc[subset_idx, err_col] / 100).tolist()
        return None

    # ── Subplot layout: 2×2, top-left=top marginal, bottom-left=joint,
    #    bottom-right=right marginal, top-right empty ─────────────────────────
    fig = make_subplots(
        rows=2, cols=2,
        shared_xaxes=True,
        shared_yaxes=True,
        column_widths=[0.8, 0.2],
        row_heights=[0.2, 0.8],
        horizontal_spacing=0.02,
        vertical_spacing=0.02,
        specs=[
            [{"type": "histogram"}, {"type": "scatter"}],   # top row
            [{"type": "scatter"},   {"type": "histogram"}],  # bottom row
        ]
    )

    # ── Joint scatter — above detection (filled black) ────────────────────────
    if len(above_idx):
        x_above = df.loc[above_idx, x_elem].tolist()
        y_above = df.loc[above_idx, y_elem].tolist()
        y_err_above = abs_err(y_elem, y_err_col, above_idx)
        x_err_above = abs_err(x_elem, x_err_col, above_idx)

        fig.add_trace(go.Scatter(
            x=x_above, y=y_above,
            mode="markers",
            name=f"{y_elem} above detection",
            marker=dict(
                symbol="circle", size=7,
                color="black", line=dict(color="black", width=0.8)
            ),
            error_y=dict(type="data", array=y_err_above,
                         visible=y_err_above is not None,
                         color="rgba(0,0,0,0.35)", thickness=0.6, width=1.5),
            error_x=dict(type="data", array=x_err_above,
                         visible=x_err_above is not None,
                         color="rgba(0,0,0,0.35)", thickness=0.6, width=1.5),
            legendgroup="above",
        ), row=2, col=1)

    # ── Joint scatter — below detection (open white) ──────────────────────────
    if len(below_idx):
        x_below = df.loc[below_idx, x_elem].tolist()
        y_below = df.loc[below_idx, y_elem].tolist()

        fig.add_trace(go.Scatter(
            x=x_below, y=y_below,
            mode="markers",
            name=f"{y_elem} below detection",
            marker=dict(
                symbol="circle", size=7,
                color="white", line=dict(color="black", width=0.8)
            ),
            legendgroup="below",
        ), row=2, col=1)

    # ── CDL horizontal line on joint plot ─────────────────────────────────────
    if y_cdl_val is not None:
        x_all = df.loc[idx, x_elem].dropna()
        fig.add_shape(
            type="line",
            x0=float(x_all.min()), x1=float(x_all.max()),
            y0=y_cdl_val, y1=y_cdl_val,
            line=dict(color="black", width=1.8, dash="dash"),
            row=2, col=1
        )
        fig.add_annotation(
            x=float(x_all.max()),
            y=y_cdl_val,
            text=f"{y_elem} CDL<sub>99</sub>",
            showarrow=False,
            xanchor="right", yanchor="bottom",
            font=dict(size=12, color="black", family="serif"),
            row=2, col=1
        )

    # ── Top marginal: X element histogram ────────────────────────────────────
    x_all_vals = df.loc[idx, x_elem].dropna().tolist()
    fig.add_trace(go.Histogram(
        x=x_all_vals,
        nbinsx=40,
        marker=dict(color="black", line=dict(color="black", width=0.6)),
        opacity=0.75,
        name=f"{x_elem} distribution",
        showlegend=False,
    ), row=1, col=1)

    # ── Right marginal: Y stacked histogram (above/below) + KDE ──────────────
    y_all_vals = df.loc[idx, y_elem].dropna().values

    if len(above_idx):
        fig.add_trace(go.Histogram(
            y=df.loc[above_idx, y_elem].tolist(),
            nbinsy=40,
            marker=dict(color="black", line=dict(color="black", width=0.6)),
            opacity=0.85,
            name=f"{y_elem} above (hist)",
            showlegend=False,
        ), row=2, col=2)

    if len(below_idx):
        fig.add_trace(go.Histogram(
            y=df.loc[below_idx, y_elem].tolist(),
            nbinsy=40,
            marker=dict(color="white", line=dict(color="black", width=0.6)),
            opacity=1.0,
            name=f"{y_elem} below (hist)",
            showlegend=False,
        ), row=2, col=2)

    # KDE overlay on right marginal
    if len(y_all_vals) >= 5:
        try:
            kde       = gaussian_kde(y_all_vals, bw_method=0.25)
            y_range   = np.linspace(y_all_vals.min(), y_all_vals.max(), 300)
            kde_vals  = kde(y_range)
            # Scale to approximate histogram counts
            y_span    = y_all_vals.max() - y_all_vals.min()
            bin_width = y_span / 40
            kde_scaled = kde_vals * len(y_all_vals) * bin_width

            fig.add_trace(go.Scatter(
                x=kde_scaled, y=y_range,
                mode="lines",
                line=dict(color="black", width=2.2),
                name=f"{y_elem} KDE",
                showlegend=False,
            ), row=2, col=2)
        except Exception as exc:
            print(f"KDE failed: {exc}")

    # Mirror CDL line onto right marginal
    if y_cdl_val is not None:
        fig.add_shape(
            type="line",
            x0=0, x1=1, xref="paper",
            y0=y_cdl_val, y1=y_cdl_val,
            line=dict(color="black", width=1.8, dash="dash"),
            row=2, col=2
        )

    # ── Axes labels and layout ────────────────────────────────────────────────
    fig.update_layout(
        height=620,
        plot_bgcolor="white",
        paper_bgcolor="white",
        barmode="overlay",
        legend=dict(
            bgcolor="white", bordercolor="black", borderwidth=1,
            x=0.01, y=0.37, xanchor="left", yanchor="top",
            font=dict(size=12)
        ),
        margin=dict(t=20, r=10, b=10, l=10),
    )

    # Joint axes
    fig.update_xaxes(
        title_text=f"{x_elem} (wt%)", row=2, col=1,
        showgrid=True, gridcolor="rgba(128,128,128,0.4)",
        showline=True, linecolor="black", linewidth=2,
        mirror=False, ticks="outside", zeroline=False,
    )
    fig.update_yaxes(
        title_text=f"{y_elem} (wt%)", row=2, col=1,
        showgrid=True, gridcolor="rgba(128,128,128,0.4)",
        showline=True, linecolor="black", linewidth=2,
        mirror=False, ticks="outside", zeroline=False,
    )
    # Top marginal axes
    fig.update_xaxes(showticklabels=False, row=1, col=1,
                     showline=True, linecolor="black", linewidth=2)
    fig.update_yaxes(title_text="Count", row=1, col=1,
                     showline=True, linecolor="black", linewidth=2)
    # Right marginal axes
    fig.update_xaxes(title_text="Count", row=2, col=2,
                     showline=True, linecolor="black", linewidth=2)
    fig.update_yaxes(showticklabels=False, row=2, col=2,
                     showline=True, linecolor="black", linewidth=2)

    return fig


# ── Layout ────────────────────────────────────────────────────────────────────

def create_bulk_analysis_layout():
    return dbc.Container(fluid=True, children=[

        html.H2("Bulk Chemistry Analysis", className="my-4 text-center"),

        # Upload
        dbc.Row([
            dbc.Col([
                html.H4("📁 Data Upload", className="mb-3"),
                dbc.Card(dbc.CardBody([
                    dcc.Upload(
                        id="upload-bulk-chemistry-file",
                        children=html.Div([
                            "Drag & Drop or ",
                            html.A("Select EPMA Data File", className="text-primary")
                        ]),
                        style={
                            "width": "100%", "height": "80px", "lineHeight": "80px",
                            "borderWidth": "2px", "borderStyle": "dashed",
                            "borderRadius": "8px", "textAlign": "center",
                            "margin": "10px 0", "borderColor": "#007bff",
                            "backgroundColor": "#f8f9fa"
                        },
                        multiple=False
                    ),
                    html.Div(id="bulk-upload-status", className="mt-2"),

                    dbc.Collapse([
                        dbc.Alert([
                            html.H6("📋 File Requirements:", className="alert-heading"),
                            html.Ul([
                                html.Li("Excel (.xlsx/.xls); all sheets concatenated automatically"),
                                html.Li([html.Strong("Required: "), "SAMPLE, PHASE"]),
                                html.Li([html.Strong("TAS: "),
                                         "SiO2, Na2O, K2O — filtered to PHASE = 'BULK' automatically"]),
                                html.Li([html.Strong("Element scatter: "),
                                         "any numeric wt% column; CDL99 and %ERR columns used "
                                         "automatically if present"]),
                                html.Li([html.Strong("Halogen evolution: "), "Cl, F, MgO, FeO"]),
                            ], className="mb-0")
                        ], color="info")
                    ], id="bulk-file-requirements-collapse", is_open=False),

                    dbc.Button("Show/Hide File Requirements",
                               id="bulk-toggle-requirements",
                               color="outline-info", size="sm", className="mt-2")
                ]))
            ], width=12)
        ], className="mb-4"),

        # Stores
        dcc.Store(id="stored-bulk-chemistry-data"),
        dcc.Store(id="stored-bulk-element-options"),

        # Controls
        dbc.Row([
            dbc.Col([
                html.H4("⚙️ Analysis Controls", className="mb-3"),
                dbc.Card(dbc.CardBody([

                    # Row 1: analysis type + PHASE filter
                    dbc.Row([
                        dbc.Col([
                            html.Label("Analysis Type:", className="fw-bold"),
                            dcc.Dropdown(
                                id="bulk-analysis-type",
                                options=[
                                    {"label": "📊 TAS Diagram (BULK phase only)",       "value": "tas"},
                                    {"label": "🔬 Element Scatter + Marginals",          "value": "element_scatter"},
                                    {"label": "🌋 Halogen Evolution Analysis",           "value": "halogen_evolution"},
                                    {"label": "📈 All Analyses",                         "value": "all"},
                                ],
                                value="element_scatter",
                                clearable=False,
                                style={"color": "black"}
                            )
                        ], width=6),

                        dbc.Col([
                            html.Label("Filter by PHASE (element scatter / halogen only):",
                                       className="fw-bold"),
                            dcc.Dropdown(
                                id="bulk-phase-filter",
                                options=[], value=[],
                                multi=True,
                                placeholder="All phases (no filter)",
                                style={"color": "black"}
                            )
                        ], width=6),
                    ], className="mb-3"),

                    # Row 2: element scatter selectors (shown/hidden by JS-free callback)
                    dbc.Row([
                        dbc.Col([
                            html.Label("Y-Axis Element:", className="fw-bold"),
                            dcc.Dropdown(
                                id="bulk-y-element",
                                options=[], value=None,
                                placeholder="Select Y element...",
                                style={"color": "black"}
                            )
                        ], width=3),

                        dbc.Col([
                            html.Label("X-Axis Element:", className="fw-bold"),
                            dcc.Dropdown(
                                id="bulk-x-element",
                                options=[], value=None,
                                placeholder="Select X element...",
                                style={"color": "black"}
                            )
                        ], width=3),

                        dbc.Col([
                            html.Label("Filter by Mg# Range:", className="fw-bold"),
                            dcc.RangeSlider(
                                id="mg-number-filter",
                                min=0, max=100, step=1,
                                value=[0, 100],
                                marks={i: str(i) for i in range(0, 101, 20)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], width=3),

                        dbc.Col([
                            html.Label("Minimum SiO₂ (wt%):", className="fw-bold"),
                            dcc.Slider(
                                id="sio2-filter",
                                min=35, max=80, step=1,
                                value=35,
                                marks={i: str(i) for i in range(35, 81, 10)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], width=3),
                    ], className="mb-3"),

                    # Row 3: color scheme
                    dbc.Row([
                        dbc.Col([
                            html.Label("Color Scheme:", className="fw-bold"),
                            dcc.Dropdown(
                                id="color-scheme-bulk",
                                options=[
                                    {"label": "Viridis",  "value": "Viridis"},
                                    {"label": "Plasma",   "value": "Plasma"},
                                    {"label": "Inferno",  "value": "Inferno"},
                                    {"label": "Magma",    "value": "magma"},
                                    {"label": "Cividis",  "value": "cividis"},
                                ],
                                value="Viridis",
                                clearable=False,
                                style={"color": "black"}
                            )
                        ], width=3),
                    ]),
                ]))
            ], width=12)
        ], className="mb-4"),

        # Results
        dbc.Row([
            dbc.Col([
                html.H4("📊 Analysis Results", className="mb-3"),
                dcc.Loading(
                    id="bulk-analysis-loading",
                    children=html.Div(id="bulk-analysis-content"),
                    type="circle",
                    color="#007bff"
                )
            ], width=12)
        ], className="mb-4"),

        # Data Summary
        dbc.Row([
            dbc.Col([
                html.H4("📋 Data Summary", className="mb-3"),
                dbc.Card(dbc.CardBody(html.Div(id="bulk-data-summary")))
            ], width=12)
        ], className="mb-4"),

        # Raw Data Table
        dbc.Row([
            dbc.Col([
                html.H4("🔍 Raw Data View", className="mb-3"),
                html.Div(id="bulk-data-table")
            ], width=12)
        ])
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────

def create_bulk_analysis_callbacks(app):

    # Toggle file requirements
    @app.callback(
        Output("bulk-file-requirements-collapse", "is_open"),
        Input("bulk-toggle-requirements", "n_clicks"),
        State("bulk-file-requirements-collapse", "is_open"),
    )
    def toggle_requirements(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open

    # Upload — populate stores, element dropdowns, PHASE filter
    @app.callback(
        [
            Output("stored-bulk-chemistry-data",  "data"),
            Output("bulk-upload-status",          "children"),
            Output("bulk-phase-filter",           "options"),
            Output("bulk-phase-filter",           "value"),
            Output("bulk-x-element",              "options"),
            Output("bulk-x-element",              "value"),
            Output("bulk-y-element",              "options"),
            Output("bulk-y-element",              "value"),
        ],
        Input("upload-bulk-chemistry-file", "contents"),
        State("upload-bulk-chemistry-file", "filename"),
        prevent_initial_call=True,
    )
    def load_bulk_file(contents, filename):
        empty = [None, None, [], [], [], None, [], None]

        if not contents:
            return empty[0], html.Div("No file uploaded", className="text-muted"), \
                   *empty[2:]

        try:
            _, b64    = contents.split(",", 1)
            file_like = io.BytesIO(base64.b64decode(b64))

            if not filename or not filename.lower().endswith((".xls", ".xlsx")):
                raise ValueError("Please upload an Excel (.xlsx or .xls) file.")

            df = load_excel_to_dataframe(file_like)
            df = compute_mg_number(df)

            # PHASE options
            phases        = sorted(df["PHASE"].dropna().unique().tolist())
            phase_options = [{"label": p, "value": p} for p in phases]

            # Element options (numeric, non-metadata columns)
            elem_options  = get_element_options(df)
            elem_vals     = [o["value"] for o in elem_options]

            default_x = "F"  if "F"  in elem_vals else (elem_vals[0]  if len(elem_vals) > 0 else None)
            default_y = "Cl" if "Cl" in elem_vals else (elem_vals[1]  if len(elem_vals) > 1 else None)

            n_rows    = len(df)
            n_samples = df["SAMPLE"].nunique()
            phase_str = ", ".join(f"{p}: {(df['PHASE']==p).sum()}" for p in phases)

            status = dbc.Alert([
                html.H6("✅ Upload Successful!", className="alert-heading"),
                html.P([
                    f"Loaded {n_rows:,} rows from {n_samples} sample(s) — {phase_str}. ",
                    html.Em(
                        "TAS uses PHASE = 'BULK' only. "
                        "Element scatter and halogen plots use the PHASE filter above."
                    )
                ], className="mb-0")
            ], color="success")

            return (df.to_dict("records"), status,
                    phase_options, [],
                    elem_options, default_x,
                    elem_options, default_y)

        except Exception as exc:
            print(f"Error in load_bulk_file: {exc}")
            err = dbc.Alert([
                html.H6("❌ Processing Error:", className="alert-heading"),
                html.P(str(exc), className="mb-0"),
            ], color="danger")
            return None, err, [], [], [], None, [], None

    # Main plot callback
    @app.callback(
        Output("bulk-analysis-content", "children"),
        [
            Input("stored-bulk-chemistry-data", "data"),
            Input("bulk-analysis-type",         "value"),
            Input("bulk-phase-filter",          "value"),
            Input("bulk-y-element",             "value"),
            Input("bulk-x-element",             "value"),
            Input("mg-number-filter",           "value"),
            Input("sio2-filter",                "value"),
            Input("color-scheme-bulk",          "value"),
        ],
        prevent_initial_call=True,
    )
    def update_bulk_analysis(data, analysis_type, phase_filter,
                              y_elem, x_elem, mg_range, sio2_min, color_scheme):
        if not data:
            return dbc.Alert("Please upload data to begin analysis.", color="info")

        try:
            df_full = pd.DataFrame(data)
            df_full = compute_mg_number(df_full)

            # ── Filtered dataframe for non-TAS analyses ───────────────────────
            df_filt = df_full.copy()
            if phase_filter:
                df_filt = df_filt[df_filt["PHASE"].isin(phase_filter)]
            if "Mg#" in df_filt.columns:
                df_filt = df_filt[(df_filt["Mg#"] >= mg_range[0]) &
                                   (df_filt["Mg#"] <= mg_range[1])]
            if "SiO2" in df_filt.columns:
                df_filt = df_filt[df_filt["SiO2"] >= sio2_min]

            # ── BULK-only dataframe for TAS ───────────────────────────────────
            df_bulk = df_full[df_full["PHASE"] == "BULK"].copy()

            graphs = []

            # TAS ──────────────────────────────────────────────────────────────
            if analysis_type in ("tas", "all"):
                if df_bulk.empty:
                    graphs.append(dbc.Alert(
                        "No rows with PHASE = 'BULK' found for TAS diagram.",
                        color="warning"
                    ))
                else:
                    missing_tas = TAS_COLS - set(df_bulk.columns)
                    if missing_tas:
                        graphs.append(dbc.Alert(
                            f"TAS requires: {sorted(missing_tas)}", color="warning"
                        ))
                    else:
                        try:
                            tas_fig = create_tas_figure(df_bulk)
                            graphs.append(html.Div([
                                html.H5(
                                    f"TAS Classification Diagram "
                                    f"(n = {len(df_bulk)} BULK analyses)",
                                    className="mb-2"
                                ),
                                dcc.Graph(figure=tas_fig)
                            ], className="mb-4"))
                        except Exception as exc:
                            graphs.append(dbc.Alert(
                                f"Error creating TAS diagram: {exc}", color="danger"
                            ))

            # Element scatter + marginals ───────────────────────────────────────
            if analysis_type in ("element_scatter", "all"):
                if not x_elem or not y_elem:
                    graphs.append(dbc.Alert(
                        "Select X and Y elements for the scatter plot.", color="info"
                    ))
                elif df_filt.empty:
                    graphs.append(dbc.Alert(
                        "No data after filtering for element scatter.", color="warning"
                    ))
                else:
                    try:
                        scatter_fig = create_element_scatter(df_filt, x_elem, y_elem)
                        phase_label = (
                            f"PHASE: {', '.join(phase_filter)}"
                            if phase_filter else "all phases"
                        )
                        graphs.append(html.Div([
                            html.H5(
                                f"{y_elem} vs {x_elem} — {phase_label} "
                                f"(n = {len(df_filt[[x_elem, y_elem]].dropna())})",
                                className="mb-2"
                            ),
                            dcc.Graph(figure=scatter_fig)
                        ], className="mb-4"))
                    except Exception as exc:
                        graphs.append(dbc.Alert(
                            f"Error creating element scatter: {exc}", color="danger"
                        ))

            # Halogen evolution ────────────────────────────────────────────────
            if analysis_type in ("halogen_evolution", "all"):
                missing_hal = HALOGEN_COLS - set(df_filt.columns)
                if missing_hal:
                    graphs.append(dbc.Alert(
                        f"Halogen evolution requires: {sorted(missing_hal)}", color="warning"
                    ))
                elif df_filt.empty:
                    graphs.append(dbc.Alert(
                        "No data after filtering for halogen evolution.", color="warning"
                    ))
                else:
                    try:
                        halogen_fig = get_mg_number_animation(df_filt)
                        graphs.append(html.Div([
                            html.H5("Halogen Evolution by Crystallization Stage",
                                    className="mb-2"),
                            dcc.Graph(figure=halogen_fig)
                        ], className="mb-4"))
                    except Exception as exc:
                        graphs.append(dbc.Alert(
                            f"Error creating halogen evolution plot: {exc}", color="danger"
                        ))

            if not graphs:
                return dbc.Alert("No plots generated.", color="warning")

            return html.Div(graphs)

        except Exception as exc:
            print(f"Error in update_bulk_analysis: {exc}")
            return dbc.Alert(f"Error in analysis: {exc}", color="danger")

    # Data summary
    @app.callback(
        Output("bulk-data-summary", "children"),
        Input("stored-bulk-chemistry-data", "data"),
        prevent_initial_call=True,
    )
    def update_data_summary(data):
        if not data:
            return "No data loaded"

        df      = pd.DataFrame(data)
        df      = compute_mg_number(df)
        phases  = df["PHASE"].value_counts().to_dict()
        phase_str = ", ".join(f"{p}: {n}" for p, n in phases.items())

        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        priority = [c for c in OPTIONAL_GEOCHM + ["Mg#"] if c in num_cols]
        display  = priority[:8] if priority else num_cols[:8]

        stat_cards = []
        for col in display:
            s = df[col].dropna().describe()
            stat_cards.append(dbc.Col([
                html.H6(col, className="fw-bold"),
                html.P(f"Mean: {s['mean']:.3f}",                  className="mb-1 small"),
                html.P(f"Range: {s['min']:.3f} – {s['max']:.3f}", className="mb-1 small"),
                html.P(f"Std: {s['std']:.3f}",                    className="mb-0 small"),
            ], width=3))

        return [
            html.H6(
                f"{len(df):,} rows · {df['SAMPLE'].nunique()} sample(s) · "
                f"{df['PHASE'].nunique()} phase(s) [{phase_str}] · "
                f"{len(df.columns)} columns"
            ),
            dbc.Row(stat_cards, className="mt-3"),
        ]

    # Raw data table
    @app.callback(
        Output("bulk-data-table", "children"),
        Input("stored-bulk-chemistry-data", "data"),
        prevent_initial_call=True,
    )
    def update_data_table(data):
        if not data:
            return "No data to display"

        df       = pd.DataFrame(data)
        num_cols = df.select_dtypes(include=["number"]).columns

        return dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[
                {"name": c, "id": c, "type": "numeric", "format": {"specifier": ".4f"}}
                if c in num_cols else {"name": c, "id": c}
                for c in df.columns
            ],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "8px",
                        "fontFamily": "Arial", "fontSize": "12px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            page_size=15,
            filter_action="native",
            sort_action="native",
            export_format="xlsx",
            export_headers="display",
        )