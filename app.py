You've got it. I have added the **Category Filter Tab** and the **Staff Ranking System** to the dashboard.

### 🌟 New Features Added

1. **🔍 Category & Sub-Category Tab:**
* You can now select a specific Category (e.g., "Fashion") and even deeper (e.g., "T-Shirts").
* It instantly shows you a leaderboard of **who sold the most** in that specific category.


2. **🏆 Staff Rankings:**
* I added a **"Rank"** column to the main dashboard.
* It automatically sorts staff by **Total Sales (GSV)** so you can see who is #1, #2, etc.



Here is the **Final Complete Code**. Replace your `app.py` content with this.

```python
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
    
    st.markdown("---")
    st.success("✅ **Active Logic:**")
    st.caption("1. **All Metrics:** Based on **GSV**.")
    st.caption("2. **Rankings:** Auto-calculated on Total Sales.")
    st.caption("3. **Exclusions:** 'Free Sample Category' removed.")

# --- MAIN LOGIC ---
if article_file:
    try:
        # 1. LOAD DATA
        df = pd.read_csv(article_file)
        
        # 2. CLEAN COLUMN NAMES
        df.columns = df.columns.str.strip()
        
        # Auto-fix common column name issues
        rename_map = {
            'SalePerson': 'SalesPerson', 
            'Date': 'BillDate',
            'Bill Date': 'BillDate'
        }
        df.rename(columns=rename_map, inplace=True)

        # 3. DATE CONVERSION
        df['BillDate'] = pd.to_datetime(df['BillDate'], dayfirst=True, errors='coerce')
        
        # Check for date errors
        if df['BillDate'].isna().all():
            st.error("🚨 Date Error: Could not read dates. Check your CSV format.")
            st.stop()

        # --- RETAIL WEEK LOGIC (1-7, 8-14, etc.) ---
        df['Day_Num'] = df['BillDate'].dt.day
        df['Week'] = (df['Day_Num'] - 1) // 7 + 1
        df['Week_Label'] = "Week " + df['Week'].astype(str)
        df['Day'] = df['BillDate'].dt.strftime('%A')
        
        # 4. SEPARATE STREAMS
        
        # Stream A: MEMBERSHIPS
        mask_mem = df['ProductName'].str.contains('Membership', case=False, na=False) | (df['Category'] == 'GiftCertificate')
        df_memberships = df[mask_mem].copy()

        # Stream B: SALES (Exclude Free Samples)
        exclusions = ['Free Sample Category']
        df_sales = df[~df['Category'].isin(exclusions)].copy()

        # 5. KPI CALCULATIONS (ALL ON GSV)
        
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
        
        # Calculate Incentives (GSV Based)
        master_df['AVPT'] = (master_df['Total_GSV'] / master_df['Total_Bills']).round(0)
        master_df['AUPT'] = (master_df['Total_Qty'] / master_df['Total_Bills']).round(2)
        master_df['Single_Bill_%'] = ((master_df['Single_Bills'] / master_df['Total_Bills']) * 100).round(1)

        # ADD RANKING (Based on Total GSV)
        master_df = master_df.sort_values('Total_GSV', ascending=False).reset_index(drop=True)
        master_df.index = master_df.index + 1  # Start rank at 1
        master_df['Rank'] = master_df.index

        # Reorder columns to put Rank first
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

        # TAB 1: RANKINGS & INCENTIVES
        with tab1:
            st.subheader("🏆 Staff Rankings (Based on GSV)")
            st.markdown("Sorted by **Highest Total Sales**")
            
            st.dataframe(
                master_df.style.format({'Total_GSV': '₹{:.2f}', 'AVPT': '₹{:.0f}'}), 
                use_container_width=True
            )
            
            st.markdown("---")
            st.write("### 🎯 Weekly Incentive Qualifiers (Current Week)")
            
            # Weekly Logic
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
                st.info("No data for current week.")

        # TAB 2: CATEGORY ANALYSIS (NEW!)
        with tab2:
            st.subheader("🔍 Category & Sub-Category Performance")
            
            col_cat, col_sub = st.columns(2)
            
            # 1. Category Filter
            cats = ['All'] + sorted(df_sales['Category'].unique().tolist())
            selected_cat = col_cat.selectbox("Select Category", cats)
            
            # 2. Sub-Category Filter (Dependent on Category)
            if selected_cat != 'All':
                sub_cats = ['All'] + sorted(df_sales[df_sales['Category'] == selected_cat]['SubCategory'].unique().tolist())
            else:
                sub_cats = ['All'] # No sub-cats if 'All' is selected
            
            selected_sub = col_sub.selectbox("Select Sub-Category", sub_cats)
            
            # 3. Filter Data
            filtered_df = df_sales.copy()
            if selected_cat != 'All':
                filtered_df = filtered_df[filtered_df['Category'] == selected_cat]
            if selected_sub != 'All':
                filtered_df = filtered_df[filtered_df['SubCategory'] == selected_sub]
            
            # 4. Display Stats
            if not filtered_df.empty:
                st.write(f"Showing data for: **{selected_cat}** > **{selected_sub}**")
                
                cat_stats = filtered_df.groupby('SalesPerson').agg(
                    Sales_GSV=('GSV', 'sum'),
                    Qty_Sold=('Quantity', 'sum'),
                    Bills_Involved=('InvoiceNumber', 'nunique')
                ).reset_index().sort_values('Sales_GSV', ascending=False)
                
                cat_stats.reset_index(drop=True, inplace=True)
                cat_stats.index += 1
                cat_stats.index.name = 'Rank'
                
                st.dataframe(cat_stats.style.format({'Sales_GSV': '₹{:.2f}'}), use_container_width=True)
            else:
                st.warning("No sales found for this selection.")

        # TAB 3: MEMBERSHIPS
        with tab3:
            st.subheader("💳 Membership Hub")
            if not df_memberships.empty:
                df_memberships['Price_Tier'] = "₹" + df_memberships['GSV'].astype(str)
                
                st.write("**Day-wise Memberships**")
                day_mem = df_memberships.groupby(['BillDate', 'Price_Tier']).size().unstack(fill_value=0).sort_index(ascending=False)
                st.dataframe(day_mem, use_container_width=True)
                
                st.write("**Week-wise Memberships**")
                week_mem = df_memberships.groupby(['Week_Label', 'Price_Tier']).size().unstack(fill_value=0)
                st.dataframe(week_mem, use_container_width=True)
            else:
                st.info("No memberships found.")

        # TAB 4: SALES REPORTS
        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📅 Day-wise Sales (GSV)")
                day_view = df_sales.groupby(['BillDate', 'Day']).agg(
                    Total_GSV=('GSV', 'sum'), 
                    Bills=('InvoiceNumber', 'nunique')
                ).reset_index().sort_values('BillDate', ascending=False)
                st.dataframe(day_view.style.format({'Total_GSV': '₹{:.2f}'}), use_container_width=True)
                
            with col2:
                st.subheader("🗓️ Week-wise Sales (GSV)")
                week_view = df_sales.groupby('Week_Label').agg(
                    Total_GSV=('GSV', 'sum'), 
                    Bills=('InvoiceNumber', 'nunique')
                ).reset_index()
                st.dataframe(week_view.style.format({'Total_GSV': '₹{:.2f}'}), use_container_width=True)

        # TAB 5: SINGLE BILLS
        with tab5:
            st.subheader("⚠️ Single Bill Risk")
            st.dataframe(master_df[['Rank', 'SalesPerson', 'Total_Bills', 'Single_Bills', 'Single_Bill_%']].sort_values('Single_Bill_%', ascending=False).style.format({'Single_Bill_%': '{:.1f}%'}), use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
        st.write("Columns found:", df.columns.tolist() if 'df' in locals() else "None")
else:
    st.info("Waiting for file upload...")

```
