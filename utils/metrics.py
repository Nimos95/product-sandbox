"""
Расчёт продуктовых метрик и статистики A/B тестов.
"""

import numpy as np
import pandas as pd
from scipy import stats
from math import ceil
from typing import Tuple, Optional


def calc_conversion_rate(users_df: pd.DataFrame) -> float:
    """Конверсия в целевое действие (доля converted)."""
    if users_df.empty:
        return 0.0
    return users_df["converted"].mean() * 100


def calc_arpu(users_df: pd.DataFrame, payments_df: pd.DataFrame) -> float:
    """ARPU = сумма платежей / все пользователи."""
    if users_df.empty:
        return 0.0
    total_revenue = payments_df["amount"].sum() if not payments_df.empty else 0
    return total_revenue / len(users_df)


def calc_arppu(users_df: pd.DataFrame, payments_df: pd.DataFrame) -> float:
    """ARPPU = сумма платежей / платящие пользователи."""
    if payments_df.empty:
        return 0.0
    payers = payments_df["user_id"].nunique()
    if payers == 0:
        return 0.0
    return payments_df["amount"].sum() / payers


def calc_ltv_n_months(
    users_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    n_months: int,
) -> float:
    """LTV за n месяцев: средний доход с пользователя за первые n месяцев жизни когорты."""
    if users_df.empty or payments_df.empty:
        return 0.0
    users = users_df.copy()
    users["reg_month"] = users["registered_at"].dt.to_period("M")
    pay = payments_df.merge(users[["user_id", "reg_month"]], on="user_id")
    pay["paid_month"] = pay["paid_at"].dt.to_period("M")
    pay["month_number"] = (pay["paid_month"] - pay["reg_month"]).apply(
        lambda x: getattr(x, "n", 0) if hasattr(x, "n") else 0
    )
    pay_first_n = pay[pay["month_number"] < n_months]
    total_revenue = pay_first_n["amount"].sum()
    return total_revenue / len(users_df)


def calc_paying_share(users_df: pd.DataFrame, payments_df: pd.DataFrame) -> float:
    """Доля платящих пользователей (у кого был хотя бы один платёж)."""
    if users_df.empty:
        return 0.0
    payers = payments_df["user_id"].nunique() if not payments_df.empty else 0
    return payers / len(users_df) * 100


def calc_payers_count(payments_df: pd.DataFrame) -> int:
    """Число платящих пользователей (абсолютное)."""
    if payments_df.empty:
        return 0
    return int(payments_df["user_id"].nunique())


def calc_avg_check_repeat(payments_df: pd.DataFrame) -> float:
    """Средний чек по повторным платежам (не первый платёж пользователя)."""
    if payments_df.empty:
        return 0.0
    first_ts = payments_df.groupby("user_id")["paid_at"].transform("min")
    repeat_mask = payments_df["paid_at"] > first_ts
    repeat_payments = payments_df.loc[repeat_mask, "amount"]
    if repeat_payments.empty:
        return 0.0
    return float(repeat_payments.mean())


def calc_churn_rate(
    payments_df: pd.DataFrame,
    inactive_days: int = 60,
    period_days: int = 30,
    reference_date: Optional[pd.Timestamp] = None,
) -> float:
    """
    Churn Rate за период (backward-looking): среди платящих, которые были активны
    на начало периода, доля тех, у кого нет платежа в последние inactive_days.
    Для транзакционной модели показатель может быть высоким; для отображения
    «типичного» месячного churn используйте calc_churn_rate_monthly().
    """
    if payments_df.empty:
        return 0.0
    if reference_date is None:
        reference_date = payments_df["paid_at"].max()
    last_payment = payments_df.groupby("user_id")["paid_at"].max()
    period_start = reference_date - pd.Timedelta(days=period_days)
    active_cutoff = period_start - pd.Timedelta(days=inactive_days)
    active_at_start = last_payment[last_payment >= active_cutoff]
    if len(active_at_start) == 0:
        return 0.0
    churn_cutoff = reference_date - pd.Timedelta(days=inactive_days)
    churned = active_at_start[active_at_start < churn_cutoff]
    return len(churned) / len(active_at_start) * 100


def calc_churn_rate_monthly(payments_df: pd.DataFrame, inactive_days: int = 60) -> float:
    """
    Средний месячный Churn Rate с учётом окна оттока inactive_days:
    среднее по месяцам из churn_rate_by_month(..., inactive_days).
    Чем больше inactive_days, тем меньше значение (меньше пользователей считаются ушедшими).
    """
    by_month = churn_rate_by_month(payments_df, inactive_days=inactive_days)
    if by_month.empty or len(by_month) == 0:
        return 0.0
    return float(by_month.mean())


def churn_rate_by_month(
    payments_df: pd.DataFrame,
    inactive_days: int = 60,
) -> pd.Series:
    """
    Churn rate по месяцам с учётом окна оттока inactive_days.
    Для каждого месяца M: активны на начало M — пользователи с last_payment >= start_M - inactive_days;
    ушедшие в M — из них те, у кого last_payment < start_M (не платили в M).
    Чем больше inactive_days, тем меньше доля считается ушедшей.
    """
    if payments_df.empty or len(payments_df) < 2:
        return pd.Series(dtype=float)
    pay = payments_df.copy()
    pay["paid_month"] = pay["paid_at"].dt.to_period("M")
    months = sorted(pay["paid_month"].unique())
    if len(months) < 2:
        return pd.Series(dtype=float)
    last_payment = payments_df.groupby("user_id")["paid_at"].max()
    result = {}
    for i in range(1, len(months)):
        curr_m = months[i]
        start_m = curr_m.to_timestamp()
        active_cutoff = start_m - pd.Timedelta(days=inactive_days)
        # Активны на начало месяца M: платили не раньше чем (start_M - inactive_days)
        active_at_start = last_payment[last_payment >= active_cutoff]
        if len(active_at_start) == 0:
            continue
        # Ушедшие в M: были активны, но не платили в M (последний платёж до start_M)
        churned = active_at_start[active_at_start < start_m]
        result[str(curr_m)] = len(churned) / len(active_at_start) * 100
    return pd.Series(result)


def churn_by_cohort_table(
    users_df: pd.DataFrame,
    payments_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    По когортам: для каждого месяца жизни доля платящих в M0, не вернувшихся к платежу в M_n.
    Churn в месяце n = 100 - retention_n (из платящих в M0).
    """
    if users_df.empty or payments_df.empty:
        return pd.DataFrame()
    users = users_df.copy()
    users["cohort"] = users["registered_at"].dt.to_period("M").astype(str)
    users["reg_month"] = users["registered_at"].dt.to_period("M")
    pay = payments_df.merge(users[["user_id", "cohort", "reg_month"]], on="user_id")
    pay["paid_month"] = pay["paid_at"].dt.to_period("M")
    pay["month_number"] = (pay["paid_month"] - pay["reg_month"]).apply(
        lambda x: x.n if hasattr(x, "n") and x.n >= 0 else 0
    )
    pay_m0 = pay[pay["month_number"] == 0].groupby("cohort")["user_id"].apply(set).to_dict()
    cohort_sizes = {c: len(s) for c, s in pay_m0.items()}
    churn_data = []
    for cohort in pay["cohort"].unique():
        payers_m0 = pay_m0.get(cohort, set())
        if not payers_m0:
            continue
        n_m0 = len(payers_m0)
        for month_num in sorted(pay["month_number"].unique()):
            payers_mn = set(
                pay[(pay["cohort"] == cohort) & (pay["month_number"] == month_num)]["user_id"]
            )
            retained = len(payers_m0 & payers_mn)
            churn_pct = 100 - (retained / n_m0 * 100) if n_m0 else 0
            churn_data.append({"cohort": cohort, "month_number": month_num, "churn_pct": churn_pct})
    if not churn_data:
        return pd.DataFrame()
    churn_df = pd.DataFrame(churn_data)
    return churn_df.pivot(index="cohort", columns="month_number", values="churn_pct").fillna(0)


def ab_metrics(
    users_df: pd.DataFrame,
    payments_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, float, float, bool]:
    """
    Сравнение контрольной и тестовой групп для A/B теста.
    
    Returns:
        summary_df: таблица с метриками по группам
        p_value: p-value для конверсии (chi-squared)
        uplift: относительный прирост конверсии в тесте vs контроль (%)
        significant: значим ли результат при alpha=0.05
    """
    if "variant" not in users_df.columns or users_df["variant"].nunique() < 2:
        return pd.DataFrame(), 0.0, 0.0, False
    
    control = users_df[users_df["variant"] == "control"]
    test = users_df[users_df["variant"] == "test"]
    
    # Конверсия
    conv_control = control["converted"].sum()
    conv_test = test["converted"].sum()
    n_control = len(control)
    n_test = len(test)
    
    # Chi-squared для конверсии
    table = np.array([
        [conv_control, n_control - conv_control],
        [conv_test, n_test - conv_test],
    ])
    chi2, p_value, _, _ = stats.chi2_contingency(table)
    
    cr_control = control["converted"].mean() * 100 if n_control else 0
    cr_test = test["converted"].mean() * 100 if n_test else 0
    uplift = ((cr_test - cr_control) / cr_control * 100) if cr_control else 0
    
    # Revenue по группам
    rev_control = 0.0
    rev_test = 0.0
    if not payments_df.empty:
        pay_control = payments_df[payments_df["user_id"].isin(control["user_id"])]
        pay_test = payments_df[payments_df["user_id"].isin(test["user_id"])]
        rev_control = pay_control["amount"].sum()
        rev_test = pay_test["amount"].sum()
    
    arpu_control = rev_control / n_control if n_control else 0
    arpu_test = rev_test / n_test if n_test else 0

    # t-test для ARPU (сравнение распределения дохода на пользователя по группам)
    p_value_arpu = 1.0
    if not payments_df.empty and n_control and n_test:
        rev_per_user_control = payments_df[payments_df["user_id"].isin(control["user_id"])].groupby("user_id")["amount"].sum()
        rev_per_user_test = payments_df[payments_df["user_id"].isin(test["user_id"])].groupby("user_id")["amount"].sum()
        # Дополняем нулями пользователей без платежей
        all_control_rev = control["user_id"].map(rev_per_user_control).fillna(0).values
        all_test_rev = test["user_id"].map(rev_per_user_test).fillna(0).values
        if len(all_control_rev) >= 2 and len(all_test_rev) >= 2:
            _, p_value_arpu = stats.ttest_ind(all_control_rev, all_test_rev, equal_var=False)
            p_value_arpu = float(p_value_arpu) if not np.isnan(p_value_arpu) else 1.0
    
    summary_df = pd.DataFrame({
        "Группа": ["Контроль", "Тест"],
        "Пользователей": [n_control, n_test],
        "Конверсия %": [round(cr_control, 2), round(cr_test, 2)],
        "Revenue": [round(rev_control, 2), round(rev_test, 2)],
        "ARPU": [round(arpu_control, 2), round(arpu_test, 2)],
        "ARPU p-value": [round(p_value_arpu, 4), round(p_value_arpu, 4)],
    })
    
    significant = p_value < 0.05
    return summary_df, float(p_value), uplift, significant


def ab_conversion_by_user(users_df: pd.DataFrame) -> pd.DataFrame:
    """По пользователям: группа и конверсия (0/1) для boxplot."""
    if "variant" not in users_df.columns:
        return pd.DataFrame()
    return users_df[["variant", "converted"]].copy()


def _z_crit(alpha: float, two_sided: bool = True) -> float:
    """Критическое значение Z для alpha."""
    return stats.norm.ppf(1 - alpha / 2) if two_sided else stats.norm.ppf(1 - alpha)


def calc_mde_and_sample_size(
    p_control: float,
    alpha: float = 0.05,
    power: float = 0.8,
    ratio: float = 1.0,
    target_lift_pct: float = 20.0,
) -> Tuple[float, int]:
    """
    MDE (minimum detectable effect) в % и рекомендуемый размер выборки на группу.
    p_control — базовая конверсия в долях (0..1). target_lift_pct — целевой относительный прирост для расчёта n.
    MDE считается для n_ref=1000 на группу (минимальный относительный прирост конверсии, который можно обнаружить).
    """
    if p_control <= 0 or p_control >= 1:
        return 0.0, 0
    z_alpha = _z_crit(alpha)
    z_beta = stats.norm.ppf(power)
    p1 = p_control
    # Размер выборки для обнаружения target_lift_pct относительного прироста
    p2 = min(0.99, p1 * (1 + target_lift_pct / 100))
    effect_size = p2 - p1
    var1 = p1 * (1 - p1)
    var2 = p2 * (1 - p2)
    n_per_group = ceil((z_alpha + z_beta) ** 2 * (var1 + var2 / ratio) / (effect_size ** 2))
    n_per_group = max(30, n_per_group)
    # MDE при n_ref=1000 на группу: решаем уравнение n_needed(effect_abs) = n_ref
    n_ref = 1000
    try:
        from scipy.optimize import brentq
        def mde_equation(effect_abs):
            if effect_abs <= 0:
                return float("inf")
            p2_test = min(0.99, p_control + effect_abs)
            v1 = p_control * (1 - p_control)
            v2 = p2_test * (1 - p2_test)
            n_needed = (z_alpha + z_beta) ** 2 * (v1 + v2 / ratio) / (effect_abs ** 2)
            return n_needed - n_ref
        effect_abs = brentq(mde_equation, 0.001, min(0.5, 1 - p_control - 0.001))
        mde_pct = (effect_abs / p_control) * 100 if p_control > 0 else 50.0
    except (ValueError, ZeroDivisionError):
        mde_pct = 50.0
    return round(float(mde_pct), 1), n_per_group


def calc_mde_simple(
    n_per_group: int,
    p_control: float,
    alpha: float = 0.05,
    power: float = 0.8,
    ratio: float = 1.0,
) -> float:
    """Минимальный обнаруживаемый эффект (относительный, %) при заданном n на группу. p_control — в долях (0..1)."""
    if n_per_group <= 0 or p_control <= 0 or p_control >= 1:
        return 0.0
    z_alpha = _z_crit(alpha)
    z_beta = stats.norm.ppf(power)
    try:
        from scipy.optimize import brentq
        def mde_equation(effect_abs):
            if effect_abs <= 0:
                return float("inf")
            p2_test = min(0.99, p_control + effect_abs)
            v1 = p_control * (1 - p_control)
            v2 = p2_test * (1 - p2_test)
            n_needed = (z_alpha + z_beta) ** 2 * (v1 + v2 / ratio) / (effect_abs ** 2)
            return n_needed - n_per_group
        effect_abs = brentq(mde_equation, 0.001, min(0.5, 1 - p_control - 0.001))
        mde_pct = (effect_abs / p_control) * 100 if p_control > 0 else 50.0
        return round(float(mde_pct), 1)
    except (ValueError, ZeroDivisionError):
        return 50.0


def calc_payback_months(cac: float, arpu_monthly: float) -> Optional[float]:
    """Payback period (месяцев): CAC / средний месячный доход с пользователя. None если не определено."""
    if arpu_monthly <= 0:
        return None
    return cac / arpu_monthly


def calc_roi_by_cohorts(
    cohort_ltv: pd.DataFrame,
    cac: float,
    last_n_months: int = 6,
) -> pd.Series:
    """
    ROI по когортам: (LTV - CAC) / CAC * 100.
    LTV берётся на last_n_months месяцев (столбец last_n_months - 1 в cohort_ltv).
    """
    if cohort_ltv.empty or cac <= 0 or len(cohort_ltv.columns) == 0:
        return pd.Series(dtype=float)
    target_col = last_n_months - 1
    cols = sorted(cohort_ltv.columns)
    col = target_col if target_col in cohort_ltv.columns else (cols[-1] if cols else 0)
    ltv = cohort_ltv[col]
    roi = (ltv - cac) / cac * 100
    return roi.round(1)
