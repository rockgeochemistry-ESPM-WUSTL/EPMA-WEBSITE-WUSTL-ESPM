import dash_bootstrap_components as dbc #type: ignore
from dash import html #type: ignore

def create_info_layout():
    
    info_layout = dbc.Container(fluid=True, children=[
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H1("Information & Documentation", className="text-center mb-4"),
                        
                        # EPMA Background Section
                        html.H3("🔬 EPMA Background", className="mt-4 mb-3"),
                        html.P([
                            "Electron Probe Micro-Analysis (EPMA) is a quantitative analytical technique used to determine ",
                            "the elemental composition of materials at the micrometer scale. In subduction zone studies, ",
                            "EPMA is essential for measuring trace element concentrations in minerals and melt inclusions."
                        ]),
                        
                        # Partition Coefficients Section
                        html.H3("📊 Partition Coefficients (D)", className="mt-4 mb-3"),
                        html.P([
                            "Partition coefficients represent the preferential distribution of elements between ",
                            "mineral phases and melts. They are calculated as:"
                        ]),
                        
                        dbc.Alert([
                            html.P("D = C_mineral / C_melt", className="text-center mb-2 font-monospace"),
                            html.P("Where C represents the concentration of an element in each phase", 
                                   className="text-center mb-0 small")
                        ], color="light", className="mb-3"),
                        
                        html.P([
                            "Values > 1 indicate the element prefers the mineral phase, ",
                            "while values < 1 indicate preference for the melt phase."
                        ]),
                        
                        # Halogen Cycling Section
                        html.H3("🌋 Halogen Cycling in Subduction Zones", className="mt-4 mb-3"),
                        html.P([
                            "Halogens (Cl, F, Br, I) play crucial roles in subduction zone processes, affecting ",
                            "melt generation, volatile transport, and ore formation. Understanding their partitioning ",
                            "behavior helps constrain:"
                        ]),
                        html.Ul([
                            html.Li("Deep volatile cycling and fluid-rock interactions"),
                            html.Li("Arc magma genesis and differentiation processes"),
                            html.Li("Formation of porphyry copper and epithermal deposits"),
                            html.Li("Atmospheric volatile contributions from volcanic degassing")
                        ]),
                        
                        # Amphibole Importance Section
                        html.H3("💎 Amphibole in Subduction Systems", className="mt-4 mb-3"),
                        html.P([
                            "Amphibole is a key hydrous mineral in subduction zone magmas, capable of storing ",
                            "significant amounts of water and trace elements. Its stability field overlaps with ",
                            "conditions of magma generation and storage, making it an important phase for:"
                        ]),
                        html.Ul([
                            html.Li("Controlling melt water content and oxidation state"),
                            html.Li("Fractionating trace elements during magma evolution"),
                            html.Li("Recording pressure-temperature-composition conditions"),
                            html.Li("Influencing halogen budgets in arc magmas")
                        ]),
                        
                        # Data Interpretation Section
                        html.H3("📈 Data Interpretation Guidelines", className="mt-4 mb-3"),
                        
                        html.H5("TAS Diagrams:", className="mt-3 mb-2"),
                        html.P([
                            "Total Alkali vs. Silica (TAS) diagrams classify volcanic rocks based on their ",
                            "alkali and silica content, helping identify magma series and tectonic settings.",
                            "Bounds represented here-in by graphing software are taken from Les Bas(1984)."
                        ]),
                        
                        html.H5("Partition Coefficient Trends:", className="mt-3 mb-2"),
                        html.P([
                            "Systematic variations in D values can indicate changes in intensive parameters ",
                            "(T, P, fO₂, aH₂O) or melt composition during magma evolution."
                        ]),
                        
                        html.H5("Quality Control:", className="mt-3 mb-2"),
                        html.Ul([
                            html.Li("Check for analytical totals between 98-102 wt%"),
                            html.Li("Verify melt inclusion integrity (no post-entrapment crystallization)"),
                            html.Li("Ensure host crystal-melt inclusion equilibrium"),
                            html.Li("Consider below-detection-limit values in statistical analyses")
                        ]),
                        
                        # Technical Notes Section
                        html.H3("⚙️ Technical Notes", className="mt-4 mb-3"),
                        
                        dbc.Alert([
                            html.H6("File Format Requirements:", className="mb-2"),
                            html.Ul([
                                html.Li("Excel files with pair ID columns for phase types (e.g., 'Amphibole', 'Melt Inclusion')"),
                                html.Li("Column headers must match expected element names (SiO2, Al2O3, etc.)"),
                                html.Li("Concentrations in weight percent (wt%) or ppm as specified"),
                                html.Li("Missing values should be left blank and treated as bdl(below detection limit)")
                            ], className="mb-0")
                        ], color="warning", className="mb-3"),
                        
                        # References Section
                        html.H3("📚 Key References", className="mt-4 mb-3"),
                        html.Ul([
                            html.Li("Botcharnikov et al. (2004) - Halogen solubility in silicate melts"),
                            html.Li("Webster et al. (2009) - Partitioning of Cl and F in magmatic systems"),
                            html.Li("Li & Hermann (2015) - Halogen cycling in subduction zones"),
                            html.Li("Zajacz & Halter (2009) - Cl and Br partitioning between apatite and melt")
                        ]),
                        
                        html.Hr(),
                        
                        # Footer
                        html.Div([
                            html.Small([
                                "This application is designed for research and educational purposes. ",
                                "For questions or technical support, contact the development team at ",
                                "Washington University in Saint Louis, Earth, Environment, and",
                                "Planetary Sciences, E.S.P.M. Group."
                            ], className="text-muted text-center d-block")
                        ])
                    ])
                ]),
                width=12, lg=10, xl=8, className="mx-auto"
            )
        ])
    ])
    
    return info_layout