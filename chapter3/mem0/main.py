"""Main entry point for the Mem0 agent with Kimi K3."""

import asyncio
import argparse
from pathlib import Path
from typing import Optional
import sys

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown

from agent import Mem0Agent
from config import Config


console = Console()


class InteractiveSession:
    """Interactive session manager for Mem0 agent."""
    
    def __init__(self, agent: Mem0Agent):
        self.agent = agent
        self.current_session = None
        self.current_user = None
        self.current_agent_id = None
        
    def start_session(self) -> None:
        """Start a new interactive session."""
        console.print(Panel.fit(
            "[bold cyan]Mem0 Agent Interactive Session[/bold cyan]\n"
            "Type 'help' for commands, 'exit' to quit",
            title="Welcome"
        ))
        
        # Get session details
        self.current_user = Prompt.ask("Enter user ID", default="user_001")
        self.current_agent_id = Prompt.ask("Enter agent ID", default="agent_001")
        session_id = Prompt.ask("Enter session ID", default="session_001")
        
        # Create context
        context = self.agent.create_context(
            agent_id=self.current_agent_id,
            user_id=self.current_user,
            session_id=session_id
        )
        self.current_session = session_id
        
        console.print(f"[green]Session started:[/green] {session_id}")
        console.print(f"[green]User:[/green] {self.current_user}")
        console.print(f"[green]Agent:[/green] {self.current_agent_id}")
        
    def show_help(self) -> None:
        """Display help information."""
        help_text = """
# Available Commands

- **help** - Show this help message
- **exit/quit** - Exit the session
- **clear** - Clear the screen
- **metrics** - Show performance metrics
- **memories** - Show stored memories
- **save** - Save conversation state
- **load** - Load conversation state
- **reset** - Reset the agent state
- **new** - Start a new session
        """
        console.print(Markdown(help_text))
    
    def show_memories(self) -> None:
        """Display stored memories."""
        if not self.current_user:
            console.print("[yellow]No active session[/yellow]")
            return
        
        memories = self.agent.memory.get_all(user_id=self.current_user)
        
        if not memories:
            console.print("[yellow]No memories found[/yellow]")
            return
        
        console.print(f"\n[cyan]Memories for {self.current_user}:[/cyan]")
        for i, memory in enumerate(memories, 1):
            console.print(f"{i}. {memory.get('memory', memory.get('text', 'N/A'))}")
    
    def save_state(self) -> None:
        """Save the current state."""
        filepath = Prompt.ask("Enter filepath to save", default="state.json")
        self.agent.save_state(filepath)
        console.print(f"[green]State saved to {filepath}[/green]")
    
    def load_state(self) -> None:
        """Load a saved state."""
        filepath = Prompt.ask("Enter filepath to load", default="state.json")
        if Path(filepath).exists():
            self.agent.load_state(filepath)
            console.print(f"[green]State loaded from {filepath}[/green]")
        else:
            console.print(f"[red]File not found: {filepath}[/red]")
    
    async def run(self) -> None:
        """Run the interactive session."""
        self.start_session()
        
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold]You[/bold]")
                
                # Check for commands
                if user_input.lower() in ["exit", "quit"]:
                    if Confirm.ask("Are you sure you want to exit?"):
                        break
                elif user_input.lower() == "help":
                    self.show_help()
                    continue
                elif user_input.lower() == "clear":
                    console.clear()
                    continue
                elif user_input.lower() == "metrics":
                    self.agent.display_metrics(self.current_session)
                    continue
                elif user_input.lower() == "memories":
                    self.show_memories()
                    continue
                elif user_input.lower() == "save":
                    self.save_state()
                    continue
                elif user_input.lower() == "load":
                    self.load_state()
                    continue
                elif user_input.lower() == "reset":
                    if Confirm.ask("Reset agent state?"):
                        self.agent.reset()
                        console.print("[green]Agent state reset[/green]")
                    continue
                elif user_input.lower() == "new":
                    self.start_session()
                    continue
                
                # Process the input through the agent
                console.print("[dim]Processing...[/dim]")
                response, metrics = await self.agent.process_turn_async(
                    self.current_session, 
                    user_input
                )
                
                # Display response
                console.print(f"\n[bold cyan]Agent[/bold cyan]: {response}")
                
                # Display metrics (optional)
                if metrics.get("generation_time"):
                    console.print(
                        f"[dim]Generated in {metrics['generation_time']:.2f}s | "
                        f"Turn {metrics['turn_count']} | "
                        f"Memories: {metrics['memory_count']}[/dim]"
                    )
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
                if Confirm.ask("Exit session?"):
                    break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        console.print("\n[cyan]Session ended. Goodbye![/cyan]")


async def run_batch_mode(agent: Mem0Agent, input_file: Path, output_file: Path) -> None:
    """Run the agent in batch mode."""
    console.print(f"[yellow]Processing batch file: {input_file}[/yellow]")
    
    # Read input file
    with open(input_file, "r") as f:
        batch_data = f.read()
    
    # Parse batch data (assuming JSON format)
    import json
    try:
        sessions = json.loads(batch_data)
    except json.JSONDecodeError:
        console.print("[red]Invalid JSON in input file[/red]")
        return
    
    results = []
    
    # Process each session
    for session_data in sessions:
        session_id = session_data.get("session_id", "batch_session")
        user_id = session_data.get("user_id", "batch_user")
        agent_id = session_data.get("agent_id", "batch_agent")
        turns = session_data.get("turns", [])
        
        # Create context
        context = agent.create_context(
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id
        )
        
        session_results = {
            "session_id": session_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "turns": []
        }
        
        # Process turns
        for turn in turns:
            response, metrics = await agent.process_turn_async(session_id, turn)
            session_results["turns"].append({
                "input": turn,
                "response": response,
                "metrics": metrics
            })
        
        results.append(session_results)
    
    # Save results
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    console.print(f"[green]Results saved to {output_file}[/green]")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Mem0 Agent with Kimi K3")
    parser.add_argument("--mode", choices=["interactive", "batch", "benchmark"], 
                       default="interactive", help="Execution mode")
    parser.add_argument("--input", type=str, help="Input file for batch mode")
    parser.add_argument("--output", type=str, help="Output file for batch mode")
    parser.add_argument("--config", type=str, help="Configuration file path")
    args = parser.parse_args()
    
    # Initialize configuration
    config = Config.from_env()
    
    # Initialize agent
    console.print("[yellow]Initializing Mem0 agent...[/yellow]")
    try:
        agent = Mem0Agent(config)
        console.print("[green]Agent initialized successfully[/green]")
    except Exception as e:
        console.print(f"[red]Failed to initialize agent: {e}[/red]")
        sys.exit(1)
    
    # Run based on mode
    if args.mode == "interactive":
        session = InteractiveSession(agent)
        await session.run()
    elif args.mode == "batch":
        if not args.input or not args.output:
            console.print("[red]Batch mode requires --input and --output arguments[/red]")
            sys.exit(1)
        await run_batch_mode(agent, Path(args.input), Path(args.output))
    elif args.mode == "benchmark":
        # Import and run benchmark
        from experiment import LOCOMOBenchmark
        benchmark = LOCOMOBenchmark(agent, config)
        results = await benchmark.run_benchmark(num_scenarios=3)
        benchmark.display_overall_results(results)


if __name__ == "__main__":
    asyncio.run(main())
