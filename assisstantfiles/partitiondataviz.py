import base64
import io
import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State
import plotly.graph_objects as go
import numpy as np
from scipy import stats


# ── Target elements ───────────────────────────────────────────────────────────
# Maps concentration column name → element symbol used in CDL99 / %ERR columns.
# e.g. "SiO2" column pairs with "Si CDL99" and "Si %ERR ".
# Cl and F use themselves as the symbol.

TARGET_ELEMENTS = {
    "SiO2":  "Si",
    "TiO2":  "Ti",
    "Al2O3": "Al",
    "Cr2O3": "Cr",
    "FeO":   "Fe",
    "NiO":   "Ni",
    "MnO":   "Mn",
    "MgO":   "Mg",
    "CaO":   "Ca",
    "BaO":   "Ba",
    "Na2O":  "Na",
    "K2O":   "K",
    "P2O5":  "P",
    "SO3":   "S",
    "Cl":    "Cl",
    "F":     "F",
}

REQUIRED_COLS = {"SAMPLE", "PHASE", "pair_id"}

# Only structural columns are metadata
_META_COLS = REQUIRED_COLS | {"NOTE"}


# ── Element detection ─────────────────────────────────────────────────────────

def _find_col(col_set, base):
    """Lookup base in col_set, tolerating a single trailing space."""
    if base in col_set:
        return base
    if (base + " ") in col_set:
        return base + " "
    return None


def detect_elements(df):
    """
    Return one config dict per TARGET_ELEMENTS key that exists as a column in df.
    CDL99 and %ERR companions are looked up via element symbol
    (e.g. SiO2 -> Si CDL99, Si %ERR ).

    Returns list of dicts: {name, cdl_col, err_col}
    """
    col_set  = {str(c) for c in df.columns}
    elements = []

    for col_name, symbol in TARGET_ELEMENTS.items():
        if col_name not in col_set:
            continue
        cdl_col = _find_col(col_set, f"{symbol} CDL99")
        err_col = _find_col(col_set, f"{symbol} %ERR")
        elements.append({
            "name":    col_name,
            "cdl_col": cdl_col,
            "err_col": err_col,
        })

    return elements


# ── Excel reader ──────────────────────────────────────────────────────────────

def load_excel_to_dataframe(file_like):
    """
    Read EPMA Excel file (all sheets concatenated).

    Returns
    -------
    combined : DataFrame
    elements : list of dicts from detect_elements()
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

    missing = REQUIRED_COLS - set(combined.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}. "
            "Required: SAMPLE, PHASE, pair_id."
        )

    combined = (
        combined[combined["PHASE"].isin(["AMPH", "MI"])]
        .dropna(subset=["pair_id"])
        .copy()
    )

    if combined.empty:
        raise ValueError("No AMPH/MI rows with a valid pair_id found.")

    elements = detect_elements(combined)
    if not elements:
        raise ValueError(
            f"None of the target elements ({', '.join(TARGET_ELEMENTS)}) "
            "were found as columns in the uploaded file."
        )

    return combined, elements


# ── Auto-detect MI always-below-detection ─────────────────────────────────────

def auto_detect_mi_below(df, elements):
    """
    For each element that has a CDL99 column, check whether every MI row
    is below its CDL99. Returns the set of element names where this is true.
    """
    mi = df[df["PHASE"] == "MI"]
    if mi.empty:
        return set()

    always_below = set()
    for e in elements:
        elem    = e["name"]
        cdl_col = e["cdl_col"]
        if not cdl_col or elem not in mi.columns or cdl_col not in mi.columns:
            continue
        if (mi[elem] < mi[cdl_col]).all():
            always_below.add(elem)

    return always_below


# ── Core pairing logic ────────────────────────────────────────────────────────

def pair_partitions(df_raw, element_configs):
    """
    Pair AMPH and MI rows by pair_id and compute D for each element.

    Parameters
    ----------
    df_raw : DataFrame
    element_configs : list of dicts, each with:
        'name'       : str
        'cdl_col'    : str | None
        'err_col'    : str | None
        'mi_use_cdl' : bool — use MI CDL99 as denominator (minimum-D estimate)

    Returns
    -------
    pairs  : DataFrame   one row per valid pair_id
    params : DataFrame   per-sample summary statistics
    """
    amph = df_raw[df_raw["PHASE"] == "AMPH"].copy()
    mi   = df_raw[df_raw["PHASE"] == "MI"].copy()

    overlap = sorted(set(amph["pair_id"].unique()) & set(mi["pair_id"].unique()))
    rows    = []

    for pid in overlap:
        a = amph[amph["pair_id"] == pid]
        m = mi[mi["pair_id"] == pid]

        if len(m) != 1:
            print(f"Skipping pair_id={pid}: {len(m)} MI rows (expected 1)")
            continue

        try:
            row = {
                "pair_id":         pid,
                "SAMPLE":          a["SAMPLE"].iloc[0],
                "n_amph_analyses": len(a),
                "any_below":       False,
            }

            for ecfg in element_configs:
                elem       = ecfg["name"]
                cdl_col    = ecfg.get("cdl_col")
                err_col    = ecfg.get("err_col")
                mi_use_cdl = ecfg.get("mi_use_cdl", False)

                if elem not in a.columns or elem not in m.columns:
                    continue

                # ── Amphibole ──────────────────────────────────────────────
                C_a     = a[elem].mean()
                C_a_CDL = a[cdl_col].mean() if cdl_col and cdl_col in a.columns else np.nan
                err_a   = a[err_col].mean()  if err_col and err_col in a.columns else np.nan

                # ── Melt inclusion ─────────────────────────────────────────
                C_m     = float(m[elem].iloc[0])
                C_m_CDL = float(m[cdl_col].iloc[0]) if cdl_col and cdl_col in m.columns else np.nan
                err_m   = float(m[err_col].iloc[0])  if err_col and err_col in m.columns else np.nan

                # ── Below-detection flags ──────────────────────────────────
                below_a = bool(not np.isnan(C_a_CDL) and C_a < C_a_CDL)
                below_m = bool(not np.isnan(C_m_CDL) and C_m < C_m_CDL)

                # mi_use_cdl means below-MI is expected — don't flag any_below
                if below_a or (below_m and not mi_use_cdl):
                    row["any_below"] = True

                row[f"below_{elem}_amph"]  = below_a
                row[f"below_{elem}_mi"]    = below_m
                row[f"C_{elem}_amph"]      = C_a
                row[f"C_{elem}_mi"]        = C_m
                row[f"C_{elem}_amph_CDL"]  = C_a_CDL
                row[f"C_{elem}_mi_CDL"]    = C_m_CDL

                # ── Partition coefficient ──────────────────────────────────
                denom = C_m_CDL if mi_use_cdl else C_m
                if not (np.isnan(denom) if isinstance(denom, float) else False) and denom and denom > 0:
                    D = C_a / denom
                    D_err = (
                        D * np.sqrt((err_a / 100) ** 2 + (err_m / 100) ** 2)
                        if not (np.isnan(err_a) or np.isnan(err_m))
                        else np.nan
                    )
                else:
                    D = D_err = np.nan

                row[f"D_{elem}"]     = D
                row[f"D_{elem}_err"] = D_err

            # ── Mg# ───────────────────────────────────────────────────────
            MgO = row.get("C_MgO_amph", np.nan)
            FeO = row.get("C_FeO_amph", np.nan)
            if not (np.isnan(MgO) or np.isnan(FeO)) and (MgO + FeO) > 0:
                row["Mg#"] = 100 * MgO / (MgO + FeO)

            # ── NOTE ──────────────────────────────────────────────────────
            if "NOTE" in a.columns:
                notes = a["NOTE"].dropna().unique()
                row["NOTE"] = "; ".join(str(n) for n in notes)

            rows.append(row)

        except Exception as exc:
            print(f"Error processing pair_id={pid}: {exc}")

    pairs  = pd.DataFrame(rows)
    d_cols = [c for c in pairs.columns if c.startswith("D_") and not c.endswith("_err")]
    if d_cols and not pairs.empty:
        pairs = pairs.dropna(subset=d_cols, how="all")

    if pairs.empty:
        return pairs, pd.DataFrame()

    # ── Per-sample summary ─────────────────────────────────────────────────
    params_rows = []
    for samp in pairs["SAMPLE"].unique():
        sp    = pairs[pairs["SAMPLE"] == samp]
        above = sp[~sp["any_below"]]
        prow  = {
            "SAMPLE":            samp,
            "n_pairs":           len(sp),
            "n_above_detection": len(above),
        }
        for ecfg in element_configs:
            col = f"D_{ecfg['name']}"
            if col in sp.columns:
                prow[f"{col}_mean"]   = sp[col].mean()
                prow[f"{col}_median"] = sp[col].median()
                prow[f"{col}_std"]    = sp[col].std()
        if "Mg#" in sp.columns:
            prow["Mg#"] = sp["Mg#"].mean()
        params_rows.append(prow)

    params = pd.DataFrame(params_rows).round(4)
    return pairs, params


# ── Statistics helper ─────────────────────────────────────────────────────────

def calculate_partition_statistics(pairs, element_configs):
    if pairs.empty:
        return pd.DataFrame()

    rows = []
    for label in ["All"] + list(pairs["SAMPLE"].unique()):
        sp    = pairs if label == "All" else pairs[pairs["SAMPLE"] == label]
        above = sp[~sp["any_below"]]
        srow  = {
            "SAMPLE":            label,
            "n_total":           len(sp),
            "n_above_detection": len(above),
        }
        for ecfg in element_configs:
            col = f"D_{ecfg['name']}"
            if col in sp.columns:
                srow[f"{col}_mean"]   = sp[col].mean()
                srow[f"{col}_median"] = sp[col].median()
                srow[f"{col}_std"]    = sp[col].std()
                srow[f"{col}_min"]    = sp[col].min()
                srow[f"{col}_max"]    = sp[col].max()
        rows.append(srow)

    return pd.DataFrame(rows).round(4)


# ── Layout ────────────────────────────────────────────────────────────────────

def create_partition_analysis_layout():
    return dbc.Container(fluid=True, children=[

        html.H2("Partition Coefficient Analysis", className="my-4 text-center"),

        # ── Upload ────────────────────────────────────────────────────────────
        dbc.Row([dbc.Col([
            html.H4("📁 Data Upload", className="mb-3"),
            dbc.Card(dbc.CardBody([
                dcc.Upload(
                    id="upload-partition-data",
                    children=html.Div([
                        "Drag & Drop or ",
                        html.A("Select EPMA Data File", className="text-primary"),
                    ]),
                    style={
                        "width": "100%", "height": "80px", "lineHeight": "80px",
                        "borderWidth": "2px", "borderStyle": "dashed",
                        "borderRadius": "8px", "textAlign": "center",
                        "margin": "10px 0", "borderColor": "#007bff",
                        "backgroundColor": "#f8f9fa",
                    },
                    multiple=False,
                ),
                html.Div(id="partition-upload-status", className="mt-2"),

                dbc.Collapse([
                    dbc.Alert([
                        html.H6("📋 File Requirements:", className="alert-heading"),
                        html.Ul([
                            html.Li("Excel (.xlsx/.xls); all sheets concatenated automatically"),
                            html.Li([html.Strong("Required columns: "), "SAMPLE, PHASE, pair_id"]),
                            html.Li("PHASE must be 'AMPH' or 'MI'; each pair_id needs exactly one MI row"),
                            html.Li([
                                html.Strong("Target elements: "),
                                ", ".join(TARGET_ELEMENTS.keys()),
                            ]),
                            html.Li([
                                html.Strong("Optional CDL/ERR companions: "),
                                "'{elem} CDL99' and '{elem} %ERR' columns enable "
                                "below-detection flagging and error bars",
                            ]),
                        ], className="mb-0"),
                    ], color="info"),
                ], id="file-requirements-collapse", is_open=False),

                dbc.Button("Show/Hide File Requirements", id="toggle-requirements",
                           color="outline-info", size="sm", className="mt-2"),
            ])),
        ], width=12)], className="mb-4"),

        # ── Stores ───────────────────────────────────────────────────────────
        dcc.Store(id="stored-raw-data"),
        dcc.Store(id="stored-element-configs"),
        dcc.Store(id="stored-partition-pairs"),
        dcc.Store(id="stored-partition-params"),

        # ── Element Configuration ─────────────────────────────────────────────
        dbc.Row([dbc.Col([
            dbc.Collapse([
                html.H4("🧪 Element Configuration", className="mb-3"),
                dbc.Card(dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Active elements:", className="fw-bold mb-2"),
                            dcc.Checklist(
                                id="active-elements-checklist",
                                options=[], value=[],
                                inline=True,
                                inputStyle={"margin-right": "5px"},
                                labelStyle={"margin-right": "15px"},
                            ),
                        ], width=6),
                        dbc.Col([
                            html.Label(
                                "MI always below detection — use CDL99 as denominator "
                                "(D becomes a minimum estimate):",
                                className="fw-bold mb-2",
                            ),
                            dcc.Checklist(
                                id="mi-below-det-checklist",
                                options=[], value=[],
                                inline=True,
                                inputStyle={"margin-right": "5px"},
                                labelStyle={"margin-right": "15px"},
                            ),
                        ], width=6),
                    ]),
                    dbc.Button("⚙️ Recompute Partitions", id="recompute-btn",
                               color="primary", className="mt-3"),
                ])),
            ], id="element-config-collapse", is_open=False),
        ], width=12)], className="mb-4"),

        # ── Analysis Controls ─────────────────────────────────────────────────
        dbc.Row([dbc.Col([
            html.H4("⚙️ Analysis Controls", className="mb-3"),
            dbc.Card(dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Plot Type:", className="fw-bold"),
                        dcc.Dropdown(
                            id="partition-plot-type",
                            options=[
                                {"label": "🔗 Scatter (X vs Y)", "value": "scatter"},
                                {"label": "📊 Boxplot",           "value": "box"},
                                {"label": "📈 All",               "value": "all"},
                            ],
                            value="scatter", clearable=False, style={"color": "black"},
                        ),
                    ], width=2),
                    dbc.Col([
                        html.Label("X axis element:", className="fw-bold"),
                        dcc.Dropdown(
                            id="partition-x-element",
                            placeholder="Select element...",
                            clearable=False, style={"color": "black"},
                        ),
                    ], width=2),
                    dbc.Col([
                        html.Label("Y axis element (scatter):", className="fw-bold"),
                        dcc.Dropdown(
                            id="partition-y-element",
                            placeholder="Select element...",
                            clearable=False, style={"color": "black"},
                        ),
                    ], width=2),
                    dbc.Col([
                        html.Label("Regression:", className="fw-bold"),
                        dcc.Dropdown(
                            id="partition-regression-toggle",
                            options=[
                                {"label": "Show (above-det. only)", "value": "show"},
                                {"label": "Hide",                   "value": "hide"},
                            ],
                            value="show", clearable=False, style={"color": "black"},
                        ),
                    ], width=2),
                    dbc.Col([
                        html.Label("Below-detection points:", className="fw-bold"),
                        dcc.Dropdown(
                            id="partition-below-det-mode",
                            options=[
                                {"label": "Plot measured D",    "value": "measured"},
                                {"label": "Plot CDL99-based D", "value": "cdl"},
                            ],
                            value="measured", clearable=False, style={"color": "black"},
                        ),
                    ], width=4),
                ]),
            ])),
        ], width=12)], className="mb-4"),

        # ── Results ───────────────────────────────────────────────────────────
        dbc.Row([dbc.Col([
            html.H4("📊 Results", className="mb-3"),
            dcc.Loading(
                children=html.Div(id="partition-results-content"),
                type="circle", color="#007bff",
            ),
        ], width=12)], className="mb-4"),

        # ── Statistics ────────────────────────────────────────────────────────
        dbc.Row([dbc.Col([
            html.Div(id="partition-statistics-section"),
        ], width=12)], className="mb-4"),

        # ── Data Tables ───────────────────────────────────────────────────────
        dbc.Row([dbc.Col([
            html.H4("📋 Data Tables", className="mb-3"),
            dbc.Tabs([
                dbc.Tab(label="📊 Summary Statistics", tab_id="summary-tab",
                        children=html.Div(id="partition-data-summary",  className="mt-3")),
                dbc.Tab(label="🔍 Paired D Values",    tab_id="raw-tab",
                        children=html.Div(id="partition-data-table",    className="mt-3")),
                dbc.Tab(label="📋 Sample Parameters",  tab_id="params-tab",
                        children=html.Div(id="partition-params-table",  className="mt-3")),
            ], id="data-tabs", active_tab="summary-tab"),
        ], width=12)]),
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────

def create_partition_analysis_callbacks(app):

    # ── Toggle file requirements ──────────────────────────────────────────────
    @app.callback(
        Output("file-requirements-collapse", "is_open"),
        Input("toggle-requirements", "n_clicks"),
        State("file-requirements-collapse", "is_open"),
    )
    def toggle_file_requirements(n_clicks, is_open):
        return not is_open if n_clicks else is_open

    # ── Upload ────────────────────────────────────────────────────────────────
    @app.callback(
        [
            Output("stored-raw-data",         "data"),
            Output("stored-element-configs",  "data"),
            Output("stored-partition-pairs",  "data"),
            Output("stored-partition-params", "data"),
            Output("partition-upload-status", "children"),
        ],
        Input("upload-partition-data", "contents"),
        State("upload-partition-data", "filename"),
        prevent_initial_call=True,
    )
    def load_partition_file(contents, filename):
        if not contents:
            return None, None, None, None, html.Div("No file uploaded.", className="text-muted")

        try:
            _, b64    = contents.split(",", 1)
            file_like = io.BytesIO(base64.b64decode(b64))

            if not filename or not filename.lower().endswith((".xls", ".xlsx")):
                raise ValueError("Please upload an Excel (.xlsx or .xls) file.")

            df_raw, elements = load_excel_to_dataframe(file_like)

            # Auto-detect elements where all MI rows are below detection
            mi_auto = auto_detect_mi_below(df_raw, elements)

            # Annotate dicts with auto-detected flag for checklist pre-selection
            elements = [{**e, "mi_always_below": e["name"] in mi_auto}
                        for e in elements]

            # Initial computation: respect auto-detected mi_use_cdl
            element_configs = [{**e, "mi_use_cdl": e["name"] in mi_auto}
                               for e in elements]
            pairs, params   = pair_partitions(df_raw, element_configs)

            if pairs.empty:
                return (
                    df_raw.to_json(orient="records"), elements, None, None,
                    dbc.Alert(
                        "No valid AMPH/MI pairs found. Verify that pair_id values match "
                        "between AMPH and MI rows, and each pair_id has exactly one MI row.",
                        color="warning",
                    ),
                )

            n_pairs        = len(pairs)
            n_above        = int((~pairs["any_below"]).sum())
            elem_names     = ", ".join(e["name"] for e in elements)
            mi_auto_names  = ", ".join(sorted(mi_auto)) if mi_auto else "none"

            status = dbc.Alert([
                html.H6("✅ Upload Successful!", className="alert-heading"),
                html.P([
                    f"Processed {n_pairs} AMPH/MI pairs from {filename}. ",
                    f"{n_above} above detection · {n_pairs - n_above} below detection. ",
                    html.Br(),
                    f"Detected elements: {elem_names}. ",
                    f"MI auto-detected below detection: {mi_auto_names}. ",
                    html.Em("Adjust element configuration below if needed."),
                ], className="mb-0"),
            ], color="success")

            return (
                df_raw.to_json(orient="records"),
                elements,
                pairs.to_dict("records"),
                params.to_dict("records"),
                status,
            )

        except Exception as exc:
            print(f"Upload error: {exc}")
            return None, None, None, None, dbc.Alert([
                html.H6("❌ Processing Error:", className="alert-heading"),
                html.P(str(exc), className="mb-0"),
            ], color="danger")

    # ── Populate element config checklists ────────────────────────────────────
    @app.callback(
        [
            Output("element-config-collapse",   "is_open"),
            Output("active-elements-checklist", "options"),
            Output("active-elements-checklist", "value"),
            Output("mi-below-det-checklist",    "options"),
            Output("mi-below-det-checklist",    "value"),
        ],
        Input("stored-element-configs", "data"),
    )
    def show_element_config(elem_data):
        if not elem_data:
            return False, [], [], [], []
        opts          = [{"label": f" {e['name']}", "value": e["name"]} for e in elem_data]
        active_vals   = [e["name"] for e in elem_data]
        # Only show MI-below-det option for elements that have a CDL99 column
        cdl_opts      = [{"label": f" {e['name']}", "value": e["name"]}
                         for e in elem_data if e.get("cdl_col")]
        mi_below_vals = [e["name"] for e in elem_data if e.get("mi_always_below")]
        return True, opts, active_vals, cdl_opts, mi_below_vals

    # ── Populate X/Y dropdowns ────────────────────────────────────────────────
    @app.callback(
        [
            Output("partition-x-element", "options"),
            Output("partition-x-element", "value"),
            Output("partition-y-element", "options"),
            Output("partition-y-element", "value"),
        ],
        Input("stored-element-configs", "data"),
    )
    def update_element_dropdowns(elem_data):
        if not elem_data:
            return [], None, [], None
        opts  = [{"label": e["name"], "value": e["name"]} for e in elem_data]
        x_val = elem_data[0]["name"] if len(elem_data) >= 1 else None
        y_val = elem_data[1]["name"] if len(elem_data) >= 2 else x_val
        return opts, x_val, opts, y_val

    # ── Recompute on button click ─────────────────────────────────────────────
    @app.callback(
        [
            Output("stored-partition-pairs",  "data", allow_duplicate=True),
            Output("stored-partition-params", "data", allow_duplicate=True),
        ],
        Input("recompute-btn", "n_clicks"),
        [
            State("stored-raw-data",           "data"),
            State("stored-element-configs",    "data"),
            State("active-elements-checklist", "value"),
            State("mi-below-det-checklist",    "value"),
        ],
        prevent_initial_call=True,
    )
    def recompute_partitions(n_clicks, raw_json, elem_configs, active_elems, mi_below):
        if not raw_json or not elem_configs:
            return None, None

        active_set   = set(active_elems or [])
        mi_below_set = set(mi_below     or [])

        element_configs = [
            {**e, "mi_use_cdl": e["name"] in mi_below_set}
            for e in elem_configs
            if e["name"] in active_set
        ]

        if not element_configs:
            return None, None

        df_raw        = pd.DataFrame(json.loads(raw_json))
        pairs, params = pair_partitions(df_raw, element_configs)

        if pairs.empty:
            return None, None

        return pairs.to_dict("records"), params.to_dict("records")

    # ── Build plots ───────────────────────────────────────────────────────────
    @app.callback(
        Output("partition-results-content", "children"),
        [
            Input("stored-partition-pairs",      "data"),
            Input("stored-element-configs",      "data"),
            Input("partition-plot-type",         "value"),
            Input("partition-x-element",         "value"),
            Input("partition-y-element",         "value"),
            Input("partition-regression-toggle", "value"),
            Input("mi-below-det-checklist",      "value"),
            Input("partition-below-det-mode",    "value"),
        ],
        prevent_initial_call=True,
    )
    def update_partition_plots(
        pairs_data, elem_configs, plot_type,
        x_elem, y_elem, show_regression, mi_below, below_det_mode
    ):
        if not pairs_data or not elem_configs:
            return dbc.Alert("Upload data to see results.", color="info")

        try:
            pairs    = pd.DataFrame(pairs_data)
            mi_below = set(mi_below or [])
            use_cdl  = (below_det_mode == "cdl")
            plots    = []

            def _axis_label(elem):
                suffix = "<sup>min</sup>" if elem in mi_below else ""
                return f"D<sub>{elem}</sub>{suffix}<sup> AMPH/MELT</sup>"

            def _cdl_d_value(row, elem):
                num = (row.get(f"C_{elem}_amph_CDL", np.nan)
                       if row.get(f"below_{elem}_amph")
                       else row.get(f"C_{elem}_amph", np.nan))
                den = (row.get(f"C_{elem}_mi_CDL", np.nan)
                       if row.get(f"below_{elem}_mi")
                       else row.get(f"C_{elem}_mi", np.nan))
                if pd.isna(num) or pd.isna(den) or den == 0:
                    return np.nan
                return num / den

            def _display_d(sub, elem, apply_cdl):
                col = f"D_{elem}"
                if not apply_cdl:
                    return sub[col]
                return sub.apply(
                    lambda r: _cdl_d_value(r, elem) if r["any_below"] else r[col],
                    axis=1,
                )

            def _display_d_err(sub, elem, apply_cdl):
                err_col = f"D_{elem}_err"
                d_col   = f"D_{elem}"
                if err_col not in sub.columns:
                    return pd.Series(np.nan, index=sub.index)
                if not apply_cdl:
                    return sub[err_col]
                cdl_d   = _display_d(sub, elem, apply_cdl=True)
                rel_err = sub[err_col] / sub[d_col].replace(0, np.nan)
                return (cdl_d * rel_err).fillna(np.nan)

            above = pairs[~pairs["any_below"]]
            below = pairs[ pairs["any_below"]]

            # ── Scatter ────────────────────────────────────────────────────
            if plot_type in ("scatter", "all") and x_elem and y_elem:
                x_col, y_col = f"D_{x_elem}", f"D_{y_elem}"
                x_err, y_err = f"D_{x_elem}_err", f"D_{y_elem}_err"

                if x_col not in pairs.columns or y_col not in pairs.columns:
                    plots.append(dbc.Alert(
                        f"Columns {x_col} or {y_col} not found. "
                        "Check element configuration and recompute.",
                        color="warning",
                    ))
                else:
                    fig = go.Figure()

                    def _scatter_trace(sub, name, fill_color, is_below=False):
                        has_note   = "NOTE" in sub.columns
                        cdata_cols = ["pair_id", "SAMPLE"] + (["NOTE"] if has_note else [])
                        note_line  = "<br>Note: %{customdata[2]}" if has_note else ""
                        cdl_active = use_cdl and is_below
                        x_vals     = _display_d(sub, x_elem, cdl_active)
                        y_vals     = _display_d(sub, y_elem, cdl_active)
                        x_errs     = _display_d_err(sub, x_elem, cdl_active)
                        y_errs     = _display_d_err(sub, y_elem, cdl_active)
                        cdl_note   = " (CDL99)" if cdl_active else ""
                        return go.Scatter(
                            x=x_vals, y=y_vals,
                            mode="markers", name=name,
                            error_x=dict(
                                type="data",
                                array=x_errs.fillna(0).tolist(),
                                visible=(x_err in sub.columns),
                                color="rgba(0,0,0,0.5)", thickness=1.5, width=4,
                            ),
                            error_y=dict(
                                type="data",
                                array=y_errs.fillna(0).tolist(),
                                visible=(y_err in sub.columns),
                                color="rgba(0,0,0,0.5)", thickness=1.5, width=4,
                            ),
                            marker=dict(
                                symbol="circle", size=10, color=fill_color,
                                line=dict(color="black", width=1.5),
                            ),
                            customdata=sub[cdata_cols].values,
                            hovertemplate=(
                                "<b>pair_id %{customdata[0]}</b><br>"
                                "Sample: %{customdata[1]}<br>"
                                f"{x_col}{cdl_note}: %{{x:.4f}}<br>"
                                f"{y_col}{cdl_note}: %{{y:.4f}}"
                                + note_line +
                                "<extra></extra>"
                            ),
                        )

                    if not above.empty:
                        fig.add_trace(_scatter_trace(above, "Above detection", "black"))
                    if not below.empty:
                        below_label = "Below det. (CDL99 D)" if use_cdl else "Below detection limit"
                        fig.add_trace(_scatter_trace(below, below_label, "white", is_below=True))

                    if show_regression == "show" and len(above) >= 2:
                        valid = above[[x_col, y_col]].dropna()
                        if len(valid) >= 2:
                            slope, intercept, r, _, _ = stats.linregress(
                                valid[x_col], valid[y_col]
                            )
                            x_fit = np.linspace(
                                pairs[x_col].min() - 0.3,
                                pairs[x_col].max() + 0.3,
                                200,
                            )
                            fig.add_trace(go.Scatter(
                                x=x_fit, y=slope * x_fit + intercept,
                                mode="lines",
                                name=(
                                    f"y = {slope:.2f}x + {intercept:.2f}  "
                                    f"(R²={r**2:.3f}, n={len(valid)})"
                                ),
                                line=dict(color="black", width=2, dash="dash"),
                            ))

                    fig.update_layout(
                        title=f"D<sub>{y_elem}</sub> vs D<sub>{x_elem}</sub>",
                        xaxis_title=_axis_label(x_elem),
                        yaxis_title=_axis_label(y_elem),
                        height=520, title_x=0.5,
                        plot_bgcolor="white", paper_bgcolor="white",
                        xaxis=dict(
                            showgrid=True, gridcolor="rgba(128,128,128,0.3)",
                            zeroline=False, showline=True, linecolor="black",
                            linewidth=2, mirror=True, ticks="outside",
                        ),
                        yaxis=dict(
                            showgrid=True, gridcolor="rgba(128,128,128,0.3)",
                            zeroline=False, showline=True, linecolor="black",
                            linewidth=2, mirror=True, ticks="outside",
                        ),
                        legend=dict(
                            bgcolor="white", bordercolor="black", borderwidth=1,
                            x=0.98, y=0.98, xanchor="right", yanchor="top",
                        ),
                    )
                    plots.append(dcc.Graph(figure=fig, style={"margin-bottom": "20px"}))

            # ── Boxplots ───────────────────────────────────────────────────
            if plot_type in ("box", "all"):
                box_elements = (
                    [e["name"] for e in elem_configs if f"D_{e['name']}" in pairs.columns]
                    if plot_type == "all"
                    else ([x_elem] if x_elem else [])
                )

                for elem in box_elements:
                    col = f"D_{elem}"
                    if col not in pairs.columns:
                        continue
                    fig = go.Figure()
                    for samp in pairs["SAMPLE"].unique():
                        sp     = pairs[pairs["SAMPLE"] == samp]
                        y_vals = _display_d(sp, elem, use_cdl)
                        fig.add_trace(go.Box(
                            y=y_vals, name=samp, boxpoints="all",
                            jitter=0.4, pointpos=0,
                            marker=dict(size=6, opacity=0.7),
                        ))
                    cdl_suffix = " (CDL99 for below-det)" if use_cdl else ""
                    fig.update_layout(
                        title=_axis_label(elem) + " by Sample" + cdl_suffix,
                        yaxis_title=_axis_label(elem),
                        height=450, title_x=0.5,
                        plot_bgcolor="white", paper_bgcolor="white",
                        xaxis=dict(showline=True, linecolor="black", linewidth=2, mirror=True),
                        yaxis=dict(
                            showline=True, linecolor="black", linewidth=2, mirror=True,
                            showgrid=True, gridcolor="rgba(128,128,128,0.3)",
                        ),
                    )
                    plots.append(dcc.Graph(figure=fig, style={"margin-bottom": "20px"}))

            return (
                html.Div(plots) if plots
                else dbc.Alert("No plots generated with current selection.", color="warning")
            )

        except Exception as exc:
            print(f"Error in update_partition_plots: {exc}")
            return dbc.Alert(f"Plot error: {exc}", color="danger")

    # ── Statistics summary ────────────────────────────────────────────────────
    @app.callback(
        Output("partition-statistics-section", "children"),
        [
            Input("stored-partition-pairs",  "data"),
            Input("stored-element-configs",  "data"),
        ],
        prevent_initial_call=True,
    )
    def update_statistics_section(pairs_data, elem_configs):
        if not pairs_data or not elem_configs:
            return html.Div()
        try:
            pairs    = pd.DataFrame(pairs_data)
            stats_df = calculate_partition_statistics(pairs, elem_configs)
            if stats_df.empty:
                return html.Div()
            non_numeric = {"SAMPLE", "n_total", "n_above_detection"}
            return html.Div([
                html.H5("📊 Partition Coefficient Statistics", className="mb-3"),
                dbc.Card(dbc.CardBody([
                    dash_table.DataTable(
                        data=stats_df.to_dict("records"),
                        columns=[
                            {"name": c, "id": c,
                             "type": "numeric", "format": {"specifier": ".4f"}}
                            if c not in non_numeric else {"name": c, "id": c}
                            for c in stats_df.columns
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "left", "padding": "10px"},
                        style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                        style_data_conditional=[
                            {"if": {"row_index": "odd"},
                             "backgroundColor": "rgb(248,248,248)"},
                            {"if": {"filter_query": '{SAMPLE} = "All"'},
                             "fontWeight": "bold", "backgroundColor": "#e8f4f8"},
                        ],
                    )
                ])),
            ])
        except Exception as exc:
            return dbc.Alert(f"Statistics error: {exc}", color="danger")

    # ── Paired D values table ─────────────────────────────────────────────────
    @app.callback(
        Output("partition-data-table", "children"),
        Input("stored-partition-pairs", "data"),
        prevent_initial_call=True,
    )
    def update_table(pairs_data):
        if not pairs_data:
            return "No data to display."
        try:
            df       = pd.DataFrame(pairs_data)
            num_cols = set(df.select_dtypes(include=["number"]).columns)
            df_disp  = df.copy()
            for col in num_cols:
                df_disp[col] = df_disp[col].round(4)
            return dash_table.DataTable(
                data=df_disp.to_dict("records"),
                columns=[
                    {"name": c, "id": c, "type": "numeric", "format": {"specifier": ".4f"}}
                    if c in num_cols else {"name": c, "id": c}
                    for c in df_disp.columns
                ],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "10px"},
                style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248,248,248)"}
                ],
                page_size=20,
                filter_action="native",
                sort_action="native",
                export_format="xlsx",
                export_headers="display",
            )
        except Exception as exc:
            return dbc.Alert(f"Table error: {exc}", color="danger")

    # ── Summary statistics table ──────────────────────────────────────────────
    @app.callback(
        Output("partition-data-summary", "children"),
        [
            Input("stored-partition-pairs",  "data"),
            Input("stored-element-configs",  "data"),
        ],
        prevent_initial_call=True,
    )
    def update_summary(pairs_data, elem_configs):
        if not pairs_data or not elem_configs:
            return "No data loaded."
        try:
            stats_df    = calculate_partition_statistics(pd.DataFrame(pairs_data), elem_configs)
            non_numeric = {"SAMPLE", "n_total", "n_above_detection"}
            return dash_table.DataTable(
                data=stats_df.to_dict("records"),
                columns=[
                    {"name": c, "id": c, "type": "numeric", "format": {"specifier": ".4f"}}
                    if c not in non_numeric else {"name": c, "id": c}
                    for c in stats_df.columns
                ],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "10px"},
                style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248,248,248)"},
                    {"if": {"filter_query": '{SAMPLE} = "All"'},
                     "fontWeight": "bold", "backgroundColor": "#e8f4f8"},
                ],
                export_format="xlsx",
                export_headers="display",
            )
        except Exception as exc:
            return dbc.Alert(f"Summary error: {exc}", color="danger")

    # ── Sample parameters table ───────────────────────────────────────────────
    @app.callback(
        Output("partition-params-table", "children"),
        Input("stored-partition-params", "data"),
        prevent_initial_call=True,
    )
    def update_params_table(param_data):
        if not param_data:
            return "No parameter data to display."
        try:
            df       = pd.DataFrame(param_data)
            num_cols = set(df.select_dtypes(include=["number"]).columns)
            df_disp  = df.copy()
            for col in num_cols:
                df_disp[col] = df_disp[col].round(4)
            return dash_table.DataTable(
                data=df_disp.to_dict("records"),
                columns=[
                    {"name": c, "id": c, "type": "numeric", "format": {"specifier": ".4f"}}
                    if c in num_cols else {"name": c, "id": c}
                    for c in df_disp.columns
                ],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "10px"},
                style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248,248,248)"}
                ],
                page_size=15,
                filter_action="native",
                sort_action="native",
                export_format="xlsx",
                export_headers="display",
            )
        except Exception as exc:
            return dbc.Alert(f"Parameters error: {exc}", color="danger")