# Pages/shiveluch.py
import dash_bootstrap_components as dbc
from dash import dcc, html
import plotly.graph_objects as go

def create_shiveluch_layout():
    """Create the Shiveluch volcanic complex analysis page with interactive map"""
    
    # Shiveluch coordinates
    shiveluch_lat = 56.653
    shiveluch_lon = 161.360
    
    # Create the map using scattermapbox
    fig = go.Figure()
    
    # Add Shiveluch marker
    fig.add_trace(go.Scattermapbox(
        lon=[shiveluch_lon],
        lat=[shiveluch_lat],
        text=['Shiveluch Volcanic Complex'],
        mode='markers+text',
        marker=dict(
            size=20,
            color='red',
            symbol='marker'
        ),
        textposition="top center",
        textfont=dict(size=12, color='darkred'),
        name='Shiveluch'
    ))
    
    # Update map layout
    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lon=shiveluch_lon, lat=shiveluch_lat),
            zoom=5
        ),
        title=dict(
            text='Shiveluch Volcanic Complex - Kamchatka, Russia',
            x=0.5,
            xanchor='center',
            font=dict(size=20)
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        showlegend=False
    )
    
    layout = dbc.Container(fluid=True, children=[
        dbc.Row([
            dbc.Col([
                html.H2("Shiveluch Volcanic Complex Analysis", className="text-center mb-4"),
                
                # Quick Facts Card
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Quick Facts", className="card-title"),
                        dbc.Row([
                            dbc.Col([
                                html.P([html.Strong("Coordinates: "), f"{shiveluch_lat}°N, {shiveluch_lon}°E"]),
                                html.P([html.Strong("Elevation: "), "3,283 m (10,771 ft)"]),
                            ], md=6),
                            dbc.Col([
                                html.P([html.Strong("Location: "), "Central Kamchatka Depression"]),
                                html.P([html.Strong("Subduction Rate: "), "~9 cm/year"]),
                            ], md=6)
                        ])
                    ])
                ], className="mb-4", color="light"),
                
                # Interactive map
                html.Div([
                    dcc.Graph(
                        id='shiveluch-map',
                        figure=fig,
                        config={
                            'displayModeBar': True, 
                            'scrollZoom': True
                        }
                    )
                ], style={'height': '600px', 'overflow': 'hidden'}),
                
                # Geological Setting
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Geological Setting", className="card-title mb-3"),
                        
                        html.H6("Tectonic Context", className="mt-3"),
                        html.P([
                            "The Kurile-Kamchatka Volcanic Arc is located at the northeastern convergent "
                            "boundary of the Eurasian and Pacific Plates in Russia. The Shiveluch Volcanic Complex, "
                            "within the Central Kamchatka Depression at the Kamchatka Peninsula that forms the "
                            "northern part of the Kurile-Kamchatka volcanic arc, composes the northern boundary "
                            "of Kamchatka's volcanic activity. The location of Shiveluch is also near the "
                            "Aleutian-Kamchatka triple-junction where from the east the Pacific plate subducts "
                            "below Kamchatka at approximately 9 cm/year."
                        ]),
                        
                        html.H6("Volcanic Zones", className="mt-4"),
                        html.P([
                            "Forming the volcanism for Kamchatka, from east to west, are three zones that sit "
                            "parallel to the subduction trench:"
                        ]),
                        html.Ul([
                            html.Li([html.Strong("Eastern Volcanic Front (EVF)"), " - Front arc volcanoes"]),
                            html.Li([html.Strong("Central Kamchatka Depression (CKD)"), " - Includes Shiveluch and the Kluchevskaya Group; slab depth 180-200 km"]),
                            html.Li([html.Strong("Sredinny Ridge (SR)"), " - Back arc volcanoes"]),
                        ]),
                        
                        html.H6("Volcanic History", className="mt-4"),
                        html.P([
                            "Shiveluch is one of Kamchatka's largest and most active volcanoes. "
                            "The volcanic complex consists of Old Shiveluch, which forms the main edifice, "
                            "and Young Shiveluch, an active lava dome complex that has been growing since "
                            "the catastrophic eruption in 1964."
                        ]),
                    ])
                ], className="mt-4"),
                
                # Petrological Characteristics
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Petrological Characteristics", className="card-title mb-3"),
                        
                        dbc.Row([
                            dbc.Col([
                                html.H6("Melt Conditions"),
                                html.Ul([
                                    html.Li([html.Strong("Temperature: "), "1062 ± 48°C"]),
                                    html.Li([html.Strong("H₂O Content: "), "8-10 wt% (avg. 4 wt%)"]),
                                    html.Li([html.Strong("Primary Rock Type: "), "Andesite"]),
                                ], className="mb-0"),
                            ], md=6),
                            dbc.Col([
                                html.H6("Crystallization"),
                                html.Ul([
                                    html.Li([html.Strong("Depth: "), "23.6-28.8 km"]),
                                    html.Li([html.Strong("H₂O at Crystallization: "), "10-14 wt%"]),
                                    html.Li([html.Strong("Amphibole Fraction: "), "0.2-12.2%"]),
                                ], className="mb-0"),
                            ], md=6)
                        ]),
                        
                        html.Hr(className="my-3"),
                        
                        dbc.Row([
                            dbc.Col([
                                html.H6("Mg# Ranges"),
                                html.Ul([
                                    html.Li([html.Strong("Mafic Enclaves: "), "Mg# > 74"]),
                                    html.Li([html.Strong("Amphibole: "), "Mg# 56-82"]),
                                ], className="mb-0"),
                            ], md=6),
                            dbc.Col([
                                html.H6("Mineral Assemblage"),
                                html.P([
                                    html.Strong("Typical: "),
                                    "Clinopyroxene + Amphibole + Plagioclase + Orthopyroxene"
                                ], className="mb-0"),
                            ], md=6)
                        ]),
                        
                        html.Hr(className="my-3"),
                        
                        html.Small([
                            html.Em("References: "),
                            "Churikova et al. (2007), Goltz et al. (2020, 2022)"
                        ], className="text-muted")
                    ])
                ], className="mt-4", color="info", outline=True),
                
            ], width=12, lg=10, xl=8, className="mx-auto")
        ])
    ])
    
    return layout