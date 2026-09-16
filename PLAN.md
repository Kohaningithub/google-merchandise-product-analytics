# Implementation plan and status

1. Inspect the existing portfolio repository and preserve its work. **Done.**
2. Verify source documentation, live credentials, schema and audit. **Documentation verified; live query blocked by missing ADC and query project.** The actual authentication library was checked and returned DefaultCredentialsError.
3. Build bounded BigQuery audit, analytical models and dbt validation. **Implemented; locally parsed, with session relational logic tested through DuckDB translation. Live BigQuery execution pending.**
4. Build funnel/retention outputs, monitoring, contribution diagnosis and prospective experimentation. **Implemented and tested using isolated synthetic fixtures only. No fixture is a published finding.**
5. Generate a polished static site from aggregate artifacts. **Done, with explicit pending-data state. Desktop/mobile browser reviewed; screenshot included.**
6. Test and review correctness, denominator boundaries and source limitations. **Offline tests and lint pass. See docs/review.md.**
7. Deploy GitHub Pages. The original private repository's plan rejected Pages. **The user authorized a separate public project repository**, keeping the existing portfolio private. Deployment uses this standalone repository.

Remaining analytical work requires one-time Google authentication and a query project, then `python -m src.pipeline all`. This will execute actual schema/audit checks, materialize models, fail on invalid data, generate observations, size the prospective experiment, and publish real aggregate charts. Never claim this step has run before it has.
