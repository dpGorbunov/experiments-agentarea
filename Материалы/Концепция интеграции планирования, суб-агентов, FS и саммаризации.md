# Концепция интеграции: Planning, Sub-Agents, File System, Summarization

## 🎯 Цель

Трансформировать текущий SDK из простого ReAct-агента в полнофункциональную платформу для решения сложных, долгосрочных задач (2-24+ часа) с автоматическим управлением контекстом, планированием и делегированием.

---

## 📊 Текущее состояние

### ✅ Что есть

| Компонент | Статус | Проблемы |
|-----------|--------|----------|
| **Agent** | ✅ Реализован | Stateless, нет интеграции с Task/Planning |
| **PlanningTool** | ✅ Базовый | Статичный план, только текст, не интегрирован в workflow |
| **TaskService** | ✅ Полнофункциональный | Не используется Agent, изолирован от основного цикла |
| **FileToolset** | ✅ Базовый | Реальная FS, нет изоляции/виртуализации |
| **ContextService** | ✅ Append-only log | Нет саммаризации, контекст переполняется |
| **GoalProgressEvaluator** | ✅ Примитивный | Keyword matching, нет LLM-based анализа |
| **Sub-Agents** | ❌ Отсутствует | Нет изоляции контекста, делегирования |
| **Middleware** | ❌ Отсутствует | Нет расширяемой архитектуры |

### ⚠️ Ограничения текущего подхода

1. **Контекст переполняется** - нет автоматического управления размером
2. **План не живой** - создается один раз, не обновляется
3. **Нет делегирования** - агент все делает сам
4. **Нет изоляции** - все результаты в основном контексте
5. **Stateless Agent** - теряет историю между вызовами

---

## 🏗️ Архитектурная концепция

### Вдохновение: Deep Agents + Magentic-One

Мы берем лучшее из обоих подходов:

- **Deep Agents**: Middleware архитектура, TODO список в state, виртуальная FS, динамические суб-агенты
- **Magentic-One**: Task/Progress Ledger для двухуровневого планирования

### Ключевые принципы

```
┌─────────────────────────────────────────────────────┐
│                  STATEFUL AGENT                      │
│  ┌───────────────────────────────────────────────┐  │
│  │         MIDDLEWARE STACK (расширяемо)         │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  1. TodoListMiddleware                  │  │  │
│  │  │     - Управление планом в реальном      │  │  │
│  │  │       времени (pending → in_progress    │  │  │
│  │  │       → completed)                      │  │  │
│  │  │     - LLM сам обновляет статусы         │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  2. FilesystemMiddleware                │  │  │
│  │  │     - Виртуальная FS в state            │  │  │
│  │  │     - Context eviction для больших      │  │  │
│  │  │       результатов (>80k chars)          │  │  │
│  │  │     - Автосохранение в /large_results/  │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  3. SummarizationMiddleware             │  │  │
│  │  │     - Автосаммаризация > 170k tokens    │  │  │
│  │  │     - Сохранение последних 6 сообщений  │  │  │
│  │  │     - LLM-based compression             │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  4. SubAgentMiddleware                  │  │  │
│  │  │     - Динамическое создание агентов     │  │  │
│  │  │     - Изоляция контекста                │  │  │
│  │  │     - Возврат только результата         │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  5. ProgressTrackingMiddleware          │  │  │
│  │  │     - Оценка прогресса через LLM        │  │  │
│  │  │     - Детекция застоя (stagnation)      │  │  │
│  │  │     - Триггер корректировки плана       │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │              AGENT STATE                      │  │
│  │  {                                            │  │
│  │    messages: [...],                           │  │
│  │    todos: [{content, status, activeForm}],    │  │
│  │    files: {'/path': 'content'},               │  │
│  │    subagent_results: {...},                   │  │
│  │    context_metadata: {...}                    │  │
│  │  }                                            │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Детальная спецификация компонентов

### 1. TodoListMiddleware

**Назначение**: Управление живым планом задач в state агента

**Механизм**:
```python
# state['todos']
[
    {
        "content": "Analyze codebase structure",  # что нужно сделать
        "activeForm": "Analyzing codebase structure",  # что происходит сейчас
        "status": "in_progress",  # pending | in_progress | completed
        "created_at": "2025-01-15T10:00:00",
        "completed_at": None
    },
    {
        "content": "Generate architecture diagram",
        "activeForm": "Generating architecture diagram",
        "status": "pending",
        "created_at": "2025-01-15T10:00:00",
        "completed_at": None
    }
]
```

**Инструмент для агента**:
```python
write_todos(todos: list[TodoItem])
# LLM может создавать, обновлять, удалять, менять статусы
```

**Промпт-инструкции**:
- ✅ Mark as `in_progress` BEFORE beginning work
- ✅ Mark as `completed` IMMEDIATELY after finishing
- ✅ Don't be afraid to revise the list (add/remove/update)
- ❌ Don't change previously completed tasks

**Интеграция**:
- Middleware перехватывает `write_todos` → обновляет `state['todos']`
- Стриминг: изменения `todos` стримятся отдельным каналом
- UI: рендерит в реальном времени (☐ pending / ⏳ in_progress / ☑ completed)

---

### 2. FilesystemMiddleware

**Назначение**: Виртуальная файловая система + context eviction

#### 2.1 Виртуальная FS

**state['files']**:
```python
{
    "/workspace/analysis.txt": "...",
    "/large_tool_results/call_abc123": "...",
    "/subagent_results/research_task": "..."
}
```

**Инструменты**:
```python
read_file(path, offset=None, limit=None)
write_file(path, content, append=False)
list_files(pattern="*")
search_files(pattern, content_pattern=None)
```

**Преимущества**:
- Изоляция от реальной FS (безопасность)
- Все в state (переносимость, восстановление)
- Версионирование (можно откатывать)

#### 2.2 Context Eviction

**Проблема**: `grep_search()` возвращает 150k символов → контекст переполняется

**Решение**:
```python
# Лимит: 80k символов или 20k токенов
if len(tool_result) > 80_000:
    # Сохраняем в виртуальную FS
    file_path = f"/large_tool_results/{tool_call_id}"
    state['files'][file_path] = tool_result

    # Заменяем результат в контексте
    tool_message.content = (
        f"Result too large ({len(tool_result)} chars). "
        f"Saved to {file_path}. "
        f"Use read_file() with offset/limit to read parts."
    )
```

**Экономия**: 150k → 500 символов в контексте

---

### 3. SummarizationMiddleware

**Назначение**: Автоматическое сжатие контекста при переполнении

**Триггер**: `len(messages_tokens) > 170_000`

**Механизм**:
```python
# Сохраняем последние 6 сообщений в полном виде
recent_messages = messages[-6:]

# Суммируем старые сообщения через LLM
old_messages = messages[:-6]
summary = await llm.summarize(
    old_messages,
    prompt="Summarize key decisions, findings, and context. "
           "Focus on what matters for continuing the task."
)

# Заменяем старые сообщения саммари
new_messages = [
    {"role": "system", "content": f"Previous context summary:\n{summary}"}
] + recent_messages

state['messages'] = new_messages
```

**Экономия**: 170k → 70k токенов (сохраняя ключевой контекст)

**Опции**:
- `max_tokens_before_summary`: порог срабатывания
- `messages_to_keep`: сколько последних сообщений сохранять в полном виде
- `summary_style`: "concise" | "detailed" | "technical"

---

### 4. SubAgentMiddleware

**Назначение**: Делегирование подзадач изолированным агентам

#### 4.1 Механизм создания

**Инструмент**:
```python
task(description: str, prompt: str, context: dict = None) -> str
# LLM решает когда создавать суб-агента
```

**Процесс**:
```python
# 1. Создаем НОВЫЙ агент с чистым контекстом
subagent = Agent(
    name=f"SubAgent-{uuid4()}",
    instruction=prompt,
    model=parent_agent.model,
    max_iterations=50,  # лимит для безопасности
    tools=parent_agent.tools.copy()  # копируем инструменты
)

# 2. Создаем изолированный state
subagent_state = {
    'messages': [{"role": "user", "content": description}],
    'todos': [],
    'files': context.get('files', {}) if context else {},
    # НЕ включаем parent messages/todos - изоляция!
}

# 3. Запускаем суб-агента
result = await subagent.run_with_state(subagent_state)

# 4. Возвращаем только итоговый результат
# Весь промежуточный контекст уничтожается!
return result['final_answer']  # ~500 токенов вместо 50k
```

#### 4.2 Изоляция контекста

**Что НЕ передается суб-агенту**:
- ❌ `parent.state['messages']` - история главного агента
- ❌ `parent.state['todos']` - план главного агента
- ❌ Промежуточные результаты инструментов

**Что передается**:
- ✅ Необходимые файлы из `parent.state['files']` (опционально)
- ✅ Конкретная задача (`description`)
- ✅ Копия инструментов

**Почему это важно**:
```
Без изоляции:
  Main agent: 100k tokens (history)
  + Subagent work: 50k tokens
  = 150k tokens → переполнение

С изоляцией:
  Main agent: 100k tokens
  + Subagent result: 0.5k tokens (только итог)
  = 100.5k tokens → управляемо
```

#### 4.3 Когда использовать суб-агентов

**LLM сам решает**, но мы даем в промпте подсказки:

```
Use the 'task' tool to delegate when:
- Research that requires many searches (e.g., "Research X technology")
- Complex analysis with multiple steps (e.g., "Analyze codebase architecture")
- Tasks that can be isolated (e.g., "Generate test cases for module Y")

Don't use subagents for:
- Simple tool calls (e.g., read one file)
- Tasks requiring main agent context
- Final synthesis/reporting (you should do this yourself)
```

---

### 5. ProgressTrackingMiddleware

**Назначение**: Оценка прогресса и детекция застоя

#### 5.1 Оценка прогресса

**Метрики**:
```python
progress = {
    'completed_todos': 3,
    'total_todos': 8,
    'percentage': 37.5,
    'last_todo_completed_at': '2025-01-15T10:30:00',
    'time_since_last_completion': '5m 30s',
    'tool_calls_since_last_completion': 12,
    'current_iteration': 45
}
```

#### 5.2 Детекция застоя

**Признаки застоя** (stagnation):
- ⚠️ 2+ итерации подряд без изменения `in_progress` задачи
- ⚠️ 10+ tool calls без completed задачи
- ⚠️ Повторяющиеся ошибки инструментов (3+ раз одна и та же)
- ⚠️ Циклические вызовы инструментов (паттерн повторяется)

**Действия при застое**:
```python
# 1. Inject system message
inject_message({
    "role": "system",
    "content": (
        "⚠️ Progress Update:\n"
        "- 2 iterations without progress on current task\n"
        "- Consider: Is your approach working?\n"
        "- Options: Try different tool, break into subtasks, ask for help\n"
        "- Update todos if your plan needs revision"
    )
})

# 2. Опционально: trigger LLM re-planning
if stagnation_count > 3:
    force_tool_call("write_todos")  # заставляем пересмотреть план
```

#### 5.3 Интеграция с GoalProgressEvaluator

**Улучшение текущего evaluator**:

```python
class EnhancedGoalProgressEvaluator:
    async def evaluate_with_llm(
        self,
        goal: str,
        success_criteria: list[str],
        todos: list[TodoItem],
        recent_messages: list[dict]
    ) -> dict:
        """LLM-based оценка вместо keyword matching."""

        evaluation_prompt = f"""
        Goal: {goal}

        Success Criteria:
        {'\n'.join(f'- {c}' for c in success_criteria)}

        Current TODO list:
        {format_todos(todos)}

        Recent activity:
        {format_messages(recent_messages[-10:])}

        Evaluate:
        1. Is the goal achieved? (yes/no)
        2. Which success criteria are met?
        3. What percentage of work is done? (0-100%)
        4. What are the next critical steps?
        5. Are there any blockers or signs of stagnation?

        Respond in JSON format.
        """

        response = await self.llm.ainvoke(evaluation_prompt)
        return json.loads(response)
```

---

## 🔄 Интеграция с существующими компонентами

### Agent → StatefulAgent

**Текущий Agent**:
```python
class Agent:
    def __init__(self, name, instruction, model_provider, model_name):
        # Stateless, каждый run() независим
        pass

    async def run(self, task):
        # Один запуск, нет истории
        pass
```

**Новый StatefulAgent**:
```python
class StatefulAgent:
    def __init__(
        self,
        name,
        instruction,
        model_provider,
        model_name,
        middlewares: list[Middleware] = None,
        state_backend: StateBackend = None
    ):
        self.state = state_backend or InMemoryStateBackend()
        self.middlewares = middlewares or self._default_middlewares()
        # ... existing setup

    def _default_middlewares(self):
        return [
            TodoListMiddleware(),
            FilesystemMiddleware(eviction_threshold=80_000),
            SummarizationMiddleware(max_tokens=170_000, keep_last=6),
            SubAgentMiddleware(agent_factory=self._create_subagent),
            ProgressTrackingMiddleware(stagnation_threshold=2)
        ]

    async def run_stream(self, task, goal=None, success_criteria=None):
        # Инициализация state если первый запуск
        if not self.state.get('initialized'):
            self.state['messages'] = []
            self.state['todos'] = []
            self.state['files'] = {}
            self.state['initialized'] = True

        # Добавляем задачу в messages
        self.state['messages'].append({
            "role": "user",
            "content": task
        })

        # Основной цикл с middleware
        async for chunk in self._agent_loop_with_middleware():
            yield chunk

    async def _agent_loop_with_middleware(self):
        """ReAct цикл с применением всех middleware."""
        iteration = 0
        done = False

        while not done and iteration < self.max_iterations:
            iteration += 1

            # BEFORE LLM CALL: apply pre-processing middleware
            for mw in self.middlewares:
                await mw.before_llm_call(self.state)

            # LLM CALL
            response = await self.model.ainvoke_stream(
                self._prepare_llm_request()
            )

            # Stream chunks
            async for chunk in response:
                # DURING STREAMING: apply streaming middleware
                for mw in self.middlewares:
                    chunk = await mw.on_stream_chunk(chunk, self.state)
                yield chunk

            # AFTER LLM CALL: apply post-processing middleware
            for mw in self.middlewares:
                await mw.after_llm_call(self.state, response)

            # TOOL EXECUTION
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    # BEFORE TOOL: apply middleware
                    for mw in self.middlewares:
                        tool_call = await mw.before_tool_call(
                            tool_call, self.state
                        )

                    # Execute tool
                    result = await self._execute_tool(tool_call)

                    # AFTER TOOL: apply middleware
                    for mw in self.middlewares:
                        result = await mw.after_tool_call(
                            tool_call, result, self.state
                        )

                    yield f"[Tool {tool_call.name}: {result}]"

            # Check completion
            done = self._check_completion()
```

### TaskService → интеграция с TodoListMiddleware

**Текущая проблема**: `TaskService` изолирован, не используется `Agent`

**Решение**: TodoList использует `TaskService` под капотом

```python
class TodoListMiddleware:
    def __init__(self):
        self.task_service = InMemoryTaskService()

    async def before_tool_call(self, tool_call, state):
        if tool_call.name == "write_todos":
            # Парсим todos из аргументов
            todos = tool_call.arguments['todos']

            # Синхронизируем с TaskService
            for todo in todos:
                if todo.get('id'):
                    # Update existing
                    self.task_service.set_status(
                        UUID(todo['id']),
                        TaskStatus(todo['status'])
                    )
                else:
                    # Create new
                    task = self.task_service.create(
                        title=todo['content'],
                        metadata={
                            'activeForm': todo['activeForm'],
                            'created_by': 'agent'
                        }
                    )
                    todo['id'] = str(task.id)

            # Обновляем state
            state['todos'] = todos

        return tool_call
```

**Преимущества**:
- ✅ Полная функциональность `TaskService` (иерархия, поиск, метаданные)
- ✅ Простой интерфейс для агента (just `write_todos`)
- ✅ Можно экспортировать план как граф зависимостей

### FileToolset → FilesystemMiddleware

**Текущий FileToolset**: работает с реальной FS

**Новый подход**: виртуальная FS в state + опциональная привязка к реальной FS

```python
class FilesystemMiddleware:
    def __init__(
        self,
        eviction_threshold: int = 80_000,
        real_fs_mount: str | None = None,
        readonly: bool = True
    ):
        self.eviction_threshold = eviction_threshold
        self.real_fs_mount = real_fs_mount
        self.readonly = readonly

    async def after_tool_call(self, tool_call, result, state):
        # Context eviction для больших результатов
        if isinstance(result, str) and len(result) > self.eviction_threshold:
            file_path = f"/large_tool_results/{tool_call.id}"
            state['files'][file_path] = result

            return {
                "evicted": True,
                "original_size": len(result),
                "file_path": file_path,
                "message": f"Result saved to {file_path}. Use read_file()."
            }

        # Обработка file operations
        if tool_call.name in ['read_file', 'write_file', 'list_files']:
            return self._handle_file_operation(tool_call, result, state)

        return result

    def _handle_file_operation(self, tool_call, result, state):
        """Route между виртуальной и реальной FS."""
        path = tool_call.arguments.get('file_name') or tool_call.arguments.get('path')

        # Виртуальная FS (приоритет)
        if path.startswith('/workspace/') or path.startswith('/large_tool_results/'):
            if tool_call.name == 'read_file':
                return state['files'].get(path, "File not found")
            elif tool_call.name == 'write_file':
                state['files'][path] = tool_call.arguments['content']
                return {"success": True, "path": path}

        # Реальная FS (если разрешено)
        elif self.real_fs_mount:
            full_path = os.path.join(self.real_fs_mount, path)
            # ... безопасная работа с реальной FS

        return result
```

**Миграция FileToolset**:
```python
# Старый код (остается для обратной совместимости)
file_tool = FileToolset(base_dir="/path")
agent.add_tool(file_tool)

# Новый код (рекомендуется)
agent = StatefulAgent(
    ...,
    middlewares=[
        FilesystemMiddleware(
            real_fs_mount="/path",  # optional
            readonly=True  # безопасность
        )
    ]
)
```

---

## 📐 Этапы реализации

### Этап 1: Middleware Infrastructure (1-2 недели)

**Задачи**:
- [ ] Создать базовый `Middleware` Protocol
- [ ] Реализовать `MiddlewareStack` для композиции
- [ ] Создать `StateBackend` Protocol (In-Memory, Persistent)
- [ ] Рефакторинг `Agent` → `StatefulAgent` с поддержкой middleware
- [ ] Написать тесты для middleware pipeline

**Файлы**:
```
agentarea_agents_sdk/
├── middleware/
│   ├── __init__.py
│   ├── base.py           # Middleware Protocol, MiddlewareStack
│   ├── state.py          # StateBackend Protocol, InMemoryState
│   └── utils.py          # Helpers
└── agents/
    └── stateful_agent.py # New StatefulAgent class
```

### Этап 2: TodoListMiddleware (1 неделя)

**Задачи**:
- [ ] Реализовать `TodoListMiddleware`
- [ ] Интегрировать с существующим `TaskService`
- [ ] Создать `write_todos` tool
- [ ] Обновить prompts с TODO инструкциями
- [ ] Streaming updates для todos
- [ ] Тесты + примеры

**Файлы**:
```
agentarea_agents_sdk/
├── middleware/
│   └── todolist.py       # TodoListMiddleware
├── tools/
│   └── write_todos_tool.py  # Tool для управления планом
└── prompts.py            # Обновленные промпты
```

### Этап 3: FilesystemMiddleware (1 неделя)

**Задачи**:
- [ ] Виртуальная FS в state
- [ ] Context eviction для больших результатов
- [ ] Интеграция с FileToolset
- [ ] read_file/write_file/list_files через middleware
- [ ] Опциональная привязка к реальной FS
- [ ] Тесты + примеры

**Файлы**:
```
agentarea_agents_sdk/
├── middleware/
│   └── filesystem.py     # FilesystemMiddleware
└── tools/
    └── file_toolset.py   # Обновленный FileToolset
```

### Этап 4: SummarizationMiddleware (1-2 недели)

**Задачи**:
- [ ] Token counter (tiktoken или LiteLLM API)
- [ ] Триггер на превышение лимита
- [ ] LLM-based summarization
- [ ] Сохранение последних N сообщений
- [ ] Конфигурация (threshold, keep_last, style)
- [ ] Тесты с реальными LLM

**Файлы**:
```
agentarea_agents_sdk/
├── middleware/
│   └── summarization.py  # SummarizationMiddleware
└── utils/
    └── token_counter.py  # Token counting utilities
```

### Этап 5: SubAgentMiddleware (2 недели)

**Задачи**:
- [ ] `task()` tool для создания суб-агентов
- [ ] Изоляция контекста (новый state)
- [ ] Agent factory pattern
- [ ] Возврат только результата (не промежуточный контекст)
- [ ] Лимиты для безопасности (max iterations, timeout)
- [ ] Nested subagents (рекурсия с ограничением)
- [ ] Тесты + сложные примеры

**Файлы**:
```
agentarea_agents_sdk/
├── middleware/
│   └── subagent.py       # SubAgentMiddleware
└── tools/
    └── task_tool.py      # Tool для создания суб-агентов
```

### Этап 6: ProgressTrackingMiddleware (1 неделя)

**Задачи**:
- [ ] Метрики прогресса
- [ ] Детекция застоя
- [ ] System message injection при застое
- [ ] LLM-based progress evaluation
- [ ] Обновление `GoalProgressEvaluator`
- [ ] Тесты + edge cases

**Файлы**:
```
agentarea_agents_sdk/
├── middleware/
│   └── progress.py       # ProgressTrackingMiddleware
└── goal/
    └── goal_progress_evaluator.py  # Enhanced version
```

### Этап 7: Интеграция и полировка (1-2 недели)

**Задачи**:
- [ ] End-to-end тесты всех middleware вместе
- [ ] Примеры использования (simple → advanced)
- [ ] Benchmarks (сравнение с/без middleware)
- [ ] Документация (README, guides, API reference)
- [ ] Миграционный гид (старый Agent → StatefulAgent)
- [ ] Performance profiling и оптимизация

---

## 📊 Сравнение: до и после

### Пример задачи: "Analyze this codebase and generate architecture documentation"

#### ❌ Сейчас (без интеграции)

```
Agent receives task
  ↓
ReAct loop (max 10 iterations):
  1. LLM: "I'll search for files"
  2. Tool: list_files() → 1000 files (50k chars)
  3. LLM: "I'll read main files"
  4. Tool: read_file(app.py) → 30k chars
  5. Tool: read_file(models.py) → 40k chars
  6. Context: 120k chars (переполнение!)
  7. LLM: confused, context trimmed, loses info
  8. Iteration limit reached → incomplete result

Problems:
- Context overflow
- No planning
- All in main agent
- Lost context
- Poor result quality
```

#### ✅ После интеграции

```
StatefulAgent receives task
  ↓
TodoListMiddleware: Инжектирует write_todos tool
  ↓
ReAct loop (max 100 iterations):

  Iteration 1-2: Planning
  1. LLM: write_todos([
       {content: "Scan codebase structure", status: "pending"},
       {content: "Identify main components", status: "pending"},
       {content: "Document architecture", status: "pending"}
     ])
     → TodoList updated, streamed to UI

  Iteration 3-10: Scanning (with eviction)
  2. LLM: Updates todo #1 to "in_progress"
  3. Tool: list_files() → 1000 files (50k chars)
     → FilesystemMiddleware: Evicted to /large_tool_results/call_1
     → Context: "File list saved to /large_tool_results/call_1 (500 chars)"
  4. LLM: read_file(/large_tool_results/call_1, limit=100)
     → Gets manageable chunk
  5. LLM: Updates todo #1 to "completed"

  Iteration 11-20: Component identification (with subagent)
  6. LLM: Updates todo #2 to "in_progress"
  7. LLM: task(
       description="Analyze authentication module",
       prompt="Read auth/*.py files and identify patterns"
     )
     → SubAgentMiddleware: Creates isolated subagent
     → Subagent runs 30 iterations (reads 10 files, 80k chars context)
     → Returns: "Summary: JWT-based auth with Redis sessions" (500 chars)
     → Main agent context: still only 120k chars!
  8. LLM: task("Analyze database module")
     → Another subagent, 40k chars context, returns 500 char summary
  9. LLM: Updates todo #2 to "completed"

  Iteration 21-30: Documentation (with summarization)
  10. LLM: Updates todo #3 to "in_progress"
  11. Context: 180k tokens
      → SummarizationMiddleware: Triggers!
      → Old messages summarized: 180k → 70k tokens
  12. LLM: write_file(/workspace/ARCHITECTURE.md, content="...")
      → FilesystemMiddleware: Saved to virtual FS
  13. LLM: Updates todo #3 to "completed"
  14. LLM: completion(result="Documentation generated")

  Done!

Benefits:
✅ Context managed automatically (eviction + summarization)
✅ Clear plan visible in real-time
✅ Heavy work delegated to subagents
✅ All intermediate results preserved in virtual FS
✅ Complete, high-quality result
✅ Can handle 100+ iterations / hours of work
```

### Метрики

| Метрика | Сейчас | После |
|---------|--------|-------|
| Max context size | 120k chars (переполнение) | 180k → 70k (управляемо) |
| Max task duration | 30 минут | 2-24 часа |
| Max iterations | 10 | 100+ |
| Planning | Неявное | Явное, видимое |
| Subagents | Нет | Динамические |
| Context isolation | Нет | Полная |
| Progress tracking | Нет | Реальное время |
| File operations | Реальная FS | Виртуальная + безопасность |

---

## 🎨 Примеры использования

### Простой случай: Quick task (без middleware)

```python
# Обратная совместимость - старый Agent работает
from agentarea_agents_sdk import Agent

agent = Agent(
    name="SimpleAgent",
    instruction="You are a helpful coding assistant",
    model_provider="ollama_chat",
    model_name="qwen2.5"
)

result = await agent.run("What is 2+2?")
print(result)  # "2+2 equals 4"
```

### Средний случай: Planning + tracking

```python
from agentarea_agents_sdk import StatefulAgent
from agentarea_agents_sdk.middleware import TodoListMiddleware

agent = StatefulAgent(
    name="PlanningAgent",
    instruction="You are a systematic problem solver",
    model_provider="ollama_chat",
    model_name="qwen2.5",
    middlewares=[TodoListMiddleware()]
)

# Streaming with live TODO updates
async for chunk in agent.run_stream(
    task="Refactor the authentication module for better security",
    success_criteria=[
        "All passwords hashed with bcrypt",
        "JWT tokens with expiration",
        "Rate limiting on login endpoint"
    ]
):
    if chunk.type == "content":
        print(chunk.data, end="")
    elif chunk.type == "todos":
        render_todos(chunk.data)  # Live TODO list update
```

### Сложный случай: Full middleware stack

```python
from agentarea_agents_sdk import StatefulAgent
from agentarea_agents_sdk.middleware import (
    TodoListMiddleware,
    FilesystemMiddleware,
    SummarizationMiddleware,
    SubAgentMiddleware,
    ProgressTrackingMiddleware
)

agent = StatefulAgent(
    name="AdvancedAgent",
    instruction="You are an expert software architect and developer",
    model_provider="openai",
    model_name="gpt-4",
    max_iterations=100,
    middlewares=[
        TodoListMiddleware(),
        FilesystemMiddleware(
            eviction_threshold=80_000,
            real_fs_mount="./workspace",
            readonly=False
        ),
        SummarizationMiddleware(
            max_tokens=170_000,
            keep_last=6,
            summary_style="technical"
        ),
        SubAgentMiddleware(
            max_depth=2,  # nested subagents
            max_iterations_per_subagent=50
        ),
        ProgressTrackingMiddleware(
            stagnation_threshold=2,
            evaluation_interval=5  # evaluate every 5 iterations
        )
    ]
)

# Complex multi-hour task
result = await agent.run(
    task="""
    Analyze the entire codebase (5000+ files) and:
    1. Generate comprehensive architecture documentation
    2. Identify security vulnerabilities
    3. Suggest refactoring opportunities
    4. Create migration plan to microservices
    """,
    success_criteria=[
        "Architecture diagram generated",
        "Security audit report with severity levels",
        "Top 10 refactoring priorities identified",
        "Microservices migration roadmap with timeline"
    ]
)

print(result)
```

### Кастомный middleware

```python
from agentarea_agents_sdk.middleware import Middleware

class CostTrackingMiddleware(Middleware):
    """Track LLM API costs in real-time."""

    def __init__(self):
        self.total_cost = 0.0
        self.calls = 0

    async def after_llm_call(self, state, response):
        if response.cost:
            self.total_cost += response.cost
            self.calls += 1

            # Inject cost info into state
            state['cost_tracking'] = {
                'total': self.total_cost,
                'calls': self.calls,
                'average': self.total_cost / self.calls
            }

            # Warn if expensive
            if self.total_cost > 10.0:
                state['messages'].append({
                    "role": "system",
                    "content": f"⚠️ Cost alert: ${self.total_cost:.2f} spent"
                })

# Use it
agent = StatefulAgent(
    ...,
    middlewares=[
        TodoListMiddleware(),
        CostTrackingMiddleware(),  # Your custom middleware!
        SummarizationMiddleware()
    ]
)
```

---

## 🔬 Технические детали

### State Management

**State structure**:
```python
AgentState = {
    # Core
    'messages': list[dict],           # LLM conversation history
    'todos': list[TodoItem],          # Current plan
    'files': dict[str, str],          # Virtual filesystem

    # Metadata
    'iteration': int,                 # Current iteration number
    'created_at': str,                # ISO timestamp
    'updated_at': str,                # ISO timestamp

    # Subagents
    'subagent_results': dict[str, Any],  # Results from subagents
    'subagent_depth': int,            # Current nesting level

    # Progress
    'progress': {
        'completed_todos': int,
        'percentage': float,
        'last_completion': str
    },

    # Context management
    'summarization_count': int,       # Times context was summarized
    'eviction_count': int,            # Times results were evicted

    # Custom (extensible)
    'user_data': dict[str, Any]       # For custom middleware
}
```

**StateBackend Protocol**:
```python
class StateBackend(Protocol):
    """Protocol for state persistence."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from state."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Set value in state."""
        ...

    def update(self, updates: dict[str, Any]) -> None:
        """Update multiple values."""
        ...

    def snapshot(self) -> dict:
        """Get full state snapshot."""
        ...

    def restore(self, snapshot: dict) -> None:
        """Restore from snapshot."""
        ...
```

**Implementations**:
```python
# In-memory (default)
InMemoryStateBackend()

# Persistent (future)
SQLiteStateBackend(db_path="./agent_state.db")
RedisStateBackend(redis_url="redis://localhost")
FileStateBackend(state_dir="./states/")
```

### Middleware Protocol

```python
class Middleware(Protocol):
    """Protocol for middleware components."""

    async def before_llm_call(self, state: AgentState) -> None:
        """Called before each LLM call.

        Can modify state['messages'], inject system prompts, etc.
        """
        pass

    async def after_llm_call(
        self,
        state: AgentState,
        response: LLMResponse
    ) -> None:
        """Called after LLM responds.

        Can process response, update state, trigger side effects.
        """
        pass

    async def on_stream_chunk(
        self,
        chunk: LLMChunk,
        state: AgentState
    ) -> LLMChunk:
        """Called for each streaming chunk.

        Can modify chunk before yielding to user.
        """
        return chunk

    async def before_tool_call(
        self,
        tool_call: ToolCall,
        state: AgentState
    ) -> ToolCall:
        """Called before tool execution.

        Can intercept, modify, or replace tool calls.
        """
        return tool_call

    async def after_tool_call(
        self,
        tool_call: ToolCall,
        result: Any,
        state: AgentState
    ) -> Any:
        """Called after tool execution.

        Can process result, trigger eviction, etc.
        """
        return result
```

### Streaming Protocol

**Current** (simple string stream):
```python
async for content in agent.run_stream(task):
    print(content, end="")  # Just text
```

**New** (structured stream):
```python
async for chunk in agent.run_stream(task):
    match chunk.type:
        case "content":
            # LLM response text
            print(chunk.data, end="")

        case "todos":
            # TODO list update
            render_todos(chunk.data)

        case "tool_call":
            # Tool being called
            print(f"\n[Calling {chunk.data['name']}...]")

        case "tool_result":
            # Tool result
            print(f"[Result: {chunk.data['result']}]")

        case "progress":
            # Progress update
            update_progress_bar(chunk.data['percentage'])

        case "cost":
            # Cost update
            print(f"[Cost: ${chunk.data['total']:.4f}]")

        case "subagent_start":
            # Subagent created
            print(f"\n[Delegating to subagent: {chunk.data['task']}]")

        case "subagent_end":
            # Subagent finished
            print(f"[Subagent completed: {chunk.data['result'][:100]}...]")
```

---

## 🚀 Преимущества концепции

### Для пользователей SDK

1. **Решение сложных задач** - от 30 минут до 24+ часов
2. **Прозрачность** - видят план и прогресс в реальном времени
3. **Гибкость** - могут выбирать middleware по потребностям
4. **Безопасность** - виртуальная FS, изоляция суб-агентов
5. **Обратная совместимость** - старый `Agent` продолжает работать

### Для разработчиков SDK

1. **Модульность** - каждый компонент независим
2. **Расширяемость** - легко добавлять новые middleware
3. **Тестируемость** - каждый middleware тестируется отдельно
4. **Композируемость** - middleware можно комбинировать
5. **Производительность** - middleware применяются только при необходимости

### Для AgentArea

1. **Конкурентное преимущество** - функции уровня Claude Code
2. **Нулевые зависимости** - остается standalone SDK
3. **Исследовательская база** - можно экспериментировать с новыми middleware
4. **Community contributions** - простая модель для контрибьюторов
5. **Масштабируемость** - готовность к enterprise use cases

---

## 📚 Следующие шаги

### Немедленно (эта неделя)

1. ✅ **Создать этот документ** - получить feedback
2. **Обсудить архитектуру** - с командой / ментором
3. **Финализировать API** - для Middleware Protocol
4. **Создать PR #1** - Middleware infrastructure

### Короткий срок (2-4 недели)

1. Реализовать TodoListMiddleware
2. Реализовать FilesystemMiddleware
3. Обновить примеры и документацию
4. Написать integration tests

### Средний срок (1-2 месяца)

1. Реализовать SummarizationMiddleware
2. Реализовать SubAgentMiddleware
3. Реализовать ProgressTrackingMiddleware
4. Benchmarks и оптимизация

### Долгий срок (семестр)

1. Production-ready release
2. Advanced middleware (caching, monitoring, etc.)
3. Persistent state backends (SQLite, Redis)
4. Enterprise features (cost limits, audit logs)
5. Публикация в PyPI

---

## 💡 Открытые вопросы

1. **State Backend**: Начинать с in-memory или сразу persistent?
   - *Предложение*: In-memory для MVP, persistent потом

2. **Streaming Protocol**: Обратная совместимость или breaking change?
   - *Предложение*: Новый `run_stream_structured()`, старый остается

3. **Subagent Factory**: Как передавать конфигурацию?
   - *Предложение*: Наследовать от родителя, можно переопределить

4. **Cost Limits**: Нужен ли budget control?
   - *Предложение*: Опциональный CostLimitMiddleware

5. **Nested Subagents**: Какая максимальная глубина?
   - *Предложение*: 2 уровня (subagent of subagent)

6. **Real FS Access**: Всегда виртуальная или опциональная реальная?
   - *Предложение*: По умолчанию виртуальная, opt-in реальная

---

## 📖 Ссылки и ресурсы

### Исследовательские материалы
- [Deep Agents Architecture](/Материалы/Deep Agents - Архитектура планирования.md)
- [Planning Solutions Overview](/Материалы/Обзор решений для планирования задач в AI-агентах.md)
- [Semester Work Plan](/Материалы/План работы на семестр.md)

### Внешние проекты
- [LangChain Deep Agents](https://github.com/langchain-ai/deepagents) - middleware архитектура
- [AutoGen Magentic-One](https://github.com/microsoft/autogen) - multi-agent orchestration
- [CAMEL](https://github.com/camel-ai/camel) - task planning
- [Awesome LLM Planning](https://github.com/Quester-one/Awesome-LLM-Planning) - 300+ статей

### Anthropic Claude Code
- [Blog Post](https://blog.langchain.com/deep-agents/) - inspiration for architecture
- Deep Agents пытается воспроизвести паттерны Claude Code в open-source

---

**Автор**: Claude (Anthropic) + Human Collaborator
**Дата**: 2025-01-15
**Версия**: 1.0 (Initial Concept)
**Статус**: 📝 Draft для обсуждения
