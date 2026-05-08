import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import pandas as pd


from assisstantfiles.plotting_utils import create_tas_figure, get_mg_number_animation

def create_bulk_analysis_layout():
    """
    Creates and returns the layout for the bulk analysis page.
    This function can be imported and called from your main app file.
    """
    
    bulk_analysis_layout = dbc.Container(fluid=True, children=[
        html.H2("Bulk Chemistry Analysis", className="my-4 text-center"),
        
        # File Upload Section
        dbc.Row([
            dbc.Col([
                html.H4("📁 Data Upload", className="mb-3"),
                dcc.Upload(
                    id='upload-bulk-chemistry-file',
                    children=html.Div([
                        'Drag and Drop or ', 
                        html.A('Select Bulk EPMA Chemistry File')
                    ]),
                    style={
                        'width': '100%', 'height': '80px', 'lineHeight': '80px',
                        'borderWidth': '2px', 'borderStyle': 'dashed', 
                        'borderRadius': '8px', 'textAlign': 'center', 
                        'margin': '10px 0', 'borderColor': '#007bff',
                        'backgroundColor': '#f8f9fa'
                    },
                    multiple=False
                ),
                html.Div(id='bulk-upload-status', className="mt-2")
            ], width=12)
        ], className="mb-4"),
        
        # Store for bulk chemistry data
        dcc.Store(id='stored-bulk-chemistry-data'),
        
        # Analysis Controls Section
        dbc.Row([
            dbc.Col([
                html.H4("⚙️ Analysis Controls", className="mb-3"),
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Analysis Type:", className="fw-bold"),
                                dcc.Dropdown(
                                    id='bulk-analysis-type',
                                    options=[
                                        {'label': 'TAS Diagram (Total Alkali vs Silica)', 'value': 'tas'},
                                        {'label': 'Halogen Evolution Analysis', 'value': 'halogen_evolution'},
                                        {'label': 'Both Analyses', 'value': 'both'}
                                    ],
                                    value='tas',
                                    clearable=False,
                                    style={'color': 'black'}
                                )
                            ], width=6),
                            
                            dbc.Col([
                                html.Label("Filter by Mg# Range:", className="fw-bold"),
                                dcc.RangeSlider(
                                    id='mg-number-filter',
                                    min=0, max=100, step=1, 
                                    value=[40, 90],
                                    marks={i: f"{i}" for i in range(0, 101, 20)},
                                    tooltip={"placement": "bottom", "always_visible": True}
                                )
                            ], width=6)
                        ]),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Label("Minimum SiO₂ (wt%):", className="fw-bold mt-3"),
                                dcc.Slider(
                                    id='sio2-filter',
                                    min=35, max=80, step=1,
                                    value=45,
                                    marks={i: f"{i}" for i in range(35, 81, 10)},
                                    tooltip={"placement": "bottom", "always_visible": True}
                                )
                            ], width=6),
                            
                            dbc.Col([
                                html.Label("Color Scheme:", className="fw-bold mt-3"),
                                dcc.Dropdown(
                                    id='color-scheme-bulk',
                                    options=[
                                        {'label': 'Viridis', 'value': 'Viridis'},
                                        {'label': 'Plasma', 'value': 'Plasma'},
                                        {'label': 'Inferno', 'value': 'Inferno'},
                                        {'label': 'Magma', 'value': 'magma'},
                                        {'label': 'Cividis', 'value': 'cividis'}
                                    ],
                                    value='Viridis',
                                    clearable=False,
                                    style={'color': 'black'}
                                )
                            ], width=6)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4"),
        
        # Results Section
        dbc.Row([
            dbc.Col([
                html.H4("📊 Analysis Results", className="mb-3"),
                dcc.Loading(
                    id='bulk-analysis-loading',
                    children=[
                        html.Div(id='bulk-analysis-content')
                    ],
                    type="circle"
                )
            ], width=12)
        ], className="mb-4"),
        
        # Data Summary Section
        dbc.Row([
            dbc.Col([
                html.H4("📋 Data Summary", className="mb-3"),
                dbc.Card([
                    dbc.CardBody([
                        html.Div(id='bulk-data-summary')
                    ])
                ])
            ], width=12)
        ], className="mb-4"),
        
        # Data Table Section
        dbc.Row([
            dbc.Col([
                html.H4("🔍 Raw Data View", className="mb-3"),
                html.Div(id='bulk-data-table')
            ], width=12)
        ])
    ])
    
    return bulk_analysis_layout

def create_bulk_analysis_callbacks(app):
    """
    Creates all the callbacks for the bulk analysis page.
    Call this function from your main app file after creating the app.
    """
    from dash.dependencies import Input, Output, State
    from dash import dash_table
    import plotly.graph_objects as go
    import base64
    import io
    
    # You'll need to import your plotting functions here
    # from your_plotting_module import create_tas_figure, get_mg_number_animation
    
    @app.callback(
        [Output('stored-bulk-chemistry-data', 'data'),
         Output('bulk-upload-status', 'children')],
        Input('upload-bulk-chemistry-file', 'contents'),
        State('upload-bulk-chemistry-file', 'filename')
    )
    def update_bulk_data(contents, filename):
        if contents is None:
            return None, html.Div("No file uploaded", className="text-muted")
        
        try:
            # Parse the uploaded file
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            
            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = pd.read_excel(io.BytesIO(decoded))
            elif filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            else:
                return None, dbc.Alert("Please upload an Excel (.xlsx, .xls) or CSV file", color="danger")
            
            # Basic data validation
            required_columns = ['SiO2', 'Al2O3', 'MgO', 'FeO', 'Na2O', 'K2O']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return None, dbc.Alert(
                    f"Missing required columns: {', '.join(missing_columns)}", 
                    color="warning"
                )
            
            # Store data and return success message
            data_dict = df.to_dict('records')
            success_msg = dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"Successfully loaded {len(df)} samples from {filename}"
            ], color="success")
            
            return data_dict, success_msg
            
        except Exception as e:
            error_msg = dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error processing file: {str(e)}"
            ], color="danger")
            return None, error_msg
    
    @app.callback(
        Output('bulk-analysis-content', 'children'),
        [Input('stored-bulk-chemistry-data', 'data'),
         Input('bulk-analysis-type', 'value'),
         Input('mg-number-filter', 'value'),
         Input('sio2-filter', 'value'),
         Input('color-scheme-bulk', 'value')]
    )
    def update_bulk_analysis(data, analysis_type, mg_range, sio2_min, color_scheme):
        if not data:
            return dbc.Alert("Please upload bulk chemistry data to begin analysis.", color="info")
        
        try:
            df = pd.DataFrame(data)
            
            # Apply filters
            if 'MgO' in df.columns and 'FeO' in df.columns:
                df['Mg#'] = 100 * df['MgO'] / (df['MgO'] + df['FeO'])
                df = df[(df['Mg#'] >= mg_range[0]) & (df['Mg#'] <= mg_range[1])]
            
            if 'SiO2' in df.columns:
                df = df[df['SiO2'] >= sio2_min]
            
            if df.empty:
                return dbc.Alert("No data remains after filtering. Please adjust filter criteria.", color="warning")
            
            graphs = []
            
            if analysis_type in ['tas', 'both']:
                # Create TAS diagram
                try:
                    tas_fig = create_tas_figure(df)  # Uncomment when function is available
                    
                    graphs.append(
                        html.Div([
                            html.H5("TAS Classification Diagram"),
                            dcc.Graph(figure=tas_fig)
                        ], className="mb-4")
                    )
                except Exception as e:
                    graphs.append(dbc.Alert(f"Error creating TAS diagram: {str(e)}", color="warning"))
            
            if analysis_type in ['halogen_evolution', 'both']:
                # Create halogen evolution analysis
                try:
                    halogen_fig = get_mg_number_animation(df)  # Uncomment when function is available
                
                    graphs.append(
                        html.Div([
                            html.H5("Halogen Evolution by Crystallization Stage"),
                            dcc.Graph(figure=halogen_fig)
                        ], className="mb-4")
                    )
                except Exception as e:
                    graphs.append(dbc.Alert(f"Error creating halogen evolution plot: {str(e)}", color="warning"))
            
            return html.Div(graphs)
            
        except Exception as e:
            return dbc.Alert(f"Error in analysis: {str(e)}", color="danger")
    
    @app.callback(
        Output('bulk-data-summary', 'children'),
        Input('stored-bulk-chemistry-data', 'data')
    )
    def update_data_summary(data):
        if not data:
            return "No data loaded"
        
        df = pd.DataFrame(data)
        
        summary_stats = []
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
        
        for col in numeric_columns[:8]:  # Show stats for first 8 numeric columns
            if col in df.columns:
                stats = df[col].describe()
                summary_stats.append(
                    dbc.Col([
                        html.H6(col, className="fw-bold"),
                        html.P(f"Mean: {stats['mean']:.2f}", className="mb-1 small"),
                        html.P(f"Range: {stats['min']:.2f} - {stats['max']:.2f}", className="mb-1 small"),
                        html.P(f"Std: {stats['std']:.2f}", className="mb-0 small")
                    ], width=3)
                )
        
        summary_content = [
            html.H6(f"Dataset contains {len(df)} samples with {len(df.columns)} variables"),
            dbc.Row(summary_stats, className="mt-3")
        ]
        
        return summary_content
    
    @app.callback(
        Output('bulk-data-table', 'children'),
        Input('stored-bulk-chemistry-data', 'data')
    )
    def update_data_table(data):
        if not data:
            return "No data to display"
        
        df = pd.DataFrame(data)
        
        return dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{"name": i, "id": i} for i in df.columns],
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left', 'padding': '8px', 
                'font_family': 'Arial', 'font_size': '12px',
                'whiteSpace': 'normal', 'height': 'auto'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)', 
                'fontWeight': 'bold'
            },
            page_size=15,
            filter_action="native",
            sort_action="native",
            export_format="xlsx"
        )