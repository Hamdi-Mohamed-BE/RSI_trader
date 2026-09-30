"""Audit-only harness amendment, leaving original frozen runner and raw EA unchanged."""
import pipeline
import extended_audit
pipeline.audit=extended_audit
pipeline.save(pipeline.ROOT/'AUDIT_AMENDMENT.json',dict(reason='Model 1 FX conversion can differ from execution price; retain exact report/deal net reconciliation and log conversion approximation differences. No signal, gate, parameter, deal or timing changes.',audit_sha=pipeline.h.sha(pipeline.ROOT/'extended_audit.py'),wrapper_sha=pipeline.h.sha(pipeline.ROOT/'continue_pipeline.py')))
pipeline.main()
