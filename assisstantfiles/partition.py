import numpy as np 
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
from typing import Tuple, List

# Global DataFrames for storing partition data
df_partition_params = pd.DataFrame()
df_partition_mc = pd.DataFrame()

ELEMENTS = ['SiO2', 'TiO2', 'Al2O3', 'Cr2O3', 'FeO', 'NiO', 'MnO',
            'MgO', 'CaO', 'BaO', 'Na2O', 'K2O', 'P2O5', 'SO3', 'Cl', 'F', 'Mg#']

def extract_base(name: str) -> str:
    """Extract the base sample name from sheet name."""
    return name.split()[0]

def get_sheet_names(file_obj) -> tuple[list[str], list[str]]:
    """Extract XT and MI sheet names from Excel file."""
    xls = pd.ExcelFile(file_obj)
    xt = [s for s in xls.sheet_names if 'XT' in s]
    mi = [s for s in xls.sheet_names if 'MI' in s]
    return xt, mi

def run_monte_carlo_and_params(file_obj, xt_sheet_names=None, mi_sheet_names=None):
    """
    Run Monte Carlo simulation for halogen partition coefficients and calculate 
    median parameters for all elements.
    
    Parameters:
    -----------
    file_obj : file-like object
        Excel file containing XT and MI sheets
    xt_sheet_names : list
        List of XT sheet names
    mi_sheet_names : list
        List of MI sheet names
        
    Returns:
    --------
    tuple : (df_mc, df_params)
        df_mc: DataFrame with Monte Carlo results
        df_params: DataFrame with median parameters for each sample
    """
    mc_results = []
    param_list = []
    N = 1000  # Number of Monte Carlo iterations

    epsilon = 1e-6  # Small value to prevent division by zero
    max_D_Cl = 11   # Maximum reasonable Cl partition coefficient
    max_D_F = 11    # Maximum reasonable F partition coefficient

    for xt_sheet, mi_sheet in zip(xt_sheet_names, mi_sheet_names):
        SAMPLE_num = extract_base(xt_sheet)

        # Read the data sheets
        df_xt = pd.read_excel(file_obj, sheet_name=xt_sheet)
        df_mi = pd.read_excel(file_obj, sheet_name=mi_sheet)
        
        # Clean column names
        df_xt.columns = df_xt.columns.str.strip()
        df_mi.columns = df_mi.columns.str.strip()

        length_params = min(len(df_xt), len(df_mi))

        # --- Monte Carlo for Cl ---
        if set(['Cl','Cl AT%']).issubset(df_xt.columns) and set(['Cl','Cl AT%']).issubset(df_mi.columns):
            cl_xt_vals = df_xt[['Cl', 'Cl AT%']].dropna().reset_index(drop=True)
            cl_mi_vals = df_mi[['Cl', 'Cl AT%']].dropna().reset_index(drop=True)
            length_cl = min(len(cl_xt_vals), len(cl_mi_vals))
            
            for i in range(length_cl):
                cl_xt = cl_xt_vals.loc[i, 'Cl']
                sigma_xt = cl_xt_vals.loc[i, 'Cl AT%']
                cl_mi = cl_mi_vals.loc[i, 'Cl']
                sigma_mi = cl_mi_vals.loc[i, 'Cl AT%']
                
                if cl_xt > 0 and cl_mi > 0 and sigma_xt > 0 and sigma_mi > 0:
                    # Generate Monte Carlo samples
                    cl_xt_mc = np.clip(cl_xt + sigma_xt * np.random.normal(size=N), epsilon, None)
                    cl_mi_mc = np.clip(cl_mi + sigma_mi * np.random.normal(size=N), epsilon, None)
                    D_Cl_mc = cl_xt_mc / cl_mi_mc
                    
                    # Filter valid partition coefficients
                    valid = D_Cl_mc <= max_D_Cl
                    for xt_val, mi_val, d_val in zip(cl_xt_mc[valid], cl_mi_mc[valid], D_Cl_mc[valid]):
                        mc_results.append({
                            'SAMPLE': SAMPLE_num,
                            'Halogen': 'Cl',
                            'D': d_val,
                            'Element_Value': xt_val,
                            'Element_Source': 'XT'
                        })
                        mc_results.append({
                            'SAMPLE': SAMPLE_num,
                            'Halogen': 'Cl',
                            'D': d_val,
                            'Element_Value': mi_val,
                            'Element_Source': 'MI'
                        })

        # --- Monte Carlo for F ---
        if set(['F','F AT%']).issubset(df_xt.columns) and set(['F CDL99','F AT%']).issubset(df_mi.columns):
            f_xt_vals = df_xt[['F','F AT%']].dropna().reset_index(drop=True)
            f_mi_vals = df_mi[['F CDL99','F AT%']].dropna().reset_index(drop=True)
            length_f = min(len(f_xt_vals), len(f_mi_vals))
            
            for i in range(length_f):
                f_xt = f_xt_vals.loc[i, 'F']
                sigma_xt = f_xt_vals.loc[i, 'F AT%']
                f_mi = f_mi_vals.loc[i, 'F CDL99']
                sigma_mi = f_mi_vals.loc[i, 'F AT%']
                
                if f_xt > 0 and f_mi > 0 and sigma_xt > 0 and sigma_mi > 0:
                    # Generate Monte Carlo samples
                    f_xt_mc = np.clip(f_xt + sigma_xt * np.random.normal(size=N), epsilon, None)
                    f_mi_mc = np.clip(f_mi + sigma_mi * np.random.normal(size=N), epsilon, None)
                    D_F_mc = f_xt_mc / f_mi_mc
                    
                    # Filter valid partition coefficients
                    valid = D_F_mc <= max_D_F
                    for xt_val, mi_val, d_val in zip(f_xt_mc[valid], f_mi_mc[valid], D_F_mc[valid]):
                        mc_results.append({
                            'SAMPLE': SAMPLE_num,
                            'Halogen': 'F',
                            'D': d_val,
                            'Element_Value': xt_val,
                            'Element_Source': 'XT'
                        })
                        mc_results.append({
                            'SAMPLE': SAMPLE_num,
                            'Halogen': 'F',
                            'D': d_val,
                            'Element_Value': mi_val,
                            'Element_Source': 'MI'
                        })

        # --- Calculate median parameters for all elements ---
        data_params = {}
        for element in ELEMENTS:
            if element == 'Mg#':
                continue  # Handle Mg# separately
                
            vals_xt = df_xt.loc[:length_params-1, element].dropna() if element in df_xt.columns else pd.Series(dtype=float)
            vals_mi = df_mi.loc[:length_params-1, element].dropna() if element in df_mi.columns else pd.Series(dtype=float)
            combined = pd.concat([vals_xt, vals_mi]).dropna()
            data_params[element] = combined.median() if not combined.empty else np.nan

        # Calculate Mg# = 100 * MgO / (MgO + FeO)
        mg_xt = df_xt['MgO'] if 'MgO' in df_xt.columns else pd.Series(dtype=float)
        fe_xt = df_xt['FeO'] if 'FeO' in df_xt.columns else pd.Series(dtype=float)
        mg_mi = df_mi['MgO'] if 'MgO' in df_mi.columns else pd.Series(dtype=float)
        fe_mi = df_mi['FeO'] if 'FeO' in df_mi.columns else pd.Series(dtype=float)
        
        mg_all = pd.concat([
            100 * mg_xt / (mg_xt + fe_xt).replace(0, np.nan), 
            100 * mg_mi / (mg_mi + fe_mi).replace(0, np.nan)
        ]).dropna()
        data_params['Mg#'] = mg_all.median() if not mg_all.empty else np.nan

        param_list.append({'SAMPLE': SAMPLE_num, **data_params})

    # Build DataFrames
    df_mc = pd.DataFrame(mc_results)
    df_params = pd.DataFrame(param_list)
    
    return df_mc, df_params

def prepare_scatter_data(df_mc, halogen, element):
    """
    Prepare data for scatter plots using actual Monte Carlo values differentiated by sample.
    
    Parameters:
    -----------
    df_mc : DataFrame
        Monte Carlo results
    halogen : str
        Halogen element ('Cl' or 'F')
    element : str
        Element to plot on x-axis
        
    Returns:
    --------
    DataFrame : Combined data ready for plotting with individual sample points
    """
    global df_partition_params
    
    # Filter for the specific halogen
    df = df_mc[df_mc['Halogen'] == halogen].copy()
    
    if df.empty:
        return df

    if element in ['Cl', 'F']:
        # For halogens, use the element values directly from MC results
        df['Element_To_Plot'] = df['Element_Value']
    else:
        # For other elements, we need to get the raw data values, not medians
        # We'll need to go back to the original data for each sample
        element_values = []
        
        for _, row in df.iterrows():
            sample = row['SAMPLE']
            source = row['Element_Source']
            
            # Look up the element value from df_partition_params
            # But we want individual values, not medians
            if not df_partition_params.empty:
                sample_data = df_partition_params[df_partition_params['SAMPLE'] == sample]
                if not sample_data.empty and element in sample_data.columns:
                    element_val = sample_data[element].iloc[0]
                    element_values.append(element_val)
                else:
                    element_values.append(np.nan)
            else:
                element_values.append(np.nan)
        
        df['Element_To_Plot'] = element_values

    return df

def get_raw_element_data(file_obj, xt_sheet_names, mi_sheet_names, element):
    """
    Extract raw element data for each sample and measurement point.
    
    Parameters:
    -----------
    file_obj : file-like object
        Excel file containing XT and MI sheets
    xt_sheet_names : list
        List of XT sheet names
    mi_sheet_names : list
        List of MI sheet names
    element : str
        Element name to extract
        
    Returns:
    --------
    DataFrame : Raw element data with SAMPLE, Element_Source, and element values
    """
    raw_data = []
    
    for xt_sheet, mi_sheet in zip(xt_sheet_names, mi_sheet_names):
        SAMPLE_num = extract_base(xt_sheet)
        
        # Read the data sheets
        df_xt = pd.read_excel(file_obj, sheet_name=xt_sheet)
        df_mi = pd.read_excel(file_obj, sheet_name=mi_sheet)
        
        # Clean column names
        df_xt.columns = df_xt.columns.str.strip()
        df_mi.columns = df_mi.columns.str.strip()
        
        # Extract element data from XT sheet
        if element in df_xt.columns:
            xt_values = df_xt[element].dropna()
            for value in xt_values:
                raw_data.append({
                    'SAMPLE': SAMPLE_num,
                    'Element_Source': 'XT',
                    element: value
                })
        
        # Extract element data from MI sheet
        if element in df_mi.columns:
            mi_values = df_mi[element].dropna()
            for value in mi_values:
                raw_data.append({
                    'SAMPLE': SAMPLE_num,
                    'Element_Source': 'MI',
                    element: value
                })
    
    return pd.DataFrame(raw_data)

def prepare_scatter_data_with_raw_values(df_mc, halogen, element, file_obj=None, xt_sheets=None, mi_sheets=None):
    """
    Prepare data for scatter plots using actual raw measurement values for each point.
    
    Parameters:
    -----------
    df_mc : DataFrame
        Monte Carlo results
    halogen : str
        Halogen element ('Cl' or 'F')
    element : str
        Element to plot on x-axis
    file_obj : file-like object, optional
        Excel file for extracting raw data
    xt_sheets : list, optional
        XT sheet names
    mi_sheets : list, optional  
        MI sheet names
        
    Returns:
    --------
    DataFrame : Combined data with raw element values for plotting
    """
    # Filter for the specific halogen
    df = df_mc[df_mc['Halogen'] == halogen].copy()
    
    if df.empty:
        return df

    if element in ['Cl', 'F']:
        # For halogens, use the element values directly from MC results
        df['Element_To_Plot'] = df['Element_Value']
    else:
        # For other elements, we need raw data if available
        if file_obj is not None and xt_sheets is not None and mi_sheets is not None:
            # Get raw element data
            raw_element_df = get_raw_element_data(file_obj, xt_sheets, mi_sheets, element)
            
            # Create expanded dataset matching each MC point with corresponding raw element values
            expanded_data = []
            
            for sample in df['SAMPLE'].unique():
                sample_mc_data = df[df['SAMPLE'] == sample]
                sample_element_data = raw_element_df[raw_element_df['SAMPLE'] == sample]
                
                for _, mc_row in sample_mc_data.iterrows():
                    source = mc_row['Element_Source']
                    source_element_data = sample_element_data[sample_element_data['Element_Source'] == source]
                    
                    if not source_element_data.empty:
                        # Use the first available raw value for this source
                        element_value = source_element_data[element].iloc[0]
                        mc_row_dict = mc_row.to_dict()
                        mc_row_dict['Element_To_Plot'] = element_value
                        expanded_data.append(mc_row_dict)
            
            df = pd.DataFrame(expanded_data)
        else:
            # Fallback to median values from df_partition_params
            global df_partition_params
            element_values = []
            
            for _, row in df.iterrows():
                sample = row['SAMPLE']
                
                if not df_partition_params.empty:
                    sample_data = df_partition_params[df_partition_params['SAMPLE'] == sample]
                    if not sample_data.empty and element in sample_data.columns:
                        element_val = sample_data[element].iloc[0]
                        element_values.append(element_val)
                    else:
                        element_values.append(np.nan)
                else:
                    element_values.append(np.nan)
            
            df['Element_To_Plot'] = element_values

    return df

def calculate_partition_statistics(df_mc, halogen):
    """
    Calculate summary statistics for partition coefficients.
    
    Parameters:
    -----------
    df_mc : DataFrame
        Monte Carlo results
    halogen : str
        Halogen element ('Cl' or 'F')
        
    Returns:
    --------
    DataFrame : Summary statistics by sample
    """
    df_halogen = df_mc[df_mc['Halogen'] == halogen]
    
    if df_halogen.empty:
        return pd.DataFrame()
    
    stats = df_halogen.groupby('SAMPLE')['D'].agg([
        'count', 'mean', 'median', 'std', 'min', 'max',
        lambda x: x.quantile(0.25),  # Q1
        lambda x: x.quantile(0.75)   # Q3
    ]).round(4)
    
    stats.columns = ['Count', 'Mean', 'Median', 'Std', 'Min', 'Max', 'Q1', 'Q3']
    stats = stats.reset_index()
    
    return stats

def validate_excel_structure(file_obj):
    """
    Validate that the Excel file has the required structure for partition analysis.
    
    Parameters:
    -----------
    file_obj : file-like object
        Excel file to validate
        
    Returns:
    --------
    tuple : (is_valid, message, xt_sheets, mi_sheets)
    """
    try:
        xt_sheets, mi_sheets = get_sheet_names(file_obj)
        
        if not xt_sheets:
            return False, "No sheets containing 'XT' found in the file.", [], []
        
        if not mi_sheets:
            return False, "No sheets containing 'MI' found in the file.", [], []
        
        if len(xt_sheets) != len(mi_sheets):
            return False, f"Mismatch: {len(xt_sheets)} XT sheets vs {len(mi_sheets)} MI sheets.", [], []
        
        # Check if sheet pairs exist
        xt_bases = [extract_base(sheet) for sheet in xt_sheets]
        mi_bases = [extract_base(sheet) for sheet in mi_sheets]
        
        if set(xt_bases) != set(mi_bases):
            missing_xt = set(mi_bases) - set(xt_bases)
            missing_mi = set(xt_bases) - set(mi_bases)
            message = "Sheet pairing issues:\n"
            if missing_xt:
                message += f"Missing XT sheets for: {missing_xt}\n"
            if missing_mi:
                message += f"Missing MI sheets for: {missing_mi}"
            return False, message, [], []
        
        return True, f"Valid structure: {len(xt_sheets)} sample pairs found.", xt_sheets, mi_sheets
        
    except Exception as e:
        return False, f"Error reading file: {str(e)}", [], []