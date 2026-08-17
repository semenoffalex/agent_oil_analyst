# Нефтегазовый аналитик

Старший аналитик нефтегазового рынка: ответы по **Reports** (OPEC MOMR, EIA STEO), **Web sources** (DuckDuckGo + denylist «жёлтой прессы»), **Forecast** (SARIMA + Holt–Winters по `yfinance`).

Ouroboros в заголовке задания **не используется** (ADR 0002).

## Стек и почему

- **LLM:** `deepseek-v4-flash`, thinking **выключен**. OpenAI-совместимый API, tool-calling, один ключ.
- **Оркестрация:** LangGraph; публичный шов — `run_turn` (вопрос → ответ + цитаты + флаги инструментов). Chainlit — адаптер UI.
- **RAG:** `intfloat/multilingual-e5-base` + Chroma in-process (RU/EN, без второго API).
- **Поиск:** DuckDuckGo, без Tavily-ключа. Фильтр — denylist доменов, не allowlist.
- **Forecast:** `statsmodels` SARIMA и Holt–Winters, оба прогона, без среднего. Prophet/LSTM нет.
- **UI:** Chainlit — чат из коробки, один процесс с LangGraph. Не Streamlit (rerun на каждое сообщение), не Gradio, не свой FastAPI-фронт.

## Запуск

```bash
cp .env.example .env
# вписать DEEPSEEK_API_KEY

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m oil_gas_analyst          # опционально: скачать Full Reports и проиндексировать
chainlit run oil_gas_analyst/app.py --port 8000
```

Docker:

```bash
cp .env.example .env   # DEEPSEEK_API_KEY
docker compose up --build
```

Открыть http://localhost:8000. `docker-compose.yml` ходит за e5 на `http://192.168.0.55:1234/v1` (`text-embedding-multilingual-e5-base`). Пустой `EMBEDDING_BASE_URL` — локальный SentenceTransformer из образа. Чат по-прежнему DeepSeek. Индекс Sample Reports — при первом старте, если том Chroma пуст.

Тесты (без сети и без LLM):

```bash
pytest -q
```

## Водопад хода

1. Классификатор Competence (`in`/`out`). `out` → отказ, без инструментов. «What's the weather today?» тоже отказ.
2. Route lists: глаголы Forecast; маркеры Time-sensitive. Промах списка = промах.
3. Всегда retrieve k=10 Chunks. Модель может Drop.
4. Web: Time-sensitive **или** все Chunks Dropped, и только если `in`.
5. Forecast только при явном глаголе (forecast / спрогнозируй / оцени диапазон / …). «Brent in 3 months» без глагола — не Forecast.
6. Цитаты: `[Отчёт …]` / `[Источник: …, web](url)` / `[Forecast …]`. Web — кликабельный URL. Sample Reports помечаются excerpt.

## Демо-диалоги (минимум 5)

1. **Отчёт.** `What is OPEC's 2026 world oil demand outlook?`  
   Ожидание: цитата MOMR excerpt, без обязательного web.
2. **Web.** `What's the latest OPEC statement on output?`  
   Ожидание: Web sources, не kp.ru / dailymail.
3. **Комбинированный.** `What's Brent today given OPEC demand?`  
   Ожидание: Report + web в Sources.
4. **Forecast.** `спрогнозируй цену Brent на 3 месяца`  
   Ожидание: SARIMA и Holt–Winters, интервалы, не среднее. WTI — если назван. Urals — «no series».
5. **Вне Competence.** `what's the weather today?` или `write a Python sort` или `Kazakhstan uranium outlook`  
   Ожидание: отказ, без web и без Forecast.

## Данные

- Sample Reports в `data/samples/`: OPEC MOMR June 2024/2026, EIA STEO August 2026 (excerpt + full), бюллетень ЦБ «О чем говорят тренды» июль 2026. Без samples установка сломана.
- Переиндексация: при старте, если отпечаток корпуса не совпал (в т.ч. старый том с STEO excerpt). Принудительно: `python -m oil_gas_analyst`.

## Ограничения v1

- Denylist отстаёт: незакрытый таблоид может просочиться.
- DuckDuckGo и Yahoo (`yfinance`) в Docker иногда падают → неопределённость, не выдуманные цифры.
- Классификатор Competence может дрожать; демо вне темы — только очевидные кейсы.
- Heading-regex не покрывает все врезки STEO; хвосты идут как `(untitled)`.
- Нет ряда Urals. IEA в корпус не входит.

## Архитектура

См. `CONTEXT.md` (глоссарий) и `docs/adr/`. Спека: `.scratch/oil-gas-analyst/spec.md`.
