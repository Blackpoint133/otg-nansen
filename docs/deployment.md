# Deployment

Development and test validation must precede deployment changes. The reviewed
`nansen` schema is applied to `server_otg_staging` only; the Nansen UI/runtime
does not require a production PostgreSQL migration.

## Production Integration

The public product is the native Nansen mode in OTG Analytics:
<https://otgos.run.place/?mode=nansen>.

The production application reads from a private loopback Nansen backend that
is separate from the staging service. The backend refreshes one shared,
sanitized observation approximately once per hour and persists the latest
successful state across service restarts. Page visits, chart changes, and
Guide interactions do not trigger Nansen requests. Credentials remain
server-side. The Nansen UI/runtime requires no production PostgreSQL schema or
data changes.

## Meridian Staging Integration

The public staging application is the existing OTG Analytics Streamlit site at
`https://otgostest.run.place/`. Caddy terminates HTTPS and routes the staging
host to the site's loopback application on `127.0.0.1:8504`.

Nansen is an additional native OTG Analytics mode at `/?mode=nansen`. The site
renders the mode inside its shared navigation and page shell. It reads the
accepted Task 034 historical artifacts through the existing internal Meridian
service and reads the shared latest successful Nansen observation.

## Internal Meridian Service

The persistent Windows service `OTG_staging_meridian_demo` remains available
on `127.0.0.1:8765` as an internal backend. It is not the public site root,
and Caddy does not route the staging host directly to it. The service is
managed through the existing OTG NSSM/system-management convention.

The runner loads `NANSEN_API_KEY` from the existing access-restricted,
untracked parser `.env` at service startup. No key is stored in Git or NSSM
arguments. The bounded live adapter has retries disabled. The service stores
the latest successful sanitized observation in a shared server-side state
file under ProgramData. Its single service process makes one initial request
when no recent successful cache exists, then refreshes hourly, no sooner than
60 minutes after the previous attempt. The hourly schedule stays at the UTC
minute and second established by that initial attempt; the adapter selects
only complete hourly buckets. A failed attempt records a sanitized error code
and leaves the last successful observation available. The OTG Analytics mode
only reads this cached snapshot; page loads, sessions, and chart interactions
do not make Nansen requests.

This section describes staging only. Production has its own application and
Nansen backend services; staging changes do not configure or update them.

The Nansen mode has no manual refresh control. The state file stores only the
sanitized successful observation, last attempt time, and sanitized failure
code; it never stores credentials or raw Nansen responses. The UI displays the
timestamp of the last successful observation below Market Takeaway. Cache
reads do not consume API calls. No public endpoint can force a refresh.
