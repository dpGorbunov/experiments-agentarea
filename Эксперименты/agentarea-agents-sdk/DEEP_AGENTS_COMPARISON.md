# Сравнение с Deep Agents (LangChain)

Реализация архитектуры Deep Agents из LangChain, адаптированная для agentarea-agents-sdk без зависимости от LangGraph/LangChain.

**Демонстрация:** `demo_deep_agents_integration.ipynb`

## Что реализовано

### StatefulAgent

Агент с поддержкой планирования, суб-агентов и управления контекстом через middleware stack.

**Конфигурация:**

```python
agent = StatefulAgent(
    name="agent",
    instruction="...",
    model_provider="ollama_chat",
    model_name="qwen2.5:3b",
    enable_default_middleware=True,  # Включить все middleware
    enable_todolist=True,            # TodoListMiddleware
    enable_filesystem=True,          # FilesystemMiddleware
    enable_subagents=True,           # SubAgentMiddleware
    enable_summarization=True,       # SummarizationMiddleware
    max_tokens_before_summary=50000,
    messages_to_keep=6,
    subagents=[...],
)
```

### Компоненты middleware

**1. TodoListMiddleware**
- Управление списком задач через `write_todos` tool
- Блокировка пустых планов (агент должен создать шаги сам)
- Обновление state через `_skip_execution` флаг
- Интегрирован через PLANNING_INSTRUCTIONS в prompts.py

**2. FilesystemMiddleware**
- Виртуальная файловая система в state["files"]
- Context eviction: результаты >80k символов сохраняются в файловую систему, агент получает ссылку
- Набор инструментов: save_file, read_file, list_files, search_files, edit_file, grep

**3. SubAgentMiddleware**
- `task` tool для делегирования задач изолированным суб-агентам
- General-purpose агент (копия основного) + кастомные суб-агенты
- Блокировка делегирования без плана (обязательный write_todos перед task)
- Рекурсивные middleware для суб-агентов (TodoList + FS + Summarization)
- Factory паттерн: default_agent_class + default_agent_kwargs

**4. SummarizationMiddleware**
- Суммаризация через LLM при превышении max_tokens_before_summary
- Сохранение последних messages_to_keep сообщений
- Fallback на обрезку при ошибке LLM
- Использует DEFAULT_SUMMARY_PROMPT из LangChain

### State management
- InMemoryState (по умолчанию) или custom StateBackend
- State хранит: messages, todos, files, iteration, initialized

### Промпты
- Скопированы и адаптированы из Deep Agents
- Оптимизация: детальные инструкции в описании tool + краткие в system prompt
- LangChain copyright attribution

### Тестирование
- 9 интеграционных тестов в test_deep_agent_integration.py
- Проверка всех компонентов middleware
- Проверка file tools, context eviction, subagents

## Отличия от Deep Agents (LangChain)

**Архитектурные:**
- Без зависимостей LangGraph/LangChain
- InMemoryState вместо LangGraph checkpointer
- Экземпляры StatefulAgent вместо CompiledStateGraph
- model_provider + model_name вместо model string (универсальность для Ollama/OpenAI)

**Функциональные:**
- Нет execute tool (нет sandbox backend)
- Нет vendor-specific middleware (AnthropicPromptCachingMiddleware, PatchToolCallsMiddleware)
- Порог суммаризации настраивается (по умолчанию 50k vs 170k)
- Добавлен fallback в SummarizationMiddleware
- Флаги enable для гибкого контроля middleware (enable_todolist, enable_filesystem, enable_subagents, enable_summarization)

**Лицензия:** LangChain copyright attribution согласно MIT license.
