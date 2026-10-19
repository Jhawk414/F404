"""Column-by-column comparison of two cycle decks.

The yardstick for spikes and PR proof: run a sweep on two versions of the
model, then compare the decks. Rows are matched on (alt, dTs, throttle), where
throttle is T4 in a dry deck and T7 in a wet deck (see ``_keyed``).
"""
import numpy as np
import pandas as pd

# A base value this close to zero is compared in absolute terms: a % change
# against a solved FAR_ab of ~1e-18 is meaningless. A column can have both
# kinds of point, and then gets one row of each.
NEAR_ZERO = 1e-9
_KEY = ['alt', 'dTs', 'throttle']


def read_deck(path):
    """Read a deck CSV with every float exactly as written.

    pandas' default parser can land one ULP off, which would make two
    distinct float64 values compare equal and break "0 means bit-identical".
    """
    return pd.read_csv(path, float_precision='round_trip')


def _mode(df, label):
    """The one mode a deck holds: from its ``mode`` column, else from FAR_ab."""
    if 'mode' in df:
        modes = sorted(df['mode'].dropna().unique())
        if len(modes) != 1:
            raise ValueError(f"{label} deck holds modes {modes}; compare one mode "
                             f"at a time (cycle_deck_dry.csv or cycle_deck_wet.csv)")
        return modes[0]
    return 'wet' if df['FAR_ab'].max() > 1e-6 else 'dry'


def _keyed(df, mode, label):
    """Index a deck by (alt, dTs, throttle).

    alt and dTs are sweep inputs, so they are matched at 1e-6 and a fractional
    grid stays distinct. The throttle is a solved T4 or T7 that can land a few
    thousandths of a degree off its target, so it is matched to 1 R. A grid
    finer than that collapses two points onto one key, which is an error, not
    a silent pairing.
    """
    out = df.copy()
    out['throttle'] = out['T7' if mode == 'wet' else 'T4'].round()
    out['alt'] = out['alt'].round(6)
    out['dTs'] = out['dTs'].round(6)
    dup = out.duplicated(_KEY, keep=False)
    if dup.any():
        keys = sorted({_point(k) for k in out.loc[dup, _KEY].itertuples(index=False)})
        raise ValueError(f"{label} deck has more than one row at (alt, dTs, throttle) "
                         f"{keys}; throttle is matched to 1 R")
    return out.set_index(_KEY).sort_index()


def _summary(column, kind, diff, keys):
    i = int(np.argmax(np.abs(diff)))
    return {'column': column, 'kind': kind, 'min': diff.min(), 'max': diff.max(),
            'max_abs': abs(diff[i]), 'worst': _point(keys[i])}


def _point(key):
    """A key as plain numbers: ints where integral, for readable output."""
    return tuple(int(v) if float(v).is_integer() else float(v) for v in key)


def compare_decks(base, new, columns=None):
    """Compare ``new`` against ``base``.

    Parameters
    ----------
    base, new : pandas.DataFrame
        Decks as read from CSV.
    columns : iterable of str, optional
        Compare only these columns, each of which must be numeric in both
        decks. By default every shared numeric column but MN is compared, so
        decks with older, narrower schemas still compare.

    Raises
    ------
    ValueError
        If a requested column is missing from either deck, either deck mixes
        modes, the two decks are different modes, or a
        deck has two rows on one (alt, dTs, throttle) key.

    Returns
    -------
    (pandas.DataFrame, list, list)
        One row per compared column and kind: ``kind`` is '%' over points
        with a non-zero base and 'abs' over points whose base is ~0. Then
        ``min``, ``max``, ``max_abs`` and ``worst`` (the (alt, dTs, throttle)
        of ``max_abs``), in base column order. A column with blank or
        non-finite values in either deck also gets an 'invalid' row:
        ``max_abs`` is the number of such points and ``worst`` the first. Then the keys only in base, and
        the keys only in new.
    """
    mode = _mode(base, 'BASE')
    if _mode(new, 'NEW') != mode:
        raise ValueError(f"BASE is a {mode} deck and NEW is a {_mode(new, 'NEW')} "
                         f"deck; their throttles (T4 vs T7) are different points")
    if columns is not None:
        columns = list(columns)
        for label, df in (('BASE', base), ('NEW', new)):
            missing = [c for c in columns
                       if c not in df or not pd.api.types.is_numeric_dtype(df[c])]
            if missing:
                raise ValueError(f"{label} deck has no numeric column {missing}")
    b, n = _keyed(base, mode, 'BASE'), _keyed(new, mode, 'NEW')
    common = b.index.intersection(n.index)
    only_base = b.index.difference(n.index).tolist()
    only_new = n.index.difference(b.index).tolist()
    b, n = b.loc[common], n.loc[common]

    rows = []
    for col in b.columns:
        if columns is not None:
            if col not in columns:
                continue
        elif (col not in n.columns or col == 'MN'
                or not pd.api.types.is_numeric_dtype(b[col])):
            continue
        bv, nv = b[col].to_numpy(float), n[col].to_numpy(float)
        # Points whose base is ~0 get their own absolute row, so a column that
        # is 0 at some points (dry ab_dPqP) never hides a change there.
        # A blank or non-finite cell is reported, never read as "no change".
        finite = np.isfinite(bv) & np.isfinite(nv)
        near_zero = np.abs(bv) < NEAR_ZERO
        with np.errstate(divide='ignore', invalid='ignore'):
            pct = 100. * (nv - bv) / bv
        for kind, mask, diff in (('%', finite & ~near_zero, pct),
                                 ('abs', finite & near_zero, nv - bv)):
            if mask.any():
                rows.append(_summary(col, kind, diff[mask], common[mask]))
        if not finite.all():
            rows.append({'column': col, 'kind': 'invalid', 'min': np.nan,
                         'max': np.nan, 'max_abs': float((~finite).sum()),
                         'worst': _point(common[~finite][0])})
    table = pd.DataFrame(rows, columns=['column', 'kind', 'min', 'max', 'max_abs', 'worst'])
    return table, [_point(k) for k in only_base], [_point(k) for k in only_new]


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
        if r.kind == 'invalid':
            lines.append(f'| {r.column} (invalid) | non-finite | in | '
                         f'{int(r.max_abs)} points | first {r.worst} |')
            continue
        unit = ' %' if r.kind == '%' else ' (abs)'
        lines.append(f'| {r.column}{unit} | {r.min:+.3g} | {r.max:+.3g} | '
                     f'{r.max_abs:.3g} | {r.worst} |')
    return '\n'.join(lines)
