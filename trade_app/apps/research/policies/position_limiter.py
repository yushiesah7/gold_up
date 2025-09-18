from __future__ import annotations

import pandas as pd


def limit_positions(
    entries: pd.Series,
    exits: pd.Series,
    *,
    max_positions: int = 1,
    exit_first: bool = True,
) -> pd.Series:
    """
    entries/exits(True/False)から、同時保有数 <= max_positions を満たすよう entries をゲート。
    - exit_first=True: 同一バーで entry & exit が同時に立っている時、先に exit を処理して枠を空ける
    """
    if max_positions is None or max_positions <= 0:
        # 0以下なら新規不可
        return pd.Series(False, index=entries.index)

    entries = entries.fillna(False).astype(bool)
    exits = exits.fillna(False).astype(bool)

    open_pos = 0
    gated: list[bool] = []
    for t in entries.index:
        e_out = bool(exits.loc[t])
        e_in = bool(entries.loc[t])

        if exit_first and e_out and open_pos > 0:
            open_pos -= 1

        allow = False
        if e_in and open_pos < max_positions:
            allow = True
            open_pos += 1

        if not exit_first and e_out and open_pos > 0:
            open_pos -= 1

        gated.append(allow)

    return pd.Series(gated, index=entries.index, dtype=bool)
