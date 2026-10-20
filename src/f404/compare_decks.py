"""Column-by-column comparison of two cycle decks.

The yardstick for spikes and PR proof: run a sweep on two versions of the
model, then compare the decks. Rows are matched on what was asked of each
point, ``_KEY``, so failed points match too and convergence changes are
reported alongside the value changes.
"""
import numpy as np
import pandas as pd

# A base value this close to zero is compared in absolute terms: a % change
# against a solved FAR_ab of ~1e-18 is meaningless. A column can have both
# kinds of point, and then gets one row of each.
NEAR_ZERO = 1e-9
_KEY = ['mode', 'alt', 'dTs', 'MN', 'T4_cmd', 'T7_cmd']
# Point lists in the report; 'failed in both' is only counted.
POINT_LISTS = ['only in base', 'only in new', 'converged only in base',
               'converged only in new', 'failed in both']


def read_deck(path):
    """Read a deck CSV with every float exactly as written.

    pandas' default parser can land one ULP off, which would make two
    distinct float64 values compare equal and break "0 means bit-identical".
    """
    return pd.read_csv(path, float_precision='round_trip')


def _with_inputs(df):
    """Give a deck written before #27 its input columns.

    Those decks hold converged rows only and no commands, so the commands
    are taken from the solved T4 and T7, which ``_keyed`` matches to 1 R.
    """
    if 'T4_cmd' in df:
        return df
    return df.assign(converged=True, T4_cmd=df['T4'],
                     T7_cmd=df['T7'].where(df['mode'] == 'wet', 0.))


def _keyed(df, label):
    """Index a deck by ``_KEY``.

    alt, dTs and MN are matched at 1e-6, so a fractional grid stays distinct.
    The commands are matched to 1 R, which also lets a pre-#27 deck's solved
    temperatures stand in for them. A throttle grid finer than that collapses
    two points onto one key, which is an error, not a silent pairing.
    """
    out = _with_inputs(df)
    out = out.assign(**{c: out[c].round(6) for c in ('alt', 'dTs', 'MN')},
                     **{c: out[c].round() for c in ('T4_cmd', 'T7_cmd')})
    dup = out.duplicated(_KEY, keep=False)
    if dup.any():
        keys = sorted({_point(k) for k in out.loc[dup, _KEY].itertuples(index=False)})
        raise ValueError(f"{label} deck has more than one row at {tuple(_KEY)} "
                         f"{keys}; the commands are matched to 1 R")
    return out.set_index(_KEY).sort_index()


def _summary(column, kind, diff, keys):
    i = int(np.argmax(np.abs(diff)))
    return {'column': column, 'kind': kind, 'min': diff.min(), 'max': diff.max(),
            'max_abs': abs(diff[i]), 'worst': _point(keys[i])}


def _point(key):
    """A key as plain values: ints where integral, for readable output."""
    return tuple(v if isinstance(v, str) else int(v) if float(v).is_integer()
                 else float(v) for v in key)


def compare_decks(base, new, columns=None):
    """Compare ``new`` against ``base``.

    Parameters
    ----------
    base, new : pandas.DataFrame
        Decks as read from CSV.
    columns : iterable of str, optional
        Compare only these columns, each of which must be numeric in both
        decks. By default every shared numeric output column is compared, so
        decks with older, narrower schemas still compare.

    Raises
    ------
    ValueError
        If a requested column is missing from either deck, or a deck has two
        rows on one ``_KEY``.

    Returns
    -------
    (pandas.DataFrame, dict)
        One row per compared column and kind, over the points converged in
        both decks: ``kind`` is '%' over points with a non-zero base and
        'abs' over points whose base is ~0. Then ``min``, ``max``,
        ``max_abs`` and ``worst`` (the key of ``max_abs``), in base column
        order. A column with blank or non-finite values also gets an
        'invalid' row: ``max_abs`` is the number of such points and ``worst``
        the first. Then the keys of each of ``POINT_LISTS``.
    """
    if columns is not None:
        columns = list(columns)
        for label, df in (('BASE', base), ('NEW', new)):
            missing = [c for c in columns
                       if c not in df or not pd.api.types.is_numeric_dtype(df[c])]
            if missing:
                raise ValueError(f"{label} deck has no numeric column {missing}")
    b, n = _keyed(base, 'BASE'), _keyed(new, 'NEW')
    common = b.index.intersection(n.index)
    b_ok = b.loc[common, 'converged'].to_numpy(bool)
    n_ok = n.loc[common, 'converged'].to_numpy(bool)
    groups = [b.index.difference(n.index), n.index.difference(b.index),
              common[b_ok & ~n_ok], common[~b_ok & n_ok], common[~b_ok & ~n_ok]]
    points = {name: [_point(k) for k in keys] for name, keys in zip(POINT_LISTS, groups)}
    both = common[b_ok & n_ok]
    b, n = b.loc[both], n.loc[both]

    rows = []
    for col in b.columns:
        if columns is not None:
            if col not in columns:
                continue
        elif (col not in n.columns or col in ('converged', 'failure')
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
                rows.append(_summary(col, kind, diff[mask], both[mask]))
        if not finite.all():
            rows.append({'column': col, 'kind': 'invalid', 'min': np.nan,
                         'max': np.nan, 'max_abs': float((~finite).sum()),
                         'worst': _point(both[~finite][0])})
    table = pd.DataFrame(rows, columns=['column', 'kind', 'min', 'max', 'max_abs', 'worst'])
    return table, points


def format_report(table, points, n_base, n_new, changed_only=False):
    """Render a comparison as a markdown report."""
    key = ', '.join(_KEY)
    n_matched = n_base - len(points['only in base'])
    n_both = n_matched - sum(len(points[k]) for k in POINT_LISTS[2:])
    lines = [f'base {n_base} rows, new {n_new} rows, matched {n_matched}, '
             f'converged in both {n_both}']
    for name in POINT_LISTS[:-1]:
        if points[name]:
            lines.append(f'{name} ({key}): {points[name]}')
    if points['failed in both']:
        lines.append(f"failed in both: {len(points['failed in both'])}")
    if changed_only:
        table = table[table['max_abs'] > 0]
    lines += ['', f'| column | min | max | max abs | worst ({key}) |',
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
