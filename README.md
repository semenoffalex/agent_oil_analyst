# Нефтегазовый аналитик

Чат со **старшим аналитиком нефтегазового рынка**. Разговор идёт в **Ouroboros** (агентный цикл: модель выбирает инструменты и когда остановиться). **Chainlit** на порту 8000 — адаптер, не второй агент. Доменные инструменты (поиск по отчётам, веб с denylist, прогноз) — **reviewed skills** в этом репозитории. **`/evolve` выключен** (`runtime_mode=light`).

Доменные Report, Web и Forecast skills уже в цикле Ouroboros. Когда skills включены, ответы цитируют отчёт, веб или расчёт.

## Запуск

### Рекомендуется: Docker

Один `compose`: Chainlit на 8000, Ouroboros внутри сети (порт 8765 не публикуется). Для проверки задания открывайте только Chainlit.

```bash
cp .env.example .env          # указать OPENROUTER_API_KEY
docker compose up --build
```

Откройте http://localhost:8000. Не нужно ставить `Ouroboros.app` и не нужно открывать `:8765`.

Main — OpenRouter `z-ai/glm-5.2:free`, thinking выкл. Heavy / Eval / skill-review без своих id в `.env` используют Main. Нет тихого отката на DeepSeek или Grok. Лимиты `:free` — принятый риск демо.

### Локально (разработка)

Нужен запущенный Ouroboros (`ouroboros server` или контейнер) и ключ OpenRouter.

```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
chainlit run oil_gas_analyst/app.py --port 8000
```

Тесты без сети и LLM: `pytest -q`

Живой **Eval** (ключ OpenRouter, поднятый Ouroboros): `LIVE_EVAL=1 pytest tests/test_graph.py -k TestLiveEval`. Модель Eval — `EVAL_CHAT_MODEL` в `.env`, иначе Main.

**Red-team pack**: `LIVE_RED_TEAM=1 pytest tests/test_graph.py -k TestLiveRedTeam`. Промпты — `config/red_team_pack.yaml`.

**Demo rate limit** — `DEMO_RATE_LIMIT_MAX` и `DEMO_RATE_LIMIT_WINDOW_SEC` в `.env` (0 = выкл. для локалки).

## Что внутри

| Часть | Технология | Зачем |
|-------|------------|--------|
| Цикл агента | Ouroboros v6.103.0 | Модель сама выбирает инструменты и стоп; не LangGraph-водопад |
| Main | OpenRouter `z-ai/glm-5.2:free`, thinking off | Выбор заказчика; TZ разрешает любой LLM |
| Адаптер | Chainlit `:8000` | Окно ревьюера; доказательство Ouroboros — код репозитория |
| Skills | playbook + retrieve + search_web + run_forecast | Все доменные tools в цикле Ouroboros |
| Отчёты (далее) | Chroma + LAN e5 embeddings API | RU/EN, без локального Torch |
| Интернет (далее) | DuckDuckGo + denylist цитат | Бесплатно; denylist — контракт цитирования, не host-strip |
| Прогноз (далее) | SARIMA + Holt–Winters | Два метода, без усреднения |

`/evolve` off. Task-acceptance Review, P3 и `/review` не гоняются на пяти диалогах Eval.

Термины и решения: [`CONTEXT.md`](CONTEXT.md), [`docs/adr/`](docs/adr/).

## Как отвечает на один вопрос

Модель в цикле Ouroboros решает, вызывать ли retrieve, Web, Forecast, и когда остановиться. Нет фиксированного classify → retrieve → compose.

Цитаты, когда tools подключены: `[Отчёт …]`, `[Источник: …, web]`, `[Forecast …]`. Тег `[Отчёт …]` валиден только если retrieve шёл в этом ходе.

## Пять проверочных диалогов

| Сценарий | Пример вопроса | Ожидание |
|----------|----------------|----------|
| Отчёт | `What is OPEC's 2026 world oil demand outlook?` | Цитата MOMR, веб не обязателен |
| Веб | `What's the latest OPEC statement on output?` | Источники из сети, без kp.ru / dailymail |
| Смешанный | `What's Brent today given OPEC demand?` | Отчёт + веб |
| Прогноз | `спрогнозируй цену Brent на 3 месяца` | SARIMA и Holt–Winters, два интервала |
| Вне темы | `what's the weather today?` | Отказ, без выдуманных цифр |

## Данные

Образцы в `data/samples/` (OPEC, EIA, ЦБ) — без них установка RAG сломана. Полные PDF — в `data/reports/` после `python -m oil_gas_analyst`.

## Ограничения

- `:free` GLM: rate limit и простои OpenRouter, без тихой смены модели. Веб-ход может идти несколько минут; таймаут Chainlit по умолчанию 900 с.
- Эмбеддинги отчётов — OpenAI-compatible API (`192.168.0.55:1234`); локальный Torch не ставится.
- Denylist неполный; неперечисленные таблоиды могут просочиться.
- DuckDuckGo и Yahoo в Docker иногда падают.
- Нет ряда Urals; IEA не в корпусе.
- Sample Report ≠ полный MOMR.

---

## Планы развития

Цикл зафиксирован в [ADR 0017](docs/adr/0017-next-cycle-is-public-demo.md): публичный **Demo** (URL без клона). DNS — только после живого Eval и red-team pack. Пароля нет, лимит запросов есть.

### Этот цикл — до URL

- [x] **Ouroboros loop** за Chainlit `:8000` ([0021](docs/adr/0021-chainlit-adapter-ouroboros-loop.md))
- [ ] Report retrieve, Web, Forecast как reviewed skills
- [ ] Demo на VPS

### Только с новым ADR

- [ ] Память для Route lists / denylist из чата ([0005](docs/adr/0005-closed-route-lists.md))
- [ ] Postgres + pgvector вместо Chroma ([0007](docs/adr/0007-e5-chroma-reports.md))
