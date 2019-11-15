/* Copyright (c) 2010 Carnegie Mellon University and Intel Corporation
   Author: Dmitry Berenson <dberenso@cs.cmu.edu>

   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions are met:

     * Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.
     * Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.
     * Neither the name of Intel Corporation nor Carnegie Mellon University,
       nor the names of their contributors, may be used to endorse or
       promote products derived from this software without specific prior
       written permission.

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
   ARE DISCLAIMED. IN NO EVENT SHALL INTEL CORPORATION OR CARNEGIE MELLON
   UNIVERSITY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
   OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
   WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
   OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

#ifndef ATLASMPNET_TASKSPACEREGIONCHAIN_H
#define ATLASMPNET_TASKSPACEREGIONCHAIN_H

#include <openrave/openrave.h>
#include "TaskSpaceRegion.h"

namespace Atlas_MPNet {
    /// Class defining a TSR Chain: a more complex representation of pose constraints
    class TaskSpaceRegionChain {
    public:
        std::vector<TaskSpaceRegion> TSRChain; ///< this is an ordered list of TSRs, where each one relies on the previous one to determine T0_w, note that the T0_w values of the TSRs in the chain will change (except the first one)
        bool Initialize(const OpenRAVE::EnvironmentBasePtr &penv_in); ///< initialize the TSR chain


        TaskSpaceRegionChain() {
            numdof = -1;
            _dx.resize(6);
            _sumbounds = -1;
        }

        ~TaskSpaceRegionChain() { DestoryRobotizedTSRChain(); }

        // return the manipulator index of the first TSR
        int GetManipInd() {
            if (TSRChain.size() > 0)
                return TSRChain[0].manipind;
            return -1;
        }

        // add a TSR to the chain
        void AddTSR(TaskSpaceRegion &TSR) {
            TSRChain.push_back(TSR);
        }

        // generate a sample from this TSR Chain
        OpenRAVE::Transform GenerateSample();

        // get the closest transform in the TSR Chain to a query transform
        OpenRAVE::dReal GetClosestTransform(const OpenRAVE::Transform &T0_s, OpenRAVE::dReal *TSRJointVals, OpenRAVE::Transform &T0_closeset);  // TODO: read this

        // create a virtual manipulator (a robot) corresponding to the TSR chain to use for ik solver calls
        bool RobotizeTSRChain(const OpenRAVE::EnvironmentBasePtr &penv_in, OpenRAVE::RobotBasePtr &probot_out);

        // apply mimiced joint values to a certain set of joints
        bool ApplyMimicValuesToMimicBody(const OpenRAVE::dReal *TSRJointVals);

        // turn the list of mimic joint values into a list of full joint values
        bool MimicValuesToFullMimicBodyValues(const OpenRAVE::dReal *TSRJointVals, std::vector<OpenRAVE::dReal> &mimicbodyvals);

        // get the joint limits of the virtual manipulator
        bool GetChainJointLimits(OpenRAVE::dReal *lowerlimits, OpenRAVE::dReal *upperlimits);

        // compute the distance between two transforms
        OpenRAVE::dReal TransformDifference(const OpenRAVE::Transform &tm_ref, const OpenRAVE::Transform &tm_targ);

        // return the sum of the length of the bounds, summed over all TSRs in the chain
        OpenRAVE::dReal GetSumOfBounds() {
            if (_sumbounds < 0)
                        RAVELOG_INFO ("ERROR TSR not initialized\n");
            else return _sumbounds;
        }

        // get the values of the mimiced DOFs
        bool ExtractMimicDOFValues(const OpenRAVE::dReal *TSRValues, OpenRAVE::dReal *MimicDOFVals);

        // get the number of mimiced DOFs
        int GetNumMimicDOF() {
            return _mimicinds.size();
        }

        // get the mimiced DOFs
        std::vector<int> GetMimicDOFInds() {
            return _mimicinds;
        }

        // get the number of DOFs of the virtual manipulator
        int GetNumDOF() {
            if (numdof == -1)
                        RAVELOG_INFO ("ERROR : this chain has not been robotized yet\n");
            return numdof;
        }

        // get a pointer to the mimiced body
        OpenRAVE::RobotBasePtr GetMimicBody() {
            return _pmimicbody;
        }

        // is this TSR chain used for sampling goals?
        bool IsForGoalSampling() {
            return bSampleGoalFromChain;
        }

        // is this TSR chain used for sampling starts?
        bool IsForStartSampling() {
            return bSampleStartFromChain;
        }

        // is this TSR chain used for constraining the whole path?
        bool IsForConstraint() {
            return bConstrainToChain;
        }

        // write the TSR Chain to a string
        bool serialize(std::ostream &O) const;

        // parse a string to set the values of the TSR Chain
        bool deserialize(std::stringstream &_ss);   // TODO: add xml input routine

        // parse a string const from matlab to set the& values of the TSR Chain
        bool deserialize_from_matlab(const OpenRAVE::RobotBasePtr &robot_in, const OpenRAVE::EnvironmentBasePtr &penv_in, std::istream &_ss);

    private:

        void DestoryRobotizedTSRChain(); ///< delete the virtual manipulator from the environment

        bool bSampleGoalFromChain;
        bool bSampleStartFromChain;
        bool bConstrainToChain;

        OpenRAVE::Transform Tw0_e;
        int numdof;

        OpenRAVE::RobotBasePtr robot;
        OpenRAVE::IkSolverBasePtr _pIkSolver;
        OpenRAVE::EnvironmentBasePtr penv;

        std::string mimicbodyname;
        OpenRAVE::RobotBasePtr _pmimicbody;
        std::vector<int> _mimicinds;
        std::vector<OpenRAVE::dReal> _mimicjointvals_temp;
        std::vector<OpenRAVE::dReal> _mimicjointoffsets;
        std::vector<OpenRAVE::dReal> _lowerlimits;
        std::vector<OpenRAVE::dReal> _upperlimits;
        bool _bPointTSR;

        OpenRAVE::Transform _tmtemp;
        std::vector<OpenRAVE::dReal> _dx;
        OpenRAVE::dReal _sumsqr;

        OpenRAVE::dReal _sumbounds;

        std::vector<OpenRAVE::dReal> ikparams;
    };
}
#endif //ATLASMPNET_TASKSPACEREGIONCHAIN_H
