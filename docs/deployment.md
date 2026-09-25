# Deployment

Development and test validation must precede any production consideration.
The reviewed `nansen` schema is applied to `server_otg_staging` only.

## Meridian Staging Integration

The public staging application is the existing OTG Analytics Streamlit site at
`https://otgostest.run.place/`. Caddy terminates HTTPS and routes the staging
host to the site's loopback application on `127.0.0.1:8504`.

Nansen is an additional native OTG Analytics mode at `/?mode=nansen`. The site
renders the mode inside its shared navigation and page shell. It reads the
accepted Task 034 historical artifacts through the existing internal Meridian
service and requests live Nansen data only after an explicit refresh.

## Internal Meridian Service

The persistent Windows service `OTG_staging_meridian_demo` remains available
on `127.0.0.1:8765` as an internal backend. It is not the public site root,
and Caddy does not route the staging host directly to it. The service is
managed through the existing OTG NSSM/system-management convention.

The runner loads `NANSEN_API_KEY` from the existing access-restricted,
untracked parser `.env` at service startup. No key is stored in Git or NSSM
arguments. The service makes no Nansen request at startup, retries are
disabled for its bounded live adapter, and the sanitized live result is cached
for at least 60 seconds. The OTG Analytics mode calls the private service only
when the user selects Refresh Live Data.

Production `https://otgos.run.place/` and its application service are outside
this staging route. Do not change its Caddy block or application service while
maintaining the Meridian staging integration.
