
## Контекст

Цель: понять механизмы планирования и декомпозиции задач в современных AI-агентах для интеграции в AgentArea (https://github.com/agentarea/agentarea).

Наблюдение: ряд решений использует схожий паттерн из четырех элементов - инструмент планирования, файловую систему для промежуточных результатов, механизм создания под-агентов и детальный системный промпт. Этот подход связывают с архитектурой Claude Code от Anthropic.

Claude Code показал, что простого вызова инструментов в цикле недостаточно для задач дольше 30 минут. Требуется явное планирование, сохранение промежуточных результатов, делегирование под-агентам и изоляция контекста.

## CAMEL (2023, 14.6k stars)

https://github.com/camel-ai/camel

LLM генерирует план через промпт, результат парсится через XML. План статичный, создается один раз. Нет под-агентов, файловой системы, изоляции контекста. Максимум 15 tool calls, до 30 минут на задачу.

Ключевые файлы: `camel/tasks/task.py`, `camel/tasks/task_prompt.py`

## AutoGen Magentic-One (2023, 51k stars)

https://github.com/microsoft/autogen https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/

Декомпозиция через диалог агентов. Двухуровневая система: Task Ledger (outer loop) содержит факты и общий план, Progress Ledger (inner loop) отслеживает текущий прогресс.

Фиксированная команда: Orchestrator, WebSurfer (браузер Chromium), FileSurfer (локальные файлы), Coder (код), ComputerTerminal (выполнение программ).

План адаптируется при застое (2+ итерации без прогресса). Изоляция через роли агентов. 20-50 tool calls, 30-120 минут на задачу.

Ключевые файлы: `autogen/agentchat/groupchat.py`, `examples/agentchat/`

## LangChain Deep Agents (2025, 4.5k stars)

https://github.com/langchain-ai/deepagents https://blog.langchain.com/deep-agents/

Модульная middleware-архитектура: TodoListMiddleware, FilesystemMiddleware (виртуальная FS в LangGraph state), SubAgentMiddleware (динамическое создание), SummarizationMiddleware, AnthropicPromptCachingMiddleware.

`write_todos` - no-op инструмент для контекстной инженерии. TODO список в состоянии со статусами (pending/in_progress/completed). Агент может вызывать инструменты, создавать под-агентов через `task` tool, сохранять результаты в виртуальную FS.

Под-агенты с изолированным контекстом и своей копией middleware. Возвращают только итоговый результат, промежуточный контекст уничтожается.

План обновляется постоянно. 50-200+ tool calls, 2-24 часа на задачу.

Ключевые файлы: `src/deepagents/middleware.py`, `src/deepagents/graph.py`

## Различия

**Планирование:** CAMEL - статичный, Magentic-One - адаптация при застое, Deep Agents - постоянное обновление.

**Агенты:** CAMEL - нет, Magentic-One - 4 фиксированных роли, Deep Agents - динамическое создание.

**Контекст:** CAMEL - общий, Magentic-One - через роли, Deep Agents - через под-агенты и виртуальную FS.

**Архитектура:** CAMEL - промпт + парсинг, Magentic-One - Task/Progress Ledger, Deep Agents - middleware stack.

## Материалы

300+ статей о планировании в LLM: https://github.com/Quester-one/Awesome-LLM-Planning

Другие проекты: relevance.ai, microsoft agent framework