"""
Сохранение и загрузка сценариев, история экспериментов, экспорт отчётов.
Все данные хранятся в папке data/ (создаётся при первом использовании).
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Корневая папка проекта (родитель каталога utils)
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCENARIOS_DIR = DATA_DIR / "scenarios"
REPORTS_DIR = DATA_DIR / "reports"
HISTORY_CSV = DATA_DIR / "experiment_history.csv"


def ensure_data_dirs() -> None:
    """Создаёт папки data/, data/scenarios/, data/reports/ при отсутствии."""
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)


# ——— Сценарии (JSON) ———

def _scenario_defaults() -> Dict[str, Any]:
    return {
        "n_users": 2000,
        "conversion_rate": 12,
        "pct_ads": 30,
        "pct_organic": 50,
        "pct_referral": 20,
        "seasonality_enabled": True,
        "min_amount": 99,
        "max_amount": 5000,
        "ab_test": True,
        "cac": 500,
        "seed": 42,
    }


def scenario_to_dict(
    n_users: int,
    conversion_rate: int,
    pct_ads: int,
    pct_organic: int,
    pct_referral: int,
    seasonality_enabled: bool,
    min_amount: int,
    max_amount: int,
    ab_test: bool,
    cac: int,
    seed: int,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Собирает текущие параметры в словарь для сохранения."""
    d = {
        "name": name or "Сценарий",
        "saved_at": datetime.now().isoformat(),
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
        "seed": seed,
    }
    return d


def save_scenario_to_file(params: Dict[str, Any], filename: str, overwrite: bool = False) -> Path:
    """Сохраняет сценарий в data/scenarios/{filename}.json. Если файл существует и overwrite=False — FileExistsError."""
    ensure_data_dirs()
    path = SCENARIOS_DIR / filename
    if not path.suffix or path.suffix.lower() != ".json":
        path = path.with_suffix(".json")
    if path.exists() and not overwrite:
        raise FileExistsError(f"Файл уже существует: {path}. Используйте overwrite=True для перезаписи.")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False, indent=2)
    return path


def list_scenario_files() -> List[str]:
    """Возвращает список имён файлов сценариев (без пути)."""
    ensure_data_dirs()
    return [f.name for f in SCENARIOS_DIR.glob("*.json")]


def load_scenario_from_file(filename: str) -> Dict[str, Any]:
    """Загружает сценарий из data/scenarios/{filename}. Расширение .json добавляется автоматически, если не указано."""
    path = SCENARIOS_DIR / filename
    if not path.suffix or path.suffix.lower() != ".json":
        path = path.with_suffix(".json")
    if not path.is_file():
        raise FileNotFoundError(f"Сценарий не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    defaults = _scenario_defaults()
    for k in defaults:
        if k not in data and k != "name":
            data[k] = defaults[k]
    return data


def load_scenario_from_bytes(content: bytes) -> Dict[str, Any]:
    """Загружает сценарий из содержимого JSON (загруженный файл)."""
    data = json.loads(content.decode("utf-8"))
    defaults = _scenario_defaults()
    for k in defaults:
        if k not in data:
            data[k] = defaults[k]
    return data


# ——— История экспериментов (CSV) ———

HISTORY_COLUMNS = [
    "timestamp",
    "n_users",
    "conversion_rate",
    "pct_ads",
    "pct_organic",
    "pct_referral",
    "seasonality_enabled",
    "min_amount",
    "max_amount",
    "ab_test",
    "cac",
    "seed",
    "total_users",
    "conv_rate",
    "arpu",
    "arppu",
    "ltv_3",
    "ltv_6",
    "paying_share",
    "churn_rate",
    "scenario_name",
]


def _round_metric(v: Any) -> Any:
    """Округляет float до 2 знаков; остальное без изменений."""
    if isinstance(v, float):
        return round(v, 2)
    return v


def append_experiment(
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    scenario_name: Optional[str] = None,
) -> None:
    """Добавляет запись в data/experiment_history.csv. Float-метрики округляются до 2 знаков."""
    ensure_data_dirs()
    row = {col: None for col in HISTORY_COLUMNS}
    row["timestamp"] = datetime.now().isoformat()
    row["n_users"] = params.get("n_users")
    row["conversion_rate"] = params.get("conversion_rate")
    row["pct_ads"] = params.get("pct_ads")
    row["pct_organic"] = params.get("pct_organic")
    row["pct_referral"] = params.get("pct_referral")
    row["seasonality_enabled"] = params.get("seasonality_enabled")
    row["min_amount"] = params.get("min_amount")
    row["max_amount"] = params.get("max_amount")
    row["ab_test"] = params.get("ab_test")
    row["cac"] = params.get("cac")
    row["seed"] = params.get("seed")
    row["total_users"] = metrics.get("total_users")
    row["conv_rate"] = _round_metric(metrics.get("conv_rate"))
    row["arpu"] = _round_metric(metrics.get("arpu"))
    row["arppu"] = _round_metric(metrics.get("arppu"))
    row["ltv_3"] = _round_metric(metrics.get("ltv_3"))
    row["ltv_6"] = _round_metric(metrics.get("ltv_6"))
    row["paying_share"] = _round_metric(metrics.get("paying_share"))
    row["churn_rate"] = _round_metric(metrics.get("churn_rate"))
    row["scenario_name"] = scenario_name or ""
    df = pd.DataFrame([row], columns=HISTORY_COLUMNS)
    write_header = not HISTORY_CSV.exists()
    df.to_csv(HISTORY_CSV, mode="a", index=False, header=write_header, encoding="utf-8-sig")


def load_experiment_history() -> pd.DataFrame:
    """Читает историю экспериментов из data/experiment_history.csv."""
    ensure_data_dirs()
    if not HISTORY_CSV.exists():
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    df = pd.read_csv(HISTORY_CSV, encoding="utf-8-sig")
    return df


# ——— Экспорт отчёта (HTML) ———

def _fmt_metric(v: Any, fmt: str = "{:.1f}") -> str:
    if v is None or (not isinstance(v, (int, float))):
        return "—"
    return fmt.format(v)


def _df_to_html_table(df: pd.DataFrame, max_rows: int = 5) -> str:
    """Первые max_rows строк DataFrame в HTML-таблице."""
    if df.empty:
        return "<p>Нет данных.</p>"
    head = df.head(max_rows)
    return head.to_html(index=False, classes="data-table", border=0, escape=False)


def build_report_html(
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    insights: List[str],
    recommendations: List[str],
    plotly_html_snippets: Dict[str, str],
    ab_result: Optional[Dict[str, Any]] = None,
    data_users_html: Optional[str] = None,
    data_payments_html: Optional[str] = None,
    scenario_name: str = "Сценарий",
    low_data_warning: Optional[str] = None,
    churn_days_label: str = "60d",
) -> str:
    """
    Собирает самодостаточный HTML-отчёт с титулом, оглавлением, метриками,
    выводами, рекомендациями, блоком A/B (если есть), графиками и примером данных.
    """
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")
    m = metrics
    scenario_title = scenario_name or "Сценарий"

    # Титульный блок и предупреждение
    warning_block = ""
    if low_data_warning:
        warning_block = f'<div class="warning-box">{low_data_warning}</div>'

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Отчёт: {scenario_title}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 960px; color: #e6edf3; background: #0d1117; }}
        h1 {{ color: #58a6ff; font-size: 1.8rem; }}
        h2 {{ color: #8b949e; margin-top: 2.5rem; font-size: 1.25rem; }}
        h3 {{ color: #b1bac4; margin-top: 1.5rem; font-size: 1.1rem; }}
        table {{ border-collapse: collapse; width: 100%; margin: 0.5rem 0; }}
        th, td {{ border: 1px solid #30363d; padding: 8px 12px; text-align: left; }}
        th {{ background: #161b22; color: #58a6ff; }}
        .toc {{ background: #161b22; padding: 1rem 1.5rem; border-radius: 8px; margin: 1rem 0; }}
        .toc a {{ color: #58a6ff; }}
        .toc ul {{ margin: 0.5rem 0 0 1rem; padding: 0; }}
        .insight {{ background: #161b22; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #58a6ff; }}
        .recommendation {{ background: #1c2128; padding: 0.75rem 1rem; border-radius: 6px; margin: 0.4rem 0; border-left: 4px solid #3fb950; }}
        .chart {{ margin: 1.5rem 0; }}
        .meta {{ color: #8b949e; font-size: 0.9rem; }}
        .title-page {{ text-align: center; padding: 3rem 0; }}
        .warning-box {{ background: #3d2a1a; border: 1px solid #d29922; color: #e6edf3; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        .ab-block {{ background: #161b22; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        .data-table {{ font-size: 0.85rem; }}
        .report-footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #30363d; color: #8b949e; font-size: 0.85rem; }}
    </style>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div class="title-page" id="top">
        <h1>📊 Product Metrics Sandbox</h1>
        <p style="font-size: 1.2rem; color: #b1bac4;">{scenario_title}</p>
        <p class="meta">Дата формирования: {ts}</p>
    </div>
    {warning_block}

    <h2 id="toc">📑 Оглавление</h2>
    <div class="toc">
        <ul>
            <li><a href="#params">Параметры сценария</a></li>
            <li><a href="#metrics">Ключевые метрики</a></li>
            <li><a href="#insights">Выводы</a></li>
            <li><a href="#recommendations">Рекомендации</a></li>
            <li><a href="#ab">A/B тест</a></li>
            <li><a href="#charts">Графики</a></li>
            <li><a href="#data">Данные</a></li>
        </ul>
    </div>

    <h2 id="params">📋 Параметры сценария</h2>
    <table>
        <tr><th>Параметр</th><th>Значение</th></tr>
        <tr><td>Пользователей</td><td>{params.get('n_users', '—')}</td></tr>
        <tr><td>Конверсия (базовая), %</td><td>{params.get('conversion_rate', '—')}</td></tr>
        <tr><td>Реклама / Органика / Рефералы, %</td><td>{params.get('pct_ads', '—')} / {params.get('pct_organic', '—')} / {params.get('pct_referral', '—')}</td></tr>
        <tr><td>Сезонность</td><td>{'Да' if params.get('seasonality_enabled') else 'Нет'}</td></tr>
        <tr><td>Платежи: мин–макс, ₽</td><td>{params.get('min_amount', '—')} – {params.get('max_amount', '—')}</td></tr>
        <tr><td>A/B тест</td><td>{'Включён' if params.get('ab_test') else 'Выключен'}</td></tr>
        <tr><td>CAC, ₽</td><td>{params.get('cac', '—')}</td></tr>
        <tr><td>Seed</td><td>{params.get('seed', '—')}</td></tr>
    </table>

    <h2 id="metrics">📊 Ключевые метрики</h2>
    <table>
        <tr><th>Метрика</th><th>Значение</th></tr>
        <tr><td>Всего пользователей</td><td>{m.get('total_users', '—')}</td></tr>
        <tr><td>Платящие пользователи (абс.)</td><td>{m.get('payers_abs', '—')}</td></tr>
        <tr><td>Conversion Rate, %</td><td>{_fmt_metric(m.get('conv_rate'), '{:.1f}')}</td></tr>
        <tr><td>ARPU, ₽</td><td>{_fmt_metric(m.get('arpu'), '{:.2f}')}</td></tr>
        <tr><td>ARPPU, ₽</td><td>{_fmt_metric(m.get('arppu'), '{:.2f}')}</td></tr>
        <tr><td>LTV 3 мес., ₽</td><td>{_fmt_metric(m.get('ltv_3'), '{:.2f}')}</td></tr>
        <tr><td>LTV 6 мес., ₽</td><td>{_fmt_metric(m.get('ltv_6'), '{:.2f}')}</td></tr>
        <tr><td>Средний чек (повторные платежи), ₽</td><td>{_fmt_metric(m.get('avg_check_repeat'), '{:.2f}')}</td></tr>
        <tr><td>Paying Share, %</td><td>{_fmt_metric(m.get('paying_share'), '{:.1f}')}</td></tr>
        <tr><td>Churn Rate ({churn_days_label}), %</td><td>{_fmt_metric(m.get('churn_rate'), '{:.1f}')}</td></tr>
    </table>
    <p class="meta">LTV 3 мес. — средний доход с пользователя за первые 3 месяца жизни; может быть ниже ARPU, т.к. ARPU считается по всем платежам за весь период наблюдения. Churn считается только среди платящих. Для транзакционной модели churn означает отсутствие платежей в данном месяце; показатель может быть выше, чем в подписках (для подписок типично 5–20% в месяц). ROI = (LTV − CAC) / CAC × 100%; у молодых когорт LTV за 6 мес. может быть ещё не накоплен — отрицательный ROI в таком случае ожидаем.</p>

    <h2 id="insights">📈 Выводы</h2>
"""
    for s in insights:
        html += f'    <div class="insight">{s}</div>\n'

    html += '\n    <h2 id="recommendations">💡 Рекомендации</h2>\n'
    for r in recommendations:
        html += f'    <div class="recommendation">{r}</div>\n'

    if ab_result:
        p_val = ab_result.get("p_value")
        uplift = ab_result.get("uplift", 0)
        significant = ab_result.get("significant", False)
        recommendation = ab_result.get("recommendation", "")
        n_control = ab_result.get("n_control", "")
        n_test = ab_result.get("n_test", "")
        html += f"""
    <h2 id="ab">🔬 A/B тест</h2>
    <div class="ab-block">
        <p><strong>Размер выборок:</strong> контроль n={n_control}, тест n={n_test}</p>
        <p><strong>p-value:</strong> {p_val:.4f}</p>
        <p><strong>Uplift конверсии:</strong> {uplift:+.1f}%</p>
        <p><strong>Вывод:</strong> {'Статистически значимо (α=0.05)' if significant else 'Не значимо (α=0.05)'}.</p>
        <p><strong>Рекомендация:</strong> {recommendation}</p>
    </div>
"""
        ab_chart = plotly_html_snippets.get("A/B сравнение", "")
        if ab_chart:
            html += '    <div class="chart"><h3>Сравнение групп</h3>' + ab_chart + "</div>\n"

    html += '\n    <h2 id="charts">📉 Графики</h2>\n'
    for title, snippet in plotly_html_snippets.items():
        if title == "A/B сравнение" and ab_result:
            continue  # уже вывели в блоке A/B
        html += f'    <div class="chart"><h3>{title}</h3>{snippet}</div>\n'

    html += '\n    <h2 id="data">📁 Данные</h2>\n'
    html += "<p class=\"meta\">Первые 5 строк (пример сырых данных).</p>\n"
    if data_users_html:
        html += "<h3>Users</h3>\n" + data_users_html + "\n"
    else:
        html += "<p>Users: нет данных.</p>\n"
    if data_payments_html:
        html += "<h3>Payments</h3>\n" + data_payments_html + "\n"
    else:
        html += "<p>Payments: нет данных.</p>\n"

    html += f'''
    <footer class="report-footer">
        <p>Сформировано: {ts} · Сценарий: {scenario_title}</p>
    </footer>
</body>
</html>'''
    return html


def save_report_to_file(html_content: str) -> Path:
    """Сохраняет HTML-отчёт в data/reports/ и возвращает путь к файлу."""
    ensure_data_dirs()
    name = datetime.now().strftime("report_%Y%m%d_%H%M%S.html")
    path = REPORTS_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return path
