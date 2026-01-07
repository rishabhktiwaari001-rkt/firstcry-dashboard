import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FirstCry Master Dashboard (GSV)", layout="wide")

st.title("🛍️ FirstCry Master Dashboard")
st.markdown("Upload **Article Sale Report** to generate the performance tracker.")

# --- SIDEBAR: FILE UPLOAD ---
with st.sidebar:
    st.header("📂 Data Upload")
    article_file = st.file_uploader("Upload Article Sale Report (CSV)", type=['csv'])

# --- MAIN LOGIC ---
if article_file:
    try:
        # 1. LOAD DATA
        df = pd.read_csv(article_file)
        
        # 2. CLEAN COLUMN NAMES (Remove spaces)
        df.columns = df.columns.str.strip()
        
        # 3. AUTO-FIX COLUMN NAMES
        # Sometimes exports use "SalePerson" instead of "SalesPerson"
        rename_map = {
            'SalePerson': 'SalesPerson', 
            'Date': 'BillDate',
            'Bill Date': 'BillDate'
        }
        df.rename(columns=rename_map, inplace=True)

        # 4. SAFETY CHECK: Are we using the right file?
        required_columns = ['SalesPerson', 'GSV', 'Category', 'Quantity', 'InvoiceNumber']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            st.error("🚨 **Error: Missing Columns!**")
            st.warning(f"Your file is missing these columns: {missing_cols}")
            st.info("Did you upload the **Billwise Report** by mistake? Please upload the **Article Sale Report**.")
            st.stop() # Stop execution here to prevent crashing

        # 5. ROBUST DATE CONVERSION
        # Handles slashes (01/01/2026), dashes (01-01-2026), and spaces
        df['BillDate'] = pd.to_datetime(df['BillDate'], dayfirst=True, errors='coerce')
        
        # Check if dates failed parsing
        if df['BillDate'].isna().all():
            st.error("🚨 **Date Error:** Could not read the dates. Please check the date format in your CSV file.")
            st.stop()

        # Add Time Columns
        df['Week'] = df['BillDate'].dt.isocalendar().week
        df['Day'] = df['BillDate'].dt.strftime('%A')
        
        # 6. SEPARATE DATA STREAMS
        
        # Stream A: MEMBERSHIPS
        mask_mem = df['ProductName'].str.contains('Membership', case=False, na=False) | (df['Category'] == 'GiftCertificate')
        df_memberships = df[mask_mem].copy()

        # Stream B: SALES DATA (Exclude Free Samples)
        exclusions = ['Free Sample Category']
        df_sales = df[~df['Category'].isin(exclusions)].copy()

        # 7. KPI CALCULATIONS (ALL ON GSV)
        
        # Group by Staff
        staff_stats = df_sales.groupby('SalesPerson').agg(
            Total_GSV=('GSV', 'sum'),
            Total_Qty=('Quantity', 'sum')
        ).reset_index()

        bill_counts = df_sales.groupby('SalesPerson')['InvoiceNumber'].nunique().reset_index(name='Total_Bills')
        
        # Single Bill Analysis
        bill_group = df_sales.groupby(['InvoiceNumber', 'SalesPerson'])['Quantity'].sum().reset_index()
        single_bills = bill_group[bill_group['Quantity'] == 1]
        sb_counts = single_bills.groupby('SalesPerson').size().reset_index(name='Single_Bills')
        
        # Merge for Master Table
        master_df = pd.merge(staff_stats, bill_counts, on='SalesPerson', how='left')
        master_df = pd.merge(master_df, sb_counts, on='SalesPerson', how='left').fillna(0)
        
        # Calculate Incentives
        master_df['AVPT'] = (master_df['Total_GSV'] / master_df['Total_Bills']).round(0)
        master_df['AUPT'] = (master_df['Total_Qty'] / master_df['Total_Bills']).round(2)
        master_df['Single_Bill_%'] = ((master_df['Single_Bills'] / master_df['Total_Bills']) * 100).round(1)

        # --- DASHBOARD VISUALS ---

        tab1, tab2, tab3, tab4 = st.tabs(["📊 Staff Incentives (GSV)", "💳 Membership Hub", "📅 Day/Week Sales (GSV)", "⚠️ Single Bill Risk"])

        with tab1:
            st.subheader("🏆 Staff Performance (GSV Based)")
            st.dataframe(master_df.style.format({'Total_GSV': '₹{:.2f}', 'AVPT': '₹{:.0f}'}), use_container_width=True)
            
            # Weekly Logic
            st.markdown("---")
            st.write("### 🎯 Weekly Incentive Qualifiers (GSV Based)")
            current_week = df['Week'].max()
            
            # Robust check for empty data
            if pd.isna(current_week):
                st.warning("Could not determine current week. Check Date column.")
            else:
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
                        st.warning("No winners yet for this week.")

        with tab2:
            st.subheader("💳 Membership Analysis")
            if not df_memberships.empty:
                df_memberships['Price_Tier'] = "₹" + df_memberships['GSV'].astype(str)
                # Group and display
                day_mem = df_memberships.groupby(['BillDate', 'Price_Tier']).size().unstack(fill_value=0).sort_index(ascending=False)
                day_mem['Total'] = day_mem.sum(axis=1)
                st.dataframe(day_mem, use_container_width=True)
            else:
                st.info("No memberships found.")

        with tab3:
            col_d, col_w = st.columns(2)
            with col_d:
                st.subheader("📅 Day-wise Sales")
                day_view = df_sales.groupby(['BillDate', 'Day']).agg(Total_GSV=('GSV', 'sum'), Bills=('InvoiceNumber', 'nunique')).reset_index().sort_values('BillDate', ascending=False)
                st.dataframe(day_view.style.format({'Total_GSV': '₹{:.2f}'}), use_container_width=True)
            with col_w:
                st.subheader("🗓️ Week-wise Sales")
                week_view = df_sales.groupby('Week').agg(Total_GSV=('GSV', 'sum'), Bills=('InvoiceNumber', 'nunique')).reset_index().sort_values('Week', ascending=False)
                st.dataframe(week_view.style.format({'Total_GSV': '₹{:.2f}'}), use_container_width=True)
        
        with tab4:
             st.subheader("⚠️ Single Bill Analysis")
             st.dataframe(master_df[['SalesPerson', 'Total_Bills', 'Single_Bills', 'Single_Bill_%']].sort_values('Single_Bill_%', ascending=False).style.format({'Single_Bill_%': '{:.1f}%'}), use_container_width=True)

    except Exception as e:
        # THIS IS THE PART THAT WILL TELL US THE EXACT ERROR
        st.error(f"🚨 An error occurred: {e}")
        st.markdown("### Debugging Info (Show this to your developer):")
        st.write("Columns found in file:", df.columns.tolist() if 'df' in locals() else "File not read")

else:
    st.info("Waiting for file upload...")
