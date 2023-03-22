class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    BLUE = "\u001b[34m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def ok(msg: str, do_print: bool = True) -> None:
    if do_print:
        print(f"{Colors.OKGREEN}{Colors.BOLD}inv{Colors.ENDC} > {msg}")


def info(msg: str, do_print: bool = True) -> None:
    if do_print:
        print(f"{Colors.OKCYAN}{Colors.BOLD}inv{Colors.ENDC} > {msg}")


def warn(msg: str, do_print: bool = True) -> None:
    if do_print:
        print(f"{Colors.WARNING}{Colors.BOLD}inv{Colors.ENDC} > {msg}")


def error(msg: str, exit_now: bool = True) -> None:
    print(f"{Colors.FAIL}{Colors.BOLD}inv{Colors.ENDC} > {msg}")
    if exit_now:
        exit(1)
