# PyZX - Python library for quantum circuit rewriting
#        and optimization using the ZX-calculus
# Copyright (C) 2018 - Aleks Kissinger and John van de Wetering

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Dict, Set, Tuple, Optional

from .extract import bi_adj
from .linalg import Mat2
from .graph.base import BaseGraph, VertexType, VT, ET
from .utils import vertex_is_zx


def gflow(
    g: BaseGraph[VT, ET], delayed: bool=False, pauli: bool=False
) -> Optional[Tuple[Dict[VT, int], Dict[VT, Set[VT]], int]]:
    r"""Compute the gflow of a diagram in graph-like form.

    :param g: A ZX-graph.
    :param delayed: Compute the maximally-delayed gflow
    :param pauli: Compute the Pauli flow, restricted to {XZ, X} measurements

    Based on algorithm by Perdrix and Mhalla.
    See dx.doi.org/10.1007/978-3-540-70575-8_70

    Slightly extended to allow searching for Pauli flow with measurement planes {XZ, X}.

    Here is the pseudocode it is based on:
    ```
    input : An open graph
    output: A generalised flow

    gFlow (V,Gamma,In,Out) =
    begin
      for all v in Out do
        l(v) := 0
      end
      return gFlowaux (V,Gamma,In,Out,1)
    end

    gFlowaux (V,Gamma,In,Out,k) =
    begin
      C := {}
      for all u in V \\ Out do
        Solve in F2 : Gamma[V \\ Out, Out \\ In] * I[X] = I[{u}]
        if there is a solution X0 then
          C := C union {u}
          g(u) := X0
          l(u) := k
        end
      end
      if C = {} then
        return (Out = V,(g,l))
      else
        return gFlowaux (V, Gamma, In, Out union C, k + 1)
      end
    end
    ```
    """
    l: Dict[VT, int] = {}
    gflow: Dict[VT, Set[VT]] = {}
    ty = g.types()

    processed: Set[VT] = set(g.outputs()) | g.grounds()
    vertices: Set[VT] = set(v for v in g.vertices() if vertex_is_zx(ty[v]))
    pattern_inputs: Set[VT] = set()
    pattern_outputs: Set[VT] = set()
    paulis: Set[VT] = set()

    for inp in g.inputs():
        pattern_inputs |= set(n for n in g.neighbors(inp) if vertex_is_zx(ty[n]))
    for outp in g.outputs():
        pattern_outputs |= set(n for n in g.neighbors(outp) if vertex_is_zx(ty[n]))

    if pauli:
        paulis = set(v for v in vertices.difference(pattern_inputs) if g.phase(v) in (0,1))

    processed = pattern_outputs.copy()
    for v in processed:
        l[v] = 0

    k: int = 1
    while True:
        correct = set()
        processed_prime = [
            v
            for v in processed.difference(pattern_inputs) | paulis
            if delayed or any(w not in processed for w in g.neighbors(v))
        ]
        candidates = [
            v
            for v in vertices.difference(processed)
            if any(w in processed_prime for w in g.neighbors(v))
        ]

        zerovec = Mat2.zeros(len(candidates), 1)

        m = bi_adj(g, processed_prime, candidates)
        for index, u in enumerate(candidates):
            vu = zerovec.copy()
            vu.data[index][0] = 1
            x = m.solve(vu)
            if x:
                correct.add(u)
                gflow[u] = {processed_prime[i] for i in range(x.rows()) if x.data[i][0]}
                l[u] = k

        if not correct:
            if len(vertices) == len(processed):
                return l, gflow, k
            return None
        else:
            processed.update(correct)
            k += 1


def extended_gflow() -> None:
    r"""NOT IMPLEMENTED YET: Compute the extended (i.e. 3-plane) gflow of a diagram in graph-like form.

    Based on the algorithm in "There and Back Again"
    See https://arxiv.org/pdf/2003.01664

    For reference, here is the pseudocode from that paper:
    ```
    input: an open graph, given as:
        - M: an adjancency matrix M
        - I: input rows/cols
        - O: output rows/cols
        - lambda: a choice of measurement plane for each vertex
    output: extended gflow, given as a triple (success, g, d) where:
        - g: assigns each vertex its correction set
        - d: assigns each vertex a "depth", i.e. the number of layers away from the output layer. This
             is related to the flow ordering as v ≺ w <=> d(v) > d(w)

    EXT_GFLOW(M, I, O, lambda)
      initialise functions g and d
      foreach (v in O)
        d(v) <- 0 // Outputs have depth 0
      end
      return GFLOWAUX(M, I, O, lambda, 1, d, g) // Start the recursive process of finding Vj^≺
    end

    GFLOWAUX(M, I, O, lambda, k, d, g)
      O' <- O \\ I
      C <- {}
      foreach (u in O^⟂)
        if lambda(u) = XY
          K' <- Solution for K Δ O' where Odd(K) ∩ O^⟂ = {u}
        elseif lambda(u) = XZ
          K' <- {u} ∪ (Solution for K Δ O' where Odd(K ∪ {u}) ∩ O^⟂ = {u})
        elseif lambda(u) = YZ
          K' <- {u} ∪ (Solution for K Δ O' where Odd(K ∪ {u}) ∩ O^⟂ = {})
        end
        if K' exists
          C <- C ∪ {u}
          g(u) <- K'  // Assign a correction set for u
          d(u) <- k   // Assign a depth value for u
        end
      end
      if C = {}
        if O = V
          return (true, g, d)  // Halt, returning maximally delayed g and depth values d
        else 
          return (false, {}, {}) // Halt if no gflow exists
        end
      else 
        return GFLOWAUX(M, I, O ∪ C, lambda, k+1, d, g)
      end
    end
    ```
    """
    raise ValueError("Not implemented")
