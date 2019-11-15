//
// Created by jiangeng on 10/11/19.
//

#ifndef ATLASMPNET_CONSTRAINT_H
#define ATLASMPNET_CONSTRAINT_H

#include <ompl/base/Constraint.h>
#include <openrave/openrave.h>

#include "TSRChain.h"

namespace AtlasMPNet {
    class TSRChainConstraint : public ompl::base::Constraint {
    public:
        typedef std::shared_ptr<TSRChainConstraint> Ptr;

        TSRChainConstraint(const OpenRAVE::RobotBasePtr &robot, const TSRChain::Ptr &tsr_chain);

        void function(const Eigen::Ref<const Eigen::VectorXd> &x, Eigen::Ref<Eigen::VectorXd> out) const override;

        void jacobian(const Eigen::Ref<const Eigen::VectorXd> &x, Eigen::Ref<Eigen::MatrixXd> out) const override;

        double distance(const Eigen::Ref<const Eigen::VectorXd> &x) const override;

        void functiontest(const Eigen::Ref<const Eigen::VectorXd> &x, Eigen::Ref<Eigen::VectorXd> out) const;

        void jacobiantest(const Eigen::Ref<const Eigen::VectorXd> &x, Eigen::Ref<Eigen::MatrixXd> out) const;

        void testNewtonRaphson(const Eigen::Ref<Eigen::VectorXd> x0);

    private:
        TSRChain::Ptr _tsr_chain;
        OpenRAVE::RobotBasePtr _robot;
        mutable int count_ = 0;

        Eigen::Affine3d robotFK(const Eigen::Ref<const Eigen::VectorXd> &x) const;
    };

    class SphereConstraint : public ompl::base::Constraint {
    public:
        explicit SphereConstraint(const unsigned int dim) : ompl::base::Constraint(dim, 1) {
        }

        void function(const Eigen::Ref<const Eigen::VectorXd> &x, Eigen::Ref<Eigen::VectorXd> out) const override {
            out[0] = x.norm() - 1;
        }

        void jacobian(const Eigen::Ref<const Eigen::VectorXd> &x, Eigen::Ref<Eigen::MatrixXd> out) const override {
            out = x.transpose().normalized();
        }
    };
}
#endif //ATLASMPNET_CONSTRAINT_H
