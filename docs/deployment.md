# Deployment

Development and test validation must precede any production consideration.
The reviewed `nansen` schema is applied to `server_otg_staging` only. The
Meridian demo is an independent read-only web application; it does not connect
to PostgreSQL.

## Meridian Staging Web Service

The judge-facing demo is served only at `https://otgostest.run.place/`. Caddy
terminates HTTPS and proxies this host to a loopback-only Python service on
`127.0.0.1:8765`. The persistent Windows service is `OTG_staging_meridian_demo`
and is managed through the OTG NSSM/system-management convention. Its runner
loads `NANSEN_API_KEY` from the existing, access-restricted, untracked parser
`.env` at service startup; no key is stored in Git or NSSM arguments. The
application makes no request until an explicit refresh and caches that result
for at least 60 seconds. Production `otgos.run.place` and its application
service are outside this staging route.
