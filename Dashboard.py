# General Libraries
import select
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
# PAGE CONFIG
# =========================================================

@st.cache_data
def load_data():
    df = pd.read_csv("FX_WIDE.csv")

    df["Date"] = pd.to_datetime(df["Date"])

    df = df.sort_values("Date")

    return df

df = load_data()

# =========================================================
# TITLE
# =========================================================

st.title("PHP/USD Forex Analysis Dashboard")

st.markdown("""
### Objective
Analyze PHP/USD exchange rate trends from 2000 to present and identify
economic factors that significantly drive peso depreciation.
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
    st.dataframe(df.head())

    st.subheader("Summary Statistics")
    st.dataframe(df.describe())

    fig = px.line(
        df,
        x="Date",
        y="USD_to_PHP",
        title="PHP/USD Exchange Rate (2000 - Present)"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
        ### Interpretation

        This graph shows the long-term movement of the Philippine Peso
        against the US Dollar.

        An upward movement indicates peso depreciation because more pesos
        are required to purchase one US dollar.
        """)

# =========================================================
# TREND ANALYSIS
# =========================================================

elif section == "Trend Analysis":

    st.header("Trend Analysis")

    df["MA_30"] = df["USD_to_PHP"].rolling(30).mean()
    df["MA_90"] = df["USD_to_PHP"].rolling(90).mean()

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

    # Financial Crisis
    fig.add_vline(
        x = pd.to_datetime("2000-09-01"),
        line_dash = "dash"
    )

    # COVID
    fig.add_vline(
        x = pd.to_datetime("2020-03-01"),
        line_dash = "dash"
    )

    fig.update_layout(
        title = "Exchange Rate Trend with Moving Averages",
        xaxis_title="Date",
        yaxis_title="PHP/USD"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Exchange Rate Volatility")

    st.markdown("""
        ### Interpretation

        Moving averages smooth short-term fluctuations and help identify
        broader exchange rate trends.

        The vertical markers highlight:
        - 2008 Global Financial Crisis
        - COVID-19 Pandemic
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

    st.plotly_chart(vol_fig, use_container_width=True)

    st.markdown("""
        ### Interpretation

        Volatility measures the degree of exchange rate fluctuations.

        Higher volatility may indicate:
        - financial uncertainty
        - speculative pressure
        - inflation shocks
        - aggressive monetary tightening
        - global crises
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

    st.plotly_chart(yearly_fig, use_container_width=True)

    st.markdown("""
        ### Interpretation

        This graph summarizes yearly average exchange rates.

        A rising trend suggests long-term peso depreciation,
        while declines suggest appreciation periods.
        """)

# =========================================================
# ECONOMIC DRIVERS
# =========================================================

elif section == "Economic Drivers":

    st.header("Economic Drivers of Peso Depreciation")

    if "PH_Inflation" in df.columns and "US_inflation" in df.columns:
        df["Inflation_Diff"] = (
            df["PH_inflation"] - df["US_Inflation"]
        )

    if "PH_Policy_Rate" in df.columns and "US_Policy_Rate" in df.columns:
        df["Rate_Diff"] = (
            df["PH_Policy_Rate"] - df["US_Policy_Rate"]
        )

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    selectable = [col for col in numeric_cols if col != "USD_to_PHP"]

    selected = st.selectbox(
        "Select Economic Variable",
        selectable
    )

    scatter_fig = px.scatter(
        df,
        x=selected,
        y="USD_to_PHP",
        trendline="ols",
        title=f"{selected} vs USD/PHP"
    )

    st.plotly_chart(scatter_fig, use_container_width=True)

    correlation = df[[selected, "USD_to_PHP"]].corr().iloc[0, 1]

    st.metric(
        "Correlation with USD/PHP",
        round(correlation, 4)
    )

    st.markdown("""
        ### Interpretation
        
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

    corr = df.select_dtypes(include=np.number).corr()

    heatmap = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        title="Correlation Heatmap"
    )

    st.plotly_chart(heatmap, use_container_width=True)

    st.subheader("Strongest Correlations with USD/PHP")

    target_corr = (
        corr["USD_to_PHP"]
        .sort_values(ascending=False)
        .reset_index()
    )

    target_corr.columns = ["Variable", "Correlation"]

    st.dataframe(target_corr)

# =========================================================
# PREDICTIVE MODELING
# =========================================================

elif section == "Predictive Modeling":

    st.header("Predictive Modeling")

    st.markdown("""
        ### Model Purpose

        This section uses Random Forest Regression to estimate
        the relationship between macroeconomic indicators
        and PHP/USD exchange rate movement.

        The model also generates a simple 2-period forecast
        using historical patterns and lag variables.
        """)

# =====================================================
# MONTHLY RESAMPLING
# =====================================================

    model_df = df.copy()

    mode_df = (
        model_df
        .set_index("Date")
        .resample("ME")
        .mean(numeric_only=True)
        .reset_index()
    )

# =====================================================
# LAG FEATURES
# =====================================================

    model_df["Lag_1"] = mode_df["USD_to_PHP"].shift(1)
    model_df["Lag_2"] = mode_df["USD_to_PHP"].shift(2)
    model_df["Lag_3"] = mode_df["USD_to_PHP"].shift(3)

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

# =====================================================
# FEATURES
# =====================================================

    target = "USD_to_PHP"

    numeric_cols = model_df.select_dtypes(include=np.number).columns

    features = [
        col for col in numeric_cols
        if col != target
    ]

    X = model_df[features]
    y = model_df[target]

# =====================================================
# TIME SERIES SPLIT
# =====================================================

    split_index = int(len(X) * 0.8)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

# =====================================================
# MODEL
# =====================================================

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=5,
        min_samples_split=5,
        random_state=42
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)

# =====================================================
# METRICS
# =====================================================

    col1, col2 = st.columns(2)

    col1.metric(
        "RMSE",
        round(rmse, 4)
    )

    col2.metric(
        "R² Score",
        round(r2, 4)
    )

    st.markdown("""
        ### Interpretation

        - RMSE measures average prediction error.
          Lower values indicate better performance.

        - R² measures how much variation in exchange rates
          is explained by the model.

          Values closer to 1 indicate stronger explanatory power.
        """)

# =====================================================
# FEATURE IMPORTANCE
# =====================================================

    importance = pd.DataFrame({
        "Feature": features,
        "Importance": model.feature_importances_
    })

    display_importance = importance[
        ~importance["Feature"].str.contains(
            "Lag_|Rolling",
            case=False,
            regex=True
        )
    ]

    display_importance = display_importance.sort_values(
        "Importance",
        ascending=True
    )

    importance_fig = px.bar(
        display_importance,
        x="Importance",
        y="Feature",
        orientation="h",
        title="Macroeconomic Feature Importance"
    )

    st.plotly_chart(importance_fig, use_container_width=True)

    st.markdown("""
    ### Interpretation

    Feature importance estimates which variables contribute most
    to exchange rate predictions.

    Variables with higher importance may have stronger influence
    on peso depreciation dynamics.
    """)

# =====================================================
# ACTUAL VS PREDICTED
# =====================================================

    compare_df = pd.DataFrame({
        "Actual": y_test,
        "Predicted": predictions
    })

    compare_fig = px.scatter(
        compare_df,
        x="Actual",
        y="Predicted",
        title="Actual vs Predicted Exchange Rates",
    )

    st.plotly_chart(compare_fig, use_container_width=True)

    st.markdown("""
    ### Interpretation

    Points closer to the diagonal trend indicate better predictions.

    Large deviations suggest periods where the model struggles
    to capture exchange rate behavior.
    """)

# =====================================================
# 2-PERIOD FORECAST
# =====================================================

    st.subheader("2-Period Forecast (Direction-Based)")

    latest = X.iloc[-1:].copy()

    day1_prediction = model.predict(latest)[0]

    latest2 = latest.copy()

    if "Lag_1" in latest2.columns:
        latest2["Lag_1"] = day1_prediction

    day2_prediction = model.predict(latest2)[0]

    last_actual = X["Lag_1"].iloc[-1] if "Lag_1" in X.columns else None

    if last_actual is not None:
        day1_label = "Increase" if day1_prediction > last_actual else "Decrease"
    else:
        day1_label = "N/A"

    day2_label = "Increase" if day2_prediction > day1_prediction else "Decrease"

    forecast_df = pd.DataFrame({
        "Forecast Period": [
            "Next Period",
            "2 Periods Ahead"
        ],
        "Direction": [
            day1_label,
            day2_label
        ]
    })

    st.subheader("Forecast Table")
    st.dataframe(forecast_df)

# =========================================================
# CREDITS
# =========================================================

elif section == "Credits":

    st.header("Credits")

    st.markdown("""
       ## Project Developers
       
       Bryant Kenzo Carolino
       
       Ulrik Garbriyel Favorada
       
       Sean Eldridge Lavado
       
       Sam Dominique Punzalan
       
       Thom Daniel Yutuc

       ## Data Sources

       Frankfurter API - Daily PHP/USD
       
       Worldbank API - GDP, FDI, Inflation
       
       U.S. Energy Information Administration (EIA) - Monthly Brent Crude Oil
       
       Federal Reserve Economic Data (FRED) - US monthly policy
       
       Bangko Sentral ng Pilipinas (scraped) - GIR
       
       Excel File (Bangko Sentral ng Pilipinas PH monetary policy)
       """)

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.markdown("""
Dashboard Developed Using:
- Streamlit
- Plotly
- Pandas
- NumPy
- Scikit-learn
""")
