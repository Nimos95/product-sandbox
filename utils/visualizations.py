"""
Визуализации для Product Metrics Sandbox (Plotly, тёмная тема).
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Optional

# Цвета текста для читаемости на тёмном фоне
PLOTLY_TEXT_COLOR = "#FAFAFA"
PLOTLY_TEXT_COLOR_DIM = "#b1bac4"

# Общая тема для тёмного стиля (явные цвета шрифтов для контраста)
PLOTLY_THEME = {
    "layout": {
        "template": "plotly_dark",
        "paper_bgcolor": "rgba(14, 17, 23, 1)",
        "plot_bgcolor": "rgba(22, 27, 34, 1)",
        "font": {"color": PLOTLY_TEXT_COLOR, "family": "Inter, system-ui, sans-serif", "size": 12},
        "margin": {"t": 50, "b": 40, "l": 50, "r": 30},
        "xaxis": {
            "gridcolor": "rgba(110, 118, 129, 0.4)",
            "zerolinecolor": "rgba(110, 118, 129, 0.5)",
            "tickfont": {"color": PLOTLY_TEXT_COLOR_DIM, "size": 11},
            "title": {"font": {"color": PLOTLY_TEXT_COLOR}},
        },
        "yaxis": {
            "gridcolor": "rgba(110, 118, 129, 0.4)",
            "zerolinecolor": "rgba(110, 118, 129, 0.5)",
            "tickfont": {"color": PLOTLY_TEXT_COLOR_DIM, "size": 11},
            "title": {"font": {"color": PLOTLY_TEXT_COLOR}},
        },
        "colorway": ["#58a6ff", "#3fb950", "#d29922", "#f85149"],
    }
}


def cohort_heatmap(cohort_revenue: pd.DataFrame) -> go.Figure:
    """Тепловая карта revenue по когортам (строка = когорта, столбец = месяц жизни)."""
    if cohort_revenue.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных для отображения", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=PLOTLY_TEXT_COLOR),
        )
        fig.update_layout(**PLOTLY_THEME["layout"], title="Revenue по когортам")
        return fig

    z = cohort_revenue.values
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=[f"M{i}" for i in cohort_revenue.columns],
        y=cohort_revenue.index.tolist(),
        colorscale="Blues",
        hoverongaps=False,
        hovertemplate="Когорта %{y}, месяц %{x}<br>Revenue: %{z:,.0f}<extra></extra>",
    ))
    layout_no_margin = {k: v for k, v in PLOTLY_THEME["layout"].items() if k != "margin"}
    fig.update_layout(
        **layout_no_margin,
        title="Revenue по когортам (месяц жизни)",
        xaxis_title="Месяц с момента регистрации",
        yaxis_title="Когорта (месяц регистрации)",
        height=400,
        autosize=True,
        margin=dict(t=50, b=45, l=55, r=80),
    )
    return fig


def cohort_heatmap_generic(
    data: pd.DataFrame,
    title: str,
    value_label: str,
    colorscale: str = "Blues",
    text_format: str = "%{text}",
    hover_suffix: str = "",
) -> go.Figure:
    """Универсальная тепловая карта для когорт (revenue / retention % / users)."""
    if data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных для отображения", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=PLOTLY_TEXT_COLOR),
        )
        fig.update_layout(**PLOTLY_THEME["layout"], title=title)
        return fig

    z = data.values
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=[f"M{i}" for i in data.columns],
        y=data.index.tolist(),
        colorscale=colorscale,
        hoverongaps=False,
        text=np.round(z, 1),
        texttemplate=text_format,
        textfont={"size": 10},
        hovertemplate="Когорта %{y}, месяц %{x}<br>" + value_label + ": %{z}" + hover_suffix + "<extra></extra>",
    ))
    layout_no_margin = {k: v for k, v in PLOTLY_THEME["layout"].items() if k != "margin"}
    fig.update_layout(
        **layout_no_margin,
        title=title,
        xaxis_title="Месяц с момента регистрации",
        yaxis_title="Когорта (месяц регистрации)",
        height=400,
        autosize=True,
        margin=dict(t=50, b=45, l=55, r=80),
    )
    return fig


def retention_heatmap(retention_df: pd.DataFrame) -> go.Figure:
    """Тепловая карта Retention (% вернувшихся к платежу)."""
    return cohort_heatmap_generic(
        retention_df,
        title="Retention: % вернувшихся к платежу (от платящих в M0)",
        value_label="Retention",
        colorscale="Greens",
        text_format="%{text:.0f}%",
        hover_suffix="%",
    )


def churn_by_month_chart(churn_series: pd.Series) -> go.Figure:
    """График Churn Rate по месяцам."""
    if churn_series.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Недостаточно данных", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=PLOTLY_TEXT_COLOR),
        )
        layout_no_margin = {k: v for k, v in PLOTLY_THEME["layout"].items() if k != "margin"}
        fig.update_layout(**layout_no_margin, title="Churn Rate по месяцам")
        return fig
    fig = go.Figure(data=[
        go.Bar(x=churn_series.index.astype(str), y=churn_series.values, name="Churn %"),
    ])
    layout_no_margin = {k: v for k, v in PLOTLY_THEME["layout"].items() if k != "margin"}
    fig.update_layout(
        **layout_no_margin,
        title="Churn Rate по месяцам (% активных в M-1, не плативших в M)",
        xaxis_title="Месяц",
        yaxis_title="Churn %",
        height=300,
        autosize=True,
        margin=dict(t=50, b=45, l=55, r=40),
    )
    return fig


def churn_cohort_heatmap(churn_df: pd.DataFrame) -> go.Figure:
    """Тепловая карта Churn по когортам (доля не вернувшихся к платежу в месяце n)."""
    if churn_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=PLOTLY_TEXT_COLOR),
        )
        layout_no_margin = {k: v for k, v in PLOTLY_THEME["layout"].items() if k != "margin"}
        fig.update_layout(**layout_no_margin, title="Churn по когортам")
        return fig
    return cohort_heatmap_generic(
        churn_df,
        title="Churn по когортам (% платящих в M0, не плативших в данном месяце)",
        value_label="Churn",
        colorscale="Reds",
        text_format="%{text:.0f}%",
        hover_suffix="%",
    )


def ltv_chart(cohort_ltv: pd.DataFrame) -> go.Figure:
    """График накопительного LTV по когортам."""
    if cohort_ltv.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных для отображения", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=PLOTLY_TEXT_COLOR),
        )
        fig.update_layout(**PLOTLY_THEME["layout"], title="Накопительный LTV")
        return fig
    
    fig = go.Figure()
    for cohort in cohort_ltv.index:
        months = cohort_ltv.columns.tolist()
        values = cohort_ltv.loc[cohort].values
        fig.add_trace(go.Scatter(
            x=months,
            y=values,
            mode="lines+markers",
            name=str(cohort),
            line=dict(width=2),
        ))
    layout_no_margin = {k: v for k, v in PLOTLY_THEME["layout"].items() if k != "margin"}
    fig.update_layout(
        **layout_no_margin,
        title="Накопительный LTV по когортам",
        xaxis_title="Месяц с момента регистрации",
        yaxis_title="LTV, ₽",
        height=400,
        autosize=True,
        margin=dict(t=50, b=45, l=55, r=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=PLOTLY_TEXT_COLOR)),
        hovermode="x unified",
    )
    return fig


def ab_comparison_chart(summary_df: pd.DataFrame) -> go.Figure:
    """Столбчатая диаграмма сравнения контрольной и тестовой групп (конверсия и ARPU)."""
    if summary_df.empty or len(summary_df) < 2:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных A/B теста", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=PLOTLY_TEXT_COLOR),
        )
        fig.update_layout(**PLOTLY_THEME["layout"])
        return fig

    groups = summary_df["Группа"].tolist()
    fig = go.Figure(data=[
        go.Bar(name="Конверсия %", x=groups, y=summary_df["Конверсия %"], yaxis="y", offsetgroup=0),
        go.Bar(name="ARPU", x=groups, y=summary_df["ARPU"], yaxis="y2", offsetgroup=1),
    ])
    # Тема без xaxis/yaxis, т.к. задаём свои оси (в т.ч. yaxis2) с читаемым текстом
    layout_theme = {k: v for k, v in PLOTLY_THEME["layout"].items() if k not in ("xaxis", "yaxis")}
    axis_style = dict(
        gridcolor="rgba(110, 118, 129, 0.4)",
        zerolinecolor="rgba(110, 118, 129, 0.5)",
        tickfont=dict(color=PLOTLY_TEXT_COLOR_DIM, size=11),
    )
    title_font = dict(color=PLOTLY_TEXT_COLOR)
    fig.update_layout(
        **layout_theme,
        barmode="group",
        title="Сравнение групп: конверсия и ARPU",
        xaxis=dict(title=dict(text="Группа", font=title_font), **axis_style),
        yaxis=dict(title=dict(text="Конверсия %", font=title_font), side="left", overlaying="y2", **axis_style),
        yaxis2=dict(title=dict(text="ARPU", font=title_font), side="right", overlaying="y", **axis_style),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color=PLOTLY_TEXT_COLOR)),
    )
    return fig


def conversion_boxplot(users_df: pd.DataFrame) -> go.Figure:
    """Boxplot распределения конверсии (0/1) по группам A/B."""
    if users_df.empty or "variant" not in users_df.columns or users_df["variant"].nunique() < 2:
        fig = go.Figure()
        fig.add_annotation(
            text="Недостаточно данных для отображения (нужны обе группы A/B)",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=PLOTLY_TEXT_COLOR),
        )
        fig.update_layout(**PLOTLY_THEME["layout"], title="Распределение конверсии по группам")
        return fig

    df = users_df[["variant", "converted"]].copy()
    df["converted_int"] = df["converted"].astype(int)
    df["variant_label"] = df["variant"].replace({"control": "Контроль", "test": "Тест"})

    fig = px.box(
        df,
        x="variant_label",
        y="converted_int",
        color="variant_label",
        title="Распределение конверсии по группам",
        labels={"variant_label": "Группа", "converted_int": "Конверсия (0/1)"},
        color_discrete_sequence=PLOTLY_THEME["layout"]["colorway"],
        points="all",
    )
    fig.update_traces(quartilemethod="linear")
    fig.update_layout(
        template=PLOTLY_THEME["layout"]["template"],
        paper_bgcolor=PLOTLY_THEME["layout"]["paper_bgcolor"],
        plot_bgcolor=PLOTLY_THEME["layout"]["plot_bgcolor"],
        font=PLOTLY_THEME["layout"]["font"],
        margin=PLOTLY_THEME["layout"]["margin"],
        height=350,
        showlegend=False,
        xaxis_title="Группа",
        yaxis_title="Конверсия (0 или 1)",
    )
    xaxis_theme = PLOTLY_THEME["layout"]["xaxis"]
    yaxis_theme = PLOTLY_THEME["layout"]["yaxis"]
    fig.update_xaxes(
        gridcolor=xaxis_theme["gridcolor"],
        zerolinecolor=xaxis_theme["zerolinecolor"],
        tickfont=xaxis_theme["tickfont"],
        title_font=xaxis_theme.get("title", {}).get("font", {}),
    )
    fig.update_yaxes(
        gridcolor=yaxis_theme["gridcolor"],
        zerolinecolor=yaxis_theme["zerolinecolor"],
        tickfont=yaxis_theme["tickfont"],
        title_font=yaxis_theme.get("title", {}).get("font", {}),
        dtick=1,
        range=[-0.5, 1.5],
    )
    return fig


def roi_cohort_chart(roi_by_cohort: pd.Series) -> go.Figure:
    """График ROI по когортам (столбцы). Горизонтальная линия на 0% для отображения зоны убытка."""
    if roi_by_cohort.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=PLOTLY_TEXT_COLOR),
        )
        fig.update_layout(**PLOTLY_THEME["layout"], title="ROI по когортам")
        return fig

    x_vals = roi_by_cohort.index.astype(str)
    y_vals = roi_by_cohort.values
    fig = go.Figure(data=[
        go.Bar(
            x=x_vals,
            y=y_vals,
            name="ROI %",
            hovertemplate="Когорта %{x}<br>ROI: %{y:.1f}%<br><i>ROI = (LTV − CAC) / CAC × 100%</i><extra></extra>",
        ),
    ])
    fig.add_hline(y=0, line_dash="dash", line_color=PLOTLY_TEXT_COLOR_DIM, line_width=1)
    layout_no_margin = {k: v for k, v in PLOTLY_THEME["layout"].items() if k != "margin"}
    fig.update_layout(
        **layout_no_margin,
        title="ROI по когортам (%)",
        xaxis_title="Когорта",
        yaxis_title="ROI %",
        height=350,
        autosize=True,
        margin=dict(t=50, b=45, l=55, r=40),
    )
    return fig
