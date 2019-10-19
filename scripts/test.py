#!//bin/env python
# This script requires the models that are shipped with OpenRAVE to be in your
# OPENRAVE_DATA path. This is true by default, but may not be true if you set
# your OPENRAVE_DATA environmental variable. Notably, this includes if you
# source a Catkin workspace that includes the openrave_catkin package.
#
# If so, you should explicitly add this directory to your path:
#
#    export OPENRAVE_DATA="${OPENRAVE_DATA}:/usr/share/openrave-0.9/data"
#
# This path assumes that you installed OpenRAVE to /usr. You may need to alter
# the command to match your acutal install destination.

from openravepy import *

start_config = [  0.80487864,  0.42326865, -0.54016693,  2.28895761,
                  -0.34930645, -1.19702164,  1.95971213 ]
goal_config  = [  2.41349473, -1.43062044, -2.69016693,  2.12681216,
                  -0.75643783, -1.52392537,  1.01239878 ]

# Setup the environment.
env = Environment()
env.SetViewer('qtcoin')
env.Load('/home/jiangeng/workspace/openrave/src/data/wamtest1.env.xml')
robot = env.GetRobot('BarrettWAM')
manipulator = robot.GetManipulator('arm')

planner = RaveCreatePlanner(env, 'AtlasMPNet')

# with env:
#     robot.SetActiveDOFs(manipulator.GetArmIndices())
#     robot.SetActiveDOFValues(start_config)
#     robot.SetActiveManipulator(manipulator)
#
# Setup the planning instance.
params = Planner.PlannerParameters()
params.SetRobotActiveJoints(robot)
params.SetGoalConfig(goal_config)
params.SetExtraParameters(
"""<tolerance>0.0001</tolerance>
<max_iter>50</max_iter>
<delta>0.05</delta>
<lambda>2</lambda>
<time>5</time>
<range>0</range>
<exploration>0.75</exploration>
<epsilon>0.05</epsilon>
<rho>5</rho>
<alpha>0.392699</alpha>
<max_chart>200</max_chart>
<using_bias>0</using_bias>
<using_tb>0</using_tb>
<separate>0</separate>""")
#
# # Set the timeout and planner-specific parameters. You can view a list of
# # supported parameters by calling: planner.SendCommand('GetParameters')
# print 'Parameters:'
# print planner.SendCommand('GetParameters')
#
# params.SetExtraParameters('<range>0.02</range>')

planner.InitPlan(robot, params)
env.GetViewer().quitmainloop()
env.Destroy()
