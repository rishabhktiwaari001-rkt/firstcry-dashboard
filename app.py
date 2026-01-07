import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FirstCry Analytics", layout="wide")

st.title("🛍️ FirstCry Manager Dashboard")
st.markdown("Upload **Article Sale Report** to generate the performance tracker.")

# --- SIDEBAR: FILE UPLOAD ---
with st.sidebar:
    st.header("📂 Data Upload")
    article_file = st.file_uploader("Upload Article Sale Report (CSV)", type=['csv'])
    
    st.markdown("---")
    st.info("ℹ️ **Note:** 'Free Sample Category' and 'GiftCertificate' are excluded from Sales, Qty, and Bill counts.")

# --- MAIN LOGIC ---
if article_file:
    try:
        # 1. LOAD DATA
        df = pd.read_csv(article_file)
        df.columns = df.columns.str.strip() # Clean column headers
        
        # 2. DATE CONVERSION
        # Try multiple date formats (DD/MM/YYYY is standard in India)
        df['BillDate'] = pd.to_datetime(df['BillDate'], dayfirst=True, errors='coerce')
        
        # Add Time Columns
        df['Week'] = df['BillDate'].dt.isocalendar().week
        df['Day'] = df['BillDate'].dt.strftime('%A')
        df['Month'] = df['BillDate'].dt.strftime('%B %Y')

        # 3. FILTER EXCLUSIONS
        # We exclude free items and gift cards from KPI calculations
        exclusions = ['Free Sample Category', 'GiftCertificate']
        clean_df = df[~df['Category'].isin(exclusions)].copy()

        # 4. SINGLE BILL ANALYSIS
        # Group by Invoice Number to find bills with only 1 item
        bill_group = clean_df.groupby(['InvoiceNumber', 'SalesPerson']).agg(
            Bill_Qty=('Quantity', 'sum')
        ).reset_index()
        
        single_bills = bill_group[bill_group['Bill_Qty'] == 1]
        
        # Count stats per staff
        sb_counts = single_bills.groupby('SalesPerson').size().reset_index(name='Single_Bills')
        total_counts = bill_group.groupby('SalesPerson').size().reset_index(name='Total_Bills')
        
        # Merge for analysis
        sb_analysis = pd.merge(total_counts, sb_counts, on='SalesPerson', how='left').fillna(0)
        sb_analysis['Single_Bill_%'] = ((sb_analysis['Single_Bills'] / sb_analysis['Total_Bills']) * 100).round(1)

        # 5. MAIN KPI CALCULATIONS
        # Group by Staff to get total Sales and Qty
        staff_stats = clean_df.groupby('SalesPerson').agg(
            Total_Sales=('NSV', 'sum'),
            Total_Qty=('Quantity', 'sum')
        ).reset_index()
        
        # Merge with Bill Counts
        master_df = pd.merge(staff_stats, total_counts, on='SalesPerson', how='left')
        
        # Calculate AUPT and AVPT
        master_df['AVPT'] = (master_df['Total_Sales'] / master_df['Total_Bills']).round(0)
        master_df['AUPT'] = (master_df['Total_Qty'] / master_df['Total_Bills']).round(2)

        # --- DASHBOARD VISUALS ---

        # TAB 1: OVERVIEW & INCENTIVES
        tab1, tab2, tab3 = st.tabs(["📊 Main Performance", "📅 Weekly & Daily Reports", "⚠️ Single Bill Alert"])

        with tab1:
            st.subheader("Staff Performance Summary")
            st.dataframe(master_df.style.format({'Total_Sales': '₹{:.2f}', 'AVPT': '₹{:.0f}'}), use_container_width=True)
            
            st.markdown("---")
            st.subheader("🏆 Weekly Incentive Winners")
            st.write("Criteria: **AUPT ≥ 4** and **AVPT ≥ 3000** (Current Week)")
            
            # Filter for current week data only
            current_week = df['Week'].max()
            weekly_df = clean_df[df['Week'] == current_week]
            
            # Recalculate stats for just this week
            w_bill_group = weekly_df.groupby(['InvoiceNumber', 'SalesPerson']).agg(Bill_Qty=('Quantity', 'sum')).reset_index()
            w_total_counts = w_bill_group.groupby('SalesPerson').size().reset_index(name='W_Bills')
            
            w_stats = weekly_df.groupby('SalesPerson').agg(W_Sales=('NSV', 'sum'), W_Qty=('Quantity', 'sum')).reset_index()
            w_master = pd.merge(w_stats, w_total_counts, on='SalesPerson', how='left')
            
            w_master['W_AVPT'] = (w_master['W_Sales'] / w_master['W_Bills'])
            w_master['W_AUPT'] = (w_master['W_Qty'] / w_master['W_Bills'])
            
            winners = w_master[(w_master['W_AUPT'] >= 4) & (w_master['W_AVPT'] >= 3000)]
            
            if not winners.empty:
                st.success(f"🎉 Winners found for Week {current_week}!")
                st.dataframe(winners[['SalesPerson', 'W_AVPT', 'W_AUPT']])
            else:
                st.info("No staff qualified for incentives yet this week.")

        # TAB 2: DAY & WEEK REPORTS
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🗓️ Week-wise Sales")
                week_view = clean_df.groupby('Week')['NSV'].sum().reset_index()
                st.dataframe(week_view, use_container_width=True)
            
            with col2:
                st.markdown("### 📅 Day-wise Sales")
                day_view = clean_df.groupby(['BillDate', 'Day'])['NSV'].sum().reset_index().sort_values('BillDate', ascending=False)
                st.dataframe(day_view, use_container_width=True)

        # TAB 3: SINGLE BILL ANALYSIS
        with tab3:
            st.markdown("### ⚠️ Single Item Bill Tracker")
            st.markdown("This shows which staff are generating bills with only 1 item (high percentage is bad).")
            
            st.dataframe(
                sb_analysis.sort_values('Single_Bill_%', ascending=False)
                .style.format({'Single_Bill_%': '{:.1f}%'}), 
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload the 'Article Sale Report' CSV file on the left sidebar.")