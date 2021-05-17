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

import zoo.zouwu.preprocessing.impute.impute as zouwu_impute
from zoo.zouwu.data.utils import *

class TSDataset:
    def __init__(self, df,
                 id_col,
                 datetime_col,
                 target_col,
                 extra_feature_col=None):
        '''
        TSDataset is an abstract of time series dataset.
        :param df: a pandas dataframe for your raw time series data.
        :param id_col: a str indicates the col name of dataframe id.
        :param datetime_col: a str indicates the col name of datetime 
               column in the input data frame.
        :param target_col: a str indicates the col name of target column
               in the input data frame.
        :param extra_feature_col: (optional) a str indicates the col name
               of extra feature columns that needs to predict the target column.
        Here is an df example:
        id        datetime      value   "extra feature 1"   "extra feature 2"
        00        2019-01-01    1.9     1                   2
        01        2019-01-01    2.3     0                   2
        00        2019-01-02    2.4     3                   2
        01        2019-01-02    2.6     0                   2
        `tsdataset = TSDataset(df,
                               datetime_col="datetime",
                               target_col="value",
                               id_col="id",
                               extra_feature_col=["extra feature 1",""extra feature 2])`
        TODO: infer `id_col` automatically if not input.
        TODO: check if datetime col is sorted.
        TODO: check if each sub dataframe divided by id col have the same length.
        TODO: respect the original order of `id_col`
        '''
        # input items
        self.df = df
        self.id_col = id_col
        self.datetime_col = datetime_col
        self.target_col = to_list(target_col, name="target_col")
        self.feature_col = to_list(extra_feature_col, name="extra_feature_col")

        # check and clean input
        self._check_input()
        self._id_bag = list(np.unique(self.df[self.id_col]))
        self._clean_input()

        # other internal variables
        self._numpy_x = None
        self._numpy_y = None

    def _clean_input(self):
        '''
        Clean the input by changing some of the dataset
        '''
        # check datetime col
        self.df = check_datetime(self.df, self.datetime_col)
        # check uniform
        self._interval = [check_uniform(self.df[self.df[self.id_col]==id_name], 
                                        self.datetime_col)
                          for id_name in self._id_bag][0]

    def _check_input(self):
        '''
        Check the input without changing anything 
        '''
        # check type
        check_type(self.df, "df", pd.DataFrame)
        check_type(self.id_col, "id_col", str)
        check_type(self.datetime_col, "datetime_col", str)
        check_type(self.target_col, "target_col", list)
        check_type(self.feature_col, "feature_col", list)
        # check valid name
        check_col_within(self.df, self.id_col)
        check_col_within(self.df, self.datetime_col)
        for target_col_name in self.target_col:
            check_col_within(self.df, target_col_name)
        for feature_col_name in self.feature_col:
            check_col_within(self.df, feature_col_name)

    def to_numpy(self):
        # TODO: will be implemented after implementing rolling
        raise NotImplementedError("This method has not been implemented!")
    
    def to_pandas(self):
        return self.df
    
    def get_feature_list(self):
        return self.feature_col
    
    def _impute_per_df(self, df):
        return self._imputer.impute(df)

    def impute(self, mode="LastFillImpute", reindex=False):
        if reindex:
            self.df = [reindex_dataframe(self.df[self.df[self.id_col]==id_name], 
                                         self.datetime_col)
                          for id_name in self._id_bag]
        self._imputer = getattr(zouwu_impute, mode)()
        self.df = pd.concat([self._impute_per_df(self.df[self.df[self.id_col]==id_name]) 
                             for id_name in self._id_bag])
        return self
