import sys


def get_runner(provider_name="youtube"):
    if provider_name == "youtube":
        from openclaw.scout.providers.youtube_provider import YouTubeProvider
        provider = YouTubeProvider()
    else:
        from openclaw.scout.providers.mock_provider import MockProvider
        provider = MockProvider()
    from openclaw.scout.runner import ScoutRunner
    return ScoutRunner(provider=provider)


def parse_flag(args, flag, default=None):
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
    return default


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage:")
        print("  python -m openclaw.main scout \"deadlift, powerlifting\"")
        print("  python -m openclaw.main brief [--persona archivist|scout|furnace]")
        print("  python -m openclaw.main brief --all")
        print("  python -m openclaw.main history")
        print("  python -m openclaw.main creators")
        sys.exit(0)

    command = args[0]
    use_mock = "--mock" in args
    provider_name = "mock" if use_mock else "youtube"

    if command == "scout":
        query_args = [a for a in args[1:] if not a.startswith("--")]
        query = query_args[0] if query_args else "deadlift, strength"
        runner = get_runner(provider_name)
        result = runner.run(query)
        print(result["brief"])

    elif command == "brief":
        from openclaw.brief.generator import generate_brief
        run_id = None
        persona = parse_flag(args, "--persona", "archivist")
        # run_id is positional but must not be a known persona name
        known_personas = ["archivist", "scout", "furnace"]
        pos = [a for a in args[1:] if not a.startswith("--") and a not in known_personas]
        if pos:
            run_id = pos[0]

        if "--all" in args:
            for p in ["archivist", "scout", "furnace"]:
                generate_brief(run_id=run_id, persona_name=p)
                print()
        else:
            generate_brief(run_id=run_id, persona_name=persona)

    elif command == "script":
        from openclaw.brief.generator import generate_brief
        persona = parse_flag(args, "--persona", "furnace")
        generate_brief(persona_name=persona, task_name="script")

    elif command == "history":
        get_runner("mock").print_recent_runs()

    elif command == "creators":
        get_runner("mock").print_top_creators()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
