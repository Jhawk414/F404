"""Column-by-column comparison of two cycle decks.

The yardstick for spikes and PR proof: run a sweep on two versions of the
model, then compare the decks. Rows are matched on (alt, dTs, throttle), where
throttle is T4 in a dry deck and T7 in a wet deck, each rounded to 1 degR, so
a solve that lands within tolerance of its target still matches.
"""
import numpy as np
import pandas as pd

# A base value this close to zero is compared in absolute terms: a % change
# against a solved FAR_ab of ~1e-18 is meaningless.
NEAR_ZERO = 1e-9
_KEY = ['alt', 'dTs', 'throttle']


def read_deck(path):
    """Read a deck CSV with every float exactly as written.

    pandas' default parser can land one ULP off, which would make two
    distinct float64 values compare equal and break "0 means bit-identical".
    """
    return pd.read_csv(path, float_precision='round_trip')


def _keyed(df):
    wet = df['mode'].eq('wet').all() if 'mode' in df else df['FAR_ab'].max() > 1e-6
    out = df.copy()
    out['throttle'] = out['T7' if wet else 'T4']
    for col in _KEY:
        out[col] = out[col].round().astype(int)
    return out.set_index(_KEY).sort_index()


def compare_decks(base, new, columns=None):
    """Compare ``new`` against ``base``.

    Parameters
    ----------
    base, new : pandas.DataFrame
        Decks as read from CSV.
    columns : iterable of str, optional
        Restrict the comparison to these columns.

    Returns
    -------
    (pandas.DataFrame, list, list)
        One row per shared numeric column: ``kind`` ('%' or 'abs'), ``min``,
        ``max``, ``max_abs`` and ``worst`` (the (alt, dTs, throttle) of
        ``max_abs``), in base column order. Then the keys only in base, and
        the keys only in new.
    """
    b, n = _keyed(base), _keyed(new)
    common = b.index.intersection(n.index)
    only_base = b.index.difference(n.index).tolist()
    only_new = n.index.difference(b.index).tolist()
    b, n = b.loc[common], n.loc[common]

    rows = []
    for col in b.columns:
        if (col not in n.columns or col == 'MN'
                or not pd.api.types.is_numeric_dtype(b[col])
                or (columns is not None and col not in columns)):
            continue
        bv, nv = b[col].to_numpy(float), n[col].to_numpy(float)
        near_zero = np.abs(bv) < NEAR_ZERO
        if near_zero.all():
            kind, diff = 'abs', nv - bv
        else:
            kind = '%'
            with np.errstate(divide='ignore', invalid='ignore'):
                diff = np.where(near_zero, np.nan, 100. * (nv - bv) / bv)
        if np.isnan(diff).all():
            continue
        i = int(np.nanargmax(np.abs(diff)))
        rows.append({'column': col, 'kind': kind,
                     'min': np.nanmin(diff), 'max': np.nanmax(diff),
                     'max_abs': abs(diff[i]),
                     'worst': tuple(int(v) for v in common[i])})
    table = pd.DataFrame(rows, columns=['column', 'kind', 'min', 'max', 'max_abs', 'worst'])
    return table, [tuple(map(int, k)) for k in only_base], [tuple(map(int, k)) for k in only_new]


def format_report(table, only_base, only_new, n_base, n_new, changed_only=False):
    """Render a comparison as a markdown report."""
    matched = n_base - len(only_base)
    lines = [f'base {n_base} rows, new {n_new} rows, matched {matched}']
    if only_base:
        lines.append(f'only in base (alt, dTs, throttle): {only_base}')
    if only_new:
        lines.append(f'only in new (alt, dTs, throttle): {only_new}')
    if changed_only:
        table = table[table['max_abs'] > 0]
    lines += ['', '| column | min | max | max abs | worst (alt, dTs, throttle) |',
              '|---|---|---|---|---|']
    for r in table.itertuples():
        unit = ' %' if r.kind == '%' else ' (abs)'
        lines.append(f'| {r.column}{unit} | {r.min:+.3g} | {r.max:+.3g} | '
                     f'{r.max_abs:.3g} | {r.worst} |')
    return '\n'.join(lines)
