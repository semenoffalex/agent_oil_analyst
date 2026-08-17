# Нефтегазовый аналитик

Чат со **старшим аналитиком нефтегазового рынка**. Сначала ищет ответ в **отчётах** (OPEC MOMR, EIA STEO, бюллетень ЦБ), при необходимости — в **интернете** (DuckDuckGo, с фильтром «жёлтой прессы»), по явной просьбе строит **прогноз цены** (SARIMA и Holt–Winters на данных `yfinance`).

Каждый ответ с цитатами: откуда взята цифра — отчёт, веб или расчёт.

## Запуск

### Рекомендуется: Docker

Один образ, тома для индекса и отчётов, без установки моделей на хост. Для демо и проверки задания — начинайте здесь.

```bash
cp .env.example .env          # указать DEEPSEEK_API_KEY
docker compose up --build
```

Откройте http://localhost:8000.

По умолчанию эмбеддинги идут на LM Studio (`http://192.168.0.55:1234/v1`). Пустой `EMBEDDING_BASE_URL` — локальная e5 из образа. Чат всегда через DeepSeek. Индекс отчётов поднимается сам при первом старте, если Chroma пуст или устарел.

### Локально (разработка)

```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m oil_gas_analyst     # по желанию: скачать полные PDF и переиндексировать
chainlit run oil_gas_analyst/app.py --port 8000
```

Тесты без сети и LLM: `pytest -q`

Живой **Eval** (ключ OpenRouter, индекс, сеть): `LIVE_EVAL=1 pytest tests/test_graph.py -k TestLiveEval`. Модель Eval — `EVAL_CHAT_MODEL` в `.env`; продукт и Demo остаются на DeepSeek.

**Red-team pack** (тот же OpenRouter и индекс): `LIVE_RED_TEAM=1 pytest tests/test_graph.py -k TestLiveRedTeam`. Промпты — `config/red_team_pack.yaml`.

## Что внутри

| Часть | Технология | Зачем |
|-------|------------|--------|
| Чат | `deepseek-v4-flash`, thinking выкл. | Один API-ключ, вызов инструментов, оптимальное соотношение цена/качество |
| Оркестрация | LangGraph → `run_turn` | де-факто стандарт для создания агентов |
| Интерфейс | Chainlit | Чат в одном процессе с графом |
| Отчёты | e5 + Chroma | RU/EN, без второго embedding API |
| Интернет | DuckDuckGo + denylist | Бесплатно, не требует ключа API |
| Прогноз | SARIMA + Holt–Winters | Два метода, без усреднения |

Термины и решения: [`CONTEXT.md`](CONTEXT.md), [`docs/adr/`](docs/adr/).

## Как отвечает на один вопрос

1. **Компетенция** — тема про нефть/газ или отказ («what's the weather today?» → отказ).
2. **Списки маршрутов** — глагол прогноза или маркер «нужна свежесть» (закрытые EN/RU списки).
3. **Поиск по отчётам** — top-10 фрагментов; модель отбрасывает лишнее, отброшенное не цитирует.
4. **Веб** — если нужна свежесть или после отбрасывания ничего не осталось.
5. **Прогноз** — только с явным глаголом (`спрогнозируй`, `forecast`, …).
6. **Цитаты** — `[Отчёт …]`, `[Источник: …, web]`, `[Forecast …]`.

Внизу ответа — что запускалось: отчёты, веб (и почему), прогноз, шаги графа.

## Пять проверочных диалогов

| Сценарий | Пример вопроса | Ожидание |
|----------|----------------|----------|
| Отчёт | `What is OPEC's 2026 world oil demand outlook?` | Цитата MOMR, веб не обязателен |
| Веб | `What's the latest OPEC statement on output?` | Источники из сети, без kp.ru / dailymail |
| Смешанный | `What's Brent today given OPEC demand?` | Отчёт + веб |
| Прогноз | `спрогнозируй цену Brent на 3 месяца` | SARIMA и Holt–Winters, два интервала |
| Вне темы | `what's the weather today?` | Отказ, без инструментов |

## Данные

Образцы в `data/samples/` (OPEC, EIA, ЦБ) — без них установка сломана. Полные PDF — в `data/reports/` после `python -m oil_gas_analyst`. Переиндекс Chroma — автоматически при смене корпуса.

## Ограничения

Denylist неполный; DuckDuckGo и Yahoo в Docker иногда падают; классификатор темы может ошибаться; нет ряда Urals; IEA не в корпусе.

---

## Планы развития

Цикл зафиксирован в [ADR 0017](docs/adr/0017-next-cycle-is-public-demo.md): публичный **Demo** (URL без клона). DNS — только после живого Eval и red-team pack. Пароля нет, лимит запросов есть (число — на деплое).

### Этот цикл — до URL

- [x] **Eval** — живой прогон пяти диалогов README на поднятом Analyst. Смотрим флаги и denylist, не золотую прозу. `pytest` с моками — не Eval.
- [x] **Red-team pack** — `LIVE_RED_TEAM=1 pytest tests/test_graph.py -k TestLiveRedTeam`; промпты в `config/red_team_pack.yaml`.
- [ ] **Лимит запросов** — без пароля; потолок IP/окно настраивается на VPS.
- [ ] **Demo на VPS** — [рецепт RUVDS](https://habr.com/ru/companies/ruvds/articles/1053382/). На машине e5 из образа (`EMBEDDING_BASE_URL` пустой), не LAN LM Studio.

### После Demo

- [ ] Свежесть Web-источников (recency; идея от Булата)
- [ ] Графики прогноза
- [ ] Веб по явной просьбе («поищи в интернете») — закрытый список
- [ ] Скилл ingest (ЦБ, EIA, OPEC)
- [ ] Внешние эмбеддинги по API — довести `EMBEDDING_BASE_URL` с fallback

### Только с новым ADR

- [ ] Память для Route lists / denylist из чата ([0005](docs/adr/0005-closed-route-lists.md))
- [ ] Postgres + pgvector вместо Chroma ([0007](docs/adr/0007-e5-chroma-reports.md))
- [ ] Дашборд Streamlit рядом с Chainlit ([0010](docs/adr/0010-chainlit-ui.md))


