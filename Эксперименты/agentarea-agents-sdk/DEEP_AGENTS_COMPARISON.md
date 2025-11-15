# Сравнение с Deep Agents (LangChain)

## Общий обзор

Наша реализация в `agentarea-agents-sdk` вдохновлена архитектурой Deep Agents из LangChain, но адаптирована для работы с нашей системой агентов без зависимости от LangGraph/LangChain.

## Архитектура middleware

### Deep Agents (LangChain)
```python
deepagent_middleware = [
    TodoListMiddleware(),
    FilesystemMiddleware(backend=backend),
    SubAgentMiddleware(
        default_model=model,
        default_tools=tools,
        subagents=subagents,
        default_middleware=[...],
        general_purpose_agent=True,
    ),
    SummarizationMiddleware(
        model=model,
        max_tokens_before_summary=170000,
        messages_to_keep=6,
    ),
    AnthropicPromptCachingMiddleware(...),
    PatchToolCallsMiddleware(),
]
```

### Наша реализация (StatefulAgent)
```python
default_middlewares = [
    TodoListMiddleware(),                    # ✓ Полностью реализовано
    FilesystemMiddleware(),                  # ✓ Полностью реализовано
    SubAgentMiddleware(
        default_agent_class=StatefulAgent,
        default_agent_kwargs={...},
        subagents=subagents,
        general_purpose_agent=True,
    ),                                       # ✓ Полностью реализовано
    SummarizationMiddleware(
        model_provider=model_provider,
        model_name=model_name,
        max_tokens_before_summary=50_000,    # 50k вместо 170k
        messages_to_keep=6,
    ),                                       # ✓ Полностью реализовано
    # AnthropicPromptCachingMiddleware - НЕ РЕАЛИЗОВАНО (vendor-specific)
    # PatchToolCallsMiddleware - НЕ РЕАЛИЗОВАНО (vendor-specific)
]
```

**Решение:** Не реализовывать vendor-specific middleware (Anthropic, Patch), т.к. работаем с Ollama/любыми LLM.

## Middleware компоненты

### 1. TodoListMiddleware ✅

**Deep Agents:**
- Управляет todo list через `write_todos` tool
- Использует `Command` из LangGraph для обновления state
- Добавляет system prompt через `wrap_model_call`

**Наша реализация:**
- Управляет todo list через `WriteTodosTool` + `TodoListMiddleware`
- Использует `_skip_execution` флаг для перехвата вызова
- Интегрирован через PLANNING_INSTRUCTIONS в prompts.py

**Различия:**
- Deep Agents использует LangGraph Command, мы — прямые state updates
- Наш подход более простой, без зависимости от LangGraph

### 2. FilesystemMiddleware ✅

**Deep Agents:**
- Использует backend (StateBackend, SandboxBackend) для реальных файловых операций
- Context eviction для больших результатов инструментов
- Интегрирован с `execute` tool для выполнения shell команд

**Наша реализация:**
- Context eviction для больших tool results (порог 80k символов)
- Виртуальная файловая система в state["files"]
- НЕТ execute tool (нет sandbox backend)
- FileToolset с 6 методами: save_file, read_file, list_files, search_files, edit_file, grep

**Различия:**
- Deep Agents имеет реальный backend с execute tool
- Мы используем виртуальную FS + context eviction без shell execution
- **Компромисс:** FS всё равно полезна для context eviction, даже без execute

### 3. SubAgentMiddleware ✅

**Deep Agents:**
- `task` tool для делегирования задач subagent'ам
- General-purpose agent (клон main agent) + custom subagents
- Recursive middleware: subagents получают TodoList, FS, Summarization
- Использует LangGraph compiled graphs

**Наша реализация:**
- `task` tool для делегирования
- General-purpose agent + custom subagents
- Recursive middleware: subagents получают TodoList, FS, Summarization
- Использует `StatefulAgent` instances напрямую
- Factory pattern: `default_agent_class` + `default_agent_kwargs`

**Различия:**
- Deep Agents использует CompiledStateGraph, мы — StatefulAgent
- Наш подход более простой, без LangGraph dependency
- **Идентичная логика:** оба поддерживают general-purpose + custom subagents

### 4. SummarizationMiddleware ✅

**Deep Agents:**
- LLM-based summarization через отдельный LLM call
- Trigger: 170k tokens
- Keeps last 6 messages + summary
- Использует DEFAULT_SUMMARY_PROMPT

**Наша реализация:**
- LLM-based summarization через LLMModel
- Trigger: 50k tokens (меньше для экономии)
- Keeps last 6 messages + summary
- Использует тот же DEFAULT_SUMMARY_PROMPT (скопирован)
- Fallback: простая truncation если LLM summarization fails

**Различия:**
- 50k tokens vs 170k tokens (для экономии в Ollama)
- Добавлен fallback механизм для надёжности
- Deep Agents использует LangChain invoke, мы — LLMModel

## Промпты

### Deep Agents
```python
WRITE_TODOS_TOOL_DESCRIPTION = """..."""  # 60+ lines в tool description
WRITE_TODOS_SYSTEM_PROMPT = """..."""     # 15 lines в system prompt
TASK_SYSTEM_PROMPT = """..."""            # 40+ lines для task tool
```

**Оптимизация:** Детальные инструкции в tool description (видны при выборе tool), краткие напоминания в system prompt.

### Наша реализация
- ✅ Скопировали и адаптировали все промпты
- ✅ Используем ту же оптимизацию: detailed tool description + brief system prompt
- ✅ Добавили LangChain copyright attribution

## Файловые инструменты

### Deep Agents
- `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute`
- 7 tools через FilesystemMiddleware backend

### Наша реализация
- `save_file`, `read_file`, `list_files`, `search_files`, `edit_file`, `grep`
- 6 tools через FileToolset
- НЕТ `execute` (нет sandbox)

**Различия:**
- Нет execute tool (требует sandbox backend)
- Остальные 6 инструментов идентичны по функционалу

## State management

### Deep Agents
- LangGraph state: messages, todos
- Checkpointer для persistence
- Store для long-term storage

### Наша реализация
- StateBackend: InMemoryState (default)
- State: messages, todos, files, iteration, initialized
- Поддержка custom StateBackend

**Различия:**
- Deep Agents использует LangGraph checkpointer
- Мы используем простой StateBackend interface
- Оба поддерживают extensibility

## Инициализация агента

### Deep Agents
```python
agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[...],
    system_prompt="...",
    middleware=[...],
    subagents=[...],
    checkpointer=checkpointer,
    store=store,
    backend=backend,
)
```

### Наша реализация
```python
agent = StatefulAgent(
    name="agent",
    instruction="...",
    model_provider="ollama_chat",
    model_name="qwen2.5:3b",
    tools=[...],
    enable_default_middleware=True,
    enable_subagents=True,
    enable_summarization=True,
    subagents=[...],
    state_backend=state_backend,
    max_tokens_before_summary=50_000,
)
```

**Различия:**
- Deep Agents использует model string, мы — provider + model_name (для Ollama)
- Мы добавили enable_* флаги для гибкого контроля middleware
- Deep Agents более унифицирован для Anthropic/OpenAI

## Тестирование

### Deep Agents
- Интеграционные тесты через pytest
- Mock LLM для unit tests
- Примеры использования в docs

### Наша реализация
✅ `test_deep_agent_integration.py`:
- 9 integration tests
- Проверка всех middleware компонентов
- Проверка file tools
- Проверка context eviction
- Проверка subagents
- Проверка system prompts

## Итоговое сравнение

### Что идентично ✅
1. **TodoListMiddleware** — полностью идентичен по логике
2. **SubAgentMiddleware** — идентичен (task tool + general-purpose + custom)
3. **SummarizationMiddleware** — идентичен (LLM-based, 6 messages, summary prompt)
4. **FilesystemMiddleware** — context eviction работает идентично
5. **Промпты** — скопированы и адаптированы с attribution
6. **Архитектура middleware** — порядок и recursive применение идентичны

### Что отличается ⚠️
1. **Execute tool** — отсутствует (нет sandbox backend)
   - **Решение:** Оставили FS для context eviction без execute
2. **Token threshold** — 50k vs 170k
   - **Решение:** Экономия для Ollama, можно настроить
3. **State management** — SimpleStateBackend vs LangGraph checkpointer
   - **Решение:** Проще, без LangGraph dependency
4. **Model initialization** — provider + model_name vs model string
   - **Решение:** Универсальность для Ollama/любых LLM
5. **Vendor-specific middleware** — отсутствуют (Anthropic caching, Patch)
   - **Решение:** Не нужны для Ollama

### Что улучшено 🚀
1. **Enable flags** — enable_subagents, enable_summarization для гибкого контроля
2. **Fallback** — в SummarizationMiddleware на случай LLM failure
3. **Integration tests** — подробные тесты всех компонентов
4. **Simpler architecture** — без LangGraph/LangChain dependencies

## Вывод

Наша реализация **полностью соответствует** архитектуре Deep Agents по всем ключевым компонентам:

✅ Middleware stack идентичен
✅ TodoList, Filesystem, SubAgent, Summarization — реализованы
✅ Промпты скопированы с attribution
✅ File tools реализованы (6 из 7)
✅ Recursive middleware для subagents
✅ System prompts интегрированы

**Единственное значимое отличие:** отсутствие execute tool из-за отсутствия sandbox backend. Это сознательный компромисс, т.к. FS всё равно полезна для context eviction.

**Лицензия:** Все заимствованные компоненты имеют LangChain copyright attribution согласно MIT license.
