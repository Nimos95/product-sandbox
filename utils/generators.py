"""
Генерация синтетических данных для Product Metrics Sandbox.
Модульная логика: сезонность, каналы, поведение платежей, churn.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional

# Множители конверсии по каналам (относительно базы)
CHANNEL_CONVERSION_MULT = {
    "ads": 0.90,      # реклама: -10%
    "organic": 1.0,   # органика: база
    "referral": 1.25, # рефералки: +25%
}

# Сезонность по месяцу: множитель к конверсии
def _seasonality_mult(month: int, enabled: bool) -> float:
    if not enabled:
        return 1.0
    if month in (12, 1):  # декабрь–январь
        return 1.2
    if month in (7, 8):   # июль–август
        return 0.85
    return 1.0


def _effective_conversion(
    base_rate_pct: float,
    channel: str,
    reg_month: int,
    seasonality_enabled: bool,
    rng: np.random.Generator,
) -> bool:
    """Вероятность конверсии с учётом канала и сезонности."""
    mult = CHANNEL_CONVERSION_MULT.get(channel, 1.0) * _seasonality_mult(reg_month, seasonality_enabled)
    p = (base_rate_pct / 100.0) * mult
    p = min(1.0, max(0.0, p))
    return rng.random() < p


def generate_users(
    n_users: int,
    conversion_rate: float,
    ab_test: bool,
    channel_pct: Optional[Dict[str, float]] = None,
    seasonality_enabled: bool = True,
    seed: Optional[int] = 42,
) -> pd.DataFrame:
    """
    Генерирует таблицу пользователей с датами регистрации за 2025 год.
    Учитывает канал привлечения и сезонность конверсии.

    Args:
        n_users: количество пользователей
        conversion_rate: базовая конверсия в целевое действие (%)
        ab_test: включать ли разбивку на A/B группы
        channel_pct: доли каналов {"ads": 30, "organic": 50, "referral": 20}, в сумме 100
        seasonality_enabled: применять ли сезонность (дек–янв +20%, июл–авг -15%)
        seed: seed для воспроизводимости (None — случайный каждый раз)

    Returns:
        DataFrame: user_id, registered_at, converted, variant, channel
    """
    rng = np.random.default_rng(seed)

    if channel_pct is None:
        channel_pct = {"ads": 30, "organic": 50, "referral": 20}
    # Нормализация к сумме 100
    total = sum(channel_pct.values()) or 1
    channels = list(channel_pct.keys())
    probs = np.array([channel_pct.get(c, 0) for c in channels]) / total
    probs = probs / probs.sum()

    start = datetime(2025, 1, 1)
    end = datetime(2025, 12, 31)
    days_span = (end - start).days + 1  # 365 дней — распределение по всему году

    registered_at = [
        start + timedelta(days=min(int(x), days_span - 1))
        for x in rng.uniform(0, days_span, n_users)
    ]

    channel = rng.choice(channels, size=n_users, p=probs)
    reg_months = pd.Series(registered_at).dt.month.values

    converted = np.array([
        _effective_conversion(conversion_rate, channel[i], reg_months[i], seasonality_enabled, rng)
        for i in range(n_users)
    ])

    if ab_test:
        variant = rng.choice(["control", "test"], size=n_users, p=[0.5, 0.5])
    else:
        variant = np.full(n_users, "control")

    df = pd.DataFrame({
        "user_id": range(1, n_users + 1),
        "registered_at": sorted(registered_at),
        "converted": converted,
        "variant": variant,
        "channel": channel,
    })
    return df


def generate_payments(
    users_df: pd.DataFrame,
    min_amount: float,
    max_amount: float,
    first_payment_min: float = 299,
    first_payment_max: float = 499,
    churn_months: float = 3,
    pay_rate: float = 0.15,
    repeat_rate: float = 0.3,
    seed: Optional[int] = 42,
) -> pd.DataFrame:
    """
    Генерирует платежи с учётом поведения:
    - первый платёж чаще минимальный (299–499);
    - при 3+ платежах суммы растут (лояльные);
    - churn: после churn_months без платежа пользователь больше не платит.

    Args:
        users_df: таблица пользователей (должна содержать user_id, registered_at)
        min_amount: минимальная сумма обычного платежа
        max_amount: максимальная сумма обычного платежа
        first_payment_min, first_payment_max: диапазон первого платежа
        churn_months: месяцев без платежа → churn
        pay_rate: доля пользователей с хотя бы одним платежом
        repeat_rate: доля платящих с повторными платежами
        seed: seed для воспроизводимости (None — случайный каждый раз)

    Returns:
        DataFrame: user_id, payment_id, amount, paid_at
    """
    rng = np.random.default_rng(seed)
    churn_days = churn_months * 30

    n_users = len(users_df)
    payers_mask = rng.random(n_users) < pay_rate
    payers = users_df.loc[payers_mask, "user_id"].values
    reg_dates = users_df.set_index("user_id").loc[payers, "registered_at"]

    rows = []
    payment_id = 1

    for uid in payers:
        reg = reg_dates.loc[uid]
        if isinstance(reg, pd.Series):
            reg = reg.iloc[0]

        # Первый платёж — в течение 30 дней после регистрации, сумма 299–499
        first_days = rng.uniform(0, 30)
        last_paid = reg + timedelta(days=first_days)
        amount = rng.uniform(first_payment_min, first_payment_max)
        rows.append({
            "user_id": uid,
            "payment_id": payment_id,
            "amount": round(amount, 2),
            "paid_at": last_paid,
        })
        payment_id += 1

        if not (rng.random() < repeat_rate):
            continue

        n_repeat = rng.integers(1, 6)  # до 5 повторных
        payment_number = 1  # уже один платёж

        for _ in range(n_repeat):
            # Интервал до следующего платежа; ограничиваем разброс, чтобы часть пользователей платила в соседних месяцах
            gap_days = rng.uniform(7, min(churn_days, 70))
            if gap_days > churn_days:
                break
            last_paid = last_paid + timedelta(days=gap_days)
            payment_number += 1

            # С 3-го платежа и далее — рост суммы (лояльные)
            if payment_number >= 3:
                # Выше среднего: от середины диапазона до max_amount
                mid = (min_amount + max_amount) / 2
                amount = rng.uniform(mid, max_amount)
            else:
                amount = rng.uniform(min_amount, max_amount)

            rows.append({
                "user_id": uid,
                "payment_id": payment_id,
                "amount": round(amount, 2),
                "paid_at": last_paid,
            })
            payment_id += 1

    return (
        pd.DataFrame(rows)
        if rows
        else pd.DataFrame(columns=["user_id", "payment_id", "amount", "paid_at"])
    )


def build_cohorts(
    users_df: pd.DataFrame,
    payments_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Строит когорты по месяцу регистрации и считает revenue по месяцам жизни когорты.

    Returns:
        cohort_revenue: pivot-таблица revenue по когорте и месяцу
        cohort_ltv: накопительный LTV по когортам
    """
    if users_df.empty or payments_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    users = users_df.copy()
    users["cohort"] = users["registered_at"].dt.to_period("M").astype(str)
    users["reg_month"] = users["registered_at"].dt.to_period("M")

    pay = payments_df.merge(users[["user_id", "cohort", "reg_month"]], on="user_id")
    pay["paid_month"] = pay["paid_at"].dt.to_period("M")
    pay["month_number"] = (pay["paid_month"] - pay["reg_month"]).apply(
        lambda x: x.n if hasattr(x, "n") and x.n >= 0 else 0
    )

    cohort_revenue = pay.pivot_table(
        index="cohort",
        columns="month_number",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )

    cohort_sizes = users.groupby("cohort").size()
    cohort_ltv = cohort_revenue.cumsum(axis=1).div(cohort_sizes, axis=0)

    return cohort_revenue, cohort_ltv


def build_retention_cohorts(
    users_df: pd.DataFrame,
    payments_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Retention по когортам: % платящих, вернувшихся к платежу в месяц N
    (из тех, кто платил в месяце 0).
    Значение в ячейке (cohort, month_N) = % пользователей когорты, плативших в M0 и снова в MN.
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

    # Платящие в месяце 0 по когортам
    pay_m0 = pay[pay["month_number"] == 0].groupby("cohort")["user_id"].apply(set).to_dict()
    cohort_sizes_m0 = {c: len(s) for c, s in pay_m0.items()}

    # По каждой когорте и месяцу — сколько из M0 платили в MN
    retention_data = []
    for cohort in pay["cohort"].unique():
        payers_m0 = pay_m0.get(cohort, set())
        if not payers_m0:
            continue
        n_m0 = len(payers_m0)
        for month_num in sorted(pay["month_number"].unique()):
            payers_mn = set(
                pay[(pay["cohort"] == cohort) & (pay["month_number"] == month_num)]["user_id"]
            )
            returned = len(payers_m0 & payers_mn)
            pct = returned / n_m0 * 100 if n_m0 else 0
            retention_data.append({"cohort": cohort, "month_number": month_num, "retention_pct": pct})

    if not retention_data:
        return pd.DataFrame()
    ret_df = pd.DataFrame(retention_data)
    retention_pivot = ret_df.pivot(
        index="cohort", columns="month_number", values="retention_pct"
    ).fillna(0)
    return retention_pivot


def build_user_cohorts(
    users_df: pd.DataFrame,
    payments_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Количество уникальных платящих по когортам и месяцам жизни (активность).
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

    cohort_users = pay.groupby(["cohort", "month_number"])["user_id"].nunique()
    user_pivot = cohort_users.unstack(fill_value=0)
    return user_pivot
