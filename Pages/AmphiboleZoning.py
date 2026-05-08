# Pages/amphibole_zoning.py
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import numpy as np

def create_amphibole_zoning_layout():
    """Create the amphibole crystal growth simulator page"""
    
    layout = dbc.Container(fluid=True, children=[
        dbc.Row([
            dbc.Col([
                html.H2("Amphibole Crystal Growth Simulator", className="text-center mb-3"),
                html.P(
                    "Watch an amphibole crystal grow in real-time and see how changing magmatic conditions "
                    "affect compositional zoning patterns.",
                    className="text-center text-muted mb-4"
                ),
                
                # Main visualization row
                dbc.Row([
                    # Left column - Crystal visualization
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H5("Crystal Cross-Section", className="d-inline"),
                                dbc.Badge("Ready", color="secondary", className="ms-2", id="growth-badge")
                            ]),
                            dbc.CardBody([
                                dcc.Graph(
                                    id='crystal-heatmap',
                                    config={'displayModeBar': False},
                                    style={'height': '500px'}
                                )
                            ])
                        ])
                    ], md=6),
                    
                    # Right column - Profile plot
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Core-to-Rim Profile")),
                            dbc.CardBody([
                                dcc.Graph(
                                    id='profile-plot',
                                    config={'displayModeBar': False},
                                    style={'height': '500px'}
                                )
                            ])
                        ])
                    ], md=6),
                ], className="mb-4"),
                
                # Control Panel
                dbc.Card([
                    dbc.CardHeader(html.H5("🎮 Growth Controls")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button("▶ Play", id="play-button", color="success", n_clicks=0),
                                    dbc.Button("⏸ Pause", id="pause-button", color="warning", n_clicks=0),
                                    dbc.Button("🔄 Reset", id="reset-button", color="danger", n_clicks=0),
                                ], className="w-100"),
                            ], md=4),
                            dbc.Col([
                                html.Label("Growth Speed:", className="fw-bold"),
                                dcc.Slider(
                                    id='growth-speed-slider',
                                    min=100,
                                    max=2000,
                                    step=100,
                                    value=500,
                                    marks={100: 'Fast', 1000: 'Medium', 2000: 'Slow'},
                                    tooltip={"placement": "bottom", "always_visible": False}
                                )
                            ], md=4),
                            dbc.Col([
                                html.Label("Zones:", className="fw-bold"),
                                html.H4(id="zone-counter", children="0 / 50", className="text-center text-primary")
                            ], md=4)
                        ]),
                    ])
                ], className="mb-4"),
                
                # Magmatic Parameter Controls
                dbc.Card([
                    dbc.CardHeader(html.H5("🌋 Magmatic Conditions")),
                    dbc.CardBody([
                        # Temperature
                        dbc.Row([
                            dbc.Col([
                                html.Label("Temperature (°C):", className="fw-bold"),
                                dcc.Slider(
                                    id='temperature-slider',
                                    min=900,
                                    max=1200,
                                    step=10,
                                    value=1050,
                                    marks={900: '900°C', 1050: '1050°C', 1200: '1200°C'},
                                    tooltip={"placement": "bottom", "always_visible": True}
                                ),
                                html.Small("Higher T → Higher Mg#", className="text-muted")
                            ], md=6),
                            dbc.Col([
                                html.Label("Pressure (GPa):", className="fw-bold"),
                                dcc.Slider(
                                    id='pressure-slider',
                                    min=0.2,
                                    max=1.5,
                                    step=0.1,
                                    value=0.7,
                                    marks={0.2: '0.2', 0.7: '0.7', 1.5: '1.5'},
                                    tooltip={"placement": "bottom", "always_visible": True}
                                ),
                                html.Small("Higher P → Higher Al content", className="text-muted")
                            ], md=6),
                        ], className="mb-3"),
                        
                        # H2O and Mafic Input
                        dbc.Row([
                            dbc.Col([
                                html.Label("H₂O Content (wt%):", className="fw-bold"),
                                dcc.Slider(
                                    id='h2o-slider',
                                    min=2,
                                    max=12,
                                    step=0.5,
                                    value=6,
                                    marks={2: '2%', 6: '6%', 12: '12%'},
                                    tooltip={"placement": "bottom", "always_visible": True}
                                ),
                                html.Small("Affects amphibole stability", className="text-muted")
                            ], md=6),
                            dbc.Col([
                                html.Label("Mafic Recharge (%):", className="fw-bold"),
                                dcc.Slider(
                                    id='mafic-recharge-slider',
                                    min=0,
                                    max=100,
                                    step=5,
                                    value=0,
                                    marks={0: '0%', 50: '50%', 100: '100%'},
                                    tooltip={"placement": "bottom", "always_visible": True}
                                ),
                                html.Small("Fresh mafic magma input → Higher Mg#", className="text-muted")
                            ], md=6),
                        ]),
                    ])
                ], className="mb-4"),
                
                # Preset Scenarios
                dbc.Card([
                    dbc.CardHeader(html.H5("📚 Preset Scenarios")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Button("Steady Cooling", id="scenario-steady", color="info", className="w-100 mb-2"),
                                html.Small("Normal zoning pattern", className="d-block text-center text-muted")
                            ], md=3),
                            dbc.Col([
                                dbc.Button("Magma Recharge", id="scenario-recharge", color="info", className="w-100 mb-2"),
                                html.Small("Reverse zoning event", className="d-block text-center text-muted")
                            ], md=3),
                            dbc.Col([
                                dbc.Button("Oscillatory", id="scenario-oscillatory", color="info", className="w-100 mb-2"),
                                html.Small("Cyclic variations", className="d-block text-center text-muted")
                            ], md=3),
                            dbc.Col([
                                dbc.Button("Complex History", id="scenario-complex", color="info", className="w-100 mb-2"),
                                html.Small("Multiple events", className="d-block text-center text-muted")
                            ], md=3),
                            dbc.Col([
                                dbc.Button("Shiveluch Typical", id="scenario-shiveluch", color="info", className="w-100 mb-2"),
                                html.Small("Conditions at Shiveluch Volcano", className="d-block text-center text-muted")
                            ], md=3),
                        ])
                    ])
                ], className="mb-4"),
                
                # Info panel
                dbc.Card([
                    dbc.CardBody([
                        html.H6("💡 How to Use:", className="card-title"),
                        html.Ul([
                            html.Li("Press PLAY to start crystal growth"),
                            html.Li("Adjust sliders in real-time to change magmatic conditions"),
                            html.Li("Watch how the crystal records changing conditions as colored zones"),
                            html.Li("Try preset scenarios or create your own patterns"),
                            html.Li("The color represents Mg# (magnesium number) - warmer colors = more mafic"),
                        ]),
                        html.Hr(),
                        html.H6("🔬 Shiveluch Context:", className="card-title mt-3"),
                        html.P([
                            "This simulator is based on amphibole crystallization conditions at Shiveluch Volcanic Complex:",
                            html.Br(),
                            html.Strong("• Temperature: "), "1062 ± 48°C",
                            html.Br(),
                            html.Strong("• H₂O: "), "8-10 wt% (avg. 4 wt%)",
                            html.Br(),
                            html.Strong("• Amphibole Mg#: "), "56-82",
                            html.Br(),
                            html.Strong("• Crystallization depth: "), "23.6-28.8 km"
                        ], className="text-muted small")
                    ])
                ], color="light"),
                
                # Hidden stores for state management
                dcc.Store(id='crystal-data-store', data={'zones': [], 'is_growing': False}),
                dcc.Interval(id='growth-interval', interval=500, disabled=True, n_intervals=0),
                
            ], width=12, lg=11, xl=10, className="mx-auto")
        ])
    ])
    
    return layout


def calculate_mg_number(temperature, pressure, h2o, mafic_recharge):
    """
    Calculate Mg# based on magmatic parameters
    Simplified model for demonstration
    """
    # Base Mg# from temperature (positive correlation)
    base_mg = 50 + (temperature - 1050) * 0.15
    
    # Pressure effect (slight negative correlation)
    pressure_effect = -2 * (pressure - 0.7)
    
    # H2O effect (slight negative correlation with Mg#)
    h2o_effect = -1 * (h2o - 6)
    
    # Mafic recharge strongly increases Mg#
    recharge_effect = mafic_recharge * 0.3
    
    mg_number = base_mg + pressure_effect + h2o_effect + recharge_effect
    
    # Clamp between realistic values
    return np.clip(mg_number, 40, 85)


def calculate_al_content(pressure, temperature):
    """Calculate Al2O3 content (pressure barometer)"""
    base_al = 8 + (pressure - 0.7) * 5
    temp_effect = -(temperature - 1050) * 0.01
    return np.clip(base_al + temp_effect, 5, 15)
       
def create_amphibole_zoning_callbacks(app):
    """Create callbacks for the crystal growth simulator"""
    
    # Play button - start growth
    @app.callback(
        [Output('growth-interval', 'disabled'),
         Output('growth-badge', 'children'),
         Output('growth-badge', 'color'),
         Output('crystal-data-store', 'data', allow_duplicate=True)],
        Input('play-button', 'n_clicks'),
        State('crystal-data-store', 'data'),
        prevent_initial_call=True
    )
    def start_growth(n_clicks, data):
        if n_clicks and n_clicks > 0:
            data['is_growing'] = True
            return False, "Growing", "success", data
        return True, "Paused", "warning", data
    
    # Pause button
    @app.callback(
        [Output('growth-interval', 'disabled', allow_duplicate=True),
         Output('growth-badge', 'children', allow_duplicate=True),
         Output('growth-badge', 'color', allow_duplicate=True),
         Output('crystal-data-store', 'data', allow_duplicate=True)],
        Input('pause-button', 'n_clicks'),
        State('crystal-data-store', 'data'),
        prevent_initial_call=True
    )
    def pause_growth(n_clicks, data):
        if n_clicks and n_clicks > 0:
            data['is_growing'] = False
            return True, "Paused", "warning", data
        return True, "Paused", "warning", data
    
    # Reset button
    @app.callback(
        [Output('crystal-data-store', 'data', allow_duplicate=True),
         Output('growth-interval', 'disabled', allow_duplicate=True),
         Output('growth-badge', 'children', allow_duplicate=True),
         Output('growth-badge', 'color', allow_duplicate=True),
         Output('growth-interval', 'n_intervals')],
        Input('reset-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_crystal(n_clicks):
        if n_clicks and n_clicks > 0:
            return {'zones': [], 'is_growing': False}, True, "Reset", "secondary", 0
        return {'zones': [], 'is_growing': False}, True, "Reset", "secondary", 0
    
    # Update growth interval speed
    @app.callback(
        Output('growth-interval', 'interval'),
        Input('growth-speed-slider', 'value')
    )
    def update_speed(speed):
        return speed
    
    # Main growth callback - adds new zone
    @app.callback(
        Output('crystal-data-store', 'data', allow_duplicate=True),
        Input('growth-interval', 'n_intervals'),
        [State('crystal-data-store', 'data'),
         State('temperature-slider', 'value'),
         State('pressure-slider', 'value'),
         State('h2o-slider', 'value'),
         State('mafic-recharge-slider', 'value')],
        prevent_initial_call=True
    )
    def grow_crystal(n_intervals, data, temp, pressure, h2o, mafic):
        # Check if we should be growing
        if not data.get('is_growing', False):
            return data
        
        # Initialize zones if needed
        if 'zones' not in data:
            data['zones'] = []
        
        # Check if we've hit the max
        if len(data['zones']) >= 50:
            data['is_growing'] = False
            return data
        
        # Calculate composition for this zone
        mg_number = calculate_mg_number(temp, pressure, h2o, mafic)
        al_content = calculate_al_content(pressure, temp)
        
        # Add new zone
        zone = {
            'mg_number': float(mg_number),
            'al_content': float(al_content),
            'temperature': float(temp),
            'pressure': float(pressure),
            'h2o': float(h2o),
            'mafic_recharge': float(mafic)
        }
        
        data['zones'].append(zone)
        
        return data

    # Update visualizations - ONLY ONE DEFINITION
    @app.callback(
        [Output('crystal-heatmap', 'figure'),
         Output('profile-plot', 'figure'),
         Output('zone-counter', 'children')],
        Input('crystal-data-store', 'data')
    )
    def update_visualizations(data):
        zones = data.get('zones', [])
        n_zones = len(zones)
        
        # Create crystal heatmap
        size = 200
        x = np.linspace(-1, 1, size)
        y = np.linspace(-1, 1, size)
        X, Y = np.meshgrid(x, y)
        
        # Initialize Z with NaN (transparent outside crystal)
        Z = np.full_like(X, np.nan)
        
        # Define amphibole parallelogram shape (60°/120° cleavage)
        crystal_length = 0.8
        crystal_width = 0.4
        angle = np.radians(60)
        offset = crystal_width * np.cos(angle)
        
        # For each pixel, check if it's inside the parallelogram AND calculate distance from edges
        inside_crystal = np.zeros_like(X, dtype=bool)
        distance_from_edge = np.full_like(X, np.inf)  # Distance from nearest edge
        
        for i in range(size):
            for j in range(size):
                px, py = X[i, j], Y[i, j]
                
                # Check if point is inside parallelogram
                if (py >= -crystal_width/2 and py <= crystal_width/2 and
                    px >= -crystal_length/2 + (py + crystal_width/2) * np.cos(angle) and
                    px <= crystal_length/2 + (py + crystal_width/2) * np.cos(angle)):
                    
                    inside_crystal[i, j] = True
                    
                    # Calculate distance from each edge (perpendicular distance)
                    # Bottom edge: distance from y = -width/2
                    dist_bottom = py - (-crystal_width/2)
                    
                    # Top edge: distance from y = width/2
                    dist_top = crystal_width/2 - py
                    
                    # Left edge: x = -length/2 + (y + width/2) * cos(60)
                    left_edge_x = -crystal_length/2 + (py + crystal_width/2) * np.cos(angle)
                    dist_left = (px - left_edge_x) / np.sin(angle)  # perpendicular distance
                    
                    # Right edge: x = length/2 + (y + width/2) * cos(60)
                    right_edge_x = crystal_length/2 + (py + crystal_width/2) * np.cos(angle)
                    dist_right = (right_edge_x - px) / np.sin(angle)  # perpendicular distance
                    
                    # Minimum distance to any edge
                    distance_from_edge[i, j] = min(dist_bottom, dist_top, dist_left, dist_right)
        
        # Find maximum distance from edge (at the center)
        center_distances = distance_from_edge[inside_crystal]
        max_distance = np.max(center_distances) if len(center_distances) > 0 else 1.0
        
        # Normalize distances (0 at edge, 1 at center)
        normalized_distance = distance_from_edge / max_distance
        
        if n_zones == 0:
            # Show empty crystal with base composition
            Z[inside_crystal] = 60  # Base Mg#
        else:
            # Assign Mg# values to zones based on normalized distance from edge
            for i, zone in enumerate(zones):
                # Zone i extends from outer_fraction to inner_fraction
                # Zone 0 (core) is at the center (highest normalized distance)
                # Zone n-1 (rim) is at the edge (lowest normalized distance)
                
                outer_fraction = (n_zones - i - 1) / n_zones  # Fraction from edge (0 = edge, 1 = center)
                inner_fraction = (n_zones - i) / n_zones
                
                # Create mask for this zone
                mask = inside_crystal & (normalized_distance >= outer_fraction) & (normalized_distance < inner_fraction)
                Z[mask] = zone['mg_number']
        
        # Create crystal figure
        crystal_fig = go.Figure()
        
        crystal_fig.add_trace(go.Heatmap(
            x=x,
            y=y,
            z=Z,
            colorscale='RdGy',  # Red = high Mg#, Blue = low Mg#
            zmin=40,
            zmax=85,
            colorbar=dict(
                title=dict(text="Mg#", side='right'),
                x=1.15
            ),
            hovertemplate='Mg#: %{z:.1f}<extra></extra>',
            showscale=True
        ))
        
        # Add parallelogram outline (60°/120° cleavage angles)
        para_x = [
            -crystal_length/2,
            -crystal_length/2 + offset,
            crystal_length/2 + offset,
            crystal_length/2,
            -crystal_length/2
        ]
        para_y = [
            -crystal_width/2,
            crystal_width/2,
            crystal_width/2,
            -crystal_width/2,
            -crystal_width/2
        ]
        
        crystal_fig.add_trace(go.Scatter(
            x=para_x, y=para_y,
            mode='lines',
            line=dict(color='black', width=3),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add cleavage angle annotations
        crystal_fig.add_annotation(
            x=-crystal_length/2 - 0.15,
            y=0,
            text="60°",
            showarrow=False,
            font=dict(size=12, color='black')
        )
        
        crystal_fig.add_annotation(
            x=crystal_length/2 + offset + 0.15,
            y=0,
            text="120°",
            showarrow=False,
            font=dict(size=12, color='black')
        )
        
        # Add core marker
        crystal_fig.add_trace(go.Scatter(
            x=[0], y=[0],
            mode='markers+text',
            marker=dict(size=10, color='white', symbol='circle', 
                       line=dict(color='black', width=2)),
            text=['CORE'],
            textposition='top center',
            textfont=dict(size=10, color='black'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add rim label if crystal has grown
        if n_zones > 0:
            crystal_fig.add_trace(go.Scatter(
                x=[crystal_length/2 + 0.1], y=[0],
                mode='text',
                text=['RIM →'],
                textposition='middle right',
                textfont=dict(size=10, color='black'),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        crystal_fig.update_layout(
            title=f"Amphibole Crystal Cross-Section ({n_zones} growth zones)<br><sub>Characteristic 60°/120° cleavage - Uniform growth from all faces</sub>",
            xaxis=dict(
                showticklabels=False, 
                showgrid=False, 
                zeroline=False, 
                range=[-1.2, 1.4]
            ),
            yaxis=dict(
                showticklabels=False, 
                showgrid=False, 
                zeroline=False, 
                range=[-0.6, 0.6], 
                scaleanchor="x",
                scaleratio=1
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=120, t=70, b=20),
            height=500
        )
        
        # Create profile plot
        profile_fig = go.Figure()
        
        if n_zones > 0:
            distances = np.arange(n_zones)
            mg_values = [z['mg_number'] for z in zones]
            
            profile_fig.add_trace(go.Scatter(
                x=distances,
                y=mg_values,
                mode='lines+markers',
                line=dict(color='#FF6B35', width=3),
                marker=dict(
                    size=8, 
                    color=mg_values, 
                    colorscale='RdYlBu_r',
                    cmin=40, 
                    cmax=85, 
                    showscale=False,
                    line=dict(color='darkred', width=1)
                ),
                name='Mg#',
                fill='tozeroy',
                fillcolor='rgba(255, 107, 53, 0.2)',
                hovertemplate='Zone %{x}<br>Mg#: %{y:.1f}<extra></extra>'
            ))
            
            # Add markers for core and rim
            profile_fig.add_trace(go.Scatter(
                x=[0, n_zones-1],
                y=[mg_values[0], mg_values[-1]],
                mode='markers+text',
                marker=dict(size=12, color=['green', 'purple'], symbol='diamond'),
                text=['CORE', 'RIM'],
                textposition=['top center', 'top center'],
                showlegend=False,
                hoverinfo='skip'
            ))
            
        else:
            # Empty plot with instruction
            profile_fig.add_annotation(
                text="Press PLAY to start crystal growth",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color="gray")
            )
        
        profile_fig.update_layout(
            title="Core → Rim Composition Profile",
            xaxis=dict(
                title="Growth Zone Number (Core → Rim)", 
                showgrid=True, 
                gridcolor='lightgray'
            ),
            yaxis=dict(
                title="Mg# (Magnesium Number)", 
                showgrid=True, 
                gridcolor='lightgray', 
                range=[40, 85]
            ),
            plot_bgcolor='white',
            height=500,
            margin=dict(l=60, r=20, t=50, b=60)
        )
        
        # Zone counter with color coding
        counter_text = f"{n_zones} / 50"
        
        return crystal_fig, profile_fig, counter_text

    # Preset scenarios - SEPARATE CALLBACK, NOT NESTED
    @app.callback(
        [Output('temperature-slider', 'value'),
         Output('pressure-slider', 'value'),
         Output('h2o-slider', 'value'),
         Output('mafic-recharge-slider', 'value')],
        [Input('scenario-steady', 'n_clicks'),
         Input('scenario-recharge', 'n_clicks'),
         Input('scenario-oscillatory', 'n_clicks'),
         Input('scenario-complex', 'n_clicks'),
         Input('scenario-shiveluch', 'n_clicks')],
        prevent_initial_call=True
    )
    def load_scenario(steady, recharge, oscillatory, complex_scenario, shiveluch):
        ctx = callback_context
        if not ctx.triggered:
            return 1050, 0.7, 6, 0
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'scenario-steady':
            return 1050, 0.7, 6, 0
        elif button_id == 'scenario-recharge':
            return 1150, 0.7, 7, 60
        elif button_id == 'scenario-oscillatory':
            return 1000, 0.8, 5, 0
        elif button_id == 'scenario-complex':
            return 1080, 0.9, 8, 25
        elif button_id == 'scenario-shiveluch':
            return 1062, 0.8, 9, 20
        
        return 1050, 0.7, 6, 0        