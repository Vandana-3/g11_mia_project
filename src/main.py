from __future__ import annotations

from src.pipeline import run_pipeline


def main() -> int:
    context, exit_code = run_pipeline()

    print("Pipeline run complete.")
    print(f"Blockers: {len(context.get('blockers', []))}")
    print(f"Warnings: {len(context.get('warnings', []))}")

    if context.get("warnings"):
        print("Run warnings:")
        for warning in context["warnings"]:
            print(f"- {warning}")

    if context.get("blockers"):
        print("Run blockers:")
        for blocker in context["blockers"]:
            print(f"- {blocker}")

    if context.get("ml_base_meta"):
        print(f"Final ML base file: {context['ml_base_meta'].get('output_path')}")

    print("QA report: outputs/qa/qa_report.md")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
