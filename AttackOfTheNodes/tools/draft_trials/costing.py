"""Cache accounting from SDK token receipts, using the adapter's pricing table."""


def cache_report(receipts, *, attempted_calls=None):
    from backend.integrations.claude import PRICES
    fields = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')
    tokens = {k: 0 for k in fields}
    actual, uncached = 0., 0.
    known = bool(receipts) and (attempted_calls is None or attempted_calls == len(receipts))
    for receipt in receipts:
        usage = receipt.get('usage') or {}
        values = [usage.get(k) for k in fields]
        valid = all(type(n) is int and n >= 0 for n in values)
        for key, value in zip(fields, values):
            if type(value) is int and value >= 0:
                tokens[key] += value
        cost = usage.get('estimated_cost_usd')
        rates = PRICES.get(usage.get('model'))
        if not valid or rates is None or cost is None:
            known = False
            continue
        inputs, outputs, reads, writes = values
        actual += cost
        uncached += ((inputs + reads + writes)*rates[0] + outputs*rates[1])/1_000_000
    return dict(setting='5 min', tokens=tokens, complete=known,
                estimated_cost_usd=actual if known else None,
                without_cache_estimated_cost_usd=uncached if known else None,
                estimated_savings_usd=uncached-actual if known else None,
                note='Actual SDK cache counts; savings may be negative during cache creation. Mock tokens do not measure inference.')


def estimate_all_runs(roots):
    """Conservative all-set projection from saved SDK counts, calibration once.

    No guessed character/token ratio or assumed cache hits. The next paid report
    measures the discount; generation lengths, prices and repairs can change.
    """
    import json
    from pathlib import Path
    from . import JUDGE_MODELS, JUDGE_EFFORTS
    cases, calibration, settings = {}, None, set()
    for root in map(Path, roots):
        report = json.loads((root/'report.json').read_text())
        settings.add((report.get('judge_model', JUDGE_MODELS[0]), report.get('judge_effort', JUDGE_EFFORTS[0])))
        sections = report.get('sets') or {str(report['case_set']): report}
        for n, section in sections.items():
            if n in cases:
                raise ValueError('Supply exactly one baseline per case set')
            wanted = set(range(1, 5 if n == '3' else 11))
            if {r['case'] for r in section['cases']} != wanted:
                raise ValueError('Cost projection needs every case in each set')
            cases[n] = [receipt for row in section['cases'] for receipt in row['usage']]
        # Last supplied run is the one calibration baseline; do not charge the
        # duplicates from the other two runs.
        calibration = json.loads((root/'calibration-report.json').read_text())
    if set(cases) != {'1', '2', '3'} or len(settings) != 1:
        raise ValueError('Cost projection needs all three sets with the same reviewer settings')
    judgments = [receipt for row in calibration['fixtures'] for receipt in row['usage']]
    receipts = judgments + [r for rows in cases.values() for r in rows]
    projection = cache_report(receipts)
    return dict(case_calls={n:len(rows) for n,rows in cases.items()}, calibration_calls=len(judgments),
                calls=len(receipts), tokens=projection['tokens'],
                estimated_cost_usd=projection['without_cache_estimated_cost_usd'],
                note='Historical SDK token counts, calibration once, no assumed cache hits. Extra repairs/generation lengths/prices may differ; actual cache savings appear in the paid calibration report.')


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=estimate_all_runs.__doc__)
    parser.add_argument('runs', nargs='+')
    print(json.dumps(estimate_all_runs(parser.parse_args().runs), indent=2))
