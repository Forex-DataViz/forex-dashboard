# General Libraries
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objs as go

# ML Libraries
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="PHP/USD Forex Dashboard",
    layout="wide",
)

# =========================================================
# CUSTOM SIDEBAR STYLE
# =========================================================

st.markdown("""
<style>

section[data-testid="stSidebar"] {
    width: 350px !important;
}

section[data-testid="stSidebar"] .stRadio label {
    font-size: 18px !important;
    padding: 8px 0px;
}

section[data-testid="stSidebar"] .stRadio div {
    gap: 10px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data
def load_data():
    df = pd.read_csv("FX_WIDE.csv")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    df = df.sort_values("Date")

    return df

df = load_data()

# =========================================================
# DIFFERENCE VARIABLES
# =========================================================

if "PH_Inflation" in df.columns and "US_Inflation" in df.columns:

    df["Inflation_Differential"] = (df["PH_Inflation"] - df["US_Inflation"])

if "PH_Policy_Rate" in df.columns and "US_Policy_Rate" in df.columns:

    df["Interest_Differential"] = (df["PH_Policy_Rate"] - df["US_Policy_Rate"])

# =========================================================
# CORRELATION INTERPRETER
# =========================================================

def corr_strength(corr):

    abs_corr = abs(corr)

    if abs_corr >= 0.8:
        return "Very Strong"

    elif abs_corr >= 0.6:
        return "Strong"

    elif abs_corr >= 0.4:
        return "Moderate"

    elif abs_corr >= 0.2:
        return "Weak"

    else:
        return "Very Weak"

# =========================================================
# TITLE
# =========================================================

st.title("PHP/USD Forex Analysis Dashboard")

st.markdown("""
### Hello!
This is a dashboard that explores the PHP/USD exchange rates from 2000 to present.
The dataset is collected daily through an active API feel free to visit
https://github.com/Forex-DataViz/forex-dashboard for the full code.
""")

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Dashboard Navigation")

section = st.sidebar.radio(
    "Go to:",
    [
        "Overview",
        "Trend Analysis",
        "Economic Drivers",
        "Correlation Analysis",
        "Predictive Modeling",
        "Credits"
    ]
)

# =========================================================
# OVERVIEW
# =========================================================

if section == "Overview":

    st.header("Dataset Overview")

    # Latest
    latest_rate = df["USD_to_PHP"].iloc[-1]
    latest_date = df["Date"].iloc[-1]

    # Highest
    highest_idx = df["USD_to_PHP"].idxmax()
    highest_rate = df.loc[highest_idx, "USD_to_PHP"]
    highest_date = df.loc[highest_idx, "Date"]

    # Lowest
    lowest_idx = df["USD_to_PHP"].idxmin()
    lowest_rate = df.loc[lowest_idx, "USD_to_PHP"]
    lowest_date = df.loc[lowest_idx, "Date"]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest PHP/USD",
        f"{latest_rate:.2f}"
    )

    col1.caption(
        f"Date: {latest_date.strftime('%Y-%m-%d')}"
    )

    col2.metric(
        "Highest PHP/USD",
        f"{highest_rate:.2f}"
    )

    col2.caption(
        f"Date: {highest_date.strftime('%Y-%m-%d')}"
    )

    col3.metric(
        "Lowest PHP/USD",
        f"{lowest_rate:.2f}"
    )

    col3.caption(
        f"Date: {lowest_date.strftime('%Y-%m-%d')}"
    )

    st.subheader("Dataset Preview")
    st.dataframe(df.tail(), width="stretch")

    st.subheader("Summary Statistics")
    st.dataframe(df.describe())

# =========================================================
# MAIN FOREX GRAPH
# =========================================================

fig = px.line(
    df,
    x="Date",
    y="USD_to_PHP",
    title="PHP/USD Exchange Rate (2000 - Present)"
)

# -----------------------------
# HISTORICAL HIGHLIGHTS
# -----------------------------

# EDSA II / Political Crisis
fig.add_vrect(
    x0="2001-01-18",
    x1="2001-01-20",
    fillcolor="purple",
    opacity=0.18,
    line_width=0,
    annotation_text="EDSA II",
    annotation_position="top left"
)

# Fiscal Crisis Escalation
fig.add_vrect(
    x0="2002-07-01",
    x1="2004-05-10",
    fillcolor="darkred",
    opacity=0.12,
    line_width=0,
    annotation_text="Fiscal Crisis",
    annotation_position="top left"
)

# Fiscal Stabilization
fig.add_vrect(
    x0="2004-05-10",
    x1="2005-11-01",
    fillcolor="green",
    opacity=0.12,
    line_width=0,
    annotation_text="Fiscal Stabilization",
    annotation_position="top left"
)

# E-VAT + OFW/BPO Boom
fig.add_vrect(
    x0="2005-11-02",
    x1="2008-02-18",
    fillcolor="limegreen",
    opacity=0.10,
    line_width=0,
    annotation_text="E-VAT + OFW/BPO Boom",
    annotation_position="top left"
)

# 2008 Global Financial Crisis
fig.add_vrect(
    x0="2008-09-01",
    x1="2009-06-01",
    fillcolor="red",
    opacity=0.15,
    line_width=0,
    annotation_text="2008 Global Financial Crisis",
    annotation_position="top left"
)

# Taper Tantrum
fig.add_vrect(
    x0="2013-05-22",
    x1="2013-09-30",
    fillcolor="gold",
    opacity=0.15,
    line_width=0,
    annotation_text="Taper Tantrum",
    annotation_position="top left"
)

# Fed Hikes + Inflation
fig.add_vrect(
    x0="2015-12-16",
    x1="2018-09-25",
    fillcolor="brown",
    opacity=0.12,
    line_width=0,
    annotation_text="Fed Hikes + Inflation",
    annotation_position="top left"
)

# COVID-19 Pandemic
fig.add_vrect(
    x0="2020-03-01",
    x1="2021-12-31",
    fillcolor="orange",
    opacity=0.15,
    line_width=0,
    annotation_text="COVID-19 Pandemic",
    annotation_position="top left"
)

# Ukraine War + Fed Tightening
fig.add_vrect(
    x0="2022-02-01",
    x1="2022-09-28",
    fillcolor="black",
    opacity=0.10,
    line_width=0,
    annotation_text="Ukraine War Shock",
    annotation_position="top left"
)

# Middle East Oil Shock
fig.add_vrect(
    x0="2026-02-28",
    x1=df["Date"].max(),
    fillcolor="crimson",
    opacity=0.15,
    line_width=0,
    annotation_text="Middle East Oil Shock",
    annotation_position="top left"
)

st.plotly_chart(fig, width="stretch")

st.markdown("""
This graph shows the movement of the Philippine Peso against the US Dollar.

- **Upward movement** → Peso weakens (more pesos needed to buy 1 USD)
- **Downward movement** → Peso strengthens

The highlighted regions mark major political and economic events that influenced exchange rate behavior.

### **2001 — EDSA II / Political Crisis**
Senate suppression of impeachment evidence triggered protests and uncertainty.  
The peso spiked sharply to **₱54/USD intraday** before recovering after Estrada’s ouster.

### **2002–2004 — Fiscal Crisis Escalation**
Budget deficits reached **5.3% of GDP**, sovereign downgrades followed, and investor confidence weakened.

### **2004–2005 — Fiscal Stabilization**
Arroyo’s re-election enabled fiscal reforms, including the **EVAT law**, helping restore confidence.

### **2005–2008 — E-VAT + OFW/BPO Boom**
Strong remittances, BPO expansion, and tax reform fueled sustained peso appreciation.

### **2008–2009 — Global Financial Crisis**
Global financial instability caused capital flight and exchange-rate volatility.

### **2013 — Taper Tantrum**
Fed tapering fears triggered capital outflows across emerging markets, weakening the peso.

### **2015–2018 — Fed Hikes + Inflation**
US monetary tightening, inflation, and trade deficits steadily weakened the peso.

### **2020–2021 — COVID-19 Pandemic**
Trade disruptions, inflation, and uncertainty reshaped foreign exchange markets globally.

### **2022 — Ukraine War + Fed Tightening**
Oil shocks and aggressive Fed hikes pushed the peso to **₱59.21/USD**, then a record low.

### **2026 onward — Middle East Oil Shock**
Energy supply risks and emergency declarations renewed depreciation pressure on the peso.
""")

# =========================================================
# TREND ANALYSIS
# =========================================================

elif section == "Trend Analysis":

    st.header("Trend Analysis")

    # =========================================================
    # ROLLING AVERAGES
    # =========================================================

    df["MA_30"] = df["USD_to_PHP"].rolling(30).mean()
    df["MA_90"] = df["USD_to_PHP"].rolling(90).mean()

    # =====================================================
    # ROLLING AVERAGE GRAPH
    # =====================================================

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["USD_to_PHP"],
            name="USD/PHP"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["MA_30"],
            name="30-Day Moving Average"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["MA_90"],
            name="90-Day Moving Average"
        )
    )

    fig.update_layout(
        title = "Rolling Average Trend Analysis",
        xaxis_title="Date",
        yaxis_title="PHP/USD"
    )

    st.plotly_chart(fig, width="stretch")

    st.markdown("""
        Moving averages smooth short-term fluctuations 
        and help identify broader exchange rate trends.
        """)

    # =====================================================
    # VOLATILITY
    # =====================================================

    st.subheader("Exchange Rate Volatility")

    df["Volatility"] = df["USD_to_PHP"].rolling(30).std()

    vol_fig = px.line(
        df,
        x="Date",
        y="Volatility",
        title="30-Day Rolling Volatility"
    )

    st.plotly_chart(vol_fig, width="stretch")

    st.markdown("""
        Volatility measures the magnitude and frequency 
        of exchange rate fluctuations over time.
        """)

    # =====================================================
    # YEARLY AVERAGE
    # =====================================================

    st.subheader("Average Yearly Exchange Rate")

    yearly = (
        df.groupby(df["Date"].dt.year)["USD_to_PHP"]
        .mean()
        .reset_index()
    )

    yearly.columns = ["Year", "Average_Rate"]

    yearly_fig = px.bar(
        yearly,
        x="Year",
        y="Average_Rate",
        title="Average Yearly PHP/USD"
    )

    st.plotly_chart(yearly_fig, width="stretch")

# =========================================================
# ECONOMIC DRIVERS
# =========================================================

elif section == "Economic Drivers":

    st.header("Economic Drivers of Philippine Peso")

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    selectable = [col for col in numeric_cols if col != "USD_to_PHP"]

    selected = st.selectbox(
        "Select Economic Variable",
        selectable
    )

    # =========================================================
    # SCATTER PLOT
    # =========================================================

    scatter_fig = px.scatter(
        df,
        x=selected,
        y="USD_to_PHP",
        trendline="ols",
        title=f"{selected} vs USD/PHP"
    )

    st.plotly_chart(scatter_fig, width="stretch")

    # =====================================================
    # CORRELATION
    # =====================================================

    temp_df = df[[selected, "USD_to_PHP"]].dropna()

    correlation = temp_df.corr().iloc[0, 1]

    strength = corr_strength(correlation)

    col1, col2 = st.columns(2)

    col1.metric(
        "Correlation",
        round(correlation, 2),
    )

    col2.metric(
        "Strength",
        strength,
    )

    st.markdown("""
            This graph examines the relationship between the selected
            economic variable and the PHP/USD exchange rate.

            - Positive correlation:
              As the variable increases, PHP/USD tends to increase
              (peso depreciates).

            - Negative correlation:
              As the variable increases, PHP/USD tends to decrease
              (peso appreciates).

            Correlation does not necessarily imply causation,
            but it helps identify potentially influential macroeconomic factors.
            """)

# =========================================================
# CORRELATION ANALYSIS
# =========================================================

elif section == "Correlation Analysis":

    st.header("Correlation Analysis")

    corr_df = df.select_dtypes(include=np.number)

    corr_df = corr_df.loc[
        :,
        ~corr_df.columns.str.contains(
            "Lag_|Rolling",
            case=False,
            regex=True
        )
    ]

    corr = corr_df.corr()

    heatmap = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        title="Correlation Heatmap"
    )

    st.plotly_chart(heatmap, width="stretch")

    st.subheader("Strongest Correlations with USD/PHP")

    target_corr = (
        corr["USD_to_PHP"]
        .sort_values(ascending=False)
        .reset_index()
    )

    target_corr.columns = ["Variable", "Correlation"]

    target_corr["Strength"] = (target_corr["Correlation"].apply(corr_strength))

    st.dataframe(target_corr, width="stretch")

# =====================================================
# PREDICTIVE MODELING
# =====================================================

elif section == "Predictive Modeling":

    st.header("Predictive Modeling")

    st.markdown("""
    ### Model Purpose

    This section uses Random Forest Regression to estimate
    the relationship between macroeconomic indicators
    and PHP/USD exchange rate movement.

    The model also generates a short-term forecast
    using historical exchange rate patterns.
    """)

    # =====================================================
    # DATA PREP
    # =====================================================

    model_df = df.copy()

    # Monthly sampling
    model_df = (
        model_df
        .set_index("Date")
        .resample("ME")
        .mean(numeric_only=True)
        .reset_index()
    )

    # Lag
    model_df["Lag_1"] = (
        model_df["USD_to_PHP"].shift(1)
    )

    model_df["Lag_2"] = (
        model_df["USD_to_PHP"].shift(2)
    )

    model_df["Lag_3"] = (
        model_df["USD_to_PHP"].shift(3)
    )

    # Rolling values
    model_df["Rolling_Mean_3"] = (
        model_df["USD_to_PHP"]
        .rolling(3)
        .mean()
    )

    model_df["Rolling_STD_3"] = (
        model_df["USD_to_PHP"]
        .rolling(3)
        .std()
    )

    model_df = model_df.dropna()

    target = "USD_to_PHP"

    numeric_cols = (
        model_df
        .select_dtypes(include=np.number)
        .columns
    )

    features = [
        col for col in numeric_cols
        if col != target
    ]

    X = model_df[features]
    y = model_df[target]

    split_index = int(len(X) * 0.8)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=5,
        min_samples_leaf=5,
        random_state=42
    )

    model.fit(X_train, y_train)

    # =====================================================
    # PREDICTIONS
    # =====================================================

    train_predictions = model.predict(X_train)

    predictions = model.predict(X_test)

    # =====================================================
    # TRAINING METRICS
    # =====================================================

    train_rmse = np.sqrt(
        mean_squared_error(y_train, train_predictions)
    )

    train_r2 = r2_score(
        y_train,
        train_predictions
    )

    # =====================================================
    # TESTING METRICS
    # =====================================================

    rmse = np.sqrt(
        mean_squared_error(y_test, predictions)
    )

    r2 = r2_score(y_test, predictions)

    # =====================================================
    # METRIC DISPLAY
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Train RMSE",
        round(train_rmse, 4)
    )

    col2.metric(
        "Test RMSE",
        round(rmse, 4)
    )

    col3.metric(
        "Train R²",
        round(train_r2, 4)
    )

    col4.metric(
        "Test R²",
        round(r2, 4)
    )

    st.markdown("""
    - RMSE measures average prediction error.
      Lower RMSE values indicate smaller prediction errors 
      and better model performance.

    - R² measures how much variation in exchange rates
      is explained by the model. Values closer to 1 indicate
      stronger explanatory power.
    """)

    # =====================================================
    # FEATURE IMPORTANCE
    # =====================================================

    importance = pd.DataFrame({
        "Feature": features,
        "Importance": model.feature_importances_
    })

    # Remove lag + rolling variables from display
    display_importance = importance[
        ~importance["Feature"].str.contains(
            "Lag_|Rolling",
            case=False,
            regex=True
        )
    ]

    display_importance = (
        display_importance
        .sort_values("Importance", ascending=True)
    )

    importance_fig = px.bar(
        display_importance,
        x="Importance",
        y="Feature",
        orientation="h",
        title="Macroeconomic Feature Importance"
    )

    st.plotly_chart(
        importance_fig,
        width="stretch"
    )

    st.subheader("Macroeconomic Variable Importance")

    st.dataframe(
        display_importance.sort_values(
            "Importance",
            ascending=False
        ),
        width="stretch"
    )

    st.markdown("""
    Feature importance estimates which macroeconomic variables
    contribute most to exchange rate movement predictions.

    Lag and rolling variables are excluded from this display
    to focus only on macroeconomic indicators.
    """)

    # =====================================================
    # RESIDUAL ANALYSIS
    # =====================================================

    # Residuals
    train_residuals = y_train - train_predictions
    test_residuals = y_test - predictions

    # =====================================================
    # TRAINING RESIDUALS
    # =====================================================

    train_residual_df = pd.DataFrame({
        "Date": pd.to_datetime(model_df["Date"].iloc[:split_index]),
        "Residuals": train_residuals
    })

    train_fig = px.scatter(
        train_residual_df,
        x="Date",
        y="Residuals",
        title="Training Set Residuals",
        opacity=0.7
    )

    train_fig.add_hline(
        y=0,
        line_dash="dash"
    )

    st.plotly_chart(
        train_fig,
        width="stretch"
    )

    st.markdown("""
    ### Training Residual Interpretation

    This graph shows the residuals from the training dataset.

    Residuals represent the difference between actual
    and predicted exchange rates.

    Residual = Actual − Predicted

    Interpretation:
    - Residuals near zero indicate accurate predictions.
    - Positive residuals indicate underprediction.
    - Negative residuals indicate overprediction.

    The training residual plot helps determine whether
    the model learned general exchange rate patterns
    or excessively memorized historical data.
    """)

    # =====================================================
    # TEST RESIDUALS
    # =====================================================

    test_residual_df = pd.DataFrame({
        "Date": pd.to_datetime(model_df["Date"].iloc[split_index:]),
        "Residuals": test_residuals
    })

    test_fig = px.scatter(
        test_residual_df,
        x="Date",
        y="Residuals",
        title="Testing Set Residuals"
    )

    test_fig.add_hline(
        y=0,
        line_dash="dash"
    )

    st.plotly_chart(
        test_fig,
        width="stretch"
    )

    st.markdown("""
    ### Testing Residual Interpretation

    This graph shows residuals from unseen testing data.

    The testing residuals are more important for evaluating
    real-world predictive performance because the model
    has not previously seen these observations.
    
    ### Interpretation of the Graph
    Early on residuals are minimal, meaning it was able to be predicted by the model.
    Once you reach mid 2025 to 2026 the residuals skyrocket. This says that predicting forex rates
    will be more difficult since the patterns are more unpredictable.
    """)

    # =====================================================
    # FORECASTING
    # =====================================================

    st.subheader("2-Month Forecast (Direction-Based)")

    latest = X.iloc[-1:].copy()

    # First forecast
    month1_prediction = model.predict(latest)[0]

    # Second forecast input
    latest2 = latest.copy()

    # Store previous lag values
    old_lag1 = latest["Lag_1"].values[0]
    old_lag2 = latest["Lag_2"].values[0]

    # Update lag structure
    latest2["Lag_1"] = month1_prediction
    latest2["Lag_2"] = old_lag1
    latest2["Lag_3"] = old_lag2

    rolling_values = [
        month1_prediction,
        old_lag1,
        old_lag2
    ]

    latest2["Rolling_Mean_3"] = np.mean(rolling_values)

    latest2["Rolling_STD_3"] = np.std(rolling_values, ddof=1)

    # Second forecast
    month2_prediction = model.predict(latest2)[0]

    last_date = model_df["Date"].iloc[-1]

    forecast_date_1 = (
        last_date + pd.offsets.MonthEnd(1)
    )

    forecast_date_2 = (
        last_date + pd.offsets.MonthEnd(2)
    )

    # Direction
    last_actual = model_df["USD_to_PHP"].iloc[-1]

    month1_label = (
        "Peso Weakening"
        if month1_prediction > last_actual
        else "Peso Strengthening"
    )

    month2_label = (
        "Peso Weakening"
        if month2_prediction > month1_prediction
        else "Peso Strengthening"
    )

    forecast_df = pd.DataFrame({
        "Forecast Date": [
            forecast_date_1.strftime("%Y-%m-%d"),
            forecast_date_2.strftime("%Y-%m-%d")
        ],
        "Predicted PHP/USD": [
            round(month1_prediction, 4),
            round(month2_prediction, 4)
        ],
        "Direction": [
            month1_label,
            month2_label
        ]
    })

    st.subheader("Forecast Table")

    st.dataframe(forecast_df)

    st.warning("""
    Forecasts are experimental estimates based on historical patterns
    and should not be interpreted as financial advice.
    """)

# =========================================================
# CREDITS
# =========================================================

elif section == "Credits":

    st.header("Credits")

    st.markdown("""
       ## Project Developers
       - Bryant Kenzo Carolino
       - Ulrik Garbriyel Favorada
       - Sean Eldridge Lavado
       - Sam Dominique Punzalan
       - Thom Daniel Yutuc

       ## Data Sources
       - Frankfurter API - Daily PHP/USD
       - Worldbank API - GDP, FDI, Inflation
       - U.S. Energy Information Administration (EIA) - Monthly Brent Crude Oil
       - Federal Reserve Economic Data (FRED) - US monthly policy
       - Bangko Sentral ng Pilipinas (scraped) - GIR
       - Excel File (Bangko Sentral ng Pilipinas PH monetary policy)
       """)

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.warning("""
Disclaimer:

This dashboard is intended solely for educational purposes.

The analyses, forecasts, and visualizations presented are based on
historical data and machine learning estimates and should not be interpreted
as financial or investment advice.

Foreign exchange markets are highly volatile and influenced by numerous
unpredictable economic and geopolitical factors.
""")
