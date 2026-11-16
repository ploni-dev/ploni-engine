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
goes around it (PROMOTION.md section 11, "What it does not do"). It does not read a
command handed to another program as text (`bash -c`, `eval`, `cmd /c`), an alias or a
variable that holds the words of a merge, a quote escaped with a backslash, a command
that quote signs hide in both readings of `segments` at once, or a file written by a
shell command and not by Edit or Write. It refuses too much in these known cases, and then the text goes in a
file, or the command is typed another way:
  - the words of a refused command on a line of their own in a here-document, in a
    quoted text of several lines, or inside `$( )` or backticks;
  - a merge whose -R stands after a quoted text of several lines: read line by line,
    the first line names no repository;
  - a push that names no branch, or names it through a variable, although it would not
    reach main;
  - `--no-verify` as a search word (`grep -- --no-verify`);
  - `push`, `commit` or `merge` as a plain word of another git or `gh pr` command
    (`git log --grep push`, `git commit -m push`, `gh pr list --search merge`);
  - a short flag with an n in it after `commit` (`git commit -m x -uno`).
A commit pushed between the gate's look and the merge is not seen; `--match-head-commit`
on the merge closes that, and the gate does not ask for it.
"""

import json
import posixpath
import re
import shlex
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
# What ends a simple command. Curly brackets: PowerShell chains commands as
# `if ($?) {...}`. A backtick: it opens and closes a command inside a command.
SEPARATORS = "();<>|&{}`\n"
EVERY_BRANCH = frozenset(("--all", "--mirror", "--branches"))
# A target the hook cannot name counts as main: it does not know the branch that is checked out.
MAIN = frozenset(("main", "HEAD", "@"))
UNREADABLE = (OSError, subprocess.SubprocessError, ValueError, LookupError, TypeError, AttributeError)


def _words(text: str) -> list[str]:
    """Split text into shell words, with each run of separator signs as a word of its own."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=SEPARATORS)
    # A new line is a separator, not a blank, but for one inside a quoted text.
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    # Windows paths hold backslashes, so a backslash escapes nothing here. Text after
    # a hash sign is read like the rest and not dropped as a comment.
    lexer.commenters = ""
    lexer.escape = ""
    return list(lexer)


def segments(command: str) -> list[list[str]]:
    """Split a shell command into its simple commands, each a list of words.

    Why: a hook sees the whole text of a tool call, and the command to judge may stand
    after `cd x &&`, on a later line, or in a pipe.

    Contract:
        Args: command, the text given to Bash or PowerShell.
        Returns: the words between separators (`;`, `&`, `|`, round and curly brackets,
            redirections, a backtick, a new line), quotes removed. A line continued with a
            backslash or a backtick is joined to the next. A quoted text is one word of
            its command, whatever it holds; where it holds `$(` or a backtick, the simple
            commands inside it follow. A command of several lines is read twice, as one
            text and line by line, and each simple command is returned once, those of the
            first reading first.
        Raises: nothing. Where a quote is never closed, every quote sign of that reading
            is read as a space, so the words after it are still found.

    Known limits: this is not a shell. The two readings exist because each alone is
    blind: read as one text, an apostrophe in a comment hides the lines up to the next
    apostrophe; read line by line, a line that ends one quoted text and opens another
    hides what stands between them. A command that both hide at once is not found. It
    follows the quoting of sh, without backslash escapes; PowerShell differs in details.
    """
    text = re.sub(r"[\\`]\r?\n", " ", command)
    found: list[list[str]] = []
    for reading in (text, *text.split("\n")):
        for segment in _reading(reading):
            if segment and segment not in found:
                found.append(segment)
    return found


def _reading(text: str) -> list[list[str]]:
    """Return the simple commands of text, read once; those inside a quoted word come last."""
    try:
        words = _words(text)
    except ValueError:
        words = _words(text.replace("'", " ").replace('"', " "))
    found: list[list[str]] = [[]]
    inside: list[list[str]] = []
    for word in words:
        if word and set(word) <= set(SEPARATORS):
            found.append([])
            continue
        found[-1].append(word)
        if "$(" in word or "`" in word:
            inside += segments(word)
    return [*found, *inside]


def _after(words: list[str], program: str) -> list[str]:
    """Return the words after the first one that names program, or nothing without one."""
    names = [re.sub(r"\.(exe|cmd|bat)$", "", re.split(r"[\\/]", word)[-1].lower()) for word in words]
    return words[names.index(program) + 1 :] if program in names else []


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
        Returns: one (number, repository) pair for each simple command that holds a `gh`
            program followed by the words `pr` and, later, `merge`; the same pair is given
            once. number is the word right after `merge` when it is made of digits, else
            "". repository is the one value of -R or --repo, else None.
        Raises: nothing.

    Known limits: a `gh pr` command with `merge` as a plain word of another kind, such as
    a search word, is returned too. See the module docstring for what is not read.
    """
    found = []
    for words in segments(command):
        rest = _after(words, "gh")
        if "pr" in rest and "merge" in rest[rest.index("pr") :]:
            number = "".join(rest[rest.index("merge", rest.index("pr")) + 1 :][:1])
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
        Returns: one line when a simple command holds the word `--no-verify`, or
            `git ... commit` followed by a short-flag word with an n in it (-n, -nm, -anm).
            Empty otherwise.
        Raises: nothing.

    Known limits: -n means something else on other git commands and is let through
    there. `core.hooksPath` and other ways around the git hooks are not looked for.
    """
    for words in segments(command):
        rest = _after(words, "git")
        flags = rest[rest.index("commit") :] if "commit" in rest else []
        if "--no-verify" in words or any(re.fullmatch("-[A-Za-z]*n[A-Za-z]*", flag) for flag in flags):
            return ["--no-verify and `git commit -n` are refused: the git hooks run on every commit"]
    return []


def push_refusals(command: str) -> list[str]:
    """Return why a shell command is refused for pushing to main.

    Why: PROCESS.md section 12 item 8. Everything reaches main through a PR; a direct push
    arrives with no check and no review.

    Contract:
        Args: command, the text given to Bash or PowerShell.
        Returns: one line when a simple command holds `git ... push` (not
            `git stash push`) and names main as a target (main, x:main, +main, :main,
            refs/heads/main, heads/main), names no target, names HEAD or a target with a
            `$` in it, or carries --all, --mirror or --branches. Empty otherwise.
        Raises: nothing.

    Known limits: the first word after `push` that is no flag is taken as the remote and
    every later one as a branch, so the value of a flag such as `-o` can be mistaken for
    the remote. A word of digits only is not taken as a branch: it is the 2 of `2>&1`.
    A push with no branch named is refused wherever it would go.
    """
    for words in segments(command):
        rest = _after(words, "git")
        if "push" not in rest or rest[: rest.index("push")][-1:] == ["stash"]:
            continue
        given = rest[rest.index("push") + 1 :]
        named = [word for word in given if not word.startswith("-") and not word.isdigit()][1:]
        targets = {
            word.rsplit(":", 1)[-1].lstrip("+").removeprefix("refs/").removeprefix("heads/") for word in named
        }
        # A variable is checked in the whole word: PowerShell writes `$env:NAME`, with a colon.
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
