import base64
import io
import pandas as pd  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
from dash import html, dcc, dash_table, Input, Output, State, callback  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import numpy as np

from assisstantfiles.partition import (
    run_monte_carlo_and_params,
    prepare_scatter_data,
    get_sheet_names,
    calculate_partition_statistics,
    validate_excel_structure,
    df_partition_params,
    df_partition_mc,
    ELEMENTS
)

def create_partition_analysis_layout():
    """Create the layout for partition analysis including upload, controls, plots, and tables."""
    return dbc.Container(fluid=True, children=[

        html.H2("Partition Coefficient Analysis", className="my-4 text-center"),

        # Upload Section
        dbc.Row([
            dbc.Col([
                html.H4("📁 Data Upload", className="mb-3"),
                dbc.Card(dbc.CardBody([
                    dcc.Upload(
                        id="upload-partition-data",
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
                    html.Div(id="partition-upload-status", className="mt-2"),
                    
                    # File requirements info
                    dbc.Collapse([
                        dbc.Alert([
                            html.H6("📋 File Requirements:", className="alert-heading"),
                            html.Ul([
                                html.Li("Excel file (.xlsx or .xls) with paired sheets"),
                                html.Li("Sheets named: 'SampleID XT' and 'SampleID MI'"),
                                html.Li("XT sheets: amphibole crystal data"),
                                html.Li("MI sheets: melt inclusion data"),
                                html.Li("Required columns: Cl, Cl AT%, F, F AT%, F CDL99"),
                                html.Li("Optional: SiO₂, MgO, FeO for scatter plots")
                            ], className="mb-0")
                        ], color="info")
                    ], id="file-requirements-collapse", is_open=False),
                    
                    dbc.Button(
                        "Show/Hide File Requirements", 
                        id="toggle-requirements",
                        color="outline-info", 
                        size="sm", 
                        className="mt-2"
                    )
                ]))
            ], width=12)
        ], className="mb-4"),

        # Persistent Stores
        dcc.Store(id="stored-partition-params"),
        dcc.Store(id="stored-partition-mc"),

        # Analysis Controls
        dbc.Row([
            dbc.Col([
                html.H4("⚙️ Analysis Controls", className="mb-3"),
                dbc.Card(dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Halogen Element:", className="fw-bold"),
                            dcc.Dropdown(
                                id="partition-element-dropdown",
                                options=[],
                                value=None,
                                clearable=False,
                                placeholder="Select element...",
                                style={"color": "black"}
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Plot Type:", className="fw-bold"),
                            dcc.Dropdown(
                                id="partition-plot-type",
                                options=[
                                    {"label": "📊 Boxplot Distribution", "value": "box"},
                                    {"label": "🔗 Scatter vs Mg#", "value": "scatter_mgno"},
                                    {"label": "🔗 Scatter vs SiO₂", "value": "scatter_sio2"},
                                    {"label": "📈 All Plots", "value": "all"}
                                ],
                                value="box",
                                clearable=False,
                                style={"color": "black"}
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Statistics View:", className="fw-bold"),
                            dcc.Dropdown(
                                id="partition-stats-toggle",
                                options=[
                                    {"label": "Show Summary Stats", "value": "show"},
                                    {"label": "Hide Summary Stats", "value": "hide"}
                                ],
                                value="show",
                                clearable=False,
                                style={"color": "black"}
                            )
                        ], width=4)
                    ])
                ]))
            ], width=12)
        ], className="mb-4"),

        # Results Section
        dbc.Row([
            dbc.Col([
                html.H4("📊 Results", className="mb-3"),
                dcc.Loading(
                    id="partition-results-loading",
                    children=html.Div(id="partition-results-content"),
                    type="circle",
                    color="#007bff"
                )
            ], width=12)
        ], className="mb-4"),

        # Statistics Summary
        dbc.Row([
            dbc.Col([
                html.Div(id="partition-statistics-section")
            ], width=12)
        ], className="mb-4"),

        # Data Tables Section
        dbc.Row([
            dbc.Col([
                html.H4("📋 Data Tables", className="mb-3"),
                dbc.Tabs([
                    dbc.Tab(
                        label="📊 Summary Statistics", 
                        tab_id="summary-tab",
                        children=html.Div(id="partition-data-summary", className="mt-3")
                    ),
                    dbc.Tab(
                        label="🔍 Raw Monte Carlo Data", 
                        tab_id="raw-tab",
                        children=html.Div(id="partition-data-table", className="mt-3")
                    ),
                    dbc.Tab(
                        label="📋 Sample Parameters", 
                        tab_id="params-tab",
                        children=html.Div(id="partition-params-table", className="mt-3")
                    )
                ], id="data-tabs", active_tab="summary-tab")
            ], width=12)
        ])
    ])

def create_partition_analysis_callbacks(app):
    """Register all callbacks for the partition analysis functionality."""

    # Toggle file requirements
    @app.callback(
        Output("file-requirements-collapse", "is_open"),
        Input("toggle-requirements", "n_clicks"),
        State("file-requirements-collapse", "is_open")
    )
    def toggle_file_requirements(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open

    # File upload and processing
    @app.callback(
        [
            Output("stored-partition-params", "data"),
            Output("stored-partition-mc", "data"),
            Output("partition-upload-status", "children"),
            Output("partition-element-dropdown", "options"),
            Output("partition-element-dropdown", "value")
        ],
        Input("upload-partition-data", "contents"),
        State("upload-partition-data", "filename"),
        prevent_initial_call=True
    )
    def load_partition_file(contents, filename):
        if not contents:
            return None, None, html.Div("No file uploaded", className="text-muted"), [], None

        try:
            # Parse the uploaded file
            header, b64 = contents.split(",", 1)
            data = base64.b64decode(b64)
            file_like = io.BytesIO(data)

            if not filename or not filename.lower().endswith((".xls", ".xlsx")):
                raise ValueError("Please upload an Excel (.xlsx, .xls) file.")

            # Validate file structure
            is_valid, message, xt_sheets, mi_sheets = validate_excel_structure(file_like)
            
            if not is_valid:
                alert = dbc.Alert([
                    html.H6("❌ File Structure Error:", className="alert-heading"),
                    html.P(message, className="mb-0")
                ], color="danger")
                return None, None, alert, [], None
            
            # Reset file pointer and run analysis
            file_like.seek(0)
            df_mc, df_params = run_monte_carlo_and_params(file_like, xt_sheets, mi_sheets)
            
            # Update global variables
            import assisstantfiles.partition as partition
            partition.df_partition_params = df_params.copy()
            partition.df_partition_mc = df_mc.copy()

            # Create element options for halogens only
            available_halogens = []
            if not df_mc.empty:
                available_halogens = df_mc['Halogen'].unique().tolist()
            
            options = [{"label": f"{hal} (Partition Coefficients)", "value": hal} for hal in available_halogens]
            default_val = "Cl" if "Cl" in available_halogens else (available_halogens[0] if available_halogens else None)

            # Success message
            n_samples = len(df_params) if not df_params.empty else 0
            n_mc_points = len(df_mc) if not df_mc.empty else 0
            
            status = dbc.Alert([
                html.H6("✅ Upload Successful!", className="alert-heading"),
                html.P([
                    f"Processed {n_samples} samples from {filename}. ",
                    f"Generated {n_mc_points:,} Monte Carlo data points for partition analysis."
                ], className="mb-0")
            ], color="success")

            return df_params.to_dict("records"), df_mc.to_dict("records"), status, options, default_val

        except Exception as e:
            print(f"Error in load_partition_file: {str(e)}")
            alert = dbc.Alert([
                html.H6("❌ Processing Error:", className="alert-heading"),
                html.P(f"Error loading data: {str(e)}", className="mb-0")
            ], color="danger")
            return None, None, alert, [], None

    # Update plots and visualizations
    @app.callback(
        Output("partition-results-content", "children"),
        [
            Input("stored-partition-mc", "data"),
            Input("stored-partition-params", "data"),
            Input("partition-element-dropdown", "value"),
            Input("partition-plot-type", "value"),
        ],
        prevent_initial_call=True
    )
    def update_partition_plots(mc_data, param_data, element, plot_type):
        if not mc_data or not param_data or element is None:
            return dbc.Alert("Please upload data and select an element.", color="info")

        try:
            df_mc = pd.DataFrame(mc_data)
            df_params = pd.DataFrame(param_data)
            
            # Update global variables for scatter plot function
            import assisstantfiles.partition as partition
            partition.df_partition_params = df_params.copy()
            partition.df_partition_mc = df_mc.copy()
            
            plots = []

            # Boxplot for halogen partition coefficients
            if plot_type in ("box", "all"):
                df_halogen = df_mc[df_mc["Halogen"] == element]
                if not df_halogen.empty:
                    fig = px.box(
                        df_halogen, 
                        y="D", 
                        title=f"{element} Partition Coefficients Distribution",
                        labels={"D": f"D_{{{element}}} (Crystal/Melt)"},
                        color_discrete_sequence=["#1f77b4"]
                    )
                    fig.update_layout(
                        showlegend=False, 
                        height=450,
                        title_x=0.5,
                        yaxis_title=f"D_{{{element}}} (Partition Coefficient)"
                    )
                    plots.append(dcc.Graph(figure=fig, style={"margin-bottom": "20px"}))
                else:
                    plots.append(dbc.Alert(f"No {element} data available for boxplot", color="warning"))

            # Scatter vs Mg#
            if plot_type in ("scatter_mgno", "all") and "Mg#" in df_params.columns:
                try:
                    df_scatter = prepare_scatter_data(df_mc, element, "Mg#")
                    if not df_scatter.empty and "Element_To_Plot" in df_scatter.columns:
                        df_scatter_clean = df_scatter.dropna(subset=["Element_To_Plot", "D"])
                        if not df_scatter_clean.empty:
                            fig = px.scatter(
                                df_scatter_clean, 
                                x="Element_To_Plot", 
                                y="D", 
                                color="Element_Source",
                                title=f"{element} Partition Coefficients vs Mg#",
                                labels={
                                    "Element_To_Plot": "Mg# (Mg/(Mg+Fe) × 100)",
                                    "D": f"D_{{{element}}} (Crystal/Melt)"
                                },
                                color_discrete_map={"XT": "#1f77b4", "MI": "#ff7f0e"}
                            )
                            fig.update_layout(height=450, title_x=0.5)
                            plots.append(dcc.Graph(figure=fig, style={"margin-bottom": "20px"}))
                        else:
                            plots.append(dbc.Alert(f"No valid data for {element} vs Mg# scatter plot", color="warning"))
                    else:
                        plots.append(dbc.Alert(f"Mg# data not available for {element} scatter plot", color="warning"))
                except Exception as scatter_error:
                    print(f"Error creating Mg# scatter plot: {str(scatter_error)}")
                    plots.append(dbc.Alert(f"Error creating Mg# scatter plot: {str(scatter_error)}", color="danger"))

            # Scatter vs SiO2 - using individual Monte Carlo points with new data structure
            if plot_type in ("scatter_sio2", "all") and "SiO2" in df_params.columns:
                try:
                    # Create scatter data using raw Monte Carlo points
                    df_scatter = df_mc[df_mc["Halogen"] == element].copy()
                    
                    if not df_scatter.empty:
                        # Add SiO2 values for each point based on sample
                        sio2_values = []
                        for _, row in df_scatter.iterrows():
                            sample = row['SAMPLE']
                            # Use the sample's SiO2 median value for all points from that sample
                            sample_sio2 = df_params[df_params['SAMPLE'] == sample]['SiO2'].iloc[0] if not df_params[df_params['SAMPLE'] == sample].empty else np.nan
                            sio2_values.append(sample_sio2)
                        
                        df_scatter['SiO2_Value'] = sio2_values
                        df_scatter_clean = df_scatter.dropna(subset=["SiO2_Value", "D"])
                        
                        if not df_scatter_clean.empty:
                            fig = px.scatter(
                                df_scatter_clean, 
                                x="SiO2_Value", 
                                y="D", 
                                color="SAMPLE",
                                title=f"{element} Partition Coefficients vs SiO₂",
                                labels={
                                    "SiO2_Value": "SiO₂ (wt%)",
                                    "D": f"D_{{{element}}} (Crystal/Melt)"
                                },
                                hover_data=["SAMPLE", "MC_Iteration"]
                            )
                            fig.update_layout(height=450, title_x=0.5)
                            plots.append(dcc.Graph(figure=fig, style={"margin-bottom": "20px"}))
                        else:
                            plots.append(dbc.Alert(f"No valid data for {element} vs SiO₂ scatter plot", color="warning"))
                    else:
                        plots.append(dbc.Alert(f"SiO₂ data not available for {element} scatter plot", color="warning"))
                except Exception as scatter_error:
                    print(f"Error creating SiO2 scatter plot: {str(scatter_error)}")
                    plots.append(dbc.Alert(f"Error creating SiO₂ scatter plot: {str(scatter_error)}", color="danger"))

            if not plots:
                return dbc.Alert("No plots could be generated with the current selection.", color="warning")

            return html.Div(plots)

        except Exception as e:
            print(f"Error in update_partition_plots: {str(e)}")
            return dbc.Alert(f"Error generating plots: {str(e)}", color="danger")

    # Update statistics section
    @app.callback(
        Output("partition-statistics-section", "children"),
        [
            Input("stored-partition-mc", "data"),
            Input("partition-element-dropdown", "value"),
            Input("partition-stats-toggle", "value")
        ],
        prevent_initial_call=True
    )
    def update_statistics_section(mc_data, element, stats_toggle):
        if stats_toggle == "hide" or not mc_data or not element:
            return html.Div()
        
        try:
            df_mc = pd.DataFrame(mc_data)
            stats_df = calculate_partition_statistics(df_mc, element)
            
            if stats_df.empty:
                return dbc.Alert(f"No statistics available for {element}", color="info")
            
            return html.Div([
                html.H5(f"📊 {element} Partition Coefficient Statistics", className="mb-3"),
                dbc.Card(dbc.CardBody([
                    dash_table.DataTable(
                        data=stats_df.to_dict("records"),
                        columns=[
                            {"name": col, "id": col, "type": "numeric", "format": {"specifier": ".4f"}} 
                            if col != "SAMPLE" else {"name": col, "id": col}
                            for col in stats_df.columns
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "left", "padding": "10px"},
                        style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "rgb(248, 248, 248)"
                            }
                        ]
                    )
                ]))
            ])
            
        except Exception as e:
            print(f"Error in update_statistics_section: {str(e)}")
            return dbc.Alert(f"Error generating statistics: {str(e)}", color="danger")

    # Update summary table
    @app.callback(
        Output("partition-data-summary", "children"),
        Input("stored-partition-mc", "data"),
        prevent_initial_call=True
    )
    def update_summary(mc_data):
        if not mc_data:
            return "No data loaded"

        try:
            df_mc = pd.DataFrame(mc_data)
            
            # Create summary statistics for numeric columns
            numeric_cols = df_mc.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary = df_mc[numeric_cols].describe().transpose().reset_index()
                summary = summary.round(4)
                
                return dash_table.DataTable(
                    data=summary.to_dict("records"),
                    columns=[
                        {"name": i, "id": i, "type": "numeric", "format": {"specifier": ".4f"}} 
                        if i != "index" else {"name": "Variable", "id": i} 
                        for i in summary.columns
                    ],
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "left", "padding": "10px"},
                    style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                    style_data_conditional=[
                        {
                            "if": {"row_index": "odd"},
                            "backgroundColor": "rgb(248, 248, 248)"
                        }
                    ],
                    page_size=10,
                    export_format="xlsx",
                    export_headers="display"
                )
            else:
                return dbc.Alert("No numeric data available for summary", color="info")
                
        except Exception as e:
            print(f"Error in update_summary: {str(e)}")
            return dbc.Alert(f"Error generating summary: {str(e)}", color="danger")

    # Update raw data table
    @app.callback(
        Output("partition-data-table", "children"),
        Input("stored-partition-mc", "data"),
        prevent_initial_call=True
    )
    def update_table(mc_data):
        if not mc_data:
            return "No data to display"

        try:
            df_mc = pd.DataFrame(mc_data)
            
            # Round numeric columns for better display
            numeric_cols = df_mc.select_dtypes(include=['number']).columns
            df_display = df_mc.copy()
            for col in numeric_cols:
                df_display[col] = df_display[col].round(4)
            
            return dash_table.DataTable(
                data=df_display.to_dict("records"),
                columns=[
                    {"name": i, "id": i, "type": "numeric", "format": {"specifier": ".4f"}} 
                    if i in numeric_cols else {"name": i, "id": i} 
                    for i in df_display.columns
                ],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "10px"},
                style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)"
                    }
                ],
                page_size=20,
                filter_action="native",
                sort_action="native",
                export_format="xlsx",
                export_headers="display"
            )
            
        except Exception as e:
            print(f"Error in update_table: {str(e)}")
            return dbc.Alert(f"Error displaying data: {str(e)}", color="danger")

    # Update parameters table
    @app.callback(
        Output("partition-params-table", "children"),
        Input("stored-partition-params", "data"),
        prevent_initial_call=True
    )
    def update_params_table(param_data):
        if not param_data:
            return "No parameter data to display"

        try:
            df_params = pd.DataFrame(param_data)
            
            # Round numeric columns for better display
            numeric_cols = df_params.select_dtypes(include=['number']).columns
            df_display = df_params.copy()
            for col in numeric_cols:
                df_display[col] = df_display[col].round(4)
            
            return dash_table.DataTable(
                data=df_display.to_dict("records"),
                columns=[
                    {"name": i, "id": i, "type": "numeric", "format": {"specifier": ".4f"}} 
                    if i in numeric_cols else {"name": i, "id": i} 
                    for i in df_display.columns
                ],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "10px"},
                style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)"
                    }
                ],
                page_size=15,
                filter_action="native",
                sort_action="native",
                export_format="xlsx",
                export_headers="display"
            )
            
        except Exception as e:
            print(f"Error in update_params_table: {str(e)}")
            return dbc.Alert(f"Error displaying parameter data: {str(e)}", color="danger")