import streamlit as st
import pandas as pd
import json
import certifi # type: ignore
import math

# Define file paths for each AUM range
FILE_PATHS = {
    "<1bn":r"Less_than_1bn.xlsx",
    "1bn to 5bn": r"1bn_to_5bn.xlsx",
    "5bn to 10bn":r"5bn_to_10bn.xlsx",
    "10bn to 20bn":r"10bn_to_20bn.xlsx",
    ">20bn":r"Above_20bn.xlsx",
    "All": r"All.xlsx"
}

date_current = '31-MAR-2025'
date_previous = '31-DEC-2024'

# File paths
file_path_submission_previous = r"December 24 Files/SUBMISSION.tsv"
file_path_submission_current = r"March 25 Files/SUBMISSION.tsv"
file_path_info_previous = r"December 24 Files/INFOTABLE.tsv"
file_path_info_current = r"March 25 Files/INFOTABLE.tsv"
file_path_summary_previous= r"December 24 Files/SUMMARYPAGE.tsv"
file_path_summary_current = r"March 25 Files/SUMMARYPAGE.tsv"
file_path_cover_previous = r"December 24 Files/COVERPAGE.tsv"
file_path_cover_current = r"March 25 Files/COVERPAGE.tsv"
ticker_file_path = r"FNP_Yfinance/fnp_file.xlsx"



# ========== CACHED FUNCTIONS ==========

@st.cache_data
def get_jsonparsed_data(url):
    try:
        from urllib.request import urlopen  # Python 3.x
    except ImportError:
        from urllib2 import urlopen  # Python 2.x
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    return json.loads(data)

@st.cache_data
def read_and_filter_tsv(file_path):
    df = pd.read_csv(file_path, sep='\t', dtype=str)
    df.columns = df.columns.str.strip()
    filtered_df = df[
        (df['PERIODOFREPORT'].isin([date_previous, date_current])) &
        (df['SUBMISSIONTYPE'] == '13F-HR')
    ]
    
    return filtered_df[['ACCESSION_NUMBER', 'CIK', 'PERIODOFREPORT', 'SUBMISSIONTYPE']]
    

@st.cache_data
def read_infotable_tsv(file_path):
    df = pd.read_csv(file_path, sep='\t', dtype=str)
    df.columns = df.columns.str.strip()
    return df

@st.cache_data
def load_initial_data():

    # Read and merge SUBMISSION files
    filtered_current_df = read_and_filter_tsv(file_path_submission_current)
    filtered_previous_df = read_and_filter_tsv(file_path_submission_previous)
    final_submission_df = pd.concat([filtered_current_df, filtered_previous_df], ignore_index=True)

    # Read and merge INFOTABLE files
    info_current_df = read_infotable_tsv(file_path_info_current)
    info_previous_df = read_infotable_tsv(file_path_info_previous)
    merged_info_df = pd.concat([info_current_df, info_previous_df], ignore_index=True)

    # Read and merge COVERPAGE + SUMMARYPAGE
    cover_current_df = pd.read_csv(file_path_cover_current, sep='\t', dtype=str)
    cover_previous_df = pd.read_csv(file_path_cover_previous, sep='\t', dtype=str)
    final_coverpage_df = pd.concat([cover_current_df, cover_previous_df], ignore_index=True)

    summary_current_df = pd.read_csv(file_path_summary_current, sep='\t', dtype=str)
    summary_previous_df = pd.read_csv(file_path_summary_previous, sep='\t', dtype=str)
    final_summarypage_df = pd.concat([summary_current_df, summary_previous_df], ignore_index=True)

    # Filter INFOTABLE based on ACCESSION_NUMBER
    reduced_info_df = merged_info_df[merged_info_df['ACCESSION_NUMBER'].isin(final_submission_df['ACCESSION_NUMBER'])]
    reduced_info_df = reduced_info_df[~reduced_info_df['PUTCALL'].isin(['Put', 'Call'])]
    
    # Drop unwanted columns
    columns_to_drop = [
        'INFOTABLE_SK', 'SSHPRNAMTTYPE', 'PUTCALL', 'INVESTMENTDISCRETION', 'OTHERMANAGER',
        'VOTING_AUTH_SOLE', 'VOTING_AUTH_SHARED', 'VOTING_AUTH_NONE'
    ]

    reduced_info_df = reduced_info_df.drop(columns=columns_to_drop, errors='ignore')
    reduced_info_df['CUSIP'] = reduced_info_df['CUSIP'].str.zfill(9).str.upper()


    return final_submission_df, reduced_info_df, final_coverpage_df, final_summarypage_df

@st.cache_data
def load_ticker_data():
    cusip_ticker_df = pd.read_excel(ticker_file_path, dtype=str)
    cusip_ticker_df.columns = cusip_ticker_df.columns.str.strip()
    cusip_ticker_df = cusip_ticker_df.dropna(subset=['Ticker'])
    cusip_ticker_df['CUSIP'] = cusip_ticker_df['CUSIP'].str.zfill(9).str.upper()
    return cusip_ticker_df

# ========== MAIN CODE ==========

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #DBDBDB;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #00448B !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

@st.cache_data
def load_data(file_path):
    try:
        xls = pd.ExcelFile(file_path, engine='openpyxl')
        net_additions = pd.read_excel(xls, sheet_name='Net Additions', engine='openpyxl')
        net_exits = pd.read_excel(xls, sheet_name='Net Exit', engine='openpyxl')
        asset_managers = pd.read_excel(xls, sheet_name='Asset Managers', engine='openpyxl')
        return net_additions, net_exits, asset_managers
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def color_rows(row):
    action = str(row['Action']).upper()
    if action == 'A':
        return ['background-color: green'] * len(row)
    elif action == 'E':
        return ['background-color: red'] * len(row)
    elif action == 'I':
        style = [''] * len(row)
        issuer_col = [col for col in row.index if 'NAMEOFISSUER' in col.upper()]
        if issuer_col:
            style[row.index.get_loc(issuer_col[0])] = 'background-color: green'
        return style
    elif action == 'D':
        style = [''] * len(row)
        issuer_col = [col for col in row.index if 'NAMEOFISSUER' in col.upper()]
        if issuer_col:
            style[row.index.get_loc(issuer_col[0])] = 'background-color: red'
        return style
    else:
        return [''] * len(row)

def main():
    # Load all initial data
    final_submission_df, reduced_info_df, final_coverpage_df, final_summarypage_df = load_initial_data()
    cusip_ticker_df = load_ticker_data()
    
    st.sidebar.image("Logo/logo.png", width=200)
    st.sidebar.header("Module Selector")
    module_option = st.sidebar.selectbox("Choose Module:", 
        ["Consolidated Holding Analysis", "Holding Analysis by Asset Managers", "Holding Analysis by Individual Stock"])

    if module_option == "Holding Analysis by Asset Managers":
        st.title("13-F Analysis Dashboard")
        st.sidebar.header("Asset Manager Filters")
        current_cik_df = final_submission_df[final_submission_df['PERIODOFREPORT'] == date_current]
        previous_cik_df = final_submission_df[final_submission_df['PERIODOFREPORT'] == date_previous]

        current_cik_df = current_cik_df.drop('SUBMISSIONTYPE', axis=1)
        previous_cik_df = previous_cik_df.drop('SUBMISSIONTYPE', axis=1)
        
        current_cik_df = current_cik_df.merge(final_coverpage_df[['ACCESSION_NUMBER', 'FILINGMANAGER_NAME']], on='ACCESSION_NUMBER', how='left')
        previous_cik_df = previous_cik_df.merge(final_coverpage_df[['ACCESSION_NUMBER', 'FILINGMANAGER_NAME']], on='ACCESSION_NUMBER', how='left')

        asset_manager_list = current_cik_df['FILINGMANAGER_NAME'].tolist()
        selected_managers = st.sidebar.multiselect("Select Asset Managers:", asset_manager_list)
        
       
        # Dropdown for ACTION filter (after asset manager selection)
        action_options = ["Additions", "Exits", "Increase", "Decrease","All"]  # Add more if there are other action types
        selected_action = st.sidebar.selectbox("Filter by:", action_options)
        fetch_clicked = st.sidebar.button("Fetch")
        
        def cik_data(managers):
            @st.cache_data
            def extract_issuer_value_dict(df, reduced_info_df, manager):
                subset = df[df['FILINGMANAGER_NAME'] == manager]
                accessions = subset['ACCESSION_NUMBER'].unique()
                filtered = reduced_info_df[reduced_info_df['ACCESSION_NUMBER'].isin(accessions)]
                
                # Clean and convert shares to numeric
                filtered.loc[:, 'SSHPRNAMT'] = pd.to_numeric(
                    filtered['SSHPRNAMT'].astype(str).str.replace(',', ''), errors='coerce'
                )
                
                grouped = (
                    filtered.groupby('NAMEOFISSUER', as_index=False)['SSHPRNAMT']
                    .sum()
                )
                
                # Convert to dictionary for fast lookup
                return dict(zip(grouped['NAMEOFISSUER'], grouped['SSHPRNAMT']))
        
            def build_final_table(current_df, previous_df, reduced_info_df):
                final_rows = []
                col_current = str(current_df['PERIODOFREPORT'].iloc[0])
                col_previous = str(previous_df['PERIODOFREPORT'].iloc[0])
                
                for manager in managers:
                    curr_dict = extract_issuer_value_dict(current_df, reduced_info_df, manager)
                    prev_dict = extract_issuer_value_dict(previous_df, reduced_info_df, manager)
                    all_issuers = sorted(set(curr_dict.keys()).union(prev_dict.keys()))
                    
                    for issuer in all_issuers:
                        prev_val = prev_dict.get(issuer, '')
                        curr_val = curr_dict.get(issuer, '')
                        
                        # Determine Action
                        if prev_val == '' and curr_val != '':
                            action = 'Additions'  # Addition
                        elif prev_val != '' and curr_val == '':
                            action = 'Exits'  # Exit
                        elif prev_val != '' and curr_val != '':
                            try:
                                if float(curr_val) > float(prev_val):
                                    action = 'Increase'  # Increase
                                elif float(curr_val) < float(prev_val):
                                    action = 'Decrease'  # Decrease
                                else:
                                    action = 'No Change'  # No change
                            except:
                                action = 'No Change'
                        else:
                            action = 'No Change'
                        
                        final_rows.append({
                            'Asset Manager': manager,
                            'Name of Stock': issuer,
                            f'No of shares ({col_previous})': prev_val,
                            f'No of shares ({col_current})': curr_val,
                            'ACTION': action
                        })
                
                return pd.DataFrame(final_rows)
            
            final_df = build_final_table(current_cik_df, previous_cik_df, reduced_info_df)
            return final_df


        if fetch_clicked and selected_managers:
            with st.spinner("Fetching Data"):
                df = cik_data(selected_managers)
                
                # Apply ACTION filter if not "All"
                if selected_action != "All" and "ACTION" in df.columns:
                    df = df[df['ACTION'].astype(str).str.upper() == selected_action.upper()]

                # Apply styling if 'Action' column exists
                display_df = df.drop(columns=['ACTION'], errors='ignore')
                if 'Action' in df.columns:
                    styled_df = display_df.style.apply(color_rows, axis=1)
                    st.dataframe(styled_df, use_container_width=True)
                else:
                    st.dataframe(df, use_container_width=True)
        elif fetch_clicked:
            st.warning("Please select at least one asset manager.")
    
    elif module_option == "Consolidated Holding Analysis":
        st.sidebar.header("AUM Range")
        aum_options = ["<1bn", "1bn to 5bn", "5bn to 10bn", "10bn to 20bn", ">20bn", "All"]
        selected_aum = st.sidebar.selectbox("Select AUM Range:", aum_options)
        file_path = FILE_PATHS[selected_aum]
        
        net_additions, net_exits, asset_managers = load_data(file_path)
        if net_additions.empty or net_exits.empty or asset_managers.empty:
            return

        # Clean and rename
        net_additions.columns = net_additions.columns.str.strip()
        net_exits.columns = net_exits.columns.str.strip()
        asset_managers.columns = asset_managers.columns.str.strip()
        
        net_additions['Additions'] = pd.to_numeric(net_additions['Additions'], errors='coerce')
        net_exits['Exits'] = pd.to_numeric(net_exits['Exits'], errors='coerce')
        
        for df in [net_additions, net_exits]:
            if 'market_cap' in df.columns:
                df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
                df['Market Cap (Mn)'] = (df['market_cap'] / 1_000_000).round()
        
        rename_map = {
            'company_name': 'Company',
            'industry': 'Industry',
            'sector': 'Sector',
            '1_year_change_percent': '1_year_change_percent',
            'category': 'Category',
            'listing_date': 'Listing date'
        }
        
        net_additions = net_additions.rename(columns=rename_map)
        net_exits = net_exits.rename(columns=rename_map)
        
        for df in [net_additions, net_exits]:
            df['Listing date'] = pd.to_datetime(df['Listing date'], errors='coerce').dt.date
            df.dropna(subset=['Listing date'], inplace=True)
        
        st.sidebar.header("Filters")
        selection_type = st.sidebar.selectbox("Select Type:", ["Additions", "Exits", "Asset Managers"])
        
        if selection_type == "Asset Managers":
            st.dataframe(asset_managers.drop(columns=["PERIODOFREPORT", "SUBMISSIONTYPE"]), 
                        use_container_width=True, hide_index=True)
            return
        
        include_ipos = st.sidebar.checkbox("Include IPOs") if selection_type != "Exits" else False
        st.title("13-F Analysis Dashboard")
        
        current_df = net_additions if selection_type == "Additions" else net_exits
        sort_column = 'Additions' if selection_type == "Additions" else 'Exits'
        
        categories = ['All'] + sorted(current_df['Category'].dropna().unique())
        selected_category = st.sidebar.selectbox("Select Categorization:", categories)
        
        top_n = st.sidebar.selectbox("Select Top N:", [10, 20, "All"], index=0)
        
        if 'Market Cap (Mn)' in current_df.columns:
            current_df['Market Cap (Mn)'] = pd.to_numeric(current_df['Market Cap (Mn)'], errors='coerce')
            cap_series = current_df['Market Cap (Mn)'].dropna()
            
            if not cap_series.empty:
                min_cap = int(cap_series.min())
                raw_max_cap = cap_series.max()
                max_cap = int(math.ceil(raw_max_cap / 1000.0)) * 1000
                
                col1, col2 = st.sidebar.columns(2)
                min_market_cap = col1.number_input("Min Market Cap (Mn):", min_value=0, value=min_cap, step=100)
                max_market_cap = col2.number_input("Max Market Cap (Mn):", min_value=min_market_cap, value=max_cap, step=100)
            else:
                st.warning("No valid Market Cap data available.")
                min_market_cap, max_market_cap = None, None
        else:
            st.warning("Market Cap (Mn) column not found.")
            min_market_cap, max_market_cap = None, None
        
        industries = ['All'] + sorted(current_df['Industry'].dropna().unique())
        selected_industry = st.sidebar.selectbox("Select Industry:", industries)
        
        if selected_industry == 'All':
            st.sidebar.text("Sector filter is disabled when 'All' is selected in Industry.")
            selected_sector = None
        else:
            applicable_sectors = sorted(current_df[current_df['Industry'] == selected_industry]['Sector'].dropna().unique())
            selected_sector = st.sidebar.selectbox("Select Sector:", ['All'] + applicable_sectors)
        
        if st.sidebar.button("Apply Filters"):
            df_filtered = current_df.copy()
            
            if selected_category != 'All':
                df_filtered = df_filtered[df_filtered['Category'] == selected_category]
            
            if selected_category != 'ETF' and min_market_cap is not None and 'Market Cap (Mn)' in df_filtered.columns:
                df_filtered = df_filtered[
                    (df_filtered['Market Cap (Mn)'] >= min_market_cap) &
                    (df_filtered['Market Cap (Mn)'] <= max_market_cap)
                ]
            
            if selected_category != 'ETF':
                if selected_industry != 'All':
                    df_filtered = df_filtered[df_filtered['Industry'] == selected_industry]
                if selected_sector and selected_sector != 'All':
                    df_filtered = df_filtered[df_filtered['Sector'] == selected_sector]
            
            if not include_ipos:
                start_date = pd.to_datetime(date_previous).date()
                end_date = pd.to_datetime(date_current).date()
                date_mask = (df_filtered['Listing date'] >= start_date) & (df_filtered['Listing date'] <= end_date)
                df_filtered = df_filtered[~date_mask]
            
            if top_n == "All":
                top_filtered = df_filtered.copy()
            else:
                top_filtered = df_filtered.nlargest(top_n, sort_column).copy()
            
            if '1_year_change_percent' in top_filtered.columns:
                top_filtered['1_year_change_percent'] = pd.to_numeric(top_filtered['1_year_change_percent'], errors='coerce')
                top_filtered['1_year_change_percent'] = top_filtered['1_year_change_percent'].apply(
                    lambda x: f"{int(round(x))}%" if pd.notnull(x) else ""
                )
            
            top_filtered['Market Cap (Mn)'] = top_filtered['Market Cap (Mn)'].apply(
                lambda x: f"{int(round(x)):,}" if pd.notnull(x) else ""
            )
            
            if selected_category == 'ETF':
                st.dataframe(
                    top_filtered[['CUSIP', 'Ticker', sort_column, 'Company', 'Market Cap (Mn)', 'Category', 'Listing date']],
                    use_container_width=True, hide_index=True
                )
            else:
                st.dataframe(
                    top_filtered[['CUSIP', 'Ticker', sort_column, 'Company', 'Industry', 'Sector', 'Market Cap (Mn)', 
                                '1_year_change_percent', 'Category', 'Listing date']],
                    use_container_width=True, hide_index=True
                )

    elif module_option == "Holding Analysis by Individual Stock":
        st.title("13-F Analysis Dashboard")
        st.sidebar.header("Stock Filter")
        
        ticker_list = cusip_ticker_df['company_name'].dropna().unique().tolist()
        stock_filter = st.sidebar.selectbox("Search by Stock Name", ticker_list)
        
        selection_types = st.sidebar.selectbox("Select Type:", 
            ["Managers in Current Qtr", "Managers in Previous Qtr", "Additions", "Exits"])
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            min_aum = st.number_input("Min AUM (In Mn)", min_value=0, value=0, step=10)
        with col2:
            max_aum = st.number_input("Max AUM (In Mn)", min_value=0, value=500000000, step=10)
        
        ticker_fetched = None
        if stock_filter:
            matches = cusip_ticker_df[
                cusip_ticker_df['company_name'].str.contains(stock_filter, case=False) |
                cusip_ticker_df['Ticker'].str.contains(stock_filter, case=False)
            ]
            if not matches.empty:
                ticker_fetched = matches.iloc[0]['Ticker']
                st.session_state['ticker_fetched'] = ticker_fetched

        @st.cache_data
        def am3(_ticker, _final_submission_df, _reduced_info_df, _final_coverpage_df, _final_summarypage_df, _cusip_ticker_df):
            # ---- Step 1: Get CUSIP list for the Ticker ----
            cusip_str = _cusip_ticker_df.loc[_cusip_ticker_df['Ticker'] == _ticker, 'CUSIP']
            cusip_list = cusip_str.iloc[0].split(',') if not cusip_str.empty else []
            cusip_list = [c.strip() for c in cusip_list]
            
            # ---- Step 2: Filter ACCESSION_NUMBERs for both reporting periods ----
            primary_previous = _final_submission_df[_final_submission_df['PERIODOFREPORT'] == date_previous]['ACCESSION_NUMBER'].unique()
            primary_current = _final_submission_df[_final_submission_df['PERIODOFREPORT'] == date_current]['ACCESSION_NUMBER'].unique()
            
            # ---- Step 3: Match ACCESSION_NUMBERs in reduced_info_df for each period ----
            matched_previous = _reduced_info_df[
                (_reduced_info_df['CUSIP'].isin(cusip_list)) &
                (_reduced_info_df['ACCESSION_NUMBER'].isin(primary_previous))
            ]['ACCESSION_NUMBER'].unique()
            
            matched_current = _reduced_info_df[
                (_reduced_info_df['CUSIP'].isin(cusip_list)) &
                (_reduced_info_df['ACCESSION_NUMBER'].isin(primary_current))
            ]['ACCESSION_NUMBER'].unique()
            
            # ---- Step 4: Prepare Matched ACCESSION_NUMBERs with CIKs ----
            df_previous = _final_submission_df[['ACCESSION_NUMBER', 'CIK']].drop_duplicates()
            df_previous = df_previous[df_previous['ACCESSION_NUMBER'].isin(matched_previous)]
            df_previous.columns = ['Matched_Reduced_Info_ACCESSION_NUMBER_previous', 'CIK_previous']
            
            df_current = _final_submission_df[['ACCESSION_NUMBER', 'CIK']].drop_duplicates()
            df_current = df_current[df_current['ACCESSION_NUMBER'].isin(matched_current)]
            df_current.columns = ['Matched_Reduced_Info_ACCESSION_NUMBER_current', 'CIK_current']
            
            # Reset index for clean merging
            df_previous.reset_index(drop=True, inplace=True)
            df_current.reset_index(drop=True, inplace=True)
            
            # ---- Step 5: Calculate Additions and Exits based on CIKs ----
            additions = list(set(df_current['CIK_current']) - set(df_previous['CIK_previous']))
            exits = list(set(df_previous['CIK_previous']) - set(df_current['CIK_current']))
            
            # ---- Step 6: Create Final Combined DataFrame ----
            max_len = max(len(df_previous), len(df_current))
            df_previous = df_previous.reindex(range(max_len)).reset_index(drop=True)
            df_current = df_current.reindex(range(max_len)).reset_index(drop=True)
            
            add_exit_df = pd.DataFrame({
                'Additions': pd.Series(additions),
                'Exits': pd.Series(exits)
            })
            
            add_exit_df = add_exit_df.reindex(range(max_len)).reset_index(drop=True)
            
            # Map ACCESSION_NUMBERs to Additions and Exits
            current_cik_to_acc = df_current.set_index('CIK_current')['Matched_Reduced_Info_ACCESSION_NUMBER_current'].to_dict()
            previous_cik_to_acc = df_previous.set_index('CIK_previous')['Matched_Reduced_Info_ACCESSION_NUMBER_previous'].to_dict()
            
            add_exit_df['Additions_Acc'] = add_exit_df['Additions'].map(current_cik_to_acc)
            add_exit_df['Exits_Acc'] = add_exit_df['Exits'].map(previous_cik_to_acc)
            
            stock_df_combined = pd.concat([df_previous, df_current, add_exit_df], axis=1)
            
            # ---- Step 7: Use COVERPAGE and SUMMARYPAGE for Asset Manager Name and AUM ----
            merged_1 = pd.merge(
                _final_coverpage_df[['ACCESSION_NUMBER', 'FILINGMANAGER_NAME']],
                _final_summarypage_df[['ACCESSION_NUMBER', 'TABLEVALUETOTAL']],
                on='ACCESSION_NUMBER', how='inner'
            )
            
            am_data = pd.merge(
                merged_1,
                _final_submission_df[['ACCESSION_NUMBER', 'CIK']],
                on='ACCESSION_NUMBER', how='inner'
            )
            
            am_data.columns = am_data.columns.str.strip()
            am_data = am_data.rename(columns={
                'FILINGMANAGER_NAME': 'Asset Manager Name',
                'TABLEVALUETOTAL': 'AUM ($000)'
            })
            
            # Helper function to extract and sort AM and AUM data from am_data
            def get_sorted_am_data(accession_numbers, label_am, label_aum):
                df = am_data[am_data['ACCESSION_NUMBER'].isin(accession_numbers)][
                    ['Asset Manager Name', 'AUM ($000)']
                ].copy()
                df = df.sort_values(by='AUM ($000)', ascending=False, key=pd.to_numeric)
                df.columns = [label_am, label_aum]
                return df.reset_index(drop=True)
            
            # Get sorted data for each category
            current_q_df = get_sorted_am_data(
                df_current['Matched_Reduced_Info_ACCESSION_NUMBER_current'],
                'Current_Q_AM', 'Current_Q_AM_AUM'
            )
            
            previous_q_df = get_sorted_am_data(
                df_previous['Matched_Reduced_Info_ACCESSION_NUMBER_previous'],
                'Previous_Q_AM', 'Previous_Q_AM_AUM'
            )
            
            additions_acc = add_exit_df['Additions_Acc'].dropna().tolist()
            additions_df = get_sorted_am_data(additions_acc, 'Additions_AM', 'Additions_AM_AUM')
            
            exits_acc = add_exit_df['Exits_Acc'].dropna().tolist()
            exits_df = get_sorted_am_data(exits_acc, 'Exits_AM', 'Exits_AM_AUM')
            
            # Pad all dataframes to same length
            max_len = max(len(current_q_df), len(previous_q_df), len(additions_df), len(exits_df))
            current_q_df = current_q_df.reindex(range(max_len)).reset_index(drop=True)
            previous_q_df = previous_q_df.reindex(range(max_len)).reset_index(drop=True)
            additions_df = additions_df.reindex(range(max_len)).reset_index(drop=True)
            exits_df = exits_df.reindex(range(max_len)).reset_index(drop=True)
            
            # Combine all into a final DataFrame
            final_am_df = pd.concat([current_q_df, previous_q_df, additions_df, exits_df], axis=1)
            
            return final_am_df

        apply_filters = st.sidebar.button("Fetch")
        
        if apply_filters and ticker_fetched:
            with st.spinner("Fetching Data"):
                data = am3(
                    ticker_fetched, 
                    final_submission_df, 
                    reduced_info_df, 
                    final_coverpage_df, 
                    final_summarypage_df, 
                    cusip_ticker_df
                )
                df = data.copy()
                
                # Convert AUM columns to millions
                aum_columns = ["Current_Q_AM_AUM", "Previous_Q_AM_AUM", "Additions_AM_AUM", "Exits_AM_AUM"]
                for col in aum_columns:
                    if col in df.columns:
                        df[col] = (pd.to_numeric(df[col], errors='coerce') / 1e6).round(1)
                
                # Define display and filter columns
                if selection_types == "Managers in Current Qtr":
                    columns_to_display = ["Current_Q_AM", "Current_Q_AM_AUM"]
                    aum_column = "Current_Q_AM_AUM"
                elif selection_types == "Managers in Previous Qtr":
                    columns_to_display = ["Previous_Q_AM", "Previous_Q_AM_AUM"]
                    aum_column = "Previous_Q_AM_AUM"
                elif selection_types == "Additions":
                    columns_to_display = ["Additions_AM", "Additions_AM_AUM"]
                    aum_column = "Additions_AM_AUM"
                elif selection_types == "Exits":
                    columns_to_display = ["Exits_AM", "Exits_AM_AUM"]
                    aum_column = "Exits_AM_AUM"
                else:
                    columns_to_display = df.columns
                    aum_column = None
                
                # Apply AUM filtering
                if aum_column and aum_column in df.columns:
                    df = df[(df[aum_column] >= min_aum) & (df[aum_column] <= max_aum)]
                
                # Final display
                filtered_columns = [col for col in columns_to_display if col in df.columns]
                st.dataframe(df[filtered_columns], use_container_width=True)

if __name__ == "__main__":
    main()