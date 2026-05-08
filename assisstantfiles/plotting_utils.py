"""
Plotting utilities for the Subduction Zone EPMA Analysis application.
Contains functions for creating TAS diagrams and halogen evolution plots.
"""

import numpy as np
import pandas as pd #type:ignore
import plotly.express as px #type:ignore
import plotly.graph_objects as go #type: ignore
from plotly.subplots import make_subplots #type:ignore




def classify_tas_field(sio2, alkali):
    """Classify sample into TAS field based on SiO₂ and Na₂O+K₂O."""
    if sio2 < 45 and alkali < 5:
        return "Foidite"
    elif 41 <= sio2 < 45 and 5 <= alkali < 9:
        return "Tephrite / Basanite"
    elif 45 <= sio2 < 53 and 7 <= alkali < 11:
        return "Phono-tephrite"
    elif 45 <= sio2 < 53 and 9 <= alkali < 13:
        return "Tephri-phonolite"
    elif 53 <= sio2 < 63 and 9 <= alkali < 13:
        return "Phonolite"
    elif 45 <= sio2 < 52 and alkali < 5:
        return "Basalt"
    elif 48 <= sio2 < 57 and 5 <= alkali < 7:
        return "Trachy-basalt"
    elif 52 <= sio2 < 57 and 5 <= alkali < 7:
        return "Basaltic trachy-andesite"
    elif 57 <= sio2 < 63 and alkali < 5:
        return "Andesite"
    elif 63 <= sio2 < 69 and alkali < 5:
        return "Dacite"
    elif 63 <= sio2 < 69 and 7 <= alkali < 11:
        return "Trachyte"
    elif 69 <= sio2 < 75 and 5 <= alkali < 9:
        return "Trachydacite"
    elif 69 <= sio2 < 75 and alkali < 5:
        return "Rhyolite"
    else:
        return "Unclassified"

def create_tas_figure(df, filter_bulk_only=True):
    """
    Create TAS diagram with optional filtering for bulk compositions only.
    Based on MATLAB plotTAS function with accurate field boundaries.
    
    Parameters:
    df: DataFrame with geochemical data
    filter_bulk_only: Boolean to enable filtering for bulk compositions
    """
    df = df.copy()
    
    # Filter for bulk compositions if requested
    if filter_bulk_only:
        df = filter_bulk_compositions(df)
    
    df['Na2O+K2O'] = df['Na2O'] + df['K2O']

    fig = go.Figure()

    # Define points of composition delineators (from MATLAB code)
    p1 = [41, 0]
    p2 = [45, 0]
    p3 = [41, 7]
    p4 = [45, 5]
    p5 = [52, 5]
    p6 = [57, 5.9]
    p7 = [63, 7]
    p8 = [69, 8]
    p9 = [69, 13]
    p10 = [61, 13.5]
    p11 = [57.6, 11.7]
    p12 = [53, 9.3]
    p13 = [49.4, 7.3]
    p14 = [45, 9.4]
    p15 = [48.4, 11.5]
    p16 = [52.5, 14]
    p17 = [78, 0]
    p18 = [48.065, 16]

    # Define lines (from MATLAB code)
    lines = [
        [p1, p3, p14, p16],  # l1
        [p2, p4, p13, p10],  # l2
        [p4, p5, p8],        # l3
        [p18, p16, p11, p7, [p7[0], 0]],  # l4
        [p15, p12, p6, [p6[0], 0]],       # l5
        [p9, p8, p17],       # l6
        [p14, p13, p5, [p5[0], 0]]        # l7
    ]

    # Draw the boundary lines
    for line in lines:
        x_coords = [point[0] for point in line]
        y_coords = [point[1] for point in line]
        
        fig.add_trace(go.Scatter(
            x=x_coords,
            y=y_coords,
            mode='lines',
            line=dict(color='black', width=1.5),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Define rock type fields with their boundaries and label positions
    # Based on the MATLAB field definitions
    rock_fields = [
        {
            "name": "Picro-basalt",
            "points": [[41, 0], [45, 0], [45, 5], [41, 7], [41, 0]],
            "label_pos": [42, 3]
        },
        {
            "name": "Basalt",
            "points": [[45, 0], [52, 0], [52, 5], [45, 5], [45, 0]],
            "label_pos": [46, 3.5]
        },
        {
            "name": "Basaltic\nAndesite",
            "points": [[52, 0], [57, 0], [57, 5.9], [52, 5], [52, 0]],
            "label_pos": [52.5, 3.5]
        },
        {
            "name": "Andesite",
            "points": [[57, 0], [63, 0], [63, 7], [57, 5.9], [57, 0]],
            "label_pos": [58, 3.75]
        },
        {
            "name": "Dacite",
            "points": [[63, 0], [69, 0], [69, 8], [63, 7], [63, 0]],
            "label_pos": [64.5, 4]
        },
        {
            "name": "Rhyolite",
            "points": [[69, 0], [78, 0], [69, 8], [69, 0]],
            "label_pos": [72, 9]
        },
        {
            "name": "Trachy-\nbasalt",
            "points": [[45, 5], [49.4, 7.3], [45, 9.4], [45, 5]],
            "label_pos": [47.5, 5.75]
        },
        {
            "name": "Basaltic\nTrachy-\nandesite",
            "points": [[49.4, 7.3], [52, 5], [53, 9.3], [49.4, 7.3]],
            "label_pos": [51, 7]
        },
        {
            "name": "Trachy-\nandesite",
            "points": [[53, 9.3], [57, 5.9], [57.6, 11.7], [53, 9.3]],
            "label_pos": [56, 9]
        },
        {
            "name": "Trachyte/\nTrachydacite",
            "points": [[57.6, 11.7], [63, 7], [69, 8], [61, 13.5], [57.6, 11.7]],
            "label_pos": [62, 10]
        },
        {
            "name": "Tephrite/\nBasanite",
            "points": [[41, 7], [45, 5], [45, 9.4], [41, 7]],
            "label_pos": [44, 7.5]
        },
        {
            "name": "Phono-\ntephrite",
            "points": [[45, 9.4], [49.4, 7.3], [53, 9.3], [48.4, 11.5], [45, 9.4]],
            "label_pos": [48, 9.5]
        },
        {
            "name": "Tephri-\nphonolite",
            "points": [[48.4, 11.5], [53, 9.3], [57.6, 11.7], [52.5, 14], [48.4, 11.5]],
            "label_pos": [51.5, 12]
        },
        {
            "name": "Phonolite",
            "points": [[52.5, 14], [57.6, 11.7], [61, 13.5], [52.5, 14]],
            "label_pos": [56, 13.5]
        },
        {
            "name": "Foidite",
            "points": [[41, 7], [45, 9.4], [48.4, 11.5], [52.5, 14], [48.065, 16], [41, 7]],
            "label_pos": [46, 13.5]
        }
    ]

    # Add field polygons with light shading
    for field in rock_fields:
        x_coords = [point[0] for point in field["points"]]
        y_coords = [point[1] for point in field["points"]]
        
        fig.add_trace(go.Scatter(
            x=x_coords,
            y=y_coords,
            fill='toself',
            mode='none',
            fillcolor='lightgray',
            opacity=0.1,
            name=field["name"],
            showlegend=False,
            hoverinfo='skip'
        ))

    # Add field labels
    for field in rock_fields:
        fig.add_annotation(
            x=field["label_pos"][0],
            y=field["label_pos"][1],
            text=field["name"],
            showarrow=False,
            font=dict(size=9, color="black"),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1
        )

    # Add sample data points
    fig.add_trace(go.Scatter(
        x=df['SiO2'],
        y=df['Na2O+K2O'],
        mode='markers',
        marker=dict(
            color='blue', 
            size=8, 
            line=dict(color='darkblue', width=1),
            symbol='star'
        ),
        name='Bulk Compositions' if filter_bulk_only else 'Samples',
        text=df['SAMPLE'],
        hovertemplate='<b>%{text}</b><br>SiO₂: %{x:.2f} wt%<br>Na₂O+K₂O: %{y:.2f} wt%<extra></extra>'
    ))

    # Update layout to match MATLAB styling
    fig.update_layout(
        title=dict(
            text="Total Alkali Silica Diagram" + (" - Bulk Compositions Only" if filter_bulk_only else ""),
            font=dict(size=16)
        ),
        xaxis=dict(
            title="Silica (SiO₂) Weight %",
            range=[40, 80],
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            dtick=5
        ),
        yaxis=dict(
            title="Alkali (Na₂O + K₂O) Weight %",
            range=[0, 16],
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            dtick=2
        ),
        height=700,
        width=900,
        template='plotly_white',
        plot_bgcolor='white'
    )

    return fig

def filter_bulk_compositions(df):
    """
    Filter DataFrame to retain only bulk composition analyses.
    
    This function applies multiple criteria to identify and retain samples
    that represent bulk rock compositions rather than melt inclusions,
    mineral separates, or other non-representative analyses.
    """
    df = df.copy()
    initial_count = len(df)
    
    # Method 1: Filter by sample type/description if available
    if 'SAMPLE_TYPE' in df.columns:
        bulk_keywords = ['whole rock', 'bulk', 'rock', 'lava', 'groundmass']
        exclude_keywords = ['melt inclusion', 'inclusion', 'glass', 'mineral', 'crystal', 'phenocryst']
        
        # Keep samples with bulk keywords
        bulk_mask = df['SAMPLE_TYPE'].str.lower().str.contains('|'.join(bulk_keywords), na=False)
        # Exclude samples with exclusion keywords
        exclude_mask = df['SAMPLE_TYPE'].str.lower().str.contains('|'.join(exclude_keywords), na=False)
        df = df[bulk_mask & ~exclude_mask]
    
    # Method 2: Filter by sample name patterns if no SAMPLE_TYPE column
    elif 'SAMPLE' in df.columns:
        # Common naming conventions
        exclude_patterns = [
            r'MI\d*',  # Melt inclusion codes
            r'.*-MI-.*',  # Melt inclusion in sample names
            r'.*inclusion.*',
            r'.*glass.*',
            r'.*phenocryst.*',
            r'.*crystal.*'
        ]
        
        for pattern in exclude_patterns:
            mask = ~df['SAMPLE'].str.contains(pattern, case=False, na=False, regex=True)
            df = df[mask]
    
    # Method 3: Chemical filtering - bulk compositions should have reasonable oxide totals
    required_oxides = ['SiO2', 'Al2O3', 'FeO', 'MgO', 'CaO', 'Na2O', 'K2O']
    available_oxides = [ox for ox in required_oxides if ox in df.columns]
    
    if len(available_oxides) >= 5:  # Need at least 5 major oxides
        # Calculate oxide total
        df['oxide_total'] = df[available_oxides].sum(axis=1)
        
        # Bulk compositions should have totals between 98-102% (accounting for volatiles, analytical error)
        df = df[(df['oxide_total'] >= 98) & (df['oxide_total'] <= 102)]
    
    # Method 4: Filter out extreme compositions that are likely melt inclusions
    if 'SiO2' in df.columns and 'K2O' in df.columns:
        # Melt inclusions often have very high K2O or extreme SiO2
        df = df[df['K2O'] <= 8.0]  # Most bulk rocks have K2O < 8%
        df = df[df['SiO2'] <= 78.0]  # Exclude extremely evolved compositions
    
    # Method 5: Filter by MgO - melt inclusions often have very low MgO
    if 'MgO' in df.columns:
        # Keep samples with reasonable MgO (bulk rocks rarely have <0.1% MgO unless very evolved)
        df = df[(df['MgO'] >= 0.1) | (df['SiO2'] >= 70)]  # Allow low MgO only for felsic rocks
    
    final_count = len(df)
    print(f"Filtered from {initial_count} to {final_count} samples ({final_count/initial_count*100:.1f}% retained)")
    
    return df

def apply_custom_filters(df, custom_criteria=None):
    """
    Apply additional custom filtering criteria for bulk compositions.
    
    Parameters:
    df: DataFrame with geochemical data
    custom_criteria: Dictionary with custom filtering parameters
    
    Example custom_criteria:
    {
        'exclude_samples': ['MI-1', 'MI-2'],  # Specific samples to exclude
        'min_oxide_total': 99.0,
        'max_oxide_total': 101.0,
        'max_K2O': 6.0,
        'sample_type_column': 'TYPE',
        'bulk_keywords': ['whole rock', 'groundmass'],
        'exclude_keywords': ['inclusion', 'glass']
    }
    """
    if custom_criteria is None:
        return df
    
    df = df.copy()
    
    # Exclude specific samples
    if 'exclude_samples' in custom_criteria:
        df = df[~df['SAMPLE'].isin(custom_criteria['exclude_samples'])]
    
    # Custom oxide total range
    if 'min_oxide_total' in custom_criteria or 'max_oxide_total' in custom_criteria:
        required_oxides = ['SiO2', 'Al2O3', 'FeO', 'MgO', 'CaO', 'Na2O', 'K2O']
        available_oxides = [ox for ox in required_oxides if ox in df.columns]
        
        if available_oxides:
            df['oxide_total'] = df[available_oxides].sum(axis=1)
            
            if 'min_oxide_total' in custom_criteria:
                df = df[df['oxide_total'] >= custom_criteria['min_oxide_total']]
            if 'max_oxide_total' in custom_criteria:
                df = df[df['oxide_total'] <= custom_criteria['max_oxide_total']]
    
    # Custom K2O threshold
    if 'max_K2O' in custom_criteria and 'K2O' in df.columns:
        df = df[df['K2O'] <= custom_criteria['max_K2O']]
    
    # Custom sample type filtering
    if 'sample_type_column' in custom_criteria:
        col = custom_criteria['sample_type_column']
        if col in df.columns:
            if 'bulk_keywords' in custom_criteria:
                bulk_mask = df[col].str.lower().str.contains('|'.join(custom_criteria['bulk_keywords']), na=False)
                df = df[bulk_mask]
            
            if 'exclude_keywords' in custom_criteria:
                exclude_mask = df[col].str.lower().str.contains('|'.join(custom_criteria['exclude_keywords']), na=False)
                df = df[~exclude_mask]
    
    return df

def get_mg_number_animation(df_bulk, color_scheme='Viridis'):
    """
    Creates a multi-panel figure showing halogen evolution through crystallization stages.
    
    Parameters:
    df_bulk (pd.DataFrame): DataFrame containing bulk chemistry data
    color_scheme (str): Color scheme for the plots
    
    Returns:
    plotly.graph_objects.Figure: Multi-panel halogen evolution figure
    """
    data = df_bulk.copy()

    # Add sample column if not present
    if 'SAMPLE' not in data.columns:
        data['SAMPLE'] = 'Unknown'

    # Remove rows with missing data
    required_cols = ['SiO2', 'MgO', 'FeO', 'Al2O3', 'Cl', 'F']
    data = data.dropna(subset=required_cols)

    # Filter for Amphibole compositions
    def classify_mineral(row):
        return row['SiO2'] < 52 and row['MgO'] > 10 and row['FeO'] < 12

    data = data[data.apply(classify_mineral, axis=1)]
    if data.empty:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No suitable amphibole compositions found in dataset",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=400, title="Halogen Evolution Analysis")
        return fig

    # Calculate Mg# and convert halogens to ppm
    data['Mg#'] = 100 * data['MgO'] / (data['MgO'] + data['FeO'])
    data['Cl_ppm'] = data['Cl'] * 10000
    data['F_ppm'] = data['F'] * 10000

    # Define crystallization stages based on Mg#
    bins = [0, 57, 60, 75, 100]
    labels = ['Evolved', 'Intermediate', 'Primitive', 'Ultra-primitive']
    data['Mg_stage'] = pd.cut(data['Mg#'], bins=bins, labels=labels)

    stages_to_plot = ['Primitive', 'Intermediate', 'Evolved']

    # Create subplots (2 rows, 4 columns)
    fig = make_subplots(
        rows=2, cols=4,
        subplot_titles=(
            [f"Cl - {stage}" for stage in stages_to_plot] + ["Cl Interpretation"] +
            [f"F - {stage}" for stage in stages_to_plot] + ["F Interpretation"]
        ),
        horizontal_spacing=0.06,
        vertical_spacing=0.12,
        specs=[[{"secondary_y": False} for _ in range(4)] for _ in range(2)]
    )

    stage_to_col = {stage: i + 1 for i, stage in enumerate(stages_to_plot)}

    # Plot Cl and F scatter plots for each stage
    for stage in stages_to_plot:
        sub_df = data[data['Mg_stage'] == stage]
        if sub_df.empty:
            continue

        col = stage_to_col[stage]

        # Chlorine plots (row 1)
        if not sub_df['Cl_ppm'].isna().all():
            raw_cl_sizes = sub_df['Cl_ppm'] / sub_df['Cl_ppm'].max() * 30 + 5
            cl_sizes = raw_cl_sizes.clip(lower=1)

            fig.add_trace(
                go.Scatter(
                    x=sub_df['Al2O3'],
                    y=sub_df['Cl_ppm'],
                    mode='markers',
                    marker=dict(
                        size=cl_sizes,
                        sizemode='area',
                        sizeref=2,
                        color=sub_df['Mg#'],
                        colorscale=color_scheme,
                        showscale=False,
                        opacity=0.7,
                        line=dict(width=0.5, color='DarkSlateGrey')
                    ),
                    text=sub_df['SAMPLE'],
                    name=f"Cl {stage}",
                    showlegend=False
                ),
                row=1, col=col
            )

        # Fluorine plots (row 2)
        if not sub_df['F_ppm'].isna().all():
            raw_f_sizes = sub_df['F_ppm'] / sub_df['F_ppm'].max() * 30 + 5
            f_sizes = raw_f_sizes.clip(lower=1)

            fig.add_trace(
                go.Scatter(
                    x=sub_df['Al2O3'],
                    y=sub_df['F_ppm'],
                    mode='markers',
                    marker=dict(
                        size=f_sizes,
                        sizemode='area',
                        sizeref=2,
                        color=sub_df['Mg#'],
                        colorscale='Plasma',
                        showscale=False,
                        opacity=0.7,
                        line=dict(width=0.5, color='DarkSlateGrey')
                    ),
                    text=sub_df['SAMPLE'],
                    name=f"F {stage}",
                    showlegend=False
                ),
                row=2, col=col
            )

    # Interpretation text for Cl
    cl_text = (
        "If there is a steady<br>"
        "increase in chlorine<br>"
        "concentration from Primitive<br>"
        "to Intermediate to Evolved<br>"
        "stages, this suggests<br>"
        "chlorine enrichment with<br>"
        "magma evolution. Conversely,<br>"
        "a decreasing trend suggests<br>"
        "chlorine depletion during<br>"
        "crystallization."
    )

    # Interpretation text for F
    f_text = (
        "Similarly, trends in fluorine<br>"
        "concentration from Primitive<br>"
        "to Intermediate to Evolved<br>"
        "stages reflect fluorine<br>"
        "behavior during magma<br>"
        "evolution. Increasing trends<br>"
        "suggest fluorine enrichment,<br>"
        "while decreasing trends<br>"
        "indicate fluorine depletion<br>"
        "during crystallization."
    )

    # Add interpretation text annotations
    fig.add_annotation(
        text=cl_text,
        xref='x4', yref='y4',
        x=0.5, y=0.8,  # center in subplot
        showarrow=False,
        font=dict(size=12),
        align='left',
        bordercolor='black',
        borderwidth=1,
        borderpad=10,
        bgcolor='white',
        opacity=0.9,
    )

    fig.add_annotation(
        text=f_text,
        xref='x8', yref='y8',
        x=0.5, y=0.8,  # center in subplot
        showarrow=False,
        font=dict(size=12),
        align='left',
        bordercolor='black',
        borderwidth=1,
        borderpad=10,
        bgcolor='white',
        opacity=0.9,
    )

    # Hide axes on interpretation columns
    fig.update_xaxes(visible=False, row=1, col=4)
    fig.update_yaxes(visible=False, row=1, col=4)
    fig.update_xaxes(visible=False, row=2, col=4)
    fig.update_yaxes(visible=False, row=2, col=4)

    # Update layout
    fig.update_layout(
        height=700,
        width=1200,
        title_text="Halogen Concentrations by Crystallization Stage",
        showlegend=False,
        margin=dict(t=100)
    )

    # Add axis labels for data subplots
    for i in range(1, 4):
        fig.update_xaxes(title_text="Al₂O₃ (wt%)", row=1, col=i)
        fig.update_xaxes(title_text="Al₂O₃ (wt%)", row=2, col=i)
        fig.update_yaxes(title_text="Cl (ppm)", row=1, col=i)
        fig.update_yaxes(title_text="F (ppm)", row=2, col=i)

    return fig