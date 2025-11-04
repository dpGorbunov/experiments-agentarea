https://github.com/langchain-ai/deepagents

## 1. Где он хранит таски

**Место хранения:** `state['todos']` в графе LangGraph

**State** - словарь с данными агента, живет всю сессию:

```python
state = {
    'messages': [...],
    'todos': [{'content': '...', 'status': 'pending'}, ...],
    'files': {...}
}
```

**Обновление:** через `Command(update={'todos': [...]})`

**Стриминг:** через канал `updates` (параллельно с `messages`)

## 2. В какой момент он понимает, что нужно менять статус задачи?

**Кто решает:** LLM самостоятельно

**Инструкции в промпте:**

- Mark as in_progress BEFORE beginning work
- Mark as completed IMMEDIATELY after finishing

**Автоматики нет** - только явный вызов инструмента

## 3. В какой момент нужно корректировать план?

**Когда:** в любой момент, LLM принимает решение

**Промпты:**

- `WRITE_TODOS_SYSTEM_PROMPT`: Don't be afraid to revise the To-Do list as you go
- You can update future tasks, delete if no longer necessary, add new tasks
- Don't change previously completed tasks

**Механизм:** один инструмент `write_todos` для создания И корректировки

**При первом создании:** запрашивается одобрение пользователя

## 4. Кто и когда меняет статус задачи?

**Цепочка вызовов:**

```
LLM генерирует tool_call → write_todos(todos=[...])
    ↓
todo.py:179-191 → функция write_todos()
    ↓
Возвращает Command(update={'todos': [...]})
    ↓
LangGraph обновляет state['todos']
    ↓
State стримится через канал updates
    ↓
execution.py:372 → детектит 'todos' in chunk_data
    ↓
execution.py:374 → сравнивает new_todos != current_todos
    ↓
ui.py:228-257 → render_todo_list()
    ↓
Терминал: ☐ pending / ⏳ in_progress / ☑ completed
```

**Статусы:**

- `pending` - серый, не начата
- `in_progress` - желтый, выполняется
- `completed` - зеленый, завершена

## 5. Что с контекстом, который возникает при выполнении плана

**Проблема:** Агент выполняет план → вызывает инструменты → результаты накапливаются в messages → контекст переполняется

### Context Eviction (автоматически)

**Лимит:** `filesystem.py:523`

```python
tool_token_limit_before_evict = 20000  # токенов
```

**Если результат > 80k символов:**

```
grep_search(...) → возвращает 150k символов
    ↓
FilesystemMiddleware перехватывает (filesystem.py:617)
    ↓
_intercept_large_tool_result()
    ↓
_process_large_message() (filesystem.py:593)
    ↓
state['files']['/large_tool_results/call_id'] = полный результат
messages = Result saved to /large_tool_results/call_id. Use read_file with offset/limit.
```

**Экономия:** 150k → 500 символов в контексте

### Summarization (автоматически)

**Конфигурация:** `graph.py:108-111`

```python
SummarizationMiddleware(
    max_tokens_before_summary=170000,
    messages_to_keep=6  # последние 6 в полном виде
)
```

**Работа:** Контекст > 170k токенов → старые messages суммируются → контекст сжимается

### Subagents (LLM решает)

**Делегирование:**

```python
task(description='Research LeBron', prompt='...')
```

**Изоляция:** `subagents.py:218-268`

- Создает НОВЫЙ агент с чистым контекстом
- Исключает messages и todos главного агента
- Субагент работает изолированно (может потратить 50k токенов)
- Возвращает только синтез (500 токенов)
- Весь промежуточный контекст уничтожается

**Экономия:** 50k токенов субагента → 500 токенов в главном

### Сценарии работы

**Без субагентов (CLI):**

- Агент делает все сам
- Eviction + Summarization управляют контекстом

**С субагентами (research example):**

- Главный агент планирует
- Субагенты делают тяжелую работу изолированно
- Главный получает только результаты

**Выбор подхода:** LLM сам выбирает когда использовать субагентов