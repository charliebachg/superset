# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from typing import Any

from pandas import DataFrame, to_numeric
from pandas.api.types import is_object_dtype, is_string_dtype

from superset.utils.pandas_postprocessing.utils import (
    _get_aggregate_funcs,
    validate_column_args,
)


def _coerce_numeric_text_columns(
    df: DataFrame, aggregates: dict[str, dict[str, Any]]
) -> DataFrame:
    """
    Parse aggregated columns that hold numbers as text into numbers.

    A column of numeric strings is held as ``str`` rather than ``object`` from
    pandas 3 on, and numeric reductions over ``str`` raise. Columns whose text
    does not parse as a number are left alone, so an aggregation over genuine
    text still fails as it did before.
    """
    coerced = {}
    for aggregate_options in aggregates.values():
        column = aggregate_options.get("column")
        if column is None or column in coerced or column not in df.columns:
            continue
        series = df[column]
        if is_object_dtype(series) or not is_string_dtype(series):
            continue
        numeric_series = to_numeric(series, errors="coerce")
        if numeric_series.notna().equals(series.notna()):
            coerced[column] = numeric_series

    if not coerced:
        return df

    df = df.copy()
    for column, numeric_series in coerced.items():
        df[column] = numeric_series
    return df


@validate_column_args("groupby")
def aggregate(
    df: DataFrame, groupby: list[str], aggregates: dict[str, dict[str, Any]]
) -> DataFrame:
    """
    Apply aggregations to a DataFrame.

    :param df: Object to aggregate.
    :param groupby: columns to aggregate
    :param aggregates: A mapping from metric column to the function used to
           aggregate values.
    :raises InvalidPostProcessingError: If the request in incorrect
    """
    aggregates = aggregates or {}
    aggregate_funcs = _get_aggregate_funcs(df, aggregates)
    df = _coerce_numeric_text_columns(df, aggregates)
    if groupby:
        df_groupby = df.groupby(by=groupby)
    else:
        df_groupby = df.groupby(lambda _: True)
    return df_groupby.agg(**aggregate_funcs).reset_index(drop=not groupby)
