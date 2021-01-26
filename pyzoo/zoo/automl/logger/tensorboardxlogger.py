# Copyright 2018 Analytics Zoo Authors.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from ray.tune.utils import flatten_dict
import numpy as np
import os

from tensorboardX import SummaryWriter
from tensorboardX.summary import hparams

VALID_SUMMARY_TYPES = (int, float, np.float32, np.float64, np.int32)


class TensorboardXLogger():
    def __init__(self, logs_dir="", writer=None):
        '''
        Initialize a tensorboard logger

        Note that this logger relies on tensorboardx and only provide tensorboard hparams log.
        An ImportError will be raised for the lack of tensorboardx

        :param logs_dir: root directory for the log, default to the current working dir
        :param writer: shared tensorboardx SummaryWriter, default to None.
        '''
        self.logs_dir = logs_dir
        self._file_writer = None
        if writer:
            self._file_writer = writer
        else:
            self._file_writer = SummaryWriter(logdir=self.logs_dir)

    def run(self, config, metric):
        '''
        Write log files(event files)

        The log files is arranged as following:
        self.logs_dir
        |--eventfile_all
        |--Trail_1
        |  |--eventfile_1
        |--Trail_2
        |  |--eventfile_2
        ...
        :param config: A dictionary. Keys are trail name,
            value is a dictionary indicates the trail config
        :param metric: A dictionary. Keys are trail name,
            value is a dictionary indicates the trail metric results for each iteration

        Example:
        Config = {"run1":{"lr":0.001, "hidden_units": 32},
                  "run2":{"lr":0.01, "hidden_units": 64}}
        Metric = {"run1":{"acc":0.91, "time": 32.13},
                  "run2":{"acc":[0.93, 0.95], "time": [61.33, 62.44]}}

        Note that the keys of config and metric should be exactly the same
        '''
        # keys check
        assert config.keys() == metric.keys(),\
            "The keys of config and metric should be exactly the same"

        new_config = {}
        for key in config.keys():
            new_config[key] = {}
            for k, value in config[key].items():
                if value is not None:
                    new_config[key]['AutoTS/' + k] = value

        new_metric = {}
        for key in metric.keys():
            new_metric[key] = {}
            for k, value in metric[key].items():
                if type(value[-1]) in VALID_SUMMARY_TYPES and not np.isnan(value[-1]):
                    new_metric[key]['AutoTS/' + k] = value
                if k == "reward_metric":
                    new_config[key]['AutoTS/' + k + "(Use this to sort)"] = float(value[-1])

        # hparams log write
        for key in new_metric.keys():
            self._write_hparams(new_config[key], new_metric[key], name=key.replace("/", "_"))
    
    def _write_hparams(self, hparam_dict, metric_dict, name):
        # adapted from 
        exp, ssi, sei = hparams(hparam_dict, metric_dict)
        w_hp = SummaryWriter(logdir=os.path.join(self._file_writer.logdir, name))
        w_hp.file_writer.add_summary(exp)
        w_hp.file_writer.add_summary(ssi)
        w_hp.file_writer.add_summary(sei)
        for k, values in metric_dict.items():
            global_step = 0
            if not isinstance(values, list):
                values = [values]
            for v in values:
                w_hp.add_scalar(k, v, global_step)
                global_step += 1
        w_hp.close()

    def close(self):
        '''
        Close the logger
        '''
        self._file_writer.close()
