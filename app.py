import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FirstCry Chowk Store Dashboard", layout="wide")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("⚙️ Dashboard Settings")
    st.write("Upload Data File below to start.")
    
    # DATA UPLOAD (Always required for new reports)
    article_file = st.file_uploader("Upload Article Sale Report (CSV)", type=['csv'])

# --- HEADER LOGIC (AUTO-DETECT IMAGES) ---
col1, col2, col3 = st.columns([1, 4, 2])

# 1. LOGO HANDLING
with col1:
    # Check if 'logo.png' or 'logo.jpg' exists in the folder
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
    elif os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=150)
    else:
        # Fallback: Allow upload if file is missing
        logo_up = st.file_uploader("Upload Logo", type=['png', 'jpg'])
        if logo_up: st.image(logo_up, width=150)

# 2. TITLE
with col2:
    st.title("🛍️ FirstCry Store Dashboard")
    st.markdown("### Performance & Retail KPIs")

# 3. STORE PHOTO HANDLING
with col3:
    # Check if 'store.png' or 'store.jpg' exists
    if os.path.exists("store.png"):
        st.image("store.png", width=300)
    elif os.path.exists("store.jpg"):
        st.image("store.jpg", width=300)
    else:
        # Fallback
        store_up = st.file_uploader("Upload Store Photo", type=['png', 'jpg'])
        if store_up: st.image(store_up, width=300)

st.markdown("---")

# --- MAIN LOGIC ---
if article_file:
    try:
        # 1. LOAD DATA
        df = pd.read_csv(article_file)
        
        # 2. CLEAN COLUMN NAMES
        df.columns = df.columns.str.strip()
        
        # Auto-fix Column Name Mismatches
        rename_map = {
            'SalePerson': 'SalesPerson', 
            'Date': 'BillDate',
            'Bill Date': 'BillDate',
            'BillDate': 'BillDate'
        }
        df.rename(columns=rename_map, inplace=True)

        # 3. CHECK FOR REQUIRED COLUMNS
        required_columns = ['SalesPerson', 'GSV', 'Category', 'Quantity', 'InvoiceNumber', 'BillDate', 'ProductName']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            st.error(f"🚨 **File Error:** Missing columns: {missing_cols}")
            st.warning("Please make sure you uploaded the **Article Sale Report**.")
            st.stop()

        # 4. ROBUST DATE CONVERSION
        df['BillDate'] = pd.to_datetime(df['BillDate'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['BillDate'])
        
        if df.empty:
            st.error("🚨 **Date Error:** All dates failed to load. Please check your CSV date format.")
            st.stop()

        # --- RETAIL WEEK LOGIC (1-7 = Week 1) ---
        df['Day_Num'] = df['BillDate'].dt.day
        df['Week'] = (df['Day_Num'] - 1) // 7 + 1
        df['Week_Label'] = "Week " + df['Week'].astype(str)
        df['Day'] = df['BillDate'].dt.strftime('%A')
        
        # 5. SEPARATE STREAMS
        
        # Stream A: MEMBERSHIPS
        mask_mem = df['ProductName'].str.contains('Membership', case=False, na=False) | (df['Category'] == 'GiftCertificate')
        df_memberships = df[mask_mem].copy()

        # Stream B: SALES (Exclude Free Samples)
        exclusions = ['Free Sample Category']
        df_sales = df[~df['Category'].isin(exclusions)].copy()

        # 6. KPI CALCULATIONS (GSV)
        
        # Staff Stats
        staff_stats = df_sales.groupby('SalesPerson').agg(
            Total_GSV=('GSV', 'sum'),
            Total_Qty=('Quantity', 'sum')
        ).reset_index()

        bill_counts = df_sales.groupby('SalesPerson')['InvoiceNumber'].nunique().reset_index(name='Total_Bills')
        
        # Single Bill Analysis
        bill_group = df_sales.groupby(['InvoiceNumber', 'SalesPerson'])['Quantity'].sum().reset_index()
        single_bills = bill_group[bill_group['Quantity'] == 1]
        sb_counts = single_bills.groupby('SalesPerson').size().reset_index(name='Single_Bills')
        
        # Merge Master
        master_df = pd.merge(staff_stats, bill_counts, on='SalesPerson', how='left')
        master_df = pd.merge(master_df, sb_counts, on='SalesPerson', how='left').fillna(0)
        
        # Avoid Division by Zero
        master_df['Total_Bills'] = master_df['Total_Bills'].replace(0, 1) 
        
        # Calculate Incentives
        master_df['AVPT'] = (master_df['Total_GSV'] / master_df['Total_Bills']).round(0)
        master_df['AUPT'] = (master_df['Total_Qty'] / master_df['Total_Bills']).round(2)
        master_df['Single_Bill_%'] = ((master_df['Single_Bills'] / master_df['Total_Bills']) * 100).round(1)

        # ADD RANKING
        master_df = master_df.sort_values('Total_GSV', ascending=False).reset_index(drop=True)
        master_df.index = master_df.index + 1
        master_df['Rank'] = master_df.index

        # Reorder columns
        cols = ['Rank', 'SalesPerson', 'Total_GSV', 'Total_Qty', 'Total_Bills', 'AVPT', 'AUPT', 'Single_Bills', 'Single_Bill_%']
        master_df = master_df[cols]

        # --- VISUALS ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏆 Rankings & Incentives", 
            "🔍 Category Analysis", 
            "💳 Membership Hub", 
            "📅 Sales Reports", 
            "⚠️ Single Bills"
        ])

        with tab1:
            st.subheader("🏆 Staff Rankings (GSV)")
            st.dataframe(master_df.style.format({'Total_GSV': '₹{:.2f}', 'AVPT': '₹{:.0f}'}), use_container_width=True)
            
            st.markdown("---")
            st.write("### 🎯 Weekly Incentive Qualifiers (Current Week)")
            
            if not df['Week'].empty:
                current_week = df['Week'].max()
                weekly_df = df_sales[df_sales['Week'] == current_week]
                
                if not weekly_df.empty:
                    w_stats = weekly_df.groupby('SalesPerson').agg(
                        W_GSV=('GSV', 'sum'), 
                        W_Qty=('Quantity', 'sum')
                    ).reset_index()
                    w_bills = weekly_df.groupby('SalesPerson')['InvoiceNumber'].nunique().reset_index(name='W_Bills')
                    w_merged = pd.merge(w_stats, w_bills, on='SalesPerson')
                    
                    w_merged['W_AVPT'] = (w_merged['W_GSV'] / w_merged['W_Bills'])
                    w_merged['W_AUPT'] = (w_merged['W_Qty'] / w_merged['W_Bills'])
                    
                    winners = w_merged[(w_merged['W_AUPT'] >= 4) & (w_merged['W_AVPT'] >= 3000)]
                    
                    if not winners.empty:
                        st.success(f"🎉 Winners for Week {current_week}")
                        st.dataframe(winners[['SalesPerson', 'W_AVPT', 'W_AUPT']].style.format({'W_AVPT': '₹{:.0f}'}))
                    else:
                        st.warning(f"No winners yet for Week {current_week}.")
                else:
                    st.info("No sales data for the current week yet.")

        # --- TAB 2: UPDATED CATEGORY LOGIC ---
        with tab2:
            st.subheader("🔍 Category & Sub-Category Analysis")
            
            # 1. Selectors
            cats = ['All'] + sorted(list(df_sales['Category'].dropna().unique()))
            col_cat, col_sub = st.columns(2)
            selected_cat = col_cat.selectbox("Select Category", cats)
            
            if selected_cat != 'All':
                sub_cats = ['All'] + sorted(list(df_sales[df_sales['Category'] == selected_cat]['SubCategory'].dropna().unique()))
            else:
                sub_cats = ['All']
            
            selected_sub = col_sub.selectbox("Select Sub-Category", sub_cats)
            
            # 2. Filter Data
            filtered_df = df_sales.copy()
            if selected_cat != 'All':
                filtered_df = filtered_df[filtered_df['Category'] == selected_cat]
            if selected_sub != 'All':
                filtered_df = filtered_df[filtered_df['SubCategory'] == selected_sub]

            # 3. Dynamic Grouping
            if not filtered_df.empty:
                if selected_cat == 'All':
                    group_cols = ['Category', 'SalesPerson']
                elif selected_sub == 'All':
                    group_cols = ['SubCategory', 'SalesPerson']
                else:
                    group_cols = ['SalesPerson']

                cat_stats = filtered_df.groupby(group_cols).agg(
                    Sales_GSV=('GSV', 'sum'),
                    Qty=('Quantity', 'sum'),
                    Bills=('InvoiceNumber', 'nunique')
                ).reset_index().sort_values('Sales_GSV', ascending=False)
                
                cat_stats.reset_index(drop=True, inplace=True)
                cat_stats.index += 1
                cat_stats.index.name = 'Rank'
                
                st.write(f"Showing performance by: **{', '.join(group_cols)}**")
                st.dataframe(cat_stats.style.format({'Sales_GSV': '₹{:.2f}'}), use_container_width=True)
                
            else:
                st.warning("No data found for this selection.")

        with tab3:
            st.subheader("💳 Membership Hub")
            if not df_memberships.empty:
                df_memberships['Price_Tier'] = "₹" + df_memberships['GSV'].astype(str)
                day_mem = df_memberships.groupby(['BillDate', 'Price_Tier']).size().unstack(fill_value=0).sort_index(ascending=False)
                st.dataframe(day_mem, use_container_width=True)
            else:
                st.info("No memberships found.")

        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📅 Day-wise Sales")
                day_view = df_sales.groupby(['BillDate', 'Day']).agg(GSV=('GSV', 'sum')).reset_index().sort_values('BillDate', ascending=False)
                st.dataframe(day_view.style.format({'GSV': '₹{:.2f}'}), use_container_width=True)
            with col2:
                st.subheader("🗓️ Week-wise Sales")
                week_view = df_sales.groupby('Week_Label').agg(GSV=('GSV', 'sum')).reset_index()
                st.dataframe(week_view.style.format({'GSV': '₹{:.2f}'}), use_container_width=True)

        with tab5:
            st.subheader("⚠️ Single Bill Risk")
            st.dataframe(master_df[['Rank', 'SalesPerson', 'Total_Bills', 'Single_Bills', 'Single_Bill_%']].style.format({'Single_Bill_%': '{:.1f}%'}), use_container_width=True)

    except Exception as e:
        st.error(f"🚨 An error occurred: {e}")
        st.write("Please send this error message to your developer.")

else:
    st.info("👈 Please upload the data file in the sidebar to begin.")
