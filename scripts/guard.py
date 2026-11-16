"""Refuse the tool calls that the Claude Code hooks of this project stop.

Why: Achia chose a local merge gate in place of paid branch protection (PROMOTION.md
section 11): the agent's merge command runs only when every check on the PR's last commit
is green. A settings file holds one command line, which cannot be tested, so the rules are
here and `.claude/settings.json` only starts this script (Achia, 2026-11-16). The small
hooks of PROCESS.md section 12 item 8 are here as well, for the same reason.

Contract: Claude Code starts the script before a Bash, PowerShell, Edit or Write call and
writes the hook payload to stdin as JSON. Exit code 0 lets the call run. Exit code 2
refuses it, and stderr gives one line for each reason. Refused are:
  - `gh pr merge`, unless it names the PR by number and one repository with -R, every
    check on that PR's last commit has finished as SUCCESS, and a workflow job named
    fast-suite is one of them;
  - `--no-verify` on any command, and `git commit -n`;
  - `git push` that names main, names no branch, or pushes every branch;
  - an edit of one of the PROTECTED files.
The settings file sets `"onFailure": "block"`, so a script that fails, cannot start or
runs out of time refuses as well. That needs Claude Code 2.1.295 or later.

Known limits: this reads commands as text and stops an honest mistake, not an agent that
goes around it (PROMOTION.md section 11, "What it does not do"). It does not see an
alias or a variable that holds the words of a command, a command that every reading of
`segments` breaks, or a file written by a shell command and not by Edit or Write. It
errs to the side of refusing, and refuses too much in these known cases; then the text
goes in a file, or the command is typed another way:
  - the words of a refused command in a text of the same call: a commit message or a PR
    comment that quotes `gh pr merge 80 -R o/r` or `git push origin main`, in quotes or
    in a here-document, also as the text of `bash -c` or of `grep`;
  - a merge whose -R stands after a quoted text of several lines, or beside a second -R
    in a quoted text;
  - a push that names no branch, or names it through a variable, although it would not
    reach main;
  - `--no-verify` as a search word (`grep -- --no-verify`);
  - `push` or `commit` as a plain word of another git command (`git log --grep push`,
    `git commit -m push`);
  - a short flag with an n in it after `commit` (`git commit -m x -uno`).
A commit pushed between the gate's look and the merge is not seen; `--match-head-commit`
on the merge closes that, and the gate does not ask for it.
"""

import json
import posixpath
import re
import shutil
import subprocess
import sys
from collections.abc import Callable

Check = dict[str, object]
Fetch = Callable[[str, str], list[Check] | None]

# The job of .github/workflows/fast.yml that CLAUDE.md, "Merging", asks for by name.
GATE_CHECK = "fast-suite"
# Under the 40 seconds that .claude/settings.json gives the hook, so that a slow GitHub
# is as a rule a refusal with a reason. A hook that is cut off all the same refuses too
# (`onFailure` in the settings file), without a reason.
GH_TIMEOUT_SECONDS = 30
# PROCESS.md section 12 item 8: the waiver file, and the files that hold the hooks.
PROTECTED = (".claude/settings.json", ".claude/settings.local.json", "docs/WAIVERS.md", "scripts/guard.py")
# One shell word, with the quoted texts that touch it; or one run of the signs that end a
# simple command. There are two ways to read a bracket or a backtick, and each sees what
# the other misses. As a blank: what stands after `$(pwd)` stays in its command
# (`git -C $(pwd) push origin main`). As an end: what stands after `}` does not join the
# command inside (`try { git push } catch { throw }`).
WORD = r"""(?:"[^"]*"|'[^']*'|[^\s;|&"'(){}`])+"""
BRACKETS_BLANK = re.compile(WORD + r"|[;|&\n]+")
BRACKETS_END = re.compile(WORD + r"|[;|&\n(){}`]+")
# A redirection with its target: `2>&1`, `> file`, `2>$null`, `<<`. It is dropped before
# reading: `2>&1` holds a separator sign, and a target is no word of the command.
REDIRECTION = re.compile(r"""\d*[<>]+(?:&\d+|[ \t]*[^\s;|&()"']*)""")
QUOTE_SIGN = re.compile("[\"']")
EVERY_BRANCH = frozenset(("--all", "--mirror", "--branches"))
# A target the hook cannot name counts as main: it does not know the branch that is checked out.
MAIN = frozenset(("main", "HEAD", "@"))
UNREADABLE = (OSError, subprocess.SubprocessError, ValueError, LookupError, TypeError, AttributeError)


def _commands(text: str, tokens: re.Pattern[str] = BRACKETS_BLANK) -> list[list[str]]:
    """Return the words of each simple command of text, read once, with quotes followed."""
    found: list[list[str]] = [[]]
    for token in tokens.findall(text):
        if token[0] in ";|&\n(){}`":
            found.append([])
        else:
            found[-1].append(QUOTE_SIGN.sub("", token))
    return [words for words in found if words]


def segments(command: str) -> list[list[str]]:
    """Return the simple commands of a shell command, in every reading of its text.

    Why: a hook sees the whole text of a tool call, and the command to judge may stand
    after `cd x &&`, on a later line, in brackets, or inside a quoted `$( )`. Following
    quotes and brackets as a shell does was tried and failed three reviews in a row:
    every fix for one shape lost another. So the text is read in several simple ways,
    and a rule refuses when any reading shows it a refused command.

    Contract:
        Args: command, the text given to Bash or PowerShell.
        Returns: the words of each simple command (ended by `;`, `&`, `|` or a new line),
            quote signs removed, for each of these readings, one after another:
            the whole text, where a quoted text is one word even over several lines;
            each line by itself, so that an apostrophe in a comment hides no other line;
            the whole text with every quote sign as a blank, so that a command inside a
            quoted text is read as well.
            Each of the three is read twice: with brackets and backticks as blanks, and
            with each of them as the end of a command. A backtick before a new line is
            read both ways too: as PowerShell's sign that the line goes on, and as the
            end of a command in sh. In every reading a line continued with a backslash is
            joined to the next, and a redirection is dropped with its target. The same
            command may be given more than once.
        Raises: nothing.

    Known limits: this is not a shell, and it errs to the side of refusing. In the third
    reading the words of a quoted text join the command they stand in, so a message that
    holds the words of a refused command is refused. A command is missed only when every
    reading breaks it: a separator sign in a quoted text between its words, and a stray
    quote sign that hides that quoted text from the first two readings.
    """
    joined = re.sub(r"\\\r?\n", " ", command)
    texts = [REDIRECTION.sub(" ", text) for text in (joined, re.sub(r"`\r?\n", " ", joined))]
    readings = dict.fromkeys(
        reading for text in texts for reading in (text, *text.split("\n"), QUOTE_SIGN.sub(" ", text))
    )
    return [
        words
        for tokens in (BRACKETS_BLANK, BRACKETS_END)
        for reading in readings
        for words in _commands(reading, tokens)
    ]


def _calls(words: list[str], program: str) -> list[list[str]]:
    """Return, for each word of a command that names program, the words after it."""
    names = [re.sub(r"\.(exe|cmd|bat)$", "", re.split(r"[\\/]", word)[-1].lower()) for word in words]
    return [words[index + 1 :] for index, name in enumerate(names) if name == program]


def _past_options(words: list[str]) -> list[str]:
    """Return words from the first one that is no option; -R and --repo take their value along."""
    while words and words[0].startswith("-"):
        words = words[2:] if words[0] in ("-R", "--repo") else words[1:]
    return words


def _repository(words: list[str]) -> str | None:
    """Return the repository that -R or --repo names, or None unless exactly one is named."""
    named = [
        match[1] or "".join(words[index + 1 : index + 2])
        for index, word in enumerate(words)
        if (match := re.fullmatch(r"(?:-R|--repo)(?:=?(.+))?", word))
    ]
    return named[0] if len(named) == 1 and named[0] else None


def merges(command: str) -> list[tuple[str, str | None]]:
    """Return the target of each `gh pr merge` in a shell command.

    Why: the gate must ask GitHub about the same PR that the command would merge. So it
    takes the number and the repository from the command and from nowhere else.

    Contract:
        Args: command, the text given to Bash or PowerShell.
        Returns: one (number, repository) pair for each `gh` program, in any reading of
            `segments`, whose first word that is no option is `pr` and whose next such
            word is `merge`; the same pair is given once. number is the word right after
            `merge` when it is made of digits, else "". repository is the one value of -R
            or --repo after that `gh`, else None.
        Raises: nothing.

    Known limits: `merge` as a word of another `gh pr` command (a title, a search word)
    is no merge. The words `gh pr merge` in a quoted text are one: see `segments`.
    """
    found = []
    for words in segments(command):
        for rest in _calls(words, "gh"):
            group = _past_options(rest)
            action = _past_options(group[1:])
            if group[:1] == ["pr"] and action[:1] == ["merge"]:
                number = "".join(action[1:2])
                found.append((number if re.fullmatch("[0-9]+", number) else "", _repository(rest)))
    return list(dict.fromkeys(found))


def _state(check: Check) -> tuple[object, object]:
    """Return a check as (name, state); the state is SUCCESS only when it finished so."""
    if check.get("__typename") == "CheckRun":
        finished = check.get("status") == "COMPLETED"
        return check.get("name"), (check.get("conclusion") if finished else check.get("status")) or "UNKNOWN"
    return check.get("context"), check.get("state") or "UNKNOWN"


def red(checks: list[Check] | None) -> list[str]:
    """Return why the checks of a PR's last commit do not allow a merge.

    Why: this is the rule of CLAUDE.md, "Merging", point 1, in one place: every check
    finished and green, the fast-suite check among them, and a missing, pending or
    skipped check counts as red.

    Contract:
        Args: checks, the `statusCheckRollup` list of `gh pr view --json`, or None.
        Returns: one line for each check that is not a finished SUCCESS (a workflow job)
            or not in state SUCCESS (a commit status), and one more when no workflow job
            is named fast-suite. Empty when the merge is allowed.
        Raises: AttributeError when an entry is not a mapping.

    Known limits: a commit status named fast-suite does not count as the fast-suite
    check, because a status can be set by hand and a workflow job cannot. The job is
    known by its name only, not by the workflow file it comes from.
    """
    checks = checks or []
    reasons = [f"check {name} is {state}" for name, state in map(_state, checks) if state != "SUCCESS"]
    if not any(check.get("__typename") == "CheckRun" and check.get("name") == GATE_CHECK for check in checks):
        reasons.append(f"there is no {GATE_CHECK} check on the last commit")
    return reasons


def rollup(number: str, repository: str) -> list[Check] | None:
    """Ask GitHub for the checks on the last commit of a PR.

    Why: the only act of the gate. It is apart from `red`, which decides, so that the
    decision is tested without GitHub.

    Contract:
        Args: number, the PR number in digits; repository, as owner/name.
        Returns: the `statusCheckRollup` list of `gh pr view`, as GitHub gave it.
        Raises: OSError when gh is not installed or cannot start;
            subprocess.CalledProcessError when gh ends with an error;
            subprocess.TimeoutExpired after GH_TIMEOUT_SECONDS; ValueError when gh
            printed no JSON; KeyError or TypeError when the JSON has no rollup.

    Known limits: it uses the first `gh` on PATH and the login that gh has.
    """
    gh = shutil.which("gh")
    if gh is None:
        raise OSError("the gh program was not found")
    done = subprocess.run(  # noqa: S603 fixed argv, no shell; gh takes the word after -R as a value
        [gh, "pr", "view", number, "-R", repository, "--json", "statusCheckRollup"],
        capture_output=True,
        encoding="utf-8",
        timeout=GH_TIMEOUT_SECONDS,
        check=True,
    )
    return json.loads(done.stdout)["statusCheckRollup"]


def merge_refusals(command: str, fetch: Fetch) -> list[str]:
    """Return why the merges in a shell command are refused.

    Why: the merge gate of PROMOTION.md section 11. A gate that cannot tell refuses.

    Contract:
        Args: command, the text given to Bash or PowerShell; fetch, called with the
            number and the repository of each merge, returns the checks as `rollup` does.
        Returns: for each merge without a number or without one repository, one line; for
            each other merge, the lines of `red`, or one line when fetch raised one of
            UNREADABLE. Each line names the PR. Empty when there is no merge, or every
            merge is allowed.
        Raises: nothing that fetch raises out of UNREADABLE; anything else passes through.

    Known limits: fetch is called once for each merge, one after another.
    """
    reasons = []
    for number, repository in merges(command):
        if not number or not repository:
            reasons.append("merge gate: write the merge as `gh pr merge <N> -R <owner>/<repo> --squash`")
            continue
        try:
            found = red(fetch(number, repository))
        except UNREADABLE as error:
            found = [f"the checks could not be read: {str(getattr(error, 'stderr', None) or error).strip()}"]
        reasons += [f"merge gate, PR {number} of {repository}: {reason}" for reason in found]
    return reasons


def no_verify_refusals(command: str) -> list[str]:
    """Return why a shell command is refused for switching off the git hooks.

    Why: PROCESS.md section 12 item 8. A hook that can be skipped with one flag checks
    nothing.

    Contract:
        Args: command, the text given to Bash or PowerShell.
        Returns: one line when a simple command, in any reading of `segments`, holds the
            word `--no-verify`, or `git ... commit` followed by a short-flag word with an
            n in it (-n, -nm, -anm). Empty otherwise.
        Raises: nothing.

    Known limits: -n means something else on other git commands and is let through
    there. `core.hooksPath` and other ways around the git hooks are not looked for.
    `commit` is looked for anywhere after `git`, not as its subcommand only.
    """
    for words in segments(command):
        flags = [flag for rest in _calls(words, "git") if "commit" in rest for flag in rest[rest.index("commit") :]]
        if "--no-verify" in words or any(re.fullmatch("-[A-Za-z]*n[A-Za-z]*", flag) for flag in flags):
            return ["--no-verify and `git commit -n` are refused: the git hooks run on every commit"]
    return []


def push_refusals(command: str) -> list[str]:
    """Return why a shell command is refused for pushing to main.

    Why: PROCESS.md section 12 item 8. Everything reaches main through a PR; a direct push
    arrives with no check and no review.

    Contract:
        Args: command, the text given to Bash or PowerShell.
        Returns: one line when a simple command, in any reading of `segments`, holds
            `git ... push` (not `git stash push`) and names main as a target (main,
            x:main, +main, :main, refs/heads/main, heads/main), names no target, names
            HEAD or a target with a `$` in it, or carries --all, --mirror or --branches.
            Empty otherwise.
        Raises: nothing.

    Known limits: the first word after `push` that is no flag is taken as the remote and
    every later one as a branch, so the value of a flag such as `-o` can be mistaken for
    the remote. `push` is looked for anywhere after `git`, not as its subcommand only:
    the options of git before it can hold a quoted text with blanks, which one reading
    takes apart. A push with no branch named is refused wherever it would go.
    """
    for words in segments(command):
        for rest in _calls(words, "git"):
            if "push" not in rest or rest[: rest.index("push")][-1:] == ["stash"]:
                continue
            given = rest[rest.index("push") + 1 :]
            named = [word for word in given if not word.startswith("-")][1:]
            targets = {
                word.rsplit(":", 1)[-1].lstrip("+").removeprefix("refs/").removeprefix("heads/") for word in named
            }
            # A variable is looked for in the whole word: PowerShell writes `$env:NAME`, with a colon.
            unknown = any("$" in word for word in named)
            if not targets or unknown or targets & MAIN or EVERY_BRANCH & set(given):
                return ["a push must name its remote and its branches, and none of them may be main"]
    return []


def edit_refusals(file_path: str) -> list[str]:
    """Return why an edit of a file is refused.

    Why: PROCESS.md section 12 item 8. Only Achia writes docs/WAIVERS.md, and an agent
    that can edit the hook files can switch the hooks off.

    Contract:
        Args: file_path, as Edit or Write got it; either kind of slash, any case.
        Returns: one line when the path is one of PROTECTED or ends with one as whole
            path parts, in this checkout or in any other. Empty otherwise.
        Raises: nothing.

    Known limits: the path is compared as text after `..` is resolved and dots and
    spaces at its end, which Windows drops, are cut. A link, a short Windows name or a
    file written by a shell command is not seen. A file of the same name in another
    project, or in the user's own `.claude` folder, is refused too.
    """
    path = "/" + posixpath.normpath(file_path.replace("\\", "/").rstrip(". ")).lower()
    return [
        f"{name} is not edited by Claude: only Achia writes docs/WAIVERS.md, and a change to a hook file "
        "is a script that Claude writes and Achia runs (PROCESS.md section 12 item 8)"
        for name in PROTECTED
        if path.endswith("/" + name.lower())
    ]


def refusals(payload: dict[str, object], fetch: Fetch = rollup) -> list[str]:
    """Return every reason to refuse the tool call of one hook payload.

    Why: one hook entry serves four tools, so one place reads the payload and asks each
    rule. Every reason is given at once; a refusal that names one of three costs two
    more tries.

    Contract:
        Args: payload, the PreToolUse payload of Claude Code; fetch, as in `merge_refusals`.
        Returns: the lines of `edit_refusals` for `tool_input.file_path`, then those of
            `no_verify_refusals`, `push_refusals` and `merge_refusals` for
            `tool_input.command`. One line when `tool_input` is not a mapping. Empty when
            the call may run.
        Raises: as `merge_refusals` does.

    Known limits: the name of the tool is not read; a tool with a `command` or a
    `file_path` is judged alike, whichever it is.
    """
    given = payload.get("tool_input")
    if not isinstance(given, dict):
        return ["the hook payload has no tool_input"]
    command = str(given.get("command", ""))
    return [
        *edit_refusals(str(given.get("file_path", ""))),
        *no_verify_refusals(command),
        *push_refusals(command),
        *merge_refusals(command, fetch),
    ]


def main() -> int:
    """Return the exit code for the hook payload on stdin.

    Why: the hook entry of `.claude/settings.json` starts here.

    Contract:
        Returns: 0 when the call may run; 2 when it is refused, with one line for each
            reason on stderr, in ASCII. Stdin that is not a JSON object is refused.
        Raises: whatever `refusals` lets through; Claude Code then refuses the call,
            because the settings file says `"onFailure": "block"`.

    Known limits: stdin is read as JSON in UTF-8, whatever the console encoding is.
    """
    try:
        payload = json.loads(sys.stdin.buffer.read())
    except ValueError:
        payload = None
    reasons = refusals(payload) if isinstance(payload, dict) else ["the hook payload is not a JSON object"]
    for reason in reasons:
        print(f"guard: {reason}".encode("ascii", "backslashreplace").decode("ascii"), file=sys.stderr)
    return 2 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
