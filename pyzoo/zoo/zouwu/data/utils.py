#
# Copyright 2018 Analytics Zoo Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import pandas as pd
import numpy as np

import warnings

def to_list(item, name, type=str):
    if isinstance(item, list):
        return item
    if item is None:
        return []
    check_type(item, name, type)
    return [item]

def check_type(item, name, expect_type):
    assert isinstance(item, expect_type),\
        f"a {str(expect_type)} is expected for {name} but found {type(item)}"

def check_col_within(df, col_name):
    assert col_name in df.columns,\
        f"{col_name} is expected in dataframe while not found"

def check_datetime(df, dt_col):
    # adapt from feature transformer _check_input func
    df = df.reset_index()
    dt = df[dt_col]
    if not np.issubdtype(dt, np.datetime64):
        raise ValueError("The dtype of datetime column is required to be np.datetime64!")
    is_nat = pd.isna(dt)
    if is_nat.any(axis=None):
        raise ValueError("Missing datetime in input dataframe!")
    return df

def reindex_dataframe(df, dt_col, interval):
    raise NotImplementedError("_reindex_dataframe has not been implemented")

def check_uniform(df, dt_col):
    # adapt from feature transformer _check_input func
    dt = df[dt_col]
    interval = dt[1] - dt[0]
    if not all([dt[i] - dt[i - 1] == interval for i in range(1, len(dt))]):
        warnings.warn("Input time sequence intervals are not uniform!")
    return interval