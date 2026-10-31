# GSK progress

## Done

- Agreed shared model, route, and billing contract in `CONTRACT.md`.
- Created Django project skeleton, billing calculation and orchestration code, and preview/run endpoint shells.
- Verified month-end cycles, discount and tax totals, catch-up, duplicate-run behavior, discount usage limits, and bad-cursor reporting with six independent tests.

## Next

- Connect YASCN subscription models and ALIAR invoice creation service in `gsk/integration.py` to make the preview/run endpoints live.
- Register their URL modules and GDM's frontend after their handoffs arrive.

## Blocked

- Full Django migrations and API checks require YASCN's custom User model and ALIAR's invoice models, which are not present yet.

## Contract changes

- None; implementation follows `CONTRACT.md`.

## Verification

- `python3 -m unittest discover -s gsk/tests -v`: 6 tests passed.
- `python3 -m compileall -q gsk manage.py` and `git diff --check`: passed.
- `.venv/bin/python manage.py check`: blocked by missing `yascn` app (the integrated project deliberately names `yascn.User` before migrations).
- Isolated Django system check with teammate apps omitted: passed, 0 issues.
