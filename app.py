Understood. This is the **Final Version**.

I have switched the entire engine to run on **GSV (Gross Sales Value)**.

* **Incentives (AVPT):** Now calculated on GSV.
* **Day/Week Reports:** Calculated on GSV.
* **Exclusions:** Only "Free Sample Category" is removed.

Here is the complete code.

### 📝 Final `app.py` (GSV Edition)

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
    st.success("✅ **Current Logic:**")
    st.caption("1. **ALL Metrics:** Based on **GSV** (Gross Sales Value).")
    st.caption("2. **Exclusions:** 'Free Sample Category' removed.")
    st.caption("3. **Inclusions:** 'GiftCertificate' is INCLUDED in Sales.")

# --- MAIN LOGIC ---
if article_file:
    try:
        # 1. LOAD DATA
        df = pd.read_csv(article_file)
        df.columns = df.columns.str.strip() 
        
        # 2. DATE CONVERSION
        df['BillDate'] = pd.to_datetime(df['BillDate'], dayfirst=True, errors='coerce')
        df['Week'] = df['BillDate'].dt.isocalendar().week
        df['Day'] = df['BillDate'].dt.strftime('%A')
        df['Month'] = df['BillDate'].dt.strftime('%B %Y')

        # 3. SEPARATE DATA STREAMS
        
        # Stream A: MEMBERSHIPS (For the Hub)
        # Filter where ProductName contains 'Membership' OR Category is 'GiftCertificate'
        mask_mem = df['ProductName'].str.contains('Membership', case=False, na=False) | (df['Category'] == 'GiftCertificate')
        df_memberships = df[mask_mem].copy()

        # Stream B: SALES DATA (For Incentives & Reports)
        # EXCLUDE ONLY Free Samples. KEEP Gift Certificates.
        exclusions = ['Free Sample Category']
        df_sales = df[~df['Category'].isin(exclusions)].copy()

        # 4. KPI CALCULATIONS (ALL ON GSV)
        
        # A. STAFF INCENTIVES
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
        
        # Calculate Incentives using GSV
        master_df['AVPT'] = (master_df['Total_GSV'] / master_df['Total_Bills']).round(0)
        master_df['AUPT'] = (master_df['Total_Qty'] / master_df['Total_Bills']).round(2)
        master_df['Single_Bill_%'] = ((master_df['Single_Bills'] / master_df['Total_Bills']) * 100).round(1)

        # --- DASHBOARD VISUALS ---

        # Create Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Staff Incentives (GSV)", "💳 Membership Hub", "📅 Day/Week Sales (GSV)", "⚠️ Single Bill Risk"])

        # TAB 1: INCENTIVES (GSV)
        with tab1:
            st.subheader("🏆 Staff Performance (Based on GSV)")
            
            st.dataframe(
                master_df[['SalesPerson', 'Total_GSV', 'Total_Qty', 'Total_Bills', 'AVPT', 'AUPT']]
                .style.format({'Total_GSV': '₹{:.2f}', 'AVPT': '₹{:.0f}'}), 
                use_container_width=True
            )
            
            st.markdown("---")
            st.write("### 🎯 Weekly Incentive Qualifiers (GSV Based)")
            st.caption("Criteria: AUPT ≥ 4 and AVPT (GSV) ≥ 3000 (Current Week)")
            
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
                
                # Metrics
                w_merged['W_AVPT'] = (w_merged['W_GSV'] / w_merged['W_Bills'])
                w_merged['W_AUPT'] = (w_merged['W_Qty'] / w_merged['W_Bills'])
                
                winners = w_merged[(w_merged['W_AUPT'] >= 4) & (w_merged['W_AVPT'] >= 3000)]
                
                if not winners.empty:
                    st.success(f"🎉 Winners for Week {current_week}")
                    st.dataframe(winners[['SalesPerson', 'W_AVPT', 'W_AUPT']].style.format({'W_AVPT': '₹{:.0f}'}))
                else:
                    st.warning("No winners yet for this week.")
            else:
                st.info("No data found for the current week.")

        # TAB 2: MEMBERSHIP HUB
        with tab2:
            st.subheader("💳 Membership Analysis")
            
            if not df_memberships.empty:
                # Create a "Price Category" column based on GSV
                df_memberships['Price_Tier'] = "₹" + df_memberships['GSV'].astype(str)
                
                # 1. Day-wise Membership Breakdown
                st.markdown("### 📅 Day-wise Memberships (By Price)")
                day_mem = df_memberships.groupby(['BillDate', 'Price_Tier']).size().unstack(fill_value=0)
                day_mem = day_mem.sort_index(ascending=False)
                day_mem['Total'] = day_mem.sum(axis=1)
                st.dataframe(day_mem, use_container_width=True)

                # 2. Week-wise Membership Breakdown
                st.markdown("### 🗓️ Week-wise Memberships (By Price)")
                week_mem = df_memberships.groupby(['Week', 'Price_Tier']).size().unstack(fill_value=0)
                week_mem['Total'] = week_mem.sum(axis=1)
                st.dataframe(week_mem, use_container_width=True)
                
                # 3. Staff Leaderboard
                st.markdown("### 👤 Staff Membership Counts")
                staff_mem = df_memberships.groupby(['SalesPerson', 'Price_Tier']).size().unstack(fill_value=0)
                staff_mem['Total'] = staff_mem.sum(axis=1)
                st.dataframe(staff_mem.sort_values('Total', ascending=False), use_container_width=True)
                
            else:
                st.warning("No Membership data found.")

        # TAB 3: DAY & WEEK REPORTS (GSV)
        with tab3:
            col_d, col_w = st.columns(2)
            
            with col_d:
                st.subheader("📅 Day-wise Sales (GSV)")
                day_view = df_sales.groupby(['BillDate', 'Day']).agg(
                    Total_GSV=('GSV', 'sum'),
                    Bill_Count=('InvoiceNumber', 'nunique')
                ).reset_index().sort_values('BillDate', ascending=False)
                
                st.dataframe(day_view.style.format({'Total_GSV': '₹{:.2f}'}), use_container_width=True)

            with col_w:
                st.subheader("🗓️ Week-wise Sales (GSV)")
                week_view = df_sales.groupby('Week').agg(
                    Total_GSV=('GSV', 'sum'),
                    Bill_Count=('InvoiceNumber', 'nunique')
                ).reset_index().sort_values('Week', ascending=False)
                
                st.dataframe(week_view.style.format({'Total_GSV': '₹{:.2f}'}), use_container_width=True)

        # TAB 4: SINGLE BILLS
        with tab4:
            st.subheader("⚠️ Single Bill Analysis")
            st.markdown("**Monitoring staff for 'Bill Splitting' behavior**")
            st.dataframe(
                master_df[['SalesPerson', 'Total_Bills', 'Single_Bills', 'Single_Bill_%']]
                .sort_values('Single_Bill_%', ascending=False)
                .style.format({'Single_Bill_%': '{:.1f}%'}),
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload the 'Article Sale Report' CSV file.")

```
