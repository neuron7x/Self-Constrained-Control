# Project documentation and quality checklist (UA prompt coverage)

This note maps the repository's existing assets to the required documentation, testing, CI/CD, and security expectations from the provided Ukrainian prompt.

## 1. Документація проекту
- **Мета та компоненти**: див. `README.md` (огляд), `docs/ARCHITECTURE.md` (потоки даних, модулі), `docs/REQUIREMENTS.md` (перевірювані вимоги), `docs/FORMALIZATION.md` (інваріанти, контракти), `docs/SAFETY_CASE.md` (аргументи безпеки).
- **Встановлення та середовище**: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev,sim]"`. Конфіґурація прикладу: `data/n1_config.yaml`; CLI запуск: `python -m self_constrained_control.cli run --config data/n1_config.yaml --actions move_arm,plan_route,stop --epochs 2`.
- **Залежності та оточення**: основні залежності описані в `pyproject.toml` і дублюються в `requirements.txt`; дев-залежності — у `requirements-dev.txt`. Опціональні екстри: `sim`, `ml`, `data`, `dev`.
- **Пояснення коду**: публічні класи/методи мають тайпінги; див. `src/self_constrained_control/` для модулів `neural_interface`, `budget_manager`, `planner_module`, `system`, `monitoring`. Приклади використання — в CLI (`src/self_constrained_control/cli.py`) і тестах.
- **Типи та перевірка даних**: проект суворо типізований (mypy `strict`), структуровані контракти — у `src/self_constrained_control/contracts.py`.
- **Принципи проєктування**: модульність, ізоляція через контракти та інваріанти; застосування S.O.L.I.D. через чіткі інтерфейси модулів (actuator/decoder/planner) і розділення обов’язків між симуляцією, плануванням та бюджетуванням.

## 2. Структура та опис тестів
- **Юніт-тести**: `tests/test_contracts.py`, `tests/test_neural_interface.py`, `tests/test_budget.py`, `tests/test_planner.py`, `tests/test_numerics.py`, `tests/test_biophysics.py`.
- **Інтеграційні тести**: `tests/test_integration.py`, `tests/test_system.py` (перевірка наскрізних шляхів планування/актуації).
- **Безпекові перевірки**: контрактні тести охоплюють валідацію даних та інваріанти (запобігання некоректним станам).
- **Продуктивність**: інфраструктура `pytest-benchmark` доступна; додайте сценарії за потреби.
- **Запуск**: `pytest` (див. `pytest.ini` для покриття, граничних умов та прапорців).

## 3. CI/CD та автоматизація
- Рекомендований конвеєр GitHub Actions: етапи `ruff check`, `ruff format --check`, `mypy`, `pytest --cov`, за потреби — збірка пакета (`python -m build`).
- Перевірка залежностей/уразливостей: Dependabot (`.github/dependabot.yml`, якщо активовано), Snyk або аналогічні сканери можна запускати поверх `requirements*.txt`.
- Статичний аналіз/стиль: проєкт використовує `ruff` (літинг + форматування). За необхідності сумісно з Flake8/Black/SonarQube (міграція через відповідні конфіги).
- Деплой: див. `docs/DEPLOYMENT.md` щодо артефактів і безпечних меж; розгортання реального актуатора вимагає додаткового огляду безпеки.

## 4. Залежності та конфігурація
- **Файли**: `requirements.txt`, `requirements-dev.txt`, екстри в `pyproject.toml`.
- **Середовище**: змінні конфігурації читаються з YAML (`data/n1_config.yaml`), параметри модулів розділені за ролями (decoder/planner/actuator).
- **Сервери/продакшн**: див. `docs/DEPLOYMENT.md`; використовуйте окремі секрети та сховища для токенів/ключів.

## 5. Безпека
- Базові принципи — у `SECURITY.md` та `docs/SAFETY_CASE.md` (ризики/мітигації).
- Рекомендовані практики: керування секретами через захищені змінні CI або Vault-постачальник; за потреби — HashiCorp Vault для довгоживучих токенів.
- Сканування: `bandit -r src` (ручний запуск), OWASP керівництва для конфігурацій/ін’єкцій; статичні контракти в коді блокують некоректні дані.

## 6. Участь та внески
- Процес внесків описано в `CONTRIBUTING.md` та `CODE_OF_CONDUCT.md`.
- Перед PR: запустіть `ruff check . && mypy src && pytest`. Додавайте тести до нових функцій; документуйте зміни в `docs/` при розширенні API або протоколів.

## 7. QL Code
- Поточна реалізація працює з in-memory симуляціями та конфігами YAML; окремого GraphQL/QL шару немає.
- Для інтеграції GraphQL/QL передбачте резолвер, який читає поточний `SystemSnapshot`/`BudgetSnapshot` з `self_constrained_control.system`/`contracts` і експонує їх через схему (наприклад, `gql`/`ariadne`). Запити мутацій можуть делегуватися до існуючих дій CLI.

## 8. Високі стандарти
- Код повністю типізований, тести покривають ключові інваріанти; очікується зелений `pytest --cov`.
- Дотримуйтеся контрактів та інваріантів при змінах; підтримуйте модульність і чисту архітектуру (S.O.L.I.D).
- Безпека і контроль якості — обов’язкові: статичний аналіз, лінтинг, тестування кожного PR.
