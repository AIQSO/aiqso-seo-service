#!/usr/bin/env python3
"""
AIQSO SEO Audit CLI

Command-line tool for running SEO audits on websites.

Usage:
    aiqso-seo audit <url> [options]
    aiqso-seo audit-site <url> [options]
    aiqso-seo compare <url1> <url2>
"""

import asyncio
import json
import sys

import click

from ..core.auditor import AuditResult, SEOAuditor
from ..core.tiers import get_tier_manager


def format_score(score: int) -> str:
    """Format a score with color coding."""
    if score >= 80:
        return click.style(f"{score}", fg="green", bold=True)
    elif score >= 60:
        return click.style(f"{score}", fg="yellow", bold=True)
    else:
        return click.style(f"{score}", fg="red", bold=True)


def format_check_result(check) -> str:
    """Format a check result for CLI output."""
    if check.passed:
        status = click.style("PASS", fg="green")
    elif check.severity == "critical":
        status = click.style("FAIL", fg="red", bold=True)
    elif check.severity == "error":
        status = click.style("FAIL", fg="red")
    elif check.severity == "warning":
        status = click.style("WARN", fg="yellow")
    else:
        status = click.style("INFO", fg="blue")

    return f"  [{status}] {check.title}: {check.current_value or 'N/A'}"


def print_audit_result(result: AuditResult, verbose: bool = False):
    """Print an audit result to the console."""
    click.echo()
    click.echo(click.style("=" * 60, fg="blue"))
    click.echo(click.style(f"SEO Audit Results: {result.url}", bold=True))
    click.echo(click.style("=" * 60, fg="blue"))
    click.echo()

    # Overall score
    click.echo(f"Overall Score: {format_score(result.overall_score)}/100")
    click.echo()

    # Category scores
    click.echo("Category Scores:")
    click.echo(f"  Configuration: {format_score(result.configuration_score)}/100")
    click.echo(f"  Meta Tags:     {format_score(result.meta_score)}/100")
    click.echo(f"  Content:       {format_score(result.content_score)}/100")
    click.echo(f"  Performance:   {format_score(result.performance_score)}/100")
    click.echo()

    # Summary
    click.echo(f"Issues Found: {click.style(str(result.issues_found), fg='red' if result.issues_found else 'green')}")
    click.echo(
        f"Warnings:     {click.style(str(result.warnings_found), fg='yellow' if result.warnings_found else 'green')}"
    )
    click.echo(f"Duration:     {result.duration_seconds:.2f}s")
    click.echo()

    # Check results
    if verbose:
        click.echo(click.style("Detailed Results:", bold=True))
        click.echo()

        # Group by category
        categories = {
            "configuration": "Configuration",
            "meta": "Meta Tags",
            "content": "Content",
            "performance": "Performance",
        }

        for cat_key, cat_name in categories.items():
            cat_checks = [c for c in result.checks if c.category == cat_key]
            if cat_checks:
                click.echo(click.style(f"  {cat_name}:", bold=True))
                for check in cat_checks:
                    click.echo(format_check_result(check))
                    if not check.passed and check.recommendation:
                        click.echo(f"      -> {check.recommendation}")
                click.echo()

    # Failed checks summary
    failed = [c for c in result.checks if not c.passed]
    if failed and not verbose:
        click.echo(click.style("Failed Checks:", bold=True, fg="red"))
        for check in failed:
            click.echo(format_check_result(check))
            if check.recommendation:
                click.echo(f"      -> {check.recommendation}")
        click.echo()

    # AI Summary
    if result.ai_summary:
        click.echo(click.style("AI Insights:", bold=True, fg="cyan"))
        click.echo(result.ai_summary)
        click.echo()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """AIQSO SEO Audit Tool - Analyze websites for SEO issues."""
    pass


@cli.command()
@click.argument("url")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed results")
@click.option("--ai", is_flag=True, help="Include AI-powered insights")
@click.option("--lighthouse", is_flag=True, help="Include Lighthouse metrics")
@click.option("--save", "-s", type=click.Path(), help="Save results to file")
def audit(url: str, output: str, verbose: bool, ai: bool, lighthouse: bool, save: str | None):
    """Audit a single URL for SEO issues.

    Example:
        aiqso-seo audit https://example.com
        aiqso-seo audit https://example.com --ai --verbose
        aiqso-seo audit https://example.com -o json -s results.json
    """
    # Ensure URL has protocol
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    click.echo(f"Auditing {url}...")

    async def run_audit():
        async with SEOAuditor() as auditor:
            return await auditor.audit_url(
                url,
                include_lighthouse=lighthouse,
                include_ai=ai,
            )

    result = asyncio.run(run_audit())

    if output == "json":
        json_output = json.dumps(result.to_dict(), indent=2)
        if save:
            with open(save, "w") as f:
                f.write(json_output)
            click.echo(f"Results saved to {save}")
        else:
            click.echo(json_output)
    else:
        print_audit_result(result, verbose=verbose)
        if save:
            with open(save, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
            click.echo(f"Results saved to {save}")

    # Exit with error code if critical issues found
    if result.issues_found > 0:
        sys.exit(1)


@cli.command()
@click.argument("url1")
@click.argument("url2")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format")
def compare(url1: str, url2: str, output: str):
    """Compare SEO scores between two URLs.

    Example:
        aiqso-seo compare https://example.com https://competitor.com
    """
    # Ensure URLs have protocol
    if not url1.startswith(("http://", "https://")):
        url1 = f"https://{url1}"
    if not url2.startswith(("http://", "https://")):
        url2 = f"https://{url2}"

    click.echo(f"Comparing {url1} vs {url2}...")

    async def run_comparison():
        async with SEOAuditor() as auditor:
            result1 = await auditor.audit_url(url1)
            result2 = await auditor.audit_url(url2)
            return result1, result2

    result1, result2 = asyncio.run(run_comparison())

    if output == "json":
        comparison = {
            "url1": result1.to_dict(),
            "url2": result2.to_dict(),
            "comparison": {
                "overall_score_diff": result1.overall_score - result2.overall_score,
                "configuration_diff": result1.configuration_score - result2.configuration_score,
                "meta_diff": result1.meta_score - result2.meta_score,
                "content_diff": result1.content_score - result2.content_score,
                "performance_diff": result1.performance_score - result2.performance_score,
            },
        }
        click.echo(json.dumps(comparison, indent=2))
    else:
        click.echo()
        click.echo(click.style("=" * 70, fg="blue"))
        click.echo(click.style("SEO Comparison Results", bold=True))
        click.echo(click.style("=" * 70, fg="blue"))
        click.echo()

        # Header
        click.echo(f"{'Metric':<25} {'URL 1':>15} {'URL 2':>15} {'Diff':>10}")
        click.echo("-" * 70)

        # Scores
        def format_diff(diff: int) -> str:
            if diff > 0:
                return click.style(f"+{diff}", fg="green")
            elif diff < 0:
                return click.style(str(diff), fg="red")
            else:
                return click.style("0", fg="white")

        metrics = [
            ("Overall Score", result1.overall_score, result2.overall_score),
            ("Configuration", result1.configuration_score, result2.configuration_score),
            ("Meta Tags", result1.meta_score, result2.meta_score),
            ("Content", result1.content_score, result2.content_score),
            ("Performance", result1.performance_score, result2.performance_score),
        ]

        for name, score1, score2 in metrics:
            diff = score1 - score2
            click.echo(f"{name:<25} {format_score(score1):>15} {format_score(score2):>15} {format_diff(diff):>10}")

        click.echo()


@cli.command()
@click.argument("url")
@click.option("--max-pages", "-m", default=50, help="Maximum pages to crawl")
@click.option("--depth", "-d", default=3, help="Maximum crawl depth")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--save", "-s", type=click.Path(), help="Save results to file")
def site(url: str, max_pages: int, depth: int, output: str, save: str | None):
    """Audit an entire website (crawl and audit multiple pages).

    Example:
        aiqso-seo site https://example.com --max-pages 100
    """
    click.echo(click.style("Full site crawl not yet implemented.", fg="yellow"))
    click.echo("Use 'audit' command for single page audits.")
    # TODO: Implement full site crawling


@cli.command()
def tiers():
    """List available service tiers and their features."""
    manager = get_tier_manager()
    all_tiers = manager.get_all_tiers()

    click.echo()
    click.echo(click.style("Available Service Tiers", bold=True))
    click.echo("=" * 60)
    click.echo()

    for _name, tier in sorted(all_tiers.items(), key=lambda x: x[1].price_monthly or 0):
        price_str = f"${tier.price_monthly}/mo" if tier.price_monthly else "Free"
        click.echo(click.style(f"{tier.display_name} ({price_str})", bold=True))
        click.echo(f"  {tier.description}")
        click.echo()
        click.echo("  Features:")
        click.echo(f"    AI Insights:    {'Yes' if tier.features.ai_insights else 'No'}")
        click.echo(f"    Lighthouse:     {'Yes' if tier.features.lighthouse_integration else 'No'}")
        click.echo(f"    Full Site Crawl:{'Yes' if tier.features.full_site_crawl else 'No'}")
        click.echo(f"    API Access:     {'Yes' if tier.features.api_access else 'No'}")
        click.echo(f"    White Label:    {'Yes' if tier.features.white_label else 'No'}")
        click.echo()
        click.echo("  Limits:")
        click.echo(f"    Audits/Day:     {tier.rate_limits.audits_per_day or 'Unlimited'}")
        click.echo(f"    Keywords:       {tier.rate_limits.keywords_tracked or 'Unlimited'}")
        click.echo(f"    Websites:       {tier.rate_limits.websites or 'Unlimited'}")
        click.echo()
        click.echo("-" * 60)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
