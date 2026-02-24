import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency
import matplotlib.ticker as mtick
sns.set(style='dark')

df = pd.read_csv("all_data.csv")


df = df.copy()
df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])

df["year"] = df["order_purchase_timestamp"].dt.year
df["month"] = df["order_purchase_timestamp"].dt.month

available_years = sorted(df["year"].unique())

def get_available_months(year):
    return sorted(df[df["year"] == year]["month"].unique())

with st.sidebar:
    st.image("assets/logo.png")
    st.subheader("Filter Waktu")

    st.markdown("### Start Periode")

    start_year = st.selectbox("Tahun Mulai", available_years)

    start_months_available = get_available_months(start_year)

    start_month = st.selectbox("Bulan Mulai", start_months_available)

    st.markdown("### End Periode")

    end_year = st.selectbox("Tahun Akhir", available_years, index=len(available_years)-1)

    end_months_available = get_available_months(end_year)

    end_month = st.selectbox("Bulan Akhir", end_months_available)

start_date = pd.to_datetime(f"{start_year}-{start_month}-01")
end_date = pd.to_datetime(f"{end_year}-{end_month}-01") + pd.offsets.MonthEnd(0)

main_df = df[
    (df["order_purchase_timestamp"] >= start_date) &
    (df["order_purchase_timestamp"] <= end_date)
]

def create_daily_orders_df(df):
    daily_orders_df = df.resample(rule='M', on='order_purchase_timestamp').agg({
        "order_id": "nunique",
        "price": "sum"
    })
    daily_orders_df = daily_orders_df.reset_index()
    daily_orders_df.rename(columns={
        "order_id": "order_count",
        "price": "revenue"
    }, inplace=True)
    
    return daily_orders_df

def create_paymentType_df(df):
    bypaymentType_df = df.groupby(by="payment_type").agg(
        order_count = ("order_id", "nunique"),
        total = ("price", "sum")).reset_index()
    return bypaymentType_df
def create_byCity_df(df):
    byCity_df = df.groupby("customer_city").order_id.count().reset_index().sort_values("order_id", ascending=False).head(10)
    byCity_df.rename(columns={
        "order_id": "order_count"
    }, inplace=True)
    
    return byCity_df

def create_sum_order_items_df(df):
    sum_order_items_df = df.groupby("product_category_name").order_id.count().reset_index().sort_values("order_id", ascending=False)
    sum_order_items_df.rename(columns={
        "order_id": "order_count"
    }, inplace=True)
    return sum_order_items_df


def create_rfm_df(df):
    def safe_qcut(series, q, labels):
        if series.nunique() < q:
            return pd.Series([1]*len(series), index=series.index)
        return pd.qcut(series, q=q, labels=labels, duplicates='drop')
    # frequency
    frequency_df = (
    df.groupby("customer_id")["order_id"]
    .nunique()
    .reset_index()
    .rename(columns={"order_id": "frequency"})
)
    frequency_df['frequency_score'] = safe_qcut(
        frequency_df['frequency'].rank(method='first'),
        5,
        labels=[1,2,3,4,5]
    ).astype(int)
    #  monetary
    monetary_df = (
    df.groupby("customer_id")["price"]
    .sum()
    .reset_index()
    .rename(columns={"price": "monetary"})
    )
    monetary_df['monetary_score'] = safe_qcut(
        monetary_df['monetary'], 5, labels=[1,2,3,4,5]
    ).astype(int)
    
    # recency   
    recent_date = df["order_purchase_timestamp"].max()

    recency_df = (
        df.groupby("customer_id")["order_purchase_timestamp"]
        .max()
        .reset_index()
        .rename(columns={"order_purchase_timestamp": "max_order_timestamp"})
    )

    recency_df["recency"] = (recent_date - recency_df["max_order_timestamp"]).dt.days
    recency_df['recency_score'] = safe_qcut(
        recency_df['recency'], 5, labels=[5,4,3,2,1]
    ).astype(int)
    
    # merge
    rfm_df = (
    recency_df.merge(frequency_df, on="customer_id")
    .merge(monetary_df, on="customer_id")
)
    rfm_df = rfm_df[['customer_id','recency_score','frequency_score','monetary_score']]
    
    # calculate RFM score
    rfm_df['frequency_monetary_score'] = (
    rfm_df['frequency_score'] + rfm_df['monetary_score']
    )// 2
    rfm_df = rfm_df[['customer_id','recency_score','frequency_monetary_score']]
    
    # segment
    segment_dict = {
    #hibernating
    (1,1):"hibernating",
    (1,2):"hibernating",
    (2,1):"hibernating",
    (2,2):"hibernating",
    #about to sleep
    (3,1):"about to sleep",
    (3,2):"about to sleep",
    # promising
    (4,1):"promising",
    # new customer
    (5,1):"new customer",
    # potential customer
    (4,2):"potential customer",
    (4,3):"potential customer",
    (5,2):"potential customer",
    (5,3):"potential customer",
    # need atention
    (3,3):"need atention",
    # at risk
    (1,3):"at risk",
    (1,4):"at risk",
    (2,3):"at risk",
    (2,4):"at risk",
    # do not lose
    (1,5):"do not lose",
    (2,5):"do not lose",
    # loyal customer
    (3,4):"loyal",
    (3,5):"loyal",
    (4,4):"loyal",
    (4,5):"loyal",
    # champions
    (5,4):"champions",
    (5,5):"champions"}
    
    rfm_df['segment']=rfm_df.apply(lambda x:segment_dict[(x['recency_score'],x['frequency_monetary_score'])], axis= 1)
    rfm_df = rfm_df.groupby(by="segment", as_index=False).customer_id.nunique().sort_values(by ="customer_id",ascending=False)
    return rfm_df


daily_orders_df = create_daily_orders_df(main_df)
bypaymentType_df = create_paymentType_df(main_df)
byCity_df = create_byCity_df(main_df)
sum_order_items_df = create_sum_order_items_df(main_df)
rfm_df = create_rfm_df(main_df)

st.header('E-commerce-public-dataset Dashboard')

# visualisasi daily_orders_df
st.subheader('Daily Orders')
 
col1, col2 = st.columns(2)
 
with col1:
    total_orders = daily_orders_df.order_count.sum()
    st.metric("Total orders", value=total_orders)
 
with col2:
    total_revenue = format_currency(daily_orders_df.revenue.sum(), "BRL", locale='es_CO') 
    st.metric("Total Revenue", value=total_revenue)
 
fig, ax = plt.subplots(figsize=(16, 8))
ax.plot(
    daily_orders_df["order_purchase_timestamp"],
    daily_orders_df["order_count"],
    marker='o', 
    linewidth=2,
    color="#90CAF9"
)

ax.tick_params(axis='y', labelsize=20)
ax.tick_params(axis='x', labelsize=15)
st.pyplot(fig)
with st.expander("See explanation"):
    st.markdown(
    """
    Tren jumlah order per bulan menunjukkan pertumbuhan yang signifikan dari tahun 2017 ke 2018.  
    Total transaksi meningkat dari **44.577 order** pada 2017 menjadi **53.769 order** pada 2018, atau tumbuh sebesar **20,62% year-over-year**.

    Puncak transaksi terjadi pada **November 2017** dengan **7.360 order**, yang mengindikasikan adanya lonjakan permintaan pada periode akhir tahun 2017.

    Sepanjang tahun 2018, volume order cenderung stabil di kisaran **6.000–7.100 order per bulan**, menunjukkan performa bisnis yang lebih konsisten dibandingkan 2017.
    """
    )

# visualisasi bypaymentType_df
st.subheader("Customer Demographics")
 
col1, col2 = st.columns(2)

with col1:
    top2 = bypaymentType_df.nlargest(2, "order_count")["payment_type"].tolist()
    payment = {seg: "#72BCD4" if seg in top2 else "#D3D3D3" for seg in bypaymentType_df["payment_type"]}
    fig, ax = plt.subplots(figsize=(20, 10))
 
    sns.barplot(
        y="order_count", 
        x="payment_type",
        data=bypaymentType_df.sort_values(by="order_count", ascending=False),
        hue="payment_type",
        palette=payment,
        ax=ax
    )
    ax.set_title("Number of Customer by payment type", loc="center", fontsize=50)
    ax.set_ylabel(None)
    ax.set_xlabel(None)
    ax.tick_params(axis='x', labelsize=35)
    ax.tick_params(axis='y', labelsize=30)
    st.pyplot(fig)
 
with col2:
    top2 = bypaymentType_df.nlargest(2, "total")["payment_type"].tolist()
    price = {
        seg: "#72BCD4" if seg in top2 else "#D3D3D3" for seg in bypaymentType_df["payment_type"]}
    fig, ax = plt.subplots(figsize=(20, 10))

    sns.barplot(
        y="total", 
        x="payment_type",
        data=bypaymentType_df.sort_values(by="total", ascending=False),
        palette=price,
        ax=ax
    )

    ax.set_title("Total Revenue by Payment Type", loc="center", fontsize=50)
    ax.set_ylabel(None)
    ax.set_xlabel(None)
    ax.tick_params(axis='x', labelsize=35)
    ax.tick_params(axis='y', labelsize=30)
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))
    st.pyplot(fig)

# Visualisasi byCity_df
top2 = byCity_df.nlargest(2, "order_count")["customer_city"].tolist()
city = {
    seg: "#72BCD4" if seg in top2 else "#D3D3D3" for seg in byCity_df["customer_city"]}
fig, ax = plt.subplots(figsize=(20, 10))

sns.barplot(
    y="customer_city", 
    x="order_count",
    data=byCity_df.sort_values(by="order_count", ascending=False),
    hue="customer_city",
    palette=city,
    ax=ax
)
ax.set_title("Top 5 Cities by Number of Orders", loc="center", fontsize=50)
ax.set_ylabel(None)
ax.set_xlabel(None)
ax.tick_params(axis='x', labelsize=35)
ax.tick_params(axis='y', labelsize=30)
st.pyplot(fig)
with st.expander("See explanation"):
    st.markdown(
        """
        Metode pembayaran **credit card** mendominasi baik dari sisi jumlah transaksi maupun total revenue, menunjukkan preferensi pelanggan terhadap pembayaran berbasis kartu.

        Dari sisi geografis, **São Paulo** menjadi kontributor order terbesar, hampir dua kali lipat dibandingkan kota lainnya. Hal ini menunjukkan konsentrasi pasar yang kuat di wilayah metropolitan.
        """
    )

# Visualisasi sum_order_items_df
st.subheader("Best & Worst Performing Product")
 
fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(35, 15))
 
producttop = sum_order_items_df.nlargest(2, "order_count")["product_category_name"].tolist()
top = sum_order_items_df.sort_values(by="order_count", ascending=False).head(5)
palette_top = {seg: "#72BCD4" if seg in producttop else "#D3D3D3" for seg in sum_order_items_df["product_category_name"]}
sns.barplot(
    x="order_count", 
    y="product_category_name", 
    data=top, 
    palette=palette_top, 
    ax=ax[0])
ax[0].set_ylabel(None)
ax[0].set_xlabel("Number of Sales", fontsize=30)
ax[0].set_title("Best Performing Product", loc="center", fontsize=50)
ax[0].tick_params(axis='y', labelsize=35)
ax[0].tick_params(axis='x', labelsize=30)

bottom = sum_order_items_df.sort_values(by="order_count", ascending=True).head(5)
palette_bottom = {seg: "#72BCD4" if seg in producttop else "#D3D3D3" for seg in sum_order_items_df["product_category_name"]}
sns.barplot(
    x="order_count", 
    y="product_category_name", 
    data=bottom, 
    palette=palette_bottom, 
    ax=ax[1])
ax[1].set_ylabel(None)
ax[1].set_xlabel("Number of Sales", fontsize=30)
ax[1].invert_xaxis()
ax[1].yaxis.set_label_position("right")
ax[1].yaxis.tick_right()
ax[1].set_title("Worst Performing Product", loc="center", fontsize=50)
ax[1].tick_params(axis='y', labelsize=35)
ax[1].tick_params(axis='x', labelsize=30)
st.pyplot(fig)

with st.expander("See explanation"):
    st.markdown(
        """
        Kategori cama_mesa_banho menjadi produk dengan performa terbaik dan unggul signifikan dibanding kategori lainnya. Hal ini menunjukkan bahwa produk kebutuhan rumah tangga merupakan driver utama penjualan.

        Sebaliknya, beberapa kategori seperti artes_e_artesanato dan seguros_e_servicos menunjukkan performa yang sangat rendah, mengindikasikan adanya ketidaksesuaian antara penawaran dan permintaan pasar.
        """
    )

# Visualiasi RFM
st.subheader("Best Customer Based on RFM")
 
fig, ax = plt.subplots(figsize=(35, 15))
rfmtop = rfm_df.nlargest(2, "customer_id")["segment"].tolist()
rfm = {seg: "#72BCD4" if seg in rfmtop else "#D3D3D3" for seg in rfm_df["segment"]}
sns.barplot(
    y="segment", 
    x="customer_id",
    data=rfm_df.sort_values(by="customer_id", ascending=False),
    palette=rfm,
    ax=ax
)
ax.set_title("Customer Distribution by RFM Segment", loc="center", fontsize=50)
ax.set_ylabel(None)
ax.set_xlabel(None)
ax.tick_params(axis='x', labelsize=35)
ax.tick_params(axis='y', labelsize=30)
st.pyplot(fig)
with st.expander("See explanation"):
    st.markdown(
        """
       Distribusi pelanggan menunjukkan dominasi segmen potential customer dan at risk, yang mengindikasikan peluang besar untuk strategi retensi dan konversi loyalitas. Jumlah pelanggan dalam segmen champions dan loyal relatif kecil, sehingga optimalisasi customer lifetime value perlu menjadi fokus utama strategi bisnis ke depan.
        """
    )
