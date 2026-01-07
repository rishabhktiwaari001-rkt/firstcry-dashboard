import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FirstCry Store Dashboard", layout="wide")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("⚙️ Dashboard Settings")
    
    # 1. DATA UPLOAD
    article_file = st.file_uploader("Upload Article Sale Report (CSV)", type=['csv'])
    
    st.markdown("---")
    st.write("### 🖼️ Branding (Optional)")
    st.caption("Place 'logo.png' & 'store.png' in folder for auto-load.")
    
    # Fallback Uploads
    if not os.path.exists("logo.png") and not os.path.exists("logo.jpg"):
        st.file_uploader("Upload Logo", type=['png', 'jpg'])
    if not os.path.exists("store.png") and not os.path.exists("store.jpg"):
        st.file_uploader("Upload Store Photo", type=['png', 'jpg'])

# --- HEADER LOGIC ---
col1, col2, col3 = st.columns([1, 4, 2])

# Logo
with col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=150)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", width=150)
    else: st.write("📷 *No Logo*")

# Title
with col2:
    st.title("🛍️ FirstCry Store Dashboard")
    st.markdown("### Performance & Retail KPIs")

# Store Photo
with col3:
    if os.path.exists("store.png"): st.image("store.png", width=300)
    elif os.path.exists("store.jpg"): st.image("store.jpg", width=300)

st.markdown("---")

# --- MAIN LOGIC ---
if article_file:
    try:
        # 1. LOAD & CLEAN
        df = pd.read_csv(article_file)
        df.columns = df.columns.str.strip()
        
        rename_map = {'SalePerson': 'SalesPerson', 'Date': 'BillDate', 'Bill Date': 'BillDate', 'BillDate': 'BillDate'}
        df.rename(columns=rename_map, inplace=True)

        # 2. DATE FIX
        df['BillDate'] = pd.to_datetime(df['BillDate'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['BillDate'])
        
        # 3. WEEK LOGIC
        df['Day_Num'] = df['BillDate'].dt.day
        df['Week'] = (df['Day_Num'] - 1) // 7 + 1
        df['Week_Label'] = "Week " + df['Week'].astype(str)
        df['Day'] = df['BillDate'].dt.strftime('%A')
        
        # 4. SEPARATE STREAMS
        mask_mem = df['ProductName'].str.contains('Membership', case=False, na=False) | (df['Category'] == 'GiftCertificate')
        df_memberships = df[mask_mem].copy()

        exclusions = ['Free Sample Category']
        df_sales = df[~df['Category'].isin(exclusions)].copy()

        # 5. MASTER KPI CALCULATIONS (GSV)
        staff_stats = df_sales.groupby('SalesPerson').agg(
            Total_GSV=('GSV', 'sum'),
            Total_Qty=('Quantity', 'sum')
        ).reset_index()

        bill_counts = df_sales.groupby('SalesPerson')['InvoiceNumber'].nunique().reset_index(name='Total_Bills')
        
        # Single Bills
        bill_group = df_sales.groupby(['InvoiceNumber', 'SalesPerson'])['Quantity'].sum().reset_index()
        single_bills = bill_group[bill_group['Quantity'] == 1]
        sb_counts = single_bills.groupby('SalesPerson').size().reset_index(name='Single_Bills')
        
        # Merge
        master_df = pd.merge(staff_stats, bill_counts, on='SalesPerson', how='left')
        master_df = pd.merge(master_df, sb_counts, on='SalesPerson', how='left').fillna(0)
        master_df['Total_Bills'] = master_df['Total_Bills'].replace(0, 1)
        
        # Ratios
        master_df['AVPT'] = (master_df['Total_GSV'] / master_df['Total_Bills']).round(0)
        master_df['AUPT'] = (master_df['Total_Qty'] / master_df['Total_Bills']).round(2)
        master_df['Single_Bill_%'] = ((master_df['Single_Bills'] / master_df['Total_Bills']) * 100).round(1)

        # Ranking
        master_df = master_df.sort_values('Total_GSV', ascending=False).reset_index(drop=True)
        master_df.index += 1
        master_df['Rank'] = master_df.index
        master_df = master_df[['Rank', 'SalesPerson', 'Total_GSV', 'Total_Qty', 'Total_Bills', 'AVPT', 'AUPT', 'Single_Bills', 'Single_Bill_%']]

        # --- TABS ---
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
                    w_stats = weekly_df.groupby('SalesPerson').agg(W_GSV=('GSV', 'sum'), W_Qty=('Quantity', 'sum')).reset_index()
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

        # --- TAB 2: SIMPLIFIED & TRANSPOSED CATEGORY ANALYSIS ---
        with tab2:
            st.subheader("🔍 Category & Sub-Category Performance")
            
            # Selectors
            cats = ['All'] + sorted(list(df_sales['Category'].dropna().unique()))
            col_cat, col_sub, col_toggle = st.columns([2, 2, 1])
            
            selected_cat = col_cat.selectbox("Select Category", cats)
            
            if selected_cat != 'All':
                sub_cats = ['All'] + sorted(list(df_sales[df_sales['Category'] == selected_cat]['SubCategory'].dropna().unique()))
            else:
                sub_cats = ['All']
            
            selected_sub = col_sub.selectbox("Select Sub-Category", sub_cats)
            
            # Filter Data
            filtered_df = df_sales.copy()
            if selected_cat != 'All': filtered_df = filtered_df[filtered_df['Category'] == selected_cat]
            if selected_sub != 'All': filtered_df = filtered_df[filtered_df['SubCategory'] == selected_sub]

            # Calculation
            if not filtered_df.empty:
                # 1. Calculate Total for this view (to get %)
                total_view_gsv = filtered_df['GSV'].sum()
                
                # 2. Group by Staff
                cat_stats = filtered_df.groupby('SalesPerson').agg(
                    Sales=('GSV', 'sum'),
                    Qty=('Quantity', 'sum'),
                    Bills=('InvoiceNumber', 'nunique')
                ).reset_index()
                
                # 3. Add Percentage Column
                cat_stats['Contrib %'] = (cat_stats['Sales'] / total_view_gsv) * 100
                
                # 4. Sort and Clean
                cat_stats = cat_stats.sort_values('Sales', ascending=False).set_index('SalesPerson')
                
                # 5. TRANSPOSE TOGGLE
                transpose_view = col_toggle.checkbox("🔄 Transpose View")
                
                st.markdown(f"**Total Sales for Selection:** ₹{total_view_gsv:,.2f}")
                
                if transpose_view:
                    # Show Horizontal (Staff Name on Top, KPIs on Side)
                    st.dataframe(
                        cat_stats.T.style.format("{:.2f}"), 
                        use_container_width=True
                    )
                else:
                    # Show Vertical (Staff Name on Side, KPIs on Top)
                    # Reorder columns to put % next to sales
                    cat_stats = cat_stats[['Sales', 'Contrib %', 'Qty', 'Bills']]
                    st.dataframe(
                        cat_stats.style.format({
                            'Sales': '₹{:.2f}', 
                            'Contrib %': '{:.1f}%'
                        }), 
                        use_container_width=True
                    )
                
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

else:
    st.info("👈 Please upload the data file.")
