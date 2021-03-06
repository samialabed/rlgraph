# Copyright 2018/2019 The RLgraph authors. All Rights Reserved.
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

import numpy as np
import unittest

from rlgraph.components.policies import Policy, SharedValueFunctionPolicy, DuelingPolicy
from rlgraph.spaces import *
from rlgraph.tests import ComponentTest
from rlgraph.tests.test_util import config_from_path
from rlgraph.utils import softmax, relu


class TestPolicies(unittest.TestCase):

    def test_policy_for_discrete_action_space(self):
        # state_space (NN is a simple single fc-layer relu network (2 units), random biases, random weights).
        state_space = FloatBox(shape=(4,), add_batch_rank=True)

        # action_space (5 possible actions).
        action_space = IntBox(5, add_batch_rank=True)
        flat_float_action_space = FloatBox(shape=(5,), add_batch_rank=True)

        policy = Policy(network_spec=config_from_path("configs/test_simple_nn.json"), action_space=action_space)
        test = ComponentTest(
            component=policy,
            input_spaces=dict(
                nn_input=state_space,
                actions=action_space,
                logits=flat_float_action_space,
                probabilities=flat_float_action_space
            ),
            action_space=action_space
        )
        policy_params = test.read_variable_values(policy.variables)

        # Some NN inputs (4 input nodes, batch size=2).
        states = np.array([[-0.08, 0.4, -0.05, -0.55], [13.0, -14.0, 10.0, -16.0]])
        # Raw NN-output.
        expected_nn_output = np.matmul(states, policy_params["policy/test-network/hidden-layer/dense/kernel"])
        test.test(("get_nn_output", states), expected_outputs=dict(output=expected_nn_output), decimals=6)

        # Raw action layer output; Expected shape=(2,5): 2=batch, 5=action categories
        expected_action_layer_output = np.matmul(
            expected_nn_output, policy_params["policy/action-adapter-0/action-network/action-layer/dense/kernel"]
        )
        test.test(("get_action_layer_output", states), expected_outputs=dict(output=expected_action_layer_output),
                  decimals=5)

        # Logits, parameters (probs) and skip log-probs (numerically unstable for small probs).
        expected_probabilities_output = softmax(expected_action_layer_output, axis=-1)
        test.test(("get_logits_probabilities_log_probs", states, ["logits", "probabilities"]), expected_outputs=dict(
            logits=expected_action_layer_output, probabilities=np.array(expected_probabilities_output, dtype=np.float32)
        ), decimals=5)

        print("Probs: {}".format(expected_probabilities_output))

        expected_actions = np.argmax(expected_action_layer_output, axis=-1)
        test.test(("get_action", states), expected_outputs=dict(action=expected_actions))

        # Action log-probs.
        expected_action_log_prob_output = np.log(np.array([
            expected_probabilities_output[0][expected_actions[0]],
            expected_probabilities_output[1][expected_actions[1]],
        ]))
        test.test(("get_action_log_probs", [states, expected_actions]),
                  expected_outputs=dict(action_log_probs=expected_action_log_prob_output,
                                        logits=expected_action_layer_output), decimals=5)

        # Stochastic sample.
        out = test.test(("get_stochastic_action", states), expected_outputs=None)  # dict(action=expected_actions))
        self.assertTrue(out["action"].dtype == np.int32)
        self.assertTrue(out["action"].shape == (2,))

        # Deterministic sample.
        test.test(("get_deterministic_action", states), expected_outputs=None)  # dict(action=expected_actions))
        self.assertTrue(out["action"].dtype == np.int32)
        self.assertTrue(out["action"].shape == (2,))

        # Distribution's entropy.
        out = test.test(("get_entropy", states), expected_outputs=None)  # dict(entropy=expected_h), decimals=3)
        self.assertTrue(out["entropy"].dtype == np.float32)
        self.assertTrue(out["entropy"].shape == (2,))

        # Action log-probs.
        expected_action_log_prob_output = dict(action_log_probs=np.log(np.array([
            expected_probabilities_output[0][expected_actions[0]],
            expected_probabilities_output[1][expected_actions[1]]
        ])), logits=expected_action_layer_output)
        test.test(("get_action_log_probs", [states, expected_actions]),
                  expected_outputs=expected_action_log_prob_output, decimals=5)

    def test_shared_value_function_policy_for_discrete_action_space(self):
        # state_space (NN is a simple single fc-layer relu network (2 units), random biases, random weights).
        state_space = FloatBox(shape=(4,), add_batch_rank=True)

        # action_space (3 possible actions).
        action_space = IntBox(3, add_batch_rank=True)
        flat_float_action_space = FloatBox(shape=(3,), add_batch_rank=True)

        # Policy with baseline action adapter.
        shared_value_function_policy = SharedValueFunctionPolicy(
            network_spec=config_from_path("configs/test_lrelu_nn.json"),
            action_space=action_space
        )
        test = ComponentTest(
            component=shared_value_function_policy,
            input_spaces=dict(
                nn_input=state_space,
                actions=action_space,
                probabilities=flat_float_action_space,
                logits=flat_float_action_space
            ),
            action_space=action_space,
        )
        policy_params = test.read_variable_values(shared_value_function_policy.variables)

        # Some NN inputs (4 input nodes, batch size=3).
        states = state_space.sample(size=3)
        # Raw NN-output (3 hidden nodes). All weights=1.5, no biases.
        expected_nn_output = relu(np.matmul(
            states, policy_params["shared-value-function-policy/test-network/hidden-layer/dense/kernel"]
        ), 0.1)
        test.test(("get_nn_output", states), expected_outputs=dict(output=expected_nn_output), decimals=5)

        # Raw action layer output; Expected shape=(3,3): 3=batch, 2=action categories + 1 state value
        expected_action_layer_output = np.matmul(
            expected_nn_output,
            policy_params["shared-value-function-policy/action-adapter-0/action-network/action-layer/dense/kernel"]
        )
        test.test(("get_action_layer_output", states), expected_outputs=dict(output=expected_action_layer_output),
                  decimals=5)

        # State-values: One for each item in the batch.
        expected_state_value_output = np.matmul(
            expected_nn_output,
            policy_params["shared-value-function-policy/value-function-node/dense-layer/dense/kernel"]
        )
        test.test(("get_state_values", states), expected_outputs=dict(state_values=expected_state_value_output),
                  decimals=5)

        # Logits-values.
        test.test(("get_state_values_logits_probabilities_log_probs", states, ["state_values", "logits"]),
                  expected_outputs=dict(state_values=expected_state_value_output, logits=expected_action_layer_output),
                  decimals=5)

        # Parameter (probabilities). Softmaxed logits.
        expected_probabilities_output = softmax(expected_action_layer_output, axis=-1)
        test.test(("get_logits_probabilities_log_probs", states, ["logits", "probabilities"]), expected_outputs=dict(
            logits=expected_action_layer_output,
            probabilities=expected_probabilities_output
        ), decimals=5)

        print("Probs: {}".format(expected_probabilities_output))

        expected_actions = np.argmax(expected_action_layer_output, axis=-1)
        test.test(("get_action", states), expected_outputs=dict(action=expected_actions))

        # Stochastic sample.
        out = test.test(("get_stochastic_action", states), expected_outputs=None)
        self.assertTrue(out["action"].dtype == np.int32)
        self.assertTrue(out["action"].shape == (3,))

        # Deterministic sample.
        out = test.test(("get_deterministic_action", states), expected_outputs=None)
        self.assertTrue(out["action"].dtype == np.int32)
        self.assertTrue(out["action"].shape == (3,))

        # Distribution's entropy.
        out = test.test(("get_entropy", states), expected_outputs=None)
        self.assertTrue(out["entropy"].dtype == np.float32)
        self.assertTrue(out["entropy"].shape == (3,))

    def test_shared_value_function_policy_for_discrete_action_space_with_time_rank_folding(self):
        # state_space (NN is a simple single fc-layer relu network (2 units), random biases, random weights).
        state_space = FloatBox(shape=(3,), add_batch_rank=True, add_time_rank=True)

        # action_space (4 possible actions).
        action_space = IntBox(4, add_batch_rank=True, add_time_rank=True)
        flat_float_action_space = FloatBox(shape=(4,), add_batch_rank=True, add_time_rank=True)

        # Policy with baseline action adapter AND batch-apply over the entire policy (NN + ActionAdapter + distr.).
        network_spec = config_from_path("configs/test_lrelu_nn.json")
        # Add folding to network.
        network_spec["fold_time_rank"] = True
        shared_value_function_policy = SharedValueFunctionPolicy(
            network_spec=network_spec,
            action_adapter_spec=dict(unfold_time_rank=True),
            action_space=action_space,
            value_unfold_time_rank=True
        )
        test = ComponentTest(
            component=shared_value_function_policy,
            input_spaces=dict(
                nn_input=state_space,
                actions=action_space,
                probabilities=flat_float_action_space,
                logits=flat_float_action_space
            ),
            action_space=action_space,
        )
        policy_params = test.read_variable_values(shared_value_function_policy.variables)

        # Some NN inputs.
        states = state_space.sample(size=(2, 3))
        states_folded = np.reshape(states, newshape=(6, 3))
        # Raw NN-output (3 hidden nodes). All weights=1.5, no biases.
        expected_nn_output = relu(np.matmul(
            states_folded, policy_params["shared-value-function-policy/test-network/hidden-layer/dense/kernel"]
        ), 0.1)
        test.test(("get_nn_output", states), expected_outputs=dict(output=expected_nn_output), decimals=5)

        # Raw action layer output; Expected shape=(3,3): 3=batch, 2=action categories + 1 state value
        expected_action_layer_output = np.matmul(
            expected_nn_output, policy_params["shared-value-function-policy/action-adapter-0/action-network/"
                                              "action-layer/dense/kernel"]
        )
        expected_action_layer_output = np.reshape(expected_action_layer_output, newshape=(2, 3, 4))
        test.test(("get_action_layer_output", states), expected_outputs=dict(output=expected_action_layer_output),
                  decimals=5)

        # State-values: One for each item in the batch.
        expected_state_value_output = np.matmul(
            expected_nn_output,
            policy_params["shared-value-function-policy/value-function-node/dense-layer/dense/kernel"]
        )
        expected_state_value_output_unfolded = np.reshape(expected_state_value_output, newshape=(2, 3, 1))
        test.test(("get_state_values", states), expected_outputs=dict(state_values=expected_state_value_output_unfolded),
                  decimals=5)

        expected_action_layer_output_unfolded = np.reshape(expected_action_layer_output, newshape=(2, 3, 4))
        test.test(
            ("get_state_values_logits_probabilities_log_probs", states, ["state_values", "logits"]),
            expected_outputs=dict(
                state_values=expected_state_value_output_unfolded, logits=expected_action_layer_output_unfolded
            ), decimals=5
        )

        # Parameter (probabilities). Softmaxed logits.
        expected_probabilities_output = softmax(expected_action_layer_output_unfolded, axis=-1)
        test.test(("get_logits_probabilities_log_probs", states, ["logits", "probabilities"]), expected_outputs=dict(
            logits=expected_action_layer_output_unfolded,
            probabilities=expected_probabilities_output
        ), decimals=5)

        print("Probs: {}".format(expected_probabilities_output))

        expected_actions = np.argmax(expected_action_layer_output_unfolded, axis=-1)
        test.test(("get_action", states), expected_outputs=dict(action=expected_actions))

        # Action log-probs.
        expected_action_log_prob_output = np.log(np.array([[
            expected_probabilities_output[0][0][expected_actions[0][0]],
            expected_probabilities_output[0][1][expected_actions[0][1]],
            expected_probabilities_output[0][2][expected_actions[0][2]],
        ], [
            expected_probabilities_output[1][0][expected_actions[1][0]],
            expected_probabilities_output[1][1][expected_actions[1][1]],
            expected_probabilities_output[1][2][expected_actions[1][2]],
        ]]))
        test.test(("get_action_log_probs", [states, expected_actions]), expected_outputs=dict(
            action_log_probs=expected_action_log_prob_output, logits=expected_action_layer_output_unfolded
        ), decimals=5)

        # Deterministic sample.
        out = test.test(("get_deterministic_action", states), expected_outputs=None)
        self.assertTrue(out["action"].dtype == np.int32)
        self.assertTrue(out["action"].shape == (2, 3))  # Make sure output is unfolded.

        # Stochastic sample.
        out = test.test(("get_stochastic_action", states), expected_outputs=None)
        self.assertTrue(out["action"].dtype == np.int32)
        self.assertTrue(out["action"].shape == (2, 3))  # Make sure output is unfolded.

        # Distribution's entropy.
        out = test.test(("get_entropy", states), expected_outputs=None)
        self.assertTrue(out["entropy"].dtype == np.float32)
        self.assertTrue(out["entropy"].shape == (2, 3))  # Make sure output is unfolded.

    def test_policy_for_discrete_action_space_with_dueling_layer(self):
        np.random.seed(10)
        # state_space (NN is a simple single fc-layer relu network (2 units), random biases, random weights).
        nn_input_space = FloatBox(shape=(3,), add_batch_rank=True)

        # action_space (2 possible actions).
        action_space = IntBox(2, add_batch_rank=True)
        flat_float_action_space = FloatBox(shape=(2,), add_batch_rank=True)

        # Policy with dueling logic.
        policy = DuelingPolicy(
            network_spec=config_from_path("configs/test_lrelu_nn.json"),
            action_adapter_spec=dict(
                pre_network_spec=[
                    dict(type="dense", units=10, activation="lrelu", activation_params=[0.1])
                ]
            ),
            units_state_value_stream=10,
            action_space=action_space
        )
        test = ComponentTest(
            component=policy,
            input_spaces=dict(
                nn_input=nn_input_space,
                actions=action_space,
                probabilities=flat_float_action_space,
                logits=flat_float_action_space
            ),
            action_space=action_space
        )
        policy_params = test.read_variable_values(policy.variables)

        # Some NN inputs.
        nn_input = nn_input_space.sample(size=3)
        # Raw NN-output.
        expected_nn_output = relu(np.matmul(
            nn_input, policy_params["dueling-policy/test-network/hidden-layer/dense/kernel"]), 0.1
        )
        test.test(("get_nn_output", nn_input), expected_outputs=dict(output=expected_nn_output))

        # Raw action layer output.
        expected_raw_advantages = np.matmul(relu(np.matmul(
            expected_nn_output, policy_params["dueling-policy/action-adapter-0/action-network/dense-layer/dense/kernel"]
        ), 0.1), policy_params["dueling-policy/action-adapter-0/action-network/action-layer/dense/kernel"])
        test.test(("get_action_layer_output", nn_input), expected_outputs=dict(output=expected_raw_advantages),
                  decimals=5)

        # Single state values.
        expected_state_values = np.matmul(relu(np.matmul(
            expected_nn_output,
            policy_params["dueling-policy/dense-layer-state-value-stream/dense/kernel"]
        )), policy_params["dueling-policy/state-value-node/dense/kernel"])
        test.test(("get_state_values", nn_input), expected_outputs=dict(state_values=expected_state_values),
                  decimals=5)

        # State-values: One for each item in the batch.
        expected_q_values_output = expected_state_values + expected_raw_advantages - \
            np.mean(expected_raw_advantages, axis=-1, keepdims=True)
        test.test(("get_logits_probabilities_log_probs", nn_input, "logits"), expected_outputs=dict(
            logits=expected_q_values_output
        ), decimals=5)

        # Parameter (probabilities). Softmaxed q_values.
        expected_probabilities_output = softmax(expected_q_values_output, axis=-1)
        test.test(("get_logits_probabilities_log_probs", nn_input, ["logits", "probabilities"]), expected_outputs=dict(
            logits=expected_q_values_output, probabilities=expected_probabilities_output
        ), decimals=5)

        print("Probs: {}".format(expected_probabilities_output))

        expected_actions = np.argmax(expected_q_values_output, axis=-1)
        test.test(("get_action", nn_input), expected_outputs=dict(action=expected_actions))

        # Action log-probs.
        expected_action_log_prob_output = np.log(np.array([
            expected_probabilities_output[0][expected_actions[0]],
            expected_probabilities_output[1][expected_actions[1]],
            expected_probabilities_output[2][expected_actions[2]],
        ]))
        test.test(("get_action_log_probs", [nn_input, expected_actions]),
                  expected_outputs=dict(action_log_probs=expected_action_log_prob_output, logits=expected_q_values_output), decimals=5)

        # Stochastic sample.
        out = test.test(("get_stochastic_action", nn_input), expected_outputs=None)
        self.assertTrue(out["action"].dtype == np.int32)
        self.assertTrue(out["action"].shape == (3,))

        # Deterministic sample.
        out = test.test(("get_deterministic_action", nn_input), expected_outputs=None)
        self.assertTrue(out["action"].dtype == np.int32)
        self.assertTrue(out["action"].shape == (3,))

        # Distribution's entropy.
        out = test.test(("get_entropy", nn_input), expected_outputs=None)
        self.assertTrue(out["entropy"].dtype == np.float32)
        self.assertTrue(out["entropy"].shape == (3,))

