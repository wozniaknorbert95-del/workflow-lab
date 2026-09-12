# PRODUCT.md — workflow-lab

One page.

## Job to be done

Commander can take an idea from a phone-sized issue to a **green MR** without opening `dsaas-platform-main`.

## User

Only the Commander (and agents working *this* repo). Not QuietForge tenants. Not Kokpit.

## Success

- First manual MR merged after green CI.
- Later: Cloud Agent can open an MR that CI accepts.
- Cost of a run is visible in Cursor usage; recorded when we care (`DECISIONS.md`).

## Non-goals

- Features for paying customers.
- A seventh Kokpit department.
- Replacing Linear as the long-term “CO” (see `docs/LINEAR.md`).
- Deploying the DSaaS platform.
