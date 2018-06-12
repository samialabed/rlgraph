# Copyright 2018 The YARL-Project, All Rights Reserved.
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
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from yarl import backend
from yarl.utils.util import get_rank
from yarl.components.loss_functions import LossFunction
from yarl.spaces import IntBox

if backend == "tf":
    import tensorflow as tf


class DQNLossFunction(LossFunction):
    """
    The classic 2015 DQN Loss Function:
    L = Expectation-over-uniform-batch(r + gamma x max_a'Qt(s',a') - Qn(s,a))²
    Where Qn is the "normal" Q-network and Qt is the "target" net (which is a little behind Qn for stability purposes).
    """

    def __init__(self, discount=0.98, double_q=False, scope="dqn-loss-function", **kwargs):
        """
        Args:
            discount (float): The discount factor (gamma).
            double_q (bool): Whether to use the double DQN loss function (see DQNAgent [2]).
        """
        # Pass our in-Socket names to parent c'tor.
        super(DQNLossFunction, self).__init__("q_values", "actions", "rewards", "q_values_s_", scope=scope,
                                              flatten_ops=kwargs.pop("flatten_ops", False), **kwargs)
        self.discount = discount  # TODO: maybe move this to parent?
        self.double_q = double_q
        self.action_space = None

    def check_input_spaces(self, input_spaces, action_space):
        """
        Do some sanity checking on the incoming Spaces:
        """
        self.action_space = action_space
        # Check for IntBox and num_categories.
        assert isinstance(self.action_space, IntBox) and self.action_space.num_categories is not None, \
            "ERROR: action_space for DQN must be IntBox (for now) and have a `num_categories` attribute that's " \
            "not None!"

    def _graph_fn_loss_per_item(self, q_values_s, actions, rewards, q_values_sp):
        """
        Args:
            q_values_s (SingleDataOp): The batch of Q-values representing the expected accumulated discounted returns
                when in s and taking different actions a.
            actions (SingleDataOp): The batch of actions that were actually taken in states s (from a memory).
            rewards (SingleDataOp): The batch of rewards that we received after having taken a in s (from a memory).
            q_values_sp (SingleDataOp): The batch of Q-values representing the expected accumulated discounted
                returns when in s' and taking different actions a'.

        Returns:
            SingleDataOp: The loss values vector (one single value for each batch item).
        """
        if backend == "tf":
            # Q(s',a') -> Use the max(a') one.
            q_sp_ap_values = tf.reduce_max(input_tensor=q_values_sp, axis=-1)

            # Q(s,a) -> Use the Q-value of the action actually taken before.
            one_hot = tf.one_hot(indices=actions, depth=self.action_space.num_categories)
            q_s_a_values = tf.reduce_sum(input_tensor=(q_values_s * one_hot), axis=-1)

            # Calculate the TD-delta (target - current estimate).
            td_delta = (rewards + self.discount * q_sp_ap_values) - q_s_a_values
            # Reduce over the composite actions?
            if get_rank(td_delta) > 1:
                td_delta = tf.reduce_mean(input_tensor=td_delta, axis=-1)
            return tf.pow(x=td_delta, y=2)
