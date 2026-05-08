import pandas as pd  # type: ignore
import dash  # type: ignore
from dash import Dash, dcc, html, Input, Output  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore

# --- Local imports ---
from Pages.info import create_info_layout
from assisstantfiles.bulkdataviz import create_bulk_analysis_layout, create_bulk_analysis_callbacks
from assisstantfiles.partitiondataviz import (
    create_partition_analysis_layout,
    create_partition_analysis_callbacks,
)
from Pages.MapShiveluch import create_shiveluch_layout
# from Pages.AmphiboleZoning import create_amphibole_zoning_layout, create_amphibole_zoning_callbacks

# ─────────────────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    assets_folder="assisstantfiles",
    external_stylesheets=[
        dbc.themes.LUX,
        "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Crimson+Pro:wght@300;400;600&family=JetBrains+Mono:wght@400;600&display=swap",
    ],
    suppress_callback_exceptions=True,
)
app.title = "Subduction Zone Analysis — EPMA Data Portal"

# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":         "#0D1117",
    "surface":    "#161B22",
    "border":     "#2A3344",
    "accent":     "#C07840",
    "text_muted": "#8A8880",
    "text_dim":   "#3A3A38",
}
FONT_DISPLAY = "Cormorant Garamond, Georgia, serif"
FONT_BODY    = "Crimson Pro, Georgia, serif"
FONT_MONO    = "JetBrains Mono, monospace"

# ─────────────────────────────────────────────────────────────────────────────
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Home",               href="/")),
        dbc.NavItem(dbc.NavLink("Info",               href="/info")),
        dbc.NavItem(dbc.NavLink("Partition Analysis", href="/analysis")),
        dbc.NavItem(dbc.NavLink("Bulk Analysis",      href="/bulk")),
        dbc.NavItem(dbc.NavLink("Shiveluch",          href="/shiveluch")),
        # dbc.NavItem(dbc.NavLink("Amphibole Zoning",   href="/amphibole_zoning")),
    ],
    brand="EPMA Portal",
    color="primary",
    dark=True,
    className="mb-0",
)

# ─────────────────────────────────────────────────────────────────────────────
def stat_chip(value, label):
    return html.Div(className="stat-chip", children=[
        html.Div(value, className="stat-chip-val"),
        html.Div(label, className="stat-chip-lbl"),
    ])

def kv_row(key, value):
    return html.Div(className="kv-row", children=[
        html.Span(key + "  ", className="kv-key"),
        html.Span(value,      className="kv-val"),
    ])

def nav_card(icon, title, body, tag, href, delay="0s", img_src=None):
    if img_src:
        top_block = html.Div(className="nav-card-img-wrap", children=[
            html.Img(src=img_src, className="nav-card-img"),
            html.Div(className="nav-card-img-fade"),
        ])
    else:
        top_block = html.Span(icon, className="nav-card-icon")

    return dbc.Col(
        html.A(
            className="nav-card",
            href=href,
            style={"animationDelay": delay},
            children=[
                top_block,
                html.Div(title, className="nav-card-title"),
                html.Div(body,  className="nav-card-body"),
                html.Span(tag,  className="nav-card-tag"),
            ],
        ),
        xs=12, sm=6, lg=3, className="mb-4 d-flex",
    )

def step_block(num, title, body, cols=None, accent_color="#C07840"):
    tags = [html.Span(c, className="col-tag") for c in (cols or [])]
    return dbc.Col([
        html.Div(
            style={
                "borderLeft": f"2px solid {accent_color}",
                "paddingLeft": "1.15rem",
                "paddingTop": "0.15rem",
                "paddingBottom": "0.15rem",
            },
            children=[
                html.Span(num,  className="step-num"),
                html.Div(title, className="step-title"),
                html.Div(body,  className="step-body"),
                html.Div(tags, className="mt-2") if tags else None,
            ],
        )
    ], xs=12, md=4, className="mb-4")


# ─────────────────────────────────────────────────────────────────────────────
home_layout = html.Div(style={"minHeight": "100vh", "background": C["bg"]}, children=[

    html.Div(className="home-hero", style={"padding": "5.5rem 2rem 4.5rem"}, children=[
        html.Div(className="home-grid"),
        dbc.Container(fluid=True, style={"maxWidth": "1280px"}, children=[
            dbc.Row([
                dbc.Col([
                    html.Div("Electron Probe MicroAnalyzer Portal", className="home-title"),
                    html.Hr(className="home-rule"),
                    html.Div(
                        "Halogen Partitioning · Amphibole Geochemistry · Subduction Systems",
                        className="home-subtitle",
                    ),
                    html.Div(className="home-meta mt-4", children=[
                        html.Span("Washington University in St. Louis",
                                  style={"fontFamily": FONT_MONO, "fontSize": "0.68rem",
                                         "letterSpacing": "0.1em", "color": C["text_dim"],
                                         "textTransform": "uppercase"}),
                        html.Span(" · ", style={"color": C["text_dim"], "margin": "0 0.5rem"}),
                        html.Span("Experimental Studies of Planetary Materials",
                                  style={"fontFamily": FONT_MONO, "fontSize": "0.68rem",
                                         "letterSpacing": "0.1em", "color": C["text_dim"],
                                         "textTransform": "uppercase"}),
                    ]),
                ], lg=7),
                dbc.Col(
                    className="d-none d-lg-flex align-items-center justify-content-end",
                    children=[
                        html.Div(
                            style={"display": "flex", "flexDirection": "column",
                                   "gap": "0.7rem", "alignItems": "flex-end"},
                            children=[
                                stat_chip("3",             "Analysis Modules"),
                                stat_chip("D_Cl · D_F", "Partition Coefficients"),
                                stat_chip("CDL₉₉",         "Detection Threshold Identification"),
                            ],
                        )
                    ],
                    lg=5,
                ),
            ])
        ]),
    ]),

    html.Div(style={"padding": "4.5rem 0 3rem"}, children=[
        dbc.Container(fluid=True, style={"maxWidth": "1280px"}, children=[

            dbc.Row([dbc.Col([
                html.Span("Modules",                    className="section-label"),
                html.Div("Choose an Analysis Module",   className="section-heading"),
            ], className="mb-4")]),

            dbc.Row([
                nav_card("⚗️", "Partition Analysis",
                         "Compute D_Cl and D_Fmin from paired AMPH/MI analyses. "
                         "Deterministic pairing by pair_id with %ERR error propagation "
                         "and below-detection flagging.",
                         "AMPH · MI", "/analysis", delay="0.3s",
                         img_src=app.get_asset_url("1704k1microscopeimage.jpeg")),
                nav_card("🌋", "Bulk Chemistry",
                         "TAS classification from BULK-phase analyses. "
                         "Element scatter plots with marginal histograms and KDE overlays "
                         "for any selectable wt% column pair.",
                         "TAS · Scatter · KDE", "/bulk", delay="0.45s",
                         img_src=app.get_asset_url("5x_PPL_twinning.jpeg")),
                #nav_card("🔬", "Amphibole Zoning",
                         #"Traverse-based compositional zoning analysis. "
                         #"Visualize diffusion profiles and inter-crystal "
                         #"chemical gradients across AMPH analyses.",
                         #"Zoning · Diffusion", "/amphibole_zoning", #delay="0.6s",
                         #img_src=app.get_asset_url("BSEimage.jpeg")),
                nav_card("🗺️", "Shiveluch Case Study",
                         "Interactive map and contextual geology for the "
                         "Shiveluch Volcanic Complex, Kamchatka — the reference "
                         "system for this portal.",
                         "Kamchatka · Geology", "/shiveluch", delay="0.75s",
                         img_src=app.get_asset_url("maficintrusion.jpg")),
            ], className="mb-5"),

            html.Hr(style={"borderColor": C["border"], "margin": "0.5rem 0 3.5rem"}),

            dbc.Row([dbc.Col([
                html.Span("Getting Started",       className="section-label"),
                html.Div("Three-Step Workflow",    className="section-heading"),
            ], className="mb-4")]),

            dbc.Row([
                step_block(
                    "01 — PREPARE", "Format Your EPMA Output",
                    "Ensure your Excel file contains the columns below. "
                    "All sheets are concatenated automatically — no manual merging required. "
                    "Create a 'pair_id' column to link AMPH/MI analyses and phase type.",
                    cols=["SAMPLE", "PHASE", "pair_id", "Cl", "F",
                          "Cl CDL99", "F CDL99", "Cl %ERR ", "F %ERR "],
                ),
                step_block(
                    "02 — UPLOAD", "Drop Your File",
                    "Drag and drop onto the Partition Analysis or Bulk Chemistry page. "
                    "Validation runs automatically and reports any missing columns.",
                ),
                step_block(
                    "03 — EXPLORE", "Interact with Results",
                    "Filter by PHASE, Mg#, or SiO₂. Toggle regression lines and "
                    "detection-limit markers. Export any table directly to .xlsx.",
                    accent_color="#8C3A2E",
                ),
            ], className="mb-5"),

            html.Hr(style={"borderColor": C["border"], "margin": "0.5rem 0 3.5rem"}),

            dbc.Row([dbc.Col([
                html.Span("About",              className="section-label"),
                html.Div("Scientific Context",  className="section-heading"),
            ], className="mb-4")]),

            dbc.Row([
                dbc.Col([
                    html.P(
                        "This portal supports the analysis of halogen (Cl, F) partitioning "
                        "between amphibole and silicate melt in subduction zone settings. "
                        "Partition coefficients are calculated from paired AMPH/MI electron "
                        "probe microanalysis (EPMA) data using a deterministic pairing scheme "
                        "and quadrature error propagation from measured %ERR values.",
                        style={"fontFamily": FONT_BODY, "fontSize": "1.05rem",
                               "fontWeight": "300", "color": C["text_muted"],
                               "lineHeight": "1.72", "marginTop": "0.5rem"},
                    ),
                    html.P(
                        "D_F values are treated as minimum estimates throughout — "
                        "MI fluorine is always assigned below-detection status, "
                        "with F CDL₉ₙ used as the melt denominator. "
                        "Below-detection pairs are visually distinguished with open symbols "
                        "on all scatter plots.",
                        style={"fontFamily": FONT_BODY, "fontSize": "1.05rem",
                               "fontWeight": "300", "color": C["text_muted"],
                               "lineHeight": "1.72"},
                    ),
                ], lg=7),
                dbc.Col([
                    html.Div(
                        style={
                            "background":   C["surface"],
                            "border":       f"1px solid {C['border']}",
                            "borderRadius": "6px",
                            "padding":      "1.6rem",
                            "marginTop":    "0.5rem",
                        },
                        children=[
                            kv_row("Reference System", "Shiveluch Volcano, Kamchatka"),
                            kv_row("Mineral Phase",    "Amphibole (hornblende)"),
                            kv_row("Halogens",         "Cl, F (wt%)"),
                            kv_row("Thermobarometry",  "Molina et al. 2021 · Putirka 2016"),
                            kv_row("D_F Treatment",    "Minimum estimate (CDL₉ₙ denominator)"),
                            kv_row("Institution",      "WashU EEPS · Krawczynski Group"),
                        ],
                    )
                ], lg=5),
            ], className="mb-5"),
        ])
    ]),

    html.Div(
        style={
            "background":  C["surface"],
            "borderTop":   f"1px solid {C['border']}",
            "padding":     "1.6rem 2rem",
            "textAlign":   "center",
        },
        children=[
            html.Span(
                "Tomás Salazar  ·  Washington University in St. Louis  ·  "
                "Experimental Studies of Planetary Materials Group",
                style={"fontFamily": FONT_MONO, "fontSize": "0.65rem",
                       "letterSpacing": "0.09em", "color": C["text_dim"],
                       "textTransform": "uppercase"},
            )
        ],
    ),
])

# ─────────────────────────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    navbar,
    html.Div(id="page-content"),
])

app.validation_layout = html.Div([
    dcc.Location(id="url", refresh=False),
    navbar,
    html.Div(id="page-content"),
    home_layout,
    create_partition_analysis_layout(),
    create_bulk_analysis_layout(),
    create_info_layout(),
    create_shiveluch_layout(),
    # create_amphibole_zoning_layout(),
])

# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("page-content", "children"),
    Input("url",  "pathname"),
)
def display_page(pathname):
    if pathname == "/analysis":
        return create_partition_analysis_layout()
    elif pathname == "/bulk":
        return create_bulk_analysis_layout()
    elif pathname == "/info":
        return create_info_layout()
    elif pathname == "/shiveluch":
        return create_shiveluch_layout()
    # elif pathname == "/amphibole_zoning":
    #     return create_amphibole_zoning_layout()
    else:
        return home_layout

# ─────────────────────────────────────────────────────────────────────────────
create_bulk_analysis_callbacks(app)
create_partition_analysis_callbacks(app)
# create_amphibole_zoning_callbacks(app)

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8060)

    import os
print("Assets folder contents:", os.listdir("assisstantfiles"))