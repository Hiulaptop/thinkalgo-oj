# ZIP problem import

Open `/problems/import-zip/` (also linked from Create problem). Users need both
`judge.add_problem` and `judge.import_problem_package` permissions.

Each ZIP contains `statement.md`, `editorial.md`, `solution.cpp`, and paired
`tests/*.in` / `tests/*.out`, either at its root or inside one wrapper directory.
The preview form accepts the problem code, title, limits, category, types, points,
and C++ runtime. Creation is new-only and leaves the problem/editorial private.

Run migrations before use. Site and worker share the private import volume;
never expose `/private-problem-imports` through nginx or public media storage.
The worker requires `BRIDGED_R2_PROBLEMS=True` and working problem-release storage
to publish tests before creating the reference submission. Failed publishing
keeps the hidden problem and exposes a Retry button. Source ZIP and solution
downloads require ownership of the draft or edit access to the created problem.

Run `python3 manage.py reconcile_problem_imports` periodically (for example every
five minutes via your scheduler) to re-enqueue pending work and remove drafts
older than 24 hours. The status page displays the current submission verdict;
refresh it after judging. A wrong answer is a completed verification, not an
upload failure. Successful verification does not publish the problem.

## Verification and current limitations

Automated tests cover parsing, unsafe paths, missing pairs, metadata, private
creation, duplicate confirmation, preview rendering, publish failure and one
reference submission across retries. Real R2/judge verification still requires
configured storage and a connected C++ judge.

This first implementation does not yet provide automatic status polling, a
dedicated Beat service, or local shared-directory judge mode. Preview shows raw
Markdown. Worker publication currently holds the import row lock during the
storage call; a lease-based worker and comprehensive mutation guards across all
administrative/CLI paths remain follow-up work. Do not change test releases via
CLI during reference verification. These differences from the full design must
be resolved before treating this as the complete planned production workflow.
