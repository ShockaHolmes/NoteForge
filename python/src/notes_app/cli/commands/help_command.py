def render_help(program_name: str = "python -m notes_app.cli.main") -> str:
    return (
        "Future Proof Notes CLI (phase-1 starter)\n\n"
        f"Usage: {program_name} [command]\n\n"
        "Commands:\n"
        "  help  Show this help text\n"
        "  list  List notes with metadata\n"
        "  create <title> <content>  Create a note\n\n"
        "Examples:\n"
        f"  {program_name} create \"My Note\" \"hello world\"\n"
        f"  {program_name} list\n"
    )
