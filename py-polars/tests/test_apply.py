from functools import reduce
from typing import List, Optional

import polars as pl


def test_apply_none() -> None:
    df = pl.DataFrame(
        {
            "g": [1, 1, 1, 2, 2, 2, 5],
            "a": [2, 4, 5, 190, 1, 4, 1],
            "b": [1, 3, 2, 1, 43, 3, 1],
        }
    )

    out = (
        df.groupby("g", maintain_order=True).agg(
            pl.apply(
                exprs=["a", pl.col("b") ** 4, pl.col("a") / 4],
                f=lambda x: x[0] * x[1] + x[2].sum(),
            ).alias("multiple")
        )
    )["multiple"]
    assert out[0].to_list() == [4.75, 326.75, 82.75]
    assert out[1].to_list() == [238.75, 3418849.75, 372.75]

    out_df = df.select(pl.map(exprs=["a", "b"], f=lambda s: s[0] * s[1]))
    assert out_df["a"].to_list() == (df["a"] * df["b"]).to_list()

    # check if we can return None
    def func(s: List) -> Optional[int]:
        if s[0][0] == 190:
            return None
        else:
            return s[0]

    out = (
        df.groupby("g", maintain_order=True).agg(
            pl.apply(exprs=["a", pl.col("b") ** 4, pl.col("a") / 4], f=func).alias(
                "multiple"
            )
        )
    )["multiple"]
    assert out[1] is None


def test_apply_return_py_object() -> None:
    df = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    out = df.select([pl.all().map(lambda s: reduce(lambda a, b: a + b, s))])

    assert out.shape == (1, 2)


def test_agg_objects() -> None:
    df = pl.DataFrame(
        {
            "names": ["foo", "ham", "spam", "cheese", "egg", "foo"],
            "dates": ["1", "1", "2", "3", "3", "4"],
            "groups": ["A", "A", "B", "B", "B", "C"],
        }
    )

    out = df.groupby("groups").agg(
        [pl.apply([pl.col("dates"), pl.col("names")], lambda s: dict(zip(s[0], s[1])))]
    )
    assert out.dtypes == [pl.Utf8, pl.Object]


def test_apply_infer_list() -> None:
    df = pl.DataFrame(
        {
            "int": [1, 2],
            "str": ["a", "b"],
            "bool": [True, None],
        }
    )
    assert df.select([pl.all().apply(lambda x: [x])]).dtypes == [pl.List] * 3


def test_apply_arithmetic_consistency() -> None:
    df = pl.DataFrame({"A": ["a", "a"], "B": [2, 3]})
    assert df.groupby("A").agg(pl.col("B").apply(lambda x: x + 1.0))["B"].to_list() == [
        [3.0, 4.0]
    ]


def test_apply_struct() -> None:
    df = pl.DataFrame(
        {"A": ["a", "a"], "B": [2, 3], "C": [True, False], "D": [12.0, None]}
    )
    out = df.with_column(pl.struct(df.columns).alias("struct")).select(
        [
            pl.col("struct").apply(lambda x: x["A"]).alias("A_field"),
            pl.col("struct").apply(lambda x: x["B"]).alias("B_field"),
            pl.col("struct").apply(lambda x: x["C"]).alias("C_field"),
            pl.col("struct").apply(lambda x: x["D"]).alias("D_field"),
        ]
    )
    expected = pl.DataFrame(
        {
            "A_field": ["a", "a"],
            "B_field": [2, 3],
            "C_field": [True, False],
            "D_field": [12.0, None],
        }
    )

    assert out.frame_equal(expected)
