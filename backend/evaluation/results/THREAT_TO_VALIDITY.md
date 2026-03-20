# Threat-to-Validity Analysis

## Internal Validity

**Instrumentation**: Centralized MetricsEngine ensures consistent correctness computation.  
**Selection Bias**: Holdout stratified by category with fixed seed (42); residual: category labels coarse.  
**Confounding**: LLM changes affect baselines; mitigation: checkpoint system preserves responses.  

## External Validity

**Population**: 393 queries may not represent all legal queries; mitigation: designed across 7 categories.  
**Corpus**: ChromaDB specific to Indian law; may have gaps; mitigation: hand-curated active acts.  
**Temporal**: Evaluation March 2026; future laws missed; mitigation: dated for reproducibility.  

## Construct Validity

**OLR Definition**: "Outdated" = citing pre-BNS law on transition queries; risk: some IPC still valid precedent.  
**HR Definition**: "Hallucination" = unsupported by retrieval; risk: may miss sophisticated hallucinations.  
**CCS Definition**: Rank correlation between confidence & correctness; risk: may hide consistent overconfidence.  

## Statistical Validity

**Sample Size**: n=14 (BNS conditional); p-values marked "n/a"; threshold holdout 50 queries.  
**Multiple Comparisons**: 7 metrics × 3 systems; no correction (exploratory); bootstrap CI for robustness.  
**Assumption Violations**: t-tests assume normality; OLR may be bimodal; mitigation: bootstrap CI.  

## Conclusion Validity

**Reproducibility Cost**: Full re-run expensive (Groq quota); mitigation: checkpoint system.  
**Reporting**: All attrition counts included; no omission of failed ablations.  

## Summary

| Threat | Severity | Mitigation | Residual |
|---|---|---|---|
| Threshold overfitting | Medium | Separate holdout | Generalization risk |
| BNS statistics | High | n/a when n<20 | p-values unreliable |
| Metric definition | Medium | Centralized method | Possible bias |
| Corpus completeness | Medium | Hand-curated | Systematic gaps |
| Multiple comparisons | Low | Bootstrap CI | Family inflation |

## Recommendations

1. Increase holdout to 100+ queries
2. External validation on held-out corpus
3. Blind evaluation by independent annotators
4. Systematic error categorization
5. Report Brier score & ECE in addition to CCS
