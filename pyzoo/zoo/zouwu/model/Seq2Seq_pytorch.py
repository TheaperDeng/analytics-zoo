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

import torch
import torch.nn as nn

from zoo.automl.model.base_pytorch_model import PytorchBaseModel, \
    PYTORCH_REGRESSION_LOSS_MAP
import numpy as np


class LSTMSeq2Seq(nn.Module):
    def __init__(self,
                 input_feature_num,
                 future_seq_len,
                 output_feature_num,
                 lstm_hidden_dim=128,
                 lstm_layer_num=2,
                 dropout=0.25,
                 teacher_forcing=False):
        super(LSTMSeq2Seq, self).__init__()
        self.lstm_encoder = nn.LSTM(input_size=input_feature_num,
                                    hidden_size=lstm_hidden_dim,
                                    num_layers=lstm_layer_num,
                                    dropout=dropout,
                                    batch_first=True)
        self.lstm_decoder = nn.LSTM(input_size=input_feature_num,
                                    hidden_size=lstm_hidden_dim,
                                    num_layers=lstm_layer_num,
                                    dropout=dropout,
                                    batch_first=True)
        self.fc = nn.Linear(in_features=lstm_hidden_dim, out_features=output_feature_num)
        self.future_seq_len = future_seq_len
        self.output_feature_num = output_feature_num
        self.teacher_forcing = teacher_forcing

    def forward(self, input_seq, target_seq=None):
        x, (hidden, cell) = self.lstm_encoder(input_seq)
        decoder_input = input_seq[:, -1, :] # last value
        decoder_input = decoder_input.unsqueeze(1)

        decoder_output = torch.zeros(input_seq.shape[0], self.future_seq_len, self.output_feature_num)
        for i in range(self.future_seq_len):
            decoder_output_step, (hidden, cell) = self.lstm_decoder(decoder_input, (hidden, cell))
            out_step = self.fc(decoder_output_step)
            decoder_output[:,i:i+1,:] = out_step
            if not self.teacher_forcing:
                # no teaching force
                decoder_input = out_step
            else:
                # with teaching force
                decoder_input = target_seq[:, i:i+1, :]
        return decoder_output


def model_creator(config):
    return LSTMSeq2Seq(input_feature_num=config["input_feature_num"],
                       output_feature_num=config["output_feature_num"],
                       future_seq_len=config["future_seq_len"],
                       lstm_hidden_dim=config.get("lstm_hidden_dim", 128),
                       lstm_layer_num=config.get("lstm_layer_num", 2),
                       dropout=config.get("dropout", 0.25),
                       teacher_forcing=config.get("teacher_forcing", False))


def optimizer_creator(model, config):
    return getattr(torch.optim, config.get("optim", "Adam"))(model.parameters(),
                                                             lr=config.get("lr", 4e-3))


def loss_creator(config):
    loss_name = config.get("loss", "mse")
    if loss_name in PYTORCH_REGRESSION_LOSS_MAP:
        loss_name = PYTORCH_REGRESSION_LOSS_MAP[loss_name]
    else:
        raise RuntimeError(f"Got \"{loss_name}\" for loss name,\
                           where \"mse\", \"mae\" or \"huber_loss\" is expected")
    return getattr(torch.nn, loss_name)()


class Seq2SeqPytorch(PytorchBaseModel):
    def __init__(self, check_optional_config=False):
        super().__init__(model_creator=model_creator,
                         optimizer_creator=optimizer_creator,
                         loss_creator=loss_creator,
                         check_optional_config=check_optional_config)
    
    def _forward(self, x, y):
        return self.model(x, y)

    def _get_required_parameters(self):
        return {
            "input_feature_num",
            "future_seq_len",
            "output_feature_num"
        }

    def _get_optional_parameters(self):
        return {
            "lstm_hidden_dim",
            "lstm_layer_num"
        } | super()._get_optional_parameters()
