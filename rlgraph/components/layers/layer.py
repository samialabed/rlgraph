# Copyright 2018 The RLGraph-Project, All Rights Reserved.
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

from rlgraph.components.component import Component


class Layer(Component):
    """
    A Layer is a simple Component that implements the `apply` method with n inputs and m return values.

    API:
        apply(*inputs): Applies the layer's logic to the inputs and returns one or more result values.
    """
    def __init__(self, **kwargs):
        flatten_ops = kwargs.pop("flatten_ops", False)
        split_ops = kwargs.pop("split_ops", False)
        add_auto_key_as_first_param = kwargs.pop("add_auto_key_as_first_param", False)

        super(Layer, self).__init__(scope=kwargs.pop("scope", "layer"), **kwargs)

        self.define_api_method(
            "apply", self._graph_fn_apply, flatten_ops=flatten_ops,
            split_ops=split_ops, add_auto_key_as_first_param=add_auto_key_as_first_param
        )

    def _graph_fn_apply(self, *inputs):
        """
        This is where the graph-logic of this layer goes.

        Args:
            *inputs (any): The input(s) to this layer.

        Returns:
            DataOp: The output(s) of this layer.
        """
        raise NotImplementedError
