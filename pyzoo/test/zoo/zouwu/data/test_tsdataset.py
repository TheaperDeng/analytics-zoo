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

import pytest
import numpy as np
import pandas as pd

from test.zoo.pipeline.utils.test_utils import ZooTestCase
from zoo.zouwu.data import TSDataset

def get_ts_df():
    sample_num = np.random.randint(100, 200)
    train_df = pd.DataFrame({"datetime": pd.date_range('1/1/2019', periods=sample_num),
                             "value": np.random.randn(sample_num),
                             "id": np.array(['00']*sample_num),
                             "extra feature": np.random.randn(sample_num)})
    return train_df

class TestImpute(ZooTestCase):
    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def test_tsdataset_initialization(self):
        df = get_ts_df()

        # legal input
        tsdata = TSDataset(df, id_col="id", datetime_col="datetime",
                           target_col="value", extra_feature_col=["extra feature"])
        tsdata = TSDataset(df, id_col="id", datetime_col="datetime",
                           target_col=["value"], extra_feature_col="extra feature")

        # illegal input
        with pytest.raises(AssertionError):
            tsdata = TSDataset(df, id_col=0, datetime_col="datetime",
                               target_col=["value"], extra_feature_col="extra feature")
        with pytest.raises(AssertionError):
            tsdata = TSDataset(df, id_col="id", datetime_col=0,
                               target_col=["value"], extra_feature_col="extra feature")
        with pytest.raises(AssertionError):
            tsdata = TSDataset(df, id_col="id", datetime_col="datetime",
                               target_col=0, extra_feature_col="extra feature")
        with pytest.raises(AssertionError):
            tsdata = TSDataset(0, id_col="id", datetime_col="datetime",
                               target_col=["value"], extra_feature_col="extra feature")
        
        # white-box test
        assert tsdata._id_bag == ['00']
        assert tsdata._interval == pd.Timedelta("1 days")

    def test_tsdataset_impute(self):
        df = get_ts_df()
        tsdata = TSDataset(df, id_col="id", datetime_col="datetime",
                           target_col="value", extra_feature_col=["extra feature"])
        tsdata.impute(mode="LastFillImpute", reindex=False)