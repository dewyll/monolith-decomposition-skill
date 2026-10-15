# Common domain candidates

Signals are hints, not verdicts. Each candidate needs a decision with the user: **consolidate** (into a shared component or a future shared service/library), **keep separate** (looks alike but serves different domains), or **not common**.

Fan-in signal: on

| Component | Signals | % | Why |
|---|---|---:|---|
| `shopco.audit` | fan-in, keyword | 5.75 | name matches shared-concern keyword(s): audit; used by 4 components (threshold 3) |
| `shopco.notification` | duplicate, keyword | 4.6 | name matches shared-concern keyword(s): notification; same leaf name as shopco.orders.notification |
| `shopco.orders.notification` | duplicate, keyword | 4.6 | name matches shared-concern keyword(s): notification; same leaf name as shopco.notification |
| `shopco.orders` | fan-in | 29.89 | used by 3 components (threshold 3) |
| `shopco.reporting` | keyword | 11.49 | name matches shared-concern keyword(s): reporting |

## Possible duplicated capabilities

- **notification**: `shopco.notification`, `shopco.orders.notification`
