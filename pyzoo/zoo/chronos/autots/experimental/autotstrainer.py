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

import types

from zoo.orca.automl.auto_estimator import AutoEstimator
from zoo.chronos.data import TSDataset
import zoo.orca.automl.hp as hp
from zoo.chronos.autots.model import AutoModelFactory
from zoo.chronos.autots.experimental.tspipeline import TSPipeline


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
                 past_seq_len=2,
                 future_seq_len=1,
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
               a model creation function indicates a 3rd party model, the function should take a
               config param and return a torch.nn.Module (backend="torch") / tf model
               (backend="keras"). If you use chronos.data.TSDataset as data input, the 3rd party
               should have 3 dim input (num_sample, past_seq_len, input_feature_num) and 3 dim
               output (num_sample, future_seq_len, output_feature_num) and use the same key
               in the model creation function. If you use a customized data creator, the output of
               data creator should fit the input of model creation function.
        :param search_space: hyper parameter configurations. Read the API docs for each auto model.
               Some common hyper parameter can be explicitly set in named parameter.
        :param metric: String. The evaluation metric name to optimize. e.g. "mse"
        :param loss: String or pytorch/tf.keras loss instance or pytorch loss creator function.
        :param optimizer: String or pyTorch optimizer creator function or
               tf.keras optimizer instance.
        :param past_seq_len: Int or or hp sampling function. The number of historical steps (i.e.
               lookback) used for forecasting. For hp sampling, see zoo.orca.automl.hp for more
               details. The values defaults to 2.
        :param future_seq_len: Int. The number of future steps to forecast. The value defaults
               to 1.
        :param input_feature_num: Int. The number of features in the input. The value is ignored if
               you set selected_features and use chronos.data.TSDataset as input data type.
        :param output_target_num: Int. The number of targets in the output.
        :param selected_features: String. "all" and "auto" are supported for now. For "all",
               all features that are generated are used for each trial. For "auto", a subset
               is sampled randomly from all features for each trial. The parameter is ignored
               if not using chronos.data.TSDataset as input data type.
        :param backend: The backend of the auto model. We only support backend as "torch" for now.
        :param logs_dir: Local directory to save logs and results.
               It defaults to "/tmp/autots_trainer"
        :param cpus_per_trial: Int. Number of cpus for each trial. It defaults to 1.
        :param name: name of the AutoLSTM. It defaults to "auto_lstm".
        """
        # check backend and set default loss
        if backend != "torch":
            raise ValueError(f"We only support backend as torch. Got {backend}")
        else:
            import torch
            if loss is None:
                loss = torch.nn.MSELoss()

        if isinstance(model, types.FunctionType) and backend == "torch":
            from zoo.orca.automl.auto_estimator import AutoEstimator
            self.model = AutoEstimator.from_torch(model_creator=model,
                                                  optimizer=optimizer,
                                                  loss=loss,
                                                  logs_dir=logs_dir,
                                                  resources_per_trial={"cpu": cpus_per_trial},
                                                  name=name)
            self.metric = metric
            search_space.update({"past_seq_len": past_seq_len,
                                 "future_seq_len": future_seq_len,
                                 "input_feature_num": input_feature_num,
                                 "output_feature_num": output_target_num})
            self.search_space = search_space

        if isinstance(model, str):
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
        self._scaler = None
        self._scaler_index = None

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
        is_third_party_model = isinstance(self.model, AutoEstimator)

        # generate data creator from TSDataset (pytorch base require validation data)
        if isinstance(data, TSDataset) and isinstance(validation_data, TSDataset):
            train_d, val_d = self._prepare_data_creator(
                search_space=self.search_space if is_third_party_model else self.model.search_space,
                train_data=data,
                val_data=validation_data,
            )
            self._scaler = data.scaler
            self._scaler_index = data.scaler_index
        else:
            train_d, val_d = data, validation_data

        if is_third_party_model:
            self.search_space.update({"batch_size": batch_size})
            self.model.fit(
                data=train_d,
                epochs=epochs,
                validation_data=val_d,
                metric=self.metric,
                metric_threshold=metric_threshold,
                n_sampling=n_sampling,
                search_space=self.search_space,
                search_alg=search_alg,
                search_alg_params=search_alg_params,
                scheduler=scheduler,
                scheduler_params=scheduler_params,
            )

        if not is_third_party_model:
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

        return TSPipeline(best_model=self.get_best_model(),
                          best_config=self.get_best_config(),
                          scaler=self._scaler,
                          scaler_index=self._scaler_index)

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
        # TODO: more flexible setting
        all_features = train_data.feature_col
        if self.selected_features not in ("all", "auto"):
            raise ValueError(f"Only \"all\" and \"auto\" are supported for selected_features,\
                but found {self.selected_features}")
        if self.selected_features == "auto":
            if len(all_features) == 0:
                search_space['selected_features'] = all_features
            else:
                search_space['selected_features'] = hp.choice_n(all_features,
                                                                min_items=0,
                                                                max_items=len(all_features))
        if self.selected_features == "all":
            search_space['selected_features'] = all_features

        # put train/val data in ray
        train_data_id = ray.put(train_data)
        valid_data_id = ray.put(val_data)

        def train_data_creator(config):
            train_d = ray.get(train_data_id)

            x, y = train_d.roll(lookback=config.get('past_seq_len'),
                                horizon=config.get('future_seq_len'),
                                feature_col=config['selected_features']) \
                          .to_numpy()

            return DataLoader(TensorDataset(torch.from_numpy(x).float(),
                                            torch.from_numpy(y).float()),
                              batch_size=config["batch_size"],
                              shuffle=True)

        def val_data_creator(config):
            val_d = ray.get(valid_data_id)

            x, y = val_d.roll(lookback=config.get('past_seq_len'),
                              horizon=config.get('future_seq_len'),
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

        :return: the best model instance
        """
        return self.model.get_best_model()

    def get_best_config(self):
        """
        Get the best configuration

        :return: A dictionary of best hyper parameters
        """
        return self.model.get_best_config()
