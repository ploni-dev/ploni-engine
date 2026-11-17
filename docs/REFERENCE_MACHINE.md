# The reference machine

`build-plan.md` section 8.1: all performance numbers of the project are measured on this machine, with pinned thread counts.

It is Achia's laptop. He decided that on 2026-11-16; the question and his answer are quoted in section 8.1.

| | |
|---|---|
| Processor | Intel Core 5 120U, 10 cores, 12 logical processors |
| Memory | 7.72 GB |
| Graphics | Intel integrated graphics, no separate GPU |
| System | Windows 11 Home, build 26200 |

Read from the machine on 2026-11-17 with `Get-CimInstance`: `Win32_Processor`, `Win32_ComputerSystem`, `Win32_VideoController` and `Win32_OperatingSystem`.

- Every time is recorded with the power state of the run, mains or battery (section 8.2). The same files took 1.03 seconds on mains power and up to 11.7 on battery (`docs/findings/2026-11-11-e2-int8-latency.md`).
- Speed is measured and recorded, and is not a gate for now (section 8.2).
- If the machine changes, with more memory or another laptop, this file changes in a PR of its own that says so, and that is a decision of Achia's. Numbers from before and after such a change are not set side by side without saying it. This last point is Claude's and only narrows what Claude may do.
