The guideline is still under construction, but let me introduce `mojopi` first.

mojopi is a flask web app, using jQuery and Materializecss as frontend libraries.
The database is a SQLite file, the ORM is Peewee.

Currently, mojopi needs to have a machinery to resolve the package dependencies.
So I imported `resolvelib` for help. The API also needs to be standardized, and I will
call the library `mups`, Mojo Ultimate Package Standard, which provides information that API needs,
including data class serialization, json marshaling, etc.

When these two works done, I will make a Mojo Enhance Proposal.
If you are interested in `mojopi`, please contact me via gmail: drunkwcodes@gmail.com.
PRs are welcome.