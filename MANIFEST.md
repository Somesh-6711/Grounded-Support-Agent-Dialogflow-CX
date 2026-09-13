# Screenshot manifest

Drop each image here with EXACTLY these filenames. The README references them
by path — a name mismatch renders as a broken image.

| Filename | What to capture | Where |
|---|---|---|
| `01-tools-list.png` | Both tools listed: `customer_service_tool` and `search_support_kb` | Conversational Agents → Tools |
| `02-openapi-tool.png` | Schema pane scrolled so the `servers:` URL is visible | Tools → `customer_service_tool` |
| `03-datastore-documents.png` | 3 documents, success state | Tools → `search_support_kb` → linked data store |
| `04-playbook.png` | Goal + instructions + attached tools. Scroll so the `MUST call search_support_kb` line shows | Playbooks → your playbook |
| `05-outage-tool-trace.png` | The two chained tool calls and the outage answer | Simulator |
| `06a-forced-409.png` | The curl returning `confirmation_required` | Cloud Shell |
| `06b-confirmed-booking.png` | `schedule_technician` trace expanded showing `confirm: true`, plus the `APT-` number | Simulator |
| `07-datastore-citation.png` | The $120 modem fee answer with `search_support_kb` in the trace | Simulator |
| `08-cloud-run.png` | Service page with revision name and Metrics tab | Cloud console → Cloud Run |
| `09-stats.png` | The `/stats` JSON | Browser |
| `10a-before-no-retrieval.png` | Troubleshooting answer with NO `search_support_kb` call — the 30-second modem advice | Simulator (pre-fix) |
| `10b-after-retrieval.png` | Same question, now WITH the retrieval call and correct steps | Simulator (post-fix) |

## Capture notes

- Expand tool-call traces before shooting. The chat bubbles show it said
  something plausible; the trace shows it called the right tool with the right
  arguments. The trace is the evidence.
- Crop to the relevant panel. Full-desktop screenshots with browser chrome and
  taskbar read as careless.
- PNG, not JPG. Screenshots of text compress badly as JPG.
- `05`, `10a` and `10b` are the three that carry the README's argument. If time
  is short, get those right and treat the rest as filler.
