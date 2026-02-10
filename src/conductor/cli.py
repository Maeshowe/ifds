"""CONDUCTOR CLI — entry point for python -m conductor."""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="conductor",
        description="CONDUCTOR — Intelligent Agent System",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    subparsers.add_parser("init", help="Initialize CONDUCTOR in this project")

    # where-am-i
    subparsers.add_parser("where-am-i", help="Instant orientation")

    # continue
    subparsers.add_parser("continue", help="Resume with full context")

    # wrap-up
    wrap_up_parser = subparsers.add_parser("wrap-up", help="End session, save state")
    wrap_up_parser.add_argument(
        "--summary", required=True, help="Session summary (mandatory)"
    )

    # pause
    subparsers.add_parser("pause", help="Emergency state save")

    # learn
    learn_parser = subparsers.add_parser("learn", help="Record discovery or correction")
    learn_parser.add_argument("--content", required=True, help="What you learned")
    learn_parser.add_argument(
        "--category",
        required=True,
        choices=["rule", "discovery", "correction"],
        help="Category of learning",
    )

    # route
    route_parser = subparsers.add_parser("route", help="Classify input and suggest routing")
    route_parser.add_argument("input", help="User input text to classify")

    # analyze-idea
    idea_subparsers = subparsers.add_parser("analyze-idea", help="BA Bridge — idea analysis")
    idea_actions = idea_subparsers.add_subparsers(dest="action", required=True)

    idea_save = idea_actions.add_parser("save", help="Save a structured brief")
    idea_save.add_argument("--title", required=True, help="Brief title")
    idea_save.add_argument("--data", required=True, help="Brief data as JSON string")

    idea_list = idea_actions.add_parser("list", help="List briefs")
    idea_list.add_argument("--status", default="all", help="Filter by status (draft|ready|all)")

    idea_status = idea_actions.add_parser("status", help="Update brief status")
    idea_status.add_argument("--id", type=int, required=True, help="Brief ID")
    idea_status.add_argument("--set", required=True, dest="new_status",
                             choices=["draft", "ready", "handed_off", "completed"],
                             help="New status")

    # build
    build_parser = subparsers.add_parser("build", help="Build management — plans and execution")
    build_actions = build_parser.add_subparsers(dest="action", required=True)

    build_plan = build_actions.add_parser("plan", help="Create build plan from brief")
    build_plan.add_argument("--brief-id", type=int, required=True, help="Brief ID to plan from")
    build_plan.add_argument("--data", required=True, help="Plan data as JSON string")

    build_list = build_actions.add_parser("list", help="List build plans")
    build_list.add_argument("--status", default="all", help="Filter by status")
    build_list.add_argument("--brief-id", type=int, help="Filter by brief ID")

    build_status = build_actions.add_parser("status", help="Update plan status")
    build_status.add_argument("--id", type=int, required=True, help="Plan ID")
    build_status.add_argument("--set", required=True, dest="new_status",
                              choices=["draft", "approved", "in_progress", "completed", "blocked"],
                              help="New status")

    build_step = build_actions.add_parser("step", help="Update a build step")
    build_step.add_argument("--id", type=int, required=True, help="Plan ID")
    build_step.add_argument("--step", type=int, required=True, help="Step order number")
    build_step.add_argument("--status", required=True,
                            choices=["pending", "in_progress", "done", "skipped"],
                            help="New step status")
    build_step.add_argument("--notes", help="Step notes")

    build_get = build_actions.add_parser("get", help="Get full plan details")
    build_get.add_argument("--id", type=int, required=True, help="Plan ID")

    # review
    review_parser = subparsers.add_parser("review", help="Code review management")
    review_actions = review_parser.add_subparsers(dest="action", required=True)

    review_create = review_actions.add_parser("create", help="Create a review")
    review_create.add_argument("--plan-id", type=int, help="Build plan ID")
    review_create.add_argument("--brief-id", type=int, help="Brief ID")
    review_create.add_argument("--type", default="code",
                               choices=["code", "brief_compliance", "quality"],
                               help="Review type")
    review_create.add_argument("--data", required=True, help="Review data as JSON")

    review_list = review_actions.add_parser("list", help="List reviews")
    review_list.add_argument("--plan-id", type=int, help="Filter by plan ID")
    review_list.add_argument("--verdict", help="Filter by verdict")

    review_update = review_actions.add_parser("update", help="Update review")
    review_update.add_argument("--id", type=int, required=True, help="Review ID")
    review_update.add_argument("--verdict",
                               choices=["pending", "approved", "changes_requested", "rejected"],
                               help="New verdict")
    review_update.add_argument("--data", help="Additional data as JSON")

    # red-team
    rt_parser = subparsers.add_parser("red-team", help="Red Team analysis — challenge assumptions")
    rt_actions = rt_parser.add_subparsers(dest="action", required=True)

    rt_save = rt_actions.add_parser("save", help="Save a red-team analysis")
    rt_save.add_argument("--title", required=True, help="Analysis title")
    rt_save.add_argument("--data", required=True, help="Analysis data as JSON")
    rt_save.add_argument("--target-type", help="Target type (plan|brief|decision|text)")
    rt_save.add_argument("--target-id", type=int, help="Target ID")

    rt_list = rt_actions.add_parser("list", help="List red-team analyses")
    rt_list.add_argument("--status", default="active", help="Filter by status (active|all)")

    rt_get = rt_actions.add_parser("get", help="Get red-team analysis details")
    rt_get.add_argument("--id", type=int, required=True, help="Analysis ID")

    # scenarios
    sc_parser = subparsers.add_parser("scenarios", help="Scenario Builder — generate alternatives")
    sc_actions = sc_parser.add_subparsers(dest="action", required=True)

    sc_save = sc_actions.add_parser("save", help="Save a scenario analysis")
    sc_save.add_argument("--title", required=True, help="Analysis title")
    sc_save.add_argument("--data", required=True, help="Analysis data as JSON")
    sc_save.add_argument("--target-type", help="Target type (plan|brief|decision|text)")
    sc_save.add_argument("--target-id", type=int, help="Target ID")

    sc_list = sc_actions.add_parser("list", help="List scenario analyses")
    sc_list.add_argument("--status", default="active", help="Filter by status (active|all)")

    sc_get = sc_actions.add_parser("get", help="Get scenario analysis details")
    sc_get.add_argument("--id", type=int, required=True, help="Analysis ID")

    # compliance
    cp_parser = subparsers.add_parser("compliance", help="Compliance review — regulatory awareness")
    cp_actions = cp_parser.add_subparsers(dest="action", required=True)

    cp_save = cp_actions.add_parser("save", help="Save a compliance analysis")
    cp_save.add_argument("--title", required=True, help="Analysis title")
    cp_save.add_argument("--data", required=True, help="Analysis data as JSON")
    cp_save.add_argument("--target-type", help="Target type (plan|brief|decision|text)")
    cp_save.add_argument("--target-id", type=int, help="Target ID")

    cp_list = cp_actions.add_parser("list", help="List compliance analyses")
    cp_list.add_argument("--status", default="active", help="Filter by status (active|all)")

    cp_get = cp_actions.add_parser("get", help="Get compliance analysis details")
    cp_get.add_argument("--id", type=int, required=True, help="Analysis ID")

    # decide
    dec_parser = subparsers.add_parser("decide", help="Decision Journal — record decisions")
    dec_actions = dec_parser.add_subparsers(dest="action", required=True)

    dec_create = dec_actions.add_parser("create", help="Record a decision")
    dec_create.add_argument("--title", required=True, help="Decision title")
    dec_create.add_argument("--data", required=True, help="Decision data as JSON")

    dec_list = dec_actions.add_parser("list", help="List decisions")
    dec_list.add_argument("--status", default="active", help="Filter by status (active|archived|all)")
    dec_list.add_argument("--tag", help="Filter by tag")

    dec_get = dec_actions.add_parser("get", help="Get decision details")
    dec_get.add_argument("--id", type=int, required=True, help="Decision ID")

    dec_archive = dec_actions.add_parser("archive", help="Archive a decision")
    dec_archive.add_argument("--id", type=int, required=True, help="Decision ID")

    # test
    test_parser = subparsers.add_parser("test", help="Test runner — save and track test results")
    test_actions = test_parser.add_subparsers(dest="action", required=True)

    test_save = test_actions.add_parser("save", help="Save test run results")
    test_save.add_argument("--data", required=True, help="Test results as JSON")
    test_save.add_argument("--plan-id", type=int, help="Build plan ID")
    test_save.add_argument("--brief-id", type=int, help="Brief ID")

    test_list = test_actions.add_parser("list", help="List test runs")
    test_list.add_argument("--status", default="all", help="Filter by status (passed|failed|error|all)")
    test_list.add_argument("--plan-id", type=int, help="Filter by plan ID")

    test_get = test_actions.add_parser("get", help="Get test run details")
    test_get.add_argument("--id", type=int, required=True, help="Test run ID")

    # setup-env
    env_parser = subparsers.add_parser("setup-env", help="Environment inspection and documentation")
    env_actions = env_parser.add_subparsers(dest="action", required=True)

    env_actions.add_parser("check", help="Inspect current environment")

    env_save = env_actions.add_parser("save", help="Save environment snapshot")
    env_save.add_argument("--data", required=True, help="Environment data as JSON")

    args = parser.parse_args()
    project_dir = args.project_dir.resolve()

    if args.command == "init":
        from conductor.init import init_project

        import json

        result = init_project(project_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "where-am-i":
        from conductor.commands.where_am_i import run

        print(run(project_dir))

    elif args.command == "continue":
        from conductor.commands.continue_session import run

        print(run(project_dir))

    elif args.command == "wrap-up":
        from conductor.commands.wrap_up import run

        print(run(project_dir, summary=args.summary))

    elif args.command == "pause":
        from conductor.commands.pause import run

        print(run(project_dir))

    elif args.command == "learn":
        from conductor.commands.learn import run

        print(run(project_dir, content=args.content, category=args.category))

    elif args.command == "route":
        from conductor.commands.route import run

        print(run(args.input))

    elif args.command == "analyze-idea":
        from conductor.commands.analyze_idea import run

        print(run(project_dir, action=args.action, args=args))

    elif args.command == "build":
        from conductor.commands.build import run

        print(run(project_dir, action=args.action, args=args))

    elif args.command == "review":
        from conductor.commands.review import run

        print(run(project_dir, action=args.action, args=args))

    elif args.command in ("red-team", "scenarios", "compliance"):
        from conductor.commands.strategy import run

        type_map = {"red-team": "red_team", "scenarios": "scenarios", "compliance": "compliance"}
        print(run(project_dir, analysis_type=type_map[args.command], action=args.action, args=args))

    elif args.command == "decide":
        from conductor.commands.decide import run

        print(run(project_dir, action=args.action, args=args))

    elif args.command == "test":
        from conductor.commands.test_cmd import run

        print(run(project_dir, action=args.action, args=args))

    elif args.command == "setup-env":
        from conductor.commands.setup_env import run

        print(run(project_dir, action=args.action, args=args))


if __name__ == "__main__":
    main()
