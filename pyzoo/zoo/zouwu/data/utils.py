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

def _to_list(item, name, type=str):
    if isinstance(item, list):
        return item
    if item is None:
        return []
    check_type(item, name, type)
    return [item]

def _check_type(item, name, type):
    assert isinstance(item, type),\
        f"a {str(type)} is expected for {name} but found {type(item)}"

def _check_col_within(df, col_name):
    assert col_name in df.columns,\
        f"{col_name} is expected in dataframe while not found"

def _check_datetime(df, dt_col):
    # adapt from feature transformer _check_input func
    df = df.reset_index()
    dt = input_df[dt_col]
    if not np.issubdtype(dt, np.datetime64):
        raise ValueError("The dtype of datetime column is required to be np.datetime64!")
    is_nat = pd.isna(dt)
    if is_nat.any(axis=None):
        raise ValueError("Missing datetime in input dataframe!")
    return df

def _reindex_dataframe(df, dt_col):
    pass
