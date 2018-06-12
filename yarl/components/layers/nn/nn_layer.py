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

from yarl.components.layers.layer import Layer
from yarl.spaces import ContainerSpace


class NNLayer(Layer):
    """
    A generic NN-layer object.
    """
    def __init__(self, *sub_components, **kwargs):
        super(NNLayer, self).__init__(*sub_components, **kwargs)

        # The wrapped layer object.
        self.layer = None

    def check_input_spaces(self, input_spaces, action_space):
        """
        Do some sanity checking on the incoming Space:
        Must not be Container (for now) and must have a batch rank.
        """
        # Loop through all our in-Sockets and sanity check each one of them for:
        for in_sock in self.input_sockets:
            in_space = input_spaces[in_sock.name]
            # a) Must not be  ContainerSpace (not supported yet for NNLayers, doesn't seem to make sense).
            assert not isinstance(in_space, ContainerSpace), "ERROR: Cannot handle container input Spaces " \
                                                             "in layer '{}' (atm; may soon do)!".format(self.name)
            # b) All input Spaces need batch ranks (we are passing through NNs after all).
            #assert in_space.has_batch_rank,\
            #    "ERROR: Space in Socket 'input' to layer '{}' must have a batch rank (0th position)!".format(self.name)

    def _graph_fn_apply(self, *inputs):
        """
        The actual calculation on one or more input Ops.

        Args:
            inputs (SingleDataOp): The single (non-container) input(s) to the layer.

        Returns:
            The output(s) after having pushed the input(s) through the layer.
        """
        return self.layer.apply(*inputs)
