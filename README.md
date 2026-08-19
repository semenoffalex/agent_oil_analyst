# Нефтегазовый аналитик

Это чат со старшим аналитиком нефтегазового рынка: спрос OPEC, живые котировки, прогноз Brent. Он не выдумывает цифры — опирается на отчёты, открытый веб или расчёт.

Под капотом разговор ведёт **Ouroboros** (это не LangGraph): модель сама решает, что вызвать и когда остановиться. **Chainlit** на порту **8000** — только окно, адаптер, не второй агент, т.е. окно Ouroboros на `:8765` ревьюеру не нужно.
Поиск по отчётам, веб (с denylist) и прогноз — **reviewed skills** в этом репозитории. Команда **`/evolve` выключена** (`runtime_mode=light`), чтобы агент не переписывал сам себя посреди демо.

Словарь терминов: [`CONTEXT.md`](CONTEXT.md). Решения — в [`docs/adr/`](docs/adr/).

## Как запустить

Самый простой путь — Docker. Один `compose` поднимает чат на 8000, Ouroboros остаётся внутри сети.

```bash
cp .env.example .env          # OPENROUTER_API_KEY или любой другой OPEN-AI-совместимый
docker compose up --build
```

Откройте http://localhost:8000. Ставить `Ouroboros.app` не надо.

Чат идёт через OpenRouter, модель `nvidia/nemotron-3.5-lightning:free` (т.к. в теории должна иметь самый быстрый TtFT из бесплатных), thinking выкл. Если в `.env` не заданы отдельные Heavy / Eval / skill-review — все используют ту же модель. Тихого отката на DeepSeek или Grok нет. Бесплатный слот иногда тормозит или упирается в лимит — для демо это осознанный риск.

### Без Docker

Нужны уже запущенный Ouroboros (`ouroboros server` или контейнер) и тот же ключ.

```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # тесты, ingest и skills
chainlit run oil_gas_analyst/app.py --port 8000
```

Быстрые тесты без сети: `pytest -q`.

Живой **Eval** пяти диалогов ниже: `LIVE_EVAL=1 pytest tests/test_graph.py -k TestLiveEval` (ключ и поднятый Ouroboros). Модель — `EVAL_CHAT_MODEL` или Main.

**Red-team pack** перед публичным URL: `LIVE_RED_TEAM=1 pytest tests/test_graph.py -k TestLiveRedTeam`. Промпты лежат в `config/red_team_pack.yaml`.

На публичном демо нет пароля, есть лимит запросов: `DEMO_RATE_LIMIT_MAX` и `DEMO_RATE_LIMIT_WINDOW_SEC` в `.env` (`0` — выкл. у себя на машине).

## Как он отвечает

На один вопрос модель может сходить в отчёты, в интернет, посчитать прогноз — или сразу отказаться, если тема не про нефть. Порядок не фиксирован.

Когда skills включены (так и есть после `docker compose`), в тексте появляются метки:

- `[Отчёт …]` — цитата из корпуса; считается честной, только если retrieve был **в этом ходе**
- `[Источник: …, web]` — страница из поиска
- `[Forecast …]` — SARIMA и Holt–Winters, два интервала, без усреднения

Пять вопросов, которыми удобно проверить, что всё живое:

| Сценарий | Пример | Чего ждать |
|----------|--------|------------|
| Отчёт | `Что пишут в отчётах по цене на нефть` | Цитата MOMR; веб не обязателен |
| Веб | `А что говорят в новостях?` | Источники из сети, без kp.ru и dailymail |
| Смешанный | `Насколько сегодняшняя цена расходится с отчётом OPEC?` | И отчёт, и веб |
| Прогноз | `спрогнозируй цену Brent на 3 месяца` | Два метода, два интервала |
| Вне темы | `Спрогнозируй погоду на 3 месяца` | Отказ, без выдуманных цифр |

Короткие PDF для поиска лежат в `data/samples/` (OPEC, EIA, ЦБ) — без них индекс не собрать. Полные отчёты качаются в `data/reports/` командой `python -m oil_gas_analyst`.

## Из чего это собрано

Ouroboros **v6.103.0**. Эмбеддинги отчётов — e5 по LAN (`192.168.0.55:1234`), без локального Torch. Веб — DuckDuckGo; denylist запрещает **цитировать** жёлтую прессу, но не вырезает её из выдачи. Прогноз — Yahoo Finance + statsmodels.

Task-acceptance Review, P3 и `/review` на пяти диалогах Eval не гоняются.

## Ограничения

Бесплатные модели на OpenRouter иногда ждёт очередь. Веб-ход может занять несколько минут (таймаут Chainlit по умолчанию 900 с). DuckDuckGo и Yahoo в Docker периодически молчат.

Denylist неполный: таблоид не из списка может проскочить в цитату. Ряда Urals нет, IEA в корпусе нет. Образец MOMR — не полный отчёт.

## Что дальше

Цель цикла — публичный **Demo** по URL, без клонирования репозитория ([ADR 0017](docs/adr/0017-next-cycle-is-public-demo.md)). DNS — после живого Eval и red-team pack.

- [x] Цикл Ouroboros за Chainlit `:8000` ([0021](docs/adr/0021-chainlit-adapter-ouroboros-loop.md))
- [x] Report, Web и Forecast как reviewed skills
- [ ] Скиллы на скачивание свежих отчётов
- [ ] Память 
- [ ] Demo на VPS

Новый ADR понадобится, если захотим память списков из чата ([0005](docs/adr/0005-closed-route-lists.md)) или Postgres + pgvector вместо Chroma ([0007](docs/adr/0007-e5-chroma-reports.md)).
