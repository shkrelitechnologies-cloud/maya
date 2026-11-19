# Publishing adapter contract

Maya's publisher is deliberately fail-closed. This folder defines the minimum
contract and evidence gate for future site-specific adapters.

- `permission_gate.py`: validates current, evidence-backed permission rows.
- `adapters/`: one dedicated adapter per approved website (none installed).
- `README.md`: implementation and operating requirements.

No site may be contacted until its current official rules or written
authorization explicitly allow the intended automated fundraising method.
