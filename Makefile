# `make check` runs the fast suite (build-plan.md Phase 0). The work is in scripts/check.py,
# which is also how the laptop runs it, as `python scripts/check.py`: it has no make.
.PHONY: check
check:
	python scripts/check.py
