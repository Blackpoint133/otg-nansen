# Deployment

Development and test validation must precede any production consideration.
The reviewed `nansen` schema is applied to `server_otg_staging` only. No
production schema or application deployment exists. The owner-approved CREATE
privilege for `gunz_user` is intentionally persistent on staging only and does
not grant privileges on `server_otg`.
