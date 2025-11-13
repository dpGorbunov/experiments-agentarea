"""
Прототип Middleware Infrastructure - минимальная рабочая версия
Можно запустить для демонстрации концепции
"""
import asyncio
from typing import Protocol, Any


# ============================================================================
# MIDDLEWARE PROTOCOL
# ============================================================================

class Middleware(Protocol):
    """Протокол для middleware компонентов."""

    async def before_llm_call(self, state: dict) -> None:
        """Вызывается перед каждым LLM запросом."""
        pass

    async def after_llm_call(self, state: dict, response: Any) -> None:
        """Вызывается после получения ответа от LLM."""
        pass

    async def before_tool_call(self, tool_call: dict, state: dict) -> dict:
        """Вызывается перед выполнением инструмента."""
        return tool_call

    async def after_tool_call(self, tool_call: dict, result: Any, state: dict) -> Any:
        """Вызывается после выполнения инструмента."""
        return result


class MiddlewareStack:
    """Управляет набором middleware."""

    def __init__(self, middlewares: list[Middleware]):
        self.middlewares = middlewares

    async def run_before_llm(self, state: dict):
        for mw in self.middlewares:
            await mw.before_llm_call(state)

    async def run_after_llm(self, state: dict, response: Any):
        for mw in self.middlewares:
            await mw.after_llm_call(state, response)

    async def run_before_tool(self, tool_call: dict, state: dict) -> dict:
        for mw in self.middlewares:
            tool_call = await mw.before_tool_call(tool_call, state)
        return tool_call

    async def run_after_tool(self, tool_call: dict, result: Any, state: dict) -> Any:
        for mw in self.middlewares:
            result = await mw.after_tool_call(tool_call, result, state)
        return result


# ============================================================================
# EXAMPLE MIDDLEWARES
# ============================================================================

class LoggingMiddleware:
    """Логирует все вызовы."""

    async def before_llm_call(self, state: dict):
        print(f"[LOG] LLM call, iteration: {state.get('iteration', 0)}")

    async def after_llm_call(self, state: dict, response: Any):
        print(f"[LOG] LLM responded: {response[:50] if isinstance(response, str) else response}...")

    async def before_tool_call(self, tool_call: dict, state: dict):
        print(f"[LOG] Tool call: {tool_call.get('name', 'unknown')}")
        return tool_call

    async def after_tool_call(self, tool_call: dict, result: Any, state: dict):
        print(f"[LOG] Tool result: {result}")
        return result


class ContextEvictionMiddleware:
    """Демо context eviction."""

    def __init__(self, threshold: int = 100):
        self.threshold = threshold

    async def before_llm_call(self, state: dict):
        if 'files' not in state:
            state['files'] = {}

    async def after_tool_call(self, tool_call: dict, result: Any, state: dict):
        if isinstance(result, str) and len(result) > self.threshold:
            # Evict!
            file_path = f"/large_results/{tool_call.get('id', 'unknown')}"
            state['files'][file_path] = result

            print(f"[EVICTION] Result too large ({len(result)} chars), saved to {file_path}")

            return {
                'evicted': True,
                'file_path': file_path,
                'original_size': len(result),
                'message': f"Result saved to {file_path}"
            }

        return result


class TodoTrackingMiddleware:
    """Демо TODO tracking."""

    async def before_tool_call(self, tool_call: dict, state: dict):
        if tool_call.get('name') == 'write_todos':
            todos = tool_call.get('arguments', {}).get('todos', [])
            state['todos'] = todos
            print(f"[TODO] Updated todos: {len(todos)} tasks")

        return tool_call

    async def after_llm_call(self, state: dict, response: Any):
        todos = state.get('todos', [])
        if todos:
            completed = len([t for t in todos if t.get('status') == 'completed'])
            total = len(todos)
            print(f"[TODO] Progress: {completed}/{total} completed")


# ============================================================================
# DEMO AGENT
# ============================================================================

class DemoAgent:
    """Упрощенный агент для демонстрации middleware."""

    def __init__(self, middlewares: list[Middleware] = None):
        self.state = {
            'messages': [],
            'iteration': 0,
            'files': {},
            'todos': []
        }
        self.middlewares = MiddlewareStack(middlewares or [])

    async def run(self, task: str, max_iterations: int = 5):
        """Симулирует agent loop."""
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        print(f"{'='*60}\n")

        self.state['messages'].append({'role': 'user', 'content': task})

        for i in range(max_iterations):
            self.state['iteration'] = i + 1
            print(f"\n--- Iteration {i + 1} ---\n")

            # Before LLM
            await self.middlewares.run_before_llm(self.state)

            # Simulate LLM call
            await asyncio.sleep(0.1)
            llm_response = self._simulate_llm_response(i)

            # After LLM
            await self.middlewares.run_after_llm(self.state, llm_response)

            self.state['messages'].append({'role': 'assistant', 'content': llm_response})

            # Simulate tool call
            if i == 0:
                # First iteration: create todos
                tool_call = {
                    'id': f'call_{i}',
                    'name': 'write_todos',
                    'arguments': {
                        'todos': [
                            {'content': 'Analyze problem', 'status': 'pending'},
                            {'content': 'Implement solution', 'status': 'pending'},
                            {'content': 'Test solution', 'status': 'pending'}
                        ]
                    }
                }
            elif i == 1:
                # Second iteration: large result
                tool_call = {
                    'id': f'call_{i}',
                    'name': 'grep_search',
                    'arguments': {'pattern': 'test'}
                }
            elif i == 2:
                # Third iteration: complete task
                tool_call = {
                    'id': f'call_{i}',
                    'name': 'write_todos',
                    'arguments': {
                        'todos': [
                            {'content': 'Analyze problem', 'status': 'completed'},
                            {'content': 'Implement solution', 'status': 'in_progress'},
                            {'content': 'Test solution', 'status': 'pending'}
                        ]
                    }
                }
            else:
                tool_call = None

            if tool_call:
                # Before tool
                tool_call = await self.middlewares.run_before_tool(tool_call, self.state)

                # Execute tool
                await asyncio.sleep(0.1)
                result = self._simulate_tool_execution(tool_call)

                # After tool
                result = await self.middlewares.run_after_tool(tool_call, result, self.state)

                self.state['messages'].append({
                    'role': 'tool',
                    'name': tool_call['name'],
                    'content': str(result)
                })

        print(f"\n{'='*60}")
        print("Final State:")
        print(f"  Messages: {len(self.state['messages'])}")
        print(f"  Files: {list(self.state['files'].keys())}")
        print(f"  Todos: {self.state.get('todos', [])}")
        print(f"{'='*60}\n")

    def _simulate_llm_response(self, iteration: int) -> str:
        responses = [
            "Let me create a plan for this task...",
            "Now I'll search for relevant information...",
            "I've analyzed the problem, implementing solution...",
            "Testing the implementation...",
            "Task completed successfully!"
        ]
        return responses[min(iteration, len(responses) - 1)]

    def _simulate_tool_execution(self, tool_call: dict) -> Any:
        if tool_call['name'] == 'write_todos':
            return {'success': True, 'todos_updated': True}
        elif tool_call['name'] == 'grep_search':
            # Return large result
            return "x" * 500  # Larger than threshold
        else:
            return "Tool executed"


# ============================================================================
# DEMO SCENARIOS
# ============================================================================

async def demo_basic():
    """Демо базового middleware stack."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Middleware Stack")
    print("="*60)

    agent = DemoAgent(middlewares=[
        LoggingMiddleware()
    ])

    await agent.run("Solve a simple problem")


async def demo_eviction():
    """Демо context eviction."""
    print("\n" + "="*60)
    print("DEMO 2: Context Eviction")
    print("="*60)

    agent = DemoAgent(middlewares=[
        LoggingMiddleware(),
        ContextEvictionMiddleware(threshold=100)
    ])

    await agent.run("Search and analyze data")


async def demo_todos():
    """Демо TODO tracking."""
    print("\n" + "="*60)
    print("DEMO 3: TODO Tracking")
    print("="*60)

    agent = DemoAgent(middlewares=[
        LoggingMiddleware(),
        TodoTrackingMiddleware()
    ])

    await agent.run("Complete multi-step task")


async def demo_full_stack():
    """Демо полного middleware stack."""
    print("\n" + "="*60)
    print("DEMO 4: Full Middleware Stack")
    print("="*60)

    agent = DemoAgent(middlewares=[
        LoggingMiddleware(),
        ContextEvictionMiddleware(threshold=100),
        TodoTrackingMiddleware()
    ])

    await agent.run("Complex task with planning and large results")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Запуск всех демо."""
    demos = [
        ("Basic Middleware", demo_basic),
        ("Context Eviction", demo_eviction),
        ("TODO Tracking", demo_todos),
        ("Full Stack", demo_full_stack)
    ]

    print("\n" + "="*60)
    print("MIDDLEWARE PROTOTYPE DEMO")
    print("="*60)
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Run all")

    choice = input("\nSelect demo (0-4): ").strip()

    if choice == "0":
        for _, demo_func in demos:
            await demo_func()
            input("\nPress Enter to continue to next demo...")
    elif choice in ["1", "2", "3", "4"]:
        _, demo_func = demos[int(choice) - 1]
        await demo_func()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
