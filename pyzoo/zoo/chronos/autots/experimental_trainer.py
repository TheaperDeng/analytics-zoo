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

from zoo.chronos.data import TSDataset
import zoo.orca.automl.hp as hp
from zoo.chronos.autots.model import AutoModelFactory

AUTOTS_DEFAULT_LOOKBACK = 5
AUTOTS_DEFAULT_HORIZON = 1


class AutoTSTrainer:
    """
    Automated Trainer.
    """

    def __init__(self,
                 model="lstm",
                 search_space=dict(),
                 metric="mse",
                 loss=None,
                 optimizer="Adam",
                 past_seq_len=None,
                 future_seq_len=None,
                 input_feature_num=None,
                 output_target_num=None,
                 selected_features="all",
                 backend="torch",
                 logs_dir="/tmp/autots_trainer",
                 cpus_per_trial=1,
                 name="autots_trainer"
                 ):
        """
        AutoTSTrainer trains a model for time series forecasting.
        User can choose one of the built-in models, or pass in a customized pytorch or keras model
        for tuning using AutoML.
        :param model: a string or a model creation function
            a string indicates a built-in model, currently "lstm", "tcn" are supported
        :param search_space: hyper parameter configurations. Some parameters are searchable and some
            are fixed parameters (such as input dimensions, etc.) Read the API docs for each auto model
        :param metric: String. The evaluation metric name to optimize. e.g. "mse"
        :param loss: String or pytorch/tf.keras loss instance or pytorch loss creator function.
        :param optimizer:
        :param past_seq_len:
        :param future_seq_len:
        :param input_feature_num:
        :param output_target_num:
        :param selected_features:
        :param backend: The backend of the lstm model. We only support backend as "torch" for now.
        :param logs_dir: Local directory to save logs and results. It defaults to "/tmp/auto_lstm"
        :param cpus_per_trial: Int. Number of cpus for each trial. It defaults to 1.
        :param name: name of the AutoLSTM. It defaults to "auto_lstm"
        :param preprocess: Whether to enable feature processing
        """
        # check backend and set default loss
        if backend != "torch":
            raise ValueError(f"We only support backend as torch. Got {backend}")
        else:
            import torch
            if loss is None:
                loss = torch.nn.MSELoss()

        # check 3rd party model
        import types
        if isinstance(model, types.FunctionType):
            self.model = model
            raise ValueError("3rd party model is not support for now")

        # update auto model common search space
        search_space.update({"past_seq_len": past_seq_len,
                             "future_seq_len": future_seq_len,
                             "input_feature_num": input_feature_num,
                             "output_target_num": output_target_num,
                             "loss": loss,
                             "metric": metric,
                             "optimizer": optimizer,
                             "backend": backend,
                             "logs_dir": logs_dir,
                             "cpus_per_trial": cpus_per_trial,
                             "name": name})

        # create auto model from name
        self.model = AutoModelFactory.create_auto_model(name=model,
                                                        search_space=search_space)

        # save selected features setting for data creator generation
        self.selected_features = selected_features

    def fit(self,
            data,
            epochs=1,
            batch_size=32,
            validation_data=None,
            metric_threshold=None,
            n_sampling=1,
            search_alg=None,
            search_alg_params=None,
            scheduler=None,
            scheduler_params=None
            ):
        """
        fit using AutoEstimator
        :param data: train data.
               For backend of "torch", data can be a TSDataset or a function that takes a
               config dictionary as parameter and returns a PyTorch DataLoader.
               For backend of "keras", data can be a TSDataset.
        :param epochs: Max number of epochs to train in each trial. Defaults to 1.
               If you have also set metric_threshold, a trial will stop if either it has been
               optimized to the metric_threshold or it has been trained for {epochs} epochs.
        :param batch_size: Int or hp sampling function from an integer space. Training batch size.
               It defaults to 32.
        :param validation_data: Validation data. Validation data type should be the same as data.
        :param metric_threshold: a trial will be terminated when metric threshold is met
        :param n_sampling: Number of times to sample from the search_space. Defaults to 1.
               If hp.grid_search is in search_space, the grid will be repeated n_sampling of times.
               If this is -1, (virtually) infinite samples are generated
               until a stopping condition is met.
        :param search_alg: str, all supported searcher provided by ray tune
               (i.e."variant_generator", "random", "ax", "dragonfly", "skopt",
               "hyperopt", "bayesopt", "bohb", "nevergrad", "optuna", "zoopt" and
               "sigopt")
        :param search_alg_params: extra parameters for searcher algorithm besides search_space,
               metric and searcher mode
        :param scheduler: str, all supported scheduler provided by ray tune
        :param scheduler_params: parameters for scheduler
        """
        # generate data creator from TSDataset (pytorch base require validation data)
        if isinstance(data, TSDataset) and isinstance(validation_data, TSDataset):
            train_d, val_d = self._prepare_data_creator(
                    search_space=self.model.search_space,
                    train_data=data,
                    val_data=validation_data,
            )
        else:
            train_d, val_d = data, validation_data

        self.model.fit(
            data=train_d,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=val_d,
            metric_threshold=metric_threshold,
            n_sampling=n_sampling,
            search_alg=search_alg,
            search_alg_params=search_alg_params,
            scheduler=scheduler,
            scheduler_params=scheduler_params
        )

    def _prepare_data_creator(self, search_space, train_data, val_data=None):
        """
        prepare the data creators and add selected features to search_space
        :param search_space: the search space
        :param train_data: train data
        :param val_data: validation data
        :return: data creators from train and validation data
        """
        import torch
        from torch.utils.data import TensorDataset, DataLoader
        import ray

        # append feature selection into search space
        all_features = train_data.feature_col
        if search_space.get('selected_features') is not None:
            raise ValueError("Do not specify ""selected_features"" in search space."
                             " The system will automatically generate this config for you")
        if self.selected_features == "auto":
            search_space['selected_features'] = hp.choice_n(all_features,
                                                            min_items=0,
                                                            max_items=len(all_features))
        if self.selected_features == "all":
            search_space['selected_features'] = all_features

        # put train/val data in ray
        train_data_id = ray.put(train_data)
        valid_data_id = ray.put(val_data)

        def train_data_creator(config):
            """
            train data creator function
            :param config:
            :return:
            """
            train_d = ray.get(train_data_id)

            x, y = train_d.roll(lookback=config.get('past_seq_len', AUTOTS_DEFAULT_LOOKBACK),
                                horizon=config.get('future_seq_len', AUTOTS_DEFAULT_HORIZON),
                                feature_col=config['selected_features']) \
                          .to_numpy()

            return DataLoader(TensorDataset(torch.from_numpy(x).float(),
                                            torch.from_numpy(y).float()),
                              batch_size=config["batch_size"],
                              shuffle=True)

        def val_data_creator(config):
            """
            train data creator function
            :param config:
            :return:
            """
            val_d = ray.get(valid_data_id)

            x, y = val_d.roll(lookback=config.get('past_seq_len', AUTOTS_DEFAULT_LOOKBACK),
                                 horizon=config.get('future_seq_len', AUTOTS_DEFAULT_HORIZON),
                                 feature_col=config['selected_features']) \
                        .to_numpy()

            return DataLoader(TensorDataset(torch.from_numpy(x).float(),
                                            torch.from_numpy(y).float()),
                              batch_size=config["batch_size"],
                              shuffle=True)

        return train_data_creator, val_data_creator

    def get_best_model(self):
        """
        Get the tuned model
        :return:
        """
        return self.model.get_best_model()

    def get_best_config(self):
        """
        Get the best configuration
        :return:
        """
        return self.model.auto_est.get_best_config()