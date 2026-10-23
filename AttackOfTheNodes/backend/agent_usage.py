"""Usage totals for one run. Missing/partial estimates never become zero bills."""


def usage_summary(receipts):
    known, missing, partial = [], 0, 0
    for receipt in receipts:
        cost = (receipt.get('usage') or {}).get('estimated_cost_usd')
        if cost is None:
            missing += 1
        else:
            known.append(cost)
        partial += bool(receipt.get('partial'))
    return {'estimated_cost_usd': sum(known) if known else None,
            'reported': len(known), 'not_reported': missing, 'partial': partial}
