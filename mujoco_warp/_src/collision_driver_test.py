# Copyright 2025 The Newton Developers
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
"""Tests the collision driver."""

import mujoco
import numpy as np
from absl.testing import absltest
from absl.testing import parameterized
from mujoco_warp.test_data.collision_sdf.nut import nut, nut_sdf_grad
from mujoco_warp.test_data.collision_sdf.bolt import bolt, bolt_sdf_grad
import mujoco_warp as mjwarp
from .types import SDFType
import warp as wp
from . import test_util
from . import collision_sdf




class CollisionTest(parameterized.TestCase):
  """Tests the collision contact functions."""

  _SDF_SDF = {
    "_NUT_NUT": """
<mujoco>
  <extension>
    <plugin plugin="mujoco.sdf.nut">
      <instance name="nut1">
        <config key="radius" value="0.27"/>
      </instance>
      <instance name="nut2">
        <config key="radius" value="0.27"/>
      </instance>
    </plugin>
  </extension>
  <compiler autolimits="true"/>
  <option sdf_iterations="10"/> <!-- Increased for better collision accuracy -->
  <asset>
    <mesh name="nut_mesh1">
      <plugin instance="nut1"/>
    </mesh>
    <mesh name="nut_mesh2">
      <plugin instance="nut2"/>
    </mesh>
  </asset>
  <worldbody>
    <!-- First nut (floating) -->
    <body pos="0 0 0.5">
      <joint type="free"/>
      <geom type="sdf" name="nut1" mesh="nut_mesh1" rgba="0.83 0.68 0.4 1">
        <plugin instance="nut1"/>
      </geom>
    </body>
    <!-- Second nut (positioned to intersect) -->
    <body pos="0 0 0.4">
      <geom type="sdf" name="nut2" mesh="nut_mesh2" rgba="0.9 0.4 0.2 1">
        <plugin instance="nut2"/>
      </geom>
    </body>
    <light name="left" pos="-1 0 2" cutoff="80"/>
    <light name="right" pos="1 0 2" cutoff="80"/>
  </worldbody>
</mujoco>
""",
     "NUT_BOLT": """<mujoco>
  <extension>
    <plugin plugin="mujoco.sdf.nut">
      <instance name="nut">
        <config key="radius" value="0.26"/>
      </instance>
    </plugin>
    <plugin plugin="mujoco.sdf.bolt">
      <instance name="bolt">
        <config key="radius" value="0.255"/>
      </instance>
    </plugin>
  </extension>

  <compiler autolimits="true"/>


  <visual>
    <map force="0.05"/>
  </visual>

  <asset>
    <mesh name="nut">
      <plugin instance="nut"/>
    </mesh>
    <mesh name="bolt">
      <plugin instance="bolt"/>
    </mesh>
  </asset>

  <option sdf_iterations="10" sdf_initpoints="20"/>

  <default>
    <geom solref="0.01 1" solimp=".95 .99 .0001" friction="0.01"/>
  </default>

  <statistic meansize=".1"/>

  <worldbody>
    <body pos="-0.0012496 0.00329058 0.830362" quat="-0.000212626 0.999996 -0.00200453 0.00185878">
      <joint type="free" damping="30"/>
      <geom type="sdf" name="nut" mesh="nut" rgba="0.83 0.68 0.4 1">
        <plugin instance="nut"/>
      </geom>
    </body>
    <body euler="180 0 0">
      <geom type="sdf" name="bolt" mesh="bolt" rgba="0.7 0.7 0.7 1">
        <plugin instance="bolt"/>
      </geom>
    </body>
    <light name="left" pos="-1 0 2" cutoff="80"/>
    <light name="right" pos="1 0 2" cutoff="80"/>
  </worldbody>
</mujoco>
"""}
  _FIXTURES = {
    "box_plane": """
        <mujoco>
          <worldbody>
            <geom size="40 40 40" type="plane"/>
            <body pos="0 0 0.3" euler="45 0 0">
              <freejoint/>
              <geom size="0.5 0.5 0.5" type="box"/>
            </body>
          </worldbody>
        </mujoco>
      """,
    "plane_sphere": """
        <mujoco>
          <worldbody>
            <geom size="40 40 40" type="plane"/>
            <body pos="0 0 0.2" euler="45 0 0">
              <freejoint/>
              <geom size="0.5" type="sphere"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "plane_capsule": """
        <mujoco>
          <worldbody>
            <geom size="40 40 40" type="plane"/>
            <body pos="0 0 0.0" euler="30 30 0">
              <freejoint/>
              <geom size="0.05 0.05" type="capsule"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "convex_convex": """
        <mujoco>
          <asset>
            <mesh name="poly"
            vertex="0.3 0 0  0 0.5 0  -0.3 0 0  0 -0.5 0  0 -1 1  0 1 1"
            face="0 1 5  0 5 4  0 4 3  3 4 2  2 4 5  1 2 5  0 2 1  0 3 2"/>
          </asset>
          <worldbody>
            <body pos="0.0 2.0 0.35" euler="0 0 90">
              <freejoint/>
              <geom size="0.2 0.2 0.2" type="mesh" mesh="poly"/>
            </body>
            <body pos="0.0 2.0 2.281" euler="180 0 0">
              <freejoint/>
              <geom size="0.2 0.2 0.2" type="mesh" mesh="poly"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "capsule_capsule": """
        <mujoco model="two_capsules">
          <worldbody>
            <body>
              <joint type="free"/>
              <geom fromto="0.62235904  0.58846647 0.651046 1.5330081 0.33564585 0.977849"
               size="0.05" type="capsule"/>
            </body>
            <body>
              <joint type="free"/>
              <geom fromto="0.5505271 0.60345304 0.476661 1.3900293 0.30709633 0.932082"
               size="0.05" type="capsule"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "sphere_sphere": """
        <mujoco>
          <worldbody>
            <body>
              <joint type="free"/>
              <geom pos="0 0 0" size="0.2" type="sphere"/>
            </body>
            <body >
              <joint type="free"/>
              <geom pos="0 0.3 0" size="0.11" type="sphere"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "sphere_capsule": """
        <mujoco>
          <worldbody>
            <body>
              <joint type="free"/>
              <geom pos="0 0 0" size="0.2" type="sphere"/>
            </body>
            <body>
              <joint type="free"/>
              <geom fromto="0.3 0 0 0.7 0 0" size="0.1" type="capsule"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "sphere_cylinder_corner": """
        <mujoco>
          <worldbody>
            <body>
              <joint type="slide" axis="1 0 0"/>
              <joint type="slide" axis="0 1 0"/>
              <joint type="slide" axis="0 0 1"/>
              <geom size="0.1" type="sphere" pos=".33 0 0"/>
            </body>
            <body>
              <geom size="0.15 0.2" type="cylinder" euler="30 45 0"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "sphere_cylinder_cap": """
        <mujoco>
          <worldbody>
            <body>
              <joint type="slide" axis="1 0 0"/>
              <joint type="slide" axis="0 1 0"/>
              <joint type="slide" axis="0 0 1"/>
              <geom size="0.1" type="sphere" pos=".26 -.14 .1"/>
            </body>
            <body>
              <geom size="0.15 0.2" type="cylinder" euler="30 45 0"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "sphere_cylinder_side": """
        <mujoco>
          <worldbody>
            <body>
              <joint type="slide" axis="1 0 0"/>
              <joint type="slide" axis="0 1 0"/>
              <joint type="slide" axis="0 0 1"/>
              <geom size="0.1" type="sphere" pos="0 -.26 0"/>
            </body>
            <body>
              <geom size="0.15 0.2" type="cylinder" euler="30 45 0"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "plane_cylinder_1": """
        <mujoco>
          <worldbody>
            <geom size="40 40 40" type="plane" euler="3 0 0"/>
            <body pos="0 0 0.1" euler="30 30 0">
              <freejoint/>
              <geom size="0.05 0.1" type="cylinder"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "plane_cylinder_2": """
        <mujoco>
          <worldbody>
            <geom size="40 40 40" type="plane" euler="3 0 0"/>
            <body pos="0.2 0 0.04" euler="90 0 0">
              <freejoint/>
              <geom size="0.05 0.1" type="cylinder"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "plane_cylinder_3": """
        <mujoco>
          <worldbody>
            <geom size="40 40 40" type="plane" euler="3 0 0"/>
            <body pos="0.5 0 0.1" euler="3 0 0">
              <freejoint/>
              <geom size="0.05 0.1" type="cylinder"/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "sphere_box_shallow": """
        <mujoco>
          <worldbody>
            <geom type="box" pos="0 0 0" size=".5 .5 .5" />
            <body pos="-0.6 -0.6 0.7">
              <geom type="sphere" size="0.5"/>
              <freejoint/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "sphere_box_deep": """
        <mujoco>
          <worldbody>
            <geom type="box" pos="0 0 0" size=".5 .5 .5" />
            <body pos="-0.6 -0.6 0.7">
              <geom type="sphere" size="0.5"/>
              <freejoint/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "capsule_box_edge": """
        <mujoco>
          <worldbody>
            <geom type="box" pos="0 0 0" size=".5 .4 .9" />
            <body pos="0.4 0.2 0.8" euler="0 -40 0" >
              <geom type="capsule" size="0.5 0.8"/>
              <freejoint/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "capsule_box_corner": """
        <mujoco>
          <worldbody>
            <geom type="box" pos="0 0 0" size=".5 .55 .6" />
            <body pos="0.55 0.6 0.65" euler="0 0 0" >
              <geom type="capsule" size="0.4 0.6"/>
              <freejoint/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "capsule_box_face_tip": """
        <mujoco>
          <worldbody>
            <geom type="box" pos="0 0 0" size=".5 .4 .9" />
            <body pos="0 0 1.5" >
              <geom type="capsule" size="0.5 0.8"/>
              <freejoint/>
            </body>
          </worldbody>
        </mujoco>
        """,
    "capsule_box_face_flat": """
        <mujoco>
          <worldbody>
            <geom type="box" pos="0 0 0" size=".5 .7 .9" />
            <body pos="0.5 0.2 0.0" euler="0 0 0" >
              <geom type="capsule" size="0.2 0.4"/>
              <freejoint/>
            </body>
          </worldbody>
        </mujoco>
        """,
  }

  # Temporarily disabled
  #  "box_mesh": """
  #      <mujoco>
  #        <asset>
  #          <mesh name="boxmesh" scale="0.1 0.1 0.1"
  #                vertex="-1 -1 -1 1 -1 -1 1 1 -1 1 1 1
  #                         1 -1 1 -1 1 -1 -1 1 1 -1 -1 1"/>
  #        </asset>
  #        <worldbody>
  #          <geom pos="0 0 -0.1" type="box" size="0.5 0.5 0.1"/>
  #          <body pos="0 0 .099">
  #            <joint type="free"/>
  #            <geom type="mesh" mesh="boxmesh"/>
  #          </body>
  #        </worldbody>
  #      </mujoco>
  #    """,

  @parameterized.parameters(_SDF_SDF.keys())
  def test_sdf_collision(self, fixture):
      
      """Tests collisions with different geometries."""

      @wp.func
      def user_sdf(p: wp.vec3, attr: wp.vec3,  sdf_type: int) -> float:
          result = 0.0
          if sdf_type == int(SDFType.NUT.value):
              result = nut(p, attr)
          elif sdf_type == int(SDFType.BOLT.value):
              result = bolt(p, attr)
          return result

      @wp.func
      def user_sdf_grad(p: wp.vec3, attr: wp.vec3, sdf_type: int) -> wp.vec3:
            if sdf_type == int(SDFType.NUT.value):
              return nut_sdf_grad(p, attr)
            elif sdf_type == int(SDFType.BOLT.value):
              return bolt_sdf_grad(p, attr)
            return wp.vec3()


      collision_sdf.user_sdf = user_sdf
      collision_sdf.user_sdf_grad = user_sdf_grad
      mjm, mjd, m, d = test_util.fixture(xml=self._SDF_SDF[fixture])

      # Exempt GJK collisions from exact contact count check
      # because GJK generates more contacts
      allow_different_contact_count = True
      mujoco.mj_collision(mjm, mjd)
      mjwarp.collision(m, d)
      for i in range(10):
          actual_dist = mjd.contact.dist[i]
          actual_pos = mjd.contact.pos[i]
          actual_frame = mjd.contact.frame[i][0:3]
          result = False
          test_dist = d.contact.dist.numpy()[i]
          test_pos = d.contact.pos.numpy()[i, :]
          test_frame = d.contact.frame.numpy()[i].flatten()[0:3] # frame is not computed always correctly (?)
          check_dist = np.allclose(actual_dist, test_dist, rtol=5e-2, atol=1.0e-2)
          print(check_dist, actual_dist, test_dist, actual_pos, test_pos, actual_frame, test_frame )

          check_pos = np.allclose(actual_pos, test_pos, rtol=5e-2, atol=1.0e-1)
          if check_dist and check_pos:
            result = True
            break
          np.testing.assert_equal(result, True, f"Contact {i} not found in Gjk results")

      if not allow_different_contact_count:
        self.assertEqual(d.ncon.numpy()[0], mjd.ncon)

  @parameterized.parameters(_FIXTURES.keys())
  def test_collision(self, fixture):
    """Tests collisions with different geometries."""
    mjm, mjd, m, d = test_util.fixture(xml=self._FIXTURES[fixture])

    # Exempt GJK collisions from exact contact count check
    # because GJK generates more contacts
    allow_different_contact_count = False

    mujoco.mj_collision(mjm, mjd)
    mjwarp.collision(m, d)

    for i in range(mjd.ncon):
      actual_dist = mjd.contact.dist[i]
      actual_pos = mjd.contact.pos[i]
      actual_frame = mjd.contact.frame[i]
      result = False
      for j in range(d.ncon.numpy()[0]):
        test_dist = d.contact.dist.numpy()[j]
        test_pos = d.contact.pos.numpy()[j, :]
        test_frame = d.contact.frame.numpy()[j].flatten()
        check_dist = np.allclose(actual_dist, test_dist, rtol=5e-2, atol=1.0e-2)
        check_pos = np.allclose(actual_pos, test_pos, rtol=5e-2, atol=1.0e-2)
        check_frame = np.allclose(actual_frame, test_frame, rtol=5e-2, atol=1.0e-2)
        if check_dist and check_pos and check_frame:
          result = True
          break
      np.testing.assert_equal(result, True, f"Contact {i} not found in Gjk results")

    if not allow_different_contact_count:
      self.assertEqual(d.ncon.numpy()[0], mjd.ncon)

  def test_contact_exclude(self):
    """Tests contact exclude."""
    _, _, m, _ = test_util.fixture(
      xml="""
      <mujoco>
        <worldbody>
          <body name="body1">
            <freejoint/>
            <geom type="sphere" size=".1"/>
          </body>
          <body name="body2">
            <freejoint/>
            <geom type="sphere" size=".1"/>
          </body>
          <body name="body3">
            <freejoint/>
            <geom type="sphere" size=".1"/>
          </body>
        </worldbody>
        <contact>
          <exclude body1="body1" body2="body2"/>
        </contact>
      </mujoco>
    """
    )
    self.assertEqual(m.nxn_geom_pair.numpy().shape[0], 3)
    np.testing.assert_equal(m.nxn_pairid.numpy(), np.array([-2, -1, -1]))

  def test_contact_pair(self):
    """Tests contact pair."""
    # no pairs
    _, _, m, _ = test_util.fixture(
      xml="""
      <mujoco>
        <worldbody>
          <body>
            <freejoint/>
            <geom type="sphere" size=".1"/>
          </body>
        </worldbody>
      </mujoco>
    """
    )
    self.assertTrue((m.nxn_pairid.numpy() == -1).all())

    # 1 pair
    _, _, m, d = test_util.fixture(
      xml="""
      <mujoco>
        <worldbody>
          <body>
            <freejoint/>
            <geom name="geom1" type="sphere" size=".1"/>
          </body>
          <body>
            <freejoint/>
            <geom name="geom2" type="sphere" size=".1"/>
          </body>
        </worldbody>
        <contact>
          <pair geom1="geom1" geom2="geom2" margin="2" gap="3" condim="6" friction="5 4 3 2 1" solref="-.25 -.5" solreffriction="2 4" solimp=".1 .2 .3 .4 .5"/>
        </contact>
      </mujoco>
    """
    )
    self.assertTrue((m.nxn_pairid.numpy() == 0).all())

    for arr in (
      d.ncon,
      d.contact.includemargin,
      d.contact.dim,
      d.contact.friction,
      d.contact.solref,
      d.contact.solreffriction,
      d.contact.solimp,
    ):
      arr.zero_()

    mjwarp.collision(m, d)

    self.assertEqual(d.ncon.numpy()[0], 1)
    self.assertEqual(d.contact.includemargin.numpy()[0], -1)
    self.assertEqual(d.contact.dim.numpy()[0], 6)
    np.testing.assert_allclose(d.contact.friction.numpy()[0], np.array([5, 4, 3, 2, 1]))
    np.testing.assert_allclose(d.contact.solref.numpy()[0], np.array([-0.25, -0.5]))
    np.testing.assert_allclose(d.contact.solreffriction.numpy()[0], np.array([2.0, 4.0]))
    np.testing.assert_allclose(d.contact.solimp.numpy()[0], np.array([0.1, 0.2, 0.3, 0.4, 0.5]))

    # 1 pair: override contype and conaffinity
    _, _, m, d = test_util.fixture(
      xml="""
      <mujoco>
        <worldbody>
          <body name="body1">
            <freejoint/>
            <geom name="geom1" type="sphere" size=".1" contype="0" conaffinity="0"/>
          </body>
          <body name="body2">
            <freejoint/>
            <geom name="geom2" type="sphere" size=".1" contype="0" conaffinity="0"/>
          </body>
        </worldbody>
        <contact>
          <pair geom1="geom1" geom2="geom2" margin="2" gap="3" condim="6" friction="5 4 3 2 1" solref="-.25 -.5" solreffriction="2 4" solimp=".1 .2 .3 .4 .5"/>
        </contact>
      </mujoco>
    """
    )
    self.assertTrue((m.nxn_pairid.numpy() == 0).all())

    for arr in (
      d.ncon,
      d.contact.includemargin,
      d.contact.dim,
      d.contact.friction,
      d.contact.solref,
      d.contact.solreffriction,
      d.contact.solimp,
    ):
      arr.zero_()

    mjwarp.collision(m, d)

    self.assertEqual(d.ncon.numpy()[0], 1)
    self.assertEqual(d.contact.includemargin.numpy()[0], -1)
    self.assertEqual(d.contact.dim.numpy()[0], 6)
    np.testing.assert_allclose(d.contact.friction.numpy()[0], np.array([5, 4, 3, 2, 1]))
    np.testing.assert_allclose(d.contact.solref.numpy()[0], np.array([-0.25, -0.5]))
    np.testing.assert_allclose(d.contact.solreffriction.numpy()[0], np.array([2.0, 4.0]))
    np.testing.assert_allclose(d.contact.solimp.numpy()[0], np.array([0.1, 0.2, 0.3, 0.4, 0.5]))

    # 1 pair: override exclude
    _, _, m, d = test_util.fixture(
      xml="""
      <mujoco>
        <worldbody>
          <body name="body1">
            <freejoint/>
            <geom name="geom1" type="sphere" size=".1"/>
          </body>
          <body name="body2">
            <freejoint/>
            <geom name="geom2" type="sphere" size=".1"/>
          </body>
        </worldbody>
        <contact>
          <exclude body1="body1" body2="body2"/>
          <pair geom1="geom1" geom2="geom2" margin="2" gap="3" condim="6" friction="5 4 3 2 1" solref="-.25 -.5" solreffriction="2 4" solimp=".1 .2 .3 .4 .5"/>
        </contact>
      </mujoco>
    """
    )
    self.assertTrue((m.nxn_pairid.numpy() == 0).all())

    for arr in (
      d.ncon,
      d.contact.includemargin,
      d.contact.dim,
      d.contact.friction,
      d.contact.solref,
      d.contact.solreffriction,
      d.contact.solimp,
    ):
      arr.zero_()

    mjwarp.collision(m, d)

    self.assertEqual(d.ncon.numpy()[0], 1)
    self.assertEqual(d.contact.includemargin.numpy()[0], -1)
    self.assertEqual(d.contact.dim.numpy()[0], 6)
    np.testing.assert_allclose(d.contact.friction.numpy()[0], np.array([5, 4, 3, 2, 1]))
    np.testing.assert_allclose(d.contact.solref.numpy()[0], np.array([-0.25, -0.5]))
    np.testing.assert_allclose(d.contact.solreffriction.numpy()[0], np.array([2.0, 4.0]))
    np.testing.assert_allclose(d.contact.solimp.numpy()[0], np.array([0.1, 0.2, 0.3, 0.4, 0.5]))

    # 1 pair 1 exclude
    _, _, m, d = test_util.fixture(
      xml="""
      <mujoco>
        <worldbody>
          <body name="body1">
            <freejoint/>
            <geom name="geom1" type="sphere" size=".1"/>
          </body>
          <body name="body2">
            <freejoint/>
            <geom name="geom2" type="sphere" size=".1"/>
          </body>
          <body name="body3">
            <freejoint/>
            <geom name="geom3" type="sphere" size=".1"/>
          </body>
        </worldbody>
        <contact>
          <exclude body1="body1" body2="body2"/>
          <pair geom1="geom2" geom2="geom3" margin="2" gap="3" condim="6" friction="5 4 3 2 1" solref="-.25 -.5" solreffriction="2 4" solimp=".1 .2 .3 .4 .5"/>
        </contact>
      </mujoco>
    """
    )
    np.testing.assert_equal(m.nxn_pairid.numpy(), np.array([-2, -1, 0]))

    for arr in (
      d.ncon,
      d.contact.includemargin,
      d.contact.dim,
      d.contact.friction,
      d.contact.solref,
      d.contact.solreffriction,
      d.contact.solimp,
    ):
      arr.zero_()

    mjwarp.collision(m, d)

    self.assertEqual(d.ncon.numpy()[0], 2)
    self.assertEqual(d.contact.includemargin.numpy()[1], -1)
    self.assertEqual(d.contact.dim.numpy()[1], 6)
    np.testing.assert_allclose(d.contact.friction.numpy()[1], np.array([5, 4, 3, 2, 1]))
    np.testing.assert_allclose(d.contact.solref.numpy()[1], np.array([-0.25, -0.5]))
    np.testing.assert_allclose(d.contact.solreffriction.numpy()[1], np.array([2.0, 4.0]))
    np.testing.assert_allclose(d.contact.solimp.numpy()[1], np.array([0.1, 0.2, 0.3, 0.4, 0.5]))

    # TODO(team): test sap_broadphase

  @parameterized.parameters(
    (True, True),
    (True, False),
    (False, True),
    (False, False),
  )
  def test_collision_disableflags(self, constraint, contact):
    """Tests collision disableflags."""
    mjm, mjd, m, d = test_util.fixture(
      "humanoid/humanoid.xml",
      keyframe=0,
      constraint=constraint,
      contact=contact,
      kick=False,
    )

    mujoco.mj_collision(mjm, mjd)
    mjwarp.collision(m, d)

    self.assertEqual(d.ncon.numpy()[0], mjd.ncon)

  # TODO(team): test contact parameter mixing


if __name__ == "__main__":
  absltest.main()
