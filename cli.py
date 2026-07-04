#!/usr/bin/env python
"""
PatentVerse AI — command-line interface.

Demonstrates the "Agent skills / Agents CLI" course concept: a simple,
scriptable way to run the multi-agent pipeline from the terminal, useful
for quick testing, demos, or batch processing invention descriptions.

Usage:
    python cli.py --invention "A smart water bottle that tracks hydration..."
    python cli.py --file inventions.txt      # one description per line
"""

import asyncio
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

load_dotenv()

from agents.pipeline_runner import RateLimitedError, ValidationError, run_patent_pipeline  # noqa: E402

console = Console()


async def _run_one(
    invention: str, user_id: str, date_from: str | None, date_to: str | None
) -> None:
    console.print(Panel(f"[bold]Invention:[/bold] {invention}", title="PatentVerse AI"))
    if date_from or date_to:
        console.print(f"[dim]Date range: {date_from or 'any'} → {date_to or 'any'}[/dim]")
    with console.status("[bold cyan]Running Search → Analysis → Report pipeline..."):
        try:
            report = await run_patent_pipeline(
                invention, user_id=user_id, date_from=date_from, date_to=date_to
            )
        except ValidationError as e:
            console.print(f"[bold red]Input error:[/bold red] {e}")
            return
        except RateLimitedError as e:
            console.print(f"[bold yellow]Rate limited:[/bold yellow] {e}")
            return
    console.print(Markdown(report))


@click.command()
@click.option("--invention", "-i", help="Plain-language invention description.")
@click.option("--file", "-f", "file_path", help="Path to a text file, one invention description per line.")
@click.option("--user-id", default="cli_user", help="Session/user id for rate limiting.")
@click.option("--from", "date_from", default=None, help="Earliest patent date to include, e.g. 2015 or 2015-01-01.")
@click.option("--to", "date_to", default=None, help="Latest patent date to include, e.g. 2024 or 2024-12-31.")
def main(
    invention: str | None,
    file_path: str | None,
    user_id: str,
    date_from: str | None,
    date_to: str | None,
) -> None:
    """Run PatentVerse AI's prior-art search & analysis pipeline."""
    if not invention and not file_path:
        console.print(
            "[bold red]Error:[/bold red] provide --invention \"...\" or --file path.txt"
        )
        sys.exit(1)

    descriptions = []
    if invention:
        descriptions.append(invention)
    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            descriptions.extend(line.strip() for line in f if line.strip())

    for desc in descriptions:
        asyncio.run(_run_one(desc, user_id, date_from, date_to))
        console.rule()


if __name__ == "__main__":
    main()
