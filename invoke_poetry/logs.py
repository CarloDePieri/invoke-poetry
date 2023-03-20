class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def ok(msg, verbose: bool = True):
    if verbose:
        print(f"{Colors.OKGREEN}{Colors.BOLD}inv{Colors.ENDC} > {msg}")


def info(msg, verbose: bool = True):
    if verbose:
        print(f"{Colors.OKCYAN}{Colors.BOLD}inv{Colors.ENDC} > {msg}")


def warn(msg, verbose: bool = True):
    if verbose:
        print(f"{Colors.WARNING}{Colors.BOLD}inv{Colors.ENDC} > {msg}")


def error(msg, exit_now: bool = True) -> None:
    print(f"{Colors.FAIL}{Colors.BOLD}inv{Colors.ENDC} > {msg}")
    if exit_now:
        exit(1)
