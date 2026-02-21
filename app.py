"""
Product Metrics Sandbox — интерактивный симулятор продуктовых метрик.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from utils.generators import (
    generate_users,
    generate_payments,
    build_cohorts,
    build_retention_cohorts,
    build_user_cohorts,
)
from utils.metrics import (
    calc_conversion_rate,
    calc_arpu,
    calc_arppu,
    calc_ltv_n_months,
    calc_paying_share,
    calc_churn_rate,
    calc_churn_rate_monthly,
    churn_rate_by_month,
    churn_by_cohort_table,
    calc_payers_count,
    calc_avg_check_repeat,
    ab_metrics,
    calc_mde_and_sample_size,
    calc_mde_simple,
    calc_payback_months,
    calc_roi_by_cohorts,
)
from utils.visualizations import (
    cohort_heatmap,
    cohort_heatmap_generic,
    retention_heatmap,
    churn_by_month_chart,
    churn_cohort_heatmap,
    ltv_chart,
    ab_comparison_chart,
    conversion_boxplot,
    roi_cohort_chart,
)
from utils.storage import (
    ensure_data_dirs,
    scenario_to_dict,
    save_scenario_to_file,
    list_scenario_files,
    load_scenario_from_file,
    load_scenario_from_bytes,
    append_experiment,
    load_experiment_history,
    build_report_html,
    save_report_to_file,
    _df_to_html_table,
)

# ——— Конфигурация страницы и тёмная тема ———
st.set_page_config(
    page_title="Product Metrics Sandbox",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ——— Фон приложения ——— */
    .stApp { background-color: #0d1117; }
    [data-testid="stHeader"] { background-color: rgba(13, 17, 23, 0.95); }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #161b22 0%, #0d1117 100%); }
    
    /* ——— Весь основной текст (контрастный) ——— */
    .stApp .stMarkdown { color: #FAFAFA !important; }
    .stApp p { color: #FAFAFA !important; }
    .stApp label { color: #e6edf3 !important; }
    .stApp div[data-testid="stCaptionContainer"] { color: #b1bac4 !important; }
    
    /* ——— Заголовки (единообразие) ——— */
    .stApp h1 { color: #ffffff !important; font-weight: 700; font-size: 1.75rem; }
    .stApp h2 { color: #e6edf3 !important; font-weight: 600; font-size: 1.25rem; }
    .stApp h3 { color: #e6edf3 !important; font-weight: 600; font-size: 1.1rem; }
    
    /* ——— Боковая панель: заголовки блоков (expander) — жирные, контрастные ——— */
    section[data-testid="stSidebar"] .stMarkdown { color: #e6edf3 !important; }
    section[data-testid="stSidebar"] p { color: #e6edf3 !important; }
    section[data-testid="stSidebar"] label { color: #e6edf3 !important; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #ffffff !important; font-weight: 700; }
    /* Заголовки expander — жирный белый текст */
    section[data-testid="stSidebar"] [data-testid="stExpander"] > div:first-child,
    section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] ~ div:first-child label,
    section[data-testid="stSidebar"] [data-testid="stExpander"] label {
        color: #ffffff !important; font-weight: 700 !important; font-size: 1rem !important;
    }
    /* Фон expander — чуть светлее для контраста */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: #1c2128; border-radius: 8px; border: 1px solid #30363d;
        margin-bottom: 0.75rem; padding: 0.5rem 0.75rem; box-sizing: border-box;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] > div { padding: 0.5rem 0 0.25rem 0; }
    /* Разделители между блоками */
    section[data-testid="stSidebar"] hr { border-color: #30363d !important; margin: 1rem 0 !important; }
    /* Подписи слайдеров — явно как заголовок контрола */
    section[data-testid="stSidebar"] [data-testid="stSlider"] label,
    section[data-testid="stSidebar"] [data-testid="stSlider"] + div { color: #e6edf3 !important; font-weight: 500 !important; }
    section[data-testid="stSidebar"] [data-testid="stNumberInput"] label { color: #e6edf3 !important; font-weight: 500 !important; }
    section[data-testid="stSidebar"] .stSelectbox label { color: #e6edf3 !important; }
    section[data-testid="stSidebar"] .stTextInput label { color: #e6edf3 !important; }
    section[data-testid="stSidebar"] .stFileUploader label { color: #e6edf3 !important; }
    section[data-testid="stSidebar"] small { color: #b1bac4 !important; }
    /* Number input: убрать визуальный акцент кнопок +/-, оставить поле */
    section[data-testid="stSidebar"] [data-testid="stNumberInput"] div[data-testid="stNumberInputContainer"] {
        border: 1px solid #30363d; border-radius: 6px; background-color: #21262d;
    }
    section[data-testid="stSidebar"] [data-testid="stNumberInput"] button { opacity: 0.85; }
    
    /* ——— Кнопка "Обновить данные" — яркая, заметная ——— */
    section[data-testid="stSidebar"] .refresh-primary-wrap + div .stButton button,
    section[data-testid="stSidebar"] .refresh-primary-wrap ~ div .stButton button {
        background: linear-gradient(180deg, #238636 0%, #2ea043 100%) !important;
        color: #ffffff !important; font-weight: 600 !important;
        border: 1px solid #3fb950 !important; border-radius: 8px !important;
        padding: 0.6rem 1.25rem !important; width: 100% !important;
    }
    section[data-testid="stSidebar"] .refresh-primary-wrap + div .stButton button:hover,
    section[data-testid="stSidebar"] .refresh-primary-wrap ~ div .stButton button:hover {
        background: #2ea043 !important; border-color: #56d364 !important;
    }
    
    /* ——— File uploader — в стиле темы (тёмный) ——— */
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
        background-color: #21262d !important; border: 1px dashed #30363d !important; border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] section { background-color: #161b22 !important; color: #e6edf3 !important; }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] p { color: #b1bac4 !important; }
    
    /* ——— Контейнер: не обрезать контент справа ——— */
    .main .block-container { max-width: 100%; padding: 1rem 1.5rem 2rem; box-sizing: border-box; }
    .stPlotlyChart { max-width: 100% !important; width: 100% !important; overflow: hidden; }
    div[data-testid="stVerticalBlock"] { max-width: 100%; }
    
    /* ——— Карточки метрик ——— */
    .metric-card {
        background: linear-gradient(145deg, #161b22 0%, #1c2128 100%) !important;
        border: 1px solid #373e47;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        box-sizing: border-box;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #ffffff !important; line-height: 1.2; }
    .metric-label { font-size: 0.85rem; color: #b1bac4 !important; margin-top: 0.35rem; }
    
    [data-testid="stMetricValue"] { color: #ffffff !important; }
    [data-testid="stMetricLabel"] { color: #b1bac4 !important; }
    
    /* ——— Вкладки ——— */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #161b22;
        border-radius: 8px;
        border: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] { color: #8b949e !important; background-color: transparent; }
    .stTabs [data-baseweb="tab"]:hover { color: #e6edf3 !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important; background-color: #21262d !important; border-radius: 6px;
    }
    
    /* ——— Таблицы ——— */
    .stDataFrame { border: 1px solid #373e47; border-radius: 8px; overflow: hidden; }
    .stDataFrame th { background-color: #161b22 !important; color: #e6edf3 !important; border-color: #30363d !important; }
    .stDataFrame td { color: #e6edf3 !important; border-color: #30363d !important; }
    .stDataFrame tr:hover td { background-color: #21262d !important; }
    
    .stApp .stButton button { color: #e6edf3; }
    .stApp .stSelectbox div { color: #e6edf3; }
    .stApp [data-testid="stCaptionContainer"] p { color: #b1bac4 !important; }
    
    /* ——— Заголовок в табах (Когорты): чёткая иерархия ——— */
    .main .stRadio label { color: #e6edf3 !important; font-weight: 500 !important; }
    .main .stSelectbox label { color: #e6edf3 !important; font-weight: 500 !important; }
    
    .stAlert { color: #e6edf3 !important; }
    .stSuccess { color: #3fb950 !important; }
    .stError { color: #f85149 !important; }
</style>
""", unsafe_allow_html=True)


def main():
    ensure_data_dirs()
    st.title("📊 Product Metrics Sandbox")
    st.caption("Интерактивный симулятор продуктовых метрик на синтетических данных")

    # ——— Значения по умолчанию из загруженного сценария ———
    defaults = st.session_state.get("scenario_params") or {}

    # ——— Боковая панель (логические блоки с иконками и разделителями) ———
    with st.sidebar:
        st.header("⚙️ Параметры")

        with st.expander("👥 Аудитория", expanded=True):
            n_users = st.slider(
                "Количество пользователей", 100, 10000,
                int(defaults.get("n_users", 2000)), 100,
            )
            conversion_rate = st.slider(
                "Базовая конверсия в целевое действие (%)", 1, 50,
                int(defaults.get("conversion_rate", 12)), 1,
            )
        st.divider()

        with st.expander("📈 Каналы привлечения", expanded=True):
            st.caption("Доли каналов (в сумме 100%). Слайдер — % пользователей из канала.")
            pct_ads = st.slider("Реклама (конверсия −10%)", 0, 100, int(defaults.get("pct_ads", 30)), 5)
            pct_organic = st.slider("Органика (базовая конверсия)", 0, 100, int(defaults.get("pct_organic", 50)), 5)
            pct_referral = st.slider("Рефералки (конверсия +25%)", 0, 100, int(defaults.get("pct_referral", 20)), 5)
        total_ch = pct_ads + pct_organic + pct_referral
        if total_ch <= 0:
            st.warning("Сумма долей должна быть больше 0. Исправьте значения.")
            channel_pct = {"ads": 30, "organic": 50, "referral": 20}
        else:
            channel_pct = {
                "ads": pct_ads / total_ch * 100,
                "organic": pct_organic / total_ch * 100,
                "referral": pct_referral / total_ch * 100,
            }
        st.divider()

        with st.expander("💰 Монетизация", expanded=True):
            min_amount = st.number_input(
                "Мин. сумма платежа (₽)",
                min_value=1, max_value=5000,
                value=int(defaults.get("min_amount", 99)),
                step=50,
                key="min_amount",
            )
            max_amount = st.number_input(
                "Макс. сумма платежа (₽)",
                min_value=100, max_value=50000,
                value=int(defaults.get("max_amount", 5000)),
                step=100,
                key="max_amount",
            )
        if min_amount > max_amount:
            st.warning("Мин. сумма не должна превышать макс. Исправьте значения.")
            max_amount = min_amount
        st.divider()

        with st.expander("🧪 Эксперименты", expanded=True):
            ab_test = st.checkbox("Включить A/B тест", value=defaults.get("ab_test", True))
            seasonality_enabled = st.checkbox(
                "Учитывать сезонность",
                value=defaults.get("seasonality_enabled", True),
                help="Дек–янв +20%, июл–авг −15%",
            )
        st.divider()

        with st.expander("📊 Юнит-экономика", expanded=True):
            cac = st.number_input(
                "CAC — стоимость привлечения (₽)",
                min_value=0,
                max_value=50000,
                value=int(defaults.get("cac", 500)),
                step=50,
                help="Средние затраты на привлечение одного пользователя (реклама, маркетинг).",
            )
        st.divider()

        with st.expander("⚙️ Дополнительно", expanded=False):
            st.caption("Слайдер: 30–180 дней. Пользователь считается ушедшим, если с последнего платежа прошло больше выбранного числа дней.")
            churn_days = st.slider(
                "Дней без активности для оттока",
                min_value=30,
                max_value=180,
                value=int(defaults.get("churn_days", 60)),
                step=15,
                help="Пользователь считается ушедшим, если с последнего платежа прошло больше этого числа дней.",
            )
            fix_seed = st.checkbox(
                "Фиксировать seed (воспроизводимость данных)",
                value=defaults.get("seed", 42) != 0,
                help="Один и тот же seed даёт одинаковые данные при каждой генерации.",
                key="fix_seed",
            )
            seed_input = 0
            if fix_seed:
                seed_input = st.number_input(
                    "Seed для генерации данных",
                    min_value=1,
                    max_value=999999,
                    value=int(defaults.get("seed", 42) or 42),
                    step=1,
                    help="Один и тот же seed даёт одинаковые данные.",
                    key="seed_input",
                )
            seed = None if seed_input == 0 else int(seed_input)

            st.markdown("**Сценарии**")
            saved = list_scenario_files()
            load_choice = ""
            if saved:
                load_choice = st.selectbox(
                    "Выберите сценарий для загрузки",
                    [""] + sorted(saved),
                    key="load_choice",
                )
            else:
                st.caption("Нет сохранённых сценариев. Сохраните текущие параметры кнопкой ниже.")
            load_clicked = st.button("📂 Загрузить выбранный сценарий", key="load_btn")
            if load_clicked and load_choice:
                try:
                    loaded = load_scenario_from_file(load_choice)
                    st.session_state["scenario_params"] = loaded
                    st.session_state["load_scenario_name"] = load_choice
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
            if st.button("💾 Сохранить сценарий", key="save_btn"):
                params = scenario_to_dict(
                    n_users, conversion_rate, pct_ads, pct_organic, pct_referral,
                    seasonality_enabled, min_amount, max_amount, ab_test, cac, seed_input,
                    name="Сценарий",
                )
                ensure_data_dirs()
                fname = "Сценарий_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
                path = save_scenario_to_file(params, fname)
                st.success(f"Сохранено: {path.name}")
                st.session_state["scenario_params"] = None
                st.rerun()
            st.caption("Или загрузите JSON с параметрами:")
            uploaded = st.file_uploader("Загрузить JSON", type=["json"], key="scenario_upload", label_visibility="collapsed")
            if uploaded is not None:
                try:
                    loaded = load_scenario_from_bytes(uploaded.read())
                    st.session_state["scenario_params"] = loaded
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        st.divider()

        st.markdown('<div class="refresh-primary-wrap" aria-hidden="true"></div>', unsafe_allow_html=True)
        try:
            refresh_clicked = st.button("🔄 Обновить данные", type="primary", key="refresh_data")
        except TypeError:
            refresh_clicked = st.button("🔄 Обновить данные", key="refresh_data")
        if refresh_clicked:
            st.session_state["should_save_history"] = True
            st.session_state["scenario_params"] = None
            st.rerun()

    # ——— Генерация данных (вся логика в generators) ———
    users_df = generate_users(
        n_users, conversion_rate, ab_test,
        channel_pct=channel_pct,
        seasonality_enabled=seasonality_enabled,
        seed=seed,
    )
    payments_df = generate_payments(
        users_df, min_amount, max_amount,
        first_payment_min=299,
        first_payment_max=499,
        churn_months=3,
        seed=seed,
    )
    cohort_revenue, cohort_ltv = build_cohorts(users_df, payments_df)

    # ——— Карточки метрик ———
    total_users = len(users_df)
    conv_rate = calc_conversion_rate(users_df)
    arpu = calc_arpu(users_df, payments_df)
    arppu = calc_arppu(users_df, payments_df)
    ltv_3 = calc_ltv_n_months(users_df, payments_df, 3)
    ltv_6 = calc_ltv_n_months(users_df, payments_df, 6)
    paying_share = calc_paying_share(users_df, payments_df)
    churn_rate = calc_churn_rate(payments_df, inactive_days=churn_days)
    payers_abs = calc_payers_count(payments_df)
    avg_check_repeat = calc_avg_check_repeat(payments_df)

    # ——— Сохранение в историю экспериментов (при нажатии «Обновить данные») ———
    if st.session_state.get("should_save_history"):
        append_experiment(
            params={
                "n_users": n_users,
                "conversion_rate": conversion_rate,
                "pct_ads": pct_ads,
                "pct_organic": pct_organic,
                "pct_referral": pct_referral,
                "seasonality_enabled": seasonality_enabled,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "ab_test": ab_test,
                "cac": cac,
                "seed": seed_input,
            },
            metrics={
                "total_users": total_users,
                "conv_rate": conv_rate,
                "arpu": arpu,
                "arppu": arppu,
                "ltv_3": ltv_3,
                "ltv_6": ltv_6,
                "paying_share": paying_share,
                "churn_rate": churn_rate,
            },
            scenario_name=st.session_state.get("load_scenario_name", ""),
        )
        st.session_state["should_save_history"] = False
        if "load_scenario_name" in st.session_state:
            del st.session_state["load_scenario_name"]

    def metric_card(value: str, label: str, tooltip: str):
        return (
            f'<div class="metric-card" title="{tooltip}">'
            f'<div class="metric-value">{value}</div>'
            f'<div class="metric-label">{label} <span style="color:#58a6ff;cursor:help" title="{tooltip}">ⓘ</span></div></div>'
        )

    # Карточки метрик: 4 колонки в ряд, с иконками
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            metric_card(
                f"{total_users:,}",
                "👥 Total Users",
                "Общее количество зарегистрированных пользователей в выборке.",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            metric_card(
                f"{conv_rate:.1f}%",
                "📈 Conversion Rate",
                "Доля пользователей, совершивших целевое действие (конверсию). Считается: (converted / всего пользователей) × 100%.",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            metric_card(
                f"{arpu:.2f} ₽",
                "💰 ARPU",
                "Average Revenue Per User — средний доход с одного пользователя. Считается: сумма всех платежей / количество пользователей.",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            metric_card(
                f"{arppu:.2f} ₽",
                "💵 ARPPU",
                "Average Revenue Per Paying User — средний доход с платящего пользователя. Считается: сумма платежей / количество платящих.",
            ),
            unsafe_allow_html=True,
        )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(
            metric_card(
                f"{ltv_3:.2f} ₽",
                "📊 LTV 3 months",
                "Lifetime Value за 3 месяца — средний доход с пользователя за первые 3 месяца жизни когорты. Считается по платежам в месяцах 0, 1, 2.",
            ),
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            metric_card(
                f"{ltv_6:.2f} ₽",
                "📊 LTV 6 months",
                "LTV за 6 месяцев — средний доход с пользователя за первые 6 месяцев. Считается по платежам в месяцах 0–5.",
            ),
            unsafe_allow_html=True,
        )
    with c7:
        st.markdown(
            metric_card(
                f"{paying_share:.1f}%",
                "🔄 Paying Share",
                "Доля платящих пользователей — % пользователей, совершивших хотя бы один платёж. Считается: (уникальные плательщики / всего пользователей) × 100%.",
            ),
            unsafe_allow_html=True,
        )
    with c8:
        st.markdown(
            metric_card(
                f"{churn_rate:.1f}%",
                f"📉 Churn Rate ({churn_days} дн.), %",
                f"Доля платящих, которые были активны на начало периода, но не платили в последние {churn_days} дн. Чем больше окно оттока (слайдер), тем меньше значение. Для транзакционной модели показатель может быть выше, чем в подписках (5–20% в месяц).",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    # ——— Когорты: retention и user activity ———
    cohort_retention = build_retention_cohorts(users_df, payments_df)
    cohort_users = build_user_cohorts(users_df, payments_df)

    # ——— Вкладки ———
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Когорты", "A/B тест", "Данные", "Юнит-экономика", "История экспериментов"])

    with tab1:
        st.markdown("### Тип когортного анализа")
        cohort_type = st.radio(
            "Выберите тип когортного анализа",
            ["Revenue", "Retention", "Users"],
            index=0,
            horizontal=True,
            help="Revenue — сумма платежей по месяцам жизни; Retention — % вернувшихся к платежу от плативших в M0; Users — количество платящих по месяцам.",
            label_visibility="collapsed",
        )
        st.caption("Revenue: сумма платежей по месяцам жизни когорты. Retention: % вернувшихся к платежу. Users: количество платящих по месяцам.")
        if cohort_type == "Revenue":
            st.subheader("Revenue по когортам")
            st.plotly_chart(cohort_heatmap(cohort_revenue), width="stretch", config={"responsive": True})
        elif cohort_type == "Retention":
            st.subheader("Retention: % вернувшихся к платежу")
            if not cohort_retention.empty:
                st.plotly_chart(retention_heatmap(cohort_retention), width="stretch", config={"responsive": True})
                st.caption("Процент пользователей когорты, плативших в месяце 0 и снова в месяце N.")
            else:
                st.info("Недостаточно данных для таблицы retention.")
            st.subheader("Retention — таблица")
            if not cohort_retention.empty:
                ret_display = cohort_retention.round(1).copy()
                ret_display.columns = [f"M{c}" for c in ret_display.columns]
                st.dataframe(ret_display, width="stretch", hide_index=True)
                st.caption("Значения в % — доля платящих в M0, вернувшихся к платежу в данном месяце.")
        else:
            st.subheader("Активность: платящие по когортам и месяцам")
            if not cohort_users.empty:
                fig_u = cohort_heatmap_generic(
                    cohort_users,
                    "Количество платящих по когортам",
                    "Платящих",
                    colorscale="Purples",
                )
                st.plotly_chart(fig_u, width="stretch", config={"responsive": True})
            else:
                st.info("Нет данных.")
        st.subheader("Накопительный LTV")
        st.plotly_chart(ltv_chart(cohort_ltv), width="stretch", config={"responsive": True})

        st.subheader("Churn Rate по месяцам")
        churn_series = churn_rate_by_month(payments_df, inactive_days=churn_days)
        if not churn_series.empty:
            st.plotly_chart(churn_by_month_chart(churn_series), width="stretch", config={"responsive": True})
            st.caption("Доля пользователей, плативших в месяце M−1, но не совершивших платёж в месяце M.")
        else:
            st.info("Нужно минимум 2 месяца с платежами для расчёта churn по месяцам.")

        st.subheader("Churn по когортам")
        churn_cohort_df = churn_by_cohort_table(users_df, payments_df)
        if not churn_cohort_df.empty:
            st.plotly_chart(churn_cohort_heatmap(churn_cohort_df), width="stretch", config={"responsive": True})
            st.caption("Доля платящих в месяце 0, не совершивших платёж в данном месяце жизни когорты (100 − retention).")
        else:
            st.info("Недостаточно данных для таблицы churn по когортам.")

    with tab2:
        summary_df, p_value, uplift, significant = ab_metrics(users_df, payments_df)
        if not summary_df.empty:
            st.subheader("Сравнение групп")
            st.dataframe(summary_df, width="stretch", hide_index=True)
            st.plotly_chart(ab_comparison_chart(summary_df), width="stretch", config={"responsive": True})
            st.subheader("Распределение конверсий по группам")
            st.plotly_chart(conversion_boxplot(users_df), width="stretch", config={"responsive": True})
            st.subheader("Калькулятор MDE и размер выборки")
            p_control_pct = users_df[users_df["variant"] == "control"]["converted"].mean() * 100 if "variant" in users_df.columns else 12
            p_control = p_control_pct / 100
            mde_pct, n_recommend = calc_mde_and_sample_size(p_control, target_lift_pct=20)
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("MDE (при n≈1000 на группу)", f"{mde_pct}%", help="Минимальный относительный прирост конверсии (%), который можно обнаружить с мощностью 80% при α=0.05.")
            with col_m2:
                st.metric("Рекомендуемый размер на группу (для 20% lift)", f"{n_recommend:,}", help="Число пользователей в каждой группе для обнаружения 20% относительного прироста конверсии с мощностью 80%.")
            with col_m3:
                n_control = len(users_df[users_df["variant"] == "control"]) if "variant" in users_df.columns else 0
                mde_actual = calc_mde_simple(n_control, p_control) if n_control else 0
                st.metric("MDE при текущем размере выборки", f"{mde_actual}%", help="Минимальный эффект, который можно обнаружить при текущем числе пользователей в контроле.")
            st.caption("MDE — Minimum Detectable Effect. Мощность 80%, α=0.05, two-sided.")

            # ——— Выводы по A/B тесту ———
            st.subheader("📊 Выводы по A/B тесту")
            n_test = int(summary_df.loc[1, "Пользователей"]) if len(summary_df) > 1 else 0
            arpu_control = float(summary_df.loc[0, "ARPU"]) if len(summary_df) > 0 else 0.0
            arpu_test = float(summary_df.loc[1, "ARPU"]) if len(summary_df) > 1 else 0.0
            arpu_uplift = ((arpu_test - arpu_control) / arpu_control * 100) if arpu_control else 0.0

            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("**Статистическая значимость**")
                if p_value < 0.05:
                    st.success(f"✅ Результат статистически значим (p-value = {p_value:.4f} < 0.05)")
                else:
                    st.warning(f"⚠️ Результат не является статистически значимым (p-value = {p_value:.4f} ≥ 0.05)")
                st.markdown(f"**Uplift конверсии:** {uplift:+.1f}%")
                st.markdown(f"**p-value:** {p_value:.4f}")

            with col_right:
                st.markdown("**Влияние на метрики**")
                if arpu_uplift > 0:
                    st.markdown(f"💰 ARPU вырос на {arpu_uplift:.1f}%")
                elif arpu_uplift < 0:
                    st.markdown(f"💰 ARPU снизился на {abs(arpu_uplift):.1f}%")
                else:
                    st.markdown("💰 ARPU не изменился")
                st.markdown(f"👥 **Размер выборки:** контроль n={n_control}, тест n={n_test}")

            st.markdown("---")
            st.markdown("**Рекомендации:**")
            if p_value < 0.05 and uplift > 0:
                st.success(f"✅ Тестовая группа показала значимый прирост конверсии на {uplift:.1f}%. Рекомендуется раскатывать изменение на всех пользователей.")
            elif p_value < 0.05 and uplift < 0:
                st.warning(f"⚠️ Тестовая группа показала значимое снижение конверсии на {abs(uplift):.1f}%. Рекомендуется отклонить изменение и проанализировать причины.")
            elif p_value >= 0.05 and (n_control < 500 or n_test < 500):
                st.warning("⚠️ Недостаточный размер выборки для обнаружения эффекта. Рекомендуется набрать больше пользователей.")
            elif p_value >= 0.05 and n_control >= 500 and n_test >= 500:
                st.info("ℹ️ При текущем размере выборки не удалось обнаружить статистически значимый эффект. Возможные причины: эффект отсутствует, либо он слишком мал для обнаружения.")

            if mde_actual and mde_actual > 0:
                st.caption(f"**Анализ чувствительности:** Минимальный обнаруживаемый эффект (MDE) при текущем размере выборки составляет {mde_actual}%. Наблюдаемый эффект ({abs(uplift):.1f}%) {'превышает MDE' if abs(uplift) > mde_actual else 'меньше MDE'}.")
        else:
            st.info("Включите «Включить A/B тест» в боковой панели и обновите данные.")

    with tab3:
        st.subheader("Таблица пользователей")
        users_preview = users_df.copy()
        users_preview["registered_at"] = users_preview["registered_at"].astype(str)
        st.dataframe(users_preview.head(500), width="stretch", hide_index=True)
        csv_users = users_preview.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Скачать users.csv", csv_users, "users.csv", "text/csv")

        st.subheader("Таблица платежей")
        if not payments_df.empty:
            pay_preview = payments_df.copy()
            pay_preview["paid_at"] = pay_preview["paid_at"].astype(str)
            st.dataframe(pay_preview.head(500), width="stretch", hide_index=True)
            csv_pay = pay_preview.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Скачать payments.csv", csv_pay, "payments.csv", "text/csv", key="dl_payments")
        else:
            st.write("Платежей нет.")

    with tab4:
        st.subheader("Юнит-экономика")
        # Средний месячный доход с пользователя (на основе LTV за 6 мес. или 3 мес.)
        arpu_monthly = (ltv_6 / 6.0) if ltv_6 > 0 else ((ltv_3 / 3.0) if ltv_3 > 0 else (arpu / 6.0))
        if arpu_monthly <= 0:
            arpu_monthly = arpu / 6.0
        payback = calc_payback_months(cac, arpu_monthly)
        roi_cohorts = calc_roi_by_cohorts(cohort_ltv, cac, last_n_months=6)

        u1, u2, u3 = st.columns(3)
        with u1:
            st.metric(
                "CAC (стоимость привлечения)",
                f"{cac:.0f} ₽",
                help="Задаётся в боковой панели. Средние затраты на привлечение одного пользователя.",
            )
        with u2:
            pb_str = f"{payback:.1f} мес." if payback is not None else "—"
            st.metric(
                "Payback period",
                pb_str,
                help="Срок окупаемости: за сколько месяцев доход с одного пользователя покроет CAC. Считается: CAC / средний месячный доход с пользователя.",
            )
        with u3:
            avg_roi = roi_cohorts.mean() if not roi_cohorts.empty else 0
            st.metric(
                "Средний ROI по когортам (6 мес.)",
                f"{avg_roi:.1f}%" if not roi_cohorts.empty else "—",
                help="ROI = (LTV − CAC) / CAC × 100%. Показан средний ROI по когортам за 6 месяцев.",
            )
        if not roi_cohorts.empty:
            st.subheader("ROI по когортам")
            st.plotly_chart(roi_cohort_chart(roi_cohorts), width="stretch", config={"responsive": True})
            st.caption("ROI по когортам за 6 месяцев жизни. LTV берётся накопительный за 6 мес., CAC — из настроек.")

    with tab5:
        st.subheader("История экспериментов")
        st.caption("Записи добавляются при нажатии «Обновить данные». Хранятся в data/experiment_history.csv.")
        hist_df = load_experiment_history()
        if not hist_df.empty:
            hist_display = hist_df.copy()
            if "timestamp" in hist_display.columns:
                hist_display["timestamp"] = pd.to_datetime(hist_display["timestamp"], errors="coerce").dt.strftime("%d.%m.%Y %H:%M")
            st.dataframe(hist_display, width="stretch", hide_index=True)
            csv_hist = hist_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Скачать историю (CSV)", csv_hist, "experiment_history.csv", "text/csv", key="dl_history")
        else:
            st.info("История пуста. Нажмите «Обновить данные» в боковой панели, чтобы сохранить текущий запуск.")

    # ——— Экспорт отчёта ———
    st.divider()
    if st.button("📄 Экспорт отчёта (HTML)"):
        low_data_warning = None
        if total_users < 100:
            low_data_warning = "⚠️ Внимание: в выборке менее 100 пользователей. Метрики носят ориентировочный характер; для надёжных выводов увеличьте объём данных."

        # Выводы с интерпретацией (что это значит, сравнение с нормой)
        ltv_vs_arpu_note = "LTV за 3 месяца может быть ниже ARPU: ARPU считается по всем платежам за весь период наблюдения, а LTV 3m — только за первые 3 месяца жизни пользователя."
        churn_note = f"Churn Rate ({churn_days} дн.) = {churn_rate:.1f}%. "
        if churn_rate > 25:
            churn_note += "Для типичного SaaS месячный отток 5–20%; повышенное значение может быть из-за транзакционной модели (см. пояснение к метрикам) или короткого окна оттока."
        else:
            churn_note += "В пределах типичного диапазона для платящей базы. Чем больше окно оттока (дней без активности), тем меньше показатель."
        insights = [
            f"LTV за 6 месяцев — {ltv_6:.2f} ₽ на пользователя. Это прогноз дохода с одного пользователя за полгода; для оценки окупаемости CAC сравните с CAC в разделе юнит-экономики.",
            ltv_vs_arpu_note,
            f"Конверсия в целевое действие — {conv_rate:.1f}%. Доля пользователей, совершивших целевое действие; для сравнения: в продуктах с сильным онбордингом часто 10–25%.",
            f"Платящих пользователей — {payers_abs} ({paying_share:.1f}% от базы). Средний чек по повторным платежам — {avg_check_repeat:.2f} ₽ (выше первого чека у лояльных пользователей).",
            churn_note,
        ]

        recommendations = []
        if payback is not None and payback > 12:
            recommendations.append("Payback period превышает 12 месяцев — рассмотрите снижение CAC или повышение LTV (удержание, монетизация).")
        if churn_rate > 20:
            recommendations.append("Высокий отток — стоит проанализировать причины (качество онбординга, ценность продукта, сегменты).")
        if not roi_cohorts.empty and roi_cohorts.mean() < 0:
            recommendations.append("Средний ROI по когортам отрицательный — когорты не окупают CAC за 6 месяцев; пересмотрите каналы привлечения или ценность продукта.")
        ab_result = None
        summary_df_ab = pd.DataFrame()
        if ab_test and "variant" in users_df.columns:
            summary_df_ab, p_val, uplift, significant = ab_metrics(users_df, payments_df)
            if not summary_df_ab.empty:
                n_ctrl = int(summary_df_ab.loc[summary_df_ab["Группа"] == "Контроль", "Пользователей"].iloc[0])
                n_tst = int(summary_df_ab.loc[summary_df_ab["Группа"] == "Тест", "Пользователей"].iloc[0])
                ab_result = {
                    "p_value": p_val,
                    "uplift": uplift,
                    "significant": significant,
                    "recommendation": "Можно раскатывать на всех." if significant else "Нужна ещё выборка или продление теста.",
                    "n_control": n_ctrl,
                    "n_test": n_tst,
                }
                rec_ab = "Можно раскатывать изменение на всех пользователей." if significant else "Недостаточно данных для вывода; рекомендуется набрать выборку или продлить тест."
                recommendations.append(f"A/B тест: {rec_ab}")
        if not recommendations:
            recommendations.append("Метрики в допустимых диапазонах. Рекомендуется отслеживать LTV и churn по когортам в динамике.")

        plotly_snippets = {}
        try:
            fig_rev = cohort_heatmap(cohort_revenue)
            plotly_snippets["Revenue по когортам"] = fig_rev.to_html(full_html=False, include_plotlyjs=False)
        except Exception:
            pass
        try:
            fig_ltv = ltv_chart(cohort_ltv)
            plotly_snippets["LTV по когортам"] = fig_ltv.to_html(full_html=False, include_plotlyjs=False)
        except Exception:
            pass
        try:
            if not summary_df_ab.empty:
                fig_ab = ab_comparison_chart(summary_df_ab)
                plotly_snippets["A/B сравнение"] = fig_ab.to_html(full_html=False, include_plotlyjs=False)
        except Exception:
            pass
        try:
            if not roi_cohorts.empty:
                fig_roi = roi_cohort_chart(roi_cohorts)
                plotly_snippets["ROI по когортам"] = fig_roi.to_html(full_html=False, include_plotlyjs=False)
        except Exception:
            pass

        try:
            params_report = {
                "n_users": n_users,
                "conversion_rate": conversion_rate,
                "pct_ads": pct_ads,
                "pct_organic": pct_organic,
                "pct_referral": pct_referral,
                "seasonality_enabled": seasonality_enabled,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "ab_test": ab_test,
                "cac": cac,
                "seed": seed_input,
            }
            metrics_report = {
                "total_users": total_users,
                "payers_abs": payers_abs,
                "conv_rate": conv_rate,
                "arpu": arpu,
                "arppu": arppu,
                "ltv_3": ltv_3,
                "ltv_6": ltv_6,
                "avg_check_repeat": avg_check_repeat,
                "paying_share": paying_share,
                "churn_rate": churn_rate,
            }
            try:
                n_u = len(users_df)
                indices = sorted(set(i for i in [
                    0, n_u // 4, n_u // 2, 3 * n_u // 4, max(0, n_u - 1)
                ] if 0 <= i < n_u))[:5] if n_u else []
                users_preview = users_df.iloc[indices].copy() if indices else users_df.head(5).copy()
                users_preview["registered_at"] = users_preview["registered_at"].dt.strftime("%Y-%m-%d")
                data_users_html = _df_to_html_table(users_preview, max_rows=5)
            except Exception:
                data_users_html = None
            try:
                if not payments_df.empty:
                    pay_preview = payments_df.head(5).copy()
                    pay_preview["payment_date"] = pay_preview["paid_at"].dt.strftime("%Y-%m-%d")
                    pay_preview = pay_preview[["user_id", "payment_id", "amount", "payment_date"]]
                    data_payments_html = _df_to_html_table(pay_preview, max_rows=5)
                else:
                    data_payments_html = "<p>Нет платежей.</p>"
            except Exception:
                data_payments_html = None

            sp = st.session_state.get("scenario_params")
            scenario_name_report = (sp.get("name", "Текущий сценарий") if isinstance(sp, dict) else getattr(sp, "name", None)) or "Текущий сценарий"

            html_report = build_report_html(
                params_report,
                metrics_report,
                insights,
                recommendations,
                plotly_snippets,
                ab_result=ab_result,
                data_users_html=data_users_html,
                data_payments_html=data_payments_html,
                scenario_name=scenario_name_report,
                low_data_warning=low_data_warning,
                churn_days_label=f"{churn_days} дн.",
            )
            report_path = save_report_to_file(html_report)
            st.success(f"Отчёт сохранён: {report_path}")
            st.download_button(
                "Скачать отчёт (HTML)",
                html_report.encode("utf-8"),
                f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                "text/html",
                key="dl_report",
            )
        except Exception as e:
            st.error(f"Ошибка при формировании отчёта: {e}")


if __name__ == "__main__":
    main()
