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

import zoo.orca.automl.hp as hp

from unittest import TestCase


class TestHp(TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_hp_choice_n(self):
        test_num = 3
        hp_instance = hp.choice_n(["1", "2", "3", "4"],
                                  min_items=2,
                                  max_items=4)
        for _ in range(test_num):
            sample_res = hp_instance.sample()
            assert isinstance(sample_res, list)
            assert len(sample_res) >= 2
            assert len(sample_res) <= 4
            assert len(set(sample_res)) == len(sample_res)
