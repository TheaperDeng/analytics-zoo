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

from zoo.zouwu.model.forecast.abstract import Forecaster
from zoo.automl.model.tcn import TCNPytorch


class TCNForecaster(Forecaster):

    def __init__(self,
                 past_seq_len,
                 future_seq_len,
                 input_feature_num,
                 output_feature_num,
                 num_channels=[30]*8,
                 kernel_size=7,
                 dropout=0.2,
                 optimizer="Adam",
                 lr=0.001):
        self.internal = TCNPytorch(check_optional_config=False)
        self.data_config = {
            "past_seq_len": past_seq_len,
            "future_seq_len": future_seq_len,
            "input_feature_num": input_feature_num,
            "output_feature_num": output_feature_num
        }
        self.config = {
            "lr": lr,
            "num_channels": num_channels,
            "kernel_size": kernel_size,
            "optim": optimizer,
            "dropout": dropout
        }

    def fit(self, x, y, epochs=1, metric="mse", batch_size=32):
        self.config.setdefault("batch_size", batch_size)
        assert self.data_config["past_seq_len"] == x.shape[-2], \
            "The x input size should be (batch_size, past_seq_len, input_feature_num)."
        assert self.data_config["future_seq_len"] == y.shape[-2], \
            "The y input size should be (batch_size, future_seq_len, output_feature_num)."
        assert self.data_config["input_feature_num"] == x.shape[-1],\
            "The x input size should be (batch_size, past_seq_len, input_feature_num)."
        assert self.data_config["input_feature_num"] == y.shape[-1], \
            "The y input size should be (batch_size, future_seq_len, output_feature_num)."
        return self.internal.fit_eval(x,
                                      y,
                                      validation_data=(x, y),
                                      epochs=epochs,
                                      metric=metric,
                                      **self.config)

    def predict(self, x):
        if not self.internal.model_built:
            raise RuntimeError("You must call fit or restore first before calling predict!")
        return self.internal.predict(x)

    def evaluate(self, x, y, metric=['mse']):
        if not self.internal.model_built:
            raise RuntimeError("You must call fit or restore first before calling evaluate!")
        return self.internal.evaluate(x, y, metric=metric)

    def save(self, checkpoint_file):
        if not self.internal.model_built:
            raise RuntimeError("You must call fit or restore first before calling save!")
        self.internal.save(checkpoint_file)

    def restore(self, checkpoint_file):
        self.internal.restore(checkpoint_file)
