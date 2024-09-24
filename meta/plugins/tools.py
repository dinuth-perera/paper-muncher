# Implementing point 4 (Refactor Module and Command Checks to Remove Repetition) only.

from cutekit import shell, vt100, cli
import subprocess
import re

def getVersionFromOutput(output: str, versionRegex: str) -> tuple[int, ...]:
    versionMatch = re.search(versionRegex, output)
    if versionMatch:
        versionStr = versionMatch[0].split(".")
        return tuple(map(int, versionStr))
    else:
        return ()

def checkVersion(cmd: str, versionExpected: tuple[int, ...], versionCommand: str, versionRegex: str) -> tuple[bool, tuple[int, ...]]:
    try:
        result = subprocess.check_output([cmd, versionCommand]).decode("utf-8")
        actualVersion = getVersionFromOutput(result, versionRegex)
        return actualVersion >= versionExpected, actualVersion
    except subprocess.CalledProcessError:
        return False, ()

def commandIsAvailable(cmd: str, versionExpected: tuple[int, ...] = (0, 0, 0), versionCommand: str = "--version", versionRegex: str = r"\d+(\.\d+)+") -> bool:
    print(f"Checking if {cmd} is available... ", end="")
    result = True
    try:
        cmd = shell.latest(cmd)
        path = shell.which(cmd) or cmd
        versionMatch, version = checkVersion(cmd, versionExpected, versionCommand, versionRegex)
        if not versionMatch:
            if versionExpected == (0, 0, 0):
                print(f"{vt100.RED}not found{vt100.RESET}")
            else:
                print(f"{vt100.RED}too old{vt100.RESET}")
                print(f"Expected: {'.'.join(map(str, versionExpected))}, Actual: {'.'.join(map(str, version))}")
            result = False
        else:
            print(f"{vt100.GREEN}ok{vt100.RESET}")
        print(f"{vt100.BRIGHT_BLACK}Command: {cmd}\nLocation: {path}\nVersion: {'.'.join(map(str, version))}{vt100.RESET}\n")
    except subprocess.CalledProcessError as e:
        print(f" {e}")
        print(f"{vt100.RED}Error: {cmd} is not available{vt100.RESET}")
        result = False
    return result

def moduleIsAvailable(module: str) -> bool:
    print(f"Checking if {module} is available...", end="")
    try:
        mod = __import__(module)
        print(f"{vt100.GREEN} ok{vt100.RESET}")
        version = getattr(mod, "__version__", "unknown")
        path = getattr(mod, "__file__", "unknown")
        print(f"{vt100.BRIGHT_BLACK}Module: {module}\nVersion: {version}\nLocation: {path}{vt100.RESET}\n")
        return True
    except ImportError as e:
        print(f" {e}")
        print(f"{vt100.RED}Error: {module} is not available{vt100.RESET}")
        return False

@cli.command("d", "tools/doctor", "Check if all required commands are available")
def _():
    everythingIsOk = True

    # Refactored module check to remove repetition
    required_modules = ["requests", "graphviz", "magic", "cutekit"]
    everythingIsOk = all(moduleIsAvailable(mod) for mod in required_modules)

    # Refactored command check to remove repetition
    required_commands = [
        ("clang", (18,)),
        ("clang++", (16,)),
        ("llvm-ar", (16,)),
        ("ld.lld", (16,)),
        ("nasm", (0, 0, 0)),
        ("ninja", (0, 0, 0)),
        ("cutekit", (0, 0, 0)),
        ("pkg-config", (0, 0, 0))
    ]

    everythingIsOk = everythingIsOk and all(commandIsAvailable(cmd, versionExpected=ver) for cmd, ver in required_commands)

    if everythingIsOk:
        print(f"\n{vt100.GREEN}Everything is looking good 😉👌{vt100.RESET}\n")
