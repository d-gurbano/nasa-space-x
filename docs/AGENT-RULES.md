# Rules for every data agent (Rewind, Team SpaceX, Space Apps 2026)

Project root: /Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind
Plan: docs/DATA-PLAN.md (read it first).

Python environment (has numpy, scipy, pandas, astropy, astroquery, pyvo, photutils, sbpy, s3fs, boto3, pyarrow, matplotlib, kete):
  cd /Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind && source env.sh
If you pip install anything new, run: xattr -dr com.apple.quarantine .venv   (macOS blocks new native libraries otherwise).

Hard rules:
1. Public data only.
   - READ-ONLY: never submit, post, upload, register or write to any external service, including the MPC, GitHub and forums.
   - No logins.
2. No Chinese sources, data, code or contacts.
3. Sources:
   - NASA/US first.
   - Partner (ESA, France, Canada, Korea, etc.) only when it adds clear value. Write down why.
4. Save everything inside the project root, in your assigned data/ subfolder.
   - Put scripts in code/<your-agent-id>/ so downloads can be repeated.
5. Provenance:
   - Append every source you used to docs/SOURCES.md. Use one line per source (append, never overwrite):
     `| agent | dataset | url | version/release | date accessed | license/credit | US or partner | local path |`
   - For downloaded files, also write a manifest.csv in your folder with: filename, url, bytes, sha256, date.
6. Label every number MEASURED (you computed it from data), VERIFIED (read in a source), COMPUTED (your arithmetic) or ESTIMATED.
7. Be polite to servers:
   - Pace requests and retry with backoff.
   - Prefer bulk files and AWS S3 public buckets (anonymous) over thousands of API calls.
   - IRSA services sometimes return 503; retry.
8. Disk budget: the whole project should stay under about 50 GB. Your agent's budget is in your task. Stop and report if you would exceed it.
9. Do not delete anything outside your own folder.
10. No em dashes in any text you write; use hyphens.
11. When done, write data/<your-folder>/REPORT.md with:
    - (a) what you collected, with counts and sizes
    - (b) every source checked, including ones that failed or had nothing, and why
    - (c) what is missing or uncertain
    - (d) how the data maps to Rewind features
    - (e) recommended next steps
